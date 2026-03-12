"""Dependency helpers for the web application layer."""

from fastapi import Request

from src.webapp.config import RuntimeConfig


def get_profile_name(request: Request) -> str:
    return str(request.app.state.profile_name)


def get_runtime_config(request: Request) -> RuntimeConfig:
    return request.app.state.runtime_config
