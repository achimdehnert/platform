"""Tests für tools/break_glass_meter.py (KONZ-platform-004 Kill-Gate)."""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from break_glass_meter import (  # noqa: E402
    evaluate,
    iso_week,
    render_report,
    within_window,
)

NOW = dt.datetime(2026, 7, 20, 12, 0, tzinfo=dt.timezone.utc)


def _suite(pushed_at, actor="achimdehnert"):
    return {"pushed_at": pushed_at, "actor_name": actor, "result": "bypass"}


def test_should_report_zero_when_no_bypasses():
    verdict = evaluate([], weeks=2, threshold_per_week=1.0, now=NOW)
    assert verdict["count"] == 0
    assert verdict["breached"] is False


def test_should_breach_when_rate_reaches_threshold():
    suites = [_suite("2026-07-19T10:00:00Z"), _suite("2026-07-14T10:00:00Z")]
    verdict = evaluate(suites, weeks=2, threshold_per_week=1.0, now=NOW)
    assert verdict["count"] == 2
    assert verdict["rate_per_week"] == 1.0
    assert verdict["breached"] is True


def test_should_not_breach_below_threshold():
    verdict = evaluate([_suite("2026-07-19T10:00:00Z")], 2, 1.0, NOW)
    assert verdict["rate_per_week"] == 0.5
    assert verdict["breached"] is False


def test_should_ignore_bypasses_outside_window():
    """Ein Break-Glass von vor 10 Wochen darf das 2-Wochen-Fenster nicht rötten."""
    verdict = evaluate([_suite("2026-05-01T10:00:00Z")], 2, 1.0, NOW)
    assert verdict["count"] == 0


def test_should_count_unparseable_timestamp_instead_of_dropping_it():
    """Unlesbares Datum wird eingeschlossen — ein stiller Verlust waere der Fund."""
    assert within_window("nicht-ein-datum", NOW - dt.timedelta(weeks=2)) is True
    verdict = evaluate([_suite("nicht-ein-datum")], 2, 1.0, NOW)
    assert verdict["count"] == 1


def test_should_group_by_actor():
    suites = [_suite("2026-07-19T10:00:00Z", "a"), _suite("2026-07-18T10:00:00Z", "a")]
    verdict = evaluate(suites, 2, 1.0, NOW)
    assert verdict["per_actor"] == {"a": 2}


def test_should_group_by_iso_week():
    assert iso_week("2026-07-20T06:57:10Z") == "2026-W30"
    assert iso_week("") == "unknown"
    assert iso_week("kaputt") == "unknown"


def test_should_list_unreadable_repos_separately_from_clean():
    """Ein API-Fehler darf nicht als 'unauffaellig' durchgehen."""
    results = [
        {"repo": "a", "count": 0, "breached": False, "per_actor": {}, "per_week": {}},
        {"repo": "b", "error": "rule-suites-API nicht lesbar (HTTP 403)"},
    ]
    report = render_report(results, weeks=2, threshold_per_week=1.0)
    assert "Nicht lesbar (kein Freispruch)" in report
    assert "HTTP 403" in report
    assert "1 über Schwelle" not in report
