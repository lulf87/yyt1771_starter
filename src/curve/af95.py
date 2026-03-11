"""Offline curve normalization and Af95 estimation."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models import SyncPoint

EPSILON = 1e-9


@dataclass(slots=True)
class NormalizedCurvePoint:
    """A filtered curve sample with normalized metric value."""

    timestamp_ms: int
    temperature_c: float
    metric_raw: float
    metric_norm: float


def normalize_sync_points(sync_points: list[SyncPoint]) -> list[NormalizedCurvePoint]:
    """Filter valid sync points and normalize their metric_raw values to 0..1."""

    valid_points = [
        sync_point
        for sync_point in sync_points
        if sync_point.temp is not None
        and sync_point.metric is not None
        and sync_point.metric.metric_raw is not None
    ]
    if not valid_points:
        return []

    raw_values = [float(sync_point.metric.metric_raw) for sync_point in valid_points if sync_point.metric is not None]
    minimum = min(raw_values)
    maximum = max(raw_values)
    if len(raw_values) < 2 or minimum == maximum:
        return []

    span = maximum - minimum
    normalized_points: list[NormalizedCurvePoint] = []
    for sync_point, raw_value in zip(valid_points, raw_values):
        temperature_c = float(sync_point.temp.celsius) if sync_point.temp is not None else 0.0
        metric_norm = (raw_value - minimum) / span
        normalized_points.append(
            NormalizedCurvePoint(
                timestamp_ms=sync_point.timestamp_ms,
                temperature_c=temperature_c,
                metric_raw=raw_value,
                metric_norm=max(0.0, min(1.0, metric_norm)),
            )
        )
    return normalized_points


def estimate_af95(sync_points: list[SyncPoint], threshold: float = 0.95) -> float | None:
    """Estimate Af95 from normalized metric curve using linear interpolation."""

    normalized_points = normalize_sync_points(sync_points)
    if not normalized_points:
        return None

    previous_point: NormalizedCurvePoint | None = None
    for point in normalized_points:
        if abs(point.metric_norm - threshold) <= EPSILON:
            return point.temperature_c
        if point.metric_norm > threshold:
            if previous_point is None:
                return point.temperature_c
            if previous_point.metric_norm < threshold - EPSILON:
                return _interpolate_temperature(previous_point, point, threshold)
        previous_point = point
    return None


def _interpolate_temperature(
    point_a: NormalizedCurvePoint,
    point_b: NormalizedCurvePoint,
    threshold: float,
) -> float:
    if point_a.metric_norm == point_b.metric_norm:
        return point_b.temperature_c
    ratio = (threshold - point_a.metric_norm) / (point_b.metric_norm - point_a.metric_norm)
    return point_a.temperature_c + ratio * (point_b.temperature_c - point_a.temperature_c)
