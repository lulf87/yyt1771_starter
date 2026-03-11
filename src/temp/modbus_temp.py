"""Modbus temperature adapter placeholder."""

from src.core.contracts import TempReader
from src.core.errors import AdapterNotConfiguredError
from src.core.models import TempReading


class ModbusTempReader(TempReader):
    def __init__(self, port: str) -> None:
        self.port = port

    def read(self) -> TempReading:
        raise AdapterNotConfiguredError("Real Modbus temperature access is deferred after scaffold freeze.")
