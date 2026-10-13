"""Tests für tools/branch_protection_meter.py (ADR-242 §Rollout 4)."""

import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import branch_protection_meter as bpm  # noqa: E402
from branch_protection_meter import load_expected, main, render_report  # noqa: E402


def evaluate_repo(entry: dict, rulesets: list) -> dict:
    """Testhelfer: Wave-Eintrag + Rulesets durch den Produktivpfad (soll_aus_wave →
    ist_zusammenfassen → bewerte); `reasons` = `gruende`."""
    ist = bpm.ist_zusammenfassen(rulesets, None)
    ist["rulesets"] = rulesets
    e = bpm.bewerte(bpm.soll_aus_wave(entry), ist)
    e["reasons"] = e["gruende"]
    return e


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
    assert result["status"] == "drift"
    assert "fehlt" in result["reasons"][0]


def test_should_count_foreign_ruleset_as_ist_but_note_missing_named_ruleset():
    """KONZ-070 Z4: Soll ist Mindestmass — ein aktives Ruleset anderen Namens, das den
    Check fordert, ist Schutz. Dass `main-required-checks` (ADR-242, Break-Glass-Zaehler)
    fehlt, steht sichtbar im Ist."""
    result = evaluate_repo(ENTRY, [_ruleset(name="andere-regel")])
    assert result["status"] == "ok"
    assert "Ruleset main-required-checks fehlt" in result["ist"]


def test_should_flag_disabled_enforcement_as_break_glass():
    result = evaluate_repo(ENTRY, [_ruleset(enforcement="disabled")])
    assert result["status"] == "drift"
    assert any("disabled" in r for r in result["reasons"])


def test_should_flag_wrong_check_context():
    result = evaluate_repo(ENTRY, [_ruleset(check="guardian")])
    assert result["status"] == "drift"
    assert any("ci / gate" in r for r in result["reasons"])


def test_should_collect_both_reasons_when_disabled_and_wrong_check():
    result = evaluate_repo(ENTRY, [_ruleset(enforcement="evaluate", check="falsch")])
    assert result["status"] == "drift"
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
        {
            "repo": "b-hub",
            "status": "drift",
            "reasons": ["Ruleset fehlt"],
            "befehl": "bash tools/apply-branch-protection.sh --repo b-hub",
        },
        {"repo": "c-hub", "status": "deferred", "reasons": ["main-CI rot"]},
    ]
    report = render_report(results)
    assert "1 konform · 1 Drift · 0 nicht messbar · 1 deferred" in report
    assert "**b-hub**: Ruleset fehlt" in report
    assert "c-hub: main-CI rot" in report
    assert "- a-hub" in report


class TestNetworkErrorDegradation:
    """F-6 (repo-optimize 2026-07-03): main() fing bisher nur HTTPError aus
    fetch_rulesets — URLError/TimeoutError (DNS-Fehler, Verbindungsabbruch,
    `_api_get`-Timeout=30) crashten den GESAMTEN Fleet-Scan statt nur das eine
    Repo als 'nicht lesbar' zu degradieren. Regression-Guard: der Scan muss bei
    einem simulierten URLError bzw. TimeoutError für ein Repo weiterlaufen und
    NUR dieses eine Repo als 'nicht messbar' melden (KONZ-070 Z4: Exit 2, nicht
    Drift — Schweigen waere Schein-Gruen, Drift waere Schein-Rot)."""

    def _run(self, monkeypatch, tmp_path, side_effects):
        # keyed by repo: messen() laeuft parallel, Aufrufreihenfolge ist nicht fix
        effekte = dict(zip(["unreachable-hub", "healthy-hub"], side_effects))

        def fake_fetch_rulesets(owner, repo, token):
            effect = effekte[repo]
            if isinstance(effect, Exception):
                raise effect
            return effect

        monkeypatch.setattr(bpm, "fetch_rulesets", fake_fetch_rulesets)
        monkeypatch.setattr(bpm, "fetch_classic", lambda owner, repo, token: None)
        monkeypatch.setenv("TOKEN", "dummy")
        expected = tmp_path / "expected.json"
        expected.write_text(
            json.dumps(
                [
                    {
                        "repo": "unreachable-hub",
                        "owner": "achimdehnert",
                        "required_check": "ci / gate",
                    },
                    {
                        "repo": "healthy-hub",
                        "owner": "achimdehnert",
                        "required_check": "ci / gate",
                    },
                ]
            )
        )
        report_path = tmp_path / "report.md"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "branch_protection_meter.py",
                "--expected",
                str(expected),
                "--report",
                str(report_path),
            ],
        )
        return main(), report_path.read_text()

    def test_should_degrade_urlerror_to_nicht_messbar_and_keep_scanning(
        self, monkeypatch, tmp_path
    ):
        rc, report = self._run(
            monkeypatch,
            tmp_path,
            [urllib.error.URLError("Name or service not known"), [_ruleset()]],
        )
        assert rc == 2  # nicht messbar → non-zero, aber KEIN Crash und keine Drift
        assert "nicht messbar" in report
        assert "unreachable-hub" in report
        assert "- healthy-hub" in report  # zweites Repo lief trotzdem konform durch

    def test_should_degrade_timeout_error_to_nicht_messbar_and_keep_scanning(
        self, monkeypatch, tmp_path
    ):
        rc, report = self._run(
            monkeypatch,
            tmp_path,
            [TimeoutError("timed out"), [_ruleset()]],
        )
        assert rc == 2
        assert "unreachable-hub" in report
        assert "- healthy-hub" in report
