"""Drill fuer das Gate fremde-worktrees-beendet (platform#3859 M1).

Realfall 2026-10-08: Eine Aufraeum-Schleife ueber das Pfadmuster
`<datum>-<owner>-*` rief `repo-session.sh end` auf Worktrees fuenf fremder
Sitzungen desselben Kontos auf, eine davon aktiv. Der Pfad traegt Datum und
Konto, nicht die Sitzung. Seitdem prueft `end` in einer Claude-Sitzung, dass die
Lease des Worktrees dieser Sitzung gehoert (Feld `claude_session`).

End-to-end ueber subprocess gegen ein lokales Fixture-Repo, analog
test_repo_session_lease_match.py. REPO_SESSION_DIR zeigt auf tmp_path.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

REPO_SESSION_SH = Path(__file__).resolve().parents[2] / "tools" / "repo-session.sh"

EIGENE = "aaaaaaaa-1111-4111-8111-000000000001"
FREMDE = "bbbbbbbb-2222-4222-8222-000000000002"


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


def _run(tmp_path: Path, *args: str, sitzung: str | None) -> subprocess.CompletedProcess:
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
        "REPO_SESSION_DIR": str(tmp_path / ".repo-session"),
        "REPO_SESSION_SKIP_PR_CHECK": "1",
    }
    if sitzung is not None:
        env["CLAUDE_CODE_SESSION_ID"] = sitzung
    return subprocess.run(
        [shutil.which("bash"), str(REPO_SESSION_SH), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _start(tmp_path: Path, work: Path, task: str, sitzung: str | None) -> Path:
    res = _run(tmp_path, "start", str(work), "--task", task, sitzung=sitzung)
    assert res.returncode == 0, res.stderr
    return Path(res.stdout.strip().splitlines()[-1])


def _leases(tmp_path: Path) -> list[Path]:
    return list((tmp_path / ".repo-session" / "leases").glob("*.json"))


def test_should_block_end_on_worktree_of_other_session(tmp_path):
    """Realfall: fremde Sitzung beendet einen Worktree -> exit 4, nichts entfernt."""
    work = _make_fixture_repo(tmp_path)
    wt = _start(tmp_path, work, "fremd", sitzung=FREMDE)

    res = _run(tmp_path, "end", str(wt), sitzung=EIGENE)

    assert res.returncode == 4, res.stdout + res.stderr
    assert "gehoert nicht dieser Sitzung" in res.stderr
    assert wt.is_dir(), "Worktree der fremden Sitzung wurde entfernt"
    assert len(_leases(tmp_path)) == 1, "Lease der fremden Sitzung wurde geschlossen"


def test_should_end_own_worktree(tmp_path):
    """Negativprobe: eigene Lease -> end laeuft wie bisher durch."""
    work = _make_fixture_repo(tmp_path)
    wt = _start(tmp_path, work, "eigen", sitzung=EIGENE)

    res = _run(tmp_path, "end", str(wt), sitzung=EIGENE)

    assert res.returncode == 0, res.stderr
    assert "Lease geschlossen" in res.stdout, res.stdout + res.stderr
    assert not wt.exists()
    assert _leases(tmp_path) == []


def test_should_block_end_on_lease_without_session_field(tmp_path):
    """Alt-Lease ohne claude_session gehoert niemandem nachweislich -> exit 4."""
    work = _make_fixture_repo(tmp_path)
    wt = _start(tmp_path, work, "alt", sitzung=None)

    res = _run(tmp_path, "end", str(wt), sitzung=EIGENE)

    assert res.returncode == 4, res.stdout + res.stderr
    assert "<ohne-sitzung>" in res.stderr
    assert wt.is_dir()


def test_should_block_end_on_worktree_without_lease(tmp_path):
    """Worktree ohne Lease -> exit 4 statt still entfernen."""
    work = _make_fixture_repo(tmp_path)
    wt = _start(tmp_path, work, "ohne", sitzung=EIGENE)
    for lease in _leases(tmp_path):
        lease.unlink()

    res = _run(tmp_path, "end", str(wt), sitzung=EIGENE)

    assert res.returncode == 4, res.stdout + res.stderr
    assert "<kein-lease>" in res.stderr
    assert wt.is_dir()


def test_should_end_foreign_worktree_with_fremd_flag(tmp_path):
    """Negativprobe: Owner-Wort --fremd hebt den Guard auf."""
    work = _make_fixture_repo(tmp_path)
    wt = _start(tmp_path, work, "freigabe", sitzung=FREMDE)

    res = _run(tmp_path, "end", str(wt), "--fremd", sitzung=EIGENE)

    assert res.returncode == 0, res.stderr
    assert not wt.exists()


def test_should_not_check_without_claude_session(tmp_path):
    """Negativprobe: Mensch am Terminal (keine CLAUDE_CODE_SESSION_ID) -> kein Guard."""
    work = _make_fixture_repo(tmp_path)
    wt = _start(tmp_path, work, "terminal", sitzung=FREMDE)

    res = _run(tmp_path, "end", str(wt), sitzung=None)

    assert res.returncode == 0, res.stderr
    assert not wt.exists()


def test_should_record_claude_session_in_lease(tmp_path):
    """Voraussetzung des Guards: start schreibt die Sitzung in die Lease."""
    work = _make_fixture_repo(tmp_path)
    _start(tmp_path, work, "feld", sitzung=EIGENE)

    (lease,) = _leases(tmp_path)
    assert json.loads(lease.read_text())["claude_session"] == EIGENE
