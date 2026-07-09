"""Tests für tools/branch_protection_meter.py (ADR-242 §Rollout 4)."""

import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import branch_protection_meter as bpm  # noqa: E402
from branch_protection_meter import evaluate_repo, load_expected, main, render_report  # noqa: E402


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


def test_should_merge_multiple_expected_files(tmp_path):
    f1 = tmp_path / "wave1.json"
    f2 = tmp_path / "wave2.json"
    f1.write_text(json.dumps([{"repo": "a-hub"}, {"repo": "b-hub"}]))
    f2.write_text(json.dumps([{"repo": "c-hub"}]))
    merged = load_expected([str(f1), str(f2)])
    assert [e["repo"] for e in merged] == ["a-hub", "b-hub", "c-hub"]


def test_should_load_single_expected_file(tmp_path):
    f1 = tmp_path / "wave1.json"
    f1.write_text(json.dumps([{"repo": "a-hub"}]))
    assert load_expected([str(f1)]) == [{"repo": "a-hub"}]


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


class TestNetworkErrorDegradation:
    """F-6 (repo-optimize 2026-07-03): main() fing bisher nur HTTPError aus
    fetch_rulesets — URLError/TimeoutError (DNS-Fehler, Verbindungsabbruch,
    `_api_get`-Timeout=30) crashten den GESAMTEN Fleet-Scan statt nur das eine
    Repo als 'nicht lesbar' zu degradieren. Regression-Guard: der Scan muss bei
    einem simulierten URLError bzw. TimeoutError für ein Repo weiterlaufen und
    NUR dieses eine Repo als Verletzung melden."""

    def _run(self, monkeypatch, tmp_path, side_effects):
        calls = iter(side_effects)

        def fake_fetch_rulesets(owner, repo, token):
            effect = next(calls)
            if isinstance(effect, Exception):
                raise effect
            return effect

        monkeypatch.setattr(bpm, "fetch_rulesets", fake_fetch_rulesets)
        monkeypatch.setenv("TOKEN", "dummy")
        expected = tmp_path / "expected.json"
        expected.write_text(
            json.dumps(
                [
                    {"repo": "unreachable-hub", "owner": "achimdehnert", "required_check": "ci / gate"},
                    {"repo": "healthy-hub", "owner": "achimdehnert", "required_check": "ci / gate"},
                ]
            )
        )
        report_path = tmp_path / "report.md"
        monkeypatch.setattr(
            sys,
            "argv",
            ["branch_protection_meter.py", "--expected", str(expected), "--report", str(report_path)],
        )
        return main(), report_path.read_text()

    def test_should_degrade_urlerror_to_violation_and_keep_scanning(self, monkeypatch, tmp_path):
        rc, report = self._run(
            monkeypatch,
            tmp_path,
            [urllib.error.URLError("Name or service not known"), [_ruleset()]],
        )
        assert rc == 1  # mindestens eine Verletzung → non-zero, aber KEIN Crash
        assert "unreachable-hub" in report
        assert "healthy-hub" in report
        assert "- healthy-hub" in report  # zweites Repo lief trotzdem konform durch

    def test_should_degrade_timeout_error_to_violation_and_keep_scanning(self, monkeypatch, tmp_path):
        rc, report = self._run(
            monkeypatch,
            tmp_path,
            [TimeoutError("timed out"), [_ruleset()]],
        )
        assert rc == 1
        assert "unreachable-hub" in report
        assert "- healthy-hub" in report
