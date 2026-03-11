"""Minimal end-displacement extractor without an OpenCV dependency."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from src.core.contracts import VisionMetricExtractor
from src.core.models import FramePacket, ShapeMetric

Roi = tuple[int, int, int, int]


@dataclass(slots=True)
class _Component:
    pixels: list[tuple[int, int]]

    @property
    def area(self) -> int:
        return len(self.pixels)


class EndDisplacementMetricExtractor(VisionMetricExtractor):
    def __init__(
        self,
        roi: Roi | None = None,
        threshold_value: int = 127,
        min_area_px: int = 4,
        baseline_px: float | None = None,
        auto_lock_baseline: bool = True,
    ) -> None:
        self.roi = roi
        self.threshold_value = threshold_value
        self.min_area_px = min_area_px
        self.baseline_px = baseline_px
        self.auto_lock_baseline = auto_lock_baseline

    def extract(self, frame: FramePacket) -> ShapeMetric:
        if frame.image is None:
            return self._failure_metric(frame, reason="missing_image", roi=self.roi)

        try:
            image = _normalize_image(frame.image)
        except ValueError as exc:
            return self._failure_metric(frame, reason="invalid_image", detail=str(exc), roi=self.roi)

        effective_roi = _resolve_roi(self.roi, image)
        roi_image, roi_origin = _crop_roi(image, effective_roi)
        components = _find_connected_components(roi_image, self.threshold_value)
        component = _pick_target_component(components, self.min_area_px)
        if component is None:
            return self._failure_metric(
                frame,
                reason="no_valid_component",
                roi=effective_roi,
                component_area=0,
            )

        feature_point = _rightmost_point(component, roi_origin)
        baseline_px = self._resolve_baseline(feature_point[0])
        metric_raw = None if baseline_px is None else float(feature_point[0] - baseline_px)
        quality = _score_quality(component.area, self.min_area_px)

        return ShapeMetric(
            timestamp_ms=frame.timestamp_ms,
            metric_name="end_displacement",
            metric_raw=metric_raw,
            metric_norm=None,
            quality=quality,
            roi=effective_roi,
            feature_point_px=feature_point,
            baseline_px=baseline_px,
            meta={
                "component_area": component.area,
                "threshold_value": self.threshold_value,
                "source": frame.source,
                "frame_id": frame.frame_id,
            },
        )

    def _resolve_baseline(self, feature_x: int) -> float | None:
        if self.baseline_px is None and self.auto_lock_baseline:
            self.baseline_px = float(feature_x)
        return self.baseline_px

    def _failure_metric(
        self,
        frame: FramePacket,
        reason: str,
        roi: Roi | None,
        detail: str | None = None,
        component_area: int = 0,
    ) -> ShapeMetric:
        meta = {
            "reason": reason,
            "component_area": component_area,
            "threshold_value": self.threshold_value,
            "source": frame.source,
        }
        if detail is not None:
            meta["detail"] = detail
        return ShapeMetric(
            timestamp_ms=frame.timestamp_ms,
            metric_name="end_displacement",
            metric_raw=None,
            metric_norm=None,
            quality=0.0 if reason == "missing_image" else 0.1,
            roi=roi,
            feature_point_px=None,
            baseline_px=self.baseline_px,
            meta=meta,
        )


def _normalize_image(image: Any) -> list[list[int]]:
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


def _pixel_to_gray(pixel: Any) -> int:
    if isinstance(pixel, bool):
        return 255 if pixel else 0
    if isinstance(pixel, (int, float)):
        return int(max(0, min(255, round(float(pixel)))))
    if isinstance(pixel, Sequence) and not isinstance(pixel, (str, bytes)):
        channel_values = [_pixel_to_gray(channel) for channel in pixel]
        if not channel_values:
            raise ValueError("pixel channel sequence must not be empty")
        return int(sum(channel_values) / len(channel_values))
    raise ValueError("unsupported pixel type")


def _resolve_roi(roi: Roi | None, image: list[list[int]]) -> Roi:
    height = len(image)
    width = len(image[0])
    if roi is None:
        return (0, 0, width, height)
    x, y, w, h = roi
    x = max(0, x)
    y = max(0, y)
    w = max(0, w)
    h = max(0, h)
    if x >= width or y >= height or w == 0 or h == 0:
        return (x, y, 0, 0)
    clamped_w = min(w, width - x)
    clamped_h = min(h, height - y)
    return (x, y, clamped_w, clamped_h)


def _crop_roi(image: list[list[int]], roi: Roi) -> tuple[list[list[int]], tuple[int, int]]:
    x, y, w, h = roi
    if w == 0 or h == 0:
        return ([[]], (x, y))
    cropped = [row[x : x + w] for row in image[y : y + h]]
    return (cropped, (x, y))


def _find_connected_components(image: list[list[int]], threshold_value: int) -> list[_Component]:
    if not image or not image[0]:
        return []
    height = len(image)
    width = len(image[0])
    visited: set[tuple[int, int]] = set()
    components: list[_Component] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in visited or image[y][x] < threshold_value:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited.add((x, y))
            pixels: list[tuple[int, int]] = []
            while queue:
                current_x, current_y = queue.popleft()
                pixels.append((current_x, current_y))
                for next_x, next_y in _neighbors(current_x, current_y, width, height):
                    if (next_x, next_y) in visited:
                        continue
                    if image[next_y][next_x] < threshold_value:
                        continue
                    visited.add((next_x, next_y))
                    queue.append((next_x, next_y))
            components.append(_Component(pixels=pixels))
    return components


def _neighbors(x: int, y: int, width: int, height: int) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            next_x = x + dx
            next_y = y + dy
            if 0 <= next_x < width and 0 <= next_y < height:
                points.append((next_x, next_y))
    return points


def _pick_target_component(components: list[_Component], min_area_px: int) -> _Component | None:
    valid_components = [component for component in components if component.area >= min_area_px]
    if not valid_components:
        return None
    return max(valid_components, key=lambda component: (component.area, _component_rightmost_x(component)))


def _component_rightmost_x(component: _Component) -> int:
    return max(x for x, _ in component.pixels)


def _rightmost_point(component: _Component, roi_origin: tuple[int, int]) -> tuple[int, int]:
    roi_x, roi_y = roi_origin
    rightmost_x = max(x for x, _ in component.pixels)
    candidate_ys = sorted(y for x, y in component.pixels if x == rightmost_x)
    mid_index = len(candidate_ys) // 2
    local_y = candidate_ys[mid_index]
    return (roi_x + rightmost_x, roi_y + local_y)


def _score_quality(component_area: int, min_area_px: int) -> float:
    if component_area < min_area_px:
        return 0.1
    area_bonus = min(0.2, component_area / max(min_area_px, 1) * 0.05)
    return min(1.0, 0.75 + area_bonus)
