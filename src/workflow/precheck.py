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

SUPPORTED_CAMERA_BACKENDS = {"mock", "hik_rtsp_opencv", "hik_gige_mvs", "offline_capture"}
ALIGNMENT_PROFILES = {
    "dev_lab": {"origin": (512, 342), "size": (2048, 1364)},
    "dev_offline_capture": {"origin": (0, 0), "size": (2048, 1364)},
}
ALIGNMENT_PREVIEW_DISPLAY_SIZE = (816, 544)


def build_system_precheck(
    profile_name: str,
    storage: dict[str, Any],
    replay: dict[str, Any],
    adapters: dict[str, str],
    camera: dict[str, Any],
    project_root: Path,
    run_config: Any | None = None,
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
    alignment_item = _check_active_profile_pixel_alignment(profile_name, camera, run_config)
    if alignment_item is not None:
        items.append(alignment_item)
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
    if adapter_name == "offline_capture":
        return {
            "name": "camera_backend",
            "status": "ok",
            "detail": "offline_capture configured for standard material replay; live camera access is not checked in precheck",
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


def _check_active_profile_pixel_alignment(
    profile_name: str,
    camera: dict[str, Any],
    run_config: Any | None,
) -> dict[str, str] | None:
    expected = ALIGNMENT_PROFILES.get(profile_name)
    if expected is None:
        return None
    setup_roi = _device_roi_from_camera_section(camera, "setup_preview")
    measurement_roi = _device_roi_from_camera_section(camera, "measurement")
    expected_origin = tuple(expected["origin"])
    expected_size = tuple(expected["size"])
    if setup_roi is None or measurement_roi is None:
        return {
            "name": "real_offline_pixel_alignment",
            "status": "fail",
            "detail": f"{profile_name} must define setup_preview and measurement device_roi for real/offline alignment",
        }
    if setup_roi != measurement_roi:
        return {
            "name": "real_offline_pixel_alignment",
            "status": "fail",
            "detail": (
                f"{profile_name} setup_preview device_roi {setup_roi} differs from measurement device_roi {measurement_roi}; "
                "preset and live run would use different source pixels"
            ),
        }
    origin = (setup_roi["x"], setup_roi["y"])
    size = (setup_roi["width"], setup_roi["height"])
    if origin != expected_origin or size != expected_size:
        return {
            "name": "real_offline_pixel_alignment",
            "status": "fail",
            "detail": (
                f"{profile_name} device_roi origin/size {origin}/{size} does not match the locked real/offline "
                f"alignment contract {expected_origin}/{expected_size}"
            ),
        }
    preview_size = _preview_display_size(run_config)
    if preview_size is not None and preview_size != ALIGNMENT_PREVIEW_DISPLAY_SIZE:
        return {
            "name": "real_offline_pixel_alignment",
            "status": "fail",
            "detail": (
                f"{profile_name} preview display bound {preview_size} does not match the locked "
                f"{ALIGNMENT_PREVIEW_DISPLAY_SIZE} real/offline display contract"
            ),
        }
    preview_detail = (
        f", preview_display={preview_size[0]}x{preview_size[1]}"
        if preview_size is not None
        else ", preview_display not provided to precheck"
    )
    return {
        "name": "real_offline_pixel_alignment",
        "status": "ok",
        "detail": (
            f"{profile_name} setup/live source pixels match the offline truth contract: "
            f"origin={origin}, size={size}{preview_detail}"
        ),
    }


def _device_roi_from_camera_section(camera: dict[str, Any], section: str) -> dict[str, int] | None:
    payload = camera.get(section)
    if not isinstance(payload, dict):
        return None
    roi = payload.get("device_roi")
    if not isinstance(roi, dict):
        return None
    try:
        return {
            "x": int(roi.get("x", 0) or 0),
            "y": int(roi.get("y", 0) or 0),
            "width": int(roi.get("width", 0) or 0),
            "height": int(roi.get("height", 0) or 0),
        }
    except (TypeError, ValueError):
        return None


def _preview_display_size(run_config: Any | None) -> tuple[int, int] | None:
    if run_config is None:
        return None
    try:
        width = _get_config_value(run_config, "preview_display_max_width")
        height = _get_config_value(run_config, "preview_display_max_height")
        if width is None or height is None:
            return None
        return int(width), int(height)
    except (TypeError, ValueError):
        return None


def _get_config_value(config: Any, key: str) -> Any:
    if isinstance(config, dict):
        return config.get(key)
    return getattr(config, key, None)


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
