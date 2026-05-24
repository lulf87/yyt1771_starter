"""Contour-based directional span extraction for live setup."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from src.core.contracts import VisionMetricExtractor
from src.core.models import FramePacket, MetricBox, PixelPoint, RectRegion, ShapeMetric


@dataclass(slots=True)
class DirectionalContourConfig:
    analysis_roi: RectRegion
    direction_angle_deg: float
    metric_box: MetricBox | None = None
    foreground_polarity: str = "dark_on_light"
    threshold_mode: str = "adaptive"
    threshold_value: float | None = None
    min_target_area_px: int = 80
    sensitivity: float = 50.0
    ignore_internal_texture: bool = True
    component_bridge_kernel: int = 11
    open_kernel: int = 1
    projection_mode: str = "auto"
    max_chord_axis_prior_point: PixelPoint | None = None
    max_chord_axis_prior_tolerance_px: float | None = None
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

        return ShapeMetric(
            timestamp_ms=frame.timestamp_ms,
            metric_name="directional_contour_span",
            metric_raw=result.metric_raw,
            quality=result.quality,
            roi=_roi_tuple(result.roi),
            point_a_px=(result.point_a.x, result.point_a.y),
            point_b_px=(result.point_b.x, result.point_b.y),
            meta={
                "direction_angle_deg": float(result.direction_angle_deg),
                "component_area": int(result.component_area),
                "threshold_value": result.threshold_value,
                "raw_component_fill_ratio": result.raw_component_fill_ratio,
                "projection_point_mode": result.projection_point_mode,
                "selection_mode": _selection_mode_for_projection(result.projection_point_mode),
            },
        )


def detect_directional_contour(image: Any, config: DirectionalContourConfig) -> DirectionalContourResult:
    gray = _normalize_gray_image(image)
    roi = _clip_roi(config.analysis_roi, gray.shape)
    crop = gray[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width]
    if crop.size == 0:
        raise DirectionalContourDetectionError("roi_outside_image")

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
    mask = _cleanup_mask(cv2, mask, config)
    component_mask = _largest_component_mask(
        cv2,
        mask,
        min_target_area_px=int(config.min_target_area_px),
        direction_angle_deg=float(config.direction_angle_deg),
        component_bridge_kernel=int(config.component_bridge_kernel),
    )
    raw_component_fill_ratio = _component_foreground_fill_ratio(raw_mask, component_mask)
    boundary_mask = _actual_component_boundary_mask(source_mask, component_mask)
    contour_xy = _component_contour_xy(cv2, boundary_mask, processing_roi)
    projection_mode = str(config.projection_mode or "auto")
    if projection_mode == "auto":
        projection_mode = choose_component_direction_projection_mode(
            boundary_mask,
            processing_roi,
            float(config.direction_angle_deg),
            raw_component_fill_ratio=raw_component_fill_ratio if config.ignore_internal_texture else None,
        )
    if projection_mode == "mask_projection":
        axis_prior_px = _max_chord_axis_prior_lateral_px(config, processing)
        axis_prior_tolerance_px = _max_chord_axis_prior_tolerance_px(config, processing)
        projection = project_component_mask_onto_direction(
            boundary_mask,
            processing_roi,
            float(config.direction_angle_deg),
            image_shape=gray.shape,
            clip_region=processing_roi,
            axis_offset_px=axis_prior_px,
            axis_tolerance_px=axis_prior_tolerance_px,
        )
        projection_point_mode = "mask_projection"
    elif projection_mode == "max_chord":
        lateral_prior_px = _max_chord_axis_prior_lateral_px(config, processing)
        lateral_prior_tolerance_px = _max_chord_axis_prior_tolerance_px(config, processing)
        projection = measure_component_max_chord_along_direction(
            boundary_mask,
            processing_roi,
            float(config.direction_angle_deg),
            image_shape=gray.shape,
            clip_region=processing_roi,
            lateral_prior_px=lateral_prior_px,
            lateral_prior_tolerance_px=lateral_prior_tolerance_px,
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
        direction_angle_deg=float(config.direction_angle_deg),
        component_area=component_area,
        contour_xy=contour_xy,
        component_mask=component_mask,
        threshold_value=threshold_value,
        projection_point_mode=projection_point_mode,
        raw_component_fill_ratio=raw_component_fill_ratio,
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
        axis_offset = float(np.median(lateral[ordered]))
        candidate = {
            "span": span,
            "count": int(len(ordered)),
            "axis_offset": axis_offset,
            "min_index": int(ordered[0]),
            "max_index": int(ordered[-1]),
            "center_distance": abs(axis_offset - median_lateral),
            "prior_distance": None if lateral_prior_px is None else abs(axis_offset - float(lateral_prior_px)),
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
    prior_delta = float(candidate["prior_distance"]) - float(current["prior_distance"])
    if abs(prior_delta) > 1e-9:
        return prior_delta < 0
    span_delta = float(candidate["span"]) - float(current["span"])
    if abs(span_delta) > 1e-9:
        return span_delta > 0
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


def _max_projection_display_index(projections: np.ndarray, normal_coords: np.ndarray) -> int:
    max_projection = float(np.max(projections))
    candidates = np.flatnonzero(np.isclose(projections, max_projection, rtol=0.0, atol=1e-9))
    if len(candidates) == 0:
        return int(np.argmax(projections))
    candidate_normals = normal_coords[candidates]
    return int(candidates[int(np.argmax(candidate_normals))])


def _selection_mode_for_projection(projection_point_mode: str) -> str:
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
        axis_offset_px=_axis_offset_to_original_space(projection, geometry),
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
        raw_mask, threshold_value = _threshold_mask(cv2, crop, config)
        original_geometry = _ProcessingGeometry(crop=crop, original_roi=roi)
        allowed_mask = _processing_metric_box_mask(cv2, original_geometry, config.metric_box)
        if allowed_mask is not None:
            raw_mask = _apply_allowed_mask(cv2, raw_mask, allowed_mask)
        source_mask = _source_foreground_mask(cv2, crop, raw_mask, threshold_value, config)
        if allowed_mask is not None:
            source_mask = _apply_allowed_mask(cv2, source_mask, allowed_mask)
        mask = _cleanup_mask(cv2, raw_mask, config)
        component_mask = _largest_component_mask(
            cv2,
            mask,
            min_target_area_px=int(config.min_target_area_px),
            direction_angle_deg=float(config.direction_angle_deg),
            component_bridge_kernel=int(config.component_bridge_kernel),
        )
        boundary_mask = _actual_component_boundary_mask(source_mask, component_mask)
        axis_offset_px = float(projection.axis_offset_px)
        axis_tolerance_px = _original_axis_refinement_tolerance_px(geometry)
        if projection_point_mode == "max_chord":
            return measure_component_max_chord_along_direction(
                boundary_mask,
                roi,
                float(config.direction_angle_deg),
                image_shape=gray.shape,
                clip_region=roi,
                lateral_prior_px=axis_offset_px,
                lateral_prior_tolerance_px=axis_tolerance_px,
            )
        return project_component_mask_onto_direction(
            boundary_mask,
            roi,
            float(config.direction_angle_deg),
            image_shape=gray.shape,
            clip_region=roi,
            axis_offset_px=axis_offset_px,
            axis_tolerance_px=axis_tolerance_px,
        )
    except DirectionalContourDetectionError:
        return projection


def _axis_offset_to_original_space(
    projection: DirectionalProjection,
    geometry: _ProcessingGeometry,
) -> float:
    normal = np.array(
        [
            -math.sin(math.radians(float(projection.direction_angle_deg))),
            math.cos(math.radians(float(projection.direction_angle_deg))),
        ],
        dtype=float,
    )
    origin = np.array([float(geometry.original_roi.x), float(geometry.original_roi.y)], dtype=float)
    return float(origin @ normal) + float(projection.axis_offset_px) / max(float(geometry.scale), 1e-9)


def _original_axis_refinement_tolerance_px(geometry: _ProcessingGeometry) -> float:
    inverse_scale = 1.0 / max(float(geometry.scale), 1e-9)
    return max(3.0, min(24.0, inverse_scale * 2.5))


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
    if int(num_labels) > 48:
        return _merge_many_fragments_with_morphology(
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


def _merge_many_fragments_with_morphology(
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
