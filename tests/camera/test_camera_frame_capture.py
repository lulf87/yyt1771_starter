import json

import numpy as np

from src.camera.camera_frame_capture import CaptureOptions, capture_frames
from src.core.models import FramePacket, TempReading


class FakeCamera:
    def __init__(self, frames: list[FramePacket]) -> None:
        self.frames = list(frames)
        self.closed = False

    def read_frame(self) -> FramePacket:
        if not self.frames:
            raise RuntimeError("no more frames")
        return self.frames.pop(0)

    def close(self) -> None:
        self.closed = True


class FakeTempReader:
    def __init__(self, readings: list[TempReading]) -> None:
        self.readings = list(readings)
        self.closed = False

    def read(self) -> TempReading:
        if not self.readings:
            raise RuntimeError("no more readings")
        return self.readings.pop(0)

    def close(self) -> None:
        self.closed = True


def test_capture_frames_writes_gray_npy_frames_and_manifest(tmp_path) -> None:
    camera = FakeCamera(
        [
            FramePacket(
                timestamp_ms=100,
                source="fake_camera",
                frame_id=7,
                image=np.array([[0, 20], [40, 255]], dtype=np.uint8),
                meta={"device_roi": {"x": 10, "y": 20, "width": 2, "height": 2}},
            ),
            FramePacket(
                timestamp_ms=150,
                source="fake_camera",
                frame_id=8,
                image=np.array([[1, 2], [3, 4]], dtype=np.uint8),
                meta={"device_roi": {"x": 10, "y": 20, "width": 2, "height": 2}},
            ),
        ]
    )

    summary = capture_frames(
        camera,
        CaptureOptions(
            output_dir=tmp_path,
            profile="dev_lab",
            camera_profile="measurement",
            frame_format="npy",
            save_video=False,
            max_frames=2,
        ),
    )

    assert summary.frame_count == 2
    assert np.load(tmp_path / "frames" / "frame_000001.npy").tolist() == [[0, 20], [40, 255]]
    assert np.load(tmp_path / "frames" / "frame_000002.npy").tolist() == [[1, 2], [3, 4]]
    assert camera.closed is True

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["profile"] == "dev_lab"
    assert manifest["camera_profile"] == "measurement"
    assert manifest["frame_count"] == 2
    assert manifest["frames"][0]["timestamp_ms"] == 100
    assert manifest["frames"][0]["source"] == "fake_camera"
    assert manifest["frames"][0]["frame_id"] == 7
    assert manifest["frames"][0]["shape"] == [2, 2]
    assert manifest["frames"][0]["dtype"] == "uint8"
    assert manifest["frames"][0]["npy"] == "frames/frame_000001.npy"
    assert manifest["frames"][0]["camera_meta"]["device_roi"] == {
        "x": 10,
        "y": 20,
        "width": 2,
        "height": 2,
    }


def test_capture_frames_preserves_uint16_raw_npy_values(tmp_path) -> None:
    camera = FakeCamera(
        [
            FramePacket(
                timestamp_ms=100,
                source="fake_camera",
                image=np.array([[0, 1024], [4096, 65535]], dtype=np.uint16),
            )
        ]
    )

    capture_frames(
        camera,
        CaptureOptions(
            output_dir=tmp_path,
            profile="dev_lab",
            camera_profile="measurement",
            frame_format="npy",
            save_video=False,
            max_frames=1,
        ),
    )

    saved = np.load(tmp_path / "frames" / "frame_000001.npy")
    assert saved.dtype == np.uint16
    assert saved.tolist() == [[0, 1024], [4096, 65535]]


def test_capture_frames_records_temperature_csv_and_frame_metadata(tmp_path) -> None:
    camera = FakeCamera(
        [
            FramePacket(timestamp_ms=100, source="fake_camera", image=np.array([[1]], dtype=np.uint8)),
            FramePacket(timestamp_ms=120, source="fake_camera", image=np.array([[2]], dtype=np.uint8)),
        ]
    )
    temp_reader = FakeTempReader(
        [
            TempReading(timestamp_ms=101, celsius=-2.5, source="fake_temp"),
            TempReading(timestamp_ms=121, celsius=48.0, source="fake_temp"),
        ]
    )

    capture_frames(
        camera,
        CaptureOptions(
            output_dir=tmp_path,
            profile="dev_lab",
            camera_profile="measurement",
            frame_format="npy",
            save_video=False,
            max_frames=2,
        ),
        temp_reader=temp_reader,
    )

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["temperature_csv"] == "temperature.csv"
    assert manifest["frames"][0]["temperature"]["celsius"] == -2.5
    assert manifest["frames"][0]["temperature"]["sampled_this_frame"] is True
    assert manifest["frames"][1]["temperature"]["celsius"] == 48.0
    csv_text = (tmp_path / "temperature.csv").read_text(encoding="utf-8")
    assert "frame_index,camera_timestamp_ms,temp_timestamp_ms,celsius,source,sampled_this_frame,error" in csv_text
    assert "1,100,101,-2.5,fake_temp,1," in csv_text
    assert "2,120,121,48.0,fake_temp,1," in csv_text
    assert temp_reader.closed is True
