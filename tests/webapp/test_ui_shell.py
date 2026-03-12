from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "ui-shell.db")
    return TestClient(app)


def test_ui_shell_route_returns_html_with_expected_hooks(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert "YYT1771 Web Console" in response.text
    assert 'id="health-status"' in response.text
    assert 'id="profile-name"' in response.text
    assert 'id="run-mock-btn"' in response.text
    assert 'id="session-result"' in response.text


def test_static_app_js_is_served(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "/api/system/profile" in response.text
    assert "/api/session/run-mock" in response.text
