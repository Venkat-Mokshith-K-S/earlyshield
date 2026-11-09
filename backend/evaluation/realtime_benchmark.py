"""
Real-time evaluation of EarlyShield (research gaps #1 and #6).

Runs the REAL monitor, model and recovery engine in-process against a
throwaway corpus, while a separate process runs either a ransomware
simulator or a benign workload (see workloads.py). For each trial it
measures:

  time to detection (TTD)       first attacker write -> model flags a window
  files encrypted before detection   how much damage happened before the alert
  files lost after recovery     corpus files not byte-identical at the end
  residual artifacts            .locked / .enc / ransom notes left behind
  attribution accuracy          did the monitor blame the attacker's PID?
  false positives               benign workloads flagged as ransomware

    cd backend
    python -m evaluation.realtime_benchmark            # full run (~35 min)
    python -m evaluation.realtime_benchmark --quick    # one window size, one trial (~5 min)

Results go to evaluation/results/: raw per-trial JSON, a Markdown report
and charts.
"""

import argparse
import hashlib
import json
import logging
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.domains.auth.models import User  # noqa: F401
from app.domains.detection.service import DetectionService
from app.domains.monitoring.service import FileSystemMonitorService
from app.domains.recovery.models import RecoveryAction
from app.domains.recovery.service import RecoveryService
from evaluation.workloads import AMBIGUOUS_BENIGN, ATTACKS, BENIGN, CORPUS_MARKER

BACKEND_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(__file__).resolve().parent / "results"
CORPUS_SIZE = 100
MAX_WORKLOAD_SECONDS = 40  # slow attacks are cut off here
ARTIFACT_SUFFIXES = (".locked", ".enc")

WORDS = (
    "the quarterly report shows revenue growth across regions while operating costs remained stable "
    "management expects continued demand for services in the coming fiscal year and plans hiring "
    "customer feedback highlighted delivery times product quality and support responsiveness"
).split()


# --- corpus ------------------------------------------------------------------

def build_corpus(root: Path, seed: int) -> dict[str, str]:
    """100 realistic low-entropy office files across 5 folders. Returns {relative_path: sha256}."""
    rng = random.Random(seed)
    root.mkdir(parents=True)
    (root / CORPUS_MARKER).write_text("throwaway benchmark corpus\n")
    folders = ["finance", "hr", "projects", "notes", "clients"]
    hashes = {}
    for i in range(CORPUS_SIZE):
        folder = root / folders[i % len(folders)]
        folder.mkdir(exist_ok=True)
        kind = i % 5
        if kind < 3:
            path = folder / f"document_{i:03d}.txt"
            text = "\n".join(" ".join(rng.choices(WORDS, k=rng.randint(10, 20))).capitalize() + "."
                             for _ in range(rng.randint(30, 200)))
        elif kind == 3:
            path = folder / f"ledger_{i:03d}.csv"
            text = "date,account,amount\n" + "\n".join(
                f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d},{rng.choice(WORDS)},{rng.uniform(10, 9999):.2f}"
                for _ in range(rng.randint(50, 400)))
        else:
            path = folder / f"record_{i:03d}.json"
            text = json.dumps([{"id": j, "name": rng.choice(WORDS), "score": rng.randint(0, 100)}
                               for j in range(rng.randint(20, 150))], indent=2)
        path.write_text(text, encoding="utf-8")
        hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def file_intact(root: Path, rel: str, sha: str) -> bool:
    p = root / rel
    return p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == sha


# --- one trial -----------------------------------------------------------------

def run_trial(workload: str, window: float, trial: int, workdir: Path, threshold: float, seed_offset: int = 0) -> dict:
    is_attack = workload in ATTACKS
    root = workdir / "watched"
    originals = build_corpus(root, seed=trial + seed_offset)

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    RecoveryService.session_factory = factory
    RecoveryService.reset_vault(workdir / "vault")
    RecoveryService._suspended.clear()
    RecoveryService._active_incident_id = None
    RecoveryService.auto_response = True
    RecoveryService.auto_suspend = False  # measured via attribution accuracy instead (see report)
    RecoveryService.confidence_threshold = threshold
    with FileSystemMonitorService._events_log_lock:
        FileSystemMonitorService._events_log.clear()

    FileSystemMonitorService.start(str(root), window)
    try:
        # One quiet window first: primes psutil's CPU counters and makes
        # the attack start at a random point inside a window, as it would
        # in reality, instead of conveniently at a window boundary.
        time.sleep(window + random.uniform(0, window))

        log_path = workdir / "workload.jsonl"
        proc = subprocess.Popen(
            [sys.executable, "-m", "evaluation.workloads", "--root", str(root),
             "--workload", workload, "--log", str(log_path)],
            cwd=BACKEND_DIR,
        )
        try:
            proc.wait(timeout=MAX_WORKLOAD_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        # Let the monitor finish analyzing and responding to the tail. A
        # fixed sleep isn't enough: a slow response (several seconds of
        # restores) can still be running when it ends, and stopping the
        # monitor then drops the next window's events, which a live system
        # would go on to process. So also wait until a full window has
        # gone by with nothing left in the buffer.
        time.sleep(3 * window + 2)
        drain_deadline = time.monotonic() + 60
        processed = FileSystemMonitorService._windows_processed
        while time.monotonic() < drain_deadline:
            time.sleep(window)
            with FileSystemMonitorService._buffer_lock:
                pending = len(FileSystemMonitorService._event_buffer)
            now_processed = FileSystemMonitorService._windows_processed
            if pending == 0 and now_processed > processed:
                break
            processed = now_processed
    finally:
        FileSystemMonitorService.stop()

    with FileSystemMonitorService._events_log_lock:
        events = list(FileSystemMonitorService._events_log)
    log = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    db = factory()
    actions = db.query(RecoveryAction).all()
    db.close()

    flagged = [e for e in events if e.result.prediction == "ransomware_like"]
    result = {
        "workload": workload,
        "kind": "attack" if is_attack else "benign",
        "window_seconds": window,
        "trial": trial,
        "windows_analyzed": len(events),
        "windows_flagged": len(flagged),
        "detected": bool(flagged),
        "confidences": [round(e.result.confidence, 4) for e in flagged],
        "attributed_processes": sorted({e.attributed_process or "?" for e in flagged}),
        "attribution_correct": (sum(e.attributed_pid == proc.pid for e in flagged) / len(flagged)) if flagged else None,
        "quarantine_actions": sum(a.action_type == "quarantine_file" for a in actions),
        "restore_actions": sum(a.action_type == "restore_file" and a.status == "success" for a in actions),
    }

    # Per-window detail, relative to the workload's first logged action,
    # so individual misses can be diagnosed from results.json.
    t_zero = log[0]["t"] if log else 0
    result["windows"] = [
        {
            "t": round(e.timestamp.timestamp() - (e.response_ms or 0) / 1000 - t_zero, 2),
            "prediction": e.result.prediction,
            "confidence": round(e.result.confidence, 4),
            "process": e.attributed_process,
            "raw_events": e.raw_event_count,
            "features": e.features.model_dump(),
        }
        for e in events
    ]

    if is_attack:
        encrypted = [r["t"] for r in log if r["op"] == "encrypted"]
        start = min(encrypted) if encrypted else next(r["t"] for r in log if r["op"] == "attack_start")
        detection_t = None
        if flagged:
            first = flagged[0]
            detection_t = first.timestamp.timestamp() - (first.response_ms or 0) / 1000
        responded = [e for e in flagged if e.recovery_incident_id]
        intact = sum(file_intact(root, rel, sha) for rel, sha in originals.items())
        artifacts = [p.name for p in root.rglob("*")
                     if p.is_file() and (p.suffix in ARTIFACT_SUFFIXES or p.name == "README_RESTORE_FILES.txt")]
        result.update({
            "files_encrypted_total": len(encrypted),
            "attack_duration_s": round(max(encrypted) - start, 2) if encrypted else 0,
            "ttd_s": round(detection_t - start, 2) if detection_t else None,
            "files_encrypted_before_detection": sum(t < detection_t for t in encrypted) if detection_t else len(encrypted),
            "responded": bool(responded),
            "response_ms": responded[0].response_ms if responded else None,
            "files_intact_after": intact,
            "files_lost_after": CORPUS_SIZE - intact,
            "residual_artifacts": len(artifacts),
        })
    return result


# --- aggregation & report ----------------------------------------------------------

def _mean(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else None


def _fmt(value, spec=".1f", suffix=""):
    return "—" if value is None else f"{value:{spec}}{suffix}"


def _mean_sd(values, spec=".1f"):
    values = [v for v in values if v is not None]
    if not values:
        return "—"
    if len(values) == 1:
        return f"{values[0]:{spec}}"
    return f"{statistics.mean(values):{spec}} ± {statistics.stdev(values):{spec}}"


def write_report(results: list[dict], out: Path, meta: dict) -> None:
    attacks = [r for r in results if r["kind"] == "attack"]
    benign = [r for r in results if r["kind"] == "benign"]
    windows = sorted({r["window_seconds"] for r in results})

    lines = [
        "# EarlyShield — Real-Time Evaluation Results",
        "",
        f"Generated {meta['generated']} on {meta['platform']} · corpus of {CORPUS_SIZE} files · "
        f"auto-response threshold {meta['threshold']:.2f} · {meta['trials']} trial(s) per attack configuration.",
        "",
        "## Ransomware simulations",
        "",
        "TTD = time from the attacker's first encrypted file to the model flagging a window. "
        "\"Before detection\" = files the attacker had already encrypted at that moment. "
        "\"Lost\" = corpus files not byte-identical to the original at the end of the trial, after automated recovery. "
        "\"Responded\" = the detection's confidence reached the auto-response threshold, so files were quarantined "
        "and restored; below it EarlyShield only raises an alert. \"Confidence\" = mean of each trial's highest "
        "flagged-window confidence. \"Attribution\" = share of flagged windows blamed on the attacker's PID.",
        "",
        "| Attack | Window | Detected | Responded | Confidence | TTD (s) | Encrypted before detection | Encrypted total | Lost after recovery | Artifacts left | Attribution |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name in ATTACKS:
        for w in windows:
            rows = [r for r in attacks if r["workload"] == name and r["window_seconds"] == w]
            if not rows:
                continue
            det = sum(r["detected"] for r in rows)
            lines.append(
                f"| {name} | {w:g}s | {det}/{len(rows)} | {sum(r['responded'] for r in rows)}/{len(rows)} | "
                f"{_fmt(_mean([max(r['confidences']) for r in rows if r['confidences']]), '.2f')} | "
                f"{_mean_sd([r['ttd_s'] for r in rows])} | "
                f"{_mean_sd([r['files_encrypted_before_detection'] for r in rows])} | "
                f"{_mean_sd([r['files_encrypted_total'] for r in rows], '.0f')} | "
                f"{_mean_sd([r['files_lost_after'] for r in rows])} | "
                f"{_mean_sd([r['residual_artifacts'] for r in rows])} | "
                f"{_fmt(_mean([r['attribution_correct'] for r in rows]), '.0%')} |"
            )

    if attacks:
        detected = [r for r in attacks if r["detected"]]
        lines += [
            "",
            "**Overall:** "
            f"{len(detected)}/{len(attacks)} attack trials detected; "
            f"mean TTD {_fmt(_mean([r['ttd_s'] for r in detected]), '.2f', ' s')}; "
            f"mean {_fmt(_mean([r['files_encrypted_before_detection'] / CORPUS_SIZE for r in attacks]), '.1%')} "
            f"of the corpus encrypted before detection; "
            f"mean {_fmt(_mean([r['files_lost_after'] / CORPUS_SIZE for r in attacks]), '.1%')} lost after recovery; "
            f"mean automated response time {_fmt(_mean([r['response_ms'] for r in attacks]), '.0f', ' ms')}.",
        ]

    lines += [
        "",
        "## Benign workloads (false positives)",
        "",
        "A false positive here also triggers the automated response, so \"Collateral actions\" counts the "
        "quarantine/restore actions EarlyShield took on legitimate activity (all reversible: quarantined files "
        "are moved into the vault, not deleted).",
        "",
        "| Workload | Window | Flagged trials | Flagged windows | Max confidence | Collateral actions |",
        "|---|---|---|---|---|---|",
    ]
    for name in BENIGN:
        for w in windows:
            rows = [r for r in benign if r["workload"] == name and r["window_seconds"] == w]
            if not rows:
                continue
            confs = [c for r in rows for c in r["confidences"]]
            label = f"{name} (expected alarm)" if name in AMBIGUOUS_BENIGN else name
            lines.append(
                f"| {label} | {w:g}s | {sum(r['detected'] for r in rows)}/{len(rows)} | "
                f"{sum(r['windows_flagged'] for r in rows)}/{sum(r['windows_analyzed'] for r in rows)} | "
                f"{_fmt(max(confs) if confs else None, '.2f')} | "
                f"{sum(r['quarantine_actions'] + r['restore_actions'] for r in rows)} |"
            )
    if benign:
        # A user encrypting their own files behaves exactly like ransomware;
        # an alarm there is correct behaviour for a behavioural detector, so
        # it's reported on its own line instead of as a false positive.
        true_benign = [r for r in benign if r["workload"] not in AMBIGUOUS_BENIGN]
        ambiguous = [r for r in benign if r["workload"] in AMBIGUOUS_BENIGN]
        fp_trials = sum(r["detected"] for r in true_benign)
        lines += ["", f"**Overall:** {fp_trials}/{len(true_benign)} benign trials produced at least one false alarm "
                      f"({sum(r['windows_flagged'] for r in true_benign)}/{sum(r['windows_analyzed'] for r in true_benign)} windows)."]
        if ambiguous:
            lines.append(f"User-initiated encryption (`legit_encrypt`) raised an alarm in "
                         f"{sum(r['detected'] for r in ambiguous)}/{len(ambiguous)} trials, as expected: it is "
                         "behaviourally identical to ransomware.")

    lines += ["", "## Charts", "", "![Time to detection](ttd_by_attack.png)", "", "![Damage](damage_by_attack.png)", ""]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def write_charts(results: list[dict], out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    attacks = [r for r in results if r["kind"] == "attack"]
    if not attacks:
        return
    windows = sorted({r["window_seconds"] for r in attacks})
    names = [n for n in ATTACKS if any(r["workload"] == n for r in attacks)]
    colors = ["#2a78d6", "#1baf9c", "#e8a33d", "#8a63d2"]
    width = 0.8 / len(windows)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, w in enumerate(windows):
        vals = [_mean([r["ttd_s"] for r in attacks if r["workload"] == n and r["window_seconds"] == w]) or 0 for n in names]
        ax.bar([x + i * width for x in range(len(names))], vals, width, label=f"{w:g}s window", color=colors[i % 4])
    ax.set_xticks([x + width * (len(windows) - 1) / 2 for x in range(len(names))], names)
    ax.set_ylabel("Mean time to detection (s)")
    ax.set_title("Time to detection by attack profile and window size")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.15)
    ax.legend(frameon=False, loc="upper center", ncol=len(windows))
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "ttd_by_attack.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    labels, before, lost = [], [], []
    for n in names:
        for w in windows:
            rows = [r for r in attacks if r["workload"] == n and r["window_seconds"] == w]
            labels.append(n.replace("_", "\n") + f"\n{w:g}s")
            before.append(_mean([r["files_encrypted_before_detection"] for r in rows]) or 0)
            lost.append(_mean([r["files_lost_after"] for r in rows]) or 0)
    xs = range(len(labels))
    ax.bar([x - 0.2 for x in xs], before, 0.4, label="Encrypted before detection", color="#e8a33d")
    ax.bar([x + 0.2 for x in xs], lost, 0.4, label="Lost after recovery", color="#d6453d")
    ax.set_xticks(list(xs), labels, fontsize=8)
    ax.set_ylabel(f"Files (of {CORPUS_SIZE})")
    ax.set_ylim(0, CORPUS_SIZE * 1.18)
    ax.set_title("Damage before detection vs. after automated recovery")
    ax.legend(frameon=False, loc="upper center", ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "damage_by_attack.png", dpi=150)
    plt.close(fig)


# --- main ----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--windows", type=float, nargs="+", default=[2, 5, 10])
    parser.add_argument("--trials", type=int, default=3, help="trials per attack configuration")
    parser.add_argument("--benign-trials", type=int, default=1)
    parser.add_argument("--attacks", nargs="+", default=list(ATTACKS), choices=list(ATTACKS))
    parser.add_argument("--benign", nargs="*", default=BENIGN, choices=BENIGN)
    parser.add_argument("--quick", action="store_true", help="5s window, 1 trial each")
    parser.add_argument("--seed-offset", type=int, default=0,
                        help="shift corpus seeds, to validate on corpora never seen before")
    parser.add_argument("--threshold", type=float, default=settings.RECOVERY_CONFIDENCE_THRESHOLD,
                        help="auto-response confidence threshold to run with (default: the configured one)")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR)
    parser.add_argument("--report-only", action="store_true", help="rebuild REPORT.md and charts from existing results")
    args = parser.parse_args()
    if args.report_only:
        results = json.loads((args.out / "results.json").read_text(encoding="utf-8"))
        meta = json.loads((args.out / "meta.json").read_text(encoding="utf-8"))
        write_report(results, args.out, meta)
        write_charts(results, args.out)
        return 0
    if args.quick:
        args.windows, args.trials, args.benign_trials = [5], 1, 1

    logging.getLogger().setLevel(logging.ERROR)  # the app logs every recovery step at INFO
    # The app loads the model at startup; without this the first trial's
    # TTD would include ~8 s of one-off model/SHAP loading.
    DetectionService.warm_up()
    args.out.mkdir(parents=True, exist_ok=True)

    plan = [(w, t, a) for a in args.attacks for w in args.windows for t in range(args.trials)]
    plan += [(w, t, b) for b in args.benign for w in args.windows for t in range(args.benign_trials)]
    results = []
    for i, (window, trial, workload) in enumerate(plan, 1):
        workdir = Path(tempfile.mkdtemp(prefix="earlyshield-bench-"))
        try:
            r = run_trial(workload, window, trial, workdir, args.threshold, args.seed_offset)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        results.append(r)
        summary = (f"TTD={r['ttd_s']}s before={r['files_encrypted_before_detection']} lost={r['files_lost_after']}"
                   if r["kind"] == "attack" else f"flagged {r['windows_flagged']}/{r['windows_analyzed']} windows")
        print(f"[{i}/{len(plan)}] {workload:<18} window={window:g}s trial={trial}  {summary}", flush=True)
        (args.out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    meta = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "platform": f"{sys.platform}, Python {sys.version.split()[0]}, "
                    f"{'PollingObserver' if settings.FILE_MONITOR_USE_POLLING else 'native observer'}",
        "threshold": args.threshold,
        "trials": args.trials,
    }
    (args.out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    write_report(results, args.out, meta)
    write_charts(results, args.out)
    print(f"\nReport: {args.out / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
