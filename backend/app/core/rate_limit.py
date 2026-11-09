"""
In-memory failed-attempt limiter (used to slow down password guessing).

In-memory is enough here because the backend runs as ONE process (the
file monitor keeps its state in-process; see DEPLOYMENT.md). A multi-process
deployment would move this to a shared store such as Redis.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from app.core.exceptions import AppException


class TooManyAttemptsError(AppException):
    status_code = 429
    error_code = "TOO_MANY_ATTEMPTS"


class FailureLimiter:
    def __init__(self, max_failures: int, window_seconds: float):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> Deque[float]:
        q = self._failures[key]
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        return q

    def check(self, key: str) -> None:
        """Raise if `key` has used up its failures in the current window."""
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, now)
            if len(q) >= self.max_failures:
                retry_after = int(self.window_seconds - (now - q[0])) + 1
                raise TooManyAttemptsError(
                    f"Too many failed attempts. Try again in {retry_after // 60 + 1} minute(s).",
                    {"retry_after_seconds": retry_after},
                )

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._failures[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
