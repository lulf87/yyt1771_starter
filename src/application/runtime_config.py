"""Shared runtime profile loading for application shells."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import sys
from typing import Any

import yaml

from src.core.config_models import (
    AnalysisRuntimeConfig,
    CameraAcquisitionProfileConfig,
    CameraRuntimeConfig,
    DeviceRoiConfig,
    LiveRunConfig,
    RunRuntimeConfig,
    SerialPortConfig,
    TempControlConfig,
    TempRegisterConfig,
    TempRegisterMapConfig,
    TempRuntimeConfig,
    VisionRuntimeConfig,
)

USER_CONFIG_DIR_ENV = "YYT1771_USER_CONFIG_DIR"
PROJECT_ROOT_ENV = "YYT1771_PROJECT_ROOT"
USER_APP_DIR_NAME = "YYT1771"


@dataclass(slots=True)
class WebAppConfig:
    host: str
    port: int


@dataclass(slots=True)
class RuntimeConfig:
    profile: str
    platform: str
    mode: str
    webapp: WebAppConfig
    adapters: dict[str, str]
    camera: dict[str, Any] = field(default_factory=dict)
    storage: dict[str, Any] = field(default_factory=dict)
    replay: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)
    live: LiveRunConfig = field(default_factory=LiveRunConfig)

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "platform": self.platform,
            "mode": self.mode,
            "webapp": {
                "host": self.webapp.host,
                "port": self.webapp.port,
            },
            "adapters": dict(self.adapters),
        }


def load_runtime_config(profile: str) -> RuntimeConfig:
    config_root = _project_root() / "configs"
    config_path = config_root / f"{profile}.yaml"
    raw_config = _load_config_mapping(config_path)
    for local_override_path in _profile_override_paths(profile, config_root=config_root):
        if not local_override_path.exists():
            continue
        local_override = _load_config_mapping(local_override_path)
        raw_config = _deep_merge_mapping(raw_config, local_override)

    webapp = raw_config.get("webapp")
    adapters = raw_config.get("adapters")
    if not isinstance(webapp, dict) or not isinstance(adapters, dict):
        raise ValueError(f"Profile config missing required sections: {config_path}")

    return RuntimeConfig(
        profile=str(raw_config.get("profile", profile)),
        platform=str(raw_config["platform"]),
        mode=str(raw_config["mode"]),
        webapp=WebAppConfig(
            host=str(webapp["host"]),
            port=int(webapp["port"]),
        ),
        adapters={str(name): str(value) for name, value in adapters.items()},
        camera=_normalize_mapping(raw_config.get("camera")),
        storage=_normalize_mapping(raw_config.get("storage")),
        replay=_normalize_mapping(raw_config.get("replay")),
        logging=_normalize_mapping(raw_config.get("logging")),
        live=_load_live_run_config(raw_config),
    )


def _project_root() -> Path:
    configured_root = os.environ.get(PROJECT_ROOT_ENV, "").strip()
    if configured_root:
        return Path(configured_root).expanduser()
    if getattr(sys, "frozen", False):
        bundle_root = str(getattr(sys, "_MEIPASS", "") or "").strip()
        if bundle_root:
            return Path(bundle_root)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _profile_override_paths(profile: str, *, config_root: Path) -> list[Path]:
    paths = [config_root / f"{profile}.local.yaml"]
    user_override = user_local_profile_override_path(profile)
    if user_override is not None:
        paths.append(user_override)
    return paths


def user_local_config_dir() -> Path | None:
    configured_dir = os.environ.get(USER_CONFIG_DIR_ENV, "").strip()
    if configured_dir:
        return Path(configured_dir).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_app_data:
        return None
    return Path(local_app_data).expanduser() / USER_APP_DIR_NAME / "configs"


def user_local_profile_override_path(profile: str) -> Path | None:
    config_dir = user_local_config_dir()
    if config_dir is None:
        return None
    return config_dir / f"{profile}.local.yaml"


def write_user_local_profile_override(profile: str, override: dict[str, Any]) -> Path | None:
    override_path = user_local_profile_override_path(profile)
    if override_path is None:
        return None
    current = _load_config_mapping(override_path) if override_path.exists() else {}
    merged = _deep_merge_mapping(current, override)
    override_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = override_path.with_suffix(override_path.suffix + ".tmp")
    temporary_path.write_text(
        yaml.safe_dump(merged, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    temporary_path.replace(override_path)
    return override_path


def _load_config_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Profile config not found: {path}")

    raw_config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw_config, dict):
        raise ValueError(f"Invalid profile config format: {path}")
    return raw_config


def _deep_merge_mapping(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, override_value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            merged[key] = _deep_merge_mapping(base_value, override_value)
        else:
            merged[key] = override_value
    return merged


def _normalize_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(name): item for name, item in value.items()}


def _load_live_run_config(raw_config: dict[str, Any]) -> LiveRunConfig:
    camera = _normalize_mapping(raw_config.get("camera"))
    temp = _normalize_mapping(raw_config.get("temp"))
    vision = _normalize_mapping(raw_config.get("vision"))
    analysis = _normalize_mapping(raw_config.get("analysis"))
    run = _normalize_mapping(raw_config.get("run"))
    serial = _normalize_mapping(temp.get("serial"))
    register_map = _normalize_mapping(temp.get("register_map"))
    process_value = _normalize_mapping(register_map.get("process_value"))
    target_or_stop_value = _normalize_mapping(register_map.get("target_or_stop_value"))
    output_power = _normalize_mapping(register_map.get("output_power"))
    control = _normalize_mapping(temp.get("control"))
    device_roi = _normalize_mapping(camera.get("device_roi"))
    setup_preview = _normalize_mapping(camera.get("setup_preview"))
    measurement = _normalize_mapping(camera.get("measurement"))
    base_trigger_mode = str(camera.get("trigger_mode", "free_run") or "free_run")
    base_pixel_format = str(camera.get("pixel_format", "mono8") or "mono8")
    base_exposure_us = int(camera.get("exposure_us", 10_000) or 10_000)
    base_gain_db = float(camera.get("gain_db", 0.0) or 0.0)
    base_timeout_ms = int(camera.get("timeout_ms", 1_000) or 1_000)
    base_device_roi = DeviceRoiConfig(
        x=int(device_roi.get("x", 0) or 0),
        y=int(device_roi.get("y", 0) or 0),
        width=int(device_roi.get("width", 0) or 0),
        height=int(device_roi.get("height", 0) or 0),
    )

    return LiveRunConfig(
        camera=CameraRuntimeConfig(
            transport=str(camera.get("transport", "") or ""),
            sdk=str(camera.get("sdk", "") or ""),
            probe_mode=str(camera.get("probe_mode", "") or ""),
            allowed_models=_normalize_string_list(camera.get("allowed_models")),
            serial_number=str(camera.get("serial_number", "") or ""),
            ip=str(camera.get("ip", "") or ""),
            trigger_mode=base_trigger_mode,
            pixel_format=base_pixel_format,
            exposure_us=base_exposure_us,
            gain_db=base_gain_db,
            timeout_ms=base_timeout_ms,
            device_roi=base_device_roi,
            setup_preview=_load_camera_acquisition_profile(
                setup_preview,
                default_trigger_mode=base_trigger_mode,
                default_pixel_format=base_pixel_format,
                default_exposure_us=base_exposure_us,
                default_gain_db=base_gain_db,
                default_timeout_ms=base_timeout_ms,
                default_device_roi=DeviceRoiConfig(),
            ),
            measurement=_load_camera_acquisition_profile(
                measurement,
                default_trigger_mode=base_trigger_mode,
                default_pixel_format=base_pixel_format,
                default_exposure_us=base_exposure_us,
                default_gain_db=base_gain_db,
                default_timeout_ms=base_timeout_ms,
                default_device_roi=base_device_roi,
            ),
        ),
        temp=TempRuntimeConfig(
            backend=str(temp.get("backend", "") or ""),
            protocol=str(temp.get("protocol", "modbus_rtu") or "modbus_rtu"),
            slave_address=int(temp.get("slave_address", 1) or 1),
            serial=SerialPortConfig(
                port=str(serial.get("port", "") or ""),
                baudrate=int(serial.get("baudrate", 19_200) or 19_200),
                bytesize=int(serial.get("bytesize", 8) or 8),
                parity=str(serial.get("parity", "N") or "N"),
                stopbits=int(serial.get("stopbits", 1) or 1),
                timeout_ms=int(serial.get("timeout_ms", 500) or 500),
            ),
            register_map=TempRegisterMapConfig(
                process_value=_load_temp_register_config(
                    process_value,
                    function_code=3,
                    start_address=264,
                    register_count=1,
                    signed=True,
                    decode_scale=0.1,
                    encode_scale=1.0,
                ),
                target_or_stop_value=_load_temp_register_config(
                    target_or_stop_value,
                    function_code=6,
                    start_address=0,
                    register_count=1,
                    signed=True,
                    decode_scale=1.0,
                    encode_scale=10.0,
                ),
                output_power=_load_temp_register_config(
                    output_power,
                    function_code=6,
                    start_address=4,
                    register_count=1,
                    signed=False,
                    decode_scale=1.0,
                    encode_scale=256.0,
                ),
            ),
            control=TempControlConfig(
                start_output_mode=str(control.get("start_output_mode", "power_nonzero") or "power_nonzero"),
                startup_power_percent=float(control.get("startup_power_percent", 100.0) or 100.0),
                completion_mode=str(control.get("completion_mode", "target_reached") or "target_reached"),
                mock_ramp_step_celsius=float(control.get("mock_ramp_step_celsius", 10.0) or 10.0),
            ),
        ),
        vision=VisionRuntimeConfig(
            foreground_polarity=str(vision.get("foreground_polarity", "dark_on_light") or "dark_on_light"),
            threshold_mode=str(vision.get("threshold_mode", "adaptive") or "adaptive"),
            edge_threshold=float(vision.get("edge_threshold", 10.0) or 10.0),
            ignore_internal_texture=bool(vision.get("ignore_internal_texture", False)),
            min_target_area_px=int(vision.get("min_target_area_px", 200) or 200),
            quality_threshold=float(vision.get("quality_threshold", 0.75) or 0.75),
        ),
        analysis=AnalysisRuntimeConfig(
            engine=str(analysis.get("engine", "afas") or "afas"),
            channel_name=str(analysis.get("channel_name", "Space1") or "Space1"),
            as_fit_point_count=int(analysis.get("as_fit_point_count", 5) or 5),
            af_fit_point_count=int(analysis.get("af_fit_point_count", 5) or 5),
        ),
        run=RunRuntimeConfig(
            preview_poll_ms=_int_with_default(run.get("preview_poll_ms"), 500),
            telemetry_poll_ms=_int_with_default(run.get("telemetry_poll_ms"), 500),
            capture_interval_ms=_int_with_default(run.get("capture_interval_ms"), 200),
            manual_stop_max_samples=_int_with_default(run.get("manual_stop_max_samples"), 10_000),
            preview_target_fps=_float_with_default(
                run.get("preview_target_fps"),
                8.0,
            ),
            preview_display_max_width=_int_with_default(
                run.get("preview_display_max_width"),
                640,
            ),
            preview_display_max_height=_int_with_default(
                run.get("preview_display_max_height"),
                480,
            ),
            measurement_target_hz=_float_with_default(
                run.get("measurement_target_hz"),
                _hz_from_interval_ms(_int_with_default(run.get("capture_interval_ms"), 200)),
            ),
            artifact_capture_hz=_float_with_default(
                run.get("artifact_capture_hz"),
                _float_with_default(
                    run.get("measurement_target_hz"),
                    _hz_from_interval_ms(_int_with_default(run.get("capture_interval_ms"), 200)),
                ),
            ),
            stop_on_invalid_tracking=bool(run.get("stop_on_invalid_tracking", True)),
            invalid_tracking_grace_samples=_int_with_default(run.get("invalid_tracking_grace_samples"), 0),
            debug_locked_points_tracking=bool(run.get("debug_locked_points_tracking", False)),
        ),
    )


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def _load_temp_register_config(
    value: dict[str, Any],
    *,
    function_code: int,
    start_address: int,
    register_count: int,
    signed: bool,
    decode_scale: float,
    encode_scale: float,
) -> TempRegisterConfig:
    return TempRegisterConfig(
        function_code=int(value.get("function_code", function_code) or function_code),
        start_address=int(value.get("start_address", start_address) or start_address),
        register_count=int(value.get("register_count", register_count) or register_count),
        signed=bool(value.get("signed", signed)),
        decode_scale=float(value.get("decode_scale", decode_scale) or decode_scale),
        encode_scale=float(value.get("encode_scale", encode_scale) or encode_scale),
    )


def _int_with_default(value: Any, default: int) -> int:
    return int(value if value is not None else default)


def _float_with_default(value: Any, default: float) -> float:
    return float(value if value is not None else default)


def _hz_from_interval_ms(interval_ms: int) -> float:
    safe_interval_ms = max(int(interval_ms), 1)
    return 1000.0 / safe_interval_ms


def _load_camera_acquisition_profile(
    value: dict[str, Any],
    *,
    default_trigger_mode: str,
    default_pixel_format: str,
    default_exposure_us: int,
    default_gain_db: float,
    default_timeout_ms: int,
    default_device_roi: DeviceRoiConfig,
) -> CameraAcquisitionProfileConfig:
    device_roi = _normalize_mapping(value.get("device_roi"))
    return CameraAcquisitionProfileConfig(
        trigger_mode=str(value.get("trigger_mode", default_trigger_mode) or default_trigger_mode),
        pixel_format=str(value.get("pixel_format", default_pixel_format) or default_pixel_format),
        exposure_us=int(value.get("exposure_us", default_exposure_us) or default_exposure_us),
        gain_db=float(value.get("gain_db", default_gain_db) or default_gain_db),
        timeout_ms=int(value.get("timeout_ms", default_timeout_ms) or default_timeout_ms),
        device_roi=DeviceRoiConfig(
            x=int(device_roi.get("x", default_device_roi.x) or default_device_roi.x),
            y=int(device_roi.get("y", default_device_roi.y) or default_device_roi.y),
            width=int(device_roi.get("width", default_device_roi.width) or default_device_roi.width),
            height=int(device_roi.get("height", default_device_roi.height) or default_device_roi.height),
        ),
        decimation=_optional_positive_int(value.get("decimation")),
        binning=_optional_positive_int(value.get("binning")),
    )


def _optional_positive_int(value: Any) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


__all__ = ["RuntimeConfig", "WebAppConfig", "load_runtime_config"]
