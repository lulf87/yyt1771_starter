from src.core.enums import CaptureMode, RunStatus
from src.core.models import (
    FramePacket,
    MeasurementDefinition,
    MeasurementProfileSnapshot,
    MetricBox,
    PixelPoint,
    RectRegion,
    RunRateSnapshot,
    RunDraftRecord,
    ShapeMetric,
    resolve_measurement_angle_deg,
    resolve_width_extreme_mode,
)
from src.vision.metric_end_displacement import EndDisplacementMetricExtractor


def test_resolve_measurement_angle_uses_metric_box_over_stale_direction_angle() -> None:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=400, height=160),
        metric_box=MetricBox(center_x=200, center_y=75, width=300, height=80, angle_deg=27.0),
        point_a_px=PixelPoint(x=60, y=70),
        point_b_px=PixelPoint(x=320, y=70),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=200,
        direction_angle_deg=0.0,  # stale, disagrees with the rotated box
    )

    assert resolve_measurement_angle_deg(definition) == 27.0


def test_frame_packet_supports_image_field() -> None:
    frame = FramePacket(
        timestamp_ms=1000,
        source="fixture",
        image=[[0, 255], [255, 0]],
        frame_id=5,
        meta={"kind": "test"},
    )

    assert frame.image == [[0, 255], [255, 0]]
    assert frame.frame_id == 5
    assert frame.meta["kind"] == "test"


def test_shape_metric_exposes_frozen_core_fields() -> None:
    metric = ShapeMetric(timestamp_ms=1000)

    assert metric.metric_name == "end_displacement"
    assert metric.metric_raw is None
    assert metric.metric_norm is None
    assert metric.quality == 0.0


def test_metric_extractor_handles_missing_image() -> None:
    extractor = EndDisplacementMetricExtractor()

    metric = extractor.extract(FramePacket(timestamp_ms=1000, source="fixture", image=None))

    assert metric.timestamp_ms == 1000
    assert metric.metric_name == "end_displacement"
    assert metric.quality == 0.0
    assert metric.meta["reason"] == "missing_image"


def test_measurement_definition_uses_semantic_two_point_fields() -> None:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=10, y=0, width=400, height=160),
        metric_box=MetricBox(center_x=200, center_y=75, width=300, height=80, angle_deg=12.5),
        point_a_px=PixelPoint(x=60, y=50),
        point_b_px=PixelPoint(x=320, y=70),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=200,
        direction_angle_deg=12.5,
    )

    assert definition.analysis_roi.width == 400
    assert definition.metric_box.angle_deg == 12.5
    assert definition.direction_angle_deg == 12.5
    assert definition.direction_projection_mode == "max_chord"
    assert definition.width_extreme_mode == "max_width"
    assert resolve_width_extreme_mode(definition) == "max_width"
    assert definition.point_a_px.x == 60
    assert definition.is_complete() is True


def test_measurement_definition_validates_width_extreme_mode() -> None:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=10, y=0, width=400, height=160),
        metric_box=MetricBox(center_x=200, center_y=75, width=300, height=80, angle_deg=0.0),
        point_a_px=PixelPoint(x=60, y=75),
        point_b_px=PixelPoint(x=320, y=75),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=200,
        direction_angle_deg=0.0,
        direction_projection_mode="envelope_max_width",
        width_extreme_mode="min_width",
    )

    assert definition.is_complete() is True
    assert resolve_width_extreme_mode(definition) == "min_width"

    definition.width_extreme_mode = "narrowest_pixel"

    assert definition.is_complete() is False


def test_run_draft_record_keeps_live_status_separate_from_session_state() -> None:
    record = RunDraftRecord(
        run_id="run-test",
        profile="dev_mock",
        preset="balloon",
        status=RunStatus.DEFINITION_EDITING,
        created_at_ms=1000,
        updated_at_ms=1200,
    )

    assert record.run_id == "run-test"
    assert record.status == RunStatus.DEFINITION_EDITING
    assert record.capture_mode == CaptureMode.IDLE
    assert record.definition is None


def test_rate_and_measurement_profile_snapshots_expose_temporal_sampling_contracts() -> None:
    rates = RunRateSnapshot(measurement_sample_hz=50.0, artifact_capture_hz=50.0)
    profile = MeasurementProfileSnapshot(
        acquisition_roi=RectRegion(x=10, y=20, width=320, height=128),
        exposure_us=4000,
    )

    assert rates.camera_resulting_fps is None
    assert rates.preview_display_fps is None
    assert rates.measurement_sample_hz == 50.0
    assert rates.artifact_capture_hz == 50.0
    assert rates.dropped_frame_count == 0
    assert profile.acquisition_roi is not None
    assert profile.acquisition_roi.width == 320
    assert profile.exposure_us == 4000


def test_measurement_definition_is_incomplete_when_points_fall_outside_roi() -> None:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=100, height=100),
        metric_box=MetricBox(center_x=50, center_y=50, width=60, height=20, angle_deg=0.0),
        point_a_px=PixelPoint(x=10, y=10),
        point_b_px=PixelPoint(x=150, y=10),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=50,
    )

    assert definition.is_complete() is False


def test_measurement_definition_is_incomplete_when_points_fall_outside_metric_box() -> None:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=200, height=120),
        metric_box=MetricBox(center_x=80, center_y=50, width=40, height=20, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=50),
        point_b_px=PixelPoint(x=120, y=50),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=50,
    )

    assert definition.is_complete() is False


def test_measurement_definition_accepts_tight_rotated_window_near_roi_boundary() -> None:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=14, y=18, width=70, height=17),
        metric_box=MetricBox(center_x=49, center_y=29, width=71, height=2, angle_deg=8.24632081446853),
        point_a_px=PixelPoint(x=14, y=24),
        point_b_px=PixelPoint(x=83, y=34),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=50,
    )

    assert definition.has_valid_points() is True
    assert definition.has_valid_window() is True
    assert definition.is_complete() is True
