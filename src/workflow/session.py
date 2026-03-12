"""Minimal offline session orchestration."""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.core.enums import SessionState
from src.core.models import FramePacket, SessionRecord, ShapeMetric, SyncPoint, TempReading
from src.curve.af95 import estimate_af95, normalize_sync_points
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SessionSummary
from src.vision.metric_end_displacement import EndDisplacementMetricExtractor


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


def build_replay_sync_points(dataset_path: str | Path) -> list[SyncPoint]:
    dataset_root = _resolve_dataset_path(dataset_path)
    temp_lookup = _load_replay_temps(dataset_root / "temp_series.csv")
    extractor = EndDisplacementMetricExtractor()
    sync_points: list[SyncPoint] = []

    for frame_index, frame_path in enumerate(sorted((dataset_root / "frames").glob("*.json")), start=1):
        frame_payload = json.loads(frame_path.read_text(encoding="utf-8"))
        timestamp_ms = int(frame_payload["timestamp_ms"])
        frame = FramePacket(
            timestamp_ms=timestamp_ms,
            source="replay_dataset",
            image=frame_payload["image"],
            frame_id=frame_index,
            meta={"dataset_path": str(dataset_root)},
        )
        metric = extractor.extract(frame)
        temp = temp_lookup.get(timestamp_ms)
        sync_points.append(
            SyncPoint(
                timestamp_ms=timestamp_ms,
                frame=frame,
                temp=temp,
                metric=metric,
            )
        )

    if not sync_points:
        raise FileNotFoundError(f"No replay frames found under: {dataset_root / 'frames'}")
    return sync_points


class WorkflowSessionRunner:
    """Run one offline session from input sync points.

    point_count counts the total input sync_points, not only the valid curve points.
    """

    def __init__(self, repo: SessionSummaryRepo, artifact_store: SessionArtifactStore | None = None) -> None:
        self.repo = repo
        self.artifact_store = artifact_store

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

    def run_replay(self, session_id: str, dataset_path: str | Path) -> SessionSummary:
        record = SessionRecord(session_id=session_id, state=SessionState.RUNNING)
        created_at_ms = int(time.time() * 1000)

        try:
            sync_points = build_replay_sync_points(dataset_path)
            af95 = estimate_af95(sync_points)
            detail_payload = build_replay_detail(session_id=session_id, sync_points=sync_points, af95=af95)
            if self.artifact_store is None:
                raise RuntimeError("artifact_store is required for replay sessions")
            self.artifact_store.save_detail(session_id, detail_payload)

            summary = SessionSummary(
                session_id=record.session_id,
                state=SessionState.COMPLETED.value,
                point_count=len(sync_points),
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
                point_count=0,
                af95=None,
                created_at_ms=created_at_ms,
                meta={"reason": "replay_failed", "detail": str(exc)},
            )


def build_replay_detail(session_id: str, sync_points: list[SyncPoint], af95: float | None) -> dict[str, Any]:
    normalized_points = normalize_sync_points(sync_points)
    normalized_by_timestamp = {point.timestamp_ms: point for point in normalized_points}
    detail_points: list[dict[str, Any]] = []
    for sync_point in sync_points:
        if sync_point.temp is None or sync_point.metric is None or sync_point.metric.metric_raw is None:
            continue
        normalized = normalized_by_timestamp.get(sync_point.timestamp_ms)
        detail_points.append(
            {
                "timestamp_ms": sync_point.timestamp_ms,
                "celsius": sync_point.temp.celsius,
                "metric_raw": sync_point.metric.metric_raw,
                "metric_norm": normalized.metric_norm if normalized is not None else None,
                "quality": sync_point.metric.quality,
            }
        )

    return {
        "session_id": session_id,
        "source": "replay",
        "af95": af95,
        "point_count": len(detail_points),
        "points": detail_points,
        "key_frames": _select_key_frames(sync_points),
    }


def _resolve_dataset_path(dataset_path: str | Path) -> Path:
    path = Path(dataset_path)
    if path.is_absolute():
        resolved = path
    else:
        resolved = Path(__file__).resolve().parents[2] / path
    if not resolved.exists():
        raise FileNotFoundError(f"Replay dataset not found: {resolved}")
    return resolved


def _load_replay_temps(csv_path: Path) -> dict[int, TempReading]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Replay temperature series not found: {csv_path}")

    temperatures: dict[int, TempReading] = {}
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            timestamp_ms = int(row["timestamp_ms"])
            temperatures[timestamp_ms] = TempReading(
                timestamp_ms=timestamp_ms,
                celsius=float(row["celsius"]),
                source="replay_dataset",
            )
    return temperatures


def _select_key_frames(sync_points: list[SyncPoint]) -> list[dict[str, Any]]:
    frame_points = [point for point in sync_points if point.frame is not None and point.metric is not None]
    if not frame_points:
        return []

    indexed_points: list[tuple[str, SyncPoint]] = [("first", frame_points[0])]
    if len(frame_points) > 2:
        indexed_points.append(("middle", frame_points[len(frame_points) // 2]))
    if len(frame_points) > 1:
        indexed_points.append(("last", frame_points[-1]))

    key_frames: list[dict[str, Any]] = []
    seen_timestamps: set[tuple[str, int]] = set()
    for label, sync_point in indexed_points:
        if sync_point.frame is None or sync_point.metric is None:
            continue
        marker = (label, sync_point.timestamp_ms)
        if marker in seen_timestamps:
            continue
        seen_timestamps.add(marker)
        key_frames.append(
            {
                "label": label,
                "timestamp_ms": sync_point.timestamp_ms,
                "image": sync_point.frame.image,
                "feature_point_px": list(sync_point.metric.feature_point_px)
                if sync_point.metric.feature_point_px is not None
                else None,
                "metric_raw": sync_point.metric.metric_raw,
            }
        )
    return key_frames
