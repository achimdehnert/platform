"""Tests für tools/branch_protection_meter.py (ADR-242 §Rollout 4)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from branch_protection_meter import evaluate_repo, render_report  # noqa: E402


def _ruleset(enforcement="active", check="ci / gate", name="main-required-checks"):
    return {
        "name": name,
        "enforcement": enforcement,
        "rules": [
            {
                "type": "required_status_checks",
                "parameters": {"required_status_checks": [{"context": check}]},
            }
        ],
    }


ENTRY = {"repo": "demo-hub", "owner": "achimdehnert", "required_check": "ci / gate"}


def test_should_pass_when_active_ruleset_with_matching_check():
    result = evaluate_repo(ENTRY, [_ruleset()])
    assert result["status"] == "ok"
    assert result["reasons"] == []


def test_should_flag_missing_ruleset():
    result = evaluate_repo(ENTRY, [])
    assert result["status"] == "violation"
    assert "fehlt" in result["reasons"][0]


def test_should_flag_foreign_ruleset_name_as_missing():
    result = evaluate_repo(ENTRY, [_ruleset(name="andere-regel")])
    assert result["status"] == "violation"


def test_should_flag_disabled_enforcement_as_break_glass():
    result = evaluate_repo(ENTRY, [_ruleset(enforcement="disabled")])
    assert result["status"] == "violation"
    assert any("disabled" in r for r in result["reasons"])


def test_should_flag_wrong_check_context():
    result = evaluate_repo(ENTRY, [_ruleset(check="guardian")])
    assert result["status"] == "violation"
    assert any("ci / gate" in r for r in result["reasons"])


def test_should_collect_both_reasons_when_disabled_and_wrong_check():
    result = evaluate_repo(ENTRY, [_ruleset(enforcement="evaluate", check="falsch")])
    assert result["status"] == "violation"
    assert len(result["reasons"]) == 2


def test_should_skip_deferred_entries_without_violation():
    entry = dict(ENTRY, deferred="main-CI rot — erst F4-Fix")
    result = evaluate_repo(entry, [])
    assert result["status"] == "deferred"
    assert "F4" in result["reasons"][0]


def test_should_render_report_with_all_sections():
    results = [
        {"repo": "a-hub", "status": "ok", "reasons": []},
        {"repo": "b-hub", "status": "violation", "reasons": ["Ruleset fehlt"]},
        {"repo": "c-hub", "status": "deferred", "reasons": ["main-CI rot"]},
    ]
    report = render_report(results)
    assert "1 konform · 1 Verletzungen · 1 deferred" in report
    assert "**b-hub**: Ruleset fehlt" in report
    assert "c-hub: main-CI rot" in report
    assert "- a-hub" in report
