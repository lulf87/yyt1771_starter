"""Dependency helpers for the web application layer."""

from fastapi import Depends, Request

from src.storage.sqlite_repo import SqliteSessionRepo
from src.webapp.config import RuntimeConfig
from src.workflow.session import WorkflowSessionRunner


def get_profile_name(request: Request) -> str:
    return str(request.app.state.profile_name)


def get_runtime_config(request: Request) -> RuntimeConfig:
    return request.app.state.runtime_config


def get_session_repo(request: Request) -> SqliteSessionRepo:
    runtime_config = get_runtime_config(request)
    sqlite_path = runtime_config.storage.get("sqlite_path")
    if not sqlite_path:
        raise ValueError("runtime_config.storage.sqlite_path is required")
    return SqliteSessionRepo(sqlite_path)


def get_session_runner(repo: SqliteSessionRepo = Depends(get_session_repo)) -> WorkflowSessionRunner:
    return WorkflowSessionRunner(repo=repo)
