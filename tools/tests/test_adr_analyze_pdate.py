"""Tests für tools/adr/adr_analyze.py — pdate() Datums-Parsing (F-10).

Repro (repo-optimize 2026-07-08-runB, Skeptiker-verifiziert): pdate() rief
`datetime.date(*map(int, m.groups()))` auf, sobald die Regex `\\d{4}-\\d{2}-\\d{2}`
matchte — auch bei kalendarisch ungültigen Daten wie 2026-13-40 oder
2026-02-30 (30. Februar existiert nicht). `datetime.date()` wirft in diesem
Fall ValueError, was das gesamte Skript zum Absturz brachte statt das
kaputte Datum als "kein Datum" (None) zu behandeln.

adr_analyze.py führt beim Import Top-Level-Code aus (liest sys.argv[1]/[2]),
daher wird sys.argv vor dem Import auf ein leeres, valides Inventory-JSON
umgebogen (leere Liste -> keine Repos -> alle Schleifen no-op).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "adr" / "adr_analyze.py"


def _load_module(tmp_path):
    inventory = tmp_path / "inventory.json"
    findings = tmp_path / "findings.json"
    inventory.write_text("[]", encoding="utf-8")
    old_argv = sys.argv
    sys.argv = ["adr_analyze.py", str(inventory), str(findings)]
    try:
        spec = importlib.util.spec_from_file_location("adr_analyze_under_test", _SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["adr_analyze_under_test"] = mod
        spec.loader.exec_module(mod)
    finally:
        sys.argv = old_argv
    return mod


def test_should_return_none_for_invalid_month(tmp_path):
    aa = _load_module(tmp_path)
    assert aa.pdate("2026-13-40") is None


def test_should_return_none_for_invalid_day(tmp_path):
    aa = _load_module(tmp_path)
    assert aa.pdate("2026-02-30") is None


def test_should_return_none_for_zero_month(tmp_path):
    aa = _load_module(tmp_path)
    assert aa.pdate("2026-00-01") is None


def test_should_parse_valid_date(tmp_path):
    import datetime

    aa = _load_module(tmp_path)
    assert aa.pdate("2026-07-08") == datetime.date(2026, 7, 8)


def test_should_return_none_for_missing_date(tmp_path):
    aa = _load_module(tmp_path)
    assert aa.pdate(None) is None
    assert aa.pdate("") is None
