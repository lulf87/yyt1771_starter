"""Compatibility wrapper for shared runtime config loading."""

from src.application.runtime_config import RuntimeConfig, WebAppConfig, load_runtime_config

__all__ = ["RuntimeConfig", "WebAppConfig", "load_runtime_config"]
