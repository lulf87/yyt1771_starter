from pathlib import Path

import pytest

from src.application import runtime_config as config_module
from src.application.runtime_config import load_runtime_config


def test_load_runtime_config_reads_known_profile() -> None:
    runtime_config = load_runtime_config("dev_mock")

    assert runtime_config.profile == "dev_mock"
    assert runtime_config.platform == "mac"
    assert runtime_config.mode == "mock"
    assert runtime_config.webapp.host == "127.0.0.1"
    assert runtime_config.webapp.port == 8000
    assert runtime_config.adapters == {
        "camera": "mock",
        "temp": "mock",
        "plc": "mock",
    }
    assert runtime_config.storage["sqlite_path"] == "examples/runtime/dev_mock.sqlite3"
    assert runtime_config.storage["artifact_dir"] == "examples/runtime/artifacts"
    assert runtime_config.replay["dataset_path"] == "examples/replay"
    assert runtime_config.camera["setup_preview"]["device_roi"]["width"] == 1120
    assert runtime_config.camera["measurement"]["device_roi"]["width"] == 2048
    assert runtime_config.live.camera.transport == ""
    assert runtime_config.live.camera.setup_preview.exposure_us == 10_000
    assert runtime_config.live.camera.setup_preview.gain_db == 18.0
    assert runtime_config.live.camera.setup_preview.device_roi.x == 1440
    assert runtime_config.live.camera.setup_preview.device_roi.y == 1086
    assert runtime_config.live.camera.setup_preview.device_roi.width == 1120
    assert runtime_config.live.camera.setup_preview.device_roi.height == 620
    assert runtime_config.live.camera.measurement.exposure_us == 10_000
    assert runtime_config.live.camera.measurement.gain_db == 18.0
    assert runtime_config.live.camera.measurement.device_roi.x == 512
    assert runtime_config.live.camera.measurement.device_roi.y == 342
    assert runtime_config.live.camera.measurement.device_roi.width == 2048
    assert runtime_config.live.camera.measurement.device_roi.height == 1364
    assert runtime_config.live.temp.protocol == "modbus_rtu"
    assert runtime_config.live.temp.slave_address == 1
    assert runtime_config.live.temp.serial.port == ""
    assert runtime_config.live.temp.serial.baudrate == 19_200
    assert runtime_config.live.temp.register_map.process_value.start_address == 264
    assert runtime_config.live.temp.control.startup_power_percent == 100.0
    assert runtime_config.live.temp.control.completion_mode == "target_reached"
    assert runtime_config.live.temp.control.mock_ramp_step_celsius == 10.0
    assert runtime_config.live.vision.foreground_polarity == "dark_on_light"
    assert runtime_config.live.analysis.engine == "afas"
    assert runtime_config.live.run.capture_interval_ms == 200
    assert runtime_config.live.run.manual_stop_max_samples == 10_000
    assert runtime_config.live.run.preview_target_fps == 8.0
    assert runtime_config.live.run.preview_display_max_width == 640
    assert runtime_config.live.run.preview_display_max_height == 480
    assert runtime_config.live.run.measurement_target_hz == 5.0
    assert runtime_config.live.run.artifact_capture_hz == 5.0
    assert runtime_config.live.run.debug_locked_points_tracking is False


def test_load_runtime_config_reads_lab_camera_mock_temp_profile() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")

    assert runtime_config.profile == "dev_lab_camera_mock_temp"
    assert runtime_config.mode == "lab"
    assert runtime_config.adapters == {
        "camera": "hik_gige_mvs",
        "temp": "mock",
        "plc": "mock",
    }
    assert runtime_config.live.temp.backend == "mock"
    assert runtime_config.live.temp.control.completion_mode == "target_reached"
    assert runtime_config.live.temp.control.mock_ramp_step_celsius == 0.005
    assert runtime_config.live.camera.setup_preview.exposure_us == 10_000
    assert runtime_config.live.camera.setup_preview.gain_db == 18.0
    assert runtime_config.live.camera.setup_preview.device_roi.x == 1440
    assert runtime_config.live.camera.setup_preview.device_roi.y == 1086
    assert runtime_config.live.camera.setup_preview.device_roi.width == 1120
    assert runtime_config.live.camera.setup_preview.device_roi.height == 620
    assert runtime_config.live.camera.measurement.exposure_us == 10_000
    assert runtime_config.live.camera.measurement.gain_db == 18.0
    assert runtime_config.live.camera.measurement.device_roi.width == 2048
    assert runtime_config.live.camera.measurement.device_roi.height == 1364
    assert runtime_config.live.run.preview_target_fps == 20.0
    assert runtime_config.live.run.measurement_target_hz == 20.0
    assert runtime_config.live.run.manual_stop_max_samples == 0
    assert runtime_config.live.run.stop_on_invalid_tracking is False
    assert runtime_config.live.run.invalid_tracking_grace_samples == 5
    assert runtime_config.live.run.debug_locked_points_tracking is False


def test_load_runtime_config_reads_offline_capture_profile() -> None:
    runtime_config = load_runtime_config("dev_offline_capture")

    assert runtime_config.profile == "dev_offline_capture"
    assert runtime_config.mode == "offline"
    assert runtime_config.adapters["camera"] == "offline_capture"
    assert runtime_config.adapters["temp"] == "offline_capture"
    assert runtime_config.live.temp.backend == "offline_capture"
    assert runtime_config.camera["offline_capture"]["capture_dir"].endswith(
        "examples/runtime/camera_captures/20260522-183158-dev_lab"
    )
    assert runtime_config.live.camera.setup_preview.device_roi.width == 0
    assert runtime_config.live.camera.measurement.device_roi.width == 2048
    assert runtime_config.live.camera.measurement.device_roi.height == 1364
    assert runtime_config.live.temp.control.completion_mode == "manual_stop_only"
    assert runtime_config.live.run.manual_stop_max_samples == 0


def test_load_runtime_config_keeps_dev_lab_baseline_without_local_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    _write_config(
        configs_dir / "dev_lab.yaml",
        """
profile: dev_lab
platform: mac
mode: lab
webapp:
  host: 127.0.0.1
  port: 8000
adapters:
  camera: hik_gige_mvs
  temp: mock
  plc: mock
camera:
  transport: gige_vision
  sdk: hik_mvs
  probe_mode: protocol_any
  allowed_models: []
  serial_number: ""
  ip: ""
  trigger_mode: free_run
  pixel_format: mono8
  exposure_us: 10000
  gain_db: 0.0
  timeout_ms: 1000
  setup_preview:
    trigger_mode: free_run
    pixel_format: mono8
    exposure_us: 50000
    gain_db: 12.0
    timeout_ms: 1000
    device_roi:
      x: 0
      y: 0
      width: 0
      height: 0
  measurement:
    trigger_mode: free_run
    pixel_format: mono8
    exposure_us: 50000
    gain_db: 12.0
    timeout_ms: 1000
    device_roi:
      x: 512
      y: 342
      width: 2048
      height: 1364
temp:
  backend: mock
  control:
    completion_mode: manual_stop_only
    mock_ramp_step_celsius: 0.5
run:
  preview_poll_ms: 50
  capture_interval_ms: 50
  preview_target_fps: 20
  measurement_target_hz: 20
  artifact_capture_hz: 20
  manual_stop_max_samples: 0
  preview_display_max_width: 816
  preview_display_max_height: 544
  invalid_tracking_grace_samples: 5
storage:
  sqlite_path: examples/runtime/dev_lab.sqlite3
  artifact_dir: examples/runtime/artifacts
replay:
  dataset_path: examples/replay
""",
    )
    monkeypatch.setattr(config_module, "_project_root", lambda: tmp_path)

    runtime_config = load_runtime_config("dev_lab")

    assert runtime_config.profile == "dev_lab"
    assert runtime_config.adapters["camera"] == "hik_gige_mvs"
    assert runtime_config.adapters["temp"] == "mock"
    assert runtime_config.storage["sqlite_path"] == "examples/runtime/dev_lab.sqlite3"
    assert runtime_config.camera["transport"] == "gige_vision"
    assert runtime_config.live.camera.pixel_format == "mono8"
    assert runtime_config.live.camera.setup_preview.pixel_format == "mono8"
    assert runtime_config.live.camera.setup_preview.exposure_us == 50_000
    assert runtime_config.live.camera.setup_preview.gain_db == 12.0
    assert runtime_config.live.camera.setup_preview.device_roi.width == 0
    assert runtime_config.live.camera.setup_preview.device_roi.height == 0
    assert runtime_config.live.camera.measurement.pixel_format == "mono8"
    assert runtime_config.live.camera.measurement.exposure_us == 50_000
    assert runtime_config.live.camera.measurement.gain_db == 12.0
    assert runtime_config.live.camera.measurement.device_roi.width == 2048
    assert runtime_config.live.camera.measurement.device_roi.height == 1364
    assert runtime_config.live.camera.transport == "gige_vision"
    assert runtime_config.live.temp.protocol == "modbus_rtu"
    assert runtime_config.live.temp.backend == "mock"
    assert runtime_config.live.temp.serial.timeout_ms == 500
    assert runtime_config.live.temp.register_map.process_value.start_address == 264
    assert runtime_config.live.temp.control.completion_mode == "manual_stop_only"
    assert runtime_config.live.temp.control.mock_ramp_step_celsius == 0.5
    assert runtime_config.live.run.preview_target_fps == 20.0
    assert runtime_config.live.run.preview_poll_ms == 50
    assert runtime_config.live.run.manual_stop_max_samples == 0
    assert runtime_config.live.run.preview_display_max_width == 816
    assert runtime_config.live.run.preview_display_max_height == 544
    assert runtime_config.live.run.capture_interval_ms == 50
    assert runtime_config.live.run.measurement_target_hz == 20.0
    assert runtime_config.live.run.artifact_capture_hz == 20.0
    assert runtime_config.live.run.invalid_tracking_grace_samples == 5
    assert runtime_config.live.run.debug_locked_points_tracking is False


def test_load_runtime_config_merges_local_override_recursively(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    _write_config(
        configs_dir / "dev_lab.yaml",
        """
profile: dev_lab
platform: mac
mode: lab
webapp:
  host: 127.0.0.1
  port: 8000
adapters:
  camera: hik_gige_mvs
  temp: mock
  plc: mock
camera:
  transport: gige_vision
  sdk: hik_mvs
  probe_mode: protocol_any
  allowed_models: []
  serial_number: ""
  ip: ""
  trigger_mode: free_run
  pixel_format: mono8
  exposure_us: 10000
  gain_db: 0.0
  timeout_ms: 1000
temp:
  backend: mock
storage:
  sqlite_path: examples/runtime/dev_lab.sqlite3
  artifact_dir: examples/runtime/artifacts
logging:
  dir: examples/runtime/logs
""",
    )
    _write_config(
        configs_dir / "dev_lab.local.yaml",
        """
adapters:
  camera: hik_gige_mvs
  temp: lu92xx_modbus_rtu
camera:
  transport: gige_vision
  sdk: hik_mvs
  probe_mode: protocol_any
  allowed_models: []
  serial_number: ""
  ip: ""
  trigger_mode: free_run
  pixel_format: mono8
  exposure_us: 10000
  gain_db: 0.0
  timeout_ms: 1000
  device_roi:
    x: 10
    y: 12
    width: 640
    height: 480
  setup_preview:
    exposure_us: 8000
    timeout_ms: 900
    device_roi:
      x: 0
      y: 0
      width: 0
      height: 0
  measurement:
    exposure_us: 4000
    timeout_ms: 450
    device_roi:
      x: 20
      y: 30
      width: 320
      height: 128
    decimation: 2
    binning: 1
temp:
  backend: lu92xx_modbus_rtu
  protocol: modbus_rtu
  slave_address: 2
  serial:
    port: COM5
    baudrate: 19200
    bytesize: 8
    parity: N
    stopbits: 1
    timeout_ms: 700
  register_map:
    process_value:
      function_code: 3
      start_address: 258
      register_count: 1
      signed: true
      decode_scale: 0.1
    target_or_stop_value:
      function_code: 6
      start_address: 0
      register_count: 1
      signed: true
      encode_scale: 10.0
    output_power:
      function_code: 6
      start_address: 4
      register_count: 1
      signed: false
      encode_scale: 128.0
  control:
    start_output_mode: power_nonzero
    startup_power_percent: 80.0
    completion_mode: manual_stop_only
    mock_ramp_step_celsius: 1.5
vision:
  foreground_polarity: dark_on_light
  threshold_mode: adaptive
  edge_threshold: 15
  ignore_internal_texture: true
  min_target_area_px: 300
  quality_threshold: 0.8
analysis:
  engine: afas
  channel_name: Space1
  as_fit_point_count: 6
  af_fit_point_count: 7
run:
  preview_poll_ms: 600
  telemetry_poll_ms: 700
  capture_interval_ms: 250
  manual_stop_max_samples: 1234
  preview_target_fps: 8
  preview_display_max_width: 720
  preview_display_max_height: 540
  measurement_target_hz: 50
  artifact_capture_hz: 25
  stop_on_invalid_tracking: false
  debug_locked_points_tracking: true
storage:
  artifact_dir: examples/runtime/local-artifacts
""",
    )
    monkeypatch.setattr(config_module, "_project_root", lambda: tmp_path)

    runtime_config = load_runtime_config("dev_lab")

    assert runtime_config.profile == "dev_lab"
    assert runtime_config.adapters == {
        "camera": "hik_gige_mvs",
        "temp": "lu92xx_modbus_rtu",
        "plc": "mock",
    }
    assert runtime_config.camera["transport"] == "gige_vision"
    assert runtime_config.camera["sdk"] == "hik_mvs"
    assert runtime_config.camera["probe_mode"] == "protocol_any"
    assert runtime_config.camera["allowed_models"] == []
    assert runtime_config.storage["sqlite_path"] == "examples/runtime/dev_lab.sqlite3"
    assert runtime_config.storage["artifact_dir"] == "examples/runtime/local-artifacts"
    assert runtime_config.logging["dir"] == "examples/runtime/logs"
    assert runtime_config.live.camera.transport == "gige_vision"
    assert runtime_config.live.camera.device_roi.width == 640
    assert runtime_config.live.camera.setup_preview.exposure_us == 8000
    assert runtime_config.live.camera.setup_preview.timeout_ms == 900
    assert runtime_config.live.camera.setup_preview.device_roi.width == 0
    assert runtime_config.live.camera.measurement.exposure_us == 4000
    assert runtime_config.live.camera.measurement.timeout_ms == 450
    assert runtime_config.live.camera.measurement.device_roi.width == 320
    assert runtime_config.live.camera.measurement.device_roi.height == 128
    assert runtime_config.live.camera.measurement.decimation == 2
    assert runtime_config.live.camera.measurement.binning == 1
    assert runtime_config.live.temp.backend == "lu92xx_modbus_rtu"
    assert runtime_config.live.temp.protocol == "modbus_rtu"
    assert runtime_config.live.temp.slave_address == 2
    assert runtime_config.live.temp.serial.port == "COM5"
    assert runtime_config.live.temp.register_map.process_value.start_address == 258
    assert runtime_config.live.temp.register_map.output_power.encode_scale == 128.0
    assert runtime_config.live.temp.control.startup_power_percent == 80.0
    assert runtime_config.live.temp.control.completion_mode == "manual_stop_only"
    assert runtime_config.live.temp.control.mock_ramp_step_celsius == 1.5
    assert runtime_config.live.vision.ignore_internal_texture is True
    assert runtime_config.live.vision.min_target_area_px == 300
    assert runtime_config.live.analysis.af_fit_point_count == 7
    assert runtime_config.live.run.manual_stop_max_samples == 1234
    assert runtime_config.live.run.preview_target_fps == 8.0
    assert runtime_config.live.run.preview_display_max_width == 720
    assert runtime_config.live.run.preview_display_max_height == 540
    assert runtime_config.live.run.measurement_target_hz == 50.0
    assert runtime_config.live.run.artifact_capture_hz == 25.0
    assert runtime_config.live.run.stop_on_invalid_tracking is False
    assert runtime_config.live.run.debug_locked_points_tracking is True


def test_load_runtime_config_reads_prod_camera_contract() -> None:
    runtime_config = load_runtime_config("prod_win")

    assert runtime_config.profile == "prod_win"
    assert runtime_config.adapters["camera"] == "hik_gige_mvs"
    assert runtime_config.adapters["temp"] == "lu92xx_modbus_rtu"
    assert runtime_config.camera["transport"] == "gige_vision"
    assert runtime_config.camera["sdk"] == "hik_mvs"
    assert runtime_config.camera["probe_mode"] == "pinned"
    assert runtime_config.camera["allowed_models"] == ["MV-CU060-10GM"]
    assert runtime_config.camera["serial_number"] == ""
    assert runtime_config.camera["ip"] == ""
    assert runtime_config.live.camera.transport == "gige_vision"
    assert runtime_config.live.camera.sdk == "hik_mvs"
    assert runtime_config.live.camera.allowed_models == ["MV-CU060-10GM"]
    assert runtime_config.live.camera.setup_preview.exposure_us == 10_000
    assert runtime_config.live.camera.measurement.exposure_us == 10_000
    assert runtime_config.live.temp.backend == "lu92xx_modbus_rtu"
    assert runtime_config.live.temp.protocol == "modbus_rtu"
    assert runtime_config.live.temp.slave_address == 1
    assert runtime_config.live.temp.serial.baudrate == 19_200
    assert runtime_config.live.temp.register_map.process_value.start_address == 264
    assert runtime_config.live.temp.register_map.target_or_stop_value.encode_scale == 10.0
    assert runtime_config.live.temp.register_map.output_power.start_address == 4
    assert runtime_config.live.temp.control.startup_power_percent == 100.0
    assert runtime_config.live.temp.control.completion_mode == "target_reached"
    assert runtime_config.live.temp.control.mock_ramp_step_celsius == 10.0
    assert runtime_config.live.run.manual_stop_max_samples == 10_000
    assert runtime_config.live.run.preview_target_fps == 8.0
    assert runtime_config.live.run.preview_display_max_width == 640
    assert runtime_config.live.run.preview_display_max_height == 480
    assert runtime_config.live.run.measurement_target_hz == 5.0
    assert runtime_config.live.run.artifact_capture_hz == 5.0
    assert runtime_config.live.run.debug_locked_points_tracking is False


def test_load_runtime_config_raises_clear_error_for_missing_profile() -> None:
    with pytest.raises(FileNotFoundError, match="Profile config not found"):
        load_runtime_config("missing_profile")


def _write_config(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")
