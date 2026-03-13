import pytest

from src.storage.session_adjustments import SessionAdjustmentStore
from src.storage.sqlite_repo import SessionSummary, SqliteSessionRepo
from src.workflow.adjustments import AdjustmentService


def _make_service(tmp_path) -> AdjustmentService:
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    repo.save_summary(
        SessionSummary(
            session_id="session-001",
            state="completed",
            point_count=3,
            af95=42.3,
            created_at_ms=1730000000000,
        )
    )
    store = SessionAdjustmentStore(tmp_path / "artifacts")
    return AdjustmentService(repo=repo, store=store)


def test_get_adjustment_state_falls_back_to_auto_result(tmp_path) -> None:
    service = _make_service(tmp_path)

    state = service.get_adjustment_state("session-001")

    assert state["auto_result"]["af95"] == 42.3
    assert state["latest_result"] == state["auto_result"]
    assert state["draft"] is None
    assert state["applied_versions"] == []


def test_save_draft_persists_without_mutating_latest_result(tmp_path) -> None:
    service = _make_service(tmp_path)

    state = service.save_draft(
        session_id="session-001",
        overrides={"af95": 43.1},
        reason="visual confirmation",
    )

    assert state["draft"] is not None
    assert state["draft"]["overrides"] == {"af95": 43.1}
    assert state["latest_result"]["af95"] == 42.3
    assert state["applied_versions"] == []


def test_apply_draft_creates_version_and_updates_latest_result(tmp_path) -> None:
    service = _make_service(tmp_path)
    service.save_draft("session-001", overrides={"af95": 43.1}, reason="visual confirmation")

    state = service.apply_draft("session-001")

    assert state["draft"] is None
    assert state["latest_result"]["af95"] == 43.1
    assert len(state["applied_versions"]) == 1
    version = state["applied_versions"][0]
    assert version["version"] == 1
    assert version["result_before"]["af95"] == 42.3
    assert version["result_after"]["af95"] == 43.1


def test_apply_draft_increments_versions(tmp_path) -> None:
    service = _make_service(tmp_path)
    service.save_draft("session-001", overrides={"af95": 43.1}, reason="first")
    service.apply_draft("session-001")
    service.save_draft("session-001", overrides={"af95": 44.4}, reason="second")

    state = service.apply_draft("session-001")

    assert [version["version"] for version in state["applied_versions"]] == [1, 2]
    assert state["latest_result"]["af95"] == 44.4


def test_apply_without_draft_raises(tmp_path) -> None:
    service = _make_service(tmp_path)

    with pytest.raises(RuntimeError, match="No adjustment draft available"):
        service.apply_draft("session-001")


def test_save_draft_rejects_unknown_override_keys(tmp_path) -> None:
    service = _make_service(tmp_path)

    with pytest.raises(ValueError, match="Unsupported adjustment keys"):
        service.save_draft("session-001", overrides={"unknown": 1.0}, reason="invalid")
