"""
Demo-day helper. Run INSIDE the backend container, so the "attacker" is a
process the monitor can actually see and attribute:

    docker compose exec backend python -m evaluation.demo setup             # fresh demo files
    docker compose exec backend python -m evaluation.demo attack            # throttled attack (default)
    docker compose exec backend python -m evaluation.demo attack --profile burst
    docker compose exec backend python -m evaluation.demo status            # how many files are intact

Then in the dashboard, watch path:  /watched/demo_files
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from evaluation.realtime_benchmark import build_corpus
from evaluation.workloads import ATTACKS, CORPUS_MARKER

DEMO_ROOT = Path("/watched/demo_files")
HASHES = Path("/watched/.demo_hashes.json")  # outside the demo folder, so it isn't watched or attacked


def setup(root: Path) -> None:
    if root.exists():
        # Only ever wipe a folder this script created itself.
        if not (root / CORPUS_MARKER).exists():
            sys.exit(f"{root} exists and isn't a demo folder; refusing to delete it.")
        shutil.rmtree(root)
    hashes = build_corpus(root, seed=7)
    HASHES.write_text(json.dumps(hashes), encoding="utf-8")
    print(f"Created {len(hashes)} demo files in {root}")
    print(f"Dashboard -> Live monitor -> directory: {root}")


def attack(root: Path, profile: str) -> None:
    if not (root / CORPUS_MARKER).exists():
        sys.exit("No demo folder. Run: python -m evaluation.demo setup")
    log = Path(tempfile.gettempdir()) / "demo_attack.jsonl"
    print(f"Launching '{profile}' ransomware simulation against {root} ...")
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.workloads", "--root", str(root), "--workload", profile, "--log", str(log)]
    )
    encrypted = sum(1 for line in log.read_text().splitlines() if json.loads(line)["op"] == "encrypted")
    print(f"Attack finished (exit {proc.returncode}): {encrypted} file(s) encrypted. Watch the dashboard.")


def status(root: Path) -> None:
    hashes = json.loads(HASHES.read_text(encoding="utf-8"))
    intact = sum(
        1 for rel, sha in hashes.items()
        if (root / rel).is_file() and hashlib.sha256((root / rel).read_bytes()).hexdigest() == sha
    )
    leftovers = [p.name for p in root.rglob("*") if p.suffix in (".locked", ".enc") or p.name.startswith("README_RESTORE")]
    print(f"{intact}/{len(hashes)} original files intact (byte-identical)")
    print(f"{len(leftovers)} ransomware artifact(s) left" + (f": {leftovers[:5]}" if leftovers else ""))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["setup", "attack", "status"])
    parser.add_argument("--profile", default="throttled", choices=list(ATTACKS))
    parser.add_argument("--root", type=Path, default=DEMO_ROOT)
    args = parser.parse_args()
    {"setup": lambda: setup(args.root), "attack": lambda: attack(args.root, args.profile),
     "status": lambda: status(args.root)}[args.command]()


if __name__ == "__main__":
    main()
