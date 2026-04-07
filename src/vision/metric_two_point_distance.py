"""Two-point distance extractor for live setup preview and future run tracking."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import math
from typing import Any

import numpy as np
from scipy import ndimage

from src.core.contracts import VisionMetricExtractor
from src.core.models import FramePacket, MetricBox, PixelPoint, RectRegion, ShapeMetric

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

    def extract(self, frame: FramePacket) -> ShapeMetric:
        if frame.image is None:
            return self._failure_metric(frame, reason="missing_image")

        try:
            image = normalize_frame_image(frame.image)
        except ValueError as exc:
            return self._failure_metric(frame, reason="invalid_image", detail=str(exc))
        array_view = _as_grayscale_ndarray(image)

        effective_roi = _resolve_roi(self.analysis_roi, image)
        if effective_roi.width == 0 or effective_roi.height == 0:
            return self._failure_metric(frame, reason="roi_outside_image", roi=effective_roi)

        sample_values = _sample_region_values(image, effective_roi)
        if len(sample_values) == 0:
            return self._failure_metric(frame, reason="roi_has_no_pixels", roi=effective_roi)

        threshold_value = _resolve_threshold(
            sample_values,
            mode=self.threshold_mode,
            polarity=self.foreground_polarity,
            margin=_threshold_margin_for_sensitivity(self.threshold_margin, self.sensitivity),
        )
        if array_view is not None and self.roi_box is not None:
            if not _metric_box_within_region(effective_roi, self.roi_box):
                return self._failure_metric(frame, reason="roi_box_outside_roi", roi=effective_roi)
            selected_mask, min_x, min_y = _select_foreground_mask(
                array_view,
                self.roi_box,
                threshold_value=threshold_value,
                foreground_polarity=self.foreground_polarity,
            )
            if self.ignore_internal_texture or self.sensitivity > 0:
                selected_mask = _fill_internal_texture_mask(
                    selected_mask,
                    max_gap_px=_texture_gap_px_for_sensitivity(self.sensitivity),
                )
            component = _pick_target_component_from_mask(
                selected_mask,
                self.min_target_area_px,
                min_x=min_x,
                min_y=min_y,
                selection_region=effective_roi,
            )
        elif array_view is not None:
            selected_mask, min_x, min_y = _select_foreground_region_mask(
                array_view,
                effective_roi,
                threshold_value=threshold_value,
                foreground_polarity=self.foreground_polarity,
            )
            if self.ignore_internal_texture:
                selected_mask = _fill_internal_texture_mask(
                    selected_mask,
                    max_gap_px=_texture_gap_px_for_sensitivity(self.sensitivity),
                )
            component = _pick_target_component_from_mask(
                selected_mask,
                self.min_target_area_px,
                min_x=min_x,
                min_y=min_y,
                selection_region=effective_roi,
            )
        elif self.roi_box is not None:
            if not _metric_box_within_region(effective_roi, self.roi_box):
                return self._failure_metric(frame, reason="roi_box_outside_roi", roi=effective_roi)
            selected_pixels = _select_foreground_pixels(
                image,
                self.roi_box,
                threshold_value=threshold_value,
                foreground_polarity=self.foreground_polarity,
            )
            if self.ignore_internal_texture or self.sensitivity > 0:
                selected_pixels = _fill_internal_texture(
                    selected_pixels,
                    max_gap_px=_texture_gap_px_for_sensitivity(self.sensitivity),
                )
            component = _pick_target_component(
                selected_pixels,
                self.min_target_area_px,
                selection_region=effective_roi,
            )
        else:
            selected_pixels = _select_foreground_pixels_in_region(
                image,
                effective_roi,
                threshold_value=threshold_value,
                foreground_polarity=self.foreground_polarity,
            )
            if self.ignore_internal_texture:
                selected_pixels = _fill_internal_texture(
                    selected_pixels,
                    max_gap_px=_texture_gap_px_for_sensitivity(self.sensitivity),
                )
            component = _pick_target_component(
                selected_pixels,
                self.min_target_area_px,
                selection_region=effective_roi,
            )
        if component is None:
            return self._failure_metric(
                frame,
                reason="no_valid_component",
                roi=effective_roi,
                threshold_value=threshold_value,
                component_area=0,
            )

        if self.roi_box is not None and self.selection_strategy == "roi_local_horizontal_boundary":
            boundary_coords = _roi_local_horizontal_boundary_object_coords(component.coords, self.roi_box)
            point_a, point_b = _roi_local_horizontal_boundary_points(boundary_coords, self.roi_box)
            component = _Component(coords=boundary_coords)
            selection_axis = "roi_local_horizontal"
            span_reference = float(max(self.roi_box.width, 1))
        else:
            point_a, point_b, selection_axis = _axis_aligned_span_points(component.pixels)
            span_reference = None
        metric_raw = _distance_between(point_a, point_b)
        border_touch_count = _component_border_touch_count(component, effective_roi)
        border_pixel_ratio = _component_border_pixel_count(component, effective_roi) / max(component.area, 1)
        quality = (
            _score_quality(
                component_area=component.area,
                min_target_area_px=self.min_target_area_px,
                metric_box=self.roi_box,
                metric_raw=metric_raw,
                axis_span_px=span_reference,
            )
            if self.roi_box is not None
            else _score_roi_quality(
                component_area=component.area,
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
                "threshold_value": threshold_value,
                "component_area": component.area,
                "component_border_touch_count": border_touch_count,
                "component_border_pixel_ratio": border_pixel_ratio,
                "selection_mode": "roi_local_horizontal_boundary"
                if self.roi_box is not None and self.selection_strategy == "roi_local_horizontal_boundary"
                else "roi_axis_aligned_span",
                "selection_axis": selection_axis,
                "sensitivity": self.sensitivity,
            },
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

    def extract(self, frame: FramePacket) -> ShapeMetric:
        if frame.image is None:
            return self._failure_metric(frame, reason="missing_image")

        try:
            image = normalize_frame_image(frame.image)
        except ValueError as exc:
            return self._failure_metric(frame, reason="invalid_image", detail=str(exc))
        array_view = _as_grayscale_ndarray(image)

        effective_roi = _resolve_roi(self.analysis_roi, image)
        if effective_roi.width == 0 or effective_roi.height == 0:
            return self._failure_metric(frame, reason="roi_outside_image", roi=effective_roi)

        effective_box = self.metric_box or _default_metric_box(effective_roi)
        if not _metric_box_within_region(effective_roi, effective_box):
            return self._failure_metric(frame, reason="metric_box_outside_roi", roi=effective_roi, metric_box=effective_box)

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
        if array_view is not None:
            selected_mask, min_x, min_y = _select_foreground_mask(
                array_view,
                effective_box,
                threshold_value=threshold_value,
                foreground_polarity=self.foreground_polarity,
            )
            if self.ignore_internal_texture or self.selection_strategy == "roi_local_horizontal_boundary":
                selected_mask = _fill_internal_texture_mask(
                    selected_mask,
                    max_gap_px=_texture_gap_px_for_sensitivity(self.sensitivity),
                )
            component = _pick_target_component_from_mask(
                selected_mask,
                self.min_target_area_px,
                min_x=min_x,
                min_y=min_y,
            )
        else:
            selected_pixels = _select_foreground_pixels(
                image,
                effective_box,
                threshold_value=threshold_value,
                foreground_polarity=self.foreground_polarity,
            )
            if self.ignore_internal_texture or self.selection_strategy == "roi_local_horizontal_boundary":
                selected_pixels = _fill_internal_texture(
                    selected_pixels,
                    max_gap_px=_texture_gap_px_for_sensitivity(self.sensitivity),
                )
            component = _pick_target_component(selected_pixels, self.min_target_area_px)
        if component is None:
            return self._failure_metric(
                frame,
                reason="no_valid_component",
                roi=effective_roi,
                metric_box=effective_box,
                threshold_value=threshold_value,
                component_area=0,
            )

        measurement_axis_deg = self.measurement_axis_deg if self.measurement_axis_deg is not None else effective_box.angle_deg
        if self.selection_strategy == "roi_local_horizontal_boundary":
            boundary_coords = _roi_local_horizontal_boundary_object_coords(component.coords, effective_box)
            point_a, point_b = _roi_local_horizontal_boundary_points(boundary_coords, effective_box)
            component = _Component(coords=boundary_coords)
            selection_mode = "roi_local_horizontal_boundary"
            axis_span_px = float(max(effective_box.width, 1))
        else:
            point_a, point_b = _axis_extreme_points(component.pixels, measurement_axis_deg)
            selection_mode = "auto_extremes"
            axis_span_px = _metric_box_axis_span_px(effective_box, measurement_axis_deg)
        metric_raw = _distance_between(point_a, point_b)
        quality = _score_quality(
            component_area=component.area,
            min_target_area_px=self.min_target_area_px,
            metric_box=effective_box,
            metric_raw=metric_raw,
            axis_span_px=axis_span_px,
        )
        metric = self._build_metric(
            frame,
            roi=effective_roi,
            metric_box=effective_box,
            point_a=point_a,
            point_b=point_b,
            metric_raw=metric_raw,
            quality=quality,
            threshold_value=threshold_value,
            selection_mode=selection_mode,
            component_area=component.area,
            measurement_axis_deg=measurement_axis_deg,
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
    width = len(image[0]) if image else 0
    if width == 0 or height == 0:
        return [[0]]
    scale = max(width / max_width, height / max_height, 1.0)
    if scale <= 1.0:
        return [row[:] for row in image]
    output_width = max(1, int(width / scale))
    output_height = max(1, int(height / scale))
    downsampled: list[list[int]] = []
    for output_y in range(output_height):
        source_y = min(height - 1, int(output_y * scale))
        row: list[int] = []
        for output_x in range(output_width):
            source_x = min(width - 1, int(output_x * scale))
            row.append(image[source_y][source_x])
        downsampled.append(row)
    return downsampled


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


def _metric_box_bounds(metric_box: MetricBox, *, width: int, height: int) -> tuple[int, int, int, int]:
    min_x = max(0, int(math.floor(metric_box.center_x - metric_box.width / 2 - 1)))
    max_x = min(width - 1, int(math.ceil(metric_box.center_x + metric_box.width / 2 + 1)))
    min_y = max(0, int(math.floor(metric_box.center_y - metric_box.height / 2 - 1)))
    max_y = min(height - 1, int(math.ceil(metric_box.center_y + metric_box.height / 2 + 1)))
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


def _roi_local_horizontal_boundary_points(
    pixels: Sequence[tuple[int, int]] | np.ndarray,
    roi_box: MetricBox,
) -> tuple[PixelPoint, PixelPoint]:
    if len(pixels) == 0:
        raise ValueError("pixels must not be empty")

    coords = _pixel_coords_array(pixels)
    angle_rad = math.radians(float(roi_box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = coords[:, 0].astype(np.float64) - float(roi_box.center_x)
    translated_y = coords[:, 1].astype(np.float64) - float(roi_box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta

    max_band = max(1.0, float(roi_box.height) / 2.0)
    band = 0.75
    selected_mask = np.ones(len(coords), dtype=bool)
    while band <= max_band:
        candidate_mask = np.abs(local_y) <= band
        if int(np.count_nonzero(candidate_mask)) >= 2:
            selected_mask = candidate_mask
            break
        band += 0.5

    selected_local_x = local_x[selected_mask]
    min_local_x = float(selected_local_x.min())
    max_local_x = float(selected_local_x.max())
    left_mask = selected_mask & (np.abs(local_x - min_local_x) <= 0.5)
    right_mask = selected_mask & (np.abs(local_x - max_local_x) <= 0.5)
    left_index = _best_local_band_index(coords, local_y, left_mask)
    right_index = _best_local_band_index(coords, local_y, right_mask)
    left = coords[left_index]
    right = coords[right_index]
    return PixelPoint(x=int(left[0]), y=int(left[1])), PixelPoint(x=int(right[0]), y=int(right[1]))


def _roi_local_horizontal_boundary_object_coords(
    pixels: Sequence[tuple[int, int]] | np.ndarray,
    roi_box: MetricBox,
) -> np.ndarray:
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

    max_band = max(1.0, float(roi_box.height) / 2.0)
    band = 0.75
    best_mask = np.ones(len(coords), dtype=bool)
    best_span = -1

    while band <= max_band:
        band_mask = np.abs(local_y) <= band
        if int(np.count_nonzero(band_mask)) < 2:
            band += 0.5
            continue
        candidate_indices = np.flatnonzero(band_mask)
        candidate_local_x = np.rint(local_x[candidate_indices]).astype(np.int32)
        min_bin = int(candidate_local_x.min())
        max_bin = int(candidate_local_x.max())
        occupancy = np.zeros(max_bin - min_bin + 1, dtype=bool)
        occupancy[candidate_local_x - min_bin] = True
        closed = _fill_small_false_runs_1d(occupancy, max_gap_bins=1)
        start, end = _longest_true_run(closed)
        if start is None or end is None:
            band += 0.5
            continue
        run_left = min_bin + start - 0.5
        run_right = min_bin + end + 0.5
        run_mask = band_mask & (local_x >= run_left) & (local_x <= run_right)
        run_span = end - start
        if run_span > best_span and int(np.count_nonzero(run_mask)) >= 2:
            best_mask = run_mask
            best_span = run_span
        band += 0.5

    return coords[best_mask]


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
) -> float:
    area_ratio = min(1.0, component_area / max(min_target_area_px, 1))
    span_reference = axis_span_px if axis_span_px is not None else max(metric_box.width, metric_box.height, 1)
    span_ratio = min(1.0, metric_raw / max(span_reference, 1))
    return min(1.0, max(0.05, 0.4 * area_ratio + 0.6 * span_ratio))


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
    return abs(local_x) <= box.width / 2 and abs(local_y) <= box.height / 2


def _point_in_region(region: RectRegion, x: int, y: int) -> bool:
    return region.x <= x < (region.x + region.width) and region.y <= y < (region.y + region.height)


def _point_in_region_float(region: RectRegion, x: float, y: float) -> bool:
    return (
        (region.x - ROI_FLOAT_EPSILON) <= x <= (region.x + region.width + ROI_FLOAT_EPSILON)
        and (region.y - ROI_FLOAT_EPSILON) <= y <= (region.y + region.height + ROI_FLOAT_EPSILON)
    )
