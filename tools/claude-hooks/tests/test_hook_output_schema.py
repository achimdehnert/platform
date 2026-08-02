"""Jeder Hook, der `hookSpecificOutput` sendet, MUSS `hookEventName` mitschicken.

Realfall 2026-08-02: `memory_link_guard.py` und `hygiene_melder.py` gaben
`{"hookSpecificOutput": {"additionalContext": …}}` aus — ohne `hookEventName`.
Claude Code verwarf die Ausgabe mit

    Hook JSON output validation failed — hookSpecificOutput is missing required
    field "hookEventName"

und zeigte dem Menschen statt des Hinweises einen Schema-Fehler samt vollem
JSON-Dump. Der Melder war damit nicht nur wirkungslos, sondern lauter als im
Erfolgsfall.

Warum der bestehende Aufrufpfad-Drill das nicht fing: er prüft nur Module aus
`docs/governance/gate-registry.json`, und dort standen beide nicht; sein
Direktaufruf-Test filtert zusätzlich auf `*_scanner.py`. Beide Filter gingen an
genau diesen zwei Dateien vorbei. Dieser Test filtert **nichts** — er liest jede
`.py` unter `tools/claude-hooks/` (ohne `tests/`) und prüft die Ausgabe-Literale
im Quelltext per AST, nicht per Textsuche: `"hookEventName"` irgendwo in der
Datei würde sonst genügen, auch wenn es im falschen Dict steht.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent
ERLAUBTE_EVENTS = {
    "PreToolUse",
    "PostToolUse",
    "PostToolBatch",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
}

_module = sorted(p for p in HOOKS.glob("*.py") if p.name != "__init__.py")


def _hook_dicts(baum: ast.AST) -> list[ast.Dict]:
    """Alle Dict-Literale, die unter dem Schlüssel `hookSpecificOutput` hängen."""
    treffer: list[ast.Dict] = []
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Dict):
            continue
        for schluessel, wert in zip(knoten.keys, knoten.values):
            if (
                isinstance(schluessel, ast.Constant)
                and schluessel.value == "hookSpecificOutput"
                and isinstance(wert, ast.Dict)
            ):
                treffer.append(wert)
    return treffer


@pytest.mark.parametrize("pfad", _module, ids=lambda p: p.name)
def test_should_hookspecificoutput_immer_hookeventname_tragen(pfad: Path) -> None:
    baum = ast.parse(pfad.read_text(encoding="utf-8"), filename=str(pfad))
    for d in _hook_dicts(baum):
        schluessel = {
            k.value
            for k in d.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)
        }
        assert "hookEventName" in schluessel, (
            f"{pfad.name}: hookSpecificOutput ohne hookEventName — Claude Code "
            "verwirft die Ausgabe und zeigt dem Menschen einen Schema-Fehler "
            "statt des Hinweises."
        )


@pytest.mark.parametrize("pfad", _module, ids=lambda p: p.name)
def test_should_hookeventname_ein_bekanntes_event_sein(pfad: Path) -> None:
    """Ein Tippfehler im Event-Namen ist derselbe Ausfall, nur schwerer zu sehen.

    Ein Variablenwert ist ausdrücklich erlaubt und sogar die bessere Lösung: ein
    Hook, der auch als `SubagentStop` registriert werden kann, sollte den Namen
    aus dem Eingangs-Event übernehmen statt ihn festzunageln
    (`memory_link_guard.py` macht das so). Geprüft wird deshalb nur, was
    statisch prüfbar ist — ein Literal muss gültig sein.
    """
    baum = ast.parse(pfad.read_text(encoding="utf-8"), filename=str(pfad))
    for d in _hook_dicts(baum):
        for k, v in zip(d.keys, d.values):
            if isinstance(k, ast.Constant) and k.value == "hookEventName":
                if not isinstance(v, ast.Constant):
                    continue  # aus dem Event abgeleitet — zur Laufzeit geprüft
                assert v.value in ERLAUBTE_EVENTS, (
                    f"{pfad.name}: hookEventName={v.value!r} ist kein bekanntes Event"
                )


def test_should_wenigstens_einen_hook_gefunden_haben() -> None:
    """Gegenprobe: findet der Glob nichts, wären beide Tests leer und grün."""
    assert len(_module) >= 5, f"nur {len(_module)} Hook-Module gefunden — Glob kaputt?"


def test_should_mindestens_ein_modul_hookspecificoutput_senden() -> None:
    """Zweite Gegenprobe: prüft der AST-Pfad überhaupt etwas?"""
    mit_ausgabe = [
        p for p in _module if _hook_dicts(ast.parse(p.read_text(encoding="utf-8")))
    ]
    assert len(mit_ausgabe) >= 3, (
        f"nur {len(mit_ausgabe)} Module mit hookSpecificOutput erkannt — "
        "der AST-Pfad greift nicht"
    )
