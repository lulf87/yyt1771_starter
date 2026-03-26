import time

from src.application.live_preview_service import LivePreviewService, compute_preview_interval_ms
from src.core.models import FramePacket


def test_compute_preview_interval_ms_allows_50hz_target() -> None:
    assert compute_preview_interval_ms(target_fps=18.0, fallback_ms=500) == 55
    assert compute_preview_interval_ms(target_fps=50.0, fallback_ms=500) == 20
    assert compute_preview_interval_ms(target_fps=100.0, fallback_ms=500) == 10
    assert compute_preview_interval_ms(target_fps=None, fallback_ms=7) == 10


def test_live_preview_service_tracks_presented_frames_for_desktop_shell() -> None:
    service = LivePreviewService()

    class FastPreviewCamera:
        def __init__(self) -> None:
            self.frame_id = 0
            self.closed = False

        def read_frame(self) -> FramePacket:
            if self.closed:
                raise RuntimeError("camera closed")
            self.frame_id += 1
            time.sleep(0.005)
            return FramePacket(
                timestamp_ms=1_000 + self.frame_id,
                source="fast_preview_camera",
                image=[[self.frame_id]],
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.closed = True

    camera = FastPreviewCamera()
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": camera

    service.start_stream(object(), run_id="run-desktop")
    time.sleep(0.02)
    first_frame = service.get_cached_frame(run_id="run-desktop")
    assert first_frame is not None
    service.mark_frame_presented(run_id="run-desktop", frame=first_frame)

    time.sleep(0.04)
    latest_frame = service.get_cached_frame(run_id="run-desktop")
    assert latest_frame is not None
    service.mark_frame_presented(run_id="run-desktop", frame=latest_frame)

    snapshot = service.get_preview_state(run_id="run-desktop")
    assert snapshot.preview_display_fps is not None
    assert snapshot.preview_display_fps > 0

    service.stop_stream(run_id="run-desktop")
    service.wait_for_stream_stop(run_id="run-desktop", timeout_ms=1_000)
    assert camera.closed is True


def test_live_preview_service_close_stream_is_idempotent() -> None:
    service = LivePreviewService()

    class CloseOnceCamera:
        def __init__(self) -> None:
            self.frame_id = 0
            self.close_calls = 0

        def read_frame(self) -> FramePacket:
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=1_000 + self.frame_id,
                source="close_once_camera",
                image=[[self.frame_id]],
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.close_calls += 1
            if self.close_calls > 1:
                raise RuntimeError("camera already closed")

    camera = CloseOnceCamera()
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": camera
    active_stream, _ = service.start_stream(object(), run_id="run-close-idempotent")

    service._close_stream(active_stream)
    service._close_stream(active_stream)

    assert camera.close_calls == 1


def test_live_preview_service_does_not_double_throttle_hardware_paced_frames() -> None:
    service = LivePreviewService()

    class HardwarePacedCamera:
        def __init__(self) -> None:
            self.frame_id = 0
            self.closed = False

        def read_frame(self) -> FramePacket:
            if self.closed:
                raise RuntimeError("camera closed")
            time.sleep(0.005)
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=1_000 + self.frame_id,
                source="hardware_paced_camera",
                image=[[self.frame_id]],
                frame_id=self.frame_id,
                meta={"camera_target_frame_rate_hz": 100.0},
            )

        def close(self) -> None:
            self.closed = True

    camera = HardwarePacedCamera()
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": camera
    active_stream, first_frame = service.start_stream(object(), run_id="run-hardware-paced")

    iterator = service.stream_frames(active_stream, first_frame=first_frame, frame_interval_ms=50)
    start = time.perf_counter()
    frames = [next(iterator) for _ in range(4)]
    elapsed_s = time.perf_counter() - start
    service.stop_stream(run_id="run-hardware-paced")
    iterator.close()
    service.wait_for_stream_stop(run_id="run-hardware-paced", timeout_ms=1_000)

    assert [frame.frame_id for frame in frames] == [1, 2, 3, 4]
    assert elapsed_s < 0.06


def test_live_preview_service_exposes_active_probe_payload() -> None:
    service = LivePreviewService()

    class ProbeCamera:
        def __init__(self) -> None:
            self.frame_id = 0
            self.model = "MV-CA060-11GM"
            self.serial_number = "00J67378626"
            self.ip = "192.168.3.211"
            self.transport = "gige_vision"
            self.sdk_name = "hik_mvs"
            self.pixel_format = "mono8"
            self.backend_name = "hik_gige_mvs"
            self.closed = False

        def read_frame(self) -> FramePacket:
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=1_000 + self.frame_id,
                source="probe_camera",
                image=[[0, 1, 2], [3, 4, 5]],
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.closed = True

    camera = ProbeCamera()
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": camera
    service.start_stream(object(), run_id="run-probe")
    time.sleep(0.02)

    payload = service.get_active_probe_payload()

    assert payload is not None
    assert payload["matched_by"] == "active_preview"
    assert payload["detected_model"] == "MV-CA060-11GM"
    assert payload["detected_serial_number"] == "00J67378626"
    assert payload["detected_ip"] == "192.168.3.211"
    assert payload["frame_shape"] == {"width": 3, "height": 2}
    assert payload["pixel_format"] == "mono8"

    service.stop_stream(run_id="run-probe")
    service.wait_for_stream_stop(run_id="run-probe", timeout_ms=1_000)
