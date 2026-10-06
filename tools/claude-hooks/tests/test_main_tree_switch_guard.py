"""Drill für das Gate `main-tree-guard-recurring-incident` (main_tree_switch_guard.py).

Positivkontrolle ist der Vorfall vom 2026-09-21T08:35:36Z (`git switch -c
session/...` im Haupt-Tree von platform, Retro f1d54f §5) — nachgebaut gegen
einen Fake-Haupt-Tree/Fake-Worktree unter `tmp_path`, damit der Drill nie echte
Pfade unter `~/github` oder `~/.repo-session/worktrees` anfasst.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "main_tree_switch_guard.py"

# Wortlaut des Vorfalls 2026-09-21T08:35:36Z (Retro f1d54f §5): `git switch -c`
# direkt im Haupt-Tree statt über `tools/repo-session.sh start`.
POSITIVKONTROLLE = "git switch -c session/2026-09-21/achim-dehnert/retro-f1d54f"


def _fake_haupt_tree(tmp_path: Path) -> Path:
    pfad = tmp_path / "github" / "platform"
    pfad.mkdir(parents=True)
    return pfad


def _fake_worktree(tmp_path: Path) -> Path:
    pfad = tmp_path / "repo-session" / "worktrees" / "platform" / "2026-09-21-sess"
    pfad.mkdir(parents=True)
    return pfad


def _entscheidung(kommando: str, cwd: str, tmp_path: Path) -> tuple[int, str]:
    # Voller os.environ als Basis (nicht nur ein paar Variablen): PYTEST_CURRENT_TEST
    # muss bis zum Hook-Subprozess durchgereicht werden, sonst haelt gate_hits.notiere()
    # den Lauf faelschlich fuer eine echte Sitzung und schreibt ins echte Protokoll.
    # GATE_HITS_DATEI zusaetzlich explizit auf tmp_path umgebogen — zweite Sicherung.
    env = {
        **os.environ,
        "GITHUB_DIR": str(tmp_path / "github"),
        "REPO_SESSION_DIR": str(tmp_path / "repo-session"),
        "GATE_HITS_DATEI": str(tmp_path / "gate-hits.jsonl"),
    }
    fertig = subprocess.run(
        [str(HOOK)],
        input=json.dumps({"tool_input": {"command": kommando}, "cwd": cwd}),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return fertig.returncode, fertig.stderr


def test_should_deny_switch_c_in_main_tree_realfall(tmp_path):
    """Positivkontrolle: der Vorfall 2026-09-21T08:35:36Z wird abgewiesen."""
    haupt = _fake_haupt_tree(tmp_path)
    code, err = _entscheidung(POSITIVKONTROLLE, str(haupt), tmp_path)
    assert code == 2
    assert "repo-session.sh start" in err
    assert "platform" in err


def test_should_allow_same_command_in_worktree(tmp_path):
    wt = _fake_worktree(tmp_path)
    code, err = _entscheidung(POSITIVKONTROLLE, str(wt), tmp_path)
    assert code == 0
    assert err == ""


def test_should_allow_switch_without_create_flag(tmp_path):
    haupt = _fake_haupt_tree(tmp_path)
    code, _ = _entscheidung("git switch main", str(haupt), tmp_path)
    assert code == 0


def test_should_deny_checkout_b_with_explicit_dash_c_path(tmp_path):
    haupt = _fake_haupt_tree(tmp_path)
    kommando = f"git -C {haupt} checkout -b feature/x"
    code, err = _entscheidung(kommando, "/tmp/somewhere-else", tmp_path)
    assert code == 2
    assert "repo-session.sh start" in err


def test_should_allow_on_broken_json_input():
    fertig = subprocess.run(
        [str(HOOK)], input="kein json", capture_output=True, text=True, timeout=30
    )
    assert fertig.returncode == 0
    assert fertig.stdout == ""
    assert fertig.stderr == ""


def test_should_allow_switch_create_outside_github_dir(tmp_path):
    ausserhalb = tmp_path / "elsewhere" / "not-a-repo"
    ausserhalb.mkdir(parents=True)
    code, _ = _entscheidung(POSITIVKONTROLLE, str(ausserhalb), tmp_path)
    assert code == 0


def test_should_deny_checkout_dash_upper_b(tmp_path):
    haupt = _fake_haupt_tree(tmp_path)
    code, err = _entscheidung("git checkout -B session/redo", str(haupt), tmp_path)
    assert code == 2
    assert "repo-session.sh start" in err


def test_should_allow_switch_create_with_unresolvable_variable_path(tmp_path):
    kommando = "git -C $SOME_VAR checkout -b x"
    code, _ = _entscheidung(kommando, "", tmp_path)
    assert code == 0


def test_should_allow_unrelated_git_command_in_main_tree(tmp_path):
    haupt = _fake_haupt_tree(tmp_path)
    code, _ = _entscheidung("git status", str(haupt), tmp_path)
    assert code == 0
