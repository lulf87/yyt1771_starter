"""Minimal Modbus temperature adapter with injectable client factory."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from src.core.contracts import TempReader
from src.core.models import TempReading


class ModbusTempReader(TempReader):
    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 1,
        register_address: int = 0,
        register_count: int = 1,
        function: str = "holding",
        scale: float = 1.0,
        offset: float = 0.0,
        source_name: str = "modbus_temp",
        client_factory: Callable[[], Any] | None = None,
        auto_open: bool = False,
    ) -> None:
        if not host.strip():
            raise ValueError("host must not be empty")
        if port < 1:
            raise ValueError("port must be >= 1")
        if register_count < 1:
            raise ValueError("register_count must be >= 1")
        if function not in {"holding", "input"}:
            raise ValueError("function must be 'holding' or 'input'")

        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.register_address = register_address
        self.register_count = register_count
        self.function = function
        self.scale = scale
        self.offset = offset
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

    def read(self) -> TempReading:
        if not self.is_opened():
            self.open()
        assert self._client is not None
        reader = self._select_reader(self._client)
        response = reader(self.register_address, self.register_count, self.unit_id)
        if response is None:
            raise RuntimeError("Failed to read temperature register")
        registers = getattr(response, "registers", None)
        if not registers:
            raise RuntimeError("Received empty register response")
        raw_value = registers[0]
        celsius = float(raw_value) * self.scale + self.offset
        return TempReading(
            timestamp_ms=int(time.time() * 1000),
            celsius=celsius,
            source=self.source_name,
        )

    def close(self) -> None:
        if self._client is None:
            return
        self._close_client(self._client)
        self._client = None

    def _select_reader(self, client: Any) -> Callable[[int, int, int], Any]:
        if self.function == "holding":
            reader = getattr(client, "read_holding_registers", None)
        else:
            reader = getattr(client, "read_input_registers", None)
        if not callable(reader):
            raise RuntimeError(f"Client does not support {self.function} register reads")
        return reader

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
