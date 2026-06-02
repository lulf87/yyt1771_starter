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
                "target_geometry_mode": "line_bundle",
                "projection_point_mode": "envelope_max_width",
                "selected_component_count": 3,
                "envelope_candidate_count": 5,
                "side_guard_foreground_area": 2,
                "envelope_support_px": 17,
                "axis_offset_px": 92.0,
            },
        ),
    )

    row = _telemetry_row(sync_point, sample_index=0, previous_timestamp_ms=None)

    assert row["source_point_a_px"] == [70, 112]
    assert row["source_point_b_px"] == [290, 72]
    assert row["axis_point_a_px"] == [80, 92]
    assert row["axis_point_b_px"] == [280, 92]
    assert row["target_geometry_mode"] == "line_bundle"
    assert row["projection_point_mode"] == "envelope_max_width"
    assert row["selected_component_count"] == 3
    assert row["envelope_candidate_count"] == 5
    assert row["side_guard_foreground_area"] == 2
    assert row["envelope_support_px"] == 17
    assert row["axis_offset_px"] == 92.0


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
    assert "target_temperature_not_reached" in execution.result["result_detail"]
    assert execution.result["artifacts"]["afas_dataset"] == "afas_dataset.json"
    assert any("terminal_failed" in warning for warning in execution.result["warnings"])
    assert execution.afas_dataset is not None
    assert execution.afas_dataset["live_result_snapshot"]["result_status"] == "ok"
    assert execution.afas_dataset["live_result_snapshot"]["terminal_state"] == "failed"
    assert "target_temperature_not_reached" in execution.afas_dataset["live_result_snapshot"]["result_detail"]


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
    assert config.projection_mode == "max_chord"
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


def test_prior_tracking_metric_source_accepts_single_component_envelope_global_relocation_without_endpoint_prior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = iter(
        [
            ShapeMetric(
                timestamp_ms=1,
                metric_name="directional_contour_span",
                metric_raw=60.0,
                quality=0.95,
                point_a_px=(20, 32),
                point_b_px=(80, 32),
                meta={
                    "selection_mode": "directional_contour_envelope_max_width",
                    "projection_point_mode": "envelope_max_width",
                },
            ),
            ShapeMetric(
                timestamp_ms=2,
                metric_name="directional_contour_span",
                metric_raw=60.0,
                quality=0.95,
                point_a_px=(20, 54),
                point_b_px=(80, 54),
                meta={
                    "selection_mode": "directional_contour_envelope_max_width",
                    "projection_point_mode": "envelope_max_width",
                },
            ),
            ShapeMetric(
                timestamp_ms=3,
                metric_name="directional_contour_span",
                metric_raw=60.0,
                quality=0.95,
                point_a_px=(20, 54),
                point_b_px=(80, 54),
                meta={
                    "selection_mode": "directional_contour_envelope_max_width",
                    "projection_point_mode": "envelope_max_width",
                },
            ),
        ]
    )

    class FakeDirectionalExtractor:
        def __init__(self, config):
            assert config.projection_mode == "envelope_max_width"
            assert config.target_geometry_mode == "single_component"
            assert config.max_chord_axis_prior_point is None
            assert config.max_chord_prior_point_a is None

        def extract(self, frame):
            del frame
            return next(observations)

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=160, height=80),
        metric_box=MetricBox(center_x=80, center_y=40, width=140, height=60, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=32),
        point_b_px=PixelPoint(x=80, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="envelope_max_width",
        target_geometry_mode="single_component",
        side_guard_ratio=0.10,
        envelope_relocate_confirm_frames=2,
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=5.0,
        max_midpoint_drift_px=5.0,
        max_span_change_ratio=0.02,
    )

    first = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=[[0]], frame_id=1),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=3,
    )
    pending = source.extract(
        FramePacket(timestamp_ms=2, source="fixture", image=[[0]], frame_id=2),
        TempReading(timestamp_ms=2, celsius=25.0, source="fixture"),
        sample_index=1,
        total_samples=3,
    )
    relocated = source.extract(
        FramePacket(timestamp_ms=3, source="fixture", image=[[0]], frame_id=3),
        TempReading(timestamp_ms=3, celsius=25.0, source="fixture"),
        sample_index=2,
        total_samples=3,
    )

    # A near-equal span that jumps laterally is held for one frame and only
    # committed once the relocation repeats (two-frame confirmation), without
    # ever consulting a max_chord endpoint prior.
    assert first.meta["tracking_state"] in {"bootstrapped_global_envelope", "accepted_global_envelope"}
    assert pending.meta["tracking_state"] == "envelope_pending_relocation"
    assert pending.meta["reason"] == "envelope_relocation_pending"
    assert pending.point_a_px == (20, 32)
    assert relocated.meta["tracking_state"] == "envelope_relocated"
    assert relocated.meta["selection_mode"] == "directional_contour_envelope_max_width"
    assert relocated.point_a_px == (20, 54)
    assert relocated.point_b_px == (80, 54)


def _envelope_definition(
    *,
    target_geometry_mode: str = "line_bundle",
    envelope_min_support_px: int = 3,
    envelope_endpoint_min_support_px: int = 3,
    width_extreme_mode: str = "max_width",
    point_a: tuple[int, int] = (20, 32),
    point_b: tuple[int, int] = (80, 32),
) -> MeasurementDefinition:
    return MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=160, height=80),
        metric_box=MetricBox(center_x=80, center_y=40, width=140, height=60, angle_deg=0.0),
        point_a_px=PixelPoint(x=point_a[0], y=point_a[1]),
        point_b_px=PixelPoint(x=point_b[0], y=point_b[1]),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="envelope_max_width",
        width_extreme_mode=width_extreme_mode,
        target_geometry_mode=target_geometry_mode,
        side_guard_ratio=0.10,
        envelope_min_support_px=envelope_min_support_px,
        envelope_endpoint_min_support_px=envelope_endpoint_min_support_px,
    )


def _fake_directional_extractor(holder: dict, *, expected_projection_mode: str):
    class FakeDirectionalExtractor:
        def __init__(self, config):
            assert config.projection_mode == expected_projection_mode
            if "expected_width_extreme_mode" in holder:
                assert config.width_extreme_mode == holder["expected_width_extreme_mode"]

        def extract(self, frame):
            spec = holder["value"]
            meta = {
                "selection_mode": spec.get(
                    "selection_mode", "directional_contour_envelope_max_width"
                ),
                "projection_point_mode": spec.get("projection_point_mode", "envelope_max_width"),
                "width_extreme_mode": spec.get(
                    "width_extreme_mode",
                    holder.get("expected_width_extreme_mode", "max_width"),
                ),
                "selected_width_extreme_mode": spec.get(
                    "selected_width_extreme_mode",
                    spec.get("width_extreme_mode", holder.get("expected_width_extreme_mode", "max_width")),
                ),
                "candidate_selection_goal": spec.get("candidate_selection_goal", "max_span"),
                "candidate_span_floor_px": spec.get("candidate_span_floor_px", 5.0),
                "min_width_valid_candidate_count": spec.get("min_width_valid_candidate_count"),
                "min_width_relaxed_candidate_count": spec.get("min_width_relaxed_candidate_count"),
                "max_width_valid_candidate_count": spec.get("max_width_valid_candidate_count"),
                "component_area": 400,
                "envelope_support_px": spec.get("envelope_support_px", 24),
                "endpoint_support_left_px": spec.get("endpoint_support_left_px", 8),
                "endpoint_support_right_px": spec.get("endpoint_support_right_px", 8),
                "configured_endpoint_min_support_px": spec.get("configured_endpoint_min_support_px", 3),
                "effective_endpoint_min_support_px": spec.get("effective_endpoint_min_support_px", 3),
                "configured_endpoint_support_radius_px": spec.get("configured_endpoint_support_radius_px", 3.0),
                "effective_endpoint_support_radius_px": spec.get("effective_endpoint_support_radius_px", 3.0),
                "endpoint_support_mode": spec.get("endpoint_support_mode"),
                "endpoint_support_reject_policy": spec.get("endpoint_support_reject_policy"),
                "endpoint_support_is_hard_reject": spec.get("endpoint_support_is_hard_reject"),
                "side_guard_foreground_area": spec.get("side_guard_foreground_area", 0),
                "source_point_a_px": spec.get("source_point_a_px", spec["a"]),
                "source_point_b_px": spec.get("source_point_b_px", spec["b"]),
                "source_point_a_trusted": spec.get("source_point_a_trusted", True),
                "source_point_b_trusted": spec.get("source_point_b_trusted", True),
                "source_point_a_in_analysis_roi": spec.get("source_point_a_in_analysis_roi", True),
                "source_point_b_in_analysis_roi": spec.get("source_point_b_in_analysis_roi", True),
                "source_point_a_in_metric_box": spec.get("source_point_a_in_metric_box", True),
                "source_point_b_in_metric_box": spec.get("source_point_b_in_metric_box", True),
                "envelope_source_trust_state": spec.get("envelope_source_trust_state", "trusted"),
                "sample_core_descriptor": spec.get(
                    "sample_core_descriptor",
                    {
                        "core_along_min": float(min(spec["a"][0], spec["b"][0])),
                        "core_along_max": float(max(spec["a"][0], spec["b"][0])),
                        "core_lateral_min": float(min(spec["a"][1], spec["b"][1]) - 2),
                        "core_lateral_max": float(max(spec["a"][1], spec["b"][1]) + 2),
                        "core_centroid_along": float((spec["a"][0] + spec["b"][0]) / 2),
                        "core_centroid_lateral": float((spec["a"][1] + spec["b"][1]) / 2),
                        "core_component_area": 400,
                        "core_component_count": 1,
                    },
                ),
            }
            meta.update(spec.get("meta", {}))
            return ShapeMetric(
                timestamp_ms=frame.timestamp_ms,
                metric_name="directional_contour_span",
                metric_raw=float(spec["span"]),
                quality=0.95,
                roi=(0, 0, 160, 80),
                point_a_px=tuple(spec["a"]),
                point_b_px=tuple(spec["b"]),
                meta=meta,
            )

    return FakeDirectionalExtractor


def _frame_temp(index: int) -> tuple[FramePacket, TempReading]:
    return (
        FramePacket(timestamp_ms=index, source="fixture", image=[[0]], frame_id=index),
        TempReading(timestamp_ms=index, celsius=25.0, source="fixture"),
    )


def test_prior_tracking_max_chord_stays_prior_gated_when_widest_jumps_to_top(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (20, 60), "b": (80, 60), "selection_mode": "directional_contour_max_chord", "projection_point_mode": "max_chord"}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="max_chord"),
    )
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=160, height=80),
        metric_box=MetricBox(center_x=80, center_y=40, width=140, height=60, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=60),
        point_b_px=PixelPoint(x=80, y=60),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=0.0,
        direction_projection_mode="max_chord",
    )
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    first = source.extract(frame0, temp0, sample_index=0, total_samples=2)

    # The widest chord suddenly jumps from the lower edge to the upper edge,
    # keeping the same width.
    holder["value"] = {"span": 60.0, "a": (20, 14), "b": (80, 14), "selection_mode": "directional_contour_max_chord", "projection_point_mode": "max_chord"}
    frame1, temp1 = _frame_temp(2)
    jumped = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert first.meta["tracking_state"] in {"bootstrapped", "accepted"}
    # max_chord must remain prior-gated: it does not unconditionally relocate to
    # the new widest section on the very first jumped frame.
    assert jumped.meta["tracking_state"] not in {
        "relocated",
        "accepted_relocated",
        "envelope_relocated",
    }
    assert abs(jumped.point_a_px[1] - 60) <= 6


def test_prior_tracking_envelope_line_bundle_moves_ab_to_wider_top_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (30, 60), "b": (90, 60)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(30, 60), point_b=(90, 60))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    first = source.extract(frame0, temp0, sample_index=0, total_samples=2)

    # The widest envelope section moves to the upper part of the ROI and gets
    # clearly wider.
    holder["value"] = {"span": 90.0, "a": (20, 18), "b": (110, 18)}
    frame1, temp1 = _frame_temp(2)
    relocated = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert first.meta["tracking_state"] in {"bootstrapped_global_envelope", "accepted_global_envelope"}
    assert relocated.meta["tracking_state"] == "envelope_relocated"
    assert relocated.point_a_px == (20, 18)
    assert relocated.point_b_px == (110, 18)


def test_prior_tracking_envelope_line_bundle_holds_repeated_near_tie_lateral_band(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (30, 60), "b": (90, 60)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(30, 60), point_b=(90, 60))
    definition.envelope_relocate_confirm_frames = 2
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    repeated_top = {"span": 61.0, "a": (30, 18), "b": (91, 18)}
    states = []
    points = []
    for index, spec in enumerate(
        [
            {"span": 60.0, "a": (30, 60), "b": (90, 60)},
            repeated_top,
            repeated_top,
            repeated_top,
        ]
    ):
        holder["value"] = dict(spec)
        frame, temp = _frame_temp(index + 1)
        result = source.extract(frame, temp, sample_index=index, total_samples=4)
        states.append(result.meta["tracking_state"])
        points.append((result.point_a_px, result.point_b_px))

    assert states == [
        "bootstrapped_global_envelope",
        "envelope_pending_relocation",
        "envelope_near_tie_hold",
        "envelope_near_tie_hold",
    ]
    assert all(point_a == (30, 60) and point_b == (90, 60) for point_a, point_b in points)


def test_envelope_near_tie_hold_reports_current_visual_candidate_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (30, 60), "b": (90, 60)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(30, 60), point_b=(90, 60))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    accepted = source.extract(frame0, temp0, sample_index=0, total_samples=2)

    holder["value"] = {
        "span": 61.0,
        "a": (30, 18),
        "b": (91, 18),
        "source_point_a_px": (28, 20),
        "source_point_b_px": (92, 16),
    }
    frame1, temp1 = _frame_temp(2)
    held = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert held.meta["tracking_state"] == "envelope_pending_relocation"
    assert held.point_a_px == accepted.point_a_px
    assert held.point_b_px == accepted.point_b_px
    assert held.meta["observed_point_a_px"] == (30, 18)
    assert held.meta["observed_point_b_px"] == (91, 18)
    assert held.meta["observed_source_point_a_px"] == (28, 20)
    assert held.meta["observed_source_point_b_px"] == (92, 16)


def test_prior_tracking_envelope_line_bundle_rejects_adjacent_band_inside_generic_drift_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (30, 60), "b": (90, 60)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(30, 60), point_b=(90, 60))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=48.0,
        max_midpoint_drift_px=48.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    locked = source.extract(frame0, temp0, sample_index=0, total_samples=2)

    holder["value"] = {"span": 61.0, "a": (30, 42), "b": (91, 42)}
    frame1, temp1 = _frame_temp(2)
    adjacent_band = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert locked.meta["tracking_state"] == "bootstrapped_global_envelope"
    assert adjacent_band.meta["tracking_state"] == "envelope_pending_relocation"
    assert adjacent_band.point_a_px == locked.point_a_px
    assert adjacent_band.point_b_px == locked.point_b_px


def test_prior_tracking_envelope_near_tie_does_not_jitter_between_top_and_bottom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bottom = {"span": 60.0, "a": (30, 60), "b": (90, 60)}
    top = {"span": 61.0, "a": (30, 18), "b": (90, 18)}
    holder: dict = {"value": dict(bottom)}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(30, 60), point_b=(90, 60))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    results = []
    # Alternate between a bottom and a near-equal top candidate every frame.
    sequence = [bottom, top, bottom, top, bottom, top]
    for index, spec in enumerate(sequence):
        holder["value"] = dict(spec)
        frame, temp = _frame_temp(index + 1)
        results.append(source.extract(frame, temp, sample_index=index, total_samples=len(sequence)))

    # The near-tie top candidate never repeats on two consecutive frames, so A/B
    # must never switch to the top and must never report a committed relocation.
    for result in results:
        assert result.point_a_px[1] >= 50
        assert result.meta["tracking_state"] != "envelope_relocated"


def test_envelope_live_run_uses_axis_offset_not_display_endpoint_jump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The display A/B is axis-projected, so its endpoints can slide a long way
    # ALONG the axis without the widest section moving. A candidate that keeps
    # the same lateral axis offset and span must be accepted even when the
    # display endpoint jump dwarfs the (tiny) endpoint prior: envelope tracking
    # keys off axis offset + span, never the display endpoint jump.
    holder: dict = {"value": {"span": 60.0, "a": (40, 32), "b": (100, 32)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(20, 32), point_b=(80, 32))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=5.0,  # deliberately tiny endpoint prior
        max_midpoint_drift_px=12.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    accepted = source.extract(frame0, temp0, sample_index=0, total_samples=2)

    # Same lateral axis (y) and span as the preset, but the display endpoints are
    # shifted 20 px along the axis: an endpoint-jump gate would have rejected it.
    assert accepted.meta["tracking_state"] in {"bootstrapped_global_envelope", "accepted_global_envelope"}
    assert accepted.point_a_px == (40, 32)
    assert accepted.point_b_px == (100, 32)
    assert float(accepted.meta["endpoint_jump_px"]) > source._max_endpoint_jump_px
    assert accepted.meta["candidate_axis_jump_px"] == pytest.approx(0.0, abs=1e-6)

    # A genuine lateral relocation (same span, axis offset jumps well past the
    # drift prior) is NOT silently accepted as a small update; it enters the
    # confirmation path instead.
    holder["value"] = {"span": 60.0, "a": (40, 56), "b": (100, 56)}
    frame1, temp1 = _frame_temp(2)
    relocating = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert relocating.meta["tracking_state"] == "envelope_pending_relocation"
    assert float(relocating.meta["candidate_axis_jump_px"]) > source._max_midpoint_drift_px


def test_envelope_axis_projected_points_do_not_cause_holding_last_good(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Axis-projected A/B endpoints slide ALONG the axis frame-to-frame while the
    # lateral axis offset (y) and width stay stable. None of these frames may be
    # treated as outliers/holds; they are all small continuous envelope updates.
    holder: dict = {"value": {"span": 60.0, "a": (20, 32), "b": (80, 32)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(20, 32), point_b=(80, 32))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=5.0,
        max_midpoint_drift_px=12.0,
        max_span_change_ratio=0.05,
    )

    sequence = [
        {"span": 60.0, "a": (18, 32), "b": (78, 32)},
        {"span": 60.0, "a": (30, 32), "b": (90, 32)},
        {"span": 60.0, "a": (14, 32), "b": (74, 32)},
        {"span": 60.0, "a": (36, 32), "b": (96, 32)},
        {"span": 60.0, "a": (16, 32), "b": (76, 32)},
        {"span": 60.0, "a": (24, 32), "b": (84, 32)},
    ]
    states = []
    jumps = []
    for index, spec in enumerate(sequence):
        holder["value"] = dict(spec)
        frame, temp = _frame_temp(index + 1)
        metric = source.extract(frame, temp, sample_index=index, total_samples=len(sequence))
        states.append(metric.meta["tracking_state"])
        jumps.append(float(metric.meta["endpoint_jump_px"]))

    assert "holding_last_good" not in states
    assert "invalidated" not in states
    assert all(state in {"bootstrapped_global_envelope", "accepted_global_envelope"} for state in states)
    # The display endpoints really did jump far more than the endpoint prior, so
    # the absence of holds is specifically because tracking ignores them.
    assert max(jumps) > source._max_endpoint_jump_px


def test_source_projection_rejection_does_not_update_last_good(monkeypatch: pytest.MonkeyPatch) -> None:
    holder: dict = {
        "value": {
            "span": 60.0,
            "a": (20, 32),
            "b": (80, 32),
            "source_point_a_px": (20, 32),
            "source_point_b_px": (80, 32),
        }
    }
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    source = PriorTrackingMetricSource(
        definition=_envelope_definition(point_a=(20, 32), point_b=(80, 32)),
        max_endpoint_jump_px=5.0,
        max_midpoint_drift_px=12.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    accepted = source.extract(frame0, temp0, sample_index=0, total_samples=2)
    assert accepted.meta["tracking_state"] == "bootstrapped_global_envelope"

    holder["value"] = {
        "span": 60.0,
        "a": (28, 32),
        "b": (88, 32),
        "source_point_a_px": (28, 32),
        "source_point_b_px": (88, 48),
        "meta": {
            "source_projection_reject_reason": "source_projection_too_far",
            "candidate_reject_reason": "source_projection_too_far",
            "source_projection_distance_a_px": 0.0,
            "source_projection_distance_b_px": 16.0,
            "envelope_max_source_projection_distance_px": 12.0,
        },
    }
    frame1, temp1 = _frame_temp(2)
    rejected = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert rejected.meta["tracking_state"] == "envelope_projection_offset_hold"
    assert rejected.meta["original_rejection_reason"] == "source_projection_too_far"
    assert rejected.point_a_px == (20, 32)
    assert rejected.point_b_px == (80, 32)
    assert source._last_good_point_a == PixelPoint(x=20, y=32)
    assert source._last_good_point_b == PixelPoint(x=80, y=32)


def test_live_run_min_width_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    holder: dict = {
        "expected_width_extreme_mode": "min_width",
        "value": {
            "span": 52.0,
            "a": (34, 32),
            "b": (86, 32),
            "width_extreme_mode": "min_width",
            "selected_width_extreme_mode": "min_width",
            "candidate_selection_goal": "min_span",
            "min_width_valid_candidate_count": 3,
        },
    }
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    source = PriorTrackingMetricSource(
        definition=_envelope_definition(width_extreme_mode="min_width", point_a=(20, 32), point_b=(90, 32)),
        max_endpoint_jump_px=5.0,
        max_midpoint_drift_px=10.0,
        max_span_change_ratio=0.05,
    )

    frame, temp = _frame_temp(1)
    metric = source.extract(frame, temp, sample_index=0, total_samples=1)

    assert metric.meta["tracking_state"] == "bootstrapped_min_width_envelope"
    assert metric.meta["selected_width_extreme_mode"] == "min_width"
    assert metric.meta["candidate_selection_goal"] == "min_span"
    assert metric.metric_raw == 52.0


def test_live_run_min_width_span_decrease_not_outlier(monkeypatch: pytest.MonkeyPatch) -> None:
    holder: dict = {
        "expected_width_extreme_mode": "min_width",
        "value": {"span": 60.0, "a": (30, 32), "b": (90, 32), "width_extreme_mode": "min_width"},
    }
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    source = PriorTrackingMetricSource(
        definition=_envelope_definition(width_extreme_mode="min_width", point_a=(30, 32), point_b=(90, 32)),
        max_endpoint_jump_px=5.0,
        max_midpoint_drift_px=10.0,
        max_span_change_ratio=0.05,
    )
    frame0, temp0 = _frame_temp(1)
    first = source.extract(frame0, temp0, sample_index=0, total_samples=2)

    holder["value"] = {
        "span": 44.0,
        "a": (38, 32),
        "b": (82, 32),
        "width_extreme_mode": "min_width",
        "selected_width_extreme_mode": "min_width",
        "candidate_selection_goal": "min_span",
    }
    frame1, temp1 = _frame_temp(2)
    decreased = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert first.meta["tracking_state"] == "bootstrapped_min_width_envelope"
    assert decreased.meta["tracking_state"] == "accepted_min_width_envelope"
    assert decreased.metric_raw == 44.0
    assert decreased.meta.get("reason") is None


def test_live_run_min_width_near_tie_stability(monkeypatch: pytest.MonkeyPatch) -> None:
    bottom = {
        "span": 60.0,
        "a": (30, 60),
        "b": (90, 60),
        "width_extreme_mode": "min_width",
        "selected_width_extreme_mode": "min_width",
    }
    top = {
        "span": 59.0,
        "a": (30, 18),
        "b": (89, 18),
        "width_extreme_mode": "min_width",
        "selected_width_extreme_mode": "min_width",
    }
    holder: dict = {"expected_width_extreme_mode": "min_width", "value": dict(bottom)}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    source = PriorTrackingMetricSource(
        definition=_envelope_definition(width_extreme_mode="min_width", point_a=(30, 60), point_b=(90, 60)),
        max_endpoint_jump_px=5.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    results = []
    for index, spec in enumerate([bottom, top, bottom, top]):
        holder["value"] = dict(spec)
        frame, temp = _frame_temp(index + 1)
        results.append(source.extract(frame, temp, sample_index=index, total_samples=4))

    assert results[0].meta["tracking_state"] == "bootstrapped_min_width_envelope"
    for result in results:
        assert result.point_a_px[1] >= 50
        assert result.meta["tracking_state"] != "envelope_relocated"


def test_prior_tracking_envelope_holds_last_good_for_single_frame_scratch_spike(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Frame 1 locks a well-supported global envelope. Frame 2 is a single-frame
    # background scratch that fabricates a much wider span with weak per-bin
    # support: it must hold the last good A/B (never refresh) and report the
    # outlier hold. Frame 3 returns to the genuine target and is re-accepted.
    holder: dict = {"value": {"span": 60.0, "a": (20, 32), "b": (80, 32), "envelope_support_px": 24}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(20, 32), point_b=(80, 32))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    locked = source.extract(frame0, temp0, sample_index=0, total_samples=3)

    holder["value"] = {"span": 130.0, "a": (20, 40), "b": (150, 40), "envelope_support_px": 4}
    frame1, temp1 = _frame_temp(2)
    held = source.extract(frame1, temp1, sample_index=1, total_samples=3)

    holder["value"] = {"span": 60.0, "a": (20, 32), "b": (80, 32), "envelope_support_px": 24}
    frame2, temp2 = _frame_temp(3)
    recovered = source.extract(frame2, temp2, sample_index=2, total_samples=3)

    assert locked.meta["tracking_state"] in {"bootstrapped_global_envelope", "accepted_global_envelope"}
    assert held.meta["tracking_state"] == "envelope_low_support_rejected"
    assert held.meta["envelope_reject_reason"] == "envelope_low_support"
    # The scratch never refreshes the last good A/B.
    assert held.point_a_px == (20, 32)
    assert held.point_b_px == (80, 32)
    assert source._last_good_point_b == PixelPoint(x=80, y=32)
    # The genuine target is re-accepted on the following frame.
    assert recovered.meta["tracking_state"] == "accepted_global_envelope"
    assert recovered.point_b_px == (80, 32)


def test_source_endpoint_component_must_be_trusted_and_does_not_poison_axis_prior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (20, 32), "b": (80, 32)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(20, 32), point_b=(80, 32))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    clean = source.extract(frame0, temp0, sample_index=0, total_samples=3)

    holder["value"] = {
        "span": 130.0,
        "a": (10, 56),
        "b": (140, 56),
        "source_point_a_px": (10, 56),
        "source_point_b_px": (140, 56),
        "source_point_a_trusted": False,
        "source_point_b_trusted": True,
        "envelope_source_trust_state": "detached_endpoint",
        "envelope_support_px": 32,
    }
    frame1, temp1 = _frame_temp(2)
    contaminated = source.extract(frame1, temp1, sample_index=1, total_samples=3)

    holder["value"] = {"span": 60.0, "a": (20, 32), "b": (80, 32)}
    frame2, temp2 = _frame_temp(3)
    recovered = source.extract(frame2, temp2, sample_index=2, total_samples=3)

    assert clean.meta["tracking_state"] in {"bootstrapped_global_envelope", "accepted_global_envelope"}
    assert contaminated.meta["tracking_state"] == "envelope_contaminated_hold"
    assert contaminated.meta["original_rejection_reason"] == "detached_source_endpoint"
    assert contaminated.meta["has_visual_candidate"] is True
    assert contaminated.meta["observed_metric_raw"] == pytest.approx(130.0)
    assert contaminated.point_a_px == clean.point_a_px
    assert contaminated.point_b_px == clean.point_b_px
    assert source._last_good_point_a == PixelPoint(x=20, y=32)
    assert source._last_good_point_b == PixelPoint(x=80, y=32)
    assert source._last_clean_axis_offset_px == pytest.approx(32.0)
    assert recovered.meta["tracking_state"] == "accepted_global_envelope"
    assert recovered.point_a_px == (20, 32)
    assert recovered.point_b_px == (80, 32)


def test_source_point_outside_metric_box_rejected_without_refreshing_last_good(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (20, 32), "b": (80, 32)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(20, 32), point_b=(80, 32))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    clean = source.extract(frame0, temp0, sample_index=0, total_samples=2)

    holder["value"] = {
        "span": 112.0,
        "a": (4, 32),
        "b": (116, 32),
        "source_point_a_px": (4, 32),
        "source_point_b_px": (116, 32),
        "source_point_a_in_metric_box": False,
        "source_point_b_in_metric_box": True,
        "envelope_source_trust_state": "source_outside_metric_box",
        "envelope_support_px": 32,
    }
    frame1, temp1 = _frame_temp(2)
    held = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert clean.meta["tracking_state"] in {"bootstrapped_global_envelope", "accepted_global_envelope"}
    assert held.meta["tracking_state"] == "envelope_contaminated_hold"
    assert held.meta["original_rejection_reason"] == "source_outside_metric_box"
    assert held.meta["source_point_a_in_metric_box"] is False
    assert held.point_a_px == clean.point_a_px
    assert held.point_b_px == clean.point_b_px
    assert source._last_good_span_px == pytest.approx(60.0)


def test_envelope_endpoint_weak_does_not_hard_reject_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {
        "value": {
            "span": 60.0,
            "a": (20, 32),
            "b": (80, 32),
            "endpoint_support_left_px": 1,
            "endpoint_support_right_px": 1,
            "effective_endpoint_min_support_px": 3,
            "endpoint_support_mode": "weak",
        }
    }
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    source = PriorTrackingMetricSource(
        definition=_envelope_definition(point_a=(20, 32), point_b=(80, 32), envelope_endpoint_min_support_px=3),
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    metric = source.extract(frame0, temp0, sample_index=0, total_samples=1)

    assert metric.point_a_px == (20, 32)
    assert metric.point_b_px == (80, 32)
    assert metric.meta["tracking_state"] == "bootstrapped_global_envelope_endpoint_weak"
    assert metric.meta["endpoint_support_mode"] == "weak"
    assert metric.meta["endpoint_support_is_hard_reject"] is False


def test_envelope_endpoint_weak_continuous_candidate_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (20, 32), "b": (80, 32)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    source = PriorTrackingMetricSource(
        definition=_envelope_definition(point_a=(20, 32), point_b=(80, 32), envelope_endpoint_min_support_px=3),
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    source.extract(frame0, temp0, sample_index=0, total_samples=2)

    holder["value"] = {
        "span": 61.0,
        "a": (20, 32),
        "b": (81, 32),
        "endpoint_support_left_px": 1,
        "endpoint_support_right_px": 1,
        "effective_endpoint_min_support_px": 3,
        "endpoint_support_mode": "weak",
    }
    frame1, temp1 = _frame_temp(2)
    metric = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert metric.meta["tracking_state"] == "accepted_envelope_endpoint_weak"
    assert metric.point_b_px == (81, 32)
    assert metric.meta["endpoint_support_mode"] == "weak"
    assert metric.meta["endpoint_support_is_hard_reject"] is False


def test_envelope_endpoint_weak_axis_jump_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (20, 32), "b": (80, 32)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    source = PriorTrackingMetricSource(
        definition=_envelope_definition(point_a=(20, 32), point_b=(80, 32), envelope_endpoint_min_support_px=3),
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    clean = source.extract(frame0, temp0, sample_index=0, total_samples=2)

    holder["value"] = {
        "span": 60.0,
        "a": (20, 54),
        "b": (80, 54),
        "endpoint_support_left_px": 1,
        "endpoint_support_right_px": 1,
        "effective_endpoint_min_support_px": 3,
        "endpoint_support_mode": "weak",
    }
    frame1, temp1 = _frame_temp(2)
    metric = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert metric.meta["tracking_state"] == "envelope_endpoint_weak_pending"
    assert metric.meta["reason"] == "endpoint_weak_pending"
    assert metric.point_a_px == clean.point_a_px
    assert metric.point_b_px == clean.point_b_px
    assert metric.meta["endpoint_support_is_hard_reject"] is False


def test_envelope_endpoint_weak_with_detached_source_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (20, 32), "b": (80, 32)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    source = PriorTrackingMetricSource(
        definition=_envelope_definition(point_a=(20, 32), point_b=(80, 32), envelope_endpoint_min_support_px=3),
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    clean = source.extract(frame0, temp0, sample_index=0, total_samples=2)

    holder["value"] = {
        "span": 61.0,
        "a": (20, 32),
        "b": (81, 32),
        "endpoint_support_left_px": 1,
        "endpoint_support_right_px": 1,
        "effective_endpoint_min_support_px": 3,
        "source_point_a_trusted": False,
        "envelope_source_trust_state": "detached_endpoint",
    }
    frame1, temp1 = _frame_temp(2)
    metric = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert metric.meta["tracking_state"] == "envelope_contaminated_hold"
    assert metric.meta["original_rejection_reason"] == "detached_source_endpoint"
    assert metric.point_a_px == clean.point_a_px
    assert metric.point_b_px == clean.point_b_px


def test_min_width_no_candidate_hold_reports_explicit_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {
        "value": ShapeMetric(
            timestamp_ms=1,
            metric_name="directional_contour_span",
            metric_raw=60.0,
            quality=0.95,
            roi=(0, 0, 160, 80),
            point_a_px=(20, 32),
            point_b_px=(80, 32),
            meta={
                "selection_mode": "directional_contour_envelope_max_width",
                "projection_point_mode": "envelope_max_width",
                "width_extreme_mode": "min_width",
                "selected_width_extreme_mode": "min_width",
                "candidate_selection_goal": "min_span",
                "candidate_span_floor_px": 5.0,
                "min_width_valid_candidate_count": 1,
                "min_width_relaxed_candidate_count": 0,
                "max_width_valid_candidate_count": 1,
                "envelope_support_px": 24,
                "endpoint_support_left_px": 8,
                "endpoint_support_right_px": 8,
                "source_point_a_trusted": True,
                "source_point_b_trusted": True,
                "source_point_a_in_metric_box": True,
                "source_point_b_in_metric_box": True,
                "source_point_a_in_analysis_roi": True,
                "source_point_b_in_analysis_roi": True,
                "envelope_source_trust_state": "trusted",
            },
        )
    }

    class FakeDirectionalExtractor:
        def __init__(self, config):
            assert config.projection_mode == "envelope_max_width"
            assert config.width_extreme_mode == "min_width"

        def extract(self, frame):
            metric = holder["value"]
            metric.timestamp_ms = frame.timestamp_ms
            return metric

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", FakeDirectionalExtractor)
    source = PriorTrackingMetricSource(
        definition=_envelope_definition(width_extreme_mode="min_width", point_a=(20, 32), point_b=(80, 32)),
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    clean = source.extract(frame0, temp0, sample_index=0, total_samples=2)

    holder["value"] = ShapeMetric(
        timestamp_ms=2,
        metric_name="directional_contour_span",
        metric_raw=None,
        quality=0.0,
        roi=(0, 0, 160, 80),
        meta={
            "reason": "min_width_no_effective_candidate",
            "width_extreme_mode": "min_width",
            "selected_width_extreme_mode": None,
            "candidate_selection_goal": "min_span",
            "candidate_span_floor_px": 5.0,
            "min_width_valid_candidate_count": 0,
            "min_width_relaxed_candidate_count": 0,
            "max_width_valid_candidate_count": 1,
            "min_width_reject_reason": "min_width_no_effective_candidate",
            "candidate_reject_reason": "min_width_no_effective_candidate",
            "envelope_candidate_debug": {"smallest": [], "largest": []},
        },
    )
    frame1, temp1 = _frame_temp(2)
    held = source.extract(frame1, temp1, sample_index=1, total_samples=2)

    assert held.point_a_px == clean.point_a_px
    assert held.point_b_px == clean.point_b_px
    assert held.meta["original_rejection_reason"] == "min_width_no_effective_candidate"
    assert held.meta["min_width_reject_reason"] == "min_width_no_effective_candidate"
    assert held.meta["candidate_selection_goal"] == "min_span"


def test_locked_definition_envelope_resolves_metric_box_angle_and_parallel_ab() -> None:
    # A horizontal line bundle with a stale direction_angle_deg of 90 deg. The
    # metric box angle (0 deg) is authoritative, so the live extractor must
    # measure horizontally and emit an A/B segment parallel to the box angle
    # (identical y), not along the stale 90 deg direction.
    image = np.full((64, 120), 240, dtype=np.uint8)
    image[26:30, 20:96] = 30
    image[34:38, 24:100] = 30
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=120, height=64),
        metric_box=MetricBox(center_x=60, center_y=32, width=110, height=48, angle_deg=0.0),
        point_a_px=PixelPoint(x=20, y=32),
        point_b_px=PixelPoint(x=99, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        ignore_internal_texture=True,
        min_target_area_px=20,
        direction_angle_deg=90.0,  # stale: disagrees with the metric box angle
        direction_projection_mode="envelope_max_width",
        target_geometry_mode="line_bundle",
        envelope_min_support_px=6,
    )
    source = LockedDefinitionMetricSource(definition=definition)

    frame = FramePacket(timestamp_ms=1, source="fixture", image=image, frame_id=1)
    temp = TempReading(timestamp_ms=1, celsius=25.0, source="fixture")
    metric = source.extract(frame, temp, sample_index=0, total_samples=1)

    assert metric.point_a_px is not None and metric.point_b_px is not None
    # A/B parallel to the metric box angle (0 deg): equal y within rounding.
    assert abs(metric.point_a_px[1] - metric.point_b_px[1]) <= 1
    # The horizontal span is recovered (measured along x, not the stale 90 deg).
    assert metric.metric_raw == pytest.approx(76.0, abs=8.0)
    # The live source resolves the metric box angle before vision, so vision sees
    # a consistent angle (no mismatch warning) and measures along 0 deg.
    assert metric.meta["resolved_measurement_angle_deg"] == pytest.approx(0.0, abs=1e-6)
    assert metric.meta["angle_mismatch_warning"] is False
    assert metric.meta["display_point_mode"] == "axis_projected"
    assert metric.meta["metric_raw_mode"] == "along_axis_span"
    assert "source_point_a_px" in metric.meta


def test_prior_tracking_envelope_bootstraps_live_candidate_away_from_preset_axis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Preset A/B sits on the middle band, but the first live candidate lands on a
    # lower near-tie band. With a soft preset prior the run must bootstrap the live
    # candidate instead of holding the preset for three fatal misses.
    holder: dict = {"value": {"span": 62.0, "a": (30, 70), "b": (90, 70), "envelope_support_px": 24}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(30, 30), point_b=(90, 30))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    assert source._has_runtime_lock is False
    results = []
    for index in range(3):
        frame, temp = _frame_temp(index + 1)
        results.append(source.extract(frame, temp, sample_index=index, total_samples=3))

    assert results[0].meta["tracking_state"] == "bootstrapped_global_envelope"
    assert results[0].point_a_px == (30, 70)
    assert results[0].point_b_px == (90, 70)
    assert source._has_runtime_lock is True
    assert all(result.meta["tracking_state"] == "accepted_global_envelope" for result in results[1:])
    assert "invalidated" not in {result.meta["tracking_state"] for result in results}


def test_envelope_gross_outlier_guards_reject_support_box_edge_and_side_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (30, 32), "b": (90, 32)}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(envelope_min_support_px=6, point_a=(30, 32), point_b=(90, 32))
    source = PriorTrackingMetricSource(definition=definition)

    def outlier(metric: ShapeMetric) -> bool:
        return source._envelope_candidate_is_gross_outlier(metric, source._tracking_diagnostics(metric))

    low_support = ShapeMetric(
        timestamp_ms=1,
        metric_name="directional_contour_span",
        metric_raw=60.0,
        quality=0.9,
        roi=(0, 0, 160, 80),
        point_a_px=(30, 32),
        point_b_px=(90, 32),
        meta={"envelope_support_px": 3},
    )
    box_grab = ShapeMetric(
        timestamp_ms=1,
        metric_name="directional_contour_span",
        metric_raw=140.0,
        quality=0.9,
        roi=(0, 0, 160, 80),
        point_a_px=(10, 40),
        point_b_px=(150, 40),
        meta={"envelope_support_px": 20},
    )
    side_guard_clutter = ShapeMetric(
        timestamp_ms=1,
        metric_name="directional_contour_span",
        metric_raw=40.0,
        quality=0.9,
        roi=(0, 0, 160, 80),
        point_a_px=(40, 32),
        point_b_px=(80, 32),
        meta={"envelope_support_px": 20, "side_guard_foreground_area": 99999},
    )
    good = ShapeMetric(
        timestamp_ms=1,
        metric_name="directional_contour_span",
        metric_raw=60.0,
        quality=0.9,
        roi=(0, 0, 160, 80),
        point_a_px=(30, 32),
        point_b_px=(90, 32),
        meta={"envelope_support_px": 20, "side_guard_foreground_area": 12},
    )

    assert outlier(low_support) is True
    assert outlier(box_grab) is True
    assert outlier(side_guard_clutter) is True
    assert outlier(good) is False


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
    definition.width_extreme_mode = "min_width"

    payload = _definition_payload(definition)

    assert payload["direction_angle_deg"] == 0.0
    assert payload["direction_projection_mode"] == "max_chord"
    assert payload["width_extreme_mode"] == "min_width"


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


def test_envelope_bootstrap_does_not_start_locked_on_preset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (40, 32), "b": (100, 32), "envelope_support_px": 24}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(20, 32), point_b=(80, 32))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    assert source._has_runtime_lock is False
    frame, temp = _frame_temp(1)
    metric = source.extract(frame, temp, sample_index=0, total_samples=1)

    assert metric.meta["tracking_state"] == "bootstrapped_global_envelope"
    assert source._has_runtime_lock is True
    assert metric.point_a_px == (40, 32)
    assert metric.point_b_px == (100, 32)


def test_envelope_visual_candidate_rejected_is_nonfatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 60.0, "a": (20, 32), "b": (80, 32), "envelope_support_px": 24}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(20, 32), point_b=(80, 32))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame0, temp0 = _frame_temp(1)
    source.extract(frame0, temp0, sample_index=0, total_samples=6)

    states = []
    for index in range(1, 6):
        holder["value"] = {
            "span": 130.0,
            "a": (20, 40),
            "b": (150, 40),
            "envelope_support_px": 4,
        }
        frame, temp = _frame_temp(index + 1)
        metric = source.extract(frame, temp, sample_index=index, total_samples=6)
        states.append(metric.meta["tracking_state"])

    assert states == ["envelope_low_support_rejected"] * 5
    assert "invalidated" not in states
    assert source._consecutive_misses == 0
    assert source._nonfatal_reject_count == 5


def test_envelope_candidate_can_establish_runtime_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": {"span": 62.0, "a": (30, 56), "b": (90, 56), "envelope_support_px": 28}}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(30, 30), point_b=(90, 30))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
    )

    frame, temp = _frame_temp(1)
    metric = source.extract(frame, temp, sample_index=0, total_samples=1)

    assert source._has_runtime_lock is True
    assert metric.meta["tracking_state"] == "bootstrapped_global_envelope"
    assert float(metric.meta["candidate_axis_jump_px"]) > source._max_midpoint_drift_px


def test_envelope_prior_exhausted_preserves_original_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder: dict = {"value": None}
    monkeypatch.setattr(
        "src.workflow.live_run.DirectionalContourMetricExtractor",
        _fake_directional_extractor(holder, expected_projection_mode="envelope_max_width"),
    )
    definition = _envelope_definition(point_a=(20, 32), point_b=(80, 32))
    source = PriorTrackingMetricSource(
        definition=definition,
        max_endpoint_jump_px=6.0,
        max_midpoint_drift_px=6.0,
        max_span_change_ratio=0.05,
        max_consecutive_misses=2,
    )

    class EmptyExtractor:
        def __init__(self, config):
            pass

        def extract(self, frame):
            return ShapeMetric(
                timestamp_ms=frame.timestamp_ms,
                metric_name="directional_contour_span",
                metric_raw=None,
                quality=0.0,
                roi=(0, 0, 160, 80),
                point_a_px=None,
                point_b_px=None,
                meta={"reason": "envelope_observation_unavailable"},
            )

    monkeypatch.setattr("src.workflow.live_run.DirectionalContourMetricExtractor", EmptyExtractor)

    metrics = []
    for index in range(3):
        frame, temp = _frame_temp(index + 1)
        metrics.append(source.extract(frame, temp, sample_index=index, total_samples=3))

    assert metrics[-1].meta["tracking_state"] == "invalidated"
    assert metrics[-1].meta["reason"] == "tracking_prior_exhausted"
    assert metrics[-1].meta["original_rejection_reason"] == "envelope_observation_unavailable"
