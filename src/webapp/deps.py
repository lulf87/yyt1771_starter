"""Dependency helpers for the web application layer."""

from dataclasses import dataclass, field, replace
from collections.abc import Callable, Iterator
import os
from pathlib import Path
from pathlib import PureWindowsPath
import threading
import time
from typing import Any
import uuid

from fastapi import Depends, Request

from src.camera import HikGigeMvsCamera, HikRtspCamera, MockCamera, build_hik_rtsp_url
from src.core.config_models import CameraAcquisitionProfileConfig
from src.core.enums import CaptureMode, RunStatus
from src.core.models import FramePacket, MeasurementDefinition, RunDraftRecord
from src.storage.probe_diagnostics import ProbeDiagnosticStore
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.session_adjustments import SessionAdjustmentStore
from src.storage.sqlite_repo import SqliteSessionRepo
from src.temp import LU92XXModbusRtuController, MockTempController
from src.webapp.config import RuntimeConfig
from src.workflow.adjustments import AdjustmentService
from src.workflow.camera_probe import run_camera_probe
from src.workflow.live_run import (
    LiveRunCoordinator,
    LiveRunExecution,
    LiveRunStopRequested,
    LiveRunTrackingInvalidated,
    LockedDefinitionMetricSource,
    MockLiveMetricSource,
)
from src.workflow.session import WorkflowSessionRunner


class LiveRunDraftRegistry:
    """Thin in-memory registry for Phase 1 live-run drafts."""

    def __init__(self) -> None:
        self._records: dict[str, RunDraftRecord] = {}

    def create(self, *, profile: str, preset: str) -> RunDraftRecord:
        now_ms = _now_ms()
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        record = RunDraftRecord(
            run_id=run_id,
            profile=profile,
            preset=preset,
            status=RunStatus.CREATED,
            capture_mode=CaptureMode.IDLE,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        self._records[run_id] = record
        return record

    def get(self, run_id: str) -> RunDraftRecord | None:
        return self._records.get(run_id)

    def save_definition(self, run_id: str, definition: MeasurementDefinition) -> RunDraftRecord:
        record = self.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")

        updated_record = replace(
            record,
            definition=definition,
            status=RunStatus.RUN_READY if definition.is_complete() else RunStatus.DEFINITION_EDITING,
            updated_at_ms=_now_ms(),
        )
        self._records[run_id] = updated_record
        return updated_record

    def mark_preview_streaming(self, run_id: str) -> RunDraftRecord:
        record = self.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")

        next_status = record.status
        if record.status in {RunStatus.CREATED, RunStatus.DEVICE_READY}:
            next_status = RunStatus.PREVIEW_READY
        updated_record = replace(
            record,
            status=next_status,
            capture_mode=CaptureMode.SETUP_PREVIEW,
            updated_at_ms=_now_ms(),
        )
        self._records[run_id] = updated_record
        return updated_record

    def mark_preview_frozen(self, run_id: str) -> RunDraftRecord:
        record = self.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")

        next_status = RunStatus.RUN_READY if record.definition and record.definition.is_complete() else RunStatus.DEFINITION_EDITING
        updated_record = replace(
            record,
            status=next_status,
            capture_mode=CaptureMode.SETUP_PREVIEW,
            updated_at_ms=_now_ms(),
        )
        self._records[run_id] = updated_record
        return updated_record

    def update_status(
        self,
        run_id: str,
        status: RunStatus,
        *,
        capture_mode: CaptureMode | None = None,
    ) -> RunDraftRecord:
        record = self.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")

        updated_record = replace(
            record,
            status=status,
            capture_mode=record.capture_mode if capture_mode is None else capture_mode,
            updated_at_ms=_now_ms(),
        )
        self._records[run_id] = updated_record
        return updated_record


@dataclass(slots=True)
class _ActivePreviewStream:
    run_id: str
    camera: object
    stop_event: threading.Event
    started_at_monotonic: float
    frames_emitted: int = 0
    latest_frame: FramePacket | None = None
    latest_sequence: int = 0
    frame_event: threading.Event = field(default_factory=threading.Event)
    frame_lock: threading.Lock = field(default_factory=threading.Lock)
    reader_thread: threading.Thread | None = None
    reader_error: str = ""


@dataclass(slots=True)
class PreviewStateSnapshot:
    stream_active: bool
    frozen_frame_available: bool
    last_frame_id: int | None = None
    preview_display_fps: float | None = None


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


class LivePreviewService:
    """Preview bridge used by the Phase 2 setup flow."""

    def __init__(self) -> None:
        self._state_lock = threading.Lock()
        self._active_stream: _ActivePreviewStream | None = None
        self._latest_frame: FramePacket | None = None
        self._latest_frame_run_id = ""
        self._last_preview_display_fps: float | None = None
        self._last_preview_display_fps_run_id = ""

    def fetch_frame(
        self,
        runtime_config: RuntimeConfig,
        *,
        run_id: str = "",
        prefer_cached: bool = False,
    ) -> FramePacket:
        cached_frame = self._latest_frame_for_run(run_id) if prefer_cached else None
        if cached_frame is not None:
            return cached_frame
        frame = self._read_with_close(self.open_camera(runtime_config, profile_name="setup_preview"))
        if run_id:
            self._store_latest_frame(run_id, frame)
        return frame

    def start_stream(
        self,
        runtime_config: RuntimeConfig,
        *,
        run_id: str,
    ) -> tuple[_ActivePreviewStream, FramePacket]:
        with self._state_lock:
            if self._active_stream is not None:
                raise RuntimeError(f"Live preview stream is already active for run: {self._active_stream.run_id}")

        camera = self.open_camera(runtime_config, profile_name="setup_preview")
        try:
            first_frame = self._read_from_camera(camera)
        except Exception:
            close = getattr(camera, "close", None)
            if callable(close):
                close()
            raise

        active_stream = _ActivePreviewStream(
            run_id=run_id,
            camera=camera,
            stop_event=threading.Event(),
            started_at_monotonic=time.monotonic(),
            latest_frame=first_frame,
            latest_sequence=1,
        )
        with self._state_lock:
            if self._active_stream is not None:
                close = getattr(camera, "close", None)
                if callable(close):
                    close()
                raise RuntimeError(f"Live preview stream is already active for run: {self._active_stream.run_id}")
            self._active_stream = active_stream
            self._latest_frame = first_frame
            self._latest_frame_run_id = run_id
            self._last_preview_display_fps = None
            self._last_preview_display_fps_run_id = run_id
        active_stream.reader_thread = threading.Thread(
            target=self._preview_reader_worker,
            args=(active_stream,),
            name=f"preview-reader-{run_id}",
            daemon=True,
        )
        active_stream.reader_thread.start()
        return active_stream, first_frame

    def stream_frames(
        self,
        active_stream: _ActivePreviewStream,
        *,
        first_frame: FramePacket,
        frame_interval_ms: int,
    ) -> Iterator[FramePacket]:
        minimum_interval_ms = max(50, int(frame_interval_ms))
        frame_interval_s = minimum_interval_ms / 1000.0
        last_emitted_sequence = 1
        last_emit_monotonic = time.monotonic()
        try:
            frame = first_frame
            while True:
                self._mark_stream_frame(active_stream, frame)
                yield frame
                if active_stream.stop_event.is_set():
                    break
                while True:
                    if active_stream.stop_event.is_set():
                        break
                    remaining_s = max(0.0, frame_interval_s - (time.monotonic() - last_emit_monotonic))
                    if remaining_s > 0 and active_stream.stop_event.wait(remaining_s):
                        break
                    if active_stream.stop_event.is_set():
                        break
                    if active_stream.stop_event.is_set():
                        break
                    with active_stream.frame_lock:
                        latest_sequence = active_stream.latest_sequence
                        latest_frame = active_stream.latest_frame
                        if latest_sequence > last_emitted_sequence:
                            active_stream.frame_event.clear()
                    if latest_frame is None or latest_sequence <= last_emitted_sequence:
                        active_stream.frame_event.wait(0.01)
                        continue
                    frame = latest_frame
                    last_emitted_sequence = latest_sequence
                    last_emit_monotonic = time.monotonic()
                    break
        finally:
            self._close_stream(active_stream)

    def stop_stream(self, *, run_id: str) -> bool:
        with self._state_lock:
            active_stream = self._active_stream
            if active_stream is None or active_stream.run_id != run_id:
                return False
            active_stream.stop_event.set()
            active_stream.frame_event.set()
            return True

    def wait_for_stream_stop(self, *, run_id: str, timeout_ms: int = 1_000) -> bool:
        deadline = time.time() + max(0.05, timeout_ms / 1000)
        while time.time() < deadline:
            with self._state_lock:
                active_stream = self._active_stream
                if active_stream is None or active_stream.run_id != run_id:
                    return True
            time.sleep(0.01)
        return False

    def force_stop_stream(self, *, run_id: str) -> bool:
        with self._state_lock:
            active_stream = self._active_stream
            if active_stream is None or active_stream.run_id != run_id:
                return False
            self._active_stream = None
            self._last_preview_display_fps = _preview_display_fps(active_stream)
            self._last_preview_display_fps_run_id = active_stream.run_id
        active_stream.stop_event.set()
        active_stream.frame_event.set()
        close = getattr(active_stream.camera, "close", None)
        if callable(close):
            close()
        reader_thread = active_stream.reader_thread
        if reader_thread is not None and reader_thread.is_alive():
            reader_thread.join(timeout=0.25)
        return True

    def get_preview_state(self, *, run_id: str) -> PreviewStateSnapshot:
        with self._state_lock:
            active_stream = self._active_stream
            stream_active = bool(
                active_stream is not None
                and active_stream.run_id == run_id
                and not active_stream.stop_event.is_set()
            )
            frame = self._latest_frame if self._latest_frame_run_id == run_id else None
            preview_display_fps = None
            if active_stream is not None and active_stream.run_id == run_id:
                preview_display_fps = _preview_display_fps(active_stream)
            elif self._last_preview_display_fps_run_id == run_id:
                preview_display_fps = self._last_preview_display_fps
            return PreviewStateSnapshot(
                stream_active=stream_active,
                frozen_frame_available=bool(frame is not None and not stream_active),
                last_frame_id=None if frame is None else frame.frame_id,
                preview_display_fps=preview_display_fps,
            )

    def cache_frame(self, *, run_id: str, frame: FramePacket) -> None:
        if not run_id:
            return
        self._store_latest_frame(run_id, frame)

    def close(self) -> None:
        with self._state_lock:
            active_stream = self._active_stream
            self._active_stream = None
            self._latest_frame = None
            self._latest_frame_run_id = ""
            self._last_preview_display_fps = None
            self._last_preview_display_fps_run_id = ""
        if active_stream is None:
            return
        active_stream.stop_event.set()
        active_stream.frame_event.set()
        close = getattr(active_stream.camera, "close", None)
        if callable(close):
            close()
        reader_thread = active_stream.reader_thread
        if reader_thread is not None and reader_thread.is_alive():
            reader_thread.join(timeout=0.25)

    def open_camera(self, runtime_config: RuntimeConfig, *, profile_name: str = "setup_preview") -> object:
        backend = str(runtime_config.adapters.get("camera", "") or "")
        profile = _camera_profile_for_mode(runtime_config.live.camera, profile_name)
        if backend == "mock":
            return MockCamera(
                profile_name=profile_name,
                exposure_us=profile.exposure_us,
                device_roi=profile.device_roi,
                decimation=profile.decimation,
                binning=profile.binning,
            )
        if backend == "hik_gige_mvs":
            return self._build_hik_gige_camera(runtime_config, profile_name=profile_name)
        if backend == "hik_rtsp_opencv":
            return self._build_hik_rtsp_camera(runtime_config)
        raise ValueError(f"Camera backend does not support preview: {backend or 'missing'}")

    def _build_hik_gige_camera(self, runtime_config: RuntimeConfig, *, profile_name: str) -> HikGigeMvsCamera:
        live_camera = runtime_config.live.camera
        legacy_camera = runtime_config.camera
        profile = _camera_profile_for_mode(live_camera, profile_name)
        model = str(legacy_camera.get("model", "") or "").strip()
        if not model and live_camera.allowed_models:
            model = live_camera.allowed_models[0]
        return HikGigeMvsCamera(
            model=model,
            transport=live_camera.transport or str(legacy_camera.get("transport", "") or ""),
            sdk_name=live_camera.sdk or str(legacy_camera.get("sdk", "hik_mvs") or "hik_mvs"),
            serial_number=live_camera.serial_number or str(legacy_camera.get("serial_number", "") or ""),
            ip=live_camera.ip or str(legacy_camera.get("ip", "") or ""),
            trigger_mode=profile.trigger_mode,
            pixel_format=profile.pixel_format,
            exposure_us=profile.exposure_us,
            gain_db=profile.gain_db,
            timeout_ms=profile.timeout_ms,
            device_roi=profile.device_roi,
            decimation=profile.decimation,
            binning=profile.binning,
            target_frame_rate_hz=_camera_target_frame_rate_hz(runtime_config, profile_name=profile_name),
            profile_name=profile_name,
        )

    def _build_hik_rtsp_camera(self, runtime_config: RuntimeConfig) -> HikRtspCamera:
        camera_config = runtime_config.camera
        rtsp_url = str(camera_config.get("rtsp_url", "") or "").strip()
        if not rtsp_url:
            host = str(camera_config.get("host", "") or "").strip()
            username = str(camera_config.get("username", "") or "").strip()
            password = str(camera_config.get("password", "") or "").strip()
            if host and username and password:
                rtsp_url = build_hik_rtsp_url(
                    host=host,
                    username=username,
                    password=password,
                    channel=int(camera_config.get("channel", 1) or 1),
                    stream=int(camera_config.get("stream", 1) or 1),
                    port=int(camera_config.get("port", 554) or 554),
                )
        if not rtsp_url:
            raise ValueError("RTSP preview requires camera.rtsp_url or camera.host/username/password")
        return HikRtspCamera(rtsp_url=rtsp_url)

    def _latest_frame_for_run(self, run_id: str) -> FramePacket | None:
        if not run_id:
            return None
        with self._state_lock:
            if self._latest_frame_run_id != run_id:
                return None
            return self._latest_frame

    def _store_latest_frame(self, run_id: str, frame: FramePacket) -> None:
        with self._state_lock:
            self._latest_frame = frame
            self._latest_frame_run_id = run_id

    def _close_stream(self, active_stream: _ActivePreviewStream) -> None:
        with self._state_lock:
            if self._active_stream is active_stream:
                self._active_stream = None
            self._last_preview_display_fps = _preview_display_fps(active_stream)
            self._last_preview_display_fps_run_id = active_stream.run_id
        active_stream.stop_event.set()
        active_stream.frame_event.set()
        close = getattr(active_stream.camera, "close", None)
        if callable(close):
            close()
        reader_thread = active_stream.reader_thread
        if (
            reader_thread is not None
            and reader_thread.is_alive()
            and reader_thread is not threading.current_thread()
        ):
            reader_thread.join(timeout=0.25)

    def _mark_stream_frame(self, active_stream: _ActivePreviewStream, frame: FramePacket) -> None:
        with self._state_lock:
            if self._active_stream is not active_stream:
                return
            active_stream.frames_emitted += 1
            self._latest_frame = frame
            self._latest_frame_run_id = active_stream.run_id

    def _preview_reader_worker(self, active_stream: _ActivePreviewStream) -> None:
        try:
            while not active_stream.stop_event.is_set():
                frame = self._read_from_camera(active_stream.camera)
                with active_stream.frame_lock:
                    active_stream.latest_frame = frame
                    active_stream.latest_sequence += 1
                    active_stream.frame_event.set()
                self._store_latest_frame(active_stream.run_id, frame)
        except Exception as exc:
            if not active_stream.stop_event.is_set():
                active_stream.reader_error = str(exc)
                active_stream.stop_event.set()
                active_stream.frame_event.set()

    def _read_from_camera(self, camera: object) -> FramePacket:
        read_frame = getattr(camera, "read_frame")
        if not callable(read_frame):
            raise ValueError("Preview camera does not provide read_frame()")
        return read_frame()

    def _read_with_close(self, camera: object) -> FramePacket:
        try:
            return self._read_from_camera(camera)
        finally:
            close = getattr(camera, "close", None)
            if callable(close):
                close()


class LiveRunService:
    """Background live-run orchestration entry point used by `/api/runs/{run_id}/start`."""

    def __init__(
        self,
        *,
        repo: SqliteSessionRepo,
        artifact_store: SessionArtifactStore,
        preview_service: LivePreviewService,
    ) -> None:
        self.repo = repo
        self.artifact_store = artifact_store
        self.preview_service = preview_service
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
    ) -> _ActiveLiveRun:
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

    def get_snapshot(self, run_id: str) -> _ActiveLiveRun | None:
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
        camera = self.preview_service.open_camera(runtime_config, profile_name="measurement")
        temp_controller = self._build_temp_controller(runtime_config)
        metric_source = self._build_metric_source(
            runtime_config=runtime_config,
            definition=record.definition,
            target_temperature_celsius=target_temperature_celsius,
        )
        coordinator = LiveRunCoordinator(repo=self.repo, artifact_store=self.artifact_store)
        try:
            execution = coordinator.run(
                session_id=record.run_id,
                definition=record.definition,
                target_temperature_celsius=target_temperature_celsius,
                run_config=runtime_config.live.run,
                analysis_engine=runtime_config.live.analysis.engine,
                channel_name=runtime_config.live.analysis.channel_name,
                as_fit_point_count=runtime_config.live.analysis.as_fit_point_count,
                af_fit_point_count=runtime_config.live.analysis.af_fit_point_count,
                camera_config=runtime_config.live.camera,
                camera=camera,
                temp_reader=temp_controller,
                temp_controller=temp_controller,
                metric_source=metric_source,
                quality_threshold=runtime_config.live.vision.quality_threshold,
                stop_requested=active_run.stop_event.is_set,
                wait_for_next_sample=active_run.stop_event.wait,
                status_callback=lambda status_value, payload: self._update_status(
                    active_run,
                    registry,
                    status_value,
                    payload=payload,
                ),
                telemetry_callback=lambda row: self._append_telemetry(active_run, row),
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
        except Exception as exc:
            self._store_error(active_run, str(exc))
            self._update_status(
                active_run,
                registry,
                RunStatus.FAILED,
                payload={"reason": str(exc)},
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
            close = getattr(camera, "close", None)
            if callable(close):
                close()

    def _append_telemetry(self, active_run: _ActiveLiveRun, row: dict[str, Any]) -> None:
        with self._state_lock:
            active_run.telemetry.append(dict(row))

    def _store_error(self, active_run: _ActiveLiveRun, detail: str) -> None:
        with self._state_lock:
            active_run.error_detail = detail

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
        backend = str(runtime_config.adapters.get("temp", "") or runtime_config.live.temp.backend or "")
        if backend == "mock":
            return MockTempController()
        if backend == "lu92xx_modbus_rtu":
            return LU92XXModbusRtuController(runtime_config.live.temp)
        raise ValueError(f"Temperature backend does not support Phase 3 live runs yet: {backend or 'missing'}")

    def _build_metric_source(
        self,
        *,
        runtime_config: RuntimeConfig,
        definition: MeasurementDefinition,
        target_temperature_celsius: float,
    ) -> object:
        camera_backend = str(runtime_config.adapters.get("camera", "") or "")
        if camera_backend == "mock":
            return MockLiveMetricSource(
                definition=definition,
                target_temperature_celsius=target_temperature_celsius,
            )
        return LockedDefinitionMetricSource(definition=definition)


def get_profile_name(request: Request) -> str:
    return str(request.app.state.profile_name)


def get_runtime_config(request: Request) -> RuntimeConfig:
    return request.app.state.runtime_config


def get_live_run_registry(request: Request) -> LiveRunDraftRegistry:
    registry = getattr(request.app.state, "live_run_registry", None)
    if registry is None:
        registry = LiveRunDraftRegistry()
        request.app.state.live_run_registry = registry
    return registry


def get_live_preview_service(request: Request) -> LivePreviewService:
    service = getattr(request.app.state, "live_preview_service", None)
    if service is None:
        service = LivePreviewService()
        request.app.state.live_preview_service = service
    return service


def get_live_run_service(request: Request) -> LiveRunService:
    service = getattr(request.app.state, "live_run_service", None)
    if service is None:
        service = LiveRunService(
            repo=get_session_repo(request),
            artifact_store=get_session_artifact_store(request),
            preview_service=get_live_preview_service(request),
        )
        request.app.state.live_run_service = service
    return service


def get_session_repo(request: Request) -> SqliteSessionRepo:
    runtime_config = get_runtime_config(request)
    sqlite_path = runtime_config.storage.get("sqlite_path")
    if not sqlite_path:
        raise ValueError("runtime_config.storage.sqlite_path is required")
    return SqliteSessionRepo(sqlite_path)


def get_session_artifact_store(request: Request) -> SessionArtifactStore:
    artifact_path = _resolve_artifact_path(get_runtime_config(request))
    return SessionArtifactStore(artifact_path)


def get_session_adjustment_store(request: Request) -> SessionAdjustmentStore:
    artifact_path = _resolve_artifact_path(get_runtime_config(request))
    return SessionAdjustmentStore(artifact_path)


def get_probe_diagnostic_store(request: Request) -> ProbeDiagnosticStore:
    diagnostic_path = _resolve_probe_diagnostic_path(get_runtime_config(request))
    return ProbeDiagnosticStore(diagnostic_path)


def _resolve_artifact_path(runtime_config: RuntimeConfig) -> Path:
    artifact_dir = runtime_config.storage.get("artifact_dir", "var/artifacts")
    return _resolve_runtime_path(artifact_dir)


def _resolve_probe_diagnostic_path(runtime_config: RuntimeConfig) -> Path:
    logging_dir = runtime_config.logging.get("dir")
    if logging_dir and not _is_non_native_windows_path(logging_dir):
        return _resolve_runtime_path(logging_dir)
    artifact_path = _resolve_artifact_path(runtime_config)
    return artifact_path.parent / "logs"


def _resolve_runtime_path(value: str | Path) -> Path:
    runtime_path = Path(value)
    if not runtime_path.is_absolute():
        runtime_path = Path(__file__).resolve().parents[2] / runtime_path
    return runtime_path


def _camera_profile_for_mode(camera_config: Any, profile_name: str) -> CameraAcquisitionProfileConfig:
    if profile_name == "measurement":
        return camera_config.measurement
    return camera_config.setup_preview


def _preview_display_fps(active_stream: _ActivePreviewStream) -> float | None:
    if active_stream.frames_emitted < 2:
        return None
    elapsed_s = max(0.0, time.monotonic() - active_stream.started_at_monotonic)
    if elapsed_s <= 0:
        return None
    return active_stream.frames_emitted / elapsed_s


def _camera_target_frame_rate_hz(runtime_config: RuntimeConfig, *, profile_name: str) -> float | None:
    if profile_name == "measurement":
        target_hz = runtime_config.live.run.measurement_target_hz
    elif profile_name == "setup_preview":
        target_hz = runtime_config.live.run.preview_target_fps
    else:
        target_hz = None
    if target_hz is None:
        return None
    resolved = float(target_hz)
    return resolved if resolved > 0 else None


def _is_non_native_windows_path(value: str | Path) -> bool:
    text = str(value)
    return os.name != "nt" and bool(PureWindowsPath(text).drive)


def get_session_runner(
    repo: SqliteSessionRepo = Depends(get_session_repo),
    artifact_store: SessionArtifactStore = Depends(get_session_artifact_store),
) -> WorkflowSessionRunner:
    return WorkflowSessionRunner(repo=repo, artifact_store=artifact_store)


def get_adjustment_service(
    repo: SqliteSessionRepo = Depends(get_session_repo),
    store: SessionAdjustmentStore = Depends(get_session_adjustment_store),
) -> AdjustmentService:
    return AdjustmentService(repo=repo, store=store)


def get_camera_probe_runner(
    diagnostics_store: ProbeDiagnosticStore = Depends(get_probe_diagnostic_store),
) -> Callable[[RuntimeConfig, dict[str, Any] | None], dict[str, Any]]:
    def _runner(runtime_config: RuntimeConfig, override: dict[str, Any] | None = None) -> dict[str, Any]:
        return run_camera_probe(runtime_config, override=override, diagnostics_store=diagnostics_store)

    return _runner


def _now_ms() -> int:
    return int(time.time() * 1000)
