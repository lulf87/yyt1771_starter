"""Minimal runtime entry point for the web application."""

from __future__ import annotations

import argparse
import threading
import webbrowser

import uvicorn

from src.webapp.app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the YYT1771 web application.")
    parser.add_argument("--profile", default="dev_lab", help="Profile name from configs/<profile>.yaml")
    parser.add_argument("--host", default=None, help="Override the configured host for this process only")
    parser.add_argument("--port", type=int, default=None, help="Override the configured port for this process only")
    parser.add_argument("--open-browser", action="store_true", help="Open the Web workstation in the default browser")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    app = create_app(profile=args.profile)
    runtime_config = app.state.runtime_config
    host = str(args.host or runtime_config.webapp.host)
    port = int(args.port or runtime_config.webapp.port)
    if args.open_browser:
        _schedule_browser_open(host=host, port=port)
    uvicorn.run(app, host=host, port=port)


def browser_url_for_server(*, host: str, port: int) -> str:
    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::", ""} else host
    return f"http://{browser_host}:{int(port)}/"


def _schedule_browser_open(*, host: str, port: int) -> None:
    url = browser_url_for_server(host=host, port=port)
    timer = threading.Timer(1.0, lambda: webbrowser.open(url))
    timer.daemon = True
    timer.start()


if __name__ == "__main__":
    main()
