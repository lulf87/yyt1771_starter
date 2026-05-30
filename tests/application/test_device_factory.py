from pathlib import Path

import numpy as np
import pytest

from src.application.device_factory import (
    apply_measurement_acquisition_roi,
    build_measurement_capture_plan,
    build_temp_controller,
    build_metric_source,
    open_camera,
)
from src.application.real_offline_alignment_guard import RealOfflineAlignmentGuardError
from src.application.runtime_config import RuntimeConfig, WebAppConfig, load_runtime_config
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
        profile="unit_lab_camera_mock_temp",
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


def test_open_camera_blocks_locked_profile_alignment_drift_before_device_creation() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")
    runtime_config.live.run.preview_display_max_width = 800

    with pytest.raises(RealOfflineAlignmentGuardError, match="open_camera:setup_preview"):
        open_camera(runtime_config, profile_name="setup_preview")


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
        runtime_config=runtime_config,
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


def test_apply_measurement_acquisition_roi_blocks_locked_profile_stale_definition_before_retranslation() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")
    good_definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=650, y=220, width=1100, height=740),
        metric_box=MetricBox(center_x=1200, center_y=590, width=1060, height=660, angle_deg=30.0),
        point_a_px=PixelPoint(x=760, y=745),
        point_b_px=PixelPoint(x=1625, y=745),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=False,
        min_target_area_px=200,
        direction_angle_deg=30.0,
        direction_projection_mode="max_chord",
    )
    stale_definition = MeasurementDefinition(
        analysis_roi=good_definition.analysis_roi,
        metric_box=good_definition.metric_box,
        point_a_px=good_definition.point_a_px,
        point_b_px=good_definition.point_b_px,
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
        direction_angle_deg=30.0,
        direction_projection_mode="mask_projection",
    )
    requested_plan = build_measurement_capture_plan(
        runtime_config=runtime_config,
        definition=good_definition,
    )

    with pytest.raises(RealOfflineAlignmentGuardError, match="apply_measurement_acquisition_roi"):
        apply_measurement_acquisition_roi(
            requested_plan,
            runtime_config=runtime_config,
            definition=stale_definition,
            applied_device_roi=DeviceRoiConfig(x=832, y=560, width=360, height=184),
        )


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


def test_build_metric_source_blocks_locked_profile_stale_definition_before_source_creation() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=320, height=160),
        metric_box=MetricBox(center_x=160, center_y=80, width=220, height=80, angle_deg=0.0),
        point_a_px=PixelPoint(x=80, y=80),
        point_b_px=PixelPoint(x=240, y=80),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
        direction_angle_deg=0.0,
        direction_projection_mode="mask_projection",
    )

    with pytest.raises(RealOfflineAlignmentGuardError, match="build_metric_source"):
        build_metric_source(
            runtime_config=runtime_config,
            definition=definition,
            target_temperature_celsius=45.0,
        )


def test_real_and_offline_metric_sources_match_on_same_pixel_frame() -> None:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=320, height=160),
        metric_box=MetricBox(center_x=160, center_y=80, width=220, height=80, angle_deg=0.0),
        point_a_px=PixelPoint(x=80, y=80),
        point_b_px=PixelPoint(x=240, y=80),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
        direction_angle_deg=0.0,
        direction_projection_mode="max_chord",
    )
    image = [[220 for _ in range(320)] for _ in range(160)]
    for row in range(60, 100):
        for col in range(90, 230):
            image[row][col] = 40
    frame = FramePacket(timestamp_ms=1_000, source="fixture", image=image, frame_id=1)
    temp = TempReading(timestamp_ms=1_005, celsius=25.0, source="fixture")

    real_source = build_metric_source(
        runtime_config=_lab_runtime_config(camera_backend="hik_gige_mvs"),
        definition=definition,
        target_temperature_celsius=45.0,
    )
    offline_source = build_metric_source(
        runtime_config=_lab_runtime_config(camera_backend="offline_capture"),
        definition=definition,
        target_temperature_celsius=45.0,
    )

    real_metric = real_source.extract(frame, temp, sample_index=0, total_samples=1)
    offline_metric = offline_source.extract(frame, temp, sample_index=0, total_samples=1)

    assert real_metric.meta["tracking_mode"] == "prior_gated_reacquire"
    assert offline_metric.meta["tracking_mode"] == "prior_gated_reacquire"
    assert real_metric.meta["selection_mode"] == offline_metric.meta["selection_mode"]
    assert real_metric.point_a_px == offline_metric.point_a_px
    assert real_metric.point_b_px == offline_metric.point_b_px
    assert real_metric.metric_raw == offline_metric.metric_raw


def test_real_and_offline_capture_plans_share_live_local_pixels_for_same_setup_definition() -> None:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=650, y=220, width=1100, height=740),
        metric_box=MetricBox(center_x=1200, center_y=590, width=1060, height=660, angle_deg=30.0),
        point_a_px=PixelPoint(x=760, y=745),
        point_b_px=PixelPoint(x=1625, y=745),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=False,
        min_target_area_px=200,
        direction_angle_deg=30.0,
        direction_projection_mode="max_chord",
    )

    real_plan = build_measurement_capture_plan(
        runtime_config=load_runtime_config("dev_lab"),
        definition=definition,
    )
    offline_plan = build_measurement_capture_plan(
        runtime_config=load_runtime_config("dev_offline_capture"),
        definition=definition,
    )

    assert real_plan.measurement_profile.device_roi.width == offline_plan.measurement_profile.device_roi.width
    assert real_plan.measurement_profile.device_roi.height == offline_plan.measurement_profile.device_roi.height
    assert real_plan.metric_definition == offline_plan.metric_definition
    assert real_plan.setup_preview_roi == DeviceRoiConfig(x=512, y=342, width=2048, height=1364)
    assert offline_plan.setup_preview_roi == DeviceRoiConfig(x=0, y=0, width=2048, height=1364)
    assert (
        real_plan.measurement_profile.device_roi.x - real_plan.setup_preview_roi.x
        == offline_plan.measurement_profile.device_roi.x
    )
    assert (
        real_plan.measurement_profile.device_roi.y - real_plan.setup_preview_roi.y
        == offline_plan.measurement_profile.device_roi.y
    )


def test_measurement_capture_plan_preserves_envelope_geometry_fields() -> None:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=650, y=220, width=1100, height=740),
        metric_box=MetricBox(center_x=1200, center_y=590, width=1060, height=660, angle_deg=30.0),
        point_a_px=PixelPoint(x=760, y=745),
        point_b_px=PixelPoint(x=1625, y=745),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=False,
        min_target_area_px=200,
        direction_angle_deg=30.0,
        direction_projection_mode="envelope_max_width",
        target_geometry_mode="mesh_lattice",
        side_guard_ratio=0.14,
    )

    real_plan = build_measurement_capture_plan(
        runtime_config=load_runtime_config("dev_lab"),
        definition=definition,
    )
    offline_plan = build_measurement_capture_plan(
        runtime_config=load_runtime_config("dev_offline_capture"),
        definition=definition,
    )

    assert real_plan.metric_definition == offline_plan.metric_definition
    assert real_plan.metric_definition.direction_projection_mode == "envelope_max_width"
    assert real_plan.metric_definition.target_geometry_mode == "mesh_lattice"
    assert real_plan.metric_definition.side_guard_ratio == pytest.approx(0.14)


def test_build_measurement_capture_plan_blocks_locked_profile_stale_definition_before_pixel_planning() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=650, y=220, width=1100, height=740),
        metric_box=MetricBox(center_x=1200, center_y=590, width=1060, height=660, angle_deg=30.0),
        point_a_px=PixelPoint(x=760, y=745),
        point_b_px=PixelPoint(x=1625, y=745),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
        direction_angle_deg=30.0,
        direction_projection_mode="mask_projection",
    )

    with pytest.raises(RealOfflineAlignmentGuardError, match="build_measurement_capture_plan"):
        build_measurement_capture_plan(runtime_config=runtime_config, definition=definition)


@pytest.mark.parametrize("angle_deg", list(range(0, 360, 30)))
def test_real_and_offline_profiles_share_metric_pixels_across_roi_angles(angle_deg: int) -> None:
    center_x = 1024
    center_y = 682
    half_span = 420
    angle_rad = np.deg2rad(angle_deg)
    dx = int(round(np.cos(angle_rad) * half_span))
    dy = int(round(np.sin(angle_rad) * half_span))
    point_a = PixelPoint(x=center_x - dx, y=center_y - dy)
    point_b = PixelPoint(x=center_x + dx, y=center_y + dy)
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=120, y=120, width=1800, height=1120),
        metric_box=MetricBox(center_x=center_x, center_y=center_y, width=980, height=220, angle_deg=float(angle_deg)),
        point_a_px=point_a,
        point_b_px=point_b,
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=False,
        min_target_area_px=200,
        direction_angle_deg=float(angle_deg),
        direction_projection_mode="max_chord",
    )

    real_config = load_runtime_config("dev_lab")
    offline_config = load_runtime_config("dev_offline_capture")
    real_plan = build_measurement_capture_plan(runtime_config=real_config, definition=definition)
    offline_plan = build_measurement_capture_plan(runtime_config=offline_config, definition=definition)

    assert real_plan.metric_definition == offline_plan.metric_definition
    assert real_plan.measurement_profile.device_roi.width == offline_plan.measurement_profile.device_roi.width
    assert real_plan.measurement_profile.device_roi.height == offline_plan.measurement_profile.device_roi.height
    assert (
        real_plan.measurement_profile.device_roi.x - real_plan.setup_preview_roi.x
        == offline_plan.measurement_profile.device_roi.x
    )
    assert (
        real_plan.measurement_profile.device_roi.y - real_plan.setup_preview_roi.y
        == offline_plan.measurement_profile.device_roi.y
    )

    image = np.full((1364, 2048), 240, dtype=np.uint8)
    _paint_test_line(
        image,
        (real_plan.metric_definition.point_a_px.x, real_plan.metric_definition.point_a_px.y),
        (real_plan.metric_definition.point_b_px.x, real_plan.metric_definition.point_b_px.y),
        width=28,
        value=30,
    )
    frame = FramePacket(timestamp_ms=1_000, source="fixture", image=image, frame_id=1)
    temp = TempReading(timestamp_ms=1_005, celsius=25.0, source="fixture")

    real_metric = build_metric_source(
        runtime_config=real_config,
        definition=real_plan.metric_definition,
        target_temperature_celsius=45.0,
    ).extract(frame, temp, sample_index=0, total_samples=1)
    offline_metric = build_metric_source(
        runtime_config=offline_config,
        definition=offline_plan.metric_definition,
        target_temperature_celsius=45.0,
    ).extract(frame, temp, sample_index=0, total_samples=1)

    assert real_metric.quality > 0.0
    assert offline_metric.quality > 0.0
    assert real_metric.meta["selection_mode"] == offline_metric.meta["selection_mode"]
    assert real_metric.point_a_px == offline_metric.point_a_px
    assert real_metric.point_b_px == offline_metric.point_b_px
    assert real_metric.metric_raw == offline_metric.metric_raw


def _paint_test_line(
    image: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    width: int,
    value: int,
) -> None:
    x0, y0 = start
    x1, y1 = end
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    radius = max(0, int(width) // 2)
    for index in range(steps + 1):
        ratio = index / steps
        x = int(round(x0 + (x1 - x0) * ratio))
        y = int(round(y0 + (y1 - y0) * ratio))
        image[
            max(0, y - radius) : min(image.shape[0], y + radius + 1),
            max(0, x - radius) : min(image.shape[1], x + radius + 1),
        ] = value
