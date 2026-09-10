"""Tests für tools/mail_agent/messjournal.py — K2 "Selbstmessung" (#3015).

Alles offline über `--eingabe` (feste Werte statt echter Kommandos) und
`--journal tmp_path` (keine Beruehrung von ~/.claude/mail-messjournal.jsonl).
Kein Test liest das echte Ledger oder ruft ein Mail-Kommando auf.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKRIPT = Path(__file__).resolve().parents[1] / "mail_agent" / "messjournal.py"


def _lauf(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _modul():
    spec = importlib.util.spec_from_file_location("messjournal", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["messjournal"] = modul
    spec.loader.exec_module(modul)
    return modul


mj = _modul()


def test_should_schreiben_eine_journalzeile_mit_pflichtfeldern(tmp_path):
    journal = tmp_path / "journal.jsonl"
    eingabe = json.dumps({"vorgaenge_gesamt": 5, "ohne_frist": 0})
    ergebnis = _lauf(
        "--schreiben",
        "--anwendung",
        "mailcheck",
        "--modell",
        "test-modell",
        "--journal",
        str(journal),
        "--eingabe",
        eingabe,
    )
    assert ergebnis.returncode == 0
    zeilen = journal.read_text(encoding="utf-8").strip().splitlines()
    assert len(zeilen) == 1
    eintrag = json.loads(zeilen[0])
    for feld in (
        "zeit",
        "anwendung",
        "modell",
        "kennzahlen",
        "fehler",
        "quelle_version",
    ):
        assert feld in eintrag


def test_should_trend_zwei_laeufe_mit_delta_zeigen(tmp_path):
    journal = tmp_path / "journal.jsonl"
    _lauf(
        "--schreiben",
        "--anwendung",
        "todo",
        "--modell",
        "m1",
        "--journal",
        str(journal),
        "--eingabe",
        json.dumps({"vorgangsseiten": 10, "mail_links": 20}),
    )
    _lauf(
        "--schreiben",
        "--anwendung",
        "todo",
        "--modell",
        "m1",
        "--journal",
        str(journal),
        "--eingabe",
        json.dumps({"vorgangsseiten": 12, "mail_links": 20}),
    )
    ergebnis = _lauf("--trend", "--anwendung", "todo", "--journal", str(journal))
    assert ergebnis.returncode == 0
    zeilen = ergebnis.stdout.strip().splitlines()
    assert len(zeilen) == 3  # Kopfzeile + 2 Laeufe
    assert "(+2)" in zeilen[-1]


def test_should_fehlende_kennzahl_zu_null_und_fehler_machen(tmp_path):
    journal = tmp_path / "journal.jsonl"
    ergebnis = _lauf(
        "--schreiben",
        "--anwendung",
        "mailcheck",
        "--journal",
        str(journal),
        "--eingabe",
        json.dumps({"vorgaenge_gesamt": 3}),
    )
    assert ergebnis.returncode == 0
    eintrag = json.loads(journal.read_text(encoding="utf-8").strip())
    assert eintrag["kennzahlen"]["unverankert"] is None
    assert "unverankert" in eintrag["fehler"]


def test_should_journalzeile_keine_personendaten_enthalten(tmp_path):
    journal = tmp_path / "journal.jsonl"
    _lauf(
        "--schreiben",
        "--anwendung",
        "mailcheck",
        "--journal",
        str(journal),
        "--eingabe",
        json.dumps({"vorgaenge_gesamt": 1}),
    )
    text = journal.read_text(encoding="utf-8")
    assert "@" not in text
    for verboten in ("betreff", "gegenueber", "thread_key"):
        assert verboten not in text


def test_should_trend_auf_leerem_journal_journal_leer_melden(tmp_path):
    journal = tmp_path / "journal-leer.jsonl"
    ergebnis = _lauf("--trend", "--journal", str(journal))
    assert ergebnis.returncode == 0
    assert ergebnis.stdout.strip() == "Journal leer"


def test_should_anwendung_alle_zwei_zeilen_je_eigener_anwendung_schreiben(tmp_path):
    """#3067: ein Lauf, zwei Journalzeilen — eine je Anwendung."""
    journal = tmp_path / "journal.jsonl"
    eingabe = json.dumps(
        {
            "vorgaenge_gesamt": 5,
            "vorgangsseiten_geprueft": 3,
            "vorgangsseiten_tot": 1,
            "vorgangsseiten": 3,
            "mail_links_tot": 1,
        }
    )
    ergebnis = _lauf(
        "--schreiben",
        "--anwendung",
        "alle",
        "--journal",
        str(journal),
        "--eingabe",
        eingabe,
    )
    assert ergebnis.returncode == 0
    zeilen = journal.read_text(encoding="utf-8").strip().splitlines()
    assert len(zeilen) == 2
    anwendungen = {json.loads(z)["anwendung"] for z in zeilen}
    assert anwendungen == {"mailcheck", "todo"}


def test_should_link_pruefen_bei_alle_genau_einmal_laufen_und_beide_zeilen_fuellen(
    monkeypatch, tmp_path
):
    """#3067: geteilte Quelle (link_pruefen) wird bei --anwendung alle einmal
    erhoben; ihr Ergebnis landet identisch in der mailcheck- UND der
    todo-Zeile."""
    aufrufe = {"n": 0}

    def gezaehlt() -> dict[str, int | None]:
        aufrufe["n"] += 1
        return {"seiten": 3, "links": 5, "geprueft": 5, "tot": 2}

    monkeypatch.setattr(mj, "_link_pruefen_vorgangsseiten", gezaehlt)
    monkeypatch.setattr(
        mj, "_mailcheck_board", lambda: {"vorgaenge_gesamt": 1, "ohne_frist": 0}
    )
    monkeypatch.setattr(
        mj, "_mailcheck_referenzen", lambda: {"referenzen_ohne_ordner": 0}
    )
    monkeypatch.setattr(mj, "_mailcheck_anker", lambda: {"unverankert": 0})
    monkeypatch.setattr(
        mj, "_mailcheck_ablage", lambda: {"posteingang_geschlossene_vorgaenge": 0}
    )
    monkeypatch.setattr(mj, "_mailcheck_index_alter", lambda: 0)
    monkeypatch.setattr(
        mj, "_todo_direkt", lambda: {"geschlossen_7_tage": 0, "ohne_kopf_aktion": 0}
    )
    monkeypatch.setattr(mj, "_quelle_version", lambda: "test")

    journal = tmp_path / "journal.jsonl"
    zeilen = mj.schreiben(["mailcheck", "todo"], "test-modell", journal, None)

    assert aufrufe["n"] == 1
    mailcheck = next(z for z in zeilen if z["anwendung"] == "mailcheck")
    todo = next(z for z in zeilen if z["anwendung"] == "todo")
    assert mailcheck["kennzahlen"]["vorgangsseiten_tot"] == 2
    assert todo["kennzahlen"]["mail_links_tot"] == 2


def _mailcheck_grundmocks(monkeypatch, ablage=None) -> None:
    """Alle Mailcheck-Quellen ausser `link_pruefen`/`ablage` auf feste Werte legen."""
    monkeypatch.setattr(
        mj, "_mailcheck_board", lambda: {"vorgaenge_gesamt": 1, "ohne_frist": 0}
    )
    monkeypatch.setattr(
        mj, "_mailcheck_referenzen", lambda: {"referenzen_ohne_ordner": 0}
    )
    monkeypatch.setattr(mj, "_mailcheck_anker", lambda: {"unverankert": 0})
    monkeypatch.setattr(mj, "_mailcheck_index_alter", lambda: 0)
    monkeypatch.setattr(mj, "_link_pruefen_vorgangsseiten", lambda: {})
    monkeypatch.setattr(
        mj, "_todo_direkt", lambda: {"geschlossen_7_tage": 0, "ohne_kopf_aktion": 0}
    )
    monkeypatch.setattr(mj, "_quelle_version", lambda: "test")
    if ablage is not None:
        monkeypatch.setattr(mj, "_mailcheck_ablage", ablage)


def test_should_ablage_bei_alle_genau_einmal_selbst_laufen_ohne_vorgabe(
    monkeypatch, tmp_path
):
    """`ablage_erledigt.py --pruefe` laeuft bei `--anwendung alle` genau einmal
    — nicht je Anwendung —, solange keine bereits erzeugte Ausgabe vorliegt."""
    aufrufe = {"n": 0}

    def gezaehlt() -> dict[str, int | None]:
        aufrufe["n"] += 1
        return {"posteingang_geschlossene_vorgaenge": 5}

    _mailcheck_grundmocks(monkeypatch, ablage=gezaehlt)

    zeilen = mj.schreiben(
        ["mailcheck", "todo"], "test-modell", tmp_path / "journal.jsonl", None
    )
    assert aufrufe["n"] == 1
    mailcheck = next(z for z in zeilen if z["anwendung"] == "mailcheck")
    assert mailcheck["kennzahlen"]["posteingang_geschlossene_vorgaenge"] == 5


def test_should_ablage_ausgabe_vorgegeben_den_eigenen_lauf_ueberspringen(
    monkeypatch, tmp_path
):
    """#3069: liegt die `--pruefe`-Ausgabe von `ablage_erledigt.py` schon vor
    (Makefile hat sie fuer den Melder bereits erzeugt), ruft messjournal den
    teuren Melder (gemessen 253s, 75 Index-Abfragen) NICHT ein zweites Mal
    auf — das war die eigentliche Ursache der 9,3-Minuten-Laufzeit."""
    aufrufe = {"n": 0}

    def nicht_erwartet() -> dict[str, int | None]:
        aufrufe["n"] += 1
        return {"posteingang_geschlossene_vorgaenge": 99}

    _mailcheck_grundmocks(monkeypatch, ablage=nicht_erwartet)

    text = (
        "ad: 3 Posteingangs-Mails gehoeren zu geschlossenen Vorgaengen\n"
        "Grundlage: Strang ueber die Konversation live, ..."
    )
    zeilen = mj.schreiben(
        ["mailcheck", "todo"],
        "test-modell",
        tmp_path / "journal.jsonl",
        None,
        ablage_text=text,
    )
    assert aufrufe["n"] == 0
    mailcheck = next(z for z in zeilen if z["anwendung"] == "mailcheck")
    assert mailcheck["kennzahlen"]["posteingang_geschlossene_vorgaenge"] == 3
