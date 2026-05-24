"""Two-point distance extractor for live setup preview and future run tracking."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import math
from typing import Any

import numpy as np
from scipy import ndimage

from src.core.contracts import VisionMetricExtractor
from src.core.models import METRIC_BOX_POINT_FLOAT_EPSILON, FramePacket, MetricBox, PixelPoint, RectRegion, ShapeMetric
from src.vision.contour_width import detect_contour_width

Roi = tuple[int, int, int, int]
ROI_FLOAT_EPSILON = 0.5


@dataclass(slots=True)
class _Component:
    coords: np.ndarray
    _pixels_cache: list[tuple[int, int]] | None = field(default=None, init=False, repr=False)

    @property
    def area(self) -> int:
        return int(len(self.coords))

    @property
    def pixels(self) -> list[tuple[int, int]]:
        if self._pixels_cache is None:
            self._pixels_cache = [
                (int(x), int(y))
                for x, y in self.coords.tolist()
            ]
        return self._pixels_cache


@dataclass(slots=True)
class _WorkingScaleTransform:
    image: np.ndarray
    analysis_roi: RectRegion
    metric_box: MetricBox
    source_crop_roi: RectRegion
    scale_x: float
    scale_y: float
    locked_points: tuple[PixelPoint, PixelPoint] | None = None


@dataclass(slots=True)
class _RoiLocalRunCandidate:
    row_bin: int
    run_length: int
    run_count: int
    run_mask: np.ndarray
    min_local_x: float
    max_local_x: float
    touches_metric_edge: bool


@dataclass(slots=True)
class _RoiLocalBoundarySelection:
    selected_coords: np.ndarray
    point_a: PixelPoint
    point_b: PixelPoint
    axis_point_a: PixelPoint
    axis_point_b: PixelPoint


class RoiLongestSpanPointDetector:
    """ROI-bounded point detector used during live setup before an observation window exists.

    Auto-detect points are constrained to an axis-aligned pair so operators only
    get horizontal or vertical anchor suggestions, never an arbitrary diagonal
    diameter through the ROI component.
    """

    def __init__(
        self,
        *,
        analysis_roi: RectRegion | None = None,
        roi_box: MetricBox | None = None,
        foreground_polarity: str = "dark_on_light",
        threshold_mode: str = "adaptive",
        threshold_margin: float = 10.0,
        ignore_internal_texture: bool = False,
        min_target_area_px: int = 200,
        quality_threshold: float = 0.75,
        sensitivity: float = 50.0,
        selection_strategy: str = "axis_aligned_span",
        working_max_width: int | None = None,
        working_max_height: int | None = None,
    ) -> None:
        self.analysis_roi = analysis_roi
        self.roi_box = roi_box
        self.foreground_polarity = foreground_polarity
        self.threshold_mode = threshold_mode
        self.threshold_margin = threshold_margin
        self.ignore_internal_texture = ignore_internal_texture
        self.min_target_area_px = min_target_area_px
        self.quality_threshold = quality_threshold
        self.sensitivity = sensitivity
        self.selection_strategy = selection_strategy
        self.working_max_width = None if working_max_width is None else max(1, int(working_max_width))
        self.working_max_height = None if working_max_height is None else max(1, int(working_max_height))

    def extract(self, frame: FramePacket) -> ShapeMetric:
        if frame.image is None:
            return self._failure_metric(frame, reason="missing_image")

        try:
            image = normalize_frame_image(frame.image)
        except ValueError as exc:
            return self._failure_metric(frame, reason="invalid_image", detail=str(exc))
        array_view = _coerce_to_grayscale_ndarray(image)
        if array_view is None:
            return self._failure_metric(frame, reason="invalid_image", detail="image could not be converted to ndarray")

        effective_roi = _resolve_roi(self.analysis_roi, image)
        if effective_roi.width == 0 or effective_roi.height == 0:
            return self._failure_metric(frame, reason="roi_outside_image", roi=effective_roi)

        if self.roi_box is not None and not _metric_box_within_region(effective_roi, self.roi_box):
            return self._failure_metric(frame, reason="roi_box_outside_roi", roi=effective_roi)

        if self.roi_box is not None and self.working_max_width is not None and self.working_max_height is not None:
            working_transform = _build_working_scale_transform(
                image=image,
                effective_box=self.roi_box,
                locked_points=None,
                max_width=self.working_max_width,
                max_height=self.working_max_height,
            )
            if working_transform is not None:
                working_metric = RoiLongestSpanPointDetector(
                    analysis_roi=working_transform.analysis_roi,
                    roi_box=working_transform.metric_box,
                    foreground_polarity=self.foreground_polarity,
                    threshold_mode=self.threshold_mode,
                    threshold_margin=self.threshold_margin,
                    ignore_internal_texture=self.ignore_internal_texture,
                    min_target_area_px=self.min_target_area_px,
                    quality_threshold=self.quality_threshold,
                    sensitivity=self.sensitivity,
                    selection_strategy=self.selection_strategy,
                ).extract(
                    FramePacket(
                        timestamp_ms=frame.timestamp_ms,
                        source=frame.source,
                        image=working_transform.image,
                        frame_id=frame.frame_id,
                        meta=dict(frame.meta),
                    )
                )
                return _remap_working_metric_to_source(
                    metric=working_metric,
                    source_frame=frame,
                    source_roi=effective_roi,
                    source_metric_box=self.roi_box,
                    working_transform=working_transform,
                    min_target_area_px=self.min_target_area_px,
                    quality_threshold=self.quality_threshold,
                    selection_strategy=self.selection_strategy,
                )

        sample_values = _sample_region_values(image, effective_roi)
        if len(sample_values) == 0:
            return self._failure_metric(frame, reason="roi_has_no_pixels", roi=effective_roi)

        threshold_value = _resolve_threshold(
            sample_values,
            mode=self.threshold_mode,
            polarity=self.foreground_polarity,
            margin=_threshold_margin_for_sensitivity(self.threshold_margin, self.sensitivity),
        )
        try:
            contour_result = detect_contour_width(
                array_view,
                analysis_roi=effective_roi,
                metric_box=self.roi_box,
                measurement_axis_deg=None,
                foreground_polarity=self.foreground_polarity,
                threshold_mode=self.threshold_mode,
                threshold_value=threshold_value,
                ignore_internal_texture=self.ignore_internal_texture,
                min_target_area_px=self.min_target_area_px,
                sensitivity=self.sensitivity,
                selection_strategy=self.selection_strategy,
                search_profile="setup",
            )
        except RuntimeError as exc:
            return self._failure_metric(
                frame,
                reason="opencv_unavailable",
                roi=effective_roi,
                detail=str(exc),
                threshold_value=threshold_value,
            )
        if contour_result is None:
            return self._failure_metric(
                frame,
                reason="no_valid_component",
                roi=effective_roi,
                threshold_value=threshold_value,
                component_area=0,
            )

        component_coords = contour_result.component_coords
        if component_coords is None or len(component_coords) == 0:
            return self._failure_metric(
                frame,
                reason="no_valid_component",
                roi=effective_roi,
                threshold_value=threshold_value,
                component_area=0,
            )
        boundary_selection: _RoiLocalBoundarySelection | None = None
        if self.roi_box is not None and self.selection_strategy == "roi_local_horizontal_boundary":
            boundary_selection = _roi_local_horizontal_boundary_selection(component_coords, self.roi_box)
            point_a, point_b = boundary_selection.point_a, boundary_selection.point_b
            selection_axis = "roi_local_horizontal"
        else:
            point_a, point_b, selection_axis = _axis_aligned_span_points(component_coords)
        if self.roi_box is not None:
            point_a, point_b = _normalize_points_for_metric_box(
                point_a,
                point_b,
                box=self.roi_box,
                region=effective_roi,
            )
        span_reference = float(max(self.roi_box.width, 1)) if self.roi_box is not None else None
        metric_raw = _distance_between(point_a, point_b)
        border_touch_count = contour_result.component_border_touch_count
        border_pixel_ratio = contour_result.component_border_pixel_ratio
        quality = (
            _score_quality(
                component_area=contour_result.component_area,
                min_target_area_px=self.min_target_area_px,
                metric_box=self.roi_box,
                metric_raw=metric_raw,
                axis_span_px=span_reference,
                penalize_full_box_coverage=self.selection_strategy == "roi_local_horizontal_boundary",
            )
            if self.roi_box is not None
            else _score_roi_quality(
                component_area=contour_result.component_area,
                min_target_area_px=self.min_target_area_px,
                roi=effective_roi,
                metric_raw=metric_raw,
                component_border_touch_count=border_touch_count,
                component_border_pixel_ratio=border_pixel_ratio,
            )
        )
        metric = ShapeMetric(
            timestamp_ms=frame.timestamp_ms,
            metric_name="roi_longest_span_points",
            metric_raw=metric_raw,
            metric_norm=None,
            quality=quality,
            roi=(effective_roi.x, effective_roi.y, effective_roi.width, effective_roi.height),
            feature_point_px=(
                int(round((point_a.x + point_b.x) / 2)),
                int(round((point_a.y + point_b.y) / 2)),
            ),
            point_a_px=(point_a.x, point_a.y),
            point_b_px=(point_b.x, point_b.y),
            baseline_px=None,
            meta={
                "source": frame.source,
                "frame_id": frame.frame_id,
                "threshold_mode": self.threshold_mode,
                "foreground_polarity": self.foreground_polarity,
                "threshold_value": contour_result.threshold_value,
                "component_area": contour_result.component_area,
                "component_border_touch_count": border_touch_count,
                "component_border_pixel_ratio": border_pixel_ratio,
                "selection_mode": "roi_local_horizontal_boundary"
                if self.roi_box is not None and self.selection_strategy == "roi_local_horizontal_boundary"
                else "roi_axis_aligned_span",
                "selection_axis": selection_axis,
                "sensitivity": self.sensitivity,
            },
        )
        if boundary_selection is not None and self.roi_box is not None:
            _attach_roi_local_boundary_points(
                metric,
                source_point_a=point_a,
                source_point_b=point_b,
                axis_point_a=boundary_selection.axis_point_a,
                axis_point_b=boundary_selection.axis_point_b,
                box=self.roi_box,
                region=effective_roi,
            )
        if quality < self.quality_threshold:
            metric.meta["reason"] = "quality_below_threshold"
        return metric

    def _failure_metric(
        self,
        frame: FramePacket,
        *,
        reason: str,
        roi: RectRegion | None = None,
        detail: str | None = None,
        threshold_value: float | None = None,
        component_area: int = 0,
    ) -> ShapeMetric:
        meta: dict[str, Any] = {
            "reason": reason,
            "source": frame.source,
            "threshold_mode": self.threshold_mode,
            "foreground_polarity": self.foreground_polarity,
            "threshold_value": threshold_value,
            "component_area": component_area,
        }
        if detail is not None:
            meta["detail"] = detail
        return ShapeMetric(
            timestamp_ms=frame.timestamp_ms,
            metric_name="roi_longest_span_points",
            metric_raw=None,
            metric_norm=None,
            quality=0.0 if reason == "missing_image" else 0.1,
            roi=None if roi is None else (roi.x, roi.y, roi.width, roi.height),
            feature_point_px=None,
            point_a_px=None,
            point_b_px=None,
            baseline_px=None,
            meta=meta,
        )


class TwoPointDistanceMetricExtractor(VisionMetricExtractor):
    def __init__(
        self,
        *,
        analysis_roi: RectRegion | None = None,
        metric_box: MetricBox | None = None,
        measurement_axis_deg: float | None = None,
        foreground_polarity: str = "dark_on_light",
        threshold_mode: str = "adaptive",
        threshold_margin: float = 10.0,
        ignore_internal_texture: bool = False,
        min_target_area_px: int = 200,
        quality_threshold: float = 0.75,
        locked_points: tuple[PixelPoint, PixelPoint] | None = None,
        sensitivity: float = 50.0,
        selection_strategy: str = "auto_extremes",
        working_max_width: int | None = None,
        working_max_height: int | None = None,
    ) -> None:
        self.analysis_roi = analysis_roi
        self.metric_box = metric_box
        self.measurement_axis_deg = measurement_axis_deg
        self.foreground_polarity = foreground_polarity
        self.threshold_mode = threshold_mode
        self.threshold_margin = threshold_margin
        self.ignore_internal_texture = ignore_internal_texture
        self.min_target_area_px = min_target_area_px
        self.quality_threshold = quality_threshold
        self.locked_points = locked_points
        self.sensitivity = sensitivity
        self.selection_strategy = selection_strategy
        self.working_max_width = None if working_max_width is None else max(1, int(working_max_width))
        self.working_max_height = None if working_max_height is None else max(1, int(working_max_height))

    def extract(self, frame: FramePacket) -> ShapeMetric:
        if frame.image is None:
            return self._failure_metric(frame, reason="missing_image")

        try:
            image = normalize_frame_image(frame.image)
        except ValueError as exc:
            return self._failure_metric(frame, reason="invalid_image", detail=str(exc))
        array_view = _coerce_to_grayscale_ndarray(image)
        if array_view is None:
            return self._failure_metric(frame, reason="invalid_image", detail="image could not be converted to ndarray")

        effective_roi = _resolve_roi(self.analysis_roi, image)
        if effective_roi.width == 0 or effective_roi.height == 0:
            return self._failure_metric(frame, reason="roi_outside_image", roi=effective_roi)

        effective_box = self.metric_box or _default_metric_box(effective_roi)
        if not _metric_box_within_region(effective_roi, effective_box):
            return self._failure_metric(frame, reason="metric_box_outside_roi", roi=effective_roi, metric_box=effective_box)

        working_transform = _build_working_scale_transform(
            image=image,
            effective_box=effective_box,
            locked_points=self.locked_points,
            max_width=self.working_max_width,
            max_height=self.working_max_height,
        )
        if working_transform is not None:
            working_metric = TwoPointDistanceMetricExtractor(
                analysis_roi=working_transform.analysis_roi,
                metric_box=working_transform.metric_box,
                measurement_axis_deg=self.measurement_axis_deg,
                foreground_polarity=self.foreground_polarity,
                threshold_mode=self.threshold_mode,
                threshold_margin=self.threshold_margin,
                ignore_internal_texture=self.ignore_internal_texture,
                min_target_area_px=self.min_target_area_px,
                quality_threshold=self.quality_threshold,
                locked_points=working_transform.locked_points,
                sensitivity=self.sensitivity,
                selection_strategy=self.selection_strategy,
            ).extract(
                FramePacket(
                    timestamp_ms=frame.timestamp_ms,
                    source=frame.source,
                    image=working_transform.image,
                    frame_id=frame.frame_id,
                    meta=dict(frame.meta),
                )
            )
            return _remap_working_metric_to_source(
                metric=working_metric,
                source_frame=frame,
                source_roi=effective_roi,
                source_metric_box=effective_box,
                working_transform=working_transform,
                min_target_area_px=self.min_target_area_px,
                quality_threshold=self.quality_threshold,
                selection_strategy=self.selection_strategy,
            )

        if self.locked_points is not None:
            point_a, point_b = self.locked_points
            if not _points_valid_for_definition(effective_roi, effective_box, point_a, point_b):
                return self._failure_metric(
                    frame,
                    reason="locked_points_outside_geometry",
                    roi=effective_roi,
                    metric_box=effective_box,
                )
            metric_raw = _distance_between(point_a, point_b)
            return self._build_metric(
                frame,
                roi=effective_roi,
                metric_box=effective_box,
                point_a=point_a,
                point_b=point_b,
                metric_raw=metric_raw,
                quality=1.0,
                threshold_value=None,
                selection_mode="locked_points",
                component_area=0,
            )

        sample_values = _sample_metric_box_values(image, effective_box)
        if len(sample_values) == 0:
            return self._failure_metric(frame, reason="metric_box_has_no_pixels", roi=effective_roi, metric_box=effective_box)

        threshold_value = _resolve_threshold(
            sample_values,
            mode=self.threshold_mode,
            polarity=self.foreground_polarity,
            margin=_threshold_margin_for_sensitivity(self.threshold_margin, self.sensitivity),
        )
        measurement_axis_deg = self.measurement_axis_deg if self.measurement_axis_deg is not None else effective_box.angle_deg
        search_profile = "setup" if self.metric_box is None else "live"
        try:
            contour_result = detect_contour_width(
                array_view,
                analysis_roi=effective_roi,
                metric_box=effective_box,
                measurement_axis_deg=measurement_axis_deg,
                foreground_polarity=self.foreground_polarity,
                threshold_mode=self.threshold_mode,
                threshold_value=threshold_value,
                ignore_internal_texture=self.ignore_internal_texture,
                min_target_area_px=self.min_target_area_px,
                sensitivity=self.sensitivity,
                selection_strategy=self.selection_strategy,
                search_profile=search_profile,
            )
        except RuntimeError as exc:
            return self._failure_metric(
                frame,
                reason="opencv_unavailable",
                roi=effective_roi,
                metric_box=effective_box,
                detail=str(exc),
                threshold_value=threshold_value,
            )
        if contour_result is None:
            return self._failure_metric(
                frame,
                reason="no_valid_component",
                roi=effective_roi,
                metric_box=effective_box,
                threshold_value=threshold_value,
                component_area=0,
            )
        component_coords = contour_result.component_coords
        if component_coords is None or len(component_coords) == 0:
            return self._failure_metric(
                frame,
                reason="no_valid_component",
                roi=effective_roi,
                metric_box=effective_box,
                threshold_value=threshold_value,
                component_area=0,
            )
        boundary_selection: _RoiLocalBoundarySelection | None = None
        if self.selection_strategy == "roi_local_horizontal_boundary":
            boundary_selection = _roi_local_horizontal_boundary_selection(component_coords, effective_box)
            point_a, point_b = boundary_selection.point_a, boundary_selection.point_b
        else:
            # `detect_contour_width()` already resolves the best direction-
            # aligned foreground run for the requested axis. Recomputing points
            # from the component-wide coordinate cloud collapses rotated
            # short-axis measurements back into global extremes and produces
            # diagonal corner picks instead of the intended width cross-
            # section.
            point_a = contour_result.point_a
            point_b = contour_result.point_b
        point_a, point_b = _normalize_points_for_metric_box(
            point_a,
            point_b,
            box=effective_box,
            region=effective_roi,
        )
        selection_mode = "roi_local_horizontal_boundary" if self.selection_strategy == "roi_local_horizontal_boundary" else "auto_extremes"
        axis_span_px = (
            float(max(effective_box.width, 1))
            if self.selection_strategy == "roi_local_horizontal_boundary"
            else _metric_box_axis_span_px(effective_box, measurement_axis_deg)
        )
        metric_raw = _distance_between(point_a, point_b)
        quality = _score_quality(
            component_area=contour_result.component_area,
            min_target_area_px=self.min_target_area_px,
            metric_box=effective_box,
            metric_raw=metric_raw,
            axis_span_px=axis_span_px,
            penalize_full_box_coverage=self.selection_strategy == "roi_local_horizontal_boundary",
        )
        metric = self._build_metric(
            frame,
            roi=effective_roi,
            metric_box=effective_box,
            point_a=point_a,
            point_b=point_b,
            metric_raw=metric_raw,
            quality=quality,
            threshold_value=contour_result.threshold_value,
            selection_mode=selection_mode,
            component_area=contour_result.component_area,
            measurement_axis_deg=measurement_axis_deg,
        )
        if boundary_selection is not None:
            _attach_roi_local_boundary_points(
                metric,
                source_point_a=point_a,
                source_point_b=point_b,
                axis_point_a=boundary_selection.axis_point_a,
                axis_point_b=boundary_selection.axis_point_b,
                box=effective_box,
                region=effective_roi,
            )
        if quality < self.quality_threshold:
            metric.meta["reason"] = "quality_below_threshold"
        return metric

    def _build_metric(
        self,
        frame: FramePacket,
        *,
        roi: RectRegion,
        metric_box: MetricBox,
        point_a: PixelPoint,
        point_b: PixelPoint,
        metric_raw: float,
        quality: float,
        threshold_value: float | None,
        selection_mode: str,
        component_area: int,
        measurement_axis_deg: float | None = None,
    ) -> ShapeMetric:
        midpoint = (
            int(round((point_a.x + point_b.x) / 2)),
            int(round((point_a.y + point_b.y) / 2)),
        )
        return ShapeMetric(
            timestamp_ms=frame.timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=metric_raw,
            metric_norm=None,
            quality=quality,
            roi=(roi.x, roi.y, roi.width, roi.height),
            feature_point_px=midpoint,
            point_a_px=(point_a.x, point_a.y),
            point_b_px=(point_b.x, point_b.y),
            baseline_px=None,
            meta={
                "source": frame.source,
                "frame_id": frame.frame_id,
                "threshold_mode": self.threshold_mode,
                "foreground_polarity": self.foreground_polarity,
                "threshold_value": threshold_value,
                "component_area": component_area,
                "selection_mode": selection_mode,
                "measurement_axis_deg": measurement_axis_deg,
                "metric_box": {
                    "center_x": metric_box.center_x,
                    "center_y": metric_box.center_y,
                    "width": metric_box.width,
                    "height": metric_box.height,
                    "angle_deg": metric_box.angle_deg,
                },
            },
        )

    def _failure_metric(
        self,
        frame: FramePacket,
        *,
        reason: str,
        roi: RectRegion | None = None,
        metric_box: MetricBox | None = None,
        detail: str | None = None,
        threshold_value: float | None = None,
        component_area: int = 0,
    ) -> ShapeMetric:
        meta: dict[str, Any] = {
            "reason": reason,
            "source": frame.source,
            "threshold_mode": self.threshold_mode,
            "foreground_polarity": self.foreground_polarity,
            "threshold_value": threshold_value,
            "component_area": component_area,
        }
        if detail is not None:
            meta["detail"] = detail
        if metric_box is not None:
            meta["metric_box"] = {
                "center_x": metric_box.center_x,
                "center_y": metric_box.center_y,
                "width": metric_box.width,
                "height": metric_box.height,
                "angle_deg": metric_box.angle_deg,
            }
        return ShapeMetric(
            timestamp_ms=frame.timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=None,
            metric_norm=None,
            quality=0.0 if reason == "missing_image" else 0.1,
            roi=None if roi is None else (roi.x, roi.y, roi.width, roi.height),
            feature_point_px=None,
            point_a_px=None,
            point_b_px=None,
            baseline_px=None,
            meta=meta,
        )


def normalize_frame_image(image: Any) -> list[list[int]]:
    if isinstance(image, np.ndarray):
        if image.ndim < 2:
            raise ValueError("image must be a 2D sequence")
        if image.shape[0] == 0 or image.shape[1] == 0:
            raise ValueError("image width and height must be greater than zero")
        if image.ndim == 2:
            if image.dtype == np.bool_:
                return image.astype(np.uint8, copy=False) * 255
            if np.issubdtype(image.dtype, np.number):
                if np.issubdtype(image.dtype, np.floating):
                    image = np.rint(image)
                return np.clip(image, 0, 255).astype(np.uint8, copy=False)
            raise ValueError("unsupported pixel type")
        if image.ndim == 3:
            if image.shape[2] == 0:
                raise ValueError("pixel channel sequence must not be empty")
            if image.dtype == np.bool_:
                image = image.astype(np.uint8, copy=False) * 255
            elif np.issubdtype(image.dtype, np.number):
                if np.issubdtype(image.dtype, np.floating):
                    image = np.rint(image)
                image = np.clip(image, 0, 255).astype(np.uint8, copy=False)
            else:
                raise ValueError("unsupported pixel type")
            return np.rint(np.mean(image, axis=2)).astype(np.uint8, copy=False)
        raise ValueError("image must be a 2D sequence")
    shape = getattr(image, "shape", None)
    if isinstance(shape, tuple) and len(shape) == 2:
        height, width = shape
        if int(height) < 1 or int(width) < 1:
            raise ValueError("image width and height must be greater than zero")
        try:
            first_row = image[0]
            first_value = first_row[0]
        except Exception as exc:
            raise ValueError("image must be a 2D sequence") from exc
        if isinstance(first_value, (bool, int, float, np.generic)):
            return image
    if hasattr(image, "tolist"):
        image = image.tolist()
    if not isinstance(image, Sequence) or isinstance(image, (str, bytes)):
        raise ValueError("image must be a 2D sequence")
    rows: list[list[int]] = []
    expected_width: int | None = None
    for row in image:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            raise ValueError("image rows must be sequences")
        normalized_row = [_pixel_to_gray(pixel) for pixel in row]
        if expected_width is None:
            expected_width = len(normalized_row)
            if expected_width == 0:
                raise ValueError("image width must be greater than zero")
        elif len(normalized_row) != expected_width:
            raise ValueError("image rows must have consistent widths")
        rows.append(normalized_row)
    if not rows:
        raise ValueError("image height must be greater than zero")
    return rows


def downsample_grayscale_image(
    image: list[list[int]],
    *,
    max_width: int = 640,
    max_height: int = 480,
) -> list[list[int]]:
    height = len(image)
    width = len(image[0]) if height > 0 else 0
    if width == 0 or height == 0:
        return [[0]]
    scale = max(width / max_width, height / max_height, 1.0)
    if scale <= 1.0:
        return [[int(value) for value in row] for row in image]
    output_width = max(1, int(width / scale))
    output_height = max(1, int(height / scale))
    downsampled: list[list[int]] = []
    for output_y in range(output_height):
        source_y = min(height - 1, int(output_y * scale))
        row: list[int] = []
        for output_x in range(output_width):
            source_x = min(width - 1, int(output_x * scale))
            row.append(int(image[source_y][source_x]))
        downsampled.append(row)
    return downsampled


def _downsample_grayscale_array(
    image: np.ndarray,
    *,
    max_width: int,
    max_height: int,
) -> tuple[np.ndarray, float, float]:
    height, width = image.shape[:2]
    if width < 1 or height < 1:
        return np.zeros((1, 1), dtype=np.uint8), 1.0, 1.0
    scale = max(width / max_width, height / max_height, 1.0)
    if scale <= 1.0:
        return image, 1.0, 1.0
    output_width = max(1, int(round(width / scale)))
    output_height = max(1, int(round(height / scale)))
    src_x = np.minimum(width - 1, np.floor(np.arange(output_width, dtype=np.float64) * (width / output_width)).astype(np.int32))
    src_y = np.minimum(height - 1, np.floor(np.arange(output_height, dtype=np.float64) * (height / output_height)).astype(np.int32))
    reduced = image[np.ix_(src_y, src_x)]
    return reduced.astype(np.uint8, copy=False), float(width / output_width), float(height / output_height)


def _pixel_to_gray(pixel: Any) -> int:
    if isinstance(pixel, bool):
        return 255 if pixel else 0
    if isinstance(pixel, (int, float)):
        return int(max(0, min(255, round(float(pixel)))))
    if isinstance(pixel, Sequence) and not isinstance(pixel, (str, bytes)):
        values = [_pixel_to_gray(channel) for channel in pixel]
        if not values:
            raise ValueError("pixel channel sequence must not be empty")
        return int(sum(values) / len(values))
    raise ValueError("unsupported pixel type")


def _resolve_roi(roi: RectRegion | None, image: list[list[int]]) -> RectRegion:
    height = len(image)
    width = len(image[0])
    if roi is None:
        return RectRegion(x=0, y=0, width=width, height=height)

    x = max(0, roi.x)
    y = max(0, roi.y)
    if x >= width or y >= height or roi.width <= 0 or roi.height <= 0:
        return RectRegion(x=x, y=y, width=0, height=0)
    clamped_width = min(roi.width, width - x)
    clamped_height = min(roi.height, height - y)
    return RectRegion(x=x, y=y, width=clamped_width, height=clamped_height)


def _default_metric_box(roi: RectRegion) -> MetricBox:
    return MetricBox(
        center_x=roi.x + roi.width // 2,
        center_y=roi.y + roi.height // 2,
        width=max(1, int(roi.width * 0.85)),
        height=max(1, int(roi.height * 0.35)),
        angle_deg=0.0,
    )


def _metric_box_within_region(region: RectRegion, box: MetricBox) -> bool:
    return all(_point_in_region_float(region, x, y) for x, y in _metric_box_corners(box))


def _points_valid_for_definition(
    region: RectRegion,
    box: MetricBox,
    point_a: PixelPoint,
    point_b: PixelPoint,
) -> bool:
    return (
        _point_in_region(region, point_a.x, point_a.y)
        and _point_in_region(region, point_b.x, point_b.y)
        and _point_in_metric_box(box, point_a.x, point_a.y)
        and _point_in_metric_box(box, point_b.x, point_b.y)
        and (point_a.x, point_a.y) != (point_b.x, point_b.y)
    )


def _sample_metric_box_values(image: list[list[int]], metric_box: MetricBox) -> list[int]:
    array_view = _as_grayscale_ndarray(image)
    if array_view is not None:
        min_x, max_x, min_y, max_y = _metric_box_bounds(metric_box, width=array_view.shape[1], height=array_view.shape[0])
        region = array_view[min_y : max_y + 1, min_x : max_x + 1]
        mask = _metric_box_mask(metric_box, min_x=min_x, max_x=max_x, min_y=min_y, max_y=max_y)
        return region[mask]
    values: list[int] = []
    min_x = max(0, int(math.floor(metric_box.center_x - metric_box.width / 2 - 1)))
    max_x = min(len(image[0]) - 1, int(math.ceil(metric_box.center_x + metric_box.width / 2 + 1)))
    min_y = max(0, int(math.floor(metric_box.center_y - metric_box.height / 2 - 1)))
    max_y = min(len(image) - 1, int(math.ceil(metric_box.center_y + metric_box.height / 2 + 1)))
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if _point_in_metric_box(metric_box, x, y):
                values.append(image[y][x])
    return values


def _sample_region_values(image: list[list[int]], region: RectRegion) -> list[int]:
    array_view = _as_grayscale_ndarray(image)
    if array_view is not None:
        max_y = min(array_view.shape[0], region.y + region.height)
        max_x = min(array_view.shape[1], region.x + region.width)
        return array_view[region.y:max_y, region.x:max_x].reshape(-1)
    values: list[int] = []
    max_y = min(len(image), region.y + region.height)
    max_x = min(len(image[0]), region.x + region.width)
    for y in range(region.y, max_y):
        values.extend(image[y][region.x:max_x])
    return values


def _resolve_threshold(
    sample_values: list[int],
    *,
    mode: str,
    polarity: str,
    margin: float,
) -> float:
    if isinstance(sample_values, np.ndarray):
        minimum = int(sample_values.min())
        maximum = int(sample_values.max())
        sorted_values = np.sort(sample_values, axis=None)
        median = int(sorted_values[len(sorted_values) // 2])
    else:
        minimum = min(sample_values)
        maximum = max(sample_values)
        sorted_values = sorted(sample_values)
        median = sorted_values[len(sorted_values) // 2]
    if mode == "binary":
        if polarity == "dark_on_light":
            return float(max(0, min(255, minimum + margin)))
        return float(max(0, min(255, maximum - margin)))
    if mode == "otsu":
        return float((minimum + maximum) / 2)
    if polarity == "dark_on_light":
        return float((minimum + median) / 2)
    return float((maximum + median) / 2)


def _select_foreground_pixels(
    image: list[list[int]],
    metric_box: MetricBox,
    *,
    threshold_value: float,
    foreground_polarity: str,
) -> set[tuple[int, int]]:
    array_view = _as_grayscale_ndarray(image)
    if array_view is not None:
        min_x, max_x, min_y, max_y = _metric_box_bounds(metric_box, width=array_view.shape[1], height=array_view.shape[0])
        region = array_view[min_y : max_y + 1, min_x : max_x + 1]
        metric_mask = _metric_box_mask(metric_box, min_x=min_x, max_x=max_x, min_y=min_y, max_y=max_y)
        foreground_mask = region <= threshold_value if foreground_polarity == "dark_on_light" else region >= threshold_value
        selected_mask = metric_mask & foreground_mask
        ys, xs = np.nonzero(selected_mask)
        return {(int(min_x + x), int(min_y + y)) for y, x in zip(ys.tolist(), xs.tolist(), strict=False)}
    pixels: set[tuple[int, int]] = set()
    min_x = max(0, int(math.floor(metric_box.center_x - metric_box.width / 2 - 1)))
    max_x = min(len(image[0]) - 1, int(math.ceil(metric_box.center_x + metric_box.width / 2 + 1)))
    min_y = max(0, int(math.floor(metric_box.center_y - metric_box.height / 2 - 1)))
    max_y = min(len(image) - 1, int(math.ceil(metric_box.center_y + metric_box.height / 2 + 1)))
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if not _point_in_metric_box(metric_box, x, y):
                continue
            value = image[y][x]
            is_foreground = value <= threshold_value if foreground_polarity == "dark_on_light" else value >= threshold_value
            if is_foreground:
                pixels.add((x, y))
    return pixels


def _select_foreground_mask(
    array_view: np.ndarray,
    metric_box: MetricBox,
    *,
    threshold_value: float,
    foreground_polarity: str,
) -> tuple[np.ndarray, int, int]:
    min_x, max_x, min_y, max_y = _metric_box_bounds(metric_box, width=array_view.shape[1], height=array_view.shape[0])
    region = array_view[min_y : max_y + 1, min_x : max_x + 1]
    metric_mask = _metric_box_mask(metric_box, min_x=min_x, max_x=max_x, min_y=min_y, max_y=max_y)
    foreground_mask = region <= threshold_value if foreground_polarity == "dark_on_light" else region >= threshold_value
    return metric_mask & foreground_mask, min_x, min_y


def _select_foreground_pixels_in_region(
    image: list[list[int]],
    region: RectRegion,
    *,
    threshold_value: float,
    foreground_polarity: str,
) -> set[tuple[int, int]]:
    array_view = _as_grayscale_ndarray(image)
    if array_view is not None:
        max_y = min(array_view.shape[0], region.y + region.height)
        max_x = min(array_view.shape[1], region.x + region.width)
        roi = array_view[region.y:max_y, region.x:max_x]
        foreground_mask = roi <= threshold_value if foreground_polarity == "dark_on_light" else roi >= threshold_value
        ys, xs = np.nonzero(foreground_mask)
        return {(int(region.x + x), int(region.y + y)) for y, x in zip(ys.tolist(), xs.tolist(), strict=False)}
    pixels: set[tuple[int, int]] = set()
    max_y = min(len(image), region.y + region.height)
    max_x = min(len(image[0]), region.x + region.width)
    for y in range(region.y, max_y):
        for x in range(region.x, max_x):
            value = image[y][x]
            is_foreground = value <= threshold_value if foreground_polarity == "dark_on_light" else value >= threshold_value
            if is_foreground:
                pixels.add((x, y))
    return pixels


def _select_foreground_region_mask(
    array_view: np.ndarray,
    region: RectRegion,
    *,
    threshold_value: float,
    foreground_polarity: str,
) -> tuple[np.ndarray, int, int]:
    max_y = min(array_view.shape[0], region.y + region.height)
    max_x = min(array_view.shape[1], region.x + region.width)
    roi = array_view[region.y:max_y, region.x:max_x]
    foreground_mask = roi <= threshold_value if foreground_polarity == "dark_on_light" else roi >= threshold_value
    return foreground_mask, region.x, region.y


def _threshold_margin_for_sensitivity(base_margin: float, sensitivity: float) -> float:
    normalized = max(0.0, min(100.0, float(sensitivity))) / 100.0
    return max(2.0, float(base_margin) * (0.5 + normalized))


def _as_grayscale_ndarray(image: Any) -> np.ndarray | None:
    if isinstance(image, np.ndarray):
        return image
    if all(hasattr(image, attr) for attr in ("_buffer", "width", "height")):
        try:
            width = int(getattr(image, "width"))
            height = int(getattr(image, "height"))
            buffer_bytes = getattr(image, "_buffer")
        except Exception:
            return None
        if width < 1 or height < 1:
            return None
        try:
            return np.frombuffer(buffer_bytes, dtype=np.uint8, count=width * height).reshape(height, width)
        except Exception:
            return None
    return None


def _coerce_to_grayscale_ndarray(image: Any) -> np.ndarray | None:
    array_view = _as_grayscale_ndarray(image)
    if array_view is not None:
        return array_view
    try:
        coerced = np.asarray(image, dtype=np.uint8)
    except Exception:
        return None
    return coerced if coerced.ndim == 2 else None


def _build_working_scale_transform(
    *,
    image: Any,
    effective_box: MetricBox,
    locked_points: tuple[PixelPoint, PixelPoint] | None,
    max_width: int | None,
    max_height: int | None,
) -> _WorkingScaleTransform | None:
    if max_width is None or max_height is None:
        return None
    array_view = _as_grayscale_ndarray(image)
    if array_view is None:
        try:
            array_view = np.asarray(image, dtype=np.uint8)
        except Exception:
            return None
    if array_view.ndim != 2:
        return None
    min_x, max_x, min_y, max_y = _metric_box_bounds(
        effective_box,
        width=int(array_view.shape[1]),
        height=int(array_view.shape[0]),
    )
    crop = array_view[min_y : max_y + 1, min_x : max_x + 1]
    if crop.size == 0:
        return None
    reduced, scale_x, scale_y = _downsample_grayscale_array(
        crop,
        max_width=max_width,
        max_height=max_height,
    )
    if scale_x <= 1.0 and scale_y <= 1.0:
        return None
    local_metric_box = _project_metric_box_to_working(
        effective_box=effective_box,
        crop_min_x=float(min_x),
        crop_min_y=float(min_y),
        scale_x=scale_x,
        scale_y=scale_y,
    )
    local_locked_points = None
    if locked_points is not None:
        local_locked_points = (
            PixelPoint(
                x=_map_source_index_to_working(int(locked_points[0].x - min_x), scale_x, int(reduced.shape[1])),
                y=_map_source_index_to_working(int(locked_points[0].y - min_y), scale_y, int(reduced.shape[0])),
            ),
            PixelPoint(
                x=_map_source_index_to_working(int(locked_points[1].x - min_x), scale_x, int(reduced.shape[1])),
                y=_map_source_index_to_working(int(locked_points[1].y - min_y), scale_y, int(reduced.shape[0])),
            ),
        )
    return _WorkingScaleTransform(
        image=reduced,
        analysis_roi=RectRegion(x=0, y=0, width=int(reduced.shape[1]), height=int(reduced.shape[0])),
        metric_box=local_metric_box,
        source_crop_roi=RectRegion(
            x=int(min_x),
            y=int(min_y),
            width=int(max_x - min_x + 1),
            height=int(max_y - min_y + 1),
        ),
        scale_x=scale_x,
        scale_y=scale_y,
        locked_points=local_locked_points,
    )


def _map_source_index_to_working(value: int, scale: float, output_size: int) -> int:
    mapped = int(round((float(value) + 0.5) / max(scale, 1e-6) - 0.5))
    return max(0, min(max(0, output_size - 1), mapped))


def _map_source_position_to_working(value: float, scale: float) -> float:
    return (float(value) + 0.5) / max(scale, 1e-6) - 0.5


def _map_working_index_to_source(value: int, scale: float, output_size: int) -> int:
    mapped = int(round((float(value) + 0.5) * scale - 0.5))
    return max(0, min(max(0, output_size - 1), mapped))


def _project_metric_box_to_working(
    *,
    effective_box: MetricBox,
    crop_min_x: float,
    crop_min_y: float,
    scale_x: float,
    scale_y: float,
) -> MetricBox:
    transformed_corners = [
        (
            _map_source_position_to_working(source_x - crop_min_x, scale_x),
            _map_source_position_to_working(source_y - crop_min_y, scale_y),
        )
        for source_x, source_y in _metric_box_corners(effective_box)
    ]
    center_x = sum(x for x, _ in transformed_corners) / len(transformed_corners)
    center_y = sum(y for _, y in transformed_corners) / len(transformed_corners)
    angle_rad = math.radians(float(effective_box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    projected_local_x: list[float] = []
    projected_local_y: list[float] = []
    for corner_x, corner_y in transformed_corners:
        translated_x = corner_x - center_x
        translated_y = corner_y - center_y
        projected_local_x.append(translated_x * cos_theta + translated_y * sin_theta)
        projected_local_y.append(-translated_x * sin_theta + translated_y * cos_theta)
    return MetricBox(
        center_x=center_x,
        center_y=center_y,
        width=max(1.0, max(projected_local_x) - min(projected_local_x)),
        height=max(1.0, max(projected_local_y) - min(projected_local_y)),
        angle_deg=float(effective_box.angle_deg),
    )


def _remap_working_metric_to_source(
    *,
    metric: ShapeMetric,
    source_frame: FramePacket,
    source_roi: RectRegion,
    source_metric_box: MetricBox,
    working_transform: _WorkingScaleTransform,
    min_target_area_px: int,
    quality_threshold: float,
    selection_strategy: str,
) -> ShapeMetric:
    if metric.metric_raw is None or metric.point_a_px is None or metric.point_b_px is None:
        return ShapeMetric(
            timestamp_ms=metric.timestamp_ms,
            metric_name=metric.metric_name,
            metric_raw=metric.metric_raw,
            metric_norm=metric.metric_norm,
            quality=metric.quality,
            roi=(source_roi.x, source_roi.y, source_roi.width, source_roi.height),
            feature_point_px=metric.feature_point_px,
            point_a_px=metric.point_a_px,
            point_b_px=metric.point_b_px,
            baseline_px=metric.baseline_px,
            meta={
                **metric.meta,
                "working_scale_x": working_transform.scale_x,
                "working_scale_y": working_transform.scale_y,
            },
        )

    def _map_working_point_to_source(point: PixelPoint) -> PixelPoint:
        return PixelPoint(
            x=int(
                working_transform.source_crop_roi.x
                + _map_working_index_to_source(
                    point.x,
                    working_transform.scale_x,
                    working_transform.source_crop_roi.width,
                )
            ),
            y=int(
                working_transform.source_crop_roi.y
                + _map_working_index_to_source(
                    point.y,
                    working_transform.scale_y,
                    working_transform.source_crop_roi.height,
                )
            ),
        )

    def _map_meta_point_to_source(key: str) -> PixelPoint | None:
        value = metric.meta.get(key)
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return None
        try:
            return _map_working_point_to_source(PixelPoint(x=int(value[0]), y=int(value[1])))
        except (TypeError, ValueError):
            return None

    local_a = PixelPoint(x=int(metric.point_a_px[0]), y=int(metric.point_a_px[1]))
    local_b = PixelPoint(x=int(metric.point_b_px[0]), y=int(metric.point_b_px[1]))
    source_a = _map_working_point_to_source(local_a)
    source_b = _map_working_point_to_source(local_b)
    source_a, source_b = _normalize_points_for_metric_box(
        source_a,
        source_b,
        box=source_metric_box,
        region=source_roi,
    )
    source_metric_raw = _distance_between(source_a, source_b)
    measurement_axis_deg = metric.meta.get("measurement_axis_deg")
    axis_span_px = (
        float(max(source_metric_box.width, 1))
        if selection_strategy == "roi_local_horizontal_boundary"
        else _metric_box_axis_span_px(
            source_metric_box,
            float(measurement_axis_deg if measurement_axis_deg is not None else source_metric_box.angle_deg),
        )
    )
    source_component_area = int(round(float(metric.meta.get("component_area") or 0) * working_transform.scale_x * working_transform.scale_y))
    source_quality = _score_quality(
        component_area=source_component_area,
        min_target_area_px=min_target_area_px,
        metric_box=source_metric_box,
        metric_raw=source_metric_raw,
        axis_span_px=axis_span_px,
        penalize_full_box_coverage=selection_strategy == "roi_local_horizontal_boundary",
    )
    meta = dict(metric.meta)
    meta["component_area"] = source_component_area
    meta["working_scale_x"] = working_transform.scale_x
    meta["working_scale_y"] = working_transform.scale_y
    meta["working_crop_source_roi"] = {
        "x": int(working_transform.source_crop_roi.x),
        "y": int(working_transform.source_crop_roi.y),
        "width": int(working_transform.source_crop_roi.width),
        "height": int(working_transform.source_crop_roi.height),
    }
    # These preview-overlay helpers are consumed in measurement-frame local space,
    # so keep them relative to the captured frame origin instead of analysis_roi.
    meta["point_a_px_local"] = [int(source_a.x), int(source_a.y)]
    meta["point_b_px_local"] = [int(source_b.x), int(source_b.y)]
    source_meta_a = _map_meta_point_to_source("source_point_a_px") or source_a
    source_meta_b = _map_meta_point_to_source("source_point_b_px") or source_b
    axis_meta_a = _map_meta_point_to_source("axis_point_a_px") or source_meta_a
    axis_meta_b = _map_meta_point_to_source("axis_point_b_px") or source_meta_b
    axis_meta_a, axis_meta_b = _normalize_points_for_metric_box(
        axis_meta_a,
        axis_meta_b,
        box=source_metric_box,
        region=source_roi,
    )
    meta["source_point_a_px"] = (int(source_meta_a.x), int(source_meta_a.y))
    meta["source_point_b_px"] = (int(source_meta_b.x), int(source_meta_b.y))
    meta["axis_point_a_px"] = (int(axis_meta_a.x), int(axis_meta_a.y))
    meta["axis_point_b_px"] = (int(axis_meta_b.x), int(axis_meta_b.y))
    if source_quality < quality_threshold:
        meta["reason"] = "quality_below_threshold"
    elif meta.get("reason") == "quality_below_threshold":
        meta.pop("reason", None)
    return ShapeMetric(
        timestamp_ms=metric.timestamp_ms,
        metric_name=metric.metric_name,
        metric_raw=source_metric_raw,
        metric_norm=metric.metric_norm,
        quality=source_quality,
        roi=(source_roi.x, source_roi.y, source_roi.width, source_roi.height),
        feature_point_px=(
            int(round((source_a.x + source_b.x) / 2)),
            int(round((source_a.y + source_b.y) / 2)),
        ),
        point_a_px=(source_a.x, source_a.y),
        point_b_px=(source_b.x, source_b.y),
        baseline_px=metric.baseline_px,
        meta=meta,
    )


def _metric_box_bounds(metric_box: MetricBox, *, width: int, height: int) -> tuple[int, int, int, int]:
    corners = _metric_box_corners(metric_box)
    min_x = max(0, int(math.floor(min(x for x, _ in corners) - 1.0)))
    max_x = min(width - 1, int(math.ceil(max(x for x, _ in corners) + 1.0)))
    min_y = max(0, int(math.floor(min(y for _, y in corners) - 1.0)))
    max_y = min(height - 1, int(math.ceil(max(y for _, y in corners) + 1.0)))
    return min_x, max_x, min_y, max_y


def _metric_box_mask(
    metric_box: MetricBox,
    *,
    min_x: int,
    max_x: int,
    min_y: int,
    max_y: int,
) -> np.ndarray:
    y_coords, x_coords = np.ogrid[min_y : max_y + 1, min_x : max_x + 1]
    angle_rad = math.radians(metric_box.angle_deg)
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = x_coords - float(metric_box.center_x)
    translated_y = y_coords - float(metric_box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return (np.abs(local_x) <= (metric_box.width / 2)) & (np.abs(local_y) <= (metric_box.height / 2))


def _pixel_coords_array(pixels: Sequence[tuple[int, int]] | set[tuple[int, int]]) -> np.ndarray:
    if isinstance(pixels, np.ndarray):
        return pixels.astype(np.int32, copy=False)
    if not pixels:
        return np.empty((0, 2), dtype=np.int32)
    return np.asarray(list(pixels), dtype=np.int32)


def _pixels_to_mask(pixels: Sequence[tuple[int, int]] | set[tuple[int, int]]) -> tuple[np.ndarray, int, int]:
    coords = _pixel_coords_array(pixels)
    if len(coords) == 0:
        return np.zeros((0, 0), dtype=bool), 0, 0
    min_x = int(coords[:, 0].min())
    max_x = int(coords[:, 0].max())
    min_y = int(coords[:, 1].min())
    max_y = int(coords[:, 1].max())
    mask = np.zeros((max_y - min_y + 1, max_x - min_x + 1), dtype=bool)
    mask[coords[:, 1] - min_y, coords[:, 0] - min_x] = True
    return mask, min_x, min_y


def _mask_to_pixels(mask: np.ndarray, *, min_x: int, min_y: int) -> set[tuple[int, int]]:
    ys, xs = np.nonzero(mask)
    return {(int(min_x + x), int(min_y + y)) for y, x in zip(ys.tolist(), xs.tolist(), strict=False)}


def _component_from_mask(mask: np.ndarray, *, min_x: int, min_y: int) -> _Component:
    ys, xs = np.nonzero(mask)
    coords = np.column_stack((xs + int(min_x), ys + int(min_y))).astype(np.int32, copy=False)
    return _Component(coords=coords)


def _best_local_band_index(coords: np.ndarray, local_y: np.ndarray, candidate_mask: np.ndarray) -> int:
    candidate_indices = np.flatnonzero(candidate_mask)
    candidate_local_abs_y = np.abs(local_y[candidate_indices])
    candidate_y = coords[candidate_indices, 1]
    candidate_x = coords[candidate_indices, 0]
    order = np.lexsort((candidate_x, candidate_y, candidate_local_abs_y))
    return int(candidate_indices[int(order[0])])


def _longest_true_run(mask: np.ndarray) -> tuple[int | None, int | None]:
    best_start: int | None = None
    best_end: int | None = None
    current_start: int | None = None
    for idx, flag in enumerate(mask.tolist()):
        if flag and current_start is None:
            current_start = idx
        elif not flag and current_start is not None:
            current_end = idx - 1
            if best_start is None or (current_end - current_start) > (best_end - best_start):
                best_start = current_start
                best_end = current_end
            current_start = None
    if current_start is not None:
        current_end = len(mask) - 1
        if best_start is None or (current_end - current_start) > (best_end - best_start):
            best_start = current_start
            best_end = current_end
    return best_start, best_end


def _fill_small_false_runs_1d(mask: np.ndarray, *, max_gap_bins: int) -> np.ndarray:
    if mask.ndim != 1:
        raise ValueError("mask must be one-dimensional")
    if mask.size == 0 or max_gap_bins <= 0:
        return mask

    filled = mask.astype(bool, copy=True)
    true_indices = np.flatnonzero(filled)
    if len(true_indices) < 2:
        return filled

    previous = int(true_indices[0])
    for current in true_indices[1:]:
        gap = int(current) - previous - 1
        if 0 < gap <= max_gap_bins:
            filled[previous + 1 : int(current)] = True
        previous = int(current)
    return filled


def _texture_gap_px_for_sensitivity(sensitivity: float) -> int:
    normalized = max(0.0, min(100.0, float(sensitivity))) / 100.0
    return max(2, 2 + int(round(normalized * 12)))


def _fill_internal_texture(pixels: set[tuple[int, int]], *, max_gap_px: int = 8) -> set[tuple[int, int]]:
    if not pixels:
        return set()
    mask, min_x, min_y = _pixels_to_mask(pixels)
    filled = _fill_internal_texture_mask(mask, max_gap_px=max_gap_px)
    return _mask_to_pixels(filled, min_x=min_x, min_y=min_y)


def _fill_internal_texture_mask(mask: np.ndarray, *, max_gap_px: int = 8) -> np.ndarray:
    if mask.size == 0:
        return mask
    kernel_span = max(2, int(max_gap_px) + 1)
    horizontal = ndimage.binary_closing(mask, structure=np.ones((1, kernel_span), dtype=bool))
    vertical = ndimage.binary_closing(mask, structure=np.ones((kernel_span, 1), dtype=bool))
    return horizontal | vertical | mask


def _roi_local_longest_foreground_run_selection(
    pixels: Sequence[tuple[int, int]] | np.ndarray,
    roi_box: MetricBox,
    *,
    max_gap_bins: int = 1,
) -> _RoiLocalBoundarySelection:
    coords = _pixel_coords_array(pixels)
    if len(coords) == 0:
        raise ValueError("pixels must not be empty")

    angle_rad = math.radians(float(roi_box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = coords[:, 0].astype(np.float64) - float(roi_box.center_x)
    translated_y = coords[:, 1].astype(np.float64) - float(roi_box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta

    x_bins = np.rint(local_x).astype(np.int32)
    y_bins = np.rint(local_y).astype(np.int32)
    min_x_bin = int(x_bins.min())
    max_x_bin = int(x_bins.max())
    min_y_bin = int(y_bins.min())
    max_y_bin = int(y_bins.max())

    occupancy = np.zeros((max_y_bin - min_y_bin + 1, max_x_bin - min_x_bin + 1), dtype=bool)
    occupancy[y_bins - min_y_bin, x_bins - min_x_bin] = True

    best_mask: np.ndarray | None = None
    best_row_bin: int | None = None
    best_candidate: _RoiLocalRunCandidate | None = None
    best_key: tuple[int, int, float, int] | None = None
    candidates: list[_RoiLocalRunCandidate] = []

    for row_offset in range(occupancy.shape[0]):
        row_mask = _fill_small_false_runs_1d(occupancy[row_offset], max_gap_bins=max_gap_bins)
        active_columns = np.flatnonzero(row_mask)
        if active_columns.size < 2:
            continue
        run_start = int(active_columns[0])
        run_end = int(active_columns[-1])
        row_bin = min_y_bin + row_offset
        run_left = float(min_x_bin + run_start) - 0.5
        run_right = float(min_x_bin + run_end) + 0.5
        # Lattice-like samples often cross the ROI-local horizontal band as
        # several separated foreground segments. Use the row envelope rather
        # than the longest single segment so A/B describes the physical outer
        # span instead of an internal wire.
        candidate_mask = np.abs(local_y - float(row_bin)) <= 0.75
        run_mask = candidate_mask & (local_x >= run_left) & (local_x <= run_right)
        run_count = int(np.count_nonzero(run_mask))
        if run_count < 2:
            candidate_mask = np.abs(local_y - float(row_bin)) <= 1.25
            run_mask = candidate_mask & (local_x >= run_left) & (local_x <= run_right)
            run_count = int(np.count_nonzero(run_mask))
        if run_count < 2:
            continue
        run_length = int(run_end - run_start)
        run_local_x = local_x[run_mask]
        min_run_local_x = float(run_local_x.min())
        max_run_local_x = float(run_local_x.max())
        edge_margin = max(2.0, float(roi_box.width) * 0.10)
        touches_metric_edge = (
            min_run_local_x <= (-float(roi_box.width) / 2.0 + edge_margin)
            or max_run_local_x >= (float(roi_box.width) / 2.0 - edge_margin)
        )
        candidate = _RoiLocalRunCandidate(
            row_bin=int(row_bin),
            run_length=run_length,
            run_count=run_count,
            run_mask=run_mask,
            min_local_x=min_run_local_x,
            max_local_x=max_run_local_x,
            touches_metric_edge=touches_metric_edge,
        )
        candidates.append(candidate)
        interior_min_length = max(6, int(round(float(roi_box.width) * 0.10)))
        interior_score = 1 if not touches_metric_edge and run_length >= interior_min_length else 0
        # ROI-local A/B is defined on the operator's horizontal ROI axis. A
        # distant tail or fixture segment can produce a longer run, so row
        # distance must dominate span length; span is only a tie-breaker among
        # similarly centered candidate rows.
        candidate_key = (-abs(float(row_bin)), interior_score, run_length, run_count)
        if best_key is None or candidate_key > best_key:
            best_mask = run_mask
            best_row_bin = row_bin
            best_candidate = candidate
            best_key = candidate_key

    if best_mask is None or best_row_bin is None:
        point_a, point_b = _axis_extreme_points(coords, float(roi_box.angle_deg))
        return _RoiLocalBoundarySelection(
            selected_coords=coords,
            point_a=point_a,
            point_b=point_b,
            axis_point_a=point_a,
            axis_point_b=point_b,
        )

    selected_coords = coords[best_mask]
    row_delta = local_y - float(best_row_bin)
    selected_local_x = local_x[best_mask]
    min_local_x = float(selected_local_x.min())
    max_local_x = float(selected_local_x.max())
    min_local_x, max_local_x = _roi_local_supported_boundary_x(
        candidates,
        roi_box,
        best_row_bin=int(best_row_bin),
        best_length=best_candidate.run_length if best_candidate is not None else 0,
        best_touches_metric_edge=best_candidate.touches_metric_edge if best_candidate is not None else True,
        fallback_min_local_x=min_local_x,
        fallback_max_local_x=max_local_x,
    )
    left_mask = best_mask & (np.abs(local_x - min_local_x) <= 0.5)
    right_mask = best_mask & (np.abs(local_x - max_local_x) <= 0.5)
    if not bool(np.any(left_mask)):
        left_mask = np.abs(local_x - min_local_x) <= 0.5
    if not bool(np.any(left_mask)):
        left_mask = best_mask & (local_x <= (min_local_x + 0.5))
    if not bool(np.any(right_mask)):
        right_mask = np.abs(local_x - max_local_x) <= 0.5
    if not bool(np.any(right_mask)):
        right_mask = best_mask & (local_x >= (max_local_x - 0.5))
    left_index = _best_local_band_index(coords, row_delta, left_mask)
    right_index = _best_local_band_index(coords, row_delta, right_mask)
    left = coords[left_index]
    right = coords[right_index]
    projected_left = _metric_box_local_point(roi_box, min_local_x, 0.0)
    projected_right = _metric_box_local_point(roi_box, max_local_x, 0.0)
    return _RoiLocalBoundarySelection(
        selected_coords=selected_coords,
        point_a=PixelPoint(x=int(left[0]), y=int(left[1])),
        point_b=PixelPoint(x=int(right[0]), y=int(right[1])),
        axis_point_a=projected_left,
        axis_point_b=projected_right,
    )


def _roi_local_supported_boundary_x(
    candidates: Sequence[_RoiLocalRunCandidate],
    roi_box: MetricBox,
    *,
    best_row_bin: int,
    best_length: int,
    best_touches_metric_edge: bool,
    fallback_min_local_x: float,
    fallback_max_local_x: float,
) -> tuple[float, float]:
    if len(candidates) < 2 or best_length <= 0:
        return fallback_min_local_x, fallback_max_local_x
    row_band = max(1, min(8, int(round(float(roi_box.height) * 0.04))))
    length_tolerance = max(1, int(round(float(best_length) * 0.08)))
    supported = [
        candidate
        for candidate in candidates
        if abs(int(candidate.row_bin) - int(best_row_bin)) <= row_band
        and int(candidate.run_length) >= int(best_length) - length_tolerance
        and (best_touches_metric_edge or not candidate.touches_metric_edge)
    ]
    if len(supported) < 2:
        return fallback_min_local_x, fallback_max_local_x
    left_values = [candidate.min_local_x for candidate in supported]
    right_values = [candidate.max_local_x for candidate in supported]
    return (
        _stable_quantile(left_values, 0.15, fallback=fallback_min_local_x),
        _stable_quantile(right_values, 0.85, fallback=fallback_max_local_x),
    )


def _stable_quantile(values: Sequence[float], quantile: float, *, fallback: float) -> float:
    finite_values = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not finite_values:
        return fallback
    if len(finite_values) == 1:
        return finite_values[0]
    clamped = max(0.0, min(1.0, float(quantile)))
    index = int(round(clamped * (len(finite_values) - 1)))
    return finite_values[index]


def _roi_local_horizontal_boundary_points(
    pixels: Sequence[tuple[int, int]] | np.ndarray,
    roi_box: MetricBox,
) -> tuple[PixelPoint, PixelPoint]:
    if len(pixels) == 0:
        raise ValueError("pixels must not be empty")
    selection = _roi_local_horizontal_boundary_selection(pixels, roi_box)
    return selection.point_a, selection.point_b


def _roi_local_horizontal_boundary_selection(
    pixels: Sequence[tuple[int, int]] | np.ndarray,
    roi_box: MetricBox,
) -> _RoiLocalBoundarySelection:
    if len(pixels) == 0:
        raise ValueError("pixels must not be empty")
    return _roi_local_longest_foreground_run_selection(pixels, roi_box)


def _roi_local_horizontal_boundary_object_coords(
    pixels: Sequence[tuple[int, int]] | np.ndarray,
    roi_box: MetricBox,
) -> np.ndarray:
    selection = _roi_local_longest_foreground_run_selection(pixels, roi_box)
    return selection.selected_coords


def _attach_roi_local_boundary_points(
    metric: ShapeMetric,
    *,
    source_point_a: PixelPoint,
    source_point_b: PixelPoint,
    axis_point_a: PixelPoint,
    axis_point_b: PixelPoint,
    box: MetricBox,
    region: RectRegion,
) -> None:
    normalized_axis_a, normalized_axis_b = _normalize_points_for_metric_box(
        axis_point_a,
        axis_point_b,
        box=box,
        region=region,
    )
    metric.meta["source_point_a_px"] = (int(source_point_a.x), int(source_point_a.y))
    metric.meta["source_point_b_px"] = (int(source_point_b.x), int(source_point_b.y))
    metric.meta["axis_point_a_px"] = (int(normalized_axis_a.x), int(normalized_axis_a.y))
    metric.meta["axis_point_b_px"] = (int(normalized_axis_b.x), int(normalized_axis_b.y))


def _pick_target_component(
    pixels: set[tuple[int, int]],
    min_area_px: int,
    *,
    selection_region: RectRegion | None = None,
) -> _Component | None:
    if not pixels:
        return None
    mask, min_x, min_y = _pixels_to_mask(pixels)
    return _pick_target_component_from_mask(
        mask,
        min_area_px,
        min_x=min_x,
        min_y=min_y,
        selection_region=selection_region,
    )


def _pick_target_component_from_mask(
    mask: np.ndarray,
    min_area_px: int,
    *,
    min_x: int,
    min_y: int,
    selection_region: RectRegion | None = None,
) -> _Component | None:
    if mask.size == 0 or not bool(mask.any()):
        return None
    labels, component_count = ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
    if component_count == 0:
        return None
    component_ids = np.arange(1, component_count + 1, dtype=np.int32)
    component_areas = ndimage.sum(mask, labels=labels, index=component_ids)
    valid_ids = component_ids[np.asarray(component_areas) >= float(min_area_px)]
    if len(valid_ids) == 0:
        return None
    if selection_region is None:
        best_component_id = int(
            valid_ids[
                int(
                    np.argmax(
                        np.asarray(component_areas, dtype=np.float64)[valid_ids - 1],
                    )
                )
            ]
        )
        return _component_from_mask(labels == best_component_id, min_x=min_x, min_y=min_y)

    best_component: _Component | None = None
    best_key: tuple[float, float, int, int, float] | None = None
    for component_id in valid_ids.tolist():
        component = _component_from_mask(labels == int(component_id), min_x=min_x, min_y=min_y)
        component_key = _roi_component_selection_key(component, selection_region)
        if best_key is None or component_key > best_key:
            best_component = component
            best_key = component_key
    return best_component


def _component_border_touch_count(component: _Component, region: RectRegion) -> int:
    coords = component.coords
    touches_left = bool(np.any(coords[:, 0] == region.x))
    touches_right = bool(np.any(coords[:, 0] == (region.x + region.width - 1)))
    touches_top = bool(np.any(coords[:, 1] == region.y))
    touches_bottom = bool(np.any(coords[:, 1] == (region.y + region.height - 1)))
    return sum((touches_left, touches_right, touches_top, touches_bottom))


def _component_border_pixel_count(component: _Component, region: RectRegion) -> int:
    coords = component.coords
    border_mask = (
        (coords[:, 0] == region.x)
        | (coords[:, 0] == (region.x + region.width - 1))
        | (coords[:, 1] == region.y)
        | (coords[:, 1] == (region.y + region.height - 1))
    )
    return int(np.count_nonzero(border_mask))


def _roi_component_selection_key(component: _Component, region: RectRegion) -> tuple[float, float, int, int, float]:
    point_a, point_b, _selection_axis = _axis_aligned_span_points(component.coords)
    span = _distance_between(point_a, point_b)
    region_area = max(region.width * region.height, 1)
    region_diagonal = max(math.hypot(region.width, region.height), 1.0)
    area_ratio = max(component.area / region_area, 1e-6)
    span_ratio = min(1.0, span / region_diagonal)
    border_touch_count = _component_border_touch_count(component, region)
    border_pixel_ratio = _component_border_pixel_count(component, region) / max(component.area, 1)
    objectness = (span_ratio * math.pow(area_ratio, 0.25)) / (
        (1.0 + 0.35 * border_touch_count) * (1.0 + 8.0 * border_pixel_ratio)
    )
    return (objectness, span, component.area, -border_touch_count, -border_pixel_ratio)


def _axis_extreme_points(pixels: Sequence[tuple[int, int]] | np.ndarray, angle_deg: float) -> tuple[PixelPoint, PixelPoint]:
    coords = _pixel_coords_array(pixels)
    if len(coords) == 0:
        raise ValueError("pixels must not be empty")
    angle_rad = math.radians(angle_deg)
    axis_x = math.cos(angle_rad)
    axis_y = math.sin(angle_rad)
    orthogonal_x = -axis_y
    orthogonal_y = axis_x
    axis_projection = coords[:, 0] * axis_x + coords[:, 1] * axis_y
    orthogonal_projection = coords[:, 0] * orthogonal_x + coords[:, 1] * orthogonal_y
    min_projection = float(axis_projection.min())
    max_projection = float(axis_projection.max())
    start_candidates = coords[np.abs(axis_projection - min_projection) < 1e-6]
    end_candidates = coords[np.abs(axis_projection - max_projection) < 1e-6]
    start = _median_orthogonal_coord(start_candidates, orthogonal_projection[np.abs(axis_projection - min_projection) < 1e-6])
    end = _median_orthogonal_coord(end_candidates, orthogonal_projection[np.abs(axis_projection - max_projection) < 1e-6])
    return (PixelPoint(x=int(start[0]), y=int(start[1])), PixelPoint(x=int(end[0]), y=int(end[1])))


def _axis_aligned_span_points(pixels: Sequence[tuple[int, int]] | np.ndarray) -> tuple[PixelPoint, PixelPoint, str]:
    coords = _pixel_coords_array(pixels)
    if len(coords) == 0:
        raise ValueError("pixels must not be empty")
    if len(coords) == 1:
        point = coords[0]
        return PixelPoint(x=int(point[0]), y=int(point[1])), PixelPoint(x=int(point[0]), y=int(point[1])), "horizontal"

    min_x = int(coords[:, 0].min())
    max_x = int(coords[:, 0].max())
    min_y = int(coords[:, 1].min())
    max_y = int(coords[:, 1].max())
    horizontal_span = max_x - min_x
    vertical_span = max_y - min_y

    if horizontal_span >= vertical_span:
        shared_y = _median_scalar(coords[:, 1])
        return PixelPoint(x=min_x, y=shared_y), PixelPoint(x=max_x, y=shared_y), "horizontal"

    shared_x = _median_scalar(coords[:, 0])
    return PixelPoint(x=shared_x, y=min_y), PixelPoint(x=shared_x, y=max_y), "vertical"


def _longest_span_points(pixels: list[tuple[int, int]]) -> tuple[PixelPoint, PixelPoint]:
    if not pixels:
        raise ValueError("pixels must not be empty")
    if len(pixels) == 1:
        point = pixels[0]
        return PixelPoint(x=point[0], y=point[1]), PixelPoint(x=point[0], y=point[1])
    hull = _convex_hull(pixels)
    if len(hull) == 1:
        point = hull[0]
        return PixelPoint(x=point[0], y=point[1]), PixelPoint(x=point[0], y=point[1])
    if len(hull) == 2:
        return PixelPoint(x=hull[0][0], y=hull[0][1]), PixelPoint(x=hull[1][0], y=hull[1][1])
    start, end = _rotating_calipers_diameter(hull)
    return PixelPoint(x=start[0], y=start[1]), PixelPoint(x=end[0], y=end[1])


def _median_orthogonal_coord(candidates: np.ndarray, orthogonal_projection: np.ndarray) -> np.ndarray:
    order = np.argsort(orthogonal_projection, kind="stable")
    return candidates[int(order[len(order) // 2])]


def _median_scalar(values: Sequence[int] | np.ndarray) -> int:
    if len(values) == 0:
        raise ValueError("values must not be empty")
    array = np.asarray(values, dtype=np.int32).reshape(-1)
    order = np.argsort(array, kind="stable")
    return int(array[int(order[len(order) // 2])])


def _score_quality(
    *,
    component_area: int,
    min_target_area_px: int,
    metric_box: MetricBox,
    metric_raw: float,
    axis_span_px: float | None = None,
    penalize_full_box_coverage: bool = False,
) -> float:
    area_ratio = min(1.0, component_area / max(min_target_area_px, 1))
    span_reference = axis_span_px if axis_span_px is not None else max(metric_box.width, metric_box.height, 1)
    span_ratio = min(1.0, metric_raw / max(span_reference, 1))
    score = min(1.0, max(0.05, 0.5 * area_ratio + 0.5 * span_ratio))
    if penalize_full_box_coverage:
        box_area = max(float(metric_box.width) * float(metric_box.height), 1.0)
        box_coverage_ratio = float(component_area) / box_area
        if box_coverage_ratio >= 0.85 and span_ratio >= 0.95:
            return min(score, 0.35)
    return score


def _metric_box_axis_span_px(metric_box: MetricBox, measurement_axis_deg: float) -> float:
    delta = abs((measurement_axis_deg - metric_box.angle_deg) % 180.0)
    if delta > 90.0:
        delta = 180.0 - delta
    return float(metric_box.width if delta <= 45.0 else metric_box.height)


def _score_roi_quality(
    *,
    component_area: int,
    min_target_area_px: int,
    roi: RectRegion,
    metric_raw: float,
    component_border_touch_count: int = 0,
    component_border_pixel_ratio: float = 0.0,
) -> float:
    area_ratio = min(1.0, component_area / max(min_target_area_px, 1))
    span_ratio = min(1.0, metric_raw / max(math.hypot(roi.width, roi.height), 1.0))
    border_penalty = min(0.3, 0.05 * component_border_touch_count + 0.5 * component_border_pixel_ratio)
    score = 0.55 * area_ratio + 0.75 * span_ratio - border_penalty
    return min(1.0, max(0.05, score))


def _distance_between(point_a: PixelPoint, point_b: PixelPoint) -> float:
    return math.hypot(point_b.x - point_a.x, point_b.y - point_a.y)


def _convex_hull(points: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    unique_points = sorted(set(points))
    if len(unique_points) <= 1:
        return list(unique_points)

    def _cross(origin: tuple[int, int], first: tuple[int, int], second: tuple[int, int]) -> int:
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (first[1] - origin[1]) * (second[0] - origin[0])

    lower: list[tuple[int, int]] = []
    for point in unique_points:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper: list[tuple[int, int]] = []
    for point in reversed(unique_points):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def _rotating_calipers_diameter(hull: Sequence[tuple[int, int]]) -> tuple[tuple[int, int], tuple[int, int]]:
    def _area_twice(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> int:
        return abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

    def _distance_sq(first: tuple[int, int], second: tuple[int, int]) -> int:
        return (first[0] - second[0]) ** 2 + (first[1] - second[1]) ** 2

    count = len(hull)
    if count == 2:
        return hull[0], hull[1]

    best_pair = (hull[0], hull[1])
    best_distance_sq = _distance_sq(*best_pair)
    j = 1
    for i in range(count):
        next_i = (i + 1) % count
        while _area_twice(hull[i], hull[next_i], hull[(j + 1) % count]) > _area_twice(hull[i], hull[next_i], hull[j]):
            j = (j + 1) % count
        for candidate in (hull[i], hull[next_i]):
            for other in (hull[j], hull[(j + 1) % count]):
                distance_sq = _distance_sq(candidate, other)
                if distance_sq > best_distance_sq:
                    best_distance_sq = distance_sq
                    best_pair = (candidate, other)
    return best_pair


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


def _point_in_metric_box(box: MetricBox, x: int, y: int) -> bool:
    angle_rad = math.radians(box.angle_deg)
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = x - box.center_x
    translated_y = y - box.center_y
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return (
        abs(local_x) <= box.width / 2 + METRIC_BOX_POINT_FLOAT_EPSILON
        and abs(local_y) <= box.height / 2 + METRIC_BOX_POINT_FLOAT_EPSILON
    )


def _metric_box_local_point(box: MetricBox, local_x: float, local_y: float) -> PixelPoint:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    world_x = float(box.center_x) + float(local_x) * cos_theta - float(local_y) * sin_theta
    world_y = float(box.center_y) + float(local_x) * sin_theta + float(local_y) * cos_theta
    rounded = PixelPoint(x=int(round(world_x)), y=int(round(world_y)))
    if _point_in_metric_box(box, rounded.x, rounded.y):
        return rounded
    best: tuple[float, PixelPoint] | None = None
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            candidate = PixelPoint(x=rounded.x + dx, y=rounded.y + dy)
            if not _point_in_metric_box(box, candidate.x, candidate.y):
                continue
            distance_sq = (float(candidate.x) - world_x) ** 2 + (float(candidate.y) - world_y) ** 2
            if best is None or distance_sq < best[0]:
                best = (distance_sq, candidate)
    return rounded if best is None else best[1]


def _normalize_points_for_metric_box(
    point_a: PixelPoint,
    point_b: PixelPoint,
    *,
    box: MetricBox,
    region: RectRegion,
) -> tuple[PixelPoint, PixelPoint]:
    normalized_a = point_a if _point_in_metric_box(box, point_a.x, point_a.y) else _clamp_point_into_metric_box(point_a, box, region)
    normalized_b = point_b if _point_in_metric_box(box, point_b.x, point_b.y) else _clamp_point_into_metric_box(point_b, box, region)
    if (normalized_a.x, normalized_a.y) != (normalized_b.x, normalized_b.y):
        return normalized_a, normalized_b
    return _default_metric_box_edge_points(box, region)


def _clamp_point_into_metric_box(point: PixelPoint, box: MetricBox, region: RectRegion) -> PixelPoint:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = float(point.x) - float(box.center_x)
    translated_y = float(point.y) - float(box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    local_x = min(max(local_x, -float(box.width) / 2.0), float(box.width) / 2.0)
    local_y = min(max(local_y, -float(box.height) / 2.0), float(box.height) / 2.0)
    world_x = float(box.center_x) + local_x * cos_theta - local_y * sin_theta
    world_y = float(box.center_y) + local_x * sin_theta + local_y * cos_theta
    return PixelPoint(
        x=max(region.x, min(region.x + region.width - 1, int(round(world_x)))),
        y=max(region.y, min(region.y + region.height - 1, int(round(world_y)))),
    )


def _default_metric_box_edge_points(box: MetricBox, region: RectRegion) -> tuple[PixelPoint, PixelPoint]:
    return (
        _clamp_point_into_metric_box(
            PixelPoint(x=int(round(box.center_x - box.width / 2.0)), y=int(round(box.center_y))),
            box,
            region,
        ),
        _clamp_point_into_metric_box(
            PixelPoint(x=int(round(box.center_x + box.width / 2.0)), y=int(round(box.center_y))),
            box,
            region,
        ),
    )


def _point_in_region(region: RectRegion, x: int, y: int) -> bool:
    return region.x <= x < (region.x + region.width) and region.y <= y < (region.y + region.height)


def _point_in_region_float(region: RectRegion, x: float, y: float) -> bool:
    return (
        (region.x - ROI_FLOAT_EPSILON) <= x <= (region.x + region.width + ROI_FLOAT_EPSILON)
        and (region.y - ROI_FLOAT_EPSILON) <= y <= (region.y + region.height + ROI_FLOAT_EPSILON)
    )
