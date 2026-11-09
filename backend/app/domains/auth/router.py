"""Router for the `auth` domain."""

import uuid
from typing import Dict, List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import get_logger
from app.domains.auth import oauth
from app.domains.auth.dependencies import get_current_user, require_roles
from app.domains.auth.models import User, UserRole
from app.domains.auth.schemas import (
    AdminUpdateUserRequest,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserProfile,
)
from app.domains.auth.service import AuthService
from app.shared.schemas import APIResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = get_logger(__name__)


@router.post(
    "/register",
    response_model=APIResponse[UserProfile],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
    description="The first account ever registered becomes `admin`; later accounts start as `analyst`.",
)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> APIResponse[UserProfile]:
    user = AuthService.register(db, data)
    return APIResponse(message="Account created", data=UserProfile.model_validate(user))


@router.post("/login", response_model=APIResponse[TokenResponse], summary="Exchange credentials for tokens")
def login(data: LoginRequest, db: Session = Depends(get_db)) -> APIResponse[TokenResponse]:
    tokens = AuthService.login(db, data.email, data.password)
    return APIResponse(message="Login successful", data=tokens)


@router.post("/refresh", response_model=APIResponse[TokenResponse], summary="Exchange a refresh token for new tokens")
def refresh(data: RefreshRequest, db: Session = Depends(get_db)) -> APIResponse[TokenResponse]:
    tokens = AuthService.refresh(db, data.refresh_token)
    return APIResponse(message="Token refreshed", data=tokens)


@router.get("/me", response_model=APIResponse[UserProfile], summary="Get the current user's profile")
def get_me(user: User = Depends(get_current_user)) -> APIResponse[UserProfile]:
    return APIResponse(message="Profile retrieved", data=UserProfile.model_validate(user))


@router.patch("/me", response_model=APIResponse[UserProfile], summary="Update the current user's profile")
def update_me(
    data: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[UserProfile]:
    updated = AuthService.update_profile(db, user, data)
    return APIResponse(message="Profile updated", data=UserProfile.model_validate(updated))


@router.post(
    "/me/change-password",
    response_model=APIResponse[TokenResponse],
    summary="Change password",
    description="Revokes every previously issued token and returns a fresh pair for the caller.",
)
def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIResponse[TokenResponse]:
    tokens = AuthService.change_password(db, user, data)
    return APIResponse(message="Password changed", data=tokens)


@router.get(
    "/users",
    response_model=APIResponse[List[UserProfile]],
    summary="List all users (admin only)",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def list_users(db: Session = Depends(get_db)) -> APIResponse[List[UserProfile]]:
    users = AuthService.list_users(db)
    return APIResponse(
        message=f"Retrieved {len(users)} users",
        data=[UserProfile.model_validate(u) for u in users],
    )


@router.patch(
    "/users/{user_id}",
    response_model=APIResponse[UserProfile],
    summary="Change a user's role or active status (admin only)",
)
def admin_update_user(
    user_id: uuid.UUID,
    data: AdminUpdateUserRequest,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> APIResponse[UserProfile]:
    updated = AuthService.admin_update_user(db, admin, user_id, data)
    return APIResponse(message="User updated", data=UserProfile.model_validate(updated))


# --- Sign in with Google / GitHub (see oauth.py for the flow) ---------------

_OAUTH_COOKIE_PATH = f"{settings.API_V1_PREFIX}/auth/oauth"


def _to_login_with_error(code: str) -> RedirectResponse:
    response = RedirectResponse(oauth.frontend_url(f"/login?{urlencode({'oauth_error': code})}"), status_code=303)
    response.delete_cookie(oauth.STATE_COOKIE, path=_OAUTH_COOKIE_PATH)
    return response


@router.get(
    "/oauth/providers",
    response_model=APIResponse[Dict[str, bool]],
    summary="Which social sign-in providers are configured",
)
def oauth_providers() -> APIResponse[Dict[str, bool]]:
    return APIResponse(message="OAuth providers", data=oauth.enabled_providers())


@router.get("/oauth/{provider}/login", summary="Start signing in with Google or GitHub", include_in_schema=True)
def oauth_login(provider: str) -> RedirectResponse:
    try:
        p = oauth.get_provider(provider)
    except oauth.OAuthError as exc:
        return _to_login_with_error(exc.code)
    state, nonce = oauth.new_state(provider)
    response = RedirectResponse(oauth.authorize_url(p, state), status_code=303)
    response.set_cookie(
        oauth.STATE_COOKIE,
        nonce,
        max_age=int(oauth.STATE_LIFETIME.total_seconds()),
        path=_OAUTH_COOKIE_PATH,
        httponly=True,
        # Lax: the cookie must come back on the provider's top-level redirect.
        samesite="lax",
        secure=settings.PUBLIC_URL.startswith("https://"),
    )
    return response


@router.get("/oauth/{provider}/callback", summary="Provider redirects here after sign-in")
def oauth_callback(
    provider: str,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    nonce: Optional[str] = Cookie(None, alias=oauth.STATE_COOKIE),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        oauth.get_provider(provider)
        if error:
            # e.g. the user pressed "Cancel" on the consent screen
            raise oauth.OAuthError("cancelled" if error == "access_denied" else "provider_error", error)
        oauth.check_state(state, provider, nonce)
        if not code:
            raise oauth.OAuthError("provider_error", "no code")
        identity = oauth.fetch_identity(provider, code)
        tokens = oauth.sign_in(db, identity, provider)
    except oauth.OAuthError as exc:
        logger.warning("%s sign-in failed: %s (%s)", provider, exc.code, exc)
        return _to_login_with_error(exc.code)

    fragment = urlencode({"access_token": tokens.access_token, "refresh_token": tokens.refresh_token})
    response = RedirectResponse(oauth.frontend_url(f"/oauth/callback#{fragment}"), status_code=303)
    response.delete_cookie(oauth.STATE_COOKIE, path=_OAUTH_COOKIE_PATH)
    return response
