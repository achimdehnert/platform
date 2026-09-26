"""Tests für tools/mail_agent/verfallsmelder.py — K3 "Verfallsignale" (#3015).

Alles offline über `--eingabe` (feste Werte statt Postfach/systemctl/Netz).
Kein Test liest das echte Ledger, Journal oder ruft ein Live-Kommando auf.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKRIPT = Path(__file__).resolve().parents[1] / "mail_agent" / "verfallsmelder.py"

JETZT = datetime.now(timezone.utc).isoformat(timespec="seconds")


def _lauf(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _signal(daten: dict, anwendung: str, name: str) -> dict:
    treffer = [
        s
        for s in daten["signale"]
        if s["anwendung"] == anwendung and s["signal"] == name
    ]
    assert treffer, f"Signal {anwendung}/{name} fehlt in {daten['signale']}"
    return treffer[0]


def test_should_warn_and_block_when_index_alter_reisst_die_schwelle():
    """Positivkontrolle: die Schwelle wird kuenstlich gerissen — der Melder muss feuern."""
    eingabe = json.dumps(
        {
            "journal": [
                {
                    "anwendung": "mailcheck",
                    "zeit": JETZT,
                    "kennzahlen": {"index_alter_tage": 2.0},
                }
            ]
        }
    )
    ergebnis = _lauf(
        "--anwendung", "mailcheck", "--json", "--eingabe", eingabe, "--block"
    )
    daten = json.loads(ergebnis.stdout)
    signal = _signal(daten, "mailcheck", "Index-Alter")
    assert signal["zustand"] == "WARNUNG"
    assert daten["warnungen"] >= 1
    assert ergebnis.returncode == 1


def test_should_report_zero_warnungen_when_all_values_are_within_thresholds():
    eingabe = json.dumps(
        {
            "journal": [
                {
                    "anwendung": "mailcheck",
                    "zeit": JETZT,
                    "kennzahlen": {
                        "index_alter_tage": 0.5,
                        "ohne_frist": 0,
                        "vorgangsseiten_tot": 0,
                    },
                },
                {
                    "anwendung": "todo",
                    "zeit": JETZT,
                    "kennzahlen": {"mail_links_tot": 0, "ohne_kopf_aktion": 0},
                },
            ]
        }
    )
    ergebnis = _lauf("--json", "--eingabe", eingabe, "--block")
    daten = json.loads(ergebnis.stdout)
    assert daten["warnungen"] == 0
    assert ergebnis.returncode == 0


def test_should_accept_skill_kopie_when_quelle_commit_is_an_ancestor():
    """Merge-Commit auf der Kopie, Datei-Commit in der Quelle: gleicher Stand, kein Alarm."""
    eingabe = json.dumps(
        {
            "journal": [],
            "skill_kopie_commit": "1c0e20978c23",
            "quelle_commit": "d868fa66d3a876239ebda87afafdfd8faeae885b",
            "quelle_ist_vorfahr": True,
        }
    )
    ergebnis = _lauf("--anwendung", "mailcheck", "--json", "--eingabe", eingabe)
    daten = json.loads(ergebnis.stdout)
    signal = _signal(daten, "mailcheck", "Skill-Kopie")
    assert signal["zustand"] == "ok"


def test_should_warn_when_skill_kopie_commit_differs_from_quelle():
    eingabe = json.dumps(
        {
            "journal": [],
            "skill_kopie_commit": "1c0e20978c23",
            "quelle_commit": "d868fa66d3a876239ebda87afafdfd8faeae885b",
        }
    )
    ergebnis = _lauf("--anwendung", "mailcheck", "--json", "--eingabe", eingabe)
    daten = json.loads(ergebnis.stdout)
    signal = _signal(daten, "mailcheck", "Skill-Kopie")
    assert signal["zustand"] == "WARNUNG"
    assert "aelter" in signal["hinweis"]


def test_should_warn_when_dienst_start_liegt_vor_dem_code_commit():
    eingabe = json.dumps(
        {
            "journal": [],
            "dienst_start": "2026-09-01T00:00:00+00:00",
            "code_commit_zeit": "2026-09-05T00:00:00+00:00",
        }
    )
    ergebnis = _lauf("--anwendung", "todo", "--json", "--eingabe", eingabe)
    daten = json.loads(ergebnis.stdout)
    signal = _signal(daten, "todo", "Dienst-Code (todo-board)")
    assert signal["zustand"] == "WARNUNG"
    assert "altem Code" in signal["hinweis"]


def test_should_mark_missing_dienst_start_as_not_checkable_without_warning():
    eingabe = json.dumps({"journal": []})
    ergebnis = _lauf("--anwendung", "todo", "--json", "--eingabe", eingabe)
    daten = json.loads(ergebnis.stdout)
    signal = _signal(daten, "todo", "Dienst-Code (todo-board)")
    assert signal["zustand"] == "nicht pruefbar"
    assert daten["warnungen"] == 0


def test_should_tip_zustand_when_schwelle_override_moves_it():
    eingabe = json.dumps(
        {
            "journal": [
                {
                    "anwendung": "mailcheck",
                    "zeit": JETZT,
                    "kennzahlen": {"ohne_frist": 1},
                }
            ]
        }
    )
    ohne_override = json.loads(
        _lauf("--anwendung", "mailcheck", "--json", "--eingabe", eingabe).stdout
    )
    mit_override = json.loads(
        _lauf(
            "--anwendung",
            "mailcheck",
            "--json",
            "--eingabe",
            eingabe,
            "--schwellen",
            json.dumps({"mailcheck.ohne_frist": 5}),
        ).stdout
    )
    assert _signal(ohne_override, "mailcheck", "Ohne Frist")["zustand"] == "WARNUNG"
    assert _signal(mit_override, "mailcheck", "Ohne Frist")["zustand"] == "ok"


def test_should_never_print_an_at_sign():
    eingabe = json.dumps(
        {
            "journal": [
                {
                    "anwendung": "mailcheck",
                    "zeit": JETZT,
                    "kennzahlen": {"index_alter_tage": 2.0, "ohne_frist": 1},
                }
            ]
        }
    )
    ergebnis = _lauf("--anwendung", "mailcheck", "--eingabe", eingabe)
    assert "@" not in ergebnis.stdout


# --- auftragsraum (KONZ-platform-059, #3079) -----------------------------


def _vor(stunden: int = 0, tage: int = 0) -> str:
    zeitpunkt = datetime.now(timezone.utc) - timedelta(hours=stunden, days=tage)
    return zeitpunkt.isoformat(timespec="seconds").replace("+00:00", "Z")


def test_should_auftragsraum_leeres_journal_nicht_pruefbar_sein_ohne_warnung():
    ergebnis = _lauf(
        "--anwendung",
        "auftragsraum",
        "--json",
        "--eingabe",
        json.dumps({"auftragsraum_journal": []}),
    )
    daten = json.loads(ergebnis.stdout)
    for name in (
        "Nachricht ohne Bearbeitung",
        "Korrektur ohne Artefakt",
        "Journal-Alter (Raum still)",
    ):
        assert _signal(daten, "auftragsraum", name)["zustand"] == "nicht pruefbar"
    assert daten["warnungen"] == 0
    assert ergebnis.returncode == 0


def test_should_auftragsraum_nachricht_ohne_bearbeitung_ueber_24h_warnen():
    eingabe = json.dumps(
        {
            "auftragsraum_journal": [
                {
                    "zeit": _vor(stunden=48),
                    "klasse": "kurzbefehl",
                    "korrektur": False,
                    "artefakt": None,
                    "bearbeitet_am": None,
                }
            ]
        }
    )
    ergebnis = _lauf(
        "--anwendung", "auftragsraum", "--json", "--eingabe", eingabe, "--block"
    )
    daten = json.loads(ergebnis.stdout)
    assert _signal(daten, "auftragsraum", "Nachricht ohne Bearbeitung")["zustand"] == (
        "WARNUNG"
    )
    assert ergebnis.returncode == 1


def test_should_auftragsraum_korrektur_ohne_artefakt_ueber_24h_warnen():
    eingabe = json.dumps(
        {
            "auftragsraum_journal": [
                {
                    "zeit": _vor(stunden=25),
                    "klasse": "korrektur",
                    "korrektur": True,
                    "artefakt": None,
                    "bearbeitet_am": None,
                }
            ]
        }
    )
    daten = json.loads(
        _lauf("--anwendung", "auftragsraum", "--json", "--eingabe", eingabe).stdout
    )
    assert _signal(daten, "auftragsraum", "Korrektur ohne Artefakt")["zustand"] == (
        "WARNUNG"
    )


def test_should_auftragsraum_journal_alter_nur_hinweis_nie_warnung_nie_block():
    eingabe = json.dumps(
        {
            "auftragsraum_journal": [
                {
                    "zeit": _vor(tage=9),
                    "klasse": "notiz",
                    "korrektur": False,
                    "artefakt": None,
                    "bearbeitet_am": _vor(tage=9),
                }
            ]
        }
    )
    ergebnis = _lauf(
        "--anwendung", "auftragsraum", "--json", "--eingabe", eingabe, "--block"
    )
    daten = json.loads(ergebnis.stdout)
    assert _signal(daten, "auftragsraum", "Journal-Alter (Raum still)")["zustand"] == (
        "HINWEIS"
    )
    assert daten["warnungen"] == 0
    assert ergebnis.returncode == 0


# --- sevdesk (#3102) --------------------------------------------------------


def test_should_sevdesk_warn_when_no_run_since_more_than_35_days():
    """Positivkontrolle: kein Lauf seit > 35 Tagen muss WARNUNG sein (nicht
    HINWEIS wie bei auftragsraum — ein ausbleibender Rechnungslauf ist ein
    Fehler, kein gewolltes Schweigen)."""
    eingabe = json.dumps(
        {
            "journal": [
                {
                    "anwendung": "sevdesk",
                    "zeit": _vor(tage=40),
                    "kennzahlen": {"entwuerfe_angelegt": 3},
                }
            ]
        }
    )
    ergebnis = _lauf(
        "--anwendung", "sevdesk", "--json", "--eingabe", eingabe, "--block"
    )
    daten = json.loads(ergebnis.stdout)
    signal = _signal(daten, "sevdesk", "Journal-Alter")
    assert signal["zustand"] == "WARNUNG"
    assert ergebnis.returncode == 1


def test_should_sevdesk_be_ok_when_run_within_35_days():
    eingabe = json.dumps(
        {
            "journal": [
                {
                    "anwendung": "sevdesk",
                    "zeit": _vor(tage=2),
                    "kennzahlen": {"entwuerfe_angelegt": 3},
                }
            ]
        }
    )
    ergebnis = _lauf(
        "--anwendung", "sevdesk", "--json", "--eingabe", eingabe, "--block"
    )
    daten = json.loads(ergebnis.stdout)
    assert _signal(daten, "sevdesk", "Journal-Alter")["zustand"] == "ok"
    assert ergebnis.returncode == 0


def test_should_sevdesk_leeres_journal_nicht_pruefbar_sein_ohne_warnung():
    eingabe = json.dumps({"journal": []})
    ergebnis = _lauf(
        "--anwendung", "sevdesk", "--json", "--eingabe", eingabe, "--block"
    )
    daten = json.loads(ergebnis.stdout)
    assert _signal(daten, "sevdesk", "Journal-Alter")["zustand"] == "nicht pruefbar"
    assert daten["warnungen"] == 0
    assert ergebnis.returncode == 0
