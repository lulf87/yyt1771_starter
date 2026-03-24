"""Mock temperature reader for dry-run flows."""

from __future__ import annotations

import time

from src.core.contracts import TempControllerPort, TempReader
from src.core.models import TempReading


class MockTempReader(TempReader):
    def read(self) -> TempReading:
        return TempReading(timestamp_ms=int(time.time() * 1000), celsius=25.0, source="mock_temp")


class MockTempController(TempReader, TempControllerPort):
    """Stateful mock controller used by the Phase 3 live run loop."""

    def __init__(self, start_celsius: float = 25.0, ramp_step_celsius: float = 10.0) -> None:
        self._current_celsius = float(start_celsius)
        self._ramp_step_celsius = float(ramp_step_celsius)
        self._target_celsius: float | None = None
        self._output_enabled = False

    def set_target_temperature(self, celsius: float) -> None:
        if celsius <= 0:
            raise ValueError("target temperature must be greater than zero")
        self._target_celsius = float(celsius)

    def start_output(self) -> None:
        if self._target_celsius is None:
            raise RuntimeError("target temperature must be set before starting output")
        self._output_enabled = True

    def stop_output(self) -> None:
        self._output_enabled = False

    def read(self) -> TempReading:
        if self._output_enabled and self._target_celsius is not None and self._current_celsius < self._target_celsius:
            self._current_celsius = min(self._target_celsius, self._current_celsius + self._ramp_step_celsius)
        return TempReading(
            timestamp_ms=int(time.time() * 1000),
            celsius=self._current_celsius,
            source="mock_temp_controller",
        )
