"""Application-layer access to temperature-controller serial-port discovery."""

from src.temp.serial_discovery import SerialPortInfo, list_serial_ports

__all__ = ["SerialPortInfo", "list_serial_ports"]
