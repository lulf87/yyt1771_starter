from fastapi.testclient import TestClient

from src.webapp.app import create_app


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

    response = client.post("/api/system/temp/target", json={"target_temperature_celsius": 75.5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "mock"
    assert payload["target_temperature_celsius"] == 75.5
    assert payload["confirmed_target_temperature_celsius"] == 75.5
    assert payload["source"] == "_TempControllerFixture"


def test_set_target_temp_api_returns_503_when_write_fails() -> None:
    app = create_app(profile="dev_mock")
    app.state.application_container.build_temp_controller = lambda: _FailingTempControllerFixture()
    client = TestClient(app)

    response = client.post("/api/system/temp/target", json={"target_temperature_celsius": 75.0})

    assert response.status_code == 503
    assert response.json() == {"detail": "Target temperature update unavailable: serial unavailable"}
