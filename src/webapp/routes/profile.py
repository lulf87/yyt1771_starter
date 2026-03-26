"""Profile-related API routes."""

from collections.abc import Callable
from pathlib import Path
import time
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from src.application.container import ApplicationContainer
from src.application.runtime_config import RuntimeConfig
from src.webapp.deps import get_application_container, get_camera_probe_runner, get_runtime_config
from src.webapp.schemas import (
    CameraProbeRequest,
    CameraProbeResponse,
    PrecheckResponse,
    ProfileResponse,
    TempCurrentResponse,
    TempTargetRequest,
    TempTargetResponse,
)
from src.workflow.precheck import build_system_precheck

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(runtime_config: RuntimeConfig = Depends(get_runtime_config)) -> dict[str, object]:
    return runtime_config.as_public_dict()


@router.get("/precheck", response_model=PrecheckResponse)
def get_precheck(runtime_config: RuntimeConfig = Depends(get_runtime_config)) -> dict[str, object]:
    return build_system_precheck(
        profile_name=runtime_config.profile,
        storage=runtime_config.storage,
        replay=runtime_config.replay,
        adapters=runtime_config.adapters,
        camera=runtime_config.camera,
        project_root=Path(__file__).resolve().parents[3],
    )


@router.post("/camera/probe", response_model=CameraProbeResponse)
def post_camera_probe(
    probe_request: CameraProbeRequest | None = Body(default=None),
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    runner: Callable[[RuntimeConfig, dict[str, Any] | None], dict[str, Any]] = Depends(get_camera_probe_runner),
) -> dict[str, Any]:
    override = None if probe_request is None else probe_request.model_dump(exclude_none=True)
    return runner(runtime_config, override)


@router.get("/temp/current", response_model=TempCurrentResponse)
def get_current_temperature(
    container: ApplicationContainer = Depends(get_application_container),
) -> dict[str, object]:
    backend = str(container.runtime_config.live.temp.backend or container.runtime_config.adapters.get("temp", "") or "")
    try:
        reading = container.with_temp_controller(lambda controller: controller.read())
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Current temperature unavailable: {exc}") from exc
    return {
        "backend": backend or "missing",
        "temperature_celsius": float(reading.celsius),
        "timestamp_ms": int(reading.timestamp_ms),
        "source": str(reading.source),
    }


@router.post("/temp/target", response_model=TempTargetResponse)
def post_target_temperature(
    payload: TempTargetRequest,
    container: ApplicationContainer = Depends(get_application_container),
) -> dict[str, object]:
    backend = str(container.runtime_config.live.temp.backend or container.runtime_config.adapters.get("temp", "") or "")
    try:
        result = container.with_temp_controller(
            lambda controller: _write_and_confirm_target_temperature(controller, payload.target_temperature_celsius)
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Target temperature update unavailable: {exc}") from exc
    return {
        "backend": backend or "missing",
        "target_temperature_celsius": float(payload.target_temperature_celsius),
        "confirmed_target_temperature_celsius": float(result["confirmed_target_temperature_celsius"]),
        "timestamp_ms": int(time.time() * 1000),
        "source": str(result["source"]),
    }


def _write_and_confirm_target_temperature(controller: object, target_temperature_celsius: float) -> dict[str, object]:
    controller.set_target_temperature(target_temperature_celsius)
    return {
        "confirmed_target_temperature_celsius": float(controller.read_target_temperature()),
        "source": type(controller).__name__,
    }
