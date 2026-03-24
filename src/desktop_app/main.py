"""Desktop workstation entry point."""

from __future__ import annotations

import argparse

from src.desktop_app.controller import DesktopWorkbenchController, build_desktop_app_context


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the YYT1771 desktop workstation.")
    parser.add_argument("--profile", default="dev_mock", help="Profile name from configs/<profile>.yaml")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    context = build_desktop_app_context(profile=args.profile)
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
