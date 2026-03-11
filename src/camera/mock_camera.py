"""Mock camera adapter used by tests and offline demos."""

from __future__ import annotations

import time
from typing import Any

from src.core.contracts import CameraPort
from src.core.models import FramePacket


def _build_mock_image() -> list[list[int]]:
    """Return a tiny black image with a white block for offline contract tests."""

    size = 8
    image = [[0 for _ in range(size)] for _ in range(size)]
    for row in range(2, 6):
        for col in range(4, 7):
            image[row][col] = 255
    return image


class MockCamera(CameraPort):
    def read_frame(self) -> FramePacket:
        timestamp_ms = int(time.time() * 1000)
        image: Any = _build_mock_image()
        return FramePacket(
            timestamp_ms=timestamp_ms,
            source="mock_camera",
            image=image,
            frame_id=1,
            meta={"format": "mock_grayscale_grid"},
        )
