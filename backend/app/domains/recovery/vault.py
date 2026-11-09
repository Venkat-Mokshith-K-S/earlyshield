"""
Shadow-copy vault: versioned, content-addressed backups of watched files.

Layout on disk (RECOVERY_VAULT_PATH):
    blobs/<sha256>            file contents, named by their own hash, read-only
    quarantine/<incident>/... suspicious files moved aside (never deleted)
    manifest.json             {absolute_path: {"first_entropy": float,
                                               "versions": [{sha256, size, entropy, captured_at}, ...]}}

Security properties (see MODULE5_README for the honest limits):
  * Content addressing — a blob's name IS its SHA-256, so every restore
    re-hashes the blob and refuses it if the content was tampered with.
  * The vault must live outside the watched directory, so whatever is
    encrypting the watched files isn't also walking the backups.
  * Blobs are written read-only; quarantined files are moved, not deleted,
    so a false positive is always fully reversible.
"""

import hashlib
import json
import os
import shutil
import stat
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.core.logging_config import get_logger
from app.shared.entropy import file_entropy

logger = get_logger(__name__)

# A version whose entropy jumped this far above the file's first-ever
# snapshot is treated as "probably already encrypted" and skipped when
# picking what to restore. Plain text sits around 4-5 bits/byte, encrypted
# data at ~8, so a jump of this size is the encryption signature itself.
ENCRYPTION_ENTROPY_JUMP = 1.5


class VaultIntegrityError(Exception):
    pass


@dataclass
class FileVersion:
    sha256: str
    size: int
    entropy: float
    captured_at: float  # unix epoch seconds


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _entropy_of(path: Path) -> float:
    return file_entropy(path) or 0.0


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


class ShadowVault:
    def __init__(self, root: Path, max_file_bytes: int, max_versions: int):
        self.root = root
        self.max_file_bytes = max_file_bytes
        self.max_versions = max_versions
        self._blobs = root / "blobs"
        self._quarantine = root / "quarantine"
        self._manifest_path = root / "manifest.json"
        self._lock = threading.RLock()
        self._blobs.mkdir(parents=True, exist_ok=True)
        self._quarantine.mkdir(parents=True, exist_ok=True)
        self._manifest: Dict[str, dict] = self._load_manifest()

    # --- manifest persistence ------------------------------------------

    def _load_manifest(self) -> Dict[str, dict]:
        if not self._manifest_path.exists():
            return {}
        try:
            return json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Vault manifest unreadable; starting with an empty one")
            return {}

    def _save_manifest(self) -> None:
        # Write-then-rename so a crash mid-write never leaves a truncated manifest.
        tmp = self._manifest_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._manifest), encoding="utf-8")
        os.replace(tmp, self._manifest_path)

    # --- capture ---------------------------------------------------------

    def capture(self, paths: List[Path]) -> int:
        """Snapshot each file's current content. Returns how many new versions were stored."""
        stored = 0
        with self._lock:
            for path in paths:
                try:
                    if self._capture_one(path):
                        stored += 1
                except OSError as exc:
                    logger.debug("Could not snapshot %s: %s", path, exc)
            if stored:
                self._save_manifest()
        return stored

    def _capture_one(self, path: Path) -> bool:
        if not path.is_file() or path.stat().st_size > self.max_file_bytes:
            return False
        sha = _sha256_of(path)
        key = str(path.resolve())
        entry = self._manifest.setdefault(key, {"first_entropy": None, "versions": []})
        if entry["versions"] and entry["versions"][-1]["sha256"] == sha:
            return False  # unchanged since the last snapshot

        blob = self._blobs / sha
        if not blob.exists():
            tmp = blob.with_suffix(".tmp")
            shutil.copyfile(path, tmp)
            os.replace(tmp, blob)
            os.chmod(blob, stat.S_IREAD)

        entropy = _entropy_of(path)
        if entry["first_entropy"] is None:
            entry["first_entropy"] = entropy
        entry["versions"].append(asdict(FileVersion(sha, path.stat().st_size, round(entropy, 4), time.time())))
        self._prune(entry)
        return True

    def _prune(self, entry: dict) -> None:
        while len(entry["versions"]) > self.max_versions:
            old = entry["versions"].pop(0)
            if not self._blob_referenced(old["sha256"]):
                blob = self._blobs / old["sha256"]
                try:
                    os.chmod(blob, stat.S_IWRITE | stat.S_IREAD)
                    blob.unlink()
                except OSError:
                    pass

    def _blob_referenced(self, sha: str) -> bool:
        return any(v["sha256"] == sha for e in self._manifest.values() for v in e["versions"])

    # --- lookup ------------------------------------------------------------

    def has(self, path: Path) -> bool:
        return str(path.resolve()) in self._manifest

    def looks_encrypted(self, original: Path, current: Path) -> bool:
        """
        True if `current` (the file now standing where/for `original`) has
        jumped to encrypted-level entropy compared with original's first
        snapshot. The same test pick_clean_version uses to reject versions.
        """
        with self._lock:
            entry = self._manifest.get(str(original.resolve()))
            if not entry or entry["first_entropy"] is None:
                return False
            ceiling = entry["first_entropy"] + ENCRYPTION_ENTROPY_JUMP
        try:
            return current.is_file() and _entropy_of(current) > ceiling
        except OSError:
            return False

    def pick_clean_version(self, path: Path, before: Optional[float] = None) -> Optional[FileVersion]:
        """Newest version captured before `before` that doesn't look encrypted."""
        with self._lock:
            entry = self._manifest.get(str(path.resolve()))
            if not entry:
                return None
            ceiling = (entry["first_entropy"] or 0.0) + ENCRYPTION_ENTROPY_JUMP
            for v in reversed(entry["versions"]):
                if before is not None and v["captured_at"] >= before:
                    continue
                if v["entropy"] > ceiling:
                    continue
                return FileVersion(**v)
        return None

    def current_matches(self, path: Path, version: FileVersion) -> bool:
        try:
            return path.is_file() and _sha256_of(path) == version.sha256
        except OSError:
            return False

    # --- restore / quarantine -------------------------------------------

    def restore(self, path: Path, version: FileVersion) -> None:
        blob = self._blobs / version.sha256
        if not blob.exists():
            raise VaultIntegrityError(f"Backup blob {version.sha256[:12]}… is missing from the vault")
        if _sha256_of(blob) != version.sha256:
            raise VaultIntegrityError(f"Backup blob {version.sha256[:12]}… failed its integrity check")

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.earlyshield-restore")
        shutil.copyfile(blob, tmp)
        os.replace(tmp, path)

    def quarantine(self, path: Path, incident_id: str, watch_root: Path) -> Path:
        try:
            relative = path.resolve().relative_to(watch_root.resolve())
        except ValueError:
            relative = Path(path.name)
        dest = self._quarantine / incident_id / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest = dest.with_name(f"{dest.name}.{int(time.time() * 1000)}")
        shutil.move(str(path), str(dest))
        return dest

    # --- stats -----------------------------------------------------------

    def stats(self) -> dict:
        with self._lock:
            versions = sum(len(e["versions"]) for e in self._manifest.values())
            files = len(self._manifest)
        blob_bytes = sum(p.stat().st_size for p in self._blobs.iterdir() if p.is_file())
        quarantined = sum(1 for p in self._quarantine.rglob("*") if p.is_file())
        return {
            "files_protected": files,
            "versions_stored": versions,
            "vault_size_bytes": blob_bytes,
            "quarantined_files": quarantined,
        }

    def list_files(self, under: Optional[Path] = None, limit: int = 500) -> List[dict]:
        with self._lock:
            items = []
            for key, entry in self._manifest.items():
                if under is not None and not is_within(Path(key), under):
                    continue
                latest = entry["versions"][-1] if entry["versions"] else None
                items.append({
                    "path": key,
                    "versions": len(entry["versions"]),
                    "latest_captured_at": latest["captured_at"] if latest else None,
                    "exists": Path(key).exists(),
                })
        items.sort(key=lambda i: i["path"])
        return items[:limit]
