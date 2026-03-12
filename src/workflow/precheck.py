"""System readiness checks that avoid live device connections."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_system_precheck(
    profile_name: str,
    storage: dict[str, Any],
    replay: dict[str, Any],
    adapters: dict[str, str],
    project_root: Path,
) -> dict[str, Any]:
    items = [
        _check_sqlite_path(storage.get("sqlite_path"), project_root),
        _check_artifact_dir(storage.get("artifact_dir"), project_root),
        _check_replay_dataset(replay.get("dataset_path"), project_root),
        _check_adapter("camera_adapter", adapters.get("camera")),
        _check_adapter("temp_adapter", adapters.get("temp")),
        _check_adapter("plc_adapter", adapters.get("plc")),
    ]
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


def _check_adapter(name: str, adapter_name: str | None) -> dict[str, str]:
    if not adapter_name:
        return {"name": name, "status": "fail", "detail": f"{name} is not configured"}

    return {
        "name": name,
        "status": "pending",
        "detail": f"{adapter_name} configured; live connectivity is not checked in precheck",
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
