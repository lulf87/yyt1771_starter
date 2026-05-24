from pathlib import Path

import numpy as np

from src.camera.offline_capture_camera import OfflineCaptureCamera
from src.core.config_models import DeviceRoiConfig


def _write_capture_frames(capture_dir: Path) -> None:
    frames_dir = capture_dir / "frames"
    frames_dir.mkdir(parents=True)
    np.save(frames_dir / "frame_000001.npy", np.arange(24, dtype=np.uint8).reshape((4, 6)))
    np.save(frames_dir / "frame_000002.npy", np.full((4, 6), 77, dtype=np.uint8))


def test_offline_capture_camera_reads_npy_frames_without_resizing(tmp_path: Path) -> None:
    capture_dir = tmp_path / "fixture-capture"
    _write_capture_frames(capture_dir)

    camera = OfflineCaptureCamera(capture_dir=capture_dir, profile_name="setup_preview")

    first = camera.read_frame()
    second = camera.read_frame()
    looped = camera.read_frame()

    assert camera.playback_sample_count() == 2
    assert first.source == "offline_capture:fixture-capture"
    assert first.frame_id == 1
    assert first.meta["source_frame_index"] == 1
    assert first.meta["profile_name"] == "setup_preview"
    assert first.meta["capture_dir"] == str(capture_dir)
    assert first.image.shape == (4, 6)
    assert second.frame_id == 2
    assert second.meta["source_frame_index"] == 2
    assert np.array_equal(second.image, np.full((4, 6), 77, dtype=np.uint8))
    assert looped.frame_id == 3
    assert looped.meta["source_frame_index"] == 1
    assert np.array_equal(looped.image, first.image)


def test_offline_capture_camera_applies_profile_roi_in_source_coordinates(tmp_path: Path) -> None:
    capture_dir = tmp_path / "fixture-capture"
    _write_capture_frames(capture_dir)

    camera = OfflineCaptureCamera(
        capture_dir=capture_dir,
        profile_name="measurement",
        device_roi=DeviceRoiConfig(x=2, y=1, width=3, height=2),
    )

    frame = camera.read_frame()

    assert frame.image.shape == (2, 3)
    assert np.array_equal(frame.image, np.array([[8, 9, 10], [14, 15, 16]], dtype=np.uint8))
    assert frame.meta["device_roi"] == {"x": 2, "y": 1, "width": 3, "height": 2}
    assert frame.meta["source_width"] == 6
    assert frame.meta["source_height"] == 4
