"""Core data models shared across frozen modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.enums import SessionState


ScalarPointValue = bool | float | int | str


@dataclass(slots=True)
class FramePacket:
    """A single image frame emitted by the camera layer."""

    timestamp_ms: int
    source: str = "unknown"
    image: Any | None = None
    frame_id: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TempReading:
    """A single temperature sample emitted by the temp layer."""

    timestamp_ms: int
    celsius: float
    source: str = "unknown"


@dataclass(slots=True)
class PlcSnapshot:
    """Point-in-time PLC values."""

    timestamp_ms: int
    values: dict[str, ScalarPointValue] = field(default_factory=dict)
    source: str = "unknown"


@dataclass(slots=True)
class ShapeMetric:
    """Vision output without coupling to workflow or hardware control."""

    timestamp_ms: int
    metric_name: str = "end_displacement"
    metric_raw: float | None = None
    metric_norm: float | None = None
    quality: float = 0.0
    roi: tuple[int, int, int, int] | None = None
    feature_point_px: tuple[int, int] | None = None
    baseline_px: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SyncPoint:
    """Time-aligned multi-source snapshot."""

    timestamp_ms: int
    frame: FramePacket | None = None
    temp: TempReading | None = None
    plc: PlcSnapshot | None = None
    metric: ShapeMetric | None = None


@dataclass(slots=True)
class CurvePoint:
    """A generic scalar point used by curve buffering code."""

    timestamp_ms: int
    value: float


@dataclass(slots=True)
class SessionRecord:
    """Workflow session state stored independent from UI concerns."""

    session_id: str
    state: SessionState = SessionState.CREATED
