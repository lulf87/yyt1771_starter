"""Request and response models for the web application layer."""

import math
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic import model_validator

ANALYSIS_ROI_FLOAT_EPSILON = 0.5


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


class TempCurrentResponse(BaseModel):
    backend: str
    temperature_celsius: float
    timestamp_ms: int
    source: str


class TempTargetRequest(BaseModel):
    target_temperature_celsius: float = Field(ge=-50, le=50)


class TempTargetResponse(BaseModel):
    backend: str
    target_temperature_celsius: float
    confirmed_target_temperature_celsius: float
    timestamp_ms: int
    source: str


class TemperatureSettingsRequest(BaseModel):
    target_temperature_celsius: float = Field(ge=-50, le=50)
    control_mode: Literal["manual"] = "manual"
    output_power_percent: float = Field(default=100.0, ge=0.0, le=100.0)


class TemperatureSettingsResponse(BaseModel):
    target_temperature_celsius: float
    control_mode: Literal["manual"]
    output_power_percent: float
    confirmed_target_temperature_celsius: float
    confirmed_at_ms: int
    source: str


class SessionSummaryResponse(BaseModel):
    session_id: str
    state: str
    point_count: int
    af95: float | None


class RectRegionRequest(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class RectRegionResponse(RectRegionRequest):
    pass


class MetricBoxRequest(BaseModel):
    center_x: int = Field(ge=0)
    center_y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    angle_deg: float = 0.0


class MetricBoxResponse(MetricBoxRequest):
    pass


class PixelPointRequest(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class PixelPointResponse(PixelPointRequest):
    pass


class MeasurementDefinitionRequest(BaseModel):
    analysis_roi: RectRegionRequest
    metric_box: MetricBoxRequest
    point_a_px: PixelPointRequest
    point_b_px: PixelPointRequest
    observation_axis: Literal["long_axis", "short_axis"]
    foreground_polarity: Literal["dark_on_light", "light_on_dark"]
    threshold_mode: Literal["adaptive", "binary", "otsu"]
    ignore_internal_texture: bool
    min_target_area_px: int = Field(gt=0)
    sensitivity: float = Field(default=50.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_distinct_points(self) -> "MeasurementDefinitionRequest":
        self.analysis_roi = _normalize_region_for_metric_box(self.analysis_roi, self.metric_box)
        if self.point_a_px == self.point_b_px:
            raise ValueError("point_a_px and point_b_px must be distinct")
        if not _metric_box_within_region(self.analysis_roi, self.metric_box):
            raise ValueError("metric_box must stay inside analysis_roi")
        if not _point_in_region(self.analysis_roi, self.metric_box.center_x, self.metric_box.center_y):
            raise ValueError("metric_box center must stay inside analysis_roi")
        if not _point_in_region(self.analysis_roi, self.point_a_px.x, self.point_a_px.y):
            raise ValueError("point_a_px must stay inside analysis_roi")
        if not _point_in_region(self.analysis_roi, self.point_b_px.x, self.point_b_px.y):
            raise ValueError("point_b_px must stay inside analysis_roi")
        if not _point_in_metric_box(self.metric_box, self.point_a_px.x, self.point_a_px.y):
            raise ValueError("point_a_px must stay inside metric_box")
        if not _point_in_metric_box(self.metric_box, self.point_b_px.x, self.point_b_px.y):
            raise ValueError("point_b_px must stay inside metric_box")
        return self


class MeasurementDefinitionResponse(MeasurementDefinitionRequest):
    pass


class AutoDetectDefinitionRequest(BaseModel):
    analysis_roi: RectRegionRequest
    metric_box: MetricBoxRequest | None = None
    foreground_polarity: Literal["dark_on_light", "light_on_dark"]
    threshold_mode: Literal["adaptive", "binary", "otsu"]
    ignore_internal_texture: bool
    min_target_area_px: int = Field(gt=0)
    sensitivity: float = Field(default=50.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_geometry(self) -> "AutoDetectDefinitionRequest":
        if self.metric_box is not None:
            self.analysis_roi = _normalize_region_for_metric_box(self.analysis_roi, self.metric_box)
            if not _metric_box_within_region(self.analysis_roi, self.metric_box):
                raise ValueError("metric_box must stay inside analysis_roi")
            if not _point_in_region(self.analysis_roi, self.metric_box.center_x, self.metric_box.center_y):
                raise ValueError("metric_box center must stay inside analysis_roi")
        return self


class AutoDetectDefinitionResponse(BaseModel):
    point_a_px: PixelPointResponse
    point_b_px: PixelPointResponse
    quality: float
    metric_raw: float | None
    detail: str = ""


class RunCreateRequest(BaseModel):
    profile: str | None = None
    preset: str = Field(default="balloon", min_length=1)


class RunSummaryResponse(BaseModel):
    run_id: str
    status: str
    profile: str
    preset: str


class PreviewStateResponse(BaseModel):
    stream_active: bool
    frozen_frame_available: bool
    last_frame_id: int | None = None


class EditorStateResponse(BaseModel):
    state: Literal["empty", "editing", "locked"]


class RunRatesResponse(BaseModel):
    camera_resulting_fps: float | None = None
    preview_display_fps: float | None = None
    measurement_sample_hz: float | None = None
    artifact_capture_hz: float | None = None
    dropped_frame_count: int = 0


class MeasurementProfileResponse(BaseModel):
    acquisition_roi: RectRegionResponse | None = None
    decimation: int | None = None
    binning: int | None = None
    exposure_us: int | None = None


class RunDetailResponse(RunSummaryResponse):
    definition: MeasurementDefinitionResponse | None = None
    temperature_settings: TemperatureSettingsResponse | None = None
    temperature_settings_confirmed: bool = False
    created_at_ms: int
    updated_at_ms: int
    definition_complete: bool = False
    capture_mode: Literal["idle", "setup_preview", "measurement", "post_run_review"]
    rates: RunRatesResponse
    measurement_profile: MeasurementProfileResponse
    preview: PreviewStateResponse
    editor: EditorStateResponse
    warnings: list[str] = Field(default_factory=list)


class RunStartRequest(BaseModel):
    target_temperature_celsius: float = Field(ge=-50, le=50)


class RunStartResponse(BaseModel):
    run_id: str
    session_id: str
    status: str
    point_count: int | None = None
    af95: float | None = None


class RunTelemetryPointResponse(BaseModel):
    timestamp_ms: int
    temperature_celsius: float
    space1_px: float
    tracking_quality: float
    point_a_px: list[int] | None = None
    point_b_px: list[int] | None = None
    tracking_mode: str | None = None
    tracking_state: str | None = None
    selection_mode: str | None = None
    reason: str | None = None
    observation_selection_mode: str | None = None
    observation_reason: str | None = None
    sample_index: int | None = None
    sample_interval_ms: int | None = None
    frame_id: int | None = None
    frame_timestamp_ms: int | None = None
    temp_timestamp_ms: int | None = None
    metric_timestamp_ms: int | None = None
    camera_resulting_fps: float | None = None
    component_area: int | None = None
    threshold_value: float | None = None
    endpoint_jump_px: float | None = None
    midpoint_drift_px: float | None = None
    span_change_ratio: float | None = None
    consecutive_misses: int | None = None


class RunTelemetryResponse(BaseModel):
    run_id: str
    status: str
    latest: RunTelemetryPointResponse | None = None
    curve: list[RunTelemetryPointResponse]


class RunArtifactRefsResponse(BaseModel):
    definition: str
    definition_original: str | None = None
    definition_effective_local: str | None = None
    measurement_capture_plan: str | None = None
    telemetry: str
    events: str
    detail: str
    result: str
    afas_dataset: str | None = None
    afas_analysis: str | None = None
    afas_plot: str | None = None
    afas_report: str | None = None
    keyframes: list[str] = []


class RunResultResponse(BaseModel):
    session_id: str
    state: str
    analysis_engine: str
    channel_name: str
    result_status: str = "ok"
    result_reason: str | None = None
    result_detail: str = ""
    af95: float | None = None
    as_value: float | None = None
    af_value: float | None = None
    point_count: int
    capture_mode: str = "post_run_review"
    rates: RunRatesResponse = Field(default_factory=RunRatesResponse)
    measurement_profile: MeasurementProfileResponse = Field(default_factory=MeasurementProfileResponse)
    warnings: list[str] = Field(default_factory=list)
    artifacts: RunArtifactRefsResponse


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


class AfasWorkspaceAnalysisRequest(BaseModel):
    channel_name: str | None = None
    group_by_temperature: bool | None = None
    outlier_window: int | None = Field(default=None, ge=3)
    outlier_threshold: float | None = Field(default=None, gt=0)
    outlier_max_iterations: int | None = Field(default=None, ge=1)
    savgol_window_length: int | None = Field(default=None, ge=3)
    savgol_polyorder: int | None = Field(default=None, ge=1)
    low_range_celsius: tuple[float, float] | None = None
    high_range_celsius: tuple[float, float] | None = None
    tangent_offset: int | None = None


class AfasOverviewSeriesResponse(BaseModel):
    temperature_celsius: list[float]
    values: list[float]


class AfasOverviewItemResponse(BaseModel):
    channel_name: str
    point_count: int
    outlier_count: int
    result_status: str
    as_value: float | None = None
    af_tan: float | None = None
    max_slope_temp: float | None = None
    series: AfasOverviewSeriesResponse


class AfasWorkspaceAnalysisResponse(BaseModel):
    session_id: str
    active_channel: str
    available_channels: list[str]
    overview: list[AfasOverviewItemResponse]
    preprocessing: dict[str, Any]
    analysis: dict[str, Any]


class PrecheckItemResponse(BaseModel):
    name: str
    status: str
    detail: str


class PrecheckResponse(BaseModel):
    profile: str
    status: str
    items: list[PrecheckItemResponse]


class CameraProbeIdentityResponse(BaseModel):
    serial_number: str = ""
    ip: str = ""


class CameraProbeRequest(BaseModel):
    probe_mode: str | None = None
    allowed_models: list[str] | None = None
    serial_number: str | None = None
    ip: str | None = None


class CameraProbeDeviceResponse(BaseModel):
    model: str = ""


class CameraProbeFrameResponse(BaseModel):
    width: int
    height: int
    pixel_format: str
    frame_id: int | None = None
    timestamp_ms: int | None = None


class CameraProbeResponse(BaseModel):
    status: str
    backend: str = ""
    transport: str = ""
    sdk: str = ""
    probe_mode: str = ""
    matched_by: str = ""
    identity: CameraProbeIdentityResponse
    device: CameraProbeDeviceResponse
    frame: CameraProbeFrameResponse | None = None
    error_code: str | None = None
    error_stage: str | None = None
    detail: str


class ErrorResponse(BaseModel):
    detail: str


def _point_in_region(region: RectRegionRequest, x: int, y: int) -> bool:
    return region.x <= x < (region.x + region.width) and region.y <= y < (region.y + region.height)


def _metric_box_within_region(region: RectRegionRequest, box: MetricBoxRequest) -> bool:
    return all(_point_in_region_float(region, x, y) for x, y in _metric_box_corners(box))


def _normalize_region_for_metric_box(region: RectRegionRequest, box: MetricBoxRequest) -> RectRegionRequest:
    corners = _metric_box_corners(box)
    box_min_x = math.floor(min(x for x, _ in corners))
    box_min_y = math.floor(min(y for _, y in corners))
    box_max_x = math.ceil(max(x for x, _ in corners))
    box_max_y = math.ceil(max(y for _, y in corners))
    region_min_x = min(region.x, box_min_x)
    region_min_y = min(region.y, box_min_y)
    region_max_x = max(region.x + region.width, box_max_x)
    region_max_y = max(region.y + region.height, box_max_y)
    return RectRegionRequest(
        x=max(0, region_min_x),
        y=max(0, region_min_y),
        width=max(1, region_max_x - region_min_x),
        height=max(1, region_max_y - region_min_y),
    )


def _point_in_metric_box(box: MetricBoxRequest, x: int, y: int) -> bool:
    angle_rad = math.radians(box.angle_deg)
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = x - box.center_x
    translated_y = y - box.center_y
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return abs(local_x) <= box.width / 2 and abs(local_y) <= box.height / 2


def _metric_box_corners(box: MetricBoxRequest) -> list[tuple[float, float]]:
    angle_rad = math.radians(box.angle_deg)
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    half_width = box.width / 2
    half_height = box.height / 2
    corners: list[tuple[float, float]] = []
    for local_x, local_y in (
        (-half_width, -half_height),
        (half_width, -half_height),
        (half_width, half_height),
        (-half_width, half_height),
    ):
        corners.append(
            (
                box.center_x + local_x * cos_theta - local_y * sin_theta,
                box.center_y + local_x * sin_theta + local_y * cos_theta,
            )
        )
    return corners


def _point_in_region_float(region: RectRegionRequest, x: float, y: float) -> bool:
    return (
        (region.x - ANALYSIS_ROI_FLOAT_EPSILON) <= x <= (region.x + region.width + ANALYSIS_ROI_FLOAT_EPSILON)
        and (region.y - ANALYSIS_ROI_FLOAT_EPSILON) <= y <= (region.y + region.height + ANALYSIS_ROI_FLOAT_EPSILON)
    )
