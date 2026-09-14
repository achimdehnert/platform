"""Drill fuer cd_fehlschlag_ketten_scanner.py (Slug cd-fehlschlag-kette-laeuft-weiter).

Realfall (Retro b7822e B12): ein Worktree war nach dem Merge geraeumt; die
naechste Bash-Kette begann trotzdem mit `cd $W; git switch -c …` — `cd`
scheiterte lautlos, die Folgebefehle liefen im platform-Haupt-Tree weiter.
Drei Memory-Vorkommen (2026-09-04 ×2, 2026-09-14), bisher KEIN Gate.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location(
    "cd_fehlschlag_ketten_scanner", _DIR / "cd_fehlschlag_ketten_scanner.py"
)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

MODUL = _DIR / "cd_fehlschlag_ketten_scanner.py"


# --- Positive Faelle: cd in einen Worktree-/Variablen-Pfad ohne Abbruch ----


@pytest.mark.parametrize(
    "cmd",
    [
        # Der Realfall, woertlich.
        "cd $W; git switch -c x",
        'cd "$W"\ngit commit -m "x"',
        # Woertlicher Worktree-Pfad statt Variable.
        "cd ~/.repo-session/worktrees/platform/foo\ngit status",
        "cd /home/devuser/.repo-session/worktrees/platform/foo; ls",
    ],
)
def test_should_flag_cd_without_abort_guard_into_worktree_target(cmd: str) -> None:
    treffer = scanner.finde_unsichere_cd_ketten(cmd)
    assert treffer, f"{cmd!r} haette gemeldet werden muessen"


# --- Negative Faelle -------------------------------------------------------


def test_should_not_flag_cd_with_exit_guard() -> None:
    """Die sichere Form aus der Meldung selbst: `|| exit 1`."""
    cmd = 'cd "$W" || exit 1; git switch -c x'
    assert scanner.finde_unsichere_cd_ketten(cmd) == []


def test_should_not_flag_cd_with_return_guard() -> None:
    cmd = "cd $W || return 1; git switch -c x"
    assert scanner.finde_unsichere_cd_ketten(cmd) == []


def test_should_not_flag_literal_repo_path_target() -> None:
    """`~/github/platform` ist der stabile Haupt-Tree, kein raeumbares Ziel."""
    cmd = "cd ~/github/platform && git status"
    assert scanner.finde_unsichere_cd_ketten(cmd) == []


def test_should_not_flag_plain_word_target_with_and_chain() -> None:
    cmd = "cd x && y"
    assert scanner.finde_unsichere_cd_ketten(cmd) == []


def test_should_not_flag_and_chained_worktree_cd() -> None:
    """`&&`-Verkettung ist ein zulaessiger Abbruch-Mechanismus."""
    cmd = "cd $W && git switch -c x"
    assert scanner.finde_unsichere_cd_ketten(cmd) == []


def test_should_not_flag_when_set_dash_e_precedes() -> None:
    cmd = "set -e\ncd $W\ngit commit -m x"
    assert scanner.finde_unsichere_cd_ketten(cmd) == []


def test_should_not_flag_set_dash_euo_pipefail_variant() -> None:
    cmd = "set -euo pipefail\ncd $W\ngit commit -m x"
    assert scanner.finde_unsichere_cd_ketten(cmd) == []


def test_should_not_flag_bare_cd_without_any_following_command() -> None:
    """cd am Ende der Kette kann nichts 'weiterlaufen lassen'."""
    assert scanner.finde_unsichere_cd_ketten("cd $W") == []
    assert scanner.finde_unsichere_cd_ketten('cd "$W"\n') == []


def test_should_not_flag_empty_or_missing_command() -> None:
    assert scanner.finde_unsichere_cd_ketten("") == []


# --- Hook-Vertrag: Eingabe/Ausgabe/Exit-Code -------------------------------


def _lauf(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(MODUL)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_should_exit_zero_and_print_hint_for_unsafe_chain() -> None:
    res = _lauf(
        {"tool_name": "Bash", "tool_input": {"command": "cd $W; git switch -c x"}}
    )
    assert res.returncode == 0
    assert "cd-fehlschlag-kette-laeuft-weiter" in res.stdout


def test_should_exit_zero_and_print_nothing_for_safe_chain() -> None:
    res = _lauf(
        {
            "tool_name": "Bash",
            "tool_input": {"command": 'cd "$W" || exit 1; git switch -c x'},
        }
    )
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_should_exit_zero_on_empty_stdin() -> None:
    """Direktaufruf-Vertrag (test_hook_invocation_contract.py): leeres Event."""
    res = subprocess.run(
        [str(MODUL)], input="{}", capture_output=True, text=True, timeout=30
    )
    assert res.returncode == 0


def test_should_ignore_non_bash_tool_calls() -> None:
    res = _lauf({"tool_name": "Read", "tool_input": {"file_path": "/etc/hostname"}})
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_should_never_use_hookspecificoutput_json_pretooluse_has_no_additionalcontext() -> (
    None
):
    """PreToolUse kennt additionalContext nicht — Klartext ist der belegte Weg
    (wie tools/hooks/foreign_clone_check.sh). Ein Rueckfall in JSON wuerde
    stumm bleiben oder den Turn anhalten/blocken. Geprueft per AST (nicht per
    Textsuche), damit die Erklaerung im Docstring hierueber nicht selbst
    durchfaellt."""
    import ast

    baum = ast.parse(MODUL.read_text(encoding="utf-8"), filename=str(MODUL))
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Dict):
            continue
        for schluessel in knoten.keys:
            assert not (
                isinstance(schluessel, ast.Constant)
                and schluessel.value == "hookSpecificOutput"
            ), "cd_fehlschlag_ketten_scanner.py darf kein hookSpecificOutput senden"
