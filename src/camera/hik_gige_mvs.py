"""Minimal Hikvision GigE / MVS camera adapter with injectable camera factory."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from src.core.contracts import CameraPort
from src.core.models import FramePacket


class HikGigeMvsCamera(CameraPort):
    def __init__(
        self,
        model: str,
        transport: str,
        sdk_name: str = "hik_mvs",
        serial_number: str = "",
        ip: str = "",
        trigger_mode: str = "free_run",
        pixel_format: str = "mono8",
        exposure_us: int = 10_000,
        gain_db: float = 0.0,
        timeout_ms: int = 1_000,
        source_name: str = "hik_gige_mvs",
        backend_name: str = "hik_gige_mvs",
        camera_factory: Callable[[], Any] | None = None,
        auto_open: bool = False,
    ) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")
        if not transport.strip():
            raise ValueError("transport must not be empty")
        if not sdk_name.strip():
            raise ValueError("sdk_name must not be empty")
        if not trigger_mode.strip():
            raise ValueError("trigger_mode must not be empty")
        if timeout_ms < 1:
            raise ValueError("timeout_ms must be >= 1")

        self.model = model
        self.transport = transport
        self.sdk_name = sdk_name
        self.serial_number = serial_number
        self.ip = ip
        self.trigger_mode = trigger_mode
        self.pixel_format = pixel_format
        self.exposure_us = exposure_us
        self.gain_db = gain_db
        self.timeout_ms = timeout_ms
        self.source_name = source_name
        self.backend_name = backend_name
        self.camera_factory = camera_factory
        self._camera: Any | None = None
        self._frame_id = 0

        if auto_open:
            self.open()

    def open(self) -> None:
        if self.is_opened():
            return
        camera_factory = self.camera_factory or self._default_camera_factory()
        try:
            camera = camera_factory()
        except Exception as exc:  # pragma: no cover - raised through tests via injection
            raise RuntimeError("Failed to create Hik MVS camera handle") from exc
        self._open_handle(camera)
        if not self._handle_is_opened(camera):
            self._close_handle(camera)
            raise RuntimeError("Failed to open Hik GigE / MVS camera")
        self._camera = camera

    def is_opened(self) -> bool:
        return self._camera is not None and self._handle_is_opened(self._camera)

    def read_frame(self) -> FramePacket:
        if not self.is_opened():
            self.open()
        assert self._camera is not None
        frame = self._read_from_handle(self._camera)
        self._frame_id += 1
        return FramePacket(
            timestamp_ms=int(time.time() * 1000),
            source=self.source_name,
            image=frame,
            frame_id=self._frame_id,
            meta={
                "transport": self.transport,
                "backend": self.backend_name,
                "model": self.model,
                "serial_number": self.serial_number,
                "ip": self.ip,
                "trigger_mode": self.trigger_mode,
                "sdk": self.sdk_name,
                "pixel_format": self.pixel_format,
            },
        )

    def close(self) -> None:
        if self._camera is None:
            return
        self._close_handle(self._camera)
        self._camera = None

    def _default_camera_factory(self) -> Callable[[], Any]:
        try:
            import MvCameraControl_class as hik_mvs  # type: ignore
        except ImportError as exc:  # pragma: no cover - tests inject fake handles
            raise RuntimeError("Hik MVS SDK is required when camera_factory is not provided") from exc

        create_handle = getattr(hik_mvs, "create_camera_handle", None)
        if callable(create_handle):
            return lambda: create_handle(
                model=self.model,
                transport=self.transport,
                serial_number=self.serial_number,
                ip=self.ip,
                trigger_mode=self.trigger_mode,
                pixel_format=self.pixel_format,
                exposure_us=self.exposure_us,
                gain_db=self.gain_db,
                timeout_ms=self.timeout_ms,
            )
        raise RuntimeError(
            "Hik MVS SDK was imported, but no supported camera factory was found for live GigE access"
        )

    @staticmethod
    def _open_handle(camera: Any) -> None:
        for method_name in ("open", "start", "start_grabbing"):
            method = getattr(camera, method_name, None)
            if callable(method):
                method()
                return

    def _read_from_handle(self, camera: Any) -> Any:
        for method_name in ("read_frame", "get_frame", "read"):
            method = getattr(camera, method_name, None)
            if not callable(method):
                continue
            frame = self._invoke_frame_reader(method)
            if frame is None:
                raise RuntimeError("Failed to read frame from Hik GigE / MVS camera")
            return frame
        raise RuntimeError("Camera handle does not provide a supported frame read method")

    def _invoke_frame_reader(self, reader: Callable[..., Any]) -> Any:
        try:
            result = reader(timeout_ms=self.timeout_ms)
        except TypeError:
            try:
                result = reader(self.timeout_ms)
            except TypeError:
                result = reader()
        if isinstance(result, tuple) and len(result) == 2:
            ok, frame = result
            return frame if ok else None
        return result

    @staticmethod
    def _handle_is_opened(camera: Any) -> bool:
        for method_name in ("is_opened", "is_open", "isOpened"):
            method = getattr(camera, method_name, None)
            if callable(method):
                return bool(method())
        if hasattr(camera, "opened"):
            return bool(camera.opened)
        return True

    @staticmethod
    def _close_handle(camera: Any) -> None:
        for method_name in ("close", "stop_grabbing", "stop", "destroy"):
            method = getattr(camera, method_name, None)
            if callable(method):
                method()
                return
