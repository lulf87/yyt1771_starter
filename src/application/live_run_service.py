"""Shared live-run orchestration service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from dataclasses import replace
import threading
import time
from typing import Any

from src.application.device_factory import build_measurement_capture_plan, build_metric_source, build_temp_controller
from src.application.live_preview_service import LivePreviewService
from src.application.live_run_registry import LiveRunDraftRegistry
from src.application.runtime_config import RuntimeConfig
from src.core.enums import CaptureMode, RunStatus
from src.core.models import MeasurementDefinition, RunDraftRecord
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
    error_detail: str = ""
    thread: threading.Thread | None = None


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
        measurement_plan = build_measurement_capture_plan(
            runtime_config=runtime_config,
            definition=record.definition,
        )
        measurement_capture_plan = _measurement_capture_plan_payload(
            original_definition=record.definition,
            effective_definition=measurement_plan.metric_definition,
            measurement_profile=measurement_plan.measurement_profile,
        )
        effective_runtime_config = _runtime_config_with_measurement_profile(
            runtime_config,
            measurement_plan.measurement_profile,
        )

        camera = self.preview_service.open_camera(effective_runtime_config, profile_name="measurement")
        temp_controller = self._build_temp_controller(runtime_config)
        metric_source = self._build_metric_source(
            runtime_config=effective_runtime_config,
            definition=measurement_plan.metric_definition,
            target_temperature_celsius=target_temperature_celsius,
        )
        coordinator = LiveRunCoordinator(repo=self.repo, artifact_store=self.artifact_store)
        try:
            execution = coordinator.run(
                session_id=record.run_id,
                definition=record.definition,
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
                stop_on_target_reached=runtime_config.live.temp.control.completion_mode != "manual_stop_only",
                stop_requested=active_run.stop_event.is_set,
                wait_for_next_sample=active_run.stop_event.wait,
                status_callback=lambda status_value, payload: self._update_status(
                    active_run,
                    registry,
                    status_value,
                    payload=payload,
                ),
                telemetry_callback=lambda row: self._append_telemetry(active_run, row),
                sample_callback=lambda sync_point, row: self._cache_tracking_frame(record.run_id, sync_point),
            )
        except LiveRunTrackingInvalidated as exc:
            self._store_error(active_run, exc.detail)
            self._update_status(active_run, registry, RunStatus.INVALIDATED, payload={"reason": exc.reason})
            self._update_status(active_run, registry, RunStatus.STOPPING, payload={"reason": exc.reason})
            self._update_status(
                active_run,
                registry,
                RunStatus.ABORTED,
                payload={"reason": exc.reason},
                capture_mode=CaptureMode.POST_RUN_REVIEW,
            )
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
        except LiveRunStopRequested as exc:
            self._store_error(active_run, exc.detail)
            self._update_status(active_run, registry, RunStatus.STOPPING, payload={"reason": exc.reason})
            self._update_status(
                active_run,
                registry,
                RunStatus.ABORTED,
                payload={"reason": exc.reason},
                capture_mode=CaptureMode.POST_RUN_REVIEW,
            )
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
        except Exception as exc:
            self._store_error(active_run, str(exc))
            self._update_status(
                active_run,
                registry,
                RunStatus.FAILED,
                payload={"reason": str(exc)},
                capture_mode=CaptureMode.POST_RUN_REVIEW,
            )
            self._persist_partial_terminal_execution(
                active_run=active_run,
                record=record,
                runtime_config=effective_runtime_config,
                effective_definition=measurement_plan.metric_definition,
                measurement_capture_plan=measurement_capture_plan,
                terminal_state=RunStatus.FAILED,
                terminal_reason="runtime_error",
                terminal_detail=str(exc),
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
            close = getattr(camera, "close", None)
            if callable(close):
                close()

    def _append_telemetry(self, active_run: _ActiveLiveRun, row: dict[str, Any]) -> None:
        with self._state_lock:
            active_run.telemetry.append(dict(row))

    def _cache_tracking_frame(self, run_id: str, sync_point) -> None:
        frame = getattr(sync_point, "frame", None)
        if frame is None:
            return
        self.preview_service.cache_tracking_frame(run_id=run_id, frame=frame)

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


def _runtime_config_with_measurement_profile(
    runtime_config: RuntimeConfig,
    measurement_profile,
) -> RuntimeConfig:
    live_camera = replace(runtime_config.live.camera, measurement=measurement_profile)
    live_config = replace(runtime_config.live, camera=live_camera)
    return replace(runtime_config, live=live_config)


def _now_ms() -> int:
    return int(time.time() * 1000)


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
    }


def _measurement_capture_plan_payload(
    *,
    original_definition: MeasurementDefinition,
    effective_definition: MeasurementDefinition,
    measurement_profile,
) -> dict[str, Any]:
    local_origin_x = original_definition.analysis_roi.x - effective_definition.analysis_roi.x
    local_origin_y = original_definition.analysis_roi.y - effective_definition.analysis_roi.y
    roi = measurement_profile.device_roi
    return {
        "effective_acquisition_roi": {
            "x": int(roi.x),
            "y": int(roi.y),
            "width": int(roi.width),
            "height": int(roi.height),
        },
        "effective_local_origin_in_setup_preview_px": {
            "x": int(local_origin_x),
            "y": int(local_origin_y),
        },
        "setup_to_effective_local_translation_px": {
            "dx": int(effective_definition.analysis_roi.x - original_definition.analysis_roi.x),
            "dy": int(effective_definition.analysis_roi.y - original_definition.analysis_roi.y),
        },
    }
