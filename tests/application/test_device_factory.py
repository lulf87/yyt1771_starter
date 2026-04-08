from src.application.device_factory import build_measurement_capture_plan
from src.application.runtime_config import RuntimeConfig, WebAppConfig
from src.core.config_models import DeviceRoiConfig
from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion


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
    runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig(
        x=512,
        y=342,
        width=2048,
        height=1364,
    )
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
        x=1352,
        y=910,
        width=360,
        height=184,
    )
    assert plan.metric_definition.analysis_roi == RectRegion(
        x=60,
        y=32,
        width=240,
        height=120,
    )
    assert plan.metric_definition.metric_box == MetricBox(
        center_x=180,
        center_y=92,
        width=200,
        height=60,
        angle_deg=0.0,
    )
    assert plan.metric_definition.point_a_px == PixelPoint(x=80, y=92)
    assert plan.metric_definition.point_b_px == PixelPoint(x=280, y=92)


def test_build_measurement_capture_plan_keeps_mock_camera_definition_and_roi_unchanged() -> None:
    runtime_config = _lab_runtime_config(camera_backend="mock")
    definition = _definition()

    plan = build_measurement_capture_plan(
        runtime_config=runtime_config,
        definition=definition,
    )

    assert plan.measurement_profile.device_roi == runtime_config.live.camera.measurement.device_roi
    assert plan.metric_definition == definition
