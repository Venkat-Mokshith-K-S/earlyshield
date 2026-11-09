"""
Service layer for the `recovery` domain — the "Secure Automated Recovery"
half of the project title.

Lifecycle, driven by the monitoring domain:

  monitor start   -> baseline snapshot of every file in the watched folder
  benign window   -> snapshot the files that changed (keeps backups current)
  malicious window, confidence >= threshold ->
      1. suspend the attributed process        (stop further damage first)
      2. quarantine encrypted / renamed copies (moved aside, never deleted)
      3. restore originals from the newest clean shadow copy
      4. write every step to the recovery_actions audit log

While an incident is active, no new snapshots are taken, so content
written during the attack can never become a "clean" backup.
"""

import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import AppException, NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.domains.recovery import process_control
from app.domains.recovery.models import RecoveryAction, RecoveryActionStatus, RecoveryActionType
from app.domains.recovery.schemas import (
    ProtectedFile,
    RecoverySettingsUpdate,
    RecoveryStatusResponse,
    RestoreResult,
    SuspendedProcess,
)
from app.domains.recovery.vault import ShadowVault, VaultIntegrityError, is_within

logger = get_logger(__name__)

RESTORE_TMP_MARKER = ".earlyshield-restore"


class VaultInsideWatchPathError(AppException):
    status_code = 422
    error_code = "VAULT_INSIDE_WATCH_PATH"


class NoWatchedFolderError(AppException):
    status_code = 409
    error_code = "MONITOR_NOT_RUNNING"


class ProcessActionError(AppException):
    status_code = 409
    error_code = "PROCESS_ACTION_FAILED"


@dataclass
class FileChange:
    """One file's net change over a monitoring window."""

    original: str            # path at the start of the window
    final: Optional[str]     # path at the end (after renames); None if deleted
    kind: str                # created | modified | moved | deleted
    from_previous_window: bool = False


class RecoveryService:
    # Runtime-adjustable copies of the settings (admins can flip them from
    # the dashboard without a restart; they reset to .env values on reboot).
    auto_response: bool = settings.RECOVERY_AUTO_RESPONSE
    auto_suspend: bool = settings.RECOVERY_AUTO_SUSPEND
    confidence_threshold: float = settings.RECOVERY_CONFIDENCE_THRESHOLD

    # Overridable so tests (and the monitor's background thread, which has
    # no request-scoped session) share one way of getting a DB session.
    session_factory: Callable[[], Session] = SessionLocal

    _vault_instance: Optional[ShadowVault] = None
    _watch_root: Optional[Path] = None
    _op_lock = threading.RLock()

    _active_incident_id: Optional[uuid.UUID] = None
    _incident_cutoff: float = 0.0
    _incident_last_seen: float = 0.0
    _window_seconds: float = 10.0

    _suspended: Dict[int, SuspendedProcess] = {}

    # --- vault access ----------------------------------------------------

    @classmethod
    def vault(cls) -> ShadowVault:
        if cls._vault_instance is None:
            cls._vault_instance = ShadowVault(
                Path(settings.RECOVERY_VAULT_PATH).resolve(),
                max_file_bytes=int(settings.RECOVERY_MAX_FILE_MB * 1024 * 1024),
                max_versions=settings.RECOVERY_MAX_VERSIONS_PER_FILE,
            )
        return cls._vault_instance

    @classmethod
    def reset_vault(cls, vault_path: Path) -> None:
        """Point the service at a different vault (used by tests)."""
        cls._vault_instance = ShadowVault(
            vault_path,
            max_file_bytes=int(settings.RECOVERY_MAX_FILE_MB * 1024 * 1024),
            max_versions=settings.RECOVERY_MAX_VERSIONS_PER_FILE,
        )

    # --- audit log -------------------------------------------------------

    @classmethod
    def _log(
        cls,
        action_type: RecoveryActionType,
        status: RecoveryActionStatus,
        detail: str,
        target: Optional[str] = None,
        incident_id: Optional[uuid.UUID] = None,
        triggered_by: str = "auto",
        extra: Optional[dict] = None,
    ) -> None:
        log = logger.warning if status == RecoveryActionStatus.FAILED else logger.info
        log("[recovery] %s %s: %s %s", action_type.value, status.value, target or "", detail)
        try:
            db = cls.session_factory()
            try:
                db.add(RecoveryAction(
                    incident_id=incident_id,
                    action_type=action_type.value,
                    status=status.value,
                    target=target,
                    detail=detail,
                    triggered_by=triggered_by,
                    extra=extra,
                ))
                db.commit()
            finally:
                db.close()
        except Exception:  # noqa: BLE001 - a DB outage must never stop the recovery itself
            logger.exception("Could not write recovery action to the audit log")

    # --- hooks called by the monitoring domain -----------------------------

    @classmethod
    def on_monitor_start(cls, watch_root: Path, window_seconds: float) -> None:
        vault_root = cls.vault().root
        if is_within(vault_root, watch_root):
            raise VaultInsideWatchPathError(
                "The recovery vault is inside the watched folder; ransomware there could encrypt the backups too. "
                "Set RECOVERY_VAULT_PATH to a location outside it.",
                details={"vault_path": str(vault_root), "watch_path": str(watch_root)},
            )
        cls._watch_root = watch_root.resolve()
        cls._window_seconds = window_seconds
        cls._active_incident_id = None
        cls._take_full_snapshot(RecoveryActionType.BASELINE_SNAPSHOT, "auto")

    @classmethod
    def on_monitor_stop(cls) -> None:
        cls._watch_root = None
        cls._active_incident_id = None

    @classmethod
    def incident_active(cls) -> bool:
        if cls._active_incident_id is None:
            return False
        # An incident "cools down" after three quiet windows.
        return time.time() - cls._incident_last_seen < 3 * cls._window_seconds

    @classmethod
    def capture_benign_window(cls, paths: List[str]) -> None:
        if cls._watch_root is None or cls.incident_active():
            return
        candidates = [
            Path(p) for p in paths
            if RESTORE_TMP_MARKER not in p and is_within(Path(p), cls._watch_root)
        ]
        if candidates:
            with cls._op_lock:
                cls.vault().capture(candidates)

    @classmethod
    def follow_up_incident(cls, changes: List[FileChange]) -> Set[str]:
        """
        A window the model scored benign, while an incident is still active.

        Two things slip past a window-level score: a ransom note dropped after
        the last flagged window, and slow in-place encryption whose windows
        hover just under the threshold. While an incident is open, any file
        that is new with no history, or whose content jumped to encrypted-level
        entropy against its first snapshot, is handled as part of that
        incident. Finding one keeps the incident open. Outside an incident
        this does nothing, so ordinary benign windows are never touched.
        """
        if not cls.auto_response or cls._watch_root is None or not cls.incident_active():
            return set()
        vault = cls.vault()
        hostile = []
        for change in changes:
            if change.final is None or RESTORE_TMP_MARKER in change.final:
                continue
            original, final = Path(change.original), Path(change.final)
            if not is_within(final, cls._watch_root):
                continue
            is_new_artifact = change.kind == "created" and not vault.has(original) and not vault.has(final)
            if is_new_artifact or vault.looks_encrypted(original, final):
                hostile.append(change)
        if not hostile:
            return set()

        with cls._op_lock:
            cls._incident_last_seen = time.time()  # the attack is still going: keep the incident open
            incident_id = cls._active_incident_id
            counts, touched = cls._recover_files(hostile, incident_id)
            cls._log(
                RecoveryActionType.INCIDENT_SUMMARY,
                RecoveryActionStatus.SUCCESS if counts["failed"] == 0 else RecoveryActionStatus.FAILED,
                f"Follow-up during the active incident (window scored benign): "
                f"{counts['restored']} file(s) restored, {counts['quarantined']} quarantined, "
                f"{counts['failed']} failed.",
                incident_id=incident_id,
                extra={**counts, "follow_up": True},
            )
        return touched

    @classmethod
    def respond_to_detection(
        cls,
        changes: List[FileChange],
        confidence: float,
        pid: Optional[int],
        process_name: Optional[str],
        io_write_rate_mb_s: float,
    ) -> Tuple[Optional[uuid.UUID], Set[str]]:
        """
        Runs the automated response for one ransomware-like window. Returns
        (incident_id, paths_touched) — the monitor ignores events on the
        touched paths so our own restores aren't mistaken for new activity.
        """
        if not cls.auto_response or cls._watch_root is None:
            return None, set()
        if confidence < cls.confidence_threshold:
            logger.info("Detection below auto-response threshold (%.2f < %.2f); alert only",
                        confidence, cls.confidence_threshold)
            return None, set()

        now = time.time()
        with cls._op_lock:
            if not cls.incident_active():
                cls._active_incident_id = uuid.uuid4()
                # Anything captured during the previous (benign) window is
                # still trusted; anything later isn't.
                cls._incident_cutoff = now - cls._window_seconds / 2
            cls._incident_last_seen = now
            incident_id = cls._active_incident_id

            suspended = cls._auto_suspend(pid, process_name, io_write_rate_mb_s, incident_id)
            counts, touched = cls._recover_files(changes, incident_id)

            cls._log(
                RecoveryActionType.INCIDENT_SUMMARY,
                RecoveryActionStatus.SUCCESS if counts["failed"] == 0 else RecoveryActionStatus.FAILED,
                f"Confidence {confidence:.0%}. Process {'suspended' if suspended else 'not suspended'}; "
                f"{counts['restored']} file(s) restored, {counts['quarantined']} quarantined, "
                f"{counts['no_backup']} without a clean backup, {counts['failed']} failed.",
                incident_id=incident_id,
                extra={**counts, "confidence": confidence, "pid": pid, "process": process_name},
            )
        return incident_id, touched

    # --- automated response steps ----------------------------------------

    @classmethod
    def _auto_suspend(cls, pid: Optional[int], name: Optional[str], write_mb_s: float, incident_id: uuid.UUID) -> bool:
        if not cls.auto_suspend:
            return False
        if pid is None:
            cls._log(RecoveryActionType.SUSPEND_PROCESS, RecoveryActionStatus.SKIPPED,
                     "No process could be attributed to this activity", incident_id=incident_id)
            return False
        if pid in cls._suspended:
            return True
        if write_mb_s <= 0:
            # The busiest process didn't write anything, so it almost
            # certainly isn't the one encrypting files. Don't guess.
            cls._log(RecoveryActionType.SUSPEND_PROCESS, RecoveryActionStatus.SKIPPED,
                     "Most active process performed no disk writes; attribution too weak to act on",
                     target=f"{name} (PID {pid})", incident_id=incident_id)
            return False
        try:
            actual_name = process_control.suspend(pid, expected_name=name)
        except process_control.ProcessControlError as exc:
            cls._log(RecoveryActionType.SUSPEND_PROCESS, RecoveryActionStatus.SKIPPED, str(exc),
                     target=f"{name} (PID {pid})", incident_id=incident_id)
            return False
        cls._suspended[pid] = SuspendedProcess(
            pid=pid, name=actual_name, suspended_at=datetime.now(timezone.utc), incident_id=incident_id
        )
        cls._log(RecoveryActionType.SUSPEND_PROCESS, RecoveryActionStatus.SUCCESS,
                 "Process suspended (reversible — resume it from the dashboard if this was a false positive)",
                 target=f"{actual_name} (PID {pid})", incident_id=incident_id)
        return True

    @classmethod
    def _recover_files(cls, changes: List[FileChange], incident_id: uuid.UUID) -> Tuple[dict, Set[str]]:
        vault = cls.vault()
        root = cls._watch_root
        counts = {"restored": 0, "quarantined": 0, "no_backup": 0, "failed": 0}
        touched: Set[str] = set()

        # One entry per original file; prefer the current window's view.
        by_original: Dict[str, FileChange] = {}
        for change in changes:
            existing = by_original.get(change.original)
            if existing is None or (existing.from_previous_window and not change.from_previous_window):
                by_original[change.original] = change
            elif change.final != change.original and change.final is not None:
                by_original[change.original] = change

        for change in by_original.values():
            original = Path(change.original)
            final = Path(change.final) if change.final else None
            if RESTORE_TMP_MARKER in change.original or not is_within(original, root):
                continue
            try:
                version = vault.pick_clean_version(original, before=cls._incident_cutoff)

                if version is None:
                    # A file that appeared during the attack with no history —
                    # typically an encrypted copy or a ransom note.
                    if (not change.from_previous_window and change.kind in ("created", "moved")
                            and final is not None and final.exists() and not vault.has(final)):
                        dest = vault.quarantine(final, str(incident_id), root)
                        touched.add(str(final))
                        counts["quarantined"] += 1
                        cls._log(RecoveryActionType.QUARANTINE_FILE, RecoveryActionStatus.SUCCESS,
                                 f"New file created during the attack moved to {dest}",
                                 target=str(final), incident_id=incident_id)
                    elif vault.has(original) or change.kind != "created":
                        counts["no_backup"] += 1
                    continue

                if final == original and vault.current_matches(original, version):
                    continue  # untouched by the attack after all

                if final is not None and final != original and final.exists():
                    dest = vault.quarantine(final, str(incident_id), root)
                    touched.add(str(final))
                    counts["quarantined"] += 1
                    cls._log(RecoveryActionType.QUARANTINE_FILE, RecoveryActionStatus.SUCCESS,
                             f"Encrypted/renamed copy moved to {dest}", target=str(final), incident_id=incident_id)
                if original.exists() and not vault.current_matches(original, version):
                    dest = vault.quarantine(original, str(incident_id), root)
                    touched.add(str(original))
                    counts["quarantined"] += 1
                    cls._log(RecoveryActionType.QUARANTINE_FILE, RecoveryActionStatus.SUCCESS,
                             f"Modified file moved to {dest}", target=str(original), incident_id=incident_id)

                vault.restore(original, version)
                touched.add(str(original))
                touched.add(str(original.with_name(f".{original.name}{RESTORE_TMP_MARKER}")))
                counts["restored"] += 1
                captured = datetime.fromtimestamp(version.captured_at, timezone.utc).isoformat(timespec="seconds")
                cls._log(RecoveryActionType.RESTORE_FILE, RecoveryActionStatus.SUCCESS,
                         f"Restored from shadow copy captured {captured} (sha256 verified)",
                         target=str(original), incident_id=incident_id,
                         extra={"sha256": version.sha256})
            except (OSError, VaultIntegrityError) as exc:
                counts["failed"] += 1
                cls._log(RecoveryActionType.RESTORE_FILE, RecoveryActionStatus.FAILED, str(exc),
                         target=str(original), incident_id=incident_id)
        return counts, touched

    @classmethod
    def _take_full_snapshot(cls, action_type: RecoveryActionType, triggered_by: str) -> int:
        root = cls._watch_root
        files: List[Path] = []
        limit = settings.RECOVERY_MAX_BASELINE_FILES
        for dirpath, _dirs, filenames in os.walk(root):
            files.extend(Path(dirpath) / n for n in filenames if RESTORE_TMP_MARKER not in n)
            if len(files) >= limit:
                logger.warning("Baseline capped at %d files (RECOVERY_MAX_BASELINE_FILES)", limit)
                files = files[:limit]
                break
        with cls._op_lock:
            stored = cls.vault().capture(files)
        cls._log(action_type, RecoveryActionStatus.SUCCESS,
                 f"Scanned {len(files)} file(s); {stored} new shadow cop{'y' if stored == 1 else 'ies'} stored",
                 target=str(root), triggered_by=triggered_by)
        return stored

    # --- user-facing operations (router) ---------------------------------

    @classmethod
    def get_status(cls) -> RecoveryStatusResponse:
        stats = cls.vault().stats()
        return RecoveryStatusResponse(
            auto_response=cls.auto_response,
            auto_suspend=cls.auto_suspend,
            confidence_threshold=cls.confidence_threshold,
            vault_path=str(cls.vault().root),
            suspended_processes=list(cls._suspended.values()),
            active_incident_id=cls._active_incident_id if cls.incident_active() else None,
            **stats,
        )

    @classmethod
    def update_settings(cls, data: RecoverySettingsUpdate, user_email: str) -> RecoveryStatusResponse:
        changes = data.model_dump(exclude_none=True)
        for key, value in changes.items():
            setattr(cls, key, value)
        logger.info("Recovery settings changed by %s: %s", user_email, changes)
        return cls.get_status()

    @classmethod
    def list_actions(cls, db: Session, limit: int, incident_id: Optional[uuid.UUID] = None) -> List[RecoveryAction]:
        query = select(RecoveryAction).order_by(RecoveryAction.created_at.desc()).limit(limit)
        if incident_id is not None:
            query = query.where(RecoveryAction.incident_id == incident_id)
        return list(db.scalars(query))

    @classmethod
    def list_protected_files(cls, limit: int) -> List[ProtectedFile]:
        items = cls.vault().list_files(under=cls._watch_root, limit=limit)
        return [
            ProtectedFile(
                path=i["path"],
                versions=i["versions"],
                latest_captured_at=datetime.fromtimestamp(i["latest_captured_at"], timezone.utc)
                if i["latest_captured_at"] else None,
                exists=i["exists"],
            )
            for i in items
        ]

    @classmethod
    def manual_snapshot(cls, user_email: str) -> int:
        if cls._watch_root is None:
            raise NoWatchedFolderError("Start the monitor first; snapshots are taken of the watched folder.")
        return cls._take_full_snapshot(RecoveryActionType.MANUAL_SNAPSHOT, user_email)

    @classmethod
    def manual_restore(cls, paths: List[str], before: Optional[datetime], user_email: str) -> RestoreResult:
        vault = cls.vault()
        cutoff = before.timestamp() if before else None
        restored = skipped = failed = 0
        with cls._op_lock:
            for raw in paths:
                path = Path(raw)
                # Only files the vault has actually backed up can be written
                # to, which also rules out writing to arbitrary paths.
                if not vault.has(path):
                    raise ValidationError(f"'{raw}' has no shadow copies", details={"path": raw})
                version = vault.pick_clean_version(path, before=cutoff)
                if version is None:
                    skipped += 1
                    cls._log(RecoveryActionType.RESTORE_FILE, RecoveryActionStatus.SKIPPED,
                             "No clean version available for the requested time", target=raw,
                             triggered_by=user_email)
                    continue
                if vault.current_matches(path, version):
                    skipped += 1
                    continue
                try:
                    if path.exists():
                        vault.quarantine(path, f"manual-{int(time.time())}", cls._watch_root or path.parent)
                    vault.restore(path, version)
                    restored += 1
                    cls._log(RecoveryActionType.RESTORE_FILE, RecoveryActionStatus.SUCCESS,
                             "Restored manually (sha256 verified); previous content quarantined",
                             target=raw, triggered_by=user_email, extra={"sha256": version.sha256})
                except (OSError, VaultIntegrityError) as exc:
                    failed += 1
                    cls._log(RecoveryActionType.RESTORE_FILE, RecoveryActionStatus.FAILED, str(exc),
                             target=raw, triggered_by=user_email)
        return RestoreResult(restored=restored, skipped=skipped, failed=failed)

    @classmethod
    def resume_process(cls, pid: int, user_email: str) -> None:
        record = cls._suspended.get(pid)
        if record is None:
            raise NotFoundError(f"PID {pid} was not suspended by EarlyShield")
        try:
            name = process_control.resume(pid)
        except process_control.ProcessControlError as exc:
            cls._suspended.pop(pid, None)
            cls._log(RecoveryActionType.RESUME_PROCESS, RecoveryActionStatus.FAILED, str(exc),
                     target=f"{record.name} (PID {pid})", incident_id=record.incident_id, triggered_by=user_email)
            raise ProcessActionError(str(exc))
        cls._suspended.pop(pid, None)
        cls._log(RecoveryActionType.RESUME_PROCESS, RecoveryActionStatus.SUCCESS,
                 "Process resumed by an analyst", target=f"{name} (PID {pid})",
                 incident_id=record.incident_id, triggered_by=user_email)
