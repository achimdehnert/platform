"""
orchestrator_mcp/agent_team/router.py

TaskRouter mit Budget-Guard (ADR-068 + ADR-116).

ADR-068: LLM-basiertes Routing mit Confidence-Score und Feedback-Loop.
ADR-116: Budget-Aware Pre-Filter — bei Budget >= 80% übernimmt
         RuleBasedBudgetRouter (kein LLM-Call-Overhead).

Feature-Flag:
    BUDGET_GUARD_ENABLED=false  → nur ADR-068 LLM-Router (Default)
    BUDGET_GUARD_ENABLED=true   → ADR-116 Pre-Filter aktiv
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

BUDGET_GUARD_ENABLED = os.environ.get(
    "BUDGET_GUARD_ENABLED", "false"
).lower() == "true"


@dataclass(frozen=True)
class RoutingDecision:
    """Ergebnis einer Routing-Entscheidung (ADR-068 kompatibel)."""

    model: str
    tier: str
    provider: str
    agent_role: str
    complexity: str
    confidence: float
    routing_reason: str  # ADR-116: für llm_calls.routing_reason

    @property
    def openrouter_model(self) -> str:
        return self.model


@dataclass
class TaskDefinition:
    """Task-Beschreibung für den Router."""

    agent_role: str
    complexity: str
    tenant_id: int = 0
    task_id: Optional[str] = None
    description: str = ""


class TaskRouterBudgetGuardMixin:
    """Mixin für TaskRouter — fügt Budget-Guard-Routing hinzu (ADR-116).

    Verwendung:
        class TaskRouter(TaskRouterBudgetGuardMixin):
            async def _llm_route(self, task: TaskDefinition) -> RoutingDecision:
                # ADR-068 LLM-basiertes Routing
                ...
    """

    async def route_with_budget_guard(
        self,
        task: TaskDefinition,
        budget_tracker,
    ) -> RoutingDecision:
        """Budget-aware Routing: ADR-116 Pre-Filter vor ADR-068 LLM-Router.

        Entscheidungslogik:
        1. Feature-Flag OFF     → ADR-068 LLM-Router (Originalverhalten)
        2. Budget < 80%         → ADR-068 LLM-Router (volle Qualität)
        3. Budget >= 80%        → RuleBasedBudgetRouter (schnell, kein LLM-Call)
        4. Budget >= 100%       → Emergency-Fallback auf gpt-4o-mini
        """
        from orchestrator_mcp.agent_team.budget_tracker import BudgetMode

        if not BUDGET_GUARD_ENABLED:
            logger.debug(
                "BUDGET_GUARD_ENABLED=false — ADR-068 LLM-Router direkt"
            )
            return await self._llm_route(task)  # type: ignore[attr-defined]

        budget = await budget_tracker.get_status()

        if not budget.is_cost_sensitive:
            logger.debug(
                "Budget %.1f%% < 80%% — ADR-068 LLM-Router",
                budget.pct * 100,
            )
            decision = await self._llm_route(task)  # type: ignore[attr-defined]
            return decision

        # Budget >= 80% oder Emergency → RuleBasedBudgetRouter
        from orchestrator_mcp.agent_team.rule_based_router import (
            RuleBasedBudgetRouter,
        )

        logger.info(
            "Budget %.1f%% >= 80%% — RuleBasedBudgetRouter übernimmt",
            budget.pct * 100,
        )
        router = RuleBasedBudgetRouter(budget_tracker)
        selection = await router.select(
            agent_role=task.agent_role,
            complexity=task.complexity,
            tenant_id=task.tenant_id,
            task_id=task.task_id,
        )

        return RoutingDecision(
            model=selection.model,
            tier=selection.tier,
            provider=selection.provider,
            agent_role=selection.agent_role,
            complexity=selection.complexity_hint,
            confidence=1.0,  # Regelbasiert = deterministisch
            routing_reason=selection.routing_reason,
        )


class TaskRouter(TaskRouterBudgetGuardMixin):
    """Vollständiger TaskRouter (ADR-068 + ADR-116).

    _llm_route() ist der ADR-068 LLM-basierte Routing-Pfad.
    route_with_budget_guard() ist der ADR-116 Pre-Filter.

    Für den Budget-Guard-Pfad:
        budget_tracker = BudgetTracker(redis_client=redis)
        router = TaskRouter()
        decision = await router.route_with_budget_guard(task, budget_tracker)
    """

    async def _llm_route(self, task: TaskDefinition) -> RoutingDecision:
        """ADR-068 LLM-basiertes Routing.

        Stub-Implementierung: gibt ein sinnvolles Default zurück.
        Vollständige ADR-068-Implementierung wird hier eingefügt sobald
        der LLM-Router aus ADR-068 in orchestrator_mcp integriert ist.
        """
        # Default-Routing: role + complexity → Modell aus bekannter Tabelle
        _defaults = {
            ("developer", "complex"): ("anthropic/claude-3.5-sonnet", "premium", "anthropic"),
            ("developer", "moderate"): ("openai/gpt-4o", "standard", "openai"),
            ("developer", "simple"): ("openai/gpt-4o-mini", "budget", "openai"),
            ("tester", "complex"): ("openai/gpt-4o", "standard", "openai"),
            ("tester", "moderate"): ("openai/gpt-4o-mini", "budget", "openai"),
            ("guardian", "complex"): ("anthropic/claude-3.5-sonnet", "premium", "anthropic"),
            ("guardian", "moderate"): ("openai/gpt-4o", "standard", "openai"),
            ("tech_lead", "complex"): ("anthropic/claude-3.5-sonnet", "premium", "anthropic"),
            ("security_auditor", "complex"): ("anthropic/claude-3.5-sonnet", "premium", "anthropic"),
            ("security_auditor", "moderate"): ("anthropic/claude-3.5-sonnet", "premium", "anthropic"),
        }

        key = (task.agent_role, task.complexity)
        model, tier, provider = _defaults.get(
            key,
            ("openai/gpt-4o-mini", "budget", "openai"),
        )

        return RoutingDecision(
            model=model,
            tier=tier,
            provider=provider,
            agent_role=task.agent_role,
            complexity=task.complexity,
            confidence=0.9,
            routing_reason=f"adr068_default:{task.agent_role}+{task.complexity}",
        )
