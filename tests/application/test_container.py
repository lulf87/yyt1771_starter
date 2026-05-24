from src.application.container import ApplicationContainer
from src.application.runtime_config import RuntimeConfig, WebAppConfig


class _ClosableTempController:
    def __init__(self) -> None:
        self.close_count = 0

    def close(self) -> None:
        self.close_count += 1


def _runtime_config(temp_backend: str) -> RuntimeConfig:
    runtime_config = RuntimeConfig(
        profile="fixture",
        platform="mac",
        mode="lab",
        webapp=WebAppConfig(host="127.0.0.1", port=8000),
        adapters={"camera": "mock", "temp": temp_backend, "plc": "mock"},
    )
    runtime_config.live.temp.backend = temp_backend
    return runtime_config


def test_lu92xx_temp_controller_is_shared_across_app_services(monkeypatch) -> None:
    created: list[_ClosableTempController] = []

    def fake_build_temp_controller(runtime_config: RuntimeConfig) -> _ClosableTempController:
        controller = _ClosableTempController()
        created.append(controller)
        return controller

    monkeypatch.setattr("src.application.container.build_temp_controller", fake_build_temp_controller)
    container = ApplicationContainer(_runtime_config("lu92xx_modbus_rtu"))

    first = container.build_temp_controller()
    second = container.build_temp_controller()
    via_handler = container.with_temp_controller(lambda controller: controller)

    assert first is second
    assert via_handler is first
    assert len(created) == 1
    assert first.close_count == 0

    container.reset_temp_controller()

    assert first.close_count == 1
    assert container.build_temp_controller() is not first
    assert len(created) == 2
