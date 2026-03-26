from src.application.runtime_config import RuntimeConfig, WebAppConfig
from src.camera.mock_camera import MockCamera
from src.core.enums import ObservationAxis
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion, ShapeMetric, TempReading
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SqliteSessionRepo
from src.temp.mock_temp import MockTempController
from src.workflow.live_run import LiveRunCoordinator, LockedDefinitionMetricSource, MockLiveMetricSource, resolve_measurement_interval_ms


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


def test_live_run_coordinator_keeps_running_when_invalid_tracking_does_not_abort(tmp_path) -> None:
    definition = _definition()
    repo = SqliteSessionRepo(tmp_path / "sessions.db")
    artifact_store = SessionArtifactStore(tmp_path / "artifacts")
    coordinator = LiveRunCoordinator(repo=repo, artifact_store=artifact_store)
    temp_controller = MockTempController()
    run_config = _runtime_run_config()
    run_config.stop_on_invalid_tracking = False

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
    )

    assert execution.summary.state == "completed"
    assert execution.telemetry
    assert all(row["tracking_quality"] == 0.2 for row in execution.telemetry)
    assert any(event["type"] == "tracking_invalidated" for event in execution.events)


def test_locked_definition_metric_source_respects_short_axis_observation_direction() -> None:
    definition = _definition()
    definition.observation_axis = ObservationAxis.SHORT_AXIS
    definition.metric_box = MetricBox(center_x=48, center_y=32, width=80, height=24, angle_deg=0.0)
    image = [[220 for _ in range(96)] for _ in range(64)]
    for row in range(20, 44):
        for col in range(24, 72):
            image[row][col] = 40

    source = LockedDefinitionMetricSource(definition=definition)
    metric = source.extract(
        FramePacket(timestamp_ms=1, source="fixture", image=image),
        TempReading(timestamp_ms=1, celsius=25.0, source="fixture"),
        sample_index=0,
        total_samples=1,
    )

    assert metric.metric_raw == 23.0
    assert metric.point_a_px == (47, 20)
    assert metric.point_b_px == (47, 43)
    assert metric.meta["measurement_axis_deg"] == 90.0


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


def test_resolve_measurement_interval_ms_prefers_target_hz_over_legacy_capture_interval() -> None:
    run_config = _runtime_run_config()
    run_config.capture_interval_ms = 500
    run_config.measurement_target_hz = 50.0

    assert resolve_measurement_interval_ms(run_config) == 20


def test_resolve_measurement_interval_ms_falls_back_to_capture_interval_when_target_missing() -> None:
    run_config = _runtime_run_config()
    run_config.capture_interval_ms = 125
    run_config.measurement_target_hz = None

    assert resolve_measurement_interval_ms(run_config) == 125
