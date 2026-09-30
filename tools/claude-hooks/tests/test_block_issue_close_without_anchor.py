"""Drill fuer block_issue_close_without_anchor.py (Gate aufschub-anker, #3169).

Realfall: Retro 97a9a1 Befund #1. Ein Issue im Ziel-Repo wurde per
`gh issue close <N> -R <repo> --comment "…"` geschlossen, ein Kommentar darin
vertagte Folgearbeit auf ein Issue ohne Nummer. Der Kommentartext hier ist
nachgebaut, nicht zitiert (platform ist oeffentlich, das Ziel-Repo nicht).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parent.parent / "block_issue_close_without_anchor.py"
_spec = importlib.util.spec_from_file_location("block_issue_close_without_anchor", _HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

WERKZEUG = hook.lade_werkzeug()

KOMMENTAR_OHNE_ANKER = (
    "**Ursache Deploy-Abbruch**\n\n"
    "Fix: das laufende Image in einen eigenen Spiegel legen.\n\n"
    "Mittelfristig: Ersatz fuer den Objektspeicher pruefen, eigenes Issue."
)
REALFALL = (
    'gh issue close 778 -R iilgmbh/risk-hub --comment "Prod ist live, '
    'der Rueckstand ist abgebaut."'
)


def _stoff(body: str, *kommentare: str):
    def laden(_werkzeug, _nummer, _repo):
        return body, [
            {"id": i, "html_url": f"https://example.invalid/c{i}", "body": k}
            for i, k in enumerate(kommentare, 1)
        ]

    return laden


def _daten(kommando: str) -> dict:
    return {"tool_input": {"command": kommando}, "cwd": "/tmp"}


def test_should_find_the_checkout_tool():
    assert WERKZEUG is not None


def test_should_block_the_real_close_with_an_unanchored_deferral_comment():
    """Positivkontrolle: der Realfall-Befehl gegen den nachgebauten Kommentar."""
    grund = hook.entscheide(
        _daten(REALFALL), WERKZEUG, _stoff("Prod-Rueckstand", KOMMENTAR_OHNE_ANKER)
    )

    assert grund is not None
    assert "iilgmbh/risk-hub#778" in grund
    assert "https://example.invalid/c1" in grund


def test_should_allow_the_close_when_the_closing_comment_names_an_anchor():
    """Gegenprobe: derselbe Befehl mit `Folgearbeit: #790` im Schliess-Kommentar."""
    kommando = REALFALL.replace("abgebaut.", "abgebaut. Folgearbeit: #790")

    assert (
        hook.entscheide(
            _daten(kommando), WERKZEUG, _stoff("Prod-Rueckstand", KOMMENTAR_OHNE_ANKER)
        )
        is None
    )


def test_should_allow_the_close_when_the_deferral_itself_is_anchored():
    kommentar = KOMMENTAR_OHNE_ANKER.replace("eigenes Issue.", "eigenes Issue #790.")

    assert hook.entscheide(_daten(REALFALL), WERKZEUG, _stoff("x", kommentar)) is None


def test_should_flag_a_deferral_in_the_closing_comment_itself():
    kommando = 'gh issue close 5 -R o/r -c "Erledigt, der Rest bleibt offen."'

    grund = hook.entscheide(_daten(kommando), WERKZEUG, _stoff("x"))

    assert grund is not None
    assert "Schliess-Kommentar" in grund


@pytest.mark.parametrize(
    "kommando, erwartet",
    [
        ("gh issue close 12", {"nummer": 12, "repo": None, "kommentar": ""}),
        ("gh issue close '#12' --repo o/r", {"nummer": 12, "repo": "o/r", "kommentar": ""}),
        (
            "gh issue close https://github.com/o/r/issues/7 --reason 'not planned'",
            {"nummer": 7, "repo": "o/r", "kommentar": ""},
        ),
        ("cd x && gh issue close 3 --comment=fertig && echo ok", {"nummer": 3, "repo": None, "kommentar": "fertig"}),
    ],
)
def test_should_parse_the_close_command(kommando, erwartet):
    assert hook.zerlege(kommando) == erwartet


@pytest.mark.parametrize(
    "kommando",
    ["gh issue view 12", "gh issue reopen 12", "gh pr close 12", "echo gh issue"],
)
def test_should_ignore_other_commands(kommando):
    assert hook.entscheide(_daten(kommando), WERKZEUG, _stoff("x", KOMMENTAR_OHNE_ANKER)) is None


def test_should_fail_open_when_gh_fails():
    def kaputt(*_):
        raise subprocess.CalledProcessError(1, "gh")

    assert hook.entscheide(_daten(REALFALL), WERKZEUG, kaputt) is None


def test_should_fail_open_without_a_resolvable_repo(monkeypatch):
    monkeypatch.setattr(hook, "repo_aus_cwd", lambda _cwd: None)

    assert hook.entscheide(_daten("gh issue close 12"), WERKZEUG, _stoff("x", KOMMENTAR_OHNE_ANKER)) is None


def test_should_emit_a_deny_decision_via_main(monkeypatch, capsys):
    monkeypatch.setattr(hook, "lade_werkzeug", lambda: WERKZEUG)
    monkeypatch.setattr(hook, "issue_stoff", _stoff("x", KOMMENTAR_OHNE_ANKER))
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps(_daten(REALFALL))))

    assert hook.main() == 0
    ausgabe = json.loads(capsys.readouterr().out)
    assert ausgabe["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_should_stay_silent_on_invalid_json(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("kein json"))

    assert hook.main() == 0
    assert capsys.readouterr().out == ""
