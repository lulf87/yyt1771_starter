"""Request and response models for the web application layer."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    profile: str
