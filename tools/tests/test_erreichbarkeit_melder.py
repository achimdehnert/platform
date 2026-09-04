"""Tests fuer tools/erreichbarkeit_melder.py.

Zwei Ebenen mit Absicht: die Klassifikation gegen eine eingesetzte Attrappe, und
die Invarianten der ECHTEN `infra/ports.yaml` ohne jede Naht. Die zweite Ebene ist
der Grund, warum die erste nicht vakuos ist — eine Attrappe kann jede Zusage
erfuellen, die reale Datei nicht.
"""

from __future__ import annotations

import importlib.util
import pathlib
import urllib.error

import pytest

WURZEL = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "erreichbarkeit_melder", WURZEL / "tools" / "erreichbarkeit_melder.py"
)
em = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(em)


def _dienst(name="x-hub", status="aktiv", grund=None):
    return {
        "name": name,
        "domain": f"{name}.iil.pet",
        "host": "prod",
        "betriebsstatus": status,
        "grund": grund,
    }


# ── Klassifikation einer einzelnen Antwort ──────────────────────────────────


@pytest.mark.parametrize(
    "code,erwartet",
    [
        (200, "erreichbar"),
        (302, "erreichbar"),
        (401, "auth"),
        (403, "auth"),
        (502, "route-ohne-backend"),
        (599, "route-ohne-backend"),
        (199, "unklar"),
    ],
)
def test_should_klassifizieren_nach_statuscode(code, erwartet):
    assert em.probiere(_dienst(), oeffner=lambda url: code) == erwartet


def test_should_httperror_wie_statuscode_behandeln():
    def wirft(url):
        raise urllib.error.HTTPError(url, 503, "boom", {}, None)

    assert em.probiere(_dienst(), oeffner=wirft) == "route-ohne-backend"


def test_should_dns_fehler_von_verbindungsfehler_trennen():
    """Die teuerste Unterscheidung des Werkzeugs — falsche Deklaration vs. toter Dienst."""

    def nxdomain(url):
        raise OSError("[Errno -2] Name or service not known")

    def refused(url):
        raise ConnectionRefusedError("[Errno 111] Connection refused")

    assert em.probiere(_dienst(), oeffner=nxdomain) == "ziel-loest-nicht-auf"
    assert em.probiere(_dienst(), oeffner=refused) == "keine-antwort"


def test_should_attrappe_wirklich_werfen():
    """Gegenprobe zur Attrappe selbst: wirft sie nicht, ist jeder Test darueber wertlos."""

    def nxdomain(url):
        raise OSError("[Errno -2] Name or service not known")

    with pytest.raises(OSError):
        nxdomain("https://x/")


# ── Urteil aus Klasse + Lebenszyklus ────────────────────────────────────────


def test_should_aktiven_toten_dienst_als_befund_melden():
    e = em.bewerte([_dienst("bahn-hub")], {"bahn-hub": "route-ohne-backend"})
    assert [b["name"] for b in e["befunde"]] == ["bahn-hub"]


def test_should_auth_antwort_nicht_als_befund_melden():
    e = em.bewerte([_dienst("doc-hub")], {"doc-hub": "auth"})
    assert e["befunde"] == []
    assert [z["name"] for z in e["ok"]] == ["doc-hub"]


def test_should_geparkten_dienst_mit_grund_stumm_stellen():
    d = _dienst("frist-hub", status="blockiert", grund="wartet auf Hosting-ADR")
    e = em.bewerte([d], {"frist-hub": "ziel-loest-nicht-auf"})
    assert e["befunde"] == []
    assert [z["name"] for z in e["geparkt"]] == ["frist-hub"]


def test_should_ausnahme_ohne_grund_selbst_zum_befund_machen():
    d = _dienst("still-hub", status="stillgelegt", grund=None)
    e = em.bewerte([d], {"still-hub": "erreichbar"})
    assert [z["name"] for z in e["stumme_ausnahme"]] == ["still-hub"]
    assert e["geparkt"] == []


def test_should_unbekannten_betriebsstatus_nicht_still_durchlassen():
    d = _dienst("tipp-hub", status="aktvi", grund="Tippfehler im Wert")
    e = em.bewerte([d], {"tipp-hub": "route-ohne-backend"})
    assert [z["name"] for z in e["stumme_ausnahme"]] == ["tipp-hub"]


# ── Der Offline-Lauf darf nicht gruen aussehen ──────────────────────────────


def test_should_offline_lauf_nicht_als_alles_gruen_melden():
    dienste = [_dienst("a-hub"), _dienst("b-hub")]
    e = em.bewerte(dienste, em.messe(dienste, offline=True))
    assert e["befunde"] == []
    zeile = em._kurzzeile(e)
    assert "NICHT geprueft" in zeile
    assert "alle antworten" not in zeile


# ── Ohne Naht: Invarianten der echten infra/ports.yaml ──────────────────────


def test_should_echte_ports_yaml_lesen_koennen():
    dienste = em.lade_dienste(str(WURZEL / "infra" / "ports.yaml"))
    assert len(dienste) >= 20
    assert all(d["domain"] and d["name"] for d in dienste)


def test_should_jede_echte_ausnahme_einen_grund_tragen():
    """Die Invariante, die das Feld ueberhaupt vertrauenswuerdig macht."""
    dienste = em.lade_dienste(str(WURZEL / "infra" / "ports.yaml"))
    ohne_grund = [
        d["name"] for d in dienste if d["betriebsstatus"] != "aktiv" and not d["grund"]
    ]
    assert ohne_grund == [], f"betriebsstatus ohne Grund: {ohne_grund}"


def test_should_nur_erlaubte_betriebsstatus_werte_verwenden():
    dienste = em.lade_dienste(str(WURZEL / "infra" / "ports.yaml"))
    falsch = [
        d["name"] for d in dienste if d["betriebsstatus"] not in em.STATUS_ERLAUBT
    ]
    assert falsch == [], f"unbekannter betriebsstatus: {falsch}"
