"""Live camera alignment probe for real/offline pixel contract checks."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import json
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
from src.application.runtime_config import load_runtime_config
from src.core.models import FramePacket


def probe_real_camera_alignment(
    runtime_config: Any,
    *,
    camera_opener: Callable[[Any, str], object] | None = None,
    alignment_auditor: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Capture setup and measurement frames and compare them to offline truth.

    This function intentionally attempts live camera access. It is the hardware
    counterpart to the no-device `real_offline_alignment` audit and should be
    run only when the camera is connected and available.
    """

    alignment_contract = _offline_truth_alignment_contract(runtime_config, alignment_auditor=alignment_auditor)
    if alignment_contract["status"] != "ok":
        return {
            "status": "fail",
            "profile": str(getattr(runtime_config, "profile", "") or ""),
            "hardware_access": "not_attempted",
            "alignment_contract": alignment_contract,
            "profiles": [],
            "detail": str(alignment_contract["detail"]),
        }

    opener = camera_opener or _open_camera_for_profile
    profiles: list[dict[str, Any]] = []
    for profile_name in ("setup_preview", "measurement"):
        result = _probe_camera_profile(runtime_config, profile_name=profile_name, camera_opener=opener)
        profiles.append(result)
        if result["status"] != "ok":
            return {
                "status": "fail",
                "profile": str(getattr(runtime_config, "profile", "") or ""),
                "hardware_access": "attempted",
                "alignment_contract": alignment_contract,
                "profiles": profiles,
                "detail": result["detail"],
            }
    return {
        "status": "ok",
        "profile": str(getattr(runtime_config, "profile", "") or ""),
        "hardware_access": "attempted",
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
        return {
            "profile_name": profile_name,
            "status": "ok",
            "expected_size_px": _size_payload(expected_size),
            "actual_size_px": _size_payload(actual_size),
            "expected_device_roi": expected_roi,
            "actual_device_roi": frame_device_roi(frame),
            "acquisition": acquisition,
            "frame_id": frame.frame_id,
            "timestamp_ms": int(frame.timestamp_ms),
            "source": str(frame.source),
            "detail": f"{profile_name} frame matches offline truth pixel contract.",
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
    args = parser.parse_args(argv)
    runtime_config = load_runtime_config(args.profile)
    payload = probe_real_camera_alignment(runtime_config)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
