from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "workspace.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    return TestClient(app)


def _sample_afas_dataset(session_id: str) -> dict[str, object]:
    return {
        "schema_version": "afas_postprocessing_dataset.v1",
        "session_id": session_id,
        "active_channel": "Space1",
        "channel_map": {
            "Space1": {
                "temperature_celsius": [25.0, 35.0, 45.0, 55.0, 65.0, 75.0, 85.0, 95.0, 105.0, 115.0],
                "values": [10.0, 10.4, 10.8, 11.6, 13.5, 18.0, 24.0, 28.4, 30.0, 30.5],
                "timestamps_ms": [1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400, 2600, 2800],
            }
        },
    }


def test_workspace_route_returns_html_for_existing_session(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    session_id = client.post("/api/session/run-replay").json()["session_id"]

    response = client.get(f"/workspace/{session_id}")

    assert response.status_code == 200
    assert "分析工作台" in response.text
    assert "数据与会话" in response.text
    assert "分析设置" in response.text
    assert "返回首页" in response.text
    assert "导入数据" in response.text
    assert "返回首页导入数据" not in response.text
    assert "切换样本或导入新数据时回到首页，当前页面只保留分析相关操作。" not in response.text
    assert "选择 afas_dataset.json 后会直接打开新的分析页面。" not in response.text
    assert "路径导轨" in response.text
    assert "设备就绪" in response.text
    assert "AFAS 出点 / 导出" in response.text
    assert "Replay 上下文" in response.text
    assert "通道选择" in response.text
    assert "分析参数" in response.text
    assert "分析结果" in response.text
    assert 'class="panel workspace-topbar-entry-card"' in response.text
    assert "保持 session 轻量可见，把 AFAS 分析、参数和导出放回主工作面。" not in response.text
    assert 'data-language-toggle="zh"' in response.text
    assert 'data-language-toggle="en"' in response.text
    assert 'data-afas-available="0"' in response.text
    assert '/static/app.css?v=' in response.text
    assert '/static/app.js?v=' in response.text
    assert 'id="workspace-shell"' in response.text
    assert 'id="workspace-stepper"' in response.text
    assert 'id="workspace-main"' in response.text
    assert 'id="workspace-sidepanel"' in response.text
    assert 'id="workspace-curve"' in response.text
    assert 'id="workspace-curve-title"' in response.text
    assert 'id="workspace-active-point"' in response.text
    assert 'id="workspace-afas-panel"' in response.text
    assert 'id="workspace-afas-run-btn"' in response.text
    assert 'id="workspace-afas-export-png-btn"' in response.text
    assert 'id="workspace-afas-export-xlsx-btn"' in response.text
    assert 'id="workspace-afas-channel"' in response.text
    assert 'id="workspace-afas-savgol-window"' in response.text
    assert 'id="workspace-afas-low-start"' in response.text
    assert 'id="workspace-afas-high-end"' in response.text
    assert 'id="workspace-afas-overview-chart"' in response.text
    assert 'id="workspace-afas-analysis-chart"' in response.text
    assert 'id="workspace-afas-result-status"' in response.text
    assert 'id="workspace-afas-result-delta"' in response.text
    assert 'id="workspace-afas-parameter-summary"' in response.text
    assert 'id="workspace-afas-result-hint"' in response.text
    assert 'id="workspace-afas-warning-list"' in response.text
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
    assert 'id="workspace-adjustment-auto-result"' in response.text
    assert 'id="workspace-adjustment-latest-result"' in response.text
    assert 'id="workspace-adjustment-draft-editor"' in response.text
    assert 'id="workspace-adjustment-notes"' in response.text
    assert 'id="workspace-adjustment-source"' in response.text
    assert 'id="workspace-adjustment-point-count"' in response.text
    assert 'id="workspace-adjustment-keyframe-count"' in response.text
    assert 'id="workspace-adjustment-af95"' in response.text
    assert 'id="adjustment-auto-af95"' in response.text
    assert 'id="adjustment-auto-source"' in response.text
    assert 'id="adjustment-latest-af95"' in response.text
    assert 'id="adjustment-latest-source"' in response.text
    assert 'id="adjustment-latest-version"' in response.text
    assert 'id="adjustment-draft-af95"' in response.text
    assert 'id="adjustment-draft-reason"' in response.text
    assert 'id="adjustment-save-draft-btn"' in response.text
    assert 'id="adjustment-apply-btn"' in response.text
    assert 'id="adjustment-draft-status"' in response.text
    assert 'id="workspace-adjustment-roi"' in response.text
    assert 'id="workspace-adjustment-feature-point"' in response.text
    assert 'id="workspace-adjustment-baseline"' in response.text
    assert 'id="workspace-adjustment-quality"' in response.text
    assert 'id="workspace-adjustment-threshold"' in response.text
    assert 'id="workspace-adjustment-component-area"' in response.text
    assert 'id="workspace-adjustment-coming-soon"' in response.text
    assert 'id="workspace-adjustment-status-card"' in response.text
    assert 'id="workspace-adjustment-history-card"' in response.text
    assert 'id="adjustment-has-draft"' in response.text
    assert 'id="adjustment-applied-count"' in response.text
    assert 'id="adjustment-is-manual"' in response.text
    assert 'id="adjustment-version-history"' in response.text
    assert "查看版本时间线" in response.text
    assert 'id="workspace-stage-card"' in response.text
    assert 'id="workspace-session-summary-card"' in response.text
    assert 'id="workspace-active-selection"' in response.text
    assert 'id="workspace-detail-summary-card"' in response.text
    assert 'id="workspace-actions-card"' in response.text
    assert 'id="workspace-refresh-btn"' not in response.text
    assert 'id="workspace-import-afas-dataset-btn"' in response.text
    assert 'id="workspace-import-afas-dataset-file"' in response.text
    assert "打开选择诊断" in response.text
    assert "打开工程链接" in response.text
    assert "打开 Adjustment、版本与追溯" in response.text
    assert "打开流程与工程信息" in response.text
    assert session_id in response.text


def test_workspace_route_marks_imported_afas_session_as_available(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    session_id = client.post("/api/session/import-afas-dataset", json=_sample_afas_dataset("import-workspace")).json()[
        "session_id"
    ]

    response = client.get(f"/workspace/{session_id}")

    assert response.status_code == 200
    assert 'data-afas-available="1"' in response.text
    assert session_id in response.text


def test_workspace_route_keeps_empty_state_when_detail_is_missing(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    session_id = client.post("/api/session/run-mock").json()["session_id"]

    response = client.get(f"/workspace/{session_id}")

    assert response.status_code == 200
    assert "暂无 replay detail。" in response.text
    assert "AFAS 分析尚未加载。" in response.text
    assert 'id="workspace-detail-status"' in response.text
    assert 'id="workspace-active-selection"' in response.text
    assert 'id="workspace-adjustment-preview"' in response.text
    assert 'id="workspace-adjustment-active-summary"' in response.text
    assert "detail 数据可用后，这里会显示自动分析依据。" in response.text
    assert "即将支持；当前阶段只读。" in response.text
    assert "尚未加载草稿。" in response.text
    assert 'disabled>' in response.text


def test_workspace_static_js_contains_selection_linking_hooks(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "setActiveWorkspacePoint" in response.text
    assert "loadWorkspaceAfasAnalysis" in response.text
    assert "exportWorkspaceAfasArtifact" in response.text
    assert "/afas/analysis" in response.text
    assert "export.png" in response.text
    assert "report.xlsx" in response.text
    assert "workspace-afas-run-btn" in response.text
    assert "workspace-afas-overview-chart" in response.text
    assert "workspace-active-label" in response.text
    assert "workspace-active-point" in response.text
    assert "updateWorkspaceAdjustmentPreview" in response.text
    assert "workspace-adjustment-source" in response.text
    assert "workspace-step--upcoming" in response.text
    assert "/api/session/${sessionId}/adjustment" in response.text
    assert "/adjustment/draft" in response.text
    assert "/adjustment/apply" in response.text
    assert "document.body.dataset.afasAvailable" in response.text
    assert "syncWorkspaceAfasAvailability" in response.text
    assert "renderAdjustmentState" in response.text


def test_workspace_route_returns_404_for_missing_session(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/workspace/missing-session")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found: missing-session"}
