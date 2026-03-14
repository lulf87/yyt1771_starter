import pytest

from src.camera.hik_gige_mvs import HikGigeMvsCamera


class FakeMvsHandle:
    def __init__(
        self,
        frames: list[object] | None = None,
        *,
        model: str = "MV-CU060-10GM",
        serial_number: str = "DEV-001",
        ip: str = "192.168.1.10",
    ) -> None:
        self.frames = list(frames or [])
        self.opened = False
        self.open_count = 0
        self.close_count = 0
        self.model = model
        self.serial_number = serial_number
        self.ip = ip

    def open(self) -> None:
        self.open_count += 1
        self.opened = True

    def is_opened(self) -> bool:
        return self.opened

    def read_frame(self, *, timeout_ms: int = 1000) -> object | None:
        assert timeout_ms == 750
        if not self.frames:
            return None
        return self.frames.pop(0)

    def close(self) -> None:
        self.close_count += 1
        self.opened = False


def _build_camera(camera_factory) -> HikGigeMvsCamera:
    return HikGigeMvsCamera(
        model="MV-CU060-10GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="DEV-001",
        trigger_mode="free_run",
        timeout_ms=750,
        camera_factory=camera_factory,
    )


def test_open_read_close_flow_returns_frame_packets_with_incrementing_ids() -> None:
    fake_handle = FakeMvsHandle(frames=[{"frame": 1}, {"frame": 2}])
    camera = _build_camera(lambda: fake_handle)

    camera.open()
    first = camera.read_frame()
    second = camera.read_frame()
    camera.close()

    assert fake_handle.open_count == 1
    assert fake_handle.close_count == 1
    assert first.image == {"frame": 1}
    assert second.image == {"frame": 2}
    assert first.frame_id == 1
    assert second.frame_id == 2
    assert first.meta["backend"] == "hik_gige_mvs"
    assert first.meta["transport"] == "gige_vision"
    assert first.meta["model"] == "MV-CU060-10GM"
    assert first.meta["serial_number"] == "DEV-001"
    assert first.meta["trigger_mode"] == "free_run"


def test_read_frame_auto_opens_camera_when_needed() -> None:
    fake_handle = FakeMvsHandle(frames=[{"frame": 1}])
    camera = _build_camera(lambda: fake_handle)

    packet = camera.read_frame()

    assert packet.frame_id == 1
    assert fake_handle.open_count == 1
    assert camera.is_opened() is True


def test_open_raises_clear_error_when_factory_cannot_create_handle() -> None:
    camera = _build_camera(lambda: (_ for _ in ()).throw(RuntimeError("sdk missing")))

    with pytest.raises(RuntimeError, match="create Hik MVS camera handle"):
        camera.open()


def test_probe_once_selection_mode_pinned_prefers_serial_number_as_identity() -> None:
    camera = HikGigeMvsCamera(
        model="MV-CU060-10GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        ip="192.168.1.10",
        pixel_format="mono8",
        timeout_ms=750,
        camera_factory=lambda: FakeMvsHandle(
            frames=[[[0, 255], [255, 0]]],
            serial_number="MV-SERIAL-001",
            ip="192.168.1.10",
        ),
    )

    payload = camera.probe_once(selection_mode="pinned")

    assert payload["matched_by"] == "serial_number"
    assert payload["detected_serial_number"] == "MV-SERIAL-001"
    assert payload["detected_ip"] == "192.168.1.10"
    assert payload["detected_model"] == "MV-CU060-10GM"
    assert payload["frame_shape"] == {"width": 2, "height": 2}
    assert payload["pixel_format"] == "mono8"
    assert payload["frame_id"] == 1
    assert isinstance(payload["timestamp_ms"], int)


def test_probe_once_selection_mode_pinned_falls_back_to_ip_identity() -> None:
    camera = HikGigeMvsCamera(
        model="MV-CU060-10GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="",
        ip="192.168.1.10",
        timeout_ms=750,
        camera_factory=lambda: FakeMvsHandle(
            frames=[[[1, 2, 3]]],
            serial_number="",
            ip="192.168.1.10",
        ),
    )

    payload = camera.probe_once(selection_mode="pinned")

    assert payload["matched_by"] == "ip"
    assert payload["detected_serial_number"] == ""
    assert payload["detected_ip"] == "192.168.1.10"
    assert payload["frame_shape"] == {"width": 3, "height": 1}


def test_probe_once_rejects_missing_identity_in_pinned_mode() -> None:
    camera = HikGigeMvsCamera(
        model="",
        transport="gige_vision",
        sdk_name="hik_mvs",
        timeout_ms=750,
        camera_factory=lambda: FakeMvsHandle(frames=[[[0]]], serial_number="", ip=""),
    )

    with pytest.raises(ValueError, match="serial_number or ip"):
        camera.probe_once(selection_mode="pinned")


def test_probe_once_first_discovered_succeeds_without_identity() -> None:
    camera = HikGigeMvsCamera(
        model="",
        transport="gige_vision",
        sdk_name="hik_mvs",
        timeout_ms=750,
        camera_factory=lambda: FakeMvsHandle(
            frames=[[[0, 1, 2], [3, 4, 5]]],
            model="ANY-MODEL",
            serial_number="DISCOVERED-001",
            ip="192.168.1.88",
        ),
    )

    payload = camera.probe_once(selection_mode="first_discovered")

    assert payload["matched_by"] == "first_discovered"
    assert payload["detected_model"] == "ANY-MODEL"
    assert payload["detected_serial_number"] == "DISCOVERED-001"
    assert payload["detected_ip"] == "192.168.1.88"
    assert payload["frame_shape"] == {"width": 3, "height": 2}


def test_probe_once_surfaces_factory_failures_clearly() -> None:
    camera = HikGigeMvsCamera(
        model="MV-CU060-10GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        timeout_ms=750,
        camera_factory=lambda: (_ for _ in ()).throw(RuntimeError("sdk missing")),
    )

    with pytest.raises(RuntimeError, match="create Hik MVS camera handle"):
        camera.probe_once(selection_mode="pinned")


def test_close_is_idempotent() -> None:
    fake_handle = FakeMvsHandle(frames=[{"frame": 1}])
    camera = _build_camera(lambda: fake_handle)
    camera.open()

    camera.close()
    camera.close()

    assert fake_handle.close_count == 1


@pytest.mark.parametrize(
    ("model", "transport", "sdk_name", "timeout_ms"),
    [
        ("MV-CU060-10GM", "", "hik_mvs", 750),
        ("MV-CU060-10GM", "gige_vision", "", 750),
        ("MV-CU060-10GM", "gige_vision", "hik_mvs", 0),
    ],
)
def test_missing_required_init_values_raise_value_error(
    model: str,
    transport: str,
    sdk_name: str,
    timeout_ms: int,
) -> None:
    with pytest.raises(ValueError):
        HikGigeMvsCamera(
            model=model,
            transport=transport,
            sdk_name=sdk_name,
            timeout_ms=timeout_ms,
            camera_factory=lambda: FakeMvsHandle(),
        )
