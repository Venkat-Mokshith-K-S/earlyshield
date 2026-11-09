# EarlyShield

**An Explainable Behavioral Machine Learning Framework for Early Ransomware
Detection and Secure Automated Recovery**

5-Credit B.Tech Mini Project (CSS7102), Presidency University, Bengaluru.
Guide: Ms. Neha Seirah Biju, Assistant Professor.

## Research grounding

This project was formally proposed and approved with the intent of
developing it into a research publication. It explicitly addresses six
research gaps in existing ransomware-detection approaches:

1. Early detection **before** significant file encryption occurs.
2. Detection of previously unseen / zero-day variants using behavioral
   features rather than static signatures.
3. Explainability and transparency of the ML decision (XAI) — every alert
   comes with a human-readable justification, not just a label.
4. Integration of detection with automated, secure recovery.
5. Reducing false positives while maintaining high detection accuracy.
6. Evaluating effectiveness under real-time/near-real-time conditions.

See `/ml/README.md` for the detection model's methodology, the synthetic
data justification, and real evaluation metrics (96.79% accuracy, F1
0.968, ROC-AUC 0.98 — verified, not fabricated).

## Repository layout

```
earlyshield/
├── backend/            FastAPI application (domain-driven: router → service → schemas)
│   └── app/domains/system/    reference implementation — health/version
├── frontend/           React + TypeScript + Vite + Tailwind
│   └── src/domains/system/    mirrors the backend's system domain
├── ml/                 Detection model training pipeline (Module 4)
├── docker-compose.yml  Postgres + backend + frontend orchestration
└── README.md
```

## The domain pattern

**Backend**, per domain: `router.py` (HTTP only) → `service.py` (business
logic) → `schemas.py` (Pydantic I/O). Register with one line in
`app/main.py`.

**Frontend**, per domain: `api/` (axios calls) → `hooks/` (React Query) →
`components/` (presentational).

## Running locally (Docker)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```
- Frontend: http://localhost:5173 (landing page; dashboard at `/dashboard`)
- API docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/v1/system/health

## Running locally (without Docker)

**Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

## Verified working (this build)

- Backend boots cleanly; `/api/v1/system/health` and `/api/v1/system/version`
  both tested live, correctly returning project name/title and graceful
  `degraded` status when Postgres is unreachable.
- Frontend: `npm install` → `tsc -b` → `vite build` all pass clean, with the
  path-alias and stale-config bugs from the previous build pre-fixed from
  the start this time.
- Full stack tested together: built frontend bundle correctly calls the
  live backend end-to-end.

## Status

- **Module 1 (this delivery): Architecture & Foundation** — done, tested.
- **Module 2: Authentication & User Management** — done, tested. See `MODULE2_README.md`.
- **Module 3: Real-Time File System Monitor** (Watchdog/Psutil) — done. See `MODULE3_README.md`.
- **Module 4: ML Detection Engine + XAI** — integrated (96.79% accuracy, SHAP explainability).
- **Module 5: Secure Automated Recovery** — done, tested end-to-end against a simulated
  encrypt-and-rename attack. See `MODULE5_README.md`.
- **Sign in with Google / GitHub** (OAuth 2.0, optional) — see `OAUTH_SETUP.md`.
- **Landing page + redesigned UI** — public landing page at `/`; light console theme.
- **Frontend dashboard** — detection, monitoring, recovery panels and audit log, plus
  Protected files (manual restore), Users (admin role management) and Account
  (profile, change password) pages.
- **Real-time evaluation** (research gaps #1 and #6) — done, 225 live trials in total.
  Final run (90 trials, fresh corpora, threshold 0.50): 33/36 attacks detected, zero files
  lost for burst, throttled and copy-then-delete attacks, no false alarm on 7 ordinary
  workloads, median time to detection 5.3 s. With incident follow-up added, a further
  36 attack trials were all detected with zero files lost and no artifacts left.
  Known limits: slow in-place encryption sits on the decision boundary (3/9 missed in
  the 90-trial run), and gzip archiving still triggers a (reversible) response.
  See `backend/evaluation/README.md`.
- **Production deployment** — HTTPS nginx, secrets from `.env`, login throttling,
  API docs off in production. See `DEPLOYMENT.md`.
- **Future work:** training on sandboxed real-ransomware traces, kernel-level
  process attribution, tamper-proof vault storage.
