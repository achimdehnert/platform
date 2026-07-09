"""Tests für tools/backup_meter.py (ADR-241 §4)."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backup_meter import (  # noqa: E402
    evaluate_app,
    evaluate_drill,
    newest_snapshot_age_hours,
    render_report,
)

NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def _snap(tag, hours_ago):
    t = NOW - timedelta(hours=hours_ago)
    return {"time": t.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00", "tags": [tag]}


ENTRY = {"app": "risk-hub", "tag": "risk-hub", "max_age_hours": 26}


def test_should_pass_when_fresh_snapshot_within_soll():
    result = evaluate_app(ENTRY, [_snap("risk-hub", 4)], NOW)
    assert result["status"] == "ok"
    assert result["reasons"] == []


def test_should_flag_violation_when_no_snapshot_for_tag():
    result = evaluate_app(ENTRY, [_snap("other-hub", 1)], NOW)
    assert result["status"] == "violation"
    assert "kein restic-Snapshot" in result["reasons"][0]


def test_should_flag_violation_when_snapshot_too_old():
    result = evaluate_app(ENTRY, [_snap("risk-hub", 30)], NOW)
    assert result["status"] == "violation"
    assert "alt" in result["reasons"][0]


def test_should_defer_in_scaffold_mode_when_snapshots_none():
    # Offsite noch nicht provisioniert → deferred, NICHT violation (CI bleibt grün)
    result = evaluate_app(ENTRY, None, NOW)
    assert result["status"] == "deferred"


def test_should_defer_explicitly_marked_entry():
    entry = {"app": "frozen-hub", "deferred": True, "reason": "eingefroren"}
    result = evaluate_app(entry, [], NOW)
    assert result["status"] == "deferred"
    assert result["reasons"] == ["eingefroren"]


def test_should_pick_most_recent_snapshot_of_tag():
    snaps = [_snap("risk-hub", 30), _snap("risk-hub", 3), _snap("risk-hub", 50)]
    age = newest_snapshot_age_hours(snaps, "risk-hub", NOW)
    assert abs(age - 3.0) < 0.01


def test_should_parse_nanosecond_restic_timestamp():
    snaps = [{"time": "2026-06-21T08:00:00.123456789+00:00", "tags": ["x"]}]
    age = newest_snapshot_age_hours(snaps, "x", NOW)
    assert abs(age - 4.0) < 0.01


def test_should_flag_missing_drill_when_enforced(tmp_path):
    result = evaluate_drill(tmp_path, NOW, enforce=True)
    assert result["status"] == "violation"


def test_should_defer_missing_drill_when_not_enforced(tmp_path):
    # Default bis G3: kein Protokoll → deferred, NICHT violation (kein Spam)
    result = evaluate_drill(tmp_path, NOW, enforce=False)
    assert result["status"] == "deferred"


def test_should_pass_drill_when_recent_protocol(tmp_path):
    (tmp_path / "2026-06-20-risk-hub.md").write_text("drill ok")
    result = evaluate_drill(tmp_path, NOW, enforce=True)
    assert result["status"] == "ok"


def test_should_defer_stale_drill_when_not_enforced(tmp_path):
    import os
    p = tmp_path / "2026-01-01-risk-hub.md"
    p.write_text("alt")
    old = NOW.timestamp() - 200 * 86400
    os.utime(p, (old, old))
    assert evaluate_drill(tmp_path, NOW, enforce=False)["status"] == "deferred"
    assert evaluate_drill(tmp_path, NOW, enforce=True)["status"] == "violation"


def test_should_ignore_readme_in_drills(tmp_path):
    (tmp_path / "README.md").write_text("nur Doku")
    result = evaluate_drill(tmp_path, NOW, enforce=True)
    assert result["status"] == "violation"


def test_should_count_each_bucket_in_report():
    results = [
        {"app": "a", "status": "ok", "reasons": []},
        {"app": "b", "status": "violation", "reasons": ["kaputt"]},
        {"app": "c", "status": "deferred", "reasons": ["scaffold"]},
    ]
    report = render_report(results)
    assert "1 konform · 1 Verletzungen · 1 deferred" in report
    assert "**b**: kaputt" in report
