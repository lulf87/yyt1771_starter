import json
from pathlib import Path

import numpy as np
import pytest

from src.core.enums import ObservationAxis
from src.core.models import (
    FramePacket,
    MeasurementDefinition,
    MetricBox,
    PixelPoint,
    RectRegion,
    TempReading,
)
from src.workflow.live_run import PriorTrackingMetricSource
from src.workflow.live_run import _directional_component_bridge_kernel_for_sensitivity
from src.vision.contour_direction import DirectionalContourConfig, DirectionalContourMetricExtractor


def test_prior_tracking_keeps_high_temp_offline_chord_from_collapsing_to_fragment() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / "examples/runtime/artifacts/run-9953bd601113"
    capture_dir = repo_root / "examples/runtime/camera_captures/20260522-183158-dev_lab"
    frame_5436 = capture_dir / "frames/frame_005436.npy"
    frame_5437 = capture_dir / "frames/frame_005437.npy"
    if not run_dir.exists() or not frame_5436.exists() or not frame_5437.exists():
        pytest.skip("local offline capture regression fixture is not available")

    definition_payload = json.loads((run_dir / "definition_effective_local.json").read_text())
    if definition_payload.get("direction_projection_mode") != "max_chord":
        pytest.skip("legacy mask_projection artifact is not the current locked A/B mode")
    acquisition_roi = json.loads((run_dir / "measurement_capture_plan.json").read_text())[
        "effective_acquisition_roi"
    ]
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(**definition_payload["analysis_roi"]),
        metric_box=MetricBox(**definition_payload["metric_box"]),
        # Frame 5436 is the accepted prior immediately before the observed high-temp collapse.
        point_a_px=PixelPoint(x=506, y=806),
        point_b_px=PixelPoint(x=1295, y=617),
        foreground_polarity=definition_payload["foreground_polarity"],
        threshold_mode=definition_payload["threshold_mode"],
        ignore_internal_texture=definition_payload["ignore_internal_texture"],
        min_target_area_px=definition_payload["min_target_area_px"],
        sensitivity=definition_payload["sensitivity"],
        direction_angle_deg=definition_payload["direction_angle_deg"],
        direction_projection_mode=definition_payload["direction_projection_mode"],
        observation_axis=ObservationAxis(definition_payload["observation_axis"]),
    )
    source = PriorTrackingMetricSource(definition=definition)

    stable_metric = source.extract(
        _offline_frame(frame_5436, acquisition_roi, frame_id=5436),
        TempReading(timestamp_ms=5_436, celsius=13.8, source="fixture"),
        sample_index=5435,
        total_samples=5807,
    )
    collapse_metric = source.extract(
        _offline_frame(frame_5437, acquisition_roi, frame_id=5437),
        TempReading(timestamp_ms=5_437, celsius=13.9, source="fixture"),
        sample_index=5436,
        total_samples=5807,
    )

    assert stable_metric.meta["tracking_state"] in {"bootstrapped", "accepted_stabilized"}
    assert stable_metric.metric_raw == pytest.approx(
        _point_distance_for_test(definition.point_a_px, definition.point_b_px),
        abs=8.0,
    )
    assert collapse_metric.meta["tracking_state"] in {
        "accepted",
        "reacquired",
        "accepted_stabilized",
        "reacquired_stabilized",
    }
    assert collapse_metric.metric_raw == pytest.approx(811.3, abs=8.0)
    assert collapse_metric.point_b_px is not None
    assert collapse_metric.point_b_px[0] >= 1260


def test_prior_tracking_stabilizes_small_early_offline_chord_overshoot() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / "examples/runtime/artifacts/run-9953bd601113"
    capture_dir = repo_root / "examples/runtime/camera_captures/20260522-183158-dev_lab"
    frame_284 = capture_dir / "frames/frame_000284.npy"
    frame_285 = capture_dir / "frames/frame_000285.npy"
    if not run_dir.exists() or not frame_284.exists() or not frame_285.exists():
        pytest.skip("local offline capture regression fixture is not available")

    definition_payload = json.loads((run_dir / "definition_effective_local.json").read_text())
    if definition_payload.get("direction_projection_mode") != "max_chord":
        pytest.skip("legacy mask_projection artifact is not the current locked A/B mode")
    acquisition_roi = json.loads((run_dir / "measurement_capture_plan.json").read_text())[
        "effective_acquisition_roi"
    ]
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(**definition_payload["analysis_roi"]),
        metric_box=MetricBox(**definition_payload["metric_box"]),
        # Frame 284 is the last accepted point pair before the early one-frame overshoot.
        point_a_px=PixelPoint(x=423, y=957),
        point_b_px=PixelPoint(x=1408, y=722),
        foreground_polarity=definition_payload["foreground_polarity"],
        threshold_mode=definition_payload["threshold_mode"],
        ignore_internal_texture=definition_payload["ignore_internal_texture"],
        min_target_area_px=definition_payload["min_target_area_px"],
        sensitivity=definition_payload["sensitivity"],
        direction_angle_deg=definition_payload["direction_angle_deg"],
        direction_projection_mode=definition_payload["direction_projection_mode"],
        observation_axis=ObservationAxis(definition_payload["observation_axis"]),
    )
    source = PriorTrackingMetricSource(definition=definition)

    stable_metric = source.extract(
        _offline_frame(frame_284, acquisition_roi, frame_id=284),
        TempReading(timestamp_ms=284, celsius=1.4, source="fixture"),
        sample_index=283,
        total_samples=5807,
    )
    overshoot_metric = source.extract(
        _offline_frame(frame_285, acquisition_roi, frame_id=285),
        TempReading(timestamp_ms=285, celsius=1.4, source="fixture"),
        sample_index=284,
        total_samples=5807,
    )

    assert stable_metric.meta["tracking_state"] in {"bootstrapped", "accepted_stabilized"}
    assert stable_metric.metric_raw == pytest.approx(
        _point_distance_for_test(definition.point_a_px, definition.point_b_px),
        abs=8.0,
    )
    assert overshoot_metric.meta["tracking_state"] in {
        "accepted",
        "reacquired",
        "accepted_stabilized",
        "reacquired_stabilized",
    }
    assert overshoot_metric.meta["tracking_state"] != "holding_last_good"
    assert overshoot_metric.metric_raw == pytest.approx(stable_metric.metric_raw, abs=8.0)


def test_prior_tracking_keeps_oblique_roi_axis_prior_wide_enough_for_full_chord() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / "examples/runtime/artifacts/run-9953bd601113"
    capture_dir = repo_root / "examples/runtime/camera_captures/20260522-183158-dev_lab"
    frame_040 = capture_dir / "frames/frame_000040.npy"
    if not run_dir.exists() or not frame_040.exists():
        pytest.skip("local offline capture regression fixture is not available")

    acquisition_roi = json.loads((run_dir / "measurement_capture_plan.json").read_text())[
        "effective_acquisition_roi"
    ]
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(
            x=0,
            y=0,
            width=int(acquisition_roi["width"]),
            height=int(acquisition_roi["height"]),
        ),
        metric_box=MetricBox(center_x=880, center_y=645, width=1080, height=700, angle_deg=30.0),
        point_a_px=PixelPoint(x=412, y=489),
        point_b_px=PixelPoint(x=1207, y=948),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=200,
        sensitivity=50.0,
        direction_angle_deg=30.0,
        direction_projection_mode="mask_projection",
        observation_axis=ObservationAxis.LONG_AXIS,
    )
    source = PriorTrackingMetricSource(definition=definition)

    next_metric = None
    for frame_id in range(1, 41):
        next_metric = source.extract(
            _offline_frame(
                capture_dir / f"frames/frame_{frame_id:06d}.npy",
                acquisition_roi,
                frame_id=frame_id,
            ),
            TempReading(timestamp_ms=frame_id, celsius=1.3, source="fixture"),
            sample_index=frame_id - 1,
            total_samples=5807,
        )

    assert next_metric is not None
    assert next_metric.meta["tracking_state"] in {
        "accepted",
        "reacquired",
        "accepted_stabilized",
        "reacquired_stabilized",
    }
    assert next_metric.metric_raw == pytest.approx(928.0, abs=12.0)
    assert next_metric.point_a_px is not None
    assert next_metric.point_a_px[0] < 450


def test_prior_tracking_bootstraps_vertical_roi_with_complete_component_bridge() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / "examples/runtime/artifacts/run-9953bd601113"
    capture_dir = repo_root / "examples/runtime/camera_captures/20260522-183158-dev_lab"
    frame_001 = capture_dir / "frames/frame_000001.npy"
    if not run_dir.exists() or not frame_001.exists():
        pytest.skip("local offline capture regression fixture is not available")

    acquisition_roi = json.loads((run_dir / "measurement_capture_plan.json").read_text())[
        "effective_acquisition_roi"
    ]
    analysis_roi = RectRegion(
        x=0,
        y=0,
        width=int(acquisition_roi["width"]),
        height=int(acquisition_roi["height"]),
    )
    metric_box = MetricBox(center_x=880, center_y=645, width=1080, height=700, angle_deg=90.0)
    initial_metric = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=analysis_roi,
            metric_box=metric_box,
            direction_angle_deg=90.0,
            foreground_polarity="dark_on_light",
            threshold_mode="adaptive",
            ignore_internal_texture=True,
            min_target_area_px=200,
            sensitivity=50.0,
            component_bridge_kernel=_directional_component_bridge_kernel_for_sensitivity(
                50.0,
                direction_angle_deg=90.0,
            ),
            projection_mode="mask_projection",
        )
    ).extract(_offline_frame(frame_001, acquisition_roi, frame_id=1))
    assert initial_metric.point_a_px is not None
    assert initial_metric.point_b_px is not None

    definition = MeasurementDefinition(
        analysis_roi=analysis_roi,
        metric_box=metric_box,
        point_a_px=PixelPoint(x=initial_metric.point_a_px[0], y=initial_metric.point_a_px[1]),
        point_b_px=PixelPoint(x=initial_metric.point_b_px[0], y=initial_metric.point_b_px[1]),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=200,
        sensitivity=50.0,
        direction_angle_deg=90.0,
        direction_projection_mode="mask_projection",
        observation_axis=ObservationAxis.LONG_AXIS,
    )
    source = PriorTrackingMetricSource(definition=definition)

    states: list[str] = []
    for frame_id in range(1, 56):
        metric = source.extract(
            _offline_frame(
                capture_dir / f"frames/frame_{frame_id:06d}.npy",
                acquisition_roi,
                frame_id=frame_id,
            ),
            TempReading(timestamp_ms=frame_id, celsius=1.4, source="fixture"),
            sample_index=frame_id - 1,
            total_samples=5807,
        )
        states.append(str(metric.meta["tracking_state"]))

    assert "holding_last_good" not in states
    assert "invalidated" not in states


def test_prior_tracking_stabilizes_oblique_full_run_hard_span_spike() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / "examples/runtime/artifacts/run-9953bd601113"
    capture_dir = repo_root / "examples/runtime/camera_captures/20260522-183158-dev_lab"
    frame_2281 = capture_dir / "frames/frame_002281.npy"
    frame_2282 = capture_dir / "frames/frame_002282.npy"
    if not run_dir.exists() or not frame_2281.exists() or not frame_2282.exists():
        pytest.skip("local offline capture regression fixture is not available")

    acquisition_roi = json.loads((run_dir / "measurement_capture_plan.json").read_text())[
        "effective_acquisition_roi"
    ]
    analysis_roi = RectRegion(
        x=0,
        y=0,
        width=int(acquisition_roi["width"]),
        height=int(acquisition_roi["height"]),
    )
    metric_box = MetricBox(center_x=880, center_y=645, width=1080, height=700, angle_deg=300.0)
    definition = MeasurementDefinition(
        analysis_roi=analysis_roi,
        metric_box=metric_box,
        point_a_px=PixelPoint(x=912, y=1274),
        point_b_px=PixelPoint(x=1398, y=434),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=200,
        sensitivity=50.0,
        direction_angle_deg=300.0,
        direction_projection_mode="mask_projection",
        observation_axis=ObservationAxis.LONG_AXIS,
    )
    source = PriorTrackingMetricSource(definition=definition)

    stable_metric = source.extract(
        _offline_frame(frame_2281, acquisition_roi, frame_id=2281),
        TempReading(timestamp_ms=2281, celsius=6.5, source="fixture"),
        sample_index=2280,
        total_samples=5807,
    )
    spike_metric = source.extract(
        _offline_frame(frame_2282, acquisition_roi, frame_id=2282),
        TempReading(timestamp_ms=2282, celsius=6.5, source="fixture"),
        sample_index=2281,
        total_samples=5807,
    )

    assert stable_metric.meta["tracking_state"] in {"bootstrapped", "accepted_stabilized"}
    assert spike_metric.meta["tracking_state"] in {"accepted", "accepted_stabilized"}
    assert spike_metric.metric_raw == pytest.approx(stable_metric.metric_raw, abs=8.0)


def test_prior_tracking_keeps_current_high_temp_max_chord_branch_continuous() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    capture_dir = repo_root / "examples/runtime/camera_captures/20260522-183158-dev_lab"
    frame_3921 = capture_dir / "frames/frame_003921.npy"
    frame_3925 = capture_dir / "frames/frame_003925.npy"
    if not frame_3921.exists() or not frame_3925.exists():
        pytest.skip("local offline capture regression fixture is not available")

    acquisition_roi = {"x": 190, "y": 0, "width": 1858, "height": 1364}
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=263, y=79, width=1538, height=1104),
        metric_box=MetricBox(
            center_x=1032,
            center_y=631,
            width=1383,
            height=754,
            angle_deg=-15.812957639483624,
        ),
        # Frame 3921 is on the accepted long contour branch immediately before
        # the current-material high-temp short-branch collapse around 3923/3924.
        point_a_px=PixelPoint(x=543, y=715),
        point_b_px=PixelPoint(x=1545, y=439),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=False,
        min_target_area_px=200,
        sensitivity=50.0,
        direction_angle_deg=-15.812957639483622,
        direction_projection_mode="max_chord",
        observation_axis=ObservationAxis.LONG_AXIS,
    )
    source = PriorTrackingMetricSource(definition=definition)

    states: list[str] = []
    reasons: list[str] = []
    metrics = []
    for frame_id in range(3921, 3926):
        metric = source.extract(
            _offline_frame(
                capture_dir / f"frames/frame_{frame_id:06d}.npy",
                acquisition_roi,
                frame_id=frame_id,
            ),
            TempReading(timestamp_ms=frame_id, celsius=10.2, source="fixture"),
            sample_index=frame_id - 1,
            total_samples=5807,
        )
        states.append(str(metric.meta["tracking_state"]))
        reasons.append(str(metric.meta.get("reason", "")))
        metrics.append(metric)

    metric_values = [float(metric.metric_raw or 0.0) for metric in metrics]
    max_step_px = max(
        abs(current - previous)
        for previous, current in zip(metric_values, metric_values[1:])
    )

    assert "invalidated" not in states
    assert "holding_last_good" not in states
    assert "persistent_reacquire" not in reasons
    assert metrics[-1].point_a_px is not None
    assert metrics[-1].point_b_px is not None
    assert min(metric_values) > 1000.0
    assert max_step_px <= 8.0


def test_prior_tracking_stabilizes_current_max_chord_span_expansion_spike() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    capture_dir = repo_root / "examples/runtime/camera_captures/20260522-183158-dev_lab"
    frame_3846 = capture_dir / "frames/frame_003846.npy"
    frame_3858 = capture_dir / "frames/frame_003858.npy"
    if not frame_3846.exists() or not frame_3858.exists():
        pytest.skip("local offline capture regression fixture is not available")

    acquisition_roi = {"x": 190, "y": 0, "width": 1858, "height": 1364}
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=263, y=79, width=1538, height=1104),
        metric_box=MetricBox(
            center_x=1032,
            center_y=631,
            width=1383,
            height=754,
            angle_deg=-15.812957639483624,
        ),
        # Frame 3846 is the accepted prior immediately before the bad run
        # started rejecting a false one-frame span expansion around frame 3847.
        point_a_px=PixelPoint(x=527, y=687),
        point_b_px=PixelPoint(x=1489, y=416),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=False,
        min_target_area_px=200,
        sensitivity=50.0,
        direction_angle_deg=-15.812957639483622,
        direction_projection_mode="max_chord",
        observation_axis=ObservationAxis.LONG_AXIS,
    )
    source = PriorTrackingMetricSource(definition=definition)

    states: list[str] = []
    metrics = []
    for frame_id in range(3846, 3859):
        metric = source.extract(
            _offline_frame(
                capture_dir / f"frames/frame_{frame_id:06d}.npy",
                acquisition_roi,
                frame_id=frame_id,
            ),
            TempReading(timestamp_ms=frame_id, celsius=10.2, source="fixture"),
            sample_index=frame_id - 1,
            total_samples=5807,
        )
        states.append(str(metric.meta["tracking_state"]))
        metrics.append(metric)

    metric_values = [float(metric.metric_raw or 0.0) for metric in metrics]
    max_step_px = max(
        abs(current - previous)
        for previous, current in zip(metric_values, metric_values[1:])
    )

    assert "invalidated" not in states
    assert "holding_last_good" not in states
    assert max_step_px <= 8.0


def _offline_frame(path: Path, acquisition_roi: dict[str, int], *, frame_id: int) -> FramePacket:
    image = np.load(path)
    x = int(acquisition_roi["x"])
    y = int(acquisition_roi["y"])
    width = int(acquisition_roi["width"])
    height = int(acquisition_roi["height"])
    crop = image[y : y + height, x : x + width]
    return FramePacket(
        timestamp_ms=frame_id,
        source="offline_capture_fixture",
        image=crop,
        frame_id=frame_id,
    )


def _point_distance_for_test(point_a: PixelPoint, point_b: PixelPoint) -> float:
    return float(((point_a.x - point_b.x) ** 2 + (point_a.y - point_b.y) ** 2) ** 0.5)
