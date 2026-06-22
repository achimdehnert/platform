"""Tests für tools/deploy_failure_monitor.py (Gate gegen deploy-failures-no-fix)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deploy_failure_monitor import (  # noqa: E402
    count_leading_failures,
    evaluate_repo,
    render_issue_body,
)


def _r(conclusion):
    return {
        "conclusion": conclusion,
        "headSha": "abcdef1234",
        "createdAt": "2026-06-22T06:00:00Z",
        "url": "u",
    }


class TestCountLeadingFailures:
    def test_should_count_consecutive_failures_from_top(self):
        runs = [_r("failure"), _r("failure"), _r("success")]
        assert count_leading_failures(runs) == 2

    def test_should_be_zero_when_latest_is_success(self):
        assert count_leading_failures([_r("success"), _r("failure")]) == 0

    def test_should_skip_in_progress_and_cancelled_without_breaking(self):
        # None (in_progress) + cancelled werden übersprungen, Serie läuft weiter
        runs = [_r(None), _r("cancelled"), _r("failure"), _r("failure"), _r("success")]
        assert count_leading_failures(runs) == 2

    def test_should_count_startup_failure_and_timed_out_as_failure(self):
        assert count_leading_failures([_r("startup_failure"), _r("timed_out")]) == 2

    def test_should_stop_streak_at_first_success_even_with_later_failures(self):
        runs = [_r("failure"), _r("success"), _r("failure"), _r("failure")]
        assert count_leading_failures(runs) == 1

    def test_should_be_zero_for_empty(self):
        assert count_leading_failures([]) == 0


class TestEvaluateRepo:
    def test_should_escalate_at_threshold(self):
        res = evaluate_repo(
            "illustration-hub", [_r("failure"), _r("failure")], threshold=2
        )
        assert res["escalate"] is True
        assert res["consecutive"] == 2
        assert len(res["runs"]) == 2

    def test_should_not_escalate_below_threshold(self):
        res = evaluate_repo("x", [_r("failure"), _r("success")], threshold=2)
        assert res["escalate"] is False
        assert res["consecutive"] == 1

    def test_should_respect_higher_threshold(self):
        res = evaluate_repo("x", [_r("failure"), _r("failure")], threshold=3)
        assert res["escalate"] is False


class TestRenderIssueBody:
    def test_should_include_count_repo_and_cheapest_check(self):
        res = evaluate_repo(
            "illustration-hub", [_r("failure"), _r("failure")], threshold=2
        )
        body = render_issue_body(res, org="achimdehnert")
        assert "2× konsekutiv" in body
        assert "achimdehnert/illustration-hub" in body
        assert "Billigster Check" in body


class TestFetchErrorNotGreen:
    """Regression: gh-Lesefehler darf NICHT als 'grün' durchgehen (2026-06-22)."""

    def test_fetch_runs_raises_on_nonzero_gh(self, monkeypatch):
        import subprocess

        from deploy_failure_monitor import FetchError, fetch_runs

        class _Res:
            returncode = 1
            stdout = ""
            stderr = "HTTP 403: Resource not accessible by integration"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Res())
        try:
            fetch_runs("achimdehnert", "weltenhub", 10)
            raised = False
        except FetchError as exc:
            raised = True
            assert "403" in str(exc)
        assert raised, (
            "fetch_runs muss bei gh-Fehler FetchError werfen, nicht [] (= grün)"
        )

    def test_fetch_runs_returns_empty_on_genuine_no_runs(self, monkeypatch):
        import subprocess

        from deploy_failure_monitor import fetch_runs

        class _Res:
            returncode = 0
            stdout = "[]"
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Res())
        assert fetch_runs("achimdehnert", "x", 10) == []


class TestNoDeployWorkflowIsNA:
    """Repo ohne 'Deploy'-Workflow → N/A, kein Fehler (2026-06-22 onboarding-hub)."""

    def test_fetch_runs_raises_no_deploy_workflow_not_fetcherror(self, monkeypatch):
        import subprocess

        from deploy_failure_monitor import FetchError, NoDeployWorkflow, fetch_runs

        class _Res:
            returncode = 1
            stdout = ""
            stderr = "gh: could not find any workflows named Deploy"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Res())
        try:
            fetch_runs("achimdehnert", "onboarding-hub", 10)
            raised = None
        except NoDeployWorkflow:
            raised = "na"
        except FetchError:
            raised = "fetch"
        assert raised == "na", (
            "kein Deploy-Workflow muss NoDeployWorkflow sein, nicht FetchError (rot)"
        )
