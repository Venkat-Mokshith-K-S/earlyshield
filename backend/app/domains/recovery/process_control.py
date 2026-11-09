"""
Suspend / resume the process blamed for ransomware-like activity.

Suspend, never kill: process attribution in Module 3 is a best-effort
heuristic (busiest process in the window), so the response has to be
reversible. A suspended process keeps its memory and handles and continues
exactly where it left off on resume, which matters both for a wrongly
blamed process and for forensic analysis of a correctly blamed one.
"""

import os
from typing import Optional

import psutil

from app.core.config import settings


class ProcessControlError(Exception):
    pass


def _protected_pids() -> set[int]:
    """EarlyShield itself and every ancestor (uvicorn reloader, shell, container init)."""
    pids = {0, 1, 4, os.getpid()}  # 4 = Windows "System"
    try:
        for parent in psutil.Process(os.getpid()).parents():
            pids.add(parent.pid)
    except psutil.Error:
        pass
    return pids


def check_suspendable(pid: int, expected_name: Optional[str] = None) -> psutil.Process:
    if pid in _protected_pids():
        raise ProcessControlError(f"PID {pid} is EarlyShield itself or a system process; refusing to suspend it")
    try:
        proc = psutil.Process(pid)
        name = proc.name()
    except psutil.NoSuchProcess:
        raise ProcessControlError(f"PID {pid} no longer exists")
    except psutil.AccessDenied:
        raise ProcessControlError(f"Access denied to PID {pid}")

    # Guards against PID reuse: the PID we sampled may have exited and been
    # handed to an unrelated process in the meantime.
    if expected_name is not None and name != expected_name:
        raise ProcessControlError(f"PID {pid} is now '{name}', not '{expected_name}'; refusing to act on it")

    protected = {n.lower() for n in settings.RECOVERY_PROTECTED_PROCESSES}
    if name.lower() in protected:
        raise ProcessControlError(f"'{name}' is on the protected-process list; refusing to suspend it")
    return proc


def suspend(pid: int, expected_name: Optional[str] = None) -> str:
    proc = check_suspendable(pid, expected_name)
    try:
        proc.suspend()
    except psutil.Error as exc:
        raise ProcessControlError(f"Could not suspend PID {pid}: {exc}")
    return proc.name()


def resume(pid: int) -> str:
    try:
        proc = psutil.Process(pid)
        proc.resume()
        return proc.name()
    except psutil.NoSuchProcess:
        raise ProcessControlError(f"PID {pid} no longer exists")
    except psutil.Error as exc:
        raise ProcessControlError(f"Could not resume PID {pid}: {exc}")
