"""Temperature replay adapter for recorded camera capture sequences."""

from __future__ import annotations

import csv
from pathlib import Path
import time

from src.core.contracts import TempControllerPort, TempReader
from src.core.models import TempReading


class OfflineCaptureTempController(TempReader, TempControllerPort):
    """Replay temperature samples recorded beside offline camera frames."""

    def __init__(self, *, capture_dir: str | Path) -> None:
        self.capture_dir = Path(capture_dir)
        self._temperatures_celsius = _load_temperatures(self.capture_dir)
        self._cursor = 0
        self._last_read_index = 0
        self._target_celsius = float(self._temperatures_celsius[-1])
        self._output_power_percent = 0.0
        self._output_enabled = False

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
        if self._output_power_percent <= 0.0:
            self._output_power_percent = 100.0
        self._output_enabled = True

    def stop_output(self) -> None:
        self._output_enabled = False
        self._output_power_percent = 0.0

    def read(self) -> TempReading:
        if self._output_enabled:
            index = min(self._cursor, len(self._temperatures_celsius) - 1)
            self._last_read_index = index
            if self._cursor < len(self._temperatures_celsius) - 1:
                self._cursor += 1
        else:
            index = self._last_read_index
        return TempReading(
            timestamp_ms=int(time.time() * 1000),
            celsius=float(self._temperatures_celsius[index]),
            source=f"offline_capture:{self.capture_dir.name}",
        )

    def close(self) -> None:
        return None

    def playback_sample_count(self) -> int:
        return len(self._temperatures_celsius)


def _load_temperatures(capture_dir: Path) -> tuple[float, ...]:
    temperature_path = capture_dir / "temperature.csv"
    if not temperature_path.exists():
        raise FileNotFoundError(f"Offline capture temperature.csv not found: {temperature_path}")
    values: list[float] = []
    with temperature_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            celsius = str(row.get("celsius", "") or "").strip()
            if not celsius:
                continue
            values.append(float(celsius))
    if not values:
        raise ValueError(f"Offline capture temperature.csv contains no celsius samples: {temperature_path}")
    return tuple(values)


__all__ = ["OfflineCaptureTempController"]
