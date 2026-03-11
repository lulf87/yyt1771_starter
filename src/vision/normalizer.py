"""Shared normalization helpers for later curve-oriented vision outputs."""

from src.core.models import CurvePoint


def normalize_points(points: list[CurvePoint]) -> list[float]:
    if not points:
        return []
    raw_values = [point.value for point in points]
    minimum = min(raw_values)
    maximum = max(raw_values)
    if maximum == minimum:
        return [0.0 for _ in raw_values]
    span = maximum - minimum
    return [(value - minimum) / span for value in raw_values]
