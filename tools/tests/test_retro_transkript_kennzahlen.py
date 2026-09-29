"""Drill für tools/retro_transkript_kennzahlen.py (Retro kbiAvn-incr, Streichkandidat Phase 1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import retro_transkript_kennzahlen as rtk  # noqa: E402


def _lies(*eintraege, **fenster):
    return rtk.lies((json.dumps(e) for e in eintraege), **fenster)


def test_should_pass_selftest_for_every_class():
    assert rtk.selbsttest() == 0


def test_should_count_error_without_is_error_flag():
    k = rtk.lies(json.dumps(z) for z in rtk._FIXTURE)
    assert any("TimeoutError" in r for *_, r in k.fehler)


def test_should_not_count_successful_result_as_error():
    k = _lies(
        {
            "type": "assistant",
            "timestamp": "t1",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "x",
                        "name": "Bash",
                        "input": {"command": "ls"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "timestamp": "t2",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "x",
                        "content": "datei.txt\n0 errors",
                    }
                ]
            },
        },
    )
    assert k.fehler == [] and k.ablehnungen == []


def test_should_redact_commands_with_secret_markers():
    k = _lies(
        {
            "type": "assistant",
            "timestamp": "t1",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "x",
                        "name": "Bash",
                        "input": {"command": "UXR_OWNER_PW=geheim python3 login.py"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "timestamp": "t2",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "x",
                        "is_error": True,
                        "content": "Exit code 2",
                    }
                ]
            },
        },
    )
    assert k.fehler[0][2] == "<geschwärzt>"
    assert "geheim" not in rtk.bericht(k)


def test_should_respect_time_window():
    k = rtk.lies((json.dumps(z) for z in rtk._FIXTURE), von="2026-01-01T10:00:05Z")
    assert k.ablehnungen == [] and k.reminder == ["2026-01-01T10:01:00Z"]


def test_should_report_gap_from_reminder_to_next_text():
    k = rtk.lies(json.dumps(z) for z in rtk._FIXTURE)
    assert "4.0 min bis Text 2026-01-01T10:05:00Z" in rtk.bericht(k)


def _eingereiht(ts: str, prompt, **felder):
    return {
        "type": "attachment",
        "timestamp": ts,
        "attachment": {"type": "queued_command", "prompt": prompt, **felder},
    }


def test_should_count_owner_word_queued_mid_turn_before_its_later_repeat():
    """Realfall Retro 02b7f5: „47 go" kam 16:31 eingereiht und 17:04 erneut —
    ohne die eingereihte Zeile sah die Widerlegungsbahn nur 17:04."""
    k = _lies(
        _eingereiht("2026-09-24T16:31:33Z", "47 go", origin={"kind": "human"}),
        {
            "type": "user",
            "timestamp": "2026-09-24T17:04:58Z",
            "message": {"content": "47 go"},
        },
    )
    assert k.nutzer == [
        ("2026-09-24T16:31:33Z", "(eingereiht) 47 go"),
        ("2026-09-24T17:04:58Z", "47 go"),
    ]


def test_should_not_count_queued_system_notifications_as_user_messages():
    k = _lies(
        _eingereiht(
            "2026-09-24T17:13:51Z",
            "<task-notification>fertig</task-notification>",
            commandMode="task-notification",
        ),
        _eingereiht("2026-09-24T17:14:00Z", "", origin={"kind": "human"}),
    )
    assert k.nutzer == []


def test_should_accept_human_turn_flag_without_origin():
    k = _lies(_eingereiht("2026-09-24T16:12:44Z", "33 was rätst du?", humanTurn=True))
    assert k.nutzer == [("2026-09-24T16:12:44Z", "(eingereiht) 33 was rätst du?")]
