"""Web application entry points."""

from src.application.runtime_config import RuntimeConfig, load_runtime_config
from src.webapp.app import create_app

__all__ = ["RuntimeConfig", "create_app", "load_runtime_config"]
