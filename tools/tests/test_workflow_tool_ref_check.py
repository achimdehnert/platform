"""Tests für scripts/checks/workflow_tool_ref_check.py (Gate `workflow-tool-ref`,
Issue #1310, Retro session-retro-2026-07-21-platform-8d663b Befund B2).

Kernpunkt (ADR-058-konform, "test_should_..."-Konvention): die Assertion muss auf die
Aufruf-Form `mcp__orchestrator__estimate_job:` zielen, nicht auf den nackten String —
sonst wäre eine Verneinungs-Prosa-Zeile ("estimate_job existiert nicht mehr") ein
False-Positive-PASS gewesen, genau der ~3-Monate-Bug aus mcp-hub#180.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "checks" / "workflow_tool_ref_check.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_should_pass_when_call_form_present(tmp_path):
    f = tmp_path / "ship.md"
    f.write_text(
        "## Schritt 2\n\n"
        "mcp__orchestrator__estimate_job:\n"
        "  job_type: deploy\n",
        encoding="utf-8",
    )
    res = _run(str(f))
    assert res.returncode == 0, res.stdout + res.stderr
    assert "PASS" in res.stdout


def test_should_pass_when_call_form_is_indented_yaml(tmp_path):
    # ship.md/backup.md nutzen die Tool-Aufruf-Zeile oft eingerückt unter einem Bullet.
    f = tmp_path / "backup.md"
    f.write_text(
        "- Schritt:\n"
        "    mcp__orchestrator__estimate_job:\n"
        "      job_type: backup\n",
        encoding="utf-8",
    )
    res = _run(str(f))
    assert res.returncode == 0, res.stdout + res.stderr


def test_should_fail_on_negation_prose_golden_test(tmp_path):
    # Golden-Test aus Issue #1310: ein konstruierter Verneinungssatz enthält den nackten
    # String "estimate_job", aber NICHT die Aufruf-Form — darf das Gate NICHT grün machen.
    f = tmp_path / "ship.md"
    f.write_text(
        "## Hinweis\n\n"
        "estimate_job existiert nicht mehr in diesem Workflow, wurde entfernt.\n",
        encoding="utf-8",
    )
    res = _run(str(f))
    assert res.returncode == 1
    assert "FAIL" in res.stdout


def test_should_fail_on_other_negation_prose_variant(tmp_path):
    f = tmp_path / "backup.md"
    f.write_text(
        "kein estimate_job mehr nötig — Schritt wurde gestrichen.\n",
        encoding="utf-8",
    )
    res = _run(str(f))
    assert res.returncode == 1
    assert "FAIL" in res.stdout


def test_should_fail_when_tool_reference_missing_entirely(tmp_path):
    f = tmp_path / "ship.md"
    f.write_text("## Schritt 1\n\nkeine Tool-Referenz hier.\n", encoding="utf-8")
    res = _run(str(f))
    assert res.returncode == 1
    assert "FAIL" in res.stdout


def test_should_fail_when_requested_file_is_missing(tmp_path):
    # Regression: ein SKIP hier machte das Gate still grün, sobald ship.md/backup.md
    # umbenannt oder (ADR-280/281) nach skills/ verschoben werden — der Workflow ruft
    # feste Pfade auf, nicht eine diff-gefilterte Liste.
    res = _run(str(tmp_path / "ship-verschoben.md"))
    assert res.returncode == 1
    assert "MISS" in res.stdout


def test_should_skip_missing_file_only_with_allow_missing(tmp_path):
    res = _run("--allow-missing", str(tmp_path / "ship-geloescht.md"))
    assert res.returncode == 0
    assert "SKIP" in res.stdout


def test_should_still_check_existing_files_with_allow_missing(tmp_path):
    ok = tmp_path / "ship.md"
    ok.write_text("mcp__orchestrator__estimate_job:\n  job_type: deploy\n", encoding="utf-8")
    bad = tmp_path / "backup.md"
    bad.write_text("estimate_job existiert nicht mehr.\n", encoding="utf-8")
    res = _run("--allow-missing", str(ok), str(bad), str(tmp_path / "weg.md"))
    assert res.returncode == 1
    assert "PASS" in res.stdout and "FAIL" in res.stdout and "SKIP" in res.stdout


def test_should_exit_usage_error_without_args():
    res = _run()
    assert res.returncode == 2


def test_should_report_one_exit_code_for_mixed_batch(tmp_path):
    ok = tmp_path / "ship.md"
    ok.write_text("mcp__orchestrator__estimate_job:\n  job_type: deploy\n", encoding="utf-8")
    bad = tmp_path / "backup.md"
    bad.write_text("estimate_job existiert nicht mehr.\n", encoding="utf-8")
    res = _run(str(ok), str(bad))
    assert res.returncode == 1
    assert "PASS" in res.stdout and "FAIL" in res.stdout


def test_should_pass_on_platform_own_ship_and_backup_workflows_dogfood():
    # Dogfood: die realen platform-Workflows müssen das Gate bestehen, nicht nur
    # synthetische Fixtures (sonst hätte das Gate beim ersten Merge sofort geblockt).
    ship = REPO_ROOT / ".windsurf" / "workflows" / "ship.md"
    backup = REPO_ROOT / ".windsurf" / "workflows" / "backup.md"
    assert ship.is_file(), "ship.md fehlt — Test-Fixture-Annahme kaputt"
    assert backup.is_file(), "backup.md fehlt — Test-Fixture-Annahme kaputt"
    res = _run(str(ship), str(backup))
    assert res.returncode == 0, res.stdout + res.stderr
