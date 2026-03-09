"""
orchestrator_mcp/agent_team/router_budget_guard_patch.py

ADR-068 router.py — Minimale Erweiterung für ADR-116 Budget-Guard

HINWEIS: Diese Datei zeigt die ERGÄNZUNG zu bestehendem router.py.
Sie wird als Patch/Diff angewendet, nicht als Ersatz.

BLOCKER B-01 behoben:
    ADR-116 ist KEINE parallele Implementierung.
    RuleBasedBudgetRouter ist ein Pre-Filter vor dem bestehenden LLM-Router.

Integration:
    - Feature-Flag BUDGET_GUARD_ENABLED (ENV, default=false für safe rollout)
    - Bei Budget < 80%: normales ADR-068 LLM-Routing (unverändert)
    - Bei Budget ≥ 80%: RuleBasedBudgetRouter (kein LLM-Call)
    - Beide Pfade schreiben routing_reason in ModelSelection

Rollback:
    BUDGET_GUARD_ENABLED=false → Originalverhalten ADR-068, sofort
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchestrator_mcp.agent_team.rule_based_router import ModelSelection
    from orchestrator_mcp.agent_team.budget_tracker import BudgetTracker
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Feature-Flag für sicheres Rollout
BUDGET_GUARD_ENABLED = os.environ.get("BUDGET_GUARD_ENABLED", "false").lower() == "true"


# ================================================================
# PATCH-ERGÄNZUNG für bestehende TaskRouter Klasse in router.py
# Methode hinzufügen, bestehende route() Methode NICHT ändern
# ================================================================

class TaskRouterBudgetGuardMixin:
    """Mixin für bestehenden TaskRouter — fügt Budget-Guard-Routing hinzu.

    Verwendung in router.py:
        class TaskRouter(TaskRouterBudgetGuardMixin):
            ...
            async def route(self, task: TaskDefinition) -> RoutingDecision:
                # Bestehende Implementierung unverändert
                ...
    """

    async def route_with_budget_guard(
        self,
        task: "TaskDefinition",
        session: "AsyncSession",
        budget_tracker: "BudgetTracker",
    ) -> "RoutingDecision":
        """Budget-aware Routing: ADR-116 Pre-Filter vor ADR-068 LLM-Router.

        Entscheidungslogik:
        1. Budget ≥ 80%  → RuleBasedBudgetRouter (schnell, kein LLM-Call)
        2. Budget < 80%  → Bestehender TaskRouter._llm_route() (volle Qualität)
        3. Feature-Flag OFF → Direkter LLM-Router (Originalverhalten)

        Args:
            task: TaskDefinition mit agent_role, complexity, tenant_id, task_id
            session: Async DB-Session für Budget-Query + Route-Lookup
            budget_tracker: BudgetTracker-Instanz (Singleton aus FastAPI lifespan)
        """
        if not BUDGET_GUARD_ENABLED:
            # Originalverhalten — kein Budget-Check
            return await self._llm_route(task)  # type: ignore[attr-defined]

        # Budget-Check (aus DB via BudgetTracker, Redis-gecacht)
        budget = await budget_tracker.get_status(session)

        if budget.is_cost_sensitive:
            # Fast-path: Regelbasiertes Routing ohne LLM-Call
            from orchestrator_mcp.agent_team.rule_based_router import RuleBasedBudgetRouter

            # RuleBasedBudgetRouter als Singleton aus FastAPI lifespan holen
            # (hier als Beispiel direkt instantiiert — in Produktion via DI)
            router = RuleBasedBudgetRouter(budget_tracker)
            selection = await router.select(
                session=session,
                agent_role=task.agent_role,
                complexity=task.complexity,
                tenant_id=task.tenant_id,
                task_id=getattr(task, "task_id", None),
            )

            logger.info(
                "Budget-Guard aktiviert (%.1f%% von $%.2f) — "
                "regelbasiertes Routing: %s",
                budget.pct * 100,
                budget.limit_usd,
                selection.model,
            )

            # RoutingDecision aus ADR-068 Format erstellen
            return _selection_to_routing_decision(selection, task)

        # Normal-path: ADR-068 LLM-Router (unverändert)
        return await self._llm_route(task)  # type: ignore[attr-defined]


def _selection_to_routing_decision(
    selection: "ModelSelection",
    task: "TaskDefinition",
) -> "RoutingDecision":
    """Konvertiert ModelSelection (ADR-116) → RoutingDecision (ADR-068).

    Stellt Kompatibilität zwischen beiden Typen sicher.
    routing_reason wird in der RoutingDecision mitgeführt und
    über usage_logger.py in llm_calls.routing_reason geschrieben.
    """
    # Import hier um zirkuläre Imports zu vermeiden
    from orchestrator_mcp.agent_team.router import RoutingDecision  # type: ignore

    return RoutingDecision(
        model=selection.model,
        tier=selection.tier,
        provider=selection.provider,
        confidence=1.0,          # Regelbasiert = deterministisch = Confidence 1.0
        routing_reason=selection.routing_reason,
        budget_mode=selection.budget_mode.value,
        # Felder aus ADR-068 RoutingDecision beibehalten
        task_complexity=task.complexity,
        agent_role=task.agent_role,
    )
