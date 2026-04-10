from src.application.live_preview_service import LivePreviewService
from src.application.live_run_service import (
    _augment_telemetry_for_setup_preview,
    _composite_tracking_frame_into_setup_preview,
    _measurement_capture_plan_payload,
)
from src.application.device_factory import apply_measurement_acquisition_roi, build_measurement_capture_plan
from src.application.runtime_config import RuntimeConfig, WebAppConfig
from src.core.config_models import DeviceRoiConfig
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion


def test_augment_telemetry_for_setup_preview_adds_preview_coordinates() -> None:
    row = {
        "point_a_px": [80, 92],
        "point_b_px": [280, 92],
    }
    measurement_capture_plan = {
        "effective_local_origin_in_setup_preview_px": {
            "x": 840,
            "y": 568,
        }
    }

    _augment_telemetry_for_setup_preview(row, measurement_capture_plan)

    assert row["point_a_preview_px"] == [920, 660]
    assert row["point_b_preview_px"] == [1120, 660]


def test_composite_tracking_frame_into_setup_preview_pastes_measurement_frame_into_cached_preview() -> None:
    preview_service = LivePreviewService()
    preview_service.cache_frame(
        run_id="run-001",
        frame=FramePacket(
            timestamp_ms=1_000,
            source="setup_preview",
            image=[
                [10, 10, 10, 10, 10],
                [10, 10, 10, 10, 10],
                [10, 10, 10, 10, 10],
                [10, 10, 10, 10, 10],
            ],
            frame_id=1,
        ),
    )
    measurement_frame = FramePacket(
        timestamp_ms=2_000,
        source="measurement",
        image=[
            [200, 201],
            [202, 203],
        ],
        frame_id=2,
    )
    measurement_capture_plan = {
        "effective_local_origin_in_setup_preview_px": {
            "x": 2,
            "y": 1,
        }
    }

    composited = _composite_tracking_frame_into_setup_preview(
        preview_service=preview_service,
        run_id="run-001",
        measurement_frame=measurement_frame,
        measurement_capture_plan=measurement_capture_plan,
    )

    assert composited.frame_id == 2
    assert composited.meta["tracking_composited"] is True
    assert composited.meta["tracking_origin_px"] == [2, 1]
    assert composited.image.tolist() == [
        [10, 10, 10, 10, 10],
        [10, 10, 200, 201, 10],
        [10, 10, 202, 203, 10],
        [10, 10, 10, 10, 10],
    ]


def test_measurement_capture_plan_payload_uses_applied_roi_relative_to_full_frame_preview() -> None:
    runtime_config = RuntimeConfig(
        profile="dev_lab_camera_mock_temp",
        platform="mac",
        mode="lab",
        webapp=WebAppConfig(host="127.0.0.1", port=8000),
        adapters={"camera": "hik_gige_mvs", "temp": "mock", "plc": "mock"},
    )
    runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig()
    runtime_config.live.camera.measurement.device_roi = DeviceRoiConfig(
        x=512,
        y=342,
        width=2048,
        height=1364,
    )
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=900, y=600, width=240, height=120),
        metric_box=MetricBox(center_x=1020, center_y=660, width=200, height=60, angle_deg=0.0),
        point_a_px=PixelPoint(x=920, y=660),
        point_b_px=PixelPoint(x=1120, y=660),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )

    requested_plan = build_measurement_capture_plan(runtime_config=runtime_config, definition=definition)
    applied_plan = apply_measurement_acquisition_roi(
        requested_plan,
        definition=definition,
        applied_device_roi=DeviceRoiConfig(x=832, y=560, width=360, height=184),
    )

    payload = _measurement_capture_plan_payload(
        original_definition=definition,
        requested_measurement_plan=requested_plan,
        applied_measurement_plan=applied_plan,
    )

    assert payload["requested_effective_acquisition_roi"] == {
        "x": 840,
        "y": 568,
        "width": 360,
        "height": 184,
    }
    assert payload["applied_effective_acquisition_roi"] == {
        "x": 832,
        "y": 560,
        "width": 360,
        "height": 184,
    }
    assert payload["setup_preview_sensor_roi"] == {
        "x": 0,
        "y": 0,
        "width": 0,
        "height": 0,
    }
    assert payload["effective_local_origin_in_setup_preview_px"] == {"x": 832, "y": 560}
    assert payload["requested_local_origin_in_setup_preview_px"] == {"x": 840, "y": 568}
    assert payload["setup_to_effective_local_translation_px"] == {"dx": -832, "dy": -560}
