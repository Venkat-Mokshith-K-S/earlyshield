"""ORM models for the `recovery` domain."""

import enum
import uuid
from typing import Optional

from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.base_model import TimestampedBase


class RecoveryActionType(str, enum.Enum):
    BASELINE_SNAPSHOT = "baseline_snapshot"
    MANUAL_SNAPSHOT = "manual_snapshot"
    SUSPEND_PROCESS = "suspend_process"
    RESUME_PROCESS = "resume_process"
    QUARANTINE_FILE = "quarantine_file"
    RESTORE_FILE = "restore_file"
    INCIDENT_SUMMARY = "incident_summary"


class RecoveryActionStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RecoveryAction(TimestampedBase, Base):
    """Append-only audit log of everything the recovery engine (or a user) did."""

    __tablename__ = "recovery_actions"

    # Groups all the actions taken in response to one detection.
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    target: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # "auto" for the recovery engine, otherwise the acting user's email.
    triggered_by: Mapped[str] = mapped_column(String(255), nullable=False, default="auto")
    extra: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
