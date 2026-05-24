"""FastAPI application factory for the frozen web architecture."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.application.container import ApplicationContainer
from src.application.runtime_config import load_runtime_config
from src.desktop_app.qt_runtime import bootstrap_desktop_runtime
from src.webapp.routes.debug import router as debug_router
from src.webapp.routes.health import router as health_router
from src.webapp.routes.live_run import router as live_run_router
from src.webapp.routes.profile import router as profile_router
from src.webapp.routes.session import router as session_router
from src.webapp.routes.ui import router as ui_router


def create_app(profile: str = "dev_lab") -> FastAPI:
    # Reuse the desktop-side runtime bootstrap so the web shell can discover the
    # locally staged Hik MVS Python bindings and dylibs in real/lab mode.
    bootstrap_desktop_runtime()
    runtime_config = load_runtime_config(profile)
    container = ApplicationContainer(runtime_config)
    static_dir = Path(__file__).resolve().parent / "static"
    app = FastAPI(title="YYT1771 Web API")
    app.state.application_container = container
    app.state.profile_name = container.profile_name
    app.state.profile = container.profile_name
    app.state.runtime_config = container.runtime_config
    # Keep legacy state aliases during the desktop transition so current tests
    # and thin web routes can continue to patch individual services directly.
    app.state.live_run_registry = container.live_run_registry
    app.state.live_preview_service = container.live_preview_service
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(ui_router)
    app.include_router(health_router)
    app.include_router(profile_router)
    app.include_router(debug_router)
    app.include_router(live_run_router)
    app.include_router(session_router)
    return app
