import pytest

from src.camera.hik_gige_mvs import HikGigeMvsCamera


class FakeMvsHandle:
    def __init__(self, frames: list[object] | None = None) -> None:
        self.frames = list(frames or [])
        self.opened = False
        self.open_count = 0
        self.close_count = 0

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
        ("", "gige_vision", "hik_mvs", 750),
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
