"""
Picks the auto-response threshold from measured data instead of guessing.

The model's probability for a window doesn't depend on the threshold (the
threshold only decides whether recovery ACTS), so one set of live runs can be
replayed at every candidate threshold:

  attack trial responds   <=> some window's p(ransomware) >= threshold
  benign trial misfires   <=> some window's p(ransomware) >= threshold

    python -m evaluation.threshold_analysis evaluation/results/results.json evaluation/results_calibration/results.json

Writes evaluation/results_calibration/THRESHOLD.md and threshold_tradeoff.png.
"""

import json
import sys
from pathlib import Path

from evaluation.workloads import AMBIGUOUS_BENIGN

OUT = Path(__file__).resolve().parent / "results_calibration"
THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]


def p_ransom(window: dict) -> float:
    return window["confidence"] if window["prediction"] == "ransomware_like" else 1 - window["confidence"]


def max_p(trial: dict) -> float:
    return max((p_ransom(w) for w in trial["windows"]), default=0.0)


def main(paths: list[str]) -> None:
    trials = [t for p in paths for t in json.loads(Path(p).read_text(encoding="utf-8"))]
    attacks = [t for t in trials if t["kind"] == "attack"]
    benign = [t for t in trials if t["kind"] == "benign" and t["workload"] not in AMBIGUOUS_BENIGN]
    ambiguous = [t for t in trials if t["kind"] == "benign" and t["workload"] in AMBIGUOUS_BENIGN]

    rows = []
    for tau in THRESHOLDS:
        rows.append({
            "tau": tau,
            "attacks_responded": sum(max_p(t) >= tau for t in attacks),
            "benign_misfires": sum(max_p(t) >= tau for t in benign),
            "ambiguous_alarms": sum(max_p(t) >= tau for t in ambiguous),
        })

    by_workload = {}
    for t in benign + ambiguous + attacks:
        by_workload.setdefault(t["workload"], []).append(max_p(t))

    lines = [
        "# Auto-response threshold calibration",
        "",
        f"{len(attacks)} attack trials, {len(benign)} benign trials, {len(ambiguous)} ambiguous trials "
        f"({', '.join(sorted(AMBIGUOUS_BENIGN))}: a user encrypting their own files, which no behavioural "
        "detector can distinguish from ransomware).",
        "",
        "## Highest p(ransomware) per trial, by workload",
        "",
        "| Workload | Kind | Trials | Lowest max p | Highest max p |",
        "|---|---|---|---|---|",
    ]
    kinds = {t["workload"]: ("ambiguous" if t["workload"] in AMBIGUOUS_BENIGN else t["kind"]) for t in trials}
    for name, ps in sorted(by_workload.items(), key=lambda kv: (kinds[kv[0]], -max(kv[1]))):
        lines.append(f"| {name} | {kinds[name]} | {len(ps)} | {min(ps):.2f} | {max(ps):.2f} |")
    lines += [
        "",
        "## Trade-off at each threshold",
        "",
        "| Threshold | Attack trials that trigger recovery | Benign trials that wrongly trigger it | Ambiguous trials that trigger it |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['tau']:.2f} | {r['attacks_responded']}/{len(attacks)} | {r['benign_misfires']}/{len(benign)} | "
                     f"{r['ambiguous_alarms']}/{len(ambiguous)} |")
    OUT.mkdir(exist_ok=True)
    (OUT / "THRESHOLD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4))
    xs = [r["tau"] for r in rows]
    ax.plot(xs, [r["attacks_responded"] / max(len(attacks), 1) for r in rows], marker="o", color="#2a78d6",
            label="Attack trials that trigger recovery")
    ax.plot(xs, [r["benign_misfires"] / max(len(benign), 1) for r in rows], marker="o", color="#d6453d",
            label="Benign trials that wrongly trigger it")
    ax.set_xlabel("Auto-response threshold (p(ransomware))")
    ax.set_ylabel("Share of trials")
    ax.set_ylim(-0.03, 1.05)
    ax.set_title("Recovery coverage vs. false responses")
    ax.legend(frameon=False, loc="center left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "threshold_tradeoff.png", dpi=150)


if __name__ == "__main__":
    main(sys.argv[1:])
