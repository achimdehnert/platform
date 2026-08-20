"""Drill fuer die Melder-Praezision in tools/befund_journal.py.

Der wichtigste Test ist `test_should_keep_a_verdict_after_the_finding_heals`:
Befund-Eintraege verschwinden, sobald ihre Phase sie nicht mehr meldet. Laege das
Urteil IM Eintrag, waere die Praezision eines Melders genau so lange messbar, wie
sein Fehlalarm noch offen steht — also nie.

Run: `python3 -m pytest tools/tests/test_befund_praezision.py -q`
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "befund_journal.py"
_spec = importlib.util.spec_from_file_location("befund_journal", _QUELLE)
bj = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(bj)


def _journal(*eintraege: tuple[str, str]) -> dict:
    return {
        "befunde": {
            bj.fingerabdruck(phase, repo): {"phase": phase, "repo": repo, "laeufe": 1}
            for phase, repo in eintraege
        }
    }


def test_should_record_a_verdict_for_a_known_finding():
    daten = _journal(("0.7 deploy-scan", "travel-beat"))
    fid = bj.fingerabdruck("0.7 deploy-scan", "travel-beat")

    bj.urteile_dazu(daten, fid, "echt", "Prod war real rot")

    assert daten["urteile"][0]["urteil"] == "echt"
    assert daten["befunde"][fid]["urteil"] == "echt"


def test_should_keep_a_verdict_after_the_finding_heals():
    """Die Historie liegt NEBEN den Befunden — sonst ueberlebt sie keine Heilung."""
    daten = _journal(("0.7.4 prio-referenzen", "platform"))
    fid = bj.fingerabdruck("0.7.4 prio-referenzen", "platform")
    bj.urteile_dazu(daten, fid, "falsch", "zitiert historischen Kontext")

    del daten["befunde"][fid]  # Phase meldet ihn nicht mehr -> Heilung

    zeilen = bj.praezision(daten)
    assert [z["falsch"] for z in zeilen] == [1], (
        "Urteil darf nicht mit dem Befund verschwinden"
    )


def test_should_record_a_verdict_even_without_a_live_entry():
    """Phase und Repo stehen im Fingerabdruck — ein geheilter Befund bleibt urteilbar."""
    daten: dict = {"befunde": {}}

    bj.urteile_dazu(daten, "0.7.9 gate-deckung::platform", "echt", "belegt")

    assert daten["urteile"][0]["phase"] == "0.7.9 gate-deckung"
    assert daten["urteile"][0]["repo"] == "platform"


def test_should_refuse_a_rate_below_the_minimum():
    """Zwei Fehlalarme sind kein Urteil ueber einen Melder — nur Rauschen."""
    daten: dict = {"befunde": {}}
    for i in range(2):
        bj.urteile_dazu(daten, f"0.7.3 opt-platform::r{i}", "falsch", "x")

    zeile = bj.praezision(daten)[0]

    assert bj.MIN_URTEILE > 2
    assert zeile["bewertbar"] is False
    assert "NICHT bewertbar" in bj.praezisions_bericht(daten)


def test_should_compute_a_rate_once_enough_verdicts_exist():
    daten: dict = {"befunde": {}}
    for i in range(3):
        bj.urteile_dazu(daten, f"0.7.3 opt-platform::r{i}", "falsch", "x")
    bj.urteile_dazu(daten, "0.7.3 opt-platform::r9", "echt", "y")

    zeile = bj.praezision(daten)[0]

    assert zeile["bewertbar"] is True
    assert zeile["praezision"] == 0.25
    assert "🚨" in bj.praezisions_bericht(daten)


def test_should_not_flag_a_precise_melder():
    daten: dict = {"befunde": {}}
    for i in range(4):
        bj.urteile_dazu(daten, f"0.7.8 zeitplan-wache::r{i}", "echt", "belegt")

    bericht = bj.praezisions_bericht(daten)

    assert "🚨" not in bericht
    assert "100%" in bericht


def test_should_keep_phases_apart():
    daten: dict = {"befunde": {}}
    for i in range(3):
        bj.urteile_dazu(daten, f"0.7.3 opt-platform::r{i}", "falsch", "x")
    for i in range(3):
        bj.urteile_dazu(daten, f"0.7.8 zeitplan-wache::r{i}", "echt", "y")

    quoten = {z["phase"]: z["praezision"] for z in bj.praezision(daten)}

    assert quoten == {"0.7.3 opt-platform": 0.0, "0.7.8 zeitplan-wache": 1.0}
