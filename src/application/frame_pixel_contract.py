"""Runtime frame pixel contract checks for real/offline alignment profiles."""

from __future__ import annotations

from typing import Any

from src.core.models import FramePacket

LOCKED_ALIGNMENT_PROFILES = {"dev_lab", "dev_lab_camera_mock_temp", "dev_offline_capture", "prod_win"}


class FramePixelContractError(RuntimeError):
    """Raised when an operator-facing frame does not match locked source pixels."""


def validate_frame_pixel_contract(
    runtime_config: Any,
    *,
    profile_name: str,
    frame: FramePacket,
    context: str,
) -> FramePacket:
    """Validate actual local source pixels before contour/A-B processing."""

    expected_size = expected_frame_size(runtime_config, profile_name=profile_name)
    if expected_size is None:
        return frame
    actual_size = frame_image_size(frame)
    if actual_size != expected_size:
        profile = str(getattr(runtime_config, "profile", "") or "unknown")
        raise FramePixelContractError(
            f"Frame pixel contract mismatch in {context}: profile={profile}, "
            f"camera_profile={profile_name}, expected={expected_size[0]}x{expected_size[1]}, "
            f"actual={actual_size[0]}x{actual_size[1]}. "
            "locked real/offline profiles must enter preset and live run with the same local "
            "source pixels as the accepted offline material before contour and A/B detection."
        )
    expected_roi = expected_frame_device_roi(runtime_config, profile_name=profile_name)
    actual_roi = frame_device_roi(frame)
    if expected_roi is not None and actual_roi is None:
        profile = str(getattr(runtime_config, "profile", "") or "unknown")
        raise FramePixelContractError(
            f"Frame pixel ROI contract mismatch in {context}: profile={profile}, "
            f"camera_profile={profile_name}, expected_roi={format_device_roi(expected_roi)}, "
            "actual_roi=missing device_roi metadata. "
            "locked real/offline profiles must expose the applied camera ROI origin and size "
            "before contour and A/B detection."
        )
    if expected_roi is not None and actual_roi != expected_roi:
        profile = str(getattr(runtime_config, "profile", "") or "unknown")
        raise FramePixelContractError(
            f"Frame pixel ROI contract mismatch in {context}: profile={profile}, "
            f"camera_profile={profile_name}, expected_roi={format_device_roi(expected_roi)}, "
            f"actual_roi={format_device_roi(actual_roi)}. "
            "locked real/offline profiles must use the same applied camera ROI origin and size "
            "as the accepted offline material before contour and A/B detection."
        )
    frame.meta["pixel_contract_profile"] = str(getattr(runtime_config, "profile", "") or "")
    frame.meta["pixel_contract_camera_profile"] = str(profile_name)
    frame.meta["pixel_contract_width"] = int(expected_size[0])
    frame.meta["pixel_contract_height"] = int(expected_size[1])
    if expected_roi is not None:
        frame.meta["pixel_contract_device_roi"] = dict(expected_roi)
    return frame


def expected_frame_size(runtime_config: Any, *, profile_name: str) -> tuple[int, int] | None:
    expected_roi = expected_frame_device_roi(runtime_config, profile_name=profile_name)
    if expected_roi is None:
        return None
    return int(expected_roi["width"]), int(expected_roi["height"])


def expected_frame_device_roi(runtime_config: Any, *, profile_name: str) -> dict[str, int] | None:
    profile = str(getattr(runtime_config, "profile", "") or "")
    if profile not in LOCKED_ALIGNMENT_PROFILES:
        return None
    live_config = getattr(runtime_config, "live", None)
    camera_config = getattr(live_config, "camera", None)
    acquisition_profile = getattr(camera_config, str(profile_name), None)
    device_roi = getattr(acquisition_profile, "device_roi", None)
    x = int(getattr(device_roi, "x", 0) or 0)
    y = int(getattr(device_roi, "y", 0) or 0)
    width = int(getattr(device_roi, "width", 0) or 0)
    height = int(getattr(device_roi, "height", 0) or 0)
    if width < 1 or height < 1:
        return None
    return {"x": x, "y": y, "width": width, "height": height}


def frame_image_size(frame: FramePacket) -> tuple[int, int]:
    image = frame.image
    if hasattr(image, "shape"):
        shape = getattr(image, "shape")
        if len(shape) >= 2:
            return int(shape[1]), int(shape[0])
    if isinstance(image, (list, tuple)):
        height = len(image)
        if height == 0:
            return (0, 0)
        first_row = image[0]
        if isinstance(first_row, (list, tuple)):
            return (len(first_row), height)
        return (height, 1)
    raise FramePixelContractError("Unable to determine frame dimensions for pixel contract validation")


def frame_device_roi(frame: FramePacket) -> dict[str, int] | None:
    payload = frame.meta.get("device_roi")
    if payload is None:
        return None
    try:
        if isinstance(payload, dict):
            return {
                "x": int(payload.get("x", 0) or 0),
                "y": int(payload.get("y", 0) or 0),
                "width": int(payload.get("width", 0) or 0),
                "height": int(payload.get("height", 0) or 0),
            }
        return {
            "x": int(getattr(payload, "x")),
            "y": int(getattr(payload, "y")),
            "width": int(getattr(payload, "width")),
            "height": int(getattr(payload, "height")),
        }
    except (TypeError, ValueError, AttributeError) as exc:
        raise FramePixelContractError(f"Unable to determine frame device_roi for pixel contract validation: {payload!r}") from exc


def format_device_roi(device_roi: dict[str, int]) -> str:
    return (
        f"x={int(device_roi['x'])},y={int(device_roi['y'])},"
        f"width={int(device_roi['width'])},height={int(device_roi['height'])}"
    )
