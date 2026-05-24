"""Mock camera adapter used by tests and offline demos."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from src.core.contracts import CameraPort
from src.core.config_models import DeviceRoiConfig
from src.core.models import FramePacket


_DEFAULT_WIDTH = 96
_DEFAULT_HEIGHT = 64


def _build_mock_image(*, width: int = _DEFAULT_WIDTH, height: int = _DEFAULT_HEIGHT) -> np.ndarray:
    """Return a brighter preview with a dark elongated target and internal texture."""

    width = max(1, int(width))
    height = max(1, int(height))
    image = np.full((height, width), 240, dtype=np.uint8)

    target_left, target_right = _scaled_span(width, 12 / 96, 84 / 96, min_size=4)
    target_top, target_bottom = _scaled_span(height, 24 / 64, 40 / 64, min_size=4)
    image[target_top:target_bottom, target_left:target_right] = 36

    texture_top, texture_bottom = _scaled_span(height, 27 / 64, 37 / 64, min_size=1)
    texture_left, texture_right = _scaled_span(width, 20 / 96, 78 / 96, min_size=1)
    dot_height = max(1, round(height / 96))
    dot_width = max(1, round(width / 96))
    row_step = max(dot_height + 1, round(height * 3 / 64))
    col_step = max(dot_width + 2, round(width * 10 / 96))
    for row in range(texture_top, texture_bottom, row_step):
        for col in range(texture_left, texture_right, col_step):
            image[row : min(target_bottom, row + dot_height), col : min(target_right, col + dot_width * 2)] = 220

    guide_left, guide_right = _scaled_span(width, 18 / 96, 78 / 96, min_size=4)
    guide_height = max(1, round(height * 2 / 64))
    upper_top = max(0, target_top - guide_height)
    image[upper_top:target_top, guide_left:guide_right] = 92
    lower_bottom = min(height, target_bottom + guide_height)
    image[target_bottom:lower_bottom, guide_left:guide_right] = 92

    return image


def _scaled_span(total: int, start_ratio: float, end_ratio: float, *, min_size: int = 1) -> tuple[int, int]:
    start = max(0, min(int(total), int(round(total * start_ratio))))
    end = max(start + int(min_size), min(int(total), int(round(total * end_ratio))))
    if end > total:
        end = int(total)
        start = max(0, end - int(min_size))
    return start, end


def _mock_output_dimensions(device_roi: DeviceRoiConfig) -> tuple[int, int]:
    width = int(device_roi.width) if int(device_roi.width) > 0 else _DEFAULT_WIDTH
    height = int(device_roi.height) if int(device_roi.height) > 0 else _DEFAULT_HEIGHT
    return width, height


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
        width, height = _mock_output_dimensions(self.device_roi)
        image: Any = _build_mock_image(width=width, height=height)
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
                "width": width,
                "height": height,
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
