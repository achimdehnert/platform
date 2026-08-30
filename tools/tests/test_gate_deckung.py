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


def _bewerte(verzeichnis: Path, registry: dict, heute: str | None = None) -> dict:
    import importlib.util as iu

    s = iu.spec_from_file_location("gw", _QUELLE.parent / "gate_wirkung.py")
    gw = iu.module_from_spec(s)
    s.loader.exec_module(gw)
    return gd.bewerte(
        gw.lies_retros([str(verzeichnis)]), gd.gedeckte_slugs(registry), heute
    )


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


# --- Liegezeit: der Loop misst bisher nur Bestand, nicht Durchsatz -----------
# platform#2278 K3. Ein Bestand von 77 unentschiedenen Slugs kann heissen, dass
# gestern 77 neue dazukamen — oder dass dieselben 77 seit Monaten liegen. Gleiche
# Zahl, verschiedene Lage. Erst die Liegezeit trennt die beiden.

_LEER = {"gates": [], "declined": []}


def test_should_measure_lying_time_from_first_occurrence_not_last(tmp_path):
    """Ein Slug, der seit Juni wiederkehrt, liegt seit Juni — nicht seit gestern.

    Waere das letzte Vorkommen der Anker, wuerde ausgerechnet der hartnaeckigste
    Befund als der juengste erscheinen: jede Wiederholung setzte seine Uhr zurueck.
    """
    _retro(tmp_path, "2026-06-01", "a", ["hartnaeckig"])
    _retro(tmp_path, "2026-08-01", "b", ["hartnaeckig"])

    lz = _bewerte(tmp_path, _LEER, heute="2026-08-25")["liegezeit"]

    assert lz["aeltester_tage"] == 85  # ab 2026-06-01, nicht ab 2026-08-01
    assert lz["aeltester_slug"] == "hartnaeckig"


def test_should_ignore_slugs_that_already_have_a_decision(tmp_path):
    _retro(tmp_path, "2026-06-01", "a", ["entschieden", "offen"])

    lz = _bewerte(tmp_path, {"gates": [], "declined": ["entschieden"]}, "2026-08-25")[
        "liegezeit"
    ]

    assert lz["slugs"] == 1 and lz["aeltester_slug"] == "offen"


def test_should_use_the_median_so_one_ancient_slug_does_not_carry_the_number(tmp_path):
    """Mit dem Mittelwert taeuscht ein einzelner Uralt-Slug eine Verbesserung vor,
    sobald er endlich entschieden wird — obwohl sich an den uebrigen nichts aendert."""
    _retro(tmp_path, "2026-08-20", "a", ["jung1", "jung2"])
    _retro(tmp_path, "2026-01-01", "b", ["uralt"])

    lz = _bewerte(tmp_path, _LEER, "2026-08-25")["liegezeit"]

    assert lz["median_tage"] == 5  # Mittelwert waere 82
    assert lz["aeltester_tage"] == 236


def test_should_report_the_corpus_start_so_the_number_reads_as_a_lower_bound(tmp_path):
    """Die Zahl kann nur so weit zurueckreichen wie der Retro-Korpus.

    Gemessen am 2026-08-25 lag der aelteste unentschiedene Slug bei 56 Tagen — bei
    einem Korpus von exakt 56 Tagen. Ein Wert am Rand ist abgeschnitten, nicht
    bestaetigt; ohne das Korpus-Datum liest sich die Zahl genauer, als sie ist.
    """
    _retro(tmp_path, "2026-07-01", "a", ["irgendwas"])

    lz = _bewerte(tmp_path, _LEER, "2026-08-25")["liegezeit"]

    assert lz["korpus_ab"] == "2026-07-01"
    assert ">=" in gd.liegezeit_zeile(lz)
    assert "Korpus ab 2026-07-01" in gd.liegezeit_zeile(lz)
    assert ">=" in gd.liegezeit_zeile(lz, kurz=True), (
        "auch kompakt bleibt es Untergrenze"
    )


def test_should_stay_none_when_every_slug_is_decided(tmp_path):
    _retro(tmp_path, "2026-08-01", "a", ["entschieden"])

    assert (
        _bewerte(tmp_path, {"gates": [], "declined": ["entschieden"]})["liegezeit"]
        is None
    )


def test_should_print_the_lying_time_without_the_finding_list(tmp_path):
    """`--liegezeit` ist ein eigener Aufruf, weil der Runner PASS/WARN an der
    LAENGE der `--kurz`-Ausgabe entscheidet. Liefe die Zahl dort mit, waere 0.7.9
    dauerhaft gelb — und ein Melder, der jede Sitzung warnt, wird nicht gelesen."""
    _retro(tmp_path, "2026-08-01", "a", ["offen"])
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps(_LEER), encoding="utf-8")

    lauf = subprocess.run(
        [
            sys.executable,
            str(_QUELLE),
            "--liegezeit",
            "--kurz",
            "--registry",
            str(registry),
            "--dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert "Liegezeit" in lauf.stdout
    assert "offen" not in lauf.stdout.split("(")[0], (
        "Befundliste gehoert hier nicht hin"
    )


def test_should_keep_the_runner_showing_lying_time_in_both_branches():
    """Gerade der PASS-Fall braucht sie: 'keine offene Gate-Pflicht' heisst nur,
    dass kein Slug ZWEIMAL ungedeckt auftrat. Die Einmal-Slugs liegen trotzdem."""
    runner = (_QUELLE.parent / "session_start_checks.sh").read_text(encoding="utf-8")
    record_zeilen = [
        z for z in runner.splitlines() if 'record "0.7.9 gate-deckung"' in z
    ]
    assert len(record_zeilen) == 2, record_zeilen
    for zeile in record_zeilen:  # WARN- und PASS-Zweig
        assert "${DECKUNG_LIEGE:+" in zeile, zeile
