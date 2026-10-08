"""Drill fuer block_aufschub_ohne_anker.py (Gate aufschub-anker, platform#3859 M7).

Realfall: Retro 767d40-incr Befund #2. Ein Kommentar in meiki-lra/meiki-hub#582
fuehrte unter „Bewusst ausgelassen“ sechs Posten, fuenf ohne Issue; gepostet per
`gh issue comment 582 --repo meiki-lra/meiki-hub -F <datei>`. Der Text hier ist
nachgebaut, nicht zitiert.
"""

from __future__ import annotations

import importlib.util
import json
import shlex
import subprocess
import sys
from pathlib import Path

_HOOK = Path(__file__).resolve().parent.parent / "block_aufschub_ohne_anker.py"
_spec = importlib.util.spec_from_file_location("block_aufschub_ohne_anker", _HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

WERKZEUG = hook.lade_werkzeug()

OHNE_ANKER = "\n".join(
    [
        "## Bewusst ausgelassen, mit Folgeschritt",
        "",
        "- Gate in den uebrigen Repos: je ein PR nach shared-ci#108.",
        "- Wortlisten zusammenfuehren: bleiben vorerst getrennt.",
        "- Bestand (145): der Abbau ist eine eigene Entscheidung.",
    ]
)
MIT_ANKER = OHNE_ANKER.replace("getrennt.", "getrennt, #110.").replace(
    "Entscheidung.", "Entscheidung, #590."
)


def _daten(kommando: str, cwd: str = "/tmp") -> dict:
    return {"tool_input": {"command": kommando}, "cwd": cwd}


def test_should_find_the_checkout_tool():
    assert WERKZEUG is not None


def test_should_block_the_real_comment_from_body_file(tmp_path):
    """Positivkontrolle: Realfall-Befehl mit relativer Body-Datei."""
    (tmp_path / "c582.md").write_text(OHNE_ANKER)
    grund = hook.entscheide(
        _daten("gh issue comment 582 --repo meiki-lra/meiki-hub -F c582.md", str(tmp_path)),
        WERKZEUG,
    )
    assert grund is not None
    assert "2 Stelle(n)" in grund
    assert "Wortlisten" in grund and "Bestand" in grund


def test_should_block_pr_create_with_inline_body():
    kommando = f"gh pr create --title t --body {shlex.quote(OHNE_ANKER)}"
    assert hook.entscheide(_daten(kommando), WERKZEUG) is not None


def test_should_block_body_with_equals_sign(tmp_path):
    (tmp_path / "b.md").write_text(OHNE_ANKER)
    kommando = f"gh pr edit 5 --body-file={tmp_path / 'b.md'}"
    assert hook.entscheide(_daten(kommando), WERKZEUG) is not None


def test_should_check_second_gh_command_in_chain(tmp_path):
    (tmp_path / "ok.md").write_text(MIT_ANKER)
    (tmp_path / "nok.md").write_text(OHNE_ANKER)
    kommando = (
        f"gh issue comment 1 -F {tmp_path / 'ok.md'} && "
        f"gh pr comment 2 -F {tmp_path / 'nok.md'}"
    )
    assert hook.entscheide(_daten(kommando), WERKZEUG) is not None


def test_should_pass_text_with_anchor_per_item(tmp_path):
    """Negativprobe: jeder Posten mit eigenem Issue."""
    (tmp_path / "c.md").write_text(MIT_ANKER)
    kommando = f"gh issue comment 582 -F {tmp_path / 'c.md'}"
    assert hook.entscheide(_daten(kommando), WERKZEUG) is None


def test_should_pass_other_gh_commands():
    """Negativprobe: lesende oder schliessende gh-Befehle prueft dieser Hook nicht."""
    for kommando in (
        "gh issue view 582 --json body",
        "gh pr list --search 'Bewusst ausgelassen'",
        "gh issue close 5 --comment 'folgt separat'",
    ):
        assert hook.entscheide(_daten(kommando), WERKZEUG) is None, kommando


def test_should_pass_stdin_body_file():
    """Negativprobe: `-F -` ist nicht auswertbar -> fail-open."""
    assert hook.entscheide(_daten("gh pr comment 1 -F -"), WERKZEUG) is None


def test_should_pass_missing_body_file(tmp_path):
    """Negativprobe: nicht lesbare Datei -> fail-open, gh meldet den Fehler selbst."""
    kommando = f"gh issue comment 1 -F {tmp_path / 'fehlt.md'}"
    assert hook.entscheide(_daten(kommando), WERKZEUG) is None


def test_should_pass_without_tool(monkeypatch):
    """Negativprobe: Werkzeug nicht ladbar -> fail-open."""
    monkeypatch.setattr(hook, "lade_werkzeug", lambda: None)
    kommando = f"gh pr comment 1 --body {shlex.quote(OHNE_ANKER)}"
    assert hook.entscheide(_daten(kommando)) is None


def test_should_emit_deny_json_end_to_end(tmp_path):
    """Echter Prozess: JSON auf stdin, deny auf stdout, Exit 0."""
    (tmp_path / "c.md").write_text(OHNE_ANKER)
    eingabe = json.dumps(_daten(f"gh issue comment 1 -F {tmp_path / 'c.md'}"))
    res = subprocess.run(
        [sys.executable, str(_HOOK)], input=eingabe, capture_output=True, text=True, timeout=30
    )
    assert res.returncode == 0
    assert json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_should_stay_silent_on_garbage_input():
    res = subprocess.run(
        [sys.executable, str(_HOOK)], input="kein json", capture_output=True, text=True, timeout=30
    )
    assert res.returncode == 0 and res.stdout == ""
