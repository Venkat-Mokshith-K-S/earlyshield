"""
Sign in with Google or GitHub (OAuth 2.0 authorization-code flow).

    browser ──► /auth/oauth/<provider>/login
                  sets a short-lived nonce cookie, redirects to the provider
    provider ──► /auth/oauth/<provider>/callback?code=…&state=…
                  checks state + cookie, swaps the code for the user's
                  verified email, finds or creates the account, then
                  redirects to PUBLIC_URL/oauth/callback#access_token=…

Security choices:
  * `state` is a signed JWT (provider + nonce, 10 min) AND must match the
    HttpOnly nonce cookie set at the start, so nobody can complete a login
    in someone else's browser (login CSRF) or replay a stale callback.
  * Only a provider-VERIFIED email is accepted. That is what makes it safe
    to sign an existing password account in by email match.
  * Our tokens go back in the URL fragment, which browsers never send to a
    server, so they don't end up in proxy or access logs. The page that
    reads them removes them from the address bar straight away.
  * Accounts created this way get a random password nobody knows, so the
    password form can't be used on them; they always sign in via provider.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Optional
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.security import hash_password
from app.domains.auth.models import User
from app.domains.auth.schemas import TokenResponse

logger = get_logger(__name__)

STATE_COOKIE = "es_oauth_nonce"
STATE_LIFETIME = timedelta(minutes=10)
HTTP_TIMEOUT = 10.0


class OAuthError(Exception):
    """Ends the flow; `code` is shown to the user on the login page."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code = code


@dataclass
class Identity:
    email: str
    name: str


@dataclass
class Provider:
    name: str
    authorize_url: str
    scope: str
    client_id: Callable[[], str]
    client_secret: Callable[[], str]
    extra_params: Dict[str, str]


PROVIDERS: Dict[str, Provider] = {
    "google": Provider(
        name="google",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        scope="openid email profile",
        client_id=lambda: settings.GOOGLE_CLIENT_ID,
        client_secret=lambda: settings.GOOGLE_CLIENT_SECRET,
        extra_params={"prompt": "select_account"},
    ),
    "github": Provider(
        name="github",
        authorize_url="https://github.com/login/oauth/authorize",
        scope="read:user user:email",
        client_id=lambda: settings.GITHUB_CLIENT_ID,
        client_secret=lambda: settings.GITHUB_CLIENT_SECRET,
        extra_params={"allow_signup": "true"},
    ),
}


def enabled_providers() -> Dict[str, bool]:
    return {name: bool(p.client_id() and p.client_secret()) for name, p in PROVIDERS.items()}


def get_provider(name: str) -> Provider:
    provider = PROVIDERS.get(name)
    if provider is None:
        raise OAuthError("unknown_provider")
    if not enabled_providers()[name]:
        raise OAuthError("not_configured")
    return provider


def redirect_uri(provider: str) -> str:
    return f"{settings.PUBLIC_URL.rstrip('/')}{settings.API_V1_PREFIX}/auth/oauth/{provider}/callback"


def frontend_url(path: str) -> str:
    return f"{settings.PUBLIC_URL.rstrip('/')}{path}"


# --- state -------------------------------------------------------------------

def new_state(provider: str) -> tuple[str, str]:
    """Returns (state for the provider, nonce for our cookie)."""
    nonce = secrets.token_urlsafe(24)
    payload = {
        "type": "oauth_state",
        "provider": provider,
        "nonce": nonce,
        "exp": datetime.now(timezone.utc) + STATE_LIFETIME,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM), nonce


def check_state(state: Optional[str], provider: str, cookie_nonce: Optional[str]) -> None:
    if not state or not cookie_nonce:
        raise OAuthError("invalid_state", "missing state or nonce cookie")
    try:
        payload = jwt.decode(state, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        raise OAuthError("invalid_state", "state signature/expiry")
    if (
        payload.get("type") != "oauth_state"
        or payload.get("provider") != provider
        or not secrets.compare_digest(str(payload.get("nonce", "")), cookie_nonce)
    ):
        raise OAuthError("invalid_state", "state does not match this browser")


def authorize_url(provider: Provider, state: str) -> str:
    params = {
        "client_id": provider.client_id(),
        "redirect_uri": redirect_uri(provider.name),
        "response_type": "code",
        "scope": provider.scope,
        "state": state,
        **provider.extra_params,
    }
    return f"{provider.authorize_url}?{urlencode(params)}"


# --- talking to the providers -------------------------------------------------

def _google_identity(client: httpx.Client, code: str) -> Identity:
    p = PROVIDERS["google"]
    token = client.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": p.client_id(),
        "client_secret": p.client_secret(),
        "redirect_uri": redirect_uri("google"),
        "grant_type": "authorization_code",
    })
    if token.status_code != 200:
        raise OAuthError("provider_error", f"google token exchange: {token.status_code}")
    access = token.json()["access_token"]
    info = client.get("https://openidconnect.googleapis.com/v1/userinfo",
                      headers={"Authorization": f"Bearer {access}"})
    if info.status_code != 200:
        raise OAuthError("provider_error", f"google userinfo: {info.status_code}")
    data = info.json()
    if not data.get("email") or not data.get("email_verified"):
        raise OAuthError("email_not_verified")
    return Identity(email=data["email"], name=data.get("name") or "")


def _github_identity(client: httpx.Client, code: str) -> Identity:
    p = PROVIDERS["github"]
    token = client.post("https://github.com/login/oauth/access_token", headers={"Accept": "application/json"}, data={
        "code": code,
        "client_id": p.client_id(),
        "client_secret": p.client_secret(),
        "redirect_uri": redirect_uri("github"),
    })
    access = token.json().get("access_token") if token.status_code == 200 else None
    if not access:
        raise OAuthError("provider_error", f"github token exchange: {token.status_code}")
    headers = {"Authorization": f"Bearer {access}", "Accept": "application/vnd.github+json"}
    user = client.get("https://api.github.com/user", headers=headers)
    emails = client.get("https://api.github.com/user/emails", headers=headers)
    if user.status_code != 200 or emails.status_code != 200:
        raise OAuthError("provider_error", "github user lookup")
    verified = [e for e in emails.json() if e.get("verified")]
    primary = next((e for e in verified if e.get("primary")), verified[0] if verified else None)
    if primary is None:
        raise OAuthError("email_not_verified")
    profile = user.json()
    return Identity(email=primary["email"], name=profile.get("name") or profile.get("login") or "")


_IDENTITY_FETCHERS = {"google": _google_identity, "github": _github_identity}


def fetch_identity(provider: str, code: str) -> Identity:
    """Swap the one-time code for the user's verified email. Tests replace this."""
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        try:
            return _IDENTITY_FETCHERS[provider](client, code)
        except httpx.HTTPError as exc:
            raise OAuthError("provider_error", f"{provider}: {exc}")


# --- accounts ------------------------------------------------------------------

def sign_in(db: Session, identity: Identity, provider: str) -> TokenResponse:
    # Imported here: service.py is the auth domain's entry point and
    # shouldn't depend on this module just to be imported.
    from app.domains.auth.service import AuthService

    email = identity.email.lower()
    user = AuthService._get_by_email(db, email)
    if user is None:
        name = (identity.name or email.split("@")[0]).strip()[:100] or "User"
        user = User(
            email=email,
            full_name=name,
            # Random and never shown: this account signs in via the provider.
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=AuthService.role_for_new_user(db).value,
        )
        db.add(user)
        db.flush()
        logger.info("Created user %s via %s sign-in with role '%s'", user.id, provider, user.role)
    if not user.is_active:
        raise OAuthError("account_deactivated")

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    logger.info("User %s signed in with %s", user.id, provider)
    return AuthService._issue_tokens(user)

