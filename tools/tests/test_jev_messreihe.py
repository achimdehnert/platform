"""Drill fuer tools/jev_messreihe.py (platform#3337).

Der teuerste Fall steht in `test_should_refuse_to_measure_below_threshold`:
Eine AUC ueber vier Faelle sieht aus wie ein Ergebnis und ist eine Zufallszahl.
Wenn das Werkzeug sie ausgibt, beruhigt sie — und niemand misst nach.

Das Netz wird hier NICHT angefasst: `frage_modell` ist die einzige Funktion mit
Aussenkontakt und wird in jedem Test ersetzt. Der echte Pfad wurde am
2026-09-21 einmal gegen den laufenden Dienst belegt (AUC 0,560 ueber 20 Faelle).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jev_messreihe as jm  # noqa: E402


@pytest.fixture
def heim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Eigenes HOME — nie das echte ~/.claude/befund-journal.json lesen."""
    claude = tmp_path / ".claude"
    claude.mkdir(parents=True)
    monkeypatch.setattr(jm, "JOURNAL", claude / "befund-journal.json")
    monkeypatch.setattr(jm, "MESSREIHE", claude / "jev-messreihe.jsonl")
    return claude


def _journal(claude: Path, urteile: list[dict]) -> None:
    (claude / "befund-journal.json").write_text(
        json.dumps({"befunde": {}, "urteile": urteile}), encoding="utf-8"
    )


def _urteile(echt: int, falsch: int, *, ab: int = 0) -> list[dict]:
    return [
        {"eingabe": f"echter Befund {i + ab}", "urteil": "echt"} for i in range(echt)
    ] + [{"eingabe": f"Fehlalarm {i + ab}", "urteil": "falsch"} for i in range(falsch)]


# ── AUC ─────────────────────────────────────────────────────────────────────


def test_should_report_auc_one_for_perfect_separation() -> None:
    assert jm.auc([0.9, 0.8, 0.7], [0.3, 0.2, 0.1]) == 1.0


def test_should_report_auc_zero_for_inverted_separation() -> None:
    """Falsch herum ist nicht dasselbe wie Zufall — das muss sichtbar bleiben."""
    assert jm.auc([0.1, 0.2], [0.8, 0.9]) == 0.0


def test_should_count_ties_as_half() -> None:
    """Lauter gleiche Werte sind Zufall, kein Treffer.

    Ohne diese Regel entscheidet die Sortierreihenfolge das Ergebnis — ein
    Modell, das ueberall 0,5 sagt, saehe je nach Implementierung perfekt oder
    wertlos aus.
    """
    assert jm.auc([0.5, 0.5], [0.5, 0.5]) == 0.5


def test_should_return_neutral_auc_without_any_pairs() -> None:
    assert jm.auc([], [0.4]) == 0.5


# ── Schwelle: lieber nichts als eine Zufallszahl ────────────────────────────


def test_should_refuse_to_measure_below_threshold(heim: Path, monkeypatch) -> None:
    gerufen = []
    monkeypatch.setattr(
        jm, "frage_modell", lambda t: gerufen.append(t) or [0.9] * len(t)
    )
    _journal(heim, _urteile(echt=3, falsch=3))

    jm.main_fuer_test(mindestens=10)
    satz = json.loads(
        (heim / "jev-messreihe.jsonl").read_text(encoding="utf-8").strip()
    )

    assert satz["auc"] is None
    assert "noch nicht messbar" in satz["status"]
    assert gerufen == [], "das Modell darf unterhalb der Schwelle gar nicht erst laufen"


def test_should_measure_once_threshold_is_reached(heim: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        jm, "frage_modell", lambda t: [0.9 if "echter" in x else 0.1 for x in t]
    )
    _journal(heim, _urteile(echt=10, falsch=10))

    jm.main_fuer_test(mindestens=10)
    satz = json.loads(
        (heim / "jev-messreihe.jsonl").read_text(encoding="utf-8").strip()
    )

    assert satz["status"] == "gemessen"
    assert satz["auc"] == 1.0


def test_should_record_no_number_when_service_is_unreachable(
    heim: Path, monkeypatch
) -> None:
    """Ein toter Dienst ist ein Befund ueber den Dienst, kein Messergebnis."""
    monkeypatch.setattr(jm, "frage_modell", lambda t: None)
    _journal(heim, _urteile(echt=10, falsch=10))

    jm.main_fuer_test(mindestens=10)
    satz = json.loads(
        (heim / "jev-messreihe.jsonl").read_text(encoding="utf-8").strip()
    )

    assert satz["auc"] is None
    assert "nicht erreichbar" in satz["status"]


# ── Datenlage ───────────────────────────────────────────────────────────────


def test_should_count_judgements_without_input_as_defect(heim: Path) -> None:
    """Die 51 Alturteile aus der Zeit vor #3339 sind unbrauchbar — und sollen
    als Mangel sichtbar bleiben, statt stillschweigend zu fehlen."""
    _journal(
        heim,
        [{"urteil": "echt"}, {"urteil": "falsch"}, {"eingabe": "x", "urteil": "echt"}],
    )

    paare, maengel = jm.lade_paare()

    assert len(paare) == 1
    assert maengel["ohne_eingabe"] == 2


def test_should_drop_duplicate_text_and_verdict_pairs(heim: Path) -> None:
    """Derselbe Meldetext mit demselben Urteil zaehlt einmal.

    Ein rollender Melder wiederholt seine Zeile Lauf fuer Lauf; ohne diese
    Regel waechst der Satz, ohne dass Information dazukommt.
    """
    _journal(
        heim,
        [
            {"eingabe": "gleiche Zeile", "urteil": "echt"},
            {"eingabe": "gleiche Zeile", "urteil": "echt"},
            {"eingabe": "gleiche Zeile", "urteil": "falsch"},
        ],
    )

    paare, maengel = jm.lade_paare()

    assert len(paare) == 2, "anderes Urteil zum selben Text bleibt erhalten"
    assert maengel["dubletten"] == 1


def test_should_treat_blank_input_as_defect_not_as_data(heim: Path) -> None:
    _journal(heim, [{"eingabe": "   ", "urteil": "echt"}])

    paare, maengel = jm.lade_paare()

    assert paare == []
    assert maengel["leere_eingabe"] == 1


def test_should_report_growth_against_the_previous_run(heim: Path, monkeypatch) -> None:
    """Die Reihe soll Zuwachs zeigen — das ist die Kennzahl, die zuerst zaehlt."""
    monkeypatch.setattr(jm, "frage_modell", lambda t: None)
    _journal(heim, _urteile(echt=2, falsch=2))
    jm.main_fuer_test(mindestens=10)
    _journal(heim, _urteile(echt=5, falsch=5))
    jm.main_fuer_test(mindestens=10)

    zeilen = [
        json.loads(z)
        for z in (heim / "jev-messreihe.jsonl").read_text(encoding="utf-8").splitlines()
        if z.strip()
    ]

    assert [z["paare"] for z in zeilen] == [4, 10]
