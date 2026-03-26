"""Shared preview service used by application shells."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Iterator
import threading
import time

from src.application.device_factory import open_camera
from src.application.runtime_config import RuntimeConfig
from src.core.models import FramePacket


@dataclass(slots=True)
class _ActivePreviewStream:
    run_id: str
    camera: object
    stop_event: threading.Event
    started_at_monotonic: float
    frames_presented: int = 0
    first_presented_at_monotonic: float | None = None
    last_presented_at_monotonic: float | None = None
    latest_frame: FramePacket | None = None
    latest_sequence: int = 0
    last_presented_signature: tuple[object, ...] | None = None
    frame_event: threading.Event = field(default_factory=threading.Event)
    frame_lock: threading.Lock = field(default_factory=threading.Lock)
    close_lock: threading.Lock = field(default_factory=threading.Lock)
    reader_thread: threading.Thread | None = None
    reader_error: str = ""
    closed: bool = False


@dataclass(slots=True)
class PreviewStateSnapshot:
    stream_active: bool
    frozen_frame_available: bool
    last_frame_id: int | None = None
    preview_display_fps: float | None = None


class LivePreviewService:
    """Preview bridge used by setup flows across delivery shells."""

    def __init__(self) -> None:
        self._state_lock = threading.Lock()
        self._active_stream: _ActivePreviewStream | None = None
        self._latest_frame: FramePacket | None = None
        self._latest_frame_run_id = ""
        self._latest_tracking_frame: FramePacket | None = None
        self._latest_tracking_frame_run_id = ""
        self._last_preview_display_fps: float | None = None
        self._last_preview_display_fps_run_id = ""

    def fetch_frame(
        self,
        runtime_config: RuntimeConfig,
        *,
        run_id: str = "",
        prefer_cached: bool = False,
    ) -> FramePacket:
        cached_frame = self._latest_frame_for_run(run_id) if prefer_cached else None
        if cached_frame is not None:
            return cached_frame
        frame = self._read_with_close(self.open_camera(runtime_config, profile_name="setup_preview"))
        if run_id:
            self._store_latest_frame(run_id, frame)
        return frame

    def start_stream(
        self,
        runtime_config: RuntimeConfig,
        *,
        run_id: str,
    ) -> tuple[object, FramePacket]:
        with self._state_lock:
            if self._active_stream is not None:
                raise RuntimeError(f"Live preview stream is already active for run: {self._active_stream.run_id}")

        camera = self.open_camera(runtime_config, profile_name="setup_preview")
        try:
            first_frame = self._read_from_camera(camera)
        except Exception:
            close = getattr(camera, "close", None)
            if callable(close):
                close()
            raise

        active_stream = _ActivePreviewStream(
            run_id=run_id,
            camera=camera,
            stop_event=threading.Event(),
            started_at_monotonic=time.monotonic(),
            latest_frame=first_frame,
            latest_sequence=1,
        )
        with self._state_lock:
            if self._active_stream is not None:
                close = getattr(camera, "close", None)
                if callable(close):
                    close()
                raise RuntimeError(f"Live preview stream is already active for run: {self._active_stream.run_id}")
            self._active_stream = active_stream
            self._latest_frame = first_frame
            self._latest_frame_run_id = run_id
            self._last_preview_display_fps = None
            self._last_preview_display_fps_run_id = run_id
        active_stream.reader_thread = threading.Thread(
            target=self._preview_reader_worker,
            args=(active_stream,),
            name=f"preview-reader-{run_id}",
            daemon=True,
        )
        active_stream.reader_thread.start()
        return active_stream, first_frame

    def open_camera(self, runtime_config: RuntimeConfig, *, profile_name: str = "setup_preview") -> object:
        return open_camera(runtime_config, profile_name=profile_name)

    def stream_frames(
        self,
        active_stream: object,
        *,
        first_frame: FramePacket,
        frame_interval_ms: int,
    ) -> Iterator[FramePacket]:
        assert isinstance(active_stream, _ActivePreviewStream)
        hardware_paced = _frame_is_hardware_paced(first_frame)
        minimum_interval_ms = (
            0 if hardware_paced else compute_preview_interval_ms(fallback_ms=frame_interval_ms)
        )
        frame_interval_s = minimum_interval_ms / 1000.0
        last_emitted_sequence = 1
        last_emit_monotonic = time.monotonic()
        try:
            frame = first_frame
            while True:
                self._mark_stream_frame(active_stream, frame)
                yield frame
                if active_stream.stop_event.is_set():
                    break
                while True:
                    if active_stream.stop_event.is_set():
                        break
                    remaining_s = max(0.0, frame_interval_s - (time.monotonic() - last_emit_monotonic))
                    if remaining_s > 0 and active_stream.stop_event.wait(remaining_s):
                        break
                    if active_stream.stop_event.is_set():
                        break
                    if active_stream.stop_event.is_set():
                        break
                    with active_stream.frame_lock:
                        latest_sequence = active_stream.latest_sequence
                        latest_frame = active_stream.latest_frame
                        if latest_sequence > last_emitted_sequence:
                            active_stream.frame_event.clear()
                    if latest_frame is None or latest_sequence <= last_emitted_sequence:
                        active_stream.frame_event.wait(0.01)
                        continue
                    frame = latest_frame
                    last_emitted_sequence = latest_sequence
                    last_emit_monotonic = time.monotonic()
                    break
        finally:
            self._close_stream(active_stream)

    def stop_stream(self, *, run_id: str) -> bool:
        with self._state_lock:
            active_stream = self._active_stream
            if active_stream is None or active_stream.run_id != run_id:
                return False
            active_stream.stop_event.set()
            active_stream.frame_event.set()
            return True

    def wait_for_stream_stop(self, *, run_id: str, timeout_ms: int = 1_000) -> bool:
        deadline = time.time() + max(0.05, timeout_ms / 1000)
        while time.time() < deadline:
            with self._state_lock:
                active_stream = self._active_stream
                if active_stream is None or active_stream.run_id != run_id:
                    return True
            time.sleep(0.01)
        return False

    def force_stop_stream(self, *, run_id: str) -> bool:
        with self._state_lock:
            active_stream = self._active_stream
            if active_stream is None or active_stream.run_id != run_id:
                return False
            self._active_stream = None
            self._last_preview_display_fps = _preview_display_fps(active_stream)
            self._last_preview_display_fps_run_id = active_stream.run_id
        active_stream.stop_event.set()
        active_stream.frame_event.set()
        close = getattr(active_stream.camera, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
        reader_thread = active_stream.reader_thread
        if reader_thread is not None and reader_thread.is_alive():
            reader_thread.join(timeout=0.25)
        return True

    def get_preview_state(self, *, run_id: str) -> PreviewStateSnapshot:
        with self._state_lock:
            active_stream = self._active_stream
            stream_active = bool(
                active_stream is not None
                and active_stream.run_id == run_id
                and not active_stream.stop_event.is_set()
            )
            frame = self._latest_frame if self._latest_frame_run_id == run_id else None
            preview_display_fps = None
            if active_stream is not None and active_stream.run_id == run_id:
                preview_display_fps = _preview_display_fps(active_stream)
            elif self._last_preview_display_fps_run_id == run_id:
                preview_display_fps = self._last_preview_display_fps
            return PreviewStateSnapshot(
                stream_active=stream_active,
                frozen_frame_available=bool(frame is not None and not stream_active),
                last_frame_id=None if frame is None else frame.frame_id,
                preview_display_fps=preview_display_fps,
            )

    def cache_frame(self, *, run_id: str, frame: FramePacket) -> None:
        if not run_id:
            return
        self._store_latest_frame(run_id, frame)

    def get_cached_frame(self, *, run_id: str) -> FramePacket | None:
        return self._latest_frame_for_run(run_id)

    def cache_tracking_frame(self, *, run_id: str, frame: FramePacket) -> None:
        if not run_id:
            return
        with self._state_lock:
            self._latest_tracking_frame = frame
            self._latest_tracking_frame_run_id = run_id

    def get_tracking_frame(self, *, run_id: str) -> FramePacket | None:
        if not run_id:
            return None
        with self._state_lock:
            if self._latest_tracking_frame_run_id != run_id:
                return None
            return self._latest_tracking_frame

    def get_active_probe_payload(self) -> dict[str, object] | None:
        with self._state_lock:
            active_stream = self._active_stream
            if active_stream is None:
                return None
            frame = active_stream.latest_frame
            camera = active_stream.camera
        if frame is None:
            return None

        width, height = _frame_dimensions(frame)
        return {
            "backend": str(getattr(camera, "backend_name", "") or frame.meta.get("backend", "")),
            "transport": str(getattr(camera, "transport", "") or frame.meta.get("transport", "")),
            "sdk": str(getattr(camera, "sdk_name", "") or frame.meta.get("sdk", "")),
            "matched_by": "active_preview",
            "detected_model": str(getattr(camera, "model", "") or frame.meta.get("model", "")),
            "detected_serial_number": str(
                getattr(camera, "serial_number", "") or frame.meta.get("serial_number", "")
            ),
            "detected_ip": str(getattr(camera, "ip", "") or frame.meta.get("ip", "")),
            "frame_shape": {
                "width": width,
                "height": height,
            },
            "pixel_format": str(getattr(camera, "pixel_format", "") or frame.meta.get("pixel_format", "")),
            "frame_id": None if frame.frame_id is None else int(frame.frame_id),
            "timestamp_ms": int(frame.timestamp_ms),
        }

    def mark_frame_presented(self, *, run_id: str, frame: FramePacket) -> None:
        with self._state_lock:
            active_stream = self._active_stream
            if active_stream is None or active_stream.run_id != run_id:
                return
            self._record_presented_frame_locked(active_stream, frame)
            self._latest_frame = frame
            self._latest_frame_run_id = run_id

    def close(self) -> None:
        with self._state_lock:
            active_stream = self._active_stream
            self._active_stream = None
            self._latest_frame = None
            self._latest_frame_run_id = ""
            self._latest_tracking_frame = None
            self._latest_tracking_frame_run_id = ""
            self._last_preview_display_fps = None
            self._last_preview_display_fps_run_id = ""
        if active_stream is None:
            return
        active_stream.stop_event.set()
        active_stream.frame_event.set()
        close = getattr(active_stream.camera, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
        reader_thread = active_stream.reader_thread
        if reader_thread is not None and reader_thread.is_alive():
            reader_thread.join(timeout=0.25)

    def _latest_frame_for_run(self, run_id: str) -> FramePacket | None:
        if not run_id:
            return None
        with self._state_lock:
            if self._latest_frame_run_id != run_id:
                return None
            return self._latest_frame

    def _store_latest_frame(self, run_id: str, frame: FramePacket) -> None:
        with self._state_lock:
            self._latest_frame = frame
            self._latest_frame_run_id = run_id

    def _close_stream(self, active_stream: _ActivePreviewStream) -> None:
        with active_stream.close_lock:
            if active_stream.closed:
                return
            active_stream.closed = True
        with self._state_lock:
            if self._active_stream is active_stream:
                self._active_stream = None
            self._last_preview_display_fps = _preview_display_fps(active_stream)
            self._last_preview_display_fps_run_id = active_stream.run_id
        active_stream.stop_event.set()
        active_stream.frame_event.set()
        close = getattr(active_stream.camera, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
        reader_thread = active_stream.reader_thread
        if (
            reader_thread is not None
            and reader_thread.is_alive()
            and reader_thread is not threading.current_thread()
        ):
            reader_thread.join(timeout=0.25)

    def _mark_stream_frame(self, active_stream: _ActivePreviewStream, frame: FramePacket) -> None:
        with self._state_lock:
            if self._active_stream is not active_stream:
                return
            self._record_presented_frame_locked(active_stream, frame)
            self._latest_frame = frame
            self._latest_frame_run_id = active_stream.run_id

    def _record_presented_frame_locked(self, active_stream: _ActivePreviewStream, frame: FramePacket) -> None:
        signature = _frame_signature(frame)
        if signature == active_stream.last_presented_signature:
            return
        now = time.monotonic()
        active_stream.frames_presented += 1
        if active_stream.first_presented_at_monotonic is None:
            active_stream.first_presented_at_monotonic = now
        active_stream.last_presented_at_monotonic = now
        active_stream.last_presented_signature = signature

    def _preview_reader_worker(self, active_stream: _ActivePreviewStream) -> None:
        try:
            while not active_stream.stop_event.is_set():
                frame = self._read_from_camera(active_stream.camera)
                with active_stream.frame_lock:
                    active_stream.latest_frame = frame
                    active_stream.latest_sequence += 1
                    active_stream.frame_event.set()
                self._store_latest_frame(active_stream.run_id, frame)
        except Exception as exc:
            if not active_stream.stop_event.is_set():
                active_stream.reader_error = str(exc)
                active_stream.stop_event.set()
                active_stream.frame_event.set()
        finally:
            self._close_stream(active_stream)

    def _read_from_camera(self, camera: object) -> FramePacket:
        read_frame = getattr(camera, "read_frame")
        if not callable(read_frame):
            raise ValueError("Preview camera does not provide read_frame()")
        return read_frame()

    def _read_with_close(self, camera: object) -> FramePacket:
        try:
            return self._read_from_camera(camera)
        finally:
            close = getattr(camera, "close", None)
            if callable(close):
                close()


def _preview_display_fps(active_stream: _ActivePreviewStream) -> float | None:
    if active_stream.frames_presented < 2:
        return None
    first_presented_at = active_stream.first_presented_at_monotonic
    last_presented_at = active_stream.last_presented_at_monotonic
    if first_presented_at is None or last_presented_at is None:
        return None
    elapsed_s = max(0.0, last_presented_at - first_presented_at)
    if elapsed_s <= 0:
        return None
    return (active_stream.frames_presented - 1) / elapsed_s


def compute_preview_interval_ms(
    *,
    target_fps: float | None = None,
    fallback_ms: int | None = None,
    minimum_interval_ms: int = 10,
) -> int:
    if target_fps is not None and target_fps > 0:
        return max(minimum_interval_ms, int(1000.0 / target_fps))
    fallback = 120 if fallback_ms is None else int(fallback_ms)
    return max(minimum_interval_ms, fallback)


def _frame_signature(frame: FramePacket) -> tuple[object, ...]:
    if frame.frame_id is not None:
        return ("frame_id", int(frame.frame_id))
    return ("timestamp_source", int(frame.timestamp_ms), frame.source)


def _frame_is_hardware_paced(frame: FramePacket) -> bool:
    meta = frame.meta or {}
    return bool(meta.get("camera_target_frame_rate_hz") or meta.get("camera_resulting_fps"))


def _frame_dimensions(frame: FramePacket) -> tuple[int, int]:
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
    raise RuntimeError("Unable to determine frame dimensions from active preview image")
