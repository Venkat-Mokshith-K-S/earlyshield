"""
Sign in with Google / GitHub. The provider round-trip is replaced by a stub
(`oauth.fetch_identity`); everything on our side (state, cookie, account
lookup, token hand-off) runs for real.
"""

from urllib.parse import parse_qs, urlparse

import pytest

from app.core.config import settings
from app.domains.auth import oauth

API = "/api/v1"


@pytest.fixture()
def providers(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "gid")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "gsecret")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "PUBLIC_URL", "http://localhost:5173")


def stub_identity(monkeypatch, email="new@gmail.com", name="New Person"):
    calls = []

    def fake(provider, code):
        calls.append((provider, code))
        return oauth.Identity(email=email, name=name)

    monkeypatch.setattr(oauth, "fetch_identity", fake)
    return calls


def start(client, provider="google"):
    res = client.get(f"{API}/auth/oauth/{provider}/login", follow_redirects=False)
    assert res.status_code == 303
    return res, parse_qs(urlparse(res.headers["location"]).query)


def finish(client, provider, state, code="abc"):
    res = client.get(f"{API}/auth/oauth/{provider}/callback", params={"code": code, "state": state},
                     follow_redirects=False)
    assert res.status_code == 303
    return res.headers["location"]


def tokens_from(location):
    assert location.startswith("http://localhost:5173/oauth/callback#"), location
    return {k: v[0] for k, v in parse_qs(urlparse(location).fragment).items()}


def test_providers_endpoint_reports_only_configured(client, providers):
    data = client.get(f"{API}/auth/oauth/providers").json()["data"]
    assert data == {"google": True, "github": False}


def test_login_redirects_to_google_with_state_and_cookie(client, providers):
    res, query = start(client)
    assert res.headers["location"].startswith("https://accounts.google.com/")
    assert query["client_id"] == ["gid"]
    assert query["redirect_uri"] == ["http://localhost:5173/api/v1/auth/oauth/google/callback"]
    assert "state" in query
    assert oauth.STATE_COOKIE in res.cookies


def test_unconfigured_provider_goes_back_to_login(client, providers):
    res = client.get(f"{API}/auth/oauth/github/login", follow_redirects=False)
    assert res.headers["location"] == "http://localhost:5173/login?oauth_error=not_configured"


def test_new_user_is_created_and_signed_in(client, providers, monkeypatch):
    calls = stub_identity(monkeypatch)
    _, query = start(client)
    tokens = tokens_from(finish(client, "google", query["state"][0]))
    assert calls == [("google", "abc")]

    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}).json()["data"]
    assert me["email"] == "new@gmail.com"
    assert me["full_name"] == "New Person"
    assert me["role"] == "admin"  # first account on a fresh install, same rule as registration


def test_existing_account_is_reused_by_verified_email(client, providers, monkeypatch):
    client.post(f"{API}/auth/register", json={"email": "Me@Gmail.com", "password": "password123", "full_name": "Me"})
    stub_identity(monkeypatch, email="me@gmail.com", name="Someone Else")
    _, query = start(client)
    tokens = tokens_from(finish(client, "google", query["state"][0]))
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}).json()["data"]
    assert me["full_name"] == "Me"  # same account, not a duplicate
    assert len(client.get(f"{API}/auth/users", headers={"Authorization": f"Bearer {tokens['access_token']}"})
               .json()["data"]) == 1


def test_callback_without_our_cookie_is_refused(client, providers, monkeypatch):
    """Login CSRF: a state minted in the attacker's browser must not work in the victim's."""
    calls = stub_identity(monkeypatch)
    _, query = start(client)
    client.cookies.clear()
    location = finish(client, "google", query["state"][0])
    assert location.endswith("/login?oauth_error=invalid_state")
    assert calls == []  # never even talked to the provider


def test_tampered_or_cross_provider_state_is_refused(client, providers, monkeypatch):
    stub_identity(monkeypatch)
    _, query = start(client)
    assert finish(client, "google", query["state"][0] + "x").endswith("oauth_error=invalid_state")
    state, nonce = oauth.new_state("github")
    client.cookies.set(oauth.STATE_COOKIE, nonce, path="/api/v1/auth/oauth")
    assert finish(client, "google", state).endswith("oauth_error=invalid_state")


def test_user_cancelling_at_provider(client, providers):
    res = client.get(f"{API}/auth/oauth/google/callback", params={"error": "access_denied"}, follow_redirects=False)
    assert res.headers["location"].endswith("oauth_error=cancelled")


def test_unverified_email_and_deactivated_account_are_refused(client, providers, monkeypatch):
    def unverified(provider, code):
        raise oauth.OAuthError("email_not_verified")

    monkeypatch.setattr(oauth, "fetch_identity", unverified)
    _, query = start(client)
    assert finish(client, "google", query["state"][0]).endswith("oauth_error=email_not_verified")

    # Deactivated account: admin first, then the target user is deactivated.
    client.post(f"{API}/auth/register", json={"email": "admin@x.com", "password": "password123", "full_name": "A"})
    client.post(f"{API}/auth/register", json={"email": "gone@gmail.com", "password": "password123", "full_name": "G"})
    admin = client.post(f"{API}/auth/login", json={"email": "admin@x.com", "password": "password123"}).json()["data"]
    h = {"Authorization": f"Bearer {admin['access_token']}"}
    target = next(u for u in client.get(f"{API}/auth/users", headers=h).json()["data"] if u["email"] == "gone@gmail.com")
    client.patch(f"{API}/auth/users/{target['id']}", headers=h, json={"is_active": False})

    stub_identity(monkeypatch, email="gone@gmail.com")
    _, query = start(client)
    assert finish(client, "google", query["state"][0]).endswith("oauth_error=account_deactivated")
