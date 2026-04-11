import threading

import numpy as np

from src.application.live_preview_service import LivePreviewService
from src.application.live_run_service import (
    _ActiveLiveRun,
    _augment_telemetry_for_setup_preview,
    _composite_tracking_frame_into_setup_preview,
    _definition_in_setup_source_space,
    _measurement_capture_plan_payload,
    _preview_point_from_tracking_frame_meta,
    _should_cache_tracking_preview,
)
from src.application.device_factory import apply_measurement_acquisition_roi, build_measurement_capture_plan
from src.application.runtime_config import RuntimeConfig, WebAppConfig
from src.core.config_models import DeviceRoiConfig
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion


class _NativePreviewImage:
    def __init__(self, *, source_width: int, source_height: int, preview_width: int, preview_height: int) -> None:
        self.shape = (source_height, source_width)
        self._preview_width = preview_width
        self._preview_height = preview_height

    def downsample_bitmap_payload(self, *, max_width: int = 640, max_height: int = 480) -> tuple[int, int, bytes]:
        return (self._preview_width, self._preview_height, bytes([0]) * (self._preview_width * self._preview_height))


class _FetchPreviewService:
    def __init__(self, frame: FramePacket) -> None:
        self._frame = frame

    def fetch_frame(self, runtime_config, *, run_id: str = "", prefer_cached: bool = False) -> FramePacket:
        return self._frame


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

    composited, preview_points = _composite_tracking_frame_into_setup_preview(
        preview_service=preview_service,
        active_run=_ActiveLiveRun(
            run_id="run-001",
            stop_event=threading.Event(),
            preview_display_max_width=5,
            preview_display_max_height=4,
        ),
        run_id="run-001",
        measurement_frame=measurement_frame,
        measurement_capture_plan=measurement_capture_plan,
    )

    assert composited.frame_id == 2
    assert composited.meta["tracking_composited"] is True
    assert composited.meta["tracking_origin_preview_px"] == [2, 1]
    assert preview_points.point_a is None
    assert preview_points.point_b is None
    assert np.asarray(composited.image).tolist() == [
        [10, 10, 10, 10, 10],
        [10, 10, 200, 201, 10],
        [10, 10, 202, 203, 10],
        [10, 10, 10, 10, 10],
    ]


def test_composite_tracking_frame_into_setup_preview_falls_back_to_base_preview_when_origin_missing() -> None:
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

    composited, preview_points = _composite_tracking_frame_into_setup_preview(
        preview_service=preview_service,
        active_run=_ActiveLiveRun(
            run_id="run-001",
            stop_event=threading.Event(),
            preview_display_max_width=5,
            preview_display_max_height=4,
        ),
        run_id="run-001",
        measurement_frame=measurement_frame,
        measurement_capture_plan=None,
    )

    assert composited.frame_id == 2
    assert composited.meta["tracking_composited"] is False
    assert composited.meta["tracking_preview_fallback"] is True
    assert preview_points.point_a is None
    assert preview_points.point_b is None
    assert np.asarray(composited.image).tolist() == [
        [10, 10, 10, 10, 10],
        [10, 10, 10, 10, 10],
        [10, 10, 10, 10, 10],
        [10, 10, 10, 10, 10],
    ]


def test_preview_point_from_tracking_frame_meta_scales_local_points_into_display_space() -> None:
    meta = {
        "tracking_origin_preview_px": [10, 20],
        "tracking_preview_scale_x": 0.5,
        "tracking_preview_scale_y": 0.25,
    }

    point = _preview_point_from_tracking_frame_meta(meta, [100, 40])

    assert point == [60, 30]


def test_augment_telemetry_for_setup_preview_preserves_existing_preview_points() -> None:
    row = {
        "point_a_px": [80, 92],
        "point_b_px": [280, 92],
        "point_a_preview_px": [10, 11],
        "point_b_preview_px": [20, 21],
    }
    measurement_capture_plan = {
        "effective_local_origin_in_setup_preview_px": {
            "x": 840,
            "y": 568,
        }
    }

    _augment_telemetry_for_setup_preview(row, measurement_capture_plan)

    assert row["point_a_preview_px"] == [10, 11]
    assert row["point_b_preview_px"] == [20, 21]


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
        "x": 870,
        "y": 598,
        "width": 300,
        "height": 124,
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
    assert payload["requested_local_origin_in_setup_preview_px"] == {"x": 870, "y": 598}
    assert payload["setup_to_effective_local_translation_px"] == {"dx": -832, "dy": -560}
    assert payload["setup_to_requested_local_translation_px"] == {"dx": -870, "dy": -598}


def test_definition_in_setup_source_space_scales_preview_coordinates_into_sensor_coordinates() -> None:
    runtime_config = RuntimeConfig(
        profile="dev_lab_camera_mock_temp",
        platform="mac",
        mode="lab",
        webapp=WebAppConfig(host="127.0.0.1", port=8000),
        adapters={"camera": "hik_gige_mvs", "temp": "mock", "plc": "mock"},
    )
    runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig()
    runtime_config.live.run.preview_display_max_width = 816
    runtime_config.live.run.preview_display_max_height = 544
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=360, y=110, width=220, height=360),
        metric_box=MetricBox(center_x=470, center_y=290, width=180, height=90, angle_deg=0.0),
        point_a_px=PixelPoint(x=380, y=290),
        point_b_px=PixelPoint(x=560, y=290),
        foreground_polarity="dark_on_light",
        threshold_mode="otsu",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )
    frame = FramePacket(
        timestamp_ms=1_000,
        source="setup_preview",
        image=_NativePreviewImage(source_width=3072, source_height=2048, preview_width=816, preview_height=544),
        frame_id=1,
    )

    translated = _definition_in_setup_source_space(
        definition=definition,
        runtime_config=runtime_config,
        preview_service=_FetchPreviewService(frame),
        run_id="run-001",
    )

    assert translated.analysis_roi.x == 1355
    assert translated.analysis_roi.y == 414
    assert translated.analysis_roi.width == 829
    assert translated.analysis_roi.height == 1355
    assert translated.metric_box.center_x == 1769
    assert translated.metric_box.center_y == 1092
    assert translated.metric_box.width == 678
    assert translated.metric_box.height == 339
    assert translated.point_a_px.x == 1431
    assert translated.point_b_px.x == 2108
    assert translated.point_a_px.y == 1092
    assert translated.point_b_px.y == 1092


def test_should_cache_tracking_preview_honors_minimum_interval() -> None:
    active_run = _ActiveLiveRun(
        run_id="run-001",
        stop_event=threading.Event(),
        tracking_preview_min_interval_ms=250,
        last_tracking_preview_cached_at_ms=1_000,
    )

    assert _should_cache_tracking_preview(active_run, 1_100) is False
    assert _should_cache_tracking_preview(active_run, 1_250) is True
