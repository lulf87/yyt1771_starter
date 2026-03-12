from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
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


def test_list_sessions_returns_latest_first_and_default_history_shape(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    first = client.post("/api/session/run-mock")
    second = client.post("/api/session/run-mock")
    response = client.get("/api/session")

    assert first.status_code == 200
    assert second.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert list(payload) == ["items"]
    assert len(payload["items"]) == 2
    assert payload["items"][0]["session_id"] == second.json()["session_id"]
    assert payload["items"][1]["session_id"] == first.json()["session_id"]


def test_list_sessions_honors_limit_query_parameter(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    client.post("/api/session/run-mock")
    newest = client.post("/api/session/run-mock")
    response = client.get("/api/session", params={"limit": 1})

    assert response.status_code == 200
    assert response.json()["items"] == [newest.json()]


def test_run_replay_session_returns_summary_and_updates_history(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    replay_response = client.post("/api/session/run-replay")
    history_response = client.get("/api/session")

    assert replay_response.status_code == 200
    replay_payload = replay_response.json()
    assert replay_payload["session_id"].startswith("replay-")
    assert replay_payload["state"] == "completed"
    assert replay_payload["point_count"] == 3
    assert replay_payload["af95"] is not None
    assert history_response.status_code == 200
    assert history_response.json()["items"][0]["session_id"] == replay_payload["session_id"]


def test_get_session_detail_returns_replay_artifact(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    replay_response = client.post("/api/session/run-replay")
    session_id = replay_response.json()["session_id"]
    detail_response = client.get(f"/api/session/{session_id}/detail")

    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["session_id"] == session_id
    assert payload["source"] == "replay"
    assert payload["af95"] is not None
    assert payload["point_count"] == 3
    assert len(payload["points"]) == 3
    assert [frame["label"] for frame in payload["key_frames"]] == ["first", "middle", "last"]


def test_get_session_detail_returns_404_for_missing_artifact(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/api/session/replay-missing/detail")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session detail not found: replay-missing"}
