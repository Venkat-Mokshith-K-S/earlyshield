"""Pydantic schemas for the `recovery` domain."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.shared.schemas import ORMBaseSchema


class SuspendedProcess(BaseModel):
    pid: int
    name: str
    suspended_at: datetime
    incident_id: Optional[uuid.UUID] = None


class RecoveryStatusResponse(BaseModel):
    auto_response: bool
    auto_suspend: bool
    confidence_threshold: float
    vault_path: str
    files_protected: int
    versions_stored: int
    vault_size_bytes: int
    quarantined_files: int
    suspended_processes: List[SuspendedProcess]
    active_incident_id: Optional[uuid.UUID] = None


class RecoverySettingsUpdate(BaseModel):
    auto_response: Optional[bool] = None
    auto_suspend: Optional[bool] = None
    confidence_threshold: Optional[float] = Field(default=None, ge=0.5, le=1.0)


class RecoveryActionOut(ORMBaseSchema):
    id: uuid.UUID
    created_at: datetime
    incident_id: Optional[uuid.UUID] = None
    action_type: str
    status: str
    target: Optional[str] = None
    detail: str
    triggered_by: str


class ProtectedFile(BaseModel):
    path: str
    versions: int
    latest_captured_at: Optional[datetime] = None
    exists: bool


class RestoreRequest(BaseModel):
    paths: List[str] = Field(..., min_length=1, max_length=500, description="Absolute paths inside the watched directory")
    before: Optional[datetime] = Field(
        None, description="Only use versions captured before this time (e.g. when an attack began)"
    )


class RestoreResult(BaseModel):
    restored: int
    skipped: int
    failed: int
