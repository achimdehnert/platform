"""Drill für `gui-geaendert-ohne-klick`.

Der Scanner meldet, wenn in einer Sitzung GUI-Dateien geschrieben wurden, aber
weder ein Browser-Werkzeug lief noch `/ux-review` aufgerufen wurde.

Der Drill prüft beide Richtungen. Ein Gate, das nur „findet nichts" beweist,
ist nicht von einem kaputten Gate zu unterscheiden.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_QUELLE = Path(__file__).resolve().parents[1] / "gui_ohne_klick_scanner.py"
_spec = importlib.util.spec_from_file_location("gui_ohne_klick_scanner", _QUELLE)
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)


def _transkript(tmp_path: Path, *eintraege: dict) -> Path:
    p = tmp_path / "t.jsonl"
    with p.open("w", encoding="utf-8") as fh:
        for e in eintraege:
            fh.write(json.dumps(e) + "\n")
    return p


def _schreib(pfad: str) -> dict:
    return {
        "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": pfad}}]}
    }


def _tool(name: str, eingabe: dict | None = None) -> dict:
    return {
        "message": {
            "content": [{"type": "tool_use", "name": name, "input": eingabe or {}}]
        }
    }


def _text(t: str) -> dict:
    return {"message": {"content": [{"type": "text", "text": t}]}}


# --- Der Befund ------------------------------------------------------------------


@pytest.mark.parametrize(
    "pfad",
    [
        "/repo/templates/worlds/world_detail.html",
        "/repo/apps/worlds/views_html.py",
        "/repo/templates/prompts/worlds/kanon_extract.jinja2",
        "/repo/static/js/editor.js",
    ],
)
def test_should_report_gui_change_without_any_look(tmp_path, pfad):
    """Der Realfall vom 2026-08-26: Templates geändert, nie geklickt."""
    t = _transkript(tmp_path, _schreib(pfad))
    gui, geblickt = scanner._pfade_und_tools(t)

    assert gui, f"{pfad} gilt nicht als GUI-Datei"
    assert not geblickt


# --- Erfüllung: jemand hat hingesehen ---------------------------------------------


def test_should_stay_silent_after_a_real_browser_call(tmp_path):
    t = _transkript(
        tmp_path,
        _schreib("/repo/templates/x.html"),
        _tool("mcp__playwright__browser_navigate", {"url": "http://localhost:8097/"}),
    )
    _, geblickt = scanner._pfade_und_tools(t)
    assert geblickt


def test_should_stay_silent_after_ux_review_skill(tmp_path):
    t = _transkript(
        tmp_path,
        _schreib("/repo/templates/x.html"),
        _tool("Skill", {"skill": "ux-review"}),
    )
    _, geblickt = scanner._pfade_und_tools(t)
    assert geblickt


def test_should_accept_the_command_mentioned_in_text(tmp_path):
    """Wer `/ux-review` ankündigt und fährt, hat die Regel befolgt."""
    t = _transkript(
        tmp_path,
        _schreib("/repo/templates/x.html"),
        _text("Ich fahre jetzt /ux-review über die Kette."),
    )
    _, geblickt = scanner._pfade_und_tools(t)
    assert geblickt


# --- Fehlalarm-Gegenproben ---------------------------------------------------------


@pytest.mark.parametrize(
    "pfad",
    [
        "/repo/tests/ux/test_gesamtdurchlauf.py",
        "/repo/tests/test_templates_compile.py",
        "/repo/docs/retros/session-retro.md",
        "/repo/AGENT_HANDOVER.md",
        "/repo/apps/worlds/services/welt_aus_konzept.py",
        "/repo/tests/conftest.py",
    ],
)
def test_should_not_report_non_gui_changes(tmp_path, pfad):
    """Tests, Doku und Dienste sind keine GUI — sonst feuert das Gate dauernd."""
    t = _transkript(tmp_path, _schreib(pfad))
    gui, _ = scanner._pfade_und_tools(t)
    assert not gui, f"{pfad} wird fälschlich als GUI gewertet"


def test_should_not_report_an_empty_session(tmp_path):
    t = _transkript(tmp_path, _text("Nur geredet."))
    gui, _ = scanner._pfade_und_tools(t)
    assert not gui


def test_should_stay_silent_when_the_transcript_is_unreadable(tmp_path):
    """Fail-open: ein Hook darf eine Sitzung nie an sich selbst scheitern lassen."""
    gui, geblickt = scanner._pfade_und_tools(tmp_path / "gibt-es-nicht.jsonl")
    assert not gui and geblickt


# --- main() ------------------------------------------------------------------------


def test_should_print_the_finding_on_stop(tmp_path, capsys, monkeypatch):
    t = _transkript(tmp_path, _schreib("/repo/templates/worlds/world_detail.html"))
    monkeypatch.setattr(
        "sys.stdin", type("S", (), {"read": staticmethod(lambda: json.dumps({"transcript_path": str(t)}))})()
    )

    assert scanner.main() == 0
    assert "gui-geaendert-ohne-klick" in capsys.readouterr().err


def test_should_respect_the_off_switch(tmp_path, capsys, monkeypatch):
    t = _transkript(tmp_path, _schreib("/repo/templates/x.html"))
    monkeypatch.setenv("GUI_KLICK_GATE", "aus")
    monkeypatch.setattr(
        "sys.stdin", type("S", (), {"read": staticmethod(lambda: json.dumps({"transcript_path": str(t)}))})()
    )

    assert scanner.main() == 0
    assert capsys.readouterr().err == ""
