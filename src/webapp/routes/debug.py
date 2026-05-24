"""Optional debug endpoints used by the web shell."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.application.container import ApplicationContainer
from src.application.runtime_config import RuntimeConfig


router = APIRouter(prefix="/api/debug", tags=["debug"])


class FixtureVideoSwitchRequest(BaseModel):
    key: str


def _empty_fixture_video_payload() -> dict[str, object]:
    return {
        "current": None,
        "current_label": None,
        "videos": [],
    }


@router.get("/fixture-videos")
def list_fixture_videos(request: Request) -> dict[str, object]:
    return _fixture_video_payload(_runtime_config(request))


@router.post("/fixture-videos/current")
def switch_fixture_video(payload: FixtureVideoSwitchRequest, request: Request) -> dict[str, object]:
    runtime_config = _runtime_config(request)
    offline_config = _offline_capture_config(runtime_config)
    fixtures = _fixture_records(offline_config)
    if not fixtures:
        return _empty_fixture_video_payload()
    requested_key = str(payload.key or "").strip()
    for fixture in fixtures:
        if fixture["key"] != requested_key:
            continue
        offline_config["capture_dir"] = fixture["capture_dir"]
        offline_config["current_key"] = fixture["key"]
        container = getattr(request.app.state, "application_container", None)
        if isinstance(container, ApplicationContainer):
            container.reset_temp_controller()
            container.live_preview_service.retire_active_stream(timeout_ms=1_000)
        return _fixture_video_payload(runtime_config)
    raise HTTPException(status_code=404, detail=f"Unknown fixture video: {requested_key}")


def _runtime_config(request: Request) -> RuntimeConfig:
    return request.app.state.runtime_config


def _fixture_video_payload(runtime_config: RuntimeConfig) -> dict[str, object]:
    offline_config = _offline_capture_config(runtime_config)
    fixtures = _fixture_records(offline_config)
    if not fixtures:
        return _empty_fixture_video_payload()
    current_key = str(offline_config.get("current_key", "") or "").strip()
    current_capture_dir = str(offline_config.get("capture_dir", "") or "").strip()
    if not current_key:
        for fixture in fixtures:
            if _same_path(fixture["capture_dir"], current_capture_dir):
                current_key = fixture["key"]
                break
    if not current_key:
        current_key = fixtures[0]["key"]
        offline_config["capture_dir"] = fixtures[0]["capture_dir"]
    offline_config["current_key"] = current_key
    current_label = next(
        (fixture["label"] for fixture in fixtures if fixture["key"] == current_key),
        current_key,
    )
    return {
        "current": current_key,
        "current_label": current_label,
        "videos": [{"key": fixture["key"], "label": fixture["label"]} for fixture in fixtures],
    }


def _offline_capture_config(runtime_config: RuntimeConfig) -> dict[str, Any]:
    if str(runtime_config.adapters.get("camera", "") or "") != "offline_capture":
        return {}
    offline_config = runtime_config.camera.get("offline_capture")
    if not isinstance(offline_config, dict):
        return {}
    return offline_config


def _fixture_records(offline_config: dict[str, Any]) -> list[dict[str, str]]:
    raw_fixtures = offline_config.get("fixtures")
    fixtures: list[dict[str, str]] = []
    if isinstance(raw_fixtures, list):
        for item in raw_fixtures:
            if not isinstance(item, dict):
                continue
            capture_dir = str(item.get("capture_dir", "") or "").strip()
            if not capture_dir:
                continue
            key = str(item.get("key", "") or "").strip() or Path(capture_dir).name
            label = str(item.get("label", "") or "").strip() or key
            fixtures.append({"key": key, "label": label, "capture_dir": capture_dir})
    if fixtures:
        return fixtures
    capture_dir = str(offline_config.get("capture_dir", "") or "").strip()
    if not capture_dir:
        return []
    key = str(offline_config.get("current_key", "") or "").strip() or Path(capture_dir).name
    label = str(offline_config.get("label", "") or "").strip() or key
    return [{"key": key, "label": label, "capture_dir": capture_dir}]


def _same_path(first: str, second: str) -> bool:
    if not first or not second:
        return False
    return Path(first).expanduser() == Path(second).expanduser()
