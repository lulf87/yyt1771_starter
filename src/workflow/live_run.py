"""Phase 3 live-run orchestration with a synchronous mock-first coordinator."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any, Callable, Protocol

from src.core.config_models import CameraAcquisitionProfileConfig, CameraRuntimeConfig, RunRuntimeConfig
from src.core.enums import CaptureMode, ObservationAxis, RunStatus
from src.core.contracts import CameraPort, TempControllerPort, TempReader
from src.core.models import (
    FramePacket,
    MeasurementDefinition,
    MeasurementProfileSnapshot,
    PixelPoint,
    RectRegion,
    RunRateSnapshot,
    ShapeMetric,
    SyncPoint,
    TempReading,
)
from src.curve.af95 import normalize_sync_points
from src.curve.afas import AfasAnalysisResult, analyze_afas
from src.curve.mock_afas_curve_playback import MockAfasCurvePlayback
from src.curve.afas_postprocessing_dataset import build_afas_postprocessing_dataset
from src.report.summary import build_live_run_result
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SessionSummary
from src.sync.hub import SyncHub
from src.vision.contour_direction import DirectionalContourConfig, DirectionalContourMetricExtractor
from src.vision.metric_two_point_distance import TwoPointDistanceMetricExtractor


DIRECTIONAL_MAX_FRAME_SPAN_CHANGE_RATIO = 0.08
DIRECTIONAL_DEFAULT_MAX_FRAME_SPAN_JUMP_PX = 6.0
DIRECTIONAL_MIN_FRAME_SPAN_JUMP_PX = 3.0
DIRECTIONAL_MAX_FRAME_SPAN_JUMP_FRACTION = 0.008
DIRECTIONAL_MAX_CHORD_HARD_SPAN_SPIKE_RATIO = 0.12
DIRECTIONAL_MAX_CHORD_RETRY_COMPONENT_BRIDGE_KERNEL = 41
ROI_LOCAL_DEFAULT_MAX_FRAME_SPAN_JUMP_PX = 1.0
ROI_LOCAL_MIN_FRAME_SPAN_JUMP_PX = 1.0
ROI_LOCAL_MAX_FRAME_SPAN_JUMP_FRACTION = 0.001
ROI_LOCAL_WORKING_MAX_WIDTH = 384
ROI_LOCAL_WORKING_MAX_HEIGHT = 240
DIRECTIONAL_WORKING_MAX_WIDTH = 384
DIRECTIONAL_WORKING_MAX_HEIGHT = 384


class SessionSummaryRepo(Protocol):
    def save_summary(self, summary: SessionSummary) -> None:
        """Persist one session summary."""


class LiveMetricSource(Protocol):
    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        """Return one shape metric sample for a live run."""


@dataclass(slots=True)
class LiveRunExecution:
    summary: SessionSummary
    detail: dict[str, Any]
    result: dict[str, Any]
    telemetry: list[dict[str, Any]]
    events: list[dict[str, Any]]
    afas_dataset: dict[str, Any] | None = None


class LiveRunStopRequested(RuntimeError):
    """Raised when the operator stops a live run."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


class LiveRunTrackingInvalidated(LiveRunStopRequested):
    """Raised when tracking quality is no longer acceptable."""


class MockLiveMetricSource:
    """Deterministic metric generator for Phase 3 mock runs."""

    def __init__(self, definition: MeasurementDefinition, target_temperature_celsius: float, start_celsius: float = 25.0) -> None:
        self.definition = definition
        self.target_temperature_celsius = float(target_temperature_celsius)
        self.start_celsius = float(start_celsius)
        self._base_a = definition.point_a_px
        self._base_b = definition.point_b_px
        delta_x = self._base_b.x - self._base_a.x
        delta_y = self._base_b.y - self._base_a.y
        self._baseline_px = math.hypot(delta_x, delta_y)
        if self._baseline_px <= 0:
            raise ValueError("measurement definition points must not overlap")
        self._unit_x = delta_x / self._baseline_px
        self._unit_y = delta_y / self._baseline_px

    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        progress = 1.0
        denominator = self.target_temperature_celsius - self.start_celsius
        if denominator > 0:
            progress = max(0.0, min(1.0, (temp.celsius - self.start_celsius) / denominator))
        curve_progress = progress * progress * (3.0 - 2.0 * progress)
        expansion_px = self._baseline_px * 0.15 * curve_progress
        offset_px = expansion_px / 2.0

        point_a_x = self._base_a.x - self._unit_x * offset_px
        point_a_y = self._base_a.y - self._unit_y * offset_px
        point_b_x = self._base_b.x + self._unit_x * offset_px
        point_b_y = self._base_b.y + self._unit_y * offset_px

        max_x, max_y = _frame_max_xy(
            frame,
            fallback_x=max(self._base_a.x, self._base_b.x),
            fallback_y=max(self._base_a.y, self._base_b.y),
        )

        point_a = (
            int(max(0, min(max_x, round(point_a_x)))),
            int(max(0, min(max_y, round(point_a_y)))),
        )
        point_b = (
            int(max(0, min(max_x, round(point_b_x)))),
            int(max(0, min(max_y, round(point_b_y)))),
        )
        metric_raw = math.hypot(point_b[0] - point_a[0], point_b[1] - point_a[1])
        midpoint = (
            int(round((point_a[0] + point_b[0]) / 2)),
            int(round((point_a[1] + point_b[1]) / 2)),
        )
        return ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=metric_raw,
            quality=max(0.85, 0.98 - progress * 0.03),
            feature_point_px=midpoint,
            point_a_px=point_a,
            point_b_px=point_b,
            baseline_px=self._baseline_px,
            meta={
                "selection_mode": "mock_tracking",
                "progress": progress,
                "curve_progress": curve_progress,
                "sample_index": sample_index,
                "total_samples": total_samples,
            },
        )


class WorkbookPlaybackMetricSource:
    """Metric source that replays AFAS workbook values during mock live runs."""

    def __init__(self, definition: MeasurementDefinition, playback: MockAfasCurvePlayback) -> None:
        self.definition = definition
        self.playback = playback
        self._base_a = definition.point_a_px
        self._base_b = definition.point_b_px
        delta_x = self._base_b.x - self._base_a.x
        delta_y = self._base_b.y - self._base_a.y
        self._baseline_px = math.hypot(delta_x, delta_y)
        if self._baseline_px <= 0:
            raise ValueError("measurement definition points must not overlap")
        self._unit_x = delta_x / self._baseline_px
        self._unit_y = delta_y / self._baseline_px
        self._center_x = (self._base_a.x + self._base_b.x) / 2.0
        self._center_y = (self._base_a.y + self._base_b.y) / 2.0

    def playback_sample_count(self) -> int:
        return int(self.playback.sample_count)

    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        resolved_index = min(max(int(sample_index), 0), self.playback.sample_count - 1)
        metric_raw = float(self.playback.values[resolved_index])
        projected_span_px = max(2.0, abs(metric_raw))
        point_a, point_b = _points_for_projected_span(
            frame=frame,
            center_x=self._center_x,
            center_y=self._center_y,
            unit_x=self._unit_x,
            unit_y=self._unit_y,
            span_px=projected_span_px,
        )
        midpoint = (
            int(round((point_a[0] + point_b[0]) / 2)),
            int(round((point_a[1] + point_b[1]) / 2)),
        )
        return ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=metric_raw,
            quality=0.99,
            feature_point_px=midpoint,
            point_a_px=point_a,
            point_b_px=point_b,
            baseline_px=self._baseline_px,
            meta={
                "selection_mode": "mock_afas_curve_playback",
                "sheet_name": self.playback.sheet_name,
                "channel_name": self.playback.channel_name,
                "sample_index": resolved_index,
                "total_samples": total_samples,
                "playback_sample_count": self.playback.sample_count,
                "playback_workbook_path": self.playback.workbook_path,
            },
        )


class LockedDefinitionMetricSource:
    """Definition-locked extractor used when mock metric generation is unavailable."""

    def __init__(
        self,
        definition: MeasurementDefinition,
        *,
        debug_locked_points: bool = False,
        working_max_width: int | None = None,
        working_max_height: int | None = None,
        max_chord_axis_prior_provider: Callable[[], PixelPoint | None] | None = None,
        max_chord_axis_prior_tolerance_provider: Callable[[], float | None] | None = None,
        max_chord_prior_point_a_provider: Callable[[], PixelPoint | None] | None = None,
        max_chord_prior_point_b_provider: Callable[[], PixelPoint | None] | None = None,
        max_chord_prior_endpoint_tolerance_provider: Callable[[], float | None] | None = None,
    ) -> None:
        self._directional_config: DirectionalContourConfig | None = None
        self._directional_axis_prior_provider = max_chord_axis_prior_provider
        self._directional_axis_prior_tolerance_provider = max_chord_axis_prior_tolerance_provider
        self._directional_prior_point_a_provider = max_chord_prior_point_a_provider
        self._directional_prior_point_b_provider = max_chord_prior_point_b_provider
        self._directional_prior_endpoint_tolerance_provider = max_chord_prior_endpoint_tolerance_provider
        self._extractor = None
        if definition.direction_angle_deg is not None:
            self._directional_config = DirectionalContourConfig(
                analysis_roi=definition.analysis_roi,
                direction_angle_deg=float(definition.direction_angle_deg),
                metric_box=definition.metric_box,
                foreground_polarity=definition.foreground_polarity,
                threshold_mode=definition.threshold_mode,
                ignore_internal_texture=definition.ignore_internal_texture,
                min_target_area_px=definition.min_target_area_px,
                sensitivity=definition.sensitivity,
                component_bridge_kernel=_directional_component_bridge_kernel_for_sensitivity(
                    definition.sensitivity,
                    direction_angle_deg=definition.direction_angle_deg,
                ),
                projection_mode=definition.direction_projection_mode,
                target_geometry_mode=definition.target_geometry_mode,
                side_guard_ratio=definition.side_guard_ratio,
                processing_max_side_px=_directional_processing_max_side_px(
                    working_max_width,
                    working_max_height,
                ),
            )
            return

        measurement_axis_deg = float(definition.metric_box.angle_deg)
        selection_strategy = "roi_local_horizontal_boundary"
        if definition.observation_axis == ObservationAxis.SHORT_AXIS:
            measurement_axis_deg += 90.0
            selection_strategy = "auto_extremes"
        self._extractor = TwoPointDistanceMetricExtractor(
            analysis_roi=definition.analysis_roi,
            metric_box=definition.metric_box,
            measurement_axis_deg=measurement_axis_deg,
            foreground_polarity=definition.foreground_polarity,
            threshold_mode=definition.threshold_mode,
            ignore_internal_texture=definition.ignore_internal_texture,
            min_target_area_px=definition.min_target_area_px,
            sensitivity=definition.sensitivity,
            selection_strategy=selection_strategy,
            locked_points=(definition.point_a_px, definition.point_b_px) if debug_locked_points else None,
            working_max_width=working_max_width,
            working_max_height=working_max_height,
        )

    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
        component_bridge_kernel: int | None = None,
    ) -> ShapeMetric:
        if self._directional_config is not None:
            config = _directional_config_with_axis_prior(
                self._directional_config,
                axis_prior_provider=self._directional_axis_prior_provider,
                axis_prior_tolerance_provider=self._directional_axis_prior_tolerance_provider,
                point_a_prior_provider=self._directional_prior_point_a_provider,
                point_b_prior_provider=self._directional_prior_point_b_provider,
                endpoint_prior_tolerance_provider=self._directional_prior_endpoint_tolerance_provider,
            )
            if component_bridge_kernel is not None:
                config = _directional_config_with_component_bridge_kernel(
                    config,
                    component_bridge_kernel,
                )
            metric = DirectionalContourMetricExtractor(config).extract(frame)
        else:
            assert self._extractor is not None
            metric = self._extractor.extract(frame)
        metric.timestamp_ms = temp.timestamp_ms
        metric.meta["sample_index"] = sample_index
        metric.meta["total_samples"] = total_samples
        return metric


def _directional_processing_max_side_px(
    working_max_width: int | None,
    working_max_height: int | None,
) -> int:
    candidates = [
        int(value)
        for value in (working_max_width, working_max_height)
        if value is not None and int(value) > 0
    ]
    return min(candidates) if candidates else 384


def _directional_odd_kernel(value: float) -> int:
    kernel = max(1, int(round(float(value))))
    if kernel % 2 == 0:
        kernel += 1
    return kernel


def _directional_component_bridge_kernel_for_sensitivity(
    sensitivity: float,
    direction_angle_deg: float | None = None,
) -> int:
    normalized = max(0.0, min(100.0, float(sensitivity))) / 100.0
    angle = None if direction_angle_deg is None else abs(float(direction_angle_deg) % 180.0)
    near_vertical = angle is not None and abs(angle - 90.0) <= 15.0
    if near_vertical:
        if normalized <= 0.5:
            size = 7.0 + (normalized / 0.5) * 34.0
        else:
            size = 41.0 + ((normalized - 0.5) / 0.5) * 22.0
    elif normalized <= 0.5:
        size = 3.0 + (normalized / 0.5) * 8.0
    else:
        size = 11.0 + ((normalized - 0.5) / 0.5) * 28.0
    return _directional_odd_kernel(size)


def _directional_retry_component_bridge_kernel(
    sensitivity: float,
    *,
    base_kernel: int,
) -> int:
    normalized = max(0.0, min(100.0, float(sensitivity))) / 100.0
    retry_kernel = _directional_odd_kernel(11.0 + normalized * 20.0)
    return max(_directional_odd_kernel(float(base_kernel) + 2.0), retry_kernel)


def _tracking_working_size(definition: MeasurementDefinition) -> tuple[int, int]:
    if definition.direction_angle_deg is None and definition.observation_axis == ObservationAxis.LONG_AXIS:
        return ROI_LOCAL_WORKING_MAX_WIDTH, ROI_LOCAL_WORKING_MAX_HEIGHT
    return DIRECTIONAL_WORKING_MAX_WIDTH, DIRECTIONAL_WORKING_MAX_HEIGHT


def _directional_config_with_axis_prior(
    config: DirectionalContourConfig,
    *,
    axis_prior_provider: Callable[[], PixelPoint | None] | None,
    axis_prior_tolerance_provider: Callable[[], float | None] | None,
    point_a_prior_provider: Callable[[], PixelPoint | None] | None = None,
    point_b_prior_provider: Callable[[], PixelPoint | None] | None = None,
    endpoint_prior_tolerance_provider: Callable[[], float | None] | None = None,
) -> DirectionalContourConfig:
    axis_prior_point = axis_prior_provider() if axis_prior_provider is not None else None
    axis_prior_tolerance_px = (
        axis_prior_tolerance_provider()
        if axis_prior_tolerance_provider is not None
        else None
    )
    point_a_prior = point_a_prior_provider() if point_a_prior_provider is not None else None
    point_b_prior = point_b_prior_provider() if point_b_prior_provider is not None else None
    endpoint_prior_tolerance_px = (
        endpoint_prior_tolerance_provider()
        if endpoint_prior_tolerance_provider is not None
        else None
    )
    if (
        axis_prior_point is None
        and axis_prior_tolerance_px is None
        and point_a_prior is None
        and point_b_prior is None
        and endpoint_prior_tolerance_px is None
    ):
        return config
    return DirectionalContourConfig(
        analysis_roi=config.analysis_roi,
        direction_angle_deg=config.direction_angle_deg,
        metric_box=config.metric_box,
        foreground_polarity=config.foreground_polarity,
        threshold_mode=config.threshold_mode,
        threshold_value=config.threshold_value,
        min_target_area_px=config.min_target_area_px,
        sensitivity=config.sensitivity,
        ignore_internal_texture=config.ignore_internal_texture,
        component_bridge_kernel=config.component_bridge_kernel,
        open_kernel=config.open_kernel,
        projection_mode=config.projection_mode,
        target_geometry_mode=config.target_geometry_mode,
        side_guard_ratio=config.side_guard_ratio,
        envelope_min_support_px=config.envelope_min_support_px,
        envelope_quantile=config.envelope_quantile,
        max_chord_axis_prior_point=axis_prior_point,
        max_chord_axis_prior_tolerance_px=axis_prior_tolerance_px,
        max_chord_prior_point_a=point_a_prior,
        max_chord_prior_point_b=point_b_prior,
        max_chord_prior_endpoint_tolerance_px=endpoint_prior_tolerance_px,
        processing_max_side_px=config.processing_max_side_px,
    )


def _directional_config_with_component_bridge_kernel(
    config: DirectionalContourConfig,
    component_bridge_kernel: int,
) -> DirectionalContourConfig:
    return DirectionalContourConfig(
        analysis_roi=config.analysis_roi,
        direction_angle_deg=config.direction_angle_deg,
        metric_box=config.metric_box,
        foreground_polarity=config.foreground_polarity,
        threshold_mode=config.threshold_mode,
        threshold_value=config.threshold_value,
        min_target_area_px=config.min_target_area_px,
        sensitivity=config.sensitivity,
        ignore_internal_texture=config.ignore_internal_texture,
        component_bridge_kernel=_directional_odd_kernel(float(component_bridge_kernel)),
        open_kernel=config.open_kernel,
        projection_mode=config.projection_mode,
        target_geometry_mode=config.target_geometry_mode,
        side_guard_ratio=config.side_guard_ratio,
        envelope_min_support_px=config.envelope_min_support_px,
        envelope_quantile=config.envelope_quantile,
        max_chord_axis_prior_point=config.max_chord_axis_prior_point,
        max_chord_axis_prior_tolerance_px=config.max_chord_axis_prior_tolerance_px,
        max_chord_prior_point_a=config.max_chord_prior_point_a,
        max_chord_prior_point_b=config.max_chord_prior_point_b,
        max_chord_prior_endpoint_tolerance_px=config.max_chord_prior_endpoint_tolerance_px,
        processing_max_side_px=config.processing_max_side_px,
    )


class PriorTrackingMetricSource:
    """Stateful real-camera tracker that gates extractor observations with temporal priors."""

    def __init__(
        self,
        definition: MeasurementDefinition,
        *,
        max_endpoint_jump_px: float | None = None,
        max_midpoint_drift_px: float | None = None,
        max_frame_span_jump_px: float | None = None,
        max_span_change_ratio: float = 0.35,
        max_consecutive_misses: int = 3,
        hold_quality: float = 0.8,
    ) -> None:
        self._tracking_mode = "prior_gated_reacquire"
        self._direction_projection_mode = definition.direction_projection_mode
        self._is_envelope_max_width = definition.direction_projection_mode == "envelope_max_width"
        if self._is_envelope_max_width:
            self._tracking_mode = "global_envelope_reacquire"
        self._is_directional_max_chord = (
            definition.direction_angle_deg is not None
            and definition.direction_projection_mode == "max_chord"
        )
        self._last_good_point_a = definition.point_a_px
        self._last_good_point_b = definition.point_b_px
        self._last_good_span_px = _point_distance(self._last_good_point_a, self._last_good_point_b)
        box_span = max(float(definition.metric_box.width), float(definition.metric_box.height), 1.0)
        endpoint_jump_cap_px = 180.0 if definition.direction_projection_mode == "max_chord" else 72.0
        self._max_endpoint_jump_px = (
            float(max_endpoint_jump_px)
            if max_endpoint_jump_px is not None
            else max(12.0, min(box_span * 0.20, endpoint_jump_cap_px))
        )
        midpoint_drift_cap_px = 180.0 if definition.direction_projection_mode == "max_chord" else 48.0
        self._max_midpoint_drift_px = (
            float(max_midpoint_drift_px)
            if max_midpoint_drift_px is not None
            else max(8.0, min(box_span * 0.20, midpoint_drift_cap_px))
        )
        allows_axis_span_stabilization = (
            definition.direction_angle_deg is None
            and definition.observation_axis == ObservationAxis.LONG_AXIS
        )
        self._max_span_change_ratio = max(0.0, float(max_span_change_ratio))
        if definition.direction_angle_deg is not None or allows_axis_span_stabilization:
            self._max_span_change_ratio = min(
                self._max_span_change_ratio,
                DIRECTIONAL_MAX_FRAME_SPAN_CHANGE_RATIO,
            )
        self._allows_directional_soft_endpoint_stabilization = (
            definition.direction_angle_deg is not None
            and definition.direction_projection_mode in {"mask_projection", "auto"}
        )
        self._max_stabilized_endpoint_jump_px = self._max_endpoint_jump_px
        if self._allows_directional_soft_endpoint_stabilization:
            self._max_stabilized_endpoint_jump_px = min(
                self._max_endpoint_jump_px * 1.15,
                max(
                    self._max_endpoint_jump_px,
                    self._last_good_span_px * self._max_span_change_ratio,
                ),
            )
        self._max_frame_span_jump_px = (
            max(0.0, float(max_frame_span_jump_px))
            if max_frame_span_jump_px is not None
            else None
        )
        if definition.direction_angle_deg is not None and self._max_frame_span_jump_px is None:
            self._max_frame_span_jump_px = max(
                DIRECTIONAL_MIN_FRAME_SPAN_JUMP_PX,
                min(
                    self._last_good_span_px * DIRECTIONAL_MAX_FRAME_SPAN_JUMP_FRACTION,
                    DIRECTIONAL_DEFAULT_MAX_FRAME_SPAN_JUMP_PX,
                ),
            )
        if allows_axis_span_stabilization and self._max_frame_span_jump_px is None:
            self._max_frame_span_jump_px = max(
                ROI_LOCAL_MIN_FRAME_SPAN_JUMP_PX,
                min(
                    self._last_good_span_px * ROI_LOCAL_MAX_FRAME_SPAN_JUMP_FRACTION,
                    ROI_LOCAL_DEFAULT_MAX_FRAME_SPAN_JUMP_PX,
                ),
            )
        self._max_soft_frame_span_jump_px: float | None = None
        if (definition.direction_angle_deg is not None or allows_axis_span_stabilization) and self._max_frame_span_jump_px is not None:
            max_stabilized_span_jump_px = self._last_good_span_px * self._max_span_change_ratio
            self._max_soft_frame_span_jump_px = max(
                float(self._max_frame_span_jump_px),
                min(
                    max_stabilized_span_jump_px,
                    self._max_stabilized_endpoint_jump_px,
                ),
            )
        self._max_consecutive_misses = max(1, int(max_consecutive_misses))
        self._hold_quality = max(float(hold_quality), 0.0)
        self._consecutive_misses = 0
        self._pending_reacquire_point_a: PixelPoint | None = None
        self._pending_reacquire_point_b: PixelPoint | None = None
        self._pending_reacquire_span_px: float | None = None
        self._pending_reacquire_count = 0
        self._has_runtime_lock = False
        self._analysis_roi = definition.analysis_roi
        self._direction_unit: tuple[float, float] | None = None
        self._normal_unit: tuple[float, float] | None = None
        self._allows_axis_lateral_stabilization = (
            definition.direction_angle_deg is None
            and definition.observation_axis == ObservationAxis.LONG_AXIS
        )
        self._allows_axis_span_stabilization = allows_axis_span_stabilization
        self._axis_lateral_stabilization_trigger_px = min(
            self._max_midpoint_drift_px,
            max(4.0, float(definition.metric_box.height) * 0.02),
        )
        if definition.direction_angle_deg is not None or self._allows_axis_lateral_stabilization:
            axis_angle_deg = (
                float(definition.direction_angle_deg)
                if definition.direction_angle_deg is not None
                else float(definition.metric_box.angle_deg)
            )
            angle_rad = math.radians(axis_angle_deg)
            direction_x = math.cos(angle_rad)
            direction_y = math.sin(angle_rad)
            self._direction_unit = (direction_x, direction_y)
            self._normal_unit = (-direction_y, direction_x)
        self._allows_directional_relocation = (
            definition.direction_angle_deg is not None
            and definition.direction_projection_mode in {"max_chord", "mask_projection", "auto"}
        )
        self._allows_directional_component_bridge_retry = (
            definition.direction_angle_deg is not None
            and definition.direction_projection_mode in {"max_chord", "mask_projection", "auto"}
        )
        self._directional_base_component_bridge_kernel: int | None = None
        self._directional_retry_component_bridge_kernel: int | None = None
        if definition.direction_angle_deg is not None:
            self._directional_base_component_bridge_kernel = (
                _directional_component_bridge_kernel_for_sensitivity(
                    definition.sensitivity,
                    direction_angle_deg=definition.direction_angle_deg,
                )
            )
            self._directional_retry_component_bridge_kernel = (
                _directional_retry_component_bridge_kernel(
                    definition.sensitivity,
                    base_kernel=self._directional_base_component_bridge_kernel,
                )
            )
            if definition.direction_projection_mode == "max_chord":
                self._directional_retry_component_bridge_kernel = max(
                    self._directional_retry_component_bridge_kernel,
                    DIRECTIONAL_MAX_CHORD_RETRY_COMPONENT_BRIDGE_KERNEL,
                )
        use_axis_prior = (
            definition.direction_angle_deg is not None
            and definition.direction_projection_mode in {"max_chord", "mask_projection", "auto"}
        )
        working_max_width, working_max_height = _tracking_working_size(definition)
        self._observation_source = LockedDefinitionMetricSource(
            definition=definition,
            working_max_width=working_max_width,
            working_max_height=working_max_height,
            max_chord_axis_prior_provider=self._current_axis_prior_point if use_axis_prior else None,
            max_chord_axis_prior_tolerance_provider=self._current_axis_prior_tolerance_px if use_axis_prior else None,
            max_chord_prior_point_a_provider=self._current_prior_point_a if use_axis_prior else None,
            max_chord_prior_point_b_provider=self._current_prior_point_b if use_axis_prior else None,
            max_chord_prior_endpoint_tolerance_provider=self._current_endpoint_prior_tolerance_px if use_axis_prior else None,
        )

    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        observation = self._observation_source.extract(
            frame,
            temp,
            sample_index=sample_index,
            total_samples=total_samples,
        )
        diagnostics = self._tracking_diagnostics(observation)
        if self._is_envelope_max_width and observation.metric_raw is not None:
            if not self._envelope_candidate_is_gross_outlier(observation, diagnostics):
                return self._accept_envelope_metric(
                    observation,
                    diagnostics,
                    sample_index=sample_index,
                    total_samples=total_samples,
                )
        if observation.metric_raw is not None and observation.point_a_px is not None and observation.point_b_px is not None and not self._has_runtime_lock:
            if self._should_attempt_bootstrap_max_chord_component_bridge_retry(observation, diagnostics):
                retry_metric = self._directional_component_bridge_retry(
                    frame,
                    temp,
                    sample_index=sample_index,
                    total_samples=total_samples,
                    observation=observation,
                    diagnostics=diagnostics,
                    bootstrap=True,
                )
                if retry_metric is not None:
                    return retry_metric
            if not self._bootstrap_candidate_within_prior(diagnostics) and not self._directional_candidate_is_plausible_relocation(
                observation,
                diagnostics,
            ):
                retry_metric = self._directional_component_bridge_retry(
                    frame,
                    temp,
                    sample_index=sample_index,
                    total_samples=total_samples,
                    observation=observation,
                    diagnostics=diagnostics,
                    bootstrap=True,
                )
                if retry_metric is not None:
                    return retry_metric
                rejection_reason = self._rejection_reason(observation, diagnostics)
                return self._hold_last_good_metric(
                    frame,
                    temp,
                    sample_index=sample_index,
                    total_samples=total_samples,
                    observation=observation,
                    diagnostics=diagnostics,
                    rejection_reason=rejection_reason,
                )
            self._remember(observation)
            self._consecutive_misses = 0
            self._clear_pending_reacquire()
            self._has_runtime_lock = True
            observation.meta["tracking_mode"] = self._tracking_mode
            observation.meta["tracking_state"] = (
                "bootstrapped"
                if self._bootstrap_candidate_within_prior(diagnostics)
                else "bootstrapped_relocated"
            )
            observation.meta.update(diagnostics)
            return observation
        if self._axis_candidate_is_stabilizable_lateral_jitter(observation, diagnostics):
            tracking_state = "reacquired_stabilized" if self._consecutive_misses > 0 else "accepted_stabilized"
            stabilized = self._stabilized_lateral_metric(
                frame,
                temp,
                sample_index=sample_index,
                total_samples=total_samples,
                observation=observation,
                diagnostics=diagnostics,
                tracking_state=tracking_state,
            )
            self._remember(stabilized)
            self._consecutive_misses = 0
            self._clear_pending_reacquire()
            return stabilized
        if self._axis_candidate_is_stabilizable_span_jitter(observation, diagnostics):
            tracking_state = "reacquired_stabilized" if self._consecutive_misses > 0 else "accepted_stabilized"
            stabilized = self._stabilized_axis_span_metric(
                frame,
                temp,
                sample_index=sample_index,
                total_samples=total_samples,
                observation=observation,
                diagnostics=diagnostics,
                tracking_state=tracking_state,
            )
            self._remember(stabilized)
            self._consecutive_misses = 0
            self._clear_pending_reacquire()
            return stabilized
        if self._axis_candidate_is_stabilizable_same_axis_step_jitter(observation, diagnostics):
            tracking_state = "reacquired_stabilized" if self._consecutive_misses > 0 else "accepted_stabilized"
            stabilized = self._stabilized_axis_span_metric(
                frame,
                temp,
                sample_index=sample_index,
                total_samples=total_samples,
                observation=observation,
                diagnostics=diagnostics,
                tracking_state=tracking_state,
                reason="same_axis_step_stabilized",
            )
            self._remember(stabilized)
            self._consecutive_misses = 0
            self._clear_pending_reacquire()
            return stabilized
        if observation.metric_raw is not None and self._candidate_within_prior(diagnostics):
            tracking_state = "reacquired" if self._consecutive_misses > 0 else "accepted"
            self._remember(observation)
            self._consecutive_misses = 0
            self._clear_pending_reacquire()
            observation.meta["tracking_mode"] = self._tracking_mode
            observation.meta["tracking_state"] = tracking_state
            observation.meta.update(diagnostics)
            return observation
        if self._directional_candidate_is_stabilizable_span_jitter(observation, diagnostics):
            tracking_state = "reacquired_stabilized" if self._consecutive_misses > 0 else "accepted_stabilized"
            stabilized = self._stabilized_directional_metric(
                frame,
                temp,
                sample_index=sample_index,
                total_samples=total_samples,
                observation=observation,
                diagnostics=diagnostics,
                tracking_state=tracking_state,
                use_last_good_midpoint=True,
            )
            self._remember(stabilized)
            self._consecutive_misses = 0
            self._clear_pending_reacquire()
            return stabilized
        if observation.metric_raw is not None and self._directional_candidate_is_plausible_relocation(
            observation,
            diagnostics,
        ):
            tracking_state = "relocated" if self._consecutive_misses > 0 else "accepted_relocated"
            self._remember(observation)
            self._consecutive_misses = 0
            self._clear_pending_reacquire()
            observation.meta["tracking_mode"] = self._tracking_mode
            observation.meta["tracking_state"] = tracking_state
            observation.meta.update(diagnostics)
            return observation
        retry_metric = self._directional_component_bridge_retry(
            frame,
            temp,
            sample_index=sample_index,
            total_samples=total_samples,
            observation=observation,
            diagnostics=diagnostics,
        )
        if retry_metric is not None:
            return retry_metric
        persistent_reacquire = self._persistent_reacquire_metric(
            frame,
            temp,
            sample_index=sample_index,
            total_samples=total_samples,
            observation=observation,
            diagnostics=diagnostics,
        )
        if persistent_reacquire is not None:
            self._remember(persistent_reacquire)
            self._consecutive_misses = 0
            self._clear_pending_reacquire()
            return persistent_reacquire
        if self._directional_candidate_is_stabilizable_hard_span_spike(observation, diagnostics):
            tracking_state = "reacquired_stabilized" if self._consecutive_misses > 0 else "accepted_stabilized"
            if self._is_directional_max_chord:
                stabilized = self._stabilized_directional_metric(
                    frame,
                    temp,
                    sample_index=sample_index,
                    total_samples=total_samples,
                    observation=observation,
                    diagnostics=diagnostics,
                    tracking_state=tracking_state,
                    reason="hard_span_spike_stabilized",
                    use_last_good_midpoint=True,
                )
                self._remember(stabilized)
            else:
                stabilized = self._stabilized_last_good_metric(
                    frame,
                    temp,
                    sample_index=sample_index,
                    total_samples=total_samples,
                    observation=observation,
                    diagnostics=diagnostics,
                    tracking_state=tracking_state,
                    reason="hard_span_spike_stabilized",
                )
            self._consecutive_misses = 0
            self._clear_pending_reacquire()
            return stabilized
        self._record_pending_reacquire(observation, diagnostics)
        rejection_reason = self._rejection_reason(observation, diagnostics)
        return self._hold_last_good_metric(
            frame,
            temp,
            sample_index=sample_index,
            total_samples=total_samples,
            observation=observation,
            diagnostics=diagnostics,
            rejection_reason=rejection_reason,
        )

    def _tracking_diagnostics(self, observation: ShapeMetric) -> dict[str, Any]:
        point_a = _shape_metric_point(observation.point_a_px)
        point_b = _shape_metric_point(observation.point_b_px)
        if point_a is None or point_b is None or observation.metric_raw is None:
            return {
                "endpoint_jump_px": None,
                "midpoint_drift_px": None,
                "midpoint_along_shift_px": None,
                "midpoint_lateral_drift_px": None,
                "span_change_px": None,
                "span_change_ratio": None,
                "max_frame_span_jump_px": self._max_frame_span_jump_px,
                "max_soft_frame_span_jump_px": self._max_soft_frame_span_jump_px,
                "consecutive_misses": self._consecutive_misses,
            }
        previous_midpoint = _midpoint(self._last_good_point_a, self._last_good_point_b)
        current_midpoint = _midpoint(point_a, point_b)
        directional_shift = self._directional_midpoint_shift(previous_midpoint, current_midpoint)
        return {
            "endpoint_jump_px": max(
                _point_distance(self._last_good_point_a, point_a),
                _point_distance(self._last_good_point_b, point_b),
            ),
            "midpoint_drift_px": _point_distance(previous_midpoint, current_midpoint),
            **directional_shift,
            "span_change_px": abs(float(observation.metric_raw) - self._last_good_span_px),
            "span_change_ratio": abs(float(observation.metric_raw) - self._last_good_span_px) / max(self._last_good_span_px, 1.0),
            "max_frame_span_jump_px": self._max_frame_span_jump_px,
            "max_soft_frame_span_jump_px": self._max_soft_frame_span_jump_px,
            "consecutive_misses": self._consecutive_misses,
        }

    def _envelope_candidate_is_gross_outlier(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> bool:
        if observation.metric_raw is None or observation.point_a_px is None or observation.point_b_px is None:
            return True
        if float(observation.quality or 0.0) <= 0.0:
            return True
        if _metric_endpoint_border_touch_count(observation, self._analysis_roi) >= 2:
            return True
        box_span = max(float(self._analysis_roi.width), float(self._analysis_roi.height), 1.0)
        if observation.roi is not None:
            box_span = max(float(observation.roi[2]), float(observation.roi[3]), box_span)
        if float(observation.metric_raw) > box_span * 1.10:
            return True
        if float(observation.metric_raw) < max(2.0, box_span * 0.01):
            return True
        if not self._has_runtime_lock:
            return False
        span_change_ratio = diagnostics.get("span_change_ratio")
        midpoint_drift_px = diagnostics.get("midpoint_drift_px")
        if span_change_ratio is None or midpoint_drift_px is None:
            return False
        return (
            float(span_change_ratio) > max(0.50, self._max_span_change_ratio * 4.0)
            and float(midpoint_drift_px) > max(self._max_midpoint_drift_px * 4.0, 48.0)
        )

    def _accept_envelope_metric(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        relocated = self._has_runtime_lock and not self._candidate_within_prior(diagnostics)
        self._remember(observation)
        self._consecutive_misses = 0
        self._clear_pending_reacquire()
        observation.meta["tracking_mode"] = self._tracking_mode
        observation.meta["tracking_state"] = "envelope_relocated" if relocated else "accepted_global_envelope"
        observation.meta["sample_index"] = sample_index
        observation.meta["total_samples"] = total_samples
        observation.meta.update(diagnostics)
        return observation

    def _directional_midpoint_shift(
        self,
        previous_midpoint: PixelPoint,
        current_midpoint: PixelPoint,
    ) -> dict[str, float | None]:
        if self._direction_unit is None or self._normal_unit is None:
            return {
                "midpoint_along_shift_px": None,
                "midpoint_lateral_drift_px": None,
            }
        delta_x = float(current_midpoint.x - previous_midpoint.x)
        delta_y = float(current_midpoint.y - previous_midpoint.y)
        direction_x, direction_y = self._direction_unit
        normal_x, normal_y = self._normal_unit
        return {
            "midpoint_along_shift_px": abs(delta_x * direction_x + delta_y * direction_y),
            "midpoint_lateral_drift_px": abs(delta_x * normal_x + delta_y * normal_y),
        }

    def _candidate_within_prior(self, diagnostics: dict[str, Any]) -> bool:
        endpoint_jump_px = diagnostics.get("endpoint_jump_px")
        midpoint_drift_px = diagnostics.get("midpoint_drift_px")
        span_change_ratio = diagnostics.get("span_change_ratio")
        if endpoint_jump_px is None or midpoint_drift_px is None or span_change_ratio is None:
            return False
        return (
            float(endpoint_jump_px) <= self._max_endpoint_jump_px
            and float(midpoint_drift_px) <= self._max_midpoint_drift_px
            and self._span_change_within_limits(diagnostics)
        )

    def _bootstrap_candidate_within_prior(self, diagnostics: dict[str, Any]) -> bool:
        endpoint_jump_px = diagnostics.get("endpoint_jump_px")
        midpoint_drift_px = diagnostics.get("midpoint_drift_px")
        if endpoint_jump_px is None or midpoint_drift_px is None:
            return False
        within_position_prior = (
            float(endpoint_jump_px) <= self._max_endpoint_jump_px
            and float(midpoint_drift_px) <= self._max_midpoint_drift_px
        )
        return within_position_prior

    def _directional_candidate_is_plausible_relocation(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not self._allows_directional_relocation:
            return False
        if observation.metric_raw is None or observation.point_a_px is None or observation.point_b_px is None:
            return False
        span_change_ratio = diagnostics.get("span_change_ratio")
        if span_change_ratio is None or not self._span_change_within_limits(diagnostics):
            return False
        lateral_drift_px = diagnostics.get("midpoint_lateral_drift_px")
        if lateral_drift_px is None or float(lateral_drift_px) > self._max_midpoint_drift_px:
            return False
        if float(observation.quality or 0.0) <= 0.0:
            return False
        return True

    def _directional_candidate_is_stabilizable_span_jitter(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not self._allows_directional_relocation:
            return False
        if observation.metric_raw is None or observation.point_a_px is None or observation.point_b_px is None:
            return False
        if float(observation.quality or 0.0) <= 0.0:
            return False
        endpoint_jump_px = diagnostics.get("endpoint_jump_px")
        midpoint_drift_px = diagnostics.get("midpoint_drift_px")
        span_change_ratio = diagnostics.get("span_change_ratio")
        span_change_px = diagnostics.get("span_change_px")
        if (
            endpoint_jump_px is None
            or midpoint_drift_px is None
            or span_change_ratio is None
            or span_change_px is None
            or self._max_frame_span_jump_px is None
            or self._max_soft_frame_span_jump_px is None
        ):
            return False
        if float(endpoint_jump_px) > self._max_endpoint_jump_px:
            if (
                not self._allows_directional_soft_endpoint_stabilization
                or float(endpoint_jump_px) > self._max_stabilized_endpoint_jump_px
            ):
                return False
        if float(midpoint_drift_px) > self._max_midpoint_drift_px:
            return False
        lateral_drift_px = diagnostics.get("midpoint_lateral_drift_px")
        if lateral_drift_px is not None and float(lateral_drift_px) > self._max_midpoint_drift_px:
            return False
        return (
            float(span_change_ratio) <= self._max_span_change_ratio
            and float(span_change_px) > self._max_frame_span_jump_px
            and float(span_change_px) <= self._max_soft_frame_span_jump_px
        )

    def _directional_candidate_is_stabilizable_hard_span_spike(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not self._has_runtime_lock:
            return False
        if not self._allows_directional_soft_endpoint_stabilization and not self._is_directional_max_chord:
            return False
        if observation.metric_raw is None or observation.point_a_px is None or observation.point_b_px is None:
            return False
        if float(observation.quality or 0.0) <= 0.0:
            return False
        span_change_ratio = diagnostics.get("span_change_ratio")
        span_change_px = diagnostics.get("span_change_px")
        lateral_drift_px = diagnostics.get("midpoint_lateral_drift_px")
        endpoint_jump_px = diagnostics.get("endpoint_jump_px")
        midpoint_drift_px = diagnostics.get("midpoint_drift_px")
        if span_change_ratio is None or span_change_px is None or lateral_drift_px is None:
            return False
        if endpoint_jump_px is None or midpoint_drift_px is None:
            return False
        if float(endpoint_jump_px) > self._max_endpoint_jump_px:
            return False
        if float(midpoint_drift_px) > self._max_midpoint_drift_px:
            return False
        if float(lateral_drift_px) > self._max_midpoint_drift_px:
            return False
        if self._max_frame_span_jump_px is not None and float(span_change_px) <= self._max_frame_span_jump_px:
            return False
        if self._is_directional_max_chord:
            if float(observation.metric_raw) <= self._last_good_span_px:
                return False
            return float(span_change_ratio) <= DIRECTIONAL_MAX_CHORD_HARD_SPAN_SPIKE_RATIO
        return float(span_change_ratio) <= 1.50

    def _axis_candidate_is_stabilizable_lateral_jitter(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not self._allows_axis_lateral_stabilization or not self._has_runtime_lock:
            return False
        if observation.metric_raw is None or observation.point_a_px is None or observation.point_b_px is None:
            return False
        if observation.meta.get("selection_mode") != "roi_local_horizontal_boundary":
            return False
        if float(observation.quality or 0.0) <= 0.0:
            return False
        if not self._span_change_within_limits(diagnostics):
            return False
        lateral_drift_px = diagnostics.get("midpoint_lateral_drift_px")
        along_shift_px = diagnostics.get("midpoint_along_shift_px")
        if lateral_drift_px is None or along_shift_px is None:
            return False
        if float(lateral_drift_px) <= self._axis_lateral_stabilization_trigger_px:
            return False
        if float(along_shift_px) > self._max_endpoint_jump_px:
            return False
        if _metric_endpoint_border_touch_count(observation, self._analysis_roi) >= 2:
            return False
        return True

    def _axis_candidate_is_stabilizable_span_jitter(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not self._allows_axis_span_stabilization or not self._has_runtime_lock:
            return False
        if observation.metric_raw is None or observation.point_a_px is None or observation.point_b_px is None:
            return False
        if observation.meta.get("selection_mode") != "roi_local_horizontal_boundary":
            return False
        if float(observation.quality or 0.0) <= 0.0:
            return False
        endpoint_jump_px = diagnostics.get("endpoint_jump_px")
        midpoint_drift_px = diagnostics.get("midpoint_drift_px")
        span_change_ratio = diagnostics.get("span_change_ratio")
        span_change_px = diagnostics.get("span_change_px")
        if (
            endpoint_jump_px is None
            or midpoint_drift_px is None
            or span_change_ratio is None
            or span_change_px is None
            or self._max_frame_span_jump_px is None
            or self._max_soft_frame_span_jump_px is None
        ):
            return False
        if float(endpoint_jump_px) > self._max_endpoint_jump_px:
            return False
        if float(midpoint_drift_px) > self._max_midpoint_drift_px:
            return False
        if _metric_endpoint_border_touch_count(observation, self._analysis_roi) >= 2:
            return False
        return (
            float(span_change_ratio) <= self._max_span_change_ratio
            and float(span_change_px) > self._max_frame_span_jump_px
            and float(span_change_px) <= self._max_soft_frame_span_jump_px
        )

    def _axis_candidate_is_stabilizable_same_axis_step_jitter(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not self._allows_axis_span_stabilization or not self._has_runtime_lock:
            return False
        if observation.metric_raw is None or observation.point_a_px is None or observation.point_b_px is None:
            return False
        if observation.meta.get("selection_mode") != "roi_local_horizontal_boundary":
            return False
        if float(observation.quality or 0.0) <= 0.0:
            return False
        endpoint_jump_px = diagnostics.get("endpoint_jump_px")
        span_change_ratio = diagnostics.get("span_change_ratio")
        span_change_px = diagnostics.get("span_change_px")
        lateral_drift_px = diagnostics.get("midpoint_lateral_drift_px")
        if (
            endpoint_jump_px is None
            or span_change_ratio is None
            or span_change_px is None
            or lateral_drift_px is None
            or self._max_frame_span_jump_px is None
            or self._max_soft_frame_span_jump_px is None
        ):
            return False
        if _metric_endpoint_border_touch_count(observation, self._analysis_roi) >= 2:
            return False
        return (
            float(span_change_ratio) <= self._max_span_change_ratio
            and float(span_change_px) <= self._max_frame_span_jump_px
            and float(endpoint_jump_px) > self._max_frame_span_jump_px
            and float(endpoint_jump_px) <= self._max_soft_frame_span_jump_px
            and float(lateral_drift_px) <= self._axis_lateral_stabilization_trigger_px
        )

    def _rejection_reason(self, observation: ShapeMetric, diagnostics: dict[str, Any]) -> str:
        if observation.metric_raw is None:
            return str(observation.meta.get("reason", "missing_observation"))
        if (
            self._allows_directional_relocation
            and diagnostics.get("midpoint_lateral_drift_px") is not None
            and float(diagnostics["midpoint_lateral_drift_px"]) > self._max_midpoint_drift_px
        ):
            return "midpoint_lateral_drift_exceeded"
        if diagnostics.get("endpoint_jump_px") is not None and float(diagnostics["endpoint_jump_px"]) > self._max_endpoint_jump_px:
            return "endpoint_jump_exceeded"
        if diagnostics.get("midpoint_drift_px") is not None and float(diagnostics["midpoint_drift_px"]) > self._max_midpoint_drift_px:
            return "midpoint_drift_exceeded"
        if diagnostics.get("span_change_ratio") is not None and not self._span_change_within_limits(diagnostics):
            return "span_change_exceeded"
        return str(observation.meta.get("reason", "tracking_rejected"))

    def _span_change_within_limits(self, diagnostics: dict[str, Any]) -> bool:
        span_change_ratio = diagnostics.get("span_change_ratio")
        if span_change_ratio is None or float(span_change_ratio) > self._max_span_change_ratio:
            return False
        if self._max_frame_span_jump_px is None:
            return True
        span_change_px = diagnostics.get("span_change_px")
        return span_change_px is not None and float(span_change_px) <= self._max_frame_span_jump_px

    def _stabilized_directional_metric(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
        tracking_state: str,
        reason: str = "span_change_stabilized",
        use_last_good_midpoint: bool = False,
    ) -> ShapeMetric:
        point_a = _shape_metric_point(observation.point_a_px)
        point_b = _shape_metric_point(observation.point_b_px)
        if point_a is None or point_b is None or observation.metric_raw is None or self._max_frame_span_jump_px is None:
            return observation
        raw_delta = float(observation.metric_raw) - self._last_good_span_px
        limited_delta = max(
            -float(self._max_frame_span_jump_px),
            min(float(self._max_frame_span_jump_px), raw_delta),
        )
        stabilized_span_px = max(0.0, self._last_good_span_px + limited_delta)
        midpoint = _midpoint(self._last_good_point_a, self._last_good_point_b) if use_last_good_midpoint else _midpoint(point_a, point_b)
        direction_x, direction_y = self._direction_unit or _unit_vector(point_a, point_b)
        stabilized_a = PixelPoint(
            x=int(round(float(midpoint.x) - direction_x * stabilized_span_px / 2.0)),
            y=int(round(float(midpoint.y) - direction_y * stabilized_span_px / 2.0)),
        )
        stabilized_b = PixelPoint(
            x=int(round(float(midpoint.x) + direction_x * stabilized_span_px / 2.0)),
            y=int(round(float(midpoint.y) + direction_y * stabilized_span_px / 2.0)),
        )
        stabilized_span_px = _point_distance(stabilized_a, stabilized_b)
        meta = dict(observation.meta)
        meta.update(
            {
                "source": frame.source,
                "frame_id": frame.frame_id,
                "selection_mode": "tracking_prior_stabilized",
                "tracking_mode": self._tracking_mode,
                "tracking_state": tracking_state,
                "reason": reason,
                "sample_index": sample_index,
                "total_samples": total_samples,
                "observed_metric_raw": observation.metric_raw,
                "observed_point_a_px": observation.point_a_px,
                "observed_point_b_px": observation.point_b_px,
                "stabilized_span_change_px": abs(stabilized_span_px - self._last_good_span_px),
                **diagnostics,
            }
        )
        return ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name=observation.metric_name,
            metric_raw=stabilized_span_px,
            metric_norm=observation.metric_norm,
            quality=observation.quality,
            roi=observation.roi,
            feature_point_px=(midpoint.x, midpoint.y),
            point_a_px=(stabilized_a.x, stabilized_a.y),
            point_b_px=(stabilized_b.x, stabilized_b.y),
            baseline_px=observation.baseline_px,
            meta=meta,
        )

    def _stabilized_last_good_metric(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
        tracking_state: str,
        reason: str,
    ) -> ShapeMetric:
        point_a = self._last_good_point_a
        point_b = self._last_good_point_b
        midpoint = _midpoint(point_a, point_b)
        meta = dict(observation.meta)
        meta.update(
            {
                "source": frame.source,
                "frame_id": frame.frame_id,
                "selection_mode": "tracking_prior_stabilized",
                "tracking_mode": self._tracking_mode,
                "tracking_state": tracking_state,
                "reason": reason,
                "sample_index": sample_index,
                "total_samples": total_samples,
                "observed_metric_raw": observation.metric_raw,
                "observed_point_a_px": observation.point_a_px,
                "observed_point_b_px": observation.point_b_px,
                "stabilized_span_change_px": 0.0,
                **diagnostics,
            }
        )
        return ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name=observation.metric_name,
            metric_raw=self._last_good_span_px,
            metric_norm=observation.metric_norm,
            quality=self._hold_quality,
            roi=observation.roi,
            feature_point_px=(midpoint.x, midpoint.y),
            point_a_px=(point_a.x, point_a.y),
            point_b_px=(point_b.x, point_b.y),
            baseline_px=self._last_good_span_px,
            meta=meta,
        )

    def _stabilized_lateral_metric(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
        tracking_state: str,
    ) -> ShapeMetric:
        point_a = _shape_metric_point(observation.point_a_px)
        point_b = _shape_metric_point(observation.point_b_px)
        if point_a is None or point_b is None or observation.metric_raw is None or self._direction_unit is None:
            return observation
        previous_midpoint = _midpoint(self._last_good_point_a, self._last_good_point_b)
        current_midpoint = _midpoint(point_a, point_b)
        direction_x, direction_y = self._direction_unit
        delta_x = float(current_midpoint.x - previous_midpoint.x)
        delta_y = float(current_midpoint.y - previous_midpoint.y)
        along_shift_px = delta_x * direction_x + delta_y * direction_y
        stabilized_midpoint_x = float(previous_midpoint.x) + direction_x * along_shift_px
        stabilized_midpoint_y = float(previous_midpoint.y) + direction_y * along_shift_px
        stabilized_span_px = float(observation.metric_raw)
        stabilized_a = PixelPoint(
            x=int(round(stabilized_midpoint_x - direction_x * stabilized_span_px / 2.0)),
            y=int(round(stabilized_midpoint_y - direction_y * stabilized_span_px / 2.0)),
        )
        stabilized_b = PixelPoint(
            x=int(round(stabilized_midpoint_x + direction_x * stabilized_span_px / 2.0)),
            y=int(round(stabilized_midpoint_y + direction_y * stabilized_span_px / 2.0)),
        )
        stabilized_span_px = _point_distance(stabilized_a, stabilized_b)
        midpoint = _midpoint(stabilized_a, stabilized_b)
        meta = dict(observation.meta)
        meta.update(
            {
                "source": frame.source,
                "frame_id": frame.frame_id,
                "selection_mode": "tracking_prior_stabilized",
                "tracking_mode": self._tracking_mode,
                "tracking_state": tracking_state,
                "reason": "lateral_drift_stabilized",
                "sample_index": sample_index,
                "total_samples": total_samples,
                "observed_metric_raw": observation.metric_raw,
                "observed_point_a_px": observation.point_a_px,
                "observed_point_b_px": observation.point_b_px,
                **diagnostics,
            }
        )
        return ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name=observation.metric_name,
            metric_raw=stabilized_span_px,
            metric_norm=observation.metric_norm,
            quality=observation.quality,
            roi=observation.roi,
            feature_point_px=(midpoint.x, midpoint.y),
            point_a_px=(stabilized_a.x, stabilized_a.y),
            point_b_px=(stabilized_b.x, stabilized_b.y),
            baseline_px=observation.baseline_px,
            meta=meta,
        )

    def _stabilized_axis_span_metric(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
        tracking_state: str,
        reason: str = "span_change_stabilized",
    ) -> ShapeMetric:
        point_a = _shape_metric_point(observation.point_a_px)
        point_b = _shape_metric_point(observation.point_b_px)
        if point_a is None or point_b is None or observation.metric_raw is None or self._max_frame_span_jump_px is None:
            return observation
        direction = self._direction_unit or _unit_vector(self._last_good_point_a, self._last_good_point_b)
        stabilized_a = _limited_axis_endpoint(
            previous=self._last_good_point_a,
            observed=point_a,
            direction=direction,
            max_step_px=float(self._max_frame_span_jump_px),
        )
        stabilized_b = _limited_axis_endpoint(
            previous=self._last_good_point_b,
            observed=point_b,
            direction=direction,
            max_step_px=float(self._max_frame_span_jump_px),
        )
        stabilized_span_px = _point_distance(stabilized_a, stabilized_b)
        midpoint = _midpoint(stabilized_a, stabilized_b)
        span_delta_px = stabilized_span_px - self._last_good_span_px
        max_span_delta_px = float(self._max_frame_span_jump_px)
        if abs(span_delta_px) > max_span_delta_px:
            limited_span_px = max(
                0.0,
                self._last_good_span_px
                + max(-max_span_delta_px, min(max_span_delta_px, span_delta_px)),
            )
            direction_x, direction_y = direction
            stabilized_a = PixelPoint(
                x=int(round(float(midpoint.x) - direction_x * limited_span_px / 2.0)),
                y=int(round(float(midpoint.y) - direction_y * limited_span_px / 2.0)),
            )
            stabilized_b = PixelPoint(
                x=int(round(float(midpoint.x) + direction_x * limited_span_px / 2.0)),
                y=int(round(float(midpoint.y) + direction_y * limited_span_px / 2.0)),
            )
            stabilized_span_px = _point_distance(stabilized_a, stabilized_b)
            midpoint = _midpoint(stabilized_a, stabilized_b)
        meta = dict(observation.meta)
        meta.update(
            {
                "source": frame.source,
                "frame_id": frame.frame_id,
                "selection_mode": "tracking_prior_stabilized",
                "tracking_mode": self._tracking_mode,
                "tracking_state": tracking_state,
                "reason": reason,
                "sample_index": sample_index,
                "total_samples": total_samples,
                "observed_metric_raw": observation.metric_raw,
                "observed_point_a_px": observation.point_a_px,
                "observed_point_b_px": observation.point_b_px,
                "stabilized_span_change_px": abs(stabilized_span_px - self._last_good_span_px),
                **diagnostics,
            }
        )
        return ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name=observation.metric_name,
            metric_raw=stabilized_span_px,
            metric_norm=observation.metric_norm,
            quality=observation.quality,
            roi=observation.roi,
            feature_point_px=(midpoint.x, midpoint.y),
            point_a_px=(stabilized_a.x, stabilized_a.y),
            point_b_px=(stabilized_b.x, stabilized_b.y),
            baseline_px=observation.baseline_px,
            meta=meta,
        )

    def _hold_last_good_metric(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
        rejection_reason: str,
    ) -> ShapeMetric:
        self._consecutive_misses += 1
        exhausted = self._consecutive_misses > self._max_consecutive_misses
        point_a = self._last_good_point_a
        point_b = self._last_good_point_b
        midpoint = _midpoint(point_a, point_b)
        metric = ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=self._last_good_span_px,
            metric_norm=None,
            quality=0.0 if exhausted else self._hold_quality,
            feature_point_px=(midpoint.x, midpoint.y),
            point_a_px=(point_a.x, point_a.y),
            point_b_px=(point_b.x, point_b.y),
            baseline_px=self._last_good_span_px,
            meta={
                "source": frame.source,
                "frame_id": frame.frame_id,
                "selection_mode": "tracking_prior_hold",
                "tracking_mode": self._tracking_mode,
                "tracking_state": "invalidated" if exhausted else "holding_last_good",
                "reason": "tracking_prior_exhausted" if exhausted else rejection_reason,
                "observation_selection_mode": observation.meta.get("selection_mode"),
                "observation_reason": observation.meta.get("reason"),
                "sample_index": sample_index,
                "total_samples": total_samples,
                "max_endpoint_jump_px": self._max_endpoint_jump_px,
                "max_midpoint_drift_px": self._max_midpoint_drift_px,
                "max_span_change_ratio": self._max_span_change_ratio,
                "max_frame_span_jump_px": self._max_frame_span_jump_px,
                "max_soft_frame_span_jump_px": self._max_soft_frame_span_jump_px,
                "max_consecutive_misses": self._max_consecutive_misses,
                "consecutive_misses": self._consecutive_misses,
                **diagnostics,
            },
        )
        return metric

    def _remember(self, observation: ShapeMetric) -> None:
        point_a = _shape_metric_point(observation.point_a_px)
        point_b = _shape_metric_point(observation.point_b_px)
        if point_a is None or point_b is None or observation.metric_raw is None:
            return
        self._last_good_point_a = point_a
        self._last_good_point_b = point_b
        self._last_good_span_px = float(observation.metric_raw)
        self._has_runtime_lock = True

    def _directional_component_bridge_retry(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
        bootstrap: bool = False,
    ) -> ShapeMetric | None:
        if not self._allows_directional_component_bridge_retry:
            return None
        if not self._should_attempt_directional_component_bridge_retry(observation, diagnostics):
            return None
        base_kernel = self._directional_base_component_bridge_kernel
        retry_kernels = self._directional_component_bridge_retry_kernels()
        if base_kernel is None or not retry_kernels:
            return None
        best_stabilized: ShapeMetric | None = None
        for retry_kernel in retry_kernels:
            retry_observation = self._observation_source.extract(
                frame,
                temp,
                sample_index=sample_index,
                total_samples=total_samples,
                component_bridge_kernel=retry_kernel,
            )
            retry_diagnostics = self._tracking_diagnostics(retry_observation)
            if retry_observation.metric_raw is None:
                continue
            if self._candidate_within_prior(retry_diagnostics):
                tracking_state = (
                    "bootstrapped"
                    if bootstrap
                    else "reacquired"
                    if self._consecutive_misses > 0
                    else "accepted"
                )
                self._remember(retry_observation)
                self._consecutive_misses = 0
                self._clear_pending_reacquire()
                retry_observation.meta["tracking_mode"] = self._tracking_mode
                retry_observation.meta["tracking_state"] = tracking_state
                retry_observation.meta["component_bridge_retry_kernel"] = retry_kernel
                retry_observation.meta["component_bridge_base_kernel"] = base_kernel
                retry_observation.meta.update(retry_diagnostics)
                return retry_observation
            if self._directional_candidate_is_stabilizable_span_jitter(
                retry_observation,
                retry_diagnostics,
            ):
                tracking_state = (
                    "bootstrapped_stabilized"
                    if bootstrap
                    else "reacquired_stabilized"
                    if self._consecutive_misses > 0
                    else "accepted_stabilized"
                )
                stabilized = self._stabilized_directional_metric(
                    frame,
                    temp,
                    sample_index=sample_index,
                    total_samples=total_samples,
                    observation=retry_observation,
                    diagnostics=retry_diagnostics,
                    tracking_state=tracking_state,
                    reason="component_bridge_retry_span_stabilized",
                    use_last_good_midpoint=True,
                )
                stabilized.meta["component_bridge_retry_kernel"] = retry_kernel
                stabilized.meta["component_bridge_base_kernel"] = base_kernel
                if self._retry_stabilized_candidate_is_better(stabilized, best_stabilized):
                    best_stabilized = stabilized
                continue
            if self._directional_candidate_is_plausible_relocation(
                retry_observation,
                retry_diagnostics,
            ):
                tracking_state = (
                    "bootstrapped_relocated"
                    if bootstrap
                    else "relocated"
                    if self._consecutive_misses > 0
                    else "accepted_relocated"
                )
                self._remember(retry_observation)
                self._consecutive_misses = 0
                self._clear_pending_reacquire()
                retry_observation.meta["tracking_mode"] = self._tracking_mode
                retry_observation.meta["tracking_state"] = tracking_state
                retry_observation.meta["component_bridge_retry_kernel"] = retry_kernel
                retry_observation.meta["component_bridge_base_kernel"] = base_kernel
                retry_observation.meta.update(retry_diagnostics)
                return retry_observation
        if best_stabilized is not None:
            self._remember(best_stabilized)
            self._consecutive_misses = 0
            self._clear_pending_reacquire()
            return best_stabilized
        return None

    def _retry_stabilized_candidate_is_better(
        self,
        candidate: ShapeMetric,
        current: ShapeMetric | None,
    ) -> bool:
        if current is None:
            return True
        candidate_endpoint_jump = float(candidate.meta.get("endpoint_jump_px") or 0.0)
        current_endpoint_jump = float(current.meta.get("endpoint_jump_px") or 0.0)
        endpoint_delta = candidate_endpoint_jump - current_endpoint_jump
        if abs(endpoint_delta) > 1e-9:
            return endpoint_delta < 0.0
        candidate_span_change = float(candidate.meta.get("span_change_px") or 0.0)
        current_span_change = float(current.meta.get("span_change_px") or 0.0)
        span_delta = candidate_span_change - current_span_change
        if abs(span_delta) > 1e-9:
            return span_delta < 0.0
        return int(candidate.meta.get("component_bridge_retry_kernel") or 0) < int(
            current.meta.get("component_bridge_retry_kernel") or 0
        )

    def _should_attempt_directional_component_bridge_retry(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> bool:
        reason = self._rejection_reason(observation, diagnostics)
        if reason != "span_change_exceeded":
            return True
        if not self._is_directional_max_chord:
            return False
        if observation.metric_raw is None:
            return False
        if observation.meta.get("component_area") is None:
            return False
        span_change_px = diagnostics.get("span_change_px")
        if span_change_px is None or self._max_frame_span_jump_px is None:
            return False
        return float(span_change_px) > float(self._max_frame_span_jump_px)

    def _should_attempt_bootstrap_max_chord_component_bridge_retry(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> bool:
        if not self._is_directional_max_chord:
            return False
        if observation.metric_raw is None:
            return False
        if observation.meta.get("component_area") is None:
            return False
        if self._rejection_reason(observation, diagnostics) != "span_change_exceeded":
            return False
        span_change_px = diagnostics.get("span_change_px")
        if span_change_px is None or self._max_frame_span_jump_px is None:
            return False
        return float(span_change_px) > float(self._max_frame_span_jump_px)

    def _directional_component_bridge_retry_kernels(self) -> tuple[int, ...]:
        retry_kernel = self._directional_retry_component_bridge_kernel
        base_kernel = self._directional_base_component_bridge_kernel
        if retry_kernel is None or base_kernel is None or retry_kernel <= base_kernel:
            return ()
        kernels = {int(retry_kernel)}
        if self._is_directional_max_chord:
            for extra in (20, 40, 60):
                kernels.add(_directional_odd_kernel(int(retry_kernel) + extra))
        return tuple(sorted(kernel for kernel in kernels if kernel > int(base_kernel)))

    def _persistent_reacquire_metric(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> ShapeMetric | None:
        if not self._candidate_can_seed_persistent_reacquire(observation, diagnostics):
            self._clear_pending_reacquire()
            return None
        point_a = _shape_metric_point(observation.point_a_px)
        point_b = _shape_metric_point(observation.point_b_px)
        if point_a is None or point_b is None or observation.metric_raw is None:
            self._clear_pending_reacquire()
            return None
        if not self._pending_reacquire_matches(point_a, point_b, float(observation.metric_raw)):
            return None
        self._pending_reacquire_count += 1
        if self._pending_reacquire_count < 2:
            return None
        meta = dict(observation.meta)
        meta.update(
            {
                "source": frame.source,
                "frame_id": frame.frame_id,
                "tracking_mode": self._tracking_mode,
                "tracking_state": "reacquired",
                "reason": "persistent_reacquire",
                "sample_index": sample_index,
                "total_samples": total_samples,
                "persistent_reacquire_count": self._pending_reacquire_count,
                **diagnostics,
            }
        )
        observation.meta = meta
        return observation

    def _record_pending_reacquire(self, observation: ShapeMetric, diagnostics: dict[str, Any]) -> None:
        if not self._candidate_can_seed_persistent_reacquire(observation, diagnostics):
            self._clear_pending_reacquire()
            return
        point_a = _shape_metric_point(observation.point_a_px)
        point_b = _shape_metric_point(observation.point_b_px)
        if point_a is None or point_b is None or observation.metric_raw is None:
            self._clear_pending_reacquire()
            return
        metric_raw = float(observation.metric_raw)
        if self._pending_reacquire_matches(point_a, point_b, metric_raw):
            self._pending_reacquire_count += 1
            return
        self._set_pending_reacquire(point_a, point_b, metric_raw, count=1)

    def _candidate_can_seed_persistent_reacquire(
        self,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
    ) -> bool:
        if self._is_directional_max_chord:
            return False
        if not self._allows_directional_relocation or not self._has_runtime_lock:
            return False
        if observation.metric_raw is None or observation.point_a_px is None or observation.point_b_px is None:
            return False
        if float(observation.quality or 0.0) <= 0.0:
            return False
        endpoint_jump_px = diagnostics.get("endpoint_jump_px")
        midpoint_drift_px = diagnostics.get("midpoint_drift_px")
        lateral_drift_px = diagnostics.get("midpoint_lateral_drift_px")
        if endpoint_jump_px is None or midpoint_drift_px is None:
            return False
        if float(endpoint_jump_px) > self._max_endpoint_jump_px:
            return False
        if float(midpoint_drift_px) > self._max_midpoint_drift_px:
            return False
        if lateral_drift_px is not None and float(lateral_drift_px) > self._max_midpoint_drift_px:
            return False
        reason = self._rejection_reason(observation, diagnostics)
        return reason == "span_change_exceeded"

    def _pending_reacquire_matches(
        self,
        point_a: PixelPoint,
        point_b: PixelPoint,
        span_px: float,
    ) -> bool:
        if (
            self._pending_reacquire_point_a is None
            or self._pending_reacquire_point_b is None
            or self._pending_reacquire_span_px is None
        ):
            return False
        max_step_px = max(
            12.0,
            float(self._max_frame_span_jump_px or 0.0) * 2.0,
        )
        max_span_delta_px = max(
            12.0,
            abs(float(self._pending_reacquire_span_px)) * 0.02,
        )
        return (
            _point_distance(self._pending_reacquire_point_a, point_a) <= max_step_px
            and _point_distance(self._pending_reacquire_point_b, point_b) <= max_step_px
            and abs(float(span_px) - float(self._pending_reacquire_span_px)) <= max_span_delta_px
        )

    def _set_pending_reacquire(
        self,
        point_a: PixelPoint,
        point_b: PixelPoint,
        span_px: float,
        *,
        count: int,
    ) -> None:
        self._pending_reacquire_point_a = point_a
        self._pending_reacquire_point_b = point_b
        self._pending_reacquire_span_px = float(span_px)
        self._pending_reacquire_count = max(1, int(count))

    def _clear_pending_reacquire(self) -> None:
        self._pending_reacquire_point_a = None
        self._pending_reacquire_point_b = None
        self._pending_reacquire_span_px = None
        self._pending_reacquire_count = 0

    def _current_axis_prior_point(self) -> PixelPoint | None:
        return _midpoint(self._last_good_point_a, self._last_good_point_b)

    def _current_axis_prior_tolerance_px(self) -> float | None:
        return self._max_midpoint_drift_px

    def _current_prior_point_a(self) -> PixelPoint | None:
        return self._last_good_point_a

    def _current_prior_point_b(self) -> PixelPoint | None:
        return self._last_good_point_b

    def _current_endpoint_prior_tolerance_px(self) -> float | None:
        if self._max_frame_span_jump_px is None:
            return min(64.0, self._max_endpoint_jump_px)
        return min(64.0, max(24.0, float(self._max_frame_span_jump_px) * 8.0))


class LiveRunCoordinator:
    """Single-threaded live-run coordinator for the Phase 3 vertical slice."""

    def __init__(self, repo: SessionSummaryRepo, artifact_store: SessionArtifactStore) -> None:
        self.repo = repo
        self.artifact_store = artifact_store

    def run(
        self,
        *,
        session_id: str,
        definition: MeasurementDefinition,
        target_temperature_celsius: float,
        run_config: RunRuntimeConfig,
        analysis_engine: str,
        channel_name: str,
        as_fit_point_count: int,
        af_fit_point_count: int,
        camera_config: CameraRuntimeConfig | None = None,
        effective_definition: MeasurementDefinition | None = None,
        measurement_capture_plan: dict[str, Any] | None = None,
        camera: CameraPort,
        temp_reader: TempReader,
        temp_controller: TempControllerPort,
        metric_source: LiveMetricSource,
        quality_threshold: float = 0.75,
        stop_on_target_reached: bool = True,
        stop_requested: Callable[[], bool] | None = None,
        wait_for_next_sample: Callable[[float], bool] | None = None,
        status_callback: Callable[[RunStatus, dict[str, Any]], None] | None = None,
        telemetry_callback: Callable[[dict[str, Any]], None] | None = None,
        sample_callback: Callable[[SyncPoint, dict[str, Any]], None] | None = None,
    ) -> LiveRunExecution:
        started_at_ms = _now_ms()
        events = [
            _event(
                started_at_ms,
                "run_started",
                {"target_temperature_celsius": target_temperature_celsius},
            )
        ]
        sync_points: list[SyncPoint] = []
        telemetry: list[dict[str, Any]] = []
        hub = SyncHub()
        output_started = False
        playback_sample_count = _resolve_playback_sample_count(metric_source, temp_reader, camera)
        sample_interval_ms = resolve_measurement_interval_ms(
            run_config,
            playback_sample_count=playback_sample_count,
            stop_on_target_reached=stop_on_target_reached,
        )
        next_sample_due_ms = started_at_ms

        try:
            temp_controller.set_target_temperature(target_temperature_celsius)
            events.append(
                _event(
                    started_at_ms,
                    "target_temperature_set",
                    {"target_temperature_celsius": target_temperature_celsius},
                )
            )
            temp_controller.start_output()
            output_started = True
            events.append(_event(started_at_ms, "output_started", {}))
            if status_callback is not None:
                status_callback(RunStatus.RUNNING, {"started_at_ms": started_at_ms})

            if playback_sample_count is not None:
                max_samples = max(1, int(playback_sample_count))
            else:
                configured_max_samples = int(getattr(run_config, "manual_stop_max_samples", 10_000) or 0)
                # A non-positive value means operator/hardware terminal conditions own the run.
                max_samples = None if configured_max_samples <= 0 else max(1, configured_max_samples)
            sample_index = 0
            sample_limit_exhausted = False
            while max_samples is None or sample_index < max_samples:
                if stop_requested is not None and stop_requested():
                    stop_detail = "Run stop requested before the next sample."
                    events.append(_event(_now_ms(), "run_stop_requested", {"reason": "user_stop"}))
                    if status_callback is not None:
                        status_callback(RunStatus.STOPPING, {"reason": "user_stop"})
                    raise LiveRunStopRequested("user_stop", stop_detail)

                sample_started_ms = _now_ms()
                sample_started_perf = time.perf_counter()
                frame = camera.read_frame()
                frame_read_ms = (time.perf_counter() - sample_started_perf) * 1000.0
                frame.timestamp_ms = _resolved_timestamp_ms(frame.timestamp_ms, fallback_ms=sample_started_ms)
                if frame.frame_id is None:
                    frame.frame_id = sample_index + 1

                temp_started_perf = time.perf_counter()
                temp = temp_reader.read()
                temp_read_ms = (time.perf_counter() - temp_started_perf) * 1000.0
                temp.timestamp_ms = _resolved_timestamp_ms(
                    temp.timestamp_ms,
                    fallback_ms=max(sample_started_ms, frame.timestamp_ms),
                )
                sample_timestamp_ms = max(frame.timestamp_ms, temp.timestamp_ms)

                extract_started_perf = time.perf_counter()
                metric = metric_source.extract(
                    frame,
                    temp,
                    sample_index=sample_index,
                    total_samples=0 if max_samples is None else max_samples,
                )
                metric_extract_ms = (time.perf_counter() - extract_started_perf) * 1000.0
                metric.meta["frame_read_ms"] = frame_read_ms
                metric.meta["temp_read_ms"] = temp_read_ms
                metric.meta["metric_extract_ms"] = metric_extract_ms
                metric.meta["sample_loop_ms"] = (time.perf_counter() - sample_started_perf) * 1000.0
                metric.timestamp_ms = sample_timestamp_ms
                if metric.metric_raw is None:
                    raise RuntimeError(f"tracking_metric_unavailable:{metric.meta.get('reason', 'unknown')}")
                quality_grace_active = (
                    bool(run_config.stop_on_invalid_tracking)
                    and int(sample_index) < max(0, int(getattr(run_config, "invalid_tracking_grace_samples", 0) or 0))
                )
                if metric.quality < quality_threshold:
                    invalidation_payload = {
                        "reason": "tracking_quality_below_threshold",
                        "tracking_quality": metric.quality,
                        "quality_threshold": quality_threshold,
                    }
                    metric.meta["quality_threshold_grace_active"] = quality_grace_active
                    metric.meta["quality_threshold_grace_samples"] = int(
                        max(0, int(getattr(run_config, "invalid_tracking_grace_samples", 0) or 0))
                    )
                    if quality_grace_active:
                        invalidation_payload["grace_active"] = True
                        invalidation_payload["sample_index"] = int(sample_index)
                        invalidation_payload["grace_samples"] = int(
                            max(0, int(getattr(run_config, "invalid_tracking_grace_samples", 0) or 0))
                        )
                        events.append(_event(sample_timestamp_ms, "tracking_quality_grace", invalidation_payload))
                    else:
                        events.append(_event(sample_timestamp_ms, "tracking_invalidated", invalidation_payload))
                        if status_callback is not None and run_config.stop_on_invalid_tracking:
                            status_callback(RunStatus.INVALIDATED, invalidation_payload)
                        if run_config.stop_on_invalid_tracking:
                            if status_callback is not None:
                                status_callback(RunStatus.STOPPING, {"reason": "invalid_tracking"})
                            raise LiveRunTrackingInvalidated(
                                "invalid_tracking",
                                f"Tracking quality dropped below threshold: {metric.quality:.3f} < {quality_threshold:.3f}",
                            )

                hub.update_frame(frame)
                hub.update_temp(temp)
                hub.update_metric(metric)
                sync_point = hub.snapshot()
                sync_points.append(sync_point)
                telemetry_started_perf = time.perf_counter()
                telemetry_row = _telemetry_row(
                    sync_point,
                    sample_index=sample_index,
                    previous_timestamp_ms=None if len(sync_points) < 2 else sync_points[-2].timestamp_ms,
                )
                telemetry_row_ms = (time.perf_counter() - telemetry_started_perf) * 1000.0
                telemetry_row["telemetry_row_ms"] = telemetry_row_ms
                callback_started_perf = time.perf_counter()
                if sample_callback is not None:
                    sample_callback(sync_point, telemetry_row)
                sample_callbacks_ms = (time.perf_counter() - callback_started_perf) * 1000.0
                telemetry_row["sample_callbacks_ms"] = sample_callbacks_ms
                telemetry_row["post_sample_ms"] = telemetry_row_ms + sample_callbacks_ms
                telemetry.append(telemetry_row)
                if telemetry_callback is not None:
                    telemetry_callback(telemetry_row)
                events.append(
                    _event(
                        sync_point.timestamp_ms,
                        "sample_captured",
                        {
                            "temperature_celsius": temp.celsius,
                            "space1_px": metric.metric_raw,
                            "tracking_quality": metric.quality,
                            "frame_id": frame.frame_id,
                        },
                    )
                )

                if (
                    playback_sample_count is not None
                    and len(sync_points) >= playback_sample_count
                ):
                    break
                if stop_on_target_reached and temp.celsius >= target_temperature_celsius and len(sync_points) >= 3:
                    break
                next_sample_due_ms += sample_interval_ms
                remaining_wait_s = max(0.0, (next_sample_due_ms - _now_ms()) / 1000.0)
                if wait_for_next_sample is not None and wait_for_next_sample(remaining_wait_s):
                    events.append(_event(_now_ms(), "run_stop_requested", {"reason": "user_stop"}))
                    if status_callback is not None:
                        status_callback(RunStatus.STOPPING, {"reason": "user_stop"})
                    raise LiveRunStopRequested("user_stop", "Run stop requested while waiting for the next sample.")
                sample_index += 1
            else:
                sample_limit_exhausted = True
            if sample_limit_exhausted:
                if playback_sample_count is not None:
                    raise RuntimeError("mock_playback_not_completed")
                if stop_on_target_reached:
                    raise RuntimeError("target_temperature_not_reached")
                raise RuntimeError("manual_stop_timeout")
        finally:
            stop_timestamp_ms = _now_ms()
            if output_started:
                temp_controller.stop_output()
                events.append(_event(stop_timestamp_ms, "output_stopped", {}))

        afas_result = analyze_afas(
            sync_points,
            channel_name=channel_name,
            as_fit_point_count=as_fit_point_count,
            af_fit_point_count=af_fit_point_count,
        )
        rate_snapshot = summarize_rate_snapshot(sync_points=sync_points, telemetry=telemetry)
        measurement_profile = summarize_measurement_profile(
            camera_config if camera_config is not None else CameraRuntimeConfig()
        )
        warnings = summarize_rate_warnings(
            rate_snapshot,
            target_measurement_hz=run_config.measurement_target_hz,
            is_terminal=True,
        )
        rates_payload = _rate_snapshot_payload(rate_snapshot)
        measurement_profile_payload = _measurement_profile_payload(measurement_profile)
        detail = build_live_detail(
            session_id=session_id,
            sync_points=sync_points,
            afas_result=afas_result,
            rate_snapshot=rate_snapshot,
            measurement_profile=measurement_profile,
            warnings=warnings,
        )
        keyframe_refs = _keyframe_artifact_refs(detail["key_frames"])
        afas_dataset = build_afas_postprocessing_dataset(
            session_id=session_id,
            definition=definition,
            sync_points=sync_points,
            channel_name=channel_name,
            analysis_engine=analysis_engine,
            capture_mode=CaptureMode.POST_RUN_REVIEW.value,
            rates=rates_payload,
            measurement_profile=measurement_profile_payload,
            warnings=warnings,
            live_result_snapshot={
                "result_status": afas_result.result_status,
                "result_reason": afas_result.reason,
                "result_detail": afas_result.detail,
                "af95": afas_result.af95,
                "as_value": afas_result.as_value,
                "af_value": afas_result.af_value,
                "point_count": detail["point_count"],
            },
        )
        if warnings:
            events.append(
                _event(
                    _now_ms(),
                    "measurement_cadence_assessed",
                    {
                        "warnings": warnings,
                        "measurement_sample_hz": rate_snapshot.measurement_sample_hz,
                        "target_measurement_hz": run_config.measurement_target_hz,
                        "dropped_frame_count": rate_snapshot.dropped_frame_count,
                    },
                )
            )
        result = build_live_run_result(
            session_id=session_id,
            state="completed",
            analysis_engine=analysis_engine,
            channel_name=channel_name,
            result_status=afas_result.result_status,
            result_reason=afas_result.reason,
            result_detail=afas_result.detail,
            af95=afas_result.af95,
            as_value=afas_result.as_value,
            af_value=afas_result.af_value,
            point_count=detail["point_count"],
            keyframe_refs=keyframe_refs,
            capture_mode=CaptureMode.POST_RUN_REVIEW.value,
            rates=rates_payload,
            measurement_profile=measurement_profile_payload,
            warnings=warnings,
        )
        self.artifact_store.save_live_bundle(
            session_id,
            definition=_definition_payload(definition),
            definition_original=_definition_payload(definition),
            definition_effective_local=None
            if effective_definition is None
            else _definition_payload(effective_definition),
            measurement_capture_plan=measurement_capture_plan,
            telemetry=telemetry,
            detail=detail,
            result=result,
            events=events,
            afas_dataset=afas_dataset,
            keyframes=detail["key_frames"],
        )

        summary = SessionSummary(
            session_id=session_id,
            state="completed",
            point_count=detail["point_count"],
            af95=afas_result.af95,
            created_at_ms=started_at_ms,
        )
        self.repo.save_summary(summary)
        events.append(
            _event(
                _now_ms(),
                "run_completed",
                {
                    "af95": afas_result.af95,
                    "result_status": afas_result.result_status,
                    "result_reason": afas_result.reason,
                },
            )
        )
        return LiveRunExecution(
            summary=summary,
            detail=detail,
            result=result,
            telemetry=telemetry,
            events=events,
            afas_dataset=afas_dataset,
        )


def build_partial_live_run_execution(
    *,
    session_id: str,
    started_at_ms: int,
    terminal_state: str,
    terminal_reason: str | None,
    terminal_detail: str,
    definition: MeasurementDefinition,
    telemetry: list[dict[str, Any]],
    events: list[dict[str, Any]],
    camera_config: CameraRuntimeConfig | None,
    analysis_engine: str,
    channel_name: str,
    as_fit_point_count: int,
    af_fit_point_count: int,
    target_measurement_hz: float | None,
) -> LiveRunExecution:
    rate_snapshot = summarize_rate_snapshot(telemetry=telemetry)
    measurement_profile = summarize_measurement_profile(
        camera_config if camera_config is not None else CameraRuntimeConfig()
    )
    warnings = summarize_rate_warnings(
        rate_snapshot,
        target_measurement_hz=target_measurement_hz,
        is_terminal=True,
    )
    rates_payload = _rate_snapshot_payload(rate_snapshot)
    measurement_profile_payload = _measurement_profile_payload(measurement_profile)
    sync_points = _sync_points_from_telemetry(telemetry)
    afas_result = analyze_afas(
        sync_points,
        channel_name=channel_name,
        as_fit_point_count=as_fit_point_count,
        af_fit_point_count=af_fit_point_count,
    )
    result_detail = _partial_result_detail(
        analysis_detail=afas_result.detail,
        terminal_detail=terminal_detail,
    )
    terminal_warning = f"terminal_{terminal_state}: {terminal_detail}"
    warnings_with_terminal = [*warnings, terminal_warning]
    afas_dataset = build_afas_postprocessing_dataset(
        session_id=session_id,
        definition=definition,
        sync_points=sync_points,
        channel_name=channel_name,
        analysis_engine=analysis_engine,
        capture_mode=CaptureMode.POST_RUN_REVIEW.value,
        rates=rates_payload,
        measurement_profile=measurement_profile_payload,
        warnings=list(warnings_with_terminal),
        live_result_snapshot={
            "result_status": afas_result.result_status,
            "result_reason": afas_result.reason,
            "result_detail": result_detail,
            "terminal_state": terminal_state,
            "terminal_reason": terminal_reason,
            "terminal_detail": terminal_detail,
            "af95": afas_result.af95,
            "as_value": afas_result.as_value,
            "af_value": afas_result.af_value,
            "point_count": len(sync_points),
        },
    )
    detail = build_live_detail(
        session_id=session_id,
        sync_points=sync_points,
        afas_result=afas_result,
        rate_snapshot=rate_snapshot,
        measurement_profile=measurement_profile,
        warnings=list(warnings_with_terminal),
    )
    detail["key_frames"] = []
    result = build_live_run_result(
        session_id=session_id,
        state=terminal_state,
        analysis_engine=analysis_engine,
        channel_name=channel_name,
        result_status=afas_result.result_status,
        result_reason=afas_result.reason,
        result_detail=result_detail,
        af95=afas_result.af95,
        as_value=afas_result.as_value,
        af_value=afas_result.af_value,
        point_count=detail["point_count"],
        keyframe_refs=[],
        capture_mode=CaptureMode.POST_RUN_REVIEW.value,
        rates=rates_payload,
        measurement_profile=measurement_profile_payload,
        warnings=warnings_with_terminal,
    )
    summary = SessionSummary(
        session_id=session_id,
        state=terminal_state,
        point_count=detail["point_count"],
        af95=afas_result.af95,
        created_at_ms=started_at_ms,
    )
    return LiveRunExecution(
        summary=summary,
        detail=detail,
        result=result,
        telemetry=list(telemetry),
        events=list(events),
        afas_dataset=afas_dataset,
    )


def _partial_result_detail(*, analysis_detail: str, terminal_detail: str) -> str:
    if not terminal_detail:
        return analysis_detail
    if not analysis_detail:
        return terminal_detail
    if terminal_detail in analysis_detail:
        return analysis_detail
    return f"{analysis_detail} Terminal detail: {terminal_detail}"


def build_live_detail(
    session_id: str,
    sync_points: list[SyncPoint],
    afas_result: AfasAnalysisResult,
    rate_snapshot: RunRateSnapshot,
    measurement_profile: MeasurementProfileSnapshot,
    warnings: list[str],
) -> dict[str, Any]:
    normalized_points = normalize_sync_points(sync_points)
    normalized_by_timestamp = {point.timestamp_ms: point for point in normalized_points}
    detail_points: list[dict[str, Any]] = []
    for sync_point in sync_points:
        if sync_point.temp is None or sync_point.metric is None or sync_point.metric.metric_raw is None:
            continue
        normalized = normalized_by_timestamp.get(sync_point.timestamp_ms)
        detail_points.append(
            {
                "timestamp_ms": sync_point.timestamp_ms,
                "celsius": sync_point.temp.celsius,
                "metric_raw": sync_point.metric.metric_raw,
                "metric_norm": normalized.metric_norm if normalized is not None else None,
                "quality": sync_point.metric.quality,
            }
        )

    return {
        "session_id": session_id,
        "source": "live_run",
        "af95": afas_result.af95,
        "as_value": afas_result.as_value,
        "af_value": afas_result.af_value,
        "result_status": afas_result.result_status,
        "result_reason": afas_result.reason,
        "result_detail": afas_result.detail,
        "point_count": len(detail_points),
        "capture_mode": CaptureMode.POST_RUN_REVIEW.value,
        "rates": _rate_snapshot_payload(rate_snapshot),
        "measurement_profile": _measurement_profile_payload(measurement_profile),
        "warnings": list(warnings),
        "points": detail_points,
        "key_frames": _select_key_frames(sync_points),
    }


def _detail_points_from_telemetry(telemetry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    detail_points: list[dict[str, Any]] = []
    for row in telemetry:
        if row.get("timestamp_ms") is None or row.get("temperature_celsius") is None or row.get("space1_px") is None:
            continue
        detail_points.append(
            {
                "timestamp_ms": int(row["timestamp_ms"]),
                "celsius": float(row["temperature_celsius"]),
                "metric_raw": float(row["space1_px"]),
                "metric_norm": None,
                "quality": float(row.get("tracking_quality") or 0.0),
            }
        )
    return detail_points


def _sync_points_from_telemetry(telemetry: list[dict[str, Any]]) -> list[SyncPoint]:
    sync_points: list[SyncPoint] = []
    for row in telemetry:
        if row.get("timestamp_ms") is None or row.get("temperature_celsius") is None or row.get("space1_px") is None:
            continue
        timestamp_ms = int(row["timestamp_ms"])
        temp_timestamp_ms = int(row.get("temp_timestamp_ms") or timestamp_ms)
        metric_timestamp_ms = int(row.get("metric_timestamp_ms") or timestamp_ms)
        frame_timestamp_ms = row.get("frame_timestamp_ms")
        frame_id = row.get("frame_id")
        frame = None
        if frame_timestamp_ms is not None or frame_id is not None:
            frame = FramePacket(
                timestamp_ms=int(frame_timestamp_ms or timestamp_ms),
                source="telemetry",
                frame_id=None if frame_id is None else int(frame_id),
            )
        sync_points.append(
            SyncPoint(
                timestamp_ms=timestamp_ms,
                frame=frame,
                temp=TempReading(
                    timestamp_ms=temp_timestamp_ms,
                    celsius=float(row["temperature_celsius"]),
                    source="telemetry",
                ),
                metric=ShapeMetric(
                    timestamp_ms=metric_timestamp_ms,
                    metric_name="metric_raw",
                    metric_raw=float(row["space1_px"]),
                    quality=float(row.get("tracking_quality") or 0.0),
                    point_a_px=_tuple_point(row.get("point_a_px")),
                    point_b_px=_tuple_point(row.get("point_b_px")),
                ),
            )
        )
    return sync_points


def _tuple_point(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        return int(value[0]), int(value[1])
    except (TypeError, ValueError):
        return None


def summarize_rate_snapshot(
    *,
    sync_points: list[SyncPoint] | None = None,
    telemetry: list[dict[str, Any]] | None = None,
    preview_display_fps: float | None = None,
) -> RunRateSnapshot:
    measurement_sample_hz = _sample_rate_hz(
        [] if telemetry is None else [int(item["timestamp_ms"]) for item in telemetry if "timestamp_ms" in item]
    )
    artifact_capture_hz = measurement_sample_hz
    camera_resulting_fps = _camera_resulting_fps(sync_points or [], telemetry or [])
    dropped_frame_count = _dropped_frame_count(sync_points or [], telemetry or [])
    return RunRateSnapshot(
        camera_resulting_fps=camera_resulting_fps,
        preview_display_fps=preview_display_fps,
        measurement_sample_hz=measurement_sample_hz,
        artifact_capture_hz=artifact_capture_hz,
        dropped_frame_count=dropped_frame_count,
    )


def summarize_measurement_profile(camera_config: CameraRuntimeConfig | CameraAcquisitionProfileConfig) -> MeasurementProfileSnapshot:
    profile = camera_config.measurement if isinstance(camera_config, CameraRuntimeConfig) else camera_config
    roi = None
    if profile.device_roi.width > 0 and profile.device_roi.height > 0:
        roi = RectRegion(
            x=profile.device_roi.x,
            y=profile.device_roi.y,
            width=profile.device_roi.width,
            height=profile.device_roi.height,
        )
    return MeasurementProfileSnapshot(
        acquisition_roi=roi,
        decimation=profile.decimation,
        binning=profile.binning,
        exposure_us=profile.exposure_us,
    )


def _definition_payload(definition: MeasurementDefinition) -> dict[str, Any]:
    return {
        "analysis_roi": {
            "x": definition.analysis_roi.x,
            "y": definition.analysis_roi.y,
            "width": definition.analysis_roi.width,
            "height": definition.analysis_roi.height,
        },
        "metric_box": {
            "center_x": definition.metric_box.center_x,
            "center_y": definition.metric_box.center_y,
            "width": definition.metric_box.width,
            "height": definition.metric_box.height,
            "angle_deg": definition.metric_box.angle_deg,
        },
        "point_a_px": {
            "x": definition.point_a_px.x,
            "y": definition.point_a_px.y,
        },
        "point_b_px": {
            "x": definition.point_b_px.x,
            "y": definition.point_b_px.y,
        },
        "observation_axis": definition.observation_axis.value,
        "foreground_polarity": definition.foreground_polarity,
        "threshold_mode": definition.threshold_mode,
        "ignore_internal_texture": definition.ignore_internal_texture,
        "min_target_area_px": definition.min_target_area_px,
        "sensitivity": definition.sensitivity,
        "direction_angle_deg": definition.direction_angle_deg,
        "direction_projection_mode": definition.direction_projection_mode,
        "target_geometry_mode": definition.target_geometry_mode,
        "side_guard_ratio": definition.side_guard_ratio,
    }


def _telemetry_row(
    sync_point: SyncPoint,
    *,
    sample_index: int,
    previous_timestamp_ms: int | None,
) -> dict[str, Any]:
    if sync_point.temp is None or sync_point.metric is None or sync_point.metric.metric_raw is None:
        raise ValueError("telemetry row requires temperature and metric data")
    frame = sync_point.frame
    metric = sync_point.metric
    metric_meta = metric.meta
    return {
        "timestamp_ms": sync_point.timestamp_ms,
        "sample_index": sample_index,
        "sample_interval_ms": None
        if previous_timestamp_ms is None
        else max(0, sync_point.timestamp_ms - previous_timestamp_ms),
        "frame_id": None if frame is None or frame.frame_id is None else int(frame.frame_id),
        "frame_timestamp_ms": None if frame is None else int(frame.timestamp_ms),
        "temp_timestamp_ms": int(sync_point.temp.timestamp_ms),
        "metric_timestamp_ms": int(sync_point.metric.timestamp_ms),
        "camera_resulting_fps": _frame_resulting_fps(frame),
        "temperature_celsius": sync_point.temp.celsius,
        "space1_px": metric.metric_raw,
        "tracking_quality": metric.quality,
        "point_a_px": None
        if metric.point_a_px is None
        else [int(metric.point_a_px[0]), int(metric.point_a_px[1])],
        "point_b_px": None
        if metric.point_b_px is None
        else [int(metric.point_b_px[0]), int(metric.point_b_px[1])],
        "source_point_a_px": _metric_meta_point(metric_meta, "source_point_a_px"),
        "source_point_b_px": _metric_meta_point(metric_meta, "source_point_b_px"),
        "axis_point_a_px": _metric_meta_point(metric_meta, "axis_point_a_px"),
        "axis_point_b_px": _metric_meta_point(metric_meta, "axis_point_b_px"),
        "tracking_mode": metric_meta.get("tracking_mode"),
        "tracking_state": metric_meta.get("tracking_state"),
        "selection_mode": metric_meta.get("selection_mode"),
        "target_geometry_mode": metric_meta.get("target_geometry_mode"),
        "projection_point_mode": metric_meta.get("projection_point_mode"),
        "selected_component_count": metric_meta.get("selected_component_count"),
        "envelope_candidate_count": metric_meta.get("envelope_candidate_count"),
        "side_guard_foreground_area": metric_meta.get("side_guard_foreground_area"),
        "envelope_support_px": metric_meta.get("envelope_support_px"),
        "axis_offset_px": metric_meta.get("axis_offset_px"),
        "reason": metric_meta.get("reason"),
        "observation_selection_mode": metric_meta.get("observation_selection_mode"),
        "observation_reason": metric_meta.get("observation_reason"),
        "component_area": metric_meta.get("component_area"),
        "threshold_value": metric_meta.get("threshold_value"),
        "endpoint_jump_px": metric_meta.get("endpoint_jump_px"),
        "midpoint_drift_px": metric_meta.get("midpoint_drift_px"),
        "midpoint_along_shift_px": metric_meta.get("midpoint_along_shift_px"),
        "midpoint_lateral_drift_px": metric_meta.get("midpoint_lateral_drift_px"),
        "span_change_px": metric_meta.get("span_change_px"),
        "span_change_ratio": metric_meta.get("span_change_ratio"),
        "max_frame_span_jump_px": metric_meta.get("max_frame_span_jump_px"),
        "max_soft_frame_span_jump_px": metric_meta.get("max_soft_frame_span_jump_px"),
        "consecutive_misses": metric_meta.get("consecutive_misses"),
        "frame_read_ms": metric_meta.get("frame_read_ms"),
        "temp_read_ms": metric_meta.get("temp_read_ms"),
        "metric_extract_ms": metric_meta.get("metric_extract_ms"),
        "sample_loop_ms": metric_meta.get("sample_loop_ms"),
        "telemetry_row_ms": metric_meta.get("telemetry_row_ms"),
        "sample_callbacks_ms": metric_meta.get("sample_callbacks_ms"),
        "post_sample_ms": metric_meta.get("post_sample_ms"),
    }


def _metric_meta_point(meta: dict[str, Any], key: str) -> list[int] | None:
    payload = meta.get(key)
    if not isinstance(payload, (list, tuple)) or len(payload) != 2:
        return None
    try:
        return [int(payload[0]), int(payload[1])]
    except (TypeError, ValueError):
        return None


def _rate_snapshot_payload(rate_snapshot: RunRateSnapshot) -> dict[str, Any]:
    return {
        "camera_resulting_fps": rate_snapshot.camera_resulting_fps,
        "preview_display_fps": rate_snapshot.preview_display_fps,
        "measurement_sample_hz": rate_snapshot.measurement_sample_hz,
        "artifact_capture_hz": rate_snapshot.artifact_capture_hz,
        "dropped_frame_count": rate_snapshot.dropped_frame_count,
    }


def _measurement_profile_payload(profile: MeasurementProfileSnapshot) -> dict[str, Any]:
    roi = profile.acquisition_roi
    return {
        "acquisition_roi": None
        if roi is None
        else {
            "x": roi.x,
            "y": roi.y,
            "width": roi.width,
            "height": roi.height,
        },
        "decimation": profile.decimation,
        "binning": profile.binning,
        "exposure_us": profile.exposure_us,
    }


def _sample_rate_hz(timestamps_ms: list[int]) -> float | None:
    if len(timestamps_ms) < 2:
        return None
    span_ms = timestamps_ms[-1] - timestamps_ms[0]
    if span_ms <= 0:
        return None
    return ((len(timestamps_ms) - 1) * 1000.0) / span_ms


def resolve_measurement_interval_ms(
    run_config: Any,
    *,
    playback_sample_count: int | None = None,
    stop_on_target_reached: bool = True,
) -> int:
    target_hz = getattr(run_config, "measurement_target_hz", None)
    if target_hz is not None:
        resolved_hz = float(target_hz)
        if resolved_hz > 0:
            return max(1, int(round(1000.0 / resolved_hz)))
    return max(int(getattr(run_config, "capture_interval_ms", 1) or 1), 1)


def _camera_resulting_fps(sync_points: list[SyncPoint], telemetry: list[dict[str, Any]]) -> float | None:
    for sync_point in reversed(sync_points):
        value = _frame_resulting_fps(sync_point.frame)
        if value is not None:
            return value
    for item in reversed(telemetry):
        value = item.get("camera_resulting_fps")
        if value is not None:
            return float(value)
    return None


def _dropped_frame_count(sync_points: list[SyncPoint], telemetry: list[dict[str, Any]]) -> int:
    frame_ids = [
        int(sync_point.frame.frame_id)
        for sync_point in sync_points
        if sync_point.frame is not None and sync_point.frame.frame_id is not None
    ]
    if not frame_ids:
        frame_ids = [int(item["frame_id"]) for item in telemetry if item.get("frame_id") is not None]
    if len(frame_ids) < 2:
        return 0
    expected = frame_ids[-1] - frame_ids[0] + 1
    return max(0, expected - len(frame_ids))


def summarize_rate_warnings(
    rate_snapshot: RunRateSnapshot,
    *,
    target_measurement_hz: float | None,
    is_terminal: bool,
) -> list[str]:
    warnings: list[str] = []
    if target_measurement_hz is not None and rate_snapshot.measurement_sample_hz is None and is_terminal:
        warnings.append("measurement cadence unavailable for this run")
    if (
        target_measurement_hz is not None
        and rate_snapshot.measurement_sample_hz is not None
        and rate_snapshot.measurement_sample_hz + 1e-9 < (float(target_measurement_hz) * 0.95)
    ):
        warnings.append(
            "measurement cadence below target: "
            f"achieved {rate_snapshot.measurement_sample_hz:.2f} Hz < target {float(target_measurement_hz):.2f} Hz"
        )
    if rate_snapshot.dropped_frame_count > 0:
        warnings.append(f"measurement dropped frames detected: {rate_snapshot.dropped_frame_count}")
    return warnings


def _frame_resulting_fps(frame: FramePacket | None) -> float | None:
    if frame is None:
        return None
    for key in ("camera_resulting_fps", "resulting_frame_rate", "resulting_fps"):
        value = frame.meta.get(key)
        if value is not None:
            return float(value)
    return None


def _resolved_timestamp_ms(value: int | None, *, fallback_ms: int) -> int:
    if value is None:
        return int(fallback_ms)
    resolved = int(value)
    return resolved if resolved > 0 else int(fallback_ms)


def _resolve_playback_sample_count(*sources: object) -> int | None:
    for source in sources:
        accessor = getattr(source, "playback_sample_count", None)
        if not callable(accessor):
            continue
        resolved = int(accessor())
        if resolved > 0:
            return resolved
    return None


def _points_for_projected_span(
    *,
    frame: FramePacket,
    center_x: float,
    center_y: float,
    unit_x: float,
    unit_y: float,
    span_px: float,
) -> tuple[tuple[int, int], tuple[int, int]]:
    half_span = max(float(span_px), 2.0) / 2.0
    point_a_x = center_x - unit_x * half_span
    point_a_y = center_y - unit_y * half_span
    point_b_x = center_x + unit_x * half_span
    point_b_y = center_y + unit_y * half_span

    max_x, max_y = _frame_max_xy(
        frame,
        fallback_x=int(round(center_x)),
        fallback_y=int(round(center_y)),
    )
    point_a = (
        int(max(0, min(max_x, round(point_a_x)))),
        int(max(0, min(max_y, round(point_a_y)))),
    )
    point_b = (
        int(max(0, min(max_x, round(point_b_x)))),
        int(max(0, min(max_y, round(point_b_y)))),
    )
    return point_a, point_b


def _frame_max_xy(frame: FramePacket, *, fallback_x: int, fallback_y: int) -> tuple[int, int]:
    image = frame.image
    shape = getattr(image, "shape", None)
    if shape is not None and len(shape) >= 2:
        height = int(shape[0])
        width = int(shape[1])
        if width > 0 and height > 0:
            return width - 1, height - 1
    if image is None:
        return int(fallback_x), int(fallback_y)
    try:
        height = len(image)
        width = len(image[0]) if height > 0 else 0
    except (TypeError, ValueError):
        return int(fallback_x), int(fallback_y)
    if width > 0 and height > 0:
        return int(width) - 1, int(height) - 1
    return int(fallback_x), int(fallback_y)


def _event(timestamp_ms: int, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_ms": timestamp_ms,
        "type": event_type,
        "payload": payload,
    }


def _shape_metric_point(value: tuple[int, int] | None) -> PixelPoint | None:
    if value is None:
        return None
    return PixelPoint(x=int(value[0]), y=int(value[1]))


def _metric_endpoint_border_touch_count(metric: ShapeMetric, roi: RectRegion) -> int:
    points = (_shape_metric_point(metric.point_a_px), _shape_metric_point(metric.point_b_px))
    if any(point is None for point in points):
        return 2
    margin = max(1, int(round(float(min(roi.width, roi.height)) * 0.015)))
    left = int(roi.x) + margin
    right = int(roi.x + roi.width) - 1 - margin
    top = int(roi.y) + margin
    bottom = int(roi.y + roi.height) - 1 - margin
    touches = 0
    for point in points:
        assert point is not None
        if point.x <= left or point.x >= right or point.y <= top or point.y >= bottom:
            touches += 1
    return min(2, touches)


def _midpoint(point_a: PixelPoint, point_b: PixelPoint) -> PixelPoint:
    return PixelPoint(
        x=int(round((point_a.x + point_b.x) / 2)),
        y=int(round((point_a.y + point_b.y) / 2)),
    )


def _point_distance(point_a: PixelPoint, point_b: PixelPoint) -> float:
    return math.hypot(float(point_b.x - point_a.x), float(point_b.y - point_a.y))


def _limited_axis_endpoint(
    *,
    previous: PixelPoint,
    observed: PixelPoint,
    direction: tuple[float, float],
    max_step_px: float,
) -> PixelPoint:
    direction_x, direction_y = direction
    delta_x = float(observed.x - previous.x)
    delta_y = float(observed.y - previous.y)
    along_delta = delta_x * direction_x + delta_y * direction_y
    limited_delta = max(-float(max_step_px), min(float(max_step_px), along_delta))
    return PixelPoint(
        x=int(round(float(previous.x) + direction_x * limited_delta)),
        y=int(round(float(previous.y) + direction_y * limited_delta)),
    )


def _unit_vector(point_a: PixelPoint, point_b: PixelPoint) -> tuple[float, float]:
    distance = _point_distance(point_a, point_b)
    if distance <= 0:
        return 1.0, 0.0
    return (float(point_b.x - point_a.x) / distance, float(point_b.y - point_a.y) / distance)


def _select_key_frames(sync_points: list[SyncPoint]) -> list[dict[str, Any]]:
    frame_points = [point for point in sync_points if point.frame is not None and point.metric is not None]
    if not frame_points:
        return []

    indexed_points: list[tuple[str, SyncPoint]] = [("first", frame_points[0])]
    if len(frame_points) > 2:
        indexed_points.append(("middle", frame_points[len(frame_points) // 2]))
    if len(frame_points) > 1:
        indexed_points.append(("last", frame_points[-1]))

    key_frames: list[dict[str, Any]] = []
    seen_timestamps: set[tuple[str, int]] = set()
    for label, sync_point in indexed_points:
        if sync_point.frame is None or sync_point.metric is None:
            continue
        marker = (label, sync_point.timestamp_ms)
        if marker in seen_timestamps:
            continue
        seen_timestamps.add(marker)
        key_frames.append(
            {
                "label": label,
                "timestamp_ms": sync_point.timestamp_ms,
                "image": sync_point.frame.image,
                "feature_point_px": list(sync_point.metric.feature_point_px)
                if sync_point.metric.feature_point_px is not None
                else None,
                "metric_raw": sync_point.metric.metric_raw,
            }
        )
    return key_frames


def _keyframe_artifact_refs(key_frames: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for key_frame in key_frames:
        label = str(key_frame.get("label", "") or "").strip()
        image = key_frame.get("image")
        if not label or image is None:
            continue
        refs.append(f"keyframes/{label}.png")
    return refs


def _now_ms() -> int:
    return int(time.time() * 1000)
