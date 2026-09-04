"""Drill fuer Ausgabefilter, Fingerabdruck und Lauf-Protokoll (#2813).

Der Filter ist die einzige technische Sicherung gegen "kein Wert in Log/Git/Chat"
(Kill-Gate-Zeile 3). Deshalb wird hier nicht nur geprueft, DASS er greift,
sondern auch, dass er beim Greifen **nicht selbst** das Fundstueck ausgibt — ein
Filter, der den Wert in die Fehlermeldung schreibt, verlagert das Leck nur.

Alle Attrappen tragen ``ATTRAPPE`` im Namen; die Muster-Praefixe stehen
zusammengesetzt (``"ghp" + "_"``), damit gitleaks diese Datei nicht als Fund
liest.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rotation import fingerprint, inventar  # noqa: E402
from rotation import log as rotlog  # noqa: E402

SCHLUESSEL = b"ATTRAPPE-hmac-schluessel-fuer-den-drill"

# Zusammengesetzt, damit die Muster hier nicht als echte Token gelesen werden.
GHP = "ghp" + "_" + "ATTRAPPExxxxxxxxxxxxxxxxxxxxxxxxxxxx"
OL = "ol" + "_api_" + "ATTRAPPEyyyyyyyyyyyyyy"
PEM = "-----" + "BEGIN" + " RSA PRIVATE KEY-----"


# --------------------------------------------------------------------------
# Ausgabefilter
# --------------------------------------------------------------------------
@pytest.mark.parametrize("text", [GHP, OL, PEM, "github" + "_pat_" + "ATTRAPPE"])
def test_should_catch_every_token_pattern(text):
    with pytest.raises(rotlog.WertGefunden):
        rotlog.filtere(f"irgendwo steht {text} mitten im Text")


def test_should_let_harmless_text_pass():
    assert rotlog.filtere("GENESOR_PROJECT_TOKEN in iilgmbh/risk-hub gesetzt")


def test_should_not_repeat_the_finding_in_the_message():
    """Ein Filter, der den Fund in die Meldung schreibt, verlagert das Leck."""
    with pytest.raises(rotlog.WertGefunden) as fehler:
        rotlog.filtere(GHP)
    assert GHP not in str(fehler.value)
    assert "github-pat-klassisch" in str(fehler.value)


def test_should_refuse_to_write_a_line_carrying_a_value(tmp_path):
    pfad = tmp_path / "rotation-log.jsonl"
    with pytest.raises(rotlog.WertGefunden):
        rotlog.schreibe({"lauf_id": "a", "hinweis": OL}, pfad)
    assert not pfad.exists(), "nichts geschrieben, wenn der Filter greift"


def test_should_find_a_value_in_an_existing_log(tmp_path):
    pfad = tmp_path / "rotation-log.jsonl"
    pfad.write_text('{"lauf_id": "a"}\n{"lauf_id": "b", "x": "%s"}\n' % OL, encoding="utf-8")
    befunde = rotlog.pruefe_datei(pfad)
    assert len(befunde) == 1 and ":2 —" in befunde[0]


def test_should_report_the_real_log_as_clean():
    assert rotlog.pruefe_datei() == []


# --------------------------------------------------------------------------
# Fingerabdruck
# --------------------------------------------------------------------------
def test_should_be_deterministic_and_16_hex():
    a = fingerprint.fingerabdruck(b"ATTRAPPE-1234", SCHLUESSEL)
    b = fingerprint.fingerabdruck(b"ATTRAPPE-1234", SCHLUESSEL)
    assert a == b and len(a) == 16 and all(c in "0123456789abcdef" for c in a)


def test_should_differ_for_a_different_value():
    assert fingerprint.fingerabdruck(b"ATTRAPPE-1234", SCHLUESSEL) != fingerprint.fingerabdruck(
        b"ATTRAPPE-5678", SCHLUESSEL
    )


def test_should_differ_for_a_different_key():
    """Das ist der Punkt von HMAC (MT-8): ohne den Werkzeug-Schluessel laesst
    sich der Fingerabdruck eines schwachen Werts nicht nachrechnen."""
    assert fingerprint.fingerabdruck(b"deploy", SCHLUESSEL) != fingerprint.fingerabdruck(
        b"deploy", b"ATTRAPPE-anderer-schluessel-fuer-den-drill"
    )


def test_should_never_contain_the_value(tmp_path):
    wert = b"ATTRAPPE-geheimer-wert-4711"
    abdruck = fingerprint.fingerabdruck(wert, SCHLUESSEL)
    pfad = tmp_path / "rotation-log.jsonl"
    rotlog.schreibe(
        {"lauf_id": "x", "fingerprint_prefix16": abdruck, "fingerprint_alg": fingerprint.ALGORITHMUS},
        pfad,
    )
    inhalt = pfad.read_text(encoding="utf-8")
    assert "ATTRAPPE-geheimer-wert-4711" not in inhalt
    assert abdruck in inhalt


def test_should_explain_how_to_create_a_missing_key(tmp_path):
    with pytest.raises(fingerprint.SchluesselFehlt, match="urandom"):
        fingerprint.lade_schluessel(tmp_path / "gibt-es-nicht")


def test_should_reject_a_too_short_key(tmp_path):
    pfad = tmp_path / "kurz"
    pfad.write_text("kurz\n")
    with pytest.raises(fingerprint.SchluesselFehlt, match="kuerzer"):
        fingerprint.lade_schluessel(pfad)


# --------------------------------------------------------------------------
# Log-Auswertung
# --------------------------------------------------------------------------
def test_should_pick_the_youngest_run_of_a_secret():
    zeilen = [
        {"secret": "A", "gestartet": "2026-01-01T00:00:00+00:00", "lauf_id": "alt"},
        {"secret": "A", "gestartet": "2026-06-01T00:00:00+00:00", "lauf_id": "neu"},
        {"secret": "B", "gestartet": "2026-09-01T00:00:00+00:00", "lauf_id": "andere"},
    ]
    assert rotlog.letzter_lauf("A", zeilen)["lauf_id"] == "neu"
    assert rotlog.letzter_lauf("C", zeilen) is None


def test_should_number_run_ids_within_a_day():
    zeilen = [{"lauf_id": "A-2026-09-04-1"}]
    assert rotlog.naechste_lauf_id("A", zeilen, "2026-09-04") == "A-2026-09-04-2"


def test_should_not_let_an_open_run_reset_the_clock():
    """Ein gescheiterter Lauf darf die Faelligkeit NICHT zuruecksetzen — sonst
    verschwindet ein Secret aus dem Melder, obwohl nichts belegt ist."""
    secret = inventar.Secret("shared", "A", {"rotation": "yearly"}, ())
    offen = {"status": "offen", "beendet": "2026-09-01T00:00:00+00:00"}
    fertig = {"status": "abgeschlossen", "beendet": "2026-09-01T00:00:00+00:00"}
    heute = date(2026, 9, 4)
    assert inventar.faellig_seit(secret, offen, heute) == 0
    assert inventar.faellig_seit(secret, fertig, heute) is None


def test_should_become_due_again_after_the_interval():
    secret = inventar.Secret("shared", "A", {"rotation": "quarterly"}, ())
    fertig = {"status": "abgeschlossen", "beendet": "2026-01-01T00:00:00+00:00"}
    assert inventar.faellig_seit(secret, fertig, date(2026, 9, 4)) > 0


def test_should_never_make_on_demand_due_on_its_own():
    secret = inventar.Secret("shared", "A", {"rotation": "on_demand"}, ())
    assert inventar.faellig_seit(secret, None, date(2026, 9, 4)) is None
