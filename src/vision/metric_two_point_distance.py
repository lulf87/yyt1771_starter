"""Two-point distance extractor for live setup preview and future run tracking."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
import math
from typing import Any

from src.core.contracts import VisionMetricExtractor
from src.core.models import FramePacket, MetricBox, PixelPoint, RectRegion, ShapeMetric

Roi = tuple[int, int, int, int]


@dataclass(slots=True)
class _Component:
    pixels: list[tuple[int, int]]

    @property
    def area(self) -> int:
        return len(self.pixels)


class TwoPointDistanceMetricExtractor(VisionMetricExtractor):
    def __init__(
        self,
        *,
        analysis_roi: RectRegion | None = None,
        metric_box: MetricBox | None = None,
        foreground_polarity: str = "dark_on_light",
        threshold_mode: str = "adaptive",
        threshold_margin: float = 10.0,
        ignore_internal_texture: bool = False,
        min_target_area_px: int = 200,
        quality_threshold: float = 0.75,
        locked_points: tuple[PixelPoint, PixelPoint] | None = None,
    ) -> None:
        self.analysis_roi = analysis_roi
        self.metric_box = metric_box
        self.foreground_polarity = foreground_polarity
        self.threshold_mode = threshold_mode
        self.threshold_margin = threshold_margin
        self.ignore_internal_texture = ignore_internal_texture
        self.min_target_area_px = min_target_area_px
        self.quality_threshold = quality_threshold
        self.locked_points = locked_points

    def extract(self, frame: FramePacket) -> ShapeMetric:
        if frame.image is None:
            return self._failure_metric(frame, reason="missing_image")

        try:
            image = normalize_frame_image(frame.image)
        except ValueError as exc:
            return self._failure_metric(frame, reason="invalid_image", detail=str(exc))

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
        if not sample_values:
            return self._failure_metric(frame, reason="metric_box_has_no_pixels", roi=effective_roi, metric_box=effective_box)

        threshold_value = _resolve_threshold(
            sample_values,
            mode=self.threshold_mode,
            polarity=self.foreground_polarity,
            margin=self.threshold_margin,
        )
        selected_pixels = _select_foreground_pixels(
            image,
            effective_box,
            threshold_value=threshold_value,
            foreground_polarity=self.foreground_polarity,
        )
        if self.ignore_internal_texture:
            selected_pixels = _fill_internal_texture(selected_pixels)
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

        point_a, point_b = _axis_extreme_points(component.pixels, effective_box.angle_deg)
        metric_raw = _distance_between(point_a, point_b)
        quality = _score_quality(
            component_area=component.area,
            min_target_area_px=self.min_target_area_px,
            metric_box=effective_box,
            metric_raw=metric_raw,
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
            selection_mode="auto_extremes",
            component_area=component.area,
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


def _resolve_threshold(
    sample_values: list[int],
    *,
    mode: str,
    polarity: str,
    margin: float,
) -> float:
    minimum = min(sample_values)
    maximum = max(sample_values)
    if mode == "binary":
        if polarity == "dark_on_light":
            return float(max(0, min(255, minimum + margin)))
        return float(max(0, min(255, maximum - margin)))
    if mode == "otsu":
        return float((minimum + maximum) / 2)
    return float(sum(sample_values) / len(sample_values))


def _select_foreground_pixels(
    image: list[list[int]],
    metric_box: MetricBox,
    *,
    threshold_value: float,
    foreground_polarity: str,
) -> set[tuple[int, int]]:
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


def _fill_internal_texture(pixels: set[tuple[int, int]]) -> set[tuple[int, int]]:
    if not pixels:
        return set()
    rows: dict[int, list[int]] = {}
    for x, y in pixels:
        rows.setdefault(y, []).append(x)
    filled = set(pixels)
    for y, xs in rows.items():
        filled.update({(x, y) for x in range(min(xs), max(xs) + 1)})
    return filled


def _pick_target_component(pixels: set[tuple[int, int]], min_area_px: int) -> _Component | None:
    if not pixels:
        return None
    remaining = set(pixels)
    components: list[_Component] = []
    while remaining:
        start = remaining.pop()
        queue: deque[tuple[int, int]] = deque([start])
        component_pixels = [start]
        while queue:
            current_x, current_y = queue.popleft()
            for next_x, next_y in _neighbors(current_x, current_y):
                if (next_x, next_y) not in remaining:
                    continue
                remaining.remove((next_x, next_y))
                queue.append((next_x, next_y))
                component_pixels.append((next_x, next_y))
        components.append(_Component(pixels=component_pixels))

    valid_components = [component for component in components if component.area >= min_area_px]
    if not valid_components:
        return None
    return max(valid_components, key=lambda component: (component.area, len(component.pixels)))


def _neighbors(x: int, y: int) -> list[tuple[int, int]]:
    return [
        (x - 1, y - 1),
        (x, y - 1),
        (x + 1, y - 1),
        (x - 1, y),
        (x + 1, y),
        (x - 1, y + 1),
        (x, y + 1),
        (x + 1, y + 1),
    ]


def _axis_extreme_points(pixels: list[tuple[int, int]], angle_deg: float) -> tuple[PixelPoint, PixelPoint]:
    angle_rad = math.radians(angle_deg)
    axis_x = math.cos(angle_rad)
    axis_y = math.sin(angle_rad)
    orthogonal_x = -axis_y
    orthogonal_y = axis_x

    def _project_axis(point: tuple[int, int]) -> float:
        return point[0] * axis_x + point[1] * axis_y

    def _project_orthogonal(point: tuple[int, int]) -> float:
        return point[0] * orthogonal_x + point[1] * orthogonal_y

    min_projection = min(_project_axis(point) for point in pixels)
    max_projection = max(_project_axis(point) for point in pixels)

    start_candidates = [point for point in pixels if abs(_project_axis(point) - min_projection) < 1e-6]
    end_candidates = [point for point in pixels if abs(_project_axis(point) - max_projection) < 1e-6]

    start = _median_orthogonal_point(start_candidates, _project_orthogonal)
    end = _median_orthogonal_point(end_candidates, _project_orthogonal)
    return (PixelPoint(x=start[0], y=start[1]), PixelPoint(x=end[0], y=end[1]))


def _median_orthogonal_point(
    candidates: list[tuple[int, int]],
    orthogonal_projection: Any,
) -> tuple[int, int]:
    sorted_candidates = sorted(candidates, key=orthogonal_projection)
    return sorted_candidates[len(sorted_candidates) // 2]


def _score_quality(
    *,
    component_area: int,
    min_target_area_px: int,
    metric_box: MetricBox,
    metric_raw: float,
) -> float:
    area_ratio = min(1.0, component_area / max(min_target_area_px, 1))
    span_ratio = min(1.0, metric_raw / max(metric_box.width, metric_box.height, 1))
    return min(1.0, max(0.05, 0.4 * area_ratio + 0.6 * span_ratio))


def _distance_between(point_a: PixelPoint, point_b: PixelPoint) -> float:
    return math.hypot(point_b.x - point_a.x, point_b.y - point_a.y)


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
    return region.x <= x <= (region.x + region.width) and region.y <= y <= (region.y + region.height)
