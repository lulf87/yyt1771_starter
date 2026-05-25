from pathlib import Path

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
    assert payload["angles_checked"] == 12
    assert [item["angle_deg"] for item in payload["angle_results"]] == list(range(0, 360, 30))
    assert all(
        item["selection_mode"] == payload["angle_results"][0]["selection_mode"]
        for item in payload["angle_results"]
    )
    assert all(item["point_a_px"] for item in payload["angle_results"])
    assert all(item["point_b_px"] for item in payload["angle_results"])
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
