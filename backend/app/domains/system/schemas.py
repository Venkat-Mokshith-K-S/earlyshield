"""Pydantic schemas for the `system` domain (health checks, version/project info)."""

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: str
    environment: str
    database_connected: bool


class VersionResponse(BaseModel):
    project_name: str
    project_full_title: str
    version: str
