import pytest

from src.application.real_offline_alignment_guard import (
    RealOfflineAlignmentGuardError,
    assert_real_offline_alignment_ready,
)
from src.application.runtime_config import load_runtime_config


def test_alignment_guard_allows_locked_profile_when_contract_matches() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")

    item = assert_real_offline_alignment_ready(runtime_config, context="unit_test")

    assert item is not None
    assert item["status"] == "ok"
    assert "source pixels and algorithm settings match" in item["detail"]


def test_alignment_guard_ignores_unlocked_mock_profile() -> None:
    runtime_config = load_runtime_config("dev_mock")

    item = assert_real_offline_alignment_ready(runtime_config, context="unit_test")

    assert item is None


def test_alignment_guard_blocks_locked_profile_when_vision_drifts() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")
    runtime_config.live.vision.threshold_mode = "binary"

    with pytest.raises(RealOfflineAlignmentGuardError, match="contour detection could diverge"):
        assert_real_offline_alignment_ready(runtime_config, context="unit_test")
