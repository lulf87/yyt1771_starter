"""Dependency helpers for the web application layer."""

from collections.abc import Callable
import os
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any

from fastapi import Depends, Request

from src.storage.probe_diagnostics import ProbeDiagnosticStore
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.session_adjustments import SessionAdjustmentStore
from src.storage.sqlite_repo import SqliteSessionRepo
from src.webapp.config import RuntimeConfig
from src.workflow.adjustments import AdjustmentService
from src.workflow.camera_probe import run_camera_probe
from src.workflow.session import WorkflowSessionRunner


def get_profile_name(request: Request) -> str:
    return str(request.app.state.profile_name)


def get_runtime_config(request: Request) -> RuntimeConfig:
    return request.app.state.runtime_config


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
