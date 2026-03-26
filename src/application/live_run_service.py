"""Shared live-run orchestration service."""

from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time
from typing import Any

from src.application.device_factory import build_metric_source, build_temp_controller
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

    def _cache_tracking_frame(self, run_id: str, sync_point) -> None:
        frame = getattr(sync_point, "frame", None)
        if frame is None:
            return
        self.preview_service.cache_tracking_frame(run_id=run_id, frame=frame)

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


def _now_ms() -> int:
    return int(time.time() * 1000)
