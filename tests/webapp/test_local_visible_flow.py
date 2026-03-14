from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "visible-flow.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    return TestClient(app)


def test_local_visible_flow_from_home_to_workspace(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    home_response = client.get("/")
    health_response = client.get("/health")
    profile_response = client.get("/api/system/profile")
    precheck_response = client.get("/api/system/precheck")

    assert home_response.status_code == 200
    assert "YYT1771 Web Console" in home_response.text
    assert "Run Replay Session" in home_response.text
    assert "Open Workspace" in home_response.text
    assert health_response.status_code == 200
    assert profile_response.status_code == 200
    assert precheck_response.status_code == 200

    replay_response = client.post("/api/session/run-replay")

    assert replay_response.status_code == 200
    replay_payload = replay_response.json()
    session_id = replay_payload["session_id"]
    assert session_id
    assert replay_payload["state"] == "completed"
    assert replay_payload["point_count"] > 0

    workspace_response = client.get(f"/workspace/{session_id}")

    assert workspace_response.status_code == 200
    assert "Replay Curve" in workspace_response.text
    assert "Key Frames" in workspace_response.text
    assert "Adjustment MVP" in workspace_response.text
    assert "Version History" in workspace_response.text

    detail_response = client.get(f"/api/session/{session_id}/detail")

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["session_id"] == session_id
    assert detail_payload["source"] == "replay"
    assert detail_payload["point_count"] > 0
