"""System readiness checks that avoid live device connections."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.camera.hik_gige_mvs import import_hik_mvs_sdk_module
from src.workflow.camera_probe import (
    EXPECTED_SDK,
    EXPECTED_TRANSPORT,
    PROBE_MODE_PINNED,
    PROBE_MODE_PROTOCOL_ANY,
    SUPPORTED_PROBE_MODES,
    resolve_camera_probe_policy,
)

SUPPORTED_CAMERA_BACKENDS = {"mock", "hik_rtsp_opencv", "hik_gige_mvs"}


def build_system_precheck(
    profile_name: str,
    storage: dict[str, Any],
    replay: dict[str, Any],
    adapters: dict[str, str],
    camera: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    camera_backend = adapters.get("camera")
    items = [
        _check_sqlite_path(storage.get("sqlite_path"), project_root),
        _check_artifact_dir(storage.get("artifact_dir"), project_root),
        _check_replay_dataset(replay.get("dataset_path"), project_root),
        _check_camera_backend(camera_backend),
        _check_adapter("temp_adapter", adapters.get("temp")),
        _check_adapter("plc_adapter", adapters.get("plc")),
    ]
    if camera_backend == "hik_gige_mvs":
        items.extend(_check_hik_gige_camera_config(profile_name, camera))
    return {
        "profile": profile_name,
        "status": _aggregate_status(items),
        "items": items,
    }


def _check_sqlite_path(sqlite_path: Any, project_root: Path) -> dict[str, str]:
    if not sqlite_path:
        return {"name": "sqlite_path", "status": "fail", "detail": "storage.sqlite_path is not configured"}

    resolved_path = _resolve_path(str(sqlite_path), project_root)
    try:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"name": "sqlite_path", "status": "fail", "detail": f"{resolved_path.parent} is not writable: {exc}"}

    return {
        "name": "sqlite_path",
        "status": "ok",
        "detail": f"{resolved_path.parent} is available for {resolved_path.name}",
    }


def _check_artifact_dir(artifact_dir: Any, project_root: Path) -> dict[str, str]:
    if not artifact_dir:
        return {"name": "artifact_dir", "status": "fail", "detail": "storage.artifact_dir is not configured"}

    resolved_path = _resolve_path(str(artifact_dir), project_root)
    try:
        resolved_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"name": "artifact_dir", "status": "fail", "detail": f"{resolved_path} is not writable: {exc}"}

    return {"name": "artifact_dir", "status": "ok", "detail": f"{resolved_path} is available"}


def _check_replay_dataset(dataset_path: Any, project_root: Path) -> dict[str, str]:
    if not dataset_path:
        return {"name": "replay_dataset", "status": "warn", "detail": "replay.dataset_path is not configured"}

    resolved_path = _resolve_path(str(dataset_path), project_root)
    if not resolved_path.exists():
        return {"name": "replay_dataset", "status": "fail", "detail": f"{resolved_path} was not found"}

    return {"name": "replay_dataset", "status": "ok", "detail": f"{resolved_path} found"}


def _check_camera_backend(adapter_name: str | None) -> dict[str, str]:
    if not adapter_name:
        return {"name": "camera_backend", "status": "fail", "detail": "adapters.camera is not configured"}
    if adapter_name not in SUPPORTED_CAMERA_BACKENDS:
        return {
            "name": "camera_backend",
            "status": "fail",
            "detail": f"{adapter_name} is not a supported camera backend",
        }
    if adapter_name == "mock":
        return {
            "name": "camera_backend",
            "status": "ok",
            "detail": "mock camera backend configured for offline development",
        }
    if adapter_name == "hik_rtsp_opencv":
        return {
            "name": "camera_backend",
            "status": "ok",
            "detail": "hik_rtsp_opencv configured; live RTSP connectivity is not checked in precheck",
        }
    return {
        "name": "camera_backend",
        "status": "ok",
        "detail": "hik_gige_mvs configured; camera parameters are checked without live SDK/device access",
    }


def _check_adapter(name: str, adapter_name: str | None) -> dict[str, str]:
    if not adapter_name:
        return {"name": name, "status": "fail", "detail": f"{name} is not configured"}

    return {
        "name": name,
        "status": "pending",
        "detail": f"{adapter_name} configured; live connectivity is not checked in precheck",
    }


def _check_hik_gige_camera_config(profile_name: str, camera: dict[str, Any]) -> list[dict[str, str]]:
    probe_policy = resolve_camera_probe_policy(profile_name, camera)
    items = [
        _check_camera_probe_mode(probe_policy["probe_mode"]),
        _check_camera_model_policy(probe_policy),
        _check_camera_transport(probe_policy["transport"]),
        _check_camera_identity(probe_policy),
        _check_camera_sdk(probe_policy["sdk"]),
        _check_camera_sdk_runtime(probe_policy["sdk"]),
    ]
    return items


def _check_camera_probe_mode(probe_mode: str) -> dict[str, str]:
    if probe_mode in SUPPORTED_PROBE_MODES:
        return {
            "name": "camera_probe_mode",
            "status": "ok",
            "detail": f"{probe_mode} is a supported camera probe strategy",
        }
    return {
        "name": "camera_probe_mode",
        "status": "fail",
        "detail": f"{probe_mode or 'missing'} is not a supported camera probe strategy",
    }


def _check_camera_model_policy(probe_policy: dict[str, Any]) -> dict[str, str]:
    allowed_models = probe_policy["allowed_models"]
    if probe_policy["probe_mode"] == PROBE_MODE_PROTOCOL_ANY:
        return {
            "name": "camera_model_policy",
            "status": "pending",
            "detail": "protocol_any does not restrict camera model before probing; model matching happens after protocol discovery",
        }
    if allowed_models:
        return {
            "name": "camera_model_policy",
            "status": "ok",
            "detail": f"Allowed models configured: {', '.join(allowed_models)}",
        }
    return {
        "name": "camera_model_policy",
        "status": "fail",
        "detail": "Pinned probe mode requires camera.allowed_models to be configured",
    }


def _check_camera_transport(transport: str) -> dict[str, str]:
    if transport == EXPECTED_TRANSPORT:
        return {
            "name": "camera_transport",
            "status": "ok",
            "detail": f"{EXPECTED_TRANSPORT} matches the Hik GigE / MVS transport contract",
        }
    if not transport:
        return {"name": "camera_transport", "status": "fail", "detail": "camera.transport is not configured"}
    return {
        "name": "camera_transport",
        "status": "fail",
        "detail": f"{transport} does not match the required {EXPECTED_TRANSPORT} transport",
    }


def _check_camera_identity(probe_policy: dict[str, Any]) -> dict[str, str]:
    serial_number = probe_policy["serial_number"]
    ip = probe_policy["ip"]
    if serial_number:
        return {
            "name": "camera_identity",
            "status": "ok",
            "detail": f"camera.serial_number is configured as {serial_number}",
        }
    if ip:
        return {
            "name": "camera_identity",
            "status": "ok",
            "detail": f"camera.ip is configured as {ip}",
        }
    if probe_policy["probe_mode"] == PROBE_MODE_PROTOCOL_ANY:
        return {
            "name": "camera_identity",
            "status": "pending",
            "detail": "protocol_any allows serial_number and ip to stay empty; probe will use first discovered device when no identity is provided",
        }
    return {
        "name": "camera_identity",
        "status": "fail",
        "detail": "Pinned probe mode requires camera.serial_number or camera.ip before probing",
    }


def _check_camera_sdk(sdk_name: str) -> dict[str, str]:
    if not sdk_name:
        return {"name": "camera_sdk", "status": "fail", "detail": "camera.sdk is not configured"}
    if sdk_name != EXPECTED_SDK:
        return {
            "name": "camera_sdk",
            "status": "fail",
            "detail": f"{sdk_name} does not match the required {EXPECTED_SDK} SDK contract",
        }
    return {
        "name": "camera_sdk",
        "status": "pending",
        "detail": "hik_mvs configured; precheck validates config only and does not import or connect the live SDK",
    }


def _check_camera_sdk_runtime(sdk_name: str) -> dict[str, str]:
    if not sdk_name:
        return {"name": "camera_sdk_runtime", "status": "fail", "detail": "camera.sdk is not configured"}
    if sdk_name != EXPECTED_SDK:
        return {
            "name": "camera_sdk_runtime",
            "status": "fail",
            "detail": f"{sdk_name} does not match the required {EXPECTED_SDK} SDK runtime contract",
        }

    try:
        import_hik_mvs_sdk_module()
    except Exception as exc:
        return {
            "name": "camera_sdk_runtime",
            "status": "warn",
            "detail": (
                "hik_mvs is configured, but local SDK/Python import readiness is not complete: "
                f"{exc}. Precheck only verifies SDK import readiness and does not attempt live device access."
            ),
        }

    return {
        "name": "camera_sdk_runtime",
        "status": "ok",
        "detail": "hik_mvs Python binding is importable on this machine. Precheck only verifies SDK import readiness and does not attempt live device access.",
    }


def _aggregate_status(items: list[dict[str, str]]) -> str:
    statuses = {item["status"] for item in items}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses or "pending" in statuses:
        return "warn"
    return "ok"


def _resolve_path(value: str, project_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root / path
