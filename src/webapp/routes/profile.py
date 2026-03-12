"""Profile-related API routes."""

from pathlib import Path

from fastapi import APIRouter, Depends

from src.webapp.config import RuntimeConfig
from src.webapp.deps import get_runtime_config
from src.webapp.schemas import PrecheckResponse, ProfileResponse
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
        project_root=Path(__file__).resolve().parents[3],
    )
