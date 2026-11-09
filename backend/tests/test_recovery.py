"""
Module 5 recovery tests.

The end-to-end test runs the REAL monitor, model and recovery engine
against a temp folder and simulates the encrypt-then-rename ransomware
pattern. Process suspension is stubbed in that test only, because the
"most active process" on a developer machine could be anything (a browser,
the IDE) and a test must never freeze it. Real suspend/resume is tested
separately against a throwaway child process.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import psutil
import pytest

from app.domains.monitoring.service import FileSystemMonitorService
from app.domains.recovery import process_control
from app.domains.recovery.models import RecoveryAction
from app.domains.recovery.service import FileChange, RecoveryService
from app.domains.recovery.vault import ShadowVault, VaultIntegrityError

API = "/api/v1"
TEXT = "Quarterly report draft. Revenue grew in the southern region.\n" * 40


# --- vault ---------------------------------------------------------------

def make_vault(tmp_path, max_versions=5):
    return ShadowVault(tmp_path / "vault", max_file_bytes=10_000_000, max_versions=max_versions)


def test_vault_capture_and_restore_roundtrip(tmp_path):
    vault = make_vault(tmp_path)
    f = tmp_path / "doc.txt"
    f.write_text(TEXT)
    assert vault.capture([f]) == 1
    assert vault.capture([f]) == 0  # unchanged content isn't stored twice

    f.write_bytes(os.urandom(4000))  # "encrypted"
    version = vault.pick_clean_version(f)
    vault.restore(f, version)
    assert f.read_text() == TEXT


def test_vault_skips_versions_that_look_encrypted(tmp_path):
    vault = make_vault(tmp_path)
    f = tmp_path / "doc.txt"
    f.write_text(TEXT)
    vault.capture([f])
    # Slow/stealthy ransomware: the encrypted content gets snapshotted in a
    # window the model scored as benign. The restore must still skip it.
    f.write_bytes(os.urandom(4000))
    vault.capture([f])
    assert vault.pick_clean_version(f).sha256 != vault._manifest[str(f.resolve())]["versions"][-1]["sha256"]
    vault.restore(f, vault.pick_clean_version(f))
    assert f.read_text() == TEXT


def test_vault_refuses_tampered_backup(tmp_path):
    vault = make_vault(tmp_path)
    f = tmp_path / "doc.txt"
    f.write_text(TEXT)
    vault.capture([f])
    version = vault.pick_clean_version(f)
    blob = vault._blobs / version.sha256
    os.chmod(blob, 0o666)
    blob.write_bytes(b"tampered")
    with pytest.raises(VaultIntegrityError):
        vault.restore(f, version)


def test_vault_prunes_old_versions(tmp_path):
    vault = make_vault(tmp_path, max_versions=2)
    f = tmp_path / "doc.txt"
    for i in range(4):
        f.write_text(TEXT + str(i))
        vault.capture([f])
    assert len(vault._manifest[str(f.resolve())]["versions"]) == 2
    assert len(list(vault._blobs.iterdir())) == 2


def test_quarantine_moves_instead_of_deleting(tmp_path):
    vault = make_vault(tmp_path)
    root = tmp_path / "watched"
    root.mkdir()
    f = root / "a.txt.locked"
    f.write_bytes(b"x")
    dest = vault.quarantine(f, "incident-1", root)
    assert not f.exists() and dest.read_bytes() == b"x"


# --- process control -----------------------------------------------------

def test_refuses_to_suspend_itself():
    with pytest.raises(process_control.ProcessControlError):
        process_control.suspend(os.getpid())


def test_refuses_on_pid_reuse_mismatch():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        with pytest.raises(process_control.ProcessControlError, match="refusing"):
            process_control.suspend(child.pid, expected_name="definitely-not-this.exe")
    finally:
        child.kill()


def test_suspend_and_resume_real_child_process():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        process_control.suspend(child.pid)
        assert psutil.Process(child.pid).status() == psutil.STATUS_STOPPED or sys.platform == "win32"
        process_control.resume(child.pid)
        assert psutil.Process(child.pid).status() != psutil.STATUS_STOPPED
    finally:
        child.kill()


# --- automated response (unit level, no monitor) ---------------------------

def test_response_restores_renamed_and_quarantines_new_files(session_factory, tmp_path):
    root = tmp_path / "watched"
    root.mkdir()
    files = [root / f"f{i}.txt" for i in range(5)]
    for f in files:
        f.write_text(TEXT)
    RecoveryService.auto_suspend = False
    RecoveryService.on_monitor_start(root, window_seconds=2)
    time.sleep(1.1)  # versions must predate the incident cutoff

    changes = []
    for f in files:
        locked = f.with_name(f.name + ".locked")
        f.write_bytes(os.urandom(3000))
        f.rename(locked)
        changes.append(FileChange(str(f), str(locked), "moved"))
    note = root / "HOW_TO_DECRYPT.txt"
    note.write_text("pay up")
    changes.append(FileChange(str(note), str(note), "created"))

    incident_id, touched = RecoveryService.respond_to_detection(
        changes, confidence=0.99, pid=None, process_name=None, io_write_rate_mb_s=0
    )
    assert incident_id is not None
    assert all(f.read_text() == TEXT for f in files)
    assert not list(root.glob("*.locked")) and not note.exists()
    assert str(files[0]) in touched

    db = session_factory()
    summary = db.query(RecoveryAction).filter_by(action_type="incident_summary").one()
    assert summary.extra["restored"] == 5 and summary.extra["quarantined"] == 6
    RecoveryService.auto_suspend = True


def test_vault_inside_watched_folder_is_refused(session_factory, tmp_path):
    RecoveryService.reset_vault(tmp_path / "watched" / ".vault")
    from app.core.exceptions import AppException
    with pytest.raises(AppException, match="inside the watched folder"):
        RecoveryService.on_monitor_start(tmp_path / "watched", window_seconds=2)


# --- API -------------------------------------------------------------------

def _login(client, email):
    client.post(f"{API}/auth/register", json={"email": email, "password": "password123", "full_name": "T"})
    tokens = client.post(f"{API}/auth/login", json={"email": email, "password": "password123"}).json()["data"]
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_recovery_api_permissions(client):
    assert client.get(f"{API}/recovery/status").status_code == 401
    admin = _login(client, "admin@x.com")
    analyst = _login(client, "analyst@x.com")

    assert client.get(f"{API}/recovery/status", headers=analyst).status_code == 200
    assert client.get(f"{API}/recovery/actions", headers=analyst).status_code == 200
    assert client.patch(f"{API}/recovery/settings", headers=analyst, json={"auto_response": False}).status_code == 403

    res = client.patch(f"{API}/recovery/settings", headers=admin, json={"auto_suspend": False})
    assert res.status_code == 200 and res.json()["data"]["auto_suspend"] is False
    RecoveryService.auto_suspend = True

    # Restore only ever writes to paths the vault backed up itself.
    res = client.post(f"{API}/recovery/restore", headers=analyst, json={"paths": ["C:/Windows/win.ini"]})
    assert res.status_code == 422
    assert client.post(f"{API}/recovery/processes/999999/resume", headers=analyst).status_code == 404


# --- end to end ----------------------------------------------------------------

def test_end_to_end_attack_is_detected_and_reverted(session_factory, tmp_path, monkeypatch):
    suspended = []
    monkeypatch.setattr(process_control, "suspend", lambda pid, expected_name=None: suspended.append(pid) or "stub")
    monkeypatch.setattr(RecoveryService, "auto_suspend", True)  # exercised, but stubbed above

    root = tmp_path / "watched"
    (root / "docs").mkdir(parents=True)
    (root / "photos").mkdir()
    originals = {}
    for i in range(40):
        f = root / ("docs" if i % 2 else "photos") / f"file_{i}.txt"
        content = f"Document {i}. " + TEXT
        f.write_text(content)
        originals[f] = content

    FileSystemMonitorService.start(str(root), window_seconds=3)
    try:
        time.sleep(3.5)
        # Ransomware pattern: overwrite with random bytes, then rename.
        for f in originals:
            f.write_bytes(os.urandom(len(originals[f]) + 16))
            f.rename(f.with_name(f.name + ".locked"))
        (root / "README_DECRYPT.txt").write_text("Your files are encrypted. Send 1 BTC.")

        deadline = time.time() + 20
        while time.time() < deadline and any(not f.exists() for f in originals):
            time.sleep(0.5)
    finally:
        FileSystemMonitorService.stop()

    events = FileSystemMonitorService.get_recent_events(50)
    flagged = [e for e in events if e.result.prediction == "ransomware_like"]
    assert flagged, f"attack not detected: {[e.result.prediction for e in events]}"
    assert any(e.recovery_incident_id for e in flagged), (
        f"no response at threshold {RecoveryService.confidence_threshold}: "
        f"{[round(e.result.confidence, 3) for e in flagged]}"
    )

    restored = sum(1 for f, c in originals.items() if f.exists() and f.read_text() == c)
    assert restored == len(originals), f"only {restored}/{len(originals)} restored"
    assert not list(root.rglob("*.locked"))
    assert not (root / "README_DECRYPT.txt").exists()

    db = session_factory()
    types = {a.action_type for a in db.query(RecoveryAction).all()}
    assert {"baseline_snapshot", "restore_file", "quarantine_file", "incident_summary", "suspend_process"} <= types


def test_follow_up_catches_attack_tail_only_during_incident(session_factory, tmp_path):
    root = tmp_path / "watched"
    root.mkdir()
    files = [root / f"f{i}.txt" for i in range(4)]
    for f in files:
        f.write_text(TEXT)
    RecoveryService.auto_suspend = False
    RecoveryService.on_monitor_start(root, window_seconds=2)
    time.sleep(1.1)

    # Outside an incident, a benign window's new or changed files are left alone.
    note = root / "notes.txt"
    note.write_text("an ordinary new file")
    assert RecoveryService.follow_up_incident([FileChange(str(note), str(note), "created")]) == set()
    assert note.exists()

    # Open an incident with one flagged window...
    files[0].write_bytes(os.urandom(3000))
    RecoveryService.respond_to_detection(
        [FileChange(str(files[0]), str(files[0]), "modified")], confidence=0.9, pid=None, process_name=None,
        io_write_rate_mb_s=0,
    )
    # ...then the attack's tail arrives in a window the model scores benign:
    # one more file encrypted in place, and the ransom note.
    files[1].write_bytes(os.urandom(3000))
    ransom = root / "README_RESTORE_FILES.txt"
    ransom.write_text("Your files have been encrypted.")
    touched = RecoveryService.follow_up_incident([
        FileChange(str(files[1]), str(files[1]), "modified"),
        FileChange(str(ransom), str(ransom), "created"),
        FileChange(str(files[2]), str(files[2]), "modified"),  # touched but still clean: left alone
    ])
    assert files[1].read_text() == TEXT
    assert not ransom.exists()
    assert files[2].read_text() == TEXT
    assert str(files[1]) in touched and str(ransom) in touched
    RecoveryService.auto_suspend = True
