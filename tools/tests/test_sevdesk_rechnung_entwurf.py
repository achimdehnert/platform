"""Tests für tools/sevdesk/rechnung_entwurf.py — Ausgangsrechnung als ENTWURF.

Die sevdesk-API wird über ``httpx.MockTransport`` simuliert, keine echte Anfrage
verlässt den Prozess. Kundendaten sind synthetisch ("Musterkommune") — nie die
realen Daten aus platform#2895 (öffentliches Repo).
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

import rechnung_entwurf as re_  # noqa: E402


def _client(handler) -> httpx.Client:
    return httpx.Client(
        base_url="https://my.sevdesk.de/api/v1",
        transport=httpx.MockTransport(handler),
    )


def _rechnung(
    nummer: str, contact_id: str = "1", status: str = "1000", **extra
) -> dict:
    basis = {
        "id": f"id-{nummer}",
        "invoiceNumber": nummer,
        "invoiceDate": "2026-08-28T00:00:00+02:00",
        "status": status,
        "contact": {"id": contact_id, "objectName": "Contact"},
        "sumNet": "0",
        "sumTax": "0",
        "sumGross": "0",
        "headText": "<p>Sehr geehrte Damen und Herren,</p>",
        "footText": "<p>Bitte überweisen Sie den Rechnungsbetrag ...</p>",
    }
    basis.update(extra)
    return basis


# ── naechste_nummer: fortlaufender Zähler, Paging, Jahreswechsel ──────────────


def test_should_return_next_number_after_highest_existing():
    bestand = [_rechnung("20260828-287"), _rechnung("20260702-286")]

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        objekte = bestand if offset == 0 else []
        return httpx.Response(200, json={"objects": objekte})

    client = _client(handler)
    assert re_.naechste_nummer(client, "2026-09-07") == "20260907-288"


def test_should_advance_numbering_across_year_boundary():
    """NNN ist ein einziger Zähler — kein Reset am Jahreswechsel."""
    bestand = [_rechnung("20251230-299"), _rechnung("20260105-300")]

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        objekte = bestand if offset == 0 else []
        return httpx.Response(200, json={"objects": objekte})

    client = _client(handler)
    assert re_.naechste_nummer(client, "2026-01-10") == "20260110-301"


def test_should_paginate_through_more_invoices_than_one_page():
    seite1 = [_rechnung(f"20260101-{i:03d}") for i in range(1, 501)]
    seite2 = [_rechnung("20260601-501")]

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        if offset == 0:
            return httpx.Response(200, json={"objects": seite1})
        if offset == 500:
            return httpx.Response(200, json={"objects": seite2})
        return httpx.Response(200, json={"objects": []})

    client = _client(handler)
    assert re_.naechste_nummer(client, "2026-09-07") == "20260907-502"


def test_should_ignore_legacy_invoice_numbers_outside_the_date_scheme():
    """Realfund 2026-09-07: eine Alt-Rechnung 'RE-1000' liegt im selben Bestand.

    Ein naiver Split auf den letzten Bindestrich läse "1000" als aktuell
    höchste laufende Nummer und würde die nächste Rechnung faelschlich auf
    ...-1001 statt ...-288 setzen.
    """
    bestand = [
        _rechnung("RE-1000"),
        _rechnung("20260828-287"),
        _rechnung("20260702-286"),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        objekte = bestand if offset == 0 else []
        return httpx.Response(200, json={"objects": objekte})

    client = _client(handler)
    assert re_.naechste_nummer(client, "2026-09-07") == "20260907-288"


# ── Kontakt: gefunden vs. neu angelegt ────────────────────────────────────────


def test_should_find_existing_contact_without_creating_a_new_one():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET", (
            "Treffer gefunden — es darf nichts angelegt werden"
        )
        return httpx.Response(
            200,
            json={"objects": [{"id": "42", "name": "Musterkommune"}]},
        )

    client = _client(handler)
    kontakt_id, war_neu = re_.kontakt_finden_oder_anlegen(
        client,
        "Musterkommune",
        "Rathausplatz 1",
        "12345",
        "Musterstadt",
        "rathaus@musterkommune.de",
    )
    assert (kontakt_id, war_neu) == ("42", False)


def test_should_create_contact_address_and_email_when_not_found():
    aufrufe: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        aufrufe.append((request.method, request.url.path))
        if request.method == "GET":
            return httpx.Response(200, json={"objects": []})
        if request.url.path == "/api/v1/Contact":
            body = request.read()
            import json as _json

            payload = _json.loads(body)
            assert payload["category"]["id"] == re_.KATEGORIE_KUNDE_ID
            assert payload["name2"] == "z. Hd. Amtsleitung Musterreferat"
            return httpx.Response(200, json={"objects": {"id": "99"}})
        if request.url.path == "/api/v1/ContactAddress":
            import json as _json

            payload = _json.loads(request.read())
            assert payload["contact"]["id"] == "99"
            assert payload["country"]["id"] == re_.DEUTSCHLAND_ID
            assert payload["category"]["id"] == re_.KATEGORIE_ADRESSE_ARBEIT_ID
            return httpx.Response(200, json={"objects": {"id": "500"}})
        if request.url.path == "/api/v1/CommunicationWay":
            import json as _json

            payload = _json.loads(request.read())
            assert payload["type"] == "EMAIL"
            assert payload["key"]["id"] == re_.EMAIL_KEY_ARBEIT_ID
            return httpx.Response(200, json={"objects": {"id": "501"}})
        raise AssertionError(
            f"unerwarteter Aufruf: {request.method} {request.url.path}"
        )

    client = _client(handler)
    kontakt_id, war_neu = re_.kontakt_finden_oder_anlegen(
        client,
        "Gemeinde Musterkommune",
        "Rathausplatz 1",
        "12345",
        "Musterstadt",
        "rathaus@musterkommune.de",
        zusatz="z. Hd. Amtsleitung Musterreferat",
    )
    assert (kontakt_id, war_neu) == ("99", True)
    methoden = [m for m, _ in aufrufe]
    assert methoden.count("POST") == 3


# ── Rechnungs-Payload: Entwurf-Status, Steuersatz, Positionen ─────────────────


def _mock_fuer_neuanlage(aufgezeichnet: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if request.method == "GET" and pfad == "/api/v1/Invoice":
            # sowohl naechste_nummer als auch entwurf_duplikat als auch neueste_texte
            # fragen /Invoice ab — je nach Filter unterschiedliche Antwort
            if "status" in request.url.params:
                return httpx.Response(200, json={"objects": []})  # kein Duplikat
            return httpx.Response(200, json={"objects": [_rechnung("20260828-287")]})
        if request.method == "GET" and pfad.startswith("/api/v1/Invoice/id-"):
            return httpx.Response(
                200,
                json={
                    "objects": _rechnung(
                        "20260907-288",
                        sumNet="650.00",
                        sumTax="123.50",
                        sumGross="773.50",
                    )
                },
            )
        if request.method == "POST" and pfad == "/api/v1/Invoice/Factory/saveInvoice":
            aufgezeichnet["daten"] = dict(request.url.params) or None
            # httpx gibt Formulardaten nicht über url.params — via content parsen
            from urllib.parse import parse_qsl

            aufgezeichnet["daten"] = dict(parse_qsl(request.read().decode()))
            return httpx.Response(
                200, json={"objects": {"invoice": {"id": "id-20260907-288"}}}
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {pfad}")

    return handler


def test_should_post_invoice_as_draft_with_tax_rate_19_and_position_fields():
    aufgezeichnet: dict = {}
    client = _client(_mock_fuer_neuanlage(aufgezeichnet))

    ergebnis = re_.rechnung_entwurf(
        client,
        kontakt_id="42",
        kontakt_name="Musterkommune",
        adresse="Musterkommune\nRathausplatz 1\n12345 Musterstadt",
        datum="2026-09-07",
        positionen=[
            {"name": "Vortrag", "text": "Klausurtagung", "menge": 1, "preis": 650.0}
        ],
    )

    daten = aufgezeichnet["daten"]
    assert daten["invoice[status]"] == "100"
    assert daten["invoice[invoiceType]"] == "RE"
    assert daten["invoice[taxType]"] == "default"
    assert daten["invoicePosSave[0][taxRate]"] == "19"
    assert daten["invoicePosSave[0][unity][id]"] == "1"
    assert daten["invoicePosSave[0][name]"] == "Vortrag"
    assert daten["invoicePosSave[0][price]"] == "650.00"
    assert "sendBy" not in daten
    assert not ergebnis["duplikat"]
    assert ergebnis["nummer"] == "20260907-288"
    assert ergebnis["netto"] == 650.0
    assert ergebnis["steuer"] == 123.5
    assert ergebnis["brutto"] == 773.5


def test_should_reject_when_sevdesk_returns_wrong_gross_sum():
    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if request.method == "GET" and pfad == "/api/v1/Invoice":
            if "status" in request.url.params:
                return httpx.Response(200, json={"objects": []})
            return httpx.Response(200, json={"objects": [_rechnung("20260828-287")]})
        if request.method == "GET" and pfad.startswith("/api/v1/Invoice/id-"):
            # Falsches Brutto: sevdesk hätte 773.50 liefern müssen
            return httpx.Response(
                200,
                json={
                    "objects": _rechnung(
                        "20260907-288",
                        sumNet="650.00",
                        sumTax="123.50",
                        sumGross="700.00",
                    )
                },
            )
        if request.method == "POST" and pfad == "/api/v1/Invoice/Factory/saveInvoice":
            return httpx.Response(
                200, json={"objects": {"invoice": {"id": "id-20260907-288"}}}
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {pfad}")

    client = _client(handler)
    with pytest.raises(ValueError, match="Plausibilitätsprobe verletzt"):
        re_.rechnung_entwurf(
            client,
            kontakt_id="42",
            kontakt_name="Musterkommune",
            adresse="Musterkommune\nRathausplatz 1\n12345 Musterstadt",
            datum="2026-09-07",
            positionen=[{"name": "Vortrag", "text": None, "menge": 1, "preis": 650.0}],
        )


def test_should_abort_when_draft_with_same_contact_date_and_net_exists():
    vorhandene_id = "id-vorhanden"

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if request.method == "GET" and pfad == "/api/v1/Invoice":
            if request.url.params.get("status") == "100":
                return httpx.Response(
                    200,
                    json={
                        "objects": [
                            _rechnung(
                                "20260907-100",
                                status="100",
                                sumNet="650.00",
                                id=vorhandene_id,
                                invoiceDate="2026-09-07T00:00:00+02:00",
                            )
                        ]
                    },
                )
            return httpx.Response(200, json={"objects": []})
        raise AssertionError(
            f"Duplikat haette abbrechen muessen, statt dessen: {request.method} {pfad}"
        )

    client = _client(handler)
    ergebnis = re_.rechnung_entwurf(
        client,
        kontakt_id="42",
        kontakt_name="Musterkommune",
        adresse="Musterkommune\nRathausplatz 1\n12345 Musterstadt",
        datum="2026-09-07",
        positionen=[{"name": "Vortrag", "text": None, "menge": 1, "preis": 650.0}],
    )
    assert ergebnis == {"duplikat": True, "vorhanden_id": vorhandene_id}


# ── Dry-run: kein einziger POST ────────────────────────────────────────────────


def test_should_write_nothing_in_dry_run(monkeypatch, capsys):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method != "GET":
            raise AssertionError(
                f"--dry-run darf nie schreiben: {request.method} {request.url}"
            )
        if request.url.path == "/api/v1/Contact":
            return httpx.Response(200, json={"objects": []})
        if request.url.path == "/api/v1/Invoice":
            return httpx.Response(200, json={"objects": [_rechnung("20260828-287")]})
        raise AssertionError(f"unerwarteter GET: {request.url}")

    monkeypatch.setattr(re_, "_client", lambda: _client(handler))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rechnung_entwurf.py",
            "--kunde",
            "Musterkommune",
            "--strasse",
            "Rathausplatz 1",
            "--plz",
            "12345",
            "--ort",
            "Musterstadt",
            "--email",
            "rathaus@musterkommune.de",
            "--datum",
            "2026-09-07",
            "--position",
            "Vortrag|Klausurtagung|1|650.00",
            "--dry-run",
        ],
    )

    assert re_.main() == 0
    ausgabe = capsys.readouterr().out
    assert "20260907-288" in ausgabe
    assert "wird neu angelegt" in ausgabe


def test_should_parse_position_with_comma_decimal():
    pos = re_.parse_position("Vortrag|Text|1|650,00")
    assert pos["preis"] == 650.0


def test_should_reject_position_with_wrong_field_count():
    with pytest.raises(ValueError):
        re_.parse_position("Vortrag|Text|1")
