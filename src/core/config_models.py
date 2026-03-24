"""Configuration models for the frozen scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RecipeConfig:
    sample_id: str
    camera_backend: str = "mock_camera"
    temp_backend: str = "mock_temp"
    plc_backend: str = "mock_plc"


@dataclass(slots=True)
class AppConfig:
    recipe_path: str = "configs/recipe_example.yaml"
    dry_run: bool = True


@dataclass(slots=True)
class DeviceRoiConfig:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


@dataclass(slots=True)
class CameraAcquisitionProfileConfig:
    trigger_mode: str = "free_run"
    pixel_format: str = "mono8"
    exposure_us: int = 10_000
    gain_db: float = 0.0
    timeout_ms: int = 1_000
    device_roi: DeviceRoiConfig = field(default_factory=DeviceRoiConfig)
    decimation: int | None = None
    binning: int | None = None


@dataclass(slots=True)
class CameraRuntimeConfig:
    transport: str = ""
    sdk: str = ""
    probe_mode: str = ""
    allowed_models: list[str] = field(default_factory=list)
    serial_number: str = ""
    ip: str = ""
    trigger_mode: str = "free_run"
    pixel_format: str = "mono8"
    exposure_us: int = 10_000
    gain_db: float = 0.0
    timeout_ms: int = 1_000
    device_roi: DeviceRoiConfig = field(default_factory=DeviceRoiConfig)
    setup_preview: CameraAcquisitionProfileConfig = field(default_factory=CameraAcquisitionProfileConfig)
    measurement: CameraAcquisitionProfileConfig = field(default_factory=CameraAcquisitionProfileConfig)


@dataclass(slots=True)
class SerialPortConfig:
    port: str = ""
    baudrate: int = 19_200
    bytesize: int = 8
    parity: str = "N"
    stopbits: int = 1
    timeout_ms: int = 500


@dataclass(slots=True)
class TempRegisterConfig:
    function_code: int = 3
    start_address: int = 0
    register_count: int = 1
    signed: bool = False
    decode_scale: float = 1.0
    encode_scale: float = 1.0


def _default_process_value_config() -> "TempRegisterConfig":
    return TempRegisterConfig(
        function_code=3,
        start_address=264,
        register_count=1,
        signed=True,
        decode_scale=0.1,
    )


def _default_target_or_stop_config() -> "TempRegisterConfig":
    return TempRegisterConfig(
        function_code=6,
        start_address=0,
        register_count=1,
        signed=True,
        encode_scale=10.0,
    )


def _default_output_power_config() -> "TempRegisterConfig":
    return TempRegisterConfig(
        function_code=6,
        start_address=4,
        register_count=1,
        signed=False,
        encode_scale=256.0,
    )


@dataclass(slots=True)
class TempRegisterMapConfig:
    process_value: TempRegisterConfig = field(default_factory=_default_process_value_config)
    target_or_stop_value: TempRegisterConfig = field(default_factory=_default_target_or_stop_config)
    output_power: TempRegisterConfig = field(default_factory=_default_output_power_config)


@dataclass(slots=True)
class TempControlConfig:
    start_output_mode: str = "power_nonzero"
    startup_power_percent: float = 100.0


@dataclass(slots=True)
class TempRuntimeConfig:
    backend: str = ""
    protocol: str = "modbus_rtu"
    slave_address: int = 1
    serial: SerialPortConfig = field(default_factory=SerialPortConfig)
    register_map: TempRegisterMapConfig = field(default_factory=TempRegisterMapConfig)
    control: TempControlConfig = field(default_factory=TempControlConfig)


@dataclass(slots=True)
class VisionRuntimeConfig:
    foreground_polarity: str = "dark_on_light"
    threshold_mode: str = "adaptive"
    edge_threshold: float = 10.0
    ignore_internal_texture: bool = False
    min_target_area_px: int = 200
    quality_threshold: float = 0.75


@dataclass(slots=True)
class AnalysisRuntimeConfig:
    engine: str = "afas"
    channel_name: str = "Space1"
    as_fit_point_count: int = 5
    af_fit_point_count: int = 5


@dataclass(slots=True)
class RunRuntimeConfig:
    preview_poll_ms: int = 500
    telemetry_poll_ms: int = 500
    capture_interval_ms: int = 200
    preview_target_fps: float | None = None
    measurement_target_hz: float | None = None
    artifact_capture_hz: float | None = None
    stop_on_invalid_tracking: bool = True


@dataclass(slots=True)
class LiveRunConfig:
    camera: CameraRuntimeConfig = field(default_factory=CameraRuntimeConfig)
    temp: TempRuntimeConfig = field(default_factory=TempRuntimeConfig)
    vision: VisionRuntimeConfig = field(default_factory=VisionRuntimeConfig)
    analysis: AnalysisRuntimeConfig = field(default_factory=AnalysisRuntimeConfig)
    run: RunRuntimeConfig = field(default_factory=RunRuntimeConfig)
