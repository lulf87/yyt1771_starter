from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    return TestClient(app)


def test_run_mock_session_returns_summary_and_persists_result(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.post("/api/session/run-mock")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"]
    assert payload["state"] == "completed"
    assert payload["point_count"] > 0
    assert payload["af95"] is not None
    assert (tmp_path / "sessions.db").exists()


def test_get_session_returns_saved_summary(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    create_response = client.post("/api/session/run-mock")
    session_id = create_response.json()["session_id"]

    response = client.get(f"/api/session/{session_id}")

    assert response.status_code == 200
    assert response.json() == create_response.json()


def test_get_session_returns_404_for_missing_summary(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/api/session/missing-session")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found: missing-session"}
