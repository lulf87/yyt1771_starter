from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    return TestClient(app)


def test_get_adjustment_returns_404_for_missing_session(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/api/session/missing-session/adjustment")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found: missing-session"}


def test_get_adjustment_returns_default_state_from_summary(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    session_id = client.post("/api/session/run-mock").json()["session_id"]

    response = client.get(f"/api/session/{session_id}/adjustment")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == session_id
    assert payload["auto_result"]["af95"] is not None
    assert payload["latest_result"] == payload["auto_result"]
    assert payload["draft"] is None
    assert payload["applied_versions"] == []


def test_put_adjustment_draft_saves_and_reads_back(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    session_id = client.post("/api/session/run-mock").json()["session_id"]

    save_response = client.put(
        f"/api/session/{session_id}/adjustment/draft",
        json={"overrides": {"af95": 43.1}, "reason": "visual confirmation"},
    )
    get_response = client.get(f"/api/session/{session_id}/adjustment")

    assert save_response.status_code == 200
    assert save_response.json()["draft"]["overrides"] == {"af95": 43.1}
    assert get_response.status_code == 200
    assert get_response.json()["draft"]["reason"] == "visual confirmation"


def test_apply_adjustment_promotes_draft_without_mutating_summary(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    summary = client.post("/api/session/run-mock").json()
    session_id = summary["session_id"]
    client.put(
        f"/api/session/{session_id}/adjustment/draft",
        json={"overrides": {"af95": 43.1}, "reason": "visual confirmation"},
    )

    apply_response = client.post(f"/api/session/{session_id}/adjustment/apply")
    summary_response = client.get(f"/api/session/{session_id}")

    assert apply_response.status_code == 200
    payload = apply_response.json()
    assert payload["draft"] is None
    assert payload["latest_result"]["af95"] == 43.1
    assert payload["applied_versions"][0]["version"] == 1
    assert summary_response.status_code == 200
    assert summary_response.json() == summary


def test_apply_adjustment_without_draft_returns_400(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    session_id = client.post("/api/session/run-mock").json()["session_id"]

    response = client.post(f"/api/session/{session_id}/adjustment/apply")

    assert response.status_code == 400
    assert response.json() == {"detail": f"No adjustment draft available for session: {session_id}"}


def test_put_adjustment_rejects_invalid_override_key(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    session_id = client.post("/api/session/run-mock").json()["session_id"]

    response = client.put(
        f"/api/session/{session_id}/adjustment/draft",
        json={"overrides": {"invalid_key": 1.0}, "reason": "invalid"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Unsupported adjustment keys: invalid_key"}


def test_apply_adjustment_increments_version_history(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    session_id = client.post("/api/session/run-mock").json()["session_id"]

    client.put(
        f"/api/session/{session_id}/adjustment/draft",
        json={"overrides": {"af95": 43.1}, "reason": "first"},
    )
    client.post(f"/api/session/{session_id}/adjustment/apply")
    client.put(
        f"/api/session/{session_id}/adjustment/draft",
        json={"overrides": {"af95": 44.2}, "reason": "second"},
    )

    response = client.post(f"/api/session/{session_id}/adjustment/apply")

    assert response.status_code == 200
    payload = response.json()
    assert [item["version"] for item in payload["applied_versions"]] == [1, 2]
    assert payload["latest_result"]["af95"] == 44.2
