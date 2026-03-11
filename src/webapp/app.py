"""FastAPI application factory for the frozen web architecture."""

from fastapi import FastAPI

from src.webapp.routes.health import router as health_router


def create_app(profile: str = "dev_mock") -> FastAPI:
    app = FastAPI(title="YYT1771 Web API")
    app.state.profile = profile
    app.include_router(health_router)
    return app
