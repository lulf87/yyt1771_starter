"""Modbus TCP PLC adapter placeholder."""

from src.core.contracts import PlcPort
from src.core.errors import AdapterNotConfiguredError
from src.core.models import PlcSnapshot


class ModbusTcpPlc(PlcPort):
    def __init__(self, host: str) -> None:
        self.host = host

    def read(self) -> PlcSnapshot:
        raise AdapterNotConfiguredError("Real PLC access is deferred after scaffold freeze.")
