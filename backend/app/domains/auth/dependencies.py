"""
FastAPI dependencies other domains use to require authentication.

    router = APIRouter(dependencies=[Depends(get_current_user)])        # any logged-in user
    @router.post(..., dependencies=[Depends(require_roles(UserRole.ADMIN))])
"""

from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.domains.auth.models import User, UserRole
from app.domains.auth.service import AuthService

# auto_error=False so a missing header goes through our own UnauthorizedError
# (and the standard JSON error envelope) rather than FastAPI's bare 403.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Not authenticated", {"reason": "missing_token"})
    return AuthService.get_user_from_access_token(db, credentials.credentials)


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    allowed = {r.value for r in roles}

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise ForbiddenError(
                "You do not have permission to perform this action",
                {"required_roles": sorted(allowed), "your_role": user.role},
            )
        return user

    return _checker
