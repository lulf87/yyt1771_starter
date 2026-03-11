import pytest

from src.camera.hik_rtsp_opencv import HikRtspCamera, build_hik_rtsp_url


class FakeCapture:
    def __init__(self, opened: bool = True, frames: list[object] | None = None) -> None:
        self._opened = opened
        self._frames = list(frames or [])
        self.release_count = 0
        self.read_count = 0

    def isOpened(self) -> bool:
        return self._opened

    def read(self) -> tuple[bool, object | None]:
        self.read_count += 1
        if not self._frames:
            return (False, None)
        return (True, self._frames.pop(0))

    def release(self) -> None:
        self.release_count += 1
        self._opened = False


def test_build_hik_rtsp_url_uses_expected_format() -> None:
    url = build_hik_rtsp_url(
        host="192.168.1.10",
        username="admin",
        password="secret",
        channel=2,
        stream=1,
        port=8554,
    )

    assert url == "rtsp://admin:secret@192.168.1.10:8554/Streaming/channels/21"


@pytest.mark.parametrize(
    ("channel", "stream", "port"),
    [
        (0, 1, 554),
        (1, 0, 554),
        (1, 1, 0),
    ],
)
def test_build_hik_rtsp_url_rejects_invalid_values(channel: int, stream: int, port: int) -> None:
    with pytest.raises(ValueError):
        build_hik_rtsp_url(
            host="192.168.1.10",
            username="admin",
            password="secret",
            channel=channel,
            stream=stream,
            port=port,
        )


def test_read_frame_returns_fake_frame_and_increments_frame_id() -> None:
    fake_capture = FakeCapture(frames=[{"frame": 1}, {"frame": 2}])
    camera = HikRtspCamera(
        rtsp_url="rtsp://example",
        capture_factory=lambda url: fake_capture,
        auto_open=True,
    )

    first = camera.read_frame()
    second = camera.read_frame()

    assert first.image == {"frame": 1}
    assert second.image == {"frame": 2}
    assert first.frame_id == 1
    assert second.frame_id == 2
    assert first.meta["transport"] == "rtsp"
    assert first.meta["backend"] == "opencv"


def test_open_raises_when_capture_cannot_open() -> None:
    camera = HikRtspCamera(
        rtsp_url="rtsp://example",
        capture_factory=lambda url: FakeCapture(opened=False),
    )

    with pytest.raises(RuntimeError, match="open RTSP stream"):
        camera.open()


def test_read_frame_raises_when_capture_read_fails() -> None:
    camera = HikRtspCamera(
        rtsp_url="rtsp://example",
        capture_factory=lambda url: FakeCapture(frames=[]),
        auto_open=True,
    )

    with pytest.raises(RuntimeError, match="read frame"):
        camera.read_frame()


def test_close_releases_capture_and_is_idempotent() -> None:
    fake_capture = FakeCapture(frames=[{"frame": 1}])
    camera = HikRtspCamera(
        rtsp_url="rtsp://example",
        capture_factory=lambda url: fake_capture,
        auto_open=True,
    )

    camera.close()
    camera.close()

    assert fake_capture.release_count == 1
