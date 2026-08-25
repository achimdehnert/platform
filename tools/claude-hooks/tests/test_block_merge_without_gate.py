"""Drill für das Gate `no-checks-reported-read-as-green`.

Ein Gate, das nicht scheitern kann, ist keins — deshalb sind vier der sieben
Fälle Block-Erwartungen. Jeder Fall ist der reale aus Retro 3106ae Befund #1
oder seine Abgrenzung.

Der Hook fragt `gh`; hier steht eine Attrappe auf dem PATH, deren Verhalten
über `GH_FALL` gesteuert wird. So läuft der Drill ohne Netz und ohne echtes
Repo — und prüft trotzdem genau die Verzweigung, um die es geht.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "block_merge_without_gate.sh"

GH_ATTRAPPE = """#!/usr/bin/env bash
args="$*"
case "$args" in
  *"repo view"*defaultBranchRef*) echo "main" ;;
  *"repo view"*nameWithOwner*)    echo "achimdehnert/probe" ;;
  *"run list"*)
    case "${GH_FALL:-}" in
      leer)  echo "" ;;
      rot)   echo "failure,success" ;;
      gruen) echo "success,success" ;;
      *)     echo "success" ;;
    esac ;;
esac
"""


@pytest.fixture
def gh_attrappe(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(GH_ATTRAPPE, encoding="utf-8")
    gh.chmod(0o755)
    return bin_dir


def _laeuft(kommando: str, fall: str, gh_attrappe: Path) -> bool:
    """True = das Kommando wird geblockt."""
    umgebung = {
        **os.environ,
        "PATH": f"{gh_attrappe}:{os.environ['PATH']}",
        "GH_FALL": fall,
    }
    fertig = subprocess.run(
        ["bash", str(HOOK)],
        input=kommando,
        capture_output=True,
        text=True,
        env=umgebung,
        timeout=30,
    )
    if not fertig.stdout.strip():
        return False
    antwort = json.loads(fertig.stdout)
    return antwort["hookSpecificOutput"]["permissionDecision"] == "deny"


MERGE = "gh pr merge 51 --repo achimdehnert/probe --squash"


def test_should_block_a_merge_when_no_run_ever_completed(gh_attrappe):
    """Der Realfall: leere Prüfliste heisst 'hier prueft nichts'."""
    assert _laeuft(MERGE, "leer", gh_attrappe)


def test_should_block_a_merge_when_the_last_run_failed(gh_attrappe):
    assert _laeuft(MERGE, "rot", gh_attrappe)


def test_should_let_a_merge_pass_when_the_last_run_was_green(gh_attrappe):
    assert not _laeuft(MERGE, "gruen", gh_attrappe)


def test_should_let_the_named_admin_bypass_pass(gh_attrappe):
    """`--admin` ist der ausgesprochene Bypass eines Menschen, nicht der stille Fall."""
    assert not _laeuft(
        "gh pr merge 51 --repo achimdehnert/probe --admin", "leer", gh_attrappe
    )


def test_should_block_a_publish_when_no_run_ever_completed(gh_attrappe, tmp_path):
    ziel = tmp_path / "probe"
    ziel.mkdir()
    assert _laeuft(f"cd {ziel} && bash publish-package.sh {ziel}", "leer", gh_attrappe)


def test_should_let_a_publish_pass_when_the_last_run_was_green(gh_attrappe, tmp_path):
    ziel = tmp_path / "probe"
    ziel.mkdir()
    assert not _laeuft(
        f"cd {ziel} && bash publish-package.sh {ziel}", "gruen", gh_attrappe
    )


def test_should_not_fire_on_an_unrelated_command(gh_attrappe):
    assert not _laeuft("git status", "leer", gh_attrappe)
