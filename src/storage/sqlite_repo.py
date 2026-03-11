"""SQLite persistence for minimal offline session summaries."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SessionSummary:
    session_id: str
    state: str
    point_count: int
    af95: float | None
    created_at_ms: int
    meta: dict[str, Any] = field(default_factory=dict)


class SqliteSessionRepo:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._ensure_parent_dir()
        self.create_table()

    def create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_results (
                    session_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    point_count INTEGER NOT NULL,
                    af95 REAL NULL,
                    created_at_ms INTEGER NOT NULL
                )
                """
            )

    def save_summary(self, summary: SessionSummary) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO session_results (
                    session_id, state, point_count, af95, created_at_ms
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    summary.session_id,
                    summary.state,
                    summary.point_count,
                    summary.af95,
                    summary.created_at_ms,
                ),
            )

    def get_summary(self, session_id: str) -> SessionSummary | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, state, point_count, af95, created_at_ms
                FROM session_results
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return SessionSummary(
            session_id=row["session_id"],
            state=row["state"],
            point_count=row["point_count"],
            af95=row["af95"],
            created_at_ms=row["created_at_ms"],
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_parent_dir(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
