"""Tests für tools/mail_agent/messjournal.py — K2 "Selbstmessung" (#3015).

Alles offline über `--eingabe` (feste Werte statt echter Kommandos) und
`--journal tmp_path` (keine Beruehrung von ~/.claude/mail-messjournal.jsonl).
Kein Test liest das echte Ledger oder ruft ein Mail-Kommando auf.
"""

from __future__ import annotations

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
