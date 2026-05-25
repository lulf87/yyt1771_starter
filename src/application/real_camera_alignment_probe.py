"""Live camera alignment probe for real/offline pixel contract checks."""

from __future__ import annotations

from collections.abc import Callable
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
from src.core.models import FramePacket


def probe_real_camera_alignment(
    runtime_config: Any,
    *,
    camera_opener: Callable[[Any, str], object] | None = None,
) -> dict[str, Any]:
    """Capture setup and measurement frames and compare them to offline truth.

    This function intentionally attempts live camera access. It is the hardware
    counterpart to the no-device `real_offline_alignment` audit and should be
    run only when the camera is connected and available.
    """

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
                "profiles": profiles,
                "detail": result["detail"],
            }
    return {
        "status": "ok",
        "profile": str(getattr(runtime_config, "profile", "") or ""),
        "hardware_access": "attempted",
        "profiles": profiles,
        "detail": "Real camera setup_preview and measurement frames match the offline truth pixel contract.",
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
