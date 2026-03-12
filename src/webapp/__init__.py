"""Web application entry points."""

from src.webapp.app import create_app
from src.webapp.config import RuntimeConfig, load_runtime_config

__all__ = ["RuntimeConfig", "create_app", "load_runtime_config"]
