"""Tests für tools/deploy_failure_monitor.py (Gate gegen deploy-failures-no-fix)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import deploy_failure_monitor as dfm  # noqa: E402
from deploy_failure_monitor import (  # noqa: E402
    count_leading_failures,
    evaluate_repo,
    render_issue_body,
    resolve_org,
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


class TestCappedCountLabel:
    """#8b: capped-Serie zeigt ≥N statt zu niedriges exaktes N."""

    def test_capped_when_all_fetched_are_failures(self):
        from deploy_failure_monitor import _count_label, evaluate_repo

        runs = [_r("failure")] * 10  # alle geholten = Fehler → Serie evtl. länger
        res = evaluate_repo("x", runs, threshold=2)
        assert res["capped"] is True
        assert _count_label(res) == "≥10×"

    def test_not_capped_when_success_breaks_series(self):
        from deploy_failure_monitor import _count_label, evaluate_repo

        runs = [_r("failure"), _r("failure"), _r("success")]
        res = evaluate_repo("x", runs, threshold=2)
        assert res["capped"] is False
        assert _count_label(res) == "2×"


class TestResolveOrgPerRepo:
    """F-7 (repo-optimize 2026-07-03): Owner PRO REPO über registry_api.owner()
    statt fixem --org achimdehnert für die gesamte Flotte (risk-hub/
    ausschreibungs-hub liegen laut Registry unter iilgmbh)."""

    def test_should_delegate_to_registry_owner(self, monkeypatch):
        monkeypatch.setattr(
            dfm, "registry_owner", lambda name: {"risk-hub": "iilgmbh"}.get(name)
        )
        assert resolve_org("risk-hub") == "iilgmbh"

    def test_should_return_none_for_registry_unresolvable_repo(self, monkeypatch):
        monkeypatch.setattr(dfm, "registry_owner", lambda name: None)
        assert resolve_org("some-unknown-repo") is None


class TestMainWarnDegradesUnresolvableOwner:
    """F-5-Folge (Precisions #4): owner()=None darf den Monitor-Lauf NICHT
    crashen — Repo wird als 'nicht in Registry' übersprungen, Lauf geht weiter."""

    def _patch_common(self, monkeypatch, owner_map, run_map):
        monkeypatch.setattr(dfm, "load_deploy_repos", lambda: list(run_map))
        monkeypatch.setattr(dfm, "resolve_org", lambda repo: owner_map.get(repo))

        def fake_fetch_runs(org, repo, limit):
            return run_map[repo]

        monkeypatch.setattr(dfm, "fetch_runs", fake_fetch_runs)
        monkeypatch.setattr(
            dfm, "escalate_issue", lambda org, repo, result, dry_run: f"escalated {repo}@{org}"
        )

    def test_should_skip_unresolvable_repo_without_crash_and_keep_scanning(
        self, monkeypatch, capsys
    ):
        owner_map = {"healthy-hub": "achimdehnert"}  # "ghost-hub" bewusst NICHT drin
        run_map = {"ghost-hub": [], "healthy-hub": [_r("success")]}
        self._patch_common(monkeypatch, owner_map, run_map)
        monkeypatch.setattr(sys, "argv", ["deploy_failure_monitor.py"])

        rc = dfm.main()

        out = capsys.readouterr().out
        assert rc == 0  # 'nicht in Registry' ist WARN, kein Fleet-Fail
        assert "ghost-hub" in out and "nicht in Registry" in out
        assert "healthy-hub: grün" in out  # Lauf ging trotz Ghost-Repo weiter

    def test_should_fall_back_to_explicit_org_flag_in_only_mode(self, monkeypatch, capsys):
        owner_map = {}  # gar nichts in der Registry aufloesbar
        run_map = {"debug-repo": [_r("success")]}
        self._patch_common(monkeypatch, owner_map, run_map)
        monkeypatch.setattr(
            sys, "argv", ["deploy_failure_monitor.py", "--only", "debug-repo", "--org", "explicit-org"]
        )

        rc = dfm.main()

        out = capsys.readouterr().out
        assert rc == 0
        assert "Fallback auf --org explicit-org" in out
        assert "debug-repo: grün" in out
