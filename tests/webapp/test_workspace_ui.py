from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "workspace.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    return TestClient(app)


def test_workspace_route_returns_html_for_existing_session(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    session_id = client.post("/api/session/run-replay").json()["session_id"]

    response = client.get(f"/workspace/{session_id}")

    assert response.status_code == 200
    assert 'id="workspace-shell"' in response.text
    assert 'id="workspace-stepper"' in response.text
    assert 'id="workspace-main"' in response.text
    assert 'id="workspace-sidepanel"' in response.text
    assert 'id="workspace-curve"' in response.text
    assert 'id="workspace-curve-title"' in response.text
    assert 'id="workspace-active-point"' in response.text
    assert 'id="workspace-keyframes"' in response.text
    assert 'data-testid="workspace-step"' in response.text
    assert 'data-testid="workspace-step-status"' in response.text
    assert 'id="workspace-current-stage"' in response.text
    assert 'id="workspace-stage-description"' in response.text
    assert 'id="workspace-af95"' in response.text
    assert 'id="workspace-source"' in response.text
    assert 'id="workspace-keyframe-count"' in response.text
    assert 'id="workspace-active-selection"' in response.text
    assert 'id="workspace-active-label"' in response.text
    assert 'id="workspace-active-timestamp"' in response.text
    assert 'id="workspace-active-metric-raw"' in response.text
    assert 'id="workspace-active-feature-point"' in response.text
    assert 'id="workspace-adjustment-preview"' in response.text
    assert 'id="workspace-adjustment-basis"' in response.text
    assert 'id="workspace-adjustment-context"' in response.text
    assert 'id="workspace-adjustment-controls"' in response.text
    assert 'id="workspace-adjustment-source"' in response.text
    assert 'id="workspace-adjustment-point-count"' in response.text
    assert 'id="workspace-adjustment-keyframe-count"' in response.text
    assert 'id="workspace-adjustment-af95"' in response.text
    assert 'id="workspace-adjustment-roi"' in response.text
    assert 'id="workspace-adjustment-feature-point"' in response.text
    assert 'id="workspace-adjustment-baseline"' in response.text
    assert 'id="workspace-adjustment-quality"' in response.text
    assert 'id="workspace-adjustment-threshold"' in response.text
    assert 'id="workspace-adjustment-component-area"' in response.text
    assert 'id="workspace-adjustment-coming-soon"' in response.text
    assert 'id="workspace-stage-card"' in response.text
    assert 'id="workspace-session-summary-card"' in response.text
    assert 'id="workspace-active-selection"' in response.text
    assert 'id="workspace-detail-summary-card"' in response.text
    assert 'id="workspace-actions-card"' in response.text
    assert 'id="workspace-refresh-btn"' in response.text
    assert session_id in response.text


def test_workspace_route_keeps_empty_state_when_detail_is_missing(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    session_id = client.post("/api/session/run-mock").json()["session_id"]

    response = client.get(f"/workspace/{session_id}")

    assert response.status_code == 200
    assert "No replay detail available." in response.text
    assert 'id="workspace-detail-status"' in response.text
    assert 'id="workspace-active-selection"' in response.text
    assert 'id="workspace-adjustment-preview"' in response.text
    assert 'id="workspace-adjustment-active-summary"' in response.text
    assert "Automatic analysis basis will appear here when detail data is available." in response.text
    assert "Coming soon. Read-only in current phase." in response.text
    assert 'disabled>' in response.text


def test_workspace_static_js_contains_selection_linking_hooks(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "setActiveWorkspacePoint" in response.text
    assert "workspace-active-label" in response.text
    assert "workspace-active-point" in response.text
    assert "updateWorkspaceAdjustmentPreview" in response.text
    assert "workspace-adjustment-source" in response.text
    assert "workspace-step--upcoming" in response.text


def test_workspace_route_returns_404_for_missing_session(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/workspace/missing-session")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found: missing-session"}
