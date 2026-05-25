from pathlib import Path

from src.workflow import precheck as precheck_module
from src.workflow.precheck import build_system_precheck


def test_build_system_precheck_returns_warn_with_pending_adapters(tmp_path: Path) -> None:
    report = build_system_precheck(
        profile_name="dev_mock",
        storage={
            "sqlite_path": str(tmp_path / "sessions.db"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={"dataset_path": "examples/replay"},
        adapters={"camera": "mock", "temp": "mock", "plc": "mock"},
        camera={},
        project_root=Path(__file__).resolve().parents[2],
    )

    assert report["profile"] == "dev_mock"
    assert report["status"] == "warn"
    items = {item["name"]: item for item in report["items"]}
    assert items["sqlite_path"]["status"] == "ok"
    assert items["artifact_dir"]["status"] == "ok"
    assert items["replay_dataset"]["status"] == "ok"
    assert items["camera_backend"]["status"] == "ok"


def test_build_system_precheck_returns_fail_when_storage_missing() -> None:
    report = build_system_precheck(
        profile_name="broken",
        storage={},
        replay={},
        adapters={"camera": "", "temp": "", "plc": ""},
        camera={},
        project_root=Path(__file__).resolve().parents[2],
    )

    assert report["status"] == "fail"
    items = {item["name"]: item for item in report["items"]}
    assert items["sqlite_path"]["status"] == "fail"
    assert items["artifact_dir"]["status"] == "fail"
    assert items["replay_dataset"]["status"] == "warn"
    assert items["camera_backend"]["status"] == "fail"


def test_build_system_precheck_fails_when_pinned_gige_identity_is_missing(tmp_path: Path) -> None:
    report = build_system_precheck(
        profile_name="prod_win",
        storage={
            "sqlite_path": str(tmp_path / "prod.sqlite3"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={"dataset_path": "examples/replay"},
        adapters={"camera": "hik_gige_mvs", "temp": "modbus_temp", "plc": "modbus_tcp"},
        camera={
            "transport": "gige_vision",
            "sdk": "hik_mvs",
            "probe_mode": "pinned",
            "allowed_models": ["MV-CU060-10GM"],
            "serial_number": "",
            "ip": "",
            **_real_hardware_camera_roi_sections(),
        },
        run_config=_locked_alignment_run_config(),
        vision_config=_locked_alignment_vision_config(),
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "fail"
    assert items["camera_probe_mode"]["status"] == "ok"
    assert items["camera_model_policy"]["status"] == "ok"
    assert items["camera_transport"]["status"] == "ok"
    assert items["real_offline_pixel_alignment"]["status"] == "ok"
    assert items["camera_identity"]["status"] == "fail"
    assert items["camera_sdk"]["status"] == "pending"


def test_build_system_precheck_fails_when_gige_transport_is_wrong(tmp_path: Path) -> None:
    report = build_system_precheck(
        profile_name="prod_win",
        storage={
            "sqlite_path": str(tmp_path / "prod.sqlite3"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={"dataset_path": "examples/replay"},
        adapters={"camera": "hik_gige_mvs", "temp": "modbus_temp", "plc": "modbus_tcp"},
        camera={
            "transport": "rtsp",
            "sdk": "hik_mvs",
            "probe_mode": "pinned",
            "allowed_models": ["MV-CU060-10GM"],
            "serial_number": "MV-123",
            **_real_hardware_camera_roi_sections(),
        },
        run_config=_locked_alignment_run_config(),
        vision_config=_locked_alignment_vision_config(),
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "fail"
    assert items["real_offline_pixel_alignment"]["status"] == "ok"
    assert items["camera_transport"]["status"] == "fail"


def test_build_system_precheck_reports_prod_win_alignment_without_device_access(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", lambda: object())
    report = build_system_precheck(
        profile_name="prod_win",
        storage={
            "sqlite_path": str(tmp_path / "prod.sqlite3"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={"dataset_path": "examples/replay"},
        adapters={"camera": "hik_gige_mvs", "temp": "lu92xx_modbus_rtu", "plc": "modbus_tcp"},
        camera={
            "transport": "gige_vision",
            "sdk": "hik_mvs",
            "probe_mode": "protocol_any",
            "allowed_models": [],
            "serial_number": "",
            "ip": "",
            **_real_hardware_camera_roi_sections(),
        },
        run_config=_locked_alignment_run_config(),
        vision_config=_locked_alignment_vision_config(),
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "warn"
    assert items["real_offline_pixel_alignment"]["status"] == "ok"
    assert "origin=(512, 342)" in items["real_offline_pixel_alignment"]["detail"]
    assert "size=(2048, 1364)" in items["real_offline_pixel_alignment"]["detail"]
    assert "preview_display=816x544" in items["real_offline_pixel_alignment"]["detail"]
    assert "vision=dark_on_light/adaptive" in items["real_offline_pixel_alignment"]["detail"]
    assert "tracking=continue_on_invalid" in items["real_offline_pixel_alignment"]["detail"]
    assert "ab_points=formal target-contour point_a_px/point_b_px" in items["real_offline_pixel_alignment"]["detail"]
    assert items["camera_sdk_runtime"]["status"] == "ok"


def test_build_system_precheck_protocol_any_keeps_identity_optional(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", lambda: object())
    report = build_system_precheck(
        profile_name="dev_lab",
        storage={
            "sqlite_path": str(tmp_path / "lab.sqlite3"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={"dataset_path": "examples/replay"},
        adapters={"camera": "hik_gige_mvs", "temp": "modbus_temp", "plc": "mock"},
        camera={
            "transport": "gige_vision",
            "sdk": "hik_mvs",
            "probe_mode": "protocol_any",
            "allowed_models": [],
            "serial_number": "",
            "ip": "",
            **_real_hardware_camera_roi_sections(),
        },
        run_config=_locked_alignment_run_config(),
        vision_config=_locked_alignment_vision_config(),
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "warn"
    assert items["camera_probe_mode"]["status"] == "ok"
    assert items["camera_model_policy"]["status"] == "pending"
    assert items["camera_identity"]["status"] == "pending"
    assert items["camera_sdk_runtime"]["status"] == "ok"
    assert "does not attempt live device access" in items["camera_sdk_runtime"]["detail"]


def test_build_system_precheck_warns_when_sdk_runtime_is_not_ready(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_import() -> object:
        raise RuntimeError("Hik MVS SDK Python binding MvCameraControl_class is not importable on this machine.")

    monkeypatch.setattr(precheck_module, "import_hik_mvs_sdk_module", fake_import)

    report = build_system_precheck(
        profile_name="dev_lab",
        storage={
            "sqlite_path": str(tmp_path / "lab.sqlite3"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={"dataset_path": "examples/replay"},
        adapters={"camera": "hik_gige_mvs", "temp": "modbus_temp", "plc": "mock"},
        camera={
            "transport": "gige_vision",
            "sdk": "hik_mvs",
            "probe_mode": "protocol_any",
            "allowed_models": [],
            "serial_number": "",
            "ip": "",
            **_real_hardware_camera_roi_sections(),
        },
        run_config=_locked_alignment_run_config(),
        vision_config=_locked_alignment_vision_config(),
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "warn"
    assert items["camera_sdk_runtime"]["status"] == "warn"
    assert "import readiness" in items["camera_sdk_runtime"]["detail"]


def test_build_system_precheck_accepts_offline_capture_and_reports_pixel_alignment(tmp_path: Path) -> None:
    report = build_system_precheck(
        profile_name="dev_offline_capture",
        storage={
            "sqlite_path": str(tmp_path / "offline.sqlite3"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={},
        adapters={"camera": "offline_capture", "temp": "offline_capture", "plc": "mock"},
        camera=_offline_capture_camera_roi_sections(),
        run_config=_locked_alignment_run_config(),
        vision_config=_locked_alignment_vision_config(),
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "warn"
    assert items["camera_backend"]["status"] == "ok"
    assert items["real_offline_pixel_alignment"]["status"] == "ok"
    assert "offline truth contract" in items["real_offline_pixel_alignment"]["detail"]


def test_build_system_precheck_fails_when_active_profile_pixels_drift(tmp_path: Path) -> None:
    report = build_system_precheck(
        profile_name="dev_lab",
        storage={
            "sqlite_path": str(tmp_path / "lab.sqlite3"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={},
        adapters={"camera": "hik_gige_mvs", "temp": "mock", "plc": "mock"},
        camera={
            "transport": "gige_vision",
            "sdk": "hik_mvs",
            "probe_mode": "protocol_any",
            "allowed_models": [],
            "serial_number": "",
            "ip": "",
            "setup_preview": {"device_roi": {"x": 512, "y": 342, "width": 2048, "height": 1364}},
            "measurement": {"device_roi": {"x": 512, "y": 342, "width": 1024, "height": 768}},
        },
        run_config={"preview_display_max_width": 816, "preview_display_max_height": 544},
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "fail"
    assert items["real_offline_pixel_alignment"]["status"] == "fail"
    assert "preset and live run would use different source pixels" in items["real_offline_pixel_alignment"]["detail"]


def test_build_system_precheck_requires_vision_for_locked_profile_alignment(tmp_path: Path) -> None:
    report = build_system_precheck(
        profile_name="dev_lab",
        storage={
            "sqlite_path": str(tmp_path / "lab.sqlite3"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={},
        adapters={"camera": "hik_gige_mvs", "temp": "mock", "plc": "mock"},
        camera={
            "transport": "gige_vision",
            "sdk": "hik_mvs",
            "probe_mode": "protocol_any",
            "allowed_models": [],
            "serial_number": "",
            "ip": "",
            **_real_hardware_camera_roi_sections(),
        },
        run_config=_locked_alignment_run_config(),
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "fail"
    assert items["real_offline_pixel_alignment"]["status"] == "fail"
    assert "must provide vision settings" in items["real_offline_pixel_alignment"]["detail"]


def test_build_system_precheck_requires_tracking_for_locked_profile_alignment(tmp_path: Path) -> None:
    report = build_system_precheck(
        profile_name="dev_lab",
        storage={
            "sqlite_path": str(tmp_path / "lab.sqlite3"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={},
        adapters={"camera": "hik_gige_mvs", "temp": "mock", "plc": "mock"},
        camera={
            "transport": "gige_vision",
            "sdk": "hik_mvs",
            "probe_mode": "protocol_any",
            "allowed_models": [],
            "serial_number": "",
            "ip": "",
            **_real_hardware_camera_roi_sections(),
        },
        vision_config=_locked_alignment_vision_config(),
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "fail"
    assert items["real_offline_pixel_alignment"]["status"] == "fail"
    assert "must provide tracking policy" in items["real_offline_pixel_alignment"]["detail"]


def _real_hardware_camera_roi_sections() -> dict[str, dict[str, object]]:
    device_roi = {"x": 512, "y": 342, "width": 2048, "height": 1364}
    acquisition = {"pixel_format": "mono8", "exposure_us": 50000, "gain_db": 12.0}
    return {
        "setup_preview": {"device_roi": dict(device_roi), **acquisition},
        "measurement": {"device_roi": dict(device_roi), **acquisition},
    }


def _offline_capture_camera_roi_sections() -> dict[str, dict[str, object]]:
    device_roi = {"x": 0, "y": 0, "width": 2048, "height": 1364}
    acquisition = {"pixel_format": "mono8", "exposure_us": 50000, "gain_db": 12.0}
    return {
        "setup_preview": {"device_roi": dict(device_roi), **acquisition},
        "measurement": {"device_roi": dict(device_roi), **acquisition},
    }


def _locked_alignment_run_config() -> dict[str, int]:
    return {
        "preview_display_max_width": 816,
        "preview_display_max_height": 544,
        "stop_on_invalid_tracking": False,
        "invalid_tracking_grace_samples": 5,
        "debug_locked_points_tracking": False,
    }


def _locked_alignment_vision_config() -> dict[str, object]:
    return {
        "foreground_polarity": "dark_on_light",
        "threshold_mode": "adaptive",
        "edge_threshold": 10.0,
        "ignore_internal_texture": False,
        "min_target_area_px": 200,
        "quality_threshold": 0.75,
    }
