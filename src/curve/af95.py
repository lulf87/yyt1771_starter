"""Placeholder Af95 estimation hook."""

from src.core.models import CurvePoint


def estimate_af95(points: list[CurvePoint]) -> float | None:
    if not points:
        return None
    return max(point.value for point in points)
