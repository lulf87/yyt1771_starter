from pathlib import Path

import pytest

from src.storage.sqlite_repo import SessionSummary, SqliteSessionRepo


def test_sqlite_repo_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "sessions.db"
    repo = SqliteSessionRepo(db_path)
    summary = SessionSummary(
        session_id="demo-001",
        state="completed",
        point_count=3,
        af95=47.5,
        created_at_ms=123456,
    )

    repo.save_summary(summary)
    loaded = repo.get_summary("demo-001")

    assert loaded == summary


def test_sqlite_repo_list_summaries_returns_latest_first_and_honors_limit(tmp_path: Path) -> None:
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    repo.save_summary(
        SessionSummary(
            session_id="demo-001",
            state="completed",
            point_count=1,
            af95=41.0,
            created_at_ms=100,
        )
    )
    repo.save_summary(
        SessionSummary(
            session_id="demo-002",
            state="completed",
            point_count=2,
            af95=42.0,
            created_at_ms=200,
        )
    )
    repo.save_summary(
        SessionSummary(
            session_id="demo-003",
            state="completed",
            point_count=3,
            af95=43.0,
            created_at_ms=300,
        )
    )

    summaries = repo.list_summaries(limit=2)

    assert [summary.session_id for summary in summaries] == ["demo-003", "demo-002"]


def test_sqlite_repo_list_summaries_rejects_non_positive_limit(tmp_path: Path) -> None:
    repo = SqliteSessionRepo(tmp_path / "sessions.db")

    with pytest.raises(ValueError, match="limit must be greater than zero"):
        repo.list_summaries(limit=0)
