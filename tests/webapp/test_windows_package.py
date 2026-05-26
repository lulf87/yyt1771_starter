import json
import zipfile
from pathlib import Path

import pytest

from src.webapp.windows_package import assemble_windows_zip, load_prereq_manifest


def test_load_prereq_manifest_requires_all_official_installers(tmp_path: Path) -> None:
    prereq_dir = tmp_path / "prereqs"
    prereq_dir.mkdir()
    (prereq_dir / "mvs.exe").write_bytes(b"mvs")
    (prereq_dir / "vc.exe").write_bytes(b"vc")
    (prereq_dir / "prereqs_manifest.json").write_text(
        json.dumps(
            {
                "entries": [
                    {"key": "hik_mvs", "label": "Hik MVS", "filename": "mvs.exe"},
                    {"key": "vc_redist_x64", "label": "VC++", "filename": "vc.exe"},
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="usb_serial"):
        load_prereq_manifest(prereq_dir)


def test_assemble_windows_zip_contains_launcher_prereqs_and_manifest(tmp_path: Path) -> None:
    app_dir = tmp_path / "app-build"
    app_dir.mkdir()
    (app_dir / "yyt1771-webstation.exe").write_bytes(b"fake exe")
    prereq_dir = tmp_path / "prereqs"
    prereq_dir.mkdir()
    for filename, payload in {
        "mvs.exe": b"mvs",
        "vc.exe": b"vc",
        "usb.exe": b"usb",
    }.items():
        (prereq_dir / filename).write_bytes(payload)
    (prereq_dir / "prereqs_manifest.json").write_text(
        json.dumps(
            {
                "entries": [
                    {"key": "hik_mvs", "label": "Hik MVS", "filename": "mvs.exe"},
                    {"key": "vc_redist_x64", "label": "VC++", "filename": "vc.exe", "install_args": ["/quiet"]},
                    {"key": "usb_serial", "label": "USB Serial", "filename": "usb.exe"},
                ]
            }
        ),
        encoding="utf-8",
    )

    zip_path = assemble_windows_zip(
        app_dir=app_dir,
        prereq_dir=prereq_dir,
        output_dir=tmp_path / "out",
        package_name="pkg",
    )

    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        assert "pkg/install_yyt1771.bat" in names
        assert "pkg/start_yyt1771.bat" in names
        assert "pkg/stop_yyt1771.bat" in names
        assert "pkg/安装与启动说明.md" in names
        assert "pkg/app/yyt1771-webstation.exe" in names
        assert "pkg/app/configs/dev_lab.yaml" in names
        assert "pkg/app/configs/dev_offline_capture.yaml" in names
        assert not any(name.endswith(".local.yaml") for name in names)
        assert "pkg/app/launcher/install_prereqs.ps1" in names
        assert "pkg/prereqs/mvs.exe" in names
        assert "pkg/prereqs/vc.exe" in names
        assert "pkg/prereqs/usb.exe" in names
        package_manifest = json.loads(archive.read("pkg/manifest.json").decode("utf-8"))
        assert package_manifest["profile"] == "dev_lab"
        assert package_manifest["camera_identity_policy"]["probe_mode"] == "protocol_any"
        assert package_manifest["camera_identity_policy"]["serial_number"] == ""
        prereq_manifest = json.loads(archive.read("pkg/prereqs/manifest.json").decode("utf-8"))
        assert {entry["key"] for entry in prereq_manifest["entries"]} == {
            "hik_mvs",
            "vc_redist_x64",
            "usb_serial",
        }
        assert all(entry["sha256"] for entry in prereq_manifest["entries"])
