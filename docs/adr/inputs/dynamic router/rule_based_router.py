"""
orchestrator_mcp/agent_team/rule_based_router.py

RuleBasedBudgetRouter — Kernkomponente ADR-116

Positionierung im ADR-Stack:
- Erweiterung von ADR-068 TaskRouter (nicht Ersatz)
- Wird aktiviert wenn Budget ≥ 80% ODER als direkter Fallback
- Route-Tabelle aus DB (ModelRouteConfig) — kein Python-Dict
- Logging in llm_calls.routing_reason (ADR-115-Schema-Erweiterung)

Alle BLOCKER behoben:
- B-01: Kein paralleles System — Integration in ADR-068 router.py
- B-02: Budget aus DB (llm_calls SUM) via BudgetTracker
- B-03: Route-Tabelle aus DB (ModelRouteConfig)

Alle KRITISCH behoben:
- K-01: routing_reason in llm_calls geschrieben
- K-02: Keine Discord-Rollen hier
- K-03: Vollständige Enum-Validierung mit _missing_
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator_mcp.agent_team.budget_tracker import BudgetStatus, BudgetTracker
from orchestrator_mcp.models.model_route_config import (
    AgentRole,
    BudgetMode,
    EMERGENCY_FALLBACK_MODEL,
    EMERGENCY_FALLBACK_TIER,
    ModelRouteConfig,
    TaskComplexityHint,
)

logger = logging.getLogger(__name__)

# Cache-TTL für Route-Tabelle (5 Minuten)
_ROUTE_CACHE_TTL = 300


@dataclass(frozen=True, slots=True)
class ModelSelection:
    """Ergebnis einer Routing-Entscheidung."""

    model: str
    tier: str
    provider: Optional[str]
    agent_role: str
    complexity_hint: str
    budget_mode: BudgetMode
    routing_reason: str  # Für llm_calls.routing_reason

    @property
    def openrouter_model(self) -> str:
        """Direkt verwendbar als `model`-Parameter in /v1/chat."""
        return self.model

    def __str__(self) -> str:
        return (
            f"ModelSelection(model={self.model!r} tier={self.tier} "
            f"mode={self.budget_mode.value} reason={self.routing_reason!r})"
        )


class RuleBasedBudgetRouter:
    """Regelbasiertes Routing mit Budget-Awareness.

    Wird als Fallback-Layer unter ADR-068 TaskRouter positioniert:
    - Bei Budget < 80%: ADR-068 LLM-Router hat Vorrang
    - Bei Budget ≥ 80%: Dieser Router übernimmt (kein LLM-Call-Overhead)
    - Bei Budget ≥ 100%: Emergency-Fallback auf gpt-4o-mini

    Alle Routing-Entscheidungen werden in routing_reason dokumentiert
    und über usage_logger.py in llm_calls geschrieben.
    """

    def __init__(self, budget_tracker: BudgetTracker) -> None:
        self._budget_tracker = budget_tracker
        # In-Memory Cache für Route-Tabelle
        self._route_cache: dict[tuple[str, str], ModelRouteConfig] = {}
        self._cache_loaded_at: float = 0.0

    async def select(
        self,
        session: AsyncSession,
        agent_role: str | AgentRole,
        complexity: str | TaskComplexityHint,
        *,
        tenant_id: int,
        task_id: Optional[str] = None,
        force_budget_mode: bool = False,
    ) -> ModelSelection:
        """Wählt das optimale Modell für einen Agent-Call.

        Args:
            session: Async DB-Session
            agent_role: AgentRole oder String (wird normalisiert)
            complexity: TaskComplexityHint oder String (wird normalisiert, Fallback MODERATE)
            tenant_id: Pflichtfeld für llm_calls-Logging
            task_id: Optional, für Korrelation in llm_calls
            force_budget_mode: Debug-Flag, erzwingt Cost-Sensitive-Mode

        Returns:
            ModelSelection mit model, tier, routing_reason
        """
        # --- Enum-Normalisierung (K-03 Fix) ---
        role = _normalize_role(agent_role)
        complexity_hint = _normalize_complexity(complexity)

        # --- Budget-Check (B-02 Fix: aus DB, nicht in-memory) ---
        budget = await self._budget_tracker.get_status(session)
        effective_budget = budget

        if force_budget_mode:
            from dataclasses import replace
            effective_budget = replace(budget, mode=BudgetMode.COST_SENSITIVE)

        # --- Emergency: Alles auf gpt-4o-mini ---
        if effective_budget.mode == BudgetMode.EMERGENCY:
            reason = (
                f"emergency:budget={effective_budget.pct*100:.1f}%"
                f">${effective_budget.limit_usd:.2f}"
                f"|role={role.value if role else agent_role}"
                f"|complexity={complexity_hint.value}"
            )
            logger.warning(
                "Budget EMERGENCY (%.1f%% of $%.2f) — alle Calls auf %s",
                effective_budget.pct * 100,
                effective_budget.limit_usd,
                EMERGENCY_FALLBACK_MODEL,
            )
            return ModelSelection(
                model=EMERGENCY_FALLBACK_MODEL,
                tier=EMERGENCY_FALLBACK_TIER,
                provider="openai",
                agent_role=role.value if role else str(agent_role),
                complexity_hint=complexity_hint.value,
                budget_mode=effective_budget.mode,
                routing_reason=reason,
            )

        # --- Route aus DB laden ---
        route = await self._get_route(session, role, complexity_hint)

        if route is None:
            # Fallback: unbekannte Combo → einfachere Complexity → budget_default
            logger.warning(
                "Keine Route für role=%s complexity=%s — verwende MODERATE-Fallback",
                role,
                complexity_hint,
            )
            route = await self._get_route(session, role, TaskComplexityHint.MODERATE)

        if route is None:
            # Letzter Fallback: Emergency-Modell (aber kein EMERGENCY-Mode)
            reason = (
                f"fallback:no_route"
                f"|role={role.value if role else agent_role}"
                f"|complexity={complexity_hint.value}"
            )
            return ModelSelection(
                model=EMERGENCY_FALLBACK_MODEL,
                tier=EMERGENCY_FALLBACK_TIER,
                provider="openai",
                agent_role=role.value if role else str(agent_role),
                complexity_hint=complexity_hint.value,
                budget_mode=effective_budget.mode,
                routing_reason=reason,
            )

        # --- Modell-Auswahl nach Budget-Mode ---
        if effective_budget.mode == BudgetMode.COST_SENSITIVE and route.budget_model:
            selected_model = route.budget_model
            selected_tier = route.budget_tier or "budget"
            reason = (
                f"budget_downgrade:{effective_budget.pct*100:.1f}%"
                f"|normal={route.model}"
                f"|downgrade={selected_model}"
                f"|role={route.agent_role}|complexity={route.complexity_hint}"
            )
        else:
            selected_model = route.model
            selected_tier = route.tier
            reason = (
                f"rule:{route.agent_role}+{route.complexity_hint}"
                f"→{selected_tier}"
                f"|budget={effective_budget.pct*100:.1f}%"
            )

        logger.debug("ModelSelection: %s", reason)

        return ModelSelection(
            model=selected_model,
            tier=selected_tier,
            provider=route.provider,
            agent_role=route.agent_role,
            complexity_hint=route.complexity_hint,
            budget_mode=effective_budget.mode,
            routing_reason=reason,
        )

    async def _get_route(
        self,
        session: AsyncSession,
        role: Optional[AgentRole],
        complexity: TaskComplexityHint,
    ) -> Optional[ModelRouteConfig]:
        """Lädt Route aus Cache oder DB."""
        if role is None:
            return None

        cache_key = (role.value, complexity.value)

        # Cache-Check (5 Minuten TTL)
        now = time.monotonic()
        if self._cache_loaded_at and (now - self._cache_loaded_at) < _ROUTE_CACHE_TTL:
            return self._route_cache.get(cache_key)

        # Cache-Refresh: alle aktiven Routes laden
        await self._refresh_cache(session)
        return self._route_cache.get(cache_key)

    async def _refresh_cache(self, session: AsyncSession) -> None:
        """Lädt alle aktiven Routes aus DB."""
        stmt = select(ModelRouteConfig).where(
            ModelRouteConfig.deleted_at.is_(None),
            ModelRouteConfig.is_active.is_(True),
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

        self._route_cache = {
            (row.agent_role, row.complexity_hint): row
            for row in rows
        }
        self._cache_loaded_at = time.monotonic()
        logger.debug("Route cache refreshed: %d entries", len(self._route_cache))

    def invalidate_cache(self) -> None:
        """Route-Cache leeren (nach DB-Änderung)."""
        self._route_cache.clear()
        self._cache_loaded_at = 0.0


def _normalize_role(value: str | AgentRole) -> Optional[AgentRole]:
    """AgentRole normalisieren. Gibt None zurück wenn unbekannt."""
    if isinstance(value, AgentRole):
        return value
    result = AgentRole(value)  # Nutzt _missing_ für Warnung + None
    return result


def _normalize_complexity(value: str | TaskComplexityHint) -> TaskComplexityHint:
    """TaskComplexityHint normalisieren. Fallback auf MODERATE."""
    if isinstance(value, TaskComplexityHint):
        return value
    return TaskComplexityHint(value)  # Nutzt _missing_ für Fallback
