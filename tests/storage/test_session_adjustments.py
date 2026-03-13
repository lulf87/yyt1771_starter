from src.storage.session_adjustments import SessionAdjustmentStore


def test_session_adjustment_store_returns_default_shape_when_missing(tmp_path) -> None:
    store = SessionAdjustmentStore(tmp_path / "artifacts")

    state = store.get_adjustment("session-001")

    assert state == {
        "session_id": "session-001",
        "draft": None,
        "applied_versions": [],
    }


def test_session_adjustment_store_round_trip(tmp_path) -> None:
    store = SessionAdjustmentStore(tmp_path / "artifacts")
    payload = {
        "session_id": "session-001",
        "draft": {
            "overrides": {"af95": 43.1},
            "reason": "visual confirmation",
            "updated_at_ms": 1730000000000,
        },
        "applied_versions": [
            {
                "version": 1,
                "result_before": {"af95": 42.3, "as_value": None, "af_value": None, "af_tan": None},
                "overrides": {"af95": 43.1},
                "result_after": {"af95": 43.1, "as_value": None, "af_value": None, "af_tan": None},
                "reason": "visual confirmation",
                "created_at_ms": 1730000001000,
            }
        ],
    }

    store.save_adjustment("session-001", payload)
    loaded = store.get_adjustment("session-001")

    assert loaded == payload
