from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
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
    assert items["camera_adapter"]["status"] == "pending"
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
