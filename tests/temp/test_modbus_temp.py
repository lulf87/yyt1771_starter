import pytest

from src.temp.modbus_temp import ModbusTempReader


class FakeResponse:
    def __init__(self, registers: list[int] | None) -> None:
        self.registers = registers


class FakeModbusClient:
    def __init__(
        self,
        *,
        connect_result: bool = True,
        holding_values: list[list[int] | None] | None = None,
        input_values: list[list[int] | None] | None = None,
    ) -> None:
        self.connect_result = connect_result
        self.holding_values = list(holding_values or [])
        self.input_values = list(input_values or [])
        self.close_count = 0
        self.connected = False

    def connect(self) -> bool:
        self.connected = self.connect_result
        return self.connect_result

    def read_holding_registers(self, address: int, count: int, slave: int) -> FakeResponse | None:
        if not self.holding_values:
            return None
        return FakeResponse(self.holding_values.pop(0))

    def read_input_registers(self, address: int, count: int, slave: int) -> FakeResponse | None:
        if not self.input_values:
            return None
        return FakeResponse(self.input_values.pop(0))

    def close(self) -> None:
        self.close_count += 1
        self.connected = False


def test_read_holding_register_returns_temp_reading() -> None:
    fake_client = FakeModbusClient(holding_values=[[123]])
    reader = ModbusTempReader(
        host="127.0.0.1",
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    reading = reader.read()

    assert reading.celsius == 123.0
    assert reading.source == "modbus_temp"


def test_read_input_register_returns_temp_reading() -> None:
    fake_client = FakeModbusClient(input_values=[[88]])
    reader = ModbusTempReader(
        host="127.0.0.1",
        function="input",
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    reading = reader.read()

    assert reading.celsius == 88.0


def test_scale_and_offset_are_applied() -> None:
    fake_client = FakeModbusClient(holding_values=[[100]])
    reader = ModbusTempReader(
        host="127.0.0.1",
        scale=0.1,
        offset=-5.0,
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    reading = reader.read()

    assert reading.celsius == 5.0


def test_read_can_be_called_multiple_times() -> None:
    fake_client = FakeModbusClient(holding_values=[[10], [20]])
    reader = ModbusTempReader(
        host="127.0.0.1",
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    first = reader.read()
    second = reader.read()

    assert first.celsius == 10.0
    assert second.celsius == 20.0


def test_open_raises_when_client_cannot_connect() -> None:
    reader = ModbusTempReader(
        host="127.0.0.1",
        client_factory=lambda: FakeModbusClient(connect_result=False),
    )

    with pytest.raises(RuntimeError, match="open Modbus connection"):
        reader.open()


def test_read_raises_when_register_read_fails() -> None:
    fake_client = FakeModbusClient(holding_values=[])
    reader = ModbusTempReader(
        host="127.0.0.1",
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    with pytest.raises(RuntimeError, match="read temperature register"):
        reader.read()


def test_read_raises_when_registers_are_empty() -> None:
    fake_client = FakeModbusClient(holding_values=[[]])
    reader = ModbusTempReader(
        host="127.0.0.1",
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    with pytest.raises(RuntimeError, match="empty register response"):
        reader.read()


def test_close_is_idempotent() -> None:
    fake_client = FakeModbusClient(holding_values=[[10]])
    reader = ModbusTempReader(
        host="127.0.0.1",
        client_factory=lambda: fake_client,
        auto_open=True,
    )

    reader.close()
    reader.close()

    assert fake_client.close_count == 1


@pytest.mark.parametrize(
    ("host", "port", "register_count"),
    [
        ("", 502, 1),
        ("127.0.0.1", 0, 1),
        ("127.0.0.1", 502, 0),
    ],
)
def test_invalid_init_values_raise_value_error(host: str, port: int, register_count: int) -> None:
    with pytest.raises(ValueError):
        ModbusTempReader(
            host=host,
            port=port,
            register_count=register_count,
            client_factory=lambda: FakeModbusClient(),
        )
