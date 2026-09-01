"""Tests fuer die Graph-Selbstheilung der Kurzlinks (platform#2563, #2592 K2).

Graph wird durch eine Tabelle URL-Muster → Antwort ersetzt. Ein Test, der die
echte Reihenfolge der drei Wege (gueltig → internetMessageId → Betreff) nicht
festhaelt, wuerde ein Raten durchlassen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

ga = pytest.importorskip("graph_anker")


class _Resp:
    def __init__(self, status, body=None):
        self.status_code = status
        self.text = json.dumps(body) if body is not None else ""

    def json(self):
        return json.loads(self.text) if self.text else {}


def _http(antworten: dict):
    """Attrappe: waehlt die Antwort ueber ein Teilstueck der entschluesselten URL."""
    aufrufe: list[str] = []

    def http(method, url, **_kw):
        klar = unquote(url)
        aufrufe.append(klar)
        for muster, antwort in antworten.items():
            if muster in klar:
                return antwort
        return _Resp(404, {"error": {"code": "ErrorItemNotFound"}})

    http.aufrufe = aufrufe
    return http


NACHRICHT = {
    "id": "NEU-ID",
    "subject": "AW: Termin morgen?",
    "receivedDateTime": "2026-08-20T10:00:00Z",
    "internetMessageId": "<abc@iil.gmbh>",
}


class TestHole:
    def test_should_return_status_and_anchor_fields(self):
        http = _http({"/me/messages/ALT-ID?": _Resp(200, NACHRICHT)})
        status, daten = ga.hole("tok", "ALT-ID", http)
        assert (status, daten["internetMessageId"]) == (200, "<abc@iil.gmbh>")

    def test_should_return_404_with_empty_data_when_the_id_died(self):
        assert ga.hole("tok", "ALT-ID", _http({})) == (404, {})


class TestFinden:
    def test_should_filter_by_internet_message_id(self):
        http = _http(
            {
                "$filter=internetMessageId eq '<abc@iil.gmbh>'": _Resp(
                    200, {"value": [NACHRICHT]}
                )
            }
        )
        assert ga.finde_per_internet_id("tok", "<abc@iil.gmbh>", http)["id"] == "NEU-ID"

    def test_should_return_none_when_the_filter_finds_nothing(self):
        http = _http({"$filter": _Resp(200, {"value": []})})
        assert ga.finde_per_internet_id("tok", "<weg@iil.gmbh>", http) is None

    def test_should_search_by_subject_and_keep_only_matching_ones_oldest_first(self):
        treffer = [
            {
                "id": "b",
                "subject": "Termin morgen? Nachtrag",
                "receivedDateTime": "2026-08-21T09:00:00Z",
            },
            {
                "id": "c",
                "subject": "Ganz anderes",
                "receivedDateTime": "2026-08-01T09:00:00Z",
            },
            {
                "id": "a",
                "subject": "Re: Termin morgen?",
                "receivedDateTime": "2026-08-20T09:00:00Z",
            },
        ]
        http = _http(
            {'$search="subject:Termin morgen?"': _Resp(200, {"value": treffer})}
        )
        assert [
            m["id"] for m in ga.finde_per_betreff("tok", "Termin morgen?", http)
        ] == ["a", "b"]

    def test_should_strip_reply_prefixes_when_comparing(self):
        assert ga.normalisiere("AW: Re:  Termin   morgen?") == "termin morgen?"


class TestHeileEintrag:
    def test_should_keep_a_valid_entry_and_add_the_internet_message_id(self):
        eintrag = {"graph_id": "ALT-ID", "notiz": "x"}
        http = _http({"/me/messages/ALT-ID?": _Resp(200, NACHRICHT)})
        b = ga.heile_eintrag("143", eintrag, "tok", [], http)
        assert b.zustand == ga.GUELTIG
        assert eintrag["internet_message_id"] == "<abc@iil.gmbh>"

    def test_should_follow_the_internet_message_id_when_the_graph_id_died(self):
        eintrag = {"graph_id": "ALT-ID", "internet_message_id": "<abc@iil.gmbh>"}
        http = _http({"$filter=internetMessageId": _Resp(200, {"value": [NACHRICHT]})})
        b = ga.heile_eintrag("143", eintrag, "tok", ["Termin morgen?"], http)
        assert b.zustand == ga.NACHGEZOGEN
        assert eintrag["graph_id"] == "NEU-ID"
        assert not any("$search" in u for u in http.aufrufe), (
            "Betreff-Suche nur ohne Anker"
        )

    def test_should_fall_back_to_the_subject_and_take_the_oldest(self):
        eintrag = {"graph_id": "ALT-ID"}
        http = _http(
            {
                "$search": _Resp(
                    200,
                    {
                        "value": [
                            NACHRICHT,
                            {
                                **NACHRICHT,
                                "id": "JUENGER",
                                "receivedDateTime": "2026-08-25T00:00:00Z",
                            },
                        ]
                    },
                )
            }
        )
        b = ga.heile_eintrag("143", eintrag, "tok", ["Termin morgen?"], http)
        assert b.zustand == ga.NEU_GESUCHT
        assert eintrag["graph_id"] == "NEU-ID"
        assert eintrag["internet_message_id"] == "<abc@iil.gmbh>"

    def test_should_report_dead_instead_of_guessing_without_subject(self):
        eintrag = {"graph_id": "ALT-ID"}
        b = ga.heile_eintrag("az1", eintrag, "tok", [], _http({}))
        assert b.zustand == ga.TOT
        assert eintrag["graph_id"] == "ALT-ID"

    def test_should_report_dead_when_the_subject_search_finds_nothing(self):
        http = _http({"$search": _Resp(200, {"value": []})})
        b = ga.heile_eintrag(
            "143", {"graph_id": "ALT-ID"}, "tok", ["Termin morgen?"], http
        )
        assert b.zustand == ga.TOT

    def test_should_report_other_errors_as_unverifiable(self):
        http = _http({"/me/messages/ALT-ID?": _Resp(503)})
        b = ga.heile_eintrag("143", {"graph_id": "ALT-ID"}, "tok", [], http)
        assert b.zustand == ga.UNPRUEFBAR


class TestHeileAlle:
    def test_should_use_the_ledger_subject_for_the_matching_number(self):
        registry = {"143": {"graph_id": "ALT-ID"}, "az1": {"graph_id": "ALT-ID"}}
        http = _http({"$search": _Resp(200, {"value": [NACHRICHT]})})
        befunde = ga.heile(registry, {"143": ["Termin morgen?"]}, "tok", http)
        assert {b.kurz: b.zustand for b in befunde} == {
            "143": ga.NEU_GESUCHT,
            "az1": ga.TOT,
        }

    def test_should_summarise_counts_first(self):
        text = ga.bericht([ga.Befund("1", ga.GUELTIG), ga.Befund("2", ga.TOT, "weg")])
        assert text.splitlines()[0] == "2 Kurzlinks: 1 gueltig, 1 tot"
        assert "2        tot          weg" in text


class TestBetreffeAusLedger:
    def test_should_offer_thread_key_first_then_quoted_subjects(self):
        ledger = {
            "vorgaenge": [
                {
                    "nr": 146,
                    "thread_key": "sevdesk Testphase / Upgrade",
                    "notiz": "2026-08-21 EINGANG: 'Deine Testphase endet bald: Spare 25 %' Noch 7 Tage",
                }
            ]
        }
        assert ga.betreffe_aus_ledger(ledger) == {
            "146": [
                "sevdesk Testphase / Upgrade",
                "Deine Testphase endet bald: Spare 25 %",
            ]
        }

    def test_should_try_the_next_subject_when_the_first_finds_nothing(self):
        def http(method, url, **_kw):
            klar = unquote(url)
            if "$search" in klar and "Deine Testphase" in klar:
                return _Resp(
                    200,
                    {"value": [{**NACHRICHT, "subject": "Deine Testphase endet bald"}]},
                )
            if "$search" in klar:
                return _Resp(200, {"value": []})
            return _Resp(404, {"error": {"code": "ErrorItemNotFound"}})

        eintrag = {"graph_id": "ALT-ID"}
        b = ga.heile_eintrag(
            "146",
            eintrag,
            "tok",
            ["sevdesk Testphase / Upgrade", "Deine Testphase"],
            http,
        )
        assert b.zustand == ga.NEU_GESUCHT
        assert eintrag["graph_id"] == "NEU-ID"
