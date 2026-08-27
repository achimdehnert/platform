"""Tests für tools/pypi_fleet_issue_emitter.py (pure functions, #2075 K4).

Die Loop-Canary (registry/pypi-loop-canary.txt) ist mit KONZ-052 V5 entfernt
(hat den Zyklus einmal real bewiesen, PR #2096) — Tests decken jetzt nur noch
echte Frühwarn-Befunde ab.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypi_fleet_issue_emitter import (  # noqa: E402
    DEFAULT_ALLOWLIST,
    issue_body,
    issue_title,
    main,
    select_findings,
)

TODAY = dt.date(2026, 8, 19)

FINDING_M4 = {
    "repo": "aifw",
    "org": "achimdehnert",
    "metric": "M4",
    "text": "aifw hinkt 2 Minor-Versionen hinter PyPI",
}


def test_should_build_deterministic_title_from_metric_and_text():
    assert issue_title(FINDING_M4) == (
        "[pypi-fleet:M4] aifw hinkt 2 Minor-Versionen hinter PyPI"
    )


def test_should_include_queue_contract_sections_in_body():
    body = issue_body(FINDING_M4, TODAY)
    assert "## Betroffene Komponenten" in body
    assert "## Akzeptanzkriterien" in body
    assert "achimdehnert/aifw" in body


def test_should_have_empty_default_allowlist():
    # KONZ-052 V5: keine Klasse ist scharf, bis der Owner sie bewusst
    # zuschaltet (#2084) — der Lauf ohne Allowlist-Klasse ist stiller No-Op.
    assert DEFAULT_ALLOWLIST == ()


def test_should_skip_silently_when_allowlist_empty_by_default():
    findings = [FINDING_M4, {**FINDING_M4, "metric": "M2"}]
    picked = select_findings(findings, DEFAULT_ALLOWLIST, 3)
    assert picked == []


def test_should_filter_by_explicit_allowlist():
    findings = [
        FINDING_M4,
        {"repo": "testkit", "org": "achimdehnert", "metric": "M2", "text": "lag"},
    ]
    picked = select_findings(findings, ("M4",), 3)
    assert [f["metric"] for f in picked] == ["M4"]


def test_should_cap_number_of_issues():
    findings = [FINDING_M4 for _ in range(5)]
    assert len(select_findings(findings, ("M4",), 2)) == 2


def test_should_run_cli_without_findings_or_allowlist_as_silent_noop(
    monkeypatch, capsys, tmp_path
):
    # Regression: DEFAULT_ALLOWLIST=() -> ",".join(()) == "" -> "".split(",")
    # liefert [''], nicht []. main() muss das trotzdem als 0 Klassen behandeln,
    # nicht als eine Klasse namens "".
    findings_file = tmp_path / "findings.json"
    findings_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["pypi_fleet_issue_emitter.py", "--findings", str(findings_file)]
    )
    rc = main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "0 nach Allowlist" in out
    assert "0 Issue(s) erstellt" in out
