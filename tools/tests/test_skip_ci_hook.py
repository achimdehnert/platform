"""commit-msg-Hook: literales `[skip ci]` nur mit Opt-in-Trailer.

Retro-Befund 2026-07-31: Ein Commit, der über den Marker SCHRIEB, trug ihn
wörtlich in der Message. GitHub startete keinen Lauf, die Required Checks
meldeten nie — platform#1503 blieb 37 h 56 min blockiert, ohne rot zu werden.
"""

from __future__ import annotations

import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "hooks" / "check_skip_ci_marker.py"
_spec = importlib.util.spec_from_file_location("skip_ci_hook", _SRC)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

MARKER = "[" + "skip ci" + "]"  # nicht literal, sonst trifft der Hook diese Datei


def test_should_reject_marker_quoted_in_prose():
    """Der Realfall: der Text schreibt ÜBER den Marker."""
    fehler = hook.pruefe(
        f"docs: Falle beschreiben\n\nDer Marker {MARKER} blockiert alles.\n"
    )
    assert fehler is not None
    assert "37 h 56 min" in fehler


def test_should_allow_marker_with_opt_in_trailer():
    fehler = hook.pruefe(f"docs: nur README\n\nSkip-CI: absichtlich\n{MARKER}\n")
    assert fehler is None


def test_should_allow_message_without_marker():
    assert hook.pruefe("fix: etwas reparieren\n\nOhne Marker.\n") is None


def test_should_ignore_marker_in_comment_lines():
    """git entfernt Kommentarzeilen — GitHub sieht sie nie."""
    assert hook.pruefe(f"fix: etwas\n\n# Hinweis: {MARKER} wäre hier falsch\n") is None


def test_should_catch_alternative_spellings():
    for variante in ("ci skip", "skip-ci", "no ci", "skip actions"):
        assert hook.pruefe(f"docs: x\n\n[{variante}]\n") is not None, variante


def test_should_be_case_insensitive():
    assert hook.pruefe("docs: x\n\n[SKIP CI]\n") is not None


def test_should_require_trailer_on_its_own_line():
    """Ein Trailer mitten im Fließtext ist keine bewusste Entscheidung."""
    fehler = hook.pruefe(f"docs: x\n\nblah Skip-CI: absichtlich blah {MARKER}\n")
    assert fehler is not None
