"""Temperature adapters."""

from src.temp.modbus_temp import ModbusTempReader
from src.temp.mock_temp import MockTempReader

__all__ = ["MockTempReader", "ModbusTempReader"]
