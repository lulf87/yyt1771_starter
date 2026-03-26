"""Shared device-construction helpers for application services."""

from __future__ import annotations

from typing import Any

from src.application.runtime_config import RuntimeConfig
from src.camera import HikGigeMvsCamera, HikRtspCamera, MockCamera, build_hik_rtsp_url
from src.core.config_models import CameraAcquisitionProfileConfig
from src.core.models import MeasurementDefinition
from src.temp import LU92XXModbusRtuController, MockTempController
from src.workflow.live_run import LockedDefinitionMetricSource, MockLiveMetricSource


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
        return MockLiveMetricSource(
            definition=definition,
            target_temperature_celsius=target_temperature_celsius,
        )
    return LockedDefinitionMetricSource(definition=definition)


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
