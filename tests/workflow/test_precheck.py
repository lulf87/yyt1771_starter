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
        project_root=Path(__file__).resolve().parents[2],
    )

    assert report["profile"] == "dev_mock"
    assert report["status"] == "warn"
    items = {item["name"]: item for item in report["items"]}
    assert items["sqlite_path"]["status"] == "ok"
    assert items["artifact_dir"]["status"] == "ok"
    assert items["replay_dataset"]["status"] == "ok"
    assert items["camera_adapter"]["status"] == "pending"


def test_build_system_precheck_returns_fail_when_storage_missing() -> None:
    report = build_system_precheck(
        profile_name="broken",
        storage={},
        replay={},
        adapters={"camera": "", "temp": "", "plc": ""},
        project_root=Path(__file__).resolve().parents[2],
    )

    assert report["status"] == "fail"
    items = {item["name"]: item for item in report["items"]}
    assert items["sqlite_path"]["status"] == "fail"
    assert items["artifact_dir"]["status"] == "fail"
    assert items["replay_dataset"]["status"] == "warn"
    assert items["camera_adapter"]["status"] == "fail"
