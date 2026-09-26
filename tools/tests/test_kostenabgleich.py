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


# ── Stufe "intern": Beleg ohne Dokument nach Regel (Bausteine 1/2/5, 2026-09-17) ──


class _SevdeskIntern(_Sevdesk):
    """Erweiterter Fake: AccountDatev, ReceiptGuidance/forAccountNumber,
    saveVoucher (legt Beleg an), bookAmount mit Typ/Betrag-Mitschrift."""

    def __init__(self, tx, belege, guidance, konten=None, erlaubt=None):
        super().__init__(tx, belege, guidance)
        self.konten = konten or {"6110": "4120", "6855": "4285", "2100": "2838"}
        self.erlaubt = erlaubt or {"6110": ["9"], "6855": ["9"], "2100": ["16"]}
        self.angelegt: list[dict] = []
        self.buchungen: list[dict] = []
        self._naechste = 900

    def handler(self, request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if request.method == "GET" and pfad.endswith("/AccountDatev"):
            raise AssertionError(
                "GET /AccountDatev listet nur 100 aktive Konten (2100 fehlt) — "
                "Konto-ID kommt aus ReceiptGuidance/forAccountNumber"
            )
        if request.method == "GET" and pfad.endswith(
            "/ReceiptGuidance/forAccountNumber"
        ):
            nr = request.url.params.get("accountNumber")
            if nr not in self.erlaubt:
                return httpx.Response(200, json={"objects": []})
            # sevdesk liefert bei einem Treffer ein Dict statt Liste (#3109);
            # accountDatevId ist die einzige verlaessliche Quelle fuer die Konto-ID
            return httpx.Response(
                200,
                json={
                    "objects": {
                        "accountNumber": nr,
                        "accountDatevId": int(self.konten[nr]),
                        "allowedTaxRules": [{"id": int(r)} for r in self.erlaubt[nr]],
                    }
                },
            )
        if request.method == "POST" and pfad.endswith("/Voucher/Factory/saveVoucher"):
            form = dict(kv.split("=", 1) for kv in request.read().decode().split("&"))
            from urllib.parse import unquote_plus

            form = {unquote_plus(k): unquote_plus(v) for k, v in form.items()}
            self._naechste += 1
            beleg = {
                "id": str(self._naechste),
                "status": "100",
                "sumGross": float(form["voucherPosSave[0][sumGross]"]),
                "paidAmount": "0",
                "form": form,
            }
            self.belege[beleg["id"]] = beleg
            self.angelegt.append(beleg)
            return httpx.Response(200, json={"objects": {"voucher": beleg}})
        if request.method == "PUT" and "/bookAmount" in pfad:
            beleg_id = pfad.split("/Voucher/")[1].split("/")[0]
            payload = json.loads(request.read().decode())
            self.buchungen.append({"beleg_id": beleg_id, **payload})
            beleg = self.belege[beleg_id]
            beleg["paidAmount"] = float(beleg["paidAmount"] or 0) + abs(
                payload["amount"]
            )
            if (
                abs(float(beleg["paidAmount"]) - float(beleg["sumGross"])) <= 0.01
                or payload["type"] == "O"
            ):
                beleg["status"] = "1000"
                beleg["paidAmount"] = beleg["sumGross"]
            self.gebuchte_ids.append(beleg_id)
            return httpx.Response(200, json={"objects": beleg})
        return super().handler(request)


def _konten(tmp_path, regeln: list[dict]) -> Path:
    pfad = tmp_path / "sevdesk-konten.json"
    pfad.write_text(json.dumps({"regeln": regeln}), encoding="utf-8")
    return pfad


REGEL_SOZIALVERS = {
    "muster": "knappschaft|rentenversicherung",
    "konto": "6110",
    "bezeichnung": "Sozialvers.-Beiträge",
    "beleg": "ohne_dokument",
    "taxrule": "9",
    "steuersatz": 0,
    "lieferant": "Knappschaft-Bahn-See",
    "beschreibung": "Sozialversicherung Beitrag",
    "autonom": True,
}
REGEL_KONTOABSCHLUSS = {
    "muster": "abschluss per",
    "konto": "6855",
    "bezeichnung": "Kontoführung",
    "beleg": "ohne_dokument",
    "klasse": "kontoabschluss_paar",
    "ust_muster": r"umsatzsteuer auf eur ([\d.,]+)-? abrechnung per",
    "taxrule": "9",
    "lieferant": "Bank – Kontoführung",
    "beschreibung": "Kontoabschluss",
    "autonom": True,
}


def test_should_create_and_book_intern_voucher_when_rule_has_mandate(
    monkeypatch, tmp_path
):
    sevdesk = _SevdeskIntern(
        [
            _tx(
                "t1",
                "2026-03-27",
                -215.46,
                "Deutsche Rentenversicherung KBS",
                "BEITRAG 0326",
            )
        ],
        [],
        [],
    )
    konten = _konten(tmp_path, [REGEL_SOZIALVERS])
    code = _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja", "--json"])
    assert code == 0
    assert len(sevdesk.angelegt) == 1
    form = sevdesk.angelegt[0]["form"]
    assert form["voucher[status]"] == "100"
    assert form["voucher[supplierName]"] == "Knappschaft-Bahn-See"
    assert form["voucher[description]"] == "Sozialversicherung Beitrag 03/2026"
    assert form["voucher[taxRule][id]"] == "9"
    assert form["voucherPosSave[0][accountDatev][id]"] == "4120"
    assert form["voucherPosSave[0][sumGross]"] == "215.46"
    assert form["voucherPosSave[0][sumTax]"] == "0.00"
    (b,) = sevdesk.buchungen
    assert b["type"] == "FULL_PAYMENT" and b["amount"] == -215.46
    assert b["date"] == "27.03.2026"  # Zahldatum = Umsatzdatum, nicht --heute
    assert b["checkAccountTransaction"]["id"] == "t1"


def test_should_list_intern_but_not_book_without_mandate(monkeypatch, tmp_path, capsys):
    sevdesk = _SevdeskIntern(
        [_tx("t1", "2026-03-27", -215.46, "Knappschaft-Bahn-See", "BEITRAG 0326")],
        [],
        [],
    )
    regel = dict(REGEL_SOZIALVERS, autonom=False)
    konten = _konten(tmp_path, [regel])
    code = _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja", "--json"])
    daten = json.loads(capsys.readouterr().out)
    assert code == 2
    assert daten["kennzahlen"]["intern"] == 1
    assert daten["kennzahlen"]["intern_ohne_mandat"] == 1
    assert "Mandat fehlt" in daten["intern"][0]["grund"]
    assert sevdesk.angelegt == [] and sevdesk.buchungen == []


def test_should_not_treat_partial_sammelueberweisung_as_intern(
    monkeypatch, tmp_path, capsys
):
    regel = dict(REGEL_SOZIALVERS, muster="sammel", nur_betraege=[850.0])
    sevdesk = _SevdeskIntern(
        [_tx("t1", "2026-03-27", -901.18, "", "SEPA Sammel-Ueberweisung")], [], []
    )
    konten = _konten(tmp_path, [regel])
    _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja", "--json"])
    daten = json.loads(capsys.readouterr().out)
    assert daten["kennzahlen"]["intern"] == 0
    assert daten["beleg_fehlt"][0]["grund"].startswith("Regel 6110: NUR TEILWEISE")
    assert sevdesk.angelegt == []


def test_should_refuse_intern_booking_when_tax_rule_not_allowed(
    monkeypatch, tmp_path, capsys
):
    regel = dict(
        REGEL_SOZIALVERS, konto="6110", taxrule="1"
    )  # 1 = USt-pflichtige Umsaetze
    sevdesk = _SevdeskIntern(
        [_tx("t1", "2026-03-27", -215.46, "Knappschaft-Bahn-See", "BEITRAG 0326")],
        [],
        [],
    )
    konten = _konten(tmp_path, [regel])
    code = _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja"])
    out = capsys.readouterr().out
    assert code == 3 and "Steuerregel 1 laut ReceiptGuidance nicht erlaubt" in out
    assert sevdesk.angelegt == [] and sevdesk.buchungen == []


def test_should_refuse_intern_booking_for_account_without_guidance(
    monkeypatch, tmp_path, capsys
):
    """7600 Koerperschaftsteuer hat keine ReceiptGuidance — nicht belegbuchbar."""
    regel = dict(REGEL_SOZIALVERS, konto="7600", muster="koerpst")
    sevdesk = _SevdeskIntern(
        [_tx("t1", "2026-03-27", -123.43, "Finanzamt", "KOERPST 1VJ.26")], [], []
    )
    konten = _konten(tmp_path, [regel])
    code = _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja"])
    out = capsys.readouterr().out
    assert code == 3 and "Konto 7600: keine ReceiptGuidance" in out
    assert sevdesk.angelegt == []


def test_should_book_deactivated_privatentnahme_account_via_guidance_id(
    monkeypatch, tmp_path
):
    """2100 fehlt in GET /AccountDatev (deactivated), ReceiptGuidance kennt die ID 2838."""
    regel = {
        "muster": "spotify",
        "konto": "2100",
        "bezeichnung": "Privatentnahme",
        "beleg": "ohne_dokument",
        "taxrule": "16",
        "beschreibung": "Privatentnahme",
        "autonom": True,
    }
    sevdesk = _SevdeskIntern(
        [
            _tx(
                "t1",
                "2026-08-20",
                -21.99,
                "PayPal Europe",
                "1052/PP.1321.PP/. Spotify AB, Ihr Einkauf bei Spotify AB",
            )
        ],
        [],
        [],
    )
    konten = _konten(tmp_path, [regel])
    code = _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja"])
    assert code == 0
    form = sevdesk.angelegt[0]["form"]
    assert form["voucherPosSave[0][accountDatev][id]"] == "2838"
    assert form["voucher[taxRule][id]"] == "16"
    assert form["voucher[supplierName]"] == "Spotify AB"


def test_should_write_log_per_booking_so_abort_keeps_earlier_entries(
    monkeypatch, tmp_path
):
    """Abbruch bei Position 2 (7600 ohne Guidance) — Position 1 steht trotzdem im Log."""
    sevdesk = _SevdeskIntern(
        [
            _tx("t1", "2026-03-27", -215.46, "Knappschaft-Bahn-See", "BEITRAG 0326"),
            _tx("t2", "2026-03-28", -123.43, "Finanzamt", "KOERPST 1VJ.26"),
        ],
        [],
        [],
    )
    konten = _konten(
        tmp_path,
        [REGEL_SOZIALVERS, dict(REGEL_SOZIALVERS, konto="7600", muster="koerpst")],
    )
    monkeypatch.setattr(ka, "LOG_VERZEICHNIS", tmp_path)
    code = _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja"])
    assert code == 3
    log = json.loads((tmp_path / "sevdesk-kostenabgleich-2026-04-15.json").read_text())
    assert [e["umsatz_id"] for e in log] == ["t1"] and log[0]["ausgefuehrt"] is True


def test_should_book_kontoabschluss_pair_as_one_voucher_with_two_partial_payments(
    monkeypatch, tmp_path
):
    sevdesk = _SevdeskIntern(
        [
            _tx("g1", "2026-02-28", -25.30, "", "ABSCHLUSS PER 28.02.2026"),
            # Bank-Tippfehler „per 30.02.2026" — Zuordnung ueber die Basis 25,30
            _tx(
                "u1",
                "2026-04-12",
                -4.81,
                "",
                "19% Umsatzsteuer auf EUR 25,30- Abrechnung per 30.02.2026 von Konto 1",
            ),
            _tx("g2", "2026-03-31", -21.30, "", "ABSCHLUSS PER 31.03.2026"),
        ],
        [],
        [],
    )
    konten = _konten(tmp_path, [REGEL_KONTOABSCHLUSS])
    code = _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja", "--json"])
    assert code == 2  # g2 wartet noch auf seine USt-Zeile
    assert len(sevdesk.angelegt) == 1
    form = sevdesk.angelegt[0]["form"]
    assert form["voucherPosSave[0][sumNet]"] == "25.30"
    assert form["voucherPosSave[0][sumTax]"] == "4.81"  # Bankzeile 1:1, nicht gerechnet
    assert form["voucherPosSave[0][sumGross]"] == "30.11"
    assert form["voucherPosSave[0][taxRate]"] == "19"
    assert form["voucher[description]"] == "Kontoabschluss 02/2026"
    typen = [
        (b["type"], b["amount"], b["checkAccountTransaction"]["id"], b["date"])
        for b in sevdesk.buchungen
    ]
    assert typen == [
        ("N", -25.30, "g1", "28.02.2026"),
        ("N", -4.81, "u1", "12.04.2026"),
    ]


def test_should_hold_fee_without_ust_line_and_report_it(monkeypatch, tmp_path, capsys):
    sevdesk = _SevdeskIntern(
        [_tx("g2", "2026-03-31", -21.30, "", "ABSCHLUSS PER 31.03.2026")], [], []
    )
    konten = _konten(tmp_path, [REGEL_KONTOABSCHLUSS])
    _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja", "--json"])
    daten = json.loads(capsys.readouterr().out)
    assert (
        daten["intern"][0]["grund"] == "Regel 6855: wartet auf die USt-Zeile der Bank"
    )
    assert daten["intern"][0]["buchbar"] is False
    assert sevdesk.angelegt == []


def test_should_not_pair_when_ust_is_not_19_percent_of_fee():
    abgaenge = [
        _tx("g1", "2026-02-28", -25.30, "", "ABSCHLUSS PER 28.02.2026"),
        _tx(
            "u1",
            "2026-04-12",
            -9.99,
            "",
            "19% Umsatzsteuer auf EUR 25,30- Abrechnung per 28.02.2026",
        ),
    ]
    paare = ka.kontoabschluss_paare(abgaenge, [REGEL_KONTOABSCHLUSS])
    assert paare == {"_ust_ids": set()}


# ── Toleranz: Cent-Rundung und Fremdwaehrung → Typ O (Baustein 2) ────────────


def test_should_match_voucher_one_cent_off_and_book_with_type_o(monkeypatch, tmp_path):
    sevdesk = _SevdeskIntern(
        [_tx("t1", "2026-04-20", -134.00, "Hetzner Online GmbH")],
        [_beleg("v1", "2026-04-16", 133.99, "Hetzner")],
        [],
    )
    konten = _konten(tmp_path, [])
    code = _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja"])
    assert code == 0
    (b,) = sevdesk.buchungen
    assert b["type"] == "O" and b["amount"] == -134.00  # Bankbetrag, nicht Belegbetrag


def test_should_match_usd_voucher_within_exchange_tolerance(
    monkeypatch, tmp_path, capsys
):
    beleg = dict(_beleg("v1", "2026-08-03", 156.83, "GitHub, Inc."), currency="USD")
    sevdesk = _SevdeskIntern(
        [
            _tx(
                "t1",
                "2026-08-05",
                -164.71,
                "PayPal Europe",
                "1050/PP.6820.PP/. GitHub, Inc., Ihr Einkauf bei GitHub",
            )
        ],
        [beleg],
        [],
    )
    konten = _konten(tmp_path, [])
    code = _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--buchen", "--ja", "--json"])
    daten = json.loads(capsys.readouterr().out)
    assert code == 0
    assert daten["beleg_vorhanden"][0]["kursdifferenz"] == 7.88
    assert "Typ O" in daten["beleg_vorhanden"][0]["grund"]
    (b,) = sevdesk.buchungen
    assert b["type"] == "O" and b["amount"] == -164.71


def test_should_not_match_eur_voucher_outside_cent_tolerance(
    monkeypatch, tmp_path, capsys
):
    sevdesk = _SevdeskIntern(
        [_tx("t1", "2026-08-05", -164.71, "Hoster GmbH")],
        [_beleg("v1", "2026-08-03", 156.83, "Hoster GmbH")],  # EUR, 5 % daneben
        [],
    )
    konten = _konten(tmp_path, [])
    _lauf(monkeypatch, sevdesk, konten, tmp_path, ["--json"])
    daten = json.loads(capsys.readouterr().out)
    assert (
        daten["kennzahlen"]["beleg_fehlt"] == 1 and daten["kennzahlen"]["sicher"] == 0
    )
