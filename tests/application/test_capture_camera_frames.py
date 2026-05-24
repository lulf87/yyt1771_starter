from src.application.capture_camera_frames import _configure_temp_controller


class FakeTempController:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float | None]] = []

    def set_target_temperature(self, celsius: float) -> None:
        self.calls.append(("set_target_temperature", float(celsius)))

    def set_output_power_percent(self, percent: float) -> None:
        self.calls.append(("set_output_power_percent", float(percent)))

    def start_output(self) -> None:
        self.calls.append(("start_output", None))


def test_configure_temp_controller_sets_target_power_and_starts_output() -> None:
    controller = FakeTempController()

    _configure_temp_controller(
        controller,
        target_temperature_celsius=25.0,
        output_power_percent=100.0,
        start_output=True,
    )

    assert controller.calls == [
        ("set_target_temperature", 25.0),
        ("set_output_power_percent", 100.0),
        ("start_output", None),
    ]


def test_configure_temp_controller_skips_unspecified_actions() -> None:
    controller = FakeTempController()

    _configure_temp_controller(
        controller,
        target_temperature_celsius=None,
        output_power_percent=75.0,
        start_output=False,
    )

    assert controller.calls == [("set_output_power_percent", 75.0)]
