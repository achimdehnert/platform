"""Tests für scripts/adr_triage.py — Frontmatter-Skelett-Generierung.

Maßnahme 11 (Follow-up aus #899, repo-optimize 2026-07-03): generate_frontmatter()
emittierte noch die alte Schlüssel-Generation (`date:`/`decision-makers:`) statt
des aktuellen Plattform-Standards (`decision_date:`/`deciders:`, siehe ADR-255/
ADR-259) — ein frisch generiertes Skelett driftete damit sofort wieder vom
Standard ab, den derselbe Triage-Lauf herstellen soll.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "adr_triage.py"
_spec = importlib.util.spec_from_file_location("adr_triage", _SCRIPT)
at = importlib.util.module_from_spec(_spec)
sys.modules["adr_triage"] = at
_spec.loader.exec_module(at)


def test_should_emit_deciders_and_decision_date_keys():
    adr = {"suggested_status": "accepted"}
    content = "**Datum**: 2026-07-03\n\nSome ADR body."
    fm = at.generate_frontmatter(adr, content)
    assert "deciders: [Achim Dehnert]" in fm
    assert "decision_date: 2026-07-03" in fm
    assert "decision-makers" not in fm
    assert "\ndate:" not in fm


def test_should_fall_back_to_today_when_no_date_in_content():
    adr = {"suggested_status": "proposed"}
    fm = at.generate_frontmatter(adr, "no date marker here")
    assert "decision_date:" in fm
