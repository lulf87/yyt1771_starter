"""Minimal offline session orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from src.core.enums import SessionState
from src.core.models import SessionRecord, ShapeMetric, SyncPoint, TempReading
from src.curve.af95 import estimate_af95
from src.storage.sqlite_repo import SessionSummary


class SessionSummaryRepo(Protocol):
    def save_summary(self, summary: SessionSummary) -> None:
        """Persist one session summary."""


@dataclass(slots=True)
class WorkflowSession:
    record: SessionRecord


def build_mock_sync_points() -> list[SyncPoint]:
    """Return a deterministic offline curve for mock session runs."""

    return [
        SyncPoint(
            timestamp_ms=1_000,
            temp=TempReading(timestamp_ms=1_000, celsius=30.0, source="workflow_mock"),
            metric=ShapeMetric(timestamp_ms=1_000, metric_raw=0.0, metric_name="end_displacement", quality=1.0),
        ),
        SyncPoint(
            timestamp_ms=2_000,
            temp=TempReading(timestamp_ms=2_000, celsius=40.0, source="workflow_mock"),
            metric=ShapeMetric(timestamp_ms=2_000, metric_raw=18.0, metric_name="end_displacement", quality=1.0),
        ),
        SyncPoint(
            timestamp_ms=3_000,
            temp=TempReading(timestamp_ms=3_000, celsius=50.0, source="workflow_mock"),
            metric=ShapeMetric(timestamp_ms=3_000, metric_raw=20.0, metric_name="end_displacement", quality=1.0),
        ),
    ]


class WorkflowSessionRunner:
    """Run one offline session from input sync points.

    point_count counts the total input sync_points, not only the valid curve points.
    """

    def __init__(self, repo: SessionSummaryRepo) -> None:
        self.repo = repo

    def run_offline(self, session_id: str, sync_points: list[SyncPoint]) -> SessionSummary:
        record = SessionRecord(session_id=session_id, state=SessionState.RUNNING)
        created_at_ms = int(time.time() * 1000)
        point_count = len(sync_points)

        try:
            af95 = estimate_af95(sync_points)
            summary = SessionSummary(
                session_id=record.session_id,
                state=SessionState.COMPLETED.value,
                point_count=point_count,
                af95=af95,
                created_at_ms=created_at_ms,
            )
            self.repo.save_summary(summary)
            record.state = SessionState.COMPLETED
            return summary
        except Exception as exc:
            record.state = SessionState.FAILED
            return SessionSummary(
                session_id=record.session_id,
                state=record.state.value,
                point_count=point_count,
                af95=None,
                created_at_ms=created_at_ms,
                meta={"reason": "storage_save_failed", "detail": str(exc)},
            )
