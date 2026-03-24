from src.application.runtime_config import RuntimeConfig, WebAppConfig
from src.camera.mock_camera import MockCamera
from src.core.enums import RunStatus
from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion, ShapeMetric, TempReading
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SqliteSessionRepo
from src.temp.mock_temp import MockTempController
from src.workflow.live_run import (
    LiveRunCoordinator,
    LiveRunStopRequested,
    LiveRunTrackingInvalidated,
    MockLiveMetricSource,
)


def _definition() -> MeasurementDefinition:
    return MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=96, height=64),
        metric_box=MetricBox(center_x=48, center_y=32, width=80, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=12, y=32),
        point_b_px=PixelPoint(x=83, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )


def _runtime_run_config():
    return RuntimeConfig(
        profile="dev_mock",
        platform="mac",
        mode="mock",
        webapp=WebAppConfig(host="127.0.0.1", port=8000),
        adapters={"camera": "mock", "temp": "mock", "plc": "mock"},
    ).live.run


class InvalidatingMetricSource:
    def extract(
        self,
        frame,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        return ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=72.0,
            quality=0.2,
            feature_point_px=(48, 32),
            point_a_px=(12, 32),
            point_b_px=(83, 32),
        )


def test_live_run_coordinator_emits_stopping_when_operator_requests_stop(tmp_path) -> None:
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    definition = _definition()
    temp_controller = MockTempController()
    status_updates: list[str] = []

    try:
        coordinator.run(
            session_id="run-stop",
            definition=definition,
            target_temperature_celsius=75.0,
            run_config=_runtime_run_config(),
            analysis_engine="afas",
            channel_name="Space1",
            as_fit_point_count=5,
            af_fit_point_count=5,
            camera=MockCamera(),
            temp_reader=temp_controller,
            temp_controller=temp_controller,
            metric_source=MockLiveMetricSource(definition=definition, target_temperature_celsius=75.0),
            status_callback=lambda status, payload: status_updates.append(status.value),
            wait_for_next_sample=lambda seconds: True,
        )
    except LiveRunStopRequested as exc:
        assert exc.reason == "user_stop"
    else:
        raise AssertionError("expected operator stop to abort the run")

    assert status_updates == [RunStatus.RUNNING.value, RunStatus.STOPPING.value]


def test_live_run_coordinator_emits_invalidated_before_abort_when_tracking_drops(tmp_path) -> None:
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = MockTempController()
    status_updates: list[str] = []

    try:
        coordinator.run(
            session_id="run-invalidated",
            definition=_definition(),
            target_temperature_celsius=75.0,
            run_config=_runtime_run_config(),
            analysis_engine="afas",
            channel_name="Space1",
            as_fit_point_count=5,
            af_fit_point_count=5,
            camera=MockCamera(),
            temp_reader=temp_controller,
            temp_controller=temp_controller,
            metric_source=InvalidatingMetricSource(),
            quality_threshold=0.75,
            status_callback=lambda status, payload: status_updates.append(status.value),
        )
    except LiveRunTrackingInvalidated as exc:
        assert exc.reason == "invalid_tracking"
    else:
        raise AssertionError("expected low-quality tracking to invalidate the run")

    assert status_updates == [
        RunStatus.RUNNING.value,
        RunStatus.INVALIDATED.value,
        RunStatus.STOPPING.value,
    ]
