"""Minimal Hikvision RTSP adapter using an OpenCV-like capture interface."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from src.core.contracts import CameraPort
from src.core.models import FramePacket


def build_hik_rtsp_url(
    host: str,
    username: str,
    password: str,
    channel: int = 1,
    stream: int = 1,
    port: int = 554,
) -> str:
    if not host.strip():
        raise ValueError("host must not be empty")
    if not username:
        raise ValueError("username must not be empty")
    if not password:
        raise ValueError("password must not be empty")
    if channel < 1:
        raise ValueError("channel must be >= 1")
    if stream < 1:
        raise ValueError("stream must be >= 1")
    if port < 1:
        raise ValueError("port must be >= 1")
    return f"rtsp://{username}:{password}@{host}:{port}/Streaming/channels/{channel}{stream}"


class HikRtspCamera(CameraPort):
    def __init__(
        self,
        rtsp_url: str,
        capture_factory: Callable[[str], Any] | None = None,
        auto_open: bool = False,
        source_name: str = "hik_rtsp_opencv",
    ) -> None:
        if not rtsp_url.strip():
            raise ValueError("rtsp_url must not be empty")
        self.rtsp_url = rtsp_url
        self.capture_factory = capture_factory
        self.source_name = source_name
        self._capture: Any | None = None
        self._frame_id = 0
        if auto_open:
            self.open()

    def open(self) -> None:
        if self._capture is not None and self.is_opened():
            return
        capture_factory = self.capture_factory or self._default_capture_factory()
        capture = capture_factory(self.rtsp_url)
        if not self._capture_is_opened(capture):
            self._release_capture(capture)
            raise RuntimeError(f"Failed to open RTSP stream: {self.rtsp_url}")
        self._capture = capture

    def is_opened(self) -> bool:
        return self._capture is not None and self._capture_is_opened(self._capture)

    def read_frame(self) -> FramePacket:
        if not self.is_opened():
            self.open()
        assert self._capture is not None
        ok, frame = self._capture.read()
        if not ok:
            raise RuntimeError("Failed to read frame from RTSP stream")
        self._frame_id += 1
        return FramePacket(
            timestamp_ms=int(time.time() * 1000),
            source=self.source_name,
            image=frame,
            frame_id=self._frame_id,
            meta={
                "transport": "rtsp",
                "backend": "opencv",
                "rtsp_url": self.rtsp_url,
            },
        )

    def close(self) -> None:
        if self._capture is None:
            return
        self._release_capture(self._capture)
        self._capture = None

    def _default_capture_factory(self) -> Callable[[str], Any]:
        try:
            import cv2  # type: ignore
        except ImportError as exc:  # pragma: no cover - test path uses injection
            raise RuntimeError("cv2 is required when capture_factory is not provided") from exc
        return lambda rtsp_url: cv2.VideoCapture(rtsp_url)

    @staticmethod
    def _capture_is_opened(capture: Any) -> bool:
        is_opened = getattr(capture, "isOpened", None)
        if callable(is_opened):
            return bool(is_opened())
        return True

    @staticmethod
    def _release_capture(capture: Any) -> None:
        release = getattr(capture, "release", None)
        if callable(release):
            release()
