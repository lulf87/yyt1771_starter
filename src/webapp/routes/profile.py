"""Profile-related API routes."""

from fastapi import APIRouter, Depends

from src.webapp.config import RuntimeConfig
from src.webapp.deps import get_runtime_config
from src.webapp.schemas import ProfileResponse

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(runtime_config: RuntimeConfig = Depends(get_runtime_config)) -> dict[str, object]:
    return runtime_config.as_public_dict()
