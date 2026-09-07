"""Tests fuer tools/erreichbarkeit_melder.py.

Zwei Ebenen mit Absicht: die Klassifikation gegen eine eingesetzte Attrappe, und
die Invarianten der ECHTEN `infra/ports.yaml` ohne jede Naht. Die zweite Ebene ist
der Grund, warum die erste nicht vakuos ist — eine Attrappe kann jede Zusage
erfuellen, die reale Datei nicht.
"""

from __future__ import annotations

import importlib.util
import json
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


# ── Gemeinsame Melder-Huelle (platform#2944) ────────────────────────────────


def _ergebnis_zeile(name, domain, klasse, grund=None):
    # Traegt bewusst ein `host`-Feld mit einem internen Namen — die Gegenprobe
    # unten prueft, dass genau dieses Feld NICHT in die Ausgabe durchsickert.
    return {
        "name": name,
        "domain": domain,
        "host": "sehr-interner-hostname-01",
        "klasse": klasse,
        "grund": grund,
    }


def test_should_map_the_four_buckets_into_the_shared_shape():
    ergebnis = {
        "befunde": [
            _ergebnis_zeile("bahn-hub", "bahn-hub.iil.pet", "route-ohne-backend")
        ],
        "geparkt": [
            _ergebnis_zeile(
                "frist-hub",
                "frist-hub.iil.pet",
                "ziel-loest-nicht-auf",
                grund="wartet auf Hosting-ADR",
            )
        ],
        "stumme_ausnahme": [],
        "ok": [_ergebnis_zeile("doc-hub", "doc-hub.iil.pet", "erreichbar")],
    }
    liste = em._ergebnis_liste(ergebnis)
    nach_name = {z["name"]: z for z in liste}
    assert nach_name["bahn-hub"]["erreichbar"] is False
    assert nach_name["frist-hub"]["erreichbar"] is False
    assert nach_name["frist-hub"]["grund"] == "wartet auf Hosting-ADR"
    assert nach_name["doc-hub"]["erreichbar"] is True
    # Gegenprobe: der interne Host-Name steht im Eingabe-Dict (oben), darf aber
    # in keiner Ausgabezeile auftauchen — weder als Feld noch als Wert irgendwo.
    for z in liste:
        assert "host" not in z
        assert "sehr-interner-hostname-01" not in json.dumps(z)


def test_should_write_result_via_cli_without_changing_behavior_when_flag_absent(
    tmp_path,
):
    """`--ergebnis-datei` ist rein additiv: ohne sie bleibt der Melder wie vorher."""
    ports = tmp_path / "ports.yaml"
    ports.write_text(
        "services:\n"
        "  test-hub:\n"
        "    domain_prod: test-hub.iil.pet\n"
        "    prod_host: sehr-interner-hostname-01\n",
        encoding="utf-8",
    )

    code_ohne = em.main(["--kurz", "--offline", "--ports", str(ports)])
    assert code_ohne == 0

    ziel = tmp_path / "ergebnis.json"
    code_mit = em.main(
        ["--kurz", "--offline", "--ports", str(ports), "--ergebnis-datei", str(ziel)]
    )
    assert code_mit == 0
    assert ziel.exists()

    daten = em.melder_ergebnis.lies(ziel)
    assert daten is not None
    assert daten["melder"] == "erreichbarkeit_melder"
    assert [e["name"] for e in daten["ergebnis"]] == ["test-hub"]

    roh = ziel.read_text(encoding="utf-8")
    assert "sehr-interner-hostname-01" not in roh
