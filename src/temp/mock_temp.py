"""Mock temperature reader for dry-run flows."""

from __future__ import annotations

import time

from src.core.contracts import TempReader
from src.core.models import TempReading


class MockTempReader(TempReader):
    def read(self) -> TempReading:
        return TempReading(timestamp_ms=int(time.time() * 1000), celsius=25.0, source="mock_temp")
