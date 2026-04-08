import math
from pathlib import Path
import time
import json

from fastapi.testclient import TestClient
from openpyxl import Workbook
import pytest

from src.camera.mock_camera import MockCamera
from src.core.config_models import DeviceRoiConfig
from src.core.models import FramePacket
from src.curve.afas_postprocessing_analysis import analyze_preprocessed_afas_channel
from src.curve.afas_preprocessing import preprocess_afas_channel
from src.temp.mock_temp import MockTempController
from src.workflow.live_run import MockLiveMetricSource
from src.webapp.app import create_app
from src.webapp.deps import LivePreviewService, PreviewStateSnapshot


class ReadFailingTempController(MockTempController):
    def __init__(self) -> None:
        super().__init__()
        self._read_count = 0

    def read(self):
        self._read_count += 1
        if self._read_count >= 2:
            raise RuntimeError("temp read failed")
        return super().read()


class IncrementingPreviewCamera:
    def __init__(self) -> None:
        self._frame_id = 0

    def read_frame(self) -> FramePacket:
        self._frame_id += 1
        return FramePacket(
            timestamp_ms=1_000 + self._frame_id,
            source="incrementing_preview_camera",
            image=[[0, 32], [64, 96]],
            frame_id=self._frame_id,
        )

    def close(self) -> None:
        return None


class NativePreviewImage:
    def __init__(self) -> None:
        self.bitmap_calls: list[tuple[int, int]] = []
        self.row_calls: list[tuple[int, int]] = []

    def downsample_bitmap_payload(self, *, max_width: int = 640, max_height: int = 480) -> tuple[int, int, bytes]:
        self.bitmap_calls.append((max_width, max_height))
        return (2, 2, bytes([1, 2, 3, 4]))

    def downsample_rows(self, *, max_width: int = 640, max_height: int = 480) -> list[list[int]]:
        self.row_calls.append((max_width, max_height))
        raise AssertionError("native preview image should prefer the bitmap fast path")

    def __len__(self) -> int:
        raise AssertionError("native preview image should not be normalized through the generic path")

    def __getitem__(self, index):
        raise AssertionError("native preview image should not be normalized through the generic path")


def _make_rotated_roi_fixture_frame() -> FramePacket:
    width = 96
    height = 64
    image = [[240 for _ in range(width)] for _ in range(height)]
    center_x = 48
    center_y = 32
    angle_deg = 82.0
    angle_rad = math.radians(angle_deg)
    for local_x in range(-4, 5):
        for local_y in range(-18, 19):
            world_x = int(round(center_x + local_x * math.cos(angle_rad) - local_y * math.sin(angle_rad)))
            world_y = int(round(center_y + local_x * math.sin(angle_rad) + local_y * math.cos(angle_rad)))
            if 0 <= world_x < width and 0 <= world_y < height:
                image[world_y][world_x] = 24
    return FramePacket(timestamp_ms=2_000, source="rotated_roi_fixture", image=image, frame_id=7)


def _make_app(tmp_path: Path):
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    _configure_mock_afas_curve_sample(app, tmp_path)
    app.state.live_run_service = app.state.application_container.build_live_run_service(
        preview_service=app.state.live_preview_service
    )
    return app


def _make_client(tmp_path: Path) -> TestClient:
    return TestClient(_make_app(tmp_path))


def _mock_definition_payload() -> dict[str, object]:
    return {
        "analysis_roi": {"x": 0, "y": 0, "width": 96, "height": 64},
        "metric_box": {"center_x": 48, "center_y": 32, "width": 80, "height": 24, "angle_deg": 0.0},
        "point_a_px": {"x": 12, "y": 32},
        "point_b_px": {"x": 83, "y": 32},
        "observation_axis": "long_axis",
        "foreground_polarity": "dark_on_light",
        "threshold_mode": "adaptive",
        "ignore_internal_texture": True,
        "min_target_area_px": 150,
    }


def _confirm_temperature_settings(
    client: TestClient,
    run_id: str,
    *,
    target_temperature_celsius: float = 45.0,
    output_power_percent: float = 100.0,
) -> dict[str, object]:
    response = client.put(
        f"/api/runs/{run_id}/temperature-settings",
        json={
            "target_temperature_celsius": target_temperature_celsius,
            "control_mode": "manual",
            "output_power_percent": output_power_percent,
        },
    )
    assert response.status_code == 200
    return response.json()


def _configure_mock_afas_curve_sample(app, tmp_path: Path, *, rows: list[tuple[float, float]] | None = None) -> Path:
    workbook_path = tmp_path / "mock_afas_curve.xlsx"
    _write_mock_afas_curve_workbook(workbook_path, rows=rows)
    app.state.runtime_config.replay["mock_afas_curve_path"] = str(workbook_path)
    return workbook_path


def _write_mock_afas_curve_workbook(path: Path, *, rows: list[tuple[float, float]] | None = None) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    for temperature_celsius, value in rows or _default_mock_afas_curve_rows():
        sheet.append((temperature_celsius, value))
    workbook.save(path)


def _default_mock_afas_curve_rows() -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    for index in range(60):
        progress = index / 59.0
        temperature_celsius = round(-5.0 + index * 0.5, 2)
        curve_progress = progress * progress * (3.0 - 2.0 * progress)
        value = round(38.0 + 35.0 * curve_progress, 3)
        rows.append((temperature_celsius, value))
    return rows


def _build_expected_afas_dataset(rows: list[tuple[float, float]]) -> dict[str, object]:
    return {
        "schema_version": "afas_postprocessing_dataset.v1",
        "session_id": "expected-mock-afas",
        "active_channel": "Space1",
        "channel_map": {
            "Space1": {
                "temperature_celsius": [float(temperature_celsius) for temperature_celsius, _ in rows],
                "values": [float(value) for _, value in rows],
                "timestamps_ms": [1_000 + index for index in range(len(rows))],
                "metric_norm": [None] * len(rows),
                "quality": [0.99] * len(rows),
                "point_a_px": [None] * len(rows),
                "point_b_px": [None] * len(rows),
            }
        },
        "preprocessing_defaults": {
            "group_by_temperature": True,
            "outlier_window": 11,
            "outlier_threshold": 5.0,
            "outlier_max_iterations": 3,
            "savgol_window_length": 51,
            "savgol_polyorder": 3,
        },
        "analysis_defaults": {
            "low_range_celsius": None,
            "high_range_celsius": None,
            "tangent_offset": 0,
        },
    }


def _create_ready_run(
    client: TestClient,
    *,
    target_temperature_celsius: float = 45.0,
    output_power_percent: float = 100.0,
) -> str:
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]
    response = client.put(f"/api/runs/{run_id}/definition", json=_mock_definition_payload())
    assert response.status_code == 200
    assert response.json()["status"] == "definition_editing"
    temp_response = _confirm_temperature_settings(
        client,
        run_id,
        target_temperature_celsius=target_temperature_celsius,
        output_power_percent=output_power_percent,
    )
    assert temp_response["status"] == "run_ready"
    return run_id


def _wait_for_run_status(client: TestClient, run_id: str, expected_status: str, timeout_s: float = 3.0) -> dict[str, object]:
    deadline = time.time() + timeout_s
    last_payload: dict[str, object] | None = None
    while time.time() < deadline:
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        last_payload = response.json()
        if last_payload["status"] == expected_status:
            return last_payload
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not reach {expected_status}; last payload={last_payload}")


def test_create_run_returns_summary(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.post("/api/runs", json={"preset": "balloon"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"].startswith("run-")
    assert payload["status"] == "created"
    assert payload["profile"] == "dev_mock"
    assert payload["preset"] == "balloon"


def test_get_run_returns_saved_draft_without_definition(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "guidewire"})
    run_id = created.json()["run_id"]

    response = client.get(f"/api/runs/{run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["preset"] == "guidewire"
    assert payload["definition"] is None
    assert payload["definition_complete"] is False
    assert payload["capture_mode"] == "idle"
    assert payload["rates"]["measurement_sample_hz"] is None
    assert payload["rates"]["artifact_capture_hz"] is None
    assert payload["measurement_profile"]["acquisition_roi"] is None
    assert payload["measurement_profile"]["exposure_us"] == 10000
    assert payload["preview"] == {
        "stream_active": False,
        "frozen_frame_available": False,
        "last_frame_id": None,
    }
    assert payload["editor"] == {"state": "empty"}
    assert payload["created_at_ms"] <= payload["updated_at_ms"]


def test_get_run_returns_404_for_missing_draft(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.get("/api/runs/missing-run")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found: missing-run"}


def test_put_definition_saves_measurement_definition_and_waits_for_temperature_confirmation(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    response = client.put(
        f"/api/runs/{run_id}/definition",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 1280, "height": 720},
            "metric_box": {"center_x": 640, "center_y": 360, "width": 900, "height": 120, "angle_deg": 12.0},
            "point_a_px": {"x": 210, "y": 320},
            "point_b_px": {"x": 980, "y": 402},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 200,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["status"] == "definition_editing"
    assert payload["definition_complete"] is True
    assert payload["editor"] == {"state": "locked"}
    assert payload["temperature_settings"] is None
    assert payload["temperature_settings_confirmed"] is False
    assert payload["definition"]["metric_box"]["angle_deg"] == 12.0
    assert payload["definition"]["observation_axis"] == "long_axis"
    assert payload["definition"]["point_a_px"] == {"x": 210, "y": 320}


def test_put_definition_rejects_invalid_payload_with_422(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    response = client.put(
        f"/api/runs/{run_id}/definition",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 1280, "height": 720},
            "metric_box": {"center_x": 640, "center_y": 360, "width": 0, "height": 120, "angle_deg": 12.0},
            "point_a_px": {"x": 210, "y": 320},
            "point_b_px": {"x": 210, "y": 320},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 200,
        },
    )

    assert response.status_code == 422


def test_put_definition_accepts_tight_rotated_window_near_roi_boundary(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "guidewire"})
    run_id = created.json()["run_id"]

    response = client.put(
        f"/api/runs/{run_id}/definition",
        json={
            "analysis_roi": {"x": 14, "y": 18, "width": 70, "height": 17},
            "metric_box": {"center_x": 49, "center_y": 29, "width": 71, "height": 2, "angle_deg": 8.24632081446853},
            "point_a_px": {"x": 14, "y": 24},
            "point_b_px": {"x": 83, "y": 34},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 50,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "definition_editing"


def test_put_temperature_settings_confirms_bundle_and_advances_ready_status(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]
    definition_response = client.put(f"/api/runs/{run_id}/definition", json=_mock_definition_payload())

    assert definition_response.status_code == 200
    assert definition_response.json()["status"] == "definition_editing"

    response = client.put(
        f"/api/runs/{run_id}/temperature-settings",
        json={
            "target_temperature_celsius": 37.5,
            "control_mode": "manual",
            "output_power_percent": 68.0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "run_ready"
    assert payload["temperature_settings_confirmed"] is True
    assert payload["temperature_settings"]["target_temperature_celsius"] == 37.5
    assert payload["temperature_settings"]["control_mode"] == "manual"
    assert payload["temperature_settings"]["output_power_percent"] == 68.0
    assert payload["temperature_settings"]["confirmed_target_temperature_celsius"] == 37.5
    assert payload["temperature_settings"]["confirmed_at_ms"] > 0
    assert payload["temperature_settings"]["source"]


def test_preview_frame_returns_png_and_marks_definition_editing_with_frozen_frame(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    response = client.post(f"/api/runs/{run_id}/preview/frame")
    detail_response = client.get(f"/api/runs/{run_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.headers["x-frame-source-width"] == "96"
    assert response.headers["x-frame-source-height"] == "64"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "definition_editing"
    assert detail_response.json()["capture_mode"] == "setup_preview"
    assert detail_response.json()["preview"]["stream_active"] is False
    assert detail_response.json()["preview"]["frozen_frame_available"] is True
    assert detail_response.json()["editor"] == {"state": "editing"}


def test_preview_frame_uses_setup_preview_camera_profile(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]
    profile_names: list[str] = []
    original_open_camera = app.state.live_preview_service.open_camera

    def wrapped_open_camera(runtime_config, *, profile_name: str = "setup_preview"):
        profile_names.append(profile_name)
        return original_open_camera(runtime_config, profile_name=profile_name)

    app.state.live_preview_service.open_camera = wrapped_open_camera

    response = client.post(f"/api/runs/{run_id}/preview/frame")

    assert response.status_code == 200
    assert profile_names == ["setup_preview"]


def test_preview_frame_refreshes_with_new_capture_by_default(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    preview_camera = IncrementingPreviewCamera()
    app.state.live_preview_service.open_camera = lambda runtime_config, *, profile_name="setup_preview": preview_camera
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]

    first = client.post(f"/api/runs/{run_id}/preview/frame")
    second = client.post(f"/api/runs/{run_id}/preview/frame")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers["X-Frame-Id"] == "1"
    assert second.headers["X-Frame-Id"] == "2"


def test_preview_frame_cached_query_reuses_frozen_frame(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    preview_camera = IncrementingPreviewCamera()
    app.state.live_preview_service.open_camera = lambda runtime_config, *, profile_name="setup_preview": preview_camera
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]

    first = client.post(f"/api/runs/{run_id}/preview/frame")
    cached = client.post(f"/api/runs/{run_id}/preview/frame?cached=1")

    assert first.status_code == 200
    assert cached.status_code == 200
    assert first.headers["X-Frame-Id"] == "1"
    assert cached.headers["X-Frame-Id"] == "1"


def test_preview_frame_tracking_query_uses_cached_measurement_frame_without_marking_frozen(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]
    app.state.live_preview_service.cache_tracking_frame(
        run_id=run_id,
        frame=FramePacket(
            timestamp_ms=1234,
            source="measurement_camera",
            image=[[0, 32], [64, 96]],
            frame_id=9,
        ),
    )

    response = client.post(f"/api/runs/{run_id}/preview/frame?cached=1&tracking=1")
    detail_response = client.get(f"/api/runs/{run_id}")

    assert response.status_code == 200
    assert response.headers["X-Frame-Id"] == "9"
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "created"
    assert detail_response.json()["preview"]["frozen_frame_available"] is False
    assert detail_response.json()["editor"] == {"state": "empty"}


def test_preview_stream_returns_multipart_jpeg_and_marks_preview_ready(tmp_path: Path) -> None:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    preview_service = app.state.live_preview_service

    def fake_start_stream(runtime_config, *, run_id):
        return object(), FramePacket(
            timestamp_ms=123,
            source="mock_camera",
            image=[[0, 32], [64, 96]],
            frame_id=7,
        )

    def fake_stream_frames(active_stream, *, first_frame, frame_interval_ms):
        yield first_frame

    preview_service.start_stream = fake_start_stream
    preview_service.stream_frames = fake_stream_frames
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    with client.stream("GET", f"/api/runs/{run_id}/preview/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
        chunks = bytearray()
        for chunk in response.iter_bytes():
            chunks.extend(chunk)
            if b"\xff\xd8\xff" in chunks:
                break

    detail_response = client.get(f"/api/runs/{run_id}")

    assert b"--frame" in chunks
    assert b"Content-Type: image/jpeg" in chunks
    assert b"X-Frame-Width" not in chunks
    assert b"X-Frame-Height" not in chunks
    assert b"X-Frame-Id" not in chunks
    assert b"\xff\xd8\xff" in chunks
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "preview_ready"
    assert detail_response.json()["capture_mode"] == "setup_preview"
    assert detail_response.json()["preview"]["stream_active"] is False
    assert detail_response.json()["preview"]["frozen_frame_available"] is True
    assert detail_response.json()["editor"] == {"state": "editing"}


def test_preview_frame_prefers_native_downsample_fast_path(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]
    image = NativePreviewImage()

    def fake_fetch_frame(runtime_config, *, run_id: str = "", prefer_cached: bool = False):
        return FramePacket(
            timestamp_ms=123,
            source="fast_preview_camera",
            image=image,
            frame_id=9,
        )

    app.state.live_preview_service.fetch_frame = fake_fetch_frame

    response = client.post(f"/api/runs/{run_id}/preview/frame")

    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert response.headers["x-frame-source-width"] == "2"
    assert response.headers["x-frame-source-height"] == "2"
    assert image.bitmap_calls == [(640, 480)]
    assert image.row_calls == []


def test_preview_stream_prefers_native_downsample_fast_path(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]
    image = NativePreviewImage()

    def fake_start_stream(runtime_config, *, run_id):
        return object(), FramePacket(
            timestamp_ms=123,
            source="fast_preview_camera",
            image=image,
            frame_id=7,
        )

    def fake_stream_frames(active_stream, *, first_frame, frame_interval_ms):
        yield first_frame

    app.state.live_preview_service.start_stream = fake_start_stream
    app.state.live_preview_service.stream_frames = fake_stream_frames

    with client.stream("GET", f"/api/runs/{run_id}/preview/stream") as response:
        assert response.status_code == 200
        chunks = bytearray()
        for chunk in response.iter_bytes():
            chunks.extend(chunk)
            if b"\xff\xd8\xff" in chunks:
                break

    assert b"\xff\xd8\xff" in chunks
    assert b"X-Frame-Width" not in chunks
    assert image.bitmap_calls == [(640, 480)]
    assert image.row_calls == []


def test_preview_stream_uses_runtime_preview_display_size(tmp_path: Path) -> None:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    app.state.runtime_config.live.run.preview_display_max_width = 768
    app.state.runtime_config.live.run.preview_display_max_height = 512
    preview_service = app.state.live_preview_service

    image = NativePreviewImage()

    def fake_start_stream(runtime_config, *, run_id):
        return object(), FramePacket(
            timestamp_ms=123,
            source="fast_preview_camera",
            image=image,
            frame_id=7,
        )

    def fake_stream_frames(active_stream, *, first_frame, frame_interval_ms):
        yield first_frame

    preview_service.start_stream = fake_start_stream
    preview_service.stream_frames = fake_stream_frames
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]

    with client.stream("GET", f"/api/runs/{run_id}/preview/stream") as response:
        assert response.status_code == 200
        for chunk in response.iter_bytes():
            if b"\xff\xd8\xff" in chunk:
                break

    assert image.bitmap_calls == [(768, 512)]
    assert image.row_calls == []


def test_live_preview_service_stream_frames_prefers_latest_frame_when_camera_outpaces_display() -> None:
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
    active_stream, first_frame = service.start_stream(object(), run_id="run-latest")

    frame_ids: list[int] = []
    for frame in service.stream_frames(
        active_stream,
        first_frame=first_frame,
        frame_interval_ms=60,
    ):
        frame_ids.append(int(frame.frame_id or 0))
        if len(frame_ids) >= 3:
            service.stop_stream(run_id="run-latest")

    assert frame_ids[0] == 1
    assert frame_ids[1] > 2
    assert frame_ids[2] > frame_ids[1]
    assert camera.closed is True


def test_stop_preview_stream_returns_detail_and_keeps_frozen_frame(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]
    preview_response = client.post(f"/api/runs/{run_id}/preview/frame")
    assert preview_response.status_code == 200

    response = client.post(f"/api/runs/{run_id}/preview/stream/stop")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "definition_editing"
    assert payload["capture_mode"] == "setup_preview"
    assert payload["preview"]["stream_active"] is False
    assert payload["preview"]["frozen_frame_available"] is True
    assert payload["editor"] == {"state": "editing"}


def test_stop_preview_stream_force_releases_timed_out_stream(tmp_path: Path) -> None:
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    preview_service = app.state.live_preview_service
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    force_calls: list[str] = []
    wait_calls: list[int] = []

    def fake_stop_stream(*, run_id: str) -> bool:
        return True

    def fake_wait_for_stream_stop(*, run_id: str, timeout_ms: int = 1_000) -> bool:
        wait_calls.append(timeout_ms)
        return len(wait_calls) > 1

    def fake_force_stop_stream(*, run_id: str) -> bool:
        force_calls.append(run_id)
        return True

    def fake_get_preview_state(*, run_id: str) -> PreviewStateSnapshot:
        return PreviewStateSnapshot(
            stream_active=False,
            frozen_frame_available=True,
            last_frame_id=7,
            preview_display_fps=7.5,
        )

    preview_service.stop_stream = fake_stop_stream
    preview_service.wait_for_stream_stop = fake_wait_for_stream_stop
    preview_service.force_stop_stream = fake_force_stop_stream
    preview_service.get_preview_state = fake_get_preview_state

    response = client.post(f"/api/runs/{run_id}/preview/stream/stop")

    assert response.status_code == 200
    assert force_calls == [run_id]
    assert wait_calls == [3_000, 250]
    assert response.json()["preview"]["frozen_frame_available"] is True
    assert response.json()["rates"]["preview_display_fps"] == 7.5


def test_get_run_detail_exposes_preview_display_fps_from_preview_state(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    app.state.live_preview_service.get_preview_state = lambda *, run_id: PreviewStateSnapshot(
        stream_active=True,
        frozen_frame_available=False,
        last_frame_id=3,
        preview_display_fps=8.4,
    )

    response = client.get(f"/api/runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["rates"]["preview_display_fps"] == 8.4


def test_auto_detect_definition_returns_suggested_points_for_mock_preview(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 96, "height": 64},
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 150,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["point_a_px"]["x"] < payload["point_b_px"]["x"]
    assert payload["quality"] > 0.75
    assert payload["metric_raw"] is not None


def test_auto_detect_definition_accepts_metric_box_that_slightly_exceeds_axis_aligned_roi(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 9, "y": 21, "width": 78, "height": 22},
            "metric_box": {"center_x": 48, "center_y": 32, "width": 80, "height": 24, "angle_deg": 0.0},
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 150,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["point_a_px"]["x"] < payload["point_b_px"]["x"]
    assert payload["metric_raw"] is not None


def test_auto_detect_definition_accepts_tight_rotated_metric_box_near_roi_boundary(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]
    frame = _make_rotated_roi_fixture_frame()

    def fake_fetch_frame(runtime_config, *, run_id: str = "", prefer_cached: bool = False):
        return frame

    app.state.live_preview_service.fetch_frame = fake_fetch_frame

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 24, "y": 12, "width": 48, "height": 40},
            "metric_box": {"center_x": 48, "center_y": 32, "width": 18, "height": 40, "angle_deg": 82.0},
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "binary",
            "ignore_internal_texture": True,
            "min_target_area_px": 20,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["point_a_px"]["x"] != payload["point_b_px"]["x"] or payload["point_a_px"]["y"] != payload["point_b_px"]["y"]
    assert payload["metric_raw"] is not None


def test_invalid_definition_does_not_overwrite_saved_locked_definition(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    run_id = _create_ready_run(client)

    response = client.put(
        f"/api/runs/{run_id}/definition",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 96, "height": 64},
            "metric_box": {"center_x": 48, "center_y": 32, "width": 80, "height": 24, "angle_deg": 0.0},
            "point_a_px": {"x": 12, "y": 32},
            "point_b_px": {"x": 12, "y": 32},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 150,
        },
    )
    detail_response = client.get(f"/api/runs/{run_id}")

    assert response.status_code == 422
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "run_ready"
    assert detail_response.json()["definition"]["point_a_px"] == {"x": 12, "y": 32}
    assert detail_response.json()["definition"]["point_b_px"] == {"x": 83, "y": 32}


def test_put_definition_rejects_points_outside_analysis_roi(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    response = client.put(
        f"/api/runs/{run_id}/definition",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 100, "height": 100},
            "metric_box": {"center_x": 50, "center_y": 50, "width": 60, "height": 20, "angle_deg": 0.0},
            "point_a_px": {"x": 10, "y": 10},
            "point_b_px": {"x": 150, "y": 10},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 50,
        },
    )

    assert response.status_code == 422


def test_put_definition_rejects_points_outside_metric_box(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    response = client.put(
        f"/api/runs/{run_id}/definition",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 200, "height": 120},
            "metric_box": {"center_x": 80, "center_y": 50, "width": 40, "height": 20, "angle_deg": 0.0},
            "point_a_px": {"x": 20, "y": 50},
            "point_b_px": {"x": 120, "y": 50},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 50,
        },
    )

    assert response.status_code == 422


def test_create_app_mounts_live_run_router(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    response = client.post("/api/runs", json={"preset": "balloon"})

    assert response.status_code == 200


def test_start_live_run_completes_and_persists_result_bundle(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    run_id = _create_ready_run(client)
    expected_rows = _default_mock_afas_curve_rows()

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    detail_payload = _wait_for_run_status(client, run_id, "completed")
    telemetry_response = client.get(f"/api/runs/{run_id}/telemetry")
    result_response = client.get(f"/api/runs/{run_id}/result")
    session_response = client.get(f"/api/session/{run_id}")
    session_detail_response = client.get(f"/api/session/{run_id}/detail")

    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["run_id"] == run_id
    assert start_payload["session_id"] == run_id
    assert start_payload["status"] == "running"
    assert start_payload["point_count"] is None
    assert start_payload["af95"] is None

    assert detail_payload["status"] == "completed"
    assert detail_payload["capture_mode"] == "post_run_review"
    assert detail_payload["rates"]["measurement_sample_hz"] is not None
    assert detail_payload["rates"]["artifact_capture_hz"] is not None

    assert telemetry_response.status_code == 200
    telemetry_payload = telemetry_response.json()
    assert telemetry_payload["status"] == "completed"
    assert len(telemetry_payload["curve"]) == len(expected_rows)
    assert telemetry_payload["latest"]["space1_px"] >= telemetry_payload["curve"][0]["space1_px"]
    assert telemetry_payload["latest"]["sample_index"] is not None
    assert telemetry_payload["latest"]["frame_id"] is not None
    assert telemetry_payload["latest"]["frame_timestamp_ms"] is not None
    assert telemetry_payload["latest"]["point_a_px"] is not None
    assert telemetry_payload["latest"]["point_b_px"] is not None
    assert telemetry_payload["curve"][1]["sample_interval_ms"] is not None
    temp_response = client.get("/api/system/temp/current")
    assert temp_response.status_code == 200
    assert temp_response.json()["temperature_celsius"] == telemetry_payload["latest"]["temperature_celsius"]
    assert telemetry_payload["curve"][0]["temperature_celsius"] == expected_rows[0][0]
    assert telemetry_payload["curve"][0]["space1_px"] == expected_rows[0][1]
    assert telemetry_payload["latest"]["temperature_celsius"] == expected_rows[-1][0]
    assert telemetry_payload["latest"]["space1_px"] == expected_rows[-1][1]

    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["session_id"] == run_id
    assert result_payload["state"] == "completed"
    assert result_payload["result_status"] == "ok"
    assert result_payload["af95"] is not None
    assert result_payload["as_value"] is not None
    assert result_payload["af_value"] is not None
    assert result_payload["capture_mode"] == "post_run_review"
    assert result_payload["rates"]["measurement_sample_hz"] is not None
    assert result_payload["rates"]["artifact_capture_hz"] == result_payload["rates"]["measurement_sample_hz"]
    assert result_payload["measurement_profile"]["exposure_us"] == 10000
    assert result_payload["warnings"] == []
    assert result_payload["artifacts"]["telemetry"] == "telemetry.csv"
    assert result_payload["artifacts"]["afas_dataset"] == "afas_dataset.json"
    assert result_payload["artifacts"]["keyframes"]

    assert session_response.status_code == 200
    assert session_response.json()["session_id"] == run_id
    assert session_response.json()["state"] == "completed"

    assert session_detail_response.status_code == 200
    assert session_detail_response.json()["source"] == "live_run"
    assert session_detail_response.json()["point_count"] >= 3

    session_dir = tmp_path / "artifacts" / run_id
    assert (session_dir / "definition.json").exists()
    assert (session_dir / "telemetry.csv").exists()
    assert (session_dir / "events.jsonl").exists()
    assert (session_dir / "result.json").exists()
    assert (session_dir / "afas_dataset.json").exists()
    assert (session_dir / "keyframes").exists()


def test_creating_a_new_mock_run_resets_shared_temperature_state(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    first_run_id = _create_ready_run(client)
    expected_rows = _default_mock_afas_curve_rows()

    start_response = client.post(
        f"/api/runs/{first_run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    _wait_for_run_status(client, first_run_id, "completed")

    assert start_response.status_code == 200
    temp_after_run = client.get("/api/system/temp/current")
    assert temp_after_run.status_code == 200
    assert temp_after_run.json()["temperature_celsius"] == expected_rows[-1][0]

    second_run = client.post("/api/runs", json={"preset": "balloon"})
    assert second_run.status_code == 200

    reset_temp = client.get("/api/system/temp/current")
    assert reset_temp.status_code == 200
    assert reset_temp.json()["temperature_celsius"] == expected_rows[0][0]


def test_start_live_run_uses_measurement_camera_profile(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    profile_names: list[str] = []

    def wrapped_open_camera(runtime_config, *, profile_name: str = "setup_preview"):
        profile_names.append(profile_name)
        return MockCamera(profile_name=profile_name)

    app.state.live_run_service.preview_service.open_camera = wrapped_open_camera
    client = TestClient(app)
    run_id = _create_ready_run(client)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    _wait_for_run_status(client, run_id, "completed")

    assert start_response.status_code == 200
    assert profile_names == ["measurement"]


def test_start_live_run_reduces_measurement_camera_roi_for_real_camera_profile(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.state.runtime_config.adapters["camera"] = "hik_gige_mvs"
    app.state.runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig(
        x=512,
        y=342,
        width=2048,
        height=1364,
    )
    app.state.runtime_config.live.camera.measurement.device_roi = DeviceRoiConfig(
        x=512,
        y=342,
        width=2048,
        height=1364,
    )
    captured: dict[str, object] = {}

    def wrapped_open_camera(runtime_config, *, profile_name: str = "setup_preview"):
        if profile_name == "measurement":
            roi = runtime_config.live.camera.measurement.device_roi
            captured["measurement_roi"] = {
                "x": roi.x,
                "y": roi.y,
                "width": roi.width,
                "height": roi.height,
            }
        return MockCamera(profile_name=profile_name)

    def wrapped_build_metric_source(*, runtime_config, definition, target_temperature_celsius: float):
        captured["metric_definition"] = definition
        return MockLiveMetricSource(
            definition=definition,
            target_temperature_celsius=target_temperature_celsius,
        )

    app.state.live_run_service.preview_service.open_camera = wrapped_open_camera
    app.state.live_run_service._build_metric_source = wrapped_build_metric_source
    app.state.live_run_service._temp_controller_factory = lambda: MockTempController()
    client = TestClient(app)
    run_id = _create_ready_run(client)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    completed_detail = _wait_for_run_status(client, run_id, "completed")
    result_response = client.get(f"/api/runs/{run_id}/result")

    assert start_response.status_code == 200
    assert captured["measurement_roi"] == {
        "x": 512,
        "y": 342,
        "width": 160,
        "height": 128,
    }
    metric_definition = captured["metric_definition"]
    assert metric_definition.analysis_roi.x == 0
    assert metric_definition.analysis_roi.y == 0
    assert completed_detail["measurement_profile"]["acquisition_roi"] == {
        "x": 512,
        "y": 342,
        "width": 160,
        "height": 128,
    }
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["artifacts"]["definition_original"] == "definition_original.json"
    assert result_payload["artifacts"]["definition_effective_local"] == "definition_effective_local.json"
    assert result_payload["artifacts"]["measurement_capture_plan"] == "measurement_capture_plan.json"
    session_dir = tmp_path / "artifacts" / run_id
    assert json.loads((session_dir / "definition_effective_local.json").read_text(encoding="utf-8"))["analysis_roi"] == {
        "x": 0,
        "y": 0,
        "width": 96,
        "height": 64,
    }


def test_failed_live_run_uses_effective_measurement_roi_and_runtime_definition_artifacts(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.state.runtime_config.adapters["camera"] = "hik_gige_mvs"
    app.state.runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig(
        x=512,
        y=342,
        width=2048,
        height=1364,
    )
    app.state.runtime_config.live.camera.measurement.device_roi = DeviceRoiConfig(
        x=512,
        y=342,
        width=2048,
        height=1364,
    )
    captured: dict[str, object] = {}

    def wrapped_open_camera(runtime_config, profile_name: str):
        if profile_name == "measurement":
            roi = runtime_config.live.camera.measurement.device_roi
            captured["measurement_roi"] = {
                "x": roi.x,
                "y": roi.y,
                "width": roi.width,
                "height": roi.height,
            }
        return MockCamera(profile_name=profile_name)

    def wrapped_build_metric_source(*, runtime_config, definition, target_temperature_celsius: float):
        captured["metric_definition"] = definition
        return MockLiveMetricSource(
            definition=definition,
            target_temperature_celsius=target_temperature_celsius,
        )

    app.state.live_run_service.preview_service.open_camera = wrapped_open_camera
    app.state.live_run_service._build_metric_source = wrapped_build_metric_source
    app.state.live_run_service._temp_controller_factory = lambda: ReadFailingTempController()
    client = TestClient(app)
    run_id = _create_ready_run(client)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    failed_detail = _wait_for_run_status(client, run_id, "failed")
    result_response = client.get(f"/api/runs/{run_id}/result")

    assert start_response.status_code == 200
    assert failed_detail["measurement_profile"]["acquisition_roi"] == {
        "x": 512,
        "y": 342,
        "width": 160,
        "height": 128,
    }
    assert captured["measurement_roi"] == failed_detail["measurement_profile"]["acquisition_roi"]
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["state"] == "failed"
    assert result_payload["artifacts"]["definition_original"] == "definition_original.json"
    assert result_payload["artifacts"]["definition_effective_local"] == "definition_effective_local.json"
    assert result_payload["artifacts"]["measurement_capture_plan"] == "measurement_capture_plan.json"
    session_dir = tmp_path / "artifacts" / run_id
    assert json.loads((session_dir / "measurement_capture_plan.json").read_text(encoding="utf-8")) == {
        "effective_acquisition_roi": {"x": 512, "y": 342, "width": 160, "height": 128},
        "effective_local_origin_in_setup_preview_px": {"x": 0, "y": 0},
        "setup_to_effective_local_translation_px": {"dx": 0, "dy": 0},
    }


def test_start_live_run_persists_explicit_unavailable_result_when_afas_curve_is_too_short(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    short_rows = [(5.0, 40.0), (7.5, 44.0), (10.0, 55.0)]
    _configure_mock_afas_curve_sample(app, tmp_path, rows=short_rows)
    client = TestClient(app)
    run_id = _create_ready_run(client, target_temperature_celsius=35.0)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 35.0},
    )
    completed_detail = _wait_for_run_status(client, run_id, "completed")
    result_response = client.get(f"/api/runs/{run_id}/result")

    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert completed_detail["status"] == "completed"
    assert completed_detail["rates"]["measurement_sample_hz"] is not None
    assert result_response.status_code == 200
    payload = result_response.json()
    assert payload["state"] == "completed"
    assert payload["result_status"] == "unavailable"
    assert payload["result_reason"] == "insufficient_points"
    assert payload["rates"]["measurement_sample_hz"] is not None
    assert payload["as_value"] is None
    assert payload["af_value"] is None


def test_start_live_run_workspace_afas_matches_direct_analysis_for_mock_curve_workbook(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    expected_rows = _default_mock_afas_curve_rows()
    client = TestClient(app)
    run_id = _create_ready_run(client)

    expected_dataset = _build_expected_afas_dataset(expected_rows)
    expected_preprocessing = preprocess_afas_channel(expected_dataset, channel_name="Space1")
    expected_analysis = analyze_preprocessed_afas_channel(expected_preprocessing)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    _wait_for_run_status(client, run_id, "completed")
    analysis_response = client.post(f"/api/session/{run_id}/afas/analysis", json={})
    dataset_response = client.get(f"/api/session/{run_id}/detail")

    assert start_response.status_code == 200
    assert analysis_response.status_code == 200
    payload = analysis_response.json()
    assert payload["active_channel"] == "Space1"
    assert payload["analysis"]["result_status"] == expected_analysis["result_status"]
    assert payload["analysis"]["result"]["As"] == pytest.approx(expected_analysis["result"]["As"])
    assert payload["analysis"]["result"]["Af_tan"] == pytest.approx(expected_analysis["result"]["Af_tan"])
    assert payload["analysis"]["result"]["max_slope_temp"] == pytest.approx(expected_analysis["result"]["max_slope_temp"])
    assert dataset_response.status_code == 200
    assert dataset_response.json()["point_count"] == len(expected_rows)


def test_start_live_run_exposes_cadence_warning_when_achieved_rate_is_below_target(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.state.runtime_config.live.run.measurement_target_hz = 50.0
    original_open_camera = app.state.live_preview_service.open_camera

    class SlowMeasurementCamera(MockCamera):
        def read_frame(self) -> FramePacket:
            time.sleep(0.03)
            return super().read_frame()

    def wrapped_open_camera(runtime_config, *, profile_name: str = "setup_preview"):
        if profile_name == "measurement":
            return SlowMeasurementCamera()
        return original_open_camera(runtime_config, profile_name=profile_name)

    app.state.live_preview_service.open_camera = wrapped_open_camera
    client = TestClient(app)
    run_id = _create_ready_run(client)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    completed_detail = _wait_for_run_status(client, run_id, "completed")
    result_response = client.get(f"/api/runs/{run_id}/result")

    assert start_response.status_code == 200
    assert len(completed_detail["warnings"]) == 1
    assert "measurement cadence below target:" in completed_detail["warnings"][0]
    assert "target 50.00 Hz" in completed_detail["warnings"][0]
    assert result_response.status_code == 200
    result_warnings = result_response.json()["warnings"]
    assert len(result_warnings) == 1
    assert "measurement cadence below target:" in result_warnings[0]
    assert "target 50.00 Hz" in result_warnings[0]


def test_start_live_run_rejects_invalid_transition_before_definition(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]

    response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": f"Run must be in run_ready before start: {run_id}"}


def test_get_live_run_result_returns_404_before_finalize(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    run_id = _create_ready_run(client)

    response = client.get(f"/api/runs/{run_id}/result")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Run result not available: {run_id}"}


def test_stop_live_run_rejects_when_run_is_not_running(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    run_id = _create_ready_run(client)

    response = client.post(f"/api/runs/{run_id}/stop")

    assert response.status_code == 409
    assert response.json() == {"detail": f"Run is not currently running: {run_id}"}


def test_stop_live_run_transitions_from_running_to_aborted(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.state.runtime_config.live.run.capture_interval_ms = 500
    client = TestClient(app)
    run_id = _create_ready_run(client)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    stop_response = client.post(f"/api/runs/{run_id}/stop")
    aborted_detail = _wait_for_run_status(client, run_id, "aborted")
    telemetry_response = client.get(f"/api/runs/{run_id}/telemetry")
    result_response = client.get(f"/api/runs/{run_id}/result")
    session_response = client.get(f"/api/session/{run_id}")
    session_detail_response = client.get(f"/api/session/{run_id}/detail")

    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopping"
    assert aborted_detail["status"] == "aborted"
    assert telemetry_response.status_code == 200
    assert telemetry_response.json()["status"] == "aborted"
    assert result_response.status_code == 200
    assert result_response.json()["state"] == "aborted"
    assert result_response.json()["result_status"] == "unavailable"
    assert session_response.status_code == 200
    assert session_response.json()["state"] == "aborted"
    assert session_detail_response.status_code == 200
    assert session_detail_response.json()["source"] == "live_run"


def test_manual_stop_only_mode_keeps_mock_run_running_until_stop(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.state.runtime_config.live.temp.control.completion_mode = "manual_stop_only"
    app.state.runtime_config.live.temp.control.mock_ramp_step_celsius = 100.0
    app.state.runtime_config.live.run.capture_interval_ms = 50
    client = TestClient(app)
    run_id = _create_ready_run(client, target_temperature_celsius=35.0)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 35.0},
    )
    time.sleep(0.25)
    running_detail = client.get(f"/api/runs/{run_id}")
    stop_response = client.post(f"/api/runs/{run_id}/stop")
    aborted_detail = _wait_for_run_status(client, run_id, "aborted")

    assert start_response.status_code == 200
    assert running_detail.status_code == 200
    assert running_detail.json()["status"] == "running"
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopping"
    assert aborted_detail["status"] == "aborted"


def test_start_live_run_marks_failed_when_temp_read_breaks_during_running(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    service = app.state.live_run_service
    service._build_temp_controller = lambda runtime_config: ReadFailingTempController()
    client = TestClient(app)
    run_id = _create_ready_run(client)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    failed_detail = _wait_for_run_status(client, run_id, "failed")
    telemetry_response = client.get(f"/api/runs/{run_id}/telemetry")
    result_response = client.get(f"/api/runs/{run_id}/result")

    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert failed_detail["status"] == "failed"
    assert telemetry_response.status_code == 200
    assert telemetry_response.json()["status"] == "failed"
    assert len(telemetry_response.json()["curve"]) == 1
    assert result_response.status_code == 200
    assert result_response.json()["state"] == "failed"
    assert result_response.json()["result_status"] == "unavailable"


def test_start_live_run_marks_failed_when_finalize_breaks(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    service = app.state.live_run_service

    def failing_save_live_bundle(*args, **kwargs):
        raise RuntimeError("artifact finalize failed")

    service.artifact_store.save_live_bundle = failing_save_live_bundle
    client = TestClient(app)
    run_id = _create_ready_run(client)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    failed_detail = _wait_for_run_status(client, run_id, "failed")
    telemetry_response = client.get(f"/api/runs/{run_id}/telemetry")
    result_response = client.get(f"/api/runs/{run_id}/result")

    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert failed_detail["status"] == "failed"
    assert telemetry_response.status_code == 200
    assert telemetry_response.json()["status"] == "failed"
    assert result_response.status_code == 404
