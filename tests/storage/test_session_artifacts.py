from pathlib import Path

from src.storage.session_artifacts import SessionArtifactStore


def test_session_artifact_store_round_trip(tmp_path: Path) -> None:
    store = SessionArtifactStore(tmp_path / "artifacts")
    payload = {
        "session_id": "replay-001",
        "source": "replay",
        "af95": 45.0,
        "point_count": 3,
        "points": [{"timestamp_ms": 1000, "celsius": 30.0, "metric_raw": 0.0, "metric_norm": 0.0, "quality": 0.9}],
        "key_frames": [{"label": "first", "timestamp_ms": 1000, "image": [[0, 255]], "feature_point_px": [1, 0], "metric_raw": 0.0}],
    }

    store.save_detail("replay-001", payload)
    loaded = store.get_detail("replay-001")

    assert loaded == payload


def test_session_artifact_store_returns_none_for_missing_detail(tmp_path: Path) -> None:
    store = SessionArtifactStore(tmp_path / "artifacts")

    assert store.get_detail("missing") is None


def test_session_artifact_store_persists_afas_outputs_and_updates_result_refs(tmp_path: Path) -> None:
    store = SessionArtifactStore(tmp_path / "artifacts")
    session_dir = store.save_live_bundle(
        "run-afas",
        definition={"point_a_px": {"x": 1, "y": 2}},
        telemetry=[],
        detail={"session_id": "run-afas", "source": "live_run", "points": [], "key_frames": [], "point_count": 0, "af95": None},
        result={
            "session_id": "run-afas",
            "state": "completed",
            "analysis_engine": "afas",
            "channel_name": "Space1",
            "result_status": "ok",
            "result_reason": None,
            "result_detail": "",
            "af95": 50.0,
            "as_value": 40.0,
            "af_value": 60.0,
            "point_count": 0,
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
        },
        events=[],
        afas_dataset={"schema_version": "afas_postprocessing_dataset.v1", "session_id": "run-afas"},
    )

    analysis_path = store.save_afas_analysis(
        "run-afas",
        {"session_id": "run-afas", "active_channel": "Space1", "analysis": {"schema_version": "afas_postprocessing_analysis.v1"}},
    )
    plot_path = store.save_afas_plot("run-afas", b"\x89PNG\r\n\x1a\nartifact")
    report_path = store.save_afas_report("run-afas", b"PKartifact")

    assert analysis_path == session_dir / "afas_analysis.json"
    assert plot_path == session_dir / "afas_plot.png"
    assert report_path == session_dir / "afas_report.xlsx"
    assert store.get_afas_analysis("run-afas")["active_channel"] == "Space1"

    result = store.get_result("run-afas")
    assert result is not None
    assert result["artifacts"]["afas_analysis"] == "afas_analysis.json"
    assert result["artifacts"]["afas_plot"] == "afas_plot.png"
    assert result["artifacts"]["afas_report"] == "afas_report.xlsx"
    assert store.validate_live_bundle("run-afas") == []
