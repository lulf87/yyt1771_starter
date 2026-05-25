import math
from pathlib import Path
import time
import json

from fastapi.testclient import TestClient
import numpy as np
from openpyxl import Workbook
import pytest

from src.camera.mock_camera import MockCamera
from src.core.config_models import DeviceRoiConfig
from src.core.enums import ObservationAxis
from src.application.runtime_config import RuntimeConfig, WebAppConfig
from src.core.models import FramePacket, MetricBox, RectRegion, ShapeMetric
from src.curve.afas_postprocessing_analysis import analyze_preprocessed_afas_channel
from src.curve.afas_preprocessing import preprocess_afas_channel
from src.temp.mock_temp import MockTempController
from src.workflow.live_run import MockLiveMetricSource
from src.webapp.app import create_app
from src.webapp.deps import LivePreviewService, PreviewStateSnapshot
from src.webapp.routes.live_run import _best_auto_detect_metric
from src.webapp.schemas import AutoDetectDefinitionRequest


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


def _make_rotated_bright_sample_frame(
    *,
    width: int = 900,
    height: int = 540,
    metric_box: MetricBox,
) -> FramePacket:
    image = np.full((height, width), 40, dtype=np.uint8)
    angle_rad = math.radians(float(metric_box.angle_deg))
    for local_x in range(-250, 251):
        for local_y in range(-45, 46):
            world_x = int(round(metric_box.center_x + local_x * math.cos(angle_rad) - local_y * math.sin(angle_rad)))
            world_y = int(round(metric_box.center_y + local_x * math.sin(angle_rad) + local_y * math.cos(angle_rad)))
            if 0 <= world_x < width and 0 <= world_y < height:
                image[world_y][world_x] = 220
    return FramePacket(timestamp_ms=2_100, source="rotated_bright_sample_fixture", image=image, frame_id=8)


def _make_rotated_dark_sample_frame(
    *,
    width: int = 900,
    height: int = 540,
    metric_box: MetricBox,
) -> FramePacket:
    image = np.full((height, width), 240, dtype=np.uint8)
    angle_rad = math.radians(float(metric_box.angle_deg))
    for local_x in range(-250, 251):
        for local_y in range(-45, 46):
            world_x = int(round(metric_box.center_x + local_x * math.cos(angle_rad) - local_y * math.sin(angle_rad)))
            world_y = int(round(metric_box.center_y + local_x * math.sin(angle_rad) + local_y * math.cos(angle_rad)))
            if 0 <= world_x < width and 0 <= world_y < height:
                image[world_y][world_x] = 35
    return FramePacket(timestamp_ms=2_110, source="rotated_dark_sample_fixture", image=image, frame_id=9)


def _make_rotated_dark_wire_frame(
    *,
    width: int = 900,
    height: int = 1000,
    metric_box: MetricBox,
    wire_span_px: int = 250,
    wire_width_px: int = 5,
) -> FramePacket:
    image = np.full((height, width), 240, dtype=np.uint8)
    angle_rad = math.radians(float(metric_box.angle_deg))
    half_span = max(1, int(wire_span_px) // 2)
    half_width = max(1, int(wire_width_px) // 2)
    for local_x in range(-half_span, half_span + 1):
        for local_y in range(-half_width, half_width + 1):
            world_x = int(round(metric_box.center_x + local_x * math.cos(angle_rad) - local_y * math.sin(angle_rad)))
            world_y = int(round(metric_box.center_y + local_x * math.sin(angle_rad) + local_y * math.cos(angle_rad)))
            if 0 <= world_x < width and 0 <= world_y < height:
                image[world_y][world_x] = 35
    return FramePacket(timestamp_ms=2_120, source="rotated_dark_wire_fixture", image=image, frame_id=10)


def _point_local_x(box: MetricBox, point: tuple[int, int]) -> float:
    angle_rad = math.radians(float(box.angle_deg))
    return (float(point[0]) - float(box.center_x)) * math.cos(angle_rad) + (
        float(point[1]) - float(box.center_y)
    ) * math.sin(angle_rad)


def _point_inside_metric_box(box: dict[str, float], point: dict[str, int]) -> bool:
    angle_rad = math.radians(float(box["angle_deg"]))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = float(point["x"]) - float(box["center_x"])
    translated_y = float(point["y"]) - float(box["center_y"])
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return abs(local_x) <= float(box["width"]) / 2.0 and abs(local_y) <= float(box["height"]) / 2.0


def test_auto_detect_rotated_roi_prefers_sample_edges_over_full_metric_box() -> None:
    metric_box = MetricBox(center_x=450, center_y=270, width=700, height=240, angle_deg=-10.0)
    frame = _make_rotated_bright_sample_frame(metric_box=metric_box)
    payload = AutoDetectDefinitionRequest(
        analysis_roi={"x": 60, "y": 80, "width": 780, "height": 380},
        metric_box={
            "center_x": metric_box.center_x,
            "center_y": metric_box.center_y,
            "width": metric_box.width,
            "height": metric_box.height,
            "angle_deg": metric_box.angle_deg,
        },
        observation_axis="long_axis",
        foreground_polarity="light_on_dark",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=50,
        sensitivity=50.0,
    )
    runtime_config = RuntimeConfig(
        profile="test",
        platform="mac",
        mode="test",
        webapp=WebAppConfig(host="127.0.0.1", port=0),
        adapters={},
    )
    runtime_config.live.vision.edge_threshold = 20.0
    runtime_config.live.vision.quality_threshold = 0.75

    metric, _threshold_mode, _foreground_polarity = _best_auto_detect_metric(
        frame=frame,
        payload=payload,
        runtime_config=runtime_config,
    )

    assert metric.metric_raw is not None
    assert metric.point_a_px is not None
    assert metric.point_b_px is not None
    assert metric.metric_raw < metric_box.width * 0.8
    assert abs(_point_local_x(metric_box, metric.point_a_px)) < metric_box.width * 0.45
    assert abs(_point_local_x(metric_box, metric.point_b_px)) < metric_box.width * 0.45


def test_auto_detect_keeps_requested_dark_polarity_when_target_is_specific() -> None:
    metric_box = MetricBox(center_x=450, center_y=270, width=700, height=240, angle_deg=12.0)
    frame = _make_rotated_dark_sample_frame(metric_box=metric_box)
    payload = AutoDetectDefinitionRequest(
        analysis_roi={"x": 60, "y": 80, "width": 780, "height": 380},
        metric_box={
            "center_x": metric_box.center_x,
            "center_y": metric_box.center_y,
            "width": metric_box.width,
            "height": metric_box.height,
            "angle_deg": metric_box.angle_deg,
        },
        observation_axis="long_axis",
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=50,
        sensitivity=50.0,
    )
    runtime_config = RuntimeConfig(
        profile="test",
        platform="mac",
        mode="test",
        webapp=WebAppConfig(host="127.0.0.1", port=0),
        adapters={},
    )
    runtime_config.live.vision.edge_threshold = 20.0
    runtime_config.live.vision.quality_threshold = 0.75

    metric, _threshold_mode, foreground_polarity = _best_auto_detect_metric(
        frame=frame,
        payload=payload,
        runtime_config=runtime_config,
    )

    assert foreground_polarity == "dark_on_light"
    assert metric.metric_raw is not None
    assert metric.point_a_px is not None
    assert metric.point_b_px is not None
    assert metric.metric_raw < metric_box.width * 0.8


def test_directional_auto_detect_keeps_requested_dark_polarity_when_alternate_finds_background() -> None:
    metric_box = MetricBox(center_x=450, center_y=500, width=620, height=220, angle_deg=60.0)
    frame = _make_rotated_dark_wire_frame(metric_box=metric_box)
    payload = AutoDetectDefinitionRequest(
        analysis_roi={"x": 199, "y": 176, "width": 502, "height": 648},
        metric_box={
            "center_x": metric_box.center_x,
            "center_y": metric_box.center_y,
            "width": metric_box.width,
            "height": metric_box.height,
            "angle_deg": metric_box.angle_deg,
        },
        observation_axis="long_axis",
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=20,
        sensitivity=50.0,
        direction_angle_deg=metric_box.angle_deg,
    )
    runtime_config = RuntimeConfig(
        profile="test",
        platform="mac",
        mode="test",
        webapp=WebAppConfig(host="127.0.0.1", port=0),
        adapters={},
    )
    runtime_config.live.vision.edge_threshold = 20.0
    runtime_config.live.vision.quality_threshold = 0.75

    metric, _threshold_mode, foreground_polarity = _best_auto_detect_metric(
        frame=frame,
        payload=payload,
        runtime_config=runtime_config,
    )

    assert foreground_polarity == "dark_on_light"
    assert metric.metric_raw is not None
    assert metric.point_a_px is not None
    assert metric.point_b_px is not None
    assert metric.metric_raw < metric_box.width * 0.8


def _make_app(tmp_path: Path):
    app = create_app(profile="dev_mock")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    app.state.runtime_config.live.run.capture_interval_ms = 33
    app.state.runtime_config.live.run.measurement_target_hz = 30.0
    _configure_mock_afas_curve_sample(app, tmp_path)
    app.state.live_run_service = app.state.application_container.build_live_run_service(
        preview_service=app.state.live_preview_service
    )
    return app


def _make_client(tmp_path: Path) -> TestClient:
    return TestClient(_make_app(tmp_path))


def _make_locked_alignment_app(tmp_path: Path):
    app = create_app(profile="dev_lab_camera_mock_temp")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    app.state.live_run_service = app.state.application_container.build_live_run_service(
        preview_service=app.state.live_preview_service
    )
    return app


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


def _locked_alignment_definition_payload() -> dict[str, object]:
    payload = dict(_mock_definition_payload())
    payload.update(
        {
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": False,
            "min_target_area_px": 200,
        }
    )
    return payload


def _offset_definition_payload(*, x: int, y: int, width: int = 96, height: int = 64) -> dict[str, object]:
    return {
        "analysis_roi": {"x": x, "y": y, "width": width, "height": height},
        "metric_box": {
            "center_x": x + width // 2,
            "center_y": y + height // 2,
            "width": 80,
            "height": 24,
            "angle_deg": 0.0,
        },
        "point_a_px": {"x": x + 12, "y": y + height // 2},
        "point_b_px": {"x": x + width - 13, "y": y + height // 2},
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
    completion_mode: str | None = None,
) -> dict[str, object]:
    payload = {
        "target_temperature_celsius": target_temperature_celsius,
        "control_mode": "manual",
        "output_power_percent": output_power_percent,
    }
    if completion_mode is not None:
        payload["completion_mode"] = completion_mode
    response = client.put(
        f"/api/runs/{run_id}/temperature-settings",
        json=payload,
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
    definition_payload: dict[str, object] | None = None,
) -> str:
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]
    response = client.put(f"/api/runs/{run_id}/definition", json=definition_payload or _mock_definition_payload())
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


def _wait_for_run_status(client: TestClient, run_id: str, expected_status: str, timeout_s: float = 6.0) -> dict[str, object]:
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
    assert payload["rates"]["preview_target_fps"] == 8.0
    assert payload["rates"]["measurement_sample_hz"] is None
    assert payload["rates"]["measurement_target_hz"] == 30.0
    assert payload["rates"]["artifact_capture_hz"] is None
    assert payload["rates"]["artifact_target_hz"] == 5.0
    assert payload["measurement_profile"]["acquisition_roi"] == {
        "x": 512,
        "y": 342,
        "width": 2048,
        "height": 1364,
    }
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
            "direction_angle_deg": 12.0,
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
    assert payload["definition"]["direction_angle_deg"] == 12.0
    assert payload["definition"]["direction_projection_mode"] == "auto"
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


def test_put_definition_accepts_preview_rounded_rotated_edge_point(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    response = client.put(
        f"/api/runs/{run_id}/definition",
        json={
            "analysis_roi": {"x": 342, "y": 232, "width": 1364, "height": 900},
            "metric_box": {"center_x": 1024, "center_y": 683, "width": 1255, "height": 652, "angle_deg": 12.0},
            "point_a_px": {"x": 665, "y": 605},
            "point_b_px": {"x": 1639, "y": 814},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "otsu",
            "ignore_internal_texture": True,
            "min_target_area_px": 200,
            "sensitivity": 50,
            "direction_angle_deg": 12.0,
            "direction_projection_mode": "max_chord",
        },
    )

    assert response.status_code == 200
    assert response.json()["definition_complete"] is True


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
            "completion_mode": "manual_stop_only",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "run_ready"
    assert payload["temperature_settings_confirmed"] is True
    assert payload["temperature_settings"]["target_temperature_celsius"] == 37.5
    assert payload["temperature_settings"]["control_mode"] == "manual"
    assert payload["temperature_settings"]["output_power_percent"] == 68.0
    assert payload["temperature_settings"]["completion_mode"] == "manual_stop_only"
    assert payload["temperature_settings"]["confirmed_target_temperature_celsius"] == 37.5
    assert payload["temperature_settings"]["confirmed_output_power_percent"] == 68.0
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
    assert response.headers["x-frame-source-width"] == "1120"
    assert response.headers["x-frame-source-height"] == "620"
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


def test_preview_frame_fetch_normalizes_hik_access_denied_error(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]

    def fake_fetch_frame(runtime_config, *, run_id: str = "", prefer_cached: bool = False):
        del runtime_config, run_id, prefer_cached
        raise RuntimeError("Failed to open device via Hik MVS SDK (ret=0x80000203)")

    app.state.live_preview_service.fetch_frame = fake_fetch_frame

    response = client.post(f"/api/runs/{run_id}/preview/frame")

    assert response.status_code == 503
    assert "Hik MVS camera access denied" in response.json()["detail"]
    assert "another camera client" in response.json()["detail"]
    assert "0x80000203" in response.json()["detail"]


def test_preview_frame_locked_contract_mismatch_returns_operator_error(tmp_path: Path) -> None:
    app = create_app(profile="dev_lab")
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / "sessions.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")

    class WrongSizeCamera:
        def __init__(self) -> None:
            self.frame_id = 0

        def read_frame(self) -> FramePacket:
            self.frame_id += 1
            return FramePacket(
                timestamp_ms=1_000 + self.frame_id,
                source="wrong_size_camera",
                image=np.zeros((620, 1120), dtype=np.uint8),
                frame_id=self.frame_id,
            )

        def close(self) -> None:
            return None

    app.state.live_preview_service.open_camera = (
        lambda runtime_config, *, profile_name="setup_preview": WrongSizeCamera()
    )
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]

    response = client.post(f"/api/runs/{run_id}/preview/frame")

    assert response.status_code == 503
    assert "Frame pixel contract mismatch" in response.json()["detail"]
    assert "expected=2048x1364, actual=1120x620" in response.json()["detail"]


def test_preview_stream_start_normalizes_hik_access_denied_error(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]

    def fake_start_stream(runtime_config, *, run_id: str):
        del runtime_config, run_id
        raise RuntimeError("Failed to open device via Hik MVS SDK (ret=0x80000203)")

    app.state.live_preview_service.start_stream = fake_start_stream

    response = client.get(f"/api/runs/{run_id}/preview/stream")

    assert response.status_code == 503
    assert "Hik MVS camera access denied" in response.json()["detail"]
    assert "another camera client" in response.json()["detail"]
    assert "0x80000203" in response.json()["detail"]


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


def test_tracking_preview_frame_preserves_setup_source_dimensions_from_frame_meta(tmp_path: Path) -> None:
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
            meta={
                "tracking_preview_source_width": 96,
                "tracking_preview_source_height": 64,
            },
        ),
    )

    response = client.post(f"/api/runs/{run_id}/preview/frame?tracking=1")

    assert response.status_code == 200
    assert response.headers["x-frame-width"] == "2"
    assert response.headers["x-frame-height"] == "2"
    assert response.headers["x-frame-source-width"] == "96"
    assert response.headers["x-frame-source-height"] == "64"


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
    assert payload["threshold_mode_used"] in {"adaptive", "binary", "otsu"}
    assert payload["foreground_polarity_used"] in {"dark_on_light", "light_on_dark"}


def test_auto_detect_definition_blocks_locked_profile_when_alignment_contract_drifts(tmp_path: Path) -> None:
    app = _make_locked_alignment_app(tmp_path)
    app.state.runtime_config.live.vision.threshold_mode = "binary"

    def unexpected_fetch_frame(*_args, **_kwargs):
        raise AssertionError("preview frame should not be fetched when the alignment guard fails")

    app.state.live_preview_service.fetch_frame = unexpected_fetch_frame
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]

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

    assert response.status_code == 409
    assert "preset_auto_detect blocked by real/offline alignment guard" in response.json()["detail"]
    assert "contour detection could diverge" in response.json()["detail"]


def test_auto_detect_definition_blocks_locked_profile_request_contour_drift(tmp_path: Path) -> None:
    app = _make_locked_alignment_app(tmp_path)

    def unexpected_fetch_frame(*_args, **_kwargs):
        raise AssertionError("preview frame should not be fetched when request contour settings drift")

    app.state.live_preview_service.fetch_frame = unexpected_fetch_frame
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 96, "height": 64},
            "foreground_polarity": "light_on_dark",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": False,
            "min_target_area_px": 200,
        },
    )

    assert response.status_code == 409
    assert "preset_auto_detect blocked by real/offline alignment guard" in response.json()["detail"]
    assert "request contour settings" in response.json()["detail"]


def test_save_definition_blocks_locked_profile_request_contour_drift(tmp_path: Path) -> None:
    app = _make_locked_alignment_app(tmp_path)
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]
    payload = _locked_alignment_definition_payload()
    payload["threshold_mode"] = "binary"

    response = client.put(f"/api/runs/{run_id}/definition", json=payload)

    assert response.status_code == 409
    assert "save_definition blocked by real/offline alignment guard" in response.json()["detail"]
    assert "request contour settings" in response.json()["detail"]


def test_locked_profile_auto_detect_uses_only_offline_truth_contour_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_locked_alignment_app(tmp_path)
    app.state.live_preview_service.fetch_frame = lambda *_args, **_kwargs: FramePacket(
        timestamp_ms=1_000,
        source="unit_test_frame",
        image=[[240 for _ in range(96)] for _ in range(64)],
        frame_id=1,
    )
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]
    candidates: list[tuple[str, str, bool, int]] = []

    class FakeDetector:
        def __init__(self, **kwargs):
            candidates.append(
                (
                    kwargs["foreground_polarity"],
                    kwargs["threshold_mode"],
                    bool(kwargs["ignore_internal_texture"]),
                    int(kwargs["min_target_area_px"]),
                )
            )

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="two_point_distance",
                metric_raw=71.0,
                quality=0.64,
                point_a_px=(12, 32),
                point_b_px=(83, 32),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            )

    monkeypatch.setattr("src.webapp.routes.live_run.RoiLongestSpanPointDetector", FakeDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 96, "height": 64},
            "metric_box": {"center_x": 48, "center_y": 32, "width": 80, "height": 24, "angle_deg": 0.0},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": False,
            "min_target_area_px": 200,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    assert candidates == [("dark_on_light", "adaptive", False, 200)]


def test_auto_detect_definition_uses_directional_contour_when_direction_angle_is_provided(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "guidewire"})
    run_id = created.json()["run_id"]
    image = [[240 for _ in range(32)] for _ in range(32)]
    for y in range(6, 24):
        for x in range(13, 17):
            image[y][x] = 24

    def fake_fetch_frame(runtime_config, *, run_id: str = "", prefer_cached: bool = False):
        return FramePacket(timestamp_ms=4_000, source="direction_fixture", image=image, frame_id=12)

    app.state.live_preview_service.fetch_frame = fake_fetch_frame

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 32, "height": 32},
            "direction_angle_deg": 90.0,
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "binary",
            "ignore_internal_texture": True,
            "min_target_area_px": 12,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["direction_angle_deg"] == 90.0
    assert payload["direction_projection_mode"] == "mask_projection"
    assert payload["selection_mode"] == "directional_contour_boundary_span"
    assert 13 <= payload["point_a_px"]["x"] <= 16
    assert 13 <= payload["point_b_px"]["x"] <= 16
    assert payload["point_a_px"]["y"] < payload["point_b_px"]["y"]
    assert payload["axis_point_a_px"] is None
    assert payload["axis_point_b_px"] is None
    assert payload["source_point_a_px"] is None
    assert payload["source_point_b_px"] is None
    assert payload["metric_raw"] == pytest.approx(19.0, abs=1.0)


def test_auto_detect_definition_directional_contour_can_flip_from_border_hugging_requested_polarity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    def fake_fetch_frame(runtime_config, *, run_id: str = "", prefer_cached: bool = False):
        del runtime_config, run_id, prefer_cached
        return FramePacket(timestamp_ms=4_000, source="direction_fixture", image=[[240] * 100 for _ in range(100)], frame_id=12)

    class FakeDirectionalDetector:
        def __init__(self, config):
            self.config = config

        def extract(self, frame):
            del frame
            if self.config.foreground_polarity == "light_on_dark" and self.config.threshold_mode == "binary":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="directional_contour_span",
                    metric_raw=120.0,
                    quality=0.95,
                    point_a_px=(20, 0),
                    point_b_px=(80, 99),
                    meta={
                        "component_area": 2_000,
                        "selection_mode": "directional_contour_max_chord",
                    },
                )
            if self.config.foreground_polarity == "dark_on_light" and self.config.threshold_mode == "binary":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="directional_contour_span",
                    metric_raw=80.0,
                    quality=0.80,
                    point_a_px=(40, 20),
                    point_b_px=(65, 80),
                    meta={
                        "component_area": 1_200,
                        "selection_mode": "directional_contour_max_chord",
                    },
                )
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="directional_contour_span",
                metric_raw=None,
                quality=0.0,
                meta={"reason": "target_component_not_found"},
            )

    app.state.live_preview_service.fetch_frame = fake_fetch_frame
    monkeypatch.setattr("src.webapp.routes.live_run.DirectionalContourMetricExtractor", FakeDirectionalDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 100, "height": 100},
            "direction_angle_deg": 70.0,
            "foreground_polarity": "light_on_dark",
            "threshold_mode": "binary",
            "ignore_internal_texture": True,
            "min_target_area_px": 12,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["foreground_polarity_used"] == "dark_on_light"
    assert payload["threshold_mode_used"] == "binary"
    assert payload["point_a_px"] == {"x": 40, "y": 20}
    assert "selected dark_on_light polarity" in payload["detail"]


def test_auto_detect_definition_directional_contour_rejects_only_roi_boundary_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    def fake_fetch_frame(runtime_config, *, run_id: str = "", prefer_cached: bool = False):
        del runtime_config, run_id, prefer_cached
        return FramePacket(timestamp_ms=4_000, source="direction_fixture", image=[[128] * 100 for _ in range(100)], frame_id=12)

    class FakeDirectionalDetector:
        def __init__(self, config):
            self.config = config

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="directional_contour_span",
                metric_raw=96.0,
                quality=0.97,
                point_a_px=(0, 0),
                point_b_px=(96, 0),
                meta={
                    "component_area": 1_200,
                    "selection_mode": "directional_contour_max_chord",
                },
            )

    app.state.live_preview_service.fetch_frame = fake_fetch_frame
    monkeypatch.setattr("src.webapp.routes.live_run.DirectionalContourMetricExtractor", FakeDirectionalDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 100, "height": 100},
            "metric_box": {"center_x": 50, "center_y": 50, "width": 100, "height": 100, "angle_deg": 0.0},
            "direction_angle_deg": 0.0,
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 12,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 422
    assert "ambiguous_contour_or_roi_boundary" in response.json()["detail"]


def test_auto_detect_definition_directional_contour_keeps_requested_threshold_when_specific(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    def fake_fetch_frame(runtime_config, *, run_id: str = "", prefer_cached: bool = False):
        del runtime_config, run_id, prefer_cached
        return FramePacket(timestamp_ms=4_000, source="direction_fixture", image=[[240] * 100 for _ in range(100)], frame_id=12)

    class FakeDirectionalDetector:
        def __init__(self, config):
            self.config = config

        def extract(self, frame):
            del frame
            if self.config.threshold_mode == "adaptive":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="directional_contour_span",
                    metric_raw=80.0,
                    quality=0.80,
                    point_a_px=(20, 40),
                    point_b_px=(90, 40),
                    meta={
                        "component_area": 1_200,
                        "selection_mode": "directional_contour_max_chord",
                    },
                )
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="directional_contour_span",
                metric_raw=94.0,
                quality=0.95,
                point_a_px=(3, 40),
                point_b_px=(97, 40),
                meta={
                    "component_area": 1_200,
                    "selection_mode": "directional_contour_max_chord",
                },
            )

    app.state.live_preview_service.fetch_frame = fake_fetch_frame
    monkeypatch.setattr("src.webapp.routes.live_run.DirectionalContourMetricExtractor", FakeDirectionalDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 100, "height": 100},
            "direction_angle_deg": 0.0,
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 12,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["threshold_mode_used"] == "adaptive"
    assert payload["point_a_px"] == {"x": 20, "y": 40}
    assert payload["point_b_px"] == {"x": 90, "y": 40}


def test_auto_detect_definition_directional_contour_maps_sensitivity_to_bridge_kernel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]
    seen_kernels: list[int] = []

    def fake_fetch_frame(runtime_config, *, run_id: str = "", prefer_cached: bool = False):
        del runtime_config, run_id, prefer_cached
        return FramePacket(timestamp_ms=4_000, source="direction_fixture", image=[[240] * 100 for _ in range(100)], frame_id=12)

    class FakeDirectionalDetector:
        def __init__(self, config):
            self.config = config
            seen_kernels.append(int(config.component_bridge_kernel))

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="directional_contour_span",
                metric_raw=80.0,
                quality=0.8,
                point_a_px=(40, 20),
                point_b_px=(65, 80),
                meta={
                    "component_area": 1_200,
                    "selection_mode": "directional_contour_max_chord",
                },
            )

    app.state.live_preview_service.fetch_frame = fake_fetch_frame
    monkeypatch.setattr("src.webapp.routes.live_run.DirectionalContourMetricExtractor", FakeDirectionalDetector)

    kernels_by_sensitivity: dict[int, set[int]] = {}
    for sensitivity in [1, 50, 100]:
        start_index = len(seen_kernels)
        response = client.post(
            f"/api/runs/{run_id}/definition/auto",
            json={
                "analysis_roi": {"x": 0, "y": 0, "width": 100, "height": 100},
                "direction_angle_deg": 70.0,
                "foreground_polarity": "dark_on_light",
                "threshold_mode": "binary",
                "ignore_internal_texture": True,
                "min_target_area_px": 12,
                "sensitivity": sensitivity,
            },
        )
        assert response.status_code == 200
        kernels_by_sensitivity[sensitivity] = set(seen_kernels[start_index:])

    assert kernels_by_sensitivity[1] == {3}
    assert kernels_by_sensitivity[50] == {11}
    assert kernels_by_sensitivity[100] == {39}


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
    assert payload["threshold_mode_used"] in {"adaptive", "binary", "otsu"}
    assert payload["foreground_polarity_used"] in {"dark_on_light", "light_on_dark"}
    assert _point_inside_metric_box(
        {"center_x": 48, "center_y": 32, "width": 80, "height": 24, "angle_deg": 0.0},
        payload["point_a_px"],
    )
    assert _point_inside_metric_box(
        {"center_x": 48, "center_y": 32, "width": 80, "height": 24, "angle_deg": 0.0},
        payload["point_b_px"],
    )


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
    assert payload["threshold_mode_used"] in {"adaptive", "binary", "otsu"}
    assert payload["foreground_polarity_used"] in {"dark_on_light", "light_on_dark"}
    assert _point_inside_metric_box(
        {"center_x": 48, "center_y": 32, "width": 18, "height": 40, "angle_deg": 82.0},
        payload["point_a_px"],
    )
    assert _point_inside_metric_box(
        {"center_x": 48, "center_y": 32, "width": 18, "height": 40, "angle_deg": 82.0},
        payload["point_b_px"],
    )


def test_auto_detect_definition_respects_long_axis_observation_direction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]
    detector_calls: list[dict[str, object]] = []

    class FakeDetector:
        def __init__(self, **kwargs):
            self._kwargs = kwargs
            detector_calls.append(kwargs)

        def extract(self, frame):
            del frame
            if self._kwargs["threshold_mode"] != "binary":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="two_point_distance",
                    metric_raw=None,
                    quality=0.0,
                    meta={"reason": "no_valid_component"},
                )
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="two_point_distance",
                metric_raw=23.0,
                quality=0.95,
                point_a_px=(20, 32),
                point_b_px=(43, 32),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            )

    monkeypatch.setattr("src.webapp.routes.live_run.RoiLongestSpanPointDetector", FakeDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 96, "height": 64},
            "metric_box": {"center_x": 48, "center_y": 32, "width": 80, "height": 24, "angle_deg": 0.0},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "binary",
            "ignore_internal_texture": True,
            "min_target_area_px": 20,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["point_a_px"]["y"] == payload["point_b_px"]["y"]
    assert payload["point_a_px"]["x"] < payload["point_b_px"]["x"]
    assert detector_calls
    assert detector_calls[0]["selection_strategy"] == "roi_local_horizontal_boundary"
    assert detector_calls[0]["roi_box"].angle_deg == 0.0


def test_auto_detect_definition_respects_rotated_long_axis_observation_direction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]
    detector_calls: list[dict[str, object]] = []

    class FakeDetector:
        def __init__(self, **kwargs):
            self._kwargs = kwargs
            detector_calls.append(kwargs)

        def extract(self, frame):
            del frame
            if self._kwargs["threshold_mode"] != "binary":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="two_point_distance",
                    metric_raw=None,
                    quality=0.0,
                    meta={"reason": "no_valid_component"},
                )
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="two_point_distance",
                metric_raw=85.44,
                quality=0.92,
                point_a_px=(137, 48),
                point_b_px=(91, 120),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            )

    monkeypatch.setattr("src.webapp.routes.live_run.RoiLongestSpanPointDetector", FakeDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 240, "height": 160},
            "metric_box": {"center_x": 120, "center_y": 80, "width": 140, "height": 70, "angle_deg": -32.0},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "binary",
            "ignore_internal_texture": True,
            "min_target_area_px": 50,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["point_a_px"] == {"x": 137, "y": 48}
    assert payload["point_b_px"] == {"x": 91, "y": 120}
    assert payload["metric_raw"] == pytest.approx(85.44, abs=1.0)
    assert detector_calls
    assert detector_calls[0]["selection_strategy"] == "roi_local_horizontal_boundary"
    assert detector_calls[0]["roi_box"].angle_deg == -32.0


def test_start_live_run_passes_persisted_long_axis_definition_into_metric_source(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    captured: dict[str, object] = {}

    def wrapped_build_metric_source(*, runtime_config, definition, target_temperature_celsius: float):
        captured["metric_definition"] = definition
        return MockLiveMetricSource(
            definition=definition,
            target_temperature_celsius=target_temperature_celsius,
        )

    app.state.live_run_service._build_metric_source = wrapped_build_metric_source
    client = TestClient(app)
    run_id = _create_ready_run(
        client,
        definition_payload={
            "analysis_roi": {"x": 0, "y": 0, "width": 240, "height": 160},
            "metric_box": {"center_x": 120, "center_y": 80, "width": 140, "height": 70, "angle_deg": -32.0},
            "point_a_px": {"x": 137, "y": 48},
            "point_b_px": {"x": 91, "y": 120},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "binary",
            "ignore_internal_texture": True,
            "min_target_area_px": 50,
        },
    )

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    deadline = time.time() + 3.0
    while "metric_definition" not in captured and time.time() < deadline:
        time.sleep(0.05)

    assert start_response.status_code == 200
    assert "metric_definition" in captured
    metric_definition = captured["metric_definition"]
    assert metric_definition.analysis_roi == RectRegion(x=0, y=0, width=240, height=160)
    assert metric_definition.metric_box.center_x == 120
    assert metric_definition.metric_box.center_y == 80
    assert metric_definition.observation_axis == ObservationAxis.LONG_AXIS
    assert metric_definition.metric_box.angle_deg == -32.0


def test_start_live_run_blocks_locked_profile_when_alignment_contract_drifts(tmp_path: Path) -> None:
    app = _make_locked_alignment_app(tmp_path)
    client = TestClient(app)
    run_id = _create_ready_run(client, definition_payload=_locked_alignment_definition_payload())
    app.state.runtime_config.live.vision.threshold_mode = "binary"

    def unexpected_open_camera(*_args, **_kwargs):
        raise AssertionError("camera should not open when the alignment guard fails")

    app.state.live_run_service.preview_service.open_camera = unexpected_open_camera

    response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )

    assert response.status_code == 409
    assert "live_run_start blocked by real/offline alignment guard" in response.json()["detail"]
    assert "contour detection could diverge" in response.json()["detail"]


def test_start_live_run_blocks_locked_profile_saved_definition_contour_drift(tmp_path: Path) -> None:
    app = _make_locked_alignment_app(tmp_path)
    client = TestClient(app)
    run_id = _create_ready_run(client, definition_payload=_locked_alignment_definition_payload())
    record = app.state.live_run_registry.get(run_id)
    assert record is not None and record.definition is not None
    record.definition.threshold_mode = "binary"

    def unexpected_open_camera(*_args, **_kwargs):
        raise AssertionError("camera should not open when saved contour settings drift")

    app.state.live_run_service.preview_service.open_camera = unexpected_open_camera

    response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )

    assert response.status_code == 409
    assert "live_run_start blocked by real/offline alignment guard" in response.json()["detail"]
    assert "request contour settings" in response.json()["detail"]


def test_auto_detect_definition_selects_higher_confidence_threshold_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    class FakeDetector:
        def __init__(self, **kwargs):
            self.threshold_mode = kwargs["threshold_mode"]

        def extract(self, frame):
            if self.threshold_mode == "adaptive":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="two_point_distance",
                    metric_raw=80.0,
                    quality=0.61,
                    point_a_px=(10, 20),
                    point_b_px=(90, 20),
                    meta={"selection_mode": "roi_local_horizontal_boundary"},
                )
            if self.threshold_mode == "otsu":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="two_point_distance",
                    metric_raw=84.0,
                    quality=0.91,
                    point_a_px=(8, 20),
                    point_b_px=(92, 20),
                    meta={"selection_mode": "roi_local_horizontal_boundary"},
                )
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="two_point_distance",
                metric_raw=None,
                quality=0.0,
                meta={"reason": "no_valid_component"},
            )

    monkeypatch.setattr("src.webapp.routes.live_run.RoiLongestSpanPointDetector", FakeDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 96, "height": 64},
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
    assert payload["threshold_mode_used"] == "otsu"
    assert payload["foreground_polarity_used"] == "dark_on_light"
    assert payload["quality"] == pytest.approx(0.91)
    assert "selected otsu thresholding" in payload["detail"]


def test_auto_detect_definition_prefers_interior_endpoint_over_single_roi_edge_touch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    class FakeDetector:
        def __init__(self, **kwargs):
            self.threshold_mode = kwargs["threshold_mode"]

        def extract(self, frame):
            del frame
            if self.threshold_mode == "adaptive":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="two_point_distance",
                    metric_raw=258.0,
                    quality=0.89,
                    point_a_px=(291, 298),
                    point_b_px=(549, 298),
                    meta={"selection_mode": "roi_local_horizontal_boundary", "component_area": 31925},
                )
            if self.threshold_mode == "otsu":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="two_point_distance",
                    metric_raw=278.0,
                    quality=0.92,
                    point_a_px=(289, 298),
                    point_b_px=(567, 298),
                    meta={"selection_mode": "roi_local_horizontal_boundary", "component_area": 50758},
                )
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="two_point_distance",
                metric_raw=None,
                quality=0.0,
                meta={"reason": "no_valid_component"},
            )

    monkeypatch.setattr("src.webapp.routes.live_run.RoiLongestSpanPointDetector", FakeDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 240, "y": 165, "width": 328, "height": 266},
            "metric_box": {"center_x": 404, "center_y": 298, "width": 328, "height": 266, "angle_deg": 0.0},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 200,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["threshold_mode_used"] == "adaptive"
    assert payload["point_b_px"] == {"x": 549, "y": 298}


def test_auto_detect_definition_accepts_edge_endpoint_for_clearly_fuller_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    class FakeDetector:
        def __init__(self, **kwargs):
            self.threshold_mode = kwargs["threshold_mode"]

        def extract(self, frame):
            del frame
            if self.threshold_mode == "adaptive":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="two_point_distance",
                    metric_raw=790.0,
                    quality=0.86,
                    point_a_px=(702, 940),
                    point_b_px=(1492, 923),
                    meta={"selection_mode": "roi_local_horizontal_boundary", "component_area": 385399},
                )
            if self.threshold_mode == "otsu":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="two_point_distance",
                    metric_raw=1038.0,
                    quality=0.97,
                    point_a_px=(656, 690),
                    point_b_px=(1694, 698),
                    meta={"selection_mode": "roi_local_horizontal_boundary", "component_area": 552370},
                )
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="two_point_distance",
                metric_raw=None,
                quality=0.0,
                meta={"reason": "no_valid_component"},
            )

    monkeypatch.setattr("src.webapp.routes.live_run.RoiLongestSpanPointDetector", FakeDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 590, "y": 419, "width": 1104, "height": 628},
            "metric_box": {"center_x": 1142, "center_y": 733, "width": 1104, "height": 628, "angle_deg": 0.0},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 200,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["threshold_mode_used"] == "otsu"
    assert payload["point_b_px"] == {"x": 1694, "y": 698}


def test_auto_detect_definition_uses_fixed_working_scale_for_roi_local_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]
    captured_kwargs: list[dict[str, object]] = []

    class FakeDetector:
        def __init__(self, **kwargs):
            captured_kwargs.append(kwargs)
            self.threshold_mode = kwargs["threshold_mode"]

        def extract(self, frame):
            del frame
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="two_point_distance",
                metric_raw=258.0,
                quality=0.89,
                point_a_px=(291, 298),
                point_b_px=(549, 298),
                meta={"selection_mode": "roi_local_horizontal_boundary", "component_area": 31925},
            )

    monkeypatch.setattr("src.webapp.routes.live_run.RoiLongestSpanPointDetector", FakeDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 956, "y": 655, "width": 1231, "height": 904},
            "metric_box": {"center_x": 1572, "center_y": 1107, "width": 1231, "height": 904, "angle_deg": 0.0},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": False,
            "min_target_area_px": 200,
            "sensitivity": 100,
        },
    )

    assert response.status_code == 200
    assert captured_kwargs
    assert all(kwargs["working_max_width"] == 384 for kwargs in captured_kwargs)
    assert all(kwargs["working_max_height"] == 240 for kwargs in captured_kwargs)


def test_auto_detect_definition_can_flip_foreground_polarity_for_higher_confidence_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    class FakeDetector:
        def __init__(self, **kwargs):
            self.foreground_polarity = kwargs["foreground_polarity"]
            self.threshold_mode = kwargs["threshold_mode"]

        def extract(self, frame):
            del frame
            if self.foreground_polarity == "light_on_dark" and self.threshold_mode == "binary":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="two_point_distance",
                    metric_raw=96.0,
                    quality=0.94,
                    point_a_px=(12, 20),
                    point_b_px=(108, 27),
                    meta={"selection_mode": "roi_local_horizontal_boundary"},
                )
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="two_point_distance",
                metric_raw=18.0,
                quality=0.12,
                point_a_px=(48, 20),
                point_b_px=(60, 20),
                meta={"selection_mode": "roi_local_horizontal_boundary"},
            )

    monkeypatch.setattr("src.webapp.routes.live_run.RoiLongestSpanPointDetector", FakeDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 128, "height": 64},
            "metric_box": {"center_x": 64, "center_y": 32, "width": 96, "height": 28, "angle_deg": 4.0},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 20,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["foreground_polarity_used"] == "light_on_dark"
    assert payload["threshold_mode_used"] == "binary"
    assert "selected light_on_dark polarity and binary thresholding" in payload["detail"]


def test_auto_detect_definition_prefers_specific_component_over_roi_filling_background(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/runs", json={"preset": "balloon"})
    run_id = created.json()["run_id"]

    class FakeDetector:
        def __init__(self, **kwargs):
            self.foreground_polarity = kwargs["foreground_polarity"]

        def extract(self, frame):
            del frame
            if self.foreground_polarity == "light_on_dark":
                return ShapeMetric(
                    timestamp_ms=1_000,
                    metric_name="two_point_distance",
                    metric_raw=127.0,
                    quality=0.99,
                    point_a_px=(0, 32),
                    point_b_px=(127, 32),
                    meta={
                        "selection_mode": "roi_local_horizontal_boundary",
                        "component_area": 128 * 64,
                    },
                )
            return ShapeMetric(
                timestamp_ms=1_000,
                metric_name="two_point_distance",
                metric_raw=88.0,
                quality=0.84,
                point_a_px=(14, 32),
                point_b_px=(102, 32),
                meta={
                    "selection_mode": "roi_local_horizontal_boundary",
                    "component_area": 1400,
                },
            )

    monkeypatch.setattr("src.webapp.routes.live_run.RoiLongestSpanPointDetector", FakeDetector)

    response = client.post(
        f"/api/runs/{run_id}/definition/auto",
        json={
            "analysis_roi": {"x": 0, "y": 0, "width": 128, "height": 64},
            "metric_box": {"center_x": 64, "center_y": 32, "width": 96, "height": 28, "angle_deg": 0.0},
            "observation_axis": "long_axis",
            "foreground_polarity": "dark_on_light",
            "threshold_mode": "adaptive",
            "ignore_internal_texture": True,
            "min_target_area_px": 20,
            "sensitivity": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["foreground_polarity_used"] == "dark_on_light"
    assert payload["point_a_px"] == {"x": 14, "y": 32}
    assert payload["point_b_px"] == {"x": 102, "y": 32}


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
    assert telemetry_payload["latest"]["selection_mode"] in {"mock_tracking", "mock_afas_curve_playback"}
    assert telemetry_payload["latest"]["tracking_state"] is None
    assert telemetry_payload["latest"]["reason"] is None
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
    app.state.runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig()
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
            class AppliedRoiMockCamera(MockCamera):
                def get_applied_device_roi(self_nonlocal):
                    return DeviceRoiConfig(x=864, y=568, width=160, height=128)

            return AppliedRoiMockCamera(
                profile_name=profile_name,
                device_roi=DeviceRoiConfig(x=864, y=568, width=160, height=128),
            )
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
    run_id = _create_ready_run(client, definition_payload=_offset_definition_payload(x=900, y=600))

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    completed_detail = _wait_for_run_status(client, run_id, "completed")
    result_response = client.get(f"/api/runs/{run_id}/result")

    assert start_response.status_code == 200
    assert captured["measurement_roi"] == {
        "x": 868,
        "y": 568,
        "width": 160,
        "height": 128,
    }
    metric_definition = captured["metric_definition"]
    assert metric_definition.analysis_roi.x == 36
    assert metric_definition.analysis_roi.y == 32
    assert completed_detail["measurement_profile"]["acquisition_roi"] == {
        "x": 864,
        "y": 568,
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
        "x": 36,
        "y": 32,
        "width": 96,
        "height": 64,
    }
    assert json.loads((session_dir / "measurement_capture_plan.json").read_text(encoding="utf-8")) == {
        "effective_acquisition_roi": {"x": 864, "y": 568, "width": 160, "height": 128},
        "requested_effective_acquisition_roi": {"x": 868, "y": 568, "width": 160, "height": 128},
        "applied_effective_acquisition_roi": {"x": 864, "y": 568, "width": 160, "height": 128},
        "setup_preview_sensor_roi": {"x": 0, "y": 0, "width": 0, "height": 0},
        "effective_local_origin_in_setup_preview_px": {"x": 864, "y": 568},
        "requested_local_origin_in_setup_preview_px": {"x": 868, "y": 568},
        "setup_to_effective_local_translation_px": {"dx": -864, "dy": -568},
        "setup_to_requested_local_translation_px": {"dx": -868, "dy": -568},
    }


def test_failed_live_run_normalizes_hik_access_denied_error(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.state.runtime_config.adapters["camera"] = "hik_gige_mvs"

    def fail_open_camera(runtime_config, *, profile_name: str = "setup_preview"):
        del runtime_config
        if profile_name == "measurement":
            raise RuntimeError("Failed to open device via Hik MVS SDK (ret=0x80000203)")
        return MockCamera(profile_name=profile_name)

    app.state.live_run_service.preview_service.open_camera = fail_open_camera
    client = TestClient(app)
    run_id = _create_ready_run(client)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    _wait_for_run_status(client, run_id, "failed")
    result_response = client.get(f"/api/runs/{run_id}/result")

    assert start_response.status_code == 200
    assert result_response.status_code == 200
    assert "Hik MVS camera access denied" in result_response.json()["result_detail"]
    assert "another camera client" in result_response.json()["result_detail"]


def test_failed_live_run_uses_effective_measurement_roi_and_runtime_definition_artifacts(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.state.runtime_config.adapters["camera"] = "hik_gige_mvs"
    app.state.runtime_config.live.camera.setup_preview.device_roi = DeviceRoiConfig()
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
            class AppliedRoiMockCamera(MockCamera):
                def get_applied_device_roi(self_nonlocal):
                    return DeviceRoiConfig(x=864, y=568, width=160, height=128)

            return AppliedRoiMockCamera(
                profile_name=profile_name,
                device_roi=DeviceRoiConfig(x=864, y=568, width=160, height=128),
            )
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
    run_id = _create_ready_run(client, definition_payload=_offset_definition_payload(x=900, y=600))

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    failed_detail = _wait_for_run_status(client, run_id, "failed")
    result_response = client.get(f"/api/runs/{run_id}/result")

    assert start_response.status_code == 200
    assert failed_detail["measurement_profile"]["acquisition_roi"] == {
        "x": 864,
        "y": 568,
        "width": 160,
        "height": 128,
    }
    assert captured["measurement_roi"] == {
        "x": 868,
        "y": 568,
        "width": 160,
        "height": 128,
    }
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["state"] == "failed"
    assert result_payload["artifacts"]["definition_original"] == "definition_original.json"
    assert result_payload["artifacts"]["definition_effective_local"] == "definition_effective_local.json"
    assert result_payload["artifacts"]["measurement_capture_plan"] == "measurement_capture_plan.json"
    session_dir = tmp_path / "artifacts" / run_id
    assert json.loads((session_dir / "measurement_capture_plan.json").read_text(encoding="utf-8")) == {
        "effective_acquisition_roi": {"x": 864, "y": 568, "width": 160, "height": 128},
        "requested_effective_acquisition_roi": {"x": 868, "y": 568, "width": 160, "height": 128},
        "applied_effective_acquisition_roi": {"x": 864, "y": 568, "width": 160, "height": 128},
        "setup_preview_sensor_roi": {"x": 0, "y": 0, "width": 0, "height": 0},
        "effective_local_origin_in_setup_preview_px": {"x": 864, "y": 568},
        "requested_local_origin_in_setup_preview_px": {"x": 868, "y": 568},
        "setup_to_effective_local_translation_px": {"dx": -864, "dy": -568},
        "setup_to_requested_local_translation_px": {"dx": -868, "dy": -568},
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
    app.state.runtime_config.live.temp.control.completion_mode = "manual_stop_only"
    app.state.runtime_config.live.run.capture_interval_ms = 500
    client = TestClient(app)
    run_id = _create_ready_run(client)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    _wait_for_run_status(client, run_id, "running")
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
    analysis_response = client.post(f"/api/session/{run_id}/afas/analysis", json={})

    assert start_response.status_code == 200
    assert running_detail.status_code == 200
    assert running_detail.json()["status"] == "running"
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopping"
    assert aborted_detail["status"] == "aborted"
    assert analysis_response.status_code == 200
    assert analysis_response.json()["active_channel"] == "Space1"


def test_run_temperature_settings_can_select_manual_stop_for_one_run(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    app.state.runtime_config.live.temp.control.completion_mode = "target_reached"
    app.state.runtime_config.live.temp.control.mock_ramp_step_celsius = 100.0
    app.state.runtime_config.live.run.capture_interval_ms = 50
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"preset": "balloon"}).json()["run_id"]
    response = client.put(f"/api/runs/{run_id}/definition", json=_mock_definition_payload())
    assert response.status_code == 200
    temp_response = _confirm_temperature_settings(
        client,
        run_id,
        target_temperature_celsius=35.0,
        completion_mode="manual_stop_only",
    )

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 35.0},
    )
    time.sleep(0.25)
    running_detail = client.get(f"/api/runs/{run_id}")
    stop_response = client.post(f"/api/runs/{run_id}/stop")
    aborted_detail = _wait_for_run_status(client, run_id, "aborted")
    analysis_response = client.post(f"/api/session/{run_id}/afas/analysis", json={})

    assert temp_response["temperature_settings"]["completion_mode"] == "manual_stop_only"
    assert start_response.status_code == 200
    assert running_detail.status_code == 200
    assert running_detail.json()["status"] == "running"
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopping"
    assert aborted_detail["status"] == "aborted"
    assert analysis_response.status_code == 200


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


def test_sample_limit_failed_run_still_returns_analyzable_result(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    service = app.state.live_run_service
    app.state.runtime_config.live.run.manual_stop_max_samples = 30
    app.state.runtime_config.live.run.measurement_target_hz = 1000.0
    app.state.runtime_config.live.run.capture_interval_ms = 1
    service._temp_controller_factory = lambda: MockTempController(start_celsius=-5.0, ramp_step_celsius=0.5)

    class IndexedCurveMetricSource:
        def __init__(self, total_samples: int) -> None:
            self._total_samples = max(2, int(total_samples))

        def extract(self, frame, temp, *, sample_index: int, total_samples: int):
            del frame, temp, total_samples
            progress = min(max(float(sample_index) / float(self._total_samples - 1), 0.0), 1.0)
            curve_progress = progress * progress * (3.0 - 2.0 * progress)
            return ShapeMetric(
                timestamp_ms=1_000 + int(sample_index),
                metric_name="two_point_distance",
                metric_raw=38.0 + 35.0 * curve_progress,
                quality=0.99,
                point_a_px=(12, 32),
                point_b_px=(83, 32),
                meta={"selection_mode": "fixture_curve"},
            )

    service._build_metric_source = lambda **kwargs: IndexedCurveMetricSource(
        app.state.runtime_config.live.run.manual_stop_max_samples
    )
    client = TestClient(app)
    run_id = _create_ready_run(client, target_temperature_celsius=45.0)

    start_response = client.post(
        f"/api/runs/{run_id}/start",
        json={"target_temperature_celsius": 45.0},
    )
    failed_detail = _wait_for_run_status(client, run_id, "failed")
    telemetry_response = client.get(f"/api/runs/{run_id}/telemetry")
    result_response = client.get(f"/api/runs/{run_id}/result")
    analysis_response = client.post(f"/api/session/{run_id}/afas/analysis", json={})

    assert start_response.status_code == 200
    assert failed_detail["status"] == "failed"
    assert telemetry_response.status_code == 200
    assert len(telemetry_response.json()["curve"]) == 30
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["state"] == "failed"
    assert result_payload["result_status"] == "ok"
    assert result_payload["as_value"] is not None
    assert result_payload["af_value"] is not None
    assert result_payload["point_count"] == 30
    assert any("terminal_failed" in warning for warning in result_payload["warnings"])
    assert analysis_response.status_code == 200
    assert analysis_response.json()["analysis"]["result_status"] == "ok"


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
