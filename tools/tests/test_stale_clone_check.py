"""Drill für tools/hooks/stale_clone_check.sh (KONZ-038 K4/D8, Slug stale-local-clone-as-ground-truth).

Der SessionStart-Hook existierte ohne einen einzigen Test — ein Gate, dessen
Wirksamkeit nie provoziert wurde, gilt nach K4 als nicht gebaut. Diese Tests
SIND der Drill: ein nachweislich staler Klon MUSS gemeldet werden, ein frischer
MUSS still bleiben (ein SessionStart-Hinweis, der immer redet, wird ignoriert
und schützt dann gar nichts — gleiche Logik wie die Redewendungs-Tests des
Evidence-Scanners).

GATE-HEADER (maschinenlesbar, D8):
  slug=stale-local-clone-as-ground-truth mode=advisory owner=achim
  last_drill_pass=2026-08-02 evidence=tools/tests/test_stale_clone_check.py
Residual-Lücke (bewusst, in #1191 dokumentiert): der Hook feuert nur am
Session-START; Mid-Session-Staleness deckt er nicht — dafür greifen
block_stale_branch_commit.sh (Commit-Pfad) und die absence-/universal-Muster
des Evidence-Scanners (Lese-Pfad).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "hooks" / "stale_clone_check.sh"

_GIT_ID = ["-c", "user.email=drill@test", "-c", "user.name=drill"]


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *_GIT_ID, *args], cwd=cwd, check=True, capture_output=True)


def _mk_fixture(tmp_path: Path, behind: int) -> Path:
    """Bare-Origin + Klon; Origin bekommt `behind` Commits, die der Klon nicht hat."""
    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(origin)],
        check=True,
        capture_output=True,
    )
    seed = tmp_path / "seed"
    subprocess.run(
        ["git", "clone", str(origin), str(seed)], check=True, capture_output=True
    )
    (seed / "a.txt").write_text("a\n")
    _git(seed, "add", "a.txt")
    _git(seed, "commit", "-m", "init")
    _git(seed, "push", "-u", "origin", "main")
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", str(origin), str(clone)], check=True, capture_output=True
    )
    for i in range(behind):
        (seed / "a.txt").write_text(f"rev {i}\n")
        _git(seed, "commit", "-am", f"ahead {i}")
    if behind:
        _git(seed, "push", "origin", "main")
    return clone


def _run_hook(clone: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env={"CLAUDE_PROJECT_DIR": str(clone), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_should_stalen_klon_melden(tmp_path: Path) -> None:
    clone = _mk_fixture(tmp_path, behind=2)
    r = _run_hook(clone)
    assert r.returncode == 0, r.stderr  # Vertrag: Hinweis blockiert nie
    assert "STALE KLON" in r.stdout, f"Drill fehlgeschlagen — stdout: {r.stdout!r}"
    assert "2 Commit" in r.stdout


def test_should_frischen_klon_in_ruhe_lassen(tmp_path: Path) -> None:
    clone = _mk_fixture(tmp_path, behind=0)
    r = _run_hook(clone)
    assert r.returncode == 0
    assert r.stdout.strip() == "", f"False Positive auf frischem Klon: {r.stdout!r}"


def test_should_ausserhalb_von_git_still_sein(tmp_path: Path) -> None:
    r = _run_hook(tmp_path / "kein-repo")
    assert r.returncode == 0
    assert r.stdout.strip() == ""
