"""
File-activity workloads for the real-time benchmark, run as a SEPARATE
process so the monitor sees (and has to attribute) a genuinely different
PID — the same situation as real ransomware.

    python -m evaluation.workloads --root <corpus> --workload burst --log out.jsonl

SAFETY: the ransomware simulators overwrite files with random bytes. They
refuse to run unless <root> contains the marker file the benchmark creates
for its own throwaway corpus, so this can't be pointed at real data by
mistake.

Every action is logged as a JSON line {"t": <unix time>, "op": ..., "path": ...}
so the benchmark can compute exactly how many files were damaged before
detection.
"""

import argparse
import gzip
import json
import os
import random
import shutil
import sys
import time
import zipfile
from pathlib import Path

CORPUS_MARKER = ".earlyshield-benchmark-corpus"

# name -> (rate in files/s, 0 = as fast as possible; style)
ATTACKS = {
    "burst": (0, "encrypt_rename"),          # classic: encrypt everything ASAP, rename to .locked
    "throttled": (10, "encrypt_rename"),     # rate-limited to blend in
    "slow_inplace": (2, "encrypt_inplace"),  # stealthy: slow, no rename/extension change
    "copy_delete": (0, "copy_delete"),       # write encrypted .enc copy, delete original
}
BENIGN = [
    "edit_docs", "bulk_rename", "zip_archive", "copy_folder", "format_conversion",
    # Harder cases, added to calibrate the response threshold: each produces
    # high-entropy writes, and gzip/legit_encrypt also change extensions.
    "software_install", "media_import", "gzip_compress", "legit_encrypt",
]
# Behaviourally identical to ransomware by design (a user encrypting their own
# files with a tool like GPG). Reported separately: no behavioural detector can
# tell intent, so an alarm here is expected, not a false positive to tune away.
AMBIGUOUS_BENIGN = {"legit_encrypt"}


class Logger:
    def __init__(self, path: Path):
        self._f = open(path, "a", encoding="utf-8", buffering=1)

    def __call__(self, op: str, path: Path | str = ""):
        self._f.write(json.dumps({"t": time.time(), "op": op, "path": str(path)}) + "\n")


def corpus_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.name != CORPUS_MARKER)


def _pace(rate: float, started: float, done: int) -> None:
    if rate > 0:
        delay = started + done / rate - time.time()
        if delay > 0:
            time.sleep(delay)


def run_attack(root: Path, name: str, log: Logger) -> None:
    rate, style = ATTACKS[name]
    files = corpus_files(root)
    random.shuffle(files)  # real ransomware doesn't go in directory order either
    log("attack_start")
    started = time.time()
    for i, f in enumerate(files):
        _pace(rate, started, i)
        try:
            size = f.stat().st_size
            ciphertext = os.urandom(size + 16)  # stand-in for AES output + IV
            if style == "encrypt_rename":
                f.write_bytes(ciphertext)
                f.rename(f.with_name(f.name + ".locked"))
            elif style == "encrypt_inplace":
                f.write_bytes(ciphertext)
            else:  # copy_delete
                f.with_name(f.name + ".enc").write_bytes(ciphertext)
                f.unlink()
            log("encrypted", f)
        except OSError:
            log("skipped", f)  # e.g. the recovery engine quarantined it first
    (root / "README_RESTORE_FILES.txt").write_text("Your files have been encrypted.\n")
    log("attack_end")


def run_benign(root: Path, name: str, log: Logger) -> None:
    files = corpus_files(root)
    log("workload_start")
    if name == "edit_docs":
        # A person editing a handful of documents, saving every half second.
        docs = [f for f in files if f.suffix == ".txt"][:10]
        end = time.time() + 15
        while time.time() < end:
            f = random.choice(docs)
            with open(f, "a", encoding="utf-8") as fh:
                fh.write("Edited paragraph with a few more sentences of plain text.\n")
            log("modified", f)
            time.sleep(0.5)
    elif name == "bulk_rename":
        # Photo-manager style batch rename; extensions stay the same.
        for i, f in enumerate(files):
            dest = f.with_name(f"renamed_{i:04d}{f.suffix}")
            f.rename(dest)
            log("renamed", dest)
    elif name == "zip_archive":
        # Compressing a folder: one large, high-entropy new file.
        with zipfile.ZipFile(root / "archive.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, f.relative_to(root))
        log("created", root / "archive.zip")
    elif name == "copy_folder":
        # Manual backup: copy everything into a new subfolder.
        dest_root = root / "backup_copy"
        for f in files:
            dest = dest_root / f.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dest)
            log("created", dest)
    elif name == "software_install":
        # An installer unpacking 60 compressed binaries (high entropy, all new)
        # into a fresh folder tree.
        for i in range(60):
            dest = root / "app_install" / f"lib{i % 6}" / f"module_{i:03d}.dll"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(os.urandom(random.randint(20_000, 120_000)))
            log("created", dest)
    elif name == "media_import":
        # Importing 40 photos from a camera: JPEG data is compressed, so ~8
        # bits/byte entropy, written as new files at USB-copy speed.
        dest_root = root / "photos_import"
        dest_root.mkdir(exist_ok=True)
        for i in range(40):
            dest = dest_root / f"IMG_{4000 + i}.jpg"
            dest.write_bytes(b"\xff\xd8\xff\xe0" + os.urandom(random.randint(80_000, 250_000)))
            log("created", dest)
            time.sleep(0.05)
    elif name == "gzip_compress":
        # Archiving old ledgers: real gzip output (high entropy), the original
        # deleted afterwards. Structurally the same shape as copy-then-delete
        # ransomware, which makes it the hardest honest benign case.
        for f in [f for f in files if f.suffix == ".csv"]:
            dest = f.with_name(f.name + ".gz")
            with open(f, "rb") as src, gzip.open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            f.unlink()
            log("compressed", dest)
    elif name == "legit_encrypt":
        # A user encrypting their own documents with a GPG-style tool:
        # encrypted copy written as name.gpg, original deleted.
        for f in [f for f in files if f.suffix == ".txt"][:30]:
            f.with_name(f.name + ".gpg").write_bytes(os.urandom(f.stat().st_size + 64))
            f.unlink()
            log("encrypted_by_user", f)
    elif name == "format_conversion":
        # Converting .txt notes to .md: a LEGITIMATE mass extension change,
        # the hardest benign case for an extension-based feature.
        for f in [f for f in files if f.suffix == ".txt"]:
            dest = f.with_suffix(".md")
            dest.write_text("# Note\n\n" + f.read_text(encoding="utf-8"), encoding="utf-8")
            f.unlink()
            log("converted", dest)
    log("workload_end")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--workload", required=True, choices=[*ATTACKS, *BENIGN])
    parser.add_argument("--log", required=True, type=Path)
    args = parser.parse_args()

    if not (args.root / CORPUS_MARKER).exists():
        print(f"Refusing to run: {args.root} is not a benchmark corpus (missing {CORPUS_MARKER}).", file=sys.stderr)
        return 2

    log = Logger(args.log)
    if args.workload in ATTACKS:
        run_attack(args.root, args.workload, log)
    else:
        run_benign(args.root, args.workload, log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
