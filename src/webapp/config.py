"""Lightweight runtime profile loading for the web application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class WebAppConfig:
    host: str
    port: int


@dataclass(slots=True)
class RuntimeConfig:
    profile: str
    platform: str
    mode: str
    webapp: WebAppConfig
    adapters: dict[str, str]
    storage: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "platform": self.platform,
            "mode": self.mode,
            "webapp": {
                "host": self.webapp.host,
                "port": self.webapp.port,
            },
            "adapters": dict(self.adapters),
        }


def load_runtime_config(profile: str) -> RuntimeConfig:
    config_path = _project_root() / "configs" / f"{profile}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Profile config not found: {config_path}")

    raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw_config, dict):
        raise ValueError(f"Invalid profile config format: {config_path}")

    webapp = raw_config.get("webapp")
    adapters = raw_config.get("adapters")
    if not isinstance(webapp, dict) or not isinstance(adapters, dict):
        raise ValueError(f"Profile config missing required sections: {config_path}")

    return RuntimeConfig(
        profile=str(raw_config.get("profile", profile)),
        platform=str(raw_config["platform"]),
        mode=str(raw_config["mode"]),
        webapp=WebAppConfig(
            host=str(webapp["host"]),
            port=int(webapp["port"]),
        ),
        adapters={str(name): str(value) for name, value in adapters.items()},
        storage=_normalize_mapping(raw_config.get("storage")),
        logging=_normalize_mapping(raw_config.get("logging")),
    )


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _normalize_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(name): item for name, item in value.items()}
