import pytest

from src.core.enums import ObservationAxis
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion, ShapeMetric, SyncPoint, TempReading
from src.curve.afas_postprocessing_analysis import (
    AFAS_ANALYSIS_SCHEMA_VERSION,
    analyze_preprocessed_afas_channel,
    compute_derivative,
    compute_tangent_at_point,
    find_intersection,
    find_max_slope_index,
    fit_baseline,
)
from src.curve.afas_postprocessing_dataset import build_afas_postprocessing_dataset
from src.curve.afas_preprocessing import preprocess_afas_channel


def _definition() -> MeasurementDefinition:
    return MeasurementDefinition(
        analysis_roi=RectRegion(x=10, y=20, width=120, height=60),
        metric_box=MetricBox(center_x=70, center_y=50, width=80, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=30, y=50),
        point_b_px=PixelPoint(x=110, y=50),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=200,
        sensitivity=55.0,
        observation_axis=ObservationAxis.LONG_AXIS,
    )


def _sync_point(timestamp_ms: int, temperature_celsius: float, metric_raw: float, frame_id: int) -> SyncPoint:
    return SyncPoint(
        timestamp_ms=timestamp_ms,
        frame=FramePacket(timestamp_ms=timestamp_ms, source="mock_camera", frame_id=frame_id),
        temp=TempReading(timestamp_ms=timestamp_ms, celsius=temperature_celsius, source="mock_temp"),
        metric=ShapeMetric(
            timestamp_ms=timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=metric_raw,
            quality=0.95,
            point_a_px=(20 + frame_id, 50),
            point_b_px=(100 + frame_id, 50),
            feature_point_px=(60, 50),
        ),
    )


def _dataset_for_analysis() -> dict:
    values = [
        100.0,
        101.0,
        102.0,
        103.0,
        105.0,
        110.0,
        118.0,
        128.0,
        138.0,
        145.0,
        149.0,
        151.0,
        152.0,
        153.0,
    ]
    sync_points = [
        _sync_point(1000 + index * 100, 20.0 + index * 2.0, value, index)
        for index, value in enumerate(values)
    ]
    return build_afas_postprocessing_dataset(
        session_id="run-afas-analysis-001",
        definition=_definition(),
        sync_points=sync_points,
        channel_name="Space1",
        analysis_engine="afas",
        capture_mode="post_run_review",
        rates={"measurement_sample_hz": 5.0},
        measurement_profile={"exposure_us": 10000},
        warnings=[],
        live_result_snapshot={"result_status": "ok", "af95": 74.0},
    )


def test_compute_derivative_matches_linear_slope() -> None:
    derivative = compute_derivative([10.0, 20.0, 30.0], [100.0, 120.0, 140.0])
    assert derivative.tolist() == pytest.approx([2.0, 2.0, 2.0])


def test_find_max_slope_index_applies_offset_and_clamps_bounds() -> None:
    assert find_max_slope_index([0.1, 0.5, -3.0, 0.8], offset=1) == 3
    assert find_max_slope_index([0.1, 0.5, -3.0, 0.8], offset=10) == 3


def test_fit_baseline_returns_exact_line_for_linear_segment() -> None:
    slope, intercept = fit_baseline([10.0, 11.0, 12.0, 13.0], [25.0, 27.0, 29.0, 31.0], 10.0, 13.0)
    assert slope == pytest.approx(2.0)
    assert intercept == pytest.approx(5.0)


def test_compute_tangent_and_intersection_return_expected_geometry() -> None:
    slope, intercept = compute_tangent_at_point([10.0, 20.0, 30.0], [5.0, 15.0, 25.0], [1.0, 2.0, 3.0], 1)
    intersection = find_intersection(slope, intercept, 0.0, 35.0)

    assert slope == pytest.approx(2.0)
    assert intercept == pytest.approx(-25.0)
    assert intersection == pytest.approx(30.0)


def test_analyze_preprocessed_afas_channel_returns_parameterized_tangent_result() -> None:
    preprocessing_result = preprocess_afas_channel(
        _dataset_for_analysis(),
        parameter_overrides={
            "group_by_temperature": True,
            "outlier_window": 11,
            "outlier_threshold": 5.0,
            "savgol_window_length": 7,
            "savgol_polyorder": 3,
        },
    )

    analysis = analyze_preprocessed_afas_channel(
        preprocessing_result,
        parameter_overrides={
            "low_range_celsius": [20.0, 28.0],
            "high_range_celsius": [40.0, 46.0],
            "tangent_offset": 0,
        },
    )

    assert analysis["schema_version"] == AFAS_ANALYSIS_SCHEMA_VERSION
    assert analysis["result_status"] == "ok"
    assert analysis["result"]["As"] is not None
    assert analysis["result"]["Af_tan"] is not None
    assert analysis["result"]["Af_tan"] > analysis["result"]["As"]
    assert analysis["fit"]["max_slope_index"] >= 0
    assert analysis["fit"]["low_baseline"]["range_celsius"] == [20.0, 28.0]
    assert analysis["fit"]["high_baseline"]["range_celsius"] == [40.0, 46.0]
    assert analysis["outlier_count"] >= 0


def test_analyze_preprocessed_afas_channel_auto_resolves_ranges_when_missing() -> None:
    preprocessing_result = preprocess_afas_channel(
        _dataset_for_analysis(),
        parameter_overrides={
            "savgol_window_length": 7,
            "savgol_polyorder": 3,
        },
    )

    analysis = analyze_preprocessed_afas_channel(preprocessing_result)

    assert analysis["result_status"] == "ok"
    assert "first 20% of the temperature span" in analysis["warnings"][0]
    assert "last 20% of the temperature span" in analysis["warnings"][1]


def test_analyze_preprocessed_afas_channel_reports_insufficient_points() -> None:
    dataset = build_afas_postprocessing_dataset(
        session_id="run-afas-analysis-002",
        definition=_definition(),
        sync_points=[
            _sync_point(1000, 25.0, 70.0, 0),
            _sync_point(1200, 30.0, 72.0, 1),
            _sync_point(1400, 35.0, 74.0, 2),
            _sync_point(1600, 40.0, 76.0, 3),
        ],
        channel_name="Space1",
        analysis_engine="afas",
        capture_mode="post_run_review",
        rates={"measurement_sample_hz": 5.0},
        measurement_profile={"exposure_us": 10000},
        warnings=[],
        live_result_snapshot={"result_status": "ok", "af95": 74.0},
    )

    preprocessing_result = preprocess_afas_channel(
        dataset,
        parameter_overrides={"savgol_window_length": 3, "savgol_polyorder": 1},
    )
    analysis = analyze_preprocessed_afas_channel(
        preprocessing_result,
        parameter_overrides={
            "low_range_celsius": [25.0, 30.0],
            "high_range_celsius": [35.0, 40.0],
        },
    )

    assert analysis["result_status"] == "unavailable"
    assert analysis["reason"] == "insufficient_points"
