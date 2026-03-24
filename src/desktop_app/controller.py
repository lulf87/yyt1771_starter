"""Desktop-facing controller built on the shared application layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.application.container import ApplicationContainer
from src.application.live_preview_service import LivePreviewService, PreviewStateSnapshot
from src.application.live_run_registry import LiveRunDraftRegistry
from src.application.live_run_service import LiveRunService
from src.application.runtime_config import RuntimeConfig, load_runtime_config
from src.core.models import FramePacket, MeasurementDefinition, RunDraftRecord
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

    def _require_run(self, run_id: str) -> RunDraftRecord:
        record = self.registry.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")
        return record
