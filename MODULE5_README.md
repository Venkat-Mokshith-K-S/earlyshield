# Module 5 — Secure Automated Recovery

Adds the `recovery` domain, the "Secure Automated Recovery" half of the
project title (research gap #4: integrating detection with recovery).
Detection now leads to action: EarlyShield keeps versioned shadow copies of
every watched file. When the model flags a window, it quarantines the
damaged files, restores the originals, can suspend the suspected process,
and records every step in an audit log shown on the dashboard.

## How it works

```
monitor start ──► baseline shadow copy of every file in the watched folder
benign window ──► snapshot the files that changed (backups stay current)
ransomware-like window, confidence ≥ threshold ──►
    1. suspend the attributed process        (optional, off by default)
    2. quarantine encrypted / renamed copies + new files (e.g. ransom notes)
    3. restore each original from its newest CLEAN shadow copy
    4. write every step to the recovery_actions audit log
```

The response also covers files changed in the window **before** the
detection, because an attack's first few seconds often score as benign.
While an incident is active, no new snapshots are taken, so content written
during the attack can never become a "clean" backup.

**Incident follow-up.** An incident stays open for 3 windows after the last
ransomware-like one. Within that time, a window the model scores as benign
can still hold the tail of the attack, such as a ransom note written last
or the next few files of a slow in-place encryption. During an open
incident, every window is therefore checked for:
- new files the vault has never seen (ransom notes, `.locked` copies)
- files whose entropy jumped to encrypted level (the same ≥1.5 bits/byte
  test used to pick clean backups)

Matches are quarantined and restored under the same incident ID. Any match
also keeps the incident open, so a slow attack can't simply outlast it.
Outside an incident, this check does nothing, so it adds no false
positives on normal activity. Added after the production-stack test, where
all 100 files came back but the ransom note was left behind.

## New/changed files

**Backend**
- **New**: `app/domains/recovery/` — `vault.py` (shadow-copy store),
  `process_control.py` (suspend/resume), `service.py`, `router.py`,
  `schemas.py`, `models.py`
- **New**: `alembic/versions/0002_create_recovery_actions_table.py`
- **New**: `tests/test_recovery.py` (13 tests, including a real end-to-end
  attack), `tests/conftest.py` (shared fixtures)
- **Changed**: `monitoring/service.py`:
  - hands every window to the recovery engine
  - ignores events caused by its own restores
  - records the attributed PID
  - **fixes a Module 3 bug** (see below)
- **Changed**: `monitoring/schemas.py` — `DetectionEvent` gains
  `attributed_pid` and `recovery_incident_id`
- **Changed**: `core/config.py`, `.env.example` — `RECOVERY_*` settings

**Frontend**
- **New**: `domains/recovery/` — `RecoveryPanel` (vault stats, response
  toggles, suspended processes with **Resume**, "Snapshot now") and
  `RecoveryActionLog` (audit log)
- **Changed**: `Dashboard.tsx` (shows both, plus a banner on any detection
  window that triggered a response), `monitoringApi.ts`

## What makes it "secure"

| Property | How |
|---|---|
| Backups can't be silently corrupted | Content-addressed: each blob is named by its SHA-256 and re-hashed before every restore; a tampered blob is refused |
| Backups aren't in the blast radius | Monitoring refuses to start if the vault is inside the watched folder |
| Encrypted content isn't restored as "clean" | No snapshots during an incident, plus an entropy check: a version whose entropy jumped ≥1.5 bits/byte above the file's first snapshot is skipped (this catches slow attacks the model scored as benign) |
| False positives are reversible | Files are **quarantined** (moved into the vault), never deleted; processes are **suspended**, never killed, and can be resumed from the dashboard |
| Never acts on the wrong process | Won't suspend EarlyShield itself or its parent processes, PIDs 0/1/4, a protected-name list (`RECOVERY_PROTECTED_PROCESSES`), a PID that now belongs to a different program (PID reuse), or a process that wrote nothing during the window |
| Accountability | Every action is stored in `recovery_actions`: what, target, result, incident ID, and `auto` or the user's email |
| Role-based control | Viewers can only look. Analysts can snapshot, restore and resume. Only admins can change the auto-response settings |

## API endpoints

- `GET  /api/v1/recovery/status` — vault stats, settings, suspended processes, active incident
- `PATCH /api/v1/recovery/settings` (admin) — `{"auto_response", "auto_suspend", "confidence_threshold"}`; runtime only, reverts to `.env` on restart
- `GET  /api/v1/recovery/actions?limit=50&incident_id=…` — audit log, newest first
- `GET  /api/v1/recovery/files` — files with shadow copies
- `POST /api/v1/recovery/snapshot` (analyst+) — snapshot the watched folder now
- `POST /api/v1/recovery/restore` (analyst+) — `{"paths": [...], "before": "<ISO time>"}`; only paths the vault has backed up are accepted, so it can't be used to write anywhere else
- `POST /api/v1/recovery/processes/{pid}/resume` (analyst+)

## Settings (`backend/.env`)

| Setting | Default | |
|---|---|---|
| `RECOVERY_VAULT_PATH` | `recovery_vault` | `backend/recovery_vault/` on the host under Docker; must be outside the watched folder |
| `RECOVERY_AUTO_RESPONSE` | `True` | quarantine + restore on detection |
| `RECOVERY_AUTO_SUSPEND` | `False` | see "Why auto-suspend is off by default" |
| `RECOVERY_CONFIDENCE_THRESHOLD` | `0.50` | minimum model confidence before acting (chosen from measured data: `backend/evaluation/README.md`) |
| `RECOVERY_MAX_FILE_MB` | `50` | larger files aren't shadow-copied |
| `RECOVERY_MAX_VERSIONS_PER_FILE` | `5` | older versions are pruned |

## Verified by testing (not assumed)

The end-to-end test runs the real monitor, model and recovery engine
against a temp folder. It plants 40 documents across two subfolders, then
simulates ransomware: it overwrites each file with random bytes, renames it
to `.locked`, and drops a `README_DECRYPT.txt` ransom note. The test checks
that:
- the attack is detected
- all 40 originals are restored byte-for-byte
- no `.locked` file or ransom note is left behind
- every step is in the audit log

Process suspension is stubbed in that test only. Real suspend/resume is
tested against a throwaway child process.

## Two findings from testing

**1. Module 3 bug: CPU percent above 100 crashed every window on Windows.**
psutil reports per-process CPU as a share of *one* core, so a busy process
reads 400% on a 4-core machine. On Windows, the "System Idle Process" read
~1000% and won the "most active process" sample every time. The model's
input schema rejects values above 100, so **every monitoring window on a
multi-core Windows host raised a validation error and was dropped**. Fixed
by dividing by the core count and skipping PID 0. (Under Docker on Linux
the bug was masked whenever no process exceeded one core.)

**2. Why auto-suspend is off by default.** In the end-to-end test, the
process blamed for the simulated attack was `claude.exe`, the desktop app
that happened to be busiest during that window, not the Python process
doing the encryption. This is the Module 3 attribution limitation showing
up in practice. Suspending the wrong process on a real desktop would be a
harmful false positive, so auto-suspend is opt-in (admin toggle on the
dashboard). File quarantine and restore don't depend on attribution and stay on by default.

## Known limitations (state these in the report)

- **Same-privilege attacker.** The vault is an ordinary folder. Ransomware
  running as the same OS user could find and delete it. Production systems
  use storage the attacker can't reach: Windows Volume Shadow Copy owned by
  SYSTEM, WORM/immutable object storage, or a separate backup host. This
  module shows the recovery *logic*, not tamper-proof storage.
- **Docker on Windows.** Inside the container, psutil sees only container
  processes. A Windows-side process encrypting the bind-mounted folder
  can't be suspended from there, but file quarantine and restore still work.
- **Data written between the last snapshot and detection** (at most about
  one observation window) can't be recovered. This trade-off is set by
  `window_seconds`.
- **Naturally high-entropy files** (zip, jpg, mp4) can't be told apart from
  encrypted ones by the entropy check; for those, only the
  no-snapshots-during-an-incident rule protects the backups.
