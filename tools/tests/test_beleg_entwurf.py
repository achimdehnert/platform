"""Tests für tools/sevdesk/beleg_entwurf.py — Eingangsbeleg-ENTWURF (platform#3102, K6).

Die sevdesk-API wird über ``httpx.MockTransport`` simuliert, keine echte Anfrage
verlässt den Prozess. Lieferanten/Beträge/Kontonummern sind synthetisch — nie die
echten Werte aus der persönlichen Kontenzuordnung (öffentliches Repo).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sevdesk"))

import beleg_entwurf as be  # noqa: E402


@pytest.fixture(autouse=True)
def _isolierte_dateien(tmp_path, monkeypatch):
    """Personenbezogene/lokale Dateien nie aus dem echten ~/.claude lesen/schreiben."""
    monkeypatch.setattr(be, "KONTEN_DATEI", tmp_path / "sevdesk-konten.json")
    monkeypatch.setattr(
        be, "GUIDANCE_CACHE", tmp_path / "sevdesk-receipt-guidance.json"
    )
    monkeypatch.setattr(be, "JOURNAL_DATEI", tmp_path / "sevdesk-belege-journal.jsonl")


def _client(handler) -> httpx.Client:
    return httpx.Client(
        base_url="https://my.sevdesk.de/api/v1", transport=httpx.MockTransport(handler)
    )


def _args(tmp_path, **override) -> argparse.Namespace:
    basis = dict(
        pdf=str(tmp_path / "rechnung.pdf"),
        lieferant="Testlieferant GmbH",
        datum="2026-09-01",
        brutto="119.00",
        steuer="19.00",
        beschreibung="TEST-RE-0001",
        taxrule="9",
        konto="",
        waehrung="EUR",
        kurs="",
        konto_vorschlag=False,
        trotzdem=False,
        strikt=False,
        dry_run=True,
    )
    basis.update(override)
    return argparse.Namespace(**basis)


def _leerer_bestand_handler(zusatz=None):
    """GET /Voucher liefert einen leeren Bestand; alles andere ruft `zusatz` (falls gesetzt)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/v1/Voucher":
            return httpx.Response(200, json={"objects": []})
        if zusatz is not None:
            return zusatz(request)
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {request.url}")

    return handler


# ── Kontovorschlag: Regel, Guidance, kein Treffer ─────────────────────────────


def test_should_suggest_account_from_matching_rule():
    regeln = [
        {
            "muster": "examplehost",
            "konto": "6837",
            "bezeichnung": "Aufwendungen für Lizenzen, Konzessionen",
        }
    ]
    ergebnis = be.vorschlaege(
        "ExampleHost GmbH", "Serverkosten September", regeln, guidance=[]
    )
    assert ergebnis[0]["konto"] == "6837"
    assert ergebnis[0]["quelle"] == "Regel"


def test_should_suggest_account_from_guidance_word_match():
    guidance = [
        {
            "accountNumber": "6805",
            "accountName": "Reisekosten Arbeitnehmer",
            "description": "Reisekosten für Dienstreisen",
        }
    ]
    ergebnis = be.vorschlaege(
        "Bahn AG", "Reisekosten Bahnfahrt September", regeln=[], guidance=guidance
    )
    assert ergebnis[0]["konto"] == "6805"
    assert ergebnis[0]["quelle"] == "Guidance"


def test_should_return_no_suggestions_when_nothing_matches():
    guidance = [
        {"accountNumber": "1234", "accountName": "Sonstiges", "description": ""}
    ]
    ergebnis = be.vorschlaege(
        "Unbekannt GmbH", "voellig andere sache", regeln=[], guidance=guidance
    )
    assert ergebnis == []


def test_should_ignore_legal_form_words_like_gmbh():
    """Echtprobe 2026-09-12: 'gmbh' aus dem Lieferantennamen traf sonst jede
    Kontobezeichnung, die zufällig ebenfalls 'gmbh' enthält (Fehlsignal)."""
    guidance = [
        {
            "accountNumber": "6024",
            "accountName": "Geschäftsführergehälter GmbH-Gesellschafter",
            "description": "",
        }
    ]
    ergebnis = be.vorschlaege(
        "Synthetik-Test GmbH", "Serverkosten September", regeln=[], guidance=guidance
    )
    assert ergebnis == []


def test_should_leave_account_empty_in_dry_run_when_no_suggestion_matches(
    tmp_path, monkeypatch
):
    def zusatz(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/ReceiptGuidance/forExpense":
            return httpx.Response(200, json={"objects": []})
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {request.url}")

    args = _args(tmp_path, konto_vorschlag=True, dry_run=True)
    monkeypatch.setattr(be, "_client", lambda: _client(_leerer_bestand_handler(zusatz)))
    ergebnis = be.anlegen(args)
    assert ergebnis == 0
    zeile = json.loads(be.JOURNAL_DATEI.read_text(encoding="utf-8").splitlines()[-1])
    assert zeile["vorschlaege"] == []
    assert zeile["konto_gesetzt"] is False


# ── Guidance-Cache: 30-Tage-Grenze ─────────────────────────────────────────────


def test_should_reuse_cached_guidance_within_30_days(tmp_path):
    cache_pfad = tmp_path / "cache.json"
    cache_pfad.write_text(
        json.dumps(
            {"datum": date.today().isoformat(), "objects": [{"accountNumber": "1"}]}
        ),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Cache jünger als 30 Tage — kein Netzwerkaufruf erwartet")

    ergebnis = be.guidance_laden(_client(handler), cache_pfad)
    assert ergebnis == [{"accountNumber": "1"}]


def test_should_refetch_guidance_when_cache_older_than_30_days(tmp_path):
    cache_pfad = tmp_path / "cache.json"
    alt = date.today() - timedelta(days=31)
    cache_pfad.write_text(
        json.dumps({"datum": alt.isoformat(), "objects": [{"accountNumber": "alt"}]}),
        encoding="utf-8",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/ReceiptGuidance/forExpense"
        return httpx.Response(200, json={"objects": [{"accountNumber": "neu"}]})

    ergebnis = be.guidance_laden(_client(handler), cache_pfad)
    assert ergebnis == [{"accountNumber": "neu"}]
    neu_geschrieben = json.loads(cache_pfad.read_text(encoding="utf-8"))
    assert neu_geschrieben["objects"] == [{"accountNumber": "neu"}]


# ── Validierung: taxRule gegen ReceiptGuidance/forAccountNumber ───────────────


def test_should_abort_when_taxrule_not_allowed_for_account(
    tmp_path, capsys, monkeypatch
):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/v1/Voucher":
            return httpx.Response(200, json={"objects": []})
        if request.url.path == "/api/v1/ReceiptGuidance/forAccountNumber":
            return httpx.Response(
                200,
                json={
                    "objects": [
                        {
                            "accountNumber": "6837",
                            "allowedTaxRules": [{"id": 9, "name": "USTPFL"}],
                        }
                    ]
                },
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {request.url}")

    args = _args(tmp_path, konto="6837", taxrule="12", dry_run=True)
    monkeypatch.setattr(be, "_client", lambda: _client(handler))
    ergebnis = be.anlegen(args)
    assert ergebnis == 2
    assert "ABBRUCH" in capsys.readouterr().out


# ── konto_validieren: allowedTaxRules als String- ODER Dict-Liste (K6-Fix, #3102) ──
# Echtprobe 2026-09-12 gegen GET /ReceiptGuidance/forAccountNumber: die API liefert
# eine Liste von String-IDs, nicht von Objekten — der alte Code griff auf regel["id"]
# zu und warf AttributeError. Beide Formen müssen validieren.


def test_should_validate_account_when_allowed_tax_rules_are_strings():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "objects": [{"accountNumber": "6837", "allowedTaxRules": ["9", "19"]}]
            },
        )

    ok, fehler = be.konto_validieren(_client(handler), "6837", "9")
    assert ok is True
    assert fehler == ""


def test_should_validate_account_when_allowed_tax_rules_are_dicts():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "objects": [
                    {
                        "accountNumber": "6837",
                        "allowedTaxRules": [{"id": 9, "name": "USTPFL"}, {"id": 19}],
                    }
                ]
            },
        )

    ok, fehler = be.konto_validieren(_client(handler), "6837", "9")
    assert ok is True
    assert fehler == ""


def test_should_validate_account_when_objects_is_a_single_dict():
    """Echte Form der sevdesk-API (Echtprobe 2026-09-12, Konten 6035/6110/6837):
    ``objects`` ist bei genau einem Treffer ein einzelnes Dict, keine Liste —
    der alte Code iterierte dann ueber die Dict-Keys (Strings) und warf
    AttributeError beim ``.get("allowedTaxRules")``."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "objects": {
                    "accountNumber": "6110",
                    "accountName": "Sonstige betriebliche Aufwendungen",
                    "allowedTaxRules": [{"id": 9, "name": "VORST_ABZUGSF_AUFW"}],
                }
            },
        )

    ok, fehler = be.konto_validieren(_client(handler), "6110", "9")
    assert ok is True
    assert fehler == ""


def test_should_reject_disallowed_taxrule_with_string_form():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"objects": [{"accountNumber": "6837", "allowedTaxRules": ["9"]}]},
        )

    ok, fehler = be.konto_validieren(_client(handler), "6837", "12")
    assert ok is False
    assert "nicht erlaubt" in fehler


def test_should_bypass_validation_with_trotzdem(tmp_path, capsys, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/v1/Voucher":
            return httpx.Response(200, json={"objects": []})
        if request.url.path == "/api/v1/ReceiptGuidance/forAccountNumber":
            return httpx.Response(
                200,
                json={
                    "objects": [
                        {
                            "accountNumber": "6837",
                            "allowedTaxRules": [{"id": 9, "name": "USTPFL"}],
                        }
                    ]
                },
            )
        if request.url.path == "/api/v1/AccountDatev":
            return httpx.Response(
                200, json={"objects": [{"id": "501", "number": "6837"}]}
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {request.url}")

    args = _args(tmp_path, konto="6837", taxrule="12", trotzdem=True, dry_run=True)
    monkeypatch.setattr(be, "_client", lambda: _client(handler))
    ergebnis = be.anlegen(args)
    assert ergebnis == 0
    assert "WARNUNG (--trotzdem)" in capsys.readouterr().out


# ── Dedup-Softcheck: Warnung vs. --strikt ─────────────────────────────────────


def _bestand_mit_gleichem_betrag_und_datum():
    return [
        {
            "id": "v-alt",
            "description": "ANDERE-BESCHREIBUNG",
            "sumGross": "119.00",
            "voucherDate": "2026-09-01T00:00:00+02:00",
            "supplierName": "Testlieferant GmbH",
        }
    ]


def test_should_warn_on_soft_duplicate_without_aborting(tmp_path, capsys, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/v1/Voucher":
            return httpx.Response(
                200, json={"objects": _bestand_mit_gleichem_betrag_und_datum()}
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {request.url}")

    args = _args(tmp_path, strikt=False, dry_run=True)
    monkeypatch.setattr(be, "_client", lambda: _client(handler))
    ergebnis = be.anlegen(args)
    assert ergebnis == 0
    ausgabe = capsys.readouterr().out
    assert "WARNUNG" in ausgabe
    assert "Dauerrechnungen" in ausgabe


def test_should_abort_soft_duplicate_with_strikt(tmp_path, capsys, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/v1/Voucher":
            return httpx.Response(
                200, json={"objects": _bestand_mit_gleichem_betrag_und_datum()}
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {request.url}")

    args = _args(tmp_path, strikt=True, dry_run=True)
    monkeypatch.setattr(be, "_client", lambda: _client(handler))
    ergebnis = be.anlegen(args)
    assert ergebnis == 2
    assert "ABBRUCH (--strikt)" in capsys.readouterr().out


def test_should_not_warn_when_supplier_differs():
    bestand = _bestand_mit_gleichem_betrag_und_datum()
    treffer = be.dedup_softcheck(bestand, 119.00, "2026-09-01", "Anderer Lieferant")
    assert treffer is None


# ── Journal: gehashte Beschreibung, keine Klartext-Leckage ────────────────────


def test_should_hash_description_in_journal_not_store_plaintext(tmp_path, monkeypatch):
    handler = _leerer_bestand_handler()
    args = _args(tmp_path, beschreibung="GEHEIME-RECHNUNGSNUMMER-42", dry_run=True)
    monkeypatch.setattr(be, "_client", lambda: _client(handler))
    be.anlegen(args)

    inhalt = be.JOURNAL_DATEI.read_text(encoding="utf-8")
    assert "GEHEIME-RECHNUNGSNUMMER-42" not in inhalt
    zeile = json.loads(inhalt.splitlines()[-1])
    assert len(zeile["beschreibung_hash"]) == 16


# ── Auswertung: Trefferquote über N Journal-Zeilen ────────────────────────────


def test_should_compute_hit_rate_from_journal(tmp_path):
    pfad = tmp_path / "journal.jsonl"
    zeilen = [
        {
            "konto_gesetzt": True,
            "vorschlaege": ["1"],
            "vorschlag_treffer_1": True,
            "vorschlag_top3": True,
        },
        {
            "konto_gesetzt": True,
            "vorschlaege": ["1", "2"],
            "vorschlag_treffer_1": False,
            "vorschlag_top3": True,
        },
        {
            "konto_gesetzt": True,
            "vorschlaege": ["9"],
            "vorschlag_treffer_1": True,
            "vorschlag_top3": True,
        },
        # nicht vergleichbar: kein Vorschlag vorhanden
        {
            "konto_gesetzt": True,
            "vorschlaege": [],
            "vorschlag_treffer_1": False,
            "vorschlag_top3": False,
        },
    ]
    for z in zeilen:
        be.journal_schreiben(z, pfad)

    text = be.auswertung_text(pfad, None)
    assert "Basis: 3 vergleichbare Läufe von 4 Journal-Zeilen." in text
    assert "Vorschlag-1-Trefferquote: 2/3 (67%)" in text
    assert "Vorschlag-in-Top-3-Trefferquote: 3/3 (100%)" in text


def test_should_report_no_journal_when_file_missing(tmp_path):
    text = be.auswertung_text(tmp_path / "fehlt.jsonl", None)
    assert "Kein Journal vorhanden" in text


# ── Regression: bestehende Aufrufe unverändert ────────────────────────────────


def test_should_abort_on_unknown_taxrule(tmp_path, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Unbekannte taxRule muss vor jedem API-Aufruf abbrechen")

    args = _args(tmp_path, taxrule="99", dry_run=False)
    monkeypatch.setattr(be, "_client", lambda: _client(handler))
    assert be.anlegen(args) == 2


def test_should_skip_creation_when_description_already_exists(
    tmp_path, capsys, monkeypatch
):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/v1/Voucher":
            return httpx.Response(
                200,
                json={
                    "objects": [
                        {"id": "v-alt", "description": "TEST-RE-0001", "sumGross": "0"}
                    ]
                },
            )
        raise AssertionError(
            "Duplikat haette abbrechen muessen, statt dessen API-Aufruf"
        )

    args = _args(tmp_path, dry_run=False)
    monkeypatch.setattr(be, "_client", lambda: _client(handler))
    ergebnis = be.anlegen(args)
    assert ergebnis == 0
    assert "DUPLIKAT" in capsys.readouterr().out


def test_should_create_voucher_without_account_when_konto_not_given(
    tmp_path, capsys, monkeypatch
):
    pdf = tmp_path / "rechnung.pdf"
    pdf.write_bytes(b"%PDF-1.4 synthetisch")
    aufgezeichnet: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if request.method == "GET" and pfad == "/api/v1/Voucher":
            return httpx.Response(200, json={"objects": []})
        if (
            request.method == "POST"
            and pfad == "/api/v1/Voucher/Factory/uploadTempFile"
        ):
            return httpx.Response(200, json={"objects": {"filename": "tmp-1.pdf"}})
        if request.method == "POST" and pfad == "/api/v1/Voucher/Factory/saveVoucher":
            from urllib.parse import parse_qsl

            aufgezeichnet["daten"] = dict(parse_qsl(request.read().decode()))
            return httpx.Response(
                200, json={"objects": {"voucher": {"id": "v-99", "status": "50"}}}
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {pfad}")

    args = _args(tmp_path, pdf=str(pdf), dry_run=False)
    monkeypatch.setattr(be, "_client", lambda: _client(handler))
    ergebnis = be.anlegen(args)

    assert ergebnis == 0
    daten = aufgezeichnet["daten"]
    assert daten["voucher[status]"] == "50"
    assert daten["voucher[creditDebit]"] == "C"
    assert daten["voucher[supplierName]"] == "Testlieferant GmbH"
    assert daten["voucher[description]"] == "TEST-RE-0001"
    assert daten["voucher[taxRule][id]"] == "9"
    assert daten["voucherPosSave[0][sumGross]"] == "119.00"
    assert "voucherPosSave[0][accountDatev][id]" not in daten
    ausgabe = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert ausgabe == {
        "beleg_id": "v-99",
        "status": "50",
        "beschreibung": "TEST-RE-0001",
        "brutto": "119.00",
        "konto": "LEER (nicht zugeordnet — Owner)",
    }


def test_should_set_account_when_konto_given_and_valid(tmp_path, capsys, monkeypatch):
    pdf = tmp_path / "rechnung.pdf"
    pdf.write_bytes(b"%PDF-1.4 synthetisch")
    aufgezeichnet: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        pfad = request.url.path
        if request.method == "GET" and pfad == "/api/v1/Voucher":
            return httpx.Response(200, json={"objects": []})
        if pfad == "/api/v1/ReceiptGuidance/forAccountNumber":
            return httpx.Response(
                200,
                json={
                    "objects": [
                        {"accountNumber": "6837", "allowedTaxRules": [{"id": 9}]}
                    ]
                },
            )
        if pfad == "/api/v1/AccountDatev":
            return httpx.Response(
                200, json={"objects": [{"id": "501", "number": "6837"}]}
            )
        if (
            request.method == "POST"
            and pfad == "/api/v1/Voucher/Factory/uploadTempFile"
        ):
            return httpx.Response(200, json={"objects": {"filename": "tmp-1.pdf"}})
        if request.method == "POST" and pfad == "/api/v1/Voucher/Factory/saveVoucher":
            from urllib.parse import parse_qsl

            aufgezeichnet["daten"] = dict(parse_qsl(request.read().decode()))
            return httpx.Response(
                200, json={"objects": {"voucher": {"id": "v-100", "status": "50"}}}
            )
        raise AssertionError(f"unerwarteter Aufruf: {request.method} {pfad}")

    args = _args(tmp_path, pdf=str(pdf), konto="6837", taxrule="9", dry_run=False)
    monkeypatch.setattr(be, "_client", lambda: _client(handler))
    ergebnis = be.anlegen(args)

    assert ergebnis == 0
    daten = aufgezeichnet["daten"]
    assert daten["voucherPosSave[0][accountDatev][id]"] == "501"
    assert daten["voucherPosSave[0][accountDatev][objectName]"] == "AccountDatev"
    ausgabe = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert ausgabe["konto"] == "6837"
