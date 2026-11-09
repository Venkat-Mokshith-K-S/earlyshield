"""Service layer for the `auth` domain."""

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.rate_limit import FailureLimiter
from app.core.logging_config import get_logger
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domains.auth.models import User, UserRole
from app.domains.auth.schemas import (
    AdminUpdateUserRequest,
    ChangePasswordRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
)

logger = get_logger(__name__)

_login_limiter = FailureLimiter(settings.LOGIN_MAX_FAILURES, settings.LOGIN_LOCKOUT_MINUTES * 60)


class AuthService:
    @staticmethod
    def _issue_tokens(user: User) -> TokenResponse:
        access_token, expires_in = create_token(user.id, "access", user.token_version)
        refresh_token, _ = create_token(user.id, "refresh", user.token_version)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in)

    @staticmethod
    def _get_by_email(db: Session, email: str) -> User | None:
        return db.scalar(select(User).where(User.email == email.lower()))

    @staticmethod
    def role_for_new_user(db: Session) -> UserRole:
        # Bootstrap: the very first account becomes the admin, so a fresh
        # deployment never needs a manual DB edit to get someone who can
        # manage users. Everyone after that starts as an analyst. Shared by
        # password registration and Google/GitHub sign-in.
        is_first_user = db.scalar(select(func.count()).select_from(User)) == 0
        return UserRole.ADMIN if is_first_user else UserRole.ANALYST

    @staticmethod
    def register(db: Session, data: RegisterRequest) -> User:
        if AuthService._get_by_email(db, data.email):
            raise ConflictError("An account with this email already exists")

        role = AuthService.role_for_new_user(db)
        user = User(
            email=data.email.lower(),
            full_name=data.full_name,
            password_hash=hash_password(data.password),
            role=role.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Registered user %s with role '%s'", user.id, user.role)
        return user

    @staticmethod
    def login(db: Session, email: str, password: str) -> TokenResponse:
        # Keyed by account, not IP: guessing one account's password is slowed
        # down however many addresses the guesses come from. The cost is that
        # someone can lock an account for LOGIN_LOCKOUT_MINUTES on purpose.
        key = email.lower()
        _login_limiter.check(key)
        user = AuthService._get_by_email(db, email)
        if user is None:
            verify_password(password, DUMMY_PASSWORD_HASH)
            _login_limiter.record_failure(key)
            raise UnauthorizedError("Invalid email or password")
        if not verify_password(password, user.password_hash):
            _login_limiter.record_failure(key)
            raise UnauthorizedError("Invalid email or password")
        _login_limiter.reset(key)
        if not user.is_active:
            raise ForbiddenError("This account has been deactivated")

        user.last_login = datetime.now(timezone.utc)
        db.commit()
        return AuthService._issue_tokens(user)

    @staticmethod
    def _load_user_from_token(db: Session, token: str, token_type: str) -> User:
        payload = decode_token(token, token_type)  # type: ignore[arg-type]
        try:
            user_id = uuid.UUID(payload["sub"])
        except ValueError:
            raise UnauthorizedError("Invalid authentication token", {"reason": "invalid"})

        user = db.get(User, user_id)
        if user is None or payload["ver"] != user.token_version:
            raise UnauthorizedError("Invalid authentication token", {"reason": "revoked"})
        if not user.is_active:
            raise ForbiddenError("This account has been deactivated")
        return user

    @staticmethod
    def get_user_from_access_token(db: Session, token: str) -> User:
        return AuthService._load_user_from_token(db, token, "access")

    @staticmethod
    def refresh(db: Session, refresh_token: str) -> TokenResponse:
        user = AuthService._load_user_from_token(db, refresh_token, "refresh")
        return AuthService._issue_tokens(user)

    @staticmethod
    def update_profile(db: Session, user: User, data: UpdateProfileRequest) -> User:
        if data.full_name is not None:
            user.full_name = data.full_name.strip()
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def change_password(db: Session, user: User, data: ChangePasswordRequest) -> TokenResponse:
        if not verify_password(data.current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect")
        user.password_hash = hash_password(data.new_password)
        # Invalidates every token issued before now (other browsers/devices).
        user.token_version += 1
        db.commit()
        db.refresh(user)
        logger.info("User %s changed their password; existing sessions revoked", user.id)
        return AuthService._issue_tokens(user)

    @staticmethod
    def list_users(db: Session) -> List[User]:
        return list(db.scalars(select(User).order_by(User.created_at)))

    @staticmethod
    def admin_update_user(db: Session, acting_admin: User, user_id: uuid.UUID, data: AdminUpdateUserRequest) -> User:
        user = db.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found")

        # An admin demoting or deactivating themselves could leave the system
        # with no admin at all, and there's no UI path back from that.
        if user.id == acting_admin.id and (
            (data.role is not None and data.role != UserRole.ADMIN) or data.is_active is False
        ):
            raise ForbiddenError("Admins cannot demote or deactivate their own account")

        if data.role is not None:
            user.role = data.role.value
        if data.is_active is not None:
            user.is_active = data.is_active
        db.commit()
        db.refresh(user)
        logger.info("Admin %s updated user %s: %s", acting_admin.id, user.id, data.model_dump(exclude_none=True))
        return user
