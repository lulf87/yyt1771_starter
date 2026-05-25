import json

import numpy as np

import src.application.real_camera_alignment_probe as real_camera_alignment_probe
from src.application.real_offline_alignment import RealOfflineAlignmentError
from src.application.real_camera_alignment_probe import probe_real_camera_alignment
from src.application.runtime_config import load_runtime_config
from src.core.models import FramePacket, MeasurementDefinition, MetricBox, PixelPoint, RectRegion


def _fake_alignment_contract(real_profile: str) -> dict[str, object]:
    return {
        "status": "ok",
        "real_profile": real_profile,
        "offline_profile": "dev_offline_capture",
        "pixel_contract": {"source_size_px": {"width": 2048, "height": 1364}},
        "algorithm_contract": {
            "vision": {
                "foreground_polarity": "dark_on_light",
                "threshold_mode": "adaptive",
            },
            "ab_selection": {
                "formal_point_source": "target_contour_boundary",
                "formal_point_fields": ["point_a_px", "point_b_px"],
                "direction_projection_mode": "max_chord",
                "projected_points_exposed_as_formal_ab": False,
            },
        },
        "angles_checked": 12,
        "angle_step_deg": 30,
        "hardware_access": "not_attempted",
    }


def test_probe_real_camera_alignment_checks_setup_and_measurement_profiles() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")
    opened_profiles: list[str] = []
    closed_profiles: list[str] = []

    class FakeCamera:
        def __init__(self, profile_name: str) -> None:
            self.profile_name = profile_name

        def read_frame(self) -> FramePacket:
            opened_profiles.append(self.profile_name)
            profile = getattr(runtime_config.live.camera, self.profile_name)
            return FramePacket(
                timestamp_ms=1_000 if self.profile_name == "setup_preview" else 2_000,
                source=f"fake_{self.profile_name}",
                image=np.zeros((1364, 2048), dtype=np.uint8),
                frame_id=1 if self.profile_name == "setup_preview" else 2,
                meta={
                    "device_roi": {
                        "x": profile.device_roi.x,
                        "y": profile.device_roi.y,
                        "width": profile.device_roi.width,
                        "height": profile.device_roi.height,
                    }
                },
            )

        def close(self) -> None:
            closed_profiles.append(self.profile_name)

    payload = probe_real_camera_alignment(
        runtime_config,
        camera_opener=lambda _runtime_config, profile_name: FakeCamera(profile_name),
        alignment_auditor=_fake_alignment_contract,
    )

    assert payload["status"] == "ok"
    assert payload["hardware_access"] == "attempted"
    assert payload["frame_source_mode"] == "real_camera"
    assert payload["frame_access"] == "attempted"
    assert payload["alignment_contract"]["algorithm_contract"]["ab_selection"]["formal_point_source"] == (
        "target_contour_boundary"
    )
    assert [item["profile_name"] for item in payload["profiles"]] == ["setup_preview", "measurement"]
    assert [item["actual_size_px"] for item in payload["profiles"]] == [
        {"width": 2048, "height": 1364},
        {"width": 2048, "height": 1364},
    ]
    assert opened_profiles == ["setup_preview", "measurement"]
    assert closed_profiles == ["setup_preview", "measurement"]


def test_probe_real_camera_alignment_marks_offline_capture_as_no_hardware_access() -> None:
    runtime_config = load_runtime_config("dev_offline_capture")
    opened_profiles: list[str] = []

    class FakeCamera:
        def __init__(self, profile_name: str) -> None:
            self.profile_name = profile_name

        def read_frame(self) -> FramePacket:
            opened_profiles.append(self.profile_name)
            profile = getattr(runtime_config.live.camera, self.profile_name)
            return FramePacket(
                timestamp_ms=1_000 if self.profile_name == "setup_preview" else 2_000,
                source=f"offline_capture:{self.profile_name}",
                image=np.zeros((1364, 2048), dtype=np.uint8),
                frame_id=1 if self.profile_name == "setup_preview" else 2,
                meta={
                    "device_roi": {
                        "x": profile.device_roi.x,
                        "y": profile.device_roi.y,
                        "width": profile.device_roi.width,
                        "height": profile.device_roi.height,
                    }
                },
            )

        def close(self) -> None:
            pass

    payload = probe_real_camera_alignment(
        runtime_config,
        camera_opener=lambda _runtime_config, profile_name: FakeCamera(profile_name),
        alignment_auditor=_fake_alignment_contract,
    )

    assert payload["status"] == "ok"
    assert payload["hardware_access"] == "not_attempted"
    assert payload["frame_source_mode"] == "offline_capture"
    assert payload["frame_access"] == "attempted"
    assert opened_profiles == ["setup_preview", "measurement"]


def test_probe_real_camera_alignment_runs_formal_ab_detection_when_definition_is_provided() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")
    opened_profiles: list[str] = []

    class FakeCamera:
        def __init__(self, profile_name: str) -> None:
            self.profile_name = profile_name

        def read_frame(self) -> FramePacket:
            opened_profiles.append(self.profile_name)
            profile = getattr(runtime_config.live.camera, self.profile_name)
            image = np.full((1364, 2048), 240, dtype=np.uint8)
            image[650:711, 600:1401] = 20
            return FramePacket(
                timestamp_ms=1_000 if self.profile_name == "setup_preview" else 2_000,
                source=f"fake_{self.profile_name}",
                image=image,
                frame_id=1 if self.profile_name == "setup_preview" else 2,
                meta={
                    "device_roi": {
                        "x": profile.device_roi.x,
                        "y": profile.device_roi.y,
                        "width": profile.device_roi.width,
                        "height": profile.device_roi.height,
                    }
                },
            )

        def close(self) -> None:
            pass

    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=500, y=540, width=1000, height=260),
        metric_box=MetricBox(center_x=1000, center_y=670, width=900, height=200, angle_deg=0.0),
        point_a_px=PixelPoint(x=600, y=680),
        point_b_px=PixelPoint(x=1400, y=680),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=False,
        min_target_area_px=200,
        sensitivity=50.0,
        direction_angle_deg=0.0,
        direction_projection_mode="max_chord",
    )

    payload = probe_real_camera_alignment(
        runtime_config,
        camera_opener=lambda _runtime_config, profile_name: FakeCamera(profile_name),
        alignment_auditor=_fake_alignment_contract,
        definition=definition,
    )

    assert payload["status"] == "ok"
    assert opened_profiles == ["setup_preview", "measurement"]
    detections = [item["ab_detection"] for item in payload["profiles"]]
    assert [item["status"] for item in detections] == ["ok", "ok"]
    assert {item["selection_mode"] for item in detections} == {"directional_contour_max_chord"}
    assert {item["direction_projection_mode"] for item in detections} == {"max_chord"}
    assert all(item["quality"] >= 0.75 for item in detections)
    assert detections[0]["point_a_px"][0] < detections[0]["point_b_px"][0]
    assert detections[1]["point_a_px"] == detections[0]["point_a_px"]
    assert detections[1]["point_b_px"] == detections[0]["point_b_px"]


def test_probe_real_camera_alignment_rejects_stale_definition_before_frame_access() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=500, y=540, width=1000, height=260),
        metric_box=MetricBox(center_x=1000, center_y=670, width=900, height=200, angle_deg=0.0),
        point_a_px=PixelPoint(x=600, y=680),
        point_b_px=PixelPoint(x=1400, y=680),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=False,
        min_target_area_px=200,
        sensitivity=50.0,
        direction_angle_deg=0.0,
        direction_projection_mode="mask_projection",
    )

    def unexpected_open(_runtime_config, _profile_name: str) -> object:
        raise AssertionError("camera should not be opened when the definition drifts from offline truth")

    payload = probe_real_camera_alignment(
        runtime_config,
        camera_opener=unexpected_open,
        alignment_auditor=_fake_alignment_contract,
        definition=definition,
    )

    assert payload["status"] == "fail"
    assert payload["hardware_access"] == "not_attempted"
    assert payload["frame_source_mode"] == "real_camera"
    assert payload["frame_access"] == "not_attempted"
    assert payload["profiles"] == []
    assert "real_camera_alignment_probe blocked by real/offline alignment guard" in payload["detail"]
    assert "mask_projection" in payload["detail"]


def test_probe_real_camera_alignment_reports_contract_mismatch() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")

    class FakeCamera:
        def __init__(self, profile_name: str) -> None:
            self.profile_name = profile_name

        def read_frame(self) -> FramePacket:
            profile = getattr(runtime_config.live.camera, self.profile_name)
            height = 1364 if self.profile_name == "setup_preview" else 768
            return FramePacket(
                timestamp_ms=1_000,
                source=f"fake_{self.profile_name}",
                image=np.zeros((height, 2048), dtype=np.uint8),
                frame_id=1,
                meta={
                    "device_roi": {
                        "x": profile.device_roi.x,
                        "y": profile.device_roi.y,
                        "width": profile.device_roi.width,
                        "height": profile.device_roi.height,
                    }
                },
            )

        def close(self) -> None:
            pass

    payload = probe_real_camera_alignment(
        runtime_config,
        camera_opener=lambda _runtime_config, profile_name: FakeCamera(profile_name),
        alignment_auditor=_fake_alignment_contract,
    )

    assert payload["status"] == "fail"
    assert [item["status"] for item in payload["profiles"]] == ["ok", "fail"]
    assert "Frame pixel contract mismatch" in payload["detail"]
    assert "actual=2048x768" in payload["detail"]


def test_probe_real_camera_alignment_normalizes_hik_open_device_error() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")

    def fail_open(_runtime_config, _profile_name: str) -> object:
        raise RuntimeError("Failed to open device via Hik MVS SDK (ret=0x80000203)")

    payload = probe_real_camera_alignment(
        runtime_config,
        camera_opener=fail_open,
        alignment_auditor=_fake_alignment_contract,
    )

    assert payload["status"] == "fail"
    assert payload["hardware_access"] == "attempted"
    assert payload["profiles"][0]["profile_name"] == "setup_preview"
    assert payload["profiles"][0]["status"] == "fail"
    assert "Hik MVS camera access denied" in payload["detail"]
    assert "0x80000203" in payload["detail"]


def test_probe_real_camera_alignment_does_not_open_camera_when_alignment_contract_fails() -> None:
    runtime_config = load_runtime_config("dev_lab_camera_mock_temp")

    def fail_alignment(_real_profile: str) -> dict[str, object]:
        raise RealOfflineAlignmentError("vision settings differ from accepted offline material")

    def unexpected_open(_runtime_config, _profile_name: str) -> object:
        raise AssertionError("camera should not be opened when the offline truth contract fails")

    payload = probe_real_camera_alignment(
        runtime_config,
        camera_opener=unexpected_open,
        alignment_auditor=fail_alignment,
    )

    assert payload["status"] == "fail"
    assert payload["hardware_access"] == "not_attempted"
    assert payload["profiles"] == []
    assert payload["alignment_contract"]["status"] == "fail"
    assert "vision settings differ" in payload["detail"]


def test_real_camera_alignment_probe_cli_returns_zero_on_ok(monkeypatch, capsys) -> None:
    def fake_probe(runtime_config, *, definition=None) -> dict[str, object]:
        assert definition is None
        return {
            "status": "ok",
            "profile": runtime_config.profile,
            "hardware_access": "attempted",
            "alignment_contract": _fake_alignment_contract(runtime_config.profile),
            "profiles": [],
            "detail": "ok",
        }

    monkeypatch.setattr(real_camera_alignment_probe, "probe_real_camera_alignment", fake_probe)

    exit_code = real_camera_alignment_probe.main(["--profile", "dev_lab_camera_mock_temp"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"status": "ok"' in captured.out
    assert '"profile": "dev_lab_camera_mock_temp"' in captured.out


def test_real_camera_alignment_probe_cli_loads_definition_file(tmp_path, monkeypatch, capsys) -> None:
    definition_path = tmp_path / "definition.json"
    definition_path.write_text(
        json.dumps(
            {
                "definition": {
                    "analysis_roi": {"x": 500, "y": 540, "width": 1000, "height": 260},
                    "metric_box": {
                        "center_x": 1000,
                        "center_y": 670,
                        "width": 900,
                        "height": 200,
                        "angle_deg": 0.0,
                    },
                    "point_a_px": {"x": 600, "y": 680},
                    "point_b_px": {"x": 1400, "y": 680},
                    "observation_axis": "long_axis",
                    "foreground_polarity": "dark_on_light",
                    "threshold_mode": "adaptive",
                    "ignore_internal_texture": False,
                    "min_target_area_px": 200,
                    "sensitivity": 50.0,
                    "direction_angle_deg": 0.0,
                    "direction_projection_mode": "max_chord",
                }
            }
        ),
        encoding="utf-8",
    )
    captured_definition: dict[str, MeasurementDefinition | None] = {}

    def fake_probe(runtime_config, *, definition=None) -> dict[str, object]:
        captured_definition["value"] = definition
        return {
            "status": "ok",
            "profile": runtime_config.profile,
            "hardware_access": "not_attempted",
            "frame_source_mode": "offline_capture",
            "frame_access": "attempted",
            "alignment_contract": _fake_alignment_contract(runtime_config.profile),
            "profiles": [
                {
                    "profile_name": "setup_preview",
                    "status": "ok",
                    "expected_size_px": {"width": 2048, "height": 1364},
                    "actual_size_px": {"width": 2048, "height": 1364},
                    "expected_device_roi": {"x": 0, "y": 0, "width": 2048, "height": 1364},
                    "actual_device_roi": {"x": 0, "y": 0, "width": 2048, "height": 1364},
                    "acquisition": {"pixel_format": "mono8", "exposure_us": 50000, "gain_db": 12.0},
                    "frame_id": 1,
                    "timestamp_ms": 1000,
                    "source": "offline_capture",
                    "ab_detection": {
                        "status": "ok",
                        "selection_mode": "directional_contour_max_chord",
                        "direction_projection_mode": "max_chord",
                    },
                    "detail": "ok",
                }
            ],
            "detail": "ok",
        }

    monkeypatch.setattr(real_camera_alignment_probe, "probe_real_camera_alignment", fake_probe)

    exit_code = real_camera_alignment_probe.main(
        ["--profile", "dev_offline_capture", "--definition-file", str(definition_path)]
    )

    assert exit_code == 0
    definition = captured_definition["value"]
    assert definition is not None
    assert definition.analysis_roi == RectRegion(x=500, y=540, width=1000, height=260)
    assert definition.metric_box == MetricBox(center_x=1000, center_y=670, width=900, height=200, angle_deg=0.0)
    assert definition.point_a_px == PixelPoint(x=600, y=680)
    assert definition.point_b_px == PixelPoint(x=1400, y=680)
    assert definition.direction_projection_mode == "max_chord"
    captured = capsys.readouterr()
    assert '"frame_source_mode": "offline_capture"' in captured.out


def test_real_camera_alignment_probe_cli_loads_run_artifact_directory(tmp_path, monkeypatch) -> None:
    run_dir = tmp_path / "run-artifact"
    run_dir.mkdir()
    (run_dir / "definition_original.json").write_text(
        json.dumps(
            {
                "analysis_roi": {"x": 510, "y": 550, "width": 980, "height": 240},
                "metric_box": {
                    "center_x": 1000,
                    "center_y": 670,
                    "width": 880,
                    "height": 180,
                    "angle_deg": -13.0,
                },
                "point_a_px": {"x": 610, "y": 710},
                "point_b_px": {"x": 1390, "y": 680},
                "observation_axis": "long_axis",
                "foreground_polarity": "dark_on_light",
                "threshold_mode": "adaptive",
                "ignore_internal_texture": False,
                "min_target_area_px": 200,
                "sensitivity": 50.0,
                "direction_angle_deg": -13.0,
                "direction_projection_mode": "max_chord",
            }
        ),
        encoding="utf-8",
    )
    captured_definition: dict[str, MeasurementDefinition | None] = {}

    def fake_probe(runtime_config, *, definition=None) -> dict[str, object]:
        captured_definition["value"] = definition
        return {
            "status": "ok",
            "profile": runtime_config.profile,
            "hardware_access": "not_attempted",
            "frame_source_mode": "offline_capture",
            "frame_access": "attempted",
            "alignment_contract": _fake_alignment_contract(runtime_config.profile),
            "profiles": [],
            "detail": "ok",
        }

    monkeypatch.setattr(real_camera_alignment_probe, "probe_real_camera_alignment", fake_probe)

    exit_code = real_camera_alignment_probe.main(["--profile", "dev_offline_capture", "--definition-file", str(run_dir)])

    assert exit_code == 0
    definition = captured_definition["value"]
    assert definition is not None
    assert definition.analysis_roi == RectRegion(x=510, y=550, width=980, height=240)
    assert definition.metric_box.angle_deg == -13.0
    assert definition.direction_projection_mode == "max_chord"


def test_real_camera_alignment_probe_cli_returns_nonzero_on_fail(monkeypatch, capsys) -> None:
    def fake_probe(runtime_config, *, definition=None) -> dict[str, object]:
        assert definition is None
        return {
            "status": "fail",
            "profile": runtime_config.profile,
            "hardware_access": "attempted",
            "alignment_contract": _fake_alignment_contract(runtime_config.profile),
            "profiles": [],
            "detail": "No Hik cameras were discovered by the MVS SDK",
        }

    monkeypatch.setattr(real_camera_alignment_probe, "probe_real_camera_alignment", fake_probe)

    exit_code = real_camera_alignment_probe.main(["--profile", "dev_lab_camera_mock_temp"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert '"status": "fail"' in captured.out
    assert "No Hik cameras were discovered" in captured.out
