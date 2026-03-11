"""Shared test fixtures for scaffold verification."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.models import CurvePoint, FramePacket, PlcSnapshot, TempReading


def make_frame(timestamp_ms: int = 1000, image: object | None = None) -> FramePacket:
    return FramePacket(
        timestamp_ms=timestamp_ms,
        source="fixture",
        image=image,
        frame_id=1,
        meta={"fixture": True},
    )


def make_temp(timestamp_ms: int = 1001, celsius: float = 25.0) -> TempReading:
    return TempReading(timestamp_ms=timestamp_ms, celsius=celsius, source="fixture")


def make_plc(timestamp_ms: int = 1002) -> PlcSnapshot:
    return PlcSnapshot(timestamp_ms=timestamp_ms, values={"ready": True}, source="fixture")


def make_curve_point(timestamp_ms: int, value: float) -> CurvePoint:
    return CurvePoint(timestamp_ms=timestamp_ms, value=value)
