import numpy as np

import src.application.real_camera_alignment_probe as real_camera_alignment_probe
from src.application.real_offline_alignment import RealOfflineAlignmentError
from src.application.real_camera_alignment_probe import probe_real_camera_alignment
from src.application.runtime_config import load_runtime_config
from src.core.models import FramePacket


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
    def fake_probe(runtime_config) -> dict[str, object]:
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


def test_real_camera_alignment_probe_cli_returns_nonzero_on_fail(monkeypatch, capsys) -> None:
    def fake_probe(runtime_config) -> dict[str, object]:
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
