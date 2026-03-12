"""Health check routes."""

from fastapi import APIRouter, Depends

from src.webapp.deps import get_profile_name
from src.webapp.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(profile: str = Depends(get_profile_name)) -> HealthResponse:
    return HealthResponse(status="ok", app="YYT1771 Web API", profile=profile)
