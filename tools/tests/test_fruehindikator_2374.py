"""Drill fuer tools/messungen/fruehindikator_2374.py (platform#2374 Ziel B, Stufe 1)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "messungen" / "fruehindikator_2374.py"
_spec = importlib.util.spec_from_file_location("fruehindikator_2374", _QUELLE)
fi = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(fi)


def _zeile(typ: str, role: str, content, ts="2026-09-02T07:00:00Z"):
    return json.dumps(
        {"type": typ, "timestamp": ts, "message": {"role": role, "content": content}}
    )


def _transkript(tmp: Path) -> str:
    zeilen = [
        _zeile("user", "user", [{"type": "text", "text": "mach mal"}]),
        # Behauptung mit Marker, kein Werkzeug vorher → strukturell ungeprueft
        _zeile(
            "assistant", "assistant", [{"type": "text", "text": "PR #12 ist gemergt."}]
        ),
        _zeile(
            "assistant",
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "Bash",
                    "input": {"command": "gh pr view 12"},
                }
            ],
        ),
        _zeile(
            "user",
            "user",
            [{"type": "tool_result", "tool_use_id": "t1", "content": "MERGED"}],
        ),
        # dieselbe Behauptung nach dem Werkzeuglauf → strukturell geprueft
        _zeile(
            "assistant", "assistant", [{"type": "text", "text": "PR #12 ist gemergt."}]
        ),
        # Block ohne Marker → kein Kandidat
        _zeile(
            "assistant", "assistant", [{"type": "text", "text": "Ich schaue weiter."}]
        ),
        # thinking zaehlt nicht
        _zeile(
            "assistant", "assistant", [{"type": "thinking", "thinking": "PR #12 alle"}]
        ),
    ]
    pfad = tmp / "abc12345-session.jsonl"
    pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return str(pfad)


def test_should_flag_a_marker_block_before_any_tool_result_as_unchecked(tmp_path):
    kandidaten, z = fi.scanne(_transkript(tmp_path))
    assert z["textbloecke"] == 3
    assert z["mit_marker"] == 2
    assert z["marker_ohne_check_im_zug"] == 1
    erster, zweiter = kandidaten
    assert erster["ungeprueft_strukturell"] is True
    assert zweiter["ungeprueft_strukturell"] is False
    assert zweiter["tool_results_vor_block"] == 1
    assert [k["art"] for k in zweiter["kontext"]] == ["use", "result"]
    assert zweiter["kontext"][1]["tool"] == "Bash"


def test_should_reset_the_turn_on_a_real_user_message(tmp_path):
    pfad = tmp_path / "x.jsonl"
    pfad.write_text(
        "\n".join(
            [
                _zeile("user", "user", [{"type": "text", "text": "a"}]),
                _zeile(
                    "assistant",
                    "assistant",
                    [{"type": "tool_use", "id": "t", "name": "Read", "input": {}}],
                ),
                _zeile(
                    "user",
                    "user",
                    [{"type": "tool_result", "tool_use_id": "t", "content": "x"}],
                ),
                _zeile("user", "user", [{"type": "text", "text": "b"}]),
                _zeile(
                    "assistant",
                    "assistant",
                    [{"type": "text", "text": "alle Tests gruen"}],
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    kandidaten, z = fi.scanne(str(pfad))
    assert kandidaten[0]["zug"] == 2
    assert kandidaten[0]["ungeprueft_strukturell"] is True
