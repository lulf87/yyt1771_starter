"""Controlled one-frame camera probe orchestration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.camera.hik_gige_mvs import HikGigeMvsCamera

EXPECTED_BACKEND = "hik_gige_mvs"
EXPECTED_TRANSPORT = "gige_vision"
EXPECTED_SDK = "hik_mvs"
PROBE_MODE_PROTOCOL_ANY = "protocol_any"
PROBE_MODE_PINNED = "pinned"
SUPPORTED_PROBE_MODES = {PROBE_MODE_PROTOCOL_ANY, PROBE_MODE_PINNED}


def run_camera_probe(
    runtime_config: Any,
    override: dict[str, Any] | None = None,
    camera_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    backend = str(runtime_config.adapters.get("camera", "") or "")
    camera_config = _merge_camera_override(runtime_config.camera, override)
    policy = resolve_camera_probe_policy(runtime_config.profile, camera_config)
    response = _build_probe_response(backend=backend, policy=policy)

    contract_error = _validate_probe_contract(backend=backend, policy=policy)
    if contract_error is not None:
        response["detail"] = contract_error
        return response

    selection_mode = _resolve_selection_mode(policy)
    camera = HikGigeMvsCamera(
        model=policy["configured_model"],
        transport=policy["transport"],
        sdk_name=policy["sdk"],
        serial_number=policy["serial_number"],
        ip=policy["ip"],
        trigger_mode=policy["trigger_mode"],
        pixel_format=policy["pixel_format"],
        exposure_us=policy["exposure_us"],
        gain_db=policy["gain_db"],
        timeout_ms=policy["timeout_ms"],
        camera_factory=camera_factory,
    )
    try:
        probe_payload = camera.probe_once(selection_mode=selection_mode)
    except Exception as exc:
        response["detail"] = _normalize_probe_error(exc)
        return response

    response["matched_by"] = _normalize_matched_by(policy["probe_mode"], str(probe_payload.get("matched_by", "")))
    response["identity"] = {
        "serial_number": str(probe_payload.get("detected_serial_number", "") or ""),
        "ip": str(probe_payload.get("detected_ip", "") or ""),
    }
    response["device"] = {
        "model": str(probe_payload.get("detected_model", "") or ""),
    }
    frame_shape = probe_payload.get("frame_shape") or {}
    response["frame"] = {
        "width": int(frame_shape.get("width", 0)),
        "height": int(frame_shape.get("height", 0)),
        "pixel_format": str(probe_payload.get("pixel_format", policy["pixel_format"])),
        "frame_id": int(probe_payload.get("frame_id", 0)),
        "timestamp_ms": int(probe_payload.get("timestamp_ms", 0)),
    }

    detected_error = _validate_detected_device(policy=policy, payload=response)
    if detected_error is not None:
        response["detail"] = detected_error
        return response

    response["status"] = "ok"
    response["detail"] = "Camera probe succeeded with one frame capture."
    return response


def resolve_camera_probe_policy(
    profile_name: str,
    camera_config: dict[str, Any],
) -> dict[str, Any]:
    probe_mode = _resolve_probe_mode(profile_name, camera_config)
    allowed_models = resolve_allowed_models(camera_config)
    return {
        "probe_mode": probe_mode,
        "allowed_models": allowed_models,
        "configured_model": str(camera_config.get("model", "") or "").strip(),
        "transport": str(camera_config.get("transport", "") or "").strip(),
        "sdk": str(camera_config.get("sdk", "") or "").strip(),
        "serial_number": str(camera_config.get("serial_number", "") or "").strip(),
        "ip": str(camera_config.get("ip", "") or "").strip(),
        "trigger_mode": str(camera_config.get("trigger_mode", "free_run") or "free_run").strip(),
        "pixel_format": str(camera_config.get("pixel_format", "mono8") or "mono8").strip(),
        "exposure_us": int(camera_config.get("exposure_us", 10_000) or 10_000),
        "gain_db": float(camera_config.get("gain_db", 0.0) or 0.0),
        "timeout_ms": int(camera_config.get("timeout_ms", 1_000) or 1_000),
    }


def resolve_allowed_models(camera_config: dict[str, Any]) -> list[str]:
    if "allowed_models" in camera_config:
        raw_allowed_models = camera_config.get("allowed_models")
        if isinstance(raw_allowed_models, list):
            return [str(item).strip() for item in raw_allowed_models if str(item).strip()]
        if raw_allowed_models is None:
            return []
        text = str(raw_allowed_models).strip()
        if not text:
            return []
        return [item.strip() for item in text.split(",") if item.strip()]

    legacy_model = str(camera_config.get("model", "") or "").strip()
    return [legacy_model] if legacy_model else []


def _merge_camera_override(camera_config: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(camera_config)
    if not override:
        return merged

    for key in ("probe_mode", "allowed_models", "serial_number", "ip"):
        if key in override:
            merged[key] = override[key]
    return merged


def _resolve_probe_mode(profile_name: str, camera_config: dict[str, Any]) -> str:
    probe_mode = str(camera_config.get("probe_mode", "") or "").strip()
    if probe_mode:
        return probe_mode
    return PROBE_MODE_PINNED if profile_name == "prod_win" else PROBE_MODE_PROTOCOL_ANY


def _build_probe_response(backend: str, policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "fail",
        "backend": backend,
        "transport": policy["transport"],
        "sdk": policy["sdk"],
        "probe_mode": policy["probe_mode"],
        "matched_by": "",
        "identity": {
            "serial_number": policy["serial_number"],
            "ip": policy["ip"],
        },
        "device": {
            "model": policy["configured_model"],
        },
        "frame": None,
        "detail": "",
    }


def _validate_probe_contract(backend: str, policy: dict[str, Any]) -> str | None:
    if backend != EXPECTED_BACKEND:
        return (
            f"{backend or 'missing'} backend does not support real GigE probe. "
            f"Use {EXPECTED_BACKEND} with the production profile."
        )
    if policy["probe_mode"] not in SUPPORTED_PROBE_MODES:
        return f"Unsupported probe_mode {policy['probe_mode']}. Expected one of: {sorted(SUPPORTED_PROBE_MODES)}."
    if policy["transport"] != EXPECTED_TRANSPORT:
        return (
            "camera.transport is not configured."
            if not policy["transport"]
            else f"{policy['transport']} does not match the required {EXPECTED_TRANSPORT} transport."
        )
    if policy["sdk"] != EXPECTED_SDK:
        return (
            "camera.sdk is not configured."
            if not policy["sdk"]
            else f"{policy['sdk']} does not match the required {EXPECTED_SDK} SDK."
        )
    if policy["probe_mode"] == PROBE_MODE_PINNED:
        if not policy["allowed_models"]:
            return "Pinned probe mode requires camera.allowed_models to be configured."
        if not policy["serial_number"] and not policy["ip"]:
            return "Pinned probe mode requires serial_number or ip before probing."
    return None


def _resolve_selection_mode(policy: dict[str, Any]) -> str:
    if policy["serial_number"] or policy["ip"]:
        return "pinned"
    return "first_discovered"


def _normalize_matched_by(probe_mode: str, matched_by: str) -> str:
    if probe_mode == PROBE_MODE_PROTOCOL_ANY and matched_by in {"serial_number", "ip"}:
        return "pinned_identity"
    return matched_by


def _validate_detected_device(policy: dict[str, Any], payload: dict[str, Any]) -> str | None:
    actual_model = str(payload["device"].get("model", "") or "").strip()
    actual_serial = str(payload["identity"].get("serial_number", "") or "").strip()
    actual_ip = str(payload["identity"].get("ip", "") or "").strip()
    allowed_models = policy["allowed_models"]

    if policy["probe_mode"] != PROBE_MODE_PINNED:
        return None
    if not actual_model:
        return "Pinned probe succeeded in transport access, but the detected device model could not be resolved."
    if actual_model not in allowed_models:
        return f"Detected camera model {actual_model} is not in the allowed_models whitelist."
    if policy["serial_number"] and actual_serial and actual_serial != policy["serial_number"]:
        return f"Detected camera serial_number {actual_serial} does not match the requested {policy['serial_number']}."
    if policy["ip"] and actual_ip and actual_ip != policy["ip"]:
        return f"Detected camera ip {actual_ip} does not match the requested {policy['ip']}."
    return None


def _normalize_probe_error(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return f"Camera probe failed with {exc.__class__.__name__}."
