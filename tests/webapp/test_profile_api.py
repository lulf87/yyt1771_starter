from pathlib import Path

from fastapi.testclient import TestClient
import yaml

from src.application.temp_serial_ports import SerialPortInfo
from src.application import runtime_config as config_module
from src.webapp.app import create_app
import src.webapp.routes.profile as profile_routes


def test_profile_api_returns_runtime_profile_payload() -> None:
    client = TestClient(create_app(profile="prod_win"))

    response = client.get("/api/system/profile")

    assert response.status_code == 200
    assert response.json() == {
        "profile": "prod_win",
        "platform": "windows",
        "mode": "production",
        "webapp": {
            "host": "0.0.0.0",
            "port": 8080,
        },
        "adapters": {
            "camera": "hik_gige_mvs",
            "temp": "lu92xx_modbus_rtu",
            "plc": "modbus_tcp",
        },
    }


class _TempReadingFixture:
    def __init__(self, celsius: float, timestamp_ms: int = 1234, source: str = "fixture_temp") -> None:
        self.celsius = celsius
        self.timestamp_ms = timestamp_ms
        self.source = source


class _TempControllerFixture:
    def __init__(self, reading: _TempReadingFixture) -> None:
        self._reading = reading
        self.target_temperature_celsius = 25.0

    def read(self) -> _TempReadingFixture:
        return self._reading

    def set_target_temperature(self, celsius: float) -> None:
        self.target_temperature_celsius = celsius

    def read_target_temperature(self) -> float:
        return self.target_temperature_celsius


class _FailingTempControllerFixture:
    def read(self) -> _TempReadingFixture:
        raise RuntimeError("serial unavailable")

    def set_target_temperature(self, celsius: float) -> None:
        raise RuntimeError("serial unavailable")

    def read_target_temperature(self) -> float:
        raise RuntimeError("serial unavailable")


class _PortAwareTempControllerFixture:
    def __init__(self, *, port: str, fail_port: str | None = None) -> None:
        self.port = port
        self.fail_port = fail_port

    def read(self) -> _TempReadingFixture:
        if self.port == self.fail_port:
            raise RuntimeError(f"cannot read {self.port}")
        return _TempReadingFixture(celsius=31.2, timestamp_ms=4321, source=f"fixture:{self.port}")


def test_current_temp_api_returns_backend_reading() -> None:
    app = create_app(profile="dev_mock")
    app.state.application_container.build_temp_controller = lambda: _TempControllerFixture(
        _TempReadingFixture(celsius=42.3, timestamp_ms=9876, source="mock_temp_fixture")
    )
    client = TestClient(app)

    response = client.get("/api/system/temp/current")

    assert response.status_code == 200
    assert response.json() == {
        "backend": "mock",
        "temperature_celsius": 42.3,
        "timestamp_ms": 9876,
        "source": "mock_temp_fixture",
    }


def test_current_temp_api_returns_503_when_temp_read_fails() -> None:
    app = create_app(profile="dev_mock")
    app.state.application_container.build_temp_controller = lambda: _FailingTempControllerFixture()
    client = TestClient(app)

    response = client.get("/api/system/temp/current")

    assert response.status_code == 503
    assert response.json() == {"detail": "Current temperature unavailable: serial unavailable"}


def test_set_target_temp_api_writes_and_reads_back_confirmed_value() -> None:
    app = create_app(profile="dev_mock")
    controller = _TempControllerFixture(_TempReadingFixture(celsius=42.3, timestamp_ms=9876, source="mock_temp_fixture"))
    app.state.application_container.build_temp_controller = lambda: controller
    client = TestClient(app)

    response = client.post("/api/system/temp/target", json={"target_temperature_celsius": 45.5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "mock"
    assert payload["target_temperature_celsius"] == 45.5
    assert payload["confirmed_target_temperature_celsius"] == 45.5
    assert payload["source"] == "_TempControllerFixture"


def test_set_target_temp_api_returns_503_when_write_fails() -> None:
    app = create_app(profile="dev_mock")
    app.state.application_container.build_temp_controller = lambda: _FailingTempControllerFixture()
    client = TestClient(app)

    response = client.post("/api/system/temp/target", json={"target_temperature_celsius": 45.0})

    assert response.status_code == 503
    assert response.json() == {"detail": "Target temperature update unavailable: serial unavailable"}


def test_set_target_temp_api_accepts_negative_temperature_within_range() -> None:
    app = create_app(profile="dev_mock")
    controller = _TempControllerFixture(_TempReadingFixture(celsius=12.3, timestamp_ms=9876, source="mock_temp_fixture"))
    app.state.application_container.build_temp_controller = lambda: controller
    client = TestClient(app)

    response = client.post("/api/system/temp/target", json={"target_temperature_celsius": -20.0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["target_temperature_celsius"] == -20.0
    assert payload["confirmed_target_temperature_celsius"] == -20.0


def test_set_target_temp_api_rejects_temperature_outside_range() -> None:
    app = create_app(profile="dev_mock")
    controller = _TempControllerFixture(_TempReadingFixture(celsius=42.3, timestamp_ms=9876, source="mock_temp_fixture"))
    app.state.application_container.build_temp_controller = lambda: controller
    client = TestClient(app)

    response = client.post("/api/system/temp/target", json={"target_temperature_celsius": 75.0})

    assert response.status_code == 422


def test_temp_serial_ports_api_lists_ports_and_current_selection(monkeypatch) -> None:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.live.temp.backend = "lu92xx_modbus_rtu"
    app.state.runtime_config.live.temp.serial.port = "COM2"
    monkeypatch.setattr(
        profile_routes,
        "list_serial_ports",
        lambda: [
            SerialPortInfo(device="COM2", name="COM2", description="USB Serial A", hwid="HWID-A"),
            SerialPortInfo(device="COM5", name="COM5", description="USB Serial B", hwid="HWID-B"),
        ],
    )
    client = TestClient(app)

    response = client.get("/api/system/temp/serial-ports")

    assert response.status_code == 200
    assert response.json() == {
        "backend": "lu92xx_modbus_rtu",
        "configured_port": "COM2",
        "selected_port": "COM2",
        "ports": [
            {"device": "COM2", "name": "COM2", "description": "USB Serial A", "hwid": "HWID-A"},
            {"device": "COM5", "name": "COM5", "description": "USB Serial B", "hwid": "HWID-B"},
        ],
    }


def test_temp_serial_port_select_updates_runtime_config_reads_temperature_and_persists_user_override(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.live.temp.backend = "lu92xx_modbus_rtu"
    app.state.runtime_config.live.temp.serial.port = "COM2"
    user_config_dir = tmp_path / "user-configs"
    monkeypatch.setenv(config_module.USER_CONFIG_DIR_ENV, str(user_config_dir))
    monkeypatch.setattr(
        profile_routes,
        "list_serial_ports",
        lambda: [SerialPortInfo(device="COM5", name="COM5", description="USB Serial B", hwid="HWID-B")],
    )
    app.state.application_container.build_temp_controller = lambda: _PortAwareTempControllerFixture(
        port=app.state.runtime_config.live.temp.serial.port,
    )
    client = TestClient(app)

    response = client.post("/api/system/temp/serial-port", json={"port": "COM5"})

    assert response.status_code == 200
    assert app.state.runtime_config.live.temp.serial.port == "COM5"
    assert response.json() == {
        "backend": "lu92xx_modbus_rtu",
        "selected_port": "COM5",
        "temperature_celsius": 31.2,
        "timestamp_ms": 4321,
        "source": "fixture:COM5",
    }
    override = yaml.safe_load((user_config_dir / "dev_mock.local.yaml").read_text(encoding="utf-8"))
    assert override == {"temp": {"serial": {"port": "COM5"}}}


def test_temp_serial_port_select_rolls_back_when_temperature_read_fails(monkeypatch) -> None:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.live.temp.backend = "lu92xx_modbus_rtu"
    app.state.runtime_config.live.temp.serial.port = "COM2"
    monkeypatch.setattr(
        profile_routes,
        "list_serial_ports",
        lambda: [SerialPortInfo(device="COM7", name="COM7", description="USB Serial C", hwid="HWID-C")],
    )
    app.state.application_container.build_temp_controller = lambda: _PortAwareTempControllerFixture(
        port=app.state.runtime_config.live.temp.serial.port,
        fail_port="COM7",
    )
    client = TestClient(app)

    response = client.post("/api/system/temp/serial-port", json={"port": "COM7"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Temperature serial port selection unavailable: cannot read COM7"}
    assert app.state.runtime_config.live.temp.serial.port == "COM2"


def test_temp_serial_port_select_rejects_unknown_visible_port(monkeypatch) -> None:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.live.temp.backend = "lu92xx_modbus_rtu"
    app.state.runtime_config.live.temp.serial.port = "COM2"
    monkeypatch.setattr(
        profile_routes,
        "list_serial_ports",
        lambda: [SerialPortInfo(device="COM5", name="COM5", description="USB Serial B", hwid="HWID-B")],
    )
    client = TestClient(app)

    response = client.post("/api/system/temp/serial-port", json={"port": "COM9"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Serial port is not currently visible: COM9"}
    assert app.state.runtime_config.live.temp.serial.port == "COM2"
