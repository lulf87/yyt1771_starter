"""Controlled one-frame camera probe orchestration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.camera.hik_gige_mvs import HikGigeMvsCamera

EXPECTED_BACKEND = "hik_gige_mvs"
EXPECTED_MODEL = "MV-CU060-10GM"
EXPECTED_TRANSPORT = "gige_vision"
EXPECTED_SDK = "hik_mvs"


def run_camera_probe(
    runtime_config: Any,
    camera_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    backend = str(runtime_config.adapters.get("camera", "") or "")
    camera_config = runtime_config.camera
    model = str(camera_config.get("model", "") or "")
    transport = str(camera_config.get("transport", "") or "")
    sdk_name = str(camera_config.get("sdk", "") or "")
    serial_number = str(camera_config.get("serial_number", "") or "")
    ip = str(camera_config.get("ip", "") or "")

    response = {
        "status": "fail",
        "backend": backend,
        "model": model,
        "transport": transport,
        "sdk": sdk_name,
        "identity": {
            "serial_number": serial_number,
            "ip": ip,
        },
        "frame": None,
        "detail": "",
    }

    if backend != EXPECTED_BACKEND:
        response["detail"] = (
            f"{backend or 'missing'} backend does not support real GigE probe. "
            f"Use {EXPECTED_BACKEND} with the production profile."
        )
        return response
    if model != EXPECTED_MODEL:
        response["detail"] = (
            "Camera model is not ready for probe." if not model else
            f"Configured camera model {model} does not match the confirmed {EXPECTED_MODEL} contract."
        )
        return response
    if transport != EXPECTED_TRANSPORT:
        response["detail"] = (
            "camera.transport is not configured."
            if not transport
            else f"{transport} does not match the required {EXPECTED_TRANSPORT} transport."
        )
        return response
    if sdk_name != EXPECTED_SDK:
        response["detail"] = (
            "camera.sdk is not configured."
            if not sdk_name
            else f"{sdk_name} does not match the required {EXPECTED_SDK} SDK."
        )
        return response
    if not serial_number.strip() and not ip.strip():
        response["detail"] = "Camera identity is missing. Configure serial_number or ip before probing."
        return response

    camera = HikGigeMvsCamera(
        model=model,
        transport=transport,
        sdk_name=sdk_name,
        serial_number=serial_number,
        ip=ip,
        trigger_mode=str(camera_config.get("trigger_mode", "free_run") or "free_run"),
        pixel_format=str(camera_config.get("pixel_format", "mono8") or "mono8"),
        exposure_us=int(camera_config.get("exposure_us", 10_000) or 10_000),
        gain_db=float(camera_config.get("gain_db", 0.0) or 0.0),
        timeout_ms=int(camera_config.get("timeout_ms", 1_000) or 1_000),
        camera_factory=camera_factory,
    )
    try:
        probe_payload = camera.probe_once()
    except Exception as exc:
        response["detail"] = _normalize_probe_error(exc)
        return response

    frame_shape = probe_payload.get("frame_shape") or {}
    response["status"] = "ok"
    response["frame"] = {
        "width": int(frame_shape.get("width", 0)),
        "height": int(frame_shape.get("height", 0)),
        "pixel_format": str(probe_payload.get("pixel_format", camera.pixel_format)),
        "frame_id": int(probe_payload.get("frame_id", 0)),
        "timestamp_ms": int(probe_payload.get("timestamp_ms", 0)),
    }
    response["detail"] = "Camera probe succeeded with one frame capture."
    return response


def _normalize_probe_error(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return f"Camera probe failed with {exc.__class__.__name__}."
