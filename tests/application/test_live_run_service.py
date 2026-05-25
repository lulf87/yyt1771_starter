from dataclasses import replace
import threading

import numpy as np

from src.application.live_preview_service import LivePreviewService
from src.application.live_run_service import (
    _ActiveLiveRun,
    _FramePixelContractCamera,
    _augment_telemetry_for_setup_preview,
    _coerce_native_bitmap_pixels,
    _composite_tracking_frame_into_setup_preview,
    _definition_in_setup_source_space,
    _measurement_capture_plan_payload,
    _preview_scaled_grayscale_image,
    _preview_point_from_tracking_frame_meta,
    _runtime_config_with_measurement_profile,
    _runtime_config_with_operator_output_power,
    _should_cache_tracking_preview,
    _tracking_preview_min_interval_ms,
)
from src.application.device_factory import apply_measurement_acquisition_roi, build_measurement_capture_plan
from src.application.frame_pixel_contract import FramePixelContractError
from src.application.runtime_config import RuntimeConfig, WebAppConfig, load_runtime_config
from src.core.config_models import DeviceRoiConfig, RunRuntimeConfig
from src.core.models import (
    FramePacket,
    MeasurementDefinition,
    MetricBox,
    PixelPoint,
    RectRegion,
    RunDraftRecord,
    TemperatureSettingsBundle,
)


class _NativePreviewImage:
    def __init__(self, *, source_width: int, source_height: int, preview_width: int, preview_height: int) -> None:
        self.shape = (source_height, source_width)
        self._preview_width = preview_width
        self._preview_height = preview_height

    def downsample_bitmap_payload(self, *, max_width: int = 640, max_height: int = 480) -> tuple[int, int, bytes]:
        return (self._preview_width, self._preview_height, bytes([0]) * (self._preview_width * self._preview_height))


class _NativePreviewArrayImage:
    def downsample_bitmap_payload(self, *, max_width: int = 640, max_height: int = 480):
        return (max_width, max_height, np.arange(max_width * max_height, dtype=np.uint8))


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

    _augment_telemetry_for_setup_preview(
        row,
        measurement_capture_plan,
        preview_source_size=(1280, 960),
        preview_size=(640, 480),
    )

    assert row["point_a_preview_px"] == [460, 330]
    assert row["point_b_preview_px"] == [560, 330]


def test_augment_telemetry_for_setup_preview_adds_direction_projection_preview_coordinates() -> None:
    row = {
        "point_a_px": [80, 92],
        "point_b_px": [280, 92],
        "source_point_a_px": [70, 112],
        "source_point_b_px": [290, 72],
        "axis_point_a_px": [80, 92],
        "axis_point_b_px": [280, 92],
    }
    measurement_capture_plan = {
        "effective_local_origin_in_setup_preview_px": {
            "x": 840,
            "y": 568,
        }
    }

    _augment_telemetry_for_setup_preview(
        row,
        measurement_capture_plan,
        preview_source_size=(1280, 960),
        preview_size=(640, 480),
    )

    assert row["source_point_a_preview_px"] == [455, 340]
    assert row["source_point_b_preview_px"] == [565, 320]
    assert row["axis_point_a_preview_px"] == [460, 330]
    assert row["axis_point_b_preview_px"] == [560, 330]


def test_augment_telemetry_for_setup_preview_does_not_label_source_points_as_preview_without_preview_geometry() -> None:
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

    assert "point_a_preview_px" not in row
    assert "point_b_preview_px" not in row


def test_coerce_native_bitmap_pixels_accepts_numpy_arrays() -> None:
    payload = _coerce_native_bitmap_pixels(np.arange(6, dtype=np.uint8), expected_size=6)

    assert payload == bytes([0, 1, 2, 3, 4, 5])


def test_preview_scaled_grayscale_image_accepts_numpy_native_bitmap_payload() -> None:
    scaled = _preview_scaled_grayscale_image(
        _NativePreviewArrayImage(),
        target_width=3,
        target_height=2,
    )

    assert scaled is not None
    assert scaled.shape == (2, 3)
    assert scaled.tolist() == [[0, 1, 2], [3, 4, 5]]


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


def test_composite_tracking_frame_into_setup_preview_projects_tracking_points_from_measurement_frame_space() -> None:
    preview_service = LivePreviewService()
    preview_service.cache_frame(
        run_id="run-001",
        frame=FramePacket(
            timestamp_ms=1_000,
            source="setup_preview",
            image=[
                [10, 10, 10, 10, 10, 10],
                [10, 10, 10, 10, 10, 10],
                [10, 10, 10, 10, 10, 10],
                [10, 10, 10, 10, 10, 10],
                [10, 10, 10, 10, 10, 10],
            ],
            frame_id=1,
        ),
    )
    measurement_frame = FramePacket(
        timestamp_ms=2_000,
        source="measurement",
        image=[
            [200, 201, 202],
            [203, 204, 205],
        ],
        frame_id=2,
        meta={
            "point_a_px_local": [1, 0],
            "point_b_px_local": [2, 1],
        },
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
            preview_display_max_width=6,
            preview_display_max_height=5,
        ),
        run_id="run-001",
        measurement_frame=measurement_frame,
        measurement_capture_plan=measurement_capture_plan,
    )

    assert composited.meta["tracking_composited"] is True
    assert preview_points.point_a == [3, 1]
    assert preview_points.point_b == [4, 2]


def test_composite_tracking_frame_into_setup_preview_crops_negative_origin_consistently() -> None:
    preview_service = LivePreviewService()
    preview_service.cache_frame(
        run_id="run-001",
        frame=FramePacket(
            timestamp_ms=1_000,
            source="setup_preview",
            image=[
                [10, 10, 10, 10],
                [10, 10, 10, 10],
                [10, 10, 10, 10],
                [10, 10, 10, 10],
            ],
            frame_id=1,
        ),
    )
    measurement_frame = FramePacket(
        timestamp_ms=2_000,
        source="measurement",
        image=[
            [200, 201, 202],
            [203, 204, 205],
            [206, 207, 208],
        ],
        frame_id=2,
        meta={
            "point_a_px_local": [1, 1],
            "point_b_px_local": [2, 2],
        },
    )
    measurement_capture_plan = {
        "effective_local_origin_in_setup_preview_px": {
            "x": -1,
            "y": -1,
        }
    }

    composited, preview_points = _composite_tracking_frame_into_setup_preview(
        preview_service=preview_service,
        active_run=_ActiveLiveRun(
            run_id="run-001",
            stop_event=threading.Event(),
            preview_display_max_width=4,
            preview_display_max_height=4,
        ),
        run_id="run-001",
        measurement_frame=measurement_frame,
        measurement_capture_plan=measurement_capture_plan,
    )

    assert composited.meta["tracking_composited"] is True
    assert composited.meta["tracking_origin_preview_px"] == [-1, -1]
    assert composited.meta["tracking_paste_origin_preview_px"] == [0, 0]
    assert composited.meta["tracking_paste_crop_preview_px"] == [1, 1]
    assert preview_points.point_a == [0, 0]
    assert preview_points.point_b == [1, 1]
    assert np.asarray(composited.image).tolist() == [
        [204, 205, 10, 10],
        [207, 208, 10, 10],
        [10, 10, 10, 10],
        [10, 10, 10, 10],
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
        "tracking_origin_source_px": [20, 80],
        "tracking_preview_source_width": 400,
        "tracking_preview_source_height": 400,
        "tracking_preview_width": 200,
        "tracking_preview_height": 100,
    }

    point = _preview_point_from_tracking_frame_meta(meta, [100, 40])

    assert point == [60, 30]


def test_preview_point_from_tracking_frame_meta_clamps_negative_source_points() -> None:
    meta = {
        "tracking_origin_source_px": [0, -100],
        "tracking_preview_source_width": 100,
        "tracking_preview_source_height": 100,
        "tracking_preview_width": 50,
        "tracking_preview_height": 50,
    }

    point = _preview_point_from_tracking_frame_meta(meta, [20, 10])

    assert point == [10, 0]


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
        profile="unit_lab_camera_mock_temp",
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
    assert payload["setup_to_requested_local_translation_px"] == {"dx": -840, "dy": -568}


def test_definition_in_setup_source_space_preserves_source_coordinates_even_in_display_bounds() -> None:
    runtime_config = RuntimeConfig(
        profile="dev_lab",
        platform="mac",
        mode="lab",
        webapp=WebAppConfig(host="127.0.0.1", port=8002),
        adapters={"camera": "offline_capture", "temp": "offline_capture", "plc": "mock"},
    )
    runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig(x=512, y=342, width=2048, height=1364)
    runtime_config.live.run.preview_display_max_width = 816
    runtime_config.live.run.preview_display_max_height = 544
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=120, y=90, width=360, height=260),
        metric_box=MetricBox(center_x=300, center_y=220, width=280, height=120, angle_deg=12.0),
        point_a_px=PixelPoint(x=170, y=230),
        point_b_px=PixelPoint(x=430, y=220),
        foreground_polarity="dark_on_light",
        threshold_mode="otsu",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )
    frame = FramePacket(
        timestamp_ms=1_000,
        source="setup_preview",
        image=_NativePreviewImage(source_width=2048, source_height=1364, preview_width=816, preview_height=543),
        frame_id=1,
    )

    translated = _definition_in_setup_source_space(
        definition=definition,
        runtime_config=runtime_config,
        preview_service=_FetchPreviewService(frame),
        run_id="run-001",
    )

    assert translated == definition


def test_live_run_measurement_camera_rejects_pixels_that_differ_from_offline_material() -> None:
    class WrongSizeCamera:
        def read_frame(self) -> FramePacket:
            return FramePacket(
                timestamp_ms=2_000,
                source="wrong_size_measurement",
                image=np.zeros((620, 1120), dtype=np.uint8),
                frame_id=1,
            )

    camera = _FramePixelContractCamera(
        WrongSizeCamera(),
        runtime_config=load_runtime_config("dev_lab"),
        profile_name="measurement",
    )

    try:
        camera.read_frame()
    except FramePixelContractError as exc:
        assert "live_run_measurement_frame" in str(exc)
        assert "expected=2048x1364, actual=1120x620" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected locked live-run pixel contract failure")


def test_live_run_measurement_camera_rejects_roi_that_differs_from_offline_material() -> None:
    class WrongRoiCamera:
        def read_frame(self) -> FramePacket:
            return FramePacket(
                timestamp_ms=2_000,
                source="wrong_roi_measurement",
                image=np.zeros((1364, 2048), dtype=np.uint8),
                frame_id=1,
                meta={"device_roi": {"x": 0, "y": 0, "width": 2048, "height": 1364}},
            )

    camera = _FramePixelContractCamera(
        WrongRoiCamera(),
        runtime_config=load_runtime_config("dev_lab"),
        profile_name="measurement",
    )

    try:
        camera.read_frame()
    except FramePixelContractError as exc:
        assert "live_run_measurement_frame" in str(exc)
        assert "expected_roi=x=512,y=342,width=2048,height=1364" in str(exc)
        assert "actual_roi=x=0,y=0,width=2048,height=1364" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected locked live-run ROI contract failure")


def test_live_run_measurement_camera_rejects_missing_roi_metadata() -> None:
    class MissingRoiMetaCamera:
        def read_frame(self) -> FramePacket:
            return FramePacket(
                timestamp_ms=2_000,
                source="missing_roi_meta_measurement",
                image=np.zeros((1364, 2048), dtype=np.uint8),
                frame_id=1,
            )

    camera = _FramePixelContractCamera(
        MissingRoiMetaCamera(),
        runtime_config=load_runtime_config("dev_lab"),
        profile_name="measurement",
    )

    try:
        camera.read_frame()
    except FramePixelContractError as exc:
        assert "live_run_measurement_frame" in str(exc)
        assert "missing device_roi metadata" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected missing ROI metadata contract failure")


def test_locked_profile_rejects_unknown_camera_profile_name() -> None:
    class MatchingSizeCamera:
        def read_frame(self) -> FramePacket:
            return FramePacket(
                timestamp_ms=2_000,
                source="matching_size_unknown_profile",
                image=np.zeros((1364, 2048), dtype=np.uint8),
                frame_id=1,
                meta={"device_roi": {"x": 512, "y": 342, "width": 2048, "height": 1364}},
            )

    camera = _FramePixelContractCamera(
        MatchingSizeCamera(),
        runtime_config=load_runtime_config("dev_lab"),
        profile_name="unknown_profile",
    )

    try:
        camera.read_frame()
    except FramePixelContractError as exc:
        assert "unknown_profile" in str(exc)
        assert "does not define a camera acquisition profile" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected unknown camera profile contract failure")


def test_live_run_measurement_camera_accepts_pixels_that_match_offline_material() -> None:
    class MatchingSizeCamera:
        def read_frame(self) -> FramePacket:
            return FramePacket(
                timestamp_ms=2_000,
                source="matching_size_measurement",
                image=np.zeros((1364, 2048), dtype=np.uint8),
                frame_id=1,
                meta={"device_roi": {"x": 512, "y": 342, "width": 2048, "height": 1364}},
            )

    camera = _FramePixelContractCamera(
        MatchingSizeCamera(),
        runtime_config=load_runtime_config("dev_lab"),
        profile_name="measurement",
    )

    frame = camera.read_frame()

    assert frame.meta["pixel_contract_width"] == 2048
    assert frame.meta["pixel_contract_height"] == 1364
    assert frame.meta["pixel_contract_device_roi"] == {"x": 512, "y": 342, "width": 2048, "height": 1364}


def test_live_run_measurement_camera_accepts_effective_applied_measurement_roi() -> None:
    effective_roi = DeviceRoiConfig(x=832, y=560, width=360, height=184)
    runtime_config = load_runtime_config("dev_lab")
    effective_profile = replace(runtime_config.live.camera.measurement, device_roi=effective_roi)
    effective_config = _runtime_config_with_measurement_profile(runtime_config, effective_profile)

    class EffectiveRoiCamera:
        def read_frame(self) -> FramePacket:
            return FramePacket(
                timestamp_ms=2_000,
                source="effective_roi_measurement",
                image=np.zeros((184, 360), dtype=np.uint8),
                frame_id=1,
                meta={"device_roi": {"x": 832, "y": 560, "width": 360, "height": 184}},
            )

    camera = _FramePixelContractCamera(
        EffectiveRoiCamera(),
        runtime_config=effective_config,
        profile_name="measurement",
    )

    frame = camera.read_frame()

    assert frame.meta["pixel_contract_width"] == 360
    assert frame.meta["pixel_contract_height"] == 184
    assert frame.meta["pixel_contract_device_roi"] == {"x": 832, "y": 560, "width": 360, "height": 184}


def test_live_run_measurement_camera_rejects_stale_baseline_roi_after_effective_roi_applied() -> None:
    effective_roi = DeviceRoiConfig(x=832, y=560, width=360, height=184)
    runtime_config = load_runtime_config("dev_lab")
    effective_profile = replace(runtime_config.live.camera.measurement, device_roi=effective_roi)
    effective_config = _runtime_config_with_measurement_profile(runtime_config, effective_profile)

    class StaleBaselineRoiCamera:
        def read_frame(self) -> FramePacket:
            return FramePacket(
                timestamp_ms=2_000,
                source="stale_baseline_roi_measurement",
                image=np.zeros((184, 360), dtype=np.uint8),
                frame_id=1,
                meta={"device_roi": {"x": 512, "y": 342, "width": 2048, "height": 1364}},
            )

    camera = _FramePixelContractCamera(
        StaleBaselineRoiCamera(),
        runtime_config=effective_config,
        profile_name="measurement",
    )

    try:
        camera.read_frame()
    except FramePixelContractError as exc:
        assert "live_run_measurement_frame" in str(exc)
        assert "expected_roi=x=832,y=560,width=360,height=184" in str(exc)
        assert "actual_roi=x=512,y=342,width=2048,height=1364" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected stale baseline ROI contract failure")


def test_should_cache_tracking_preview_honors_minimum_interval() -> None:
    active_run = _ActiveLiveRun(
        run_id="run-001",
        stop_event=threading.Event(),
        tracking_preview_min_interval_ms=250,
        last_tracking_preview_cached_at_ms=1_000,
    )

    assert _should_cache_tracking_preview(active_run, 1_100) is False
    assert _should_cache_tracking_preview(active_run, 1_250) is True


def test_tracking_preview_min_interval_follows_preview_poll_for_live_display() -> None:
    run_config = RunRuntimeConfig(preview_poll_ms=50)

    assert _tracking_preview_min_interval_ms(run_config) == 50


def test_runtime_config_with_operator_output_power_uses_confirmed_run_power() -> None:
    runtime_config = RuntimeConfig(
        profile="dev_lab",
        platform="mac",
        mode="lab",
        webapp=WebAppConfig(host="127.0.0.1", port=8000),
        adapters={"camera": "hik_gige_mvs", "temp": "lu92xx_modbus_rtu", "plc": "mock"},
    )
    runtime_config.live.temp.control.startup_power_percent = 100.0
    record = RunDraftRecord(
        run_id="run-001",
        profile="dev_lab",
        preset="balloon",
        temperature_settings=TemperatureSettingsBundle(
            target_temperature_celsius=37.5,
            output_power_percent=68.0,
        ),
    )

    updated = _runtime_config_with_operator_output_power(runtime_config, record)

    assert updated.live.temp.control.startup_power_percent == 68.0
    assert runtime_config.live.temp.control.startup_power_percent == 100.0
