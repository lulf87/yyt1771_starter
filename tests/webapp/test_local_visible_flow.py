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
    assert "实时预览" in home_response.text
    assert "ROI 框选" in home_response.text
    assert "查看ROI参数" in home_response.text
    assert "更多工具与诊断" in home_response.text
    assert "保存数据" in home_response.text
    assert "进入分析" in home_response.text
    assert "启动与控制驾驶舱" not in home_response.text
    assert "操作路径" not in home_response.text
    assert "当前任务" not in home_response.text
    assert "保存定义" not in home_response.text
    assert "探测相机" in home_response.text
    assert "运行 Replay 会话" in home_response.text
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
    assert "分析工作台" in workspace_response.text
    assert "数据与会话" in workspace_response.text
    assert "分析设置" in workspace_response.text
    assert "返回首页" in workspace_response.text
    assert "导入数据" in workspace_response.text
    assert "返回首页导入数据" not in workspace_response.text
    assert "路径导轨" in workspace_response.text
    assert "Replay 上下文" in workspace_response.text
    assert "通道选择" in workspace_response.text
    assert "分析参数" in workspace_response.text
    assert "分析结果" in workspace_response.text
    assert "打开 Adjustment、版本与追溯" in workspace_response.text
    assert "打开流程与工程信息" in workspace_response.text

    detail_response = client.get(f"/api/session/{session_id}/detail")

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["session_id"] == session_id
    assert detail_payload["source"] == "replay"
    assert detail_payload["point_count"] > 0
