import pytest

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


def test_load_runtime_config_reads_prod_camera_contract() -> None:
    runtime_config = load_runtime_config("prod_win")

    assert runtime_config.profile == "prod_win"
    assert runtime_config.adapters["camera"] == "hik_gige_mvs"
    assert runtime_config.camera["model"] == "MV-CU060-10GM"
    assert runtime_config.camera["transport"] == "gige_vision"
    assert runtime_config.camera["sdk"] == "hik_mvs"
    assert runtime_config.camera["serial_number"] == ""
    assert runtime_config.camera["ip"] == ""


def test_load_runtime_config_raises_clear_error_for_missing_profile() -> None:
    with pytest.raises(FileNotFoundError, match="Profile config not found"):
        load_runtime_config("missing_profile")
