from src.application.real_offline_alignment import run_alignment_audit


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
    assert all(item["selection_mode"] == payload["angle_results"][0]["selection_mode"] for item in payload["angle_results"])
    assert all(item["point_a_px"] for item in payload["angle_results"])
    assert all(item["point_b_px"] for item in payload["angle_results"])
