from src.storage.session_artifacts import SessionArtifactStore


def test_save_live_bundle_writes_expected_files_and_readers(tmp_path) -> None:
    store = SessionArtifactStore(tmp_path / "artifacts")

    session_dir = store.save_live_bundle(
        "run-001",
        definition={"point_a_px": {"x": 1, "y": 2}},
        telemetry=[
            {
                "timestamp_ms": 1000,
                "sample_index": 0,
                "frame_id": 1,
                "frame_timestamp_ms": 995,
                "temp_timestamp_ms": 1000,
                "metric_timestamp_ms": 1000,
                "temperature_celsius": 25.0,
                "space1_px": 71.0,
                "tracking_quality": 0.98,
            },
            {
                "timestamp_ms": 1200,
                "sample_index": 1,
                "sample_interval_ms": 200,
                "frame_id": 2,
                "frame_timestamp_ms": 1195,
                "temp_timestamp_ms": 1200,
                "metric_timestamp_ms": 1200,
                "camera_resulting_fps": 14.86,
                "temperature_celsius": 35.0,
                "space1_px": 72.5,
                "tracking_quality": 0.97,
            },
        ],
        detail={"session_id": "run-001", "source": "live_run", "points": [], "key_frames": [], "point_count": 0, "af95": None},
        result={
            "session_id": "run-001",
            "state": "completed",
            "analysis_engine": "afas",
            "channel_name": "Space1",
            "result_status": "ok",
            "result_reason": None,
            "result_detail": "",
            "af95": 74.0,
            "as_value": 41.2,
            "af_value": 57.8,
            "point_count": 2,
            "capture_mode": "post_run_review",
            "rates": {
                "camera_resulting_fps": None,
                "preview_display_fps": None,
                "measurement_sample_hz": 5.0,
                "artifact_capture_hz": 5.0,
                "dropped_frame_count": 0,
            },
            "measurement_profile": {
                "acquisition_roi": {"x": 0, "y": 0, "width": 96, "height": 64},
                "decimation": None,
                "binning": None,
                "exposure_us": 10000,
            },
            "warnings": ["measurement cadence below target: achieved 5.00 Hz < target 50.00 Hz"],
            "artifacts": {
                "definition": "definition.json",
                "telemetry": "telemetry.csv",
                "events": "events.jsonl",
                "detail": "detail.json",
                "result": "result.json",
                "keyframes": ["keyframes/first.png"],
            },
        },
        events=[{"timestamp_ms": 1000, "type": "run_started", "payload": {}}],
        keyframes=[
            {
                "label": "first",
                "timestamp_ms": 1000,
                "image": [[0, 32], [64, 96]],
                "feature_point_px": [1, 1],
                "metric_raw": 71.0,
            }
        ],
    )

    assert session_dir == tmp_path / "artifacts" / "run-001"
    assert (session_dir / "definition.json").exists()
    assert (session_dir / "telemetry.csv").exists()
    assert (session_dir / "events.jsonl").exists()
    assert (session_dir / "result.json").exists()
    assert (session_dir / "detail.json").exists()
    assert (session_dir / "keyframes" / "first.png").exists()

    assert store.get_detail("run-001")["source"] == "live_run"
    assert store.get_result("run-001")["af95"] == 74.0
    assert store.get_result("run-001")["rates"]["measurement_sample_hz"] == 5.0
    telemetry = store.get_telemetry("run-001")
    assert telemetry is not None
    assert telemetry[-1]["space1_px"] == 72.5
    assert telemetry[-1]["sample_interval_ms"] == 200
    assert telemetry[-1]["frame_timestamp_ms"] == 1195
    assert telemetry[-1]["camera_resulting_fps"] == 14.86
    assert store.get_result("run-001")["warnings"] == [
        "measurement cadence below target: achieved 5.00 Hz < target 50.00 Hz"
    ]
    assert store.validate_live_bundle("run-001", expected_keyframes=["keyframes/first.png"]) == []
