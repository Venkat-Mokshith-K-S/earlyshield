"""
Password hashing and JWT token primitives.

Kept free of any database or domain knowledge — the auth domain's service
layer decides *who* gets a token; this module only knows *how* to make and
verify one.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

TokenType = Literal["access", "refresh"]

# bcrypt only looks at the first 72 bytes of a password; anything longer is
# silently truncated by older libraries and rejected outright by bcrypt>=4.1.
# The schema layer enforces this limit so users get a clear error instead.
BCRYPT_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# A real bcrypt hash of a random string. Verifying against it when the
# email doesn't exist makes a failed login take the same time whether or
# not the account exists, so response timing can't be used to enumerate
# registered emails.
DUMMY_PASSWORD_HASH = hash_password(uuid.uuid4().hex)


def create_token(subject: uuid.UUID, token_type: TokenType, token_version: int) -> tuple[str, int]:
    """Return (encoded_jwt, lifetime_in_seconds)."""
    if token_type == "access":
        lifetime = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        lifetime = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "type": token_type,
        # Bumped on password change; any token minted before that is rejected.
        "ver": token_version,
        "iat": now,
        "exp": now + lifetime,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "type", "ver", "exp"]},
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired", {"reason": "expired"})
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid authentication token", {"reason": "invalid"})

    # Stops a long-lived refresh token from being used as an access token.
    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid authentication token", {"reason": "wrong_token_type"})
    return payload
