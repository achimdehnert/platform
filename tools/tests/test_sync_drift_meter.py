"""Tests für tools/sync_drift_meter.py (ADR-265 REC-3 / Option 1, Issue #949).

Nur die Parse-/Klassifikations-/Report-Funktionen gegen Fixture-Strings —
KEIN echter Fleet-Lauf, kein Netz (siehe Issue #949 Akzeptanzkriterium 3).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sync_drift_meter import (  # noqa: E402
    has_drift,
    parse_sync_output,
    render_report,
)

NO_DRIFT_OUTPUT = """\
=== Workflow Sync ===
Source: /home/runner/github/platform/.windsurf/workflows
Workflows: 27 universal + 22 django-hub + 1 package

=== Done ===
SKIP-SUMMARY: 0 Repos übersprungen
"""

SKIP_REPO_OUTPUT = """\
=== Workflow Sync ===
Source: /home/runner/github/platform/.windsurf/workflows
Workflows: 27 universal + 22 django-hub + 1 package

📦 some-repo
  SKIP-REPO: '.windsurf/' nicht in .gitignore — Zeile committen, dann sync (ADR-265)

=== Done ===
SKIP-SUMMARY: 1 Repo(s) übersprungen (SKIP-REPO: some-repo; SKIP-TRACKED: )
"""

SKIP_TRACKED_OUTPUT = """\
=== Workflow Sync ===
Source: /home/runner/github/platform/.windsurf/workflows
Workflows: 27 universal + 22 django-hub + 1 package

📦 risk-hub (django-hub)
  SKIP-TRACKED: adr.md ist im Index getrackt — erst 'git rm --cached' (ADR-265)

=== Done ===
SKIP-SUMMARY: 1 Repo(s) übersprungen (SKIP-REPO: ; SKIP-TRACKED: risk-hub)
"""

MIXED_OUTPUT = """\
=== Workflow Sync ===
Source: /home/runner/github/platform/.windsurf/workflows
Workflows: 27 universal + 22 django-hub + 1 package

📦 alpha-hub
  SKIP-REPO: '.windsurf/' nicht in .gitignore — Zeile committen, dann sync (ADR-265)
📦 beta-hub (django-hub)
  SKIP-TRACKED: adr.md ist im Index getrackt — erst 'git rm --cached' (ADR-265)
📦 gamma-hub (package)
  FIX-LINK: release.md (/old/path/release.md → /new/path/release.md)

=== Done ===
SKIP-SUMMARY: 2 Repo(s) übersprungen (SKIP-REPO: alpha-hub; SKIP-TRACKED: beta-hub)
"""

STALE_ONLY_OUTPUT = """\
=== Workflow Sync ===
Source: /home/runner/github/platform/.windsurf/workflows
Workflows: 27 universal + 22 django-hub + 1 package

📦 delta-hub (other)
  FIX-LINK: prompt.md (/old/prompt.md → /new/prompt.md)
  FIX-LINK: adr.md (/old/adr.md → /new/adr.md)

=== Done ===
SKIP-SUMMARY: 0 Repos übersprungen
"""

BROKEN_OUTPUT = """\
=== Workflow Sync ===
ERROR: Registry nicht gefunden: /home/runner/github/platform/registry/github_repos.yaml
"""


def test_should_parse_zero_drift_when_no_skips_reported():
    parsed = parse_sync_output(NO_DRIFT_OUTPUT)
    assert parsed["total_skips"] == 0
    assert parsed["skip_repo"] == []
    assert parsed["skip_tracked"] == []
    assert parsed["stale"] == []
    assert parsed["summary_line"] is not None
    assert not has_drift(parsed)


def test_should_classify_skip_repo_from_summary_line():
    parsed = parse_sync_output(SKIP_REPO_OUTPUT)
    assert parsed["skip_repo"] == ["some-repo"]
    assert parsed["skip_tracked"] == []
    assert parsed["total_skips"] == 1
    assert has_drift(parsed)


def test_should_classify_skip_tracked_from_summary_line():
    parsed = parse_sync_output(SKIP_TRACKED_OUTPUT)
    assert parsed["skip_repo"] == []
    assert parsed["skip_tracked"] == ["risk-hub"]
    assert has_drift(parsed)


def test_should_classify_stale_from_fix_link_in_repo_block():
    parsed = parse_sync_output(STALE_ONLY_OUTPUT)
    assert parsed["stale"] == ["delta-hub"]
    # FIX-LINK allein zaehlt nicht in die SKIP-SUMMARY (nur SKIP-REPO/TRACKED),
    # ist aber trotzdem Drift laut has_drift().
    assert parsed["total_skips"] == 0
    assert has_drift(parsed)


def test_should_classify_all_three_categories_independently():
    parsed = parse_sync_output(MIXED_OUTPUT)
    assert parsed["skip_repo"] == ["alpha-hub"]
    assert parsed["skip_tracked"] == ["beta-hub"]
    assert parsed["stale"] == ["gamma-hub"]
    assert parsed["total_skips"] == 2


def test_should_not_duplicate_stale_repo_on_multiple_fix_links():
    parsed = parse_sync_output(STALE_ONLY_OUTPUT)
    # delta-hub hat 2 FIX-LINK-Zeilen -> trotzdem nur 1x in stale
    assert parsed["stale"].count("delta-hub") == 1


def test_should_report_no_summary_line_when_run_aborted_before_summary():
    parsed = parse_sync_output(BROKEN_OUTPUT)
    assert parsed["summary_line"] is None
    assert not has_drift(parsed)  # Aufruffehler != Drift-Klassifikation


def test_should_render_clean_report_when_no_drift():
    parsed = parse_sync_output(NO_DRIFT_OUTPUT)
    report = render_report(parsed, exit_code=0)
    assert "0 Drift" in report
    assert "SKIP-REPO" not in report.split("\n", 2)[-1] or "## SKIP-REPO" not in report


def test_should_render_all_three_sections_when_mixed_drift():
    parsed = parse_sync_output(MIXED_OUTPUT)
    report = render_report(parsed, exit_code=1)
    assert "## SKIP-REPO" in report
    assert "alpha-hub" in report
    assert "## SKIP-TRACKED" in report
    assert "beta-hub" in report
    assert "## STALE" in report
    assert "gamma-hub" in report


def test_should_strip_whitespace_from_split_names():
    parsed = parse_sync_output(
        "SKIP-SUMMARY: 2 Repo(s) übersprungen "
        "(SKIP-REPO:  a-hub , b-hub ; SKIP-TRACKED: )\n"
    )
    assert parsed["skip_repo"] == ["a-hub", "b-hub"]
    assert parsed["skip_tracked"] == []
