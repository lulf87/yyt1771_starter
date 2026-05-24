import numpy as np

from src.storage.session_artifacts import SessionArtifactStore


def test_save_live_bundle_writes_expected_files_and_readers(tmp_path) -> None:
    store = SessionArtifactStore(tmp_path / "artifacts")

    session_dir = store.save_live_bundle(
        "run-001",
        definition={"point_a_px": {"x": 1, "y": 2}},
        definition_original={"point_a_px": {"x": 1, "y": 2}},
        definition_effective_local={"point_a_px": {"x": 11, "y": 22}},
        measurement_capture_plan={
            "effective_acquisition_roi": {"x": 12, "y": 24, "width": 160, "height": 128},
            "effective_local_origin_in_setup_preview_px": {"x": 100, "y": 120},
            "setup_to_effective_local_translation_px": {"dx": -100, "dy": -120},
        },
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
                "point_a_px": [12, 24],
                "point_b_px": [80, 24],
                "tracking_mode": "prior_gated_reacquire",
                "tracking_state": "accepted",
                "selection_mode": "roi_local_horizontal_boundary",
                "reason": None,
                "observation_selection_mode": None,
                "observation_reason": None,
                "component_area": 3210,
                "threshold_value": 118.5,
                "endpoint_jump_px": 3.0,
                "midpoint_drift_px": 1.5,
                "span_change_ratio": 0.02,
                "consecutive_misses": 0,
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
                "point_a_px": [13, 24],
                "point_b_px": [81, 24],
                "point_a_preview_px": [113, 144],
                "point_b_preview_px": [181, 144],
                "source_point_a_px": [10, 30],
                "source_point_b_px": [84, 18],
                "axis_point_a_px": [13, 24],
                "axis_point_b_px": [81, 24],
                "source_point_a_preview_px": [110, 150],
                "source_point_b_preview_px": [184, 138],
                "axis_point_a_preview_px": [113, 144],
                "axis_point_b_preview_px": [181, 144],
                "tracking_mode": "prior_gated_reacquire",
                "tracking_state": "holding_last_good",
                "selection_mode": "tracking_prior_hold",
                "reason": "endpoint_jump_exceeded",
                "observation_selection_mode": "roi_local_horizontal_boundary",
                "observation_reason": "quality_below_threshold",
                "component_area": 3200,
                "threshold_value": 120.0,
                "endpoint_jump_px": 15.0,
                "midpoint_drift_px": 9.0,
                "midpoint_along_shift_px": 7.0,
                "midpoint_lateral_drift_px": 2.0,
                "span_change_px": 5.5,
                "span_change_ratio": 0.08,
                "max_frame_span_jump_px": 6.0,
                "consecutive_misses": 1,
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
                "afas_dataset": "afas_dataset.json",
                "keyframes": ["keyframes/first.png"],
            },
        },
        events=[{"timestamp_ms": 1000, "type": "run_started", "payload": {}}],
        afas_dataset={
            "schema_version": "afas_postprocessing_dataset.v1",
            "session_id": "run-001",
            "active_channel": "Space1",
            "channel_map": {"Space1": {"values": [71.0, 72.5]}},
        },
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
    assert (session_dir / "definition_original.json").exists()
    assert (session_dir / "definition_effective_local.json").exists()
    assert (session_dir / "measurement_capture_plan.json").exists()
    assert (session_dir / "telemetry.csv").exists()
    assert (session_dir / "events.jsonl").exists()
    assert (session_dir / "result.json").exists()
    assert (session_dir / "detail.json").exists()
    assert (session_dir / "afas_dataset.json").exists()
    assert (session_dir / "keyframes" / "first.png").exists()

    assert store.get_detail("run-001")["source"] == "live_run"
    assert store.get_result("run-001")["af95"] == 74.0
    assert store.get_afas_dataset("run-001")["active_channel"] == "Space1"
    assert store.get_result("run-001")["rates"]["measurement_sample_hz"] == 5.0
    assert store.get_result("run-001")["artifacts"]["definition_original"] == "definition_original.json"
    assert store.get_result("run-001")["artifacts"]["definition_effective_local"] == "definition_effective_local.json"
    assert store.get_result("run-001")["artifacts"]["measurement_capture_plan"] == "measurement_capture_plan.json"
    telemetry = store.get_telemetry("run-001")
    assert telemetry is not None
    assert telemetry[-1]["space1_px"] == 72.5
    assert telemetry[-1]["sample_interval_ms"] == 200
    assert telemetry[-1]["frame_timestamp_ms"] == 1195
    assert telemetry[-1]["camera_resulting_fps"] == 14.86
    assert telemetry[-1]["point_a_px"] == [13, 24]
    assert telemetry[-1]["point_b_px"] == [81, 24]
    assert telemetry[-1]["point_a_preview_px"] == [113, 144]
    assert telemetry[-1]["point_b_preview_px"] == [181, 144]
    assert telemetry[-1]["source_point_a_px"] == [10, 30]
    assert telemetry[-1]["source_point_b_px"] == [84, 18]
    assert telemetry[-1]["axis_point_a_px"] == [13, 24]
    assert telemetry[-1]["axis_point_b_px"] == [81, 24]
    assert telemetry[-1]["source_point_a_preview_px"] == [110, 150]
    assert telemetry[-1]["source_point_b_preview_px"] == [184, 138]
    assert telemetry[-1]["axis_point_a_preview_px"] == [113, 144]
    assert telemetry[-1]["axis_point_b_preview_px"] == [181, 144]
    assert telemetry[-1]["tracking_mode"] == "prior_gated_reacquire"
    assert telemetry[-1]["tracking_state"] == "holding_last_good"
    assert telemetry[-1]["selection_mode"] == "tracking_prior_hold"
    assert telemetry[-1]["reason"] == "endpoint_jump_exceeded"
    assert telemetry[-1]["observation_selection_mode"] == "roi_local_horizontal_boundary"
    assert telemetry[-1]["observation_reason"] == "quality_below_threshold"
    assert telemetry[-1]["component_area"] == 3200
    assert telemetry[-1]["threshold_value"] == 120.0
    assert telemetry[-1]["endpoint_jump_px"] == 15.0
    assert telemetry[-1]["midpoint_drift_px"] == 9.0
    assert telemetry[-1]["midpoint_along_shift_px"] == 7.0
    assert telemetry[-1]["midpoint_lateral_drift_px"] == 2.0
    assert telemetry[-1]["span_change_px"] == 5.5
    assert telemetry[-1]["span_change_ratio"] == 0.08
    assert telemetry[-1]["max_frame_span_jump_px"] == 6.0
    assert telemetry[-1]["consecutive_misses"] == 1
    assert store.get_result("run-001")["warnings"] == [
        "measurement cadence below target: achieved 5.00 Hz < target 50.00 Hz"
    ]
    assert store.validate_live_bundle("run-001", expected_keyframes=["keyframes/first.png"]) == []


class _NativeKeyframeImage:
    def downsample_rows(self, *, max_width: int, max_height: int) -> list[list[int]]:
        return [[0, 64], [128, 255]]


def test_save_live_bundle_serializes_keyframe_images_in_detail_payload(tmp_path) -> None:
    store = SessionArtifactStore(tmp_path / "artifacts")

    store.save_live_bundle(
        "run-serializable",
        definition={"point_a_px": {"x": 1, "y": 2}},
        telemetry=[],
        detail={
            "session_id": "run-serializable",
            "source": "live_run",
            "points": [],
            "key_frames": [
                {
                    "label": "first",
                    "timestamp_ms": 1000,
                    "image": _NativeKeyframeImage(),
                    "feature_point_px": [1, 1],
                    "metric_raw": 71.0,
                }
            ],
            "point_count": 0,
            "af95": None,
        },
        result={
            "session_id": "run-serializable",
            "state": "completed",
            "analysis_engine": "afas",
            "channel_name": "Space1",
            "result_status": "ok",
            "result_reason": None,
            "result_detail": "",
            "af95": 74.0,
            "as_value": 41.2,
            "af_value": 57.8,
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
                "keyframes": ["keyframes/first.png"],
            },
        },
        events=[],
        afas_dataset={"schema_version": "afas_postprocessing_dataset.v1", "session_id": "run-serializable"},
        keyframes=[
            {
                "label": "first",
                "timestamp_ms": 1000,
                "image": _NativeKeyframeImage(),
                "feature_point_px": [1, 1],
                "metric_raw": 71.0,
            }
        ],
    )

    detail = store.get_detail("run-serializable")
    assert detail is not None
    assert detail["key_frames"][0]["label"] == "first"
    assert detail["key_frames"][0]["image"] == [[0, 64], [128, 255]]


def test_save_live_bundle_serializes_numpy_keyframe_images_in_detail_payload(tmp_path) -> None:
    store = SessionArtifactStore(tmp_path / "artifacts")
    keyframe = {
        "label": "first",
        "timestamp_ms": 1000,
        "image": np.array([[0, 64], [128, 255]], dtype=np.uint8),
        "feature_point_px": [1, 1],
        "metric_raw": 71.0,
    }

    store.save_live_bundle(
        "run-numpy-keyframe",
        definition={"point_a_px": {"x": 1, "y": 2}},
        telemetry=[],
        detail={
            "session_id": "run-numpy-keyframe",
            "source": "live_run",
            "points": [],
            "key_frames": [keyframe],
            "point_count": 0,
            "af95": None,
        },
        result={
            "session_id": "run-numpy-keyframe",
            "state": "completed",
            "analysis_engine": "afas",
            "channel_name": "Space1",
            "result_status": "ok",
            "result_reason": None,
            "result_detail": "",
            "af95": 74.0,
            "as_value": 41.2,
            "af_value": 57.8,
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
                "keyframes": ["keyframes/first.png"],
            },
        },
        events=[],
        afas_dataset={"schema_version": "afas_postprocessing_dataset.v1", "session_id": "run-numpy-keyframe"},
        keyframes=[keyframe],
    )

    detail = store.get_detail("run-numpy-keyframe")
    assert detail is not None
    assert detail["key_frames"][0]["image"] == [[0, 64], [128, 255]]
