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


class SessionHistoryResponse(BaseModel):
    items: list[SessionSummaryResponse]


class ReplayDetailPointResponse(BaseModel):
    timestamp_ms: int
    celsius: float
    metric_raw: float
    metric_norm: float | None
    quality: float


class ReplayKeyFrameResponse(BaseModel):
    label: str
    timestamp_ms: int
    image: list[list[int]]
    feature_point_px: list[int] | None
    metric_raw: float | None


class ReplayDetailResponse(BaseModel):
    session_id: str
    source: str
    af95: float | None
    point_count: int
    points: list[ReplayDetailPointResponse]
    key_frames: list[ReplayKeyFrameResponse]


class ErrorResponse(BaseModel):
    detail: str
