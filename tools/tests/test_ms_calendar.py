"""Tests für tools/calendar_agent/ms_calendar.py — netzfreie Funktionen:
Zeit-Parsing, Event-Body-Bau (inkl. Stufe-A-Riegel: nie Teilnehmer), ICS-Serien-Expansion,
sowie cmd_delete/--list --ids mit gemocktem Graph-HTTP (nie echte Netz-/Login-Zugriffe;
alle Termine synthetisch — dieses Repo ist öffentlich). cmd_login/cmd_status bleiben
Dogfood/Integration.
"""

import datetime as dt
import importlib.util
import pathlib
import types

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "calendar_agent" / "ms_calendar.py"
_spec = importlib.util.spec_from_file_location("ms_calendar", _SRC)
mc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mc)


# --- Test-Fixtures für Graph-Mocks -------------------------------------------


class _FakeResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


def _cfg(tmp_path, accounts):
    return {
        "accounts": accounts,
        "client_for": {a: "client-id" for a in accounts},
        "tenant": "organizations",
        "token_dir": tmp_path,
    }


def _event(
    id_,
    subject="Testtermin",
    attendees=None,
    is_organizer=True,
    ev_type="singleInstance",
    series_master_id=None,
    start="2026-09-20T10:00:00.0000000",
    end="2026-09-20T11:00:00.0000000",
):
    return {
        "id": id_,
        "subject": subject,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "location": {"displayName": ""},
        "isOnlineMeeting": False,
        "isAllDay": False,
        "attendees": attendees or [],
        "isOrganizer": is_organizer,
        "type": ev_type,
        "seriesMasterId": series_master_id,
    }


def _delete_args(kennung, tage=60, yes=True):
    return types.SimpleNamespace(delete=kennung, tage=tage, yes=yes)


# --- parse_local -------------------------------------------------------------


def test_should_convert_local_datetime_to_graph_string():
    assert mc.parse_local("2026-07-24 14:00") == "2026-07-24T14:00:00"
    assert mc.parse_local("2026-07-24T14:00") == "2026-07-24T14:00:00"


def test_should_reject_malformed_datetime():
    with pytest.raises(ValueError):
        mc.parse_local("24.07.2026 14 Uhr")


# --- build_event_body: Stufe-A-Riegel ---------------------------------------


def test_should_build_event_with_subject_start_end():
    b = mc.build_event_body(
        "Prüfungsvorbereitung", "2026-07-24 14:00", "2026-07-24 16:00", "", ""
    )
    assert b["subject"] == "Prüfungsvorbereitung"
    assert b["start"]["dateTime"] == "2026-07-24T14:00:00"
    assert b["start"]["timeZone"] == mc.TIMEZONE
    assert b["end"]["dateTime"] == "2026-07-24T16:00:00"


def test_should_never_set_attendees_stufe_a_riegel():
    # Der harte Riegel: Stufe A legt NIE Teilnehmer an (das wäre Außenwirkung, Stufe B).
    b = mc.build_event_body(
        "Block", "2026-07-24 09:00", "2026-07-24 10:00", "Büro", "Notiz"
    )
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


# --- resolve_kennung ----------------------------------------------------------


def test_should_resolve_unique_kennung():
    events = [
        _event("xxxxxxxxxxxxxxxxAAAABBBBCCCC"),
        _event("yyyyyyyyyyyyyyyyDDDDEEEEFFFF"),
    ]
    matches = mc.resolve_kennung(events, "AAAABBBBCCCC")
    assert len(matches) == 1
    assert matches[0]["id"].endswith("AAAABBBBCCCC")


def test_should_report_ambiguous_kennung():
    events = [_event("oneXXXXAAAABBBBCCCC"), _event("twoYYYYAAAABBBBCCCC")]
    matches = mc.resolve_kennung(events, "AAAABBBBCCCC")
    assert len(matches) == 2


def test_should_report_missing_kennung():
    events = [_event("xxxxxxxxxxxxxxxxAAAABBBBCCCC")]
    matches = mc.resolve_kennung(events, "000000000000")
    assert matches == []


# --- cmd_delete: Kennungs-Auflösung (0/>1 Treffer -> Exit 2) ------------------


def test_should_exit_2_when_kennung_ambiguous(tmp_path, monkeypatch):
    acc = "achim.dehnert@iil.gmbh"
    cfg = _cfg(tmp_path, [acc])
    events = [_event("oneAAAABBBBCCCC"), _event("twoAAAABBBBCCCC")]
    monkeypatch.setattr(mc, "get_access_token", lambda cfg, a: "tok")
    monkeypatch.setattr(
        mc.requests, "get", lambda *a, **k: _FakeResp(200, {"value": events})
    )
    with pytest.raises(SystemExit) as exc:
        mc.cmd_delete(cfg, acc, _delete_args("AAAABBBBCCCC"))
    assert exc.value.code == 2


def test_should_exit_2_when_kennung_not_found(tmp_path, monkeypatch):
    acc = "achim.dehnert@iil.gmbh"
    cfg = _cfg(tmp_path, [acc])
    monkeypatch.setattr(mc, "get_access_token", lambda cfg, a: "tok")
    monkeypatch.setattr(
        mc.requests, "get", lambda *a, **k: _FakeResp(200, {"value": []})
    )
    with pytest.raises(SystemExit) as exc:
        mc.cmd_delete(cfg, acc, _delete_args("000000000000"))
    assert exc.value.code == 2


# --- cmd_delete: Schutzregeln (hart, Exit 3, kein DELETE) ---------------------


def test_should_delete_event_without_attendees_calls_delete_once(tmp_path, monkeypatch):
    acc = "achim.dehnert@iil.gmbh"
    cfg = _cfg(tmp_path, [acc])
    ev = _event("xxxxxxxxxxxxxxxxAAAABBBBCCCC", subject="Testtermin frei")
    monkeypatch.setattr(mc, "get_access_token", lambda cfg, a: "tok")
    monkeypatch.setattr(
        mc.requests, "get", lambda *a, **k: _FakeResp(200, {"value": [ev]})
    )
    calls = []
    monkeypatch.setattr(
        mc.requests,
        "delete",
        lambda url, **k: calls.append(url) or _FakeResp(204),
    )
    mc.cmd_delete(cfg, acc, _delete_args("AAAABBBBCCCC"))
    assert len(calls) == 1
    assert calls[0].endswith(ev["id"])


def test_should_refuse_delete_when_attendees_present(tmp_path, monkeypatch):
    acc = "achim.dehnert@iil.gmbh"
    cfg = _cfg(tmp_path, [acc])
    ev = _event(
        "xxxxxxxxxxxxxxxxAAAABBBBCCCC",
        attendees=[{"emailAddress": {"address": "dritte@example.invalid"}}],
    )
    monkeypatch.setattr(mc, "get_access_token", lambda cfg, a: "tok")
    monkeypatch.setattr(
        mc.requests, "get", lambda *a, **k: _FakeResp(200, {"value": [ev]})
    )
    calls = []
    monkeypatch.setattr(mc.requests, "delete", lambda *a, **k: calls.append(1))
    with pytest.raises(SystemExit) as exc:
        mc.cmd_delete(cfg, acc, _delete_args("AAAABBBBCCCC"))
    assert exc.value.code == 3
    assert calls == []


def test_should_refuse_delete_when_not_organizer(tmp_path, monkeypatch):
    acc = "achim.dehnert@iil.gmbh"
    cfg = _cfg(tmp_path, [acc])
    ev = _event("xxxxxxxxxxxxxxxxAAAABBBBCCCC", is_organizer=False)
    monkeypatch.setattr(mc, "get_access_token", lambda cfg, a: "tok")
    monkeypatch.setattr(
        mc.requests, "get", lambda *a, **k: _FakeResp(200, {"value": [ev]})
    )
    calls = []
    monkeypatch.setattr(mc.requests, "delete", lambda *a, **k: calls.append(1))
    with pytest.raises(SystemExit) as exc:
        mc.cmd_delete(cfg, acc, _delete_args("AAAABBBBCCCC"))
    assert exc.value.code == 3
    assert calls == []


def test_should_refuse_delete_for_series_event(tmp_path, monkeypatch):
    acc = "achim.dehnert@iil.gmbh"
    cfg = _cfg(tmp_path, [acc])
    ev = _event("xxxxxxxxxxxxxxxxAAAABBBBCCCC", ev_type="seriesMaster")
    monkeypatch.setattr(mc, "get_access_token", lambda cfg, a: "tok")
    monkeypatch.setattr(
        mc.requests, "get", lambda *a, **k: _FakeResp(200, {"value": [ev]})
    )
    calls = []
    monkeypatch.setattr(mc.requests, "delete", lambda *a, **k: calls.append(1))
    with pytest.raises(SystemExit) as exc:
        mc.cmd_delete(cfg, acc, _delete_args("AAAABBBBCCCC"))
    assert exc.value.code == 3
    assert calls == []


def test_should_refuse_delete_for_series_occurrence_via_series_master_id(
    tmp_path, monkeypatch
):
    acc = "achim.dehnert@iil.gmbh"
    cfg = _cfg(tmp_path, [acc])
    ev = _event(
        "xxxxxxxxxxxxxxxxAAAABBBBCCCC",
        ev_type="occurrence",
        series_master_id="masterid123",
    )
    monkeypatch.setattr(mc, "get_access_token", lambda cfg, a: "tok")
    monkeypatch.setattr(
        mc.requests, "get", lambda *a, **k: _FakeResp(200, {"value": [ev]})
    )
    calls = []
    monkeypatch.setattr(mc.requests, "delete", lambda *a, **k: calls.append(1))
    with pytest.raises(SystemExit) as exc:
        mc.cmd_delete(cfg, acc, _delete_args("AAAABBBBCCCC"))
    assert exc.value.code == 3
    assert calls == []


def test_should_refuse_delete_for_ics_account(tmp_path, monkeypatch):
    acc = "achim.dehnert@hnu.de"
    cfg = _cfg(tmp_path, [acc])
    mc.ics_path(cfg, acc).write_text("http://example.invalid/cal.ics")
    calls = []
    monkeypatch.setattr(mc.requests, "delete", lambda *a, **k: calls.append(1))
    with pytest.raises(SystemExit) as exc:
        mc.cmd_delete(cfg, acc, _delete_args("AAAABBBBCCCC"))
    assert exc.value.code == 3
    assert calls == []


# --- --list --ids --------------------------------------------------------------


def test_should_show_kennung_teilnehmerzahl_und_organisator_with_ids(
    tmp_path, monkeypatch, capsys
):
    acc = "achim.dehnert@iil.gmbh"
    cfg = _cfg(tmp_path, [acc])
    ev = _event(
        "xxxxxxxxxxxxxxxxAAAABBBBCCCC",
        subject="Testtermin sichtbar",
        attendees=[{"emailAddress": {"address": "dritte@example.invalid"}}],
    )
    monkeypatch.setattr(mc, "get_access_token", lambda cfg, a: "tok")
    monkeypatch.setattr(
        mc.requests, "get", lambda *a, **k: _FakeResp(200, {"value": [ev]})
    )
    mc.cmd_list(cfg, 7, show_ids=True)
    out = capsys.readouterr().out
    assert "id=AAAABBBBCCCC" in out
    assert "teilnehmer=1" in out
    assert "organisator=ja" in out


def test_should_mark_series_events_in_ids_listing(tmp_path, monkeypatch, capsys):
    acc = "achim.dehnert@iil.gmbh"
    cfg = _cfg(tmp_path, [acc])
    ev = _event("xxxxxxxxxxxxxxxxAAAABBBBCCCC", ev_type="seriesMaster")
    monkeypatch.setattr(mc, "get_access_token", lambda cfg, a: "tok")
    monkeypatch.setattr(
        mc.requests, "get", lambda *a, **k: _FakeResp(200, {"value": [ev]})
    )
    mc.cmd_list(cfg, 7, show_ids=True)
    out = capsys.readouterr().out
    assert "serie" in out


def test_should_mark_ics_events_as_read_only_with_ids(tmp_path, monkeypatch, capsys):
    acc = "achim.dehnert@hnu.de"
    cfg = _cfg(tmp_path, [acc])
    mc.ics_path(cfg, acc).write_text("http://example.invalid/cal.ics")
    when = dt.datetime.now(mc.BERLIN) + dt.timedelta(days=2)

    ics_text = (
        "BEGIN:VCALENDAR\nBEGIN:VEVENT\n"
        f"DTSTART:{when.strftime('%Y%m%dT%H%M%S')}\n"
        f"DTEND:{(when + dt.timedelta(hours=1)).strftime('%Y%m%dT%H%M%S')}\n"
        "SUMMARY:Testtermin HNU\nEND:VEVENT\nEND:VCALENDAR"
    )

    class _IcsResp:
        text = ics_text

        def raise_for_status(self):
            pass

    monkeypatch.setattr(mc.requests, "get", lambda *a, **k: _IcsResp())
    mc.cmd_list(cfg, 7, show_ids=True)
    out = capsys.readouterr().out
    assert "nur lesen" in out
