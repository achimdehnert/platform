"""Drill-Tests fuer Regel 2 / E18-Praezisierung ueber `gegenprobe_treffer`.

platform#3168 (Nachtrag zu KONZ-platform-051 R7): die freie gegenprobe kann
mit einer Zahl beginnen, die Kandidaten zaehlt statt der Absenz ("8
DateInput-Definitionen ...") — der Gegenpart las das bislang als Treffer und
widerlegte einen reproduzierten Datenverlust (apo-hub#110). Diese Tests
messen rot (vor dem Fix) und gruen (danach) fuer genau diesen Fall.

Ohne Netz: `frage` wird gemockt oder es wird gezeigt, dass es gar nicht
aufgerufen wird (Muster aus test_ux_falsifikator.py).
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ux_falsifikator as uf  # noqa: E402


# apo-hub#110: reproduzierter Datenverlust, faelschlich widerlegt, weil die
# gegenprobe mit "8 DateInput-Definitionen ..." begann (Kandidaten-Zahl, nicht
# Absenz-Zahl). gegenprobe_treffer=0 sagt strukturiert: 0 Treffer fuer format.
BEFUND_110 = {
    "klasse": "formular-verliert-eingabe",
    "severity": "fehler",
    "station": "Apotheke bearbeiten",
    "symptom": "Nach einer Fehleingabe sind alle Formularfelder leer statt "
    "die getippten Werte zu behalten.",
    "antwortkoerper": "HTTP 200, Formular neu gerendert, alle Felder leer",
    "gegenprobe": '8 DateInput-Definitionen in templates/apotheken/ -> 0 davon mit format="iso"',
    "referenz": "",
    "bekannt": False,
    "gegenprobe_treffer": 0,
}

# Echter Fehlbefund: Feld existiert nachweislich anderswo (3 Treffer) — Regel
# 2 soll hier greifen, deterministisch, ohne je das LLM zu fragen.
BEFUND_ECHTER_FEHLBEFUND = {
    "klasse": "feld-fehlt",
    "severity": "fehler",
    "station": "Apotheke anlegen",
    "symptom": "Feld 'Ansprechpartner' fehlt im Formular.",
    "antwortkoerper": "HTTP 200, Formular ohne Feld 'Ansprechpartner'",
    "gegenprobe": "grep -rn 'Ansprechpartner' templates/ -> 3 Treffer in anderen Formularen",
    "referenz": "",
    "bekannt": False,
    "gegenprobe_treffer": 3,
}


def _antwort(inhalt: str) -> dict:
    return {"choices": [{"message": {"content": inhalt}}]}


def _drei(*sprueche):
    antworten = iter(
        _antwort(json.dumps({"spruch": s, "begruendung": f"Regel X ({s})."}))
        for s in sprueche
    )
    return lambda *a, **k: next(antworten)


# --- Positivkontrolle: apo-hub#110 darf NICHT via Regel 2 widerlegt werden --


def test_should_not_trigger_regel2_when_treffer_is_zero():
    """Reiner Regel-2-Check: treffer=0 loest keine deterministische Widerlegung aus."""
    assert uf.regel2_deterministisch(BEFUND_110) is None


def test_should_reach_llm_path_end_to_end_when_treffer_is_zero(monkeypatch, capsys):
    """Integrationspfad: treffer=0 -> Regel 2 greift nicht, LLM entscheidet regulaer."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND_110)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "test")
    monkeypatch.setattr(
        uf, "frage", _drei("bestaetigt", "bestaetigt", "bestaetigt")
    )
    assert uf.main([]) == 0
    satz = json.loads(capsys.readouterr().out)
    assert satz["spruch"] == "bestaetigt"
    assert "hinweis" not in satz  # gegenprobe_treffer war gesetzt (0), kein R7-Hinweis


# --- Gegenprobe: echter Fehlbefund -> deterministisch widerlegt, ohne LLM ---


def test_should_refute_deterministically_without_llm_call_when_treffer_positive(
    monkeypatch, capsys
):
    aufrufe = []

    def zaehlend(*a, **k):
        aufrufe.append(1)
        pytest.fail("Regel 2 haette deterministisch entscheiden muessen, kein LLM-Aufruf")

    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps(BEFUND_ECHTER_FEHLBEFUND))
    )
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "test")
    monkeypatch.setattr(uf, "frage", zaehlend)

    assert uf.main([]) == 0
    satz = json.loads(capsys.readouterr().out)
    assert satz["spruch"] == "widerlegt"
    assert satz["laeufe"] == 0
    assert satz["einig"] is True
    assert len(aufrufe) == 0
    assert "gegenprobe_treffer" in satz["begruendung"] or "3" in satz["begruendung"]


def test_should_expose_deterministic_verdict_in_direct_call():
    satz = uf.regel2_deterministisch(BEFUND_ECHTER_FEHLBEFUND)
    assert satz is not None
    assert satz["spruch"] == "widerlegt"
    assert satz["laeufe"] == 0


# --- Abwaertskompatibilitaet: ohne gegenprobe_treffer bleibt der LLM-Pfad ---


def test_should_keep_llm_path_and_emit_r7_hinweis_when_field_missing(
    monkeypatch, capsys
):
    befund_ohne_feld = {k: v for k, v in BEFUND_110.items() if k != "gegenprobe_treffer"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(befund_ohne_feld)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "test")
    monkeypatch.setattr(uf, "frage", _drei("widerlegt", "widerlegt", "widerlegt"))

    assert uf.main([]) == 0
    satz = json.loads(capsys.readouterr().out)
    assert satz["spruch"] == "widerlegt"  # bisheriges (fehlbares) Verhalten bleibt
    assert satz["hinweis"] == uf.HINWEIS_R7


def test_should_treat_non_numeric_treffer_as_absent():
    """Ein kaputtes Feld darf nicht wie ein Treffer aussehen."""
    kaputt = {**BEFUND_ECHTER_FEHLBEFUND, "gegenprobe_treffer": "drei"}
    assert uf.regel2_deterministisch(kaputt) is None
