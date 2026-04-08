"""Shared device-construction helpers for application services."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from src.application.runtime_config import RuntimeConfig
from src.camera import HikGigeMvsCamera, HikRtspCamera, MockCamera, build_hik_rtsp_url
from src.core.config_models import CameraAcquisitionProfileConfig, DeviceRoiConfig
from src.core.models import MeasurementDefinition
from src.curve.mock_afas_curve_playback import resolve_mock_afas_curve_playback
from src.temp import LU92XXModbusRtuController, MockTempController, WorkbookPlaybackTempController
from src.workflow.live_run import (
    LockedDefinitionMetricSource,
    MockLiveMetricSource,
    PriorTrackingMetricSource,
    WorkbookPlaybackMetricSource,
)

_MEASUREMENT_ROI_TARGET_MAX_WIDTH = 512
_MEASUREMENT_ROI_TARGET_MAX_HEIGHT = 512
_MEASUREMENT_ROI_MIN_PADDING_PX = 32
_MEASUREMENT_ROI_MAX_PADDING_PX = 160


@dataclass(slots=True)
class MeasurementCapturePlan:
    measurement_profile: CameraAcquisitionProfileConfig
    metric_definition: MeasurementDefinition


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
    return LockedDefinitionMetricSource(
        definition=definition,
        debug_locked_points=runtime_config.live.run.debug_locked_points_tracking,
    ) if runtime_config.live.run.debug_locked_points_tracking else PriorTrackingMetricSource(definition=definition)


def build_measurement_capture_plan(
    *,
    runtime_config: RuntimeConfig,
    definition: MeasurementDefinition,
) -> MeasurementCapturePlan:
    measurement_profile = camera_profile_for_mode(runtime_config.live.camera, "measurement")
    camera_backend = str(runtime_config.adapters.get("camera", "") or "")
    if camera_backend == "mock":
        return MeasurementCapturePlan(
            measurement_profile=measurement_profile,
            metric_definition=definition,
        )

    reference_roi = _reference_preview_device_roi(runtime_config)
    if reference_roi.width < 1 or reference_roi.height < 1:
        return MeasurementCapturePlan(
            measurement_profile=measurement_profile,
            metric_definition=definition,
        )

    local_capture_roi = _derive_measurement_local_capture_roi(
        definition.analysis_roi,
        container_width=reference_roi.width,
        container_height=reference_roi.height,
    )
    if (
        local_capture_roi.x == 0
        and local_capture_roi.y == 0
        and local_capture_roi.width == reference_roi.width
        and local_capture_roi.height == reference_roi.height
    ):
        return MeasurementCapturePlan(
            measurement_profile=measurement_profile,
            metric_definition=definition,
        )

    effective_profile = replace(
        measurement_profile,
        device_roi=DeviceRoiConfig(
            x=reference_roi.x + local_capture_roi.x,
            y=reference_roi.y + local_capture_roi.y,
            width=local_capture_roi.width,
            height=local_capture_roi.height,
        ),
    )
    shifted_definition = _translate_measurement_definition(
        definition,
        dx=-local_capture_roi.x,
        dy=-local_capture_roi.y,
    )
    return MeasurementCapturePlan(
        measurement_profile=effective_profile,
        metric_definition=shifted_definition,
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


def _reference_preview_device_roi(runtime_config: RuntimeConfig) -> DeviceRoiConfig:
    camera_config = runtime_config.live.camera
    for candidate in (
        camera_config.setup_preview.device_roi,
        camera_config.measurement.device_roi,
        camera_config.device_roi,
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
        max(span_width, min(_MEASUREMENT_ROI_TARGET_MAX_WIDTH, span_width + padding_x * 2)),
    )
    desired_height = min(
        int(container_height),
        max(span_height, min(_MEASUREMENT_ROI_TARGET_MAX_HEIGHT, span_height + padding_y * 2)),
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


def _measurement_padding_px(span_px: int) -> int:
    proportional = int(round(float(span_px) * 0.25))
    return max(_MEASUREMENT_ROI_MIN_PADDING_PX, min(_MEASUREMENT_ROI_MAX_PADDING_PX, proportional))


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
        observation_axis=definition.observation_axis,
    )
