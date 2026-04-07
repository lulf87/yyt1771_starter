"""Desktop workstation entry point."""

from __future__ import annotations

import argparse
import json
from tempfile import TemporaryDirectory
from typing import Any

from src.desktop_app.controller import DesktopWorkbenchController, build_desktop_app_context
from src.desktop_app.qt_runtime import bootstrap_desktop_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the YYT1771 desktop workstation.")
    parser.add_argument("--profile", default="dev_lab", help="Profile name from configs/<profile>.yaml")
    parser.add_argument(
        "--smoke-run",
        action="store_true",
        help="Run the minimum desktop bootstrap flow without launching Qt.",
    )
    parser.add_argument(
        "--preview-benchmark",
        action="store_true",
        help="Run a headless preview benchmark without launching Qt.",
    )
    parser.add_argument(
        "--qt-preview-benchmark",
        action="store_true",
        help="Run a Qt-driven preview benchmark through the desktop window event loop.",
    )
    parser.add_argument(
        "--duration-s",
        type=float,
        default=1.5,
        help="Duration for headless preview benchmarking.",
    )
    parser.add_argument(
        "--target-preview-fps",
        type=float,
        default=None,
        help="Override preview target fps for benchmark modes.",
    )
    parser.add_argument(
        "--preview-poll-ms",
        type=int,
        default=None,
        help="Override preview poll interval for benchmark modes.",
    )
    parser.add_argument("--setup-preview-roi-x", type=int, default=None, help="Override setup-preview ROI x.")
    parser.add_argument("--setup-preview-roi-y", type=int, default=None, help="Override setup-preview ROI y.")
    parser.add_argument(
        "--setup-preview-roi-width",
        type=int,
        default=None,
        help="Override setup-preview ROI width for benchmark modes.",
    )
    parser.add_argument(
        "--setup-preview-roi-height",
        type=int,
        default=None,
        help="Override setup-preview ROI height for benchmark modes.",
    )
    return parser


def run_qt_preview_benchmark(
    *,
    controller: DesktopWorkbenchController,
    duration_s: float,
) -> dict[str, object]:
    bootstrap_desktop_runtime()
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PySide6 is not installed. Install the desktop extra first, for example: "
            "`pip install -e .[desktop]`"
        ) from exc

    from src.desktop_app.window import DesktopMainWindow

    app = QApplication.instance() or QApplication([])
    window = DesktopMainWindow(controller=controller)
    summary: dict[str, object] = {}

    def _finish() -> None:
        try:
            if window.current_run_id:
                window._handle_stop_preview()
            summary.update(window.preview_benchmark_summary())
        finally:
            window.close()
            app.quit()

    window._handle_create_run()
    window._handle_start_preview()
    QTimer.singleShot(max(50, int(duration_s * 1000)), _finish)
    app.exec()
    return summary


def _apply_preview_benchmark_overrides(
    context,
    *,
    target_preview_fps: float | None,
    preview_poll_ms: int | None,
    setup_preview_roi_x: int | None,
    setup_preview_roi_y: int | None,
    setup_preview_roi_width: int | None,
    setup_preview_roi_height: int | None,
) -> None:
    if target_preview_fps is not None:
        context.runtime_config.live.run.preview_target_fps = target_preview_fps
    if preview_poll_ms is not None:
        context.runtime_config.live.run.preview_poll_ms = preview_poll_ms
    setup_preview_roi = context.runtime_config.live.camera.setup_preview.device_roi
    if setup_preview_roi_x is not None:
        setup_preview_roi.x = setup_preview_roi_x
    if setup_preview_roi_y is not None:
        setup_preview_roi.y = setup_preview_roi_y
    if setup_preview_roi_width is not None:
        setup_preview_roi.width = setup_preview_roi_width
    if setup_preview_roi_height is not None:
        setup_preview_roi.height = setup_preview_roi_height


def _run_benchmark_with_diagnostics(
    controller: DesktopWorkbenchController,
    runner,
) -> tuple[int, dict[str, Any]]:
    try:
        return 0, runner()
    except Exception as exc:
        payload: dict[str, Any] = {
            "status": "fail",
            "profile": controller.context.profile,
            "error": str(exc),
        }
        try:
            payload["camera_probe"] = controller.probe_camera()
        except Exception as probe_exc:  # pragma: no cover - defensive diagnostics path
            payload["camera_probe_error"] = str(probe_exc)
        return 1, payload


def main() -> int:
    args = build_parser().parse_args()
    bootstrap_desktop_runtime()
    context = build_desktop_app_context(profile=args.profile)
    if args.smoke_run:
        with TemporaryDirectory(prefix="yyt1771-desktop-smoke-") as temp_dir:
            context.runtime_config.storage["sqlite_path"] = f"{temp_dir}/desktop-smoke.db"
            context.runtime_config.storage["artifact_dir"] = f"{temp_dir}/artifacts"
            controller = DesktopWorkbenchController(context)
            summary = controller.run_bootstrap_smoke()
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
            controller.preview_service.close()
        return 0
    if args.preview_benchmark:
        with TemporaryDirectory(prefix="yyt1771-desktop-preview-") as temp_dir:
            context.runtime_config.storage["sqlite_path"] = f"{temp_dir}/desktop-preview.db"
            context.runtime_config.storage["artifact_dir"] = f"{temp_dir}/artifacts"
            _apply_preview_benchmark_overrides(
                context,
                target_preview_fps=args.target_preview_fps,
                preview_poll_ms=args.preview_poll_ms,
                setup_preview_roi_x=args.setup_preview_roi_x,
                setup_preview_roi_y=args.setup_preview_roi_y,
                setup_preview_roi_width=args.setup_preview_roi_width,
                setup_preview_roi_height=args.setup_preview_roi_height,
            )
            controller = DesktopWorkbenchController(context)
            exit_code, summary = _run_benchmark_with_diagnostics(
                controller,
                lambda: controller.run_preview_benchmark(duration_s=args.duration_s),
            )
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
            controller.preview_service.close()
        return exit_code
    if args.qt_preview_benchmark:
        with TemporaryDirectory(prefix="yyt1771-desktop-qt-preview-") as temp_dir:
            context.runtime_config.storage["sqlite_path"] = f"{temp_dir}/desktop-qt-preview.db"
            context.runtime_config.storage["artifact_dir"] = f"{temp_dir}/artifacts"
            _apply_preview_benchmark_overrides(
                context,
                target_preview_fps=args.target_preview_fps,
                preview_poll_ms=args.preview_poll_ms,
                setup_preview_roi_x=args.setup_preview_roi_x,
                setup_preview_roi_y=args.setup_preview_roi_y,
                setup_preview_roi_width=args.setup_preview_roi_width,
                setup_preview_roi_height=args.setup_preview_roi_height,
            )
            controller = DesktopWorkbenchController(context)
            exit_code, summary = _run_benchmark_with_diagnostics(
                controller,
                lambda: run_qt_preview_benchmark(controller=controller, duration_s=args.duration_s),
            )
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
            controller.preview_service.close()
        return exit_code

    controller = DesktopWorkbenchController(context)

    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PySide6 is not installed. Install the desktop extra first, for example: "
            "`pip install -e .[desktop]`"
        ) from exc

    from src.desktop_app.window import DesktopMainWindow

    app = QApplication.instance() or QApplication([])
    window = DesktopMainWindow(controller=controller)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
