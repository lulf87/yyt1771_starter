import pytest

from src.core.models import ShapeMetric, SyncPoint, TempReading
from src.curve.afas import analyze_afas, extract_afas_curve_points


def _sync_point(timestamp_ms: int, temp_celsius: float | None, metric_raw: float | None) -> SyncPoint:
    temp = None if temp_celsius is None else TempReading(timestamp_ms=timestamp_ms, celsius=temp_celsius, source="fixture")
    metric = None if metric_raw is None else ShapeMetric(timestamp_ms=timestamp_ms, metric_raw=metric_raw, quality=0.98)
    return SyncPoint(timestamp_ms=timestamp_ms, temp=temp, metric=metric)


def test_extract_afas_curve_points_preserves_valid_channel_sequence() -> None:
    sync_points = [
        _sync_point(1_000, 20.0, 10.0),
        _sync_point(1_200, 30.0, 12.5),
        _sync_point(1_400, 40.0, 14.0),
    ]

    result = extract_afas_curve_points(sync_points, channel_name="Space1")

    assert result.result_status == "ok"
    assert result.point_count == 3
    assert [point.temperature_celsius for point in result.curve_points] == [20.0, 30.0, 40.0]
    assert [point.channel_value for point in result.curve_points] == [10.0, 12.5, 14.0]


def test_analyze_afas_returns_unavailable_for_insufficient_points() -> None:
    sync_points = [
        _sync_point(1_000, 25.0, 10.0),
        _sync_point(1_200, 35.0, 12.0),
        _sync_point(1_400, 45.0, 14.0),
        _sync_point(1_600, 55.0, 16.0),
    ]

    result = analyze_afas(sync_points, channel_name="Space1", as_fit_point_count=5, af_fit_point_count=5)

    assert result.result_status == "unavailable"
    assert result.reason == "insufficient_points"
    assert result.as_value is None
    assert result.af_value is None


def test_analyze_afas_returns_unavailable_for_missing_temperature_sample() -> None:
    sync_points = [
        _sync_point(1_000, 25.0, 10.0),
        _sync_point(1_200, None, 12.0),
        _sync_point(1_400, 45.0, 14.0),
        _sync_point(1_600, 55.0, 16.0),
        _sync_point(1_800, 65.0, 18.0),
    ]

    result = analyze_afas(sync_points, channel_name="Space1", as_fit_point_count=5, af_fit_point_count=5)

    assert result.result_status == "unavailable"
    assert result.reason == "missing_temperature"


def test_analyze_afas_returns_unavailable_for_invalid_metric_sample() -> None:
    sync_points = [
        _sync_point(1_000, 25.0, 10.0),
        _sync_point(1_200, 35.0, 12.0),
        _sync_point(1_400, 45.0, None),
        _sync_point(1_600, 55.0, 16.0),
        _sync_point(1_800, 65.0, 18.0),
    ]

    result = analyze_afas(sync_points, channel_name="Space1", as_fit_point_count=5, af_fit_point_count=5)

    assert result.result_status == "unavailable"
    assert result.reason == "invalid_metric"


def test_analyze_afas_returns_tangent_result_for_live_curve() -> None:
    sync_points = [
        _sync_point(1_000, 25.0, 100.0),
        _sync_point(1_200, 30.0, 101.0),
        _sync_point(1_400, 35.0, 103.0),
        _sync_point(1_600, 40.0, 110.0),
        _sync_point(1_800, 45.0, 122.0),
        _sync_point(2_000, 50.0, 133.0),
        _sync_point(2_200, 55.0, 139.0),
        _sync_point(2_400, 60.0, 141.0),
        _sync_point(2_600, 65.0, 142.0),
    ]

    result = analyze_afas(sync_points, channel_name="Space1", as_fit_point_count=3, af_fit_point_count=3)

    assert result.result_status == "ok"
    assert result.point_count == 9
    assert result.as_value is not None
    assert result.af_value is not None
    assert result.af_value > result.as_value
    assert result.max_slope_temperature_celsius is not None
    assert result.af95 is not None
    assert result.low_baseline is not None
    assert result.high_baseline is not None
    assert result.tangent is not None
    assert result.as_value == pytest.approx(37.2, abs=5.0)
    assert result.af_value == pytest.approx(54.6, abs=5.0)
