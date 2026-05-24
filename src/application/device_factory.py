"""Shared device-construction helpers for application services."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import math
from pathlib import Path
from typing import Any

from src.application.runtime_config import RuntimeConfig
from src.camera import HikGigeMvsCamera, HikRtspCamera, MockCamera, OfflineCaptureCamera, build_hik_rtsp_url
from src.core.config_models import CameraAcquisitionProfileConfig, DeviceRoiConfig
from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion, _metric_box_within_region
from src.curve.mock_afas_curve_playback import resolve_mock_afas_curve_playback
from src.temp import LU92XXModbusRtuController, MockTempController, OfflineCaptureTempController, WorkbookPlaybackTempController
from src.workflow.live_run import (
    DIRECTIONAL_WORKING_MAX_HEIGHT,
    DIRECTIONAL_WORKING_MAX_WIDTH,
    LockedDefinitionMetricSource,
    MockLiveMetricSource,
    PriorTrackingMetricSource,
    WorkbookPlaybackMetricSource,
)

_MEASUREMENT_ROI_MIN_PADDING_PX = 32
_MEASUREMENT_ROI_MAX_PADDING_PX = 160


@dataclass(slots=True)
class MeasurementCapturePlan:
    measurement_profile: CameraAcquisitionProfileConfig
    metric_definition: MeasurementDefinition
    setup_preview_roi: DeviceRoiConfig = field(default_factory=DeviceRoiConfig)
    measurement_base_roi: DeviceRoiConfig = field(default_factory=DeviceRoiConfig)


def open_camera(runtime_config: RuntimeConfig, *, profile_name: str = "setup_preview") -> object:
    backend = str(runtime_config.adapters.get("camera", "") or "")
    profile = camera_profile_for_mode(runtime_config.live.camera, profile_name)
    if backend == "mock":
        return MockCamera(
            profile_name=profile_name,
            exposure_us=profile.exposure_us,
            device_roi=profile.device_roi,
            decimation=profile.decimation,
            binning=profile.binning,
        )
    if backend == "offline_capture":
        return OfflineCaptureCamera(
            capture_dir=_resolve_offline_capture_dir(runtime_config),
            profile_name=profile_name,
            device_roi=profile.device_roi,
        )
    if backend == "hik_gige_mvs":
        return _build_hik_gige_camera(runtime_config, profile_name=profile_name)
    if backend == "hik_rtsp_opencv":
        return _build_hik_rtsp_camera(runtime_config)
    raise ValueError(f"Camera backend does not support preview: {backend or 'missing'}")


def build_temp_controller(runtime_config: RuntimeConfig) -> object:
    backend = str(runtime_config.live.temp.backend or runtime_config.adapters.get("temp", "") or "")
    if backend == "mock":
        playback = _resolve_mock_afas_curve_playback(runtime_config)
        if playback is not None:
            return WorkbookPlaybackTempController(playback)
        return MockTempController(
            ramp_step_celsius=runtime_config.live.temp.control.mock_ramp_step_celsius,
        )
    if backend == "lu92xx_modbus_rtu":
        return LU92XXModbusRtuController(runtime_config.live.temp)
    if backend == "offline_capture":
        return OfflineCaptureTempController(capture_dir=_resolve_offline_capture_dir(runtime_config))
    raise ValueError(f"Temperature backend does not support Phase 3 live runs yet: {backend or 'missing'}")


def build_metric_source(
    *,
    runtime_config: RuntimeConfig,
    definition: MeasurementDefinition,
    target_temperature_celsius: float,
) -> object:
    camera_backend = str(runtime_config.adapters.get("camera", "") or "")
    if camera_backend == "mock":
        playback = _resolve_mock_afas_curve_playback(runtime_config)
        if playback is not None:
            return WorkbookPlaybackMetricSource(definition=definition, playback=playback)
        return MockLiveMetricSource(
            definition=definition,
            target_temperature_celsius=target_temperature_celsius,
        )
    if runtime_config.live.run.debug_locked_points_tracking:
        return LockedDefinitionMetricSource(
            definition=definition,
            debug_locked_points=True,
            working_max_width=DIRECTIONAL_WORKING_MAX_WIDTH if definition.direction_angle_deg is not None else None,
            working_max_height=DIRECTIONAL_WORKING_MAX_HEIGHT if definition.direction_angle_deg is not None else None,
        )
    return PriorTrackingMetricSource(definition=definition)


def build_measurement_capture_plan(
    *,
    runtime_config: RuntimeConfig,
    definition: MeasurementDefinition,
) -> MeasurementCapturePlan:
    measurement_profile = camera_profile_for_mode(runtime_config.live.camera, "measurement")
    camera_backend = str(runtime_config.adapters.get("camera", "") or "")
    setup_preview_roi = _setup_preview_sensor_roi(runtime_config)
    measurement_base_roi = _measurement_base_device_roi(runtime_config)
    if camera_backend == "mock":
        return MeasurementCapturePlan(
            measurement_profile=measurement_profile,
            metric_definition=definition,
            setup_preview_roi=setup_preview_roi,
            measurement_base_roi=measurement_base_roi,
        )

    if measurement_base_roi.width < 1 or measurement_base_roi.height < 1:
        if measurement_profile.device_roi.width < 1 or measurement_profile.device_roi.height < 1:
            return MeasurementCapturePlan(
                measurement_profile=measurement_profile,
                metric_definition=definition,
                setup_preview_roi=setup_preview_roi,
                measurement_base_roi=measurement_base_roi,
            )
        effective_definition = _translate_definition_for_measurement_roi(
            definition,
            setup_preview_roi=setup_preview_roi,
            effective_acquisition_roi=measurement_profile.device_roi,
        )
        return MeasurementCapturePlan(
            measurement_profile=measurement_profile,
            metric_definition=effective_definition,
            setup_preview_roi=setup_preview_roi,
            measurement_base_roi=measurement_base_roi,
        )

    analysis_roi_in_sensor = type(definition.analysis_roi)(
        x=int(definition.analysis_roi.x + setup_preview_roi.x),
        y=int(definition.analysis_roi.y + setup_preview_roi.y),
        width=int(definition.analysis_roi.width),
        height=int(definition.analysis_roi.height),
    )
    metric_box_region_in_sensor = _metric_box_bounding_region(
        type(definition.analysis_roi)(
            x=int(definition.metric_box.center_x - definition.metric_box.width / 2 + setup_preview_roi.x),
            y=int(definition.metric_box.center_y - definition.metric_box.height / 2 + setup_preview_roi.y),
            width=int(definition.metric_box.width),
            height=int(definition.metric_box.height),
        ),
        angle_deg=float(definition.metric_box.angle_deg),
    )
    measurement_focus_region = _region_union(
        analysis_roi_in_sensor,
        metric_box_region_in_sensor,
    )
    if _region_contains_region(measurement_base_roi, measurement_focus_region):
        focus_region_in_measurement_base = type(definition.analysis_roi)(
            x=int(measurement_focus_region.x - measurement_base_roi.x),
            y=int(measurement_focus_region.y - measurement_base_roi.y),
            width=int(measurement_focus_region.width),
            height=int(measurement_focus_region.height),
        )
        local_capture_roi = _derive_measurement_local_capture_roi(
            focus_region_in_measurement_base,
            container_width=measurement_base_roi.width,
            container_height=measurement_base_roi.height,
        )
        effective_device_roi = DeviceRoiConfig(
            x=measurement_base_roi.x + local_capture_roi.x,
            y=measurement_base_roi.y + local_capture_roi.y,
            width=local_capture_roi.width,
            height=local_capture_roi.height,
        )
    else:
        unconstrained_capture_roi = _derive_unbounded_measurement_capture_roi(
            measurement_focus_region,
        )
        effective_device_roi = DeviceRoiConfig(
            x=unconstrained_capture_roi.x,
            y=unconstrained_capture_roi.y,
            width=unconstrained_capture_roi.width,
            height=unconstrained_capture_roi.height,
        )
    effective_profile = replace(measurement_profile, device_roi=effective_device_roi)
    shifted_definition = _translate_definition_for_measurement_roi(
        definition,
        setup_preview_roi=setup_preview_roi,
        effective_acquisition_roi=effective_device_roi,
    )
    return MeasurementCapturePlan(
        measurement_profile=effective_profile,
        metric_definition=shifted_definition,
        setup_preview_roi=setup_preview_roi,
        measurement_base_roi=measurement_base_roi,
    )


def apply_measurement_acquisition_roi(
    plan: MeasurementCapturePlan,
    *,
    definition: MeasurementDefinition,
    applied_device_roi: DeviceRoiConfig,
) -> MeasurementCapturePlan:
    effective_profile = replace(
        plan.measurement_profile,
        device_roi=DeviceRoiConfig(
            x=int(applied_device_roi.x),
            y=int(applied_device_roi.y),
            width=int(applied_device_roi.width),
            height=int(applied_device_roi.height),
        ),
    )
    shifted_definition = _translate_definition_for_measurement_roi(
        definition,
        setup_preview_roi=plan.setup_preview_roi,
        effective_acquisition_roi=effective_profile.device_roi,
    )
    return MeasurementCapturePlan(
        measurement_profile=effective_profile,
        metric_definition=shifted_definition,
        setup_preview_roi=plan.setup_preview_roi,
        measurement_base_roi=plan.measurement_base_roi,
    )


def camera_profile_for_mode(camera_config: Any, profile_name: str) -> CameraAcquisitionProfileConfig:
    if profile_name == "measurement":
        return camera_config.measurement
    return camera_config.setup_preview


def camera_target_frame_rate_hz(runtime_config: RuntimeConfig, *, profile_name: str) -> float | None:
    if profile_name == "measurement":
        target_hz = runtime_config.live.run.measurement_target_hz
    elif profile_name == "setup_preview":
        target_hz = runtime_config.live.run.preview_target_fps
    else:
        target_hz = None
    if target_hz is None:
        return None
    resolved = float(target_hz)
    return resolved if resolved > 0 else None


def _build_hik_gige_camera(runtime_config: RuntimeConfig, *, profile_name: str) -> HikGigeMvsCamera:
    live_camera = runtime_config.live.camera
    legacy_camera = runtime_config.camera
    profile = camera_profile_for_mode(live_camera, profile_name)
    model = str(legacy_camera.get("model", "") or "").strip()
    if not model and live_camera.allowed_models:
        model = live_camera.allowed_models[0]
    return HikGigeMvsCamera(
        model=model,
        transport=live_camera.transport or str(legacy_camera.get("transport", "") or ""),
        sdk_name=live_camera.sdk or str(legacy_camera.get("sdk", "hik_mvs") or "hik_mvs"),
        serial_number=live_camera.serial_number or str(legacy_camera.get("serial_number", "") or ""),
        ip=live_camera.ip or str(legacy_camera.get("ip", "") or ""),
        trigger_mode=profile.trigger_mode,
        pixel_format=profile.pixel_format,
        exposure_us=profile.exposure_us,
        gain_db=profile.gain_db,
        timeout_ms=profile.timeout_ms,
        device_roi=profile.device_roi,
        decimation=profile.decimation,
        binning=profile.binning,
        target_frame_rate_hz=camera_target_frame_rate_hz(runtime_config, profile_name=profile_name),
        profile_name=profile_name,
    )


def _build_hik_rtsp_camera(runtime_config: RuntimeConfig) -> HikRtspCamera:
    camera_config = runtime_config.camera
    rtsp_url = str(camera_config.get("rtsp_url", "") or "").strip()
    if not rtsp_url:
        host = str(camera_config.get("host", "") or "").strip()
        username = str(camera_config.get("username", "") or "").strip()
        password = str(camera_config.get("password", "") or "").strip()
        if host and username and password:
            rtsp_url = build_hik_rtsp_url(
                host=host,
                username=username,
                password=password,
                channel=int(camera_config.get("channel", 1) or 1),
                stream=int(camera_config.get("stream", 1) or 1),
                port=int(camera_config.get("port", 554) or 554),
            )
    if not rtsp_url:
        raise ValueError("RTSP preview requires camera.rtsp_url or camera.host/username/password")
    return HikRtspCamera(rtsp_url=rtsp_url)


def _resolve_mock_afas_curve_playback(runtime_config: RuntimeConfig):
    try:
        return resolve_mock_afas_curve_playback(
            runtime_config,
            channel_name=runtime_config.live.analysis.channel_name,
        )
    except FileNotFoundError as exc:
        configured_path = str(runtime_config.replay.get("mock_afas_curve_path", "") or "").strip()
        resolved_path = Path(configured_path)
        if configured_path and not resolved_path.is_absolute():
            resolved_path = Path(__file__).resolve().parents[2] / configured_path
        raise FileNotFoundError(f"Configured mock AFAS curve sample is missing: {resolved_path}") from exc


def _resolve_offline_capture_dir(runtime_config: RuntimeConfig) -> Path:
    offline_config = runtime_config.camera.get("offline_capture")
    if not isinstance(offline_config, dict):
        offline_config = {}
    capture_dir = str(offline_config.get("capture_dir", "") or "").strip()
    if not capture_dir:
        raise ValueError("offline_capture camera config requires camera.offline_capture.capture_dir")
    resolved_path = Path(capture_dir)
    if not resolved_path.is_absolute():
        resolved_path = Path(__file__).resolve().parents[2] / resolved_path
    return resolved_path


def _setup_preview_sensor_roi(runtime_config: RuntimeConfig) -> DeviceRoiConfig:
    camera_config = runtime_config.live.camera
    candidate = camera_config.setup_preview.device_roi
    if candidate.width > 0 and candidate.height > 0:
        return DeviceRoiConfig(
            x=int(candidate.x),
            y=int(candidate.y),
            width=int(candidate.width),
            height=int(candidate.height),
        )
    return DeviceRoiConfig()


def _measurement_base_device_roi(runtime_config: RuntimeConfig) -> DeviceRoiConfig:
    camera_config = runtime_config.live.camera
    for candidate in (
        camera_config.measurement.device_roi,
        camera_config.device_roi,
        camera_config.setup_preview.device_roi,
    ):
        if candidate.width > 0 and candidate.height > 0:
            return DeviceRoiConfig(
                x=int(candidate.x),
                y=int(candidate.y),
                width=int(candidate.width),
                height=int(candidate.height),
            )
    return DeviceRoiConfig()


def _derive_measurement_local_capture_roi(
    analysis_roi,
    *,
    container_width: int,
    container_height: int,
):
    span_width = max(1, int(analysis_roi.width))
    span_height = max(1, int(analysis_roi.height))
    padding_x = _measurement_padding_px(span_width)
    padding_y = _measurement_padding_px(span_height)

    desired_width = min(
        int(container_width),
        max(span_width, span_width + padding_x * 2),
    )
    desired_height = min(
        int(container_height),
        max(span_height, span_height + padding_y * 2),
    )

    center_x = float(analysis_roi.x) + float(span_width) / 2.0
    center_y = float(analysis_roi.y) + float(span_height) / 2.0
    x = int(round(center_x - float(desired_width) / 2.0))
    y = int(round(center_y - float(desired_height) / 2.0))
    x = max(0, min(int(container_width) - int(desired_width), x))
    y = max(0, min(int(container_height) - int(desired_height), y))
    return type(analysis_roi)(
        x=int(x),
        y=int(y),
        width=int(desired_width),
        height=int(desired_height),
    )


def _derive_unbounded_measurement_capture_roi(region):
    span_width = max(1, int(region.width))
    span_height = max(1, int(region.height))
    padding_x = _measurement_padding_px(span_width)
    padding_y = _measurement_padding_px(span_height)
    desired_width = max(span_width, span_width + padding_x * 2)
    desired_height = max(span_height, span_height + padding_y * 2)
    center_x = float(region.x) + float(span_width) / 2.0
    center_y = float(region.y) + float(span_height) / 2.0
    x = max(0, int(round(center_x - float(desired_width) / 2.0)))
    y = max(0, int(round(center_y - float(desired_height) / 2.0)))
    return type(region)(
        x=int(x),
        y=int(y),
        width=int(desired_width),
        height=int(desired_height),
    )


def _measurement_padding_px(span_px: int) -> int:
    proportional = int(round(float(span_px) * 0.25))
    return max(_MEASUREMENT_ROI_MIN_PADDING_PX, min(_MEASUREMENT_ROI_MAX_PADDING_PX, proportional))


def _region_union(first, second):
    min_x = min(int(first.x), int(second.x))
    min_y = min(int(first.y), int(second.y))
    max_x = max(int(first.x) + int(first.width), int(second.x) + int(second.width))
    max_y = max(int(first.y) + int(first.height), int(second.y) + int(second.height))
    return type(first)(
        x=int(min_x),
        y=int(min_y),
        width=max(1, int(max_x - min_x)),
        height=max(1, int(max_y - min_y)),
    )


def _region_contains_region(container, region) -> bool:
    return (
        int(container.x) <= int(region.x)
        and int(container.y) <= int(region.y)
        and int(region.x) + int(region.width) <= int(container.x) + int(container.width)
        and int(region.y) + int(region.height) <= int(container.y) + int(container.height)
    )


def _metric_box_bounding_region(region, *, angle_deg: float):
    center_x = float(region.x) + float(region.width) / 2.0
    center_y = float(region.y) + float(region.height) / 2.0
    half_width = float(region.width) / 2.0
    half_height = float(region.height) / 2.0
    radians = math.radians(float(angle_deg))
    cos_theta = math.cos(radians)
    sin_theta = math.sin(radians)
    corners = []
    for local_x, local_y in (
        (-half_width, -half_height),
        (half_width, -half_height),
        (half_width, half_height),
        (-half_width, half_height),
    ):
        corners.append(
            (
                center_x + local_x * cos_theta - local_y * sin_theta,
                center_y + local_x * sin_theta + local_y * cos_theta,
            )
        )
    min_x = int(math.floor(min(x for x, _ in corners)))
    max_x = int(math.ceil(max(x for x, _ in corners)))
    min_y = int(math.floor(min(y for _, y in corners)))
    max_y = int(math.ceil(max(y for _, y in corners)))
    return type(region)(
        x=min_x,
        y=min_y,
        width=max(1, max_x - min_x),
        height=max(1, max_y - min_y),
    )


def _translate_measurement_definition(definition: MeasurementDefinition, *, dx: int, dy: int) -> MeasurementDefinition:
    return MeasurementDefinition(
        analysis_roi=type(definition.analysis_roi)(
            x=int(definition.analysis_roi.x + dx),
            y=int(definition.analysis_roi.y + dy),
            width=int(definition.analysis_roi.width),
            height=int(definition.analysis_roi.height),
        ),
        metric_box=type(definition.metric_box)(
            center_x=int(definition.metric_box.center_x + dx),
            center_y=int(definition.metric_box.center_y + dy),
            width=int(definition.metric_box.width),
            height=int(definition.metric_box.height),
            angle_deg=float(definition.metric_box.angle_deg),
        ),
        point_a_px=type(definition.point_a_px)(
            x=int(definition.point_a_px.x + dx),
            y=int(definition.point_a_px.y + dy),
        ),
        point_b_px=type(definition.point_b_px)(
            x=int(definition.point_b_px.x + dx),
            y=int(definition.point_b_px.y + dy),
        ),
        foreground_polarity=definition.foreground_polarity,
        threshold_mode=definition.threshold_mode,
        ignore_internal_texture=definition.ignore_internal_texture,
        min_target_area_px=int(definition.min_target_area_px),
        sensitivity=float(definition.sensitivity),
        direction_angle_deg=definition.direction_angle_deg,
        direction_projection_mode=definition.direction_projection_mode,
        observation_axis=definition.observation_axis,
    )


def _translate_definition_for_measurement_roi(
    definition: MeasurementDefinition,
    *,
    setup_preview_roi: DeviceRoiConfig,
    effective_acquisition_roi: DeviceRoiConfig,
) -> MeasurementDefinition:
    dx = int(setup_preview_roi.x) - int(effective_acquisition_roi.x)
    dy = int(setup_preview_roi.y) - int(effective_acquisition_roi.y)
    translated = _translate_measurement_definition(definition, dx=dx, dy=dy)
    return _normalize_definition_to_local_frame(
        translated,
        frame_width=int(effective_acquisition_roi.width),
        frame_height=int(effective_acquisition_roi.height),
    )


def _normalize_definition_to_local_frame(
    definition: MeasurementDefinition,
    *,
    frame_width: int,
    frame_height: int,
) -> MeasurementDefinition:
    local_frame = RectRegion(x=0, y=0, width=max(1, int(frame_width)), height=max(1, int(frame_height)))
    translated = definition
    if (
        translated.analysis_roi.x >= 0
        and translated.analysis_roi.y >= 0
        and translated.analysis_roi.x + translated.analysis_roi.width <= local_frame.width
        and translated.analysis_roi.y + translated.analysis_roi.height <= local_frame.height
        and _metric_box_within_region(local_frame, translated.metric_box)
        and 0 <= translated.point_a_px.x < local_frame.width
        and 0 <= translated.point_a_px.y < local_frame.height
        and 0 <= translated.point_b_px.x < local_frame.width
        and 0 <= translated.point_b_px.y < local_frame.height
    ):
        return translated

    normalized_box = _fit_metric_box_within_region(translated.metric_box, local_frame)
    normalized_point_a = _clamp_point_into_metric_box_region(translated.point_a_px, normalized_box, local_frame)
    normalized_point_b = _clamp_point_into_metric_box_region(translated.point_b_px, normalized_box, local_frame)
    if (normalized_point_a.x, normalized_point_a.y) == (normalized_point_b.x, normalized_point_b.y):
        normalized_point_a, normalized_point_b = _default_edge_points(normalized_box, local_frame)
    return MeasurementDefinition(
        analysis_roi=local_frame,
        metric_box=normalized_box,
        point_a_px=normalized_point_a,
        point_b_px=normalized_point_b,
        foreground_polarity=translated.foreground_polarity,
        threshold_mode=translated.threshold_mode,
        ignore_internal_texture=translated.ignore_internal_texture,
        min_target_area_px=translated.min_target_area_px,
        sensitivity=translated.sensitivity,
        direction_angle_deg=translated.direction_angle_deg,
        direction_projection_mode=translated.direction_projection_mode,
        observation_axis=translated.observation_axis,
    )


def _fit_metric_box_within_region(box: MetricBox, region: RectRegion) -> MetricBox:
    width = max(1.0, min(float(box.width), float(region.width)))
    height = max(1.0, min(float(box.height), float(region.height)))
    angle_deg = float(box.angle_deg)
    center_x = float(box.center_x)
    center_y = float(box.center_y)
    candidate = MetricBox(center_x=int(round(center_x)), center_y=int(round(center_y)), width=int(round(width)), height=int(round(height)), angle_deg=angle_deg)
    for _ in range(12):
        half_width = width / 2.0
        half_height = height / 2.0
        angle_rad = math.radians(angle_deg)
        span_x = abs(half_width * math.cos(angle_rad)) + abs(half_height * math.sin(angle_rad))
        span_y = abs(half_width * math.sin(angle_rad)) + abs(half_height * math.cos(angle_rad))
        if span_x > region.width / 2.0 or span_y > region.height / 2.0:
            scale = min(
                float(region.width) / max(2.0 * span_x, 1.0),
                float(region.height) / max(2.0 * span_y, 1.0),
                1.0,
            )
            width = max(1.0, math.floor(width * scale))
            height = max(1.0, math.floor(height * scale))
            candidate = MetricBox(
                center_x=int(round(center_x)),
                center_y=int(round(center_y)),
                width=max(1, int(round(width))),
                height=max(1, int(round(height))),
                angle_deg=angle_deg,
            )
            continue
        min_center_x = region.x + span_x
        max_center_x = region.x + region.width - span_x
        min_center_y = region.y + span_y
        max_center_y = region.y + region.height - span_y
        center_x = min(max(center_x, min_center_x), max_center_x)
        center_y = min(max(center_y, min_center_y), max_center_y)
        candidate = MetricBox(
            center_x=int(round(center_x)),
            center_y=int(round(center_y)),
            width=max(1, int(round(width))),
            height=max(1, int(round(height))),
            angle_deg=angle_deg,
        )
        if _metric_box_within_region(region, candidate):
            return candidate
        width = max(1.0, width - 1.0)
        height = max(1.0, height - 1.0)
    return candidate


def _clamp_point_into_metric_box_region(point: PixelPoint, box: MetricBox, region: RectRegion) -> PixelPoint:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = float(point.x) - float(box.center_x)
    translated_y = float(point.y) - float(box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    local_x = min(max(local_x, -float(box.width) / 2.0), float(box.width) / 2.0)
    local_y = min(max(local_y, -float(box.height) / 2.0), float(box.height) / 2.0)
    world_x = float(box.center_x) + local_x * cos_theta - local_y * sin_theta
    world_y = float(box.center_y) + local_x * sin_theta + local_y * cos_theta
    clamped_x = max(region.x, min(region.x + region.width - 1, int(round(world_x))))
    clamped_y = max(region.y, min(region.y + region.height - 1, int(round(world_y))))
    return PixelPoint(x=clamped_x, y=clamped_y)


def _default_edge_points(box: MetricBox, region: RectRegion) -> tuple[PixelPoint, PixelPoint]:
    point_a = _clamp_point_into_metric_box_region(
        PixelPoint(x=int(round(box.center_x - box.width / 2.0)), y=int(round(box.center_y))),
        box,
        region,
    )
    point_b = _clamp_point_into_metric_box_region(
        PixelPoint(x=int(round(box.center_x + box.width / 2.0)), y=int(round(box.center_y))),
        box,
        region,
    )
    return point_a, point_b
