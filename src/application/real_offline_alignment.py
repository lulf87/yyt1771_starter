"""Audit the real-device profile against the accepted offline material profile."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
import math
from typing import Any

import numpy as np

from src.application.device_factory import build_measurement_capture_plan, build_metric_source
from src.application.runtime_config import load_runtime_config
from src.core.config_models import DeviceRoiConfig
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion, TempReading

REAL_PROFILE = "dev_lab"
OFFLINE_PROFILE = "dev_offline_capture"
ANGLES_DEG = tuple(range(0, 360, 30))
SOURCE_WIDTH = 2048
SOURCE_HEIGHT = 1364


class RealOfflineAlignmentError(AssertionError):
    """Raised when real/offline profile alignment drifts."""


def run_alignment_audit(
    *,
    real_profile: str = REAL_PROFILE,
    offline_profile: str = OFFLINE_PROFILE,
    angles_deg: tuple[int, ...] = ANGLES_DEG,
) -> dict[str, Any]:
    """Compare real and offline profile pixels, contour selection, and A/B points.

    This audit intentionally does not open the real camera or temperature
    controller. It verifies that the real-device profile would feed the same
    local source pixels and metric chain as the accepted offline material.
    """

    real_config = load_runtime_config(real_profile)
    offline_config = load_runtime_config(offline_profile)
    profile_summary = _audit_profile_pixel_contract(real_config=real_config, offline_config=offline_config)
    angle_results = [
        _audit_angle(real_config=real_config, offline_config=offline_config, angle_deg=angle_deg) for angle_deg in angles_deg
    ]
    return {
        "status": "ok",
        "real_profile": real_config.profile,
        "offline_profile": offline_config.profile,
        "pixel_contract": profile_summary,
        "angles_checked": len(angle_results),
        "angle_step_deg": 30,
        "angle_results": angle_results,
        "hardware_access": "not_attempted",
    }


def _audit_profile_pixel_contract(*, real_config: Any, offline_config: Any) -> dict[str, Any]:
    real_setup_roi = real_config.live.camera.setup_preview.device_roi
    real_measurement_roi = real_config.live.camera.measurement.device_roi
    offline_setup_roi = offline_config.live.camera.setup_preview.device_roi
    offline_measurement_roi = offline_config.live.camera.measurement.device_roi
    _assert_equal(real_setup_roi, real_measurement_roi, "dev_lab setup and measurement ROI differ")
    _assert_equal(offline_setup_roi, offline_measurement_roi, "dev_offline_capture setup and measurement ROI differ")
    _assert_equal((real_setup_roi.width, real_setup_roi.height), (SOURCE_WIDTH, SOURCE_HEIGHT), "dev_lab source pixels drifted")
    _assert_equal(
        (offline_setup_roi.width, offline_setup_roi.height),
        (SOURCE_WIDTH, SOURCE_HEIGHT),
        "dev_offline_capture source pixels drifted",
    )
    _assert_equal(
        real_config.live.run.preview_display_max_width,
        offline_config.live.run.preview_display_max_width,
        "preview display width differs",
    )
    _assert_equal(
        real_config.live.run.preview_display_max_height,
        offline_config.live.run.preview_display_max_height,
        "preview display height differs",
    )
    return {
        "real_setup_roi": _to_plain(real_setup_roi),
        "offline_setup_roi": _to_plain(offline_setup_roi),
        "source_size_px": {"width": SOURCE_WIDTH, "height": SOURCE_HEIGHT},
        "preview_display_px": {
            "width": int(real_config.live.run.preview_display_max_width),
            "height": int(real_config.live.run.preview_display_max_height),
        },
    }


def _audit_angle(*, real_config: Any, offline_config: Any, angle_deg: int) -> dict[str, Any]:
    definition = _definition_for_angle(angle_deg)
    real_plan = build_measurement_capture_plan(runtime_config=real_config, definition=definition)
    offline_plan = build_measurement_capture_plan(runtime_config=offline_config, definition=definition)
    _assert_equal(real_plan.metric_definition, offline_plan.metric_definition, f"metric definition differs at {angle_deg} deg")
    _assert_equal(
        real_plan.measurement_profile.device_roi.width,
        offline_plan.measurement_profile.device_roi.width,
        f"measurement ROI width differs at {angle_deg} deg",
    )
    _assert_equal(
        real_plan.measurement_profile.device_roi.height,
        offline_plan.measurement_profile.device_roi.height,
        f"measurement ROI height differs at {angle_deg} deg",
    )
    _assert_equal(
        real_plan.measurement_profile.device_roi.x - real_plan.setup_preview_roi.x,
        offline_plan.measurement_profile.device_roi.x,
        f"measurement local X origin differs at {angle_deg} deg",
    )
    _assert_equal(
        real_plan.measurement_profile.device_roi.y - real_plan.setup_preview_roi.y,
        offline_plan.measurement_profile.device_roi.y,
        f"measurement local Y origin differs at {angle_deg} deg",
    )

    image = np.full((SOURCE_HEIGHT, SOURCE_WIDTH), 240, dtype=np.uint8)
    _paint_test_line(
        image,
        (real_plan.metric_definition.point_a_px.x, real_plan.metric_definition.point_a_px.y),
        (real_plan.metric_definition.point_b_px.x, real_plan.metric_definition.point_b_px.y),
        width=28,
        value=30,
    )
    frame = FramePacket(timestamp_ms=1_000, source="alignment_audit", image=image, frame_id=1)
    temp = TempReading(timestamp_ms=1_005, celsius=25.0, source="alignment_audit")
    real_metric = build_metric_source(
        runtime_config=real_config,
        definition=real_plan.metric_definition,
        target_temperature_celsius=45.0,
    ).extract(frame, temp, sample_index=0, total_samples=1)
    offline_metric = build_metric_source(
        runtime_config=offline_config,
        definition=offline_plan.metric_definition,
        target_temperature_celsius=45.0,
    ).extract(frame, temp, sample_index=0, total_samples=1)

    if real_metric.quality <= 0.0 or offline_metric.quality <= 0.0:
        raise RealOfflineAlignmentError(f"metric quality failed at {angle_deg} deg")
    _assert_equal(real_metric.meta.get("selection_mode"), offline_metric.meta.get("selection_mode"), f"selection mode differs at {angle_deg} deg")
    _assert_equal(real_metric.point_a_px, offline_metric.point_a_px, f"point A differs at {angle_deg} deg")
    _assert_equal(real_metric.point_b_px, offline_metric.point_b_px, f"point B differs at {angle_deg} deg")
    _assert_equal(real_metric.metric_raw, offline_metric.metric_raw, f"metric raw differs at {angle_deg} deg")
    return {
        "angle_deg": int(angle_deg),
        "selection_mode": real_metric.meta.get("selection_mode"),
        "point_a_px": list(real_metric.point_a_px or ()),
        "point_b_px": list(real_metric.point_b_px or ()),
        "metric_raw": real_metric.metric_raw,
        "quality": real_metric.quality,
    }


def _definition_for_angle(angle_deg: int) -> MeasurementDefinition:
    center_x = 1024
    center_y = 682
    half_span = 420
    angle_rad = math.radians(angle_deg)
    dx = int(round(math.cos(angle_rad) * half_span))
    dy = int(round(math.sin(angle_rad) * half_span))
    return MeasurementDefinition(
        analysis_roi=RectRegion(x=120, y=120, width=1800, height=1120),
        metric_box=MetricBox(center_x=center_x, center_y=center_y, width=980, height=220, angle_deg=float(angle_deg)),
        point_a_px=PixelPoint(x=center_x - dx, y=center_y - dy),
        point_b_px=PixelPoint(x=center_x + dx, y=center_y + dy),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        ignore_internal_texture=True,
        min_target_area_px=150,
        direction_angle_deg=float(angle_deg),
        direction_projection_mode="max_chord",
    )


def _paint_test_line(
    image: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    width: int,
    value: int,
) -> None:
    x0, y0 = start
    x1, y1 = end
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    radius = max(0, int(width) // 2)
    for index in range(steps + 1):
        ratio = index / steps
        x = int(round(x0 + (x1 - x0) * ratio))
        y = int(round(y0 + (y1 - y0) * ratio))
        image[
            max(0, y - radius) : min(image.shape[0], y + radius + 1),
            max(0, x - radius) : min(image.shape[1], x + radius + 1),
        ] = value


def _assert_equal(left: Any, right: Any, message: str) -> None:
    if left != right:
        raise RealOfflineAlignmentError(f"{message}: {left!r} != {right!r}")


def _to_plain(value: Any) -> Any:
    if isinstance(value, DeviceRoiConfig):
        return {"x": int(value.x), "y": int(value.y), "width": int(value.width), "height": int(value.height)}
    if is_dataclass(value):
        return asdict(value)
    return value


def main() -> int:
    try:
        payload = run_alignment_audit()
    except RealOfflineAlignmentError as exc:
        payload = {"status": "fail", "detail": str(exc), "hardware_access": "not_attempted"}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
