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
    assert '/static/app.css?v=' in response.text
    assert '/static/app.js?v=' in response.text
    assert 'id="health-status"' in response.text
    assert 'id="profile-name"' in response.text
    assert 'id="live-run-id"' in response.text
    assert 'id="live-run-status"' in response.text
    assert 'id="live-run-preset-select"' in response.text
    assert 'id="live-preview-rate"' in response.text
    assert 'id="live-measurement-rate"' in response.text
    assert 'id="create-live-run-btn"' in response.text
    assert 'id="fetch-live-preview-btn"' in response.text
    assert 'id="start-live-preview-stream-btn"' in response.text
    assert 'id="stop-live-preview-stream-btn"' in response.text
    assert 'id="auto-detect-definition-btn"' in response.text
    assert 'id="save-live-definition-btn"' in response.text
    assert 'id="live-preview-img"' in response.text
    assert 'id="live-preview-stage"' in response.text
    assert 'id="live-preview-overlay"' in response.text
    assert 'id="live-target-temperature"' in response.text
    assert 'id="stop-live-run-btn"' in response.text
    assert 'id="draw-analysis-roi-btn"' in response.text
    assert 'id="draw-observation-window-btn"' in response.text
    assert 'id="rotate-observation-window-btn"' in response.text
    assert 'id="pick-point-a-btn"' in response.text
    assert 'id="pick-point-b-btn"' in response.text
    assert 'id="live-analysis-roi-width"' in response.text
    assert 'id="live-metric-box-angle"' in response.text
    assert 'id="live-point-a-x"' in response.text
    assert 'id="live-point-b-y"' in response.text
    assert 'id="precheck-status"' in response.text
    assert 'id="precheck-items"' in response.text
    assert 'id="refresh-precheck-btn"' in response.text
    assert 'id="probe-camera-btn"' in response.text
    assert 'id="probe-mode-select"' in response.text
    assert 'id="probe-allowed-models-input"' in response.text
    assert 'id="probe-serial-number-input"' in response.text
    assert 'id="probe-ip-input"' in response.text
    assert 'id="probe-local-override-hint"' in response.text
    assert "camera_sdk_runtime" in response.text
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
    assert "/api/runs" in response.text
    assert "/preview/frame" in response.text
    assert "/preview/stream" in response.text
    assert "/definition/auto" in response.text
    assert "/start" in response.text
    assert "/stop" in response.text
    assert "/telemetry" in response.text
    assert "/result" in response.text
    assert "live-run-preset-select" in response.text
    assert "live-preview-rate" in response.text
    assert "live-measurement-rate" in response.text
    assert "live-target-temperature" in response.text
    assert "stop-live-run-btn" in response.text
    assert "live-preview-img" in response.text
    assert "live-preview-overlay" in response.text
    assert "draw-analysis-roi-btn" in response.text
    assert "draw-observation-window-btn" in response.text
    assert "rotate-observation-window-btn" in response.text
    assert "start-live-preview-stream-btn" in response.text
    assert "stop-live-preview-stream-btn" in response.text
    assert "async function stopLivePreviewStream({ clearImage = false, silent = false } = {})" in response.text
    assert "async function loadFrozenPreviewFrame({ runId, cached = false })" in response.text
    assert '?cached=1' in response.text
    assert "probe-mode-select" in response.text
    assert "/api/session" in response.text
    assert "/api/session/run-mock" in response.text
    assert "/api/session/run-replay" in response.text
    assert "/api/session/${sessionId}/detail" in response.text
    assert "/workspace/" in response.text
    assert 'workspace-keyframe-card' in response.text
