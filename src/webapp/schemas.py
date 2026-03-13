"""Request and response models for the web application layer."""

from pydantic import BaseModel, Field


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


class AdjustmentResultResponse(BaseModel):
    af95: float | None = None
    as_value: float | None = None
    af_value: float | None = None
    af_tan: float | None = None


class AdjustmentDraftRequest(BaseModel):
    overrides: dict[str, float | None]
    reason: str = Field(min_length=1)


class AdjustmentDraftResponse(BaseModel):
    overrides: dict[str, float | None]
    reason: str
    updated_at_ms: int


class AppliedAdjustmentVersionResponse(BaseModel):
    version: int
    result_before: AdjustmentResultResponse
    overrides: dict[str, float | None]
    result_after: AdjustmentResultResponse
    reason: str
    created_at_ms: int


class AdjustmentStateResponse(BaseModel):
    session_id: str
    auto_result: AdjustmentResultResponse
    latest_result: AdjustmentResultResponse
    draft: AdjustmentDraftResponse | None
    applied_versions: list[AppliedAdjustmentVersionResponse]


class PrecheckItemResponse(BaseModel):
    name: str
    status: str
    detail: str


class PrecheckResponse(BaseModel):
    profile: str
    status: str
    items: list[PrecheckItemResponse]


class ErrorResponse(BaseModel):
    detail: str
