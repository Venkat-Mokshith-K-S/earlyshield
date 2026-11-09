# Deploying EarlyShield

The development setup (`docker compose up`) is for building and demos. For a
real deployment, layer `docker-compose.prod.yml` on top: HTTPS only, the
database and API not reachable from outside, secrets from `.env`, code baked
into the image, and the recovery vault in its own volume.

## 1. Prerequisites

- A Linux host (or Windows/macOS with Docker Desktop) with Docker Compose v2.24+
  (the override file uses `!reset` / `!override`)
- A DNS name pointing at the host, if it will be reached from other machines
- Ports 80 and 443 free

## 2. Secrets

```bash
cp .env.production.example .env
python -c "import secrets;print(secrets.token_urlsafe(32))"   # use for POSTGRES_PASSWORD
python -c "import secrets;print(secrets.token_urlsafe(48))"   # use for JWT_SECRET_KEY
```

- Put the first value in `.env` as `POSTGRES_PASSWORD`, and set `PUBLIC_ORIGIN`
  and `WATCH_DIR`.
- Put the second value in `backend/.env` as `JWT_SECRET_KEY`. The backend
  **refuses to start** in production with a placeholder or short secret.
- `.env` and `backend/.env` are git-ignored and excluded from the Docker image.

## 3. TLS certificates

nginx expects `fullchain.pem` and `privkey.pem` in `./certs` (or `TLS_CERT_DIR`).

**Real domain:** use Let's Encrypt (e.g. `certbot certonly --standalone -d
earlyshield.example.org`) and copy or link the two files into `./certs`.

**Internal / lab use:** a self-signed certificate (browsers will warn once):

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout certs/privkey.pem -out certs/fullchain.pem -subj "/CN=localhost"
```

## 4. Start

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps   # all (healthy)
```

Open `PUBLIC_ORIGIN` and **register the first account immediately**. The first
account becomes admin. Change roles of later accounts on the **Users** page.

## 5. What production mode changes

| | Development | Production |
|---|---|---|
| Reachable from outside | frontend 5173, API 8000, Postgres 5432 | only nginx 80 (redirects) and 443 |
| Transport | HTTP | HTTPS (TLS 1.2/1.3), HSTS, CSP and anti-framing headers |
| Backend code | your folder mounted live | baked into the image |
| API docs (`/api/docs`) | on | off |
| JWT secret | warning if weak | refuses to start if weak |
| Database password | `earlyshield` | from `.env` |
| Recovery vault | `backend/recovery_vault/` | Docker volume `vault_data`, mounted at `/vault` |
| Login guessing | throttled (10 failures / 15 min per account) | same |

## 6. Operating it

- **One backend process only.** The file monitor, the login throttle and the
  recovery state live in the backend's memory, so run exactly one backend
  container with uvicorn's default single worker. Scaling out would need that
  state moved to a shared store such as Redis.
- **Back up the database** (users and the recovery audit log):
  `docker compose exec postgres pg_dump -U earlyshield earlyshield_db > backup.sql`
- **Back up the vault volume** if you need shadow copies to survive losing the host.
- **Upgrades:** pull the new code, then run the same `up -d --build`. Database
  migrations run automatically when the backend starts.
- **Logs:** `docker compose logs -f backend`. Every recovery action is also
  in the dashboard's Recovery log.

## 7. Known limits (unchanged by production mode)

- Ransomware running as **root/administrator on the host** can still reach the
  vault volume. Stronger isolation means a separate backup host or immutable
  (WORM) object storage.
- **Process suspension** only reaches processes inside the backend container.
  To protect a host folder against host processes, run the backend natively
  on the host instead of in Docker (see the README's non-Docker instructions).
- Polling-based watching adds up to 1 s of delay; on a native Linux host set
  `FILE_MONITOR_USE_POLLING=false` to use inotify.
