"""Protocols for boundary-facing components."""

from __future__ import annotations

from typing import Protocol

from src.core.models import FramePacket, PlcSnapshot, ShapeMetric, TempReading


class CameraPort(Protocol):
    def read_frame(self) -> FramePacket:
        """Return one frame packet from a camera source."""


class TempReader(Protocol):
    def read(self) -> TempReading:
        """Return one temperature sample."""


class PlcPort(Protocol):
    def read(self) -> PlcSnapshot:
        """Return a PLC snapshot."""


class VisionMetricExtractor(Protocol):
    def extract(self, frame: FramePacket) -> ShapeMetric:
        """Convert a frame into a shape metric."""
