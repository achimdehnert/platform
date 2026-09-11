"""Gemeinsame Ablageform fuer Melder-Ergebnisse (platform#2944).

Geprueft wird die Invariante, an der alles haengt: ein Ergebnis, das fehlt,
kaputt ist oder zu alt, muss DASSELBE liefern wie kein Ergebnis — naemlich
nichts. Wer daraus "rot" macht, behauptet einen Mangel, den niemand gemessen hat.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import melder_ergebnis as me  # noqa: E402

JETZT = datetime(2026, 9, 7, 12, 0, 0, tzinfo=timezone.utc)


def test_should_roundtrip_a_fresh_result(tmp_path):
    p = tmp_path / "alarmweg.json"
    me.schreibe(p, "melder_x", [{"kanal": "a", "vorhanden": True}], gemessen_am=JETZT)
    gelesen = me.lies(p, jetzt=JETZT)
    assert gelesen is not None
    assert gelesen["melder"] == "melder_x"
    assert gelesen["ergebnis"] == [{"kanal": "a", "vorhanden": True}]
    assert gelesen["gemessen_am"].endswith("Z")


def test_should_return_none_for_a_stale_result(tmp_path):
    """Die Frische-Grenze ist der eigentliche Punkt der ganzen Huelle."""
    p = tmp_path / "alt.json"
    me.schreibe(p, "melder_x", [], gemessen_am=JETZT - timedelta(days=8))
    assert me.lies(p, jetzt=JETZT) is None
    # Gegenprobe: eine Stunde juenger als die Grenze wird sehr wohl gelesen.
    me.schreibe(
        p, "melder_x", [], gemessen_am=JETZT - timedelta(days=7) + timedelta(hours=1)
    )
    assert me.lies(p, jetzt=JETZT) is not None


def test_should_return_none_for_missing_broken_or_foreign_file(tmp_path):
    assert me.lies(tmp_path / "gibtsnicht.json", jetzt=JETZT) is None
    kaputt = tmp_path / "kaputt.json"
    kaputt.write_text("{kein json", encoding="utf-8")
    assert me.lies(kaputt, jetzt=JETZT) is None
    fremd = tmp_path / "fremd.json"
    fremd.write_text(json.dumps({"schema": "etwas-anderes/9"}), encoding="utf-8")
    assert me.lies(fremd, jetzt=JETZT) is None
    ohne_datum = tmp_path / "ohne.json"
    ohne_datum.write_text(json.dumps({"schema": me.SCHEMA}), encoding="utf-8")
    assert me.lies(ohne_datum, jetzt=JETZT) is None


def test_should_treat_naive_timestamps_as_utc(tmp_path):
    """Ein Zeitstempel ohne Zone darf nicht zum Absturz fuehren."""
    p = tmp_path / "naiv.json"
    p.write_text(
        json.dumps(
            {"schema": me.SCHEMA, "gemessen_am": "2026-09-07T11:00:00", "ergebnis": []}
        ),
        encoding="utf-8",
    )
    assert me.lies(p, jetzt=JETZT) is not None


def test_should_create_missing_parent_directories(tmp_path):
    p = tmp_path / "tief" / "drin" / "x.json"
    me.schreibe(p, "melder_x", [], gemessen_am=JETZT)
    assert p.exists()


# --- Der Fehler, den erst die erste echte Verwendung zeigte (platform#2944) ---


def test_should_pfad_als_zeichenkette_annehmen(tmp_path):
    """Bis zur Verdrahtung der Melder reichten alle Tests `Path`-Objekte herein.

    Der erste Aufruf aus einem Shell-Skript uebergab eine Zeichenkette, und
    ``lies()`` brach mit ``AttributeError: 'str' object has no attribute
    'read_text'`` ab — eine Funktion, die gebaut, getestet und gruen war, und beim
    ersten realistischen Gebrauch scheiterte. Genau die Klasse, gegen die das Gate
    `built-but-never-called` gebaut ist.
    """
    ziel = tmp_path / "unterordner" / "ergebnis.json"
    me.schreibe(str(ziel), "probe", {"a": 1})
    assert ziel.exists()
    assert me.lies(str(ziel))["ergebnis"] == {"a": 1}
    assert me.lies(ziel)["ergebnis"] == {"a": 1}


def test_should_bei_unsinnigem_pfad_none_liefern(tmp_path):
    """Gegenprobe: ein Wert, der gar kein Pfad ist, gibt `None` statt zu werfen."""
    assert me.lies(None) is None
    assert me.lies(12345) is None
