"""
orchestrator_mcp/audit_store.py

AuditStore Service per ADR-108 §3.1 Phase 4.

Central write point for all agent task outcomes:
  - QALog: quality scores, rollback levels, completion status
  - CostLog: token usage, budget, overrun
  - DeploymentLog: deployment outcomes (see models/deployment_log.py)
  - ReviewLog: PR review outcomes (see models/review_log.py)

All writes are idempotent (upsert by task_id).
Django ORM used — no raw SQL, no cursor.execute.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchestrator_mcp.agent_team.evaluator import QualityScore
    from orchestrator_mcp.agent_team.completion import CompletionResult

logger = logging.getLogger(__name__)


class AuditStore:
    """
    Service layer for writing all agent audit data.

    Usage:
        store = AuditStore()
        store.log_quality_score(score)
        store.log_completion(result)
        store.log_cost(task_id, tokens_used, tokens_budget, model_tier)
    """

    def log_quality_score(self, score: "QualityScore") -> None:
        """
        Persists a QualityScore as QALog entry.
        Upserts by (task_id) — safe to call multiple times.
        """
        try:
            from orchestrator_mcp.models.qa_log import QALog

            QALog.objects.update_or_create(
                task_id=score.task_id,
                defaults={
                    "task_type": score.task_type,
                    "agent_role": score.agent_role,
                    "model_tier": score.model_tier,
                    "completion_score": score.completion_score,
                    "guardian_passed": score.guardian_passed,
                    "coverage_delta": score.coverage_delta,
                    "adr_compliance": score.adr_compliance,
                    "iteration_count": score.iteration_count,
                    "composite_score": score.composite_score,
                    "rollback_level": score.rollback_level.value,
                    "passed": score.passed,
                    "tokens_used": score.tokens_used,
                    "tokens_budget": score.tokens_budget,
                    "details": score.details,
                    "evaluated_at": datetime.now(timezone.utc),
                },
            )
            logger.info("AuditStore: QALog written for task %s", score.task_id)
        except Exception as exc:
            logger.error("AuditStore.log_quality_score failed: %s", exc)

    def log_completion(self, result: "CompletionResult") -> None:
        """
        Persists open criteria to QALog details field.
        Requires QALog entry to exist (call after log_quality_score).
        """
        try:
            from orchestrator_mcp.models.qa_log import QALog

            QALog.objects.filter(task_id=result.task_id).update(
                details__update={
                    "open_criteria": result.open_criteria,
                    "blocking_open": result.blocking_open,
                    "completion_complete": result.blocking_complete,
                }
            )
        except Exception as exc:
            logger.error("AuditStore.log_completion failed: %s", exc)

    def log_cost(
        self,
        task_id: str,
        task_type: str,
        agent_role: str,
        model_tier: str,
        repository: str,
        tokens_used: int,
        tokens_budget: int,
        tenant_id: int = 1,
    ) -> None:
        """
        Persists token usage as CostLog entry.
        Flags overrun if tokens_used > tokens_budget * 1.2.
        """
        try:
            from orchestrator_mcp.models.cost_log import CostLog

            overrun = tokens_used > int(tokens_budget * 1.2) if tokens_budget > 0 else False
            CostLog.objects.update_or_create(
                task_id=task_id,
                defaults={
                    "task_type": task_type,
                    "agent_role": agent_role,
                    "model_tier": model_tier,
                    "repository": repository,
                    "tenant_id": tenant_id,
                    "tokens_used": tokens_used,
                    "tokens_budget": tokens_budget,
                    "overrun": overrun,
                    "logged_at": datetime.now(timezone.utc),
                },
            )
            if overrun:
                logger.warning(
                    "AuditStore: Cost overrun for task %s: %d > %d (budget)",
                    task_id, tokens_used, tokens_budget,
                )
        except Exception as exc:
            logger.error("AuditStore.log_cost failed: %s", exc)

    def get_cost_estimate(
        self, task_id: str, model_tier: str, estimated_tokens: int = 0
    ) -> dict[str, object]:
        """
        Returns cost estimate for a task before execution.
        Used by orchestrator tools to show budget before commit.
        """
        from orchestrator_mcp.agent_team.evaluator import QualityEvaluator

        evaluator = QualityEvaluator()
        complexity = "moderate"  # default
        budget = evaluator.TOKEN_BUDGETS.get(complexity, 80_000)
        hard_limit = evaluator.TOKEN_HARD_LIMITS.get(complexity, 150_000)

        return {
            "task_id": task_id,
            "model_tier": model_tier,
            "estimated_tokens": estimated_tokens,
            "budget_tokens": budget,
            "hard_limit_tokens": hard_limit,
            "within_budget": estimated_tokens <= budget,
            "within_hard_limit": estimated_tokens <= hard_limit,
        }
