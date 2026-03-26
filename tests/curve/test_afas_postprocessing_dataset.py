from src.core.enums import ObservationAxis
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion, ShapeMetric, SyncPoint, TempReading
from src.curve.afas_postprocessing_dataset import (
    AFAS_DATASET_SCHEMA_VERSION,
    build_afas_postprocessing_dataset,
)


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


def _sync_point(timestamp_ms: int, temperature_celsius: float, metric_raw: float, metric_norm_seed: int) -> SyncPoint:
    return SyncPoint(
        timestamp_ms=timestamp_ms,
        frame=FramePacket(timestamp_ms=timestamp_ms, source="mock_camera", frame_id=metric_norm_seed),
        temp=TempReading(timestamp_ms=timestamp_ms, celsius=temperature_celsius, source="mock_temp"),
        metric=ShapeMetric(
            timestamp_ms=timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=metric_raw,
            quality=0.95,
            point_a_px=(20 + metric_norm_seed, 50),
            point_b_px=(100 + metric_norm_seed, 50),
            feature_point_px=(60, 50),
        ),
    )


def test_build_afas_postprocessing_dataset_returns_future_proof_single_channel_contract() -> None:
    dataset = build_afas_postprocessing_dataset(
        session_id="run-001",
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
        warnings=["measurement cadence below target"],
        live_result_snapshot={"result_status": "ok", "af95": 74.0},
    )

    assert dataset["schema_version"] == AFAS_DATASET_SCHEMA_VERSION
    assert dataset["session_id"] == "run-001"
    assert dataset["active_channel"] == "Space1"
    assert dataset["artifact_provenance"]["telemetry"] == "telemetry.csv"
    assert dataset["channel_map"]["Space1"]["values"] == [70.0, 75.0, 80.0]
    assert dataset["channel_map"]["Space1"]["temperature_celsius"] == [25.0, 35.0, 45.0]
    assert dataset["channel_map"]["Space1"]["metric_norm"][0] == 0.0
    assert dataset["channel_map"]["Space1"]["metric_norm"][-1] == 1.0
    assert dataset["channel_map"]["Space1"]["point_a_px"][1] == [21, 50]
    assert dataset["definition"]["sensitivity"] == 55.0
    assert dataset["preprocessing_defaults"]["savgol_window_length"] == 51
    assert dataset["analysis_defaults"]["tangent_offset"] == 0
