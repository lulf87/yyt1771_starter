"""Shared preview service used by application shells."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Iterator
import threading
import time

from src.application.device_factory import open_camera
from src.application.frame_pixel_contract import validate_frame_pixel_contract
from src.application.real_offline_alignment_guard import assert_real_offline_alignment_ready
from src.application.runtime_config import RuntimeConfig
from src.core.models import FramePacket


@dataclass(slots=True)
class _ActivePreviewStream:
    run_id: str
    camera: object
    runtime_config: RuntimeConfig
    profile_name: str
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
        self._stream_transition_lock = threading.Lock()
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
        _assert_preview_alignment_ready(runtime_config, context="preview_fetch_frame")
        cached_frame = self._latest_frame_for_run(run_id) if prefer_cached else None
        if cached_frame is not None:
            return validate_frame_pixel_contract(
                runtime_config,
                profile_name="setup_preview",
                frame=cached_frame,
                context="preview_cached_frame",
            )
        active_frame = self.get_active_frame()
        if active_frame is not None:
            active_frame = validate_frame_pixel_contract(
                runtime_config,
                profile_name="setup_preview",
                frame=active_frame,
                context="preview_active_frame",
            )
            if run_id:
                self._store_latest_frame(run_id, active_frame)
            return active_frame
        frame = self._read_fresh_frame_with_retry(
            runtime_config,
            profile_name="setup_preview",
            warmup_frame_count=_fresh_capture_warmup_frame_count(runtime_config),
        )
        if run_id:
            self._store_latest_frame(run_id, frame)
        return frame

    def start_stream(
        self,
        runtime_config: RuntimeConfig,
        *,
        run_id: str,
    ) -> tuple[object, FramePacket]:
        _assert_preview_alignment_ready(runtime_config, context="preview_stream_start")
        with self._stream_transition_lock:
            active_stream = self._handoff_active_stream(run_id=run_id)
            if active_stream is not None:
                self._retire_stream(active_stream, join_timeout_s=1.0)
                time.sleep(0.08)

            last_error: Exception | None = None
            for attempt_index in range(3):
                camera = None
                try:
                    camera = self.open_camera(runtime_config, profile_name="setup_preview")
                    first_frame = self._read_from_camera(camera)
                    first_frame = validate_frame_pixel_contract(
                        runtime_config,
                        profile_name="setup_preview",
                        frame=first_frame,
                        context="preview_stream_start",
                    )
                    break
                except Exception as exc:
                    last_error = exc
                    close = getattr(camera, "close", None) if camera is not None else None
                    if callable(close):
                        try:
                            close()
                        except Exception:
                            pass
                    if attempt_index >= 2 or not _is_retryable_preview_open_error(exc):
                        raise
                    time.sleep(0.12 * (attempt_index + 1))
            else:  # pragma: no cover
                raise RuntimeError(f"Preview stream start failed: {last_error}")

            active_stream = _ActivePreviewStream(
                run_id=run_id,
                camera=camera,
                runtime_config=runtime_config,
                profile_name="setup_preview",
                stop_event=threading.Event(),
                started_at_monotonic=time.monotonic(),
                latest_frame=first_frame,
                latest_sequence=1,
            )
            lingering_stream = self._handoff_active_stream(run_id=run_id)
            if lingering_stream is not None:
                self._retire_stream(lingering_stream, join_timeout_s=0.5)
            with self._state_lock:
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

    def _handoff_active_stream(self, *, run_id: str) -> _ActivePreviewStream | None:
        with self._state_lock:
            active_stream = self._active_stream
            if active_stream is None:
                return None
            if active_stream.run_id == run_id and active_stream.stop_event.is_set():
                return None
            return active_stream

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
        self._retire_stream(active_stream, join_timeout_s=0.5)
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

    def get_active_frame(self) -> FramePacket | None:
        with self._state_lock:
            active_stream = self._active_stream
            if active_stream is None:
                return None
            return active_stream.latest_frame

    def retire_active_stream(self, *, timeout_ms: int = 1_000) -> bool:
        with self._state_lock:
            active_stream = self._active_stream
        if active_stream is None:
            return False
        active_stream.stop_event.set()
        active_stream.frame_event.set()
        self._retire_stream(active_stream, join_timeout_s=max(0.05, float(timeout_ms) / 1000.0))
        return True

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
        self._retire_stream(active_stream, join_timeout_s=0.5)

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
        self._retire_stream(active_stream, join_timeout_s=0.25)

    def _retire_stream(self, active_stream: _ActivePreviewStream, *, join_timeout_s: float) -> None:
        with active_stream.close_lock:
            if active_stream.closed:
                return
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
            active_stream.closed = True
        reader_thread = active_stream.reader_thread
        if (
            reader_thread is not None
            and reader_thread.is_alive()
            and reader_thread is not threading.current_thread()
        ):
            reader_thread.join(timeout=max(0.05, float(join_timeout_s)))

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
                frame = validate_frame_pixel_contract(
                    active_stream.runtime_config,
                    profile_name=active_stream.profile_name,
                    frame=frame,
                    context="preview_stream_frame",
                )
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

    def _read_with_close(self, camera: object, *, warmup_frame_count: int = 0) -> FramePacket:
        try:
            frame = self._read_from_camera(camera)
            for _ in range(max(0, int(warmup_frame_count))):
                frame = self._read_from_camera(camera)
            return frame
        finally:
            close = getattr(camera, "close", None)
            if callable(close):
                close()

    def _read_fresh_frame_with_retry(
        self,
        runtime_config: RuntimeConfig,
        *,
        profile_name: str,
        warmup_frame_count: int = 0,
    ) -> FramePacket:
        last_error: Exception | None = None
        for attempt_index in range(3):
            camera = None
            try:
                camera = self.open_camera(runtime_config, profile_name=profile_name)
                frame = self._read_with_close(camera, warmup_frame_count=warmup_frame_count)
                return validate_frame_pixel_contract(
                    runtime_config,
                    profile_name=profile_name,
                    frame=frame,
                    context="preview_fresh_frame",
                )
            except Exception as exc:
                last_error = exc
                close = getattr(camera, "close", None) if camera is not None else None
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass
                if attempt_index >= 2 or not _is_retryable_preview_open_error(exc):
                    raise
                time.sleep(0.12 * (attempt_index + 1))
        raise RuntimeError(f"Preview fresh capture failed: {last_error}")


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


def _is_retryable_preview_open_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in ("0x80000203", "0x80000004", "resource", "access denied", "already active", "create handle")
    )


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


def _fresh_capture_warmup_frame_count(runtime_config: RuntimeConfig) -> int:
    adapters = getattr(runtime_config, "adapters", {}) or {}
    camera_backend = str(adapters.get("camera", "") or "").strip()
    if camera_backend == "hik_gige_mvs":
        return 2
    return 0


def _assert_preview_alignment_ready(runtime_config: RuntimeConfig, *, context: str) -> None:
    if not str(getattr(runtime_config, "profile", "") or ""):
        return
    assert_real_offline_alignment_ready(runtime_config, context=context)


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
