"""Live camera alignment probe for real/offline pixel contract checks."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import json
from pathlib import Path
from typing import Any

from src.application.camera_errors import normalize_camera_runtime_error
from src.application.device_factory import camera_profile_for_mode, open_camera
from src.application.frame_pixel_contract import (
    expected_frame_device_roi,
    expected_frame_size,
    frame_device_roi,
    frame_image_size,
    validate_frame_pixel_contract,
)
from src.application.real_offline_alignment import (
    OFFLINE_PROFILE,
    REAL_ALIGNMENT_PROFILES,
    REAL_PROFILE,
    RealOfflineAlignmentError,
    run_alignment_audit,
)
from src.application.real_offline_alignment_guard import (
    RealOfflineAlignmentGuardError,
    assert_real_offline_definition_ready,
)
from src.application.runtime_config import load_runtime_config
from src.core.enums import ObservationAxis
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion
from src.vision.contour_direction import DirectionalContourConfig, DirectionalContourMetricExtractor


def probe_real_camera_alignment(
    runtime_config: Any,
    *,
    camera_opener: Callable[[Any, str], object] | None = None,
    alignment_auditor: Callable[[str], dict[str, Any]] | None = None,
    definition: MeasurementDefinition | None = None,
) -> dict[str, Any]:
    """Capture setup and measurement frames and compare them to offline truth.

    This function intentionally attempts live camera access. It is the hardware
    counterpart to the no-device `real_offline_alignment` audit and should be
    run only when the camera is connected and available.
    """

    frame_source_mode = _frame_source_mode(runtime_config)
    alignment_contract = _offline_truth_alignment_contract(runtime_config, alignment_auditor=alignment_auditor)
    if alignment_contract["status"] != "ok":
        return {
            "status": "fail",
            "profile": str(getattr(runtime_config, "profile", "") or ""),
            "hardware_access": "not_attempted",
            "frame_source_mode": frame_source_mode,
            "frame_access": "not_attempted",
            "alignment_contract": alignment_contract,
            "profiles": [],
            "detail": str(alignment_contract["detail"]),
        }

    if definition is not None:
        try:
            assert_real_offline_definition_ready(
                runtime_config,
                definition,
                context="real_camera_alignment_probe",
            )
        except RealOfflineAlignmentGuardError as exc:
            return {
                "status": "fail",
                "profile": str(getattr(runtime_config, "profile", "") or ""),
                "hardware_access": "not_attempted",
                "frame_source_mode": frame_source_mode,
                "frame_access": "not_attempted",
                "alignment_contract": alignment_contract,
                "profiles": [],
                "detail": str(exc),
            }

    opener = camera_opener or _open_camera_for_profile
    profiles: list[dict[str, Any]] = []
    for profile_name in ("setup_preview", "measurement"):
        result = _probe_camera_profile(
            runtime_config,
            profile_name=profile_name,
            camera_opener=opener,
            definition=definition,
        )
        profiles.append(result)
        if result["status"] != "ok":
            return {
                "status": "fail",
                "profile": str(getattr(runtime_config, "profile", "") or ""),
                "hardware_access": _hardware_access_state(frame_source_mode=frame_source_mode, frame_access="attempted"),
                "frame_source_mode": frame_source_mode,
                "frame_access": "attempted",
                "alignment_contract": alignment_contract,
                "profiles": profiles,
                "detail": result["detail"],
            }
    return {
        "status": "ok",
        "profile": str(getattr(runtime_config, "profile", "") or ""),
        "hardware_access": _hardware_access_state(frame_source_mode=frame_source_mode, frame_access="attempted"),
        "frame_source_mode": frame_source_mode,
        "frame_access": "attempted",
        "alignment_contract": alignment_contract,
        "profiles": profiles,
        "detail": (
            "Real camera setup_preview and measurement frames match the offline truth pixel contract, "
            "and the profile contour / formal A-B contracts match the accepted offline material."
        ),
    }


def _probe_camera_profile(
    runtime_config: Any,
    *,
    profile_name: str,
    camera_opener: Callable[[Any, str], object],
    definition: MeasurementDefinition | None,
) -> dict[str, Any]:
    expected_size = expected_frame_size(runtime_config, profile_name=profile_name)
    expected_roi = expected_frame_device_roi(runtime_config, profile_name=profile_name)
    acquisition = _acquisition_summary(runtime_config, profile_name=profile_name)
    camera: object | None = None
    try:
        camera = camera_opener(runtime_config, profile_name)
        read_frame = getattr(camera, "read_frame")
        if not callable(read_frame):
            raise RuntimeError(f"Camera profile {profile_name} does not expose read_frame()")
        frame = read_frame()
        if not isinstance(frame, FramePacket):
            raise RuntimeError(f"Camera profile {profile_name} did not return a FramePacket")
        validate_frame_pixel_contract(
            runtime_config,
            profile_name=profile_name,
            frame=frame,
            context=f"real_camera_alignment_probe_{profile_name}",
        )
        actual_size = frame_image_size(frame)
        ab_detection = _probe_formal_ab_detection(
            runtime_config,
            frame=frame,
            definition=definition,
        )
        profile_status = "ok" if ab_detection["status"] in {"ok", "not_attempted"} else "fail"
        profile_detail = (
            f"{profile_name} frame matches offline truth pixel contract."
            if profile_status == "ok"
            else f"{profile_name} frame matches pixel contract, but formal A/B detection failed: {ab_detection['detail']}"
        )
        return {
            "profile_name": profile_name,
            "status": profile_status,
            "expected_size_px": _size_payload(expected_size),
            "actual_size_px": _size_payload(actual_size),
            "expected_device_roi": expected_roi,
            "actual_device_roi": frame_device_roi(frame),
            "acquisition": acquisition,
            "frame_id": frame.frame_id,
            "timestamp_ms": int(frame.timestamp_ms),
            "source": str(frame.source),
            "ab_detection": ab_detection,
            "detail": profile_detail,
        }
    except Exception as exc:
        return {
            "profile_name": profile_name,
            "status": "fail",
            "expected_size_px": _size_payload(expected_size),
            "actual_size_px": None,
            "expected_device_roi": expected_roi,
            "actual_device_roi": None,
            "acquisition": acquisition,
            "frame_id": None,
            "timestamp_ms": None,
            "source": "",
            "ab_detection": None,
            "detail": normalize_camera_runtime_error(exc),
        }
    finally:
        if camera is not None:
            close = getattr(camera, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass


def _open_camera_for_profile(runtime_config: Any, profile_name: str) -> object:
    return open_camera(runtime_config, profile_name=profile_name)


def _frame_source_mode(runtime_config: Any) -> str:
    backend = str(getattr(runtime_config, "adapters", {}).get("camera", "") or "")
    if backend in {"hik_gige_mvs", "hik_rtsp_opencv"}:
        return "real_camera"
    if backend in {"offline_capture", "mock"}:
        return backend
    return backend or "unknown"


def _hardware_access_state(*, frame_source_mode: str, frame_access: str) -> str:
    if frame_access != "attempted":
        return "not_attempted"
    return "attempted" if frame_source_mode == "real_camera" else "not_attempted"


def _probe_formal_ab_detection(
    runtime_config: Any,
    *,
    frame: FramePacket,
    definition: MeasurementDefinition | None,
) -> dict[str, Any]:
    if definition is None:
        return {
            "status": "not_attempted",
            "detail": "No measurement definition was provided for real-frame contour/A-B probing.",
        }
    direction_angle_deg = (
        float(definition.metric_box.angle_deg)
        if definition.direction_angle_deg is None
        else float(definition.direction_angle_deg)
    )
    extractor = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=definition.analysis_roi,
            direction_angle_deg=direction_angle_deg,
            metric_box=definition.metric_box,
            foreground_polarity=definition.foreground_polarity,
            threshold_mode=definition.threshold_mode,
            threshold_value=runtime_config.live.vision.edge_threshold,
            ignore_internal_texture=definition.ignore_internal_texture,
            min_target_area_px=definition.min_target_area_px,
            sensitivity=definition.sensitivity,
            component_bridge_kernel=_directional_component_bridge_kernel_for_sensitivity(
                definition.sensitivity,
                direction_angle_deg=direction_angle_deg,
            ),
            projection_mode=definition.direction_projection_mode,
            target_geometry_mode=definition.target_geometry_mode,
            side_guard_ratio=definition.side_guard_ratio,
            envelope_min_support_px=definition.envelope_min_support_px,
            envelope_quantile=definition.envelope_quantile,
            envelope_normal_bin_width_px=definition.envelope_normal_bin_width_px,
            envelope_lateral_window_bins=definition.envelope_lateral_window_bins,
            envelope_endpoint_support_radius_px=definition.envelope_endpoint_support_radius_px,
            envelope_endpoint_min_support_px=definition.envelope_endpoint_min_support_px,
        )
    )
    metric = extractor.extract(frame)
    selection_mode = str(metric.meta.get("selection_mode", "") or "")
    projection_mode = str(metric.meta.get("projection_point_mode", "") or "")
    if metric.metric_raw is None or metric.point_a_px is None or metric.point_b_px is None:
        return {
            "status": "fail",
            "selection_mode": selection_mode or None,
            "direction_projection_mode": projection_mode or definition.direction_projection_mode,
            "quality": float(metric.quality),
            "metric_raw": None,
            "point_a_px": None,
            "point_b_px": None,
            "detail": f"Formal A/B detection failed: {metric.meta.get('reason', 'unknown_error')}",
        }
    expected_selection = "directional_contour_max_chord"
    expected_projection = "max_chord"
    if selection_mode != expected_selection or projection_mode != expected_projection:
        return {
            "status": "fail",
            "selection_mode": selection_mode,
            "direction_projection_mode": projection_mode,
            "quality": float(metric.quality),
            "metric_raw": float(metric.metric_raw),
            "point_a_px": list(metric.point_a_px),
            "point_b_px": list(metric.point_b_px),
            "detail": (
                "Formal A/B detection did not use the offline truth selection mode: "
                f"selection_mode={selection_mode}, direction_projection_mode={projection_mode}"
            ),
        }
    if float(metric.quality) < float(runtime_config.live.vision.quality_threshold):
        return {
            "status": "fail",
            "selection_mode": selection_mode,
            "direction_projection_mode": projection_mode,
            "quality": float(metric.quality),
            "metric_raw": float(metric.metric_raw),
            "point_a_px": list(metric.point_a_px),
            "point_b_px": list(metric.point_b_px),
            "detail": (
                f"Formal A/B detection quality {float(metric.quality):.3f} is below "
                f"offline truth threshold {float(runtime_config.live.vision.quality_threshold):.3f}"
            ),
        }
    return {
        "status": "ok",
        "selection_mode": selection_mode,
        "direction_projection_mode": projection_mode,
        "quality": float(metric.quality),
        "metric_raw": float(metric.metric_raw),
        "point_a_px": list(metric.point_a_px),
        "point_b_px": list(metric.point_b_px),
        "component_area": metric.meta.get("component_area"),
        "threshold_value": metric.meta.get("threshold_value"),
        "detail": "Formal A/B detection used the offline truth contour max-chord rule.",
    }


def _directional_component_bridge_kernel_for_sensitivity(
    sensitivity: float,
    *,
    direction_angle_deg: float,
) -> int:
    normalized = max(0.0, min(100.0, float(sensitivity))) / 100.0
    angle = abs(float(direction_angle_deg) % 180.0)
    near_vertical = abs(angle - 90.0) <= 15.0
    if near_vertical:
        if normalized <= 0.5:
            size = 7.0 + (normalized / 0.5) * 34.0
        else:
            size = 41.0 + ((normalized - 0.5) / 0.5) * 22.0
    elif normalized <= 0.5:
        size = 3.0 + (normalized / 0.5) * 10.0
    else:
        size = 13.0 + ((normalized - 0.5) / 0.5) * 14.0
    kernel = max(1, int(round(size)))
    if kernel % 2 == 0:
        kernel += 1
    return kernel


def _offline_truth_alignment_contract(
    runtime_config: Any,
    *,
    alignment_auditor: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    profile = str(getattr(runtime_config, "profile", "") or "")
    real_profile = profile if profile in REAL_ALIGNMENT_PROFILES else REAL_PROFILE
    auditor = alignment_auditor or _run_alignment_audit_for_profile
    try:
        payload = auditor(real_profile)
    except RealOfflineAlignmentError as exc:
        return {
            "status": "fail",
            "real_profile": real_profile,
            "offline_profile": OFFLINE_PROFILE,
            "pixel_contract": None,
            "algorithm_contract": None,
            "angles_checked": None,
            "angle_step_deg": None,
            "hardware_access": "not_attempted",
            "detail": str(exc),
        }
    return {
        "status": str(payload.get("status", "ok")),
        "real_profile": str(payload.get("real_profile", real_profile) or real_profile),
        "offline_profile": str(payload.get("offline_profile", OFFLINE_PROFILE) or OFFLINE_PROFILE),
        "pixel_contract": payload.get("pixel_contract"),
        "algorithm_contract": payload.get("algorithm_contract"),
        "angles_checked": payload.get("angles_checked"),
        "angle_step_deg": payload.get("angle_step_deg"),
        "hardware_access": str(payload.get("hardware_access", "not_attempted") or "not_attempted"),
        "detail": "Real/offline pixel, contour, and formal A-B contracts match before live camera access.",
    }


def _run_alignment_audit_for_profile(real_profile: str) -> dict[str, Any]:
    return run_alignment_audit(real_profile=real_profile)


def _size_payload(size: tuple[int, int] | None) -> dict[str, int] | None:
    if size is None:
        return None
    return {"width": int(size[0]), "height": int(size[1])}


def _acquisition_summary(runtime_config: Any, *, profile_name: str) -> dict[str, Any]:
    profile = camera_profile_for_mode(runtime_config.live.camera, profile_name)
    return {
        "pixel_format": str(profile.pixel_format),
        "exposure_us": int(profile.exposure_us),
        "gain_db": float(profile.gain_db),
    }


def _load_measurement_definition(path: Path) -> MeasurementDefinition:
    definition_path = _resolve_measurement_definition_path(path)
    payload = json.loads(definition_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        for key in ("definition", "definition_original", "measurement_definition"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                payload = nested
                break
    if not isinstance(payload, dict):
        raise ValueError("measurement definition file must contain a JSON object")
    return _measurement_definition_from_payload(payload)


def _resolve_measurement_definition_path(path: Path) -> Path:
    if path.is_dir():
        for name in ("definition_original.json", "definition.json", "definition_effective_local.json"):
            candidate = path / name
            if candidate.exists():
                return candidate
        raise FileNotFoundError(
            f"Run artifact directory does not contain definition_original.json, definition.json, "
            f"or definition_effective_local.json: {path}"
        )
    return path


def _measurement_definition_from_payload(payload: dict[str, Any]) -> MeasurementDefinition:
    return MeasurementDefinition(
        analysis_roi=RectRegion(
            x=int(payload["analysis_roi"]["x"]),
            y=int(payload["analysis_roi"]["y"]),
            width=int(payload["analysis_roi"]["width"]),
            height=int(payload["analysis_roi"]["height"]),
        ),
        metric_box=MetricBox(
            center_x=int(payload["metric_box"]["center_x"]),
            center_y=int(payload["metric_box"]["center_y"]),
            width=int(payload["metric_box"]["width"]),
            height=int(payload["metric_box"]["height"]),
            angle_deg=float(payload["metric_box"].get("angle_deg", 0.0)),
        ),
        point_a_px=PixelPoint(x=int(payload["point_a_px"]["x"]), y=int(payload["point_a_px"]["y"])),
        point_b_px=PixelPoint(x=int(payload["point_b_px"]["x"]), y=int(payload["point_b_px"]["y"])),
        foreground_polarity=str(payload["foreground_polarity"]),
        threshold_mode=str(payload["threshold_mode"]),
        ignore_internal_texture=bool(payload["ignore_internal_texture"]),
        min_target_area_px=int(payload["min_target_area_px"]),
        sensitivity=float(payload.get("sensitivity", 50.0)),
        direction_angle_deg=(
            None if payload.get("direction_angle_deg") is None else float(payload["direction_angle_deg"])
        ),
        direction_projection_mode=str(payload.get("direction_projection_mode", "max_chord")),
        target_geometry_mode=str(payload.get("target_geometry_mode", "single_component")),
        side_guard_ratio=float(payload.get("side_guard_ratio", 0.0) or 0.0),
        envelope_min_support_px=int(payload.get("envelope_min_support_px", 3) or 3),
        envelope_quantile=float(payload.get("envelope_quantile", 0.0) or 0.0),
        envelope_normal_bin_width_px=float(payload.get("envelope_normal_bin_width_px", 5.0) or 5.0),
        envelope_lateral_window_bins=int(payload.get("envelope_lateral_window_bins", 1) or 1),
        envelope_endpoint_support_radius_px=float(payload.get("envelope_endpoint_support_radius_px", 3.0) or 3.0),
        envelope_endpoint_min_support_px=int(payload.get("envelope_endpoint_min_support_px", 3) or 3),
        envelope_relocate_confirm_frames=int(payload.get("envelope_relocate_confirm_frames", 3) or 3),
        envelope_near_tie_span_ratio=float(payload.get("envelope_near_tie_span_ratio", 0.03) or 0.03),
        envelope_immediate_span_gain_ratio=float(payload.get("envelope_immediate_span_gain_ratio", 0.12) or 0.12),
        observation_axis=ObservationAxis(str(payload.get("observation_axis", ObservationAxis.LONG_AXIS.value))),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read one setup_preview frame and one measurement frame from a connected real camera, "
            "then compare both against the accepted offline material pixel contract."
        ),
    )
    parser.add_argument(
        "--profile",
        default="dev_lab",
        help="Runtime profile used to open the real camera, for example dev_lab or prod_win.",
    )
    parser.add_argument(
        "--definition-file",
        type=Path,
        help=(
            "Optional MeasurementDefinition JSON from the Web setup flow, or a run artifact directory containing "
            "definition_original.json. When provided, the probe also validates formal A/B contour detection on "
            "setup_preview and measurement frames."
        ),
    )
    args = parser.parse_args(argv)
    runtime_config = load_runtime_config(args.profile)
    definition = None if args.definition_file is None else _load_measurement_definition(args.definition_file)
    payload = probe_real_camera_alignment(runtime_config, definition=definition)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
