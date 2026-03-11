import pytest

from src.plc.modbus_tcp import ModbusTcpPlc


class FakeResponse:
    def __init__(
        self,
        *,
        registers: list[int] | None = None,
        bits: list[bool] | None = None,
        error: bool = False,
    ) -> None:
        self.registers = registers
        self.bits = bits
        self._error = error

    def isError(self) -> bool:
        return self._error


class FakeModbusClient:
    def __init__(
        self,
        *,
        connect_result: bool = True,
        holding_values: dict[int, FakeResponse | None] | None = None,
        coil_values: dict[int, FakeResponse | None] | None = None,
    ) -> None:
        self.connect_result = connect_result
        self.holding_values = dict(holding_values or {})
        self.coil_values = dict(coil_values or {})
        self.close_count = 0
        self.connected = False

    def connect(self) -> bool:
        self.connected = self.connect_result
        return self.connect_result

    def read_holding_registers(
        self,
        address: int,
        *,
        count: int = 1,
        device_id: int = 1,
        **_: object,
    ) -> FakeResponse | None:
        return self.holding_values.get(address)

    def read_coils(
        self,
        address: int,
        *,
        count: int = 1,
        device_id: int = 1,
        **_: object,
    ) -> FakeResponse | None:
        return self.coil_values.get(address)

    def close(self) -> None:
        self.close_count += 1
        self.connected = False


def test_read_returns_holding_snapshot_values() -> None:
    fake_client = FakeModbusClient(
        holding_values={
            10: FakeResponse(registers=[123]),
            11: FakeResponse(registers=[456]),
        }
    )
    plc = ModbusTcpPlc(
        host="127.0.0.1",
        holding_register_map={"temp_raw": 10, "speed_raw": 11},
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    snapshot = plc.read()

    assert snapshot.values == {"temp_raw": 123, "speed_raw": 456}
    assert snapshot.source == "modbus_plc"


def test_read_returns_coil_snapshot_values() -> None:
    fake_client = FakeModbusClient(
        coil_values={
            1: FakeResponse(bits=[True]),
            2: FakeResponse(bits=[False]),
        }
    )
    plc = ModbusTcpPlc(
        host="127.0.0.1",
        coil_map={"ready": 1, "alarm": 2},
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    snapshot = plc.read()

    assert snapshot.values == {"ready": True, "alarm": False}


def test_read_merges_holding_and_coil_values() -> None:
    fake_client = FakeModbusClient(
        holding_values={10: FakeResponse(registers=[7])},
        coil_values={1: FakeResponse(bits=[True])},
    )
    plc = ModbusTcpPlc(
        host="127.0.0.1",
        holding_register_map={"heartbeat": 10},
        coil_map={"ready": 1},
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    snapshot = plc.read()

    assert snapshot.values == {"heartbeat": 7, "ready": True}


def test_open_raises_when_client_cannot_connect() -> None:
    plc = ModbusTcpPlc(
        host="127.0.0.1",
        holding_register_map={"heartbeat": 10},
        client_factory=lambda: FakeModbusClient(connect_result=False),
    )

    with pytest.raises(RuntimeError, match="open Modbus connection"):
        plc.open()


def test_read_raises_when_response_is_none() -> None:
    plc = ModbusTcpPlc(
        host="127.0.0.1",
        holding_register_map={"heartbeat": 10},
        client_factory=lambda: FakeModbusClient(holding_values={10: None}),
        auto_open=True,
    )

    with pytest.raises(RuntimeError, match="read holding register"):
        plc.read()


def test_read_raises_on_error_response() -> None:
    plc = ModbusTcpPlc(
        host="127.0.0.1",
        coil_map={"ready": 1},
        client_factory=lambda: FakeModbusClient(coil_values={1: FakeResponse(bits=None, error=True)}),
        auto_open=True,
    )

    with pytest.raises(RuntimeError, match="Modbus exception response"):
        plc.read()


def test_close_is_idempotent() -> None:
    fake_client = FakeModbusClient(holding_values={10: FakeResponse(registers=[1])})
    plc = ModbusTcpPlc(
        host="127.0.0.1",
        holding_register_map={"heartbeat": 10},
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    plc.close()
    plc.close()

    assert fake_client.close_count == 1


@pytest.mark.parametrize(
    ("host", "port", "holding_map", "coil_map"),
    [
        ("", 502, {"heartbeat": 10}, None),
        ("127.0.0.1", 0, {"heartbeat": 10}, None),
        ("127.0.0.1", 502, None, None),
    ],
)
def test_invalid_init_values_raise_value_error(
    host: str,
    port: int,
    holding_map: dict[str, int] | None,
    coil_map: dict[str, int] | None,
) -> None:
    with pytest.raises(ValueError):
        ModbusTcpPlc(
            host=host,
            port=port,
            holding_register_map=holding_map,
            coil_map=coil_map,
            client_factory=lambda: FakeModbusClient(),
        )
