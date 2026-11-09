"""ORM models for the `auth` domain."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.base_model import TimestampedBase


class UserRole(str, enum.Enum):
    # admin   — everything, plus user management
    # analyst — run/stop the live monitor and analyze activity
    # viewer  — read-only access to detections and model info
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(TimestampedBase, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Stored as a plain string (not a native PG enum) so adding a role later
    # doesn't need an ALTER TYPE migration.
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.ANALYST.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
