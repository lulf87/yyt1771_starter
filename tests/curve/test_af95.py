import pytest

from src.core.models import ShapeMetric, SyncPoint, TempReading
from src.curve.af95 import estimate_af95, normalize_sync_points


def _sync_point(
    timestamp_ms: int,
    temp_celsius: float | None,
    metric_raw: float | None,
) -> SyncPoint:
    temp = None if temp_celsius is None else TempReading(timestamp_ms=timestamp_ms, celsius=temp_celsius, source="fixture")
    metric = None
    if metric_raw is not None:
        metric = ShapeMetric(timestamp_ms=timestamp_ms, metric_raw=metric_raw)
    return SyncPoint(timestamp_ms=timestamp_ms, temp=temp, metric=metric)


def test_normalize_sync_points_scales_metric_raw_to_zero_one() -> None:
    sync_points = [
        _sync_point(1, 30.0, 0.0),
        _sync_point(2, 40.0, 10.0),
        _sync_point(3, 50.0, 20.0),
    ]

    normalized = normalize_sync_points(sync_points)

    assert [point.metric_norm for point in normalized] == [0.0, 0.5, 1.0]
    assert [point.temperature_c for point in normalized] == [30.0, 40.0, 50.0]


def test_estimate_af95_interpolates_between_points() -> None:
    sync_points = [
        _sync_point(1, 30.0, 0.0),
        _sync_point(2, 40.0, 18.0),
        _sync_point(3, 50.0, 20.0),
    ]

    af95 = estimate_af95(sync_points)

    assert af95 is not None
    assert af95 == pytest.approx(45.0)


def test_estimate_af95_returns_exact_temperature_on_threshold_hit() -> None:
    sync_points = [
        _sync_point(1, 30.0, 0.0),
        _sync_point(2, 40.0, 19.0),
        _sync_point(3, 50.0, 20.0),
    ]

    af95 = estimate_af95(sync_points)

    assert af95 == 40.0


def test_estimate_af95_filters_points_missing_temperature_or_metric() -> None:
    sync_points = [
        _sync_point(1, None, 0.0),
        _sync_point(2, 35.0, None),
        _sync_point(3, 40.0, 10.0),
        _sync_point(4, 50.0, 20.0),
    ]

    normalized = normalize_sync_points(sync_points)

    assert len(normalized) == 2
    assert [point.temperature_c for point in normalized] == [40.0, 50.0]
    assert [point.metric_norm for point in normalized] == [0.0, 1.0]


def test_estimate_af95_returns_none_when_curve_is_not_computable() -> None:
    assert estimate_af95([]) is None
    assert estimate_af95([_sync_point(1, 30.0, 10.0)]) is None
    assert estimate_af95([_sync_point(1, 30.0, 5.0), _sync_point(2, 40.0, 5.0)]) is None
    assert estimate_af95([_sync_point(1, 30.0, 0.0), _sync_point(2, 40.0, 10.0)], threshold=1.1) is None
