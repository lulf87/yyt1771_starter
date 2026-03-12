"""Request and response models for the web application layer."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    profile: str


class WebAppSettingsResponse(BaseModel):
    host: str
    port: int


class ProfileResponse(BaseModel):
    profile: str
    platform: str
    mode: str
    webapp: WebAppSettingsResponse
    adapters: dict[str, str]


class SessionSummaryResponse(BaseModel):
    session_id: str
    state: str
    point_count: int
    af95: float | None


class ErrorResponse(BaseModel):
    detail: str
