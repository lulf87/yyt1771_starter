"""Minimal PLC Modbus TCP snapshot adapter with injectable client factory."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from src.core.contracts import PlcPort
from src.core.models import PlcSnapshot


class ModbusTcpPlc(PlcPort):
    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 1,
        holding_register_map: dict[str, int] | None = None,
        coil_map: dict[str, int] | None = None,
        source_name: str = "modbus_plc",
        client_factory: Callable[[], Any] | None = None,
        auto_open: bool = False,
    ) -> None:
        if not host.strip():
            raise ValueError("host must not be empty")
        if port < 1:
            raise ValueError("port must be >= 1")
        if not holding_register_map and not coil_map:
            raise ValueError("holding_register_map and coil_map cannot both be empty")

        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.holding_register_map = dict(holding_register_map or {})
        self.coil_map = dict(coil_map or {})
        self.source_name = source_name
        self.client_factory = client_factory
        self._client: Any | None = None

        if auto_open:
            self.open()

    def open(self) -> None:
        if self.is_opened():
            return
        client_factory = self.client_factory or self._default_client_factory()
        client = client_factory()
        connect = getattr(client, "connect", None)
        connected = True
        if callable(connect):
            connected = bool(connect())
        if not connected:
            self._close_client(client)
            raise RuntimeError(f"Failed to open Modbus connection to {self.host}:{self.port}")
        self._client = client

    def is_opened(self) -> bool:
        if self._client is None:
            return False
        if hasattr(self._client, "connected"):
            return bool(self._client.connected)
        is_socket_open = getattr(self._client, "is_socket_open", None)
        if callable(is_socket_open):
            return bool(is_socket_open())
        return True

    def read(self) -> PlcSnapshot:
        if not self.is_opened():
            self.open()
        assert self._client is not None

        values: dict[str, bool | float | int | str] = {}
        for name, address in self.holding_register_map.items():
            values[name] = self._read_holding_register(address)
        for name, address in self.coil_map.items():
            values[name] = self._read_coil(address)

        return PlcSnapshot(
            timestamp_ms=int(time.time() * 1000),
            values=values,
            source=self.source_name,
        )

    def close(self) -> None:
        if self._client is None:
            return
        self._close_client(self._client)
        self._client = None

    def _read_holding_register(self, address: int) -> int:
        assert self._client is not None
        reader = getattr(self._client, "read_holding_registers", None)
        if not callable(reader):
            raise RuntimeError("Client does not support holding register reads")
        response = self._read_modbus(reader, address)
        registers = getattr(response, "registers", None)
        if not registers:
            raise RuntimeError("Received invalid holding register response")
        return int(registers[0])

    def _read_coil(self, address: int) -> bool:
        assert self._client is not None
        reader = getattr(self._client, "read_coils", None)
        if not callable(reader):
            raise RuntimeError("Client does not support coil reads")
        response = self._read_modbus(reader, address)
        bits = getattr(response, "bits", None)
        if not bits:
            raise RuntimeError("Received invalid coil response")
        return bool(bits[0])

    def _read_modbus(self, reader: Callable[..., Any], address: int) -> Any:
        try:
            response = reader(address, count=1, device_id=self.unit_id)
        except TypeError:
            try:
                response = reader(address, count=1, slave=self.unit_id)
            except TypeError:
                response = reader(address, 1, self.unit_id)
        if response is None:
            raise RuntimeError("Failed to read holding register or coil")
        is_error = getattr(response, "isError", None)
        if callable(is_error) and is_error():
            raise RuntimeError("Modbus exception response while reading PLC snapshot")
        return response

    def _default_client_factory(self) -> Callable[[], Any]:
        try:
            from pymodbus.client import ModbusTcpClient  # type: ignore
        except ImportError as exc:  # pragma: no cover - tests inject fake client
            raise RuntimeError("pymodbus is required when client_factory is not provided") from exc
        return lambda: ModbusTcpClient(host=self.host, port=self.port)

    @staticmethod
    def _close_client(client: Any) -> None:
        close = getattr(client, "close", None)
        if callable(close):
            close()
