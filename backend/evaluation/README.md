# Real-Time Evaluation (research gaps #1 and #6)

The model's 96.79% accuracy (see `/ml/README.md`) is measured on held-out
**synthetic feature vectors**. That number says nothing about whether the
*running system* catches an attack in time. This benchmark measures that
directly: the real monitor, model and recovery engine run against a live
folder while a separate process encrypts it.

- **Gap #1 (early detection):** how many files are encrypted before the
  alert, and how many are still lost after automated recovery.
- **Gap #6 (real-time conditions):** time to detection with real
  filesystem events, real process sampling, and a real OS scheduler,
  across window sizes.

## Incident follow-up (2026-10-25: 84 more trials, `--seed-offset 200`)

The 90-trial run below showed two kinds of loss once an attack was caught.
Slow in-place trials lost the files encrypted during windows that scored
just under 0.50, and the production-stack test left a ransom note that had
been written in a benign-scored window. The recovery engine now does an
**incident follow-up**: while an incident is open, every window, including
benign-scored ones, is checked for new files the vault has never seen and
for files whose entropy has jumped to encrypted level. Those are
quarantined and restored under the same incident (`MODULE5_README.md`).
Outside an incident the check does nothing, so normal activity is
unaffected.

Two runs on fresh corpora:

| | `results_followup` (48 trials) | `results_followup_drained` (36 attack trials) |
|---|---|---|
| burst / throttled | 9/9 and 9/9 detected, 0 lost | 9/9 and 9/9 detected, 0 lost |
| slow_inplace | **9/9 detected, 0 lost** | **9/9 detected, 0 lost** (p 0.52–0.56) |
| copy_delete | 9/9 detected; 0 lost in 8, **13 lost in 1** (harness artefact, below) | 9/9 detected, 0 lost |
| Artifacts left (incl. ransom notes) | 16, all in that one trial | **0** |
| Time to detection | n/a | median 5.5 s, p90 10.5 s, max 11.5 s |
| gzip_compress / legit_encrypt | 6/6 and 6/6 trigger (p up to 0.65 / 0.91), unchanged | not re-run |

**The 13-file loss was caused by the harness.** In that trial (2 s
window), the response took 4.0 s. The harness stopped the monitor after a
fixed `3*window + 2` s, which fell while the response was still running.
The next window, holding the last 16 encrypted copies, was therefore never
processed. A deployed monitor keeps running and would have handled it.
The harness now also waits until a full window passes with an empty event
buffer before stopping (`run_trial`). With that change, all 36 attack
trials lost nothing.

**What this does and doesn't fix.** The follow-up turns "detected" into
"fully recovered": once any window crosses the threshold, the rest of a
slow attack is caught even in windows scored below it. It does **not**
help an attack whose windows *all* stay below the threshold. Slow in-place
encryption still scores 0.48–0.56 across the three runs, and in the
90-trial run 3 of 9 trials were never detected. That boundary problem
remains, and the gzip false positive is unchanged.

**Production stack** (`docker-compose.prod.yml`, HTTPS, fresh database):
a throttled attack on 100 demo files left 100/100 byte-identical, no
`.locked` files and no ransom note in the folder (the note is in
quarantine). In this run the note was caught by the second detection
window, not by the follow-up path.

## Final results (2026-10-25: 90 trials, fresh corpora, threshold 0.50)

These are the numbers for the finished system: content-aware entropy,
threshold 0.50, 9 benign workloads including the hard ones, and corpora
the system had never seen (`--seed-offset 100`). Full tables:
[`results_final/REPORT.md`](results_final/REPORT.md). Raw data:
`results_final/results.json`.

| | |
|---|---|
| Attack trials detected | **33 / 36**: burst 9/9, throttled 9/9, copy_delete 9/9, slow_inplace 6/9 |
| Recovery fired | in all 33 detected trials |
| Files lost: burst, throttled, copy_delete | **0 in all 27 trials**, no artifacts left |
| Files lost: slow_inplace | 0 in 4 trials; 11 and 79 in two responded trials; 80 in the 3 undetected ones |
| Time to detection | median **5.3 s**, 90th percentile 9.1 s, max 17.6 s |
| Automated response time | mean 1.5 s, max 4.2 s |
| False alarms, 7 ordinary workloads | **0 / 42** trials (highest p(ransomware) 0.23) |
| gzip archiving (`gzip_compress`) | triggers recovery in 6/6 trials (p 0.57–0.62); reversible, see below |
| User encrypting own files (`legit_encrypt`) | alarms in 6/6, as expected for any behavioural detector |

### How the final configuration was reached

1. **Harder benign workloads.** Four were added: a software install (60 new
   high-entropy binaries), a photo import, gzip archiving (`x.csv` →
   `x.csv.gz` + delete) and user-initiated GPG-style encryption.
2. **Calibration run** (54 benign trials, threshold 0.75): gzip archiving
   scored **0.78–0.91**, a false positive the first benchmark never tested.
   Every threshold from 0.50 to 0.75 wrongly triggered on the same 6 gzip
   trials, while only 0.50 let recovery cover the slow in-place attack
   (`results_calibration/THRESHOLD.md`, `threshold_tradeoff.png`).
3. **Content-aware entropy.** A file that genuinely decompresses
   (gzip/bzip2/xz/unencrypted zip) is now judged by the entropy of what it
   decompresses to. Ciphertext never decompresses, ciphertext inside a valid
   gzip decompresses to random bytes, and encrypted zips aren't decoded, so
   encryption still scores ~8 (`tests/test_entropy.py`). This was designed
   *after* seeing the gzip result, so it was validated on fresh corpora.
4. **Threshold 0.50**, chosen from the calibration table.

### What the final run shows

- gzip archiving dropped from 0.78–0.91 to **0.57–0.62** but still crosses
  0.50, because the rename-and-delete pattern alone looks like copy-then-delete
  ransomware. The response is reversible (the archives sit in quarantine), but
  it is a real false positive at this threshold.
- **Slow in-place encryption sits on the decision boundary**: its windows
  score 0.48–0.55. In this run 6/9 trials crossed 0.50; in the first run 9/9
  did. When a slow attack crosses the threshold only in some windows, files
  encrypted during the windows below it are not restored, which is where the
  11 and 79 lost files came from.
- **No single threshold separates slow in-place encryption from gzip
  archiving with this model.** At 0.65 gzip stops triggering and slow
  in-place is never recovered; at 0.50 the reverse. 0.50 is the default
  because a wrong response is reversible and a missed one loses data; the
  setting is exposed to admins on the dashboard. Analysts can also restore
  files manually from the *Protected files* page, because the vault's
  entropy check keeps the pre-attack versions even when no automatic
  response happened.

## First run (2026-10-22: 51 trials, threshold 0.75)

The first full benchmark, before the hard benign workloads, content-aware
entropy and the threshold change. Full tables: [`results/REPORT.md`](results/REPORT.md).

| | |
|---|---|
| Attack trials detected | **36 / 36** (4 attack profiles × 3 window sizes × 3 trials) |
| Benign false alarms | **0 / 15** trials (0 / 26 analyzed windows) |
| Time to detection | median **5.4 s**, 90th percentile 7.7 s, max 11.9 s |
| Median TTD by window size | 2 s → 3.2 s · 5 s → 4.1 s · 10 s → 7.4 s |
| Data lost when the auto-response fired | **0 files, 0 artifacts left, in all 26 such trials** |
| Automated response time | mean 2.1 s, max 4.4 s (100 files quarantined + restored, every hash verified) |
| Correct process attribution | **0%** of flagged windows |

### Findings

1. **Gap #1: recovery makes "how early" matter less than "whether".**
   A burst attack encrypts all 100 files in ~0.2 s, faster than any
   window-based detector can react, so 100% are encrypted before
   detection. In every trial where the response fired, all 100 came
   back byte-for-byte anyway. For throttled attacks, damage before
   detection grows with the window (27 → 41 → 73 files at 2/5/10 s),
   which makes the window size the main tuning knob for early detection.

2. **Every file lost came from a detection below the auto-response
   threshold, never from a failed recovery.** All 10 trials that lost data
   were *detected* but scored under 0.75:
   - **`slow_inplace`, 9 of 9 trials:** confidence 0.54–0.57. The synthetic
     training data assumed even stealthy ransomware renames files
     (`extension_change_ratio` ~ Beta(3.5, 4), mean 0.47), so encrypting in
     place with no rename falls outside what the model learned. It still
     tips over 0.5 (high `entropy_delta` carries it) but not to 0.75.
     80 files lost = everything the attacker reached in the 40 s cap.
   - **`copy_delete`, 1 of 9 trials:** confidence 0.736, just under the
     threshold. All 100 files lost.

   This is the false-positive vs. data-loss trade-off measured directly.
   No benign window's ransomware probability exceeded 0.23, so there's
   headroom to lower the threshold, but that should be evaluated on more
   benign workloads before changing the default.

3. **Process attribution doesn't work on a busy desktop.** The process
   blamed was `claude.exe`, `chrome.exe`, `msedgewebview2.exe` or
   unidentified, never the attacker. Two reasons: the burst attacker exits
   within ~0.2 s, before the next process sample; and the slower attackers
   write ~20 KB/s, far less than a browser or Electron app. This is why
   auto-suspend is off by default (Module 5). It also means the three
   process features (`process_cpu_percent`, `io_write_rate_mb_s`,
   `read_write_ratio`) mostly describe the wrong process, and the
   detections above rest on the eight file-level features.

4. **TTD varies more than window alignment alone explains.** For example,
   one burst trial with a 2 s window took 6.2 s. This benchmark doesn't
   separate out filesystem-event delivery delay (polling observer, thread
   scheduling), so that variance is reported, not explained.

## Running it

```bash
cd backend
python -m evaluation.realtime_benchmark            # full run: 3 windows x 4 attacks x 3 trials + benign (~35 min)
python -m evaluation.realtime_benchmark --quick    # 5 s window, 1 trial each (~5 min)
python -m evaluation.realtime_benchmark --windows 5 --trials 5 --attacks burst slow_inplace --benign
```

Output goes to `evaluation/results/`:
- `REPORT.md` — summary tables
- `results.json` — every trial, including each window's 11 features,
  prediction and confidence, so any miss can be diagnosed
- two charts

## Method

Each trial:
1. Builds a fresh corpus of 100 office-style files (txt/csv/json, 5 folders).
2. Starts the monitor with a fresh recovery vault and an empty audit DB.
3. Waits one quiet window plus a random offset, so the attack starts at
   a random point *inside* a window, not conveniently at a boundary.
4. Launches the workload as a **separate process**, so the monitor has to
   attribute activity to a foreign PID exactly as it would for real malware.
5. Waits three more windows for the monitor to finish responding.
6. Hashes every corpus file against its original.

The workload process logs a timestamp for each file it touches, so
"files encrypted before detection" is counted exactly, not estimated.

**Detection time** is when the flagged window finished *analysis*
(`DetectionEvent.timestamp − response_ms`), so it excludes the time the
recovery itself took. Recovery time is reported separately.

### Ransomware simulators (`workloads.py`)

| Profile | Rate | Behaviour |
|---|---|---|
| `burst` | as fast as possible | overwrite with random bytes, rename to `.locked` |
| `throttled` | 10 files/s | same, rate-limited to blend in |
| `slow_inplace` | 2 files/s | overwrite in place: **no rename, no extension change** |
| `copy_delete` | as fast as possible | write encrypted `name.enc`, delete the original |

All four drop a ransom note at the end. "Encryption" is `os.urandom`
output, which has the same byte statistics (entropy ≈ 8) as AES output.
The simulators **refuse to run** unless the target folder holds the
benchmark's marker file, so they can't be pointed at real data.

### Benign workloads (false-positive check)

| Workload | Why it's a hard case |
|---|---|
| `edit_docs` | baseline: someone saving documents |
| `bulk_rename` | 100 renames in a burst (photo-manager style) |
| `zip_archive` | a large, new, high-entropy file |
| `copy_folder` | 100 new files written quickly |
| `format_conversion` | a *legitimate* mass extension change (.txt → .md + delete) |

## Module 3 bugs this evaluation found (and fixed)

The first run detected only 2 of 4 attacks. Per-window feature dumps
showed the cause was the feature extraction, not the model:

1. **`entropy_delta` was always 0 and `avg_size_change_ratio` always 1.0
   for attacked files.** A file's baseline was recorded the first time it
   *changed*, i.e. after it had already been encrypted. Baselines are now
   seeded for every file when monitoring starts and carried across renames.
2. **Newly created files weren't counted as file activity.** Copy-then-delete
   ransomware produced a modification rate of 0 and an extension-change
   ratio of 0. Created files now count, and `a.txt.enc` (created) is paired
   with `a.txt` (deleted in the same window).
3. **`read_write_ratio` was always 0.** Reads were compared against a
   baseline that had already been overwritten with the current value.
4. **Windows ran late.** The loop waited a full window *after* processing,
   and a full psutil scan takes 3–5 s on Windows, so a "5 s" window was
   really ~10 s. Windows now run on a fixed schedule; process sampling
   moved to its own thread and is 2–3× faster; rates use the true elapsed time.
5. **Entropy calculation** moved from a Python byte loop to numpy (~25× faster).

## Threats to validity (state these in the paper)

- **Simulated ransomware.** The simulators reproduce the file-level
  behaviour of real families: overwrite, rename, copy-delete, throttling.
  They don't reproduce in-memory behaviour, process injection, or
  intermittent encryption (e.g. LockFile, which encrypts alternating 16-byte
  blocks so that encrypted files stay statistically close to the originals
  and evade entropy-based detection; Sophos, Aug 2021).
- **One machine.** Timings come from one Windows desktop with other
  applications running, which is realistic background noise but not a
  controlled environment. Polling-based watching (needed for Docker on
  Windows) adds up to 1 s of event delay. Native inotify on Linux would be faster.
- **Small corpus.** 100 files of 2–40 KB. Larger files make each
  encryption slower and so give the detector *more* time; this corpus
  is a pessimistic case for the detector.
- **The model was not tuned on these results.** The benchmark was used
  to find and fix *feature-extraction bugs*. The model and its synthetic
  training data are unchanged, so the detection numbers aren't inflated
  by fitting to the test.
