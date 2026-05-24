"""File-backed camera adapter for recorded grayscale capture sequences."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any

import numpy as np

from src.core.contracts import CameraPort
from src.core.config_models import DeviceRoiConfig
from src.core.models import FramePacket


class OfflineCaptureCamera(CameraPort):
    """Replay `.npy` frames captured from the real camera."""

    def __init__(
        self,
        *,
        capture_dir: str | Path,
        profile_name: str = "setup_preview",
        device_roi: DeviceRoiConfig | None = None,
        loop: bool = True,
    ) -> None:
        self.capture_dir = Path(capture_dir)
        self.profile_name = str(profile_name)
        self.device_roi = device_roi or DeviceRoiConfig()
        self.loop = bool(loop)
        self._frame_paths = _resolve_frame_paths(self.capture_dir)
        self._manifest_frames = _load_manifest_frames(self.capture_dir)
        self._cursor = 0
        self._read_count = 0

    def read_frame(self) -> FramePacket:
        if self._cursor >= len(self._frame_paths):
            if not self.loop:
                raise EOFError(f"Offline capture exhausted: {self.capture_dir}")
            self._cursor = 0

        source_frame_index = self._cursor + 1
        frame_path = self._frame_paths[self._cursor]
        self._cursor += 1
        self._read_count += 1

        source_image = np.load(frame_path)
        if not hasattr(source_image, "shape") or len(source_image.shape) < 2:
            raise ValueError(f"Offline frame must be a 2D grayscale array: {frame_path}")
        source_height, source_width = int(source_image.shape[0]), int(source_image.shape[1])
        image = _apply_device_roi(source_image, self.device_roi)
        manifest_frame = self._manifest_frames.get(frame_path.name, {})
        recorded_timestamp_ms = manifest_frame.get("timestamp_ms")
        camera_meta = manifest_frame.get("camera_meta") if isinstance(manifest_frame, dict) else None
        meta: dict[str, Any] = {
            "format": "offline_capture_npy",
            "profile_name": self.profile_name,
            "capture_dir": str(self.capture_dir),
            "frame_path": str(frame_path),
            "source_frame_index": int(manifest_frame.get("index", source_frame_index) or source_frame_index),
            "source_frame_count": len(self._frame_paths),
            "source_width": source_width,
            "source_height": source_height,
            "device_roi": {
                "x": int(self.device_roi.x),
                "y": int(self.device_roi.y),
                "width": int(self.device_roi.width),
                "height": int(self.device_roi.height),
            },
        }
        if recorded_timestamp_ms is not None:
            meta["recorded_timestamp_ms"] = int(recorded_timestamp_ms)
        if isinstance(camera_meta, dict):
            meta["recorded_camera_meta"] = camera_meta

        return FramePacket(
            timestamp_ms=int(time.time() * 1000),
            source=f"offline_capture:{self.capture_dir.name}",
            image=image,
            frame_id=self._read_count,
            meta=meta,
        )

    def close(self) -> None:
        return None

    def playback_sample_count(self) -> int:
        return len(self._frame_paths)


def _resolve_frame_paths(capture_dir: Path) -> list[Path]:
    frames_dir = capture_dir / "frames"
    if not frames_dir.exists():
        raise FileNotFoundError(f"Offline capture frames directory not found: {frames_dir}")
    frame_paths = sorted(frames_dir.glob("*.npy"))
    if not frame_paths:
        raise FileNotFoundError(f"Offline capture contains no .npy frames: {frames_dir}")
    return frame_paths


def _load_manifest_frames(capture_dir: Path) -> dict[str, dict[str, Any]]:
    manifest_path = capture_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    frames = raw.get("frames") if isinstance(raw, dict) else None
    if not isinstance(frames, list):
        return {}
    resolved: dict[str, dict[str, Any]] = {}
    for item in frames:
        if not isinstance(item, dict):
            continue
        npy_path = str(item.get("npy", "") or "")
        if not npy_path:
            continue
        resolved[Path(npy_path).name] = item
    return resolved


def _apply_device_roi(image: np.ndarray, device_roi: DeviceRoiConfig) -> np.ndarray:
    if int(device_roi.width) <= 0 or int(device_roi.height) <= 0:
        return image.copy()
    height, width = int(image.shape[0]), int(image.shape[1])
    x = max(0, min(width, int(device_roi.x)))
    y = max(0, min(height, int(device_roi.y)))
    crop_width = max(0, min(int(device_roi.width), width - x))
    crop_height = max(0, min(int(device_roi.height), height - y))
    if crop_width < 1 or crop_height < 1:
        raise ValueError(
            "Offline capture device_roi does not overlap the recorded frame: "
            f"x={device_roi.x}, y={device_roi.y}, width={device_roi.width}, height={device_roi.height}, "
            f"frame_width={width}, frame_height={height}"
        )
    return image[y : y + crop_height, x : x + crop_width].copy()


__all__ = ["OfflineCaptureCamera"]
