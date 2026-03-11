"""Timestamp alignment for multi-source packets."""

from __future__ import annotations

from src.core.models import FramePacket, PlcSnapshot, ShapeMetric, SyncPoint, TempReading


class SyncHub:
    def __init__(self) -> None:
        self._frame: FramePacket | None = None
        self._temp: TempReading | None = None
        self._plc: PlcSnapshot | None = None
        self._metric: ShapeMetric | None = None

    def update_frame(self, frame: FramePacket) -> None:
        self._frame = frame

    def update_temp(self, reading: TempReading) -> None:
        self._temp = reading

    def update_plc(self, snapshot: PlcSnapshot) -> None:
        self._plc = snapshot

    def update_metric(self, metric: ShapeMetric) -> None:
        self._metric = metric

    def snapshot(self) -> SyncPoint:
        timestamps = [
            packet.timestamp_ms
            for packet in (self._frame, self._temp, self._plc, self._metric)
            if packet is not None
        ]
        timestamp_ms = max(timestamps) if timestamps else 0
        return SyncPoint(
            timestamp_ms=timestamp_ms,
            frame=self._frame,
            temp=self._temp,
            plc=self._plc,
            metric=self._metric,
        )
