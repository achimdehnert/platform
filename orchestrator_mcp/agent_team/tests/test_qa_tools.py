"""
Tests for QA cycle MCP tools: get_cost_estimate, evaluate_task, verify_task.
ADR-108 Phase 5.
"""
from __future__ import annotations

import pytest

from orchestrator_mcp.tools import evaluate_task, get_cost_estimate, verify_task


class TestGetCostEstimate:
    def test_agent_cost_structure(self):
        result = get_cost_estimate("t1", "opus", estimated_tokens=10_000)
        assert result["agent"]["model"] == "opus"
        assert result["agent"]["cost_usd"] == pytest.approx(0.15, rel=0.01)
        assert result["agent"]["tokens"] == 10_000

    def test_cascade_comparison_present(self):
        result = get_cost_estimate("t2", "swe", complexity="moderate")
        assert "cascade" in result
        assert "comparison" in result
        assert result["cascade"]["cost_usd"] > 0

    def test_agent_cheaper_than_cascade(self):
        result = get_cost_estimate("t3", "gpt_low", complexity="moderate")
        assert result["comparison"]["cheaper"] == "agent"
        assert result["comparison"]["savings_pct"] > 0

    def test_opus_same_as_cascade(self):
        result = get_cost_estimate("t4", "opus", estimated_tokens=80_000, complexity="moderate")
        assert result["comparison"]["savings_pct"] == pytest.approx(0.0, abs=5.0)

    def test_cascade_tokens_override(self):
        result = get_cost_estimate("t5", "swe", cascade_tokens=200_000, complexity="moderate")
        assert result["cascade"]["tokens"] == 200_000
        assert result["cascade"]["source"] == "actual"

    def test_cascade_baseline_fallback(self):
        result = get_cost_estimate("t6", "swe", complexity="complex")
        assert result["cascade"]["source"] == "baseline_estimate"
        assert result["cascade"]["tokens"] == 150_000

    def test_complexity_affects_budget(self):
        simple = get_cost_estimate("t7a", "swe", complexity="simple")
        arch = get_cost_estimate("t7b", "swe", complexity="architectural")
        assert simple["agent"]["token_budget"] < arch["agent"]["token_budget"]

    def test_unknown_model_falls_back_to_swe(self):
        result = get_cost_estimate("t8", "unknown_model", estimated_tokens=1_000)
        assert result["agent"]["cost_usd"] > 0

    def test_adr_reference(self):
        result = get_cost_estimate("t9", "swe")
        assert result["adr_reference"] == "ADR-108"


class TestEvaluateTask:
    def test_high_quality_task_no_rollback(self):
        result = evaluate_task(
            task_id="e1",
            completion_score=1.0,
            guardian_passed=True,
            adr_violations=0,
            iterations_used=3,
            tokens_used=40_000,
            complexity="moderate",
        )
        assert result["rollback_level"] == "none"
        assert result["composite_score"] >= 0.85
        assert "ship it" in result["recommendation"]

    def test_low_completion_triggers_rollback(self):
        result = evaluate_task(
            task_id="e2",
            completion_score=0.3,
            guardian_passed=False,
            adr_violations=2,
            iterations_used=8,
            tokens_used=90_000,
        )
        assert result["rollback_level"] in ("soft", "hard", "escalate")

    def test_adr_violations_lower_score(self):
        clean = evaluate_task(
            task_id="e3a",
            completion_score=1.0,
            guardian_passed=True,
            adr_violations=0,
            iterations_used=2,
            tokens_used=20_000,
        )
        violated = evaluate_task(
            task_id="e3b",
            completion_score=1.0,
            guardian_passed=True,
            adr_violations=3,
            iterations_used=2,
            tokens_used=20_000,
        )
        assert clean["composite_score"] > violated["composite_score"]

    def test_escalate_on_critical_failure(self):
        result = evaluate_task(
            task_id="e4",
            completion_score=0.0,
            guardian_passed=False,
            adr_violations=5,
            iterations_used=10,
            tokens_used=250_000,
        )
        assert result["rollback_level"] == "escalate"

    def test_sub_scores_present(self):
        result = evaluate_task(
            task_id="e5",
            completion_score=0.8,
            guardian_passed=True,
            adr_violations=0,
            iterations_used=4,
            tokens_used=50_000,
        )
        assert set(result["sub_scores"].keys()) == {
            "completion", "guardian", "adr_compliance", "iteration", "token",
        }

    def test_metrics_present(self):
        result = evaluate_task(
            task_id="e6",
            completion_score=0.9,
            guardian_passed=True,
            adr_violations=0,
            iterations_used=2,
            tokens_used=30_000,
            complexity="simple",
        )
        assert result["metrics"]["complexity"] == "simple"
        assert result["metrics"]["tokens_used"] == 30_000


class TestVerifyTask:
    def test_complete_when_all_criteria_met(self):
        result = verify_task(
            task_id="v1",
            criteria=[
                {"description": "Feature works", "met": True, "blocking": True},
            ],
            tests_passed=True,
            lint_passed=True,
            adr_violations=0,
        )
        assert result["is_complete"] is True
        assert result["blocking_open"] == []
        assert "task_complete" in result["next_action"]

    def test_incomplete_when_tests_fail(self):
        result = verify_task(
            task_id="v2",
            criteria=[{"description": "Feature works", "met": True, "blocking": True}],
            tests_passed=False,
            lint_passed=True,
        )
        assert result["is_complete"] is False
        assert "fix_tests" in result["next_action"]

    def test_incomplete_when_lint_fails(self):
        result = verify_task(
            task_id="v3",
            criteria=[{"description": "Feature works", "met": True, "blocking": True}],
            tests_passed=True,
            lint_passed=False,
        )
        assert result["is_complete"] is False
        assert "fix_lint" in result["next_action"]

    def test_incomplete_when_adr_violations(self):
        result = verify_task(
            task_id="v4",
            criteria=[{"description": "Feature works", "met": True, "blocking": True}],
            tests_passed=True,
            lint_passed=True,
            adr_violations=2,
        )
        assert result["is_complete"] is False
        assert "fix_adr" in result["next_action"]

    def test_incomplete_blocking_criterion_open(self):
        result = verify_task(
            task_id="v5",
            criteria=[
                {"description": "Must deploy", "met": False, "blocking": True},
            ],
        )
        assert result["is_complete"] is False
        assert "Must deploy" in result["blocking_open"]

    def test_non_blocking_criterion_does_not_block(self):
        result = verify_task(
            task_id="v6",
            criteria=[
                {"description": "Nice to have", "met": False, "blocking": False},
                {"description": "Required", "met": True, "blocking": True},
            ],
            tests_passed=True,
            lint_passed=True,
        )
        assert result["is_complete"] is True

    def test_criteria_counts(self):
        result = verify_task(
            task_id="v7",
            criteria=[
                {"description": "A", "met": True, "blocking": True},
                {"description": "B", "met": False, "blocking": False},
            ],
            tests_passed=True,
            lint_passed=True,
        )
        assert result["criteria_met"] >= 2
        assert result["criteria_total"] >= 3  # 2 custom + tests + lint

    def test_adr_reference(self):
        result = verify_task(task_id="v8", criteria=[])
        assert result["adr_reference"] == "ADR-108"
