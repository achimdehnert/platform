"""Drill fuer das Gate edit-in-worktree-without-read (platform#3906).

Anlass: Retro 2026-10-13 robo-lab 4ce56a, Befund 1 — 18 von 31 Fehlerlaeufen
waren Edit-Salven auf Dateien, die der Harness als ungelesen fuehrte. Zwei
Ausloeser, zwei Erzwingungspunkte:

- `repo-session.sh start` legt einen neuen Pfad an; Gelesenes im Haupt-Tree
  zaehlt dort nicht. Der Start-Block nennt das jetzt.
- Nach der Kontextverdichtung ist der Read-Zustand leer.
  `tools/hooks/compact_read_reset_hint.sh` sagt das an, aber nur dann: ein
  Hinweis, der bei jedem Start redet, wird ueberlesen.

End-to-end ueber subprocess; REPO_SESSION_DIR und HOME zeigen auf tmp_path.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
REPO_SESSION_SH = TOOLS / "repo-session.sh"
HOOK = TOOLS / "hooks" / "compact_read_reset_hint.sh"
SLUG = "edit-in-worktree-without-read"


def _fixture_repo(tmp_path: Path) -> Path:
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


def _hook(stdin: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [shutil.which("bash"), str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_should_name_read_batch_and_worktree_path_when_session_starts(tmp_path):
    work = _fixture_repo(tmp_path)
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
        "REPO_SESSION_DIR": str(tmp_path / ".repo-session"),
        "REPO_SESSION_SKIP_PR_CHECK": "1",
    }
    res = subprocess.run(
        [shutil.which("bash"), str(REPO_SESSION_SH), "start", str(work), "--task", "t"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, res.stderr
    wt = res.stdout.strip().splitlines()[-1]
    assert SLUG in res.stderr
    assert "Read-Batch" in res.stderr
    assert f'unter "{wt}"' in res.stderr
    # stdout bleibt der nackte Pfad — `wt=$(… start …)` darf nicht brechen.
    assert res.stdout.strip() == wt


def test_should_announce_read_reset_after_compaction():
    res = _hook(json.dumps({"hook_event_name": "SessionStart", "source": "compact"}))
    assert res.returncode == 0
    assert SLUG in res.stdout
    assert "Read-Batch" in res.stdout


@pytest.mark.parametrize("quelle", ["startup", "resume", "clear"])
def test_should_stay_silent_on_other_session_starts(quelle):
    res = _hook(json.dumps({"hook_event_name": "SessionStart", "source": quelle}))
    assert res.returncode == 0
    assert res.stdout == ""


@pytest.mark.parametrize("stdin", ["", "kein json", "[]"])
def test_should_exit_zero_and_stay_silent_on_unreadable_input(stdin):
    res = _hook(stdin)
    assert res.returncode == 0
    assert res.stdout == ""
