import time
from types import SimpleNamespace

import numpy as np
import pytest

from src.application.frame_pixel_contract import FramePixelContractError
from src.application.live_preview_service import LivePreviewService, compute_preview_interval_ms
from src.application.runtime_config import load_runtime_config
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


def test_live_preview_service_start_stream_hands_off_previous_run() -> None:
    service = LivePreviewService()

    class PreviewCamera:
        def __init__(self, label: str) -> None:
            self.label = label
            self.frame_id = 0
            self.closed = False

        def read_frame(self) -> FramePacket:
            if self.closed:
                raise RuntimeError(f"{self.label} closed")
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=1_000 + self.frame_id,
                source=self.label,
                image=[[self.frame_id]],
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.closed = True

    cameras = [PreviewCamera("camera-a"), PreviewCamera("camera-b")]
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": cameras.pop(0)

    first_stream, first_frame = service.start_stream(object(), run_id="run-a")
    second_stream, second_frame = service.start_stream(object(), run_id="run-b")

    assert first_frame.source == "camera-a"
    assert second_frame.source == "camera-b"
    assert first_stream.run_id == "run-a"
    assert second_stream.run_id == "run-b"
    assert service.get_preview_state(run_id="run-a").stream_active is False
    assert service.get_preview_state(run_id="run-b").stream_active is True
    assert service.get_cached_frame(run_id="run-a") is None
    assert service.get_cached_frame(run_id="run-b") is not None
    assert second_stream.reader_thread is not None
    assert cameras == []

    service.stop_stream(run_id="run-b")
    service.wait_for_stream_stop(run_id="run-b", timeout_ms=1_000)

    assert first_stream.camera.closed is True
    assert second_stream.camera.closed is True


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


def test_fetch_frame_reuses_active_stream_frame_before_opening_new_camera() -> None:
    service = LivePreviewService()

    class StreamingCamera:
        def __init__(self) -> None:
            self.frame_id = 0
            self.closed = False

        def read_frame(self) -> FramePacket:
            if self.closed:
                raise RuntimeError("camera closed")
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=1_000 + self.frame_id,
                source="active_preview_camera",
                image=[[self.frame_id]],
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.closed = True

    active_camera = StreamingCamera()
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": active_camera
    service.start_stream(object(), run_id="run-active")
    time.sleep(0.02)

    frame = service.fetch_frame(SimpleNamespace(adapters={"camera": "hik_gige_mvs"}), run_id="run-other", prefer_cached=False)

    assert frame.source == "active_preview_camera"
    assert service.get_cached_frame(run_id="run-other") is frame

    service.stop_stream(run_id="run-active")
    service.wait_for_stream_stop(run_id="run-active", timeout_ms=1_000)


def test_retire_active_stream_stops_current_preview_without_knowing_run_id() -> None:
    service = LivePreviewService()

    class PreviewCamera:
        def __init__(self) -> None:
            self.frame_id = 0
            self.closed = False

        def read_frame(self) -> FramePacket:
            if self.closed:
                raise RuntimeError("camera closed")
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=1_000 + self.frame_id,
                source="retired_preview_camera",
                image=[[self.frame_id]],
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.closed = True

    camera = PreviewCamera()
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": camera
    service.start_stream(object(), run_id="run-retire")
    time.sleep(0.02)

    assert service.retire_active_stream(timeout_ms=1_000) is True
    assert service.wait_for_stream_stop(run_id="run-retire", timeout_ms=1_000) is True
    assert camera.closed is True
    assert service.get_preview_state(run_id="run-retire").stream_active is False


def test_fetch_frame_discards_hik_warmup_frames_for_fresh_capture() -> None:
    service = LivePreviewService()

    class IncrementingCamera:
        def __init__(self) -> None:
            self.frame_id = 0
            self.closed = False

        def read_frame(self) -> FramePacket:
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=1_000 + self.frame_id,
                source="hik_warmup_camera",
                image=[[self.frame_id]],
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.closed = True

    camera = IncrementingCamera()
    runtime_config = SimpleNamespace(adapters={"camera": "hik_gige_mvs"})
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": camera

    frame = service.fetch_frame(runtime_config, run_id="run-hik-fresh", prefer_cached=False)

    assert frame.frame_id == 3
    assert camera.closed is True


def test_fetch_frame_keeps_single_read_for_non_hik_backends() -> None:
    service = LivePreviewService()

    class IncrementingCamera:
        def __init__(self) -> None:
            self.frame_id = 0
            self.closed = False

        def read_frame(self) -> FramePacket:
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=2_000 + self.frame_id,
                source="generic_preview_camera",
                image=[[self.frame_id]],
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.closed = True

    camera = IncrementingCamera()
    runtime_config = SimpleNamespace(adapters={"camera": "mock"})
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": camera

    frame = service.fetch_frame(runtime_config, run_id="run-mock-fresh", prefer_cached=False)

    assert frame.frame_id == 1
    assert camera.closed is True


def test_fetch_frame_retries_retryable_hik_handle_creation_failures() -> None:
    service = LivePreviewService()

    class RetryableFailCamera:
        def __init__(self) -> None:
            self.closed = False

        def read_frame(self) -> FramePacket:
            raise RuntimeError("Failed to create handle via Hik MVS SDK (ret=0x80000004)")

        def close(self) -> None:
            self.closed = True

    class SuccessCamera:
        def __init__(self) -> None:
            self.closed = False
            self.frame_id = 0

        def read_frame(self) -> FramePacket:
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=3_000 + self.frame_id,
                source="retry_success_camera",
                image=[[self.frame_id]],
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.closed = True

    failing_camera = RetryableFailCamera()
    success_camera = SuccessCamera()
    cameras = [failing_camera, success_camera]
    runtime_config = SimpleNamespace(adapters={"camera": "hik_gige_mvs"})
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": cameras.pop(0)

    frame = service.fetch_frame(runtime_config, run_id="run-hik-retry", prefer_cached=False)

    assert frame.source == "retry_success_camera"
    assert failing_camera.closed is True
    assert success_camera.closed is True


def test_fetch_frame_rejects_locked_profile_preview_pixels_that_differ_from_offline_material() -> None:
    service = LivePreviewService()

    class WrongSizeCamera:
        def __init__(self) -> None:
            self.closed = False
            self.frame_id = 0

        def read_frame(self) -> FramePacket:
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=4_000 + self.frame_id,
                source="wrong_size_camera",
                image=np.zeros((620, 1120), dtype=np.uint8),
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.closed = True

    camera = WrongSizeCamera()
    runtime_config = load_runtime_config("dev_lab")
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": camera

    with pytest.raises(FramePixelContractError, match="expected=2048x1364, actual=1120x620"):
        service.fetch_frame(runtime_config, run_id="run-wrong-size", prefer_cached=False)

    assert camera.closed is True


def test_fetch_frame_accepts_locked_profile_preview_pixels_that_match_offline_material() -> None:
    service = LivePreviewService()

    class MatchingSizeCamera:
        def __init__(self) -> None:
            self.closed = False
            self.frame_id = 0

        def read_frame(self) -> FramePacket:
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=5_000 + self.frame_id,
                source="matching_size_camera",
                image=np.zeros((1364, 2048), dtype=np.uint8),
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            self.closed = True

    camera = MatchingSizeCamera()
    runtime_config = load_runtime_config("dev_lab")
    service.open_camera = lambda runtime_config, *, profile_name="setup_preview": camera

    frame = service.fetch_frame(runtime_config, run_id="run-matching-size", prefer_cached=False)

    assert frame.frame_id == 3
    assert frame.meta["pixel_contract_width"] == 2048
    assert frame.meta["pixel_contract_height"] == 1364
    assert camera.closed is True
