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
    assert runtime_config.replay["dataset_path"] == "examples/replay"


def test_load_runtime_config_raises_clear_error_for_missing_profile() -> None:
    with pytest.raises(FileNotFoundError, match="Profile config not found"):
        load_runtime_config("missing_profile")
