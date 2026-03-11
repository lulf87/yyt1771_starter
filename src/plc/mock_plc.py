"""Mock PLC adapter for scaffold-safe flows."""

from __future__ import annotations

import time

from src.core.contracts import PlcPort
from src.core.models import PlcSnapshot


class MockPlc(PlcPort):
    def read(self) -> PlcSnapshot:
        values = {"ready": True, "heartbeat": 1}
        return PlcSnapshot(timestamp_ms=int(time.time() * 1000), values=values, source="mock_plc")
