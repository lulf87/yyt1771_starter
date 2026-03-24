"""Mock camera adapter used by tests and offline demos."""

from __future__ import annotations

import time
from typing import Any

from src.core.contracts import CameraPort
from src.core.config_models import DeviceRoiConfig
from src.core.models import FramePacket


def _build_mock_image() -> list[list[int]]:
    """Return a brighter preview with a dark elongated target and internal texture."""

    width = 96
    height = 64
    image = [[240 for _ in range(width)] for _ in range(height)]

    for row in range(24, 40):
        for col in range(12, 84):
            image[row][col] = 36

    for row in range(27, 37, 3):
        for col in range(20, 78, 10):
            image[row][col] = 220
            image[row][col + 1] = 220

    for row in range(22, 24):
        for col in range(18, 78):
            image[row][col] = 92
    for row in range(40, 42):
        for col in range(18, 78):
            image[row][col] = 92

    return image


class MockCamera(CameraPort):
    def __init__(
        self,
        *,
        profile_name: str = "setup_preview",
        exposure_us: int = 10_000,
        device_roi: DeviceRoiConfig | None = None,
        decimation: int | None = None,
        binning: int | None = None,
    ) -> None:
        self.profile_name = profile_name
        self.exposure_us = exposure_us
        self.device_roi = device_roi or DeviceRoiConfig()
        self.decimation = decimation
        self.binning = binning
        self._frame_id = 0

    def read_frame(self) -> FramePacket:
        timestamp_ms = int(time.time() * 1000)
        image: Any = _build_mock_image()
        self._frame_id += 1
        return FramePacket(
            timestamp_ms=timestamp_ms,
            source="mock_camera",
            image=image,
            frame_id=self._frame_id,
            meta={
                "format": "mock_preview_band",
                "profile_name": self.profile_name,
                "exposure_us": self.exposure_us,
                "device_roi": {
                    "x": self.device_roi.x,
                    "y": self.device_roi.y,
                    "width": self.device_roi.width,
                    "height": self.device_roi.height,
                },
                "decimation": self.decimation,
                "binning": self.binning,
            },
        )
