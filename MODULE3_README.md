# Module 3 — Real-Time File System Monitor

Adds the `monitoring` domain: watches a directory in real time using
Watchdog, computes the same 11 behavioral features the detection model
was trained on, and feeds them to the `detection` domain automatically
on a fixed interval.

## New/changed files

- **New**: `backend/app/domains/monitoring/` (schemas.py, service.py, router.py)
- **Changed**: `backend/app/domains/detection/service.py` — added a
  `warm_up()` method (see "Bug #2" below)
- **Changed**: `backend/app/main.py` — includes the new monitoring router,
  and calls `DetectionService.warm_up()` at startup

No changes needed to `requirements.txt` — `watchdog` and `psutil` were
already included from Module 1.

## API endpoints

- `POST /api/v1/monitoring/start` — `{"watch_path": "...", "window_seconds": 10}`
- `POST /api/v1/monitoring/stop`
- `GET /api/v1/monitoring/status`
- `GET /api/v1/monitoring/events?limit=20` — recent detection results, newest first

## Known limitation — process attribution (stated honestly, not hidden)

Attributing a specific file change to the specific process that caused it
requires kernel-level hooks (ETW on Windows, fanotify/audit on Linux) —
the kind of access real EDR products use. Pure Python, cross-platform
tooling cannot do this precisely. This service instead approximates "the
responsible process" as whichever process had the highest combined CPU +
disk-write activity during the observation window. This is a defensible
academic approximation and should be described as such in your report —
not claimed as precise process-level attribution.

## Two real bugs found and fixed during end-to-end testing

Both were caught by actually simulating an encrypt-then-rename ransomware
pattern (`os.urandom()` overwrite + rename to `.locked`) against a live
running instance — not just written and assumed correct.

**Bug #1 — stale path after rename.** A common ransomware pattern is
write-encrypted-content-then-rename. Reading a file's entropy from its
*original* path at window-end fails once it's been renamed away (the path
no longer exists). Fixed by resolving rename chains within each window
(`_resolve_final_path`) and reading from each file's stable *final* path,
not its original one.

**Bug #2 — unpredictable first-detection latency.** The Random Forest
model and SHAP explainer are ~13MB combined and take ~1.2 seconds to
deserialize on first use (16ms once warm). Left lazy, this entire delay
would land unpredictably on whichever request happens to be first — for
the monitoring domain, that meant the very first observation window could
take over a second longer than every subsequent one. Fixed by adding
`DetectionService.warm_up()`, called once at application startup, so the
model is already loaded before any real detection is needed.

## Testing this locally

```bash
curl -X POST http://localhost:8000/api/v1/monitoring/start \
  -H "Content-Type: application/json" \
  -d '{"watch_path": "/watched", "window_seconds": 10}'
```

To point this at a real folder on your Windows machine (rather than a
path inside the container), add a volume mount to `docker-compose.yml`
under the `backend` service:

```yaml
  backend:
    ...
    volumes:
      - ./backend:/app
      - ./watched_folder:/watched   # add this line
```

Then create a `watched_folder/` next to `docker-compose.yml`, drop files
into it from Windows Explorer, and use `"watch_path": "/watched"` in the
`/monitoring/start` request. `GET /api/v1/monitoring/events` will show
live detection results as you edit files in that folder.

## Later fixes (found by the Module 5 tests and the real-time evaluation)

The real-time benchmark (`backend/evaluation/`) and the Module 5
end-to-end test exposed six feature-extraction bugs. These fixes
change *how features are computed*, not the model:

- **CPU > 100% crashed every window on multi-core Windows.** psutil reports
  per-process CPU per core; it's now normalized to share-of-machine and
  the System Idle Process (PID 0) is skipped.
- **Baselines were taken after encryption**, so `entropy_delta` stayed 0
  and `avg_size_change_ratio` stayed 1.0 for attacked files. They're now
  seeded for every file at monitor start and carried across renames.
- **Created files didn't count** toward the modification rate, so
  copy-then-delete ransomware was invisible. They count now, and
  `a.txt.enc` (created) is paired with `a.txt` (deleted).
- **`read_write_ratio` was always 0.** It read an already-overwritten baseline.
- **Windows were ~2× longer than configured.** The loop now runs on a
  fixed schedule, and the slow psutil scan runs on its own thread.
- **Entropy** moved to numpy (~25× faster).

See `backend/evaluation/README.md` for the measurements before and after.
