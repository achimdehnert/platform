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


# ── K1-Nachtrag #3102: "beendet" — Luecke zwischen letztem Zeitraum und dem ──
# ── angeforderten Zeitraum, > 2 Rhythmusperioden = beendet ───────────────────


def test_should_mark_customer_as_beendet_when_gap_exceeds_two_periods():
    """Realfall: letzte Rechnung Juni 2025, angeforderter Monat weit dahinter
    liegend — der Kunde ist beendet und darf NIE wieder automatisch eine
    Rechnung bekommen."""
    assert rl.ist_beendet("monat", ["2025-06-01", "2025-06-30"], "2026-09-01") is True


def test_should_keep_customer_active_when_gap_is_exactly_one_period():
    """Normalfall: letzte Rechnung im Vormonat des angeforderten Zeitraums —
    Luecke von genau 1 Periode ist der erwartete Ablauf, kein Abbruch."""
    assert rl.ist_beendet("monat", ["2026-08-01", "2026-08-31"], "2026-09-01") is False


def test_should_keep_quarterly_customer_active_within_two_quarter_gap():
    """Positivkontrolle fuer den Quartals-Rhythmus: Luecke von genau 2
    Quartalen (Q1 -> Q3) ist noch KEIN Abbruch (Schwelle ist '> 2', nicht
    '>= 2')."""
    assert (
        rl.ist_beendet("quartal", ["2026-01-01", "2026-03-31"], "2026-07-01") is False
    )


def test_should_mark_quarterly_customer_as_beendet_beyond_two_quarter_gap():
    assert rl.ist_beendet("quartal", ["2025-01-01", "2025-03-31"], "2026-10-01") is True


def test_should_treat_missing_letzter_zeitraum_as_not_beendet():
    """Fehlt der letzte Zeitraum (z. B. handverfasster Kundendatei-Eintrag),
    wird NICHT automatisch beendet — sonst wuerde ein unvollstaendiger
    Eintrag stillschweigend jeden Lauf blockieren."""
    assert rl.ist_beendet("monat", None, "2026-09-01") is False


def test_should_set_zustand_beendet_on_dauerkunden_when_gap_is_large():
    """``dauerkunden_erkennen`` setzt ``zustand`` als Schnappschuss relativ
    zu ``heute`` — hier mit fixem Referenzdatum fuer deterministische Tests."""
    import datetime as dt

    rechnungen = [
        {
            "id": "r1",
            "contact_id": "50",
            "contact_name": "Beendete Kunde GmbH",
            "von": "2025-04-01",
            "bis": "2025-04-30",
        },
        {
            "id": "r2",
            "contact_id": "50",
            "contact_name": "Beendete Kunde GmbH",
            "von": "2025-05-01",
            "bis": "2025-05-31",
        },
    ]
    kunden, _ = rl.dauerkunden_erkennen(rechnungen, heute=dt.date(2026, 9, 12))
    assert kunden["50"]["zustand"] == "beendet"


def test_should_set_zustand_aktiv_on_dauerkunden_when_recently_billed():
    import datetime as dt

    rechnungen = [
        {
            "id": "r1",
            "contact_id": "51",
            "contact_name": "Aktive Kunde GmbH",
            "von": "2026-07-01",
            "bis": "2026-07-31",
        },
        {
            "id": "r2",
            "contact_id": "51",
            "contact_name": "Aktive Kunde GmbH",
            "von": "2026-08-01",
            "bis": "2026-08-31",
        },
    ]
    kunden, _ = rl.dauerkunden_erkennen(rechnungen, heute=dt.date(2026, 9, 12))
    assert kunden["51"]["zustand"] == "aktiv"


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


def test_should_report_zustand_counts_without_names(tmp_path):
    """K1-Nachtrag #3102: Rueckmeldung nennt nur Zahlen je Zustand, keine
    Namen — ein aktiver Monats-, ein aktiver Quartals- und ein beendeter
    Kunde ergeben 1/1/1."""
    import datetime as dt

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/Invoice":
            offset = int(request.url.params.get("offset", "0"))
            if offset > 0:
                return httpx.Response(200, json={"objects": []})
            return httpx.Response(
                200,
                json={
                    "objects": [
                        # aktiver Monatskunde
                        _rechnung("20260701-1", "10", "2026-07-01", "2026-07-31"),
                        _rechnung("20260801-1", "10", "2026-08-01", "2026-08-31"),
                        # aktiver Quartalskunde
                        _rechnung("20260101-2", "20", "2026-01-01", "2026-03-31"),
                        _rechnung("20260401-2", "20", "2026-04-01", "2026-06-30"),
                        # beendeter Monatskunde (letzte Rechnung weit zurueck)
                        _rechnung("20250401-3", "30", "2025-04-01", "2025-04-30"),
                        _rechnung("20250501-3", "30", "2025-05-01", "2025-05-31"),
                    ]
                },
            )
        if request.url.path.startswith("/api/v1/Contact/"):
            kid = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(
                200, json={"objects": {"id": kid, "name": f"Kunde {kid}"}}
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.url.path}")

    kunden_datei = tmp_path / "dauerkunden.json"
    client = _client(handler)
    bericht = rl.kunden_ermitteln(client, kunden_datei, heute=dt.date(2026, 9, 12))

    assert bericht["aktiv_monatlich"] == 1
    assert bericht["aktiv_quartalsweise"] == 1
    assert bericht["beendet"] == 1
    # "neu"/"entfallen" fuehren nur Kontakt-IDs, keine Namen
    for kontakt_id in bericht["neu"]:
        assert kontakt_id.isdigit()


def test_should_preserve_manual_aktiv_false_across_reruns(tmp_path):
    """Ein Owner-Override (``"aktiv": false``) darf ein erneuter
    --kunden-ermitteln-Lauf NICHT stillschweigend zuruecksetzen."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/Invoice":
            offset = int(request.url.params.get("offset", "0"))
            if offset > 0:
                return httpx.Response(200, json={"objects": []})
            return httpx.Response(
                200,
                json={
                    "objects": [
                        _rechnung("20260701-1", "10", "2026-07-01", "2026-07-31"),
                        _rechnung("20260801-1", "10", "2026-08-01", "2026-08-31"),
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
        json.dumps(
            {"10": {"name": "Musterkunde GmbH", "rhythmus": "monat", "aktiv": False}}
        ),
        encoding="utf-8",
    )

    client = _client(handler)
    rl.kunden_ermitteln(client, kunden_datei)

    geschrieben = json.loads(kunden_datei.read_text(encoding="utf-8"))
    assert geschrieben["10"]["aktiv"] is False


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
    # Positivkontrolle K1-Nachtrag #3102: ein normaler aktiver Kunde
    # (Luecke von nur 2 Perioden, kein "aktiv": false) wird durch die neuen
    # Beendet-/Inaktiv-Pruefungen NICHT ausgebremst.


# ── K1-Nachtrag #3102: beendete/inaktive Kunden bekommen GARANTIERT nichts ──


def _kunde_beendet(letzter_zeitraum: list[str]) -> dict:
    return {
        "20": {
            "name": "Beendete Kunde GmbH",
            "rhythmus": "monat",
            "letzte_rechnung_id": "id-tpl-alt",
            "letzter_zeitraum": letzter_zeitraum,
        }
    }


def test_should_skip_beendet_customer_in_rechnungslauf_without_further_api_calls():
    kunden = _kunde_beendet(["2025-01-01", "2025-01-31"])

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(
            f"beendeter Kunde darf KEINE sevdesk-Anfrage ausloesen: {request.method} {request.url}"
        )

    client = _client(handler)
    posten = rl.rechnungslauf(
        client, kunden, "monat", "2026-09-01", "2026-09-30", dry_run=True
    )

    assert posten[0]["status"] == "beendet"
    assert posten[0]["entwurfsnummer"] is None
    assert "beendet" in rl.markdown_tabelle(posten)


def test_should_skip_beendet_customer_even_when_not_dry_run():
    """ "auch nicht mit --senden"/dem Anlege-Lauf — die Sperre gilt fuer
    dry_run=False genauso wie fuer dry_run=True."""
    kunden = _kunde_beendet(["2025-01-01", "2025-01-31"])

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("beendeter Kunde darf nie angelegt werden")

    client = _client(handler)
    posten = rl.rechnungslauf(
        client, kunden, "monat", "2026-09-01", "2026-09-30", dry_run=False
    )
    assert posten[0]["status"] == "beendet"


def test_should_skip_customer_with_manual_aktiv_false_in_rechnungslauf():
    kunden = {
        "30": {
            "name": "Manuell inaktive GmbH",
            "rhythmus": "monat",
            "letzte_rechnung_id": "id-tpl-30",
            "letzter_zeitraum": ["2026-08-01", "2026-08-31"],  # sonst voellig normal
            "aktiv": False,
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(
            f"aktiv=false darf KEINE sevdesk-Anfrage ausloesen: {request.method} {request.url}"
        )

    client = _client(handler)
    posten = rl.rechnungslauf(
        client, kunden, "monat", "2026-09-01", "2026-09-30", dry_run=True
    )

    assert posten[0]["status"] == "inaktiv"
    assert "inaktiv" in rl.markdown_tabelle(posten)


def test_should_never_send_to_beendet_or_inactive_customer():
    """--senden darf fuer beendete/inaktive Kunden gar nicht erst eine
    Invoice-Abfrage absetzen — auch mit --ja waere daher nichts zu finden."""
    kunden = {
        **_kunde_beendet(["2025-01-01", "2025-01-31"]),
        "30": {
            "name": "Manuell inaktive GmbH",
            "rhythmus": "monat",
            "letzter_zeitraum": ["2026-08-01", "2026-08-31"],
            "aktiv": False,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(
            f"beendet/inaktiv duerfen keine Versand-Anfrage ausloesen: {request.url}"
        )

    client = _client(handler)
    kandidaten = rl._entwuerfe_fuer_versand(client, kunden, "monat", "2026-09-01")
    assert kandidaten == []


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
