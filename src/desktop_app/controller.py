"""Desktop-facing controller built on the shared application layer."""

from __future__ import annotations

from dataclasses import dataclass
import time
from pathlib import Path
from typing import Any

from src.application.container import ApplicationContainer
from src.application.live_preview_service import compute_preview_interval_ms
from src.application.live_preview_service import LivePreviewService, PreviewStateSnapshot
from src.application.live_run_registry import LiveRunDraftRegistry
from src.application.live_run_service import LiveRunService
from src.application.runtime_config import RuntimeConfig, load_runtime_config
from src.core.enums import RunStatus
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion, RunDraftRecord
from src.workflow.precheck import build_system_precheck


@dataclass(slots=True)
class DesktopAppContext:
    profile: str
    runtime_config: RuntimeConfig
    container: ApplicationContainer
    project_root: Path


def build_desktop_app_context(profile: str = "dev_mock") -> DesktopAppContext:
    runtime_config = load_runtime_config(profile)
    return DesktopAppContext(
        profile=runtime_config.profile,
        runtime_config=runtime_config,
        container=ApplicationContainer(runtime_config),
        project_root=Path(__file__).resolve().parents[2],
    )


class DesktopWorkbenchController:
    """Controller used by the desktop shell to drive the existing workflow."""

    def __init__(self, context: DesktopAppContext) -> None:
        self.context = context
        self.registry: LiveRunDraftRegistry = context.container.live_run_registry
        self.preview_service: LivePreviewService = context.container.live_preview_service
        self.live_run_service: LiveRunService = context.container.build_live_run_service(
            preview_service=self.preview_service
        )

    def get_precheck(self) -> dict[str, Any]:
        runtime_config = self.context.runtime_config
        return build_system_precheck(
            profile_name=runtime_config.profile,
            storage=runtime_config.storage,
            replay=runtime_config.replay,
            adapters=runtime_config.adapters,
            camera=runtime_config.camera,
            project_root=self.context.project_root,
        )

    def probe_camera(self, override: dict[str, Any] | None = None) -> dict[str, Any]:
        runner = self.context.container.build_camera_probe_runner()
        return runner(self.context.runtime_config, override)

    def create_run(self, *, preset: str) -> RunDraftRecord:
        return self.registry.create(profile=self.context.profile, preset=preset)

    def get_run(self, run_id: str) -> RunDraftRecord | None:
        return self.registry.get(run_id)

    def save_definition(self, run_id: str, definition: MeasurementDefinition) -> RunDraftRecord:
        return self.registry.save_definition(run_id, definition)

    def fetch_preview_frame(self, run_id: str, *, cached: bool = False) -> FramePacket:
        self._require_run(run_id)
        frame = self.preview_service.fetch_frame(self.context.runtime_config, run_id=run_id, prefer_cached=cached)
        self.registry.mark_preview_frozen(run_id)
        return frame

    def start_preview(self, run_id: str) -> FramePacket:
        self._require_run(run_id)
        _, first_frame = self.preview_service.start_stream(self.context.runtime_config, run_id=run_id)
        self.registry.mark_preview_streaming(run_id)
        return first_frame

    def stop_preview(self, run_id: str) -> PreviewStateSnapshot:
        self._require_run(run_id)
        stopped = self.preview_service.stop_stream(run_id=run_id)
        if stopped and not self.preview_service.wait_for_stream_stop(run_id=run_id, timeout_ms=3_000):
            self.preview_service.force_stop_stream(run_id=run_id)
            self.preview_service.wait_for_stream_stop(run_id=run_id, timeout_ms=250)
        snapshot = self.preview_service.get_preview_state(run_id=run_id)
        if snapshot.frozen_frame_available:
            self.registry.mark_preview_frozen(run_id)
            snapshot = self.preview_service.get_preview_state(run_id=run_id)
        return snapshot

    def get_preview_state(self, run_id: str) -> PreviewStateSnapshot:
        self._require_run(run_id)
        return self.preview_service.get_preview_state(run_id=run_id)

    def get_cached_preview_frame(self, run_id: str) -> FramePacket | None:
        self._require_run(run_id)
        return self.preview_service.get_cached_frame(run_id=run_id)

    def mark_preview_frame_presented(self, run_id: str, frame: FramePacket) -> None:
        self._require_run(run_id)
        self.preview_service.mark_frame_presented(run_id=run_id, frame=frame)

    def start_live_run(self, run_id: str, *, target_temperature_celsius: float) -> object:
        record = self._require_run(run_id)
        return self.live_run_service.start_run(
            record=record,
            runtime_config=self.context.runtime_config,
            target_temperature_celsius=target_temperature_celsius,
            registry=self.registry,
        )

    def request_stop_live_run(self, run_id: str) -> bool:
        self._require_run(run_id)
        return self.live_run_service.request_stop(run_id)

    def get_result(self, run_id: str) -> dict[str, Any] | None:
        self._require_run(run_id)
        return self.context.container.artifact_store.get_result(run_id)

    def get_detail(self, run_id: str) -> dict[str, Any] | None:
        self._require_run(run_id)
        return self.context.container.artifact_store.get_detail(run_id)

    def get_telemetry(self, run_id: str) -> list[dict[str, Any]] | None:
        self._require_run(run_id)
        return self.context.container.artifact_store.get_telemetry(run_id)

    def run_bootstrap_smoke(
        self,
        *,
        preset: str = "balloon",
        target_temperature_celsius: float = 80.0,
        timeout_s: float = 5.0,
    ) -> dict[str, Any]:
        precheck = self.get_precheck()
        run = self.create_run(preset=preset)
        first_frame = self.start_preview(run.run_id)
        stopped_snapshot = self.stop_preview(run.run_id)
        updated = self.save_definition(run.run_id, _desktop_bootstrap_definition())
        self.start_live_run(run.run_id, target_temperature_celsius=target_temperature_celsius)

        deadline = time.time() + timeout_s
        current = updated
        while time.time() < deadline:
            current = self.get_run(run.run_id)
            assert current is not None
            if current.status == RunStatus.COMPLETED:
                break
            time.sleep(0.05)
        else:
            active_snapshot = self.live_run_service.get_snapshot(run.run_id)
            error_detail = ""
            if active_snapshot is not None:
                error_detail = getattr(active_snapshot, "error_detail", "") or ""
            raise RuntimeError(
                f"Desktop bootstrap smoke did not complete within {timeout_s:.1f}s; "
                f"last status={current.status.value}; "
                f"active_error={error_detail or 'none'}"
            )

        result = self.get_result(run.run_id)
        detail = self.get_detail(run.run_id)
        telemetry = self.get_telemetry(run.run_id)
        return {
            "profile": precheck["profile"],
            "run_id": run.run_id,
            "run_status": current.status.value,
            "preview": {
                "first_frame_id": first_frame.frame_id,
                "first_frame_source": first_frame.source,
                "frozen_frame_available": stopped_snapshot.frozen_frame_available,
                "preview_display_fps": stopped_snapshot.preview_display_fps,
            },
            "definition_complete": bool(updated.definition and updated.definition.is_complete()),
            "result_available": result is not None,
            "detail_available": detail is not None,
            "telemetry_points": 0 if telemetry is None else len(telemetry),
        }

    def run_preview_benchmark(
        self,
        *,
        preset: str = "balloon",
        duration_s: float = 1.5,
    ) -> dict[str, Any]:
        if duration_s <= 0:
            raise ValueError("duration_s must be positive")
        run = self.create_run(preset=preset)
        first_frame = self.start_preview(run.run_id)
        presented_frames = 1
        self.mark_preview_frame_presented(run.run_id, first_frame)
        first_presented_frame_id = first_frame.frame_id
        last_presented_frame_id = first_frame.frame_id
        last_seen_frame_id = first_frame.frame_id
        start_monotonic = time.monotonic()
        deadline = start_monotonic + duration_s
        benchmark_interval_s = compute_preview_interval_ms(
            target_fps=self.context.runtime_config.live.run.preview_target_fps,
            fallback_ms=self.context.runtime_config.live.run.preview_poll_ms,
        ) / 1000.0

        while time.monotonic() < deadline:
            snapshot = self.get_preview_state(run.run_id)
            frame = self.get_cached_preview_frame(run.run_id)
            if frame is not None and frame.frame_id is not None and frame.frame_id != last_seen_frame_id:
                self.mark_preview_frame_presented(run.run_id, frame)
                presented_frames += 1
                last_seen_frame_id = frame.frame_id
                last_presented_frame_id = frame.frame_id
            if snapshot.stream_active:
                time.sleep(max(0.005, benchmark_interval_s))
            else:
                break

        snapshot = self.stop_preview(run.run_id)
        elapsed_s = max(0.001, time.monotonic() - start_monotonic)
        measured_presented_fps = presented_frames / elapsed_s
        return {
            "profile": self.context.profile,
            "run_id": run.run_id,
            "duration_s": round(elapsed_s, 3),
            "presented_frames": presented_frames,
            "first_frame_id": first_presented_frame_id,
            "last_frame_id": last_presented_frame_id,
            "measured_presented_fps": round(measured_presented_fps, 3),
            "preview_display_fps": None
            if snapshot.preview_display_fps is None
            else round(snapshot.preview_display_fps, 3),
            "frozen_frame_available": snapshot.frozen_frame_available,
            "target_preview_fps": self.context.runtime_config.live.run.preview_target_fps,
            "preview_poll_ms": self.context.runtime_config.live.run.preview_poll_ms,
        }

    def _require_run(self, run_id: str) -> RunDraftRecord:
        record = self.registry.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")
        return record


def _desktop_bootstrap_definition() -> MeasurementDefinition:
    return MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=96, height=64),
        metric_box=MetricBox(center_x=48, center_y=32, width=80, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=12, y=32),
        point_b_px=PixelPoint(x=83, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )
