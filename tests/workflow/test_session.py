from pathlib import Path

from src.core.models import ShapeMetric, SyncPoint, TempReading
from src.storage.sqlite_repo import SessionSummary, SqliteSessionRepo
from src.workflow.session import WorkflowSessionRunner, build_replay_sync_points


def _sync_point(timestamp_ms: int, temp_celsius: float | None, metric_raw: float | None) -> SyncPoint:
    temp = None if temp_celsius is None else TempReading(timestamp_ms=timestamp_ms, celsius=temp_celsius, source="fixture")
    metric = None if metric_raw is None else ShapeMetric(timestamp_ms=timestamp_ms, metric_raw=metric_raw)
    return SyncPoint(timestamp_ms=timestamp_ms, temp=temp, metric=metric)


def test_run_offline_completes_and_persists_summary(tmp_path: Path) -> None:
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    runner = WorkflowSessionRunner(repo=repo)
    sync_points = [
        _sync_point(1, 30.0, 0.0),
        _sync_point(2, 40.0, 18.0),
        _sync_point(3, 50.0, 20.0),
    ]

    result = runner.run_offline(session_id="demo-001", sync_points=sync_points)
    persisted = repo.get_summary("demo-001")

    assert result.session_id == "demo-001"
    assert result.state == "completed"
    assert result.point_count == 3
    assert result.af95 is not None
    assert persisted == result


def test_run_offline_completes_even_when_af95_is_not_computable(tmp_path: Path) -> None:
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    runner = WorkflowSessionRunner(repo=repo)

    result = runner.run_offline(session_id="demo-empty", sync_points=[])
    persisted = repo.get_summary("demo-empty")

    assert result.state == "completed"
    assert result.point_count == 0
    assert result.af95 is None
    assert persisted == result


class FailingRepo:
    def save_summary(self, summary: SessionSummary) -> None:
        raise RuntimeError("disk unavailable")


def test_run_offline_marks_failed_when_repo_save_raises() -> None:
    runner = WorkflowSessionRunner(repo=FailingRepo())

    result = runner.run_offline(
        session_id="demo-fail",
        sync_points=[_sync_point(1, 30.0, 0.0), _sync_point(2, 40.0, 20.0)],
    )

    assert result.state == "failed"
    assert result.point_count == 2
    assert result.meta["reason"] == "storage_save_failed"


def test_build_replay_sync_points_reads_valid_dataset() -> None:
    dataset_path = Path(__file__).resolve().parents[2] / "examples" / "replay"

    sync_points = build_replay_sync_points(dataset_path)

    assert len(sync_points) == 3
    assert sync_points[0].frame is not None
    assert sync_points[0].metric is not None
    assert sync_points[0].metric.metric_raw == 0.0
    assert sync_points[-1].metric is not None
    assert sync_points[-1].metric.metric_raw is not None
    assert sync_points[-1].metric.metric_raw > 0.0


def test_run_replay_completes_and_persists_summary(tmp_path: Path) -> None:
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    runner = WorkflowSessionRunner(repo=repo)
    dataset_path = Path(__file__).resolve().parents[2] / "examples" / "replay"

    result = runner.run_replay(session_id="replay-001", dataset_path=dataset_path)
    persisted = repo.get_summary("replay-001")

    assert result.state == "completed"
    assert result.point_count == 3
    assert result.af95 is not None
    assert persisted == result


def test_build_replay_sync_points_raises_for_missing_dataset(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-replay"

    try:
        build_replay_sync_points(missing_path)
    except FileNotFoundError as exc:
        assert "Replay dataset not found" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError for missing replay dataset")
