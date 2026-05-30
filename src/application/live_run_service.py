"""Shared live-run orchestration service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from dataclasses import replace
import threading
import time
from typing import Any

import numpy as np
from PIL import Image

from src.application.camera_errors import normalize_camera_runtime_error
from src.application.device_factory import (
    apply_measurement_acquisition_roi,
    build_measurement_capture_plan,
    build_metric_source,
    build_temp_controller,
)
from src.application.frame_pixel_contract import validate_frame_pixel_contract
from src.application.live_preview_service import LivePreviewService
from src.application.preview_render import build_preview_bitmap, enhance_preview_bitmap
from src.application.live_run_registry import LiveRunDraftRegistry
from src.application.real_offline_alignment_guard import (
    assert_real_offline_alignment_ready,
    assert_real_offline_definition_ready,
)
from src.application.runtime_config import RuntimeConfig
from src.core.config_models import DeviceRoiConfig
from src.core.enums import CaptureMode, RunStatus
from src.core.models import FramePacket, MeasurementDefinition, RunDraftRecord
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SqliteSessionRepo
from src.workflow.live_run import (
    LiveRunCoordinator,
    LiveRunExecution,
    LiveRunStopRequested,
    LiveRunTrackingInvalidated,
    build_partial_live_run_execution,
)


@dataclass(slots=True)
class _ActiveLiveRun:
    run_id: str
    stop_event: threading.Event
    status: RunStatus = RunStatus.CREATED
    telemetry: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    execution: LiveRunExecution | None = None
    measurement_capture_plan: dict[str, Any] | None = None
    error_detail: str = ""
    thread: threading.Thread | None = None
    preview_display_max_width: int = 816
    preview_display_max_height: int = 544
    tracking_preview_min_interval_ms: int = 250
    last_tracking_preview_cached_at_ms: int = 0
    tracking_preview_base_image: np.ndarray | None = None
    tracking_preview_base_source_size: tuple[int, int] | None = None


class LiveRunService:
    """Background live-run orchestration entry point."""

    def __init__(
        self,
        *,
        repo: SqliteSessionRepo,
        artifact_store: SessionArtifactStore,
        preview_service: LivePreviewService,
        temp_controller_factory: Callable[[], object] | None = None,
    ) -> None:
        self.repo = repo
        self.artifact_store = artifact_store
        self.preview_service = preview_service
        self._temp_controller_factory = temp_controller_factory
        self._state_lock = threading.Lock()
        self._active_runs: dict[str, _ActiveLiveRun] = {}
        self._recent_runs: dict[str, _ActiveLiveRun] = {}

    def start_run(
        self,
        *,
        record: RunDraftRecord,
        runtime_config: RuntimeConfig,
        target_temperature_celsius: float,
        registry: LiveRunDraftRegistry,
    ) -> object:
        if record.definition is None:
            raise ValueError("measurement definition is required before starting a live run")
        assert_real_offline_alignment_ready(runtime_config, context="live_run_start")
        assert_real_offline_definition_ready(runtime_config, record.definition, context="live_run_start")

        with self._state_lock:
            if any(
                active_run.thread is not None and active_run.thread.is_alive()
                for active_run in self._active_runs.values()
            ):
                raise RuntimeError("another live run is already active")
            if record.run_id in self._active_runs:
                active_run = self._active_runs[record.run_id]
                if active_run.thread is not None and active_run.thread.is_alive():
                    raise RuntimeError(f"live run is already active: {record.run_id}")

            active_run = _ActiveLiveRun(
                run_id=record.run_id,
                stop_event=threading.Event(),
                status=RunStatus.RUNNING,
                preview_display_max_width=int(runtime_config.live.run.preview_display_max_width),
                preview_display_max_height=int(runtime_config.live.run.preview_display_max_height),
                tracking_preview_min_interval_ms=_tracking_preview_min_interval_ms(runtime_config.live.run),
            )
            self._active_runs[record.run_id] = active_run
            self._recent_runs[record.run_id] = active_run

        registry.update_status(record.run_id, RunStatus.RUNNING, capture_mode=CaptureMode.MEASUREMENT)
        worker = threading.Thread(
            target=self._run_worker,
            kwargs={
                "active_run": active_run,
                "record": record,
                "runtime_config": runtime_config,
                "target_temperature_celsius": target_temperature_celsius,
                "registry": registry,
            },
            name=f"live-run-{record.run_id}",
            daemon=True,
        )
        active_run.thread = worker
        worker.start()
        return active_run

    def request_stop(self, run_id: str) -> bool:
        with self._state_lock:
            active_run = self._active_runs.get(run_id)
            if active_run is None:
                return False
            active_run.stop_event.set()
            return True

    def get_snapshot(self, run_id: str) -> object | None:
        with self._state_lock:
            return self._active_runs.get(run_id) or self._recent_runs.get(run_id)

    def _run_worker(
        self,
        *,
        active_run: _ActiveLiveRun,
        record: RunDraftRecord,
        runtime_config: RuntimeConfig,
        target_temperature_celsius: float,
        registry: LiveRunDraftRegistry,
    ) -> None:
        assert record.definition is not None
        runtime_definition = _definition_in_setup_source_space(
            definition=record.definition,
            runtime_config=runtime_config,
            preview_service=self.preview_service,
            run_id=record.run_id,
        )
        requested_measurement_plan = build_measurement_capture_plan(
            runtime_config=runtime_config,
            definition=runtime_definition,
        )
        measurement_plan = requested_measurement_plan
        measurement_capture_plan = _measurement_capture_plan_payload(
            original_definition=record.definition,
            requested_measurement_plan=requested_measurement_plan,
            applied_measurement_plan=None,
        )
        with self._state_lock:
            active_run.measurement_capture_plan = measurement_capture_plan
        effective_runtime_config = _runtime_config_with_measurement_profile(
            runtime_config,
            requested_measurement_plan.measurement_profile,
        )
        effective_runtime_config = _runtime_config_with_operator_output_power(
            effective_runtime_config,
            record,
        )
        camera: object | None = None
        try:
            self.preview_service.retire_active_stream(timeout_ms=3_000)
            camera = self.preview_service.open_camera(effective_runtime_config, profile_name="measurement")
            self._open_camera_if_supported(camera)
            applied_device_roi = _camera_applied_device_roi(camera)
            measurement_plan = (
                apply_measurement_acquisition_roi(
                    requested_measurement_plan,
                    runtime_config=runtime_config,
                    definition=runtime_definition,
                    applied_device_roi=applied_device_roi,
                )
                if applied_device_roi is not None
                else requested_measurement_plan
            )
            measurement_capture_plan = _measurement_capture_plan_payload(
                original_definition=record.definition,
                requested_measurement_plan=requested_measurement_plan,
                applied_measurement_plan=measurement_plan,
            )
            with self._state_lock:
                active_run.measurement_capture_plan = measurement_capture_plan
            effective_runtime_config = _runtime_config_with_measurement_profile(
                runtime_config,
                measurement_plan.measurement_profile,
            )
            effective_runtime_config = _runtime_config_with_operator_output_power(
                effective_runtime_config,
                record,
            )
            temp_controller = self._build_temp_controller(effective_runtime_config)
            metric_source = self._build_metric_source(
                runtime_config=effective_runtime_config,
                definition=measurement_plan.metric_definition,
                target_temperature_celsius=target_temperature_celsius,
            )
            camera = _FramePixelContractCamera(
                camera,
                runtime_config=effective_runtime_config,
                profile_name="measurement",
            )
            coordinator = LiveRunCoordinator(repo=self.repo, artifact_store=self.artifact_store)
            execution = coordinator.run(
                session_id=record.run_id,
                definition=runtime_definition,
                target_temperature_celsius=target_temperature_celsius,
                run_config=effective_runtime_config.live.run,
                analysis_engine=runtime_config.live.analysis.engine,
                channel_name=runtime_config.live.analysis.channel_name,
                as_fit_point_count=runtime_config.live.analysis.as_fit_point_count,
                af_fit_point_count=runtime_config.live.analysis.af_fit_point_count,
                camera_config=effective_runtime_config.live.camera,
                effective_definition=measurement_plan.metric_definition,
                measurement_capture_plan=measurement_capture_plan,
                camera=camera,
                temp_reader=temp_controller,
                temp_controller=temp_controller,
                metric_source=metric_source,
                quality_threshold=runtime_config.live.vision.quality_threshold,
                stop_on_target_reached=_completion_mode_for_record(record, runtime_config) != "manual_stop_only",
                stop_requested=active_run.stop_event.is_set,
                wait_for_next_sample=active_run.stop_event.wait,
                status_callback=lambda status_value, payload: self._update_status(
                    active_run,
                    registry,
                    status_value,
                    payload=payload,
                ),
                telemetry_callback=lambda row: self._append_telemetry(active_run, row),
                sample_callback=lambda sync_point, row: self._cache_tracking_frame(record.run_id, sync_point, row),
            )
        except LiveRunTrackingInvalidated as exc:
            self._store_error(active_run, exc.detail)
            self._update_status(active_run, registry, RunStatus.INVALIDATED, payload={"reason": exc.reason})
            self._update_status(active_run, registry, RunStatus.STOPPING, payload={"reason": exc.reason})
            self._persist_partial_terminal_execution(
                active_run=active_run,
                record=record,
                runtime_config=effective_runtime_config,
                effective_definition=measurement_plan.metric_definition,
                measurement_capture_plan=measurement_capture_plan,
                terminal_state=RunStatus.ABORTED,
                terminal_reason=exc.reason,
                terminal_detail=exc.detail,
            )
            self._update_status(
                active_run,
                registry,
                RunStatus.ABORTED,
                payload={"reason": exc.reason},
                capture_mode=CaptureMode.POST_RUN_REVIEW,
            )
        except LiveRunStopRequested as exc:
            self._store_error(active_run, exc.detail)
            self._update_status(active_run, registry, RunStatus.STOPPING, payload={"reason": exc.reason})
            self._persist_partial_terminal_execution(
                active_run=active_run,
                record=record,
                runtime_config=effective_runtime_config,
                effective_definition=measurement_plan.metric_definition,
                measurement_capture_plan=measurement_capture_plan,
                terminal_state=RunStatus.ABORTED,
                terminal_reason=exc.reason,
                terminal_detail=exc.detail,
            )
            self._update_status(
                active_run,
                registry,
                RunStatus.ABORTED,
                payload={"reason": exc.reason},
                capture_mode=CaptureMode.POST_RUN_REVIEW,
            )
        except Exception as exc:
            normalized_detail = normalize_camera_runtime_error(exc)
            self._store_error(active_run, normalized_detail)
            self._persist_partial_terminal_execution(
                active_run=active_run,
                record=record,
                runtime_config=effective_runtime_config,
                effective_definition=measurement_plan.metric_definition,
                measurement_capture_plan=measurement_capture_plan,
                terminal_state=RunStatus.FAILED,
                terminal_reason="runtime_error",
                terminal_detail=normalized_detail,
            )
            self._update_status(
                active_run,
                registry,
                RunStatus.FAILED,
                payload={"reason": normalized_detail},
                capture_mode=CaptureMode.POST_RUN_REVIEW,
            )
        else:
            with self._state_lock:
                active_run.execution = execution
                active_run.events = list(execution.events)
                active_run.telemetry = list(execution.telemetry)
            self._update_status(
                active_run,
                registry,
                RunStatus.COMPLETED,
                payload={"point_count": execution.summary.point_count},
                capture_mode=CaptureMode.POST_RUN_REVIEW,
            )
        finally:
            with self._state_lock:
                self._active_runs.pop(record.run_id, None)
            if camera is not None:
                close = getattr(camera, "close", None)
                if callable(close):
                    close()

    def _append_telemetry(self, active_run: _ActiveLiveRun, row: dict[str, Any]) -> None:
        preview_source_size: tuple[int, int] | None = None
        preview_size: tuple[int, int] | None = None
        with self._state_lock:
            preview_source_size = active_run.tracking_preview_base_source_size
            preview_image = active_run.tracking_preview_base_image
            if preview_image is not None and getattr(preview_image, "shape", None) is not None:
                preview_size = (int(preview_image.shape[1]), int(preview_image.shape[0]))
        _augment_telemetry_for_setup_preview(
            row,
            active_run.measurement_capture_plan,
            preview_source_size=preview_source_size,
            preview_size=preview_size,
        )
        with self._state_lock:
            active_run.telemetry.append(dict(row))

    def _cache_tracking_frame(self, run_id: str, sync_point, telemetry_row: dict[str, Any]) -> None:
        frame = getattr(sync_point, "frame", None)
        if frame is None:
            return
        measurement_capture_plan = None
        active_run: _ActiveLiveRun | None = None
        with self._state_lock:
            active_run = self._active_runs.get(run_id) or self._recent_runs.get(run_id)
            if active_run is not None:
                measurement_capture_plan = active_run.measurement_capture_plan
                sample_timestamp_ms = int(getattr(sync_point, "timestamp_ms", 0) or 0)
                if not _should_cache_tracking_preview(active_run, sample_timestamp_ms):
                    return
        composited_frame, preview_points = _composite_tracking_frame_into_setup_preview(
            preview_service=self.preview_service,
            active_run=active_run,
            run_id=run_id,
            measurement_frame=frame,
            measurement_capture_plan=measurement_capture_plan,
        )
        point_a_preview = preview_points.point_a or _preview_point_from_tracking_frame_meta(
            composited_frame.meta,
            telemetry_row.get("point_a_px"),
        )
        point_b_preview = preview_points.point_b or _preview_point_from_tracking_frame_meta(
            composited_frame.meta,
            telemetry_row.get("point_b_px"),
        )
        if point_a_preview is not None:
            telemetry_row["point_a_preview_px"] = point_a_preview
        if point_b_preview is not None:
            telemetry_row["point_b_preview_px"] = point_b_preview
        self.preview_service.cache_tracking_frame(run_id=run_id, frame=composited_frame)
        if active_run is not None:
            with self._state_lock:
                active_run.last_tracking_preview_cached_at_ms = int(getattr(sync_point, "timestamp_ms", 0) or _now_ms())

    def _store_error(self, active_run: _ActiveLiveRun, detail: str) -> None:
        with self._state_lock:
            active_run.error_detail = detail

    def _persist_partial_terminal_execution(
        self,
        *,
        active_run: _ActiveLiveRun,
        record: RunDraftRecord,
        runtime_config: RuntimeConfig,
        effective_definition: MeasurementDefinition,
        measurement_capture_plan: dict[str, Any],
        terminal_state: RunStatus,
        terminal_reason: str | None,
        terminal_detail: str,
    ) -> None:
        if record.definition is None:
            return
        with self._state_lock:
            telemetry = list(active_run.telemetry)
            events = list(active_run.events)
        started_at_ms = _started_at_ms(events, fallback_ms=record.created_at_ms or _now_ms())
        execution = build_partial_live_run_execution(
            session_id=record.run_id,
            started_at_ms=started_at_ms,
            terminal_state=terminal_state.value,
            terminal_reason=terminal_reason,
            terminal_detail=terminal_detail,
            definition=record.definition,
            telemetry=telemetry,
            events=events,
            camera_config=runtime_config.live.camera,
            analysis_engine=runtime_config.live.analysis.engine,
            channel_name=runtime_config.live.analysis.channel_name,
            as_fit_point_count=runtime_config.live.analysis.as_fit_point_count,
            af_fit_point_count=runtime_config.live.analysis.af_fit_point_count,
            target_measurement_hz=runtime_config.live.run.measurement_target_hz,
        )
        try:
            self.artifact_store.save_live_bundle(
                record.run_id,
                definition=_definition_payload(record.definition),
                definition_original=_definition_payload(record.definition),
                definition_effective_local=_definition_payload(effective_definition),
                measurement_capture_plan=measurement_capture_plan,
                telemetry=execution.telemetry,
                detail=execution.detail,
                result=execution.result,
                events=execution.events,
                afas_dataset=execution.afas_dataset,
                keyframes=execution.detail.get("key_frames", []),
            )
            self.repo.save_summary(execution.summary)
        except Exception as exc:
            self._store_error(active_run, f"{terminal_detail}; partial artifact save failed: {exc}")
            return
        with self._state_lock:
            active_run.execution = execution
            active_run.events = list(execution.events)
            active_run.telemetry = list(execution.telemetry)

    def _update_status(
        self,
        active_run: _ActiveLiveRun,
        registry: LiveRunDraftRegistry,
        status: RunStatus,
        *,
        payload: dict[str, Any],
        capture_mode: CaptureMode | None = None,
    ) -> None:
        with self._state_lock:
            active_run.status = status
            active_run.events.append(
                {
                    "timestamp_ms": _now_ms(),
                    "type": "state_changed",
                    "payload": {"status": status.value, **payload},
                }
            )
        registry.update_status(active_run.run_id, status, capture_mode=capture_mode)

    def _build_temp_controller(self, runtime_config: RuntimeConfig) -> object:
        if self._temp_controller_factory is not None:
            return self._temp_controller_factory()
        return build_temp_controller(runtime_config)

    def _build_metric_source(
        self,
        *,
        runtime_config: RuntimeConfig,
        definition: MeasurementDefinition,
        target_temperature_celsius: float,
    ) -> object:
        return build_metric_source(
            runtime_config=runtime_config,
            definition=definition,
            target_temperature_celsius=target_temperature_celsius,
        )

    @staticmethod
    def _open_camera_if_supported(camera: object) -> None:
        open_method = getattr(camera, "open", None)
        if callable(open_method):
            open_method()


class _FramePixelContractCamera:
    def __init__(self, camera: object, *, runtime_config: RuntimeConfig, profile_name: str) -> None:
        self._camera = camera
        self._runtime_config = runtime_config
        self._profile_name = str(profile_name)

    def read_frame(self) -> FramePacket:
        read_frame = getattr(self._camera, "read_frame")
        frame = read_frame()
        return validate_frame_pixel_contract(
            self._runtime_config,
            profile_name=self._profile_name,
            frame=frame,
            context="live_run_measurement_frame",
        )

    def __getattr__(self, name: str) -> object:
        return getattr(self._camera, name)


def _runtime_config_with_measurement_profile(
    runtime_config: RuntimeConfig,
    measurement_profile,
) -> RuntimeConfig:
    live_camera = replace(runtime_config.live.camera, measurement=measurement_profile)
    live_config = replace(runtime_config.live, camera=live_camera)
    return replace(runtime_config, live=live_config)


def _runtime_config_with_operator_output_power(
    runtime_config: RuntimeConfig,
    record: RunDraftRecord,
) -> RuntimeConfig:
    if record.temperature_settings is None:
        return runtime_config
    control = replace(
        runtime_config.live.temp.control,
        startup_power_percent=float(record.temperature_settings.output_power_percent),
    )
    temp = replace(runtime_config.live.temp, control=control)
    live_config = replace(runtime_config.live, temp=temp)
    return replace(runtime_config, live=live_config)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _completion_mode_for_record(record: RunDraftRecord, runtime_config: RuntimeConfig) -> str:
    if record.temperature_settings is not None:
        return str(record.temperature_settings.completion_mode or "target_reached")
    return str(runtime_config.live.temp.control.completion_mode or "target_reached")


def _started_at_ms(events: list[dict[str, Any]], *, fallback_ms: int) -> int:
    if events:
        timestamp_ms = events[0].get("timestamp_ms")
        if timestamp_ms is not None:
            return int(timestamp_ms)
    return int(fallback_ms)


def _definition_payload(definition: MeasurementDefinition) -> dict[str, Any]:
    return {
        "analysis_roi": {
            "x": definition.analysis_roi.x,
            "y": definition.analysis_roi.y,
            "width": definition.analysis_roi.width,
            "height": definition.analysis_roi.height,
        },
        "metric_box": {
            "center_x": definition.metric_box.center_x,
            "center_y": definition.metric_box.center_y,
            "width": definition.metric_box.width,
            "height": definition.metric_box.height,
            "angle_deg": definition.metric_box.angle_deg,
        },
        "point_a_px": {
            "x": definition.point_a_px.x,
            "y": definition.point_a_px.y,
        },
        "point_b_px": {
            "x": definition.point_b_px.x,
            "y": definition.point_b_px.y,
        },
        "observation_axis": definition.observation_axis.value,
        "foreground_polarity": definition.foreground_polarity,
        "threshold_mode": definition.threshold_mode,
        "ignore_internal_texture": definition.ignore_internal_texture,
        "min_target_area_px": definition.min_target_area_px,
        "sensitivity": definition.sensitivity,
        "direction_angle_deg": definition.direction_angle_deg,
        "direction_projection_mode": definition.direction_projection_mode,
        "target_geometry_mode": definition.target_geometry_mode,
        "side_guard_ratio": definition.side_guard_ratio,
        "envelope_min_support_px": definition.envelope_min_support_px,
        "envelope_quantile": definition.envelope_quantile,
    }


def _measurement_capture_plan_payload(
    *,
    original_definition: MeasurementDefinition,
    requested_measurement_plan,
    applied_measurement_plan,
) -> dict[str, Any]:
    setup_preview_roi = requested_measurement_plan.setup_preview_roi
    requested_roi = requested_measurement_plan.measurement_profile.device_roi
    applied_roi = (
        applied_measurement_plan.measurement_profile.device_roi
        if applied_measurement_plan is not None
        else None
    )
    effective_roi = applied_roi or requested_roi
    return {
        "effective_acquisition_roi": {
            "x": int(effective_roi.x),
            "y": int(effective_roi.y),
            "width": int(effective_roi.width),
            "height": int(effective_roi.height),
        },
        "requested_effective_acquisition_roi": {
            "x": int(requested_roi.x),
            "y": int(requested_roi.y),
            "width": int(requested_roi.width),
            "height": int(requested_roi.height),
        },
        "applied_effective_acquisition_roi": None
        if applied_roi is None
        else {
            "x": int(applied_roi.x),
            "y": int(applied_roi.y),
            "width": int(applied_roi.width),
            "height": int(applied_roi.height),
        },
        "setup_preview_sensor_roi": {
            "x": int(setup_preview_roi.x),
            "y": int(setup_preview_roi.y),
            "width": int(setup_preview_roi.width),
            "height": int(setup_preview_roi.height),
        },
        "effective_local_origin_in_setup_preview_px": {
            "x": int(effective_roi.x - setup_preview_roi.x),
            "y": int(effective_roi.y - setup_preview_roi.y),
        },
        "requested_local_origin_in_setup_preview_px": {
            "x": int(requested_roi.x - setup_preview_roi.x),
            "y": int(requested_roi.y - setup_preview_roi.y),
        },
        "setup_to_effective_local_translation_px": {
            "dx": int(setup_preview_roi.x - effective_roi.x),
            "dy": int(setup_preview_roi.y - effective_roi.y),
        },
        "setup_to_requested_local_translation_px": {
            "dx": int(setup_preview_roi.x - requested_roi.x),
            "dy": int(setup_preview_roi.y - requested_roi.y),
        },
    }


def _definition_in_setup_source_space(
    *,
    definition: MeasurementDefinition,
    runtime_config: RuntimeConfig,
    preview_service: LivePreviewService,
    run_id: str,
) -> MeasurementDefinition:
    del runtime_config, preview_service, run_id
    # The current Web setup sends definition geometry in preview source-frame
    # coordinates. Do not infer display-coordinate input from small ROI values;
    # source-frame ROIs near the upper-left can legitimately fit inside the
    # 816x543 display bounds.
    return definition


def _camera_applied_device_roi(camera: object) -> DeviceRoiConfig | None:
    getter = getattr(camera, "get_applied_device_roi", None)
    if not callable(getter):
        return None
    payload = getter()
    if isinstance(payload, DeviceRoiConfig):
        return DeviceRoiConfig(
            x=int(payload.x),
            y=int(payload.y),
            width=int(payload.width),
            height=int(payload.height),
        )
    return None


def _augment_telemetry_for_setup_preview(
    row: dict[str, Any],
    measurement_capture_plan: dict[str, Any] | None,
    *,
    preview_source_size: tuple[int, int] | None = None,
    preview_size: tuple[int, int] | None = None,
) -> None:
    origin = _effective_local_origin(measurement_capture_plan)
    if origin is None:
        return
    if preview_source_size is None or preview_size is None:
        return
    for key in (
        "point_a",
        "point_b",
        "source_point_a",
        "source_point_b",
        "axis_point_a",
        "axis_point_b",
    ):
        preview_key = f"{key}_preview_px"
        if row.get(preview_key) is not None:
            continue
        source_point = _translate_point_to_setup_preview(row.get(f"{key}_px"), origin)
        if source_point is None:
            continue
        row[preview_key] = list(
            _scale_point_to_preview(
                point=(int(source_point[0]), int(source_point[1])),
                source_size=preview_source_size,
                preview_size=preview_size,
            )
        )


def _translate_point_to_setup_preview(
    point: Any,
    origin: tuple[int, int] | None,
) -> list[int] | None:
    if origin is None or not isinstance(point, (list, tuple)) or len(point) != 2:
        return None
    try:
        return [int(point[0]) + int(origin[0]), int(point[1]) + int(origin[1])]
    except (TypeError, ValueError):
        return None


def _effective_local_origin(
    measurement_capture_plan: dict[str, Any] | None,
) -> tuple[int, int] | None:
    if not isinstance(measurement_capture_plan, dict):
        return None
    payload = measurement_capture_plan.get("effective_local_origin_in_setup_preview_px")
    if not isinstance(payload, dict):
        return None
    try:
        return int(payload.get("x", 0) or 0), int(payload.get("y", 0) or 0)
    except (TypeError, ValueError):
        return None


def _should_cache_tracking_preview(active_run: _ActiveLiveRun, sample_timestamp_ms: int) -> bool:
    if sample_timestamp_ms <= 0:
        return True
    if active_run.last_tracking_preview_cached_at_ms <= 0:
        return True
    return sample_timestamp_ms - active_run.last_tracking_preview_cached_at_ms >= active_run.tracking_preview_min_interval_ms


def _tracking_preview_min_interval_ms(run_config: Any) -> int:
    return max(50, int(getattr(run_config, "preview_poll_ms", 0) or 250))


@dataclass(slots=True)
class _TrackingPreviewBase:
    image: np.ndarray
    source_size: tuple[int, int]


@dataclass(slots=True)
class _TrackingPreviewPoints:
    point_a: list[int] | None = None
    point_b: list[int] | None = None


def _composite_tracking_frame_into_setup_preview(
    *,
    preview_service: LivePreviewService,
    active_run: _ActiveLiveRun | None,
    run_id: str,
    measurement_frame: FramePacket,
    measurement_capture_plan: dict[str, Any] | None,
) -> tuple[FramePacket, _TrackingPreviewPoints]:
    base_preview = _tracking_preview_base(
        preview_service=preview_service,
        active_run=active_run,
        run_id=run_id,
    )
    origin = _effective_local_origin(measurement_capture_plan)
    if base_preview is None:
        return measurement_frame, _TrackingPreviewPoints()
    if origin is None or measurement_frame.image is None:
        return _tracking_preview_fallback_frame(
            base_preview=base_preview,
            measurement_frame=measurement_frame,
        ), _TrackingPreviewPoints()
    measurement_width, measurement_height = _frame_image_dimensions(measurement_frame)
    if measurement_width < 1 or measurement_height < 1:
        return _tracking_preview_fallback_frame(
            base_preview=base_preview,
            measurement_frame=measurement_frame,
        ), _TrackingPreviewPoints()

    base_image = base_preview.image.copy()
    base_height, base_width = int(base_image.shape[0]), int(base_image.shape[1])
    source_width = max(1, int(base_preview.source_size[0]))
    source_height = max(1, int(base_preview.source_size[1]))
    preview_scale_x = base_width / source_width
    preview_scale_y = base_height / source_height
    origin_x = int(round(origin[0] * preview_scale_x))
    origin_y = int(round(origin[1] * preview_scale_y))
    if origin_x >= base_width or origin_y >= base_height:
        return _tracking_preview_fallback_frame(
            base_preview=base_preview,
            measurement_frame=measurement_frame,
        ), _TrackingPreviewPoints()

    target_width = max(1, int(round(measurement_width * preview_scale_x)))
    target_height = max(1, int(round(measurement_height * preview_scale_y)))
    measurement_image = _preview_scaled_grayscale_image(
        measurement_frame.image,
        target_width=target_width,
        target_height=target_height,
    )
    if measurement_image is None:
        return _tracking_preview_fallback_frame(
            base_preview=base_preview,
            measurement_frame=measurement_frame,
        ), _TrackingPreviewPoints()
    measurement_height, measurement_width = int(measurement_image.shape[0]), int(measurement_image.shape[1])

    paste_x = max(0, origin_x)
    paste_y = max(0, origin_y)
    crop_x = max(0, -origin_x)
    crop_y = max(0, -origin_y)
    paste_width = min(measurement_width - crop_x, max(0, base_width - paste_x))
    paste_height = min(measurement_height - crop_y, max(0, base_height - paste_y))
    if paste_width < 1 or paste_height < 1:
        return _tracking_preview_fallback_frame(
            base_preview=base_preview,
            measurement_frame=measurement_frame,
        ), _TrackingPreviewPoints()

    base_image[paste_y : paste_y + paste_height, paste_x : paste_x + paste_width] = measurement_image[
        crop_y : crop_y + paste_height,
        crop_x : crop_x + paste_width,
    ]
    meta = dict(measurement_frame.meta or {})
    meta["tracking_composited"] = True
    meta["tracking_preview_already_enhanced"] = True
    meta["tracking_origin_source_px"] = [int(origin[0]), int(origin[1])]
    meta["tracking_origin_preview_px"] = [origin_x, origin_y]
    meta["tracking_paste_origin_preview_px"] = [paste_x, paste_y]
    meta["tracking_paste_crop_preview_px"] = [crop_x, crop_y]
    meta["tracking_preview_width"] = base_width
    meta["tracking_preview_height"] = base_height
    meta["tracking_preview_source_width"] = source_width
    meta["tracking_preview_source_height"] = source_height
    meta["tracking_preview_scale_x"] = float(preview_scale_x)
    meta["tracking_preview_scale_y"] = float(preview_scale_y)
    preview_points = _TrackingPreviewPoints(
        point_a=_scale_local_point_to_setup_preview(
            point=_shape_metric_meta_point(measurement_frame.meta, "point_a_px_local"),
            origin=origin,
            source_size=base_preview.source_size,
            preview_size=(base_width, base_height),
        ),
        point_b=_scale_local_point_to_setup_preview(
            point=_shape_metric_meta_point(measurement_frame.meta, "point_b_px_local"),
            origin=origin,
            source_size=base_preview.source_size,
            preview_size=(base_width, base_height),
        ),
    )
    return (
        FramePacket(
            timestamp_ms=int(measurement_frame.timestamp_ms),
            source=measurement_frame.source,
            image=base_image,
            frame_id=measurement_frame.frame_id,
            meta=meta,
        ),
        preview_points,
    )


def _tracking_preview_fallback_frame(
    *,
    base_preview: _TrackingPreviewBase,
    measurement_frame: FramePacket,
) -> FramePacket:
    base_image = base_preview.image.copy()
    meta = dict(measurement_frame.meta or {})
    meta["tracking_composited"] = False
    meta["tracking_preview_fallback"] = True
    meta["tracking_preview_already_enhanced"] = True
    meta["tracking_preview_source_width"] = int(base_preview.source_size[0])
    meta["tracking_preview_source_height"] = int(base_preview.source_size[1])
    meta["tracking_preview_scale_x"] = 1.0
    meta["tracking_preview_scale_y"] = 1.0
    return FramePacket(
        timestamp_ms=int(measurement_frame.timestamp_ms),
        source=measurement_frame.source,
        image=base_image,
        frame_id=measurement_frame.frame_id,
        meta=meta,
    )


def _tracking_preview_base(
    *,
    preview_service: LivePreviewService,
    active_run: _ActiveLiveRun | None,
    run_id: str,
) -> _TrackingPreviewBase | None:
    if (
        active_run is not None
        and active_run.tracking_preview_base_image is not None
        and active_run.tracking_preview_base_source_size is not None
    ):
        return _TrackingPreviewBase(
            image=active_run.tracking_preview_base_image,
            source_size=active_run.tracking_preview_base_source_size,
        )
    base_frame = preview_service.get_cached_frame(run_id=run_id)
    if base_frame is None or base_frame.image is None:
        return None
    bitmap = enhance_preview_bitmap(
        build_preview_bitmap(
            base_frame.image,
            max_width=active_run.preview_display_max_width if active_run is not None else 816,
            max_height=active_run.preview_display_max_height if active_run is not None else 544,
        )
    )
    image = np.frombuffer(bitmap.pixels, dtype=np.uint8).reshape((bitmap.height, bitmap.width)).copy()
    source_size = _frame_image_dimensions(base_frame)
    if active_run is not None:
        active_run.tracking_preview_base_image = image
        active_run.tracking_preview_base_source_size = source_size
    return _TrackingPreviewBase(image=image, source_size=source_size)


def _frame_image_dimensions(frame: FramePacket) -> tuple[int, int]:
    image = frame.image
    if hasattr(image, "shape"):
        shape = getattr(image, "shape")
        if len(shape) >= 2:
            return int(shape[1]), int(shape[0])
    if isinstance(image, (list, tuple)):
        height = len(image)
        if height == 0:
            return (0, 0)
        first_row = image[0]
        if isinstance(first_row, (list, tuple)):
            return (len(first_row), height)
        return (height, 1)
    return (0, 0)


def _preview_scaled_grayscale_image(
    image: Any,
    *,
    target_width: int,
    target_height: int,
) -> np.ndarray | None:
    target_width = max(1, int(target_width))
    target_height = max(1, int(target_height))
    native_bitmap_payload = getattr(image, "downsample_bitmap_payload", None)
    if callable(native_bitmap_payload):
        try:
            width, height, pixels = native_bitmap_payload(max_width=target_width, max_height=target_height)
            width = int(width)
            height = int(height)
            if width == target_width and height == target_height:
                payload = _coerce_native_bitmap_pixels(pixels, expected_size=target_width * target_height)
                if payload is not None:
                    return np.frombuffer(payload, dtype=np.uint8).reshape((height, width))
        except Exception:
            pass

    if isinstance(image, np.ndarray):
        array_view = image
    elif all(hasattr(image, attr) for attr in ("_buffer", "width", "height")):
        try:
            width = int(getattr(image, "width"))
            height = int(getattr(image, "height"))
            buffer_bytes = getattr(image, "_buffer")
            array_view = np.frombuffer(buffer_bytes, dtype=np.uint8, count=width * height).reshape(height, width)
        except Exception:
            return None
    else:
        try:
            array_view = np.asarray(image, dtype=np.uint8)
        except Exception:
            return None
    if getattr(array_view, "ndim", 0) != 2:
        return None
    if int(array_view.shape[1]) == target_width and int(array_view.shape[0]) == target_height:
        return array_view
    return np.asarray(
        Image.fromarray(array_view, mode="L").resize((target_width, target_height), resample=Image.BILINEAR),
        dtype=np.uint8,
    )


def _coerce_native_bitmap_pixels(pixels: Any, *, expected_size: int) -> bytes | None:
    if expected_size <= 0 or pixels is None:
        return None
    if isinstance(pixels, bytes):
        payload = pixels
    elif isinstance(pixels, bytearray):
        payload = bytes(pixels)
    elif isinstance(pixels, memoryview):
        payload = pixels.tobytes()
    elif isinstance(pixels, np.ndarray):
        payload = np.asarray(pixels, dtype=np.uint8).reshape(-1).tobytes()
    else:
        try:
            payload = bytes(pixels)
        except Exception:
            return None
    if len(payload) < expected_size:
        return None
    if len(payload) > expected_size:
        payload = payload[:expected_size]
    return payload


def _scale_point_to_preview(
    *,
    point: tuple[int, int],
    source_size: tuple[int, int],
    preview_size: tuple[int, int],
) -> tuple[int, int]:
    source_width = max(1, int(source_size[0]))
    source_height = max(1, int(source_size[1]))
    preview_width = max(1, int(preview_size[0]))
    preview_height = max(1, int(preview_size[1]))
    return (
        max(0, min(preview_width - 1, int(round(point[0] * preview_width / source_width)))),
        max(0, min(preview_height - 1, int(round(point[1] * preview_height / source_height)))),
    )


def _shape_metric_meta_point(meta: Any, key: str) -> tuple[int, int] | None:
    if not isinstance(meta, dict):
        return None
    payload = meta.get(key)
    if not isinstance(payload, (list, tuple)) or len(payload) != 2:
        return None
    try:
        return int(payload[0]), int(payload[1])
    except (TypeError, ValueError):
        return None


def _scale_local_point_to_setup_preview(
    *,
    point: tuple[int, int] | None,
    origin: tuple[int, int],
    source_size: tuple[int, int],
    preview_size: tuple[int, int],
) -> list[int] | None:
    if point is None:
        return None
    source_point = _translate_point_to_setup_preview(point, origin)
    if source_point is None:
        return None
    return list(
        _scale_point_to_preview(
            point=(int(source_point[0]), int(source_point[1])),
            source_size=source_size,
            preview_size=preview_size,
        )
    )


def _preview_point_from_tracking_frame_meta(meta: Any, point: Any) -> list[int] | None:
    if not isinstance(meta, dict):
        return None
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        return None
    source_origin_payload = meta.get("tracking_origin_source_px")
    if isinstance(source_origin_payload, (list, tuple)) and len(source_origin_payload) == 2:
        try:
            source_width = int(meta["tracking_preview_source_width"])
            source_height = int(meta["tracking_preview_source_height"])
            preview_width = int(meta["tracking_preview_width"])
            preview_height = int(meta["tracking_preview_height"])
            source_point = (
                int(source_origin_payload[0]) + int(point[0]),
                int(source_origin_payload[1]) + int(point[1]),
            )
        except (KeyError, TypeError, ValueError):
            pass
        else:
            return list(
                _scale_point_to_preview(
                    point=source_point,
                    source_size=(source_width, source_height),
                    preview_size=(preview_width, preview_height),
                )
            )

    origin_payload = meta.get("tracking_origin_preview_px")
    if not isinstance(origin_payload, (list, tuple)) or len(origin_payload) != 2:
        return None
    try:
        origin_x = int(origin_payload[0])
        origin_y = int(origin_payload[1])
        scale_x = float(meta.get("tracking_preview_scale_x", 1.0))
        scale_y = float(meta.get("tracking_preview_scale_y", 1.0))
        point_x = float(point[0])
        point_y = float(point[1])
    except (TypeError, ValueError):
        return None
    return [
        int(round(origin_x + point_x * scale_x)),
        int(round(origin_y + point_y * scale_y)),
    ]
