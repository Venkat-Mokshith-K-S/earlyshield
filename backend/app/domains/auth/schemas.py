"""Pydantic schemas for the `auth` domain."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import BCRYPT_MAX_PASSWORD_BYTES
from app.domains.auth.models import UserRole
from app.shared.schemas import ORMBaseSchema


def _validate_new_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = Field(min_length=1, max_length=100)

    _check_password = field_validator("password")(_validate_new_password)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name cannot be blank")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class UserProfile(ORMBaseSchema):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    _check_new_password = field_validator("new_password")(_validate_new_password)


class AdminUpdateUserRequest(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
