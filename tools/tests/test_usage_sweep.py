"""Tests für tools/usage_sweep.py (Issue #1076)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from usage_sweep import (  # noqa: E402
    compute_skill_usage,
    current_quarter_label,
    evaluate_kill_gates,
    evaluate_label_usage,
    evaluate_meter_consequence,
    extract_issue_label,
    extract_usage_events,
    find_scheduled_workflows,
    load_skill_inventory,
    skill_candidates,
)

NOW = datetime(2026, 7, 13, 6, 0, 0, tzinfo=timezone.utc)


# --- Messung 1: Skill-Nutzung -----------------------------------------------


def test_should_load_skill_inventory_from_md_filenames(tmp_path):
    (tmp_path / "adr.md").write_text("# /adr")
    (tmp_path / "session-start.md").write_text("# /session-start")
    (tmp_path / "not-a-skill.txt").write_text("ignored")

    result = load_skill_inventory(tmp_path)

    assert result == {"adr", "session-start"}


def test_should_return_empty_inventory_when_dir_missing(tmp_path):
    result = load_skill_inventory(tmp_path / "does-not-exist")
    assert result == set()


def test_should_extract_skill_slug_from_tool_use_block():
    obj = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "konzept"}},
            ]
        },
    }

    events = extract_usage_events(obj)

    assert events == [("konzept", "tool_use")]


def test_should_extract_skill_slug_from_typed_slash_command():
    obj = {
        "type": "user",
        "message": {"content": "<command-name>/session-start</command-name>\nbody"},
    }

    events = extract_usage_events(obj)

    assert events == [("session-start", "command")]


def test_should_ignore_skill_mentioned_only_as_text_reference():
    obj = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "siehe /adr-health für Details"}]},
    }

    events = extract_usage_events(obj)

    assert events == []


def test_should_count_events_within_window_from_jsonl_files(tmp_path):
    project_dir = tmp_path / "-home-devuser-github-platform"
    project_dir.mkdir()
    lines = [
        '{"type":"assistant","timestamp":"2026-07-10T00:00:00.000Z","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"konzept"}}]}}',
        '{"type":"user","timestamp":"2026-07-11T00:00:00.000Z","message":{"content":"<command-name>/session-start</command-name>"}}',
        '{"type":"user","timestamp":"2025-01-01T00:00:00.000Z","message":{"content":"<command-name>/old-skill</command-name>"}}',
        "not-json-garbage",
    ]
    (project_dir / "t.jsonl").write_text("\n".join(lines))

    window_start = datetime(2026, 7, 1, tzinfo=timezone.utc)
    usage, sources = compute_skill_usage(tmp_path, window_start)

    assert usage["konzept"] == 1
    assert usage["session-start"] == 1
    assert "old-skill" not in usage
    assert sources["tool_use"] == 1
    assert sources["command"] == 1


def test_should_flag_inventory_entries_with_zero_usage_as_candidates():
    inventory = {"adr", "session-start", "unused-skill"}
    from collections import Counter

    usage = Counter({"adr": 3, "session-start": 10})

    result = skill_candidates(inventory, usage)

    assert result == ["unused-skill"]


# --- Messung 2: Meter-ohne-Konsequenz ---------------------------------------


def test_should_find_scheduled_workflows_by_cron_trigger(tmp_path):
    (tmp_path / "scheduled.yml").write_text("on:\n  schedule:\n    - cron: '0 7 * * 1'\n")
    (tmp_path / "manual-only.yml").write_text("on:\n  workflow_dispatch:\n")

    result = find_scheduled_workflows(tmp_path)

    assert [p.name for p in result] == ["scheduled.yml"]


def test_should_extract_label_from_gh_issue_create_flag():
    text = 'gh issue create --title "x" --label sync-drift --body-file x.md'
    assert extract_issue_label(text) == "sync-drift"


def test_should_extract_label_from_gh_api_f_name_flag():
    text = 'gh api repos/x/labels -f name="fleet-drift" -f color="fbca04"'
    assert extract_issue_label(text) == "fleet-drift"


def test_should_return_none_when_no_label_pattern_present():
    assert extract_issue_label("echo hello world") is None


def test_should_flag_workflow_as_candidate_when_stale_unreacted_issue_exists():
    label_by_workflow = {"sync-drift-meter.yml": "sync-drift"}
    issues_by_label = {
        "sync-drift": [
            {"number": 1, "createdAt": "2026-01-01T00:00:00Z", "comments": 0, "state": "OPEN"},
        ]
    }

    result = evaluate_meter_consequence(label_by_workflow, issues_by_label, NOW)

    assert len(result) == 1
    assert result[0]["workflow"] == "sync-drift-meter.yml"
    assert result[0]["stale_issues"] == [1]


def test_should_not_flag_workflow_when_stale_issue_was_commented():
    label_by_workflow = {"x.yml": "lbl"}
    issues_by_label = {
        "lbl": [
            {"number": 1, "createdAt": "2026-01-01T00:00:00Z", "comments": 2, "state": "OPEN"},
        ]
    }

    result = evaluate_meter_consequence(label_by_workflow, issues_by_label, NOW)

    assert result == []


def test_should_not_flag_workflow_when_stale_issue_is_closed():
    label_by_workflow = {"x.yml": "lbl"}
    issues_by_label = {
        "lbl": [
            {"number": 1, "createdAt": "2026-01-01T00:00:00Z", "comments": 0, "state": "CLOSED"},
        ]
    }

    result = evaluate_meter_consequence(label_by_workflow, issues_by_label, NOW)

    assert result == []


def test_should_not_flag_workflow_when_issue_younger_than_min_age():
    label_by_workflow = {"x.yml": "lbl"}
    issues_by_label = {
        "lbl": [
            {"number": 1, "createdAt": "2026-07-01T00:00:00Z", "comments": 0, "state": "OPEN"},
        ]
    }

    result = evaluate_meter_consequence(label_by_workflow, issues_by_label, NOW, min_age_days=90)

    assert result == []


# --- Messung 3: Label-Nutzung ------------------------------------------------


def test_should_flag_labels_with_zero_issues_in_window():
    all_labels = ["bug", "unused-label", "docu-quality"]
    issues_in_window = [
        {"labels": [{"name": "bug"}]},
        {"labels": [{"name": "docu-quality"}]},
    ]

    result = evaluate_label_usage(all_labels, issues_in_window)

    assert result == ["unused-label"]


def test_should_return_no_candidates_when_all_labels_used():
    all_labels = ["bug"]
    issues_in_window = [{"labels": [{"name": "bug"}]}]

    assert evaluate_label_usage(all_labels, issues_in_window) == []


# --- Messung 4: Kill-Gate-Vollzug --------------------------------------------


def test_should_report_not_checkable_when_no_report_body():
    result = evaluate_kill_gates(None, NOW)
    assert result["checked"] is False
    assert result["candidates"] == []


def test_should_report_not_checkable_when_no_kill_gate_section():
    body = "## Fleet-Drift-Report\n\n### 1. Registry-Konsistenz\nn=2 geprüft"
    result = evaluate_kill_gates(body, NOW)
    assert result["checked"] is False


def test_should_extract_overdue_kill_gate_lines():
    body = (
        "## Report\n\n"
        "### Kill-Gates\n"
        "- ADR-233 Snap-back-Guard seit 2026-05-01 überfällig\n"
        "- Frisches Item seit 2026-07-10 noch jung\n"
        "\n### Naechster Abschnitt\nirrelevant"
    )
    result = evaluate_kill_gates(body, NOW, min_age_days=30)

    assert result["checked"] is True
    assert len(result["candidates"]) == 1
    assert "2026-05-01" in result["candidates"][0]


# --- Sonstiges ----------------------------------------------------------------


def test_should_format_current_quarter_label():
    assert current_quarter_label(datetime(2026, 7, 13, tzinfo=timezone.utc)) == "2026-Q3"
    assert current_quarter_label(datetime(2026, 1, 1, tzinfo=timezone.utc)) == "2026-Q1"
    assert current_quarter_label(datetime(2026, 12, 31, tzinfo=timezone.utc)) == "2026-Q4"
