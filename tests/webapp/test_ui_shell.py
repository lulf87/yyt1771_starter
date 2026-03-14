from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "ui-shell.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    return TestClient(app)


def test_ui_shell_route_returns_html_with_expected_hooks(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert "YYT1771 Web Console" in response.text
    assert 'id="health-status"' in response.text
    assert 'id="profile-name"' in response.text
    assert 'id="precheck-status"' in response.text
    assert 'id="precheck-items"' in response.text
    assert 'id="refresh-precheck-btn"' in response.text
    assert 'id="probe-camera-btn"' in response.text
    assert 'id="camera-probe-result"' in response.text
    assert 'id="run-mock-btn"' in response.text
    assert 'id="run-replay-btn"' in response.text
    assert 'id="session-workspace-link"' in response.text
    assert 'id="session-result"' in response.text
    assert 'id="recent-sessions"' in response.text
    assert 'id="detail-af95"' in response.text
    assert 'id="detail-point-count"' in response.text
    assert 'id="detail-curve"' in response.text
    assert 'id="detail-key-frames"' in response.text


def test_static_app_js_is_served(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "/api/system/profile" in response.text
    assert "/api/system/precheck" in response.text
    assert "/api/system/camera/probe" in response.text
    assert "/api/session" in response.text
    assert "/api/session/run-mock" in response.text
    assert "/api/session/run-replay" in response.text
    assert "/api/session/${sessionId}/detail" in response.text
    assert "/workspace/" in response.text
    assert 'workspace-keyframe-card' in response.text
