"""Draws figures/architecture.png for the paper.  python make_architecture.py"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

INK = "#1f2937"
MUTED = "#6b7280"
FILL = {"io": "#eef2f7", "core": "#e3eefc", "ml": "#e6f6f2", "rec": "#fdf1e3"}

fig, ax = plt.subplots(figsize=(7.2, 3.1))
ax.set_xlim(0, 100)
ax.set_ylim(0, 44)
ax.axis("off")


def box(x, y, w, h, title, lines, kind):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2",
                                linewidth=0.9, edgecolor=INK, facecolor=FILL[kind]))
    ax.text(x + w / 2, y + h - 2.4, title, ha="center", va="top", fontsize=7.6, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h - 6.4, "\n".join(lines), ha="center", va="top", fontsize=6.1, color=INK, linespacing=1.3)


def arrow(x1, y1, x2, y2, label=None, lx=0, ly=1.4):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=8, linewidth=0.9, color=INK))
    if label:
        ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, ha="center", fontsize=5.8, color=MUTED, style="italic")


# Row 1: sensing -> features -> model
box(0.5, 24, 17, 18, "Watched folder", ["file create / modify /", "rename / delete", "events (watchdog)"], "io")
box(22, 24, 22, 18, "Window aggregator", ["fixed-cadence window W", "per-file baselines", "rename & copy-delete", "pairing -> 8 file features"], "core")
box(22, 1.5, 22, 17, "Process sampler", ["own thread (psutil)", "busiest process ->", "3 process features", "+ attributed PID"], "core")
box(49, 24, 21, 18, "Detector + XAI", ["Random Forest (200 trees)", "p(ransomware)", "TreeSHAP per alert", "-> top features, summary"], "ml")
box(75, 24, 24.5, 18, "Recovery engine", ["if p >= tau (0.75):", "1 suspend PID (opt-in)", "2 quarantine artifacts", "3 restore clean versions"], "rec")
box(75, 1.5, 24.5, 17, "Shadow-copy vault", ["SHA-256 content-addressed", "outside watched tree", "versions + entropy guard", "quarantine (never delete)"], "rec")
box(49, 1.5, 21, 17, "Audit log + UI", ["recovery_actions table", "per-incident trail", "RBAC (JWT): admin /", "analyst / viewer"], "io")

arrow(17.8, 33, 21.7, 33)
arrow(44.3, 33, 48.7, 33)
arrow(33, 18.8, 33, 23.7)
arrow(70.3, 33, 74.7, 33)
arrow(87.2, 23.7, 87.2, 18.8)
arrow(87.2, 18.8, 87.2, 23.7)
ax.text(89.3, 21.2, "restore /\ncapture", fontsize=5.8, color=MUTED, style="italic", va="center")
arrow(74.7, 10, 70.3, 10)
# benign windows refresh the vault
ax.add_patch(FancyArrowPatch((66.5, 23.7), (75.2, 17.2), connectionstyle="arc3,rad=0", arrowstyle="-|>",
                             mutation_scale=8, linewidth=0.8, color=MUTED, linestyle=(0, (3, 2))))
ax.text(65.8, 21.2, "benign window: snapshot changed files", fontsize=5.6, color=MUTED, style="italic",
        va="center", ha="right")

out = Path(__file__).resolve().parent / "architecture.png"
fig.savefig(out, dpi=300, bbox_inches="tight")
print("wrote", out)
