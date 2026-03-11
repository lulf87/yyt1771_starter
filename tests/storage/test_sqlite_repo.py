from pathlib import Path

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
