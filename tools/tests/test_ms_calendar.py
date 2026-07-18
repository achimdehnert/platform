"""Tests für tools/calendar_agent/ms_calendar.py — netzfreie Funktionen:
Zeit-Parsing, Event-Body-Bau (inkl. Stufe-A-Riegel: nie Teilnehmer), ICS-Serien-Expansion.
Kein Graph-/Netz-Test (cmd_login/cmd_create/cmd_list bleiben Dogfood/Integration).
"""
import datetime as dt
import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "calendar_agent" / "ms_calendar.py"
_spec = importlib.util.spec_from_file_location("ms_calendar", _SRC)
mc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mc)


# --- parse_local -------------------------------------------------------------

def test_should_convert_local_datetime_to_graph_string():
    assert mc.parse_local("2026-07-24 14:00") == "2026-07-24T14:00:00"
    assert mc.parse_local("2026-07-24T14:00") == "2026-07-24T14:00:00"


def test_should_reject_malformed_datetime():
    with pytest.raises(ValueError):
        mc.parse_local("24.07.2026 14 Uhr")


# --- build_event_body: Stufe-A-Riegel ---------------------------------------

def test_should_build_event_with_subject_start_end():
    b = mc.build_event_body("Prüfungsvorbereitung", "2026-07-24 14:00", "2026-07-24 16:00", "", "")
    assert b["subject"] == "Prüfungsvorbereitung"
    assert b["start"]["dateTime"] == "2026-07-24T14:00:00"
    assert b["start"]["timeZone"] == mc.TIMEZONE
    assert b["end"]["dateTime"] == "2026-07-24T16:00:00"


def test_should_never_set_attendees_stufe_a_riegel():
    # Der harte Riegel: Stufe A legt NIE Teilnehmer an (das wäre Außenwirkung, Stufe B).
    b = mc.build_event_body("Block", "2026-07-24 09:00", "2026-07-24 10:00", "Büro", "Notiz")
    assert b["attendees"] == []
    assert b["location"]["displayName"] == "Büro"
    assert b["body"]["content"] == "Notiz"


def test_should_omit_optional_fields_when_empty():
    b = mc.build_event_body("X", "2026-07-24 09:00", "2026-07-24 10:00", "", "")
    assert "location" not in b
    assert "body" not in b


# --- ics_events: Serien-Expansion (netzfrei via monkeypatch) -----------------

def test_should_expand_weekly_series(monkeypatch):
    ics = (
        "BEGIN:VCALENDAR\n"
        "BEGIN:VEVENT\n"
        "DTSTART:20260713T140000\nDTEND:20260713T160000\n"
        "RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=4\nSUMMARY:Vorlesung\n"
        "END:VEVENT\nEND:VCALENDAR"
    )

    class _Resp:
        text = ics
        def raise_for_status(self):
            pass

    monkeypatch.setattr(mc.requests, "get", lambda *a, **k: _Resp())
    ws = dt.datetime(2026, 7, 18, tzinfo=mc.BERLIN)
    we = dt.datetime(2026, 8, 10, tzinfo=mc.BERLIN)
    mondays = [s for s, *_ in mc.ics_events("http://x", ws, we)]
    assert len(mondays) == 3  # 20.07., 27.07., 03.08. (13.07. liegt vor dem Fenster)
    assert all(m.weekday() == 0 for m in mondays)
