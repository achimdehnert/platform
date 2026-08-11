"""Tests fuer die Befund-Leseflaeche (platform#1908 Etappe 1).

Die Kriterien L1-L4 sind hier einzeln als Test verankert, nicht als Prosa im PR.
Der teuerste Fehlermodus ist derselbe wie beim Original-Problem: das Werkzeug
laeuft, meldet aber nichts Sichtbares — ein gruener Test ueber einer stummen
Ausgabe waere wertlos. Deshalb prueft jeder Fall die AUSGABE, nicht nur den
Rueckgabewert.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "hooks" / "befund_leseflaeche.py"


@pytest.fixture()
def lf(tmp_path, monkeypatch):
    """Modul mit isoliertem State-Pfad laden (kein Zugriff auf ~/.claude)."""
    monkeypatch.setenv("LESEFLAECHE_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("LESEFLAECHE_FRIST_TAGE", "2")
    spec = importlib.util.spec_from_file_location("befund_leseflaeche", _SRC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _report(*schluessel: str) -> dict:
    return {
        "schema": 1,
        "geprueft": len(schluessel),
        "befunde": [
            {
                "schluessel": s,
                "klasse": "DISKREPANZ",
                "detail": "Issue geschlossen",
                "zeile_nr": 120,
                "zeile": "2. **irgendein Punkt**",
            }
            for s in schluessel
        ],
    }


def _schreibe(tmp_path, report: dict) -> pathlib.Path:
    p = tmp_path / "report.json"
    p.write_text(json.dumps(report), encoding="utf-8")
    return p


# --- L1: Auffindbarkeit ------------------------------------------------------


def test_should_eingesaeter_befund_in_der_ausgabe_erscheinen(lf, tmp_path, capsys):
    """L3-Beweis in seiner Grundform: ein eingesaeter Befund MUSS sichtbar werden.

    Das ist der Test, den das Original-Problem nie hatte — der Melder arbeitete,
    aber niemand pruefte je, ob sein Ergebnis irgendwo ankommt.
    """
    rc = lf.main(["--report", str(_schreibe(tmp_path, _report("achimdehnert/platform#1549")))])
    assert rc == 0
    assert "achimdehnert/platform#1549" in capsys.readouterr().out


def test_should_ohne_befunde_still_bleiben(lf, tmp_path, capsys):
    """Kein Rauschen, wenn nichts offen ist — sonst wird die Flaeche selbst ignoriert."""
    lf.main(["--report", str(_schreibe(tmp_path, _report()))])
    assert capsys.readouterr().out.strip() == ""


# --- L2: Dedup + Zustand -----------------------------------------------------


def test_should_denselben_befund_nicht_doppelt_listen(lf, tmp_path, capsys):
    """Fuenf Meldungen desselben Befunds sind EIN Eintrag, nicht fuenf Zeilen."""
    p = _schreibe(tmp_path, _report("a/b#1"))
    for _ in range(5):
        lf.main(["--report", str(p)])
    out = capsys.readouterr().out
    assert out.count("a/b#1") == 5  # je Lauf einmal gerendert …
    zustand = json.loads(lf.STATE_PFAD.read_text())
    assert list(zustand["befunde"]) == ["a/b#1"]  # … aber nur EIN Eintrag im Zustand


def test_should_behobenen_befund_entfernen(lf, tmp_path, capsys):
    """Ein Befund, der im neuen Report fehlt, ist behoben und verschwindet."""
    lf.main(["--report", str(_schreibe(tmp_path, _report("a/b#1", "a/b#2")))])
    capsys.readouterr()
    lf.main(["--report", str(_schreibe(tmp_path, _report("a/b#2")))])
    out = capsys.readouterr().out
    assert "a/b#2" in out
    assert "a/b#1" not in out


def test_should_alter_und_wiederholung_ausweisen(lf, tmp_path, capsys):
    """Die Wiederholungszahl ist die eigentliche Information: wie lange sah niemand hin."""
    lf.main(["--report", str(_schreibe(tmp_path, _report("a/b#1")))])
    capsys.readouterr()
    zustand = json.loads(lf.STATE_PFAD.read_text())
    alt = datetime.now(timezone.utc) - timedelta(days=5)
    zustand["befunde"]["a/b#1"]["erstmals"] = alt.replace(microsecond=0).isoformat()
    zustand["befunde"]["a/b#1"]["wiederholungen"] = 5
    lf.STATE_PFAD.write_text(json.dumps(zustand), encoding="utf-8")
    lf.main([])
    out = capsys.readouterr().out
    assert "seit 5 Tag(en)" in out
    assert "5x gemeldet" in out


# --- L3: Sicht-Frist + Eskalation -------------------------------------------


def test_should_ueberfaelligen_befund_eskalieren(lf, tmp_path, capsys):
    lf.main(["--report", str(_schreibe(tmp_path, _report("a/b#1")))])
    capsys.readouterr()
    zustand = json.loads(lf.STATE_PFAD.read_text())
    alt = datetime.now(timezone.utc) - timedelta(days=4)
    zustand["befunde"]["a/b#1"]["erstmals"] = alt.replace(microsecond=0).isoformat()
    lf.STATE_PFAD.write_text(json.dumps(zustand), encoding="utf-8")
    lf.main([])
    out = capsys.readouterr().out
    assert "ueber der Sicht-Frist" in out
    assert "⏰" in out


def test_should_frischen_befund_nicht_eskalieren(lf, tmp_path, capsys):
    """Gegenprobe — sonst eskaliert alles und die Markierung sagt nichts mehr."""
    lf.main(["--report", str(_schreibe(tmp_path, _report("a/b#1")))])
    out = capsys.readouterr().out
    assert "ueber der Sicht-Frist" not in out
    assert "⏰" not in out


def test_should_bestaetigten_befund_nicht_mehr_zeigen(lf, tmp_path, capsys):
    """Gesehen-Status: nach Bestaetigung verschwindet der Befund aus der Flaeche."""
    p = _schreibe(tmp_path, _report("a/b#1"))
    lf.main(["--report", str(p)])
    capsys.readouterr()
    lf.main(["--alle-gesehen"])
    capsys.readouterr()
    lf.main(["--report", str(p)])
    assert "a/b#1" not in capsys.readouterr().out


# --- L4: Exit-Kriterium ------------------------------------------------------


def test_should_exit_kriterium_bei_ueberfaelligem_befund_scheitern(lf, tmp_path, capsys):
    lf.main(["--report", str(_schreibe(tmp_path, _report("a/b#1")))])
    capsys.readouterr()
    zustand = json.loads(lf.STATE_PFAD.read_text())
    alt = datetime.now(timezone.utc) - timedelta(days=9)
    zustand["befunde"]["a/b#1"]["erstmals"] = alt.replace(microsecond=0).isoformat()
    lf.STATE_PFAD.write_text(json.dumps(zustand), encoding="utf-8")
    assert lf.main(["--exit-kriterium"]) == 1
    assert "NICHT erfuellt" in capsys.readouterr().out


def test_should_exit_kriterium_ohne_ueberfaellige_erfuellen(lf, tmp_path, capsys):
    lf.main(["--report", str(_schreibe(tmp_path, _report("a/b#1")))])
    capsys.readouterr()
    assert lf.main(["--exit-kriterium"]) == 0
    assert "L4 erfuellt" in capsys.readouterr().out


# --- Fail-open ---------------------------------------------------------------


def test_should_bei_kaputtem_report_still_scheitern(lf, tmp_path, capsys):
    """Ein Hook, der den Sitzungsstart kaputtmacht, wird abgeschaltet — dann meldet
    er nie wieder etwas. Genau der Fehlermodus, gegen den dieses Werkzeug existiert."""
    p = tmp_path / "kaputt.json"
    p.write_text("{kein json", encoding="utf-8")
    assert lf.main(["--report", str(p)]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_should_bei_fehlendem_state_nicht_abstuerzen(lf, capsys):
    assert lf.main(["--exit-kriterium"]) == 0
