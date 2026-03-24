"""Dependency helpers for the thin web application shell."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, Request

from src.application.container import ApplicationContainer
from src.application.live_preview_service import LivePreviewService, PreviewStateSnapshot
from src.application.live_run_registry import LiveRunDraftRegistry
from src.application.live_run_service import LiveRunService
from src.application.runtime_config import RuntimeConfig
from src.storage.probe_diagnostics import ProbeDiagnosticStore
from src.storage.session_adjustments import SessionAdjustmentStore
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SqliteSessionRepo
from src.workflow.adjustments import AdjustmentService
from src.workflow.session import WorkflowSessionRunner


def get_application_container(request: Request) -> ApplicationContainer:
    container = getattr(request.app.state, "application_container", None)
    if container is None:
        runtime_config = getattr(request.app.state, "runtime_config")
        container = ApplicationContainer(runtime_config)
        request.app.state.application_container = container
    return container


def get_profile_name(request: Request) -> str:
    return str(get_application_container(request).profile_name)


def get_runtime_config(request: Request) -> RuntimeConfig:
    return get_application_container(request).runtime_config


def get_live_run_registry(request: Request) -> LiveRunDraftRegistry:
    registry = getattr(request.app.state, "live_run_registry", None)
    if registry is None:
        registry = get_application_container(request).live_run_registry
        request.app.state.live_run_registry = registry
    return registry


def get_live_preview_service(request: Request) -> LivePreviewService:
    service = getattr(request.app.state, "live_preview_service", None)
    if service is None:
        service = get_application_container(request).live_preview_service
        request.app.state.live_preview_service = service
    return service


def get_live_run_service(request: Request) -> LiveRunService:
    service = getattr(request.app.state, "live_run_service", None)
    if service is None:
        service = get_application_container(request).build_live_run_service(preview_service=get_live_preview_service(request))
        request.app.state.live_run_service = service
    return service


def get_session_repo(request: Request) -> SqliteSessionRepo:
    return get_application_container(request).session_repo


def get_session_artifact_store(request: Request) -> SessionArtifactStore:
    return get_application_container(request).artifact_store


def get_session_adjustment_store(request: Request) -> SessionAdjustmentStore:
    return get_application_container(request).adjustment_store


def get_probe_diagnostic_store(request: Request) -> ProbeDiagnosticStore:
    return get_application_container(request).probe_diagnostic_store


def get_session_runner(
    request: Request,
) -> WorkflowSessionRunner:
    return get_application_container(request).build_session_runner()


def get_adjustment_service(
    request: Request,
) -> AdjustmentService:
    return get_application_container(request).build_adjustment_service()


def get_camera_probe_runner(
    request: Request,
) -> Callable[[RuntimeConfig, dict[str, Any] | None], dict[str, Any]]:
    return get_application_container(request).build_camera_probe_runner()


__all__ = [
    "ApplicationContainer",
    "LivePreviewService",
    "LiveRunDraftRegistry",
    "LiveRunService",
    "PreviewStateSnapshot",
    "get_adjustment_service",
    "get_application_container",
    "get_camera_probe_runner",
    "get_live_preview_service",
    "get_live_run_registry",
    "get_live_run_service",
    "get_profile_name",
    "get_runtime_config",
    "get_session_adjustment_store",
    "get_session_artifact_store",
    "get_session_repo",
    "get_session_runner",
]
