"""Curve point buffering for later result calculations."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator

from src.core.models import CurvePoint


class CurveBuffer:
    def __init__(self, maxlen: int | None = None) -> None:
        self._points: deque[CurvePoint] = deque(maxlen=maxlen)

    def append(self, point: CurvePoint) -> None:
        self._points.append(point)

    def __iter__(self) -> Iterator[CurvePoint]:
        return iter(self._points)

    def __len__(self) -> int:
        return len(self._points)

    def values(self) -> list[float]:
        return [point.value for point in self._points]
