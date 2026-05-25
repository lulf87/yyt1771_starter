from pathlib import Path

from fastapi.testclient import TestClient

from src.application.real_offline_alignment import RealOfflineAlignmentError
from src.workflow import precheck as precheck_module
from src.webapp.app import create_app
from src.webapp.routes import profile as profile_routes


def _make_client(tmp_path: Path, profile: str = "dev_mock") -> TestClient:
    app = create_app(profile=profile)
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    app.state.runtime_config.replay["dataset_path"] = "examples/replay"
    return TestClient(app)


def test_precheck_api_returns_ready_status_for_dev_mock(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"] == "dev_mock"
    assert payload["status"] == "warn"
    items = {item["name"]: item for item in payload["items"]}
    assert items["sqlite_path"]["status"] == "ok"
    assert items["artifact_dir"]["status"] == "ok"
    assert items["replay_dataset"]["status"] == "ok"
    assert items["camera_backend"]["status"] == "ok"
    assert items["temp_adapter"]["status"] == "pending"
    assert items["plc_adapter"]["status"] == "pending"


def test_precheck_api_reports_fail_for_missing_replay_dataset(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.app.state.runtime_config.replay["dataset_path"] = "examples/missing_replay"

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    items = {item["name"]: item for item in payload["items"]}
    assert items["replay_dataset"]["status"] == "fail"


def test_precheck_api_reports_pinned_camera_policy_fail_for_prod_win_without_identity(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    items = {item["name"]: item for item in payload["items"]}
    assert items["camera_backend"]["status"] == "ok"
    assert items["camera_probe_mode"]["status"] == "ok"
    assert items["camera_model_policy"]["status"] == "ok"
    assert items["camera_transport"]["status"] == "ok"
    assert items["real_offline_pixel_alignment"]["status"] == "ok"
    assert "origin=(512, 342)" in items["real_offline_pixel_alignment"]["detail"]
    assert "preview_display=816x544" in items["real_offline_pixel_alignment"]["detail"]
    assert items["camera_identity"]["status"] == "fail"
    assert items["camera_sdk"]["status"] == "pending"


def test_precheck_api_returns_fail_when_gige_transport_is_invalid(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")
    client.app.state.runtime_config.camera["transport"] = "rtsp"

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    items = {item["name"]: item for item in payload["items"]}
    assert items["camera_transport"]["status"] == "fail"


def test_precheck_api_protocol_any_marks_identity_as_pending(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")
    client.app.state.runtime_config.camera["probe_mode"] = "protocol_any"
    client.app.state.runtime_config.camera["allowed_models"] = []

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "warn"
    items = {item["name"]: item for item in payload["items"]}
    assert items["camera_probe_mode"]["status"] == "ok"
    assert items["camera_model_policy"]["status"] == "pending"
    assert items["camera_identity"]["status"] == "pending"
    assert items["real_offline_pixel_alignment"]["status"] == "ok"


def test_precheck_api_reports_sdk_runtime_warn_when_import_is_not_ready(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="prod_win")
    client.app.state.runtime_config.camera["probe_mode"] = "protocol_any"
    client.app.state.runtime_config.camera["allowed_models"] = []

    def fake_import() -> object:
        raise RuntimeError("Hik MVS SDK Python binding MvCameraControl_class is not importable on this machine.")

    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", fake_import)

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    items = {item["name"]: item for item in payload["items"]}
    assert items["camera_sdk_runtime"]["status"] == "warn"
    assert "import readiness" in items["camera_sdk_runtime"]["detail"]
    assert "does not attempt live device access" in items["camera_sdk_runtime"]["detail"]


def test_precheck_api_reports_prod_win_alignment_as_ready_without_device_access(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="prod_win")
    client.app.state.runtime_config.camera["probe_mode"] = "protocol_any"
    client.app.state.runtime_config.camera["allowed_models"] = []
    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", lambda: object())

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    items = {item["name"]: item for item in payload["items"]}
    assert payload["status"] == "warn"
    assert items["real_offline_pixel_alignment"]["status"] == "ok"
    assert "origin=(512, 342)" in items["real_offline_pixel_alignment"]["detail"]
    assert "size=(2048, 1364)" in items["real_offline_pixel_alignment"]["detail"]
    assert "preview_display=816x544" in items["real_offline_pixel_alignment"]["detail"]
    assert "does not attempt live device access" in items["camera_sdk_runtime"]["detail"]


def test_precheck_api_reports_sdk_runtime_ok_when_import_is_ready(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="prod_win")
    client.app.state.runtime_config.camera["probe_mode"] = "protocol_any"
    client.app.state.runtime_config.camera["allowed_models"] = []
    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", lambda: object())

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    items = {item["name"]: item for item in payload["items"]}
    assert items["camera_sdk_runtime"]["status"] == "ok"
    assert "importable on this machine" in items["camera_sdk_runtime"]["detail"]
    assert "does not attempt live device access" in items["camera_sdk_runtime"]["detail"]


def test_precheck_api_reports_offline_capture_alignment_as_ready(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="dev_offline_capture")

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    items = {item["name"]: item for item in payload["items"]}
    assert items["camera_backend"]["status"] == "ok"
    assert items["real_offline_pixel_alignment"]["status"] == "ok"
    assert "origin=(0, 0)" in items["real_offline_pixel_alignment"]["detail"]
    assert "size=(2048, 1364)" in items["real_offline_pixel_alignment"]["detail"]
    assert "preview_display=816x544" in items["real_offline_pixel_alignment"]["detail"]


def test_precheck_api_reports_dev_lab_alignment_as_ready_without_device_access(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="dev_lab")
    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", lambda: object())

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    items = {item["name"]: item for item in payload["items"]}
    assert items["camera_backend"]["status"] == "ok"
    assert items["real_offline_pixel_alignment"]["status"] == "ok"
    assert "origin=(512, 342)" in items["real_offline_pixel_alignment"]["detail"]
    assert "size=(2048, 1364)" in items["real_offline_pixel_alignment"]["detail"]
    assert "preview_display=816x544" in items["real_offline_pixel_alignment"]["detail"]
    assert "acquisition=mono8/50000us/12.0dB" in items["real_offline_pixel_alignment"]["detail"]
    assert "vision=dark_on_light/adaptive" in items["real_offline_pixel_alignment"]["detail"]
    assert "tracking=continue_on_invalid" in items["real_offline_pixel_alignment"]["detail"]
    assert "ab_points=formal target-contour point_a_px/point_b_px" in items["real_offline_pixel_alignment"]["detail"]
    assert "does not attempt live device access" in items["camera_sdk_runtime"]["detail"]


def test_precheck_api_reports_real_offline_contract_scope_without_device_access(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="dev_lab_camera_mock_temp")
    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", lambda: object())

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    items = {item["name"]: item for item in payload["items"]}
    detail = items["real_offline_pixel_alignment"]["detail"]
    assert "source pixels and algorithm settings match" in detail
    assert "acquisition=mono8/50000us/12.0dB" in detail
    assert "vision=dark_on_light/adaptive edge=10.0 min_area=200 quality=0.75 internal_texture=False" in detail
    assert "tracking=continue_on_invalid grace=5 debug_locked_points=False" in detail
    assert "ab_points=formal target-contour point_a_px/point_b_px" in detail


def test_precheck_api_reports_lab_camera_mock_temp_alignment_as_ready_without_device_access(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="dev_lab_camera_mock_temp")
    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", lambda: object())

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    items = {item["name"]: item for item in payload["items"]}
    assert items["real_offline_pixel_alignment"]["status"] == "ok"
    assert "origin=(512, 342)" in items["real_offline_pixel_alignment"]["detail"]
    assert "size=(2048, 1364)" in items["real_offline_pixel_alignment"]["detail"]
    assert "preview_display=816x544" in items["real_offline_pixel_alignment"]["detail"]
    assert "acquisition=mono8/50000us/12.0dB" in items["real_offline_pixel_alignment"]["detail"]
    assert "vision=dark_on_light/adaptive" in items["real_offline_pixel_alignment"]["detail"]
    assert "tracking=continue_on_invalid" in items["real_offline_pixel_alignment"]["detail"]
    assert "ab_points=formal target-contour point_a_px/point_b_px" in items["real_offline_pixel_alignment"]["detail"]


def test_precheck_api_fails_when_locked_profile_acquisition_drifts_from_offline_truth(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="dev_lab_camera_mock_temp")
    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", lambda: object())
    client.app.state.runtime_config.camera["setup_preview"]["exposure_us"] = 10_000
    client.app.state.runtime_config.camera["measurement"]["exposure_us"] = 10_000

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    items = {item["name"]: item for item in payload["items"]}
    assert items["real_offline_pixel_alignment"]["status"] == "fail"
    assert "setup_preview acquisition" in items["real_offline_pixel_alignment"]["detail"]
    assert "offline truth acquisition" in items["real_offline_pixel_alignment"]["detail"]


def test_precheck_api_fails_when_locked_profile_vision_drifts_from_offline_truth(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="dev_lab_camera_mock_temp")
    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", lambda: object())
    client.app.state.runtime_config.live.vision.edge_threshold = 8.0

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    items = {item["name"]: item for item in payload["items"]}
    assert items["real_offline_pixel_alignment"]["status"] == "fail"
    assert "vision settings" in items["real_offline_pixel_alignment"]["detail"]
    assert "offline truth vision" in items["real_offline_pixel_alignment"]["detail"]


def test_precheck_api_fails_when_locked_profile_tracking_policy_drifts_from_offline_truth(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="dev_lab_camera_mock_temp")
    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", lambda: object())
    client.app.state.runtime_config.live.run.stop_on_invalid_tracking = True

    response = client.get("/api/system/precheck")

    assert response.status_code == 200
    payload = response.json()
    items = {item["name"]: item for item in payload["items"]}
    assert items["real_offline_pixel_alignment"]["status"] == "fail"
    assert "tracking policy" in items["real_offline_pixel_alignment"]["detail"]
    assert "offline truth tracking policy" in items["real_offline_pixel_alignment"]["detail"]


def test_real_offline_alignment_api_returns_audit_without_device_access(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="dev_lab")

    response = client.get("/api/system/real-offline-alignment")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["real_profile"] == "dev_lab"
    assert payload["offline_profile"] == "dev_offline_capture"
    assert payload["hardware_access"] == "not_attempted"
    assert payload["pixel_contract"]["source_size_px"] == {"width": 2048, "height": 1364}
    assert payload["pixel_contract"]["preview_display_px"] == {"width": 816, "height": 544}
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
    assert payload["algorithm_contract"]["ab_selection"] == {
        "formal_point_source": "target_contour_boundary",
        "formal_point_fields": ["point_a_px", "point_b_px"],
        "projected_points_exposed_as_formal_ab": False,
        "angle_audit_selection_modes": ["directional_contour_max_chord"],
        "angles_checked": 12,
        "angle_step_deg": 30,
    }
    assert payload["offline_material"]["status"] in {"ok", "missing"}
    if payload["offline_material"]["status"] == "ok":
        assert payload["offline_material"]["frame_count"] == 5807
        assert payload["offline_material"]["source_size_px"] == {"width": 2048, "height": 1364}
        assert payload["offline_material"]["sample_frames_checked"] == 9
    assert payload["angles_checked"] == 12
    assert [item["angle_deg"] for item in payload["angle_results"]] == list(range(0, 360, 30))
    assert all(item["point_a_px"] for item in payload["angle_results"])
    assert all(item["point_b_px"] for item in payload["angle_results"])


def test_real_offline_alignment_api_uses_current_prod_win_profile_without_device_access(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    response = client.get("/api/system/real-offline-alignment")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["real_profile"] == "prod_win"
    assert payload["offline_profile"] == "dev_offline_capture"
    assert payload["hardware_access"] == "not_attempted"
    assert payload["angles_checked"] == 12


def test_real_offline_alignment_api_returns_failure_payload_without_device_access(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="dev_lab")

    def fail_audit(**_kwargs: object) -> dict[str, object]:
        raise RealOfflineAlignmentError("source pixels drifted")

    monkeypatch.setattr(profile_routes, "run_alignment_audit", fail_audit)

    response = client.get("/api/system/real-offline-alignment")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    assert payload["detail"] == "source pixels drifted"
    assert payload["hardware_access"] == "not_attempted"
    assert payload["angle_results"] == []


def test_real_camera_alignment_live_probe_api_returns_hardware_probe_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _make_client(tmp_path, profile="dev_lab_camera_mock_temp")

    def fake_probe(runtime_config) -> dict[str, object]:
        return {
            "status": "ok",
            "profile": runtime_config.profile,
            "hardware_access": "attempted",
            "profiles": [
                {
                    "profile_name": "setup_preview",
                    "status": "ok",
                    "expected_size_px": {"width": 2048, "height": 1364},
                    "actual_size_px": {"width": 2048, "height": 1364},
                    "expected_device_roi": {"x": 512, "y": 342, "width": 2048, "height": 1364},
                    "actual_device_roi": {"x": 512, "y": 342, "width": 2048, "height": 1364},
                    "acquisition": {"pixel_format": "mono8", "exposure_us": 50000, "gain_db": 12.0},
                    "frame_id": 1,
                    "timestamp_ms": 1000,
                    "source": "fake_setup_preview",
                    "detail": "setup_preview frame matches offline truth pixel contract.",
                },
                {
                    "profile_name": "measurement",
                    "status": "ok",
                    "expected_size_px": {"width": 2048, "height": 1364},
                    "actual_size_px": {"width": 2048, "height": 1364},
                    "expected_device_roi": {"x": 512, "y": 342, "width": 2048, "height": 1364},
                    "actual_device_roi": {"x": 512, "y": 342, "width": 2048, "height": 1364},
                    "acquisition": {"pixel_format": "mono8", "exposure_us": 50000, "gain_db": 12.0},
                    "frame_id": 2,
                    "timestamp_ms": 2000,
                    "source": "fake_measurement",
                    "detail": "measurement frame matches offline truth pixel contract.",
                },
            ],
            "detail": "Real camera setup_preview and measurement frames match the offline truth pixel contract.",
        }

    monkeypatch.setattr(profile_routes, "probe_real_camera_alignment", fake_probe)

    response = client.post("/api/system/real-offline-alignment/live-probe")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["profile"] == "dev_lab_camera_mock_temp"
    assert payload["hardware_access"] == "attempted"
    assert [item["profile_name"] for item in payload["profiles"]] == ["setup_preview", "measurement"]
    assert payload["profiles"][0]["actual_size_px"] == {"width": 2048, "height": 1364}
    assert payload["profiles"][1]["actual_size_px"] == {"width": 2048, "height": 1364}
