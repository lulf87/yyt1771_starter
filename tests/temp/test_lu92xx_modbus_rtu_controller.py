import pytest

from src.core.config_models import (
    SerialPortConfig,
    TempControlConfig,
    TempRegisterConfig,
    TempRegisterMapConfig,
    TempRuntimeConfig,
)
from src.temp.lu92xx_modbus_rtu_controller import LU92XXModbusRtuController


class FakeSerialTransport:
    def __init__(self, responses: list[bytes] | None = None) -> None:
        self.responses = list(responses or [])
        self.writes: list[bytes] = []
        self.close_count = 0

    def read(self, size: int) -> bytes:
        if not self.responses:
            return b""
        return self.responses.pop(0)

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def close(self) -> None:
        self.close_count += 1


def _crc_bytes(payload: bytes) -> bytes:
    crc = 0xFFFF
    for value in payload:
        crc ^= value
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return bytes((crc & 0xFF, (crc >> 8) & 0xFF))


def _read_response(slave: int, function_code: int, values: list[int]) -> bytes:
    payload = bytearray([slave, function_code, len(values) * 2])
    for value in values:
        payload.extend(((value >> 8) & 0xFF, value & 0xFF))
    return bytes(payload) + _crc_bytes(bytes(payload))


def _write_response(slave: int, function_code: int, start_address: int, value_or_count: int) -> bytes:
    payload = bytes(
        [
            slave,
            function_code,
            (start_address >> 8) & 0xFF,
            start_address & 0xFF,
            (value_or_count >> 8) & 0xFF,
            value_or_count & 0xFF,
        ]
    )
    return payload + _crc_bytes(payload)


def _exception_response(slave: int, function_code: int, exception_code: int) -> bytes:
    payload = bytes([slave, function_code | 0x80, exception_code])
    return payload + _crc_bytes(payload)


def _config() -> TempRuntimeConfig:
    return TempRuntimeConfig(
        backend="lu92xx_modbus_rtu",
        protocol="modbus_rtu",
        slave_address=1,
        serial=SerialPortConfig(port="COM5", baudrate=19_200, bytesize=8, parity="N", stopbits=1, timeout_ms=500),
        register_map=TempRegisterMapConfig(
            process_value=TempRegisterConfig(
                function_code=3,
                start_address=264,
                register_count=1,
                signed=True,
                decode_scale=0.1,
            ),
            target_or_stop_value=TempRegisterConfig(
                function_code=6,
                start_address=0,
                register_count=1,
                signed=True,
                encode_scale=10.0,
            ),
            output_power=TempRegisterConfig(
                function_code=6,
                start_address=4,
                register_count=1,
                signed=False,
                encode_scale=256.0,
            ),
        ),
        control=TempControlConfig(start_output_mode="power_nonzero", startup_power_percent=100.0),
    )


def test_read_decodes_process_value_with_default_scale() -> None:
    transport = FakeSerialTransport(responses=[_read_response(1, 3, [253])])
    controller = LU92XXModbusRtuController(_config(), transport_factory=lambda serial: transport)

    reading = controller.read()

    assert reading.celsius == 25.3
    request = transport.writes[0]
    assert request[:6] == bytes([1, 3, 0x01, 0x08, 0x00, 0x01])


def test_set_target_temperature_encodes_register_zero_with_x10_scale() -> None:
    transport = FakeSerialTransport(responses=[_write_response(1, 6, 0, 755)])
    controller = LU92XXModbusRtuController(_config(), transport_factory=lambda serial: transport)

    controller.set_target_temperature(75.5)

    assert transport.writes[0][:6] == bytes([1, 6, 0x00, 0x00, 0x02, 0xF3])


def test_read_target_temperature_decodes_register_zero_with_x10_scale() -> None:
    transport = FakeSerialTransport(responses=[_read_response(1, 3, [755])])
    controller = LU92XXModbusRtuController(_config(), transport_factory=lambda serial: transport)

    confirmed = controller.read_target_temperature()

    assert confirmed == 75.5
    assert transport.writes[0][:6] == bytes([1, 3, 0x00, 0x00, 0x00, 0x01])


def test_start_output_writes_scaled_power_register() -> None:
    transport = FakeSerialTransport(responses=[_write_response(1, 6, 4, 25600)])
    controller = LU92XXModbusRtuController(_config(), transport_factory=lambda serial: transport)

    controller.start_output()

    assert transport.writes[0][:6] == bytes([1, 6, 0x00, 0x04, 0x64, 0x00])


def test_stop_output_writes_zero_even_if_already_stopped() -> None:
    transport = FakeSerialTransport(
        responses=[
            _write_response(1, 6, 4, 0),
            _write_response(1, 6, 4, 0),
        ]
    )
    controller = LU92XXModbusRtuController(_config(), transport_factory=lambda serial: transport)

    controller.stop_output()
    controller.stop_output()

    assert transport.writes[0][:6] == bytes([1, 6, 0x00, 0x04, 0x00, 0x00])
    assert transport.writes[1][:6] == bytes([1, 6, 0x00, 0x04, 0x00, 0x00])


def test_process_value_address_can_be_overridden_to_258() -> None:
    config = _config()
    config.register_map.process_value.start_address = 258
    transport = FakeSerialTransport(responses=[_read_response(1, 3, [321])])
    controller = LU92XXModbusRtuController(config, transport_factory=lambda serial: transport)

    reading = controller.read()

    assert reading.celsius == 32.1
    assert transport.writes[0][:6] == bytes([1, 3, 0x01, 0x02, 0x00, 0x01])


def test_read_raises_on_bad_crc() -> None:
    bad_response = bytearray(_read_response(1, 3, [253]))
    bad_response[-1] ^= 0xFF
    transport = FakeSerialTransport(responses=[bytes(bad_response)])
    controller = LU92XXModbusRtuController(_config(), transport_factory=lambda serial: transport)

    with pytest.raises(RuntimeError, match="Invalid CRC"):
        controller.read()


def test_read_raises_on_timeout_or_no_response() -> None:
    controller = LU92XXModbusRtuController(_config(), transport_factory=lambda serial: FakeSerialTransport())

    with pytest.raises(RuntimeError, match="No response"):
        controller.read()


def test_read_raises_on_exception_response() -> None:
    transport = FakeSerialTransport(responses=[_exception_response(1, 3, 2)])
    controller = LU92XXModbusRtuController(_config(), transport_factory=lambda serial: transport)

    with pytest.raises(RuntimeError, match="illegal data address"):
        controller.read()


def test_close_is_idempotent() -> None:
    transport = FakeSerialTransport()
    controller = LU92XXModbusRtuController(_config(), transport_factory=lambda serial: transport)

    controller.open()
    controller.close()
    controller.close()

    assert transport.close_count == 1
