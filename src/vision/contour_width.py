"""OpenCV-backed contour width measurement helpers."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
from scipy import ndimage

from src.core.models import MetricBox, PixelPoint, RectRegion


@dataclass(slots=True)
class ContourWidthResult:
    point_a: PixelPoint
    point_b: PixelPoint
    metric_raw: float
    component_area: int
    threshold_value: float | None
    selection_angle_deg: float
    selection_axis: str
    component_border_touch_count: int = 0
    component_border_pixel_ratio: float = 0.0
    component_coords: np.ndarray | None = None


def detect_contour_width(
    gray_image: np.ndarray,
    *,
    analysis_roi: RectRegion,
    metric_box: MetricBox | None,
    measurement_axis_deg: float | None,
    foreground_polarity: str,
    threshold_mode: str,
    threshold_value: float | None,
    ignore_internal_texture: bool,
    min_target_area_px: int,
    sensitivity: float,
    selection_strategy: str,
    search_profile: str,
) -> ContourWidthResult | None:
    cv2 = _import_cv2()
    crop = gray_image[
        analysis_roi.y : analysis_roi.y + analysis_roi.height,
        analysis_roi.x : analysis_roi.x + analysis_roi.width,
    ]
    if crop.size == 0:
        return None

    local_box = None if metric_box is None else MetricBox(
        center_x=int(metric_box.center_x - analysis_roi.x),
        center_y=int(metric_box.center_y - analysis_roi.y),
        width=int(metric_box.width),
        height=int(metric_box.height),
        angle_deg=float(metric_box.angle_deg),
    )
    allowed_mask = (
        np.full(crop.shape, 255, dtype=np.uint8)
        if local_box is None
        else _metric_box_mask(crop.shape, local_box)
    )
    binary_mask, threshold_value_used = _threshold_mask(
        cv2,
        crop,
        allowed_mask=allowed_mask,
        foreground_polarity=foreground_polarity,
        threshold_mode=threshold_mode,
        threshold_value=threshold_value,
        sensitivity=sensitivity,
    )
    cleaned_mask = _cleanup_mask(
        cv2,
        binary_mask,
        ignore_internal_texture=ignore_internal_texture or selection_strategy == "roi_local_horizontal_boundary",
        sensitivity=sensitivity,
    )
    if not bool(cleaned_mask.any()):
        return None

    component_mask = _select_component_mask(
        cv2,
        cleaned_mask,
        min_target_area_px=max(1, int(min_target_area_px)),
        selection_strategy=selection_strategy,
    )
    if component_mask is None or not bool(component_mask.any()):
        return None
    component_coords = _component_coords(component_mask, analysis_roi)

    if selection_strategy == "axis_aligned_span":
        point_a_local, point_b_local, selection_axis = _axis_aligned_span_from_mask(component_mask)
        component_area = int(np.count_nonzero(component_mask))
        border_touch_count, border_pixel_ratio = _component_border_stats(component_mask)
        point_a = PixelPoint(x=int(analysis_roi.x + point_a_local.x), y=int(analysis_roi.y + point_a_local.y))
        point_b = PixelPoint(x=int(analysis_roi.x + point_b_local.x), y=int(analysis_roi.y + point_b_local.y))
        metric_raw = math.hypot(point_b.x - point_a.x, point_b.y - point_a.y)
        return ContourWidthResult(
            point_a=point_a,
            point_b=point_b,
            metric_raw=float(metric_raw),
            component_area=component_area,
            threshold_value=threshold_value_used,
            selection_angle_deg=0.0 if selection_axis == "horizontal" else 90.0,
            selection_axis=selection_axis,
            component_border_touch_count=border_touch_count,
            component_border_pixel_ratio=border_pixel_ratio,
            component_coords=component_coords,
        )

    search_angles, selection_axis_hint = _candidate_angles(
        metric_box=metric_box,
        measurement_axis_deg=measurement_axis_deg,
        selection_strategy=selection_strategy,
        search_profile=search_profile,
    )
    measurement = (
        _measure_roi_local_horizontal_boundary(cv2, component_mask, angle_deg=float(search_angles[0]))
        if selection_strategy == "roi_local_horizontal_boundary"
        else _measure_mask_width(
            cv2,
            component_mask,
            search_angles=search_angles,
            selection_axis_hint=selection_axis_hint,
        )
    )
    if measurement is None:
        return None
    selection_axis = (
        "roi_local_horizontal"
        if selection_strategy == "roi_local_horizontal_boundary"
        else _cardinal_axis_name(measurement.angle_deg)
    )

    point_a = PixelPoint(x=int(analysis_roi.x + measurement.point_a[0]), y=int(analysis_roi.y + measurement.point_a[1]))
    point_b = PixelPoint(x=int(analysis_roi.x + measurement.point_b[0]), y=int(analysis_roi.y + measurement.point_b[1]))
    component_area = int(np.count_nonzero(component_mask))
    border_touch_count, border_pixel_ratio = _component_border_stats(component_mask)
    metric_raw = math.hypot(point_b.x - point_a.x, point_b.y - point_a.y)
    return ContourWidthResult(
        point_a=point_a,
        point_b=point_b,
        metric_raw=float(metric_raw),
        component_area=component_area,
        threshold_value=threshold_value_used,
        selection_angle_deg=float(measurement.angle_deg),
        selection_axis=selection_axis,
        component_border_touch_count=border_touch_count,
        component_border_pixel_ratio=border_pixel_ratio,
        component_coords=component_coords,
    )


def _import_cv2() -> Any:
    try:
        import cv2  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised through callers
        raise RuntimeError(f"opencv unavailable: {exc}") from exc
    return cv2


def _threshold_mask(
    cv2: Any,
    crop: np.ndarray,
    *,
    allowed_mask: np.ndarray,
    foreground_polarity: str,
    threshold_mode: str,
    threshold_value: float | None,
    sensitivity: float,
) -> tuple[np.ndarray, float | None]:
    blurred = cv2.GaussianBlur(crop, (5, 5), 0)
    binary_flag = cv2.THRESH_BINARY_INV if foreground_polarity == "dark_on_light" else cv2.THRESH_BINARY

    if threshold_mode == "adaptive":
        source = crop if min(crop.shape[:2]) <= 32 else blurred
        block_size = max(3, int(round(11 + (float(sensitivity) / 100.0) * 12)))
        if block_size % 2 == 0:
            block_size += 1
        c_value = max(1, int(round(3 + (float(sensitivity) / 100.0) * 6)))
        mask = cv2.adaptiveThreshold(
            source,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            binary_flag,
            block_size,
            c_value,
        )
        threshold_value_used = None
    elif threshold_mode == "otsu":
        otsu_threshold, mask = cv2.threshold(blurred, 0, 255, binary_flag | cv2.THRESH_OTSU)
        threshold_value_used = float(otsu_threshold)
    else:
        resolved_threshold = 0.0 if threshold_value is None else float(threshold_value)
        source = crop if min(crop.shape[:2]) <= 48 else blurred
        _unused_threshold, mask = cv2.threshold(source, resolved_threshold, 255, binary_flag)
        threshold_value_used = resolved_threshold

    if allowed_mask is not None:
        mask = cv2.bitwise_and(mask, allowed_mask)
    return mask, threshold_value_used


def _cleanup_mask(
    cv2: Any,
    mask: np.ndarray,
    *,
    ignore_internal_texture: bool,
    sensitivity: float,
) -> np.ndarray:
    if not ignore_internal_texture:
        return mask
    min_dimension = min(mask.shape[:2]) if mask.size else 0
    if min_dimension <= 24:
        kernel_size = 3
    else:
        kernel_size = max(3, 3 + int(round((float(sensitivity) / 100.0) * 2)))
        if kernel_size % 2 == 0:
            kernel_size += 1
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1 if min_dimension <= 24 else 2)
    if ignore_internal_texture:
        # Fill only enclosed holes. A border-seeded flood fill can misclassify
        # the entire ROI as foreground when the target touches the ROI edge.
        cleaned = ndimage.binary_fill_holes(cleaned > 0).astype(np.uint8) * 255
    return cleaned


def _select_component_mask(
    cv2: Any,
    mask: np.ndarray,
    *,
    min_target_area_px: int,
    selection_strategy: str,
) -> np.ndarray | None:
    contours, _hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    image_h, image_w = mask.shape[:2]
    best_mask: np.ndarray | None = None
    best_key: tuple[float, float, int, int, float] | tuple[float, int] | None = None
    roi_local_masks: list[np.ndarray] = []
    max_reasonable_area = int(max(1, image_h * image_w) * 0.85)

    for contour in contours:
        component_mask = np.zeros_like(mask)
        cv2.drawContours(component_mask, [contour], -1, 255, thickness=cv2.FILLED)
        component_area = int(np.count_nonzero(component_mask))
        if component_area < min_target_area_px:
            continue
        if selection_strategy == "axis_aligned_span":
            candidate_key = _roi_component_selection_key(component_mask)
        else:
            candidate_key = (float(component_area), int(round(cv2.contourArea(contour))))
            if component_area < max_reasonable_area:
                border_touch_count, border_pixel_ratio = _component_border_stats(component_mask)
                if border_touch_count == 0 or border_pixel_ratio <= 0.01:
                    roi_local_masks.append(component_mask)
        if best_key is None or candidate_key > best_key:
            best_key = candidate_key
            best_mask = component_mask
    if selection_strategy == "roi_local_horizontal_boundary" and roi_local_masks:
        union_mask = np.zeros_like(mask)
        for component_mask in roi_local_masks:
            union_mask = cv2.bitwise_or(union_mask, component_mask)
        if bool(union_mask.any()):
            return union_mask
    return best_mask


def _roi_component_selection_key(component_mask: np.ndarray) -> tuple[float, float, int, int, float]:
    ys, xs = np.nonzero(component_mask)
    if len(xs) == 0:
        return (0.0, 0.0, 0, 0, 0.0)
    span_x = int(xs.max()) - int(xs.min())
    span_y = int(ys.max()) - int(ys.min())
    span = float(max(span_x, span_y))
    area = int(len(xs))
    region_h, region_w = component_mask.shape[:2]
    region_area = max(region_w * region_h, 1)
    region_diagonal = max(math.hypot(region_w, region_h), 1.0)
    area_ratio = max(area / region_area, 1e-6)
    span_ratio = min(1.0, span / region_diagonal)
    border_touch_count, border_pixel_ratio = _component_border_stats(component_mask)
    objectness = (span_ratio * math.pow(area_ratio, 0.25)) / (
        (1.0 + 0.35 * border_touch_count) * (1.0 + 8.0 * border_pixel_ratio)
    )
    return (objectness, span, area, -border_touch_count, -border_pixel_ratio)


def _component_border_stats(component_mask: np.ndarray) -> tuple[int, float]:
    foreground = component_mask > 0
    if not bool(foreground.any()):
        return 0, 0.0
    height, width = foreground.shape[:2]
    border_mask = np.zeros_like(foreground, dtype=bool)
    border_mask[0, :] = True
    border_mask[height - 1, :] = True
    border_mask[:, 0] = True
    border_mask[:, width - 1] = True
    border_pixels = foreground & border_mask
    border_touch_count = int(
        bool(np.any(foreground[0, :]))
        + bool(np.any(foreground[height - 1, :]))
        + bool(np.any(foreground[:, 0]))
        + bool(np.any(foreground[:, width - 1]))
    )
    return border_touch_count, float(np.count_nonzero(border_pixels) / max(np.count_nonzero(foreground), 1))


def _component_coords(component_mask: np.ndarray, analysis_roi: RectRegion) -> np.ndarray:
    ys, xs = np.nonzero(component_mask)
    if len(xs) == 0:
        return np.empty((0, 2), dtype=np.int32)
    return np.column_stack((xs + int(analysis_roi.x), ys + int(analysis_roi.y))).astype(np.int32, copy=False)


def _axis_aligned_span_from_mask(component_mask: np.ndarray) -> tuple[PixelPoint, PixelPoint, str]:
    ys, xs = np.nonzero(component_mask)
    if len(xs) == 0:
        raise ValueError("component mask must not be empty")
    min_x = int(xs.min())
    max_x = int(xs.max())
    min_y = int(ys.min())
    max_y = int(ys.max())
    horizontal_span = max_x - min_x
    vertical_span = max_y - min_y
    if horizontal_span >= vertical_span:
        shared_y = _stable_median(ys)
        return PixelPoint(x=min_x, y=shared_y), PixelPoint(x=max_x, y=shared_y), "horizontal"
    shared_x = _stable_median(xs)
    return PixelPoint(x=shared_x, y=min_y), PixelPoint(x=shared_x, y=max_y), "vertical"


def _stable_median(values: np.ndarray) -> int:
    ordered = np.sort(values, kind="stable")
    return int(ordered[len(ordered) // 2])


def _candidate_angles(
    *,
    metric_box: MetricBox | None,
    measurement_axis_deg: float | None,
    selection_strategy: str,
    search_profile: str,
) -> tuple[list[float], str]:
    if selection_strategy == "axis_aligned_span":
        return [0.0, 90.0], "cardinal"

    if selection_strategy == "roi_local_horizontal_boundary" and metric_box is not None:
        base_angle = float(metric_box.angle_deg)
        return [base_angle], "roi_local_horizontal"

    base_angle = float(metric_box.angle_deg if measurement_axis_deg is None and metric_box is not None else measurement_axis_deg or 0.0)
    return [base_angle], _cardinal_axis_name(base_angle)


def _cardinal_axis_name(angle_deg: float) -> str:
    normalized = abs(float(angle_deg) % 180.0)
    if normalized > 90.0:
        normalized = 180.0 - normalized
    return "horizontal" if normalized <= 45.0 else "vertical"


@dataclass(slots=True)
class _RunMeasurement:
    point_a: tuple[int, int]
    point_b: tuple[int, int]
    angle_deg: float
    length: int


def _measure_mask_width(
    cv2: Any,
    component_mask: np.ndarray,
    *,
    search_angles: list[float],
    selection_axis_hint: str,
) -> _RunMeasurement | None:
    points = np.argwhere(component_mask > 0)
    if len(points) == 0:
        return None
    xy_points = np.column_stack((points[:, 1], points[:, 0])).astype(np.float32, copy=False)
    best: _RunMeasurement | None = None
    best_key: tuple[int, float, float, float] | None = None

    for angle_deg in search_angles:
        rotated, matrix = _rotate_image_keep_bounds(cv2, component_mask, -float(angle_deg))
        foreground = rotated > 0
        center_row = (foreground.shape[0] - 1) / 2.0
        center_col = (foreground.shape[1] - 1) / 2.0
        inverse_matrix = cv2.invertAffineTransform(matrix)

        for row_index, row in enumerate(foreground):
            active_columns = np.flatnonzero(row)
            runs = _all_runs(active_columns)
            if not runs:
                continue
            for x_start, x_end, length in runs:
                run_center_distance = abs(float(row_index) - center_row)
                run_midpoint_distance = abs(((float(x_start) + float(x_end)) / 2.0) - center_col)
                candidate_key = (int(length), -run_center_distance, -run_midpoint_distance, -abs(float(angle_deg)))
                if best_key is not None and candidate_key <= best_key:
                    continue

                rotated_points = np.array([[[x_start, row_index]], [[x_end, row_index]]], dtype=np.float32)
                local_points = cv2.transform(rotated_points, inverse_matrix).reshape(-1, 2)
                snapped_points = _snap_to_component(xy_points, local_points)
                measurement = _RunMeasurement(
                    point_a=(int(snapped_points[0][0]), int(snapped_points[0][1])),
                    point_b=(int(snapped_points[1][0]), int(snapped_points[1][1])),
                    angle_deg=float(angle_deg),
                    length=int(length),
                )
                best = measurement
                best_key = candidate_key

    if best is None:
        return None
    return _orient_measurement(best, selection_axis_hint)


def _measure_roi_local_horizontal_boundary(
    cv2: Any,
    component_mask: np.ndarray,
    *,
    angle_deg: float,
) -> _RunMeasurement | None:
    rotated, matrix = _rotate_image_keep_bounds(cv2, component_mask, -float(angle_deg))
    foreground = rotated > 0
    if not bool(foreground.any()):
        return None
    center_row = (foreground.shape[0] - 1) / 2.0
    center_col = (foreground.shape[1] - 1) / 2.0
    best_run: tuple[int, int, int, int, float, float] | None = None

    for row_index, row in enumerate(foreground):
        active_columns = np.flatnonzero(row)
        if active_columns.size == 0:
            continue
        split_points = np.where(np.diff(active_columns) > 1)[0] + 1
        runs = np.split(active_columns, split_points)
        for run in runs:
            if run.size == 0:
                continue
            x_start = int(run[0])
            x_end = int(run[-1])
            length = int(run.size)
            run_center_distance = abs(float(row_index) - center_row)
            run_midpoint_distance = abs(((float(x_start) + float(x_end)) / 2.0) - center_col)
            candidate = (length, x_start, x_end, int(row_index), run_center_distance, run_midpoint_distance)
            if best_run is None or (candidate[0], -candidate[4], -candidate[5]) > (best_run[0], -best_run[4], -best_run[5]):
                best_run = candidate

    if best_run is None:
        return None

    inverse_matrix = cv2.invertAffineTransform(matrix)
    length, x_start, x_end, row_index, _row_distance, _midpoint_distance = best_run
    rotated_points = np.array([[[x_start, row_index]], [[x_end, row_index]]], dtype=np.float32)
    local_points = cv2.transform(rotated_points, inverse_matrix).reshape(-1, 2)
    point_a = tuple(int(round(value)) for value in local_points[0])
    point_b = tuple(int(round(value)) for value in local_points[1])
    return _orient_measurement(
        _RunMeasurement(
            point_a=point_a,
            point_b=point_b,
            angle_deg=float(angle_deg),
            length=int(length),
        ),
        "roi_local_horizontal",
    )


def _rotate_image_keep_bounds(cv2: Any, image: np.ndarray, angle_deg: float) -> tuple[np.ndarray, np.ndarray]:
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    cos_value = abs(matrix[0, 0])
    sin_value = abs(matrix[0, 1])
    new_width = int((height * sin_value) + (width * cos_value))
    new_height = int((height * cos_value) + (width * sin_value))
    matrix[0, 2] += (new_width / 2.0) - center[0]
    matrix[1, 2] += (new_height / 2.0) - center[1]
    rotated = cv2.warpAffine(
        image,
        matrix,
        (new_width, new_height),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return rotated, matrix


def _all_runs(indices: np.ndarray) -> list[tuple[int, int, int]]:
    if indices.size == 0:
        return []
    split_points = np.where(np.diff(indices) > 1)[0] + 1
    runs = np.split(indices, split_points)
    return [
        (int(run[0]), int(run[-1]), int(len(run)))
        for run in runs
        if len(run) > 0
    ]


def _snap_to_component(component_points: np.ndarray, mapped_points: np.ndarray) -> np.ndarray:
    snapped: list[np.ndarray] = []
    for mapped_point in mapped_points:
        deltas = component_points - mapped_point
        distances = np.sum(deltas * deltas, axis=1)
        snapped.append(component_points[int(np.argmin(distances))])
    return np.asarray(snapped, dtype=np.float32)


def _orient_measurement(measurement: _RunMeasurement, selection_axis_hint: str) -> _RunMeasurement:
    selection_axis = (
        _cardinal_axis_name(measurement.angle_deg)
        if selection_axis_hint == "cardinal"
        else selection_axis_hint
    )
    point_a = measurement.point_a
    point_b = measurement.point_b
    if selection_axis == "vertical":
        if (point_a[1], point_a[0]) <= (point_b[1], point_b[0]):
            return measurement
        return _RunMeasurement(point_a=point_b, point_b=point_a, angle_deg=measurement.angle_deg, length=measurement.length)
    if point_a <= point_b:
        return measurement
    return _RunMeasurement(point_a=point_b, point_b=point_a, angle_deg=measurement.angle_deg, length=measurement.length)


def _metric_box_mask(shape: tuple[int, int], box: MetricBox) -> np.ndarray:
    height, width = shape
    y_coords, x_coords = np.ogrid[0:height, 0:width]
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = x_coords - float(box.center_x)
    translated_y = y_coords - float(box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    mask = (np.abs(local_x) <= (float(box.width) / 2.0)) & (np.abs(local_y) <= (float(box.height) / 2.0))
    return np.where(mask, 255, 0).astype(np.uint8, copy=False)
