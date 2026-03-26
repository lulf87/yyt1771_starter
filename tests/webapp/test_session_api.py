import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app


def _make_client(tmp_path: Path) -> TestClient:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    return TestClient(app)


def _seed_afas_dataset(client: TestClient, session_id: str) -> None:
    artifact_dir = Path(client.app.state.runtime_config.storage["artifact_dir"])
    session_dir = artifact_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    dataset = {
        "schema_version": "afas_postprocessing_dataset.v1",
        "session_id": session_id,
        "active_channel": "Space1",
        "channel_map": {
            "Space1": {
                "temperature_celsius": [25.0, 35.0, 45.0, 55.0, 65.0, 75.0, 85.0, 95.0, 105.0, 115.0],
                "values": [10.0, 10.4, 10.8, 11.6, 13.5, 18.0, 24.0, 28.4, 30.0, 30.5],
                "timestamps_ms": [1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400, 2600, 2800],
                "metric_norm": [0.0, 0.02, 0.05, 0.11, 0.26, 0.55, 0.82, 0.94, 0.99, 1.0],
                "quality": [0.95] * 10,
                "point_a_px": [[20, 50]] * 10,
                "point_b_px": [[100, 50]] * 10,
            }
        },
        "preprocessing_defaults": {
            "group_by_temperature": True,
            "outlier_window": 11,
            "outlier_threshold": 5.0,
            "outlier_max_iterations": 3,
            "savgol_window_length": 5,
            "savgol_polyorder": 2,
        },
        "analysis_defaults": {
            "low_range_celsius": [25.0, 45.0],
            "high_range_celsius": [95.0, 115.0],
            "tangent_offset": 0,
        },
    }
    (session_dir / "afas_dataset.json").write_text(json.dumps(dataset), encoding="utf-8")


def _seed_afas_result(session_dir: Path, session_id: str) -> None:
    result = {
        "session_id": session_id,
        "state": "completed",
        "analysis_engine": "afas",
        "channel_name": "Space1",
        "result_status": "ok",
        "result_reason": None,
        "result_detail": "",
        "af95": 82.5,
        "as_value": 44.0,
        "af_value": 71.0,
        "point_count": 10,
        "capture_mode": "post_run_review",
        "rates": {},
        "measurement_profile": {},
        "warnings": [],
        "artifacts": {
            "definition": "definition.json",
            "telemetry": "telemetry.csv",
            "events": "events.jsonl",
            "detail": "detail.json",
            "result": "result.json",
            "afas_dataset": "afas_dataset.json",
            "afas_analysis": None,
            "afas_plot": None,
            "afas_report": None,
            "keyframes": [],
        },
    }
    (session_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")


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


def test_post_session_afas_analysis_returns_preprocessing_and_tangent_payload(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    _seed_afas_dataset(client, "session-afas")

    response = client.post("/api/session/session-afas/afas/analysis", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-afas"
    assert payload["active_channel"] == "Space1"
    assert payload["available_channels"] == ["Space1"]
    assert payload["overview"][0]["channel_name"] == "Space1"
    assert payload["preprocessing"]["schema_version"] == "afas_preprocessing_result.v1"
    assert payload["analysis"]["schema_version"] == "afas_postprocessing_analysis.v1"
    assert payload["analysis"]["fit"]["low_baseline"]["range_celsius"] == [25.0, 45.0]
    assert payload["analysis"]["result"]["As"] is not None
    artifact_path = tmp_path / "artifacts" / "session-afas" / "afas_analysis.json"
    assert artifact_path.exists()
    persisted = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert persisted["active_channel"] == "Space1"


def test_post_session_afas_analysis_accepts_parameter_overrides(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    _seed_afas_dataset(client, "session-afas")

    response = client.post(
        "/api/session/session-afas/afas/analysis",
        json={
            "savgol_window_length": 7,
            "savgol_polyorder": 3,
            "low_range_celsius": [25.0, 55.0],
            "high_range_celsius": [85.0, 115.0],
            "tangent_offset": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["preprocessing"]["parameters"]["savgol_window_length"] == 7
    assert payload["preprocessing"]["parameters"]["savgol_polyorder"] == 3
    assert payload["analysis"]["parameters"]["resolved_low_range_celsius"] == [25.0, 55.0]
    assert payload["analysis"]["parameters"]["resolved_high_range_celsius"] == [85.0, 115.0]
    assert payload["analysis"]["parameters"]["tangent_offset"] == 1


def test_post_session_afas_analysis_returns_404_when_dataset_is_missing(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.post("/api/session/missing-session/afas/analysis", json={})

    assert response.status_code == 404
    assert response.json() == {"detail": "AFAS dataset not found: missing-session"}


def test_post_session_afas_export_png_returns_attachment(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    _seed_afas_dataset(client, "session-afas")
    session_dir = tmp_path / "artifacts" / "session-afas"
    _seed_afas_result(session_dir, "session-afas")

    response = client.post("/api/session/session-afas/afas/export.png", json={})

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert "attachment;" in response.headers["content-disposition"]
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert (session_dir / "afas_analysis.json").exists()
    assert (session_dir / "afas_plot.png").exists()
    result = json.loads((session_dir / "result.json").read_text(encoding="utf-8"))
    assert result["artifacts"]["afas_analysis"] == "afas_analysis.json"
    assert result["artifacts"]["afas_plot"] == "afas_plot.png"
    assert result["artifacts"]["afas_report"] is None


def test_post_session_afas_export_excel_returns_attachment(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    _seed_afas_dataset(client, "session-afas")
    session_dir = tmp_path / "artifacts" / "session-afas"
    _seed_afas_result(session_dir, "session-afas")

    response = client.post("/api/session/session-afas/afas/report.xlsx", json={})

    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment;" in response.headers["content-disposition"]
    assert response.content[:2] == b"PK"
    assert (session_dir / "afas_analysis.json").exists()
    assert (session_dir / "afas_report.xlsx").exists()
    result = json.loads((session_dir / "result.json").read_text(encoding="utf-8"))
    assert result["artifacts"]["afas_analysis"] == "afas_analysis.json"
    assert result["artifacts"]["afas_report"] == "afas_report.xlsx"
    assert result["artifacts"]["afas_plot"] is None
