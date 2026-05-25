from pathlib import Path
import json
import subprocess
import sys

import pytest

from src.application.real_offline_alignment import REAL_ALIGNMENT_PROFILES, run_all_alignment_audits, run_alignment_audit


def test_run_alignment_audit_confirms_pixels_contours_and_ab_points() -> None:
    payload = run_alignment_audit()

    assert payload["status"] == "ok"
    assert payload["real_profile"] == "dev_lab"
    assert payload["offline_profile"] == "dev_offline_capture"
    assert payload["hardware_access"] == "not_attempted"
    assert payload["pixel_contract"]["source_size_px"] == {"width": 2048, "height": 1364}
    assert payload["pixel_contract"]["preview_display_px"] == {"width": 816, "height": 544}
    assert payload["pixel_contract"]["setup_preview_acquisition"] == {
        "pixel_format": "mono8",
        "exposure_us": 50000,
        "gain_db": 12.0,
    }
    assert payload["pixel_contract"]["measurement_acquisition"] == {
        "pixel_format": "mono8",
        "exposure_us": 50000,
        "gain_db": 12.0,
    }
    assert payload["algorithm_contract"]["vision"] == {
        "foreground_polarity": "dark_on_light",
        "threshold_mode": "adaptive",
        "edge_threshold": 10.0,
        "ignore_internal_texture": False,
        "min_target_area_px": 200,
        "quality_threshold": 0.75,
    }
    assert payload["algorithm_contract"]["tracking_policy"] == {
        "stop_on_invalid_tracking": False,
        "invalid_tracking_grace_samples": 5,
        "debug_locked_points_tracking": False,
    }
    assert payload["angles_checked"] == 12
    assert [item["angle_deg"] for item in payload["angle_results"]] == list(range(0, 360, 30))
    assert all(
        item["selection_mode"] == payload["angle_results"][0]["selection_mode"]
        for item in payload["angle_results"]
    )
    assert all(item["measurement_frame_size_px"] for item in payload["angle_results"])
    assert all(item["measurement_origin_in_setup_px"] for item in payload["angle_results"])
    assert all(item["point_a_setup_px"] for item in payload["angle_results"])
    assert all(item["point_b_setup_px"] for item in payload["angle_results"])
    assert all(item["point_a_px"] for item in payload["angle_results"])
    assert all(item["point_b_px"] for item in payload["angle_results"])
    for item in payload["angle_results"]:
        origin = item["measurement_origin_in_setup_px"]
        assert item["point_a_setup_px"] == [
            item["point_a_px"][0] + origin["x"],
            item["point_a_px"][1] + origin["y"],
        ]
        assert item["point_b_setup_px"] == [
            item["point_b_px"][0] + origin["x"],
            item["point_b_px"][1] + origin["y"],
        ]
    assert payload["offline_material"]["status"] in {"ok", "missing"}


def test_run_alignment_audit_confirms_prod_win_matches_offline_truth_without_device_access() -> None:
    payload = run_alignment_audit(real_profile="prod_win")

    assert payload["status"] == "ok"
    assert payload["real_profile"] == "prod_win"
    assert payload["offline_profile"] == "dev_offline_capture"
    assert payload["hardware_access"] == "not_attempted"
    assert payload["pixel_contract"]["source_size_px"] == {"width": 2048, "height": 1364}
    assert payload["pixel_contract"]["preview_display_px"] == {"width": 816, "height": 544}
    assert payload["angles_checked"] == 12
    assert [item["angle_deg"] for item in payload["angle_results"]] == list(range(0, 360, 30))
    assert all(item["point_a_px"] for item in payload["angle_results"])
    assert all(item["point_b_px"] for item in payload["angle_results"])
    assert payload["offline_material"]["status"] in {"ok", "missing"}


def test_run_all_alignment_audits_confirms_every_locked_real_profile_without_device_access() -> None:
    payload = run_all_alignment_audits()

    assert payload["status"] == "ok"
    assert payload["offline_profile"] == "dev_offline_capture"
    assert payload["hardware_access"] == "not_attempted"
    assert [item["real_profile"] for item in payload["profile_results"]] == list(REAL_ALIGNMENT_PROFILES)
    assert all(item["status"] == "ok" for item in payload["profile_results"])
    assert all(item["angles_checked"] == 12 for item in payload["profile_results"])
    assert all(
        item["pixel_contract"]["source_size_px"] == {"width": 2048, "height": 1364}
        for item in payload["profile_results"]
    )
    assert all(
        item["pixel_contract"]["setup_preview_acquisition"]
        == {"pixel_format": "mono8", "exposure_us": 50000, "gain_db": 12.0}
        for item in payload["profile_results"]
    )
    assert all(
        item["pixel_contract"]["measurement_acquisition"]
        == {"pixel_format": "mono8", "exposure_us": 50000, "gain_db": 12.0}
        for item in payload["profile_results"]
    )
    assert all(
        item["algorithm_contract"]["vision"]
        == {
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "edge_threshold": 10.0,
            "ignore_internal_texture": False,
            "min_target_area_px": 200,
            "quality_threshold": 0.75,
        }
        for item in payload["profile_results"]
    )
    assert all(
        item["algorithm_contract"]["tracking_policy"]
        == {
            "stop_on_invalid_tracking": False,
            "invalid_tracking_grace_samples": 5,
            "debug_locked_points_tracking": False,
        }
        for item in payload["profile_results"]
    )


def test_real_offline_alignment_cli_can_audit_all_locked_profiles_without_device_access() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "src.application.real_offline_alignment", "--all-profiles"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["status"] == "ok"
    assert payload["hardware_access"] == "not_attempted"
    assert payload["profiles_checked"] == len(REAL_ALIGNMENT_PROFILES)
    assert [item["real_profile"] for item in payload["profile_results"]] == list(REAL_ALIGNMENT_PROFILES)


def test_run_alignment_audit_confirms_standard_offline_material_samples_when_available() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    capture_dir = repo_root / "examples/runtime/camera_captures/20260522-183158-dev_lab"
    run_dir = repo_root / "examples/runtime/artifacts/run-9953bd601113"
    if not capture_dir.exists() or not run_dir.exists():
        pytest.skip("standard offline material fixture is not available")

    payload = run_alignment_audit()
    material = payload["offline_material"]

    assert material["status"] == "ok"
    assert material["capture_dir"] == "examples/runtime/camera_captures/20260522-183158-dev_lab"
    assert material["reference_run_dir"] == "examples/runtime/artifacts/run-9953bd601113"
    assert material["frame_count"] == 5807
    assert material["source_size_px"] == {"width": 2048, "height": 1364}
    assert material["dtype"] == "uint8"
    assert material["accepted_effective_acquisition_roi"] == {"x": 275, "y": 0, "width": 1759, "height": 1289}
    assert material["sample_frames_checked"] == 9
    assert [item["frame_index"] for item in material["sample_results"]] == [
        1,
        40,
        284,
        285,
        2281,
        2282,
        5436,
        5437,
        5807,
    ]
    assert all(item["point_a_px"] for item in material["sample_results"])
    assert all(item["point_b_px"] for item in material["sample_results"])
