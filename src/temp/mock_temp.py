"""Mock temperature reader for dry-run flows."""

from __future__ import annotations

import time
from typing import Protocol

from src.core.contracts import TempControllerPort, TempReader
from src.core.models import TempReading


class _AfasCurvePlaybackLike(Protocol):
    sheet_name: str
    temperatures_celsius: tuple[float, ...]

    @property
    def sample_count(self) -> int: ...

    @property
    def end_temperature_celsius(self) -> float: ...


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
        self._output_power_percent = 0.0

    def set_target_temperature(self, celsius: float) -> None:
        self._target_celsius = float(celsius)

    def read_target_temperature(self) -> float:
        return float(self._target_celsius if self._target_celsius is not None else self._current_celsius)

    def set_output_power_percent(self, percent: float) -> None:
        if percent < 0.0 or percent > 100.0:
            raise ValueError("output power percent must be within 0..100")
        self._output_power_percent = float(percent)

    def read_output_power_percent(self) -> float:
        return float(self._output_power_percent)

    def start_output(self) -> None:
        if self._target_celsius is None:
            raise RuntimeError("target temperature must be set before starting output")
        if self._output_power_percent <= 0.0:
            self._output_power_percent = 100.0
        self._output_enabled = True

    def stop_output(self) -> None:
        self._output_enabled = False
        self._output_power_percent = 0.0

    def read(self) -> TempReading:
        if self._output_enabled and self._target_celsius is not None:
            if self._current_celsius < self._target_celsius:
                self._current_celsius = min(self._target_celsius, self._current_celsius + self._ramp_step_celsius)
            elif self._current_celsius > self._target_celsius:
                self._current_celsius = max(self._target_celsius, self._current_celsius - self._ramp_step_celsius)
        return TempReading(
            timestamp_ms=int(time.time() * 1000),
            celsius=self._current_celsius,
            source="mock_temp_controller",
        )


class WorkbookPlaybackTempController(TempReader, TempControllerPort):
    """Temp controller that replays workbook-backed AFAS temperatures."""

    def __init__(self, playback: _AfasCurvePlaybackLike) -> None:
        self._playback = playback
        self._cursor = 0
        self._last_read_index = 0
        self._target_celsius = float(playback.end_temperature_celsius)
        self._output_enabled = False
        self._output_power_percent = 0.0

    def set_target_temperature(self, celsius: float) -> None:
        self._target_celsius = float(celsius)

    def read_target_temperature(self) -> float:
        return float(self._target_celsius)

    def set_output_power_percent(self, percent: float) -> None:
        if percent < 0.0 or percent > 100.0:
            raise ValueError("output power percent must be within 0..100")
        self._output_power_percent = float(percent)

    def read_output_power_percent(self) -> float:
        return float(self._output_power_percent)

    def start_output(self) -> None:
        if self._target_celsius is None:
            raise RuntimeError("target temperature must be set before starting output")
        if self._output_power_percent <= 0.0:
            self._output_power_percent = 100.0
        self._output_enabled = True

    def stop_output(self) -> None:
        self._output_enabled = False
        self._output_power_percent = 0.0

    def read(self) -> TempReading:
        if self._output_enabled:
            index = min(self._cursor, self._playback.sample_count - 1)
            self._last_read_index = index
            if self._cursor < self._playback.sample_count - 1:
                self._cursor += 1
        else:
            index = self._last_read_index
        return TempReading(
            timestamp_ms=int(time.time() * 1000),
            celsius=float(self._playback.temperatures_celsius[index]),
            source=f"mock_afas_curve:{self._playback.sheet_name}",
        )
