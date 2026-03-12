"""FastAPI application factory for the frozen web architecture."""

from fastapi import FastAPI

from src.webapp.config import load_runtime_config
from src.webapp.routes.health import router as health_router
from src.webapp.routes.profile import router as profile_router


def create_app(profile: str = "dev_mock") -> FastAPI:
    runtime_config = load_runtime_config(profile)
    app = FastAPI(title="YYT1771 Web API")
    app.state.profile_name = runtime_config.profile
    app.state.profile = runtime_config.profile
    app.state.runtime_config = runtime_config
    app.include_router(health_router)
    app.include_router(profile_router)
    return app
