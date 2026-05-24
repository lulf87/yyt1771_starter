"""Diagnostic capture helpers for recording camera frames as offline fixtures."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
import time
from typing import Any

import numpy as np

from src.core.contracts import CameraPort, TempReader


FRAME_FORMATS = {"none", "npy", "png", "both"}


@dataclass(slots=True)
class CaptureOptions:
    output_dir: Path
    profile: str
    camera_profile: str
    frame_format: str = "npy"
    save_video: bool = True
    video_fps: float = 20.0
    duration_sec: float | None = None
    max_frames: int | None = None
    target_fps: float | None = None
    temp_every_n_frames: int = 1


@dataclass(slots=True)
class CaptureSummary:
    output_dir: Path
    manifest_path: Path
    frame_count: int
    elapsed_sec: float
    video_path: Path | None = None
    temperature_csv_path: Path | None = None


def capture_frames(
    camera: CameraPort,
    options: CaptureOptions,
    *,
    temp_reader: TempReader | None = None,
) -> CaptureSummary:
    """Capture frames from a camera-like source and persist raw grayscale fixtures."""

    frame_format = str(options.frame_format or "npy").lower()
    if frame_format not in FRAME_FORMATS:
        raise ValueError(f"Unsupported frame format: {options.frame_format}")
    if options.max_frames is not None and int(options.max_frames) < 1:
        raise ValueError("max_frames must be positive when provided")
    if options.duration_sec is not None and float(options.duration_sec) <= 0:
        raise ValueError("duration_sec must be positive when provided")
    temp_every_n_frames = max(1, int(options.temp_every_n_frames or 1))

    output_dir = Path(options.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    if frame_format != "none":
        frames_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    video_writer = _LazyVideoWriter(
        output_dir / "capture.avi",
        fps=_positive_float(options.video_fps, default=20.0),
        enabled=bool(options.save_video),
    )
    temperature_csv_path = output_dir / "temperature.csv" if temp_reader is not None else None

    started_monotonic = time.monotonic()
    started_at_ms = int(time.time() * 1000)
    manifest: dict[str, Any] = {
        "profile": options.profile,
        "camera_profile": options.camera_profile,
        "started_at_ms": started_at_ms,
        "duration_limit_sec": options.duration_sec,
        "max_frames": options.max_frames,
        "target_fps": options.target_fps,
        "frame_format": frame_format,
        "video": "capture.avi" if options.save_video else None,
        "temperature_csv": "temperature.csv" if temp_reader is not None else None,
        "temp_every_n_frames": temp_every_n_frames if temp_reader is not None else None,
        "frame_count": 0,
        "frames": [],
    }

    frame_count = 0
    latest_temperature: dict[str, Any] | None = None
    temperature_rows: list[dict[str, Any]] = []
    try:
        while _should_continue(
            started_monotonic=started_monotonic,
            duration_sec=options.duration_sec,
            max_frames=options.max_frames,
            frame_count=frame_count,
        ):
            loop_started = time.monotonic()
            packet = camera.read_frame()
            gray = _coerce_gray_array(packet.image)
            frame_count += 1
            sampled_this_frame = False
            if temp_reader is not None and (
                latest_temperature is None or ((frame_count - 1) % temp_every_n_frames == 0)
            ):
                latest_temperature = _read_temperature(temp_reader)
                sampled_this_frame = True
            frame_name = f"frame_{frame_count:06d}"
            frame_entry = _write_frame(
                frames_dir=frames_dir,
                frame_name=frame_name,
                gray=gray,
                frame_format=frame_format,
            )
            video_writer.write(gray)
            frame_entry.update(
                {
                    "index": frame_count,
                    "timestamp_ms": packet.timestamp_ms,
                    "source": packet.source,
                    "frame_id": packet.frame_id,
                    "shape": [int(v) for v in gray.shape],
                    "dtype": str(gray.dtype),
                    "camera_meta": packet.meta,
                }
            )
            if latest_temperature is not None:
                frame_entry["temperature"] = {
                    **latest_temperature,
                    "sampled_this_frame": sampled_this_frame,
                }
                temperature_rows.append(
                    _temperature_csv_row(
                        frame_index=frame_count,
                        camera_timestamp_ms=packet.timestamp_ms,
                        temperature=latest_temperature,
                        sampled_this_frame=sampled_this_frame,
                    )
                )
            manifest["frames"].append(frame_entry)
            manifest["frame_count"] = frame_count
            _sleep_for_target_fps(loop_started=loop_started, target_fps=options.target_fps)
    except KeyboardInterrupt:
        manifest["interrupted"] = True
    except Exception as exc:
        manifest["error"] = str(exc)
        raise
    finally:
        elapsed_sec = time.monotonic() - started_monotonic
        manifest["elapsed_sec"] = elapsed_sec
        manifest["achieved_fps"] = frame_count / elapsed_sec if elapsed_sec > 0 and frame_count else 0.0
        if temperature_csv_path is not None:
            _write_temperature_csv(temperature_csv_path, temperature_rows)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        video_writer.release()
        _close_camera(camera)
        if temp_reader is not None:
            _close_reader(temp_reader)

    elapsed_sec = time.monotonic() - started_monotonic
    return CaptureSummary(
        output_dir=output_dir,
        manifest_path=manifest_path,
        frame_count=frame_count,
        elapsed_sec=elapsed_sec,
        video_path=video_writer.path if video_writer.created else None,
        temperature_csv_path=temperature_csv_path,
    )


def _should_continue(
    *,
    started_monotonic: float,
    duration_sec: float | None,
    max_frames: int | None,
    frame_count: int,
) -> bool:
    if max_frames is not None and frame_count >= int(max_frames):
        return False
    if duration_sec is not None and (time.monotonic() - started_monotonic) >= float(duration_sec):
        return False
    return True


def _write_frame(
    *,
    frames_dir: Path,
    frame_name: str,
    gray: np.ndarray,
    frame_format: str,
) -> dict[str, Any]:
    entry: dict[str, Any] = {}
    if frame_format in {"npy", "both"}:
        npy_path = frames_dir / f"{frame_name}.npy"
        np.save(npy_path, gray)
        entry["npy"] = str(npy_path.relative_to(frames_dir.parent))
    if frame_format in {"png", "both"}:
        png_path = frames_dir / f"{frame_name}.png"
        _write_png(png_path, gray)
        entry["png"] = str(png_path.relative_to(frames_dir.parent))
    return entry


def _read_temperature(temp_reader: TempReader) -> dict[str, Any]:
    try:
        reading = temp_reader.read()
    except Exception as exc:
        return {
            "timestamp_ms": None,
            "celsius": None,
            "source": None,
            "error": str(exc),
        }
    return {
        "timestamp_ms": int(reading.timestamp_ms),
        "celsius": float(reading.celsius),
        "source": reading.source,
        "error": "",
    }


def _temperature_csv_row(
    *,
    frame_index: int,
    camera_timestamp_ms: int,
    temperature: dict[str, Any],
    sampled_this_frame: bool,
) -> dict[str, Any]:
    return {
        "frame_index": int(frame_index),
        "camera_timestamp_ms": int(camera_timestamp_ms),
        "temp_timestamp_ms": temperature.get("timestamp_ms"),
        "celsius": temperature.get("celsius"),
        "source": temperature.get("source") or "",
        "sampled_this_frame": 1 if sampled_this_frame else 0,
        "error": temperature.get("error") or "",
    }


def _write_temperature_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "frame_index",
        "camera_timestamp_ms",
        "temp_timestamp_ms",
        "celsius",
        "source",
        "sampled_this_frame",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _coerce_gray_array(image: Any) -> np.ndarray:
    if image is None:
        raise ValueError("Camera frame has no image payload")
    array = np.asarray(image)
    if array.ndim == 2:
        return np.ascontiguousarray(array)
    if array.ndim == 3 and array.shape[2] == 1:
        return np.ascontiguousarray(array[:, :, 0])
    if array.ndim == 3 and array.shape[2] >= 3:
        red = array[:, :, 0].astype(np.float32)
        green = array[:, :, 1].astype(np.float32)
        blue = array[:, :, 2].astype(np.float32)
        gray = np.rint((0.299 * red) + (0.587 * green) + (0.114 * blue))
        return np.ascontiguousarray(gray.astype(array.dtype, copy=False))
    raise ValueError(f"Unsupported camera frame shape: {array.shape}")


def _write_png(path: Path, gray: np.ndarray) -> None:
    from PIL import Image

    Image.fromarray(_uint8_view(gray)).save(path)


def _uint8_view(gray: np.ndarray) -> np.ndarray:
    array = np.asarray(gray)
    if array.dtype == np.uint8:
        return np.ascontiguousarray(array)
    if np.issubdtype(array.dtype, np.integer):
        info = np.iinfo(array.dtype)
        if info.max <= info.min:
            return np.zeros(array.shape, dtype=np.uint8)
        scaled = (array.astype(np.float32) - float(info.min)) * (255.0 / float(info.max - info.min))
        return np.ascontiguousarray(np.clip(np.rint(scaled), 0, 255).astype(np.uint8))
    if np.issubdtype(array.dtype, np.floating):
        finite = array[np.isfinite(array)]
        if finite.size == 0:
            return np.zeros(array.shape, dtype=np.uint8)
        min_value = float(finite.min())
        max_value = float(finite.max())
        if max_value <= min_value:
            return np.zeros(array.shape, dtype=np.uint8)
        scaled = (array.astype(np.float32) - min_value) * (255.0 / (max_value - min_value))
        return np.ascontiguousarray(np.clip(np.rint(scaled), 0, 255).astype(np.uint8))
    return np.ascontiguousarray(array.astype(np.uint8, copy=False))


def _sleep_for_target_fps(*, loop_started: float, target_fps: float | None) -> None:
    if target_fps is None:
        return
    fps = float(target_fps)
    if fps <= 0:
        return
    remaining = (1.0 / fps) - (time.monotonic() - loop_started)
    if remaining > 0:
        time.sleep(remaining)


def _positive_float(value: float | None, *, default: float) -> float:
    if value is None:
        return default
    resolved = float(value)
    return resolved if resolved > 0 else default


def _close_camera(camera: CameraPort) -> None:
    for method_name in ("close", "release"):
        method = getattr(camera, method_name, None)
        if callable(method):
            method()
            return


def _close_reader(reader: TempReader) -> None:
    method = getattr(reader, "close", None)
    if callable(method):
        method()


class _LazyVideoWriter:
    def __init__(self, path: Path, *, fps: float, enabled: bool) -> None:
        self.path = path
        self.fps = fps
        self.enabled = enabled
        self.created = False
        self._writer: Any | None = None

    def write(self, gray: np.ndarray) -> None:
        if not self.enabled:
            return
        if self._writer is None:
            self._writer = self._open(gray)
            self.created = True
        self._writer.write(_uint8_view(gray))

    def release(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None

    def _open(self, gray: np.ndarray) -> Any:
        try:
            import cv2  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on optional runtime import
            raise RuntimeError("opencv-python is required to write capture video") from exc

        height, width = np.asarray(gray).shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        writer = cv2.VideoWriter(str(self.path), fourcc, self.fps, (int(width), int(height)), isColor=False)
        if not writer.isOpened():
            raise RuntimeError(f"Could not open video writer: {self.path}")
        return writer
