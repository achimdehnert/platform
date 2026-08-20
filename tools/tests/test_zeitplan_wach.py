"""Drill fuer tools/zeitplan_wach.py — findet still abgeschaltete Zeitplaene.

Der wichtigste Test ist `test_should_not_report_zero_when_a_repo_was_unreachable`:
ein Flotten-Melder, der Abfragefehler verschluckt, meldet eine Null, die nur sein
eigener Filter ist. Genau das passierte beim ersten Lauf — er meldete null
abgeschaltete Zeitplaene, waehrend zwei seit drei Wochen tot waren; das betroffene
Repo fehlte schlicht in der Liste.

Run: `python3 -m pytest tools/tests/test_zeitplan_wach.py -q`
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "zeitplan_wach.py"
_spec = importlib.util.spec_from_file_location("zeitplan_wach", _QUELLE)
zw = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(zw)


def _mit_antworten(monkeypatch, antworten: dict):
    monkeypatch.setattr(zw, "workflows", lambda repo: antworten.get(repo))


def test_should_report_a_schedule_disabled_by_github(monkeypatch):
    _mit_antworten(
        monkeypatch,
        {"o/r": [{"name": "Database Backup", "state": "disabled_inactivity"}]},
    )

    ergebnis = zw.pruefe(["o/r"], nebenlaeufig=1)

    assert [e["workflow"] for e in ergebnis["still_abgeschaltet"]] == [
        "Database Backup"
    ]


def test_should_separate_manual_from_automatic_disabling(monkeypatch):
    """Von Hand abgeschaltet ist meist Absicht — nie mit dem stillen Fall mischen."""
    _mit_antworten(
        monkeypatch,
        {
            "o/r": [
                {"name": "Deploy", "state": "disabled_manually"},
                {"name": "Backup", "state": "disabled_inactivity"},
            ]
        },
    )

    ergebnis = zw.pruefe(["o/r"], nebenlaeufig=1)

    assert [e["workflow"] for e in ergebnis["still_abgeschaltet"]] == ["Backup"]
    assert [e["workflow"] for e in ergebnis["von_hand_abgeschaltet"]] == ["Deploy"]


def test_should_not_report_zero_when_a_repo_was_unreachable(monkeypatch):
    """Ein Abfragefehler ist KEIN gruener Zustand — er muss sichtbar bleiben."""
    _mit_antworten(monkeypatch, {"o/erreichbar": [], "o/kaputt": None})

    ergebnis = zw.pruefe(["o/erreichbar", "o/kaputt"], nebenlaeufig=1)

    assert ergebnis["nicht_abfragbar"] == ["o/kaputt"]
    assert ergebnis["geprueft"] == 1, (
        "nicht abfragbare Repos duerfen nicht als geprueft zaehlen"
    )


def test_should_ignore_active_workflows(monkeypatch):
    _mit_antworten(monkeypatch, {"o/r": [{"name": "CI", "state": "active"}]})

    ergebnis = zw.pruefe(["o/r"], nebenlaeufig=1)

    assert ergebnis["still_abgeschaltet"] == []
    assert ergebnis["von_hand_abgeschaltet"] == []


def test_should_read_full_names_from_registry_rich_github(tmp_path):
    """Die Org kommt aus `rich.github` — nie aus dem Repo-Namen geraten."""
    reg = tmp_path / "canonical.yaml"
    reg.write_text(
        "repos:\n"
        "  risk-hub:\n"
        "    rich:\n"
        "      github: iilgmbh/risk-hub\n"
        "  ohne-feld:\n"
        "    flat:\n"
        "      type: django\n",
        encoding="utf-8",
    )

    assert zw.repos_aus_registry(str(reg)) == ["iilgmbh/risk-hub"]


def test_should_sort_results_stably(monkeypatch):
    """Nebenlaeufigkeit darf die Ausgabe nicht bei jedem Lauf umsortieren."""
    _mit_antworten(
        monkeypatch,
        {
            "o/b": [{"name": "X", "state": "disabled_inactivity"}],
            "o/a": [{"name": "Y", "state": "disabled_inactivity"}],
        },
    )

    ergebnis = zw.pruefe(["o/b", "o/a"], nebenlaeufig=2)

    assert [e["repo"] for e in ergebnis["still_abgeschaltet"]] == ["o/a", "o/b"]
