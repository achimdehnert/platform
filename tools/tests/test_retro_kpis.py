"""Tests für tools/retro_kpis.py (session-retro Längsschnitt-Hebel, v2.2)."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retro_kpis import (  # noqa: E402
    _create_gate_issue,
    _existing_gate_issue,
    _gate_issue_title,
    file_gate_issues,
    load_reports,
    parse_frontmatter,
)

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
    assert fm["recurring_findings"] == [
        "stale-local-vs-origin",
        "worktree-orphan-accumulation",
    ]


def test_should_parse_nested_scores_block_as_ints():
    fm = parse_frontmatter(SAMPLE)
    assert fm["scores"] == {
        "zielerreichung": 4,
        "architektur_design": 3,
        "risiko_debt": 2,
    }


def test_should_not_leak_body_keys_into_frontmatter():
    # Der `recurring_findings`-Eintrag IM BODY darf den Frontmatter-Wert nicht überschreiben.
    fm = parse_frontmatter(SAMPLE)
    assert "should-be-ignored" not in fm["recurring_findings"]


def test_should_return_none_without_frontmatter():
    assert parse_frontmatter("kein Frontmatter hier\n") is None


def test_should_skip_extern_briefings_and_load_real_reports(tmp_path):
    (tmp_path / "session-retro-2026-06-14-x-aaa.md").write_text(
        SAMPLE, encoding="utf-8"
    )
    (tmp_path / "session-retro-extern-2026-06-14-x-aaa.md").write_text(
        SAMPLE, encoding="utf-8"
    )
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
        (dir_a / "session-retro-2026-06-14-x-aaa.md").write_text(
            SAMPLE, encoding="utf-8"
        )
        (dir_b / "session-retro-2026-06-15-y-bbb.md").write_text(
            self.SAMPLE_B, encoding="utf-8"
        )

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
        (dir_a / "session-retro-2026-06-14-x-aaa.md").write_text(
            SAMPLE, encoding="utf-8"
        )
        (dir_a / "session-retro-extern-2026-06-14-x-aaa.md").write_text(
            SAMPLE, encoding="utf-8"
        )
        (dir_b / "session-retro-2026-06-15-y-bbb.md").write_text(
            self.SAMPLE_B, encoding="utf-8"
        )
        (dir_b / "unrelated.md").write_text("nope", encoding="utf-8")

        reports = load_reports([str(dir_a), str(dir_b)])

        # Gesamtzahl = 2 echte Retros; -extern- (dir_a) + unrelated.md (dir_b) ausgeschlossen.
        assert len(reports) == 2


def _proc(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestFileIssues:
    """--file-issues (Retro d80d23/2026-07-16): GATE-PFLICHT-Slugs sollen als durables
    'Gate: <slug>'-Issue landen statt nur als Prosa im Report zu versanden — genau die
    Lücke, die `session-retro-2026-07-11-platform-d2522c-incr.md` für
    `handover-stale-vor-merge` explizit als "ohne systemisches Gate" vermerkte."""

    def test_should_format_gate_issue_title_from_slug(self):
        assert (
            _gate_issue_title("stale-local-clone-as-ground-truth")
            == "Gate: stale-local-clone-as-ground-truth"
        )

    def test_should_find_existing_gate_issue_by_exact_title_match(self):
        listing = _proc(
            stdout='[{"number": 42, "title": "Gate: my-slug", '
            '"state": "OPEN", "url": "https://x/42"}]'
        )
        with patch("retro_kpis.subprocess.run", return_value=listing) as run:
            found = _existing_gate_issue("owner/repo", "my-slug")
        assert found == {
            "number": 42,
            "title": "Gate: my-slug",
            "state": "OPEN",
            "url": "https://x/42",
        }
        run.assert_called_once()

    def test_should_ignore_substring_only_title_matches(self):
        # gh --search kann lose matchen; nur ein EXAKTER Titel-Treffer zaehlt,
        # sonst wuerde z.B. "Gate: my-slug-v2" faelschlich als Duplikat gelten.
        listing = _proc(
            stdout='[{"number": 1, "title": "Gate: my-slug-v2", '
            '"state": "OPEN", "url": "https://x/1"}]'
        )
        with patch("retro_kpis.subprocess.run", return_value=listing):
            found = _existing_gate_issue("owner/repo", "my-slug")
        assert found is None

    def test_should_fail_open_on_gh_error(self):
        with patch(
            "retro_kpis.subprocess.run", return_value=_proc(returncode=1, stderr="boom")
        ):
            assert _existing_gate_issue("owner/repo", "my-slug") is None

    def test_should_fail_open_on_missing_gh(self):
        with patch("retro_kpis.subprocess.run", side_effect=OSError("no gh")):
            assert _existing_gate_issue("owner/repo", "my-slug") is None

    def test_should_return_url_from_last_stdout_line_on_create(self):
        created = _proc(
            stdout="creating issue...\nhttps://github.com/owner/repo/issues/99\n"
        )
        with patch("retro_kpis.subprocess.run", return_value=created) as run:
            url = _create_gate_issue(
                "owner/repo", "my-slug", ["s1", "s2"], {"s1": "session-retro-a.md"}
            )
        assert url == "https://github.com/owner/repo/issues/99"
        args = run.call_args[0][0]
        assert args[:4] == ["gh", "issue", "create", "--repo"]
        assert "Gate: my-slug" in args

    def test_should_return_none_when_create_fails(self):
        with patch("retro_kpis.subprocess.run", return_value=_proc(returncode=1)):
            assert _create_gate_issue("owner/repo", "my-slug", ["s1"], {}) is None

    def test_should_skip_all_when_gh_not_authenticated(self, capsys):
        with patch(
            "retro_kpis.subprocess.run", return_value=_proc(returncode=1)
        ) as run:
            file_gate_issues({"my-slug": ["s1", "s2"]}, [], "owner/repo")
        out = capsys.readouterr().out
        assert "übersprungen" in out
        run.assert_called_once()  # nur der auth-status-Check, keine Such-/Create-Calls danach

    def test_should_create_missing_and_report_existing_gate_issues(self, capsys):
        reports = [
            {
                "session_id": "s1",
                "_path": "session-retro-a.md",
                "recurring_findings": ["missing-slug"],
            },
            {
                "session_id": "s2",
                "_path": "session-retro-b.md",
                "recurring_findings": ["existing-slug"],
            },
        ]

        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["gh", "auth"]:
                return _proc(returncode=0)
            if cmd[:3] == ["gh", "issue", "list"]:
                if "existing-slug" in cmd[8]:
                    return _proc(
                        stdout='[{"number": 5, "title": "Gate: existing-slug", '
                        '"state": "CLOSED", "url": "https://x/5"}]'
                    )
                return _proc(stdout="[]")
            if cmd[:3] == ["gh", "issue", "create"]:
                return _proc(stdout="https://github.com/owner/repo/issues/77\n")
            raise AssertionError(f"unexpected call: {cmd}")

        gated = {"missing-slug": ["s1"], "existing-slug": ["s2"]}
        with patch("retro_kpis.subprocess.run", side_effect=fake_run):
            file_gate_issues(gated, reports, "owner/repo")

        out = capsys.readouterr().out
        assert "existing-slug: bereits vorhanden — CLOSED https://x/5" in out
        assert (
            "missing-slug: neu angelegt — https://github.com/owner/repo/issues/77"
            in out
        )
