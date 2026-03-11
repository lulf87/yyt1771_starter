"""Placeholder quality helpers."""

from src.core.models import ShapeMetric


def score_metric(metric: ShapeMetric) -> float:
    return metric.quality
