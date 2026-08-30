"""Drill fuer tools/kennzahl_verfall.py — markierte Kennzahlen nachrechnen.

Zwei Tests fixieren Fehler, die beim Bau real auftraten:
`test_should_allow_counting_builtins_in_expressions` — der erste Anlauf sperrte
ALLE Builtins in der eval-Umgebung und damit `sum`/`len`; jede Kennzahl meldete
"nicht berechenbar", der Schutzwall hatte das Werkzeug erledigt.
`test_should_not_match_a_number_far_from_the_marker` — ohne Abstandsgrenze faengt
der Marker die naechstbeste Zahl im Dokument ein.

Run: `python3 -m pytest tools/tests/test_kennzahl_verfall.py -q`
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "kennzahl_verfall.py"
_spec = importlib.util.spec_from_file_location("kennzahl_verfall", _QUELLE)
kv = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(kv)

_KATALOG = {
    "gate-rueckfaellig": {"name": "gate-rueckfaellig", "werkzeug": [], "ausdruck": ""}
}


def test_should_find_a_marked_number():
    text = "Prio 1: <!--kz:gate-rueckfaellig-->7 von 20 Gates."

    assert kv.finde_marker(text) == [("gate-rueckfaellig", "7", 8)]


def test_should_look_through_markdown_emphasis():
    """`**7**` ist derselbe Wert wie `7` — Auszeichnung darf nicht blockieren."""
    text = "Es sind <!--kz:gate-rueckfaellig--> **7** Stueck."

    assert kv.finde_marker(text)[0][1] == "7"


def test_should_not_match_a_number_far_from_the_marker():
    """Ohne Abstandsgrenze faengt der Marker irgendeine Zahl weiter hinten ein."""
    text = "<!--kz:gate-rueckfaellig-->" + "x" * 60 + "42"

    assert kv.finde_marker(text) == []


def test_should_report_a_stale_number(tmp_path):
    datei = tmp_path / "doc.md"
    datei.write_text("Stand: <!--kz:gate-rueckfaellig-->7 Gates.", encoding="utf-8")

    befunde = kv.pruefe_datei(str(datei), _KATALOG, {"gate-rueckfaellig": 5.0})

    assert [b["art"] for b in befunde] == ["veraltet"]
    assert befunde[0]["im_dokument"] == "7"
    assert befunde[0]["aktuell"] == 5.0


def test_should_stay_silent_when_the_number_is_current(tmp_path):
    datei = tmp_path / "doc.md"
    datei.write_text("<!--kz:gate-rueckfaellig-->5 Gates.", encoding="utf-8")

    assert kv.pruefe_datei(str(datei), _KATALOG, {"gate-rueckfaellig": 5.0}) == []


def test_should_not_call_an_unavailable_value_correct(tmp_path):
    """Nicht berechenbar ist KEIN gruener Zustand — es muss sichtbar bleiben."""
    datei = tmp_path / "doc.md"
    datei.write_text("<!--kz:gate-rueckfaellig-->7 Gates.", encoding="utf-8")

    befunde = kv.pruefe_datei(str(datei), _KATALOG, {"gate-rueckfaellig": None})

    assert [b["art"] for b in befunde] == ["nicht-berechenbar"]


def test_should_flag_a_marker_missing_from_the_catalogue(tmp_path):
    datei = tmp_path / "doc.md"
    datei.write_text("<!--kz:gibt-es-nicht-->3", encoding="utf-8")

    assert [b["art"] for b in kv.pruefe_datei(str(datei), _KATALOG, {})] == [
        "unbekannt"
    ]


def test_should_allow_counting_builtins_in_expressions(tmp_path):
    """`sum` und `len` muessen im Ausdruck verfuegbar sein — sonst ist alles blind."""
    werkzeug = tmp_path / "werkzeug.py"
    werkzeug.write_text(
        "import json; print(json.dumps({'gates':[{'u':'A'},{'u':'A'},{'u':'B'}]}))",
        encoding="utf-8",
    )
    import sys

    kennzahl = {
        "werkzeug": [sys.executable, str(werkzeug)],
        "ausdruck": "sum(1 for g in d['gates'] if g['u'] == 'A')",
    }

    assert kv.berechne(kennzahl, cwd=str(tmp_path)) == 2.0


def test_should_write_current_values_back(tmp_path):
    datei = tmp_path / "doc.md"
    datei.write_text(
        "Es sind <!--kz:gate-rueckfaellig-->**7** Gates.", encoding="utf-8"
    )

    geaendert = kv.setze(str(datei), _KATALOG, {"gate-rueckfaellig": 5.0})

    assert geaendert == 1
    assert "**5**" in datei.read_text(encoding="utf-8")
    assert "<!--kz:gate-rueckfaellig-->" in datei.read_text(encoding="utf-8"), (
        "Marker muss bleiben"
    )


def test_should_read_the_catalogue(tmp_path):
    katalog = tmp_path / "k.json"
    katalog.write_text(
        json.dumps({"kennzahlen": [{"name": "a", "werkzeug": [], "ausdruck": "1"}]}),
        encoding="utf-8",
    )

    assert list(kv.lade_katalog(str(katalog))) == ["a"]
