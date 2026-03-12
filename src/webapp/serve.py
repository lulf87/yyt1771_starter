"""Minimal runtime entry point for the web application."""

from __future__ import annotations

import argparse

import uvicorn

from src.webapp.app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the YYT1771 web application.")
    parser.add_argument("--profile", default="dev_mock", help="Profile name from configs/<profile>.yaml")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    app = create_app(profile=args.profile)
    runtime_config = app.state.runtime_config
    uvicorn.run(app, host=runtime_config.webapp.host, port=runtime_config.webapp.port)


if __name__ == "__main__":
    main()
