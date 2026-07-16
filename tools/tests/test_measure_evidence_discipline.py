"""Tests fuer tools/measure-evidence-discipline.py (Signal R, platform issue #256).

Issue #1199 TEST-4 (M): misst die org-weite Policy-Metrik aus
policies/evidence-discipline.md, hatte 0 Tests. Kernpfad-Test fuer die
Score-Berechnung (R = checked/total ueber "logische Turns") + Edge Cases
(leere Historie, kein Marker-Claim, Claim ohne vorangehenden Check-Tool-Use).

Modul heisst `measure-evidence-discipline.py` (Bindestriche) -> importlib
spec_from_file_location wie bei den Schwester-Tests.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

_SPEC = importlib.util.spec_from_file_location(
    "measure_evidence_discipline",
    pathlib.Path(__file__).resolve().parents[1] / "measure-evidence-discipline.py",
)
med = importlib.util.module_from_spec(_SPEC)
sys.modules["measure_evidence_discipline"] = med
_SPEC.loader.exec_module(med)


def _user(text: str = "") -> dict:
    return {"type": "user", "message": {"content": text}}


def _assistant(*blocks: dict) -> dict:
    return {"type": "assistant", "message": {"content": list(blocks)}}


def _text(t: str) -> dict:
    return {"type": "text", "text": t}


def _tool_use(name: str) -> dict:
    return {"type": "tool_use", "name": name, "id": "toolu_1", "input": {}}


def _tool_result_user() -> dict:
    return {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}


def _write_jsonl(path: pathlib.Path, entries: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")


# ---------------------------------------------------------------------------
# Score-Berechnung: checked-vs-unchecked marker-claim turns
# ---------------------------------------------------------------------------

def test_should_count_checked_claim_when_check_tool_precedes_marker(tmp_path):
    """Bash-Call vor einer Text-Aussage mit PR-#-Marker im selben Turn -> checked."""
    entries = [
        _user("mach mal"),
        _assistant(_tool_use("Bash"), _text("PR #1199 ist gemergt, alles gruen.")),
    ]
    p = tmp_path / "session.jsonl"
    _write_jsonl(p, entries)

    checked, total = med.measure_file(p)

    assert (checked, total) == (1, 1)


def test_should_count_unchecked_claim_when_no_check_tool_precedes_marker(tmp_path):
    """Marker-Claim ganz ohne vorangehenden Check-Tool-Use -> total++, checked bleibt 0."""
    entries = [
        _user("mach mal"),
        _assistant(_text("PR #1199 ist gemergt, alles gruen.")),
    ]
    p = tmp_path / "session.jsonl"
    _write_jsonl(p, entries)

    checked, total = med.measure_file(p)

    assert (checked, total) == (0, 1)


def test_should_ignore_turns_without_any_marker_claim(tmp_path):
    """Reiner Prosa-Text ohne Marker-Pattern zaehlt nicht in total."""
    entries = [
        _user("wie gehts?"),
        _assistant(_text("Gut, danke der Nachfrage.")),
    ]
    p = tmp_path / "session.jsonl"
    _write_jsonl(p, entries)

    checked, total = med.measure_file(p)

    assert (checked, total) == (0, 0)


def test_should_keep_tool_result_callbacks_inside_same_logical_turn(tmp_path):
    """Ein Tool-Result-User-Entry (kein echter Prompt) darf den Turn NICHT
    aufsplitten -- ein Check-Tool vor dem Result zaehlt weiter fuer den
    Marker-Claim danach."""
    entries = [
        _user("pruefe den Stand"),
        _assistant(_tool_use("Bash")),
        _tool_result_user(),
        _assistant(_text("commit a1b2c3 zeigt den Fix, erfolgreich verifiziert.")),
    ]
    p = tmp_path / "session.jsonl"
    _write_jsonl(p, entries)

    checked, total = med.measure_file(p)

    assert (checked, total) == (1, 1)


def test_should_aggregate_multiple_turns_in_one_file(tmp_path):
    entries = [
        _user("t1"),
        _assistant(_tool_use("Read"), _text("ADR-236 ist accepted.")),
        _user("t2"),
        _assistant(_text("ADR-999 ist auch accepted.")),  # kein Check davor
    ]
    p = tmp_path / "session.jsonl"
    _write_jsonl(p, entries)

    checked, total = med.measure_file(p)

    assert (checked, total) == (1, 2)


# ---------------------------------------------------------------------------
# Edge Case: leere Historie
# ---------------------------------------------------------------------------

def test_should_return_zero_zero_for_empty_transcript(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")

    checked, total = med.measure_file(p)

    assert (checked, total) == (0, 0)


def test_should_skip_malformed_json_lines_without_crashing(tmp_path):
    p = tmp_path / "broken.jsonl"
    p.write_text(
        "not-json-at-all\n"
        + json.dumps(_user("t1")) + "\n"
        + json.dumps(_assistant(_tool_use("Bash"), _text("PR #42 done."))) + "\n",
        encoding="utf-8",
    )

    checked, total = med.measure_file(p)

    assert (checked, total) == (1, 1)


def test_should_scan_project_dir_with_no_jsonl_files_as_zero(tmp_path):
    empty_dir = tmp_path / "no-sessions"
    empty_dir.mkdir()

    checked, total = med.scan_project_dir(empty_dir)

    assert (checked, total) == (0, 0)
