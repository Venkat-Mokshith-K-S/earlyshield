"""
Module 2 auth tests. Runs against a throwaway SQLite DB so it doesn't need
Postgres:  cd backend && pytest -q
"""

API = "/api/v1"


def register(client, email, password="password123", name="Test User"):
    return client.post(f"{API}/auth/register", json={"email": email, "password": password, "full_name": name})


def login(client, email, password="password123"):
    res = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["data"]


def auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_first_user_is_admin_then_analyst(client):
    assert register(client, "admin@x.com").json()["data"]["role"] == "admin"
    assert register(client, "second@x.com").json()["data"]["role"] == "analyst"


def test_duplicate_email_case_insensitive(client):
    register(client, "a@x.com")
    res = register(client, "A@X.com")
    assert res.status_code == 409
    assert res.json()["error_code"] == "CONFLICT"


def test_short_password_rejected_with_readable_message(client):
    res = register(client, "a@x.com", password="short")
    assert res.status_code == 422
    assert "at least 8" in res.json()["message"]


def test_login_and_me(client):
    register(client, "a@x.com")
    tokens = login(client, "a@x.com")
    me = client.get(f"{API}/auth/me", headers=auth(tokens)).json()["data"]
    assert me["email"] == "a@x.com"
    assert me["last_login"] is not None


def test_wrong_password_and_unknown_email_same_error(client):
    register(client, "a@x.com")
    r1 = client.post(f"{API}/auth/login", json={"email": "a@x.com", "password": "wrongpass1"})
    r2 = client.post(f"{API}/auth/login", json={"email": "nobody@x.com", "password": "wrongpass1"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["message"] == r2.json()["message"]


def test_protected_routes_require_token(client):
    assert client.get(f"{API}/detection/model-info").status_code == 401
    assert client.get(f"{API}/monitoring/status").status_code == 401
    # Health stays public so the status bar works on the login page.
    assert client.get(f"{API}/system/version").status_code == 200


def test_refresh_token_cannot_be_used_as_access_token(client):
    register(client, "a@x.com")
    tokens = login(client, "a@x.com")
    res = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert res.status_code == 401


def test_refresh_issues_working_tokens(client):
    register(client, "a@x.com")
    tokens = login(client, "a@x.com")
    new = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).json()["data"]
    assert client.get(f"{API}/auth/me", headers=auth(new)).status_code == 200


def test_change_password_revokes_old_tokens(client):
    register(client, "a@x.com")
    old = login(client, "a@x.com")
    res = client.post(
        f"{API}/auth/me/change-password",
        headers=auth(old),
        json={"current_password": "password123", "new_password": "newpassword456"},
    )
    assert res.status_code == 200
    new = res.json()["data"]
    assert client.get(f"{API}/auth/me", headers=auth(old)).status_code == 401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": old["refresh_token"]}).status_code == 401
    assert client.get(f"{API}/auth/me", headers=auth(new)).status_code == 200
    login(client, "a@x.com", "newpassword456")


def test_viewer_cannot_control_monitor(client):
    register(client, "admin@x.com")
    viewer_id = register(client, "v@x.com").json()["data"]["id"]
    admin = login(client, "admin@x.com")
    client.patch(f"{API}/auth/users/{viewer_id}", headers=auth(admin), json={"role": "viewer"})

    viewer = login(client, "v@x.com")
    assert client.get(f"{API}/monitoring/status", headers=auth(viewer)).status_code == 200
    res = client.post(f"{API}/monitoring/stop", headers=auth(viewer))
    assert res.status_code == 403
    assert res.json()["details"]["your_role"] == "viewer"


def test_admin_endpoints(client):
    register(client, "admin@x.com")
    register(client, "b@x.com")
    admin = login(client, "admin@x.com")
    analyst = login(client, "b@x.com")

    assert client.get(f"{API}/auth/users", headers=auth(analyst)).status_code == 403
    users = client.get(f"{API}/auth/users", headers=auth(admin)).json()["data"]
    assert len(users) == 2

    admin_id = users[0]["id"]
    res = client.patch(f"{API}/auth/users/{admin_id}", headers=auth(admin), json={"role": "viewer"})
    assert res.status_code == 403  # can't demote yourself


def test_deactivated_user_locked_out_immediately(client):
    register(client, "admin@x.com")
    uid = register(client, "b@x.com").json()["data"]["id"]
    admin = login(client, "admin@x.com")
    b = login(client, "b@x.com")

    client.patch(f"{API}/auth/users/{uid}", headers=auth(admin), json={"is_active": False})
    assert client.get(f"{API}/auth/me", headers=auth(b)).status_code == 403
    res = client.post(f"{API}/auth/login", json={"email": "b@x.com", "password": "password123"})
    assert res.status_code == 403


def test_repeated_failed_logins_are_throttled(client):
    from app.core.config import settings

    register(client, "a@x.com")
    for _ in range(settings.LOGIN_MAX_FAILURES):
        r = client.post(f"{API}/auth/login", json={"email": "a@x.com", "password": "wrongpass1"})
        assert r.status_code == 401
    # Even the RIGHT password is refused until the lockout passes.
    r = client.post(f"{API}/auth/login", json={"email": "A@x.com", "password": "password123"})
    assert r.status_code == 429
    assert r.json()["error_code"] == "TOO_MANY_ATTEMPTS"
    # Other accounts are unaffected.
    register(client, "b@x.com")
    login(client, "b@x.com")


def test_successful_login_resets_failure_count(client):
    from app.core.config import settings

    register(client, "a@x.com")
    for _ in range(settings.LOGIN_MAX_FAILURES - 1):
        client.post(f"{API}/auth/login", json={"email": "a@x.com", "password": "wrongpass1"})
    login(client, "a@x.com")
    for _ in range(settings.LOGIN_MAX_FAILURES - 1):
        assert client.post(f"{API}/auth/login", json={"email": "a@x.com", "password": "wrongpass1"}).status_code == 401
