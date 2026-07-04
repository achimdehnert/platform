"""Tests für scripts/checks/handoff_banner_check.py (Gate `handover-stale-vor-merge`).

Retro f5e1d F-S3/F-P3 (×2 → Gate-Pflicht, Tracking platform#913): statische
HANDOFF-Dokumente müssen in den ersten 30 Zeilen ein Live-Status-Banner tragen
(`Live-Status:` + `#<nr>` oder URL). Läuft im tools-tests-Gate („Gate wächst mit",
claude-skills F-A) — der CI-Workflow selbst ist handoff-banner-gate.yml.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "checks" / "handoff_banner_check.py"

BANNER = (
    "> **Live-Status: achimdehnert/platform#913** — der Stand in diesem Dokument "
    "ist eingefroren; lebende Quelle ist das Issue.\n"
)


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_should_pass_when_banner_with_issue_ref_in_head(tmp_path):
    f = tmp_path / "HANDOFF-x.md"
    f.write_text("# Titel\n\n" + BANNER + "\nInhalt.\n")
    res = _run(str(f))
    assert res.returncode == 0, res.stdout + res.stderr
    assert "PASS" in res.stdout


def test_should_pass_when_banner_uses_url_instead_of_issue_number(tmp_path):
    f = tmp_path / "HANDOFF-x.md"
    f.write_text(
        "# Titel\n\n> Live-Status: https://github.com/achimdehnert/platform/issues/913\n"
    )
    res = _run(str(f))
    assert res.returncode == 0, res.stdout + res.stderr


def test_should_fail_when_banner_missing(tmp_path):
    f = tmp_path / "HANDOFF-x.md"
    f.write_text("# Titel\n\nKein Banner, nirgends.\n")
    res = _run(str(f))
    assert res.returncode == 1
    assert "FAIL" in res.stdout
    assert "Live-Status-Banner Pflicht" in res.stdout
    assert "f5e1d" in res.stdout


def test_should_fail_when_banner_below_head_window(tmp_path):
    f = tmp_path / "HANDOFF-x.md"
    f.write_text("# Titel\n" + "füller\n" * 40 + BANNER)
    res = _run(str(f))
    assert res.returncode == 1


def test_should_fail_when_live_status_lacks_issue_reference(tmp_path):
    # `Live-Status:` ohne #nr/URL zeigt auf nichts Lebendes → kein gültiges Banner.
    f = tmp_path / "HANDOFF-x.md"
    f.write_text("# Titel\n\n> Live-Status: siehe Tracking-Issue.\n")
    res = _run(str(f))
    assert res.returncode == 1


def test_should_report_one_exit_code_for_mixed_batch(tmp_path):
    ok = tmp_path / "HANDOFF-ok.md"
    ok.write_text("# T\n" + BANNER)
    bad = tmp_path / "HANDOFF-bad.md"
    bad.write_text("# T\nohne Banner\n")
    res = _run(str(ok), str(bad))
    assert res.returncode == 1
    assert "PASS" in res.stdout and "FAIL" in res.stdout


def test_should_skip_missing_files_instead_of_crashing(tmp_path):
    # Gelöschte Handoffs (Rename/Remove im PR) sind kein Gate-Fall.
    res = _run(str(tmp_path / "HANDOFF-geloescht.md"))
    assert res.returncode == 0
    assert "SKIP" in res.stdout


def test_should_exit_usage_error_without_args():
    res = _run()
    assert res.returncode == 2


def test_should_pass_on_retrofitted_repo_handoff_dogfood():
    # Dogfood-Beleg (Retro f5e1d R2): die im selben PR nachgerüstete Bestandsdatei
    # muss das Gate real bestehen — nicht nur synthetische Fixtures.
    handoff = REPO_ROOT / "docs" / "audits" / "HANDOFF-nl2x-fleet-2026-07-04.md"
    assert handoff.is_file(), "Bestands-Handoff fehlt — Test-Fixture-Annahme kaputt"
    res = _run(str(handoff))
    assert res.returncode == 0, res.stdout + res.stderr
