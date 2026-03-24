"""AFAS-oriented curve extraction and tangent-style live result analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from src.core.models import SyncPoint
from src.curve.af95 import estimate_af95


@dataclass(slots=True)
class AfasCurvePoint:
    """One valid AFAS input point extracted from a sync sequence."""

    timestamp_ms: int
    temperature_celsius: float
    channel_value: float


@dataclass(slots=True)
class AfasLine:
    """Simple y = slope * x + intercept line model."""

    slope: float
    intercept: float


@dataclass(slots=True)
class AfasAnalysisResult:
    """Curve analysis output consumed by workflow/result assembly."""

    channel_name: str
    point_count: int
    result_status: str
    af95: float | None = None
    as_value: float | None = None
    af_value: float | None = None
    reason: str | None = None
    detail: str = ""
    curve_points: list[AfasCurvePoint] = field(default_factory=list)
    max_slope_temperature_celsius: float | None = None
    low_baseline: AfasLine | None = None
    high_baseline: AfasLine | None = None
    tangent: AfasLine | None = None


def extract_afas_curve_points(
    sync_points: list[SyncPoint],
    *,
    channel_name: str,
) -> AfasAnalysisResult:
    """Validate sync points and extract the single live channel curve."""

    curve_points: list[AfasCurvePoint] = []
    for sync_point in sync_points:
        if sync_point.temp is None:
            return AfasAnalysisResult(
                channel_name=channel_name,
                point_count=len(curve_points),
                result_status="unavailable",
                reason="missing_temperature",
                detail=f"Sync point at {sync_point.timestamp_ms} is missing temperature data.",
                curve_points=curve_points,
            )
        if sync_point.metric is None or sync_point.metric.metric_raw is None:
            return AfasAnalysisResult(
                channel_name=channel_name,
                point_count=len(curve_points),
                result_status="unavailable",
                reason="invalid_metric",
                detail=f"Sync point at {sync_point.timestamp_ms} is missing {channel_name} metric data.",
                curve_points=curve_points,
            )
        channel_value = float(sync_point.metric.metric_raw)
        if not math.isfinite(channel_value):
            return AfasAnalysisResult(
                channel_name=channel_name,
                point_count=len(curve_points),
                result_status="unavailable",
                reason="invalid_metric",
                detail=f"Sync point at {sync_point.timestamp_ms} contains a non-finite {channel_name} value.",
                curve_points=curve_points,
            )
        curve_points.append(
            AfasCurvePoint(
                timestamp_ms=sync_point.timestamp_ms,
                temperature_celsius=float(sync_point.temp.celsius),
                channel_value=channel_value,
            )
        )

    return AfasAnalysisResult(
        channel_name=channel_name,
        point_count=len(curve_points),
        result_status="ok",
        curve_points=curve_points,
    )


def analyze_afas(
    sync_points: list[SyncPoint],
    *,
    channel_name: str,
    as_fit_point_count: int,
    af_fit_point_count: int,
) -> AfasAnalysisResult:
    """Run a lightweight tangent-style AFAS analysis on a single live channel."""

    extracted = extract_afas_curve_points(sync_points, channel_name=channel_name)
    extracted.af95 = estimate_af95(sync_points)
    if extracted.result_status != "ok":
        return extracted

    point_count = len(extracted.curve_points)
    if point_count < 5:
        extracted.result_status = "unavailable"
        extracted.reason = "insufficient_points"
        extracted.detail = (
            f"AFAS analysis needs at least 5 valid points, but only {point_count} {channel_name} samples were captured."
        )
        return extracted

    low_window = _fit_window_size(point_count, as_fit_point_count)
    high_window = _fit_window_size(point_count, af_fit_point_count)
    derivatives = _compute_derivatives(extracted.curve_points)
    tangent_index = _find_tangent_index(
        derivatives,
        low_window=low_window,
        high_window=high_window,
    )
    tangent_point = extracted.curve_points[tangent_index]
    tangent = AfasLine(
        slope=derivatives[tangent_index],
        intercept=tangent_point.channel_value - derivatives[tangent_index] * tangent_point.temperature_celsius,
    )
    low_baseline = _fit_line(extracted.curve_points[:low_window])
    high_baseline = _fit_line(extracted.curve_points[-high_window:])
    as_value = _find_intersection_temperature(tangent, low_baseline)
    af_value = _find_intersection_temperature(tangent, high_baseline)

    extracted.tangent = tangent
    extracted.low_baseline = low_baseline
    extracted.high_baseline = high_baseline
    extracted.max_slope_temperature_celsius = tangent_point.temperature_celsius
    extracted.as_value = as_value
    extracted.af_value = af_value

    if as_value is None or af_value is None:
        extracted.result_status = "unavailable"
        extracted.reason = "degenerate_curve"
        extracted.detail = "AFAS tangent or baseline fitting became degenerate and could not produce intersections."
        return extracted
    if af_value <= as_value:
        extracted.result_status = "unavailable"
        extracted.reason = "invalid_result"
        extracted.detail = f"AFAS produced non-increasing intersections: As={as_value:.3f}, Af={af_value:.3f}."
        extracted.as_value = None
        extracted.af_value = None
        return extracted
    return extracted


def _fit_window_size(point_count: int, requested_count: int) -> int:
    clamped_requested = max(2, int(requested_count))
    max_window = max(2, (point_count - 1) // 2)
    return min(clamped_requested, max_window)


def _compute_derivatives(curve_points: list[AfasCurvePoint]) -> list[float]:
    derivatives: list[float] = []
    last_index = len(curve_points) - 1
    for index, point in enumerate(curve_points):
        if index == 0:
            left = point
            right = curve_points[1]
        elif index == last_index:
            left = curve_points[last_index - 1]
            right = point
        else:
            left = curve_points[index - 1]
            right = curve_points[index + 1]
        delta_temp = right.temperature_celsius - left.temperature_celsius
        if abs(delta_temp) < 1e-9:
            derivatives.append(0.0)
            continue
        derivatives.append((right.channel_value - left.channel_value) / delta_temp)
    return derivatives


def _find_tangent_index(
    derivatives: list[float],
    *,
    low_window: int,
    high_window: int,
) -> int:
    last_index = len(derivatives) - 1
    start_index = min(max(1, low_window - 1), last_index)
    stop_index = max(start_index + 1, len(derivatives) - high_window + 1)
    candidate_indexes = range(start_index, min(stop_index, len(derivatives)))
    return max(candidate_indexes, key=lambda index: abs(derivatives[index]))


def _fit_line(curve_points: list[AfasCurvePoint]) -> AfasLine:
    if len(curve_points) < 2:
        raise ValueError("line fitting requires at least 2 points")

    xs = [point.temperature_celsius for point in curve_points]
    ys = [point.channel_value for point in curve_points]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if abs(denominator) < 1e-9:
        return AfasLine(slope=0.0, intercept=mean_y)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    return AfasLine(slope=slope, intercept=intercept)


def _find_intersection_temperature(line_a: AfasLine, line_b: AfasLine) -> float | None:
    denominator = line_a.slope - line_b.slope
    if abs(denominator) < 1e-9:
        return None
    return (line_b.intercept - line_a.intercept) / denominator
