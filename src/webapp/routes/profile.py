"""Profile-related API routes."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends

from src.webapp.config import RuntimeConfig
from src.webapp.deps import get_camera_probe_runner, get_runtime_config
from src.webapp.schemas import CameraProbeRequest, CameraProbeResponse, PrecheckResponse, ProfileResponse
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
