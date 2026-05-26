import math

import pytest

from src.curve.afas_postprocessing_dataset import build_afas_postprocessing_dataset
from src.curve.afas_preprocessing import (
    AFAS_PREPROCESSING_SCHEMA_VERSION,
    group_by_temperature,
    preprocess_afas_channel,
    remove_outliers,
    smooth_data,
)
from src.core.enums import ObservationAxis
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion, ShapeMetric, SyncPoint, TempReading


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


def test_group_by_temperature_returns_sorted_temperature_means() -> None:
    grouped_temperatures, grouped_values = group_by_temperature(
        [30.0, 20.0, 20.0, 30.0, 40.0],
        [10.0, 2.0, 4.0, 14.0, 18.0],
    )

    assert grouped_temperatures.tolist() == [20.0, 30.0, 40.0]
    assert grouped_values.tolist() == pytest.approx([3.0, 12.0, 18.0])


def test_remove_outliers_repairs_isolated_spike_with_neighbor_interpolation() -> None:
    temperatures, repaired_values, outlier_mask = remove_outliers(
        [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0],
        [100.0, 101.0, 100.5, 101.5, 102.0, 320.0, 103.0, 103.5, 104.0, 104.5, 105.0, 105.5, 106.0],
        window=11,
        threshold=3.0,
        max_iterations=3,
    )

    assert temperatures.tolist()[5] == 25.0
    assert outlier_mask.tolist()[5] is True
    assert repaired_values.tolist()[5] == pytest.approx(102.5)


def test_remove_outliers_keeps_short_quantized_smooth_curve_intact() -> None:
    temperatures = [1.2 + index * 0.1 for index in range(41)]
    values = [
        1009.024360,
        1009.854383,
        1010.391433,
        1008.333333,
        1008.000000,
        1007.622310,
        1007.708333,
        1005.933571,
        1005.176900,
        1005.750331,
        1005.416853,
        1005.500062,
        1005.583271,
        1005.250083,
        1005.400000,
        1004.500207,
        1005.000021,
        1004.833333,
        1004.222361,
        1004.500000,
        1004.333458,
        1003.487359,
        1004.389055,
        1003.000000,
        1001.533800,
        1002.250083,
        1000.718551,
        1001.208770,
        1001.305583,
        1002.250083,
        1002.166708,
        1002.142952,
        1001.305583,
        1001.055556,
        1000.667229,
        999.555927,
        998.250543,
        998.942730,
        998.547643,
        997.944482,
        995.435212,
    ]

    _, repaired_values, outlier_mask = remove_outliers(
        temperatures,
        values,
        window=11,
        threshold=5.0,
        max_iterations=3,
    )

    assert outlier_mask.tolist() == [False] * len(values)
    assert repaired_values.tolist() == pytest.approx(values)


def test_smooth_data_matches_expected_length_and_preserves_temperatures() -> None:
    temperatures, smoothed_values = smooth_data(
        [20.0, 21.0, 22.0, 23.0, 24.0],
        [100.0, 102.0, 101.0, 103.0, 102.0],
        window_length=5,
        polyorder=2,
    )

    assert temperatures.tolist() == [20.0, 21.0, 22.0, 23.0, 24.0]
    assert smoothed_values.tolist() == pytest.approx(
        [100.17142857142856, 101.31428571428572, 102.02857142857138, 102.31428571428565, 102.17142857142844]
    )


def test_preprocess_afas_channel_returns_structured_grouped_repaired_and_smoothed_payload() -> None:
    dataset = build_afas_postprocessing_dataset(
        session_id="run-afas-001",
        definition=_definition(),
        sync_points=[
            _sync_point(1000, 25.0, 70.0, 0),
            _sync_point(1100, 25.0, 72.0, 1),
            _sync_point(1200, 30.0, 75.0, 2),
            _sync_point(1300, 35.0, 140.0, 3),
            _sync_point(1400, 40.0, 80.0, 4),
            _sync_point(1500, 45.0, 82.0, 5),
            _sync_point(1600, 50.0, 84.0, 6),
        ],
        channel_name="Space1",
        analysis_engine="afas",
        capture_mode="post_run_review",
        rates={"measurement_sample_hz": 5.0},
        measurement_profile={"exposure_us": 10000},
        warnings=[],
        live_result_snapshot={"result_status": "ok", "af95": 74.0},
    )

    result = preprocess_afas_channel(
        dataset,
        parameter_overrides={
            "outlier_window": 11,
            "outlier_threshold": 3.0,
            "savgol_window_length": 5,
            "savgol_polyorder": 2,
        },
    )

    assert result["schema_version"] == AFAS_PREPROCESSING_SCHEMA_VERSION
    assert result["channel_name"] == "Space1"
    assert result["raw"]["temperature_celsius"][:2] == [25.0, 25.0]
    assert result["grouped"]["temperature_celsius"] == [25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
    assert result["grouped"]["values"][0] == pytest.approx(71.0)
    assert result["outlier_repair"]["outlier_count"] == 0
    assert result["smoothed"]["applied"] is True
    assert len(result["smoothed"]["values"]) == 6


def test_preprocess_afas_channel_gracefully_skips_smoothing_when_dataset_too_short() -> None:
    dataset = build_afas_postprocessing_dataset(
        session_id="run-afas-002",
        definition=_definition(),
        sync_points=[
            _sync_point(1000, 25.0, 70.0, 0),
            _sync_point(1200, 35.0, 75.0, 1),
            _sync_point(1400, 45.0, 80.0, 2),
        ],
        channel_name="Space1",
        analysis_engine="afas",
        capture_mode="post_run_review",
        rates={"measurement_sample_hz": 5.0},
        measurement_profile={"exposure_us": 10000},
        warnings=[],
        live_result_snapshot={"result_status": "ok", "af95": 74.0},
    )

    result = preprocess_afas_channel(dataset)

    assert result["smoothed"]["applied"] is False
    assert "cannot be larger than data length" in result["warnings"][0]
    assert result["smoothed"]["values"] == pytest.approx(result["outlier_repair"]["values"])


def test_preprocess_afas_channel_skips_full_length_savgol_window_to_avoid_edge_distortion() -> None:
    sync_points = [
        _sync_point(1000 + index * 100, 25.0 + index * 0.5, 100.0 + max(0, index - 20) * 3.0, index)
        for index in range(51)
    ]
    dataset = build_afas_postprocessing_dataset(
        session_id="run-afas-003",
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

    result = preprocess_afas_channel(dataset)

    assert result["smoothed"]["applied"] is False
    assert "covers the full data length" in result["warnings"][0]
    assert result["smoothed"]["values"] == pytest.approx(result["outlier_repair"]["values"])


def test_preprocess_afas_channel_caps_large_savgol_window_to_avoid_terminal_edge_reversal() -> None:
    sync_points = []
    for index in range(63):
        temperature = 11.0 + index * 0.1
        curve_position = -4.0 + 8.0 * index / 62.0
        metric_raw = 883.0 - 124.0 / (1.0 + math.exp(-curve_position))
        sync_points.append(_sync_point(1000 + index * 100, temperature, metric_raw, index))
    dataset = build_afas_postprocessing_dataset(
        session_id="run-afas-edge-guard",
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

    result = preprocess_afas_channel(
        dataset,
        parameter_overrides={
            "savgol_window_length": 51,
            "savgol_polyorder": 3,
        },
    )

    smoothed_values = result["smoothed"]["values"]
    assert result["smoothed"]["applied"] is True
    assert any("reduced" in warning and "edge distortion" in warning for warning in result["warnings"])
    assert smoothed_values[-1] <= min(smoothed_values[-20:]) + 0.25
