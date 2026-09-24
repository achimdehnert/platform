"""Tests fuer die Befund-Sperre in tools/repo-session.sh (platform#3495 V1).

Anlass: zwei Sitzungen desselben Owners legten am 2026-09-24 6 s auseinander
dieselben PRs (#3465/#3466) und 17 s auseinander dieselben Issues (#3467/#3468)
an. `start --befund <phase::repo>` belegt den Journal-Schluessel atomar; ein
zweiter `start` auf denselben Schluessel muss mit exit 3 abbrechen, ohne einen
Worktree zu hinterlassen.

End-to-end ueber subprocess gegen ein lokales Fixture-Repo (bare "origin" +
Arbeitsbaum), analog test_repo_session_lease_match.py. REPO_SESSION_DIR und
HOME zeigen auf tmp_path — ~/.repo-session bleibt unberuehrt.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

REPO_SESSION_SH = Path(__file__).resolve().parents[2] / "tools" / "repo-session.sh"
KEY = "0.7 deploy-scan::fixture"
BEFUND_EXIT = 3


def _make_fixture_repo(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    git = shutil.which("git")
    subprocess.run([git, "init", "--bare", "-q", str(origin)], check=True)
    subprocess.run([git, "init", "-q", "-b", "main", str(work)], check=True)
    subprocess.run(
        [git, "-C", str(work), "config", "user.email", "t@example.com"], check=True
    )
    subprocess.run(
        [git, "-C", str(work), "config", "user.name", "Test User"], check=True
    )
    (work / "README.md").write_text("fixture\n")
    subprocess.run([git, "-C", str(work), "add", "."], check=True)
    subprocess.run([git, "-C", str(work), "commit", "-q", "-m", "init"], check=True)
    subprocess.run(
        [git, "-C", str(work), "remote", "add", "origin", str(origin)], check=True
    )
    subprocess.run([git, "-C", str(work), "push", "-q", "origin", "main"], check=True)
    return work


def _run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
        "REPO_SESSION_DIR": str(tmp_path / ".repo-session"),
        "REPO_SESSION_SKIP_PR_CHECK": "1",
    }
    return subprocess.run(
        [shutil.which("bash"), str(REPO_SESSION_SH), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _lock_dir(tmp_path: Path) -> Path:
    return tmp_path / ".repo-session" / "leases" / "befund"


def _locks(tmp_path: Path) -> list[Path]:
    d = _lock_dir(tmp_path)
    return sorted(d.glob("*.lock")) if d.is_dir() else []


def _start(tmp_path: Path, work: Path, task: str, *extra: str):
    return _run(tmp_path, "start", str(work), "--task", task, *extra)


def _worktrees(work: Path) -> int:
    out = subprocess.run(
        ["git", "-C", str(work), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out.count("worktree ")


def test_should_abort_second_start_with_exit_3_when_befund_is_taken(tmp_path):
    """Drill (a): zwei Starts 1 s nacheinander auf denselben Schluessel."""
    work = _make_fixture_repo(tmp_path)
    first = _start(tmp_path, work, "sitzung-a", "--befund", KEY)
    assert first.returncode == 0, first.stderr
    lock = json.loads(_locks(tmp_path)[0].read_text())
    assert lock["key"] == KEY
    assert set(lock) == {"key", "lease_id", "worktree", "created_at", "expires_at"}

    time.sleep(1)
    wt_vorher = _worktrees(work)
    second = _start(tmp_path, work, "sitzung-b", "--befund", KEY)

    assert second.returncode == BEFUND_EXIT, second.stderr
    assert f"Befund {KEY} in Arbeit von {lock['lease_id']}" in second.stderr
    assert lock["created_at"] in second.stderr
    # Abbruch VOR dem Worktree: kein zweiter Tree, Sperre unveraendert.
    assert _worktrees(work) == wt_vorher
    assert json.loads(_locks(tmp_path)[0].read_text()) == lock


def test_should_take_over_lock_when_it_is_expired(tmp_path):
    """(b) Abgelaufene Sperre wird uebernommen, mit Hinweis auf stderr.

    Meist raeumt schon der Auto-Reap des Starts sie ab ("♻ Befund-Sperre
    abgelaufen entfernt"); scheitert der, uebernimmt befund_belegen selbst
    ("↻ ... übernommen — vorige Sperre abgelaufen"). Beide Pfade melden sich."""
    work = _make_fixture_repo(tmp_path)
    d = _lock_dir(tmp_path)
    d.mkdir(parents=True)
    (d / "0.7_deploy-scan__fixture.lock").write_text(
        json.dumps(
            {
                "key": KEY,
                "lease_id": "alt-lease",
                "worktree": "/nirgends",
                "created_at": "2026-01-01T00:00:00Z",
                "expires_at": "2026-01-08T00:00:00Z",
            }
        )
    )

    res = _start(tmp_path, work, "uebernahme", "--befund", KEY)

    assert res.returncode == 0, res.stderr
    assert "Befund-Sperre" in res.stderr and "abgelaufen" in res.stderr
    assert KEY in res.stderr
    locks = _locks(tmp_path)
    assert len(locks) == 1
    assert json.loads(locks[0].read_text())["lease_id"] != "alt-lease"


def test_should_release_lock_on_end_and_allow_new_start(tmp_path):
    """(c) `end` gibt die Sperre frei; danach geht `start --befund` wieder."""
    work = _make_fixture_repo(tmp_path)
    first = _start(tmp_path, work, "sitzung-a", "--befund", KEY)
    assert first.returncode == 0, first.stderr
    wt = first.stdout.strip().splitlines()[-1]

    end = _run(tmp_path, "end", wt)
    assert end.returncode == 0, end.stderr
    assert f"Befund-Sperre freigegeben: {KEY}" in end.stdout
    assert _locks(tmp_path) == []

    again = _start(tmp_path, work, "sitzung-b", "--befund", KEY)
    assert again.returncode == 0, again.stderr


def test_should_treat_lock_as_free_when_its_lease_is_closed(tmp_path):
    """Reaper-Pfad: worktree-reaper.py schliesst Leases per .json.closed,
    kennt die Sperren aber nicht — die Sperre darf dann nicht mehr blockieren,
    und `reap` raeumt die Datei ab."""
    work = _make_fixture_repo(tmp_path)
    first = _start(tmp_path, work, "sitzung-a", "--befund", KEY)
    assert first.returncode == 0, first.stderr
    lid = json.loads(_locks(tmp_path)[0].read_text())["lease_id"]
    lease = tmp_path / ".repo-session" / "leases" / f"{lid}.json"
    lease.rename(lease.with_suffix(".json.closed"))

    listing = _run(tmp_path, "befunde")
    assert "keine aktiven Befund-Sperren." in listing.stdout
    assert "verwaiste" in listing.stdout

    reap = _run(tmp_path, "reap", str(work))
    assert "Befund-Sperre verwaist entfernt" in reap.stderr, reap.stderr
    assert _locks(tmp_path) == []


def test_should_list_active_locks_with_lease_and_age(tmp_path):
    """(d) `befunde` listet key, Lease, Alter im Runner-Format."""
    work = _make_fixture_repo(tmp_path)
    assert "keine aktiven Befund-Sperren." in _run(tmp_path, "befunde").stdout

    res = _start(tmp_path, work, "sitzung-a", "--befund", KEY, "--befund", "0.9 x::y")
    assert res.returncode == 0, res.stderr
    lids = {json.loads(p.read_text())["lease_id"] for p in _locks(tmp_path)}
    assert len(lids) == 1

    out = _run(tmp_path, "befunde").stdout
    zeilen = [z for z in out.splitlines() if z.startswith("⛔ in Arbeit von ")]
    assert len(zeilen) == 2
    lid = next(iter(lids))
    assert all(z.startswith(f"⛔ in Arbeit von {lid} (seit ") for z in zeilen)
    assert any(z.endswith(f": {KEY}") for z in zeilen)
    assert "2 aktive Befund-Sperre(n)." in out


def test_should_release_all_keys_when_one_of_several_is_taken(tmp_path):
    """Alles-oder-nichts: scheitert der zweite Schluessel, bleibt vom ersten
    keine Sperre der abgebrochenen Sitzung zurueck."""
    work = _make_fixture_repo(tmp_path)
    assert _start(tmp_path, work, "sitzung-a", "--befund", KEY).returncode == 0

    res = _start(tmp_path, work, "sitzung-b", "--befund", "0.9 x::y", "--befund", KEY)

    assert res.returncode == BEFUND_EXIT, res.stderr
    assert [json.loads(p.read_text())["key"] for p in _locks(tmp_path)] == [KEY]


def test_should_start_unchanged_when_no_befund_is_given(tmp_path):
    """(e) Ohne --befund: kein Sperr-Verzeichnis, zwei Starts parallel moeglich."""
    work = _make_fixture_repo(tmp_path)
    a = _start(tmp_path, work, "ohne-a")
    b = _start(tmp_path, work, "ohne-b")

    assert a.returncode == 0, a.stderr
    assert b.returncode == 0, b.stderr
    assert "Befund :" not in a.stderr
    assert not _lock_dir(tmp_path).exists()
