"""Drill für das Gate `parallel-subagents-shared-scratch-state`.

Realfall: Retro 2026-09-14 apo-hub (40c069) Befund #4 — ein von acht parallelen
Fix-Subagenten führte beim Rot/Grün-Messen ein blankes `git stash pop` aus und
holte den Stash einer fremden Sitzung zurück. `refs/stash` liegt in `.git` und
ist über alle Worktrees desselben Repos geteilt.

Positivkontrolle ist Teil des Drills: die Befehle, die der Hook NICHT blocken
darf, stehen unten mit eigener Begründung. Ein Gate, das nur seine Treffer
zeigt, belegt nicht, dass es zielt.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from block_bare_stash_pop import SLUG, entscheide  # noqa: E402


def test_should_have_the_registered_slug():
    assert SLUG == "parallel-subagents-shared-scratch-state"


# ── Realfall + Familie: blanker Griff in geteilten Zustand ───────────────────


def test_should_deny_realfall_bare_stash_pop():
    grund = entscheide("git stash pop")
    assert grund is not None
    assert "geteilt" in grund


def test_should_deny_bare_stash_apply():
    assert entscheide("git stash apply") is not None


def test_should_deny_bare_stash_drop():
    assert entscheide("git stash drop") is not None


def test_should_deny_when_hidden_in_a_chain():
    assert entscheide("cd /repo && make test; git stash pop") is not None


def test_should_deny_with_global_git_options_before_stash():
    assert entscheide("git -C /repo stash pop") is not None


# ── Positivkontrolle: was durchlaufen MUSS ───────────────────────────────────


def test_should_allow_pop_with_explicit_entry():
    """Der gelesene Eintrag ist genau das, was der Hook erreichen will."""
    assert entscheide("git stash list && git stash pop stash@{2}") is None


def test_should_allow_stash_push():
    """Stashen selbst ist harmlos — es nimmt niemandem etwas weg."""
    assert entscheide("git stash push -m 'wip'") is None


def test_should_allow_read_only_subcommands():
    assert entscheide("git stash list") is None
    assert entscheide("git stash show -p") is None


def test_should_fail_open_on_variable_reference():
    """Pfad/Ref aus einer Variablen ist nicht lesbar — nicht raten, durchlassen."""
    assert entscheide("git stash pop $REF") is None


def test_should_not_trigger_on_unrelated_commands():
    assert entscheide("git status") is None
    assert entscheide("git pull --rebase") is None


def test_documents_the_known_over_block():
    """Bekannte Fehlalarm-Grenze, hier festgeschrieben statt verschwiegen.

    Der Hook liest den BEFEHLSTEXT (wie `block_empty_body_file`), nicht den
    Ausführungsplan. Wer die Zeichenkette in eine Datei schreibt, wird geblockt.
    Bewusst in Kauf genommen: der Fall ist selten, der Ausweg (Text anders
    schreiben) billig, und die Alternative — Shell-Parsing — wäre die größere
    Fehlerquelle.
    """
    assert entscheide("echo 'git stash pop' >> runbook.md") is not None
