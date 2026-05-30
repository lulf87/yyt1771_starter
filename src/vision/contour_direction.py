"""Contour-based directional span extraction for live setup."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from src.core.contracts import VisionMetricExtractor
from src.core.models import (
    FramePacket,
    MetricBox,
    PixelPoint,
    RectRegion,
    ShapeMetric,
    resolve_envelope_min_support_px,
)


@dataclass(slots=True)
class DirectionalContourConfig:
    analysis_roi: RectRegion
    direction_angle_deg: float
    metric_box: MetricBox | None = None
    foreground_polarity: str = "dark_on_light"
    threshold_mode: str = "adaptive"
    threshold_value: float | None = None
    min_target_area_px: int = 200
    sensitivity: float = 50.0
    ignore_internal_texture: bool = False
    component_bridge_kernel: int = 11
    open_kernel: int = 1
    projection_mode: str = "max_chord"
    target_geometry_mode: str = "single_component"
    side_guard_ratio: float = 0.0
    envelope_min_support_px: int = 3
    envelope_quantile: float = 0.0
    envelope_normal_bin_width_px: float = 5.0
    envelope_lateral_window_bins: int = 1
    envelope_endpoint_support_radius_px: float = 3.0
    envelope_endpoint_min_support_px: int = 3
    envelope_axis_prior_px: float | None = None
    envelope_axis_prior_tolerance_px: float | None = None
    max_chord_axis_prior_point: PixelPoint | None = None
    max_chord_axis_prior_tolerance_px: float | None = None
    max_chord_prior_point_a: PixelPoint | None = None
    max_chord_prior_point_b: PixelPoint | None = None
    max_chord_prior_endpoint_tolerance_px: float | None = None
    processing_max_side_px: int = 384


@dataclass(slots=True)
class DirectionalProjection:
    point_a: PixelPoint
    point_b: PixelPoint
    source_point_a: PixelPoint
    source_point_b: PixelPoint
    axis_point_a: PixelPoint
    axis_point_b: PixelPoint
    metric_raw: float
    direction_angle_deg: float
    axis_offset_px: float
    envelope_support_px: int | None = None
    envelope_candidate_count: int | None = None
    side_guard_foreground_area: int | None = None
    endpoint_support_left_px: int | None = None
    endpoint_support_right_px: int | None = None
    selected_candidate_score: float | None = None
    candidate_reject_reason: str | None = None


@dataclass(slots=True)
class DirectionalContourResult:
    point_a: PixelPoint
    point_b: PixelPoint
    source_point_a: PixelPoint
    source_point_b: PixelPoint
    axis_point_a: PixelPoint
    axis_point_b: PixelPoint
    metric_raw: float
    quality: float
    roi: RectRegion
    direction_angle_deg: float
    component_area: int
    contour_xy: np.ndarray
    component_mask: np.ndarray
    threshold_value: float | None
    projection_point_mode: str
    raw_component_fill_ratio: float | None = None
    target_geometry_mode: str = "single_component"
    selected_component_count: int = 1
    rejected_component_count: int = 0
    envelope_candidate_count: int | None = None
    side_guard_foreground_area: int | None = None
    envelope_support_px: int | None = None
    axis_offset_px: float | None = None
    endpoint_support_left_px: int | None = None
    endpoint_support_right_px: int | None = None
    selected_candidate_score: float | None = None
    envelope_reject_reason: str | None = None
    configured_envelope_min_support_px: int | None = None
    effective_envelope_min_support_px: int | None = None
    resolved_measurement_angle_deg: float | None = None
    metric_box_angle_deg: float | None = None
    angle_delta_deg: float | None = None
    angle_mismatch_warning: bool = False


class DirectionalContourDetectionError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(slots=True)
class _ProcessingGeometry:
    crop: np.ndarray
    original_roi: RectRegion
    scale_x: float = 1.0
    scale_y: float = 1.0

    @property
    def roi(self) -> RectRegion:
        return RectRegion(x=0, y=0, width=int(self.crop.shape[1]), height=int(self.crop.shape[0]))

    @property
    def scale(self) -> float:
        return (float(self.scale_x) + float(self.scale_y)) / 2.0


class DirectionalContourMetricExtractor(VisionMetricExtractor):
    def __init__(self, config: DirectionalContourConfig) -> None:
        self.config = config

    def extract(self, frame: FramePacket) -> ShapeMetric:
        try:
            result = detect_directional_contour(frame.image, self.config)
        except DirectionalContourDetectionError as exc:
            return ShapeMetric(
                timestamp_ms=frame.timestamp_ms,
                metric_name="directional_contour_span",
                metric_raw=None,
                quality=0.0,
                roi=_roi_tuple(self.config.analysis_roi),
                meta={
                    "reason": exc.reason,
                    "direction_angle_deg": float(self.config.direction_angle_deg),
                },
            )

        meta: dict[str, Any] = {
            "direction_angle_deg": float(result.direction_angle_deg),
            "resolved_measurement_angle_deg": (
                None
                if result.resolved_measurement_angle_deg is None
                else float(result.resolved_measurement_angle_deg)
            ),
            "metric_box_angle_deg": (
                None if result.metric_box_angle_deg is None else float(result.metric_box_angle_deg)
            ),
            "angle_delta_deg": (
                None if result.angle_delta_deg is None else float(result.angle_delta_deg)
            ),
            "angle_mismatch_warning": bool(result.angle_mismatch_warning),
            "component_area": int(result.component_area),
            "threshold_value": result.threshold_value,
            "raw_component_fill_ratio": result.raw_component_fill_ratio,
            "target_geometry_mode": result.target_geometry_mode,
            "projection_point_mode": result.projection_point_mode,
            "selection_mode": _selection_mode_for_projection(result.projection_point_mode),
            "selected_component_count": result.selected_component_count,
            "rejected_component_count": result.rejected_component_count,
            "envelope_candidate_count": result.envelope_candidate_count,
            "side_guard_foreground_area": result.side_guard_foreground_area,
            "envelope_support_px": result.envelope_support_px,
            "endpoint_support_left_px": result.endpoint_support_left_px,
            "endpoint_support_right_px": result.endpoint_support_right_px,
            "selected_candidate_score": result.selected_candidate_score,
            "selected_candidate_span": result.metric_raw,
            "selected_candidate_axis_offset": result.axis_offset_px,
            "envelope_reject_reason": result.envelope_reject_reason,
            "axis_offset_px": result.axis_offset_px,
        }
        if result.projection_point_mode == "envelope_max_width":
            # The displayed A/B is axis-projected; the foreground support points are
            # surfaced separately for debug overlays and must never be drawn as the
            # final A/B segment.
            meta.update(
                {
                    "source_point_a_px": (result.source_point_a.x, result.source_point_a.y),
                    "source_point_b_px": (result.source_point_b.x, result.source_point_b.y),
                    "axis_point_a_px": (result.axis_point_a.x, result.axis_point_a.y),
                    "axis_point_b_px": (result.axis_point_b.x, result.axis_point_b.y),
                    "display_point_mode": "axis_projected",
                    "source_point_mode": "foreground_support",
                    "metric_raw_mode": "along_axis_span",
                    "configured_envelope_min_support_px": result.configured_envelope_min_support_px,
                    "effective_envelope_min_support_px": result.effective_envelope_min_support_px,
                }
            )
        return ShapeMetric(
            timestamp_ms=frame.timestamp_ms,
            metric_name="directional_contour_span",
            metric_raw=result.metric_raw,
            quality=result.quality,
            roi=_roi_tuple(result.roi),
            point_a_px=(result.point_a.x, result.point_a.y),
            point_b_px=(result.point_b.x, result.point_b.y),
            meta=meta,
        )


def detect_directional_contour(image: Any, config: DirectionalContourConfig) -> DirectionalContourResult:
    gray = _normalize_gray_image(image)
    roi = _clip_roi(config.analysis_roi, gray.shape)
    crop = gray[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width]
    if crop.size == 0:
        raise DirectionalContourDetectionError("roi_outside_image")

    # The rotated metric box angle is the authoritative measurement direction.
    # ``direction_angle_deg`` is a compatibility field; if a caller passes a stale
    # value while a metric box is present we self-heal to the box angle and warn,
    # so a rotated ROI is always measured along its own angle.
    configured_angle_deg = float(config.direction_angle_deg)
    metric_box_angle_deg = None if config.metric_box is None else float(config.metric_box.angle_deg)
    resolved_angle_deg = metric_box_angle_deg if metric_box_angle_deg is not None else configured_angle_deg
    angle_delta_deg = abs(resolved_angle_deg - configured_angle_deg)
    angle_mismatch_warning = angle_delta_deg > 0.5

    cv2 = _try_import_cv2()
    processing = _prepare_processing_geometry(cv2, crop, roi, config)
    crop = processing.crop
    processing_roi = processing.roi
    mask, threshold_value = _threshold_mask(cv2, crop, config)
    allowed_mask = _processing_metric_box_mask(cv2, processing, config.metric_box)
    if allowed_mask is not None:
        mask = _apply_allowed_mask(cv2, mask, allowed_mask)
    source_mask = _source_foreground_mask(cv2, crop, mask, threshold_value, config)
    if allowed_mask is not None:
        source_mask = _apply_allowed_mask(cv2, source_mask, allowed_mask)
    raw_mask = mask
    projection_mode = str(config.projection_mode or "max_chord")
    mask = _cleanup_mask(cv2, mask, config)
    target_geometry_mode = str(config.target_geometry_mode or "single_component")
    selected_component_count = 1
    rejected_component_count = 0
    envelope_candidate_count: int | None = None
    side_guard_foreground_area: int | None = None
    envelope_support_px: int | None = None
    endpoint_support_left_px: int | None = None
    endpoint_support_right_px: int | None = None
    selected_candidate_score: float | None = None
    envelope_reject_reason: str | None = None
    configured_envelope_min_support_px: int | None = None
    effective_envelope_min_support_px: int | None = None
    if projection_mode == "envelope_max_width":
        component_mask, selected_component_count, rejected_component_count = _envelope_target_mask(
            mask,
            config,
            cv2=cv2,
        )
        raw_component_fill_ratio = _component_foreground_fill_ratio(raw_mask, component_mask)
        boundary_mask = _actual_component_boundary_mask(source_mask, component_mask)
        scale = max(float(processing.scale), 1e-6)
        projection = measure_component_envelope_max_width(
            boundary_mask,
            processing_roi,
            resolved_angle_deg,
            image_shape=gray.shape,
            clip_region=processing_roi,
            allowed_mask=allowed_mask,
            side_guard_ratio=float(config.side_guard_ratio),
            normal_bin_width_px=max(0.5, float(config.envelope_normal_bin_width_px) * scale),
            lateral_window_bins=int(config.envelope_lateral_window_bins),
            min_support_px=int(config.envelope_min_support_px),
            geometry_min_support_px=resolve_envelope_min_support_px(
                target_geometry_mode,
                int(config.envelope_min_support_px),
            ),
            quantile=float(config.envelope_quantile),
            endpoint_support_radius_px=max(0.0, float(config.envelope_endpoint_support_radius_px) * scale),
            endpoint_min_support_px=int(config.envelope_endpoint_min_support_px),
            axis_prior_px=(
                None
                if config.envelope_axis_prior_px is None
                else _axis_offset_to_processing_space(
                    float(config.envelope_axis_prior_px),
                    processing,
                    resolved_angle_deg,
                )
            ),
            axis_prior_tolerance_px=(
                None
                if config.envelope_axis_prior_tolerance_px is None
                else float(config.envelope_axis_prior_tolerance_px) * scale
            ),
        )
        projection_point_mode = "envelope_max_width"
        envelope_candidate_count = projection.envelope_candidate_count
        side_guard_foreground_area = projection.side_guard_foreground_area
        envelope_support_px = projection.envelope_support_px
        endpoint_support_left_px = projection.endpoint_support_left_px
        endpoint_support_right_px = projection.endpoint_support_right_px
        selected_candidate_score = projection.selected_candidate_score
        envelope_reject_reason = projection.candidate_reject_reason
        configured_envelope_min_support_px = int(config.envelope_min_support_px)
        effective_envelope_min_support_px = int(
            resolve_envelope_min_support_px(
                target_geometry_mode,
                int(config.envelope_min_support_px),
            )
        )
        contour_xy = _component_boundary_xy_numpy(boundary_mask, processing_roi)
    else:
        component_mask = _largest_component_mask(
            cv2,
            mask,
            min_target_area_px=int(config.min_target_area_px),
            direction_angle_deg=resolved_angle_deg,
            component_bridge_kernel=int(config.component_bridge_kernel),
        )
        raw_component_fill_ratio = _component_foreground_fill_ratio(raw_mask, component_mask)
        boundary_mask = _actual_component_boundary_mask(source_mask, component_mask)
        contour_xy = _component_contour_xy(cv2, boundary_mask, processing_roi)
        selected_component_count = 1
    if projection_mode == "auto":
        projection_mode = choose_component_direction_projection_mode(
            boundary_mask,
            processing_roi,
            resolved_angle_deg,
            raw_component_fill_ratio=raw_component_fill_ratio if config.ignore_internal_texture else None,
        )
    if projection_mode == "envelope_max_width":
        pass
    elif projection_mode == "mask_projection":
        axis_prior_px = _max_chord_axis_prior_lateral_px(config, processing)
        axis_prior_tolerance_px = _max_chord_axis_prior_tolerance_px(config, processing)
        projection = project_component_mask_onto_direction(
            boundary_mask,
            processing_roi,
            resolved_angle_deg,
            image_shape=gray.shape,
            clip_region=processing_roi,
            axis_offset_px=axis_prior_px,
            axis_tolerance_px=axis_prior_tolerance_px,
        )
        projection_point_mode = "mask_projection"
    elif projection_mode == "max_chord":
        lateral_prior_px = _max_chord_axis_prior_lateral_px(config, processing)
        lateral_prior_tolerance_px = _max_chord_axis_prior_tolerance_px(config, processing)
        endpoint_prior_a = _max_chord_prior_point(config.max_chord_prior_point_a, processing)
        endpoint_prior_b = _max_chord_prior_point(config.max_chord_prior_point_b, processing)
        endpoint_prior_tolerance_px = _max_chord_endpoint_prior_tolerance_px(config, processing)
        projection = measure_component_max_chord_along_direction(
            boundary_mask,
            processing_roi,
            resolved_angle_deg,
            image_shape=gray.shape,
            clip_region=processing_roi,
            lateral_prior_px=lateral_prior_px,
            lateral_prior_tolerance_px=lateral_prior_tolerance_px,
            endpoint_prior_a=endpoint_prior_a,
            endpoint_prior_b=endpoint_prior_b,
            endpoint_prior_tolerance_px=endpoint_prior_tolerance_px,
        )
        projection_point_mode = "max_chord"
    else:
        raise DirectionalContourDetectionError("unsupported_direction_projection_mode")
    projection = _projection_to_original_roi(projection, processing, image_shape=gray.shape)
    projection = _refine_projection_on_original_axis(
        cv2,
        gray,
        roi,
        config,
        processing,
        projection,
        projection_point_mode=projection_point_mode,
    )
    if projection_point_mode == "envelope_max_width":
        # Guarantee the displayed A/B is strictly parallel to the measurement
        # direction by re-projecting both endpoints onto the same axis line in
        # original-image coordinates. The foreground support points are kept
        # untouched (debug only); the metric is the along-axis span.
        projection = _project_envelope_endpoints_onto_axis(
            projection,
            resolved_angle_deg,
            image_shape=gray.shape,
        )
    contour_xy = _contour_to_original_roi(contour_xy, processing)

    component_area = int(round(float(np.count_nonzero(component_mask)) / max(processing.scale_x * processing.scale_y, 1e-9)))
    quality = _quality_score(
        metric_raw=projection.metric_raw,
        component_area=component_area,
        roi=roi,
        metric_box=config.metric_box,
    )
    return DirectionalContourResult(
        point_a=projection.point_a,
        point_b=projection.point_b,
        source_point_a=projection.source_point_a,
        source_point_b=projection.source_point_b,
        axis_point_a=projection.axis_point_a,
        axis_point_b=projection.axis_point_b,
        metric_raw=projection.metric_raw,
        quality=quality,
        roi=roi,
        direction_angle_deg=resolved_angle_deg,
        component_area=component_area,
        contour_xy=contour_xy,
        component_mask=component_mask,
        threshold_value=threshold_value,
        projection_point_mode=projection_point_mode,
        raw_component_fill_ratio=raw_component_fill_ratio,
        target_geometry_mode=target_geometry_mode,
        selected_component_count=selected_component_count,
        rejected_component_count=rejected_component_count,
        envelope_candidate_count=envelope_candidate_count,
        side_guard_foreground_area=side_guard_foreground_area,
        envelope_support_px=envelope_support_px,
        endpoint_support_left_px=endpoint_support_left_px,
        endpoint_support_right_px=endpoint_support_right_px,
        selected_candidate_score=selected_candidate_score,
        envelope_reject_reason=envelope_reject_reason,
        configured_envelope_min_support_px=configured_envelope_min_support_px,
        effective_envelope_min_support_px=effective_envelope_min_support_px,
        axis_offset_px=float(projection.axis_offset_px),
        resolved_measurement_angle_deg=resolved_angle_deg,
        metric_box_angle_deg=metric_box_angle_deg,
        angle_delta_deg=angle_delta_deg,
        angle_mismatch_warning=angle_mismatch_warning,
    )


def _project_envelope_endpoints_onto_axis(
    projection: DirectionalProjection,
    angle_deg: float,
    *,
    image_shape: tuple[int, ...],
) -> DirectionalProjection:
    """Pin both endpoints to one axis line so A/B is parallel to ``angle_deg``.

    Works in the final (original-image) coordinate space. Each endpoint keeps its
    own along-direction coordinate but shares a single lateral offset, so the
    resulting A/B segment is collinear with the measurement direction. The metric
    becomes the absolute along-axis span and the source foreground points are
    preserved unchanged for debugging.
    """
    direction = directional_unit_vector(float(angle_deg))
    normal = np.array([-direction[1], direction[0]], dtype=float)
    point_a_xy = np.array([float(projection.point_a.x), float(projection.point_a.y)], dtype=float)
    point_b_xy = np.array([float(projection.point_b.x), float(projection.point_b.y)], dtype=float)
    along_a = float(point_a_xy @ direction)
    along_b = float(point_b_xy @ direction)
    axis_offset = float(projection.axis_offset_px)
    axis_a_xy = direction * along_a + normal * axis_offset
    axis_b_xy = direction * along_b + normal * axis_offset
    axis_point_a = _pixel_point_from_xy(axis_a_xy, image_shape=image_shape)
    axis_point_b = _pixel_point_from_xy(axis_b_xy, image_shape=image_shape)
    return replace(
        projection,
        point_a=axis_point_a,
        point_b=axis_point_b,
        axis_point_a=axis_point_a,
        axis_point_b=axis_point_b,
        metric_raw=abs(along_b - along_a),
        direction_angle_deg=float(angle_deg),
    )


def project_points_onto_direction(
    points_xy: np.ndarray,
    angle_deg: float,
    *,
    image_shape: tuple[int, ...] | None = None,
    clip_region: RectRegion | None = None,
    lateral_offset_px: float = 0.0,
    axis_offset_px: float | None = None,
) -> DirectionalProjection:
    points = np.asarray(points_xy, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        raise DirectionalContourDetectionError("direction_projection_unavailable")
    finite = np.isfinite(points).all(axis=1)
    points = points[finite]
    if len(points) == 0:
        raise DirectionalContourDetectionError("direction_projection_unavailable")

    direction = directional_unit_vector(float(angle_deg))
    normal = np.array([-direction[1], direction[0]], dtype=float)
    projections = points @ direction
    normal_coords = points @ normal
    min_index = int(np.argmin(projections))
    max_index = _max_projection_display_index(projections, normal_coords)
    min_projection = float(projections[min_index])
    max_projection = float(projections[max_index])
    axis_offset = (
        float(axis_offset_px)
        if axis_offset_px is not None
        else float(np.median(normal_coords) + lateral_offset_px)
    )

    source_point_a = _pixel_point_from_xy(points[min_index], image_shape=image_shape, clip_region=clip_region)
    source_point_b = _pixel_point_from_xy(points[max_index], image_shape=image_shape, clip_region=clip_region)
    return DirectionalProjection(
        point_a=source_point_a,
        point_b=source_point_b,
        source_point_a=source_point_a,
        source_point_b=source_point_b,
        axis_point_a=source_point_a,
        axis_point_b=source_point_b,
        metric_raw=_distance_between(source_point_a, source_point_b),
        direction_angle_deg=float(angle_deg),
        axis_offset_px=axis_offset,
    )


def project_component_mask_onto_direction(
    component_mask: np.ndarray,
    roi: RectRegion,
    angle_deg: float,
    *,
    image_shape: tuple[int, ...] | None = None,
    clip_region: RectRegion | None = None,
    normal_bin_width_px: float = 1.0,
    near_max_span_ratio: float = 0.98,
    axis_offset_px: float | None = None,
    axis_tolerance_px: float | None = None,
) -> DirectionalProjection:
    return measure_component_max_chord_along_direction(
        component_mask,
        roi,
        angle_deg,
        image_shape=image_shape,
        clip_region=clip_region,
        normal_bin_width_px=normal_bin_width_px,
        lateral_prior_px=axis_offset_px,
        lateral_prior_tolerance_px=axis_tolerance_px,
    )


def measure_component_max_chord_along_direction(
    component_mask: np.ndarray,
    roi: RectRegion,
    angle_deg: float,
    *,
    image_shape: tuple[int, ...] | None = None,
    clip_region: RectRegion | None = None,
    normal_bin_width_px: float = 1.0,
    lateral_prior_px: float | None = None,
    lateral_prior_tolerance_px: float | None = None,
    endpoint_prior_a: np.ndarray | None = None,
    endpoint_prior_b: np.ndarray | None = None,
    endpoint_prior_tolerance_px: float | None = None,
) -> DirectionalProjection:
    rows, cols = np.where(np.asarray(component_mask) > 0)
    if len(rows) == 0:
        raise DirectionalContourDetectionError("direction_projection_unavailable")
    points = np.column_stack([cols + int(roi.x), rows + int(roi.y)]).astype(float)
    direction = directional_unit_vector(float(angle_deg))
    normal = np.array([-direction[1], direction[0]], dtype=float)
    along = points @ direction
    lateral = points @ normal
    bin_width = max(0.5, float(normal_bin_width_px))
    median_lateral = float(np.median(lateral))
    bin_anchor = float(lateral_prior_px) if lateral_prior_px is not None else median_lateral
    bin_indices = np.round((lateral - bin_anchor) / bin_width).astype(np.int64)

    best: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = []
    for bin_index in np.unique(bin_indices):
        indices = np.flatnonzero(bin_indices == bin_index)
        if len(indices) < 2:
            continue
        ordered = indices[np.argsort(along[indices])]
        ordered_along = along[ordered]
        span = float(ordered_along[-1] - ordered_along[0])
        if span <= 0.0:
            continue
        min_index = int(ordered[0])
        max_index = int(ordered[-1])
        axis_offset = float(np.median(lateral[ordered]))
        endpoint_prior_distance = _max_chord_endpoint_prior_distance(
            points[min_index],
            points[max_index],
            endpoint_prior_a,
            endpoint_prior_b,
        )
        candidate = {
            "span": span,
            "count": int(len(ordered)),
            "axis_offset": axis_offset,
            "min_index": min_index,
            "max_index": max_index,
            "center_distance": abs(axis_offset - median_lateral),
            "prior_distance": None if lateral_prior_px is None else abs(axis_offset - float(lateral_prior_px)),
            "endpoint_prior_distance": endpoint_prior_distance,
            "endpoint_prior_within": _max_chord_endpoint_prior_within(
                endpoint_prior_distance,
                endpoint_prior_tolerance_px,
            ),
        }
        candidates.append(candidate)
        if _max_chord_candidate_is_better(candidate, best):
            best = candidate

    if lateral_prior_px is not None and candidates:
        tolerance_px = (
            None
            if lateral_prior_tolerance_px is None
            else max(0.0, float(lateral_prior_tolerance_px))
        )
        prior_candidates = [
            candidate
            for candidate in candidates
            if tolerance_px is None or float(candidate["prior_distance"]) <= tolerance_px
        ]
        if prior_candidates:
            best = None
            for candidate in prior_candidates:
                if _max_chord_prior_candidate_is_better(candidate, best):
                    best = candidate

    if best is None:
        return project_points_onto_direction(points, angle_deg, image_shape=image_shape, clip_region=clip_region)

    axis_offset = float(best["axis_offset"])
    source_point_a = _pixel_point_from_xy(
        points[int(best["min_index"])],
        image_shape=image_shape,
        clip_region=clip_region,
    )
    source_point_b = _pixel_point_from_xy(
        points[int(best["max_index"])],
        image_shape=image_shape,
        clip_region=clip_region,
    )
    return DirectionalProjection(
        point_a=source_point_a,
        point_b=source_point_b,
        source_point_a=source_point_a,
        source_point_b=source_point_b,
        axis_point_a=source_point_a,
        axis_point_b=source_point_b,
        metric_raw=_distance_between(source_point_a, source_point_b),
        direction_angle_deg=float(angle_deg),
        axis_offset_px=axis_offset,
    )


def measure_component_envelope_max_width(
    component_mask: np.ndarray,
    roi: RectRegion,
    angle_deg: float,
    *,
    image_shape: tuple[int, ...] | None = None,
    clip_region: RectRegion | None = None,
    allowed_mask: np.ndarray | None = None,
    normal_bin_width_px: float = 1.0,
    lateral_window_bins: int = 0,
    side_guard_ratio: float = 0.0,
    min_support_px: int = 3,
    geometry_min_support_px: int | None = None,
    quantile: float = 0.0,
    endpoint_support_radius_px: float = 0.0,
    endpoint_min_support_px: int = 0,
    axis_prior_px: float | None = None,
    axis_prior_tolerance_px: float | None = None,
) -> DirectionalProjection:
    rows, cols = np.where(np.asarray(component_mask) > 0)
    if len(rows) == 0:
        raise DirectionalContourDetectionError("direction_projection_unavailable")

    points = np.column_stack([cols + int(roi.x), rows + int(roi.y)]).astype(float)
    direction = directional_unit_vector(float(angle_deg))
    normal = np.array([-direction[1], direction[0]], dtype=float)
    along = points @ direction
    lateral = points @ normal

    guard_area, keep_mask = _side_guard_keep_mask(
        points,
        roi,
        direction,
        allowed_mask=allowed_mask,
        side_guard_ratio=side_guard_ratio,
    )
    if not bool(np.any(keep_mask)):
        raise DirectionalContourDetectionError("direction_projection_unavailable")
    points = points[keep_mask]
    along = along[keep_mask]
    lateral = lateral[keep_mask]

    bin_width = max(0.5, float(normal_bin_width_px))
    median_lateral = float(np.median(lateral))
    bin_indices = np.round((lateral - median_lateral) / bin_width).astype(np.int64)
    effective_min_support = max(2, int(min_support_px))
    if geometry_min_support_px is not None:
        effective_min_support = max(effective_min_support, int(geometry_min_support_px))
    endpoint_quantile = max(0.0, min(0.20, float(quantile)))
    window = max(0, int(lateral_window_bins))
    endpoint_radius = max(0.0, float(endpoint_support_radius_px))
    endpoint_min_support = max(0, int(endpoint_min_support_px))

    endpoint_tree: cKDTree | None = None
    if endpoint_radius > 0.0 and endpoint_min_support > 0 and len(points) > 0:
        endpoint_tree = cKDTree(points)

    span_tolerance = max(3.0, bin_width)
    best: dict[str, Any] | None = None
    best_supported: dict[str, Any] | None = None
    candidate_count = 0
    unique_bins = np.unique(bin_indices)
    for bin_index in unique_bins:
        if window <= 0:
            window_mask = bin_indices == bin_index
        else:
            window_mask = np.abs(bin_indices - bin_index) <= window
        indices = np.flatnonzero(window_mask)
        support = int(len(indices))
        if support < effective_min_support:
            continue
        ordered = indices[np.argsort(along[indices])]
        ordered_along = along[ordered]
        low_value = float(np.quantile(ordered_along, endpoint_quantile))
        high_value = float(np.quantile(ordered_along, 1.0 - endpoint_quantile))
        span = high_value - low_value
        if span <= 0.0:
            continue
        low_index = int(ordered[int(np.argmin(np.abs(ordered_along - low_value)))])
        high_index = int(ordered[int(np.argmin(np.abs(ordered_along - high_value)))])
        if low_index == high_index:
            continue
        axis_offset = float(np.median(lateral[indices]))
        endpoint_support_left = support
        endpoint_support_right = support
        if endpoint_tree is not None:
            endpoint_support_left = int(len(endpoint_tree.query_ball_point(points[low_index], endpoint_radius)))
            endpoint_support_right = int(len(endpoint_tree.query_ball_point(points[high_index], endpoint_radius)))
        endpoints_supported = (
            endpoint_min_support <= 0
            or (
                endpoint_support_left >= endpoint_min_support
                and endpoint_support_right >= endpoint_min_support
            )
        )
        axis_jump = None if axis_prior_px is None else abs(axis_offset - float(axis_prior_px))
        score = _envelope_candidate_score(
            span=span,
            support=support,
            endpoint_support_left=endpoint_support_left,
            endpoint_support_right=endpoint_support_right,
            endpoint_min_support=endpoint_min_support,
            axis_jump=axis_jump,
            span_tolerance=span_tolerance,
            axis_prior_tolerance_px=axis_prior_tolerance_px,
        )
        candidate = {
            "span": span,
            "support": support,
            "axis_offset": axis_offset,
            "low_index": low_index,
            "high_index": high_index,
            "low_value": low_value,
            "high_value": high_value,
            "center_distance": abs(axis_offset - median_lateral),
            "endpoint_support_left": endpoint_support_left,
            "endpoint_support_right": endpoint_support_right,
            "endpoints_supported": endpoints_supported,
            "score": score,
        }
        candidate_count += 1
        if _envelope_candidate_is_better(candidate, best):
            best = candidate
        if endpoints_supported and _envelope_candidate_is_better(candidate, best_supported):
            best_supported = candidate

    reject_reason: str | None = None
    chosen = best_supported
    if chosen is None:
        chosen = best
        if chosen is not None:
            reject_reason = "weak_endpoint_support"
    if chosen is None:
        raise DirectionalContourDetectionError("direction_projection_unavailable")
    best = chosen

    # Foreground support points: the actual extreme pixels, kept for debug and
    # support verification only. They may sit on different filaments and are NOT
    # used as the final A/B display segment.
    source_point_a = _pixel_point_from_xy(
        points[int(best["low_index"])],
        image_shape=image_shape,
        clip_region=clip_region,
    )
    source_point_b = _pixel_point_from_xy(
        points[int(best["high_index"])],
        image_shape=image_shape,
        clip_region=clip_region,
    )
    # Axis-projected measurement points: same lateral (axis_offset), differing
    # only along the measurement direction, so A/B is strictly parallel to it.
    best_axis_offset = float(best["axis_offset"])
    axis_a_xy = direction * float(best["low_value"]) + normal * best_axis_offset
    axis_b_xy = direction * float(best["high_value"]) + normal * best_axis_offset
    axis_point_a = _pixel_point_from_xy(axis_a_xy, image_shape=image_shape, clip_region=clip_region)
    axis_point_b = _pixel_point_from_xy(axis_b_xy, image_shape=image_shape, clip_region=clip_region)
    return DirectionalProjection(
        point_a=axis_point_a,
        point_b=axis_point_b,
        source_point_a=source_point_a,
        source_point_b=source_point_b,
        axis_point_a=axis_point_a,
        axis_point_b=axis_point_b,
        metric_raw=float(best["high_value"]) - float(best["low_value"]),
        direction_angle_deg=float(angle_deg),
        axis_offset_px=best_axis_offset,
        envelope_support_px=int(best["support"]),
        envelope_candidate_count=int(candidate_count),
        side_guard_foreground_area=int(guard_area),
        endpoint_support_left_px=int(best.get("endpoint_support_left", best["support"])),
        endpoint_support_right_px=int(best.get("endpoint_support_right", best["support"])),
        selected_candidate_score=float(best.get("score", best["span"])),
        candidate_reject_reason=reject_reason,
    )


def _envelope_candidate_score(
    *,
    span: float,
    support: int,
    endpoint_support_left: int,
    endpoint_support_right: int,
    endpoint_min_support: int,
    axis_jump: float | None,
    span_tolerance: float,
    axis_prior_tolerance_px: float | None,
) -> float:
    """Composite candidate score for envelope_max_width selection.

    Span is the dominant term so the genuinely widest section still wins, but a
    candidate is rewarded for strong support, penalised for weak/asymmetric
    endpoint support, and (when a prior axis is supplied) penalised for jumping
    laterally so near-tie spans prefer to stay continuous with the prior axis.
    """
    support_bonus = min(float(support), 400.0) * 0.02
    weakest_endpoint = float(min(endpoint_support_left, endpoint_support_right))
    endpoint_penalty = 0.0
    if endpoint_min_support > 0:
        deficit = max(0.0, float(endpoint_min_support) - weakest_endpoint)
        endpoint_penalty = deficit * 2.0
    axis_penalty = 0.0
    if axis_jump is not None:
        # Only meaningful for near-tie spans: weight it so a lateral jump of a
        # few span_tolerances outweighs a sub-tolerance span gain.
        weight = 0.6
        if axis_prior_tolerance_px is not None and float(axis_prior_tolerance_px) > 0.0:
            within = float(axis_jump) <= float(axis_prior_tolerance_px)
            weight = 0.2 if within else 0.9
        axis_penalty = float(axis_jump) * weight
    return float(span) + support_bonus - endpoint_penalty - axis_penalty


def _envelope_candidate_is_better(candidate: dict[str, Any], current: dict[str, Any] | None) -> bool:
    if current is None:
        return True
    candidate_score = float(candidate.get("score", candidate["span"]))
    current_score = float(current.get("score", current["span"]))
    score_delta = candidate_score - current_score
    if abs(score_delta) > 1e-9:
        return score_delta > 0.0
    span_delta = float(candidate["span"]) - float(current["span"])
    if abs(span_delta) > 1e-9:
        return span_delta > 0.0
    support_delta = int(candidate["support"]) - int(current["support"])
    if support_delta != 0:
        return support_delta > 0
    return float(candidate["center_distance"]) < float(current["center_distance"])


def choose_component_direction_projection_mode(
    component_mask: np.ndarray,
    roi: RectRegion,
    angle_deg: float,
    *,
    raw_component_fill_ratio: float | None = None,
) -> str:
    """Choose wire-style or wide-contour directional measurement from shape cues."""
    rows, cols = np.where(np.asarray(component_mask) > 0)
    if len(rows) < 2:
        return "mask_projection"
    if raw_component_fill_ratio is not None and float(raw_component_fill_ratio) <= 0.65:
        return "mask_projection"

    points = np.column_stack([cols, rows]).astype(float)
    area = float(len(points))
    bbox_width = float(np.max(cols) - np.min(cols) + 1)
    bbox_height = float(np.max(rows) - np.min(rows) + 1)
    bbox_fill_ratio = area / max(bbox_width * bbox_height, 1.0)
    pca_aspect_ratio = _component_pca_aspect_ratio(points)
    max_inscribed_diameter = float(ndimage.distance_transform_edt(np.asarray(component_mask) > 0).max() * 2.0)

    try:
        global_projection = project_component_mask_onto_direction(component_mask, roi, angle_deg)
        max_chord_projection = measure_component_max_chord_along_direction(component_mask, roi, angle_deg)
    except DirectionalContourDetectionError:
        return "mask_projection"

    global_span = max(float(global_projection.metric_raw), 1.0)
    local_to_global_ratio = float(max_chord_projection.metric_raw) / global_span
    thickness_to_span_ratio = max_inscribed_diameter / global_span

    if thickness_to_span_ratio <= 0.20 and bbox_fill_ratio <= 0.30:
        return "mask_projection"
    if thickness_to_span_ratio <= 0.30 and pca_aspect_ratio <= 0.30:
        return "mask_projection"
    looks_thin = thickness_to_span_ratio <= 0.12
    looks_sparse_or_open = bbox_fill_ratio <= 0.28 or local_to_global_ratio <= 0.35 or pca_aspect_ratio <= 0.12
    if looks_thin and looks_sparse_or_open:
        return "mask_projection"
    if local_to_global_ratio <= 0.18 and bbox_fill_ratio <= 0.40:
        return "mask_projection"
    return "max_chord"


def _component_pca_aspect_ratio(points_xy: np.ndarray) -> float:
    points = np.asarray(points_xy, dtype=float)
    if points.ndim != 2 or points.shape[0] < 3:
        return 0.0
    centered = points - np.mean(points, axis=0)
    covariance = np.cov(centered, rowvar=False)
    if not np.isfinite(covariance).all():
        return 0.0
    values, vectors = np.linalg.eigh(covariance)
    order = np.argsort(values)[::-1]
    projected = centered @ vectors[:, order]
    extents = np.ptp(projected, axis=0)
    major = float(np.max(extents))
    minor = float(np.min(extents))
    if major <= 0.0:
        return 0.0
    return minor / major


def _component_foreground_fill_ratio(source_mask: np.ndarray, component_mask: np.ndarray) -> float | None:
    source = np.asarray(source_mask) > 0
    component = np.asarray(component_mask) > 0
    if source.shape != component.shape:
        return None
    component_area = int(np.count_nonzero(component))
    if component_area <= 0:
        return None
    source_area = int(np.count_nonzero(source & component))
    return float(source_area) / float(component_area)


def _envelope_target_mask(
    mask: np.ndarray,
    config: DirectionalContourConfig,
    *,
    cv2: Any | None,
) -> tuple[np.ndarray, int, int]:
    foreground = np.asarray(mask) > 0
    if not bool(np.any(foreground)):
        raise DirectionalContourDetectionError("target_component_not_found")
    labels, num_labels = ndimage.label(foreground, structure=np.ones((3, 3), dtype=bool))
    if int(num_labels) <= 0:
        raise DirectionalContourDetectionError("target_component_not_found")

    area_floor = max(1, int(round(float(max(1, int(config.min_target_area_px))) * 0.2)))
    geometry_mode = str(config.target_geometry_mode or "single_component")
    if geometry_mode not in {"line_bundle", "single_component", "mesh_lattice"}:
        geometry_mode = "line_bundle"

    direction = directional_unit_vector(float(config.direction_angle_deg))
    normal = np.array([-direction[1], direction[0]], dtype=float)

    components: list[dict[str, Any]] = []
    union_kept = np.zeros_like(foreground, dtype=bool)
    for label in range(1, int(num_labels) + 1):
        component = labels == label
        area = int(np.count_nonzero(component))
        if area < area_floor:
            continue
        rows, cols = np.where(component)
        lateral = cols * float(normal[0]) + rows * float(normal[1])
        along = cols * float(direction[0]) + rows * float(direction[1])
        components.append(
            {
                "mask": component,
                "area": area,
                "lateral_centroid": float(np.median(lateral)),
                "lateral_min": float(np.min(lateral)),
                "lateral_max": float(np.max(lateral)),
                "lateral_extent": float(np.ptp(lateral)),
                "along_extent": float(np.ptp(along)),
                "lateral": lateral,
            }
        )
        union_kept |= component
    if not components:
        raise DirectionalContourDetectionError("target_component_not_found")

    # single_component keeps the historical union-of-all-above-floor behaviour.
    if geometry_mode == "single_component":
        return union_kept.astype(np.uint8) * 255, len(components), 0

    # Group components into lateral clusters separated by gaps in the normal
    # (cross-measurement) direction. A genuine line bundle stacks contiguously,
    # so all its filaments fall into one cluster; an isolated background
    # scratch/dot/dust/hair that sits laterally far from the bundle body forms a
    # separate cluster. The bundle is the highest-total-area cluster, and the
    # remaining clusters are rejected so they can never fabricate a wider span,
    # even when a scratch is wide and elongated along the measurement direction.
    ordered = sorted(components, key=lambda item: item["lateral_min"])
    max_lateral_extent = max(component["lateral_extent"] for component in components)
    gap_threshold = max(20.0, float(max_lateral_extent) * 0.5)

    clusters: list[list[dict[str, Any]]] = []
    cluster_high: float | None = None
    for component in ordered:
        if not clusters or cluster_high is None or (
            float(component["lateral_min"]) - cluster_high > gap_threshold
        ):
            clusters.append([component])
            cluster_high = float(component["lateral_max"])
        else:
            clusters[-1].append(component)
            cluster_high = max(cluster_high, float(component["lateral_max"]))

    def _cluster_area(cluster: list[dict[str, Any]]) -> int:
        return int(sum(int(item["area"]) for item in cluster))

    core_cluster = max(clusters, key=_cluster_area)
    core_ids = {id(component) for component in core_cluster}

    selected = np.zeros_like(foreground, dtype=bool)
    selected_count = 0
    rejected_count = 0
    for component in components:
        if id(component) in core_ids:
            selected |= component["mask"]
            selected_count += 1
        else:
            rejected_count += 1

    if selected_count == 0:
        core = max(components, key=lambda item: item["area"])
        selected |= core["mask"]
        selected_count = 1
        rejected_count = max(0, len(components) - 1)

    if geometry_mode == "mesh_lattice":
        selected = _mesh_lattice_envelope_mask(selected, config, cv2=cv2)

    return selected.astype(np.uint8) * 255, int(selected_count), int(rejected_count)


def _mesh_lattice_envelope_mask(
    selected: np.ndarray,
    config: DirectionalContourConfig,
    *,
    cv2: Any | None,
) -> np.ndarray:
    foreground = np.asarray(selected, dtype=bool)
    if not bool(np.any(foreground)):
        return foreground
    sensitivity = float(np.clip(config.sensitivity, 0.0, 100.0))
    close_size = max(3, int(round(3 + (sensitivity / 100.0) * 6)))
    if close_size % 2 == 0:
        close_size += 1
    if cv2 is not None:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_size, close_size))
        closed = cv2.morphologyEx(foreground.astype(np.uint8) * 255, cv2.MORPH_CLOSE, kernel, iterations=1) > 0
    else:
        closed = ndimage.binary_closing(foreground, structure=_ellipse_structure(close_size))
    return _fill_small_holes(closed, max_area_px=max(8, int(config.min_target_area_px) * 4))


def _fill_small_holes(foreground: np.ndarray, *, max_area_px: int) -> np.ndarray:
    mask = np.asarray(foreground, dtype=bool)
    if not bool(np.any(mask)):
        return mask
    background = ~mask
    labels, num_labels = ndimage.label(background, structure=np.ones((3, 3), dtype=bool))
    if int(num_labels) <= 0:
        return mask
    border_labels = set(int(value) for value in np.unique(np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])))
    filled = mask.copy()
    for label in range(1, int(num_labels) + 1):
        if label in border_labels:
            continue
        hole = labels == label
        if int(np.count_nonzero(hole)) <= int(max_area_px):
            filled[hole] = True
    return filled


def _actual_component_boundary_mask(source_mask: np.ndarray, component_mask: np.ndarray) -> np.ndarray:
    source = np.asarray(source_mask) > 0
    component = np.asarray(component_mask) > 0
    if source.shape != component.shape:
        return np.asarray(component_mask, dtype=np.uint8)
    actual = source & component
    if not bool(np.any(actual)):
        return np.asarray(component_mask, dtype=np.uint8)
    return actual.astype(np.uint8)


def _max_chord_candidate_is_better(candidate: dict[str, Any], current: dict[str, Any] | None) -> bool:
    if current is None:
        return True
    span_delta = float(candidate["span"]) - float(current["span"])
    if abs(span_delta) > 1e-9:
        return span_delta > 0
    count_delta = int(candidate["count"]) - int(current["count"])
    if count_delta != 0:
        return count_delta > 0
    return float(candidate["center_distance"]) < float(current["center_distance"])


def _max_chord_prior_candidate_is_better(candidate: dict[str, Any], current: dict[str, Any] | None) -> bool:
    if current is None:
        return True
    candidate_endpoint_distance = candidate.get("endpoint_prior_distance")
    current_endpoint_distance = current.get("endpoint_prior_distance")
    if candidate_endpoint_distance is not None and current_endpoint_distance is not None:
        candidate_within = bool(candidate.get("endpoint_prior_within"))
        current_within = bool(current.get("endpoint_prior_within"))
        if candidate_within != current_within:
            return candidate_within
        if candidate_within and current_within:
            endpoint_delta = float(candidate_endpoint_distance) - float(current_endpoint_distance)
            if abs(endpoint_delta) > 2.0:
                return endpoint_delta < 0.0
    span_delta = float(candidate["span"]) - float(current["span"])
    meaningful_span_delta = max(8.0, float(current["span"]) * 0.05)
    if abs(span_delta) > meaningful_span_delta:
        return span_delta > 0
    prior_delta = float(candidate["prior_distance"]) - float(current["prior_distance"])
    if abs(prior_delta) > 1e-9:
        return prior_delta < 0
    count_delta = int(candidate["count"]) - int(current["count"])
    if count_delta != 0:
        return count_delta > 0
    return float(candidate["center_distance"]) < float(current["center_distance"])


def _max_chord_axis_prior_lateral_px(
    config: DirectionalContourConfig,
    geometry: _ProcessingGeometry,
) -> float | None:
    point = config.max_chord_axis_prior_point
    if point is None:
        return None
    direction = directional_unit_vector(float(config.direction_angle_deg))
    normal = np.array([-direction[1], direction[0]], dtype=float)
    roi = geometry.original_roi
    processing_point = np.array(
        [
            (float(point.x) - float(roi.x)) * float(geometry.scale_x),
            (float(point.y) - float(roi.y)) * float(geometry.scale_y),
        ],
        dtype=float,
    )
    return float(processing_point @ normal)


def _max_chord_axis_prior_tolerance_px(
    config: DirectionalContourConfig,
    geometry: _ProcessingGeometry,
) -> float | None:
    tolerance_px = config.max_chord_axis_prior_tolerance_px
    if tolerance_px is None:
        return None
    return max(0.0, float(tolerance_px) * float(geometry.scale))


def _max_chord_prior_point(
    point: PixelPoint | None,
    geometry: _ProcessingGeometry,
) -> np.ndarray | None:
    if point is None:
        return None
    roi = geometry.original_roi
    return np.array(
        [
            (float(point.x) - float(roi.x)) * float(geometry.scale_x),
            (float(point.y) - float(roi.y)) * float(geometry.scale_y),
        ],
        dtype=float,
    )


def _max_chord_endpoint_prior_tolerance_px(
    config: DirectionalContourConfig,
    geometry: _ProcessingGeometry,
) -> float | None:
    tolerance_px = config.max_chord_prior_endpoint_tolerance_px
    if tolerance_px is None:
        return None
    return max(0.0, float(tolerance_px) * float(geometry.scale))


def _max_chord_endpoint_prior_distance(
    point_a_xy: np.ndarray,
    point_b_xy: np.ndarray,
    prior_a_xy: np.ndarray | None,
    prior_b_xy: np.ndarray | None,
) -> float | None:
    if prior_a_xy is None or prior_b_xy is None:
        return None
    direct = float(np.linalg.norm(point_a_xy - prior_a_xy) + np.linalg.norm(point_b_xy - prior_b_xy))
    swapped = float(np.linalg.norm(point_a_xy - prior_b_xy) + np.linalg.norm(point_b_xy - prior_a_xy))
    return min(direct, swapped)


def _max_chord_endpoint_prior_within(
    endpoint_prior_distance: float | None,
    endpoint_prior_tolerance_px: float | None,
) -> bool:
    if endpoint_prior_distance is None or endpoint_prior_tolerance_px is None:
        return False
    return float(endpoint_prior_distance) <= float(endpoint_prior_tolerance_px) * 2.0


def _max_projection_display_index(projections: np.ndarray, normal_coords: np.ndarray) -> int:
    max_projection = float(np.max(projections))
    candidates = np.flatnonzero(np.isclose(projections, max_projection, rtol=0.0, atol=1e-9))
    if len(candidates) == 0:
        return int(np.argmax(projections))
    candidate_normals = normal_coords[candidates]
    return int(candidates[int(np.argmax(candidate_normals))])


def _side_guard_keep_mask(
    points_xy: np.ndarray,
    roi: RectRegion,
    direction: np.ndarray,
    *,
    allowed_mask: np.ndarray | None,
    side_guard_ratio: float,
) -> tuple[int, np.ndarray]:
    points = np.asarray(points_xy, dtype=float)
    if points.ndim != 2 or points.shape[0] == 0:
        return 0, np.zeros((0,), dtype=bool)
    ratio = max(0.0, min(0.45, float(side_guard_ratio or 0.0)))
    if ratio <= 0.0:
        return 0, np.ones((points.shape[0],), dtype=bool)

    if allowed_mask is not None and np.asarray(allowed_mask).shape[:2] == (int(roi.height), int(roi.width)):
        rows, cols = np.where(np.asarray(allowed_mask) > 0)
        if len(rows) > 0:
            allowed_points = np.column_stack([cols + int(roi.x), rows + int(roi.y)]).astype(float)
        else:
            allowed_points = _roi_pixel_points(roi)
    else:
        allowed_points = _roi_pixel_points(roi)

    allowed_along = allowed_points @ direction
    if len(allowed_along) == 0:
        return 0, np.ones((points.shape[0],), dtype=bool)
    along_min = float(np.min(allowed_along))
    along_max = float(np.max(allowed_along))
    guard_width = max(0.0, (along_max - along_min) * ratio)
    if guard_width <= 0.0:
        return 0, np.ones((points.shape[0],), dtype=bool)
    point_along = points @ direction
    in_guard = (point_along < along_min + guard_width) | (point_along > along_max - guard_width)
    return int(np.count_nonzero(in_guard)), ~in_guard


def _roi_pixel_points(roi: RectRegion) -> np.ndarray:
    height = max(0, int(roi.height))
    width = max(0, int(roi.width))
    if height <= 0 or width <= 0:
        return np.empty((0, 2), dtype=float)
    rows, cols = np.indices((height, width))
    return np.column_stack([cols.ravel() + int(roi.x), rows.ravel() + int(roi.y)]).astype(float)


def _selection_mode_for_projection(projection_point_mode: str) -> str:
    if projection_point_mode == "envelope_max_width":
        return "directional_contour_envelope_max_width"
    if projection_point_mode == "max_chord":
        return "directional_contour_max_chord"
    return "directional_contour_boundary_span"


def directional_unit_vector(angle_deg: float) -> np.ndarray:
    angle_rad = math.radians(float(angle_deg))
    vector = np.array([math.cos(angle_rad), math.sin(angle_rad)], dtype=float)
    vector[np.abs(vector) < 1e-12] = 0.0
    return _unit_direction(vector)


def _normalize_gray_image(image: Any) -> np.ndarray:
    if image is None:
        raise DirectionalContourDetectionError("empty_frame")
    array = np.asarray(image)
    if array.size == 0:
        raise DirectionalContourDetectionError("empty_frame")
    if array.ndim == 3:
        array = np.mean(array[:, :, :3], axis=2)
    if array.ndim != 2:
        raise DirectionalContourDetectionError("unsupported_frame_shape")
    return np.clip(array, 0, 255).astype(np.uint8, copy=False)


def _prepare_processing_geometry(
    cv2: Any | None,
    crop: np.ndarray,
    roi: RectRegion,
    config: DirectionalContourConfig,
) -> _ProcessingGeometry:
    max_side = max(0, int(config.processing_max_side_px or 0))
    height, width = crop.shape[:2]
    if cv2 is None or max_side <= 0 or max(width, height) <= max_side:
        return _ProcessingGeometry(crop=crop, original_roi=roi)

    scale = float(max_side) / float(max(width, height))
    target_width = max(2, int(round(float(width) * scale)))
    target_height = max(2, int(round(float(height) * scale)))
    resized = cv2.resize(crop, (target_width, target_height), interpolation=cv2.INTER_AREA)
    return _ProcessingGeometry(
        crop=resized,
        original_roi=roi,
        scale_x=float(target_width) / float(width),
        scale_y=float(target_height) / float(height),
    )


def _projection_to_original_roi(
    projection: DirectionalProjection,
    geometry: _ProcessingGeometry,
    *,
    image_shape: tuple[int, ...],
) -> DirectionalProjection:
    if (
        abs(float(geometry.scale_x) - 1.0) < 1e-9
        and abs(float(geometry.scale_y) - 1.0) < 1e-9
        and int(geometry.original_roi.x) == 0
        and int(geometry.original_roi.y) == 0
    ):
        return projection

    point_a = _point_from_processing_space(projection.point_a, geometry, image_shape=image_shape)
    point_b = _point_from_processing_space(projection.point_b, geometry, image_shape=image_shape)
    source_point_a = _point_from_processing_space(projection.source_point_a, geometry, image_shape=image_shape)
    source_point_b = _point_from_processing_space(projection.source_point_b, geometry, image_shape=image_shape)
    axis_point_a = _point_from_processing_space(projection.axis_point_a, geometry, image_shape=image_shape)
    axis_point_b = _point_from_processing_space(projection.axis_point_b, geometry, image_shape=image_shape)
    return DirectionalProjection(
        point_a=point_a,
        point_b=point_b,
        source_point_a=source_point_a,
        source_point_b=source_point_b,
        axis_point_a=axis_point_a,
        axis_point_b=axis_point_b,
        metric_raw=_distance_between(point_a, point_b),
        direction_angle_deg=float(projection.direction_angle_deg),
        axis_offset_px=_axis_offset_to_original_space(
            float(projection.axis_offset_px),
            geometry,
            float(projection.direction_angle_deg),
        ),
        envelope_support_px=projection.envelope_support_px,
        envelope_candidate_count=projection.envelope_candidate_count,
        side_guard_foreground_area=projection.side_guard_foreground_area,
    )


def _refine_projection_on_original_axis(
    cv2: Any | None,
    gray: np.ndarray,
    roi: RectRegion,
    config: DirectionalContourConfig,
    geometry: _ProcessingGeometry,
    projection: DirectionalProjection,
    *,
    projection_point_mode: str,
) -> DirectionalProjection:
    if projection_point_mode == "envelope_max_width":
        # Envelope A/B are analytic axis points, not foreground pixels. Snapping
        # each endpoint independently to the nearest original-frame foreground
        # would re-tilt the segment off the measurement axis, so skip it; the
        # dedicated axis re-projection keeps A/B parallel instead.
        return projection
    if (
        cv2 is None
        or (
            abs(float(geometry.scale_x) - 1.0) < 1e-9
            and abs(float(geometry.scale_y) - 1.0) < 1e-9
        )
    ):
        return projection
    crop = gray[int(roi.y) : int(roi.y + roi.height), int(roi.x) : int(roi.x + roi.width)]
    if crop.size == 0:
        return projection
    try:
        if projection_point_mode == "mask_projection":
            return _refine_mask_projection_on_original_axis(
                cv2,
                crop,
                gray,
                roi,
                config,
                projection,
                geometry,
            )
        radius_px = _original_endpoint_refinement_radius_px(geometry)
        point_a = _snap_projection_endpoint_to_original_foreground(
            cv2,
            gray,
            config,
            projection.point_a,
            radius_px=radius_px,
        )
        point_b = _snap_projection_endpoint_to_original_foreground(
            cv2,
            gray,
            config,
            projection.point_b,
            radius_px=radius_px,
        )
        if point_a == point_b:
            return projection
        return DirectionalProjection(
            point_a=point_a,
            point_b=point_b,
            source_point_a=point_a,
            source_point_b=point_b,
            axis_point_a=point_a,
            axis_point_b=point_b,
            metric_raw=_distance_between(point_a, point_b),
            direction_angle_deg=float(projection.direction_angle_deg),
            axis_offset_px=float(projection.axis_offset_px),
            envelope_support_px=projection.envelope_support_px,
            envelope_candidate_count=projection.envelope_candidate_count,
            side_guard_foreground_area=projection.side_guard_foreground_area,
        )
    except DirectionalContourDetectionError:
        return projection


def _axis_normal_vector(angle_deg: float) -> np.ndarray:
    angle_rad = math.radians(float(angle_deg))
    return np.array([-math.sin(angle_rad), math.cos(angle_rad)], dtype=float)


def _axis_offset_to_original_space(
    axis_offset_px: float,
    geometry: _ProcessingGeometry,
    angle_deg: float,
) -> float:
    """Map a processing-crop-local lateral offset back to the original frame.

    The envelope measurement works on the (possibly downscaled) processing crop
    whose pixel origin is (0, 0); the original analysis ROI lives at
    ``original_roi.(x, y)``. A lateral offset is ``point . normal``; converting
    back to the original frame therefore divides by the processing scale and adds
    the projection of the ROI origin onto the normal.
    """
    normal = _axis_normal_vector(angle_deg)
    origin = np.array([float(geometry.original_roi.x), float(geometry.original_roi.y)], dtype=float)
    return float(origin @ normal) + float(axis_offset_px) / max(float(geometry.scale), 1e-9)


def _axis_offset_to_processing_space(
    axis_offset_original: float,
    geometry: _ProcessingGeometry,
    angle_deg: float,
) -> float:
    """Strict inverse of :func:`_axis_offset_to_original_space`.

    Maps an original-frame lateral offset (e.g. the tracking axis prior, which is
    ``midpoint_global . normal``) into the processing-crop-local coordinate frame
    that :func:`measure_component_envelope_max_width` operates in. Multiplying by
    the scale alone is wrong because it omits the ROI-origin projection.
    """
    normal = _axis_normal_vector(angle_deg)
    origin = np.array([float(geometry.original_roi.x), float(geometry.original_roi.y)], dtype=float)
    return (float(axis_offset_original) - float(origin @ normal)) * float(geometry.scale)


def _original_axis_refinement_tolerance_px(geometry: _ProcessingGeometry) -> float:
    inverse_scale = 1.0 / max(float(geometry.scale), 1e-9)
    return max(3.0, min(24.0, inverse_scale * 2.5))


def _original_endpoint_refinement_radius_px(geometry: _ProcessingGeometry) -> int:
    inverse_scale = 1.0 / max(float(geometry.scale), 1e-9)
    return max(6, min(32, int(math.ceil(inverse_scale * 4.0))))


def _refine_mask_projection_on_original_axis(
    cv2: Any | None,
    crop: np.ndarray,
    gray: np.ndarray,
    roi: RectRegion,
    config: DirectionalContourConfig,
    projection: DirectionalProjection,
    geometry: _ProcessingGeometry,
) -> DirectionalProjection:
    if cv2 is None:
        return projection
    raw_mask, threshold_value = _threshold_mask(cv2, crop, config)
    original_geometry = _ProcessingGeometry(crop=crop, original_roi=roi)
    allowed_mask = _processing_metric_box_mask(cv2, original_geometry, config.metric_box)
    if allowed_mask is not None:
        raw_mask = _apply_allowed_mask(cv2, raw_mask, allowed_mask)
    source_mask = _source_foreground_mask(cv2, crop, raw_mask, threshold_value, config)
    if allowed_mask is not None:
        source_mask = _apply_allowed_mask(cv2, source_mask, allowed_mask)
    return project_component_mask_onto_direction(
        source_mask,
        roi,
        float(config.direction_angle_deg),
        image_shape=gray.shape,
        clip_region=roi,
        axis_offset_px=float(projection.axis_offset_px),
        axis_tolerance_px=_original_axis_refinement_tolerance_px(geometry),
    )


def _snap_projection_endpoint_to_original_foreground(
    cv2: Any | None,
    gray: np.ndarray,
    config: DirectionalContourConfig,
    point: PixelPoint,
    *,
    radius_px: int,
) -> PixelPoint:
    if cv2 is None:
        return point
    height, width = gray.shape[:2]
    if height <= 0 or width <= 0:
        return point
    center_x = max(0, min(width - 1, int(point.x)))
    center_y = max(0, min(height - 1, int(point.y)))
    radius = max(1, int(radius_px))
    x0 = max(0, center_x - radius)
    x1 = min(width, center_x + radius + 1)
    y0 = max(0, center_y - radius)
    y1 = min(height, center_y + radius + 1)
    patch = gray[y0:y1, x0:x1]
    if patch.size == 0:
        return point

    mask, threshold_value = _threshold_mask(cv2, patch, config)
    patch_roi = RectRegion(x=x0, y=y0, width=x1 - x0, height=y1 - y0)
    allowed_mask = _processing_metric_box_mask(
        cv2,
        _ProcessingGeometry(crop=patch, original_roi=patch_roi),
        config.metric_box,
    )
    if allowed_mask is not None:
        mask = _apply_allowed_mask(cv2, mask, allowed_mask)
    foreground_mask = _source_foreground_mask(cv2, patch, mask, threshold_value, config)
    if allowed_mask is not None:
        foreground_mask = _apply_allowed_mask(cv2, foreground_mask, allowed_mask)
    foreground = np.asarray(foreground_mask) > 0
    if not bool(foreground.any()):
        return point

    boundary = _foreground_boundary_mask(foreground)
    candidate_mask = boundary if bool(boundary.any()) else foreground
    ys, xs = np.nonzero(candidate_mask)
    if len(xs) == 0:
        return point
    global_x = xs.astype(float) + float(x0)
    global_y = ys.astype(float) + float(y0)
    distances = (global_x - float(point.x)) ** 2 + (global_y - float(point.y)) ** 2
    best_index = int(np.argmin(distances))
    return PixelPoint(x=int(round(global_x[best_index])), y=int(round(global_y[best_index])))


def _foreground_boundary_mask(foreground: np.ndarray) -> np.ndarray:
    mask = np.asarray(foreground, dtype=bool)
    if mask.size == 0:
        return mask
    eroded = ndimage.binary_erosion(
        mask,
        structure=np.ones((3, 3), dtype=bool),
        border_value=0,
    )
    return mask & ~eroded


def _point_from_processing_space(
    point: PixelPoint,
    geometry: _ProcessingGeometry,
    *,
    image_shape: tuple[int, ...],
) -> PixelPoint:
    roi = geometry.original_roi
    x = int(round(float(roi.x) + (float(point.x) / max(float(geometry.scale_x), 1e-9))))
    y = int(round(float(roi.y) + (float(point.y) / max(float(geometry.scale_y), 1e-9))))
    return _pixel_point_from_xy(np.array([x, y], dtype=float), image_shape=image_shape, clip_region=roi)


def _distance_between(point_a: PixelPoint, point_b: PixelPoint) -> float:
    return math.hypot(float(point_b.x - point_a.x), float(point_b.y - point_a.y))


def _contour_to_original_roi(contour_xy: np.ndarray, geometry: _ProcessingGeometry) -> np.ndarray:
    if (
        abs(float(geometry.scale_x) - 1.0) < 1e-9
        and abs(float(geometry.scale_y) - 1.0) < 1e-9
        and int(geometry.original_roi.x) == 0
        and int(geometry.original_roi.y) == 0
    ):
        return contour_xy
    contour = np.asarray(contour_xy, dtype=float).copy()
    contour[:, 0] = float(geometry.original_roi.x) + contour[:, 0] / max(float(geometry.scale_x), 1e-9)
    contour[:, 1] = float(geometry.original_roi.y) + contour[:, 1] / max(float(geometry.scale_y), 1e-9)
    return contour


def _clip_roi(region: RectRegion, image_shape: tuple[int, ...]) -> RectRegion:
    height, width = image_shape[:2]
    x0 = max(0, min(int(region.x), width))
    y0 = max(0, min(int(region.y), height))
    x1 = max(0, min(int(region.x + region.width), width))
    y1 = max(0, min(int(region.y + region.height), height))
    if x1 <= x0 or y1 <= y0:
        raise DirectionalContourDetectionError("roi_outside_image")
    if x1 - x0 < 2 or y1 - y0 < 2:
        raise DirectionalContourDetectionError("roi_too_small")
    return RectRegion(x=x0, y=y0, width=x1 - x0, height=y1 - y0)


def _threshold_mask(
    cv2: Any | None,
    crop: np.ndarray,
    config: DirectionalContourConfig,
) -> tuple[np.ndarray, float | None]:
    if cv2 is None:
        return _threshold_mask_numpy(crop, config)

    sensitivity = float(np.clip(config.sensitivity, 0.0, 100.0))
    blur = cv2.GaussianBlur(crop, (5, 5), 0) if min(crop.shape[:2]) > 8 else crop
    threshold_flag = cv2.THRESH_BINARY_INV if config.foreground_polarity == "dark_on_light" else cv2.THRESH_BINARY

    if config.threshold_mode == "adaptive":
        block_size = max(3, int(round(11 + (sensitivity / 100.0) * 12)))
        if block_size % 2 == 0:
            block_size += 1
        c_value = max(1, int(round(3 + (sensitivity / 100.0) * 6)))
        return (
            cv2.adaptiveThreshold(
                blur,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                threshold_flag,
                block_size,
                c_value,
            ),
            None,
        )
    if config.threshold_mode == "otsu":
        threshold_value, mask = cv2.threshold(blur, 0, 255, threshold_flag | cv2.THRESH_OTSU)
        return mask, float(threshold_value)

    threshold_value = 100.0 if config.threshold_value is None else float(config.threshold_value)
    source = crop if min(crop.shape[:2]) <= 48 else blur
    _unused, mask = cv2.threshold(source, threshold_value, 255, threshold_flag)
    return mask, threshold_value


def _source_foreground_mask(
    cv2: Any | None,
    crop: np.ndarray,
    fallback_mask: np.ndarray,
    threshold_value: float | None,
    config: DirectionalContourConfig,
) -> np.ndarray:
    if threshold_value is None:
        return np.asarray(fallback_mask, dtype=np.uint8)
    if config.foreground_polarity == "dark_on_light":
        foreground = np.asarray(crop) < float(threshold_value)
    else:
        foreground = np.asarray(crop) > float(threshold_value)
    return foreground.astype(np.uint8) * 255


def _processing_metric_box_mask(
    cv2: Any | None,
    geometry: _ProcessingGeometry,
    metric_box: MetricBox | None,
) -> np.ndarray | None:
    if cv2 is None or metric_box is None:
        return None
    height, width = geometry.crop.shape[:2]
    if height <= 0 or width <= 0:
        return None
    roi = geometry.original_roi
    corners = np.asarray(
        [
            [
                (float(x) - float(roi.x)) * float(geometry.scale_x),
                (float(y) - float(roi.y)) * float(geometry.scale_y),
            ]
            for x, y in _metric_box_corners(metric_box)
        ],
        dtype=np.float32,
    )
    if not np.isfinite(corners).all():
        return None
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillConvexPoly(mask, np.rint(corners).astype(np.int32), 255)
    return mask


def _apply_allowed_mask(cv2: Any | None, mask: np.ndarray, allowed_mask: np.ndarray) -> np.ndarray:
    if cv2 is not None:
        return cv2.bitwise_and(mask, allowed_mask)
    return np.where((np.asarray(mask) > 0) & (np.asarray(allowed_mask) > 0), 255, 0).astype(np.uint8)


def _metric_box_corners(box: MetricBox) -> list[tuple[float, float]]:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    half_width = float(box.width) / 2.0
    half_height = float(box.height) / 2.0
    corners: list[tuple[float, float]] = []
    for local_x, local_y in (
        (-half_width, -half_height),
        (half_width, -half_height),
        (half_width, half_height),
        (-half_width, half_height),
    ):
        corners.append(
            (
                float(box.center_x) + local_x * cos_theta - local_y * sin_theta,
                float(box.center_y) + local_x * sin_theta + local_y * cos_theta,
            )
        )
    return corners


def _cleanup_mask(cv2: Any | None, mask: np.ndarray, config: DirectionalContourConfig) -> np.ndarray:
    foreground = np.asarray(mask) > 0
    if min(mask.shape[:2]) <= 24:
        return foreground.astype(np.uint8) * 255
    if cv2 is None:
        sensitivity = float(np.clip(config.sensitivity, 0.0, 100.0))
        close_size = max(3, int(round(3 + (sensitivity / 100.0) * 8)))
        if close_size % 2 == 0:
            close_size += 1
        cleaned = _binary_morphology_preserve_edges(
            foreground,
            ndimage.binary_closing,
            _ellipse_structure(close_size),
        )
        if config.ignore_internal_texture:
            cleaned = ndimage.binary_fill_holes(cleaned)
        open_size = max(1, int(config.open_kernel))
        if open_size > 1:
            cleaned = _binary_morphology_preserve_edges(
                cleaned,
                ndimage.binary_opening,
                np.ones((open_size, open_size), dtype=bool),
            )
        return cleaned.astype(np.uint8) * 255

    sensitivity = float(np.clip(config.sensitivity, 0.0, 100.0))
    close_size = max(3, int(round(3 + (sensitivity / 100.0) * 8)))
    if close_size % 2 == 0:
        close_size += 1
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_size, close_size))
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel, iterations=1)
    if config.ignore_internal_texture:
        contours, _hierarchy = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filled = np.zeros_like(cleaned)
        if contours:
            cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
            cleaned = filled
    open_size = max(1, int(config.open_kernel))
    if open_size <= 1:
        return cleaned
    open_kernel = np.ones((open_size, open_size), dtype=np.uint8)
    return cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, open_kernel, iterations=1)


def _merge_aligned_component_fragments(
    mask: np.ndarray,
    *,
    direction_angle_deg: float,
    min_target_area_px: int,
    component_bridge_kernel: int,
) -> np.ndarray:
    foreground = np.asarray(mask) > 0
    labels, num_labels = ndimage.label(foreground, structure=np.ones((3, 3), dtype=bool))
    if int(num_labels) <= 1:
        return foreground.astype(np.uint8) * 255
    if int(num_labels) > 48 or int(component_bridge_kernel) >= 31:
        return _merge_many_fragments_with_cv_morphology(
            foreground,
            component_bridge_kernel=component_bridge_kernel,
        )

    direction = directional_unit_vector(float(direction_angle_deg))
    normal = np.array([-direction[1], direction[0]], dtype=float)
    fragment_area_floor = max(24, int(round(float(max(1, int(min_target_area_px))) * 0.2)))
    components: list[dict[str, Any]] = []
    for label in range(1, int(num_labels) + 1):
        ys, xs = np.nonzero(labels == label)
        area = int(len(xs))
        if area < fragment_area_floor:
            continue
        points = np.column_stack((xs, ys)).astype(float)
        along = points @ direction
        lateral = points @ normal
        components.append(
            {
                "label": int(label),
                "area": area,
                "along_min": float(np.min(along)),
                "along_max": float(np.max(along)),
                "lateral_min": float(np.min(lateral)),
                "lateral_max": float(np.max(lateral)),
                "points": points,
            }
        )

    if not components:
        return foreground.astype(np.uint8) * 255

    best = max(components, key=lambda item: int(item["area"]))
    kept_labels = {int(best["label"])}
    bridge_distance_px = max(24.0, 2.0 * float(component_bridge_kernel))
    best_along_span_px = float(best["along_max"]) - float(best["along_min"])
    lateral_gap_limit_px = max(24.0, 0.08 * max(best_along_span_px, 1.0))
    bridge_segments: list[tuple[np.ndarray, np.ndarray]] = []
    changed = True
    while changed:
        changed = False
        kept = [component for component in components if int(component["label"]) in kept_labels]
        for candidate in components:
            candidate_label = int(candidate["label"])
            if candidate_label in kept_labels:
                continue
            bridge = _nearest_bridge_to_kept_components(
                candidate,
                kept,
                bridge_distance_px=bridge_distance_px,
                lateral_gap_limit_px=lateral_gap_limit_px,
            )
            if bridge is not None:
                kept_labels.add(candidate_label)
                bridge_segments.append(bridge)
                changed = True

    merged = np.isin(labels, list(kept_labels))
    if len(kept_labels) <= 1:
        return merged.astype(np.uint8) * 255

    bridge_size = max(1, int(component_bridge_kernel))
    if bridge_size % 2 == 0:
        bridge_size += 1
    bridge_thickness = max(1, int(math.ceil(float(bridge_size) / 4.0)))
    for start_xy, end_xy in bridge_segments:
        _draw_line_on_binary_mask(merged, start_xy, end_xy, thickness_px=bridge_thickness)
    bridge_structure = _ellipse_structure(bridge_size)
    merged = _binary_morphology_preserve_edges(
        merged,
        ndimage.binary_closing,
        bridge_structure,
    )
    return merged.astype(np.uint8) * 255


def _merge_many_fragments_with_cv_morphology(
    foreground: np.ndarray,
    *,
    component_bridge_kernel: int,
) -> np.ndarray:
    bridge_size = max(5, int(component_bridge_kernel))
    if bridge_size % 2 == 0:
        bridge_size += 1
    cv2 = _try_import_cv2()
    foreground_u8 = np.asarray(foreground, dtype=np.uint8) * 255
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (bridge_size, bridge_size))
    closed = cv2.morphologyEx(foreground_u8, cv2.MORPH_CLOSE, close_kernel, iterations=1)
    contours, _hierarchy = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(closed)
    if contours:
        cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
    return filled


def _merge_many_fragments_with_scipy_morphology(
    foreground: np.ndarray,
    *,
    component_bridge_kernel: int,
) -> np.ndarray:
    bridge_size = max(5, int(component_bridge_kernel))
    if bridge_size % 2 == 0:
        bridge_size += 1
    bridge_structure = _ellipse_structure(bridge_size)
    merged = _binary_morphology_preserve_edges(
        np.asarray(foreground, dtype=bool),
        ndimage.binary_closing,
        bridge_structure,
    )
    merged = ndimage.binary_fill_holes(merged)
    return merged.astype(np.uint8) * 255


def _component_profiles_align_for_bridge(
    first: dict[str, Any],
    second: dict[str, Any],
    *,
    bridge_distance_px: float,
    lateral_gap_limit_px: float,
) -> bool:
    along_gap = _interval_gap(
        float(first["along_min"]),
        float(first["along_max"]),
        float(second["along_min"]),
        float(second["along_max"]),
    )
    lateral_gap = _interval_gap(
        float(first["lateral_min"]),
        float(first["lateral_max"]),
        float(second["lateral_min"]),
        float(second["lateral_max"]),
    )
    return along_gap <= bridge_distance_px and lateral_gap <= lateral_gap_limit_px


def _nearest_bridge_to_kept_components(
    candidate: dict[str, Any],
    kept_components: list[dict[str, Any]],
    *,
    bridge_distance_px: float,
    lateral_gap_limit_px: float,
) -> tuple[np.ndarray, np.ndarray] | None:
    best: tuple[float, np.ndarray, np.ndarray] | None = None
    candidate_points = np.asarray(candidate["points"], dtype=float)
    for selected in kept_components:
        if not _component_profiles_align_for_bridge(
            candidate,
            selected,
            bridge_distance_px=bridge_distance_px,
            lateral_gap_limit_px=lateral_gap_limit_px,
        ):
            continue
        distance, selected_point, candidate_point = _nearest_points_between_components(
            np.asarray(selected["points"], dtype=float),
            candidate_points,
        )
        if best is None or distance < best[0]:
            best = (distance, selected_point, candidate_point)
    if best is None:
        return None
    return best[1], best[2]


def _nearest_points_between_components(
    first_points: np.ndarray,
    second_points: np.ndarray,
) -> tuple[float, np.ndarray, np.ndarray]:
    first = np.asarray(first_points, dtype=float)
    second = np.asarray(second_points, dtype=float)
    if first.ndim != 2 or second.ndim != 2 or first.shape[1] != 2 or second.shape[1] != 2:
        raise DirectionalContourDetectionError("target_component_not_found")
    if len(first) == 0 or len(second) == 0:
        raise DirectionalContourDetectionError("target_component_not_found")

    # Real braided parts can produce large fragmented masks. Building the full
    # N x M distance matrix is quadratic in memory and stalls on camera frames.
    distances, indexes = cKDTree(second).query(first, k=1)
    first_index = int(np.argmin(distances))
    second_index = int(indexes[first_index])
    return float(distances[first_index]), first[first_index], second[second_index]


def _draw_line_on_binary_mask(
    mask: np.ndarray,
    start_xy: np.ndarray,
    end_xy: np.ndarray,
    *,
    thickness_px: int,
) -> None:
    start = np.asarray(start_xy, dtype=float)
    end = np.asarray(end_xy, dtype=float)
    steps = max(1, int(math.ceil(float(np.max(np.abs(end - start))))))
    xs = np.linspace(float(start[0]), float(end[0]), steps + 1)
    ys = np.linspace(float(start[1]), float(end[1]), steps + 1)
    radius = max(0, int(math.ceil(float(thickness_px) / 2.0)))
    height, width = mask.shape[:2]
    for x_float, y_float in zip(xs, ys):
        x = int(round(x_float))
        y = int(round(y_float))
        x0 = max(0, x - radius)
        x1 = min(width, x + radius + 1)
        y0 = max(0, y - radius)
        y1 = min(height, y + radius + 1)
        mask[y0:y1, x0:x1] = True


def _interval_gap(first_min: float, first_max: float, second_min: float, second_max: float) -> float:
    return max(0.0, max(first_min, second_min) - min(first_max, second_max))


def _largest_component_mask(
    cv2: Any | None,
    mask: np.ndarray,
    *,
    min_target_area_px: int,
    direction_angle_deg: float,
    component_bridge_kernel: int,
) -> np.ndarray:
    mask = _merge_aligned_component_fragments(
        mask,
        direction_angle_deg=direction_angle_deg,
        min_target_area_px=min_target_area_px,
        component_bridge_kernel=component_bridge_kernel,
    )
    if cv2 is None:
        return _largest_component_mask_numpy(mask, min_target_area_px=min_target_area_px)

    num_labels, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        (mask > 0).astype(np.uint8),
        connectivity=8,
    )
    best_label = 0
    best_area = 0
    for label in range(1, int(num_labels)):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= max(1, int(min_target_area_px)) and area > best_area:
            best_label = label
            best_area = area
    if best_label == 0:
        raise DirectionalContourDetectionError("target_component_not_found")
    return (labels == best_label).astype(np.uint8) * 255


def _component_contour_xy(cv2: Any | None, component_mask: np.ndarray, roi: RectRegion) -> np.ndarray:
    if cv2 is None:
        return _component_boundary_xy_numpy(component_mask, roi)

    contours, _hierarchy = cv2.findContours(component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise DirectionalContourDetectionError("target_contour_not_found")
    contour = max(contours, key=cv2.contourArea)
    contour_xy = contour[:, 0, :].astype(float)
    contour_xy[:, 0] += float(roi.x)
    contour_xy[:, 1] += float(roi.y)
    return contour_xy


def _quality_score(*, metric_raw: float, component_area: int, roi: RectRegion, metric_box: MetricBox | None = None) -> float:
    if metric_box is not None:
        reference_area = max(int(metric_box.width) * int(metric_box.height), 1)
        reference_short_side = max(min(int(metric_box.width), int(metric_box.height)), 1)
        reference_diagonal = max(math.hypot(float(metric_box.width), float(metric_box.height)), 1.0)
    else:
        reference_area = max(int(roi.width) * int(roi.height), 1)
        reference_short_side = max(min(int(roi.width), int(roi.height)), 1)
        reference_diagonal = max(math.hypot(float(roi.width), float(roi.height)), 1.0)
    area_fraction = max(0.0, float(component_area) / float(reference_area))
    if area_fraction >= 0.85:
        return 0.55
    span_presence = min(
        1.0,
        max(0.0, float(metric_raw) / max(float(reference_short_side) * 0.10, 8.0)),
    )
    component_presence = min(
        1.0,
        max(0.0, float(component_area) / max(float(reference_area) * 0.005, 20.0)),
    )
    fill_specificity = 1.0 - min(1.0, area_fraction / 0.85)
    diagonal_coverage = min(1.0, max(0.0, float(metric_raw) / reference_diagonal))
    quality = 0.55 + 0.20 * span_presence + 0.15 * component_presence + 0.05 * fill_specificity + 0.05 * diagonal_coverage
    return float(min(1.0, max(0.0, quality)))


def _pixel_point_from_xy(
    point_xy: np.ndarray,
    *,
    image_shape: tuple[int, ...] | None,
    clip_region: RectRegion | None = None,
) -> PixelPoint:
    x = int(round(float(point_xy[0])))
    y = int(round(float(point_xy[1])))
    if image_shape is not None:
        height, width = image_shape[:2]
        x = max(0, min(max(0, int(width) - 1), x))
        y = max(0, min(max(0, int(height) - 1), y))
    if clip_region is not None:
        x = max(int(clip_region.x), min(int(clip_region.x + clip_region.width - 1), x))
        y = max(int(clip_region.y), min(int(clip_region.y + clip_region.height - 1), y))
    return PixelPoint(x=x, y=y)


def _unit_direction(vector_xy: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector_xy))
    if norm < 1e-9:
        raise DirectionalContourDetectionError("degenerate_direction")
    return vector_xy / norm


def _roi_tuple(roi: RectRegion) -> tuple[int, int, int, int]:
    return (int(roi.x), int(roi.y), int(roi.width), int(roi.height))


def _threshold_mask_numpy(crop: np.ndarray, config: DirectionalContourConfig) -> tuple[np.ndarray, float | None]:
    if config.threshold_mode == "otsu":
        threshold_value = _otsu_threshold(crop)
    elif config.threshold_mode == "adaptive":
        sensitivity = float(np.clip(config.sensitivity, 0.0, 100.0))
        offset = 4.0 + (sensitivity / 100.0) * 8.0
        mean_value = float(np.mean(crop))
        threshold_value = mean_value - offset if config.foreground_polarity == "dark_on_light" else mean_value + offset
    else:
        threshold_value = 100.0 if config.threshold_value is None else float(config.threshold_value)

    if config.foreground_polarity == "dark_on_light":
        mask = crop < threshold_value
    else:
        mask = crop > threshold_value
    return mask.astype(np.uint8) * 255, float(threshold_value)


def _otsu_threshold(crop: np.ndarray) -> float:
    hist = np.bincount(crop.astype(np.uint8, copy=False).ravel(), minlength=256).astype(float)
    total = float(np.sum(hist))
    if total <= 0:
        return 0.0
    values = np.arange(256, dtype=float)
    sum_total = float(np.sum(values * hist))
    weight_background = np.cumsum(hist)
    weight_foreground = total - weight_background
    sum_background = np.cumsum(values * hist)
    valid = (weight_background > 0) & (weight_foreground > 0)
    if not bool(np.any(valid)):
        return float(np.argmax(hist))
    mean_background = np.zeros_like(values)
    mean_foreground = np.zeros_like(values)
    mean_background[valid] = sum_background[valid] / weight_background[valid]
    mean_foreground[valid] = (sum_total - sum_background[valid]) / weight_foreground[valid]
    between = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
    return float(np.argmax(between))


def _largest_component_mask_numpy(mask: np.ndarray, *, min_target_area_px: int) -> np.ndarray:
    foreground = np.asarray(mask) > 0
    labels, num_labels = ndimage.label(foreground, structure=np.ones((3, 3), dtype=bool))
    if int(num_labels) == 0:
        raise DirectionalContourDetectionError("target_component_not_found")
    areas = np.bincount(labels.ravel())
    areas[0] = 0
    areas[areas < max(1, int(min_target_area_px))] = 0
    best_label = int(np.argmax(areas))
    if best_label == 0:
        raise DirectionalContourDetectionError("target_component_not_found")
    return (labels == best_label).astype(np.uint8) * 255


def _component_boundary_xy_numpy(component_mask: np.ndarray, roi: RectRegion) -> np.ndarray:
    foreground = np.asarray(component_mask) > 0
    if not bool(np.any(foreground)):
        raise DirectionalContourDetectionError("target_contour_not_found")

    eroded = ndimage.binary_erosion(
        foreground,
        structure=np.ones((3, 3), dtype=bool),
        border_value=0,
    )
    boundary = foreground & ~eroded
    if not bool(np.any(boundary)):
        boundary = foreground
    ys, xs = np.nonzero(boundary)
    return np.column_stack((xs + int(roi.x), ys + int(roi.y))).astype(float)


def _ellipse_structure(size: int) -> np.ndarray:
    radius = max(1.0, (float(size) - 1.0) / 2.0)
    yy, xx = np.ogrid[:size, :size]
    center = (float(size) - 1.0) / 2.0
    return ((xx - center) ** 2 + (yy - center) ** 2) <= radius**2


def _binary_morphology_preserve_edges(
    image: np.ndarray,
    operation: Any,
    structure: np.ndarray,
) -> np.ndarray:
    pad = max(1, int(max(structure.shape) // 2))
    padded = np.pad(np.asarray(image, dtype=bool), pad_width=pad, mode="edge")
    morphed = operation(padded, structure=structure, iterations=1)
    return morphed[pad:-pad, pad:-pad]


def _try_import_cv2() -> Any | None:
    try:
        import cv2  # type: ignore
    except Exception as exc:  # pragma: no cover
        return None
    return cv2
