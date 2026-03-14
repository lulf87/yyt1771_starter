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
        },
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "fail"
    assert items["camera_probe_mode"]["status"] == "ok"
    assert items["camera_model_policy"]["status"] == "ok"
    assert items["camera_transport"]["status"] == "ok"
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
        },
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "fail"
    assert items["camera_transport"]["status"] == "fail"


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
        },
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
        },
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "warn"
    assert items["camera_sdk_runtime"]["status"] == "warn"
    assert "import readiness" in items["camera_sdk_runtime"]["detail"]
