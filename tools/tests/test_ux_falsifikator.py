"""Tests fuer tools/ux_falsifikator.py (KONZ-051 Stufe 1b).

Ohne Netz. Der eine Weg, der Netz braucht (`frage`), wird ueber `lies_spruch`
und ueber den Fehlerpfad in `main` abgedeckt — nicht gemockt-und-deshalb-blind:
`lies_spruch` bekommt echte Anbieter-Antwortformen, keine Attrappe.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ux_falsifikator as uf  # noqa: E402


BEFUND = {
    "klasse": "nicht-begehbar",
    "severity": "fehler",
    "station": "4 Angebotsentwurf",
    "symptom": "Station nur ueber getippte URL erreichbar.",
    "antwortkoerper": "HTTP 200 unter getippter URL",
    "gegenprobe": "grep -rn 'angebote:review' templates/ apps/ -> 0 Treffer",
    "referenz": "",
    "bekannt": False,
}


def test_should_include_every_evidence_field_in_prompt():
    block = uf.evidenz_block(BEFUND)
    for feld in (
        "klasse",
        "severity",
        "station",
        "symptom",
        "antwortkoerper",
        "gegenprobe",
        "referenz",
        "bekannt",
    ):
        assert f"{feld}:" in block, f"{feld} fehlt im Prompt"
    assert "getippte URL" in block


def test_should_render_bekannt_as_boolean_literal():
    assert "bekannt: true" in uf.evidenz_block({**BEFUND, "bekannt": True})
    assert "bekannt: false" in uf.evidenz_block({**BEFUND, "bekannt": False})


@pytest.mark.parametrize("feld", uf.VERBOTENE_FELDER)
def test_should_refuse_image_fields_e17(feld):
    with pytest.raises(SystemExit) as exc:
        uf.pruefe_eingabe({**BEFUND, feld: "/tmp/screen.png"})
    assert "E17" in str(exc.value)


def test_should_accept_finding_without_image_fields():
    uf.pruefe_eingabe(BEFUND)  # wirft nicht


def _antwort(inhalt: str) -> dict:
    """Antwortform von Groq/OpenAI-kompatiblen Endpunkten."""
    return {"choices": [{"message": {"content": inhalt}}]}


def test_should_read_valid_verdict():
    satz = uf.lies_spruch(
        _antwort('{"spruch": "widerlegt", "begruendung": "Regel 2 greift."}')
    )
    assert satz == {"spruch": "widerlegt", "begruendung": "Regel 2 greift."}


def test_should_downgrade_unknown_verdict_to_unklar():
    satz = uf.lies_spruch(_antwort('{"spruch": "sieht gut aus", "begruendung": "x"}'))
    assert satz["spruch"] == "unklar"
    assert "sieht gut aus" in satz["begruendung"]


def test_should_cap_overlong_reason():
    lang = "x" * 900
    satz = uf.lies_spruch(
        _antwort(json.dumps({"spruch": "bestaetigt", "begruendung": lang}))
    )
    assert len(satz["begruendung"]) == 400


def test_should_skip_without_asking_on_real_data_e17(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND)))
    monkeypatch.setattr(
        uf, "frage", lambda *a, **k: pytest.fail("E17: nicht fragen bei Echtdaten")
    )
    assert uf.main(["--echtdaten"]) == 0
    satz = json.loads(capsys.readouterr().out)
    assert satz["spruch"] == "uebersprungen"


def test_should_skip_when_no_key_present(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "")
    monkeypatch.setattr(
        uf, "frage", lambda *a, **k: pytest.fail("ohne Schluessel nicht fragen")
    )
    assert uf.main([]) == 0
    assert json.loads(capsys.readouterr().out)["spruch"] == "uebersprungen"


def test_should_exit_zero_on_widerlegt_e16(monkeypatch, capsys):
    """E16: der Spruch filtert nicht — er darf nie als Gate wirken."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "test")
    monkeypatch.setattr(
        uf,
        "frage",
        lambda *a, **k: _antwort('{"spruch":"widerlegt","begruendung":"Regel 1."}'),
    )
    assert uf.main([]) == 0
    assert json.loads(capsys.readouterr().out)["spruch"] == "widerlegt"


def test_should_report_unreachable_provider_as_unklar_not_bestaetigt(
    monkeypatch, capsys
):
    """Ein Fetch-Fehler ist kein gruener Zustand."""

    def kaputt(*a, **k):
        raise OSError("connection reset")

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "test")
    monkeypatch.setattr(uf, "frage", kaputt)
    assert uf.main([]) == 0
    satz = json.loads(capsys.readouterr().out)
    assert satz["spruch"] == "unklar"
    assert "connection reset" in satz["begruendung"]


def test_should_send_user_agent_because_cloudflare_blocks_urllib_default():
    """403/1010 kam von der urllib-Vorgabe, nicht vom Schluessel (2026-08-30)."""
    gesehen = {}

    class Antwort:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"{\\"spruch\\":\\"bestaetigt\\",\\"begruendung\\":\\"Regel 6.\\"}"}}]}'

    def fake_urlopen(req, timeout=None):
        gesehen.update(req.headers)
        return Antwort()

    import urllib.request

    orig = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        uf.frage(BEFUND, "test")
    finally:
        urllib.request.urlopen = orig

    # urllib normalisiert Header-Namen auf Kapitalisierung der ersten Buchstaben
    assert gesehen.get("User-agent") == uf.KENNUNG


# --- Option B aus platform#2489: Streuung offenlegen (R9) -------------------


def _drei(*sprueche):
    """Erzeugt eine Folge von Anbieter-Antworten fuer aufeinanderfolgende Aufrufe."""
    antworten = iter(
        _antwort(json.dumps({"spruch": s, "begruendung": f"Regel X ({s})."}))
        for s in sprueche
    )
    return lambda *a, **k: next(antworten)


def test_should_ask_three_times_by_default_because_one_call_is_a_throw():
    """R9: ein Aufruf ist keine Messung — die Vorgabe fragt dreimal."""
    aufrufe = []
    monkey = _drei("bestaetigt", "bestaetigt", "bestaetigt")

    def zaehlend(*a, **k):
        aufrufe.append(1)
        return monkey()

    import io as _io

    orig_stdin = sys.stdin
    sys.stdin = _io.StringIO(json.dumps(BEFUND))
    orig_key, orig_frage = uf.schluessel_lesen, uf.frage
    uf.schluessel_lesen, uf.frage = (lambda: "test"), zaehlend
    try:
        assert uf.main([]) == 0
    finally:
        sys.stdin, uf.schluessel_lesen, uf.frage = orig_stdin, orig_key, orig_frage
    assert len(aufrufe) == uf.LAEUFE == 3


def test_should_expose_disagreement_instead_of_hiding_it(monkeypatch, capsys):
    """Zwei zu eins ist eine Mehrheit — und muss als uneinig sichtbar bleiben."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "test")
    monkeypatch.setattr(uf, "frage", _drei("bestaetigt", "unklar", "bestaetigt"))
    assert uf.main([]) == 0
    satz = json.loads(capsys.readouterr().out)
    assert satz["spruch"] == "bestaetigt"
    assert satz["einig"] is False
    assert satz["sprueche"] == ["bestaetigt", "unklar", "bestaetigt"]
    assert satz["laeufe"] == 3


def test_should_mark_unanimous_verdict_as_einig(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "test")
    monkeypatch.setattr(uf, "frage", _drei("widerlegt", "widerlegt", "widerlegt"))
    assert uf.main([]) == 0
    satz = json.loads(capsys.readouterr().out)
    assert satz["spruch"] == "widerlegt"
    assert satz["einig"] is True


def test_should_return_unklar_when_all_three_verdicts_differ(monkeypatch, capsys):
    """Ohne Mehrheit gibt es kein Urteil — auch keins, das zufaellig zuerst kam."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "test")
    monkeypatch.setattr(uf, "frage", _drei("bestaetigt", "widerlegt", "unklar"))
    assert uf.main([]) == 0
    satz = json.loads(capsys.readouterr().out)
    assert satz["spruch"] == "unklar"
    assert satz["einig"] is False
    assert "Keine Mehrheit" in satz["begruendung"]


def test_should_keep_exit_zero_when_majority_is_widerlegt_e16(monkeypatch, capsys):
    """E16 bleibt: auch eine Mehrheit `widerlegt` ist kein Gate."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "test")
    monkeypatch.setattr(uf, "frage", _drei("widerlegt", "widerlegt", "bestaetigt"))
    assert uf.main([]) == 0
    assert json.loads(capsys.readouterr().out)["spruch"] == "widerlegt"


def test_should_survive_one_failing_call_of_three(monkeypatch, capsys):
    """Ein Anbieterfehler in einem von drei Laeufen kippt die Mehrheit nicht."""
    folge = iter(
        [
            _antwort('{"spruch":"bestaetigt","begruendung":"Regel 6."}'),
            OSError("connection reset"),
            _antwort('{"spruch":"bestaetigt","begruendung":"Regel 6."}'),
        ]
    )

    def wechselhaft(*a, **k):
        naechste = next(folge)
        if isinstance(naechste, Exception):
            raise naechste
        return naechste

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "test")
    monkeypatch.setattr(uf, "frage", wechselhaft)
    assert uf.main([]) == 0
    satz = json.loads(capsys.readouterr().out)
    assert satz["spruch"] == "bestaetigt"
    assert satz["einig"] is False
    assert "unklar" in satz["sprueche"]


def test_should_not_claim_agreement_when_it_never_asked(monkeypatch, capsys):
    """Uebersprungen ist kein Spruch — dann gibt es auch kein `einig`."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(BEFUND)))
    monkeypatch.setattr(uf, "schluessel_lesen", lambda: "")
    assert uf.main([]) == 0
    satz = json.loads(capsys.readouterr().out)
    assert satz["spruch"] == "uebersprungen"
    assert "einig" not in satz
