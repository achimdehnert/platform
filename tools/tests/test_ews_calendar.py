"""Tests für tools/calendar_agent/ews_calendar.py — netzfreie Funktionen: curl-Konfig
(Passwort-Escaping), SOAP-Bausteine (Stufe-A-Riegel: nie Teilnehmer, SendToNone),
FindItem-Auswertung, Schutzregeln für --update/--delete sowie die Kommandos mit
gemocktem EWS-Aufruf. Alle Termine synthetisch — dieses Repo ist öffentlich.
"""

import datetime as dt
import importlib.util
import pathlib
import types

import pytest

_SRC = (
    pathlib.Path(__file__).resolve().parents[1] / "calendar_agent" / "ews_calendar.py"
)
_spec = importlib.util.spec_from_file_location("ews_calendar", _SRC)
ec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ec)

T = "http://schemas.microsoft.com/exchange/services/2006/types"
M = "http://schemas.microsoft.com/exchange/services/2006/messages"


def _find_response(items: list[dict]) -> str:
    def one(it):
        return (
            f'<t:CalendarItem><t:ItemId Id="{it["id"]}" ChangeKey="ck1"/>'
            f"<t:Subject>{it.get('subject', 'Test')}</t:Subject>"
            f"<t:Start>{it.get('start', '2026-10-01T08:00:00Z')}</t:Start>"
            f"<t:End>{it.get('end', '2026-10-01T09:00:00Z')}</t:End>"
            f"<t:Location>{it.get('location', '')}</t:Location>"
            f"<t:IsAllDayEvent>{it.get('allday', 'false')}</t:IsAllDayEvent>"
            f"<t:CalendarItemType>{it.get('type', 'Single')}</t:CalendarItemType>"
            f"<t:IsMeeting>{it.get('meeting', 'false')}</t:IsMeeting>"
            f"<t:MyResponseType>{it.get('resp', 'Unknown')}</t:MyResponseType>"
            "</t:CalendarItem>"
        )

    return (
        f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" xmlns:t="{T}" '
        f'xmlns:m="{M}"><s:Body><m:FindItemResponse><m:ResponseMessages>'
        '<m:FindItemResponseMessage ResponseClass="Success"><m:ResponseCode>NoError'
        "</m:ResponseCode><m:RootFolder><t:Items>"
        + "".join(one(i) for i in items)
        + "</t:Items></m:RootFolder></m:FindItemResponseMessage></m:ResponseMessages>"
        "</m:FindItemResponse></s:Body></s:Envelope>"
    )


_OK = (
    f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" xmlns:m="{M}" '
    f'xmlns:t="{T}"><s:Body><m:DeleteItemResponse><m:ResponseMessages>'
    '<m:DeleteItemResponseMessage ResponseClass="Success"><m:ResponseCode>NoError'
    "</m:ResponseCode></m:DeleteItemResponseMessage></m:ResponseMessages>"
    "</m:DeleteItemResponse></s:Body></s:Envelope>"
)
_CFG = {"account": "hnu", "url": "https://x/EWS", "login": "u", "creds_file": None}


# --- curl-Konfig -------------------------------------------------------------


def test_should_escape_quotes_and_backslashes_in_curl_config():
    out = ec.curl_config("dehnert", 'pa"ss\\wd')
    assert out == 'user = "dehnert:pa\\"ss\\\\wd"\n'


# --- SOAP-Bausteine ------------------------------------------------------------


def test_should_build_create_item_without_attendees_and_send_to_none():
    body = ec.body_create_item(
        "Probe & Co", "2026-10-01 10:00", "2026-10-01 11:00", "R1", "n"
    )
    assert 'SendMeetingInvitations="SendToNone"' in body
    assert "Attendees" not in body
    assert "<t:Subject>Probe &amp; Co</t:Subject>" in body
    assert "<t:Start>2026-10-01T10:00:00+02:00</t:Start>" in body
    assert body.index("<t:Body") < body.index("<t:Start>") < body.index("<t:Location>")


def test_should_reject_end_before_start():
    with pytest.raises(SystemExit):
        ec.body_create_item("x", "2026-10-01 11:00", "2026-10-01 10:00")


def test_should_build_update_only_for_given_fields_in_schema_order():
    body = ec.body_update_item(
        "ID", "CK", {"location": "R2", "subject": "Neu", "start": None}
    )
    assert body.count("<t:SetItemField>") == 2
    assert body.index("item:Subject") < body.index("calendar:Location")
    assert 'SendMeetingInvitationsOrCancellations="SendToNone"' in body


def test_should_refuse_update_without_fields():
    with pytest.raises(SystemExit):
        ec.body_update_item("ID", "CK", {"subject": None})


def test_should_build_delete_with_send_to_none():
    body = ec.body_delete_item("ID", "CK")
    assert 'SendMeetingCancellations="SendToNone"' in body
    assert 'ItemId Id="ID" ChangeKey="CK"' in body


def test_should_use_calendar_view_in_utc_window():
    start = dt.datetime(2026, 10, 1, 10, 0, tzinfo=ec.BERLIN)
    body = ec.body_find_items(start, start + dt.timedelta(days=1))
    assert 'StartDate="2026-10-01T08:00:00Z"' in body
    assert 'EndDate="2026-10-02T08:00:00Z"' in body


# --- Antwort-Auswertung --------------------------------------------------------


def test_should_parse_items_into_berlin_time():
    items = ec.parse_items(
        _find_response([{"id": "AAAAxyz12345", "start": "2026-10-01T08:00:00Z"}])
    )
    assert len(items) == 1
    assert items[0]["start"].strftime("%H:%M %z") == "10:00 +0200"
    assert items[0]["organizer"] is True and items[0]["meeting"] is False
    assert ec.kennung(items[0]["id"]) == "AAAAxyz12345"


def test_should_detect_error_response_and_soap_fault():
    err = _OK.replace('ResponseClass="Success"', 'ResponseClass="Error"').replace(
        "NoError", "ErrorAccessDenied"
    )
    assert ec.response_error(_OK) is None
    assert ec.response_error(err).startswith("ErrorAccessDenied")
    fault = (
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
        "<s:Fault><faultstring>kaputt</faultstring></s:Fault></s:Body></s:Envelope>"
    )
    assert ec.response_error(fault) == "SOAP-Fault: kaputt"
    assert "keine SOAP" in ec.response_error("<html>login</html>")
    assert "keine SOAP" in ec.response_error("not xml at all")


def test_should_mark_series_and_meeting_in_ids_line():
    ev = ec.parse_items(
        _find_response(
            [{"id": "ID1", "type": "Occurrence", "meeting": "true", "resp": "Accept"}]
        )
    )[0]
    line = ec.format_line(ev, "HNU", show_ids=True)
    assert "besprechung=ja organisator=nein serie" in line
    assert ec.format_line(ev, "HNU", show_ids=False).endswith("Test")


# --- Schutzregeln --------------------------------------------------------------


@pytest.mark.parametrize(
    "ev, reason",
    [
        ({"meeting": True, "organizer": True, "type": "Single"}, "Besprechung"),
        ({"meeting": False, "organizer": False, "type": "Single"}, "fremde Einladung"),
        ({"meeting": False, "organizer": True, "type": "Occurrence"}, "Serientermin"),
    ],
)
def test_should_block_foreign_meeting_and_series(ev, reason):
    assert reason in ec.guard_own_single(ev)


def test_should_allow_own_single_item():
    assert (
        ec.guard_own_single({"meeting": False, "organizer": True, "type": "Single"})
        is None
    )


# --- Kommandos mit gemocktem EWS --------------------------------------------------


def _mock_ews(monkeypatch, responses):
    calls = []

    def fake(cfg, body, timeout=60):
        calls.append(body)
        return 200, responses[min(len(calls) - 1, len(responses) - 1)]

    monkeypatch.setattr(ec, "ews_call", fake)
    return calls


def test_should_delete_own_single_item_after_resolving_kennung(monkeypatch, capsys):
    calls = _mock_ews(monkeypatch, [_find_response([{"id": "AAAAxyz12345"}]), _OK])
    ec.cmd_delete(_CFG, types.SimpleNamespace(delete="AAAAxyz12345", tage=7, yes=True))
    assert "<m:DeleteItem" in calls[1] and 'Id="AAAAxyz12345"' in calls[1]
    assert "✔ gelöscht" in capsys.readouterr().out


def test_should_exit_3_on_meeting_without_calling_delete(monkeypatch):
    calls = _mock_ews(monkeypatch, [_find_response([{"id": "ID1", "meeting": "true"}])])
    with pytest.raises(SystemExit) as e:
        ec.cmd_delete(_CFG, types.SimpleNamespace(delete="ID1", tage=7, yes=True))
    assert e.value.code == 3
    assert len(calls) == 1  # nur FindItem, kein DeleteItem


def test_should_exit_2_when_kennung_is_ambiguous(monkeypatch):
    _mock_ews(monkeypatch, [_find_response([{"id": "SAME"}, {"id": "SAME"}])])
    with pytest.raises(SystemExit) as e:
        ec.resolve(_CFG, "SAME", 7)
    assert e.value.code == 2


def test_should_update_via_set_item_field(monkeypatch, capsys):
    calls = _mock_ews(monkeypatch, [_find_response([{"id": "ID1"}]), _OK])
    args = types.SimpleNamespace(
        update="ID1",
        tage=7,
        yes=True,
        subject=None,
        start=None,
        end="2026-10-01 12:00",
        location=None,
        note=None,
    )
    ec.cmd_update(_CFG, args)
    assert calls[1].count("<t:SetItemField>") == 1 and "calendar:End" in calls[1]
    assert "✔ geändert" in capsys.readouterr().out


def test_should_list_sorted_and_report_empty(monkeypatch, capsys):
    _mock_ews(
        monkeypatch,
        [
            _find_response(
                [
                    {"id": "B", "start": "2026-10-02T08:00:00Z", "subject": "Zwei"},
                    {"id": "A", "start": "2026-10-01T08:00:00Z", "subject": "Eins"},
                ]
            )
        ],
    )
    ec.cmd_list(_CFG, 7, False)
    out = capsys.readouterr().out.splitlines()
    assert out[0].endswith("Eins") and out[1].endswith("Zwei")
    _mock_ews(monkeypatch, [_find_response([])])
    ec.cmd_list(_CFG, None, False)
    assert "Keine Termine" in capsys.readouterr().out


def test_should_gate_machine_without_config(monkeypatch, tmp_path):
    monkeypatch.setattr(ec.Path, "home", classmethod(lambda cls: tmp_path))
    with pytest.raises(SystemExit) as e:
        ec.load_config("hnu")
    assert "Capability-Profil" in str(e.value)
