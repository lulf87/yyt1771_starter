import os
from pathlib import Path
import sys
import builtins
from types import SimpleNamespace

import pytest

from src.desktop_app.main import _run_benchmark_with_diagnostics, bootstrap_desktop_runtime, build_parser, main


def test_desktop_main_parser_defaults_to_dev_lab() -> None:
    parser = build_parser()

    args = parser.parse_args([])

    assert args.profile == "dev_lab"
    assert args.qt_preview_benchmark is False
    assert args.target_preview_fps is None
    assert args.preview_poll_ms is None
    assert args.setup_preview_roi_width is None
    assert args.setup_preview_roi_height is None


def test_bootstrap_desktop_runtime_prepends_vendor_sys_path(monkeypatch) -> None:
    original_path = list(sys.path)
    try:
        vendor_a = str(Path("/tmp/vendor-a"))
        vendor_b = str(Path("/tmp/vendor-b"))
        monkeypatch.setenv("YYT1771_DESKTOP_EXTRA_SYS_PATH", os.pathsep.join([vendor_a, vendor_b]))
        monkeypatch.setattr("src.desktop_app.qt_runtime.find_pyside6_qt_root", lambda: None)

        bootstrap_desktop_runtime()

        assert sys.path[0] == vendor_a
        assert sys.path[1] == vendor_b
    finally:
        sys.path[:] = original_path


def test_bootstrap_desktop_runtime_configures_qt_plugin_paths(monkeypatch, tmp_path: Path) -> None:
    qt_root = tmp_path / "PySide6" / "Qt"
    plugin_root = qt_root / "plugins"
    platform_root = plugin_root / "platforms"
    platform_root.mkdir(parents=True)
    monkeypatch.delenv("QT_PLUGIN_PATH", raising=False)
    monkeypatch.delenv("QT_QPA_PLATFORM_PLUGIN_PATH", raising=False)
    monkeypatch.setattr("src.desktop_app.qt_runtime.find_pyside6_qt_root", lambda: qt_root)

    bootstrap_desktop_runtime()

    assert os.environ["QT_PLUGIN_PATH"].split(os.pathsep)[0] == str(plugin_root)
    assert os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] == str(platform_root)


def test_bootstrap_desktop_runtime_injects_local_hik_mvs_paths(monkeypatch, tmp_path: Path) -> None:
    original_path = list(sys.path)
    sdk_python_dir = tmp_path / "MvImport"
    sdk_python_dir.mkdir(parents=True)
    runtime_lib_dir = tmp_path / "runtime-lib"
    runtime_lib_dir.mkdir(parents=True)
    sdk_library = runtime_lib_dir / "libMvCameraControl.dylib"
    sdk_library.write_text("", encoding="utf-8")
    for library_name in (
        "libMVGigEVisionSDK.dylib",
        "libMVU3VisionSDK.dylib",
        "libMediaProcess.dylib",
    ):
        (runtime_lib_dir / library_name).write_text("", encoding="utf-8")
    staging_dir = tmp_path / "tmp-mvs"
    monkeypatch.delenv("HIK_MVS_PYTHON_PATH", raising=False)
    monkeypatch.delenv("HIK_MVS_LIBRARY_PATH", raising=False)
    monkeypatch.setattr("src.desktop_app.qt_runtime.find_pyside6_qt_root", lambda: None)
    monkeypatch.setattr("src.desktop_app.qt_runtime._find_local_hik_mvs_python_path", lambda: sdk_python_dir)
    monkeypatch.setattr("src.desktop_app.qt_runtime._find_local_hik_mvs_library_path", lambda: sdk_library)
    monkeypatch.setattr("src.desktop_app.qt_runtime.HIK_MVS_SIDE_CAR_STAGING_DIR", staging_dir)

    try:
        bootstrap_desktop_runtime()
        assert os.environ["HIK_MVS_PYTHON_PATH"] == str(sdk_python_dir)
        assert os.environ["HIK_MVS_LIBRARY_PATH"] == str(sdk_library)
        assert sys.path[0] == str(sdk_python_dir)
        assert (staging_dir / "libMVGigEVisionSDK.dylib").is_symlink()
        assert (staging_dir / "libMVU3VisionSDK.dylib").is_symlink()
        assert (staging_dir / "libMediaProcess.dylib").is_symlink()
    finally:
        sys.path[:] = original_path


def test_desktop_main_smoke_run_succeeds_without_pyside6(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["yyt1771-desktop", "--profile", "dev_mock", "--smoke-run"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"profile": "dev_mock"' in captured.out
    assert '"run_status": "completed"' in captured.out


def test_desktop_main_preview_benchmark_succeeds_without_pyside6(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "yyt1771-desktop",
            "--profile",
            "dev_mock",
            "--preview-benchmark",
            "--duration-s",
            "0.2",
            "--target-preview-fps",
            "50",
            "--preview-poll-ms",
            "20",
            "--setup-preview-roi-width",
            "512",
            "--setup-preview-roi-height",
            "512",
        ],
    )

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"profile": "dev_mock"' in captured.out
    assert '"measured_presented_fps"' in captured.out
    assert '"target_preview_fps": 50.0' in captured.out
    assert '"preview_poll_ms": 20' in captured.out


def test_apply_preview_benchmark_overrides_can_set_setup_preview_roi() -> None:
    from src.desktop_app.main import _apply_preview_benchmark_overrides
    from src.desktop_app.controller import build_desktop_app_context

    context = build_desktop_app_context(profile="dev_mock")

    _apply_preview_benchmark_overrides(
        context,
        target_preview_fps=50.0,
        preview_poll_ms=20,
        setup_preview_roi_x=1,
        setup_preview_roi_y=2,
        setup_preview_roi_width=512,
        setup_preview_roi_height=384,
    )

    assert context.runtime_config.live.run.preview_target_fps == 50.0
    assert context.runtime_config.live.run.preview_poll_ms == 20
    assert context.runtime_config.live.camera.setup_preview.device_roi.x == 1
    assert context.runtime_config.live.camera.setup_preview.device_roi.y == 2
    assert context.runtime_config.live.camera.setup_preview.device_roi.width == 512
    assert context.runtime_config.live.camera.setup_preview.device_roi.height == 384


def test_run_benchmark_with_diagnostics_includes_camera_probe_on_failure() -> None:
    controller = SimpleNamespace(
        context=SimpleNamespace(profile="dev_lab"),
        probe_camera=lambda: {"status": "fail", "error_code": "DEVICE_DISCOVERY_FAILED"},
    )

    exit_code, payload = _run_benchmark_with_diagnostics(
        controller,
        lambda: (_ for _ in ()).throw(RuntimeError("preview benchmark failed")),
    )

    assert exit_code == 1
    assert payload["status"] == "fail"
    assert payload["profile"] == "dev_lab"
    assert payload["error"] == "preview benchmark failed"
    assert payload["camera_probe"]["error_code"] == "DEVICE_DISCOVERY_FAILED"


def test_desktop_main_exits_with_clear_message_when_pyside6_is_missing(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["yyt1771-desktop", "--profile", "dev_mock"])
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "PySide6.QtWidgets":
            raise ModuleNotFoundError("No module named 'PySide6'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(SystemExit, match="PySide6 is not installed"):
        main()
