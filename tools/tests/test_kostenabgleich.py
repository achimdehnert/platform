"""Tests für tools/sevdesk/kostenabgleich.py — Kostenabgleich (K7, platform#3102).

sevdesk wird über ``httpx.MockTransport`` simuliert, keine echte Anfrage verlässt
den Prozess. Alle Namen/Beträge sind synthetisch (öffentliches Repo).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

import kostenabgleich as ka  # noqa: E402


# ── Fixtures: synthetische sevdesk-Objekte ─────────────────────────────────


def _tx(
    id_: str, datum: str, betrag: float, name: str, zweck: str = "", status: str = "100"
) -> dict:
    return {
        "id": id_,
        "valueDate": f"{datum}T00:00:00+02:00",
        "amount": betrag,
        "payeePayerName": name,
        "paymtPurpose": zweck,
        "status": status,
        "checkAccount": {"id": "ca-1", "objectName": "CheckAccount"},
    }


def _beleg(
    id_: str, datum: str, betrag: float, lieferant: str, status: str = "100"
) -> dict:
    return {
        "id": id_,
        "voucherDate": f"{datum}T00:00:00+02:00",
        "sumGross": betrag,
        "paidAmount": "0",
        "supplierName": lieferant,
        "status": status,
        "creditDebit": "C",
    }


def _guidance(nummer: str, name: str, beschreibung: str = "") -> dict:
    return {"accountNumber": nummer, "accountName": name, "description": beschreibung}


class _Sevdesk:
    """Minimaler In-Memory-sevdesk fuer httpx.MockTransport — GET Liste/Einzel,
    PUT bookAmount aktualisiert paidAmount fuer die anschliessende Kontrolle."""

    def __init__(self, tx: list[dict], belege: list[dict], guidance: list[dict]):
        self.tx = tx
        self.belege = {v["id"]: v for v in belege}
        self.guidance = guidance
        self.gebuchte_ids: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if request.method == "GET" and pfad.endswith("/CheckAccountTransaction"):
            return httpx.Response(200, json={"objects": self.tx})
        if request.method == "GET" and pfad.endswith("/Voucher"):
            return httpx.Response(200, json={"objects": list(self.belege.values())})
        if request.method == "GET" and pfad.endswith("/ReceiptGuidance/forExpense"):
            return httpx.Response(200, json={"objects": self.guidance})
        if request.method == "PUT" and "/bookAmount" in pfad:
            beleg_id = pfad.split("/Voucher/")[1].split("/")[0]
            beleg = self.belege[beleg_id]
            beleg["paidAmount"] = beleg["sumGross"]
            self.gebuchte_ids.append(beleg_id)
            return httpx.Response(200, json={"objects": beleg})
        if request.method == "GET" and "/Voucher/" in pfad:
            beleg_id = pfad.rsplit("/", 1)[-1]
            return httpx.Response(200, json={"objects": [self.belege[beleg_id]]})
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {pfad}")


def _client(sevdesk: _Sevdesk) -> httpx.Client:
    return httpx.Client(
        base_url="https://my.sevdesk.de/api/v1",
        transport=httpx.MockTransport(sevdesk.handler),
    )


@pytest.fixture()
def konten_datei(tmp_path) -> Path:
    pfad = tmp_path / "sevdesk-konten.json"
    pfad.write_text(
        json.dumps(
            {
                "regeln": [
                    {"muster": "hoster", "konto": "6837", "bezeichnung": "Lizenzen"}
                ]
            }
        ),
        encoding="utf-8",
    )
    return pfad


def _lauf(
    monkeypatch,
    sevdesk: _Sevdesk,
    konten_datei: Path,
    tmp_path,
    argv: list[str] | None = None,
):
    monkeypatch.setattr(ka, "client", lambda mandant: _client(sevdesk))
    ziel = tmp_path / "board.md"
    args = [
        "kostenabgleich.py",
        "--konten",
        str(konten_datei),
        "--ziel",
        str(ziel),
        "--heute",
        "2026-04-15",
    ]
    args += argv or []
    monkeypatch.setattr(sys, "argv", args)
    exit_code = ka.main()
    return exit_code


# ── Grundzuordnung: sicher / unklar / fehlend ──────────────────────────────


def test_should_mark_beleg_vorhanden_when_amount_name_and_date_match(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -119.00, "Muster Hoster GmbH", "Rechnung April")],
        belege=[_beleg("b1", "2026-04-03", 119.00, "Muster Hoster GmbH")],
        guidance=[],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    assert code == 0
    assert "Beleg vorhanden (buchbar) (1)" in ausgabe
    assert "6837" in ausgabe  # Kontovorschlag aus der Regel


def test_should_mark_unklar_when_two_vouchers_match_amount_and_name(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -50.00, "Muster Hoster GmbH")],
        belege=[
            _beleg("b1", "2026-04-01", 50.00, "Muster Hoster GmbH"),
            _beleg("b2", "2026-04-10", 50.00, "Muster Hoster AG"),
        ],
        guidance=[],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    assert code == 2
    assert "Unklar (1)" in ausgabe
    assert "Beleg vorhanden (buchbar) (0)" in ausgabe


def test_should_mark_beleg_fehlt_when_no_voucher_matches_amount(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -77.70, "Unbekannte Firma")],
        belege=[_beleg("b1", "2026-04-01", 12.34, "Andere Firma")],
        guidance=[],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    assert code == 2
    assert "Beleg fehlt (1)" in ausgabe
    assert "77.70" in ausgabe  # Summe Beleg fehlt in der Kennzahlen-Zeile


def test_should_mark_unklar_when_amount_matches_but_no_supplier_name_matches(
    monkeypatch, konten_datei, tmp_path, capsys
):
    """Betrag trifft, Name nicht -> unklar, NICHT Beleg fehlt."""
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -30.00, "Voellig Anderer Zahler")],
        belege=[_beleg("b1", "2026-04-01", 30.00, "Muster Hoster GmbH")],
        guidance=[],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    assert code == 2
    assert "Unklar (1)" in ausgabe
    assert "Beleg fehlt (0)" in ausgabe


def test_should_ignore_legal_form_fillwords_when_matching_names(
    monkeypatch, konten_datei, tmp_path, capsys
):
    """'GmbH'/'AG' duerfen keine Firma faelschlich gleichsetzen; das
    gemeinsame Wort 'Muster' traegt die Zuordnung."""
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -25.00, "Muster GmbH")],
        belege=[_beleg("b1", "2026-04-01", 25.00, "Muster AG")],
        guidance=[],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    assert code == 0
    assert "Beleg vorhanden (buchbar) (1)" in ausgabe


# ── Wiederkehrend ────────────────────────────────────────────────────────


def test_should_detect_recurring_charge_across_three_consecutive_months(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[
            _tx("t1", "2026-02-05", -49.99, "Miete Beispiel GmbH"),
            _tx("t2", "2026-03-05", -49.99, "Miete Beispiel GmbH"),
            _tx("t3", "2026-04-05", -49.99, "Miete Beispiel GmbH"),
        ],
        belege=[
            _beleg("b1", "2026-02-03", 49.99, "Miete Beispiel GmbH"),
            _beleg("b2", "2026-03-03", 49.99, "Miete Beispiel GmbH"),
            _beleg("b3", "2026-04-03", 49.99, "Miete Beispiel GmbH"),
        ],
        guidance=[],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path, argv=["--tage", "120"])
    ausgabe = capsys.readouterr().out
    assert code == 0
    assert "wiederkehrend (3x)" in ausgabe
    assert "3 wiederkehrend" in ausgabe


def test_should_flag_missing_receipt_for_this_month_when_earlier_month_had_one(
    monkeypatch, konten_datei, tmp_path, capsys
):
    # April weicht bewusst um 0,16 EUR vom Maerz-Betrag ab (realistische
    # Schwankung, noch innerhalb der Wiederkehrend-Toleranz 0,50) — nur so
    # bleibt es "Beleg fehlt" statt eines Betragstreffers auf den alten Beleg.
    sevdesk = _Sevdesk(
        tx=[
            _tx("t1", "2026-03-05", -49.99, "Miete Beispiel GmbH"),
            _tx("t2", "2026-04-05", -50.15, "Miete Beispiel GmbH"),
        ],
        belege=[
            _beleg("b1", "2026-03-03", 49.99, "Miete Beispiel GmbH")
        ],  # nur Maerz hat einen Beleg
        guidance=[],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path, argv=["--tage", "120"])
    ausgabe = capsys.readouterr().out
    assert code == 2
    assert "wiederkehrend (2x)" in ausgabe
    assert "Beleg fuer diesen Monat fehlt" in ausgabe


def test_should_not_mark_recurring_when_only_one_month_has_the_charge(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -49.99, "Einmalzahler GmbH")],
        belege=[_beleg("b1", "2026-04-03", 49.99, "Einmalzahler GmbH")],
        guidance=[],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    assert code == 0
    assert "0 wiederkehrend" in ausgabe
    assert (
        "wiederkehrend (" not in ausgabe
    )  # keine "(Nx)"-Markierung in irgendeiner Zeile


# ── Kontovorschlag: Regel vor Guidance ──────────────────────────────────


def test_should_prefer_konten_json_rule_over_receipt_guidance(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -10.00, "Hoster Beispiel")],
        belege=[_beleg("b1", "2026-04-03", 10.00, "Hoster Beispiel")],
        guidance=[_guidance("6300", "Sonstige Aufwendungen", "hoster mieten")],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    assert code == 0
    assert "6837" in ausgabe
    assert "6300" not in ausgabe


def test_should_fall_back_to_receipt_guidance_when_no_rule_matches(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -10.00, "Buerobedarf Beispiel")],
        belege=[_beleg("b1", "2026-04-03", 10.00, "Buerobedarf Beispiel")],
        guidance=[_guidance("4930", "Buerobedarf", "Kosten fuer Buerobedarf")],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    assert code == 0
    assert "4930" in ausgabe


def test_should_show_dash_when_neither_rule_nor_guidance_matches(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -10.00, "Voellig Unbekannt")],
        belege=[_beleg("b1", "2026-04-03", 10.00, "Voellig Unbekannt")],
        guidance=[_guidance("4930", "Buerobedarf", "Kosten fuer Buerobedarf")],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    assert code == 0
    assert "| — |" in ausgabe


# ── guidance_treffer: nur Zahlername, Stoppwoerter, Mindesttreffer (K7-Fix, #3102) ──
# Echtlauf-Fehlfall 2026-09-12: ein Hosting-Anbieter wurde ueber ein Fuellwort im
# Bank-Verwendungszweck faelschlich als "Freiwillige soziale Aufwendungen" vorgeschlagen.


def test_should_not_suggest_when_only_a_purpose_fillword_matches():
    """Der beschriebene Fehlfall: Zweck traegt ein Fuellwort, das zufaellig zum
    Kontonamen passt — der Zahlername selbst hat keine Gemeinsamkeit. Muss
    seit dem Fix KEINEN Vorschlag mehr liefern (vorher: Treffer ueber Zweck)."""
    guidance = [_guidance("4630", "Freiwillige soziale Aufwendungen")]
    treffer = ka.guidance_treffer(guidance, "Beispiel Hosting GmbH")
    assert treffer == []


def test_should_suggest_when_single_payer_word_is_long_enough():
    """Ein echter Treffer: ein Zahler-Wort ab 7 Zeichen im Kontonamen reicht allein."""
    guidance = [_guidance("4930", "IT-Dienstleistungen Beispielhosting")]
    treffer = ka.guidance_treffer(guidance, "Beispielhosting AG")
    assert treffer
    assert treffer[0][0] == "4930"


def test_should_suggest_when_two_payer_words_match():
    """Zwei gemeinsame Woerter reichen auch unterhalb der 7-Zeichen-Schwelle."""
    guidance = [_guidance("4930", "Buero Technik Zubehoer")]
    treffer = ka.guidance_treffer(guidance, "Buero Technik Beispiel GmbH")
    assert treffer
    assert treffer[0][0] == "4930"


def test_should_not_suggest_on_single_short_word_match():
    """Ein einzelnes kurzes (< 7 Zeichen) gemeinsames Wort reicht nicht."""
    guidance = [_guidance("4930", "Mieten Raeume")]
    treffer = ka.guidance_treffer(guidance, "Mieten Beispiel GmbH")
    assert treffer == []


def test_should_not_suggest_on_single_stopword_match():
    """Ein einzelnes Wort aus der Stoppliste (z.B. 'online') zaehlt nicht, auch
    wenn es laenger als 7 Zeichen ist."""
    guidance = [_guidance("4930", "Beispiel Online Dienste")]
    treffer = ka.guidance_treffer(guidance, "Andere Online GmbH")
    assert treffer == []


def test_should_ignore_purpose_in_end_to_end_kostenvorschlag(
    monkeypatch, konten_datei, tmp_path, capsys
):
    """End-to-End (kontovorschlag ueber den ganzen Lauf): der Zweck-Fuellwort-
    Fehlfall darf auch ueber die volle Pipeline keinen Vorschlag mehr liefern."""
    sevdesk = _Sevdesk(
        tx=[
            _tx(
                "t1",
                "2026-04-05",
                -10.00,
                "Beispiel Hosting GmbH",
                zweck="Dauerauftrag soziale Zwecke Referenz 123",
            )
        ],
        belege=[],
        guidance=[_guidance("4630", "Freiwillige soziale Aufwendungen")],
    )
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    # code 2: kein offener Beleg zum Betrag -> Status "fehlend" (Owner-Blick noetig,
    # siehe main()) — hier geht es nur um den Kontovorschlag, nicht um den Exit-Code.
    assert code == 2
    assert "4630" not in ausgabe
    assert "| — |" in ausgabe


# ── Buchen: Gate, nur sichere, keine Doppelbuchung ─────────────────────────


def test_should_book_nothing_without_ja_flag(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -19.00, "Muster Hoster GmbH")],
        belege=[_beleg("b1", "2026-04-03", 19.00, "Muster Hoster GmbH")],
        guidance=[],
    )
    _lauf(monkeypatch, sevdesk, konten_datei, tmp_path, argv=["--buchen"])
    assert sevdesk.gebuchte_ids == []
    ausgabe = capsys.readouterr().out
    assert "Vorschau — NICHTS gebucht" in ausgabe


def test_should_book_only_sichere_positions_with_ja_flag(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[
            _tx("t1", "2026-04-05", -19.00, "Muster Hoster GmbH"),  # sicher
            _tx(
                "t2", "2026-04-06", -30.00, "Voellig Anderer Zahler"
            ),  # unklar (Name passt nicht)
        ],
        belege=[
            _beleg("b1", "2026-04-03", 19.00, "Muster Hoster GmbH"),
            _beleg("b2", "2026-04-01", 30.00, "Muster Hoster GmbH"),
        ],
        guidance=[],
    )
    _lauf(monkeypatch, sevdesk, konten_datei, tmp_path, argv=["--buchen", "--ja"])
    assert sevdesk.gebuchte_ids == ["b1"]


def test_should_log_booking_result_to_claude_directory(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -19.00, "Muster Hoster GmbH")],
        belege=[_beleg("b1", "2026-04-03", 19.00, "Muster Hoster GmbH")],
        guidance=[],
    )
    log_verzeichnis = tmp_path / "claude-home"
    monkeypatch.setattr(ka, "LOG_VERZEICHNIS", log_verzeichnis)
    _lauf(monkeypatch, sevdesk, konten_datei, tmp_path, argv=["--buchen", "--ja"])
    log_dateien = list(log_verzeichnis.glob("sevdesk-kostenabgleich-*.json"))
    assert len(log_dateien) == 1
    eintraege = json.loads(log_dateien[0].read_text(encoding="utf-8"))
    assert eintraege[0]["beleg_id"] == "b1"
    assert eintraege[0]["ausgefuehrt"] is True


def test_should_skip_transaction_that_is_no_longer_open_on_repeat_run(
    monkeypatch, konten_datei, tmp_path, capsys
):
    """Nach einer Buchung wechselt die Transaktion den Status (!= 100) — ein
    Wiederholungslauf sieht sie nicht mehr unter den offenen Abgaengen."""
    sevdesk = _Sevdesk(
        tx=[_tx("t1", "2026-04-05", -19.00, "Muster Hoster GmbH", status="200")],
        belege=[_beleg("b1", "2026-04-03", 19.00, "Muster Hoster GmbH")],
        guidance=[],
    )
    code = _lauf(
        monkeypatch, sevdesk, konten_datei, tmp_path, argv=["--buchen", "--ja"]
    )
    assert code == 0
    assert sevdesk.gebuchte_ids == []


# ── Positivkontrolle: leerer Bestand ergibt einen sauberen Nulllauf ────────


def test_should_return_zero_positions_and_exit_0_when_nothing_open(
    monkeypatch, konten_datei, tmp_path, capsys
):
    sevdesk = _Sevdesk(tx=[], belege=[], guidance=[])
    code = _lauf(monkeypatch, sevdesk, konten_datei, tmp_path)
    ausgabe = capsys.readouterr().out
    assert code == 0
    assert "0 Abgaenge geprueft" in ausgabe


def test_should_not_match_the_same_voucher_to_two_debits(monkeypatch):
    """1:1 — ein Beleg deckt genau einen Abgang (Echtprobe 2026-09-13)."""
    import datetime as dt

    tx1 = _tx("t1", "2026-06-11", -10.99, "Abo Anbieter")
    tx2 = _tx("t2", "2026-06-23", -10.99, "Abo Anbieter")
    beleg = _beleg("v1", "2026-06-21", 10.99, "Abo Anbieter", status="50")
    antworten = {
        "/CheckAccountTransaction": [tx1, tx2],
        "/Voucher": [beleg],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path.replace("/api/v1", "")
        if pfad == "/ReceiptGuidance/forExpense":
            return httpx.Response(200, json={"objects": []})
        return httpx.Response(200, json={"objects": antworten.get(pfad, [])})

    c = httpx.Client(
        base_url="https://my.sevdesk.de/api/v1", transport=httpx.MockTransport(handler)
    )
    positionen = ka.positionen_ermitteln(c, dt.date(2026, 9, 13), 120, [])
    stati = [p["status"] for p in positionen]
    assert stati.count("sicher") == 1
    assert [p["beleg"]["id"] for p in positionen if p["status"] == "sicher"] == ["v1"]


def test_should_book_draft_voucher_to_status_100_before_book_amount():
    """Entwurf (50) → saveVoucher Status 100 → bookAmount (Echtprobe 2026-09-13: 422 ohne diesen Schritt)."""
    import datetime as dt

    aufrufe: list[tuple[str, str]] = []
    zustand = {"status": "50", "paid": "0"}

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path.replace("/api/v1", "")
        aufrufe.append((request.method, pfad))
        if pfad == "/VoucherPos":
            return httpx.Response(200, json={"objects": [{"id": "p1"}]})
        if pfad == "/Voucher/Factory/saveVoucher":
            body = request.read().decode()
            assert (
                "voucher%5Bstatus%5D=100" in body
                and "voucherPosSave%5B0%5D%5Bid%5D=p1" in body
            )
            zustand["status"] = "100"
            return httpx.Response(
                200, json={"objects": {"voucher": {"id": "v1", "status": "100"}}}
            )
        if pfad == "/Voucher/v1/bookAmount":
            assert zustand["status"] == "100"
            # Ausgabenbeleg: Zahlung negativ (Echtprobe 2026-09-13, 25 Belege falsch)
            assert json.loads(request.read().decode())["amount"] == -10.99
            zustand["paid"] = "10.99"
            return httpx.Response(200, json={"objects": {"ok": True}})
        if pfad == "/Voucher/v1":
            return httpx.Response(
                200,
                json={
                    "objects": [
                        {
                            "id": "v1",
                            "status": zustand["status"],
                            "sumGross": 10.99,
                            "paidAmount": zustand["paid"],
                        }
                    ]
                },
            )
        raise AssertionError(f"unerwartet: {request.method} {pfad}")

    c = httpx.Client(
        base_url="https://my.sevdesk.de/api/v1", transport=httpx.MockTransport(handler)
    )
    position = {
        "id": "t1",
        "beleg": {"id": "v1", "status": "50", "sumGross": 10.99, "paidAmount": "0"},
        "checkAccount": {"id": "ca"},
    }
    ergebnis = ka.buchen(c, position, dt.date(2026, 9, 13))
    assert ergebnis["warnung"] is None
    pfade = [p for _, p in aufrufe]
    assert pfade.index("/Voucher/Factory/saveVoucher") < pfade.index(
        "/Voucher/v1/bookAmount"
    )


# ── entwurf_buchen: Fremdwaehrung (Befund 2026-09-13, Kurs doppelt gerechnet) ──


def _fremdwaehrung_handler(positionen: list[dict], aufrufe: list[tuple[str, str]]):
    """Ein-Positionen-Entwurf v1: 10,00 USD / 8,68 EUR — saveVoucher liefert
    unveraenderte Fremdwaehrungssumme zurueck (der reparierte Fall)."""

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path.replace("/api/v1", "")
        aufrufe.append((request.method, pfad))
        if pfad == "/VoucherPos":
            return httpx.Response(200, json={"objects": positionen})
        if pfad == "/Voucher/Factory/saveVoucher":
            aufrufe.append(("BODY", request.read().decode()))
            return httpx.Response(200, json={"objects": {"id": "v1", "status": "100"}})
        if pfad == "/Voucher/v1":
            return httpx.Response(
                200,
                json={
                    "objects": [
                        {
                            "id": "v1",
                            "status": "100",
                            "sumGross": 8.68,
                            "sumGrossForeignCurrency": 10.00,
                        }
                    ]
                },
            )
        raise AssertionError(f"unerwartet: {request.method} {pfad}")

    return handler


def test_should_send_foreign_currency_sums_for_single_position_draft():
    aufrufe: list[tuple[str, str]] = []
    positionen = [{"id": "p1", "taxRate": 0}]
    c = httpx.Client(
        base_url="https://my.sevdesk.de/api/v1",
        transport=httpx.MockTransport(_fremdwaehrung_handler(positionen, aufrufe)),
    )
    beleg = {
        "id": "v1",
        "status": "50",
        "currency": "USD",
        "sumNetForeignCurrency": 8.40,
        "sumTaxForeignCurrency": 1.60,
        "sumGrossForeignCurrency": 10.00,
        "sumGross": 8.68,
    }
    danach = ka.entwurf_buchen(c, beleg)
    assert danach["status"] == "100"
    body = next(v for k, v in aufrufe if k == "BODY")
    assert "voucher%5Bcurrency%5D=USD" in body
    assert "voucherPosSave%5B0%5D%5Bnet%5D=false" in body
    assert "voucherPosSave%5B0%5D%5BsumNet%5D=8.4" in body
    assert "voucherPosSave%5B0%5D%5BsumTax%5D=1.6" in body
    assert "voucherPosSave%5B0%5D%5BsumGross%5D=10.0" in body


def test_should_not_send_sums_for_eur_draft():
    aufrufe: list[tuple[str, str]] = []
    positionen = [{"id": "p1", "taxRate": 19}]

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path.replace("/api/v1", "")
        aufrufe.append((request.method, pfad))
        if pfad == "/VoucherPos":
            return httpx.Response(200, json={"objects": positionen})
        if pfad == "/Voucher/Factory/saveVoucher":
            aufrufe.append(("BODY", request.read().decode()))
            return httpx.Response(200, json={"objects": {"id": "v1", "status": "100"}})
        if pfad == "/Voucher/v1":
            return httpx.Response(
                200,
                json={"objects": [{"id": "v1", "status": "100", "sumGross": 19.00}]},
            )
        raise AssertionError(f"unerwartet: {request.method} {pfad}")

    c = httpx.Client(
        base_url="https://my.sevdesk.de/api/v1", transport=httpx.MockTransport(handler)
    )
    beleg = {"id": "v1", "status": "50", "currency": "EUR", "sumGross": 19.00}
    danach = ka.entwurf_buchen(c, beleg)
    assert danach["status"] == "100"
    body = next(v for k, v in aufrufe if k == "BODY")
    assert "sumNet" not in body
    assert "sumTax" not in body
    assert "sumGross" not in body
    assert "voucher%5Bcurrency%5D" not in body
    assert "net%5D=false" not in body


def test_should_raise_for_foreign_currency_draft_with_two_positions():
    aufrufe: list[tuple[str, str]] = []
    positionen = [
        {"id": "p1", "taxRate": 0},
        {"id": "p2", "taxRate": 0},
    ]
    c = httpx.Client(
        base_url="https://my.sevdesk.de/api/v1",
        transport=httpx.MockTransport(_fremdwaehrung_handler(positionen, aufrufe)),
    )
    beleg = {
        "id": "v1",
        "status": "50",
        "currency": "USD",
        "sumNetForeignCurrency": 8.40,
        "sumTaxForeignCurrency": 1.60,
        "sumGrossForeignCurrency": 10.00,
        "sumGross": 8.68,
    }
    with pytest.raises(RuntimeError, match="2 Positionen"):
        ka.entwurf_buchen(c, beleg)
    assert not any(pfad == "/Voucher/Factory/saveVoucher" for _, pfad in aufrufe)


def test_should_raise_when_foreign_currency_sum_changed_after_save():
    aufrufe: list[tuple[str, str]] = []
    positionen = [{"id": "p1", "taxRate": 0}]

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path.replace("/api/v1", "")
        aufrufe.append((request.method, pfad))
        if pfad == "/VoucherPos":
            return httpx.Response(200, json={"objects": positionen})
        if pfad == "/Voucher/Factory/saveVoucher":
            return httpx.Response(200, json={"objects": {"id": "v1", "status": "100"}})
        if pfad == "/Voucher/v1":
            # Kurs doppelt gerechnet: 10.00 -> 8.68 (der urspruengliche Befund)
            return httpx.Response(
                200,
                json={
                    "objects": [
                        {
                            "id": "v1",
                            "status": "100",
                            "sumGross": 7.53,
                            "sumGrossForeignCurrency": 8.68,
                        }
                    ]
                },
            )
        raise AssertionError(f"unerwartet: {request.method} {pfad}")

    c = httpx.Client(
        base_url="https://my.sevdesk.de/api/v1", transport=httpx.MockTransport(handler)
    )
    beleg = {
        "id": "v1",
        "status": "50",
        "currency": "USD",
        "sumNetForeignCurrency": 8.40,
        "sumTaxForeignCurrency": 1.60,
        "sumGrossForeignCurrency": 10.00,
        "sumGross": 8.68,
    }
    with pytest.raises(RuntimeError, match="veraendert"):
        ka.entwurf_buchen(c, beleg)
