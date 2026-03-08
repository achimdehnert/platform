"""
orchestrator_mcp/audit_store.py

AuditStore service per ADR-108.
Logs QualityScore and CompletionResult to QALog and CostLog Django models.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AuditStore:
    """
    Service for persisting QA and cost audit data.

    Lazy-imports Django models to avoid import errors when Django is not
    configured (e.g. in unit tests without DJANGO_SETTINGS_MODULE).
    """

    def log_quality_score(
        self,
        task_id: str,
        score,  # QualityScore instance
        task_type: str = "",
        repo: str = "",
        branch: str = "",
        agent_role: str = "",
    ) -> Optional[object]:
        """
        Persist a QualityScore to QALog.
        Returns the created QALog instance or None on error.
        """
        try:
            from orchestrator_mcp.models.qa_log import QALog

            qa_log = QALog.objects.create(
                task_id=task_id,
                task_type=task_type,
                repo=repo,
                branch=branch,
                agent_role=agent_role,
                composite_score=score.composite,
                completion_score=score.completion_score,
                guardian_score=score.guardian_score,
                adr_compliance_score=score.adr_compliance_score,
                iteration_score=score.iteration_score,
                token_score=score.token_score,
                rollback_level=score.rollback_level.value,
                iterations_used=score.iterations_used,
                tokens_used=score.tokens_used,
                token_budget=score.token_budget,
                complexity=score.complexity,
            )
            logger.info(
                "QALog created: task=%s composite=%.2f rollback=%s",
                task_id, score.composite, score.rollback_level.value,
            )
            return qa_log
        except Exception as exc:
            logger.error("AuditStore.log_quality_score failed: %s", exc)
            return None

    def log_completion(
        self,
        task_id: str,
        result,  # CompletionResult instance
    ) -> None:
        """
        Update QALog with completion details.
        """
        try:
            from orchestrator_mcp.models.qa_log import QALog

            QALog.objects.filter(task_id=task_id).update(
                completion_score=result.score,
                is_complete=result.is_complete,
                blocking_open=result.blocking_open,
            )
        except Exception as exc:
            logger.error("AuditStore.log_completion failed: %s", exc)

    def log_token_usage(
        self,
        task_id: str,
        tokens_used: int,
        token_budget: int,
        model: str = "",
        complexity: str = "moderate",
        agent_role: str = "",
    ) -> Optional[object]:
        """
        Persist token usage to CostLog.
        Returns the created CostLog instance or None on error.
        """
        try:
            from orchestrator_mcp.models.cost_log import CostLog

            over_budget = tokens_used > token_budget
            utilization = tokens_used / token_budget if token_budget else 0.0

            cost_log = CostLog.objects.create(
                task_id=task_id,
                model=model,
                complexity=complexity,
                agent_role=agent_role,
                tokens_used=tokens_used,
                token_budget=token_budget,
                over_budget=over_budget,
                utilization=round(utilization, 4),
            )
            if over_budget:
                logger.warning(
                    "Token budget exceeded: task=%s used=%d budget=%d (%.0f%%)",
                    task_id, tokens_used, token_budget, utilization * 100,
                )
            return cost_log
        except Exception as exc:
            logger.error("AuditStore.log_token_usage failed: %s", exc)
            return None

    def get_cost_estimate(
        self,
        task_id: str,
        estimated_tokens: int,
        complexity: str = "moderate",
    ) -> dict:
        """
        Pre-execution budget check.
        Returns dict with budget, estimated_tokens, over_budget, utilization.
        """
        from orchestrator_mcp.agent_team.evaluator import TOKEN_BUDGETS

        budget = TOKEN_BUDGETS.get(complexity, TOKEN_BUDGETS["moderate"])
        over = estimated_tokens > budget
        utilization = estimated_tokens / budget if budget else 0.0

        return {
            "task_id": task_id,
            "complexity": complexity,
            "token_budget": budget,
            "estimated_tokens": estimated_tokens,
            "over_budget": over,
            "utilization": round(utilization, 4),
        }
