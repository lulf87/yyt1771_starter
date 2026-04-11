"""Phase 3 live-run orchestration with a synchronous mock-first coordinator."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any, Callable, Protocol

from src.core.config_models import CameraAcquisitionProfileConfig, CameraRuntimeConfig, RunRuntimeConfig
from src.core.enums import CaptureMode, ObservationAxis, RunStatus
from src.core.contracts import CameraPort, TempControllerPort, TempReader
from src.core.models import (
    FramePacket,
    MeasurementDefinition,
    MeasurementProfileSnapshot,
    PixelPoint,
    RectRegion,
    RunRateSnapshot,
    ShapeMetric,
    SyncPoint,
    TempReading,
)
from src.curve.af95 import normalize_sync_points
from src.curve.afas import AfasAnalysisResult, analyze_afas
from src.curve.mock_afas_curve_playback import MockAfasCurvePlayback
from src.curve.afas_postprocessing_dataset import build_afas_postprocessing_dataset
from src.report.summary import build_live_run_result
from src.storage.session_artifacts import SessionArtifactStore
from src.storage.sqlite_repo import SessionSummary
from src.sync.hub import SyncHub
from src.vision.metric_two_point_distance import TwoPointDistanceMetricExtractor


class SessionSummaryRepo(Protocol):
    def save_summary(self, summary: SessionSummary) -> None:
        """Persist one session summary."""


class LiveMetricSource(Protocol):
    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        """Return one shape metric sample for a live run."""


@dataclass(slots=True)
class LiveRunExecution:
    summary: SessionSummary
    detail: dict[str, Any]
    result: dict[str, Any]
    telemetry: list[dict[str, Any]]
    events: list[dict[str, Any]]


class LiveRunStopRequested(RuntimeError):
    """Raised when the operator stops a live run."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


class LiveRunTrackingInvalidated(LiveRunStopRequested):
    """Raised when tracking quality is no longer acceptable."""


class MockLiveMetricSource:
    """Deterministic metric generator for Phase 3 mock runs."""

    def __init__(self, definition: MeasurementDefinition, target_temperature_celsius: float, start_celsius: float = 25.0) -> None:
        self.definition = definition
        self.target_temperature_celsius = float(target_temperature_celsius)
        self.start_celsius = float(start_celsius)
        self._base_a = definition.point_a_px
        self._base_b = definition.point_b_px
        delta_x = self._base_b.x - self._base_a.x
        delta_y = self._base_b.y - self._base_a.y
        self._baseline_px = math.hypot(delta_x, delta_y)
        if self._baseline_px <= 0:
            raise ValueError("measurement definition points must not overlap")
        self._unit_x = delta_x / self._baseline_px
        self._unit_y = delta_y / self._baseline_px

    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        progress = 1.0
        denominator = self.target_temperature_celsius - self.start_celsius
        if denominator > 0:
            progress = max(0.0, min(1.0, (temp.celsius - self.start_celsius) / denominator))
        curve_progress = progress * progress * (3.0 - 2.0 * progress)
        expansion_px = self._baseline_px * 0.15 * curve_progress
        offset_px = expansion_px / 2.0

        point_a_x = self._base_a.x - self._unit_x * offset_px
        point_a_y = self._base_a.y - self._unit_y * offset_px
        point_b_x = self._base_b.x + self._unit_x * offset_px
        point_b_y = self._base_b.y + self._unit_y * offset_px

        max_x = (len(frame.image[0]) - 1) if frame.image and frame.image[0] else max(self._base_a.x, self._base_b.x)
        max_y = (len(frame.image) - 1) if frame.image else max(self._base_a.y, self._base_b.y)

        point_a = (
            int(max(0, min(max_x, round(point_a_x)))),
            int(max(0, min(max_y, round(point_a_y)))),
        )
        point_b = (
            int(max(0, min(max_x, round(point_b_x)))),
            int(max(0, min(max_y, round(point_b_y)))),
        )
        metric_raw = math.hypot(point_b[0] - point_a[0], point_b[1] - point_a[1])
        midpoint = (
            int(round((point_a[0] + point_b[0]) / 2)),
            int(round((point_a[1] + point_b[1]) / 2)),
        )
        return ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=metric_raw,
            quality=max(0.85, 0.98 - progress * 0.03),
            feature_point_px=midpoint,
            point_a_px=point_a,
            point_b_px=point_b,
            baseline_px=self._baseline_px,
            meta={
                "selection_mode": "mock_tracking",
                "progress": progress,
                "curve_progress": curve_progress,
                "sample_index": sample_index,
                "total_samples": total_samples,
            },
        )


class WorkbookPlaybackMetricSource:
    """Metric source that replays AFAS workbook values during mock live runs."""

    def __init__(self, definition: MeasurementDefinition, playback: MockAfasCurvePlayback) -> None:
        self.definition = definition
        self.playback = playback
        self._base_a = definition.point_a_px
        self._base_b = definition.point_b_px
        delta_x = self._base_b.x - self._base_a.x
        delta_y = self._base_b.y - self._base_a.y
        self._baseline_px = math.hypot(delta_x, delta_y)
        if self._baseline_px <= 0:
            raise ValueError("measurement definition points must not overlap")
        self._unit_x = delta_x / self._baseline_px
        self._unit_y = delta_y / self._baseline_px
        self._center_x = (self._base_a.x + self._base_b.x) / 2.0
        self._center_y = (self._base_a.y + self._base_b.y) / 2.0

    def playback_sample_count(self) -> int:
        return int(self.playback.sample_count)

    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        resolved_index = min(max(int(sample_index), 0), self.playback.sample_count - 1)
        metric_raw = float(self.playback.values[resolved_index])
        projected_span_px = max(2.0, abs(metric_raw))
        point_a, point_b = _points_for_projected_span(
            frame=frame,
            center_x=self._center_x,
            center_y=self._center_y,
            unit_x=self._unit_x,
            unit_y=self._unit_y,
            span_px=projected_span_px,
        )
        midpoint = (
            int(round((point_a[0] + point_b[0]) / 2)),
            int(round((point_a[1] + point_b[1]) / 2)),
        )
        return ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=metric_raw,
            quality=0.99,
            feature_point_px=midpoint,
            point_a_px=point_a,
            point_b_px=point_b,
            baseline_px=self._baseline_px,
            meta={
                "selection_mode": "mock_afas_curve_playback",
                "sheet_name": self.playback.sheet_name,
                "channel_name": self.playback.channel_name,
                "sample_index": resolved_index,
                "total_samples": total_samples,
                "playback_sample_count": self.playback.sample_count,
                "playback_workbook_path": self.playback.workbook_path,
            },
        )


class LockedDefinitionMetricSource:
    """Definition-locked extractor used when mock metric generation is unavailable."""

    def __init__(
        self,
        definition: MeasurementDefinition,
        *,
        debug_locked_points: bool = False,
        working_max_width: int | None = None,
        working_max_height: int | None = None,
    ) -> None:
        measurement_axis_deg = float(definition.metric_box.angle_deg)
        selection_strategy = "roi_local_horizontal_boundary"
        if definition.observation_axis == ObservationAxis.SHORT_AXIS:
            measurement_axis_deg += 90.0
            selection_strategy = "auto_extremes"
        self._extractor = TwoPointDistanceMetricExtractor(
            analysis_roi=definition.analysis_roi,
            metric_box=definition.metric_box,
            measurement_axis_deg=measurement_axis_deg,
            foreground_polarity=definition.foreground_polarity,
            threshold_mode=definition.threshold_mode,
            ignore_internal_texture=definition.ignore_internal_texture,
            min_target_area_px=definition.min_target_area_px,
            sensitivity=definition.sensitivity,
            selection_strategy=selection_strategy,
            locked_points=(definition.point_a_px, definition.point_b_px) if debug_locked_points else None,
            working_max_width=working_max_width,
            working_max_height=working_max_height,
        )

    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        metric = self._extractor.extract(frame)
        metric.timestamp_ms = temp.timestamp_ms
        metric.meta["sample_index"] = sample_index
        metric.meta["total_samples"] = total_samples
        return metric


class PriorTrackingMetricSource:
    """Stateful real-camera tracker that gates extractor observations with temporal priors."""

    def __init__(
        self,
        definition: MeasurementDefinition,
        *,
        max_endpoint_jump_px: float | None = None,
        max_midpoint_drift_px: float | None = None,
        max_span_change_ratio: float = 0.35,
        max_consecutive_misses: int = 3,
        hold_quality: float = 0.8,
    ) -> None:
        self._observation_source = LockedDefinitionMetricSource(
            definition=definition,
            working_max_width=256,
            working_max_height=160,
        )
        self._tracking_mode = "prior_gated_reacquire"
        self._last_good_point_a = definition.point_a_px
        self._last_good_point_b = definition.point_b_px
        self._last_good_span_px = _point_distance(self._last_good_point_a, self._last_good_point_b)
        box_span = max(float(definition.metric_box.width), float(definition.metric_box.height), 1.0)
        self._max_endpoint_jump_px = (
            float(max_endpoint_jump_px)
            if max_endpoint_jump_px is not None
            else max(12.0, min(box_span * 0.20, 72.0))
        )
        self._max_midpoint_drift_px = (
            float(max_midpoint_drift_px)
            if max_midpoint_drift_px is not None
            else max(8.0, min(box_span * 0.16, 48.0))
        )
        self._max_span_change_ratio = max(0.0, float(max_span_change_ratio))
        self._max_consecutive_misses = max(1, int(max_consecutive_misses))
        self._hold_quality = max(float(hold_quality), 0.0)
        self._consecutive_misses = 0
        self._has_runtime_lock = False

    def extract(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
    ) -> ShapeMetric:
        observation = self._observation_source.extract(
            frame,
            temp,
            sample_index=sample_index,
            total_samples=total_samples,
        )
        diagnostics = self._tracking_diagnostics(observation)
        if observation.metric_raw is not None and observation.point_a_px is not None and observation.point_b_px is not None and not self._has_runtime_lock:
            if not self._bootstrap_candidate_within_prior(diagnostics):
                rejection_reason = self._rejection_reason(observation, diagnostics)
                return self._hold_last_good_metric(
                    frame,
                    temp,
                    sample_index=sample_index,
                    total_samples=total_samples,
                    observation=observation,
                    diagnostics=diagnostics,
                    rejection_reason=rejection_reason,
                )
            self._remember(observation)
            self._consecutive_misses = 0
            self._has_runtime_lock = True
            observation.meta["tracking_mode"] = self._tracking_mode
            observation.meta["tracking_state"] = "bootstrapped"
            observation.meta.update(diagnostics)
            return observation
        if observation.metric_raw is not None and self._candidate_within_prior(diagnostics):
            tracking_state = "reacquired" if self._consecutive_misses > 0 else "accepted"
            self._remember(observation)
            self._consecutive_misses = 0
            observation.meta["tracking_mode"] = self._tracking_mode
            observation.meta["tracking_state"] = tracking_state
            observation.meta.update(diagnostics)
            return observation
        rejection_reason = self._rejection_reason(observation, diagnostics)
        return self._hold_last_good_metric(
            frame,
            temp,
            sample_index=sample_index,
            total_samples=total_samples,
            observation=observation,
            diagnostics=diagnostics,
            rejection_reason=rejection_reason,
        )

    def _tracking_diagnostics(self, observation: ShapeMetric) -> dict[str, Any]:
        point_a = _shape_metric_point(observation.point_a_px)
        point_b = _shape_metric_point(observation.point_b_px)
        if point_a is None or point_b is None or observation.metric_raw is None:
            return {
                "endpoint_jump_px": None,
                "midpoint_drift_px": None,
                "span_change_ratio": None,
                "consecutive_misses": self._consecutive_misses,
            }
        previous_midpoint = _midpoint(self._last_good_point_a, self._last_good_point_b)
        current_midpoint = _midpoint(point_a, point_b)
        return {
            "endpoint_jump_px": max(
                _point_distance(self._last_good_point_a, point_a),
                _point_distance(self._last_good_point_b, point_b),
            ),
            "midpoint_drift_px": _point_distance(previous_midpoint, current_midpoint),
            "span_change_ratio": abs(float(observation.metric_raw) - self._last_good_span_px) / max(self._last_good_span_px, 1.0),
            "consecutive_misses": self._consecutive_misses,
        }

    def _candidate_within_prior(self, diagnostics: dict[str, Any]) -> bool:
        endpoint_jump_px = diagnostics.get("endpoint_jump_px")
        midpoint_drift_px = diagnostics.get("midpoint_drift_px")
        span_change_ratio = diagnostics.get("span_change_ratio")
        if endpoint_jump_px is None or midpoint_drift_px is None or span_change_ratio is None:
            return False
        return (
            float(endpoint_jump_px) <= self._max_endpoint_jump_px
            and float(midpoint_drift_px) <= self._max_midpoint_drift_px
            and float(span_change_ratio) <= self._max_span_change_ratio
        )

    def _bootstrap_candidate_within_prior(self, diagnostics: dict[str, Any]) -> bool:
        endpoint_jump_px = diagnostics.get("endpoint_jump_px")
        midpoint_drift_px = diagnostics.get("midpoint_drift_px")
        if endpoint_jump_px is None or midpoint_drift_px is None:
            return False
        return (
            float(endpoint_jump_px) <= self._max_endpoint_jump_px
            and float(midpoint_drift_px) <= self._max_midpoint_drift_px
        )

    def _rejection_reason(self, observation: ShapeMetric, diagnostics: dict[str, Any]) -> str:
        if observation.metric_raw is None:
            return str(observation.meta.get("reason", "missing_observation"))
        if diagnostics.get("endpoint_jump_px") is not None and float(diagnostics["endpoint_jump_px"]) > self._max_endpoint_jump_px:
            return "endpoint_jump_exceeded"
        if diagnostics.get("midpoint_drift_px") is not None and float(diagnostics["midpoint_drift_px"]) > self._max_midpoint_drift_px:
            return "midpoint_drift_exceeded"
        if diagnostics.get("span_change_ratio") is not None and float(diagnostics["span_change_ratio"]) > self._max_span_change_ratio:
            return "span_change_exceeded"
        return str(observation.meta.get("reason", "tracking_rejected"))

    def _hold_last_good_metric(
        self,
        frame: FramePacket,
        temp: TempReading,
        *,
        sample_index: int,
        total_samples: int,
        observation: ShapeMetric,
        diagnostics: dict[str, Any],
        rejection_reason: str,
    ) -> ShapeMetric:
        self._consecutive_misses += 1
        exhausted = self._consecutive_misses > self._max_consecutive_misses
        point_a = self._last_good_point_a
        point_b = self._last_good_point_b
        midpoint = _midpoint(point_a, point_b)
        metric = ShapeMetric(
            timestamp_ms=temp.timestamp_ms,
            metric_name="two_point_distance",
            metric_raw=self._last_good_span_px,
            metric_norm=None,
            quality=0.0 if exhausted else self._hold_quality,
            feature_point_px=(midpoint.x, midpoint.y),
            point_a_px=(point_a.x, point_a.y),
            point_b_px=(point_b.x, point_b.y),
            baseline_px=self._last_good_span_px,
            meta={
                "source": frame.source,
                "frame_id": frame.frame_id,
                "selection_mode": "tracking_prior_hold",
                "tracking_mode": self._tracking_mode,
                "tracking_state": "invalidated" if exhausted else "holding_last_good",
                "reason": "tracking_prior_exhausted" if exhausted else rejection_reason,
                "observation_selection_mode": observation.meta.get("selection_mode"),
                "observation_reason": observation.meta.get("reason"),
                "sample_index": sample_index,
                "total_samples": total_samples,
                "max_endpoint_jump_px": self._max_endpoint_jump_px,
                "max_midpoint_drift_px": self._max_midpoint_drift_px,
                "max_span_change_ratio": self._max_span_change_ratio,
                "max_consecutive_misses": self._max_consecutive_misses,
                "consecutive_misses": self._consecutive_misses,
                **diagnostics,
            },
        )
        return metric

    def _remember(self, observation: ShapeMetric) -> None:
        point_a = _shape_metric_point(observation.point_a_px)
        point_b = _shape_metric_point(observation.point_b_px)
        if point_a is None or point_b is None or observation.metric_raw is None:
            return
        self._last_good_point_a = point_a
        self._last_good_point_b = point_b
        self._last_good_span_px = float(observation.metric_raw)
        self._has_runtime_lock = True


class LiveRunCoordinator:
    """Single-threaded live-run coordinator for the Phase 3 vertical slice."""

    def __init__(self, repo: SessionSummaryRepo, artifact_store: SessionArtifactStore) -> None:
        self.repo = repo
        self.artifact_store = artifact_store

    def run(
        self,
        *,
        session_id: str,
        definition: MeasurementDefinition,
        target_temperature_celsius: float,
        run_config: RunRuntimeConfig,
        analysis_engine: str,
        channel_name: str,
        as_fit_point_count: int,
        af_fit_point_count: int,
        camera_config: CameraRuntimeConfig | None = None,
        effective_definition: MeasurementDefinition | None = None,
        measurement_capture_plan: dict[str, Any] | None = None,
        camera: CameraPort,
        temp_reader: TempReader,
        temp_controller: TempControllerPort,
        metric_source: LiveMetricSource,
        quality_threshold: float = 0.75,
        stop_on_target_reached: bool = True,
        stop_requested: Callable[[], bool] | None = None,
        wait_for_next_sample: Callable[[float], bool] | None = None,
        status_callback: Callable[[RunStatus, dict[str, Any]], None] | None = None,
        telemetry_callback: Callable[[dict[str, Any]], None] | None = None,
        sample_callback: Callable[[SyncPoint, dict[str, Any]], None] | None = None,
    ) -> LiveRunExecution:
        started_at_ms = _now_ms()
        events = [
            _event(
                started_at_ms,
                "run_started",
                {"target_temperature_celsius": target_temperature_celsius},
            )
        ]
        sync_points: list[SyncPoint] = []
        telemetry: list[dict[str, Any]] = []
        hub = SyncHub()
        output_started = False
        playback_sample_count = _resolve_playback_sample_count(metric_source, temp_reader)
        sample_interval_ms = resolve_measurement_interval_ms(
            run_config,
            playback_sample_count=playback_sample_count,
            stop_on_target_reached=stop_on_target_reached,
        )
        next_sample_due_ms = started_at_ms

        try:
            temp_controller.set_target_temperature(target_temperature_celsius)
            events.append(
                _event(
                    started_at_ms,
                    "target_temperature_set",
                    {"target_temperature_celsius": target_temperature_celsius},
                )
            )
            temp_controller.start_output()
            output_started = True
            events.append(_event(started_at_ms, "output_started", {}))
            if status_callback is not None:
                status_callback(RunStatus.RUNNING, {"started_at_ms": started_at_ms})

            if playback_sample_count is not None and stop_on_target_reached:
                max_samples = max(1, int(playback_sample_count))
            else:
                # Do not hard-stop target-reached runs after a tiny temperature-only heuristic.
                # Real cooling/heating benches may need many samples even for low target values.
                max_samples = max(1, int(run_config.manual_stop_max_samples))
            for sample_index in range(max_samples):
                if stop_requested is not None and stop_requested():
                    stop_detail = "Run stop requested before the next sample."
                    events.append(_event(_now_ms(), "run_stop_requested", {"reason": "user_stop"}))
                    if status_callback is not None:
                        status_callback(RunStatus.STOPPING, {"reason": "user_stop"})
                    raise LiveRunStopRequested("user_stop", stop_detail)

                sample_started_ms = _now_ms()
                sample_started_perf = time.perf_counter()
                frame = camera.read_frame()
                frame_read_ms = (time.perf_counter() - sample_started_perf) * 1000.0
                frame.timestamp_ms = _resolved_timestamp_ms(frame.timestamp_ms, fallback_ms=sample_started_ms)
                if frame.frame_id is None:
                    frame.frame_id = sample_index + 1

                temp_started_perf = time.perf_counter()
                temp = temp_reader.read()
                temp_read_ms = (time.perf_counter() - temp_started_perf) * 1000.0
                temp.timestamp_ms = _resolved_timestamp_ms(
                    temp.timestamp_ms,
                    fallback_ms=max(sample_started_ms, frame.timestamp_ms),
                )
                sample_timestamp_ms = max(frame.timestamp_ms, temp.timestamp_ms)

                extract_started_perf = time.perf_counter()
                metric = metric_source.extract(
                    frame,
                    temp,
                    sample_index=sample_index,
                    total_samples=max_samples,
                )
                metric_extract_ms = (time.perf_counter() - extract_started_perf) * 1000.0
                metric.meta["frame_read_ms"] = frame_read_ms
                metric.meta["temp_read_ms"] = temp_read_ms
                metric.meta["metric_extract_ms"] = metric_extract_ms
                metric.meta["sample_loop_ms"] = (time.perf_counter() - sample_started_perf) * 1000.0
                metric.timestamp_ms = sample_timestamp_ms
                if metric.metric_raw is None:
                    raise RuntimeError(f"tracking_metric_unavailable:{metric.meta.get('reason', 'unknown')}")
                quality_grace_active = (
                    bool(run_config.stop_on_invalid_tracking)
                    and int(sample_index) < max(0, int(getattr(run_config, "invalid_tracking_grace_samples", 0) or 0))
                )
                if metric.quality < quality_threshold:
                    invalidation_payload = {
                        "reason": "tracking_quality_below_threshold",
                        "tracking_quality": metric.quality,
                        "quality_threshold": quality_threshold,
                    }
                    metric.meta["quality_threshold_grace_active"] = quality_grace_active
                    metric.meta["quality_threshold_grace_samples"] = int(
                        max(0, int(getattr(run_config, "invalid_tracking_grace_samples", 0) or 0))
                    )
                    if quality_grace_active:
                        invalidation_payload["grace_active"] = True
                        invalidation_payload["sample_index"] = int(sample_index)
                        invalidation_payload["grace_samples"] = int(
                            max(0, int(getattr(run_config, "invalid_tracking_grace_samples", 0) or 0))
                        )
                        events.append(_event(sample_timestamp_ms, "tracking_quality_grace", invalidation_payload))
                    else:
                        events.append(_event(sample_timestamp_ms, "tracking_invalidated", invalidation_payload))
                        if status_callback is not None and run_config.stop_on_invalid_tracking:
                            status_callback(RunStatus.INVALIDATED, invalidation_payload)
                        if run_config.stop_on_invalid_tracking:
                            if status_callback is not None:
                                status_callback(RunStatus.STOPPING, {"reason": "invalid_tracking"})
                            raise LiveRunTrackingInvalidated(
                                "invalid_tracking",
                                f"Tracking quality dropped below threshold: {metric.quality:.3f} < {quality_threshold:.3f}",
                            )

                hub.update_frame(frame)
                hub.update_temp(temp)
                hub.update_metric(metric)
                sync_point = hub.snapshot()
                sync_points.append(sync_point)
                telemetry_started_perf = time.perf_counter()
                telemetry_row = _telemetry_row(
                    sync_point,
                    sample_index=sample_index,
                    previous_timestamp_ms=None if len(sync_points) < 2 else sync_points[-2].timestamp_ms,
                )
                telemetry_row_ms = (time.perf_counter() - telemetry_started_perf) * 1000.0
                telemetry_row["telemetry_row_ms"] = telemetry_row_ms
                callback_started_perf = time.perf_counter()
                if sample_callback is not None:
                    sample_callback(sync_point, telemetry_row)
                sample_callbacks_ms = (time.perf_counter() - callback_started_perf) * 1000.0
                telemetry_row["sample_callbacks_ms"] = sample_callbacks_ms
                telemetry_row["post_sample_ms"] = telemetry_row_ms + sample_callbacks_ms
                telemetry.append(telemetry_row)
                if telemetry_callback is not None:
                    telemetry_callback(telemetry_row)
                events.append(
                    _event(
                        sync_point.timestamp_ms,
                        "sample_captured",
                        {
                            "temperature_celsius": temp.celsius,
                            "space1_px": metric.metric_raw,
                            "tracking_quality": metric.quality,
                            "frame_id": frame.frame_id,
                        },
                    )
                )

                if (
                    playback_sample_count is not None
                    and stop_on_target_reached
                    and len(sync_points) >= playback_sample_count
                ):
                    break
                if stop_on_target_reached and temp.celsius >= target_temperature_celsius and len(sync_points) >= 3:
                    break
                next_sample_due_ms += sample_interval_ms
                remaining_wait_s = max(0.0, (next_sample_due_ms - _now_ms()) / 1000.0)
                if wait_for_next_sample is not None and wait_for_next_sample(remaining_wait_s):
                    events.append(_event(_now_ms(), "run_stop_requested", {"reason": "user_stop"}))
                    if status_callback is not None:
                        status_callback(RunStatus.STOPPING, {"reason": "user_stop"})
                    raise LiveRunStopRequested("user_stop", "Run stop requested while waiting for the next sample.")
            else:
                if playback_sample_count is not None and stop_on_target_reached:
                    raise RuntimeError("mock_playback_not_completed")
                if stop_on_target_reached:
                    raise RuntimeError("target_temperature_not_reached")
                raise RuntimeError("manual_stop_timeout")
        finally:
            stop_timestamp_ms = _now_ms()
            if output_started:
                temp_controller.stop_output()
                events.append(_event(stop_timestamp_ms, "output_stopped", {}))

        afas_result = analyze_afas(
            sync_points,
            channel_name=channel_name,
            as_fit_point_count=as_fit_point_count,
            af_fit_point_count=af_fit_point_count,
        )
        rate_snapshot = summarize_rate_snapshot(sync_points=sync_points, telemetry=telemetry)
        measurement_profile = summarize_measurement_profile(
            camera_config if camera_config is not None else CameraRuntimeConfig()
        )
        warnings = summarize_rate_warnings(
            rate_snapshot,
            target_measurement_hz=run_config.measurement_target_hz,
            is_terminal=True,
        )
        rates_payload = _rate_snapshot_payload(rate_snapshot)
        measurement_profile_payload = _measurement_profile_payload(measurement_profile)
        detail = build_live_detail(
            session_id=session_id,
            sync_points=sync_points,
            afas_result=afas_result,
            rate_snapshot=rate_snapshot,
            measurement_profile=measurement_profile,
            warnings=warnings,
        )
        keyframe_refs = _keyframe_artifact_refs(detail["key_frames"])
        afas_dataset = build_afas_postprocessing_dataset(
            session_id=session_id,
            definition=definition,
            sync_points=sync_points,
            channel_name=channel_name,
            analysis_engine=analysis_engine,
            capture_mode=CaptureMode.POST_RUN_REVIEW.value,
            rates=rates_payload,
            measurement_profile=measurement_profile_payload,
            warnings=warnings,
            live_result_snapshot={
                "result_status": afas_result.result_status,
                "result_reason": afas_result.reason,
                "result_detail": afas_result.detail,
                "af95": afas_result.af95,
                "as_value": afas_result.as_value,
                "af_value": afas_result.af_value,
                "point_count": detail["point_count"],
            },
        )
        if warnings:
            events.append(
                _event(
                    _now_ms(),
                    "measurement_cadence_assessed",
                    {
                        "warnings": warnings,
                        "measurement_sample_hz": rate_snapshot.measurement_sample_hz,
                        "target_measurement_hz": run_config.measurement_target_hz,
                        "dropped_frame_count": rate_snapshot.dropped_frame_count,
                    },
                )
            )
        result = build_live_run_result(
            session_id=session_id,
            state="completed",
            analysis_engine=analysis_engine,
            channel_name=channel_name,
            result_status=afas_result.result_status,
            result_reason=afas_result.reason,
            result_detail=afas_result.detail,
            af95=afas_result.af95,
            as_value=afas_result.as_value,
            af_value=afas_result.af_value,
            point_count=detail["point_count"],
            keyframe_refs=keyframe_refs,
            capture_mode=CaptureMode.POST_RUN_REVIEW.value,
            rates=rates_payload,
            measurement_profile=measurement_profile_payload,
            warnings=warnings,
        )
        self.artifact_store.save_live_bundle(
            session_id,
            definition=_definition_payload(definition),
            definition_original=_definition_payload(definition),
            definition_effective_local=None
            if effective_definition is None
            else _definition_payload(effective_definition),
            measurement_capture_plan=measurement_capture_plan,
            telemetry=telemetry,
            detail=detail,
            result=result,
            events=events,
            afas_dataset=afas_dataset,
            keyframes=detail["key_frames"],
        )

        summary = SessionSummary(
            session_id=session_id,
            state="completed",
            point_count=detail["point_count"],
            af95=afas_result.af95,
            created_at_ms=started_at_ms,
        )
        self.repo.save_summary(summary)
        events.append(
            _event(
                _now_ms(),
                "run_completed",
                {
                    "af95": afas_result.af95,
                    "result_status": afas_result.result_status,
                    "result_reason": afas_result.reason,
                },
            )
        )
        return LiveRunExecution(
            summary=summary,
            detail=detail,
            result=result,
            telemetry=telemetry,
            events=events,
        )


def build_partial_live_run_execution(
    *,
    session_id: str,
    started_at_ms: int,
    terminal_state: str,
    terminal_reason: str | None,
    terminal_detail: str,
    definition: MeasurementDefinition,
    telemetry: list[dict[str, Any]],
    events: list[dict[str, Any]],
    camera_config: CameraRuntimeConfig | None,
    analysis_engine: str,
    channel_name: str,
    target_measurement_hz: float | None,
) -> LiveRunExecution:
    rate_snapshot = summarize_rate_snapshot(telemetry=telemetry)
    measurement_profile = summarize_measurement_profile(
        camera_config if camera_config is not None else CameraRuntimeConfig()
    )
    warnings = summarize_rate_warnings(
        rate_snapshot,
        target_measurement_hz=target_measurement_hz,
        is_terminal=True,
    )
    rates_payload = _rate_snapshot_payload(rate_snapshot)
    measurement_profile_payload = _measurement_profile_payload(measurement_profile)
    detail_points = _detail_points_from_telemetry(telemetry)
    detail = {
        "session_id": session_id,
        "source": "live_run",
        "af95": None,
        "as_value": None,
        "af_value": None,
        "result_status": "unavailable",
        "result_reason": terminal_reason,
        "result_detail": terminal_detail,
        "point_count": len(detail_points),
        "capture_mode": CaptureMode.POST_RUN_REVIEW.value,
        "rates": rates_payload,
        "measurement_profile": measurement_profile_payload,
        "warnings": list(warnings),
        "points": detail_points,
        "key_frames": [],
    }
    result = build_live_run_result(
        session_id=session_id,
        state=terminal_state,
        analysis_engine=analysis_engine,
        channel_name=channel_name,
        result_status="unavailable",
        result_reason=terminal_reason,
        result_detail=terminal_detail,
        af95=None,
        as_value=None,
        af_value=None,
        point_count=len(detail_points),
        keyframe_refs=[],
        capture_mode=CaptureMode.POST_RUN_REVIEW.value,
        rates=rates_payload,
        measurement_profile=measurement_profile_payload,
        warnings=warnings,
    )
    summary = SessionSummary(
        session_id=session_id,
        state=terminal_state,
        point_count=len(detail_points),
        af95=None,
        created_at_ms=started_at_ms,
    )
    return LiveRunExecution(
        summary=summary,
        detail=detail,
        result=result,
        telemetry=list(telemetry),
        events=list(events),
    )


def build_live_detail(
    session_id: str,
    sync_points: list[SyncPoint],
    afas_result: AfasAnalysisResult,
    rate_snapshot: RunRateSnapshot,
    measurement_profile: MeasurementProfileSnapshot,
    warnings: list[str],
) -> dict[str, Any]:
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
        "source": "live_run",
        "af95": afas_result.af95,
        "as_value": afas_result.as_value,
        "af_value": afas_result.af_value,
        "result_status": afas_result.result_status,
        "result_reason": afas_result.reason,
        "result_detail": afas_result.detail,
        "point_count": len(detail_points),
        "capture_mode": CaptureMode.POST_RUN_REVIEW.value,
        "rates": _rate_snapshot_payload(rate_snapshot),
        "measurement_profile": _measurement_profile_payload(measurement_profile),
        "warnings": list(warnings),
        "points": detail_points,
        "key_frames": _select_key_frames(sync_points),
    }


def _detail_points_from_telemetry(telemetry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    detail_points: list[dict[str, Any]] = []
    for row in telemetry:
        if row.get("timestamp_ms") is None or row.get("temperature_celsius") is None or row.get("space1_px") is None:
            continue
        detail_points.append(
            {
                "timestamp_ms": int(row["timestamp_ms"]),
                "celsius": float(row["temperature_celsius"]),
                "metric_raw": float(row["space1_px"]),
                "metric_norm": None,
                "quality": float(row.get("tracking_quality") or 0.0),
            }
        )
    return detail_points


def summarize_rate_snapshot(
    *,
    sync_points: list[SyncPoint] | None = None,
    telemetry: list[dict[str, Any]] | None = None,
    preview_display_fps: float | None = None,
) -> RunRateSnapshot:
    measurement_sample_hz = _sample_rate_hz(
        [] if telemetry is None else [int(item["timestamp_ms"]) for item in telemetry if "timestamp_ms" in item]
    )
    artifact_capture_hz = measurement_sample_hz
    camera_resulting_fps = _camera_resulting_fps(sync_points or [], telemetry or [])
    dropped_frame_count = _dropped_frame_count(sync_points or [], telemetry or [])
    return RunRateSnapshot(
        camera_resulting_fps=camera_resulting_fps,
        preview_display_fps=preview_display_fps,
        measurement_sample_hz=measurement_sample_hz,
        artifact_capture_hz=artifact_capture_hz,
        dropped_frame_count=dropped_frame_count,
    )


def summarize_measurement_profile(camera_config: CameraRuntimeConfig | CameraAcquisitionProfileConfig) -> MeasurementProfileSnapshot:
    profile = camera_config.measurement if isinstance(camera_config, CameraRuntimeConfig) else camera_config
    roi = None
    if profile.device_roi.width > 0 and profile.device_roi.height > 0:
        roi = RectRegion(
            x=profile.device_roi.x,
            y=profile.device_roi.y,
            width=profile.device_roi.width,
            height=profile.device_roi.height,
        )
    return MeasurementProfileSnapshot(
        acquisition_roi=roi,
        decimation=profile.decimation,
        binning=profile.binning,
        exposure_us=profile.exposure_us,
    )


def _definition_payload(definition: MeasurementDefinition) -> dict[str, Any]:
    return {
        "analysis_roi": {
            "x": definition.analysis_roi.x,
            "y": definition.analysis_roi.y,
            "width": definition.analysis_roi.width,
            "height": definition.analysis_roi.height,
        },
        "metric_box": {
            "center_x": definition.metric_box.center_x,
            "center_y": definition.metric_box.center_y,
            "width": definition.metric_box.width,
            "height": definition.metric_box.height,
            "angle_deg": definition.metric_box.angle_deg,
        },
        "point_a_px": {
            "x": definition.point_a_px.x,
            "y": definition.point_a_px.y,
        },
        "point_b_px": {
            "x": definition.point_b_px.x,
            "y": definition.point_b_px.y,
        },
        "observation_axis": definition.observation_axis.value,
        "foreground_polarity": definition.foreground_polarity,
        "threshold_mode": definition.threshold_mode,
        "ignore_internal_texture": definition.ignore_internal_texture,
        "min_target_area_px": definition.min_target_area_px,
        "sensitivity": definition.sensitivity,
    }


def _telemetry_row(
    sync_point: SyncPoint,
    *,
    sample_index: int,
    previous_timestamp_ms: int | None,
) -> dict[str, Any]:
    if sync_point.temp is None or sync_point.metric is None or sync_point.metric.metric_raw is None:
        raise ValueError("telemetry row requires temperature and metric data")
    frame = sync_point.frame
    return {
        "timestamp_ms": sync_point.timestamp_ms,
        "sample_index": sample_index,
        "sample_interval_ms": None
        if previous_timestamp_ms is None
        else max(0, sync_point.timestamp_ms - previous_timestamp_ms),
        "frame_id": None if frame is None or frame.frame_id is None else int(frame.frame_id),
        "frame_timestamp_ms": None if frame is None else int(frame.timestamp_ms),
        "temp_timestamp_ms": int(sync_point.temp.timestamp_ms),
        "metric_timestamp_ms": int(sync_point.metric.timestamp_ms),
        "camera_resulting_fps": _frame_resulting_fps(frame),
        "temperature_celsius": sync_point.temp.celsius,
        "space1_px": sync_point.metric.metric_raw,
        "tracking_quality": sync_point.metric.quality,
        "point_a_px": None
        if sync_point.metric.point_a_px is None
        else [int(sync_point.metric.point_a_px[0]), int(sync_point.metric.point_a_px[1])],
        "point_b_px": None
        if sync_point.metric.point_b_px is None
        else [int(sync_point.metric.point_b_px[0]), int(sync_point.metric.point_b_px[1])],
        "tracking_mode": sync_point.metric.meta.get("tracking_mode"),
        "tracking_state": sync_point.metric.meta.get("tracking_state"),
        "selection_mode": sync_point.metric.meta.get("selection_mode"),
        "reason": sync_point.metric.meta.get("reason"),
        "observation_selection_mode": sync_point.metric.meta.get("observation_selection_mode"),
        "observation_reason": sync_point.metric.meta.get("observation_reason"),
        "component_area": sync_point.metric.meta.get("component_area"),
        "threshold_value": sync_point.metric.meta.get("threshold_value"),
        "endpoint_jump_px": sync_point.metric.meta.get("endpoint_jump_px"),
        "midpoint_drift_px": sync_point.metric.meta.get("midpoint_drift_px"),
        "span_change_ratio": sync_point.metric.meta.get("span_change_ratio"),
        "consecutive_misses": sync_point.metric.meta.get("consecutive_misses"),
        "frame_read_ms": sync_point.metric.meta.get("frame_read_ms"),
        "temp_read_ms": sync_point.metric.meta.get("temp_read_ms"),
        "metric_extract_ms": sync_point.metric.meta.get("metric_extract_ms"),
        "sample_loop_ms": sync_point.metric.meta.get("sample_loop_ms"),
        "telemetry_row_ms": sync_point.metric.meta.get("telemetry_row_ms"),
        "sample_callbacks_ms": sync_point.metric.meta.get("sample_callbacks_ms"),
        "post_sample_ms": sync_point.metric.meta.get("post_sample_ms"),
    }


def _rate_snapshot_payload(rate_snapshot: RunRateSnapshot) -> dict[str, Any]:
    return {
        "camera_resulting_fps": rate_snapshot.camera_resulting_fps,
        "preview_display_fps": rate_snapshot.preview_display_fps,
        "measurement_sample_hz": rate_snapshot.measurement_sample_hz,
        "artifact_capture_hz": rate_snapshot.artifact_capture_hz,
        "dropped_frame_count": rate_snapshot.dropped_frame_count,
    }


def _measurement_profile_payload(profile: MeasurementProfileSnapshot) -> dict[str, Any]:
    roi = profile.acquisition_roi
    return {
        "acquisition_roi": None
        if roi is None
        else {
            "x": roi.x,
            "y": roi.y,
            "width": roi.width,
            "height": roi.height,
        },
        "decimation": profile.decimation,
        "binning": profile.binning,
        "exposure_us": profile.exposure_us,
    }


def _sample_rate_hz(timestamps_ms: list[int]) -> float | None:
    if len(timestamps_ms) < 2:
        return None
    span_ms = timestamps_ms[-1] - timestamps_ms[0]
    if span_ms <= 0:
        return None
    return ((len(timestamps_ms) - 1) * 1000.0) / span_ms


def resolve_measurement_interval_ms(
    run_config: Any,
    *,
    playback_sample_count: int | None = None,
    stop_on_target_reached: bool = True,
) -> int:
    if playback_sample_count is not None and stop_on_target_reached:
        return 1
    target_hz = getattr(run_config, "measurement_target_hz", None)
    if target_hz is not None:
        resolved_hz = float(target_hz)
        if resolved_hz > 0:
            return max(1, int(round(1000.0 / resolved_hz)))
    return max(int(getattr(run_config, "capture_interval_ms", 1) or 1), 1)


def _camera_resulting_fps(sync_points: list[SyncPoint], telemetry: list[dict[str, Any]]) -> float | None:
    for sync_point in reversed(sync_points):
        value = _frame_resulting_fps(sync_point.frame)
        if value is not None:
            return value
    for item in reversed(telemetry):
        value = item.get("camera_resulting_fps")
        if value is not None:
            return float(value)
    return None


def _dropped_frame_count(sync_points: list[SyncPoint], telemetry: list[dict[str, Any]]) -> int:
    frame_ids = [
        int(sync_point.frame.frame_id)
        for sync_point in sync_points
        if sync_point.frame is not None and sync_point.frame.frame_id is not None
    ]
    if not frame_ids:
        frame_ids = [int(item["frame_id"]) for item in telemetry if item.get("frame_id") is not None]
    if len(frame_ids) < 2:
        return 0
    expected = frame_ids[-1] - frame_ids[0] + 1
    return max(0, expected - len(frame_ids))


def summarize_rate_warnings(
    rate_snapshot: RunRateSnapshot,
    *,
    target_measurement_hz: float | None,
    is_terminal: bool,
) -> list[str]:
    warnings: list[str] = []
    if target_measurement_hz is not None and rate_snapshot.measurement_sample_hz is None and is_terminal:
        warnings.append("measurement cadence unavailable for this run")
    if (
        target_measurement_hz is not None
        and rate_snapshot.measurement_sample_hz is not None
        and rate_snapshot.measurement_sample_hz + 1e-9 < (float(target_measurement_hz) * 0.95)
    ):
        warnings.append(
            "measurement cadence below target: "
            f"achieved {rate_snapshot.measurement_sample_hz:.2f} Hz < target {float(target_measurement_hz):.2f} Hz"
        )
    if rate_snapshot.dropped_frame_count > 0:
        warnings.append(f"measurement dropped frames detected: {rate_snapshot.dropped_frame_count}")
    return warnings


def _frame_resulting_fps(frame: FramePacket | None) -> float | None:
    if frame is None:
        return None
    for key in ("camera_resulting_fps", "resulting_frame_rate", "resulting_fps"):
        value = frame.meta.get(key)
        if value is not None:
            return float(value)
    return None


def _resolved_timestamp_ms(value: int | None, *, fallback_ms: int) -> int:
    if value is None:
        return int(fallback_ms)
    resolved = int(value)
    return resolved if resolved > 0 else int(fallback_ms)


def _resolve_playback_sample_count(*sources: object) -> int | None:
    for source in sources:
        accessor = getattr(source, "playback_sample_count", None)
        if not callable(accessor):
            continue
        resolved = int(accessor())
        if resolved > 0:
            return resolved
    return None


def _points_for_projected_span(
    *,
    frame: FramePacket,
    center_x: float,
    center_y: float,
    unit_x: float,
    unit_y: float,
    span_px: float,
) -> tuple[tuple[int, int], tuple[int, int]]:
    half_span = max(float(span_px), 2.0) / 2.0
    point_a_x = center_x - unit_x * half_span
    point_a_y = center_y - unit_y * half_span
    point_b_x = center_x + unit_x * half_span
    point_b_y = center_y + unit_y * half_span

    max_x = (len(frame.image[0]) - 1) if frame.image and frame.image[0] else int(round(center_x))
    max_y = (len(frame.image) - 1) if frame.image else int(round(center_y))
    point_a = (
        int(max(0, min(max_x, round(point_a_x)))),
        int(max(0, min(max_y, round(point_a_y)))),
    )
    point_b = (
        int(max(0, min(max_x, round(point_b_x)))),
        int(max(0, min(max_y, round(point_b_y)))),
    )
    return point_a, point_b


def _event(timestamp_ms: int, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_ms": timestamp_ms,
        "type": event_type,
        "payload": payload,
    }


def _shape_metric_point(value: tuple[int, int] | None) -> PixelPoint | None:
    if value is None:
        return None
    return PixelPoint(x=int(value[0]), y=int(value[1]))


def _midpoint(point_a: PixelPoint, point_b: PixelPoint) -> PixelPoint:
    return PixelPoint(
        x=int(round((point_a.x + point_b.x) / 2)),
        y=int(round((point_a.y + point_b.y) / 2)),
    )


def _point_distance(point_a: PixelPoint, point_b: PixelPoint) -> float:
    return math.hypot(float(point_b.x - point_a.x), float(point_b.y - point_a.y))


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


def _keyframe_artifact_refs(key_frames: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for key_frame in key_frames:
        label = str(key_frame.get("label", "") or "").strip()
        image = key_frame.get("image")
        if not label or image is None:
            continue
        refs.append(f"keyframes/{label}.png")
    return refs


def _now_ms() -> int:
    return int(time.time() * 1000)
