"""Core data models shared across frozen modules."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from src.core.enums import CaptureMode, ObservationAxis, RunStatus, SessionState


ScalarPointValue = bool | float | int | str
ANALYSIS_ROI_FLOAT_EPSILON = 0.5


@dataclass(slots=True)
class RectRegion:
    """Axis-aligned pixel region."""

    x: int
    y: int
    width: int
    height: int


@dataclass(slots=True)
class MetricBox:
    """Rotated tracking box used to constrain two-point measurement."""

    center_x: int
    center_y: int
    width: int
    height: int
    angle_deg: float = 0.0


@dataclass(slots=True)
class PixelPoint:
    """A single pixel coordinate."""

    x: int
    y: int


@dataclass(slots=True)
class MeasurementDefinition:
    """Operator-confirmed measurement definition for a live run."""

    analysis_roi: RectRegion
    metric_box: MetricBox
    point_a_px: PixelPoint
    point_b_px: PixelPoint
    foreground_polarity: str
    threshold_mode: str
    ignore_internal_texture: bool
    min_target_area_px: int
    sensitivity: float = 50.0
    observation_axis: ObservationAxis = ObservationAxis.LONG_AXIS

    def has_valid_roi(self) -> bool:
        return self.analysis_roi.width > 0 and self.analysis_roi.height > 0

    def has_valid_points(self) -> bool:
        return (
            self.has_valid_roi()
            and _point_in_region(self.analysis_roi, self.point_a_px.x, self.point_a_px.y)
            and _point_in_region(self.analysis_roi, self.point_b_px.x, self.point_b_px.y)
            and (self.point_a_px.x, self.point_a_px.y) != (self.point_b_px.x, self.point_b_px.y)
        )

    def has_valid_window(self) -> bool:
        return (
            self.has_valid_roi()
            and self.metric_box.width > 0
            and self.metric_box.height > 0
            and _metric_box_within_region(self.analysis_roi, self.metric_box)
            and _point_in_region(self.analysis_roi, self.metric_box.center_x, self.metric_box.center_y)
        )

    def is_complete(self) -> bool:
        return (
            self.has_valid_points()
            and self.has_valid_window()
            and self.min_target_area_px > 0
            and 0.0 <= float(self.sensitivity) <= 100.0
            and _point_in_metric_box(self.metric_box, self.point_a_px.x, self.point_a_px.y)
            and _point_in_metric_box(self.metric_box, self.point_b_px.x, self.point_b_px.y)
            and self.observation_axis in {ObservationAxis.LONG_AXIS, ObservationAxis.SHORT_AXIS}
        )


@dataclass(slots=True)
class RunDraftRecord:
    """Mutable live-run draft stored outside replay/session history."""

    run_id: str
    profile: str
    preset: str
    status: RunStatus = RunStatus.CREATED
    capture_mode: CaptureMode = CaptureMode.IDLE
    definition: MeasurementDefinition | None = None
    temperature_settings: TemperatureSettingsBundle | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0


@dataclass(slots=True)
class TemperatureSettingsBundle:
    """Operator-confirmed temperature settings attached to the current live-run draft."""

    target_temperature_celsius: float
    control_mode: str = "manual"
    output_power_percent: float = 100.0
    confirmed_target_temperature_celsius: float | None = None
    confirmed_at_ms: int = 0
    source: str = "unknown"


@dataclass(slots=True)
class RunRateSnapshot:
    """Canonical rate concepts for preview, measurement, and persisted artifacts."""

    camera_resulting_fps: float | None = None
    preview_display_fps: float | None = None
    measurement_sample_hz: float | None = None
    artifact_capture_hz: float | None = None
    dropped_frame_count: int = 0


@dataclass(slots=True)
class MeasurementProfileSnapshot:
    """Camera-side acquisition settings used for measurement-oriented runs."""

    acquisition_roi: RectRegion | None = None
    decimation: int | None = None
    binning: int | None = None
    exposure_us: int | None = None


@dataclass(slots=True)
class FramePacket:
    """A single image frame emitted by the camera layer."""

    timestamp_ms: int
    source: str = "unknown"
    image: Any | None = None
    frame_id: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TempReading:
    """A single temperature sample emitted by the temp layer."""

    timestamp_ms: int
    celsius: float
    source: str = "unknown"


@dataclass(slots=True)
class PlcSnapshot:
    """Point-in-time PLC values."""

    timestamp_ms: int
    values: dict[str, ScalarPointValue] = field(default_factory=dict)
    source: str = "unknown"


@dataclass(slots=True)
class ShapeMetric:
    """Vision output without coupling to workflow or hardware control."""

    timestamp_ms: int
    metric_name: str = "end_displacement"
    metric_raw: float | None = None
    metric_norm: float | None = None
    quality: float = 0.0
    roi: tuple[int, int, int, int] | None = None
    feature_point_px: tuple[int, int] | None = None
    point_a_px: tuple[int, int] | None = None
    point_b_px: tuple[int, int] | None = None
    baseline_px: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SyncPoint:
    """Time-aligned multi-source snapshot."""

    timestamp_ms: int
    frame: FramePacket | None = None
    temp: TempReading | None = None
    plc: PlcSnapshot | None = None
    metric: ShapeMetric | None = None


@dataclass(slots=True)
class CurvePoint:
    """A generic scalar point used by curve buffering code."""

    timestamp_ms: int
    value: float


@dataclass(slots=True)
class SessionRecord:
    """Workflow session state stored independent from UI concerns."""

    session_id: str
    state: SessionState = SessionState.CREATED


def _point_in_region(region: RectRegion, x: int, y: int) -> bool:
    return region.x <= x < (region.x + region.width) and region.y <= y < (region.y + region.height)


def _metric_box_within_region(region: RectRegion, box: MetricBox) -> bool:
    return all(_point_in_region_float(region, x, y) for x, y in _metric_box_corners(box))


def _point_in_metric_box(box: MetricBox, x: int, y: int) -> bool:
    angle_rad = math.radians(box.angle_deg)
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = x - box.center_x
    translated_y = y - box.center_y
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return abs(local_x) <= box.width / 2 and abs(local_y) <= box.height / 2


def _metric_box_corners(box: MetricBox) -> list[tuple[float, float]]:
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


def _point_in_region_float(region: RectRegion, x: float, y: float) -> bool:
    return (
        (region.x - ANALYSIS_ROI_FLOAT_EPSILON) <= x <= (region.x + region.width + ANALYSIS_ROI_FLOAT_EPSILON)
        and (region.y - ANALYSIS_ROI_FLOAT_EPSILON) <= y <= (region.y + region.height + ANALYSIS_ROI_FLOAT_EPSILON)
    )
