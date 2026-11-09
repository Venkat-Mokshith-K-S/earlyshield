# Module 2 — Authentication & User Management

Adds the `auth` domain: user accounts stored in Postgres, bcrypt password
hashing, JWT access/refresh tokens, and three roles that gate what each
user can do in the rest of the system.

## New/changed files

**Backend**
- **New**: `app/core/security.py` — bcrypt hashing, JWT create/decode
- **New**: `app/domains/auth/` — `models.py`, `schemas.py`, `service.py`,
  `router.py`, `dependencies.py` (`get_current_user`, `require_roles`)
- **New**: `alembic/versions/0001_create_users_table.py`
- **New**: `tests/test_auth.py`, `pytest.ini` — 12 tests, SQLite-backed
  (no Postgres needed): `cd backend && pytest -q`
- **Changed**: `detection/router.py`, `monitoring/router.py` — now require login
- **Changed**: `core/exceptions.py` — validation errors (422) use the same
  JSON envelope as every other error, so the UI shows a readable message
- **Changed**: `main.py` — auth router; refuses to boot in `production`
  with a placeholder `JWT_SECRET_KEY`
- **Changed**: `Dockerfile` — runs `alembic upgrade head` before uvicorn
- **Changed**: `requirements.txt` — see "Dependency change" below

**Frontend**
- **New**: `domains/auth/components/RouteGuards.tsx` (`RequireAuth`, `GuestOnly`),
  `shared/lib/tokenStorage.ts`
- **Changed**: `App.tsx` (routes `/login`, `/register`, `/`), `main.tsx`
  (`BrowserRouter`), `apiClient.ts` (automatic token refresh on 401),
  `TopStatusBar.tsx` (user menu), `MonitorControlPanel.tsx` (disabled for viewers)

## Roles

| Role      | Detection / model info / events | Start & stop monitor | Manage users |
|-----------|:---:|:---:|:---:|
| `admin`   | ✓ | ✓ | ✓ |
| `analyst` | ✓ | ✓ |   |
| `viewer`  | ✓ |   |   |

The **first account ever registered becomes `admin`**; everyone after starts
as `analyst`. An admin can't demote or deactivate themselves, so the system
can't end up with no admin.

## API endpoints

- `POST /api/v1/auth/register` — `{"email", "password", "full_name"}`
- `POST /api/v1/auth/login` — `{"email", "password"}` → access + refresh token
- `POST /api/v1/auth/refresh` — `{"refresh_token"}` → new token pair
- `GET  /api/v1/auth/me`, `PATCH /api/v1/auth/me` — `{"full_name"}`
- `POST /api/v1/auth/me/change-password` — returns a new token pair
- `GET  /api/v1/auth/users` (admin), `PATCH /api/v1/auth/users/{id}` — `{"role", "is_active"}` (admin)

`/system/health` and `/system/version` stay public. In Swagger
(`/api/docs`), log in, copy `access_token`, and paste it into **Authorize**.

## Security design decisions (worth citing in the report)

- **Token revocation without a blacklist.** Each user has a
  `token_version`, embedded in every JWT. Changing the password bumps it,
  which instantly invalidates every token issued before — on all devices —
  without keeping a revoked-token table.
- **Role/deactivation take effect immediately.** The user row is re-read on
  every request instead of trusting a role claim in the token, so demoting
  or deactivating someone doesn't wait for their token to expire.
- **No account enumeration.** Wrong password and unknown email return the
  identical message, and an unknown email still runs a bcrypt comparison so
  the response time doesn't reveal which emails are registered.
- **Refresh tokens can't be used as access tokens** (`type` claim is checked).
- **72-byte password limit** is validated up front (bcrypt ignores
  anything past 72 bytes).

## Dependency change

`python-jose` + `passlib` were replaced with `PyJWT` + `bcrypt`.
`passlib` is unmaintained and breaks with `bcrypt` ≥ 4.1 (which pip would
install), and `python-jose` has open CVEs. `email-validator` was added for
email validation. **Rebuild the backend image**: `docker compose up --build`.

## Known limitation

Tokens are stored in `localStorage`, which an XSS bug could read.
`httpOnly` cookies are stronger but need CSRF protection; for a
single-origin academic deployment this trade-off is acceptable and should
be stated as such.
