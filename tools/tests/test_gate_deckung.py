"""Drill fuer tools/gate_deckung.py — die vierte Achse (Abdeckung).

Der wichtigste Test hier ist `covers`: der erste Lauf des Werkzeugs las nur das
`slug`-Feld der Registry und meldete deshalb 19 offene Gate-Pflichten, waehrend
`retro_kpis.py` (das `covers` liest) 5 meldete. Zwei Werkzeuge, die dieselbe
Registry unterschiedlich lesen, machen jede Zahl verhandelbar — genau das faengt
`test_should_count_covers_as_decided` ab.

Run: `python3 -m pytest tools/tests/test_gate_deckung.py -q`
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "gate_deckung.py"
_spec = importlib.util.spec_from_file_location("gate_deckung", _QUELLE)
gd = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gd)


def _retro(verzeichnis: Path, datum: str, kuerzel: str, slugs: list[str]) -> None:
    (verzeichnis / f"session-retro-{datum}-platform-{kuerzel}.md").write_text(
        "---\nretro_schema: 1\nrecurring_findings: [" + ", ".join(slugs) + "]\n---\n",
        encoding="utf-8",
    )


def _bewerte(verzeichnis: Path, registry: dict) -> dict:
    import importlib.util as iu

    s = iu.spec_from_file_location("gw", _QUELLE.parent / "gate_wirkung.py")
    gw = iu.module_from_spec(s)
    s.loader.exec_module(gw)
    return gd.bewerte(gw.lies_retros([str(verzeichnis)]), gd.gedeckte_slugs(registry))


def test_should_count_covers_as_decided():
    """Ein Gate deckt oft mehr als seinen eigenen Slug — `covers` ist Pflicht."""
    registry = {
        "gates": [{"slug": "anker-gate", "covers": ["planned-phase-no-issue"]}],
        "declined": [],
    }

    gedeckt = gd.gedeckte_slugs(registry)

    assert "anker-gate" in gedeckt
    assert "planned-phase-no-issue" in gedeckt, "covers ignoriert ⇒ Falschmeldung"


def test_should_count_declined_as_decided():
    """Ein bewusst abgelehntes Gate ist eine getroffene Entscheidung, keine Luecke."""
    registry = {"gates": [], "declined": ["bewusst-ohne-gate"]}

    assert "bewusst-ohne-gate" in gd.gedeckte_slugs(registry)


def test_should_report_a_slug_seen_twice_without_any_decision(tmp_path):
    _retro(tmp_path, "2026-07-10", "a", ["nie-gegated"])
    _retro(tmp_path, "2026-07-11", "b", ["nie-gegated"])

    ergebnis = _bewerte(tmp_path, {"gates": [], "declined": []})

    assert [e["slug"] for e in ergebnis["offene_pflichten"]] == ["nie-gegated"]
    assert ergebnis["offene_pflichten"][0]["vorkommen"] == 2


def test_should_not_report_a_single_occurrence(tmp_path):
    """Die Hausschwelle ist 2 — ein einmaliger Befund ist kein Versaeumnis."""
    _retro(tmp_path, "2026-07-10", "a", ["nur-einmal"])

    ergebnis = _bewerte(tmp_path, {"gates": [], "declined": []})

    assert ergebnis["offene_pflichten"] == []
    assert "nur-einmal" in ergebnis["einmalig_ungedeckt"]


def test_should_agree_with_retro_kpis_threshold():
    """Beide Werkzeuge muessen dieselbe GATE-PFLICHT-Schwelle benutzen.

    Laufen sie auseinander, eskaliert das eine, was das andere durchwinkt — und
    niemand weiss, welche Zahl gilt.
    """
    import importlib.util as iu

    s = iu.spec_from_file_location("rk", _QUELLE.parent / "retro_kpis.py")
    rk = iu.module_from_spec(s)
    s.loader.exec_module(rk)

    assert gd.PFLICHT_SCHWELLE == getattr(rk, "GATE_THRESHOLD", 2)


def test_should_print_nothing_in_kurz_mode_without_open_duties(tmp_path):
    _retro(tmp_path, "2026-07-10", "a", ["nur-einmal"])
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({"gates": [], "declined": []}), encoding="utf-8")

    lauf = subprocess.run(
        [
            sys.executable,
            str(_QUELLE),
            "--kurz",
            "--registry",
            str(registry),
            "--dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert lauf.returncode == 0
    assert lauf.stdout.strip() == ""


def test_should_stay_exit_zero_on_unreadable_registry(tmp_path):
    lauf = subprocess.run(
        [
            sys.executable,
            str(_QUELLE),
            "--kurz",
            "--registry",
            str(tmp_path / "weg.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert lauf.returncode == 0
