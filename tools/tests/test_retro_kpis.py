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


class TestMultiDirLoadReports:
    """T-11 (repo-optimize 2026-07-03): load_reports() akzeptiert seit #891/#886
    eine LISTE von Verzeichnissen (git-durables docs/retros/ + Skill-Schreibpfad
    ~/shared/) und dedupliziert nach Dateiname — bislang war das nur per Code-
    Review verifiziert, kein Test rief die Multi-Dir-Variante auf."""

    SAMPLE_B = SAMPLE.replace("2d7cd9", "other-session-id")

    def test_should_accept_list_of_directories(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        (dir_a / "session-retro-2026-06-14-x-aaa.md").write_text(SAMPLE, encoding="utf-8")
        (dir_b / "session-retro-2026-06-15-y-bbb.md").write_text(self.SAMPLE_B, encoding="utf-8")

        reports = load_reports([str(dir_a), str(dir_b)])

        assert len(reports) == 2
        assert {r["_path"] for r in reports} == {
            "session-retro-2026-06-14-x-aaa.md",
            "session-retro-2026-06-15-y-bbb.md",
        }

    def test_should_dedupe_same_filename_across_dirs_first_dir_wins(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        same_name = "session-retro-2026-06-14-x-aaa.md"
        (dir_a / same_name).write_text(SAMPLE, encoding="utf-8")
        # gleicher Dateiname in dir_b, aber INHALTLICH anders — first-dir-wins
        # muss die dir_a-Version behalten, nicht die aus dir_b nachladen.
        (dir_b / same_name).write_text(self.SAMPLE_B, encoding="utf-8")

        reports = load_reports([str(dir_a), str(dir_b)])

        assert len(reports) == 1  # kein Doppelzählen trotz zwei Fundstellen
        assert reports[0]["session_id"] == "2d7cd9"  # dir_a-Inhalt gewinnt

    def test_should_sum_totals_across_both_dirs_without_overlap(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        (dir_a / "session-retro-2026-06-14-x-aaa.md").write_text(SAMPLE, encoding="utf-8")
        (dir_a / "session-retro-extern-2026-06-14-x-aaa.md").write_text(SAMPLE, encoding="utf-8")
        (dir_b / "session-retro-2026-06-15-y-bbb.md").write_text(self.SAMPLE_B, encoding="utf-8")
        (dir_b / "unrelated.md").write_text("nope", encoding="utf-8")

        reports = load_reports([str(dir_a), str(dir_b)])

        # Gesamtzahl = 2 echte Retros; -extern- (dir_a) + unrelated.md (dir_b) ausgeschlossen.
        assert len(reports) == 2
