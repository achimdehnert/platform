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
  *"pr view"*comments*)
    # Kommentare am PR — der Freigabe-Check der --admin-Ausweitung 2026-08-31.
    case "${GH_KOMMENTARE:-leer}" in
      mensch)  printf 'achimdehnert\\tFreigabe --admin fuer #51 go\\n' ;;
      botonly) printf 'github-actions[bot]\\tCI gruen, admin bypass ok\\n' ;;
      leer)    ;;
    esac ;;
  *"pr view"*headRefOid*)          echo "abc1234def5678" ;;
  *"api"*check-runs*)
    # Zahl der Check-Runs am Head-SHA des PR — der Fall, den das Gate seit
    # 2026-08-26 zusaetzlich prueft.
    case "${GH_PR_CHECKS:-viele}" in
      null) echo "0" ;;
      *)    echo "7" ;;
    esac ;;
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


def _laeuft(
    kommando: str,
    fall: str,
    gh_attrappe: Path,
    pr_checks: str = "viele",
    kommentare: str = "leer",
) -> bool:
    """True = das Kommando wird geblockt."""
    umgebung = {
        **os.environ,
        "PATH": f"{gh_attrappe}:{os.environ['PATH']}",
        "GH_FALL": fall,
        "GH_PR_CHECKS": pr_checks,
        "GH_KOMMENTARE": kommentare,
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


def test_should_let_the_admin_bypass_pass_with_a_human_approval_comment(gh_attrappe):
    """`--admin` bleibt der Bypass eines Menschen — wenn das Wort DURABEL am PR steht."""
    assert not _laeuft(
        "gh pr merge 51 --repo achimdehnert/probe --admin",
        "leer",
        gh_attrappe,
        kommentare="mensch",
    )


def test_should_block_an_admin_bypass_without_any_approval_comment(gh_attrappe):
    """Der Realfall dev-hub 2026-08-25: 10 --admin-Merges, Freigabe nur im Chat."""
    assert _laeuft(
        "gh pr merge 51 --repo achimdehnert/probe --admin",
        "leer",
        gh_attrappe,
        kommentare="leer",
    )


def test_should_block_an_admin_bypass_when_only_bots_commented(gh_attrappe):
    """Ein Bot-Kommentar mit Freigabe-Woertern ist kein menschliches Wort."""
    assert _laeuft(
        "gh pr merge 51 --repo achimdehnert/probe --admin",
        "leer",
        gh_attrappe,
        kommentare="botonly",
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


# --- Der PR selbst, nicht nur der Default-Branch (Ausweitung 2026-08-26) ----------


def test_should_block_a_merge_when_the_pr_itself_has_no_check_runs(gh_attrappe):
    """Der Realfall vom 2026-08-26: `main` gruen, der PR ohne einen einzigen Lauf.

    Das Gate sah bis dahin ausschliesslich auf den Default-Branch und liess
    diesen Fall glatt durch. `gh pr checks` meldete "no checks reported", das
    wurde als gruen gelesen, und der Merge scheiterte danach mit BLOCKED.
    """
    assert _laeuft(MERGE, "gruen", gh_attrappe, pr_checks="null")


def test_should_let_a_merge_pass_when_the_pr_has_check_runs(gh_attrappe):
    """Positivkontrolle: die neue Pruefung blockt nicht den Normalfall."""
    assert not _laeuft(MERGE, "gruen", gh_attrappe, pr_checks="viele")


def test_should_let_the_admin_bypass_pass_even_without_pr_checks(gh_attrappe):
    """Der benannte, durabel abgelegte Bypass gilt auch bei null Check-Runs."""
    assert not _laeuft(
        "gh pr merge 51 --repo achimdehnert/probe --admin",
        "gruen",
        gh_attrappe,
        pr_checks="null",
        kommentare="mensch",
    )


def test_should_not_check_a_pr_that_is_not_named(gh_attrappe, tmp_path):
    """Ohne PR-Nummer gibt es nichts nachzuschlagen — publish faellt nicht hierunter."""
    ziel = tmp_path / "probe"
    ziel.mkdir()
    assert not _laeuft(
        f"cd {ziel} && bash publish-package.sh {ziel}", "gruen", gh_attrappe, pr_checks="null"
    )
