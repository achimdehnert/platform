"""Tests für tools/sevdesk/zahlungsabgleich.py — Zahlungsabgleich + Mahnkandidaten (K4, platform#3102).

Die sevdesk-API wird über ``httpx.MockTransport`` simuliert, keine echte Anfrage
verlässt den Prozess. Kunden-/Zahlerdaten sind synthetisch — nie echte Namen oder
Beträge (platform ist öffentlich).
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

import zahlungsabgleich as za  # noqa: E402

HEUTE = dt.date(2026, 9, 12)


# ── Fixture-Bausteine ─────────────────────────────────────────────────────────


def _tx(id_, datum, betrag, name, zweck, status="100", checkaccount_id="7"):
    return {
        "id": id_,
        "valueDate": f"{datum}T00:00:00+02:00",
        "amount": betrag,
        "payeePayerName": name,
        "paymtPurpose": zweck,
        "status": status,
        "checkAccount": {"id": checkaccount_id, "objectName": "CheckAccount"},
    }


def _rechnung(
    id_, nummer, datum, brutto, kunde, timetopay=14, bezahlt="0", status="200"
):
    return {
        "id": id_,
        "invoiceNumber": nummer,
        "invoiceDate": datum,
        "timeToPay": timetopay,
        "status": status,
        "sumGross": brutto,
        "paidAmount": bezahlt,
        "contact": {"id": f"k-{id_}", "objectName": "Contact", "name": kunde},
    }


class _Zustand:
    def __init__(self, transaktionen, rechnungen):
        self.transaktionen = transaktionen
        self.rechnungen = rechnungen
        self.buchungen: list[dict] = []


def _mock_client(zustand: _Zustand) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        # base_url der echten API ist "https://my.sevdesk.de/api/v1" — httpx haengt
        # den Pfad dahinter an, also "/api/v1/Invoice" statt "/Invoice".
        pfad = request.url.path.removeprefix("/api/v1")
        methode = request.method

        if methode == "GET" and pfad == "/CheckAccountTransaction":
            return httpx.Response(200, json={"objects": zustand.transaktionen})

        if methode == "GET" and pfad == "/Invoice":
            status = request.url.params.get("status")
            objekte = [
                r
                for r in zustand.rechnungen
                if status is None or r.get("status") == status
            ]
            return httpx.Response(200, json={"objects": objekte})

        if methode == "PUT" and pfad.endswith("/bookAmount"):
            rechnung_id = pfad.split("/")[2]
            rechnung = next(r for r in zustand.rechnungen if r["id"] == rechnung_id)
            payload = json.loads(request.content)
            rechnung["paidAmount"] = str(
                round(
                    float(rechnung.get("paidAmount") or 0) + float(payload["amount"]), 2
                )
            )
            tx_id = payload["checkAccountTransaction"]["id"]
            for t in zustand.transaktionen:
                if t["id"] == tx_id:
                    t["status"] = "200"  # verknuepft -> faellt aus kuenftigen Laeufen
            zustand.buchungen.append(payload)
            return httpx.Response(
                200,
                json={
                    "id": "log-1",
                    "objectName": "InvoiceLog",
                    "fromStatus": "200",
                    "toStatus": "1000",
                    "ammountPayed": payload["amount"],
                },
            )

        if methode == "GET" and pfad.startswith("/Invoice/"):
            rechnung_id = pfad.split("/")[2]
            rechnung = next(
                (r for r in zustand.rechnungen if r["id"] == rechnung_id), None
            )
            return httpx.Response(200, json={"objects": [rechnung] if rechnung else []})

        raise AssertionError(f"unerwarteter Call im Test: {methode} {pfad}")

    return httpx.Client(
        base_url="https://my.sevdesk.de/api/v1", transport=httpx.MockTransport(handler)
    )


def _lauf(monkeypatch, zustand: _Zustand, argv: list[str]):
    monkeypatch.setattr(za, "_client", lambda: _mock_client(zustand))
    monkeypatch.setattr(
        sys, "argv", ["zahlungsabgleich.py", *argv, "--heute", HEUTE.isoformat()]
    )
    return za.main()


# ── zuordnen(): die drei Stufen ────────────────────────────────────────────────


def test_should_match_single_invoice_number_in_purpose_as_sicher():
    rechnungen = [
        _rechnung("1", "20260701-001", "2026-07-01", "500.00", "Musterkunde AB")
    ]
    eingang = _tx("t1", "2026-08-01", 500.00, "Musterkunde AB", "RE 20260701-001")
    treffer = za.zuordnen(eingang, rechnungen)
    assert treffer["stufe"] == "sicher"
    assert [r["id"] for r in treffer["rechnungen"]] == ["1"]


def test_should_match_multiple_invoice_numbers_in_sammelueberweisung_as_sicher():
    rechnungen = [
        _rechnung("1", "20260422-270", "2026-04-22", "300.00", "Kunde Eins"),
        _rechnung("2", "20260422-271", "2026-04-22", "200.00", "Kunde Eins"),
    ]
    eingang = _tx(
        "t1",
        "2026-05-01",
        500.00,
        "Kunde Eins",
        "RE 20260422-271 und RE 20260422-270 Sammelzahlung",
    )
    treffer = za.zuordnen(eingang, rechnungen)
    assert treffer["stufe"] == "sicher"
    assert {r["id"] for r in treffer["rechnungen"]} == {"1", "2"}


def test_should_mark_unsicher_when_amount_deviates_skonto():
    rechnungen = [
        _rechnung("1", "20260701-001", "2026-07-01", "500.00", "Musterkunde AB")
    ]
    # 2 % Skonto abgezogen -> Nummer stimmt, Betrag nicht
    eingang = _tx(
        "t1", "2026-08-01", 490.00, "Musterkunde AB", "RE 20260701-001 Skonto"
    )
    treffer = za.zuordnen(eingang, rechnungen)
    assert treffer["stufe"] == "unsicher"
    assert treffer["rechnungen"][0]["id"] == "1"


def test_should_mark_unsicher_when_payer_name_matches_single_invoice_without_number():
    rechnungen = [
        _rechnung(
            "1", "20260701-001", "2026-07-01", "500.00", "Musterkunde Aachen GmbH"
        )
    ]
    eingang = _tx(
        "t1", "2026-08-01", 500.00, "Musterkunde Aachen GmbH", "Ueberweisung, danke"
    )
    treffer = za.zuordnen(eingang, rechnungen)
    assert treffer["stufe"] == "unsicher"
    assert treffer["rechnungen"][0]["id"] == "1"


def test_should_mark_ohne_zuordnung_for_unrelated_deposit():
    rechnungen = [
        _rechnung("1", "20260701-001", "2026-07-01", "500.00", "Musterkunde AB")
    ]
    eingang = _tx("t1", "2026-08-01", 77.50, "Voellig Fremde Firma", "Irgendein Zweck")
    treffer = za.zuordnen(eingang, rechnungen)
    assert treffer["stufe"] == "ohne"
    assert treffer["rechnungen"] == []


def test_should_fall_back_to_ohne_when_named_number_missing_from_open_invoices():
    # Nummer im Zweck genannt, existiert aber nicht (mehr) unter den offenen Rechnungen,
    # und weder Betrag noch Zahlername passen zu einer anderen offenen Rechnung.
    rechnungen = [
        _rechnung("1", "20260701-001", "2026-07-01", "500.00", "Musterkunde AB")
    ]
    eingang = _tx("t1", "2026-08-01", 123.45, "Fremdfirma", "RE 20269999-999")
    treffer = za.zuordnen(eingang, rechnungen)
    assert treffer["stufe"] == "ohne"


# ── Mahnkandidaten ──────────────────────────────────────────────────────────────


def test_should_compute_days_overdue_for_mahnkandidat():
    rechnungen = [
        _rechnung("1", "20260701-001", "2026-07-01", "500.00", "Kunde", timetopay=14)
    ]
    kandidaten = za.mahnkandidaten_ermitteln(rechnungen, set(), HEUTE)
    assert len(kandidaten) == 1
    # faellig = 2026-07-15, heute 2026-09-12 -> 59 Tage
    assert kandidaten[0]["tage_ueberfaellig"] == 59


def test_should_sort_mahnkandidaten_descending_by_days_overdue():
    rechnungen = [
        _rechnung("1", "20260801-001", "2026-08-01", "100.00", "Kunde A", timetopay=14),
        _rechnung("2", "20260601-001", "2026-06-01", "200.00", "Kunde B", timetopay=14),
    ]
    kandidaten = za.mahnkandidaten_ermitteln(rechnungen, set(), HEUTE)
    assert [k["rechnung"]["id"] for k in kandidaten] == ["2", "1"]


def test_should_exclude_already_matched_invoice_from_mahnkandidaten():
    rechnungen = [
        _rechnung("1", "20260701-001", "2026-07-01", "500.00", "Kunde", timetopay=14)
    ]
    kandidaten = za.mahnkandidaten_ermitteln(rechnungen, {"1"}, HEUTE)
    assert kandidaten == []


def test_should_not_flag_not_yet_due_invoice_as_mahnkandidat():
    rechnungen = [
        _rechnung("1", "20260901-001", "2026-09-01", "500.00", "Kunde", timetopay=30)
    ]
    kandidaten = za.mahnkandidaten_ermitteln(rechnungen, set(), HEUTE)
    assert kandidaten == []


# ── --buchen / --ja / Idempotenz ────────────────────────────────────────────────


def test_should_write_nothing_when_buchen_without_ja(monkeypatch):
    zustand = _Zustand(
        transaktionen=[
            _tx("t1", "2026-08-01", 500.00, "Musterkunde AB", "RE 20260701-001")
        ],
        rechnungen=[
            _rechnung("1", "20260701-001", "2026-07-01", "500.00", "Musterkunde AB")
        ],
    )
    rc = _lauf(monkeypatch, zustand, ["--buchen"])
    assert zustand.buchungen == []
    assert zustand.rechnungen[0]["paidAmount"] == "0"
    assert rc == 0


def test_should_book_only_sichere_zuordnungen_with_ja(monkeypatch, tmp_path):
    monkeypatch.setattr(za, "LOG_VERZEICHNIS", tmp_path)
    zustand = _Zustand(
        transaktionen=[
            _tx("t-sicher", "2026-08-01", 500.00, "Musterkunde AB", "RE 20260701-001"),
            _tx(
                "t-unsicher",
                "2026-08-02",
                490.00,
                "Musterkunde CD",
                "RE 20260702-002 Skonto",
            ),
        ],
        rechnungen=[
            _rechnung("1", "20260701-001", "2026-07-01", "500.00", "Musterkunde AB"),
            _rechnung("2", "20260702-002", "2026-07-02", "500.00", "Musterkunde CD"),
        ],
    )
    rc = _lauf(monkeypatch, zustand, ["--buchen", "--ja"])
    assert len(zustand.buchungen) == 1
    assert zustand.buchungen[0]["checkAccountTransaction"]["id"] == "t-sicher"
    # die unsichere Rechnung 2 bleibt unangetastet
    assert zustand.rechnungen[1]["paidAmount"] == "0"
    assert rc == 2  # unsichere Faelle vorhanden -> Owner-Blick noetig

    log_datei = tmp_path / f"sevdesk-zahlungsabgleich-{HEUTE.isoformat()}.json"
    assert log_datei.exists()
    inhalt = json.loads(log_datei.read_text(encoding="utf-8"))
    assert inhalt[0]["rechnung"] == "20260701-001"


def test_should_skip_already_booked_transaction_on_repeat_run(monkeypatch, tmp_path):
    monkeypatch.setattr(za, "LOG_VERZEICHNIS", tmp_path)
    zustand = _Zustand(
        transaktionen=[
            _tx("t1", "2026-08-01", 500.00, "Musterkunde AB", "RE 20260701-001")
        ],
        rechnungen=[
            _rechnung("1", "20260701-001", "2026-07-01", "500.00", "Musterkunde AB")
        ],
    )
    _lauf(monkeypatch, zustand, ["--buchen", "--ja"])
    assert len(zustand.buchungen) == 1

    # Wiederholung: dieselbe Transaktion steht jetzt (vom Fake-Client gesetzt) auf
    # Status 200 (verknuepft) und wird beim erneuten Abruf nicht mehr als offen geliefert.
    rc = _lauf(monkeypatch, zustand, ["--buchen", "--ja"])
    assert len(zustand.buchungen) == 1  # nicht doppelt
    assert rc == 0


# ── Positivkontrolle: bekannter Treffer Ende-zu-Ende ────────────────────────────


def test_should_reproduce_known_fixture_end_to_end(monkeypatch, capsys):
    zustand = _Zustand(
        transaktionen=[
            _tx("t1", "2026-08-15", 250.00, "Musterkunde XY", "RE 20260801-005")
        ],
        rechnungen=[
            _rechnung("1", "20260801-005", "2026-08-01", "250.00", "Musterkunde XY")
        ],
    )
    rc = _lauf(monkeypatch, zustand, [])
    ausgabe = capsys.readouterr().out
    assert rc == 0
    assert "Sicher zugeordnet (1)" in ausgabe
    assert "20260801-005" in ausgabe


def test_should_return_exit_code_2_when_unsichere_faelle_vorhanden(monkeypatch):
    zustand = _Zustand(
        transaktionen=[
            _tx("t1", "2026-08-01", 490.00, "Musterkunde AB", "RE 20260701-001 Skonto")
        ],
        rechnungen=[
            _rechnung("1", "20260701-001", "2026-07-01", "500.00", "Musterkunde AB")
        ],
    )
    rc = _lauf(monkeypatch, zustand, [])
    assert rc == 2


def test_should_return_exit_code_3_on_api_error(monkeypatch):
    def _explodierender_client():
        raise httpx.ConnectError("kein Netz (Test)")

    monkeypatch.setattr(za, "_client", _explodierender_client)
    monkeypatch.setattr(sys, "argv", ["zahlungsabgleich.py"])
    assert za.main() == 3


def test_should_emit_valid_json_with_json_flag(monkeypatch, capsys):
    zustand = _Zustand(
        transaktionen=[
            _tx("t1", "2026-08-15", 250.00, "Musterkunde XY", "RE 20260801-005")
        ],
        rechnungen=[
            _rechnung("1", "20260801-005", "2026-08-01", "250.00", "Musterkunde XY")
        ],
    )
    _lauf(monkeypatch, zustand, ["--json"])
    ausgabe = capsys.readouterr().out
    daten = json.loads(ausgabe)
    assert daten["sicher"][0]["rechnungen"] == ["20260801-005"]
    assert daten["gebucht"] == []
