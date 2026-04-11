from src.application.device_factory import (
    apply_measurement_acquisition_roi,
    build_measurement_capture_plan,
    build_metric_source,
)
from src.application.runtime_config import RuntimeConfig, WebAppConfig
from src.core.config_models import DeviceRoiConfig
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion, TempReading


def _definition(*, x: int = 900, y: int = 600, width: int = 240, height: int = 120) -> MeasurementDefinition:
    return MeasurementDefinition(
        analysis_roi=RectRegion(x=x, y=y, width=width, height=height),
        metric_box=MetricBox(
            center_x=x + width // 2,
            center_y=y + height // 2,
            width=200,
            height=60,
            angle_deg=0.0,
        ),
        point_a_px=PixelPoint(x=x + 20, y=y + height // 2),
        point_b_px=PixelPoint(x=x + width - 20, y=y + height // 2),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )


def _lab_runtime_config(*, camera_backend: str = "hik_gige_mvs") -> RuntimeConfig:
    runtime_config = RuntimeConfig(
        profile="dev_lab_camera_mock_temp",
        platform="mac",
        mode="lab",
        webapp=WebAppConfig(host="127.0.0.1", port=8000),
        adapters={"camera": camera_backend, "temp": "mock", "plc": "mock"},
    )
    runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig()
    runtime_config.live.camera.measurement.device_roi = DeviceRoiConfig(
        x=512,
        y=342,
        width=2048,
        height=1364,
    )
    return runtime_config


def test_build_measurement_capture_plan_reduces_real_camera_measurement_roi_and_shifts_definition() -> None:
    runtime_config = _lab_runtime_config(camera_backend="hik_gige_mvs")
    definition = _definition()

    plan = build_measurement_capture_plan(
        runtime_config=runtime_config,
        definition=definition,
    )

    assert plan.measurement_profile.device_roi == DeviceRoiConfig(
        x=870,
        y=598,
        width=300,
        height=124,
    )
    assert plan.metric_definition.analysis_roi == RectRegion(
        x=30,
        y=2,
        width=240,
        height=120,
    )
    assert plan.metric_definition.metric_box == MetricBox(
        center_x=150,
        center_y=62,
        width=200,
        height=60,
        angle_deg=0.0,
    )
    assert plan.metric_definition.point_a_px == PixelPoint(x=50, y=62)
    assert plan.metric_definition.point_b_px == PixelPoint(x=250, y=62)
    assert plan.setup_preview_roi == DeviceRoiConfig()
    assert plan.measurement_base_roi == DeviceRoiConfig(x=512, y=342, width=2048, height=1364)


def test_build_measurement_capture_plan_keeps_mock_camera_definition_and_roi_unchanged() -> None:
    runtime_config = _lab_runtime_config(camera_backend="mock")
    definition = _definition()

    plan = build_measurement_capture_plan(
        runtime_config=runtime_config,
        definition=definition,
    )

    assert plan.measurement_profile.device_roi == runtime_config.live.camera.measurement.device_roi
    assert plan.metric_definition == definition


def test_apply_measurement_acquisition_roi_retranslates_definition_against_applied_roi() -> None:
    runtime_config = _lab_runtime_config(camera_backend="hik_gige_mvs")
    definition = _definition()

    requested_plan = build_measurement_capture_plan(
        runtime_config=runtime_config,
        definition=definition,
    )
    applied_plan = apply_measurement_acquisition_roi(
        requested_plan,
        definition=definition,
        applied_device_roi=DeviceRoiConfig(x=832, y=560, width=360, height=184),
    )

    assert requested_plan.measurement_profile.device_roi == DeviceRoiConfig(
        x=870,
        y=598,
        width=300,
        height=124,
    )
    assert applied_plan.measurement_profile.device_roi == DeviceRoiConfig(
        x=832,
        y=560,
        width=360,
        height=184,
    )
    assert applied_plan.metric_definition.analysis_roi == RectRegion(
        x=68,
        y=40,
        width=240,
        height=120,
    )
    assert applied_plan.metric_definition.metric_box == MetricBox(
        center_x=188,
        center_y=100,
        width=200,
        height=60,
        angle_deg=0.0,
    )
    assert applied_plan.metric_definition.point_a_px == PixelPoint(x=88, y=100)
    assert applied_plan.metric_definition.point_b_px == PixelPoint(x=288, y=100)


def test_build_measurement_capture_plan_prioritizes_metric_box_over_tall_analysis_roi() -> None:
    runtime_config = _lab_runtime_config(camera_backend="hik_gige_mvs")
    definition = _definition(y=300, height=900)

    plan = build_measurement_capture_plan(
        runtime_config=runtime_config,
        definition=definition,
    )

    assert plan.measurement_profile.device_roi.width <= 300
    assert plan.measurement_profile.device_roi.height <= 124


def test_build_metric_source_can_debug_lock_points_for_real_camera() -> None:
    runtime_config = _lab_runtime_config(camera_backend="hik_gige_mvs")
    runtime_config.live.run.debug_locked_points_tracking = True
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=320, height=160),
        metric_box=MetricBox(center_x=160, center_y=80, width=200, height=60, angle_deg=0.0),
        point_a_px=PixelPoint(x=80, y=80),
        point_b_px=PixelPoint(x=240, y=80),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )

    source = build_metric_source(
        runtime_config=runtime_config,
        definition=definition,
        target_temperature_celsius=45.0,
    )
    metric = source.extract(
        FramePacket(
            timestamp_ms=1_000,
            source="fixture",
            image=[[255 for _ in range(320)] for _ in range(160)],
            frame_id=1,
        ),
        TempReading(timestamp_ms=1_005, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.point_a_px == (80, 80)
    assert metric.point_b_px == (240, 80)
    assert metric.meta["selection_mode"] == "locked_points"


def test_build_metric_source_uses_prior_tracker_by_default_for_real_camera() -> None:
    runtime_config = _lab_runtime_config(camera_backend="hik_gige_mvs")
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=320, height=160),
        metric_box=MetricBox(center_x=160, center_y=80, width=200, height=60, angle_deg=0.0),
        point_a_px=PixelPoint(x=80, y=80),
        point_b_px=PixelPoint(x=240, y=80),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )
    image = [[220 for _ in range(320)] for _ in range(160)]
    for row in range(50, 110):
        for col in range(100, 220):
            image[row][col] = 40

    source = build_metric_source(
        runtime_config=runtime_config,
        definition=definition,
        target_temperature_celsius=45.0,
    )
    metric = source.extract(
        FramePacket(timestamp_ms=1_000, source="fixture", image=image, frame_id=1),
        TempReading(timestamp_ms=1_005, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.meta["tracking_mode"] == "prior_gated_reacquire"
    assert metric.meta["tracking_state"] == "bootstrapped"
