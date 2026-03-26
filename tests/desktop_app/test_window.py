import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

def test_desktop_main_window_bootstrap_preview_smoke(tmp_path: Path) -> None:
    script = textwrap.dedent(
        f"""
        import json
        from pathlib import Path
        from src.desktop_app.controller import DesktopWorkbenchController, build_desktop_app_context
        from src.desktop_app.main import bootstrap_desktop_runtime

        bootstrap_desktop_runtime()

        from PySide6.QtWidgets import QApplication
        from src.desktop_app.window import DesktopMainWindow

        app = QApplication.instance() or QApplication([])
        context = build_desktop_app_context(profile="dev_mock")
        context.runtime_config.storage["sqlite_path"] = {str(tmp_path / "desktop-window.db")!r}
        context.runtime_config.storage["artifact_dir"] = {str(tmp_path / "desktop-window-artifacts")!r}
        controller = DesktopWorkbenchController(context)
        window = DesktopMainWindow(controller=controller)

        try:
            window._handle_create_run()
            window._handle_start_preview()
            app.processEvents()
            window._handle_stop_preview()
            app.processEvents()
            print(json.dumps({{
                "current_run_id": window.current_run_id,
                "preview_meta": window.preview_meta_label.text(),
                "has_bitmap": window.preview_canvas.has_preview_bitmap(),
            }}))
        finally:
            controller.preview_service.close()
            window.close()
        """
    )
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = env.get("QT_QPA_PLATFORM", "offscreen")
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(Path(__file__).resolve().parents[2]),
        env=env,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0 and "Could not find the Qt platform plugin" in result.stderr:
        pytest.skip("PySide6 runtime is installed, but QPA platform plugins cannot initialize on this machine.")

    assert result.returncode == 0, result.stderr
    assert '"current_run_id": "run-' in result.stdout
    assert '"has_bitmap": true' in result.stdout.lower()
    assert '"preview_meta": "Preview: ' in result.stdout


def test_desktop_main_window_uses_target_preview_fps_for_timer(tmp_path: Path) -> None:
    script = textwrap.dedent(
        f"""
        import json
        from src.desktop_app.controller import DesktopWorkbenchController, build_desktop_app_context
        from src.desktop_app.main import bootstrap_desktop_runtime

        bootstrap_desktop_runtime()

        from PySide6.QtWidgets import QApplication
        from src.desktop_app.window import DesktopMainWindow

        app = QApplication.instance() or QApplication([])
        context = build_desktop_app_context(profile="dev_mock")
        context.runtime_config.storage["sqlite_path"] = {str(tmp_path / "desktop-window-fps.db")!r}
        context.runtime_config.storage["artifact_dir"] = {str(tmp_path / "desktop-window-fps-artifacts")!r}
        context.runtime_config.live.run.preview_target_fps = 50.0
        controller = DesktopWorkbenchController(context)
        window = DesktopMainWindow(controller=controller)
        try:
            print(json.dumps({{"timer_interval_ms": window._preview_timer.interval()}}))
        finally:
            controller.preview_service.close()
            window.close()
        """
    )
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = env.get("QT_QPA_PLATFORM", "offscreen")
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(Path(__file__).resolve().parents[2]),
        env=env,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0 and "Could not find the Qt platform plugin" in result.stderr:
        pytest.skip("PySide6 runtime is installed, but QPA platform plugins cannot initialize on this machine.")

    assert result.returncode == 0, result.stderr
    assert '"timer_interval_ms": 20' in result.stdout


def test_desktop_main_qt_preview_benchmark_cli_outputs_summary(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = env.get("QT_QPA_PLATFORM", "offscreen")
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.desktop_app.main",
            "--profile",
            "dev_mock",
            "--qt-preview-benchmark",
            "--duration-s",
            "0.25",
            "--target-preview-fps",
            "50",
            "--preview-poll-ms",
            "20",
        ],
        cwd=str(Path(__file__).resolve().parents[2]),
        env=env,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0 and "Could not find the Qt platform plugin" in result.stderr:
        pytest.skip("PySide6 runtime is installed, but QPA platform plugins cannot initialize on this machine.")

    assert result.returncode == 0, result.stderr
    assert '"stream_presented_frames":' in result.stdout
    assert '"measured_presented_fps":' in result.stdout
    assert '"preview_display_fps":' in result.stdout
    assert '"target_preview_fps": 50.0' in result.stdout
    assert '"preview_poll_ms": 20' in result.stdout
