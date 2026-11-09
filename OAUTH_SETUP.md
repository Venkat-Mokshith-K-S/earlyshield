# Sign in with Google and GitHub

The login and register pages have **Google** and **GitHub** buttons. They stay
greyed out until you give the backend a client ID and secret for each
provider. This takes about 5 minutes per provider, and only you can do it,
because the keys belong to your own Google / GitHub account.

The redirect (callback) URLs to register are:

| Running as | Google redirect URI | GitHub callback URL |
|---|---|---|
| Dev (`docker compose up`) | `http://localhost:5173/api/v1/auth/oauth/google/callback` | `http://localhost:5173/api/v1/auth/oauth/github/callback` |
| Production | `https://<your-domain>/api/v1/auth/oauth/google/callback` | `https://<your-domain>/api/v1/auth/oauth/github/callback` |

They must match **exactly** (http vs https, port, no trailing slash).

## Google

1. Open <https://console.cloud.google.com/> and create (or pick) a project.
2. **APIs & Services → OAuth consent screen**: choose *External*, fill in an
   app name (EarlyShield) and your email, then save. While the app is in
   *Testing* mode, add the Google accounts that should be able to sign in
   under **Test users**.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**
   - Application type: **Web application**
   - Authorized redirect URIs: the Google URI from the table above
4. Copy the **Client ID** and **Client secret**.

## GitHub

1. Open <https://github.com/settings/developers> → **OAuth Apps → New OAuth App**.
2. Homepage URL: `http://localhost:5173` (or your domain).
   Authorization callback URL: the GitHub URL from the table above.
3. Click **Register application**, then **Generate a new client secret**.
4. Copy the **Client ID** and the secret.

## Put the keys in

Dev: edit `backend/.env` (never commit it):

```
PUBLIC_URL=http://localhost:5173
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

then `docker compose up -d backend` (`restart` does **not** re-read `.env`; the container must be recreated). Production: put the same four
variables in the root `.env` next to `PUBLIC_ORIGIN` (see `DEPLOYMENT.md`).

Check: <http://localhost:5173/api/v1/auth/oauth/providers> should now say
`true` for each configured provider, and its button lights up.

## How it behaves

- **New email** → a new account is created with the same rule as normal
  registration (first account on a fresh install = admin, everyone after =
  analyst). An admin can change the role on the *Users* page.
- **Email that already has an account** → signs in to that account. This is
  only allowed because both providers return a **verified** email; a GitHub
  account with no verified email is refused.
- **Deactivated account** → refused, same as the password form.
- Accounts created through Google/GitHub have no password you know, so they
  always sign in through the provider (the *Change password* form won't work
  for them).

## Security notes

- The `state` parameter is a signed, 10-minute token that must also match an
  HttpOnly cookie set when sign-in started, so a sign-in link can't be
  finished in someone else's browser (login CSRF).
- The client secret never leaves the backend; the browser only ever sees the
  provider's sign-in page and our own tokens.
- Our tokens come back in the URL *fragment* (`#...`), which browsers never
  send to servers or proxies, and the page removes them from the address bar
  immediately.
- Tested in `backend/tests/test_oauth.py` (9 tests, provider calls stubbed).
