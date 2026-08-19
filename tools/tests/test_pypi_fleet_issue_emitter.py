"""Tests für tools/pypi_fleet_issue_emitter.py (pure functions, #2075 K4)."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypi_fleet_issue_emitter import (  # noqa: E402
    canary_finding,
    issue_body,
    issue_title,
    select_findings,
)

TODAY = dt.date(2026, 8, 19)


def test_should_build_deterministic_canary_title():
    f = canary_finding(TODAY)
    assert issue_title(f) == (
        "[pypi-fleet:canary] Loop-Canary: registry/pypi-loop-canary.txt "
        "auf 2026-08-19 nachziehen"
    )


def test_should_include_queue_contract_sections_in_body():
    body = issue_body(canary_finding(TODAY), TODAY)
    assert "## Betroffene Komponenten" in body
    assert "## Akzeptanzkriterien" in body
    assert "last_cycle: 2026-08-19" in body


def test_should_filter_by_allowlist_default_canary_only():
    findings = [
        {"repo": "aifw", "org": "achimdehnert", "metric": "M4", "text": "lag"},
        canary_finding(TODAY),
    ]
    picked = select_findings(findings, ("canary",), 3)
    assert [f["metric"] for f in picked] == ["canary"]


def test_should_cap_number_of_issues():
    findings = [canary_finding(TODAY) for _ in range(5)]
    assert len(select_findings(findings, ("canary",), 2)) == 2
