"""Audit the real-device profile against the accepted offline material profile."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from src.application.device_factory import build_measurement_capture_plan, build_metric_source
from src.application.runtime_config import load_runtime_config
from src.core.config_models import DeviceRoiConfig
from src.core.enums import ObservationAxis
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion, TempReading

REAL_PROFILE = "dev_lab"
REAL_ALIGNMENT_PROFILES = ("dev_lab", "dev_lab_camera_mock_temp", "prod_win")
OFFLINE_PROFILE = "dev_offline_capture"
ANGLES_DEG = tuple(range(0, 360, 30))
SOURCE_WIDTH = 2048
SOURCE_HEIGHT = 1364
OFFLINE_MATERIAL_CAPTURE_DIR = Path("examples/runtime/camera_captures/20260522-183158-dev_lab")
OFFLINE_MATERIAL_REFERENCE_RUN_DIR = Path("examples/runtime/artifacts/run-9953bd601113")
OFFLINE_MATERIAL_SAMPLE_FRAMES = (1, 40, 284, 285, 2281, 2282, 5436, 5437, 5807)
FORMAL_AB_DIRECTION_PROJECTION_MODE = "max_chord"


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
    algorithm_contract = _audit_algorithm_contract(real_config=real_config, offline_config=offline_config)
    angle_results = [
        _audit_angle(real_config=real_config, offline_config=offline_config, angle_deg=angle_deg)
        for angle_deg in angles_deg
    ]
    algorithm_contract["ab_selection"] = _audit_ab_selection_contract(angle_results)
    offline_material = _audit_offline_material_samples(
        real_config=real_config,
        offline_config=offline_config,
        sample_frames=OFFLINE_MATERIAL_SAMPLE_FRAMES,
    )
    return {
        "status": "ok",
        "real_profile": real_config.profile,
        "offline_profile": offline_config.profile,
        "pixel_contract": profile_summary,
        "algorithm_contract": algorithm_contract,
        "angles_checked": len(angle_results),
        "angle_step_deg": 30,
        "angle_results": angle_results,
        "offline_material": offline_material,
        "hardware_access": "not_attempted",
    }


def run_all_alignment_audits(
    *,
    real_profiles: tuple[str, ...] = REAL_ALIGNMENT_PROFILES,
    offline_profile: str = OFFLINE_PROFILE,
    angles_deg: tuple[int, ...] = ANGLES_DEG,
) -> dict[str, Any]:
    """Run the no-hardware offline-truth audit for every locked real profile."""

    profile_results = [
        run_alignment_audit(real_profile=real_profile, offline_profile=offline_profile, angles_deg=angles_deg)
        for real_profile in real_profiles
    ]
    return {
        "status": "ok",
        "offline_profile": offline_profile,
        "profiles_checked": len(profile_results),
        "profile_results": profile_results,
        "hardware_access": "not_attempted",
    }


def _audit_profile_pixel_contract(*, real_config: Any, offline_config: Any) -> dict[str, Any]:
    real_setup_roi = real_config.live.camera.setup_preview.device_roi
    real_measurement_roi = real_config.live.camera.measurement.device_roi
    offline_setup_roi = offline_config.live.camera.setup_preview.device_roi
    offline_measurement_roi = offline_config.live.camera.measurement.device_roi
    real_setup_acquisition = _acquisition_summary(real_config.live.camera.setup_preview)
    real_measurement_acquisition = _acquisition_summary(real_config.live.camera.measurement)
    offline_setup_acquisition = _acquisition_summary(offline_config.live.camera.setup_preview)
    offline_measurement_acquisition = _acquisition_summary(offline_config.live.camera.measurement)
    _assert_equal(real_setup_roi, real_measurement_roi, f"{real_config.profile} setup and measurement ROI differ")
    _assert_equal(offline_setup_roi, offline_measurement_roi, "dev_offline_capture setup and measurement ROI differ")
    _assert_equal(
        real_setup_acquisition,
        offline_setup_acquisition,
        f"{real_config.profile} setup acquisition differs from accepted offline material",
    )
    _assert_equal(
        real_measurement_acquisition,
        offline_measurement_acquisition,
        f"{real_config.profile} measurement acquisition differs from accepted offline material",
    )
    _assert_equal(
        (real_setup_roi.width, real_setup_roi.height),
        (SOURCE_WIDTH, SOURCE_HEIGHT),
        f"{real_config.profile} source pixels drifted",
    )
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
        "setup_preview_acquisition": real_setup_acquisition,
        "measurement_acquisition": real_measurement_acquisition,
    }


def _audit_algorithm_contract(*, real_config: Any, offline_config: Any) -> dict[str, Any]:
    real_vision = _vision_summary(real_config.live.vision)
    offline_vision = _vision_summary(offline_config.live.vision)
    real_tracking_policy = _tracking_policy_summary(real_config.live.run)
    offline_tracking_policy = _tracking_policy_summary(offline_config.live.run)
    real_measurement_timing = _measurement_timing_summary(real_config.live.run)
    offline_measurement_timing = _measurement_timing_summary(offline_config.live.run)
    _assert_equal(
        real_vision,
        offline_vision,
        f"{real_config.profile} vision settings differ from accepted offline material",
    )
    _assert_equal(
        real_tracking_policy,
        offline_tracking_policy,
        f"{real_config.profile} tracking policy differs from accepted offline material",
    )
    _assert_equal(
        real_measurement_timing,
        offline_measurement_timing,
        f"{real_config.profile} measurement timing differs from accepted offline material",
    )
    _assert_equal(
        real_measurement_timing,
        {
            "capture_interval_ms": 100,
            "measurement_target_hz": 10.0,
            "artifact_capture_hz": 10.0,
        },
        f"{real_config.profile} measurement timing drifted from the locked 10 Hz temperature/A-B sampling contract",
    )
    return {
        "vision": real_vision,
        "tracking_policy": real_tracking_policy,
        "measurement_timing": real_measurement_timing,
    }


def _audit_ab_selection_contract(angle_results: list[dict[str, Any]]) -> dict[str, Any]:
    selection_modes = sorted({_formal_ab_selection_mode(item) for item in angle_results})
    _assert_equal(selection_modes, ["directional_contour_max_chord"], "angle audit A/B selection mode drifted")
    if not all(item.get("point_a_px") and item.get("point_b_px") for item in angle_results):
        raise RealOfflineAlignmentError("angle audit did not produce formal A/B points for every checked angle")
    return {
        "formal_point_source": "target_contour_boundary",
        "formal_point_fields": ["point_a_px", "point_b_px"],
        "direction_projection_mode": FORMAL_AB_DIRECTION_PROJECTION_MODE,
        "projected_points_exposed_as_formal_ab": False,
        "angle_audit_selection_modes": selection_modes,
        "angles_checked": len(angle_results),
        "angle_step_deg": 30,
    }


def _formal_ab_selection_mode(item: dict[str, Any]) -> str:
    if str(item.get("projection_point_mode", "")) == FORMAL_AB_DIRECTION_PROJECTION_MODE:
        return "directional_contour_max_chord"
    return str(item.get("selection_mode", ""))


def _audit_offline_material_samples(
    *,
    real_config: Any,
    offline_config: Any,
    sample_frames: tuple[int, ...],
) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    capture_dir = repo_root / OFFLINE_MATERIAL_CAPTURE_DIR
    reference_run_dir = repo_root / OFFLINE_MATERIAL_REFERENCE_RUN_DIR
    manifest_path = capture_dir / "manifest.json"
    definition_path = reference_run_dir / "definition_original.json"
    capture_plan_path = reference_run_dir / "measurement_capture_plan.json"
    required_paths = (manifest_path, definition_path, capture_plan_path)
    missing_paths = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing_paths:
        return {
            "status": "missing",
            "capture_dir": str(OFFLINE_MATERIAL_CAPTURE_DIR),
            "reference_run_dir": str(OFFLINE_MATERIAL_REFERENCE_RUN_DIR),
            "missing": missing_paths,
            "sample_frames_checked": 0,
            "detail": "standard offline material is not available in this checkout",
        }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frames = manifest.get("frames") if isinstance(manifest, dict) else None
    if not isinstance(frames, list) or not frames:
        raise RealOfflineAlignmentError(f"offline material manifest has no frames: {manifest_path}")
    frames_by_index = {int(item.get("index", 0)): item for item in frames if isinstance(item, dict)}
    _assert_equal(int(manifest.get("frame_count", 0)), len(frames), "offline material manifest frame_count differs")
    _assert_equal(int(manifest.get("frame_count", 0)), 5807, "offline material frame count drifted")

    first_frame = frames_by_index.get(1) or frames[0]
    _assert_equal(
        tuple(first_frame.get("shape", ())),
        (SOURCE_HEIGHT, SOURCE_WIDTH),
        "offline material source shape drifted",
    )
    _assert_equal(str(first_frame.get("dtype", "")), "uint8", "offline material dtype drifted")
    camera_meta = first_frame.get("camera_meta") if isinstance(first_frame, dict) else None
    if isinstance(camera_meta, dict):
        _assert_equal(
            camera_meta.get("device_roi"),
            _to_plain(real_config.live.camera.measurement.device_roi),
            "recorded material ROI no longer matches dev_lab measurement ROI",
        )

    definition = _measurement_definition_from_payload(
        json.loads(definition_path.read_text(encoding="utf-8")),
        vision_config=offline_config.live.vision,
        direction_projection_mode=FORMAL_AB_DIRECTION_PROJECTION_MODE,
    )
    accepted_plan = json.loads(capture_plan_path.read_text(encoding="utf-8"))
    accepted_effective_roi = DeviceRoiConfig(**accepted_plan["effective_acquisition_roi"])
    real_plan = build_measurement_capture_plan(runtime_config=real_config, definition=definition)
    offline_plan = build_measurement_capture_plan(runtime_config=offline_config, definition=definition)
    _assert_equal(real_plan.metric_definition, offline_plan.metric_definition, "material metric definition differs")
    _assert_equal(
        offline_plan.measurement_profile.device_roi,
        accepted_effective_roi,
        "offline material effective acquisition ROI drifted",
    )
    _assert_equal(
        real_plan.measurement_profile.device_roi.x - real_plan.setup_preview_roi.x,
        offline_plan.measurement_profile.device_roi.x,
        "material local X origin differs",
    )
    _assert_equal(
        real_plan.measurement_profile.device_roi.y - real_plan.setup_preview_roi.y,
        offline_plan.measurement_profile.device_roi.y,
        "material local Y origin differs",
    )

    real_source = build_metric_source(
        runtime_config=real_config,
        definition=real_plan.metric_definition,
        target_temperature_celsius=45.0,
    )
    offline_source = build_metric_source(
        runtime_config=offline_config,
        definition=offline_plan.metric_definition,
        target_temperature_celsius=45.0,
    )

    sample_results: list[dict[str, Any]] = []
    for frame_index in sample_frames:
        item = frames_by_index.get(int(frame_index))
        if item is None:
            raise RealOfflineAlignmentError(f"offline material sample frame is missing: {frame_index}")
        frame_path = capture_dir / str(item.get("npy", ""))
        if not frame_path.exists():
            raise RealOfflineAlignmentError(f"offline material sample file is missing: {frame_path}")
        source_image = np.load(frame_path)
        _assert_equal(
            tuple(source_image.shape),
            (SOURCE_HEIGHT, SOURCE_WIDTH),
            f"offline material frame shape drifted at {frame_index}",
        )
        crop = _crop_image(source_image, offline_plan.measurement_profile.device_roi)
        timestamp_ms = int(item.get("timestamp_ms", frame_index) or frame_index)
        temperature_payload = item.get("temperature") if isinstance(item, dict) else None
        temperature_c = 25.0
        if isinstance(temperature_payload, dict) and temperature_payload.get("celsius") is not None:
            temperature_c = float(temperature_payload["celsius"])
        frame = FramePacket(
            timestamp_ms=timestamp_ms,
            source="offline_material_alignment_audit",
            image=crop,
            frame_id=int(frame_index),
        )
        temp = TempReading(timestamp_ms=timestamp_ms, celsius=temperature_c, source="offline_material_alignment_audit")
        real_metric = real_source.extract(
            frame,
            temp,
            sample_index=int(frame_index) - 1,
            total_samples=int(manifest["frame_count"]),
        )
        offline_metric = offline_source.extract(
            frame,
            temp,
            sample_index=int(frame_index) - 1,
            total_samples=int(manifest["frame_count"]),
        )
        _assert_metric_parity(real_metric, offline_metric, f"offline material frame {frame_index}")
        sample_results.append(
            {
                "frame_index": int(frame_index),
                "temperature_celsius": temperature_c,
                "selection_mode": real_metric.meta.get("selection_mode"),
                "tracking_state": real_metric.meta.get("tracking_state"),
                "point_a_px": list(real_metric.point_a_px or ()),
                "point_b_px": list(real_metric.point_b_px or ()),
                "metric_raw": real_metric.metric_raw,
                "quality": real_metric.quality,
            }
        )

    return {
        "status": "ok",
        "capture_dir": str(OFFLINE_MATERIAL_CAPTURE_DIR),
        "reference_run_dir": str(OFFLINE_MATERIAL_REFERENCE_RUN_DIR),
        "frame_count": int(manifest["frame_count"]),
        "source_size_px": {"width": SOURCE_WIDTH, "height": SOURCE_HEIGHT},
        "dtype": "uint8",
        "accepted_effective_acquisition_roi": _to_plain(accepted_effective_roi),
        "sample_frames_checked": len(sample_results),
        "sample_results": sample_results,
    }


def _audit_angle(*, real_config: Any, offline_config: Any, angle_deg: int) -> dict[str, Any]:
    definition = _definition_for_angle(angle_deg, vision_config=offline_config.live.vision)
    real_plan = build_measurement_capture_plan(runtime_config=real_config, definition=definition)
    offline_plan = build_measurement_capture_plan(runtime_config=offline_config, definition=definition)
    _assert_equal(
        real_plan.metric_definition,
        offline_plan.metric_definition,
        f"metric definition differs at {angle_deg} deg",
    )
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

    measurement_width = int(offline_plan.measurement_profile.device_roi.width)
    measurement_height = int(offline_plan.measurement_profile.device_roi.height)
    image = np.full((measurement_height, measurement_width), 240, dtype=np.uint8)
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
    _assert_equal(
        real_metric.meta.get("selection_mode"),
        offline_metric.meta.get("selection_mode"),
        f"selection mode differs at {angle_deg} deg",
    )
    _assert_equal(real_metric.point_a_px, offline_metric.point_a_px, f"point A differs at {angle_deg} deg")
    _assert_equal(real_metric.point_b_px, offline_metric.point_b_px, f"point B differs at {angle_deg} deg")
    _assert_equal(real_metric.metric_raw, offline_metric.metric_raw, f"metric raw differs at {angle_deg} deg")
    origin_in_setup = {
        "x": int(real_plan.measurement_profile.device_roi.x - real_plan.setup_preview_roi.x),
        "y": int(real_plan.measurement_profile.device_roi.y - real_plan.setup_preview_roi.y),
    }
    point_a_setup = _local_metric_point_to_setup(real_metric.point_a_px, origin_in_setup)
    point_b_setup = _local_metric_point_to_setup(real_metric.point_b_px, origin_in_setup)
    return {
        "angle_deg": int(angle_deg),
        "measurement_frame_size_px": {
            "width": measurement_width,
            "height": measurement_height,
        },
        "measurement_origin_in_setup_px": origin_in_setup,
        "selection_mode": real_metric.meta.get("selection_mode"),
        "projection_point_mode": real_metric.meta.get("projection_point_mode"),
        "point_a_px": list(real_metric.point_a_px or ()),
        "point_b_px": list(real_metric.point_b_px or ()),
        "point_a_setup_px": point_a_setup,
        "point_b_setup_px": point_b_setup,
        "metric_raw": real_metric.metric_raw,
        "quality": real_metric.quality,
        "contour_settings": _definition_contour_summary(real_plan.metric_definition),
    }


def _local_metric_point_to_setup(point: Any, origin_in_setup: dict[str, int]) -> list[int]:
    if point is None:
        return []
    return [
        int(point[0]) + int(origin_in_setup["x"]),
        int(point[1]) + int(origin_in_setup["y"]),
    ]


def _acquisition_summary(profile: Any) -> dict[str, Any]:
    return {
        "pixel_format": str(profile.pixel_format),
        "exposure_us": int(profile.exposure_us),
        "gain_db": float(profile.gain_db),
    }


def _vision_summary(vision: Any) -> dict[str, Any]:
    return {
        "foreground_polarity": str(vision.foreground_polarity),
        "threshold_mode": str(vision.threshold_mode),
        "edge_threshold": float(vision.edge_threshold),
        "ignore_internal_texture": bool(vision.ignore_internal_texture),
        "min_target_area_px": int(vision.min_target_area_px),
        "quality_threshold": float(vision.quality_threshold),
    }


def _tracking_policy_summary(run: Any) -> dict[str, Any]:
    return {
        "stop_on_invalid_tracking": bool(run.stop_on_invalid_tracking),
        "invalid_tracking_grace_samples": int(run.invalid_tracking_grace_samples),
        "debug_locked_points_tracking": bool(run.debug_locked_points_tracking),
    }


def _measurement_timing_summary(run: Any) -> dict[str, Any]:
    return {
        "capture_interval_ms": int(run.capture_interval_ms),
        "measurement_target_hz": float(run.measurement_target_hz),
        "artifact_capture_hz": float(run.artifact_capture_hz),
    }


def _definition_for_angle(angle_deg: int, *, vision_config: Any) -> MeasurementDefinition:
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
        foreground_polarity=str(vision_config.foreground_polarity),
        threshold_mode=str(vision_config.threshold_mode),
        ignore_internal_texture=bool(vision_config.ignore_internal_texture),
        min_target_area_px=int(vision_config.min_target_area_px),
        direction_angle_deg=float(angle_deg),
        direction_projection_mode=FORMAL_AB_DIRECTION_PROJECTION_MODE,
    )


def _measurement_definition_from_payload(
    payload: dict[str, Any],
    *,
    vision_config: Any | None = None,
    direction_projection_mode: str | None = None,
) -> MeasurementDefinition:
    return MeasurementDefinition(
        analysis_roi=RectRegion(**payload["analysis_roi"]),
        metric_box=MetricBox(**payload["metric_box"]),
        point_a_px=PixelPoint(**payload["point_a_px"]),
        point_b_px=PixelPoint(**payload["point_b_px"]),
        foreground_polarity=(
            str(payload["foreground_polarity"])
            if vision_config is None
            else str(vision_config.foreground_polarity)
        ),
        threshold_mode=(
            str(payload["threshold_mode"])
            if vision_config is None
            else str(vision_config.threshold_mode)
        ),
        ignore_internal_texture=(
            bool(payload["ignore_internal_texture"])
            if vision_config is None
            else bool(vision_config.ignore_internal_texture)
        ),
        min_target_area_px=(
            int(payload["min_target_area_px"])
            if vision_config is None
            else int(vision_config.min_target_area_px)
        ),
        sensitivity=float(payload.get("sensitivity", 50.0)),
        direction_angle_deg=(
            None if payload.get("direction_angle_deg") is None else float(payload["direction_angle_deg"])
        ),
        direction_projection_mode=(
            str(payload.get("direction_projection_mode", "max_chord"))
            if direction_projection_mode is None
            else str(direction_projection_mode)
        ),
        target_geometry_mode=str(payload.get("target_geometry_mode", "single_component")),
        side_guard_ratio=float(payload.get("side_guard_ratio", 0.0) or 0.0),
        observation_axis=ObservationAxis(payload.get("observation_axis", ObservationAxis.LONG_AXIS.value)),
    )


def _definition_contour_summary(definition: MeasurementDefinition) -> dict[str, Any]:
    return {
        "foreground_polarity": str(definition.foreground_polarity),
        "threshold_mode": str(definition.threshold_mode),
        "ignore_internal_texture": bool(definition.ignore_internal_texture),
        "min_target_area_px": int(definition.min_target_area_px),
    }


def _paint_test_line(
    image: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    width: int,
    value: int,
) -> None:
    x0, y0 = float(start[0]), float(start[1])
    x1, y1 = float(end[0]), float(end[1])
    length = math.hypot(x1 - x0, y1 - y0)
    half_width = max(0.5, float(width) / 2.0)
    margin = int(math.ceil(half_width)) + 2
    x_min = max(0, int(math.floor(min(x0, x1) - margin)))
    x_max = min(image.shape[1], int(math.ceil(max(x0, x1) + margin)) + 1)
    y_min = max(0, int(math.floor(min(y0, y1) - margin)))
    y_max = min(image.shape[0], int(math.ceil(max(y0, y1) + margin)) + 1)
    if x_min >= x_max or y_min >= y_max:
        return
    xs, ys = np.meshgrid(
        np.arange(x_min, x_max, dtype=float),
        np.arange(y_min, y_max, dtype=float),
    )
    if length <= 0.0:
        mask = (xs - x0) ** 2 + (ys - y0) ** 2 <= half_width**2
    else:
        direction_x = (x1 - x0) / length
        direction_y = (y1 - y0) / length
        dx = xs - x0
        dy = ys - y0
        along = dx * direction_x + dy * direction_y
        lateral = -dx * direction_y + dy * direction_x
        mask = (along >= 0.0) & (along <= length) & (np.abs(lateral) <= half_width)
    patch = image[y_min:y_max, x_min:x_max]
    patch[mask] = value


def _crop_image(image: np.ndarray, roi: DeviceRoiConfig) -> np.ndarray:
    x = int(roi.x)
    y = int(roi.y)
    width = int(roi.width)
    height = int(roi.height)
    return image[y : y + height, x : x + width].copy()


def _assert_metric_parity(left: Any, right: Any, label: str) -> None:
    _assert_equal(
        left.meta.get("selection_mode"),
        right.meta.get("selection_mode"),
        f"selection mode differs for {label}",
    )
    _assert_equal(
        left.meta.get("tracking_state"),
        right.meta.get("tracking_state"),
        f"tracking state differs for {label}",
    )
    _assert_equal(left.point_a_px, right.point_a_px, f"point A differs for {label}")
    _assert_equal(left.point_b_px, right.point_b_px, f"point B differs for {label}")
    _assert_equal(left.quality, right.quality, f"quality differs for {label}")
    if left.metric_raw is None or right.metric_raw is None:
        _assert_equal(left.metric_raw, right.metric_raw, f"metric raw differs for {label}")
    elif not math.isclose(float(left.metric_raw), float(right.metric_raw), rel_tol=0.0, abs_tol=1e-9):
        raise RealOfflineAlignmentError(f"metric raw differs for {label}: {left.metric_raw!r} != {right.metric_raw!r}")


def _assert_equal(left: Any, right: Any, message: str) -> None:
    if left != right:
        raise RealOfflineAlignmentError(f"{message}: {left!r} != {right!r}")


def _to_plain(value: Any) -> Any:
    if isinstance(value, DeviceRoiConfig):
        return {"x": int(value.x), "y": int(value.y), "width": int(value.width), "height": int(value.height)}
    if is_dataclass(value):
        return asdict(value)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit real-device profiles against the accepted offline material.")
    parser.add_argument(
        "--all-profiles",
        action="store_true",
        help="Audit every locked real/production profile against dev_offline_capture without opening hardware.",
    )
    args = parser.parse_args(argv)
    try:
        payload = run_all_alignment_audits() if args.all_profiles else run_alignment_audit()
    except RealOfflineAlignmentError as exc:
        payload = {"status": "fail", "detail": str(exc), "hardware_access": "not_attempted"}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
