import pytest

from src.application.real_offline_alignment_guard import (
    RealOfflineAlignmentGuardError,
    assert_real_offline_alignment_ready,
    assert_real_offline_contour_request_ready,
    assert_real_offline_definition_ready,
    is_real_offline_alignment_locked_profile,
)
from src.application.runtime_config import load_runtime_config
from src.core.enums import ObservationAxis
from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion


def test_alignment_guard_allows_locked_profile_when_contract_matches() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")

    item = assert_real_offline_alignment_ready(runtime_config, context="unit_test")

    assert item is not None
    assert item["status"] == "ok"
    assert is_real_offline_alignment_locked_profile(runtime_config)
    assert "source pixels and algorithm settings match" in item["detail"]


def test_alignment_guard_ignores_unlocked_mock_profile() -> None:
    runtime_config = load_runtime_config("dev_mock")

    item = assert_real_offline_alignment_ready(runtime_config, context="unit_test")

    assert item is None
    assert not is_real_offline_alignment_locked_profile(runtime_config)


def test_alignment_guard_blocks_locked_profile_when_vision_drifts() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")
    runtime_config.live.vision.threshold_mode = "binary"

    with pytest.raises(RealOfflineAlignmentGuardError, match="contour detection could diverge"):
        assert_real_offline_alignment_ready(runtime_config, context="unit_test")


def test_contour_request_guard_blocks_locked_profile_request_drift() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")

    request = {
        "foreground_polarity": "light_on_dark",
        "threshold_mode": "adaptive",
        "ignore_internal_texture": False,
        "min_target_area_px": 200,
    }

    with pytest.raises(RealOfflineAlignmentGuardError, match="request contour settings"):
        assert_real_offline_contour_request_ready(runtime_config, request, context="unit_test")


def test_definition_guard_blocks_locked_profile_definition_drift() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=96, height=64),
        metric_box=MetricBox(center_x=48, center_y=32, width=80, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=12, y=32),
        point_b_px=PixelPoint(x=83, y=32),
        observation_axis=ObservationAxis.LONG_AXIS,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        ignore_internal_texture=False,
        min_target_area_px=200,
    )

    with pytest.raises(RealOfflineAlignmentGuardError, match="request contour settings"):
        assert_real_offline_definition_ready(runtime_config, definition, context="unit_test")
