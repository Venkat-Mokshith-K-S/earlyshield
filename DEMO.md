# Demo-day runbook

Verified end-to-end in Docker on 2026-10-22. A throttled attack was
detected, the attacker process was suspended, and 100/100 files came
back byte-identical with no ransomware files left behind.

## Before the demo (the day before, or ≥1 hour before your slot)

**Easiest:** right-click `start-earlyshield.ps1` → *Run with PowerShell*. It
starts Docker Desktop, works around the "sailor-ingest.sock … cannot be
accessed" crash this laptop gets after every reboot, starts the stack and
opens the site. If Docker ever shows that error dialog, click **Quit** (never
*Reset to factory defaults*) and run the script.

Or by hand:

```bash
cd earlyshield-module1-fresh/earlyshield
docker compose up -d                 # NOT --build: images are already built; no downloads
docker compose ps                    # all three should say (healthy) after ~30 s
```

- **Don't click "Update" in Docker Desktop** until after the demo.
- Open http://localhost:5173 and **register your account first**. The first
  account becomes **admin**. Use a normal-looking email (e.g. `name@gmail.com`):
  `.test` / `.local` addresses are rejected as invalid.
- Prepare fresh demo files:
  ```bash
  docker compose exec backend python -m evaluation.demo setup
  ```

## The demo (≈5 minutes)

1. **Landing page** (http://localhost:5173): scroll once through it (the numbers on it are
   the real measured ones). Click **Sign in** → **Get Started** → dashboard
   (http://localhost:5173/dashboard). Point out the project title, and that the top
   bar says *Connected*.
2. **Explainability first (no risk):** in **Try a scenario**, run
   *ransomware typical* → threat gauge + SHAP chart show *why* it was
   flagged. Then run *benign* for contrast.
3. **Arm the system:** in **Automated recovery**, switch on **Auto suspend
   process** (admin only). Point out the vault stats.
4. **Start monitoring:** Live monitor → directory is pre-filled with
   **`/watched/demo_files`**; set the window to **5** s → *Start monitoring*. The recovery panel shows ~100
   files protected (the baseline snapshot).
5. **Attack** (second terminal, ideally visible on screen):
   ```bash
   docker compose exec backend python -m evaluation.demo attack
   ```
   Within ~5–10 s:
   - timeline bar turns red, gauge spikes, SHAP explains it (entropy jump,
     extension changes, rename rate)
   - red banner: *Automated response triggered*
   - **Recovery log** fills: suspend → quarantine → restore, each with a
     verified hash
   - **Suspended processes** shows `python`. The attack terminal
     **freezes**, because the attacker is paused mid-attack.
6. **Prove it** (third terminal, or stop the frozen one with Ctrl+C first):
   ```bash
   docker compose exec backend python -m evaluation.demo status
   ```
   → `100/100 original files intact (byte-identical)`, `0 ransomware artifact(s) left`.

> ⚠️ **Don't click "Resume"** on the suspended attacker during the demo:
> resuming lets it carry on encrypting. Resume exists for *false positives*.

### Run it again
```bash
docker compose restart backend          # resets runtime toggles; kills a frozen attacker
docker compose exec backend python -m evaluation.demo setup
```
Then restart monitoring in the dashboard and turn auto-suspend back on.

## Other attack profiles

```bash
docker compose exec backend python -m evaluation.demo attack --profile burst        # 100 files in ~0.2 s
docker compose exec backend python -m evaluation.demo attack --profile copy_delete  # writes .enc copies, deletes originals
```
Avoid `slow_inplace` live: it scores **0.48–0.56**, right on the 0.50
auto-response threshold, so whether it's caught varies run to run. Present
it as the known limitation (see `backend/evaluation/README.md`), not as a
live demo.

## Likely questions → where the answers are

| Question | Answer / file |
|---|---|
| "Is the accuracy real?" | 96.79% on held-out synthetic data; plus live-system results: 36/36 attacks detected, 0/15 false alarms → `backend/evaluation/README.md` |
| "Why synthetic training data?" | Running live ransomware is unsafe/illegal outside a sandbox → `ml/data/generate_dataset.py` docstring |
| "How do you know which process?" | Heuristic (busiest process); works in the container, failed on a busy desktop (0%) → why auto-suspend is opt-in |
| "What if ransomware deletes the backups?" | Honest limitation: same-privilege attacker can; production needs immutable storage → `MODULE5_README.md` |
| "What does 'secure' recovery mean?" | SHA-256-verified blobs, vault outside watched path, quarantine not delete, audit log, RBAC → `MODULE5_README.md` |

## If something goes wrong

| Symptom | Fix |
|---|---|
| Dashboard shows *Degraded* | `docker compose restart backend`, wait 30 s |
| "Invalid watch path" | Path must be `/watched/demo_files` (container path, not a Windows path) |
| Nothing appears after the attack | Monitor not started, or the window not yet elapsed: wait one window |
| Can't log in after a restart | Accounts persist in Postgres; re-register only if you ran `docker compose down -v` |
