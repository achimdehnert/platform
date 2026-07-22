"""Tests für tools/repo-session.sh cmd_start/cmd_end Pfad-Kanonisierung (#1360).

Zwei Defekte, end-to-end über subprocess gegen ein lokales Fixture-Repo
(bare "origin" + Arbeitsbaum) belegt, analog test_repo_session_pr_collision.py:

  1. `start <repo> --task <slug>` mit einem nicht-kanonischen Repo-Pfad (".")
     darf keinen "." im Lease-Feld "repo" und kein "/./" im Worktree-Pfad
     hinterlassen (vorher: nur der Fallback-Zweig kanonisierte, der bei
     "-d "$repo/.git"" == wahr nie griff).
  2. `end <worktree>` muss den zugehörigen Lease auch dann schliessen, wenn
     der im Lease gespeicherte Pfad textuell vom übergebenen (kanonischen)
     Pfad abweicht (z.B. "/./" aus einem Alt-Lease) — und MUSS auf stderr
     warnen + exit 0 bleiben, wenn wirklich kein Lease passt (Worktree ist
     zu dem Zeitpunkt bereits entfernt, stilles Scheitern ist der
     schlechteste Zustand).

REPO_SESSION_DIR zeigt auf tmp_path — rührt NICHT an ~/.repo-session.
REPO_SESSION_SKIP_PR_CHECK=1, weil hier nicht der PR-Kollisionscheck
(bereits von test_repo_session_pr_collision.py abgedeckt) im Fokus steht.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

REPO_SESSION_SH = Path(__file__).resolve().parents[2] / "tools" / "repo-session.sh"


def _make_fixture_repo(tmp_path: Path) -> Path:
    """Lokales bare-'origin' + Arbeitsbaum auf main, damit fetch/rev-parse
    offline funktionieren (kein echtes GitHub nötig)."""
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


def _env(tmp_path: Path) -> dict:
    return {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
        "REPO_SESSION_DIR": str(tmp_path / ".repo-session"),
        "REPO_SESSION_SKIP_PR_CHECK": "1",
    }


def _run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    bash_bin = shutil.which("bash")
    return subprocess.run(
        [bash_bin, str(REPO_SESSION_SH), *args],
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_should_canonicalize_repo_path_when_started_with_dot(tmp_path):
    """Defekt 1: 'start .' aus dem Haupt-Tree darf kein 'repo': '.' erzeugen."""
    work = _make_fixture_repo(tmp_path)
    bash_bin = shutil.which("bash")
    res = subprocess.run(
        [bash_bin, str(REPO_SESSION_SH), "start", ".", "--task", "canon"],
        cwd=str(work),
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0, res.stderr
    wt = res.stdout.strip()
    assert wt != "", res.stderr
    assert "/./" not in wt, f"Worktree-Pfad enthaelt nicht-kanonisches '/./': {wt}"

    lease_files = list((tmp_path / ".repo-session" / "leases").glob("*.json"))
    assert len(lease_files) == 1
    lease = json.loads(lease_files[0].read_text())
    assert lease["repo"] == "work", lease["repo"]
    assert "/./" not in lease["worktree"]


def test_should_close_lease_when_stored_path_has_noncanonical_dot_segment(tmp_path):
    """Defekt 2 (Kernfall aus #1360): Lease speichert '/./', end() bekommt den
    kanonischen Pfad (wie git worktree list ihn liefert) -> muss trotzdem matchen."""
    work = _make_fixture_repo(tmp_path)
    res = _run(tmp_path, "start", str(work), "--task", "mismatch")
    assert res.returncode == 0, res.stderr
    wt = res.stdout.strip()

    lease_dir = tmp_path / ".repo-session" / "leases"
    lease_files = list(lease_dir.glob("*.json"))
    assert len(lease_files) == 1
    lease_path = lease_files[0]
    lease = json.loads(lease_path.read_text())
    # Nicht-kanonischen Pfad simulieren, wie ihn ein Vor-Fix-'start .' erzeugt hätte.
    lease["worktree"] = lease["worktree"].replace("/worktrees/", "/worktrees/./")
    lease_path.write_text(json.dumps(lease, indent=2))

    res = _run(tmp_path, "end", wt)
    assert res.returncode == 0, res.stderr
    assert "Lease geschlossen" in res.stdout, res.stdout + res.stderr
    assert not lease_path.exists()
    assert (
        lease_path.with_suffix(".json.closed").exists()
        or (lease_dir / (lease_path.name + ".closed")).exists()
    )


def test_should_warn_on_stderr_when_no_lease_matches_instead_of_failing_silently(
    tmp_path,
):
    """Der eigentliche Fix aus #1360: kein stilles Scheitern. Worktree ohne
    zugehoerigen Lease (z.B. weil der Lease bereits anderweitig verschwunden
    ist) -> end() muss auf stderr warnen, exit 0 bleibt (Worktree ist eh weg)."""
    work = _make_fixture_repo(tmp_path)
    res = _run(tmp_path, "start", str(work), "--task", "orphan")
    assert res.returncode == 0, res.stderr
    wt = res.stdout.strip()

    lease_dir = tmp_path / ".repo-session" / "leases"
    for f in lease_dir.glob("*.json"):
        f.unlink()  # Lease weg, Worktree bleibt -> end() findet keinen Match.

    res = _run(tmp_path, "end", wt)
    assert res.returncode == 0, res.stderr
    assert "Kein Lease geschlossen" in res.stderr
    assert wt in res.stderr
    assert "Worktree entfernt" in res.stdout


def test_should_close_lease_on_exact_canonical_match_no_regression(tmp_path):
    """Regressionscheck: der normale, bereits-kanonische Fall funktioniert weiter."""
    work = _make_fixture_repo(tmp_path)
    res = _run(tmp_path, "start", str(work), "--task", "plain")
    assert res.returncode == 0, res.stderr
    wt = res.stdout.strip()

    res = _run(tmp_path, "end", wt)
    assert res.returncode == 0, res.stderr
    assert "Lease geschlossen" in res.stdout

    lease_dir = tmp_path / ".repo-session" / "leases"
    assert list(lease_dir.glob("*.json.closed"))
    assert not list(lease_dir.glob("*.json"))
