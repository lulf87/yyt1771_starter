from pathlib import Path

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


def test_build_system_precheck_warns_when_gige_identity_is_missing(tmp_path: Path) -> None:
    report = build_system_precheck(
        profile_name="prod_win",
        storage={
            "sqlite_path": str(tmp_path / "prod.sqlite3"),
            "artifact_dir": str(tmp_path / "artifacts"),
        },
        replay={"dataset_path": "examples/replay"},
        adapters={"camera": "hik_gige_mvs", "temp": "modbus_temp", "plc": "modbus_tcp"},
        camera={
            "model": "MV-CU060-10GM",
            "transport": "gige_vision",
            "sdk": "hik_mvs",
            "serial_number": "",
            "ip": "",
        },
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "warn"
    assert items["camera_model"]["status"] == "ok"
    assert items["camera_transport"]["status"] == "ok"
    assert items["camera_identity"]["status"] == "warn"
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
            "model": "MV-CU060-10GM",
            "transport": "rtsp",
            "sdk": "hik_mvs",
            "serial_number": "MV-123",
        },
        project_root=Path(__file__).resolve().parents[2],
    )

    items = {item["name"]: item for item in report["items"]}
    assert report["status"] == "fail"
    assert items["camera_transport"]["status"] == "fail"
