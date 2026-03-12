"""FastAPI application factory for the frozen web architecture."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.webapp.config import load_runtime_config
from src.webapp.routes.health import router as health_router
from src.webapp.routes.profile import router as profile_router
from src.webapp.routes.session import router as session_router
from src.webapp.routes.ui import router as ui_router


def create_app(profile: str = "dev_mock") -> FastAPI:
    runtime_config = load_runtime_config(profile)
    static_dir = Path(__file__).resolve().parent / "static"
    app = FastAPI(title="YYT1771 Web API")
    app.state.profile_name = runtime_config.profile
    app.state.profile = runtime_config.profile
    app.state.runtime_config = runtime_config
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(ui_router)
    app.include_router(health_router)
    app.include_router(profile_router)
    app.include_router(session_router)
    return app
