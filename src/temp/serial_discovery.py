"""Local serial-port discovery helpers for temperature-controller setup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SerialPortInfo:
    device: str
    name: str = ""
    description: str = ""
    hwid: str = ""


def list_serial_ports() -> list[SerialPortInfo]:
    try:
        from serial.tools import list_ports  # type: ignore
    except ImportError as exc:  # pragma: no cover - pyserial is a project dependency
        raise RuntimeError("pyserial is required for serial-port discovery") from exc

    ports: list[SerialPortInfo] = []
    for port in list_ports.comports():
        ports.append(_port_info_from_pyserial(port))
    return sorted(ports, key=lambda item: _natural_port_key(item.device))


def _port_info_from_pyserial(port: Any) -> SerialPortInfo:
    device = str(getattr(port, "device", "") or "").strip()
    return SerialPortInfo(
        device=device,
        name=str(getattr(port, "name", "") or device),
        description=str(getattr(port, "description", "") or ""),
        hwid=str(getattr(port, "hwid", "") or ""),
    )


def _natural_port_key(value: str) -> tuple[str, int, str]:
    text = str(value)
    prefix = text.rstrip("0123456789")
    suffix = text[len(prefix) :]
    number = int(suffix) if suffix.isdigit() else -1
    return (prefix.lower(), number, text.lower())


__all__ = ["SerialPortInfo", "list_serial_ports"]
