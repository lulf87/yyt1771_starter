from pathlib import Path

import pytest

from src.webapp import config as config_module
from src.webapp.config import load_runtime_config


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
    assert runtime_config.camera == {}


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
  camera: hik_rtsp_opencv
  temp: modbus_temp
  plc: mock
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
    assert runtime_config.adapters["camera"] == "hik_rtsp_opencv"
    assert runtime_config.storage["sqlite_path"] == "examples/runtime/dev_lab.sqlite3"
    assert runtime_config.camera == {}


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
  camera: hik_rtsp_opencv
  temp: modbus_temp
  plc: mock
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
storage:
  artifact_dir: examples/runtime/local-artifacts
""",
    )
    monkeypatch.setattr(config_module, "_project_root", lambda: tmp_path)

    runtime_config = load_runtime_config("dev_lab")

    assert runtime_config.profile == "dev_lab"
    assert runtime_config.adapters == {
        "camera": "hik_gige_mvs",
        "temp": "modbus_temp",
        "plc": "mock",
    }
    assert runtime_config.camera["transport"] == "gige_vision"
    assert runtime_config.camera["sdk"] == "hik_mvs"
    assert runtime_config.camera["probe_mode"] == "protocol_any"
    assert runtime_config.camera["allowed_models"] == []
    assert runtime_config.storage["sqlite_path"] == "examples/runtime/dev_lab.sqlite3"
    assert runtime_config.storage["artifact_dir"] == "examples/runtime/local-artifacts"
    assert runtime_config.logging["dir"] == "examples/runtime/logs"


def test_load_runtime_config_reads_prod_camera_contract() -> None:
    runtime_config = load_runtime_config("prod_win")

    assert runtime_config.profile == "prod_win"
    assert runtime_config.adapters["camera"] == "hik_gige_mvs"
    assert runtime_config.camera["transport"] == "gige_vision"
    assert runtime_config.camera["sdk"] == "hik_mvs"
    assert runtime_config.camera["probe_mode"] == "pinned"
    assert runtime_config.camera["allowed_models"] == ["MV-CU060-10GM"]
    assert runtime_config.camera["serial_number"] == ""
    assert runtime_config.camera["ip"] == ""


def test_load_runtime_config_raises_clear_error_for_missing_profile() -> None:
    with pytest.raises(FileNotFoundError, match="Profile config not found"):
        load_runtime_config("missing_profile")


def _write_config(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")
