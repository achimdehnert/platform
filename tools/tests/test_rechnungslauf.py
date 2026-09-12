"""Tests für tools/sevdesk/rechnungslauf.py — Monats-/Quartalsrechnungslauf (#3102).

Die sevdesk-API wird über ``httpx.MockTransport`` simuliert, keine echte Anfrage
verlässt den Prozess. Kundendaten sind synthetisch ("Musterkunde GmbH"), Kontakt-
IDs frei erfunden — nie die realen Daten aus platform#3102 (öffentliches Repo).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

import rechnungslauf as rl  # noqa: E402


def _client(handler) -> httpx.Client:
    return httpx.Client(
        base_url="https://my.sevdesk.de/api/v1",
        transport=httpx.MockTransport(handler),
    )


def _rechnung(
    nummer: str, contact_id: str, von: str, bis: str, status: str = "1000", **extra
) -> dict:
    basis = {
        "id": f"id-{nummer}",
        "invoiceNumber": nummer,
        "invoiceDate": f"{von}T00:00:00+02:00",
        "deliveryDate": f"{von}T00:00:00+02:00",
        "deliveryDateUntil": f"{bis}T00:00:00+02:00",
        "status": status,
        "contact": {"id": contact_id, "objectName": "Contact"},
        "timeToPay": "14",
        "sumNet": "0",
        "sumTax": "0",
        "sumGross": "0",
    }
    basis.update(extra)
    return basis


# ── Rhythmuserkennung (reine Logik, ohne API) ────────────────────────────────


def test_should_recognize_monthly_rhythm_from_two_matching_periods():
    rechnungen = [
        {
            "id": "r1",
            "contact_id": "10",
            "contact_name": "Musterkunde GmbH",
            "von": "2026-06-01",
            "bis": "2026-06-30",
        },
        {
            "id": "r2",
            "contact_id": "10",
            "contact_name": "Musterkunde GmbH",
            "von": "2026-07-01",
            "bis": "2026-07-31",
        },
    ]
    kunden, unregelmaessig = rl.dauerkunden_erkennen(rechnungen)
    assert unregelmaessig == []
    assert kunden["10"]["rhythmus"] == rl.RHYTHMUS_MONAT
    assert kunden["10"]["letzte_rechnung_id"] == "r2"
    assert kunden["10"]["letzter_zeitraum"] == ["2026-07-01", "2026-07-31"]


def test_should_recognize_quarterly_rhythm_from_two_matching_periods():
    rechnungen = [
        {
            "id": "r1",
            "contact_id": "20",
            "contact_name": "Musterfirma AG",
            "von": "2026-01-01",
            "bis": "2026-03-31",
        },
        {
            "id": "r2",
            "contact_id": "20",
            "contact_name": "Musterfirma AG",
            "von": "2026-04-01",
            "bis": "2026-06-30",
        },
    ]
    kunden, unregelmaessig = rl.dauerkunden_erkennen(rechnungen)
    assert unregelmaessig == []
    assert kunden["20"]["rhythmus"] == rl.RHYTHMUS_QUARTAL


def test_should_mark_customer_as_irregular_with_only_one_matching_period():
    rechnungen = [
        {
            "id": "r1",
            "contact_id": "30",
            "contact_name": "Einzelkunde",
            "von": "2026-06-01",
            "bis": "2026-06-30",
        },
        {
            "id": "r2",
            "contact_id": "30",
            "contact_name": "Einzelkunde",
            "von": "2026-08-15",
            "bis": "2026-09-02",
        },
    ]
    kunden, unregelmaessig = rl.dauerkunden_erkennen(rechnungen)
    assert kunden == {}
    assert unregelmaessig == [{"kontakt_id": "30", "name": "Einzelkunde"}]


def test_should_ignore_invoices_without_delivery_period_when_grouping():
    rechnungen = [
        {"id": "r0", "contact_id": "10", "contact_name": "x", "von": "", "bis": ""},
        {
            "id": "r1",
            "contact_id": "10",
            "contact_name": "x",
            "von": "2026-06-01",
            "bis": "2026-06-30",
        },
        {
            "id": "r2",
            "contact_id": "10",
            "contact_name": "x",
            "von": "2026-07-01",
            "bis": "2026-07-31",
        },
    ]
    kunden, _ = rl.dauerkunden_erkennen(rechnungen)
    assert kunden["10"]["letzte_rechnung_id"] == "r2"


# ── kunden_ermitteln: Diff-Meldung bei erneutem Lauf ─────────────────────────


def test_should_report_new_and_dropped_customers_on_repeated_run(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/Invoice":
            offset = int(request.url.params.get("offset", "0"))
            if offset > 0:
                return httpx.Response(200, json={"objects": []})
            return httpx.Response(
                200,
                json={
                    "objects": [
                        _rechnung("20260601-1", "10", "2026-06-01", "2026-06-30"),
                        _rechnung("20260701-1", "10", "2026-07-01", "2026-07-31"),
                    ]
                },
            )
        if request.url.path == "/api/v1/Contact/10":
            return httpx.Response(
                200, json={"objects": {"id": "10", "name": "Musterkunde GmbH"}}
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.url.path}")

    kunden_datei = tmp_path / "dauerkunden.json"
    kunden_datei.write_text(
        json.dumps({"99": {"name": "Alt-Kunde", "rhythmus": "monat"}}), encoding="utf-8"
    )

    client = _client(handler)
    bericht = rl.kunden_ermitteln(client, kunden_datei)

    assert bericht["neu"] == ["10"]
    assert bericht["entfallen"] == ["99"]
    geschrieben = json.loads(kunden_datei.read_text(encoding="utf-8"))
    assert geschrieben["10"]["name"] == "Musterkunde GmbH"
    assert geschrieben["10"]["rhythmus"] == "monat"
    # 0600 — nur Owner darf lesen (lokale Kundendatei, nie im Repo)
    assert oct(kunden_datei.stat().st_mode)[-3:] == "600"


# ── Zeitraumgrenzen ───────────────────────────────────────────────────────────


def test_should_compute_february_month_boundaries_in_non_leap_year():
    assert rl.zeitraum_monat("2026-02") == ("2026-02-01", "2026-02-28")


def test_should_compute_february_month_boundaries_in_leap_year():
    assert rl.zeitraum_monat("2028-02") == ("2028-02-01", "2028-02-29")


def test_should_compute_quarter_boundaries_across_three_months():
    assert rl.zeitraum_quartal("2026-Q1") == ("2026-01-01", "2026-03-31")
    assert rl.zeitraum_quartal("2026-Q4") == ("2026-10-01", "2026-12-31")


def test_should_compute_previous_month_across_year_boundary():
    import datetime as dt

    assert rl.vormonat(dt.date(2026, 1, 15)) == "2025-12"


def test_should_compute_previous_quarter_across_year_boundary():
    import datetime as dt

    assert rl.vorquartal(dt.date(2026, 1, 15)) == "2025-Q4"


# ── Rechnungslauf: Duplikat, Dry-Run, Idempotenz ─────────────────────────────


_KUNDEN = {
    "10": {
        "name": "Musterkunde GmbH",
        "rhythmus": "monat",
        "letzte_rechnung_id": "id-tpl",
        "letzter_zeitraum": ["2026-07-01", "2026-07-31"],
    }
}


def _handler_ohne_duplikat(aufgezeichnet: list):
    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if request.method == "GET" and pfad == "/api/v1/Invoice":
            if "status" in request.url.params or request.url.params.get(
                "offset"
            ) not in (None, "0"):
                return httpx.Response(200, json={"objects": []})
            return httpx.Response(200, json={"objects": []})
        if request.method == "GET" and pfad == "/api/v1/InvoicePos":
            return httpx.Response(
                200,
                json={
                    "objects": [
                        {
                            "name": "Beratung",
                            "text": None,
                            "quantity": "1",
                            "price": "100.00",
                            "taxRate": "19",
                            "unity": {"id": "1"},
                        }
                    ]
                },
            )
        if request.method == "GET" and pfad == "/api/v1/Invoice/id-tpl":
            return httpx.Response(
                200,
                json={
                    "objects": {
                        "address": "Musterkunde GmbH\nMusterstr. 1\n12345 Musterstadt",
                        "addressName": "Musterkunde GmbH",
                        "headText": "",
                        "footText": "",
                        "timeToPay": "14",
                    }
                },
            )
        if request.method == "POST" and pfad == "/api/v1/Invoice/Factory/saveInvoice":
            from urllib.parse import parse_qsl

            aufgezeichnet.append(dict(parse_qsl(request.read().decode())))
            return httpx.Response(200, json={"objects": {"invoice": {"id": "id-neu"}}})
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {pfad}")

    return handler


def test_should_skip_when_duplicate_delivery_date_exists():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/Invoice":
            return httpx.Response(
                200,
                json={
                    "objects": [
                        _rechnung("20260801-1", "10", "2026-08-01", "2026-08-31")
                    ]
                },
            )
        raise AssertionError(
            "Duplikat haette abbrechen muessen, kein weiterer Aufruf erwartet"
        )

    client = _client(handler)
    posten = rl.rechnungslauf(
        client, _KUNDEN, "monat", "2026-08-01", "2026-08-31", dry_run=True
    )
    assert posten[0]["status"] == "vorhanden"
    assert posten[0]["entwurfsnummer"] == "20260801-1"


def test_should_write_nothing_in_dry_run_and_be_idempotent():
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method != "GET":
            raise AssertionError(
                f"--dry-run darf nie schreiben: {request.method} {request.url}"
            )
        return _handler_ohne_duplikat(calls)(request)

    client = _client(handler)
    lauf1 = rl.rechnungslauf(
        client, _KUNDEN, "monat", "2026-09-01", "2026-09-30", dry_run=True
    )
    lauf2 = rl.rechnungslauf(
        client, _KUNDEN, "monat", "2026-09-01", "2026-09-30", dry_run=True
    )

    assert lauf1 == lauf2
    assert lauf1[0]["status"] == "wuerde_angelegt"
    assert calls == []


def test_should_create_draft_from_template_when_no_duplicate_exists():
    aufgezeichnet: list = []
    client = _client(_handler_ohne_duplikat(aufgezeichnet))

    posten = rl.rechnungslauf(
        client, _KUNDEN, "monat", "2026-09-01", "2026-09-30", dry_run=False
    )

    assert posten[0]["status"] == "angelegt"
    daten = aufgezeichnet[0]
    assert daten["invoice[status]"] == "100"
    assert daten["invoice[deliveryDate]"] == "2026-09-01"
    assert daten["invoice[deliveryDateUntil]"] == "2026-09-30"
    assert daten["invoicePosSave[0][name]"] == "Beratung"
    assert daten["invoicePosSave[0][price]"] == "100.00"


# ── Betragsformat, Fälligkeit ─────────────────────────────────────────────────


def test_should_format_amount_with_german_thousands_and_comma():
    assert rl.betrag_format(1234.5) == "1.234,50 EUR"
    assert rl.betrag_format(99.9) == "99,90 EUR"


def test_should_compute_due_date_from_invoice_date_and_payment_term():
    assert rl.faelligkeit("2026-09-01", 14) == "2026-09-15"


# ── Versand: nur Status 100, 429-Wiederholung, Doppelversand-Schutz ──────────


def test_should_only_offer_drafts_with_status_100_for_sending():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/Invoice":
            assert request.url.params.get("status") == "100"
            return httpx.Response(
                200,
                json={
                    "objects": [
                        _rechnung(
                            "20260901-1",
                            "10",
                            "2026-09-01",
                            "2026-09-30",
                            status="100",
                            sumGross="119.00",
                        )
                    ]
                },
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.url.path}")

    client = _client(handler)
    kandidaten = rl._entwuerfe_fuer_versand(client, _KUNDEN, "monat", "2026-09-01")
    assert len(kandidaten) == 1
    assert kandidaten[0]["nummer"] == "20260901-1"
    assert kandidaten[0]["brutto"] == 119.0


def test_should_skip_sending_when_status_changed_since_listing(tmp_path, monkeypatch):
    monkeypatch.setattr(rl.Path, "home", classmethod(lambda cls: tmp_path))

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if pfad == "/api/v1/Invoice" and "status" in request.url.params:
            return httpx.Response(
                200,
                json={
                    "objects": [
                        _rechnung(
                            "20260901-1",
                            "10",
                            "2026-09-01",
                            "2026-09-30",
                            status="100",
                            sumGross="119.00",
                        )
                    ]
                },
            )
        if pfad == "/api/v1/Invoice/id-20260901-1":
            # zwischenzeitlich verbucht -> nicht mehr Status 100
            return httpx.Response(200, json={"objects": {"status": "1000"}})
        raise AssertionError(
            f"unerwarteter Aufruf (kein Versand erwartet): {request.method} {pfad}"
        )

    client = _client(handler)
    ergebnis = rl.versenden(
        client, _KUNDEN, "monat", "2026-09-01", "2026-09-30", ja=True
    )
    assert ergebnis["gesendet"] == 0
    assert ergebnis["uebersprungen"] == 1
    assert "status=1000" in ergebnis["kandidaten"][0]["aktion"]


def test_should_retry_on_http_429_and_respect_retry_after_header():
    versuche = {"n": 0}
    geschlafen: list[float] = []

    def aufruf():
        versuche["n"] += 1
        if versuche["n"] < 3:
            return httpx.Response(429, headers={"Retry-After": "5"})
        return httpx.Response(200, json={"objects": {"id": "mail-1"}})

    antwort, wiederholungen = rl._mit_429_wiederholung(aufruf, schlaf=geschlafen.append)

    assert antwort.status_code == 200
    assert wiederholungen == 2
    assert geschlafen == [5.0, 5.0]


def test_should_stop_retrying_after_max_attempts_on_persistent_429():
    def aufruf():
        return httpx.Response(429)

    antwort, wiederholungen = rl._mit_429_wiederholung(aufruf, schlaf=lambda _s: None)
    assert antwort.status_code == 429
    assert wiederholungen == rl.VERSAND_MAX_VERSUCHE


def test_should_prevent_double_send_when_log_already_has_mail_id(tmp_path, monkeypatch):
    monkeypatch.setattr(rl.Path, "home", classmethod(lambda cls: tmp_path))
    log_pfad = rl._versandlog_pfad("2026-09-01")
    log_pfad.parent.mkdir(parents=True, exist_ok=True)
    log_pfad.write_text(
        json.dumps([{"rechnung_id": "id-20260901-1", "mail_id": "mail-alt"}]),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if pfad == "/api/v1/Invoice" and "status" in request.url.params:
            return httpx.Response(
                200,
                json={
                    "objects": [
                        _rechnung(
                            "20260901-1",
                            "10",
                            "2026-09-01",
                            "2026-09-30",
                            status="100",
                            sumGross="119.00",
                        )
                    ]
                },
            )
        raise AssertionError(
            f"bereits gesendet — kein weiterer Aufruf erwartet: {request.method} {pfad}"
        )

    client = _client(handler)
    ergebnis = rl.versenden(
        client, _KUNDEN, "monat", "2026-09-01", "2026-09-30", ja=True
    )
    assert ergebnis["gesendet"] == 0
    assert ergebnis["uebersprungen"] == 1
    assert "bereits gesendet" in ergebnis["kandidaten"][0]["aktion"]


def test_should_send_email_with_signature_and_write_log(tmp_path, monkeypatch):
    monkeypatch.setattr(rl.Path, "home", classmethod(lambda cls: tmp_path))
    gesendete_texte: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if pfad == "/api/v1/Invoice" and "status" in request.url.params:
            return httpx.Response(
                200,
                json={
                    "objects": [
                        _rechnung(
                            "20260901-1",
                            "10",
                            "2026-09-01",
                            "2026-09-30",
                            status="100",
                            sumGross="119.00",
                            timeToPay="14",
                        )
                    ]
                },
            )
        if pfad == "/api/v1/Invoice/id-20260901-1":
            return httpx.Response(200, json={"objects": {"status": "100"}})
        if pfad == "/api/v1/CommunicationWay":
            return httpx.Response(
                200,
                json={
                    "objects": [
                        {"type": "EMAIL", "value": "buchhaltung@musterkunde.example"}
                    ]
                },
            )
        if pfad == "/api/v1/TextTemplate":
            return httpx.Response(
                200, json={"objects": [{"main": "1", "text": "IIL GmbH Signatur"}]}
            )
        if pfad == "/api/v1/Invoice/id-20260901-1/sendViaEmail":
            from urllib.parse import parse_qsl

            gesendete_texte.append(dict(parse_qsl(request.read().decode())))
            return httpx.Response(200, json={"objects": {"id": "mail-1"}})
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {pfad}")

    client = _client(handler)
    ergebnis = rl.versenden(
        client,
        _KUNDEN,
        "monat",
        "2026-09-01",
        "2026-09-30",
        ja=True,
        schlaf=lambda _s: None,
    )

    assert ergebnis["gesendet"] == 1
    text = gesendete_texte[0]
    assert text["subject"] == "Rechnung 20260901-1 der IIL GmbH"
    assert "IIL GmbH Signatur" in text["text"]
    assert "119,00 EUR" in text["text"]
    assert text["toEmail"] == "buchhaltung@musterkunde.example"

    log = json.loads(rl._versandlog_pfad("2026-09-01").read_text(encoding="utf-8"))
    assert log[0]["mail_id"] == "mail-1"


def test_should_show_preview_without_ja_and_send_nothing():
    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if pfad == "/api/v1/Invoice" and "status" in request.url.params:
            return httpx.Response(
                200,
                json={
                    "objects": [
                        _rechnung(
                            "20260901-1",
                            "10",
                            "2026-09-01",
                            "2026-09-30",
                            status="100",
                            sumGross="119.00",
                        )
                    ]
                },
            )
        if pfad == "/api/v1/Invoice/id-20260901-1":
            return httpx.Response(200, json={"objects": {"status": "100"}})
        raise AssertionError(
            f"ohne --ja darf nichts gesendet werden: {request.method} {pfad}"
        )

    client = _client(handler)
    ergebnis = rl.versenden(
        client, _KUNDEN, "monat", "2026-09-01", "2026-09-30", ja=False
    )
    assert ergebnis["gesendet"] == 0
    assert ergebnis["kandidaten"][0]["aktion"] == "wuerde_gesendet"
