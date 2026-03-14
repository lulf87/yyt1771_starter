from pathlib import Path

from fastapi.testclient import TestClient

from src.workflow import precheck as precheck_module
from src.webapp.app import create_app


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
