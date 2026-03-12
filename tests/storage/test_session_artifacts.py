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
