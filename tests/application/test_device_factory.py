from pathlib import Path

import numpy as np

from src.application.device_factory import (
    apply_measurement_acquisition_roi,
    build_measurement_capture_plan,
    build_temp_controller,
    build_metric_source,
    open_camera,
)
from src.application.runtime_config import RuntimeConfig, WebAppConfig
from src.core.config_models import DeviceRoiConfig
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion, TempReading, _metric_box_within_region


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
        x=840,
        y=568,
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


def test_open_mock_camera_uses_profile_device_roi_as_output_dimensions() -> None:
    runtime_config = _lab_runtime_config(camera_backend="mock")
    runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig(
        x=1440,
        y=1086,
        width=1120,
        height=620,
    )
    runtime_config.live.camera.measurement.device_roi = DeviceRoiConfig(
        x=512,
        y=342,
        width=2048,
        height=1364,
    )

    setup_frame = open_camera(runtime_config, profile_name="setup_preview").read_frame()
    measurement_frame = open_camera(runtime_config, profile_name="measurement").read_frame()

    assert getattr(setup_frame.image, "shape", None) == (620, 1120)
    assert setup_frame.meta["device_roi"] == {
        "x": 1440,
        "y": 1086,
        "width": 1120,
        "height": 620,
    }
    assert getattr(measurement_frame.image, "shape", None) == (1364, 2048)
    assert measurement_frame.meta["device_roi"] == {
        "x": 512,
        "y": 342,
        "width": 2048,
        "height": 1364,
    }


def test_build_measurement_capture_plan_keeps_definition_when_measurement_roi_is_unconfigured() -> None:
    runtime_config = _lab_runtime_config(camera_backend="hik_rtsp_opencv")
    runtime_config.live.camera.measurement.device_roi = DeviceRoiConfig()
    definition = _definition()

    plan = build_measurement_capture_plan(
        runtime_config=runtime_config,
        definition=definition,
    )

    assert plan.measurement_profile.device_roi == DeviceRoiConfig()
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
        x=840,
        y=568,
        width=360,
        height=184,
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


def test_build_measurement_capture_plan_preserves_tall_analysis_roi_as_capture_region() -> None:
    runtime_config = _lab_runtime_config(camera_backend="hik_gige_mvs")
    definition = _definition(y=300, height=900)

    plan = build_measurement_capture_plan(
        runtime_config=runtime_config,
        definition=definition,
    )

    assert plan.measurement_profile.device_roi == DeviceRoiConfig(
        x=840,
        y=140,
        width=360,
        height=1220,
    )
    assert plan.metric_definition.analysis_roi == RectRegion(
        x=60,
        y=160,
        width=240,
        height=900,
    )


def test_build_measurement_capture_plan_does_not_clip_roi_to_configured_measurement_base() -> None:
    runtime_config = _lab_runtime_config(camera_backend="hik_gige_mvs")
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=1201, y=270, width=1356, height=1048),
        metric_box=MetricBox(center_x=1879, center_y=794, width=1355, height=1047, angle_deg=0.0),
        point_a_px=PixelPoint(x=1329, y=851),
        point_b_px=PixelPoint(x=2327, y=851),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=200,
        direction_angle_deg=0.0,
        direction_projection_mode="mask_projection",
    )

    plan = build_measurement_capture_plan(
        runtime_config=runtime_config,
        definition=definition,
    )

    assert plan.measurement_profile.device_roi == DeviceRoiConfig(
        x=1041,
        y=110,
        width=1676,
        height=1368,
    )
    assert plan.metric_definition.analysis_roi == RectRegion(
        x=160,
        y=160,
        width=1356,
        height=1048,
    )
    assert plan.metric_definition.point_a_px == PixelPoint(x=288, y=741)
    assert plan.metric_definition.point_b_px == PixelPoint(x=1286, y=741)


def test_build_measurement_capture_plan_preserves_padding_for_wide_rotated_metric_box() -> None:
    runtime_config = _lab_runtime_config(camera_backend="hik_gige_mvs")
    runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig(
        x=1440,
        y=1086,
        width=1120,
        height=620,
    )
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=1120, height=620),
        metric_box=MetricBox(center_x=700, center_y=150, width=650, height=180, angle_deg=-8.0),
        point_a_px=PixelPoint(x=378, y=192),
        point_b_px=PixelPoint(x=1021, y=102),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        ignore_internal_texture=True,
        min_target_area_px=200,
    )

    plan = build_measurement_capture_plan(
        runtime_config=runtime_config,
        definition=definition,
    )
    local_frame = RectRegion(
        x=0,
        y=0,
        width=plan.measurement_profile.device_roi.width,
        height=plan.measurement_profile.device_roi.height,
    )

    assert plan.measurement_profile.device_roi.width > 900
    assert plan.measurement_profile.device_roi.height > 300
    assert plan.metric_definition.analysis_roi.x >= 0
    assert plan.metric_definition.analysis_roi.y >= 0
    assert plan.metric_definition.analysis_roi.x + plan.metric_definition.analysis_roi.width <= local_frame.width
    assert plan.metric_definition.analysis_roi.y + plan.metric_definition.analysis_roi.height <= local_frame.height
    assert _metric_box_within_region(local_frame, plan.metric_definition.metric_box)


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


def test_offline_capture_backend_uses_recorded_frames_temperature_and_real_tracker(tmp_path: Path) -> None:
    frames_dir = tmp_path / "capture" / "frames"
    frames_dir.mkdir(parents=True)
    image = [[220 for _ in range(320)] for _ in range(160)]
    for row in range(60, 100):
        for col in range(90, 230):
            image[row][col] = 40
    np.save(frames_dir / "frame_000001.npy", np.asarray(image, dtype=np.uint8))
    (tmp_path / "capture" / "temperature.csv").write_text(
        "\n".join(
            [
                "frame_index,camera_timestamp_ms,temp_timestamp_ms,celsius,source,sampled_this_frame,error",
                "1,1000,1001,-0.5,lu92xx_modbus_rtu,1,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime_config = _lab_runtime_config(camera_backend="offline_capture")
    runtime_config.adapters["temp"] = "offline_capture"
    runtime_config.live.temp.backend = "offline_capture"
    runtime_config.camera["offline_capture"] = {
        "capture_dir": str(tmp_path / "capture"),
    }
    runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig()
    runtime_config.live.camera.measurement.device_roi = DeviceRoiConfig()
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=320, height=160),
        metric_box=MetricBox(center_x=160, center_y=80, width=220, height=80, angle_deg=0.0),
        point_a_px=PixelPoint(x=80, y=80),
        point_b_px=PixelPoint(x=240, y=80),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )

    camera = open_camera(runtime_config, profile_name="measurement")
    temp_controller = build_temp_controller(runtime_config)
    metric_source = build_metric_source(
        runtime_config=runtime_config,
        definition=definition,
        target_temperature_celsius=25.0,
    )

    frame = camera.read_frame()
    temp_controller.set_target_temperature(25.0)
    temp_controller.start_output()
    temp = temp_controller.read()
    metric = metric_source.extract(frame, temp, sample_index=0, total_samples=1)

    assert frame.source == "offline_capture:capture"
    assert frame.image.shape == (160, 320)
    assert temp.celsius == -0.5
    assert temp.source == "offline_capture:capture"
    assert metric.meta["tracking_mode"] == "prior_gated_reacquire"
    assert metric.meta["tracking_state"] == "bootstrapped"


def test_build_metric_source_uses_frame_directional_contour_for_direction_definition() -> None:
    runtime_config = _lab_runtime_config(camera_backend="hik_gige_mvs")
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=320, height=160),
        metric_box=MetricBox(center_x=160, center_y=80, width=220, height=80, angle_deg=0.0),
        point_a_px=PixelPoint(x=80, y=80),
        point_b_px=PixelPoint(x=240, y=80),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        ignore_internal_texture=True,
        min_target_area_px=150,
        direction_angle_deg=0.0,
        direction_projection_mode="max_chord",
    )
    image = [[220 for _ in range(320)] for _ in range(160)]
    for row in range(60, 100):
        for col in range(90, 230):
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

    assert metric.meta["selection_mode"] == "directional_contour_max_chord"
    assert metric.meta["tracking_mode"] == "prior_gated_reacquire"
    assert metric.meta["tracking_state"] == "bootstrapped"
