"""Dependency helpers for the web application layer."""

from fastapi import Request


def get_profile(request: Request) -> str:
    return str(request.app.state.profile)
