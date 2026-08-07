"""Tests für tools/todo_board/todo_board.py — Arbeitsliste aus dem Vorgangs-Ledger.

Geprüft wird das, was die Seite aussagekräftig macht: die Fristen-Arithmetik
inklusive Überfälligkeit, die Sortierung (Fristen zuerst, aufsteigend) und die
Zusicherung, dass kein Vorgang stillschweigend verschwindet, wenn seine
Bucket-Angabe fehlt oder unbekannt ist.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "todo_board"))

tb = pytest.importorskip("todo_board")

STICHTAG = date(2026, 8, 7)


def vorgang(**kw) -> dict:
    grund = {
        "konto": "iil",
        "thread_key": "Beispiel",
        "gegenueber": "Jemand",
        "bucket": "owner",
        "frist": None,
        "kurz": "etwas tun",
        "next_trigger": "etwas tun",
    }
    grund.update(kw)
    return grund


class TestFristTage:
    def test_should_return_none_without_frist(self):
        assert tb.frist_tage(vorgang(frist=None), STICHTAG) is None

    def test_should_count_days_until_frist(self):
        assert tb.frist_tage(vorgang(frist="2026-08-19"), STICHTAG) == 12

    def test_should_return_negative_when_overdue(self):
        assert tb.frist_tage(vorgang(frist="2026-08-01"), STICHTAG) == -6

    def test_should_return_none_for_unparsable_frist(self):
        # Ein kaputtes Datum darf die Seite nicht abreißen lassen.
        assert tb.frist_tage(vorgang(frist="19.08.2026"), STICHTAG) is None


class TestAmpel:
    @pytest.mark.parametrize(
        "tage,klasse",
        [(-1, "rot"), (0, "rot"), (3, "rot"), (4, "gelb"), (10, "gelb"), (11, "gruen")],
    )
    def test_should_classify_by_remaining_days(self, tage, klasse):
        assert tb.ampel(tage)[0] == klasse

    def test_should_name_overdue_days_explicitly(self):
        assert tb.ampel(-6)[1] == "6 Tage ueberfaellig"

    def test_should_stay_neutral_without_frist(self):
        assert tb.ampel(None) == ("keine", "—")


class TestSortierung:
    def test_should_put_deadlines_before_undated(self):
        mit = vorgang(frist="2026-09-30", thread_key="A")
        ohne = vorgang(frist=None, thread_key="B")
        geordnet = sorted([ohne, mit], key=lambda v: tb.sortschluessel(v, STICHTAG))
        assert [v["thread_key"] for v in geordnet] == ["A", "B"]

    def test_should_order_deadlines_ascending(self):
        spaet = vorgang(frist="2026-08-31", thread_key="spaet")
        frueh = vorgang(frist="2026-08-12", thread_key="frueh")
        geordnet = sorted([spaet, frueh], key=lambda v: tb.sortschluessel(v, STICHTAG))
        assert [v["thread_key"] for v in geordnet] == ["frueh", "spaet"]


class TestSeite:
    def test_should_render_every_vorgang(self):
        daten = {
            "letzte_pruefung": "2026-08-07",
            "vorgaenge": [
                vorgang(bucket="owner", thread_key="Euramco", frist="2026-08-19"),
                vorgang(bucket="agent", thread_key="Scheppach", frist="2026-08-22"),
                vorgang(bucket="warten", thread_key="Kramer"),
            ],
        }
        seite = tb.baue(daten, STICHTAG)
        for name in ("Euramco", "Scheppach", "Kramer"):
            assert name in seite

    def test_should_not_swallow_unknown_bucket(self):
        # Ein Tippfehler im Ledger darf einen Vorgang nicht unsichtbar machen —
        # er gehört sichtbar nach "Dein Zug", nicht ins Nichts.
        daten = {"vorgaenge": [vorgang(bucket="tippfehler", thread_key="Verwaist")]}
        seite = tb.baue(daten, STICHTAG)
        assert "Verwaist" in seite
        assert "Dein Zug" in seite

    def test_should_warn_about_imminent_deadlines(self):
        daten = {"vorgaenge": [vorgang(frist="2026-08-08", thread_key="Morgen")]}
        assert "1 in den naechsten 3 Tagen faellig" in tb.baue(daten, STICHTAG)

    def test_should_omit_empty_sections(self):
        daten = {"vorgaenge": [vorgang(bucket="owner")]}
        seite = tb.baue(daten, STICHTAG)
        assert "Dein Zug" in seite
        assert "Wartet auf andere" not in seite

    def test_should_escape_names_from_the_ledger(self):
        # Gegenüber-Namen kommen aus fremden Mails — sie dürfen kein Markup einschleusen.
        daten = {"vorgaenge": [vorgang(gegenueber="<script>alert(1)</script>")]}
        seite = tb.baue(daten, STICHTAG)
        assert "<script>" not in seite
        assert "&lt;script&gt;" in seite


class TestBindGuard:
    def test_should_refuse_public_bind_without_flag(self):
        import argparse

        args = argparse.Namespace(
            bind="0.0.0.0", port=8789, oeffentlich_hinter_auth=False
        )
        with pytest.raises(SystemExit) as exc:
            tb.cmd_serve(args)
        assert "verweigert" in str(exc.value)


class TestFrische:
    """Eine Liste, die stillschweigend alten Stand zeigt, beruhigt fälschlich."""

    def test_should_stay_silent_when_recent(self):
        daten = {"letzte_pruefung": "2026-08-07", "vorgaenge": []}
        assert tb.frische_banner(daten, STICHTAG) == ""

    def test_should_stay_silent_at_the_freshness_limit(self):
        daten = {"letzte_pruefung": "2026-08-05", "vorgaenge": []}
        assert tb.frische_banner(daten, STICHTAG) == ""

    def test_should_warn_one_day_past_the_limit(self):
        daten = {"letzte_pruefung": "2026-08-04", "vorgaenge": []}
        banner = tb.frische_banner(daten, STICHTAG)
        assert "3 Tage alt" in banner
        assert "2026-08-04" in banner

    def test_should_warn_when_date_is_missing(self):
        assert "Stand unbekannt" in tb.frische_banner({"vorgaenge": []}, STICHTAG)

    def test_should_warn_when_date_is_unparsable(self):
        banner = tb.frische_banner({"letzte_pruefung": "07.08.2026"}, STICHTAG)
        assert "unlesbar" in banner

    def test_should_surface_the_banner_on_the_page(self):
        daten = {"letzte_pruefung": "2026-07-01", "vorgaenge": [vorgang()]}
        assert "37 Tage alt" in tb.baue(daten, STICHTAG)
