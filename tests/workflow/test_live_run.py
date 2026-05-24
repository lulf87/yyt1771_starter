import numpy as np
import pytest

from src.application.runtime_config import RuntimeConfig, WebAppConfig
from src.camera.mock_camera import MockCamera
from src.core.enums import ObservationAxis
from src.core.models import (
    FramePacket,
    MeasurementDefinition,
    MetricBox,
    PixelPoint,
    RectRegion,
    ShapeMetric,
    SyncPoint,
    TempReading,
)
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SqliteSessionRepo
from src.temp.mock_temp import MockTempController
from src.workflow.live_run import (
    LiveRunCoordinator,
    LockedDefinitionMetricSource,
    MockLiveMetricSource,
    PriorTrackingMetricSource,
    build_partial_live_run_execution,
    resolve_measurement_interval_ms,
    _definition_payload,
    _telemetry_row,
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


class SequencedCamera:
    def __init__(self, timestamps_ms: list[int]) -> None:
        self._timestamps_ms = list(timestamps_ms)
        self._frame_id = 0

    def read_frame(self) -> FramePacket:
        timestamp_ms = self._timestamps_ms[self._frame_id]
        self._frame_id += 1
        return FramePacket(
            timestamp_ms=timestamp_ms,
            source="sequenced_camera",
            image=[[0, 1], [2, 3]],
            frame_id=self._frame_id,
        )


class SequencedTempController:
    def __init__(self, *, timestamps_ms: list[int], celsius_values: list[float]) -> None:
        self._timestamps_ms = list(timestamps_ms)
        self._celsius_values = list(celsius_values)
        self._read_index = 0
        self._output_enabled = False

    def set_target_temperature(self, celsius: float) -> None:
        self._target = celsius

    def start_output(self) -> None:
        self._output_enabled = True

    def stop_output(self) -> None:
        self._output_enabled = False

    def read(self) -> TempReading:
        timestamp_ms = self._timestamps_ms[self._read_index]
        celsius = self._celsius_values[self._read_index]
        self._read_index += 1
        return TempReading(timestamp_ms=timestamp_ms, celsius=celsius, source="sequenced_temp")


def test_telemetry_row_includes_direction_projection_points() -> None:
    sync_point = SyncPoint(
        timestamp_ms=1_000,
        frame=FramePacket(timestamp_ms=980, source="camera", frame_id=7),
        temp=TempReading(timestamp_ms=990, celsius=30.0, source="temp"),
        metric=ShapeMetric(
            timestamp_ms=995,
            metric_raw=42.0,
            quality=0.98,
            point_a_px=(80, 92),
            point_b_px=(280, 92),
            meta={
                "source_point_a_px": (70, 112),
                "source_point_b_px": (290, 72),
                "axis_point_a_px": (80, 92),
                "axis_point_b_px": (280, 92),
            },
        ),
    )

    row = _telemetry_row(sync_point, sample_index=0, previous_timestamp_ms=None)

    assert row["source_point_a_px"] == [70, 112]
    assert row["source_point_b_px"] == [290, 72]
    assert row["axis_point_a_px"] == [80, 92]
    assert row["axis_point_b_px"] == [280, 92]


class LowQualityMetricSource:
    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        return ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=71.0,
            quality=0.2,
            point_a_px=(12, 32),
            point_b_px=(83, 32),
            baseline_px=71.0,
            meta={
                "reason": "test_low_quality",
                "sample_index": sample_index,
                "total_samples": total_samples,
            },
        )


def _fixture_image(*rectangles: tuple[int, int, int, int], width: int = 96, height: int = 64) -> list[list[int]]:
    image = [[220 for _ in range(width)] for _ in range(height)]
    for x, y, rect_width, rect_height in rectangles:
        for row in range(y, min(y + rect_height, height)):
            for col in range(x, min(x + rect_width, width)):
                image[row][col] = 40
    return image


def test_mock_live_metric_source_uses_numpy_frame_bounds() -> None:
    source = MockLiveMetricSource(definition=_definition(), target_temperature_celsius=75.0)

    metric = source.extract(
        FramePacket(
            timestamp_ms=1_000,
            source="mock_camera",
            image=np.full((620, 1120), 240, dtype=np.uint8),
            frame_id=1,
        ),
        TempReading(timestamp_ms=1_005, celsius=75.0, source="mock_temp"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.point_a_px is not None
    assert metric.point_b_px is not None
    assert 0 <= metric.point_a_px[0] <= 1119
    assert 0 <= metric.point_b_px[0] <= 1119
    assert 0 <= metric.point_a_px[1] <= 619
    assert 0 <= metric.point_b_px[1] <= 619


def test_live_run_coordinator_completes_and_persists_bundle(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = MockTempController()

    execution = coordinator.run(
        session_id="run-001",
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
    )

    assert execution.summary.session_id == "run-001"
    assert execution.summary.state == "completed"
    assert execution.summary.point_count >= 3
    assert execution.summary.af95 is not None
    assert execution.detail["source"] == "live_run"
    assert execution.detail["result_status"] == "ok"
    assert execution.detail["as_value"] is not None
    assert execution.detail["af_value"] is not None
    assert execution.result["state"] == "completed"
    assert execution.result["result_status"] == "ok"
    assert execution.result["as_value"] is not None
    assert execution.result["af_value"] is not None
    assert execution.result["artifacts"]["afas_dataset"] == "afas_dataset.json"
    assert execution.result["artifacts"]["keyframes"]
    assert repo.get_summary("run-001") == execution.summary
    assert (tmp_path / "artifacts" / "run-001" / "result.json").exists()
    assert (tmp_path / "artifacts" / "run-001" / "afas_dataset.json").exists()
    assert (tmp_path / "artifacts" / "run-001" / "keyframes" / "first.png").exists()


def test_live_run_coordinator_completes_with_explicit_unavailable_result_when_curve_points_are_insufficient(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = MockTempController()

    execution = coordinator.run(
        session_id="run-short",
        definition=definition,
        target_temperature_celsius=35.0,
        run_config=_runtime_run_config(),
        analysis_engine="afas",
        channel_name="Space1",
        as_fit_point_count=5,
        af_fit_point_count=5,
        camera=MockCamera(),
        temp_reader=temp_controller,
        temp_controller=temp_controller,
        metric_source=MockLiveMetricSource(definition=definition, target_temperature_celsius=35.0),
    )

    assert execution.summary.state == "completed"
    assert execution.detail["result_status"] == "unavailable"
    assert execution.detail["result_reason"] == "insufficient_points"
    assert execution.result["result_status"] == "unavailable"
    assert execution.result["result_reason"] == "insufficient_points"
    assert execution.result["as_value"] is None
    assert execution.result["af_value"] is None


def test_live_run_coordinator_zero_max_samples_disables_sample_count_cap(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    camera = SequencedCamera([1_000, 1_100, 1_200])
    temp_controller = SequencedTempController(
        timestamps_ms=[1_005, 1_105, 1_205],
        celsius_values=[25.0, 26.0, 27.0],
    )
    run_config = _runtime_run_config()
    run_config.manual_stop_max_samples = 0

    execution = coordinator.run(
        session_id="run-unbounded-sample-count",
        definition=definition,
        target_temperature_celsius=27.0,
        run_config=run_config,
        analysis_engine="afas",
        channel_name="Space1",
        as_fit_point_count=5,
        af_fit_point_count=5,
        camera=camera,
        temp_reader=temp_controller,
        temp_controller=temp_controller,
        metric_source=MockLiveMetricSource(definition=definition, target_temperature_celsius=27.0),
    )

    assert execution.summary.state == "completed"
    assert execution.detail["point_count"] == 3
    assert execution.telemetry[-1]["temperature_celsius"] == 27.0


def test_partial_terminal_execution_runs_afas_when_telemetry_is_available() -> None:
    telemetry = []
    for index in range(60):
        progress = index / 59.0
        curve_progress = progress * progress * (3.0 - 2.0 * progress)
        telemetry.append(
            {
                "timestamp_ms": 1_000 + index,
                "temperature_celsius": -5.0 + index * 0.5,
                "space1_px": 38.0 + 35.0 * curve_progress,
                "tracking_quality": 0.99,
                "frame_id": index + 1,
                "frame_timestamp_ms": 1_000 + index,
                "temp_timestamp_ms": 1_000 + index,
                "metric_timestamp_ms": 1_000 + index,
                "point_a_px": [12, 32],
                "point_b_px": [83, 32],
            }
        )

    execution = build_partial_live_run_execution(
        session_id="run-failed-with-data",
        started_at_ms=1_000,
        terminal_state="failed",
        terminal_reason="runtime_error",
        terminal_detail="target_temperature_not_reached",
        definition=_definition(),
        telemetry=telemetry,
        events=[],
        camera_config=None,
        analysis_engine="afas",
        channel_name="Space1",
        as_fit_point_count=5,
        af_fit_point_count=5,
        target_measurement_hz=20.0,
    )

    assert execution.summary.state == "failed"
    assert execution.summary.af95 is not None
    assert execution.detail["result_status"] == "ok"
    assert execution.result["state"] == "failed"
    assert execution.result["result_status"] == "ok"
    assert execution.result["as_value"] is not None
    assert execution.result["af_value"] is not None
    assert execution.result["point_count"] == 60
    assert execution.result["artifacts"]["afas_dataset"] == "afas_dataset.json"
    assert any("terminal_failed" in warning for warning in execution.result["warnings"])
    assert execution.afas_dataset is not None
    assert execution.afas_dataset["live_result_snapshot"]["result_status"] == "ok"
    assert execution.afas_dataset["live_result_snapshot"]["terminal_state"] == "failed"


class FailingTempController(MockTempController):
    def set_target_temperature(self, celsius: float) -> None:
        raise RuntimeError("target rejected")


class ReadFailingTempController(MockTempController):
    def __init__(self) -> None:
        super().__init__()
        self._read_count = 0

    def read(self):
        self._read_count += 1
        if self._read_count >= 2:
            raise RuntimeError("temp read failed")
        return super().read()


class FailingArtifactStore(SessionArtifactStore):
    def save_live_bundle(self, session_id: str, **kwargs):
        raise RuntimeError("artifact finalize failed")


def test_live_run_coordinator_raises_when_temp_target_is_rejected(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)

    try:
        coordinator.run(
            session_id="run-fail",
            definition=definition,
            target_temperature_celsius=75.0,
            run_config=_runtime_run_config(),
            analysis_engine="afas",
            channel_name="Space1",
            as_fit_point_count=5,
            af_fit_point_count=5,
            camera=MockCamera(),
            temp_reader=FailingTempController(),
            temp_controller=FailingTempController(),
            metric_source=MockLiveMetricSource(definition=definition, target_temperature_celsius=75.0),
        )
    except RuntimeError as exc:
        assert str(exc) == "target rejected"
    else:
        raise AssertionError("expected target rejection to propagate")


def test_live_run_coordinator_raises_when_temp_read_fails_during_running(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = ReadFailingTempController()

    try:
        coordinator.run(
            session_id="run-temp-read-fail",
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
        )
    except RuntimeError as exc:
        assert str(exc) == "temp read failed"
    else:
        raise AssertionError("expected read failure to propagate")


def test_live_run_coordinator_manual_stop_mode_does_not_auto_complete_on_target_reached(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = MockTempController(ramp_step_celsius=100.0)
    run_config = _runtime_run_config()
    run_config.capture_interval_ms = 500
    run_config.manual_stop_max_samples = 25

    def _stop_while_waiting(seconds: float) -> bool:
        return True

    try:
        coordinator.run(
            session_id="run-manual-stop-mode",
            definition=definition,
            target_temperature_celsius=35.0,
            run_config=run_config,
            analysis_engine="afas",
            channel_name="Space1",
            as_fit_point_count=5,
            af_fit_point_count=5,
            camera=MockCamera(),
            temp_reader=temp_controller,
            temp_controller=temp_controller,
            metric_source=MockLiveMetricSource(definition=definition, target_temperature_celsius=35.0),
            stop_on_target_reached=False,
            wait_for_next_sample=_stop_while_waiting,
        )
    except Exception as exc:
        assert exc.__class__.__name__ == "LiveRunStopRequested"
        assert getattr(exc, "reason", None) == "user_stop"
    else:
        raise AssertionError("expected manual-stop mode to keep running until stop is requested")


def test_live_run_coordinator_stops_at_playback_end_in_manual_stop_mode(tmp_path) -> None:
    class PlaybackTempController(SequencedTempController):
        def playback_sample_count(self) -> int:
            return 3

    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = PlaybackTempController(
        timestamps_ms=[1_005, 1_105, 1_205],
        celsius_values=[25.0, 25.1, 25.2],
    )
    run_config = _runtime_run_config()
    run_config.manual_stop_max_samples = 0

    execution = coordinator.run(
        session_id="run-manual-stop-playback-end",
        definition=definition,
        target_temperature_celsius=75.0,
        run_config=run_config,
        analysis_engine="afas",
        channel_name="Space1",
        as_fit_point_count=5,
        af_fit_point_count=5,
        camera=SequencedCamera([1_000, 1_100, 1_200]),
        temp_reader=temp_controller,
        temp_controller=temp_controller,
        metric_source=MockLiveMetricSource(definition=definition, target_temperature_celsius=75.0),
        stop_on_target_reached=False,
    )

    assert execution.summary.state == "completed"
    assert execution.detail["point_count"] == 3
    assert execution.telemetry[-1]["temperature_celsius"] == pytest.approx(25.2)


def test_live_run_coordinator_keeps_running_when_invalid_tracking_does_not_abort(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = MockTempController()
    run_config = _runtime_run_config()
    run_config.stop_on_invalid_tracking = False
    statuses: list[str] = []

    execution = coordinator.run(
        session_id="run-low-quality-allowed",
        definition=definition,
        target_temperature_celsius=35.0,
        run_config=run_config,
        analysis_engine="afas",
        channel_name="Space1",
        as_fit_point_count=5,
        af_fit_point_count=5,
        camera=MockCamera(),
        temp_reader=temp_controller,
        temp_controller=temp_controller,
        metric_source=LowQualityMetricSource(),
        status_callback=lambda status, payload: statuses.append(status.value),
    )

    assert execution.summary.state == "completed"
    assert execution.telemetry
    assert all(row["tracking_quality"] == 0.2 for row in execution.telemetry)
    assert any(event["type"] == "tracking_invalidated" for event in execution.events)
    assert "invalidated" not in statuses


def test_live_run_coordinator_allows_low_quality_during_startup_grace_window(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = MockTempController(ramp_step_celsius=0.5)
    run_config = _runtime_run_config()
    run_config.invalid_tracking_grace_samples = 5
    statuses: list[str] = []

    def _stop_after_first_wait(seconds: float) -> bool:
        return True

    try:
        coordinator.run(
            session_id="run-low-quality-grace",
            definition=definition,
            target_temperature_celsius=35.0,
            run_config=run_config,
            analysis_engine="afas",
            channel_name="Space1",
            as_fit_point_count=5,
            af_fit_point_count=5,
            camera=MockCamera(),
            temp_reader=temp_controller,
            temp_controller=temp_controller,
            metric_source=LowQualityMetricSource(),
            stop_on_target_reached=False,
            wait_for_next_sample=_stop_after_first_wait,
            status_callback=lambda status, payload: statuses.append(status.value),
        )
    except Exception as exc:
        assert exc.__class__.__name__ == "LiveRunStopRequested"
        assert getattr(exc, "reason", None) == "user_stop"
    else:
        raise AssertionError("expected grace-window run to continue until an explicit stop request")
    assert "invalidated" not in statuses


def test_live_run_coordinator_invalidates_after_startup_grace_window_is_exhausted(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = MockTempController(ramp_step_celsius=0.5)
    run_config = _runtime_run_config()
    run_config.invalid_tracking_grace_samples = 2

    try:
        coordinator.run(
            session_id="run-low-quality-grace-expired",
            definition=definition,
            target_temperature_celsius=35.0,
            run_config=run_config,
            analysis_engine="afas",
            channel_name="Space1",
            as_fit_point_count=5,
            af_fit_point_count=5,
            camera=MockCamera(),
            temp_reader=temp_controller,
            temp_controller=temp_controller,
            metric_source=LowQualityMetricSource(),
            stop_on_target_reached=False,
        )
    except Exception as exc:
        assert exc.__class__.__name__ == "LiveRunTrackingInvalidated"
        assert getattr(exc, "reason", None) == "invalid_tracking"
    else:
        raise AssertionError("expected low-quality run to invalidate after startup grace is exhausted")


def test_locked_definition_metric_source_respects_long_axis_observation_direction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition = _definition()
    definition.observation_axis = ObservationAxis.LONG_AXIS
    definition.metric_box = MetricBox(center_x=48, center_y=32, width=80, height=24, angle_deg=0.0)
    extractor_init: dict[str, object] = {}

    class FakeExtractor:
        def __init__(self, **kwargs):
            extractor_init.update(kwargs)

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1,
                metric_name="two_point_distance",
                metric_raw=23.0,
                quality=0.99,
                point_a_px=(20, 32),
                point_b_px=(43, 32),
                meta={
                    "measurement_axis_deg": extractor_init["measurement_axis_deg"],
                    "selection_mode": extractor_init["selection_strategy"],
                },
            )

    monkeypatch.setattr("src.workflow.live_run.TwoPointDistanceMetricExtractor", FakeExtractor)

    source = LockedDefinitionMetricSource(definition=definition)
    metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]]),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.metric_raw == 23.0
    assert metric.point_a_px == (20, 32)
    assert metric.point_b_px == (43, 32)
    assert metric.meta["measurement_axis_deg"] == 0.0
    assert metric.meta["selection_mode"] == "roi_local_horizontal_boundary"


def test_locked_definition_metric_source_respects_rotated_long_axis_observation_direction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor_init: dict[str, object] = {}

    class FakeExtractor:
        def __init__(self, **kwargs):
            extractor_init.update(kwargs)

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1,
                metric_name="two_point_distance",
                metric_raw=85.44,
                quality=0.99,
                point_a_px=(137, 48),
                point_b_px=(91, 120),
                meta={
                    "measurement_axis_deg": extractor_init["measurement_axis_deg"],
                    "selection_mode": extractor_init["selection_strategy"],
                },
            )

    monkeypatch.setattr("src.workflow.live_run.TwoPointDistanceMetricExtractor", FakeExtractor)

    width = 240
    height = 160
    band_angle_deg = -32.0
    center_x = 120
    center_y = 80
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=width, height=height),
        metric_box=MetricBox(center_x=center_x, center_y=center_y, width=140, height=70, angle_deg=band_angle_deg),
        point_a_px=PixelPoint(x=137, y=48),
        point_b_px=PixelPoint(x=91, y=120),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        ignore_internal_texture=True,
        min_target_area_px=50,
        observation_axis=ObservationAxis.LONG_AXIS,
    )

    source = LockedDefinitionMetricSource(definition=definition)
    metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]]),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.point_a_px == (137, 48)
    assert metric.point_b_px == (91, 120)
    assert metric.metric_raw == pytest.approx(85.44, abs=1.0)
    assert metric.meta["measurement_axis_deg"] == -32.0
    assert metric.meta["selection_mode"] == "roi_local_horizontal_boundary"


def test_locked_definition_metric_source_uses_directional_contour_when_direction_angle_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor_config: dict[str, object] = {}

    class FakeDirectionalExtractor:
        def __init__(self, config):
            extractor_config["config"] = config

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=18.0,
                quality=0.98,
                point_a_px=(15, 6),
                point_b_px=(15, 24),
                meta={
                    "selection_mode": "directional_contour_projection",
                    "direction_angle_deg": 90.0,
                },
            )

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=32, height=32),
        metric_box=MetricBox(center_x=16, center_y=16, width=24, height=8, angle_deg=90.0),
        point_a_px=PixelPoint(x=15, y=6),
        point_b_px=PixelPoint(x=15, y=24),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        ignore_internal_texture=True,
        min_target_area_px=12,
        direction_angle_deg=90.0,
    )

    source = LockedDefinitionMetricSource(definition=definition)
    metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]]),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    config = extractor_config["config"]
    assert config.analysis_roi == definition.analysis_roi
    assert config.direction_angle_deg == 90.0
    assert config.metric_box == definition.metric_box
    assert config.projection_mode == "auto"
    assert config.processing_max_side_px >= 384
    assert config.threshold_mode == "binary"
    assert metric.metric_name == "directional_contour_span"
    assert metric.point_a_px == (15, 6)
    assert metric.point_b_px == (15, 24)
    assert metric.meta["selection_mode"] == "directional_contour_projection"
    assert metric.meta["sample_index"] == 0


def test_prior_tracking_metric_source_holds_last_good_points_when_observation_jumps() -> None:
    source = PriorTrackingMetricSource(
        definition=_definition(),
        max_endpoint_jump_px=12.0,
        max_midpoint_drift_px=8.0,
        max_span_change_ratio=0.20,
        max_consecutive_misses=2,
    )
    stable_metric = source.extract(
        FramePacket(
            timestamp_ms=1,
            source="fixture",
            image=_fixture_image((24, 20, 48, 24)),
            frame_id=1,
        ),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=3,
    )
    drifting_metric = source.extract(
        FramePacket(
            timestamp_ms=2,
            source="fixture",
            image=_fixture_image((2, 20, 30, 24)),
            frame_id=2,
        ),
        TempReading(timestamp_ms=2, celsius=25.0, source="fixture"),
        sample_index=1,
        total_samples=3,
    )

    assert stable_metric.meta["tracking_state"] == "bootstrapped"
    assert drifting_metric.meta["selection_mode"] == "tracking_prior_hold"
    assert drifting_metric.meta["tracking_state"] == "holding_last_good"
    assert drifting_metric.point_a_px == stable_metric.point_a_px
    assert drifting_metric.point_b_px == stable_metric.point_b_px
    assert drifting_metric.meta["reason"] in {"endpoint_jump_exceeded", "midpoint_drift_exceeded"}


def test_prior_tracking_metric_source_stabilizes_roi_horizontal_lateral_row_jitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = iter(
        [
            ShapeMetric(
                timestamp_ms=1,
                metric_name="two_point_distance",
                metric_raw=800.0,
                quality=0.95,
                point_a_px=(100, 32),
                point_b_px=(900, 32),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            ),
            ShapeMetric(
                timestamp_ms=2,
                metric_name="two_point_distance",
                metric_raw=800.0,
                quality=0.95,
                point_a_px=(120, 77),
                point_b_px=(920, 77),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            ),
        ]
    )

    class FakeLockedDefinitionMetricSource:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def extract(self, frame, temp, *, sample_index: int, total_samples: int):
            del frame, temp, sample_index, total_samples
            return next(observations)

    monkeypatch.setattr("src.workflow.live_run.LockedDefinitionMetricSource", FakeLockedDefinitionMetricSource)
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=1200, height=160),
        metric_box=MetricBox(center_x=500, center_y=32, width=900, height=80, angle_deg=0.0),
        point_a_px=PixelPoint(x=100, y=32),
        point_b_px=PixelPoint(x=900, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="otsu",
        ignore_internal_texture=True,
        min_target_area_px=20,
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=80.0,
        max_midpoint_drift_px=80.0,
        max_span_change_ratio=0.20,
    )

    first_metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=2,
    )
    jitter_metric = source.extract(
        FramePacket(timestamp_ms=2, source="fixture", image=[[0]], frame_id=2),
        TempReading(timestamp_ms=2, celsius=25.1, source="fixture"),
        sample_index=1,
        total_samples=2,
    )

    assert first_metric.meta["tracking_state"] == "bootstrapped"
    assert jitter_metric.meta["selection_mode"] == "tracking_prior_stabilized"
    assert jitter_metric.meta["tracking_state"] == "accepted_stabilized"
    assert jitter_metric.meta["reason"] == "lateral_drift_stabilized"
    assert jitter_metric.point_a_px == (120, 32)
    assert jitter_metric.point_b_px == (920, 32)
    assert jitter_metric.metric_raw == pytest.approx(800.0)
    assert jitter_metric.meta["observed_point_a_px"] == (120, 77)
    assert jitter_metric.meta["midpoint_along_shift_px"] == pytest.approx(20.0)
    assert jitter_metric.meta["midpoint_lateral_drift_px"] == pytest.approx(45.0)


def test_prior_tracking_metric_source_stabilizes_roi_horizontal_single_endpoint_span_jitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = iter(
        [
            ShapeMetric(
                timestamp_ms=1,
                metric_name="two_point_distance",
                metric_raw=800.0,
                quality=0.95,
                point_a_px=(100, 32),
                point_b_px=(900, 32),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            ),
            ShapeMetric(
                timestamp_ms=2,
                metric_name="two_point_distance",
                metric_raw=824.0,
                quality=0.95,
                point_a_px=(100, 32),
                point_b_px=(924, 32),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            ),
        ]
    )

    class FakeLockedDefinitionMetricSource:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def extract(self, frame, temp, *, sample_index: int, total_samples: int):
            del frame, temp, sample_index, total_samples
            return next(observations)

    monkeypatch.setattr("src.workflow.live_run.LockedDefinitionMetricSource", FakeLockedDefinitionMetricSource)
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=1200, height=160),
        metric_box=MetricBox(center_x=500, center_y=32, width=900, height=80, angle_deg=0.0),
        point_a_px=PixelPoint(x=100, y=32),
        point_b_px=PixelPoint(x=900, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="otsu",
        ignore_internal_texture=True,
        min_target_area_px=20,
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=80.0,
        max_midpoint_drift_px=80.0,
        max_span_change_ratio=0.20,
    )

    first_metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=2,
    )
    jitter_metric = source.extract(
        FramePacket(timestamp_ms=2, source="fixture", image=[[0]], frame_id=2),
        TempReading(timestamp_ms=2, celsius=25.1, source="fixture"),
        sample_index=1,
        total_samples=2,
    )

    assert first_metric.meta["tracking_state"] == "bootstrapped"
    assert jitter_metric.meta["selection_mode"] == "tracking_prior_stabilized"
    assert jitter_metric.meta["tracking_state"] == "accepted_stabilized"
    assert jitter_metric.meta["reason"] == "span_change_stabilized"
    assert jitter_metric.point_a_px == (100, 32)
    assert jitter_metric.point_b_px[0] - first_metric.point_b_px[0] <= 4
    assert jitter_metric.metric_raw - first_metric.metric_raw <= 4
    assert jitter_metric.meta["observed_point_b_px"] == (924, 32)


def test_prior_tracking_metric_source_stabilizes_roi_horizontal_same_axis_step_jitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = iter(
        [
            ShapeMetric(
                timestamp_ms=1,
                metric_name="two_point_distance",
                metric_raw=800.0,
                quality=0.95,
                point_a_px=(100, 32),
                point_b_px=(900, 32),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            ),
            ShapeMetric(
                timestamp_ms=2,
                metric_name="two_point_distance",
                metric_raw=800.0,
                quality=0.95,
                point_a_px=(108, 32),
                point_b_px=(908, 32),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            ),
        ]
    )

    class FakeLockedDefinitionMetricSource:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def extract(self, frame, temp, *, sample_index: int, total_samples: int):
            del frame, temp, sample_index, total_samples
            return next(observations)

    monkeypatch.setattr("src.workflow.live_run.LockedDefinitionMetricSource", FakeLockedDefinitionMetricSource)
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=1200, height=160),
        metric_box=MetricBox(center_x=500, center_y=32, width=900, height=80, angle_deg=0.0),
        point_a_px=PixelPoint(x=100, y=32),
        point_b_px=PixelPoint(x=900, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="otsu",
        ignore_internal_texture=True,
        min_target_area_px=20,
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=80.0,
        max_midpoint_drift_px=80.0,
        max_span_change_ratio=0.20,
    )

    first_metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=2,
    )
    jitter_metric = source.extract(
        FramePacket(timestamp_ms=2, source="fixture", image=[[0]], frame_id=2),
        TempReading(timestamp_ms=2, celsius=25.1, source="fixture"),
        sample_index=1,
        total_samples=2,
    )

    assert first_metric.meta["tracking_state"] == "bootstrapped"
    assert jitter_metric.meta["selection_mode"] == "tracking_prior_stabilized"
    assert jitter_metric.meta["tracking_state"] == "accepted_stabilized"
    assert jitter_metric.meta["reason"] == "same_axis_step_stabilized"
    assert jitter_metric.point_a_px[0] - first_metric.point_a_px[0] <= 4
    assert jitter_metric.point_b_px[0] - first_metric.point_b_px[0] <= 4
    assert jitter_metric.metric_raw == pytest.approx(800.0)
    assert jitter_metric.meta["observed_point_a_px"] == (108, 32)
    assert jitter_metric.meta["observed_point_b_px"] == (908, 32)


def test_prior_tracking_metric_source_limits_roi_horizontal_stabilized_span_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = iter(
        [
            ShapeMetric(
                timestamp_ms=1,
                metric_name="two_point_distance",
                metric_raw=800.0,
                quality=0.95,
                point_a_px=(100, 32),
                point_b_px=(900, 32),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            ),
            ShapeMetric(
                timestamp_ms=2,
                metric_name="two_point_distance",
                metric_raw=808.0,
                quality=0.95,
                point_a_px=(96, 32),
                point_b_px=(904, 32),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            ),
        ]
    )

    class FakeLockedDefinitionMetricSource:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def extract(self, frame, temp, *, sample_index: int, total_samples: int):
            del frame, temp, sample_index, total_samples
            return next(observations)

    monkeypatch.setattr("src.workflow.live_run.LockedDefinitionMetricSource", FakeLockedDefinitionMetricSource)
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=1200, height=160),
        metric_box=MetricBox(center_x=500, center_y=32, width=900, height=80, angle_deg=0.0),
        point_a_px=PixelPoint(x=100, y=32),
        point_b_px=PixelPoint(x=900, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="otsu",
        ignore_internal_texture=True,
        min_target_area_px=20,
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=80.0,
        max_midpoint_drift_px=80.0,
        max_span_change_ratio=0.20,
    )

    first_metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=2,
    )
    jitter_metric = source.extract(
        FramePacket(timestamp_ms=2, source="fixture", image=[[0]], frame_id=2),
        TempReading(timestamp_ms=2, celsius=25.1, source="fixture"),
        sample_index=1,
        total_samples=2,
    )

    assert first_metric.meta["tracking_state"] == "bootstrapped"
    assert jitter_metric.meta["selection_mode"] == "tracking_prior_stabilized"
    assert jitter_metric.meta["tracking_state"] == "accepted_stabilized"
    assert jitter_metric.meta["reason"] == "span_change_stabilized"
    assert jitter_metric.metric_raw - first_metric.metric_raw <= 1
    assert jitter_metric.point_a_px == (100, 32)
    assert jitter_metric.point_b_px == (900, 32)
    assert jitter_metric.meta["max_frame_span_jump_px"] == pytest.approx(1.0)
    assert jitter_metric.meta["observed_point_a_px"] == (96, 32)
    assert jitter_metric.meta["observed_point_b_px"] == (904, 32)


def test_prior_tracking_metric_source_allows_larger_endpoint_bootstrap_for_max_chord() -> None:
    definition = _definition()
    definition.direction_projection_mode = "max_chord"
    definition.metric_box = MetricBox(center_x=300, center_y=32, width=900, height=240, angle_deg=0.0)

    source = PriorTrackingMetricSource(definition=definition)

    assert source._max_endpoint_jump_px == pytest.approx(180.0)
    assert source._max_midpoint_drift_px == pytest.approx(180.0)


def test_prior_tracking_directional_contour_uses_setup_scale_and_rotated_roi_mask(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor_configs: list[object] = []

    class FakeDirectionalExtractor:
        def __init__(self, config):
            extractor_configs.append(config)

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=80.0,
                quality=0.98,
                point_a_px=(20, 30),
                point_b_px=(100, 30),
                meta={
                    "selection_mode": "directional_contour_projection",
                    "direction_angle_deg": 0.0,
                },
            )

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=140, height=80),
        metric_box=MetricBox(center_x=60, center_y=30, width=100, height=28, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=30),
        point_b_px=PixelPoint(x=100, y=30),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="mask_projection",
    )

    source = PriorTrackingMetricSource(definition=definition)
    metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.meta["tracking_state"] == "bootstrapped"
    assert extractor_configs
    assert extractor_configs[0].metric_box == definition.metric_box
    assert extractor_configs[0].processing_max_side_px >= 384


def test_prior_tracking_metric_source_guides_max_chord_to_previous_axis() -> None:
    image = [[230 for _ in range(110)] for _ in range(70)]
    for row in range(20, 24):
        for col in range(24, 84):
            image[row][col] = 35
    for row in range(42, 46):
        for col in range(6, 104):
            image[row][col] = 35
    for row in range(20, 46):
        for col in range(52, 56):
            image[row][col] = 35
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=110, height=70),
        metric_box=MetricBox(center_x=54, center_y=22, width=70, height=20, angle_deg=0.0),
        point_a_px=PixelPoint(x=24, y=22),
        point_b_px=PixelPoint(x=83, y=22),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        ignore_internal_texture=False,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="max_chord",
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=12.0,
        max_midpoint_drift_px=8.0,
        max_span_change_ratio=0.30,
    )

    metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=image, frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.meta["tracking_state"] == "bootstrapped"
    assert metric.meta["selection_mode"] == "directional_contour_max_chord"
    assert metric.point_a_px is not None
    assert metric.point_b_px is not None
    assert abs(metric.point_a_px[1] - 22) <= 1
    assert abs(metric.point_b_px[1] - 22) <= 1


def test_prior_tracking_metric_source_guides_mask_projection_to_previous_axis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_configs = []

    class FakeDirectionalExtractor:
        def __init__(self, config):
            captured_configs.append(config)

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=60.0,
                quality=0.95,
                point_a_px=(20, 32),
                point_b_px=(80, 32),
                meta={"selection_mode": "directional_contour_projection"},
            )

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=160, height=64),
        metric_box=MetricBox(center_x=50, center_y=32, width=80, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=32),
        point_b_px=PixelPoint(x=80, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="mask_projection",
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=12.0,
        max_midpoint_drift_px=8.0,
        max_span_change_ratio=0.20,
    )

    metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.meta["tracking_state"] == "bootstrapped"
    assert captured_configs
    assert captured_configs[0].max_chord_axis_prior_point == PixelPoint(x=50, y=32)
    assert captured_configs[0].max_chord_axis_prior_tolerance_px == pytest.approx(8.0)


def test_prior_tracking_metric_source_allows_directional_along_axis_relocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeDirectionalExtractor:
        def __init__(self, config):
            del config

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=60.0,
                quality=0.95,
                point_a_px=(60, 32),
                point_b_px=(120, 32),
                meta={"selection_mode": "directional_contour_projection"},
            )

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=180, height=80),
        metric_box=MetricBox(center_x=50, center_y=32, width=80, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=32),
        point_b_px=PixelPoint(x=80, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="mask_projection",
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=12.0,
        max_midpoint_drift_px=8.0,
        max_span_change_ratio=0.20,
    )

    metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.meta["tracking_state"] == "bootstrapped_relocated"
    assert metric.meta["midpoint_along_shift_px"] == pytest.approx(40.0)
    assert metric.meta["midpoint_lateral_drift_px"] == pytest.approx(0.0)
    assert metric.point_a_px == (60, 32)
    assert metric.point_b_px == (120, 32)


def test_prior_tracking_metric_source_rejects_directional_lateral_jump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeDirectionalExtractor:
        def __init__(self, config):
            del config

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=60.0,
                quality=0.95,
                point_a_px=(20, 72),
                point_b_px=(80, 72),
                meta={"selection_mode": "directional_contour_projection"},
            )

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=180, height=90),
        metric_box=MetricBox(center_x=50, center_y=32, width=80, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=32),
        point_b_px=PixelPoint(x=80, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="mask_projection",
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=12.0,
        max_midpoint_drift_px=8.0,
        max_span_change_ratio=0.20,
    )

    metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.meta["tracking_state"] == "holding_last_good"
    assert metric.meta["reason"] == "midpoint_lateral_drift_exceeded"
    assert metric.meta["midpoint_along_shift_px"] == pytest.approx(0.0)
    assert metric.meta["midpoint_lateral_drift_px"] == pytest.approx(40.0)
    assert metric.point_a_px == (20, 32)
    assert metric.point_b_px == (80, 32)


def test_prior_tracking_metric_source_accepts_directional_relocation_when_span_is_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = iter(
        [
            ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=60.0,
                quality=0.95,
                point_a_px=(70, 32),
                point_b_px=(130, 32),
                meta={"selection_mode": "directional_contour_max_chord"},
            ),
            ShapeMetric(
                timestamp_ms=2,
                metric_name="directional_contour_span",
                metric_raw=60.0,
                quality=0.95,
                point_a_px=(90, 32),
                point_b_px=(150, 32),
                meta={"selection_mode": "directional_contour_max_chord"},
            ),
        ]
    )

    class FakeDirectionalExtractor:
        def __init__(self, config):
            del config

        def extract(self, frame):
            del frame
            return next(observations)

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=160, height=64),
        metric_box=MetricBox(center_x=50, center_y=32, width=80, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=32),
        point_b_px=PixelPoint(x=80, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="max_chord",
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=5.0,
        max_midpoint_drift_px=5.0,
        max_span_change_ratio=0.20,
    )

    bootstrapped = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=2,
    )
    relocated = source.extract(
        FramePacket(timestamp_ms=2, source="fixture", image=[[0]], frame_id=2),
        TempReading(timestamp_ms=2, celsius=25.0, source="fixture"),
        sample_index=1,
        total_samples=2,
    )

    assert bootstrapped.meta["tracking_state"] == "bootstrapped_relocated"
    assert bootstrapped.meta["selection_mode"] == "directional_contour_max_chord"
    assert bootstrapped.point_a_px == (70, 32)
    assert bootstrapped.point_b_px == (130, 32)
    assert relocated.meta["tracking_state"] == "accepted_relocated"
    assert relocated.point_a_px == (90, 32)
    assert relocated.point_b_px == (150, 32)


def test_prior_tracking_metric_source_rejects_directional_relocation_when_span_collapses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeDirectionalExtractor:
        def __init__(self, config):
            del config

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=8.0,
                quality=0.95,
                point_a_px=(80, 32),
                point_b_px=(88, 32),
                meta={"selection_mode": "directional_contour_max_chord"},
            )

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=160, height=64),
        metric_box=MetricBox(center_x=50, center_y=32, width=80, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=32),
        point_b_px=PixelPoint(x=80, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="max_chord",
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=5.0,
        max_midpoint_drift_px=5.0,
        max_span_change_ratio=0.20,
    )

    metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.meta["selection_mode"] == "tracking_prior_hold"
    assert metric.meta["tracking_state"] == "holding_last_good"
    assert metric.meta["reason"] in {"endpoint_jump_exceeded", "midpoint_drift_exceeded", "span_change_exceeded"}
    assert metric.point_a_px == (20, 32)
    assert metric.point_b_px == (80, 32)


def test_prior_tracking_metric_source_rejects_directional_single_frame_span_blip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = iter(
        [
            ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=100.0,
                quality=0.95,
                point_a_px=(20, 32),
                point_b_px=(120, 32),
                meta={"selection_mode": "directional_contour_max_chord"},
            ),
            ShapeMetric(
                timestamp_ms=2,
                metric_name="directional_contour_span",
                metric_raw=90.0,
                quality=0.95,
                point_a_px=(20, 32),
                point_b_px=(110, 32),
                meta={"selection_mode": "directional_contour_max_chord"},
            ),
        ]
    )

    class FakeDirectionalExtractor:
        def __init__(self, config):
            del config

        def extract(self, frame):
            del frame
            return next(observations)

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=180, height=64),
        metric_box=MetricBox(center_x=70, center_y=32, width=120, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=32),
        point_b_px=PixelPoint(x=120, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="max_chord",
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=20.0,
        max_midpoint_drift_px=20.0,
        max_span_change_ratio=0.20,
    )

    source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=2,
    )
    metric = source.extract(
        FramePacket(timestamp_ms=2, source="fixture", image=[[0]], frame_id=2),
        TempReading(timestamp_ms=2, celsius=25.0, source="fixture"),
        sample_index=1,
        total_samples=2,
    )

    assert metric.meta["selection_mode"] == "tracking_prior_hold"
    assert metric.meta["tracking_state"] == "holding_last_good"
    assert metric.meta["reason"] == "span_change_exceeded"
    assert metric.point_a_px == (20, 32)
    assert metric.point_b_px == (120, 32)


def test_prior_tracking_metric_source_stabilizes_large_directional_span_jitter_below_ratio_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = iter(
        [
            ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=800.0,
                quality=0.95,
                point_a_px=(100, 32),
                point_b_px=(900, 32),
                meta={"selection_mode": "directional_contour_projection"},
            ),
            ShapeMetric(
                timestamp_ms=2,
                metric_name="directional_contour_span",
                metric_raw=815.0,
                quality=0.95,
                point_a_px=(100, 32),
                point_b_px=(915, 32),
                meta={"selection_mode": "directional_contour_projection"},
            ),
        ]
    )

    class FakeDirectionalExtractor:
        def __init__(self, config):
            del config

        def extract(self, frame):
            del frame
            return next(observations)

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=1200, height=80),
        metric_box=MetricBox(center_x=500, center_y=32, width=900, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=100, y=32),
        point_b_px=PixelPoint(x=900, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="mask_projection",
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=80.0,
        max_midpoint_drift_px=80.0,
        max_span_change_ratio=0.08,
    )

    first_metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=2,
    )
    jitter_metric = source.extract(
        FramePacket(timestamp_ms=2, source="fixture", image=[[0]], frame_id=2),
        TempReading(timestamp_ms=2, celsius=25.0, source="fixture"),
        sample_index=1,
        total_samples=2,
    )

    assert first_metric.meta["tracking_state"] == "bootstrapped"
    assert jitter_metric.meta["selection_mode"] == "tracking_prior_stabilized"
    assert jitter_metric.meta["tracking_state"] == "accepted_stabilized"
    assert jitter_metric.meta["reason"] == "span_change_stabilized"
    assert jitter_metric.metric_raw == pytest.approx(806.0)
    assert jitter_metric.meta["observed_metric_raw"] == pytest.approx(815.0)
    assert jitter_metric.meta["span_change_px"] == pytest.approx(15.0)
    assert jitter_metric.meta["max_frame_span_jump_px"] == pytest.approx(6.0)
    assert jitter_metric.meta["max_soft_frame_span_jump_px"] == pytest.approx(64.0)


def test_prior_tracking_metric_source_stabilizes_high_quality_directional_span_jitter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = iter(
        [
            ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=800.0,
                quality=0.95,
                point_a_px=(100, 32),
                point_b_px=(900, 32),
                meta={"selection_mode": "directional_contour_projection"},
            ),
            ShapeMetric(
                timestamp_ms=2,
                metric_name="directional_contour_span",
                metric_raw=810.0,
                quality=0.95,
                point_a_px=(100, 32),
                point_b_px=(910, 32),
                meta={"selection_mode": "directional_contour_projection"},
            ),
        ]
    )

    class FakeDirectionalExtractor:
        def __init__(self, config):
            del config

        def extract(self, frame):
            del frame
            return next(observations)

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=1200, height=80),
        metric_box=MetricBox(center_x=500, center_y=32, width=900, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=100, y=32),
        point_b_px=PixelPoint(x=900, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="mask_projection",
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=80.0,
        max_midpoint_drift_px=80.0,
        max_span_change_ratio=0.08,
    )

    first_metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=2,
    )
    jitter_metric = source.extract(
        FramePacket(timestamp_ms=2, source="fixture", image=[[0]], frame_id=2),
        TempReading(timestamp_ms=2, celsius=25.0, source="fixture"),
        sample_index=1,
        total_samples=2,
    )

    assert first_metric.meta["tracking_state"] == "bootstrapped"
    assert jitter_metric.meta["selection_mode"] == "tracking_prior_stabilized"
    assert jitter_metric.meta["tracking_state"] == "accepted_stabilized"
    assert jitter_metric.meta["reason"] == "span_change_stabilized"
    assert jitter_metric.metric_raw == pytest.approx(806.0)
    assert jitter_metric.meta["observed_metric_raw"] == pytest.approx(810.0)
    assert jitter_metric.meta["span_change_px"] == pytest.approx(10.0)
    assert jitter_metric.meta["stabilized_span_change_px"] == pytest.approx(6.0)
    assert jitter_metric.meta["max_frame_span_jump_px"] == pytest.approx(6.0)
    assert jitter_metric.meta["max_soft_frame_span_jump_px"] == pytest.approx(64.0)
    assert jitter_metric.quality == pytest.approx(0.95)


def test_prior_tracking_metric_source_stabilizes_large_same_axis_span_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = iter(
        [
            ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=979.0,
                quality=0.88,
                point_a_px=(753, 64),
                point_b_px=(1732, 64),
                meta={"selection_mode": "directional_contour_projection"},
            ),
            ShapeMetric(
                timestamp_ms=2,
                metric_name="directional_contour_span",
                metric_raw=953.0,
                quality=0.87,
                point_a_px=(779, 64),
                point_b_px=(1732, 64),
                meta={"selection_mode": "directional_contour_projection"},
            ),
        ]
    )

    class FakeDirectionalExtractor:
        def __init__(self, config):
            del config

        def extract(self, frame):
            del frame
            return next(observations)

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=700, y=0, width=1150, height=128),
        metric_box=MetricBox(center_x=1275, center_y=64, width=1150, height=128, angle_deg=0.0),
        point_a_px=PixelPoint(x=753, y=64),
        point_b_px=PixelPoint(x=1732, y=64),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="mask_projection",
    )
    source = PriorTrackingMetricSource(definition=definition)

    source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=2,
    )
    step_metric = source.extract(
        FramePacket(timestamp_ms=2, source="fixture", image=[[0]], frame_id=2),
        TempReading(timestamp_ms=2, celsius=25.1, source="fixture"),
        sample_index=1,
        total_samples=2,
    )

    assert step_metric.meta["selection_mode"] == "tracking_prior_stabilized"
    assert step_metric.meta["tracking_state"] == "accepted_stabilized"
    assert step_metric.meta["reason"] == "span_change_stabilized"
    assert step_metric.metric_raw == pytest.approx(972.0)
    assert step_metric.meta["observed_metric_raw"] == pytest.approx(953.0)
    assert step_metric.meta["span_change_px"] == pytest.approx(26.0)
    assert step_metric.meta["stabilized_span_change_px"] == pytest.approx(7.0)
    assert step_metric.quality == pytest.approx(0.87)


def test_prior_tracking_metric_source_reacquires_after_transient_bad_frame() -> None:
    source = PriorTrackingMetricSource(
        definition=_definition(),
        max_endpoint_jump_px=12.0,
        max_midpoint_drift_px=8.0,
        max_span_change_ratio=0.20,
        max_consecutive_misses=2,
    )
    first_metric = source.extract(
        FramePacket(
            timestamp_ms=1,
            source="fixture",
            image=_fixture_image((24, 20, 48, 24)),
            frame_id=1,
        ),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=3,
    )
    held_metric = source.extract(
        FramePacket(
            timestamp_ms=2,
            source="fixture",
            image=_fixture_image((2, 20, 30, 24)),
            frame_id=2,
        ),
        TempReading(timestamp_ms=2, celsius=25.0, source="fixture"),
        sample_index=1,
        total_samples=3,
    )
    reacquired_metric = source.extract(
        FramePacket(
            timestamp_ms=3,
            source="fixture",
            image=_fixture_image((24, 20, 48, 24)),
            frame_id=3,
        ),
        TempReading(timestamp_ms=3, celsius=25.0, source="fixture"),
        sample_index=2,
        total_samples=3,
    )

    assert held_metric.meta["selection_mode"] == "tracking_prior_hold"
    assert reacquired_metric.meta["tracking_state"] == "reacquired"
    assert reacquired_metric.meta["selection_mode"] == "roi_local_horizontal_boundary"
    assert reacquired_metric.point_a_px == first_metric.point_a_px
    assert reacquired_metric.point_b_px == first_metric.point_b_px


def test_prior_tracking_metric_source_rejects_bad_bootstrap_observation() -> None:
    source = PriorTrackingMetricSource(
        definition=_definition(),
        max_endpoint_jump_px=12.0,
        max_midpoint_drift_px=8.0,
        max_span_change_ratio=0.20,
        max_consecutive_misses=2,
    )
    rejected_bootstrap = source.extract(
        FramePacket(
            timestamp_ms=1,
            source="fixture",
            image=_fixture_image((2, 20, 30, 24)),
            frame_id=1,
        ),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=3,
    )
    recovered_bootstrap = source.extract(
        FramePacket(
            timestamp_ms=2,
            source="fixture",
            image=_fixture_image((24, 20, 48, 24)),
            frame_id=2,
        ),
        TempReading(timestamp_ms=2, celsius=25.0, source="fixture"),
        sample_index=1,
        total_samples=3,
    )

    assert rejected_bootstrap.meta["selection_mode"] == "tracking_prior_hold"
    assert rejected_bootstrap.meta["tracking_state"] == "holding_last_good"
    assert rejected_bootstrap.meta["reason"] in {"endpoint_jump_exceeded", "midpoint_drift_exceeded"}
    assert rejected_bootstrap.point_a_px == (_definition().point_a_px.x, _definition().point_a_px.y)
    assert rejected_bootstrap.point_b_px == (_definition().point_b_px.x, _definition().point_b_px.y)
    assert recovered_bootstrap.meta["tracking_state"] == "bootstrapped"
    assert recovered_bootstrap.meta["selection_mode"] == "roi_local_horizontal_boundary"


def test_prior_tracking_metric_source_invalidates_after_too_many_rejections() -> None:
    source = PriorTrackingMetricSource(
        definition=_definition(),
        max_endpoint_jump_px=12.0,
        max_midpoint_drift_px=8.0,
        max_span_change_ratio=0.20,
        max_consecutive_misses=1,
    )
    source.extract(
        FramePacket(
            timestamp_ms=1,
            source="fixture",
            image=_fixture_image((24, 20, 48, 24)),
            frame_id=1,
        ),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=3,
    )
    source.extract(
        FramePacket(
            timestamp_ms=2,
            source="fixture",
            image=_fixture_image((2, 20, 30, 24)),
            frame_id=2,
        ),
        TempReading(timestamp_ms=2, celsius=25.0, source="fixture"),
        sample_index=1,
        total_samples=3,
    )
    invalidated_metric = source.extract(
        FramePacket(
            timestamp_ms=3,
            source="fixture",
            image=_fixture_image((2, 20, 30, 24)),
            frame_id=3,
        ),
        TempReading(timestamp_ms=3, celsius=25.0, source="fixture"),
        sample_index=2,
        total_samples=3,
    )

    assert invalidated_metric.meta["selection_mode"] == "tracking_prior_hold"
    assert invalidated_metric.meta["tracking_state"] == "invalidated"
    assert invalidated_metric.meta["reason"] == "tracking_prior_exhausted"
    assert invalidated_metric.quality == 0.0


def test_workflow_definition_payload_includes_directional_fields() -> None:
    definition = _definition()
    definition.direction_angle_deg = 0.0
    definition.direction_projection_mode = "max_chord"

    payload = _definition_payload(definition)

    assert payload["direction_angle_deg"] == 0.0
    assert payload["direction_projection_mode"] == "max_chord"


def test_live_run_coordinator_raises_when_artifact_finalize_fails(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = FailingArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = MockTempController()

    try:
        coordinator.run(
            session_id="run-finalize-fail",
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
        )
    except RuntimeError as exc:
        assert str(exc) == "artifact finalize failed"
    else:
        raise AssertionError("expected finalize failure to propagate")


def test_live_run_coordinator_uses_source_timestamps_for_cadence_summary(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    camera = SequencedCamera([1_000, 1_200, 1_400])
    temp_controller = SequencedTempController(
        timestamps_ms=[1_005, 1_205, 1_405],
        celsius_values=[35.0, 45.0, 55.0],
    )
    run_config = _runtime_run_config()
    run_config.capture_interval_ms = 50
    run_config.measurement_target_hz = 5.0

    execution = coordinator.run(
        session_id="run-cadence",
        definition=definition,
        target_temperature_celsius=55.0,
        run_config=run_config,
        analysis_engine="afas",
        channel_name="Space1",
        as_fit_point_count=5,
        af_fit_point_count=5,
        camera=camera,
        temp_reader=temp_controller,
        temp_controller=temp_controller,
        metric_source=MockLiveMetricSource(definition=definition, target_temperature_celsius=55.0),
    )

    assert execution.telemetry[0]["timestamp_ms"] == 1_005
    assert execution.telemetry[1]["sample_interval_ms"] == 200
    assert execution.telemetry[2]["frame_id"] == 3
    assert execution.telemetry[2]["frame_timestamp_ms"] == 1_400
    assert execution.detail["rates"]["measurement_sample_hz"] == 5.0
    assert execution.result["rates"]["measurement_sample_hz"] == 5.0
    assert execution.result["warnings"] == []


def test_live_run_coordinator_records_cadence_warning_when_below_target(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    camera = SequencedCamera([1_000, 1_200, 1_400])
    temp_controller = SequencedTempController(
        timestamps_ms=[1_005, 1_205, 1_405],
        celsius_values=[35.0, 45.0, 55.0],
    )
    run_config = _runtime_run_config()
    run_config.capture_interval_ms = 50
    run_config.measurement_target_hz = 50.0

    execution = coordinator.run(
        session_id="run-cadence-warning",
        definition=definition,
        target_temperature_celsius=55.0,
        run_config=run_config,
        analysis_engine="afas",
        channel_name="Space1",
        as_fit_point_count=5,
        af_fit_point_count=5,
        camera=camera,
        temp_reader=temp_controller,
        temp_controller=temp_controller,
        metric_source=MockLiveMetricSource(definition=definition, target_temperature_celsius=55.0),
    )

    assert execution.detail["warnings"] == execution.result["warnings"]
    assert execution.result["warnings"] == [
        "measurement cadence below target: achieved 5.00 Hz < target 50.00 Hz"
    ]
    assert any(event["type"] == "measurement_cadence_assessed" for event in execution.events)


def test_live_run_coordinator_does_not_fail_early_for_low_target_before_target_is_reached(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    camera = SequencedCamera([1_000, 1_100, 1_200, 1_300])
    temp_controller = SequencedTempController(
        timestamps_ms=[1_005, 1_105, 1_205, 1_305],
        celsius_values=[6.0, 9.0, 12.0, 14.0],
    )
    run_config = _runtime_run_config()
    run_config.capture_interval_ms = 50
    run_config.manual_stop_max_samples = 10

    execution = coordinator.run(
        session_id="run-low-target-progression",
        definition=definition,
        target_temperature_celsius=14.0,
        run_config=run_config,
        analysis_engine="afas",
        channel_name="Space1",
        as_fit_point_count=5,
        af_fit_point_count=5,
        camera=camera,
        temp_reader=temp_controller,
        temp_controller=temp_controller,
        metric_source=MockLiveMetricSource(definition=definition, target_temperature_celsius=14.0),
    )

    assert execution.summary.state == "completed"
    assert execution.detail["point_count"] == 4
    assert execution.telemetry[-1]["temperature_celsius"] == 14.0


def test_resolve_measurement_interval_ms_prefers_target_hz_over_legacy_capture_interval() -> None:
    run_config = _runtime_run_config()
    run_config.capture_interval_ms = 500
    run_config.measurement_target_hz = 50.0

    assert resolve_measurement_interval_ms(run_config) == 20


def test_resolve_measurement_interval_ms_keeps_playback_observable_when_target_stop_enabled() -> None:
    run_config = _runtime_run_config()
    run_config.capture_interval_ms = 500
    run_config.measurement_target_hz = 10.0

    assert (
        resolve_measurement_interval_ms(
            run_config,
            playback_sample_count=5_807,
            stop_on_target_reached=True,
        )
        == 100
    )


def test_resolve_measurement_interval_ms_falls_back_to_capture_interval_when_target_missing() -> None:
    run_config = _runtime_run_config()
    run_config.capture_interval_ms = 125
    run_config.measurement_target_hz = None

    assert resolve_measurement_interval_ms(run_config) == 125
