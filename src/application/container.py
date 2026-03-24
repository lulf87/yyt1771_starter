"""Shared application container for web and future desktop shells."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path, PureWindowsPath
from typing import Any

from src.application.live_preview_service import LivePreviewService
from src.application.live_run_registry import LiveRunDraftRegistry
from src.application.live_run_service import LiveRunService
from src.application.runtime_config import RuntimeConfig
from src.storage.probe_diagnostics import ProbeDiagnosticStore
from src.storage.session_adjustments import SessionAdjustmentStore
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SqliteSessionRepo
from src.workflow.adjustments import AdjustmentService
from src.workflow.camera_probe import run_camera_probe
from src.workflow.session import WorkflowSessionRunner


class ApplicationContainer:
    """Own shared runtime configuration, storage adapters, and application services."""

    def __init__(self, runtime_config: RuntimeConfig) -> None:
        self.runtime_config = runtime_config
        self.profile_name = runtime_config.profile
        self.live_run_registry = LiveRunDraftRegistry()
        self.live_preview_service = LivePreviewService()
        self._session_repo: SqliteSessionRepo | None = None
        self._session_repo_key: str | None = None
        self._artifact_store: SessionArtifactStore | None = None
        self._artifact_store_key: str | None = None
        self._adjustment_store: SessionAdjustmentStore | None = None
        self._adjustment_store_key: str | None = None
        self._probe_diagnostic_store: ProbeDiagnosticStore | None = None
        self._probe_diagnostic_store_key: str | None = None

    @property
    def session_repo(self) -> SqliteSessionRepo:
        sqlite_path = self.runtime_config.storage.get("sqlite_path")
        if not sqlite_path:
            raise ValueError("runtime_config.storage.sqlite_path is required")
        cache_key = str(sqlite_path)
        if self._session_repo is None or self._session_repo_key != cache_key:
            self._session_repo = SqliteSessionRepo(sqlite_path)
            self._session_repo_key = cache_key
        return self._session_repo

    @property
    def artifact_store(self) -> SessionArtifactStore:
        artifact_path = self._resolve_artifact_path()
        cache_key = str(artifact_path)
        if self._artifact_store is None or self._artifact_store_key != cache_key:
            self._artifact_store = SessionArtifactStore(artifact_path)
            self._artifact_store_key = cache_key
        return self._artifact_store

    @property
    def adjustment_store(self) -> SessionAdjustmentStore:
        artifact_path = self._resolve_artifact_path()
        cache_key = str(artifact_path)
        if self._adjustment_store is None or self._adjustment_store_key != cache_key:
            self._adjustment_store = SessionAdjustmentStore(artifact_path)
            self._adjustment_store_key = cache_key
        return self._adjustment_store

    @property
    def probe_diagnostic_store(self) -> ProbeDiagnosticStore:
        diagnostic_path = self._resolve_probe_diagnostic_path()
        cache_key = str(diagnostic_path)
        if self._probe_diagnostic_store is None or self._probe_diagnostic_store_key != cache_key:
            self._probe_diagnostic_store = ProbeDiagnosticStore(diagnostic_path)
            self._probe_diagnostic_store_key = cache_key
        return self._probe_diagnostic_store

    def build_live_run_service(self, preview_service: LivePreviewService | None = None) -> LiveRunService:
        return LiveRunService(
            repo=self.session_repo,
            artifact_store=self.artifact_store,
            preview_service=preview_service or self.live_preview_service,
        )

    def build_session_runner(self) -> WorkflowSessionRunner:
        return WorkflowSessionRunner(repo=self.session_repo, artifact_store=self.artifact_store)

    def build_adjustment_service(self) -> AdjustmentService:
        return AdjustmentService(repo=self.session_repo, store=self.adjustment_store)

    def build_camera_probe_runner(self) -> Callable[[RuntimeConfig, dict[str, Any] | None], dict[str, Any]]:
        diagnostics_store = self.probe_diagnostic_store

        def _runner(runtime_config: RuntimeConfig, override: dict[str, Any] | None = None) -> dict[str, Any]:
            return run_camera_probe(runtime_config, override=override, diagnostics_store=diagnostics_store)

        return _runner

    def _resolve_artifact_path(self) -> Path:
        artifact_dir = self.runtime_config.storage.get("artifact_dir", "var/artifacts")
        return self._resolve_runtime_path(artifact_dir)

    def _resolve_probe_diagnostic_path(self) -> Path:
        logging_dir = self.runtime_config.logging.get("dir")
        if logging_dir and not _is_non_native_windows_path(logging_dir):
            return self._resolve_runtime_path(logging_dir)
        artifact_path = self._resolve_artifact_path()
        return artifact_path.parent / "logs"

    def _resolve_runtime_path(self, value: str | Path) -> Path:
        runtime_path = Path(value)
        if not runtime_path.is_absolute():
            runtime_path = Path(__file__).resolve().parents[2] / runtime_path
        return runtime_path


def _is_non_native_windows_path(value: str | Path) -> bool:
    text = str(value)
    return os.name != "nt" and bool(PureWindowsPath(text).drive)
