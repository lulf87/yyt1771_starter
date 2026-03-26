"""Pure geometry helpers shared by the desktop preview overlay."""

from __future__ import annotations

import math

from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def point_in_rotated_metric_box(box: MetricBox, x: int, y: int) -> bool:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = x - float(box.center_x)
    translated_y = y - float(box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return abs(local_x) <= float(box.width) / 2 and abs(local_y) <= float(box.height) / 2


def metric_box_corners(box: MetricBox) -> list[tuple[float, float]]:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    half_width = float(box.width) / 2
    half_height = float(box.height) / 2
    points: list[tuple[float, float]] = []
    for local_x, local_y in (
        (-half_width, -half_height),
        (half_width, -half_height),
        (half_width, half_height),
        (-half_width, half_height),
    ):
        points.append(
            (
                float(box.center_x) + local_x * cos_theta - local_y * sin_theta,
                float(box.center_y) + local_x * sin_theta + local_y * cos_theta,
            )
        )
    return points


def seed_points_for_metric_box(box: MetricBox) -> tuple[PixelPoint, PixelPoint]:
    angle_rad = math.radians(float(box.angle_deg))
    offset_x = math.cos(angle_rad) * (float(box.width) * 0.3)
    offset_y = math.sin(angle_rad) * (float(box.width) * 0.3)
    return (
        PixelPoint(x=round(float(box.center_x) - offset_x), y=round(float(box.center_y) - offset_y)),
        PixelPoint(x=round(float(box.center_x) + offset_x), y=round(float(box.center_y) + offset_y)),
    )


def clamp_metric_box_to_roi(
    roi: RectRegion,
    box: MetricBox,
    *,
    fallback_angle_deg: float | None = None,
) -> MetricBox:
    clamped_width = round(clamp(float(box.width) or float(roi.width) * 0.8, 1, float(roi.width)))
    clamped_height = round(clamp(float(box.height) or float(roi.height) * 0.35, 1, float(roi.height)))
    center_x = round(
        clamp(
            float(box.center_x) or float(roi.x + roi.width / 2),
            float(roi.x) + clamped_width / 2,
            float(roi.x + roi.width) - clamped_width / 2,
        )
    )
    center_y = round(
        clamp(
            float(box.center_y) or float(roi.y + roi.height / 2),
            float(roi.y) + clamped_height / 2,
            float(roi.y + roi.height) - clamped_height / 2,
        )
    )
    return MetricBox(
        center_x=center_x,
        center_y=center_y,
        width=clamped_width,
        height=clamped_height,
        angle_deg=float(box.angle_deg if fallback_angle_deg is None else fallback_angle_deg),
    )


def ensure_definition_geometry(definition: MeasurementDefinition) -> MeasurementDefinition:
    roi = definition.analysis_roi
    box = clamp_metric_box_to_roi(roi, definition.metric_box)
    point_a = definition.point_a_px
    point_b = definition.point_b_px
    if not point_in_rotated_metric_box(box, point_a.x, point_a.y) or not point_in_rotated_metric_box(
        box, point_b.x, point_b.y
    ):
        point_a, point_b = seed_points_for_metric_box(box)
    return MeasurementDefinition(
        analysis_roi=definition.analysis_roi,
        metric_box=box,
        point_a_px=point_a,
        point_b_px=point_b,
        foreground_polarity=definition.foreground_polarity,
        threshold_mode=definition.threshold_mode,
        ignore_internal_texture=definition.ignore_internal_texture,
        min_target_area_px=definition.min_target_area_px,
    )
