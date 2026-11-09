"""
Service layer for the `monitoring` domain.

Architecture:
  watchdog.Observer runs in its own background thread, firing our
  FileSystemEventHandler on every create/modify/delete/move under the
  watched directory. The handler ONLY buffers raw events (cheap, non-
  blocking) — no feature computation happens on the watchdog thread.

  A separate background thread (`_aggregation_loop`) wakes up every
  `window_seconds`, drains the event buffer, computes the 11 behavioral
  features for that window, samples psutil for the most active process,
  calls DetectionService.analyze(), and appends the result to an
  in-memory event log.

  Each window's result is then handed to the recovery domain (Module 5):
  benign windows refresh the shadow copies of changed files; a confident
  ransomware-like window triggers the automated response. Files the
  recovery engine itself writes are ignored for a couple of windows so a
  restore isn't analyzed as fresh suspicious activity.

KNOWN LIMITATION (documented honestly, not hidden — see project README):
  Attributing a specific file change to the specific process that caused
  it requires kernel-level hooks (ETW on Windows, fanotify/audit on
  Linux) — the kind of access real EDR products use. Pure Python,
  cross-platform tooling cannot do this precisely. This service instead
  approximates "the responsible process" as whichever process had the
  highest combined CPU + disk-write activity during the observation
  window. This is a defensible academic approximation, not a claim of
  precise process-level attribution.
"""

import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Optional

import psutil
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging_config import get_logger
from app.domains.detection.schemas import FileActivityFeatures
from app.domains.detection.service import DetectionService
from app.domains.monitoring.schemas import DetectionEvent, MonitorStatusResponse
from app.domains.recovery.service import RESTORE_TMP_MARKER, FileChange, RecoveryService
from app.shared.entropy import file_entropy

logger = get_logger(__name__)



class MonitorAlreadyRunningError(AppException):
    status_code = 409
    error_code = "MONITOR_ALREADY_RUNNING"


class MonitorNotRunningError(AppException):
    status_code = 409
    error_code = "MONITOR_NOT_RUNNING"


class InvalidWatchPathError(AppException):
    status_code = 422
    error_code = "INVALID_WATCH_PATH"


def _read_entropy_and_size(path: Path):
    try:
        entropy = file_entropy(path)
        return (entropy, path.stat().st_size) if entropy is not None else (None, None)
    except OSError:
        return None, None


def _resolve_final_path(src_path: str, moved_events: list, deleted_paths: set) -> Optional[str]:
    """
    Follows a chain of rename events starting at src_path to find where that
    file ended up by the end of the window (e.g. a.txt -> a.txt.tmp ->
    a.txt.locked). Returns None if the file was ultimately deleted.
    """
    current = src_path
    seen = {current}  # guard against pathological rename cycles
    changed = True
    while changed:
        changed = False
        if current in deleted_paths:
            return None
        for e in moved_events:
            if e["src_path"] == current and e["dest_path"] not in seen:
                current = e["dest_path"]
                seen.add(current)
                changed = True
                break
    return current


class _BufferingEventHandler(FileSystemEventHandler):
    """Runs on watchdog's thread. Only buffers events — no file I/O here.

    File content is read at WINDOW-END (see _process_window), not at
    event-time. This was a deliberate design change after testing revealed
    a race: a common ransomware pattern is write-encrypted-content-then-
    rename (e.g. `invoice.docx` -> `invoice.docx.locked`), and reading
    synchronously in the event callback could catch the file either
    mid-write (empty/incomplete, mistakenly attributed as 0 entropy) or
    already-renamed-away (FileNotFoundError) — both are genuine races
    against the OS's own event delivery timing, not something a fixed
    retry count reliably wins. Deferring to window-end and resolving
    rename chains (see _resolve_final_path) reads each file only after
    all of a window's rapid churn has settled, which is both simpler and
    provably race-free.
    """

    def __init__(self, buffer: Deque[dict], lock: threading.Lock):
        super().__init__()
        self._buffer = buffer
        self._lock = lock

    def _push(self, event_type: str, src_path: str, dest_path: Optional[str] = None):
        with self._lock:
            self._buffer.append({
                "type": event_type,
                "src_path": src_path,
                "dest_path": dest_path,
                "ts": time.monotonic(),
            })

    def on_created(self, event):
        if not event.is_directory:
            self._push("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._push("modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._push("deleted", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._push("moved", event.src_path, event.dest_path)


class FileSystemMonitorService:
    """
    Singleton-style service (class-level state) managing one active monitor
    at a time — matches the scope of a single-machine detection agent.
    """

    _observer: Optional[Observer] = None
    _handler: Optional[_BufferingEventHandler] = None
    _agg_thread: Optional[threading.Thread] = None
    _sampler_thread: Optional[threading.Thread] = None
    _stop_flag = threading.Event()
    _buffer_lock = threading.Lock()
    _event_buffer: Deque[dict] = deque()

    _watch_path: Optional[str] = None
    _window_seconds: float = 10.0
    _windows_processed: int = 0
    _started_at: Optional[datetime] = None

    # Per-file baselines, used to compute entropy_delta / avg_size_change_ratio /
    # extension_change_ratio relative to each file's own history.
    _file_baseline_entropy: Dict[str, float] = {}
    _file_baseline_size: Dict[str, int] = {}
    _file_baseline_ext: Dict[str, str] = {}

    _events_log: Deque[DetectionEvent] = deque(maxlen=200)
    _events_log_lock = threading.Lock()

    # path -> monotonic expiry. Events on these paths were caused by the
    # recovery engine's own quarantine/restore, not by a process under watch.
    _suppressed_paths: Dict[str, float] = {}
    # The previous window's changes, so an incident can also undo damage
    # from the window just before detection (an attack's first seconds).
    _prev_changes: List[FileChange] = []

    # --- Public API -----------------------------------------------------

    @classmethod
    def start(cls, watch_path: str, window_seconds: float) -> MonitorStatusResponse:
        if cls._observer is not None:
            raise MonitorAlreadyRunningError(
                "A monitor is already running. Stop it before starting a new one.",
                details={"currently_watching": cls._watch_path},
            )

        path = Path(watch_path)
        if not path.exists() or not path.is_dir():
            raise InvalidWatchPathError(
                f"'{watch_path}' does not exist or is not a directory.",
                details={"watch_path": watch_path},
            )

        # Baseline shadow copy BEFORE watching starts, so every existing
        # file is recoverable from the very first window. Also refuses to
        # start if the vault sits inside the watched folder.
        RecoveryService.on_monitor_start(path.resolve(), window_seconds)

        cls._event_buffer.clear()
        cls._suppressed_paths.clear()
        cls._prev_changes = []
        cls._file_baseline_entropy.clear()
        cls._file_baseline_size.clear()
        cls._file_baseline_ext.clear()
        cls._windows_processed = 0
        cls._watch_path = str(path.resolve())
        cls._window_seconds = window_seconds
        cls._stop_flag.clear()
        cls._seed_baselines(path.resolve())
        cls._proc_prev = {}
        cls._latest_sample = (None, None, 0.0, 0.0, 1.0)

        cls._handler = _BufferingEventHandler(cls._event_buffer, cls._buffer_lock)

        # inotify (the default, fast, event-driven Observer) does not
        # reliably propagate file-change notifications across a Docker
        # Desktop for Windows bind mount when files are created/edited
        # from the Windows side rather than from inside the Linux
        # container — a well-documented Docker Desktop limitation, not a
        # bug in this code. PollingObserver works around it by actively
        # re-scanning the directory instead of waiting for kernel events.
        # Set FILE_MONITOR_USE_POLLING=false in .env for native Linux
        # deployments, where inotify is faster and this workaround isn't
        # needed.
        if settings.FILE_MONITOR_USE_POLLING:
            cls._observer = PollingObserver(timeout=1.0)
        else:
            cls._observer = Observer()
        cls._observer.schedule(cls._handler, cls._watch_path, recursive=True)
        cls._observer.start()

        # watchdog's Observer.start() launches its background thread, but
        # that thread's underlying OS-level watch (inotify_add_watch, etc.)
        # is armed asynchronously — a race that showed up in testing as the
        # very first window after start() missing file events created
        # immediately afterward. A brief wait here ensures the watch is
        # actually live before we tell the caller monitoring has begun.
        time.sleep(0.3)

        cls._agg_thread = threading.Thread(target=cls._aggregation_loop, daemon=True)
        cls._agg_thread.start()
        cls._sampler_thread = threading.Thread(target=cls._sampler_loop, daemon=True)
        cls._sampler_thread.start()

        cls._started_at = datetime.now(timezone.utc)
        logger.info("Monitor started on '%s' (window=%.1fs)", cls._watch_path, window_seconds)
        return cls.get_status()

    @classmethod
    def stop(cls) -> MonitorStatusResponse:
        if cls._observer is None:
            raise MonitorNotRunningError("No monitor is currently running.")

        cls._stop_flag.set()
        cls._observer.stop()
        cls._observer.join(timeout=5)
        if cls._agg_thread:
            cls._agg_thread.join(timeout=5)
        if cls._sampler_thread:
            cls._sampler_thread.join(timeout=5)

        RecoveryService.on_monitor_stop()
        status = cls.get_status()
        cls._observer = None
        cls._handler = None
        cls._agg_thread = None
        cls._sampler_thread = None
        cls._watch_path = None
        logger.info("Monitor stopped")
        return status

    @classmethod
    def get_status(cls) -> MonitorStatusResponse:
        return MonitorStatusResponse(
            is_running=cls._observer is not None,
            watch_path=cls._watch_path,
            window_seconds=cls._window_seconds if cls._observer is not None else None,
            windows_processed=cls._windows_processed,
            started_at=cls._started_at,
        )

    @classmethod
    def get_recent_events(cls, limit: int = 20) -> List[DetectionEvent]:
        with cls._events_log_lock:
            events = list(cls._events_log)
        return list(reversed(events))[:limit]

    # --- Internal: background aggregation loop ---------------------------

    @classmethod
    def _aggregation_loop(cls):
        # Fixed cadence: windows END every `window_seconds`, regardless of
        # how long processing took. (Waiting a full window AFTER processing,
        # as an earlier version did, stretched a "5 s" window to ~10 s on
        # Windows and directly delayed detection.) Rates are divided by the
        # real elapsed time, so a window that ran long still yields
        # correct per-second features.
        window = cls._window_seconds
        last_boundary = time.monotonic()
        next_deadline = last_boundary + window
        while not cls._stop_flag.wait(timeout=max(0.0, next_deadline - time.monotonic())):
            now = time.monotonic()
            elapsed = now - last_boundary
            last_boundary = now
            next_deadline += window
            if next_deadline <= now:  # fell behind (e.g. a long recovery); don't fire a burst of tiny windows
                next_deadline = now + window
            try:
                cls._process_window(elapsed)
            except Exception:  # noqa: BLE001 - never let the background loop die silently
                logger.exception("Error while processing a monitoring window")

    @classmethod
    def _process_window(cls, elapsed: Optional[float] = None):
        with cls._buffer_lock:
            events = list(cls._event_buffer)
            cls._event_buffer.clear()
        events = cls._drop_self_inflicted(events)

        window_seconds = cls._window_seconds
        elapsed = max(elapsed or window_seconds, 0.001)
        cls._windows_processed += 1

        modified = [e for e in events if e["type"] == "modified"]
        created = [e for e in events if e["type"] == "created"]
        deleted = [e for e in events if e["type"] == "deleted"]
        moved = [e for e in events if e["type"] == "moved"]

        touched_paths = {e["src_path"] for e in events}
        unique_dirs = {str(Path(p).parent) for p in touched_paths}
        changes = cls._summarize_changes(modified, created, moved, deleted)

        # --- content features ---------------------------------------------
        # Reads happen HERE, at window-end: by now any individual write has
        # settled (no races against in-flight writes). Renamed files are
        # read from their FINAL path in the chain, not their original
        # (possibly already-gone) path; see _resolve_final_path.
        #
        # Each file is compared against its baseline from BEFORE this
        # window, seeded for every existing file when monitoring starts.
        # (An earlier version recorded a file's baseline the first time it
        # changed, i.e. AFTER it was encrypted, so entropy_delta and
        # avg_size_change_ratio were always 0 and 1.0 for exactly the files
        # that mattered, and slow in-place encryption went undetected.)
        written = {e["src_path"] for e in modified + created}
        deleted_paths = {e["src_path"] for e in deleted}
        entropies, entropy_deltas, size_ratios = [], [], []
        ext_changed = considered = 0

        for change in changes:
            if change.final is None:
                continue
            final = Path(change.final)
            baseline_key = change.original
            if change.kind == "created" and change.original not in cls._file_baseline_ext:
                # Copy-then-delete ransomware writes "a.txt.enc" and deletes
                # "a.txt"; watchdog sees two unrelated events. Pair them so
                # the new file is judged against the original's baseline.
                baseline_key = cls._paired_deleted(final, deleted_paths) or baseline_key

            baseline_ext = cls._file_baseline_ext.get(baseline_key)
            if baseline_ext is not None or change.kind == "moved":
                considered += 1
                reference_ext = baseline_ext if baseline_ext is not None else Path(change.original).suffix
                if reference_ext != final.suffix:
                    ext_changed += 1

            if change.original not in written:
                continue  # pure rename: no new content to read
            entropy, size = _read_entropy_and_size(final)
            if entropy is None:
                continue
            entropies.append(entropy)
            base_entropy = cls._file_baseline_entropy.get(baseline_key)
            if base_entropy is not None:
                entropy_deltas.append(entropy - base_entropy)
            base_size = cls._file_baseline_size.get(baseline_key)
            if base_size and size is not None:
                size_ratios.append(size / base_size)

        entropy_mean = sum(entropies) / len(entropies) if entropies else 0.0
        entropy_delta = sum(entropy_deltas) / len(entropy_deltas) if entropy_deltas else 0.0
        avg_size_change_ratio = sum(size_ratios) / len(size_ratios) if size_ratios else 1.0
        extension_change_ratio = (ext_changed / considered) if considered else 0.0

        # --- process attribution (best-effort; see module docstring) ---
        # Comes from the background sampler (see _sampler_loop), so this
        # window doesn't wait the 1-5 s a full process scan takes on Windows.
        proc_pid, proc_name, cpu_pct, write_mb_s, rw_ratio = cls._latest_sample

        features = FileActivityFeatures(
            file_modification_rate=len(written) / elapsed,
            file_rename_rate=len(moved) / elapsed,
            file_deletion_rate=len(deleted) / elapsed,
            entropy_mean=round(entropy_mean, 4),
            entropy_delta=round(entropy_delta, 4),
            extension_change_ratio=round(extension_change_ratio, 4),
            unique_dirs_touched=len(unique_dirs),
            avg_size_change_ratio=round(avg_size_change_ratio, 4),
            process_cpu_percent=round(cpu_pct, 2),
            io_write_rate_mb_s=round(write_mb_s, 4),
            read_write_ratio=round(rw_ratio, 4),
        )
        cls._update_baselines(changes, written)

        if not events:
            # Nothing happened this window — skip calling the model (an
            # all-zero window is not an interesting event and would just
            # be noise in the log).
            cls._prev_changes = []
            return

        result = DetectionService.analyze(features)

        incident_id = None
        response_ms = None
        if result.prediction == "ransomware_like":
            response_started = time.perf_counter()
            previous = [FileChange(c.original, c.final, c.kind, from_previous_window=True) for c in cls._prev_changes]
            incident_id, touched = RecoveryService.respond_to_detection(
                changes + previous,
                confidence=result.confidence,
                pid=proc_pid,
                process_name=proc_name,
                io_write_rate_mb_s=features.io_write_rate_mb_s,
            )
            response_ms = round((time.perf_counter() - response_started) * 1000, 1)
            # Two windows of grace plus the polling interval.
            expiry = time.monotonic() + 2 * window_seconds + 2
            for p in touched:
                cls._suppressed_paths[p] = expiry
        else:
            # During an open incident, a benign-scored window can still hold
            # the attack's tail (a ransom note, slow in-place encryption).
            touched = RecoveryService.follow_up_incident(changes)
            if touched:
                incident_id = RecoveryService._active_incident_id
                expiry = time.monotonic() + 2 * window_seconds + 2
                for p in touched:
                    cls._suppressed_paths[p] = expiry
            RecoveryService.capture_benign_window([c.final for c in changes if c.final])
        cls._prev_changes = changes

        event = DetectionEvent(
            timestamp=datetime.now(timezone.utc),
            window_seconds=round(elapsed, 2),
            raw_event_count=len(events),
            attributed_process=proc_name,
            attributed_pid=proc_pid,
            features=features,
            result=result,
            recovery_incident_id=incident_id,
            response_ms=response_ms,
        )
        with cls._events_log_lock:
            cls._events_log.append(event)

        if result.prediction == "ransomware_like":
            logger.warning(
                "RANSOMWARE-LIKE ACTIVITY DETECTED: confidence=%.1f%% process=%s | %s",
                result.confidence * 100, proc_name, result.explanation_summary,
            )

    @classmethod
    def _drop_self_inflicted(cls, events: List[dict]) -> List[dict]:
        now = time.monotonic()
        cls._suppressed_paths = {p: exp for p, exp in cls._suppressed_paths.items() if exp > now}
        suppressed = cls._suppressed_paths

        def ours(path: Optional[str]) -> bool:
            return path is not None and (path in suppressed or RESTORE_TMP_MARKER in path)

        return [e for e in events if not (ours(e["src_path"]) or ours(e["dest_path"]))]

    @staticmethod
    def _summarize_changes(modified, created, moved, deleted) -> List[FileChange]:
        """Collapse a window's raw events into one net change per original path."""
        deleted_paths = {e["src_path"] for e in deleted}
        changes: Dict[str, FileChange] = {}
        for kind, group in (("created", created), ("modified", modified), ("moved", moved)):
            for e in group:
                original = e["src_path"]
                if original in changes and changes[original].kind == "created":
                    continue  # "created" is the most informative label; keep it
                changes[original] = FileChange(original, _resolve_final_path(original, moved, deleted_paths), kind)
        for e in deleted:
            changes.setdefault(e["src_path"], FileChange(e["src_path"], None, "deleted"))
        return list(changes.values())

    # --- Internal: per-file baselines -------------------------------------

    @classmethod
    def _seed_baselines(cls, root: Path) -> None:
        cls._file_baseline_entropy.clear()
        cls._file_baseline_size.clear()
        cls._file_baseline_ext.clear()
        limit = settings.RECOVERY_MAX_BASELINE_FILES
        seeded = 0
        for dirpath, _dirs, filenames in os.walk(root):
            for name in filenames:
                path = Path(dirpath) / name
                entropy, size = _read_entropy_and_size(path)
                if entropy is None:
                    continue
                key = str(path)
                cls._file_baseline_entropy[key] = entropy
                cls._file_baseline_size[key] = size
                cls._file_baseline_ext[key] = path.suffix
                seeded += 1
            if seeded >= limit:
                break
        logger.info("Seeded behavioral baselines for %d file(s)", seeded)

    @staticmethod
    def _paired_deleted(created: Path, deleted_paths: set) -> Optional[str]:
        """'a.txt.enc' created + 'a.txt' deleted in the same window -> 'a.txt'."""
        for d in deleted_paths:
            dp = Path(d)
            if dp.parent == created.parent and created.name.startswith(dp.name + "."):
                return d
        return None

    @classmethod
    def _update_baselines(cls, changes: List[FileChange], written: set) -> None:
        for change in changes:
            if change.final is None:
                continue
            original, final = change.original, change.final
            if final != original and original in cls._file_baseline_ext:
                # Carry history across renames, so "a.txt" -> "a.txt.locked"
                # is still compared with a.txt's pre-attack content later.
                cls._file_baseline_entropy[final] = cls._file_baseline_entropy.get(original)
                cls._file_baseline_size[final] = cls._file_baseline_size.get(original)
                cls._file_baseline_ext[final] = cls._file_baseline_ext[original]
            elif final not in cls._file_baseline_ext:
                # A genuinely new file: its first version becomes its baseline.
                entropy, size = _read_entropy_and_size(Path(final))
                if entropy is not None:
                    cls._file_baseline_entropy[final] = entropy
                    cls._file_baseline_size[final] = size
                    cls._file_baseline_ext[final] = Path(final).suffix
            elif original in written:
                # The entropy baseline stays fixed (the pre-attack reference);
                # size tracks the previous version, matching the feature's
                # definition (new_size / old_size).
                try:
                    cls._file_baseline_size[final] = Path(final).stat().st_size
                except OSError:
                    pass

    # --- Internal: psutil process sampling --------------------------------

    _latest_sample: tuple = (None, None, 0.0, 0.0, 1.0)  # pid, name, cpu%, write MB/s, read/write ratio
    _proc_prev: Dict[int, tuple] = {}  # pid -> (cpu_seconds, read_bytes, write_bytes)

    @classmethod
    def _sampler_loop(cls):
        cls._sample_most_active_process(1.0)  # prime the per-process counters
        last = time.monotonic()
        while not cls._stop_flag.wait(timeout=cls._window_seconds):
            now = time.monotonic()
            try:
                cls._latest_sample = cls._sample_most_active_process(now - last)
            except Exception:  # noqa: BLE001
                logger.exception("Process sampling failed")
            last = now

    @classmethod
    def _sample_most_active_process(cls, elapsed: float):
        """
        Best-effort attribution: the process with the highest combined CPU
        and disk-write activity since the previous sample. See the module
        docstring for why this is an approximation, not precise attribution.
        """
        elapsed = max(elapsed, 0.001)
        # psutil per-process CPU is a share of ONE core; the model was
        # trained on share-of-machine (0-100), and the feature schema rejects
        # values above 100, which crashed every window on multi-core Windows
        # hosts until this was normalized.
        cpu_count = psutil.cpu_count() or 1
        current: Dict[int, tuple] = {}
        best, best_score = None, -1.0

        # Fetching all attributes in one process_iter call is ~2-3x faster
        # on Windows than querying each process separately.
        for proc in psutil.process_iter(["pid", "name", "cpu_times", "io_counters"]):
            info = proc.info
            pid = info["pid"]
            # PID 0 is the Windows "System Idle Process" (idle time, not a process).
            if pid == 0 or info["cpu_times"] is None:
                continue
            cpu_s = info["cpu_times"].user + info["cpu_times"].system
            io = info["io_counters"]
            read_b, write_b = (io.read_bytes, io.write_bytes) if io else (0, 0)
            current[pid] = (cpu_s, read_b, write_b)

            prev = cls._proc_prev.get(pid)
            if prev is None:
                continue
            cpu_pct = min(100.0, max(0.0, (cpu_s - prev[0]) / elapsed / cpu_count * 100))
            read_delta, write_delta = max(0, read_b - prev[1]), max(0, write_b - prev[2])
            score = cpu_pct + write_delta / (1024 * 1024)  # weight 1 MB written like 1 CPU-percent point
            if score > best_score:
                best_score = score
                best = (pid, info["name"], cpu_pct, read_delta, write_delta)

        cls._proc_prev = current
        if best is None:
            return None, None, 0.0, 0.0, 1.0
        pid, name, cpu_pct, read_delta, write_delta = best
        write_mb_s = write_delta / (1024 * 1024) / elapsed
        # (An earlier version compared reads against an already-overwritten
        # baseline, so this ratio was always 0 whenever the process wrote.)
        rw_ratio = (read_delta / write_delta) if write_delta > 0 else (1.0 if read_delta == 0 else 5.0)
        return pid, name, cpu_pct, write_mb_s, min(rw_ratio, 50.0)
