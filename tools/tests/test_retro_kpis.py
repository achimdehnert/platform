"""Tests für tools/retro_kpis.py (session-retro Längsschnitt-Hebel, v2.2)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retro_kpis import load_reports, parse_frontmatter  # noqa: E402

SAMPLE = """---
retro_schema: 1
date: 2026-06-14
repo_scope: [coach-hub, platform]
session_id: 2d7cd9
footprint: deep
findings_total: 12
findings_survived: 8
refuted_rate: 0.33
phase3_refuted: 2
pre_refuted: 2
scores:
  zielerreichung: 4
  architektur_design: 3
  risiko_debt: 2
gate_candidates: [a-gate, b-gate]
recurring_findings: [stale-local-vs-origin, worktree-orphan-accumulation]
---

# Body, darf NICHT geparst werden
recurring_findings: [should-be-ignored]
"""


def test_should_parse_inline_list_and_scalars():
    fm = parse_frontmatter(SAMPLE)
    assert fm is not None
    assert fm["session_id"] == "2d7cd9"
    assert fm["refuted_rate"] == "0.33"
    assert fm["recurring_findings"] == ["stale-local-vs-origin", "worktree-orphan-accumulation"]


def test_should_parse_nested_scores_block_as_ints():
    fm = parse_frontmatter(SAMPLE)
    assert fm["scores"] == {"zielerreichung": 4, "architektur_design": 3, "risiko_debt": 2}


def test_should_not_leak_body_keys_into_frontmatter():
    # Der `recurring_findings`-Eintrag IM BODY darf den Frontmatter-Wert nicht überschreiben.
    fm = parse_frontmatter(SAMPLE)
    assert "should-be-ignored" not in fm["recurring_findings"]


def test_should_return_none_without_frontmatter():
    assert parse_frontmatter("kein Frontmatter hier\n") is None


def test_should_skip_extern_briefings_and_load_real_reports(tmp_path):
    (tmp_path / "session-retro-2026-06-14-x-aaa.md").write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "session-retro-extern-2026-06-14-x-aaa.md").write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "unrelated.md").write_text("nope", encoding="utf-8")
    reports = load_reports(str(tmp_path))
    assert len(reports) == 1  # -extern- + unrelated ausgeschlossen
    assert reports[0]["_path"] == "session-retro-2026-06-14-x-aaa.md"
