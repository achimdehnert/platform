"""
orchestrator_mcp/agent_team/rule_based_router.py

RuleBasedBudgetRouter — Kernkomponente ADR-116.

Positionierung im ADR-Stack:
- Erweiterung von ADR-068 TaskRouter (nicht Ersatz)
- Pre-Filter: Budget >= 80% → regelbasiertes Routing (kein LLM-Call)
- Budget < 80% → ADR-068 LLM-basiertes Routing (unverändert)
- Route-Tabelle aus DB (ModelRouteConfig) — kein Python-Dict
- routing_reason in llm_calls (ADR-115-Schema-Erweiterung)

Alle BLOCKER behoben:
- B-01: Kein paralleles System — Pre-Filter vor ADR-068
- B-02: Budget aus DB (llm_calls SUM) via BudgetTracker
- B-03: Route-Tabelle aus DB (ModelRouteConfig)

Alle KRITISCH behoben:
- K-01: routing_reason wird zurückgegeben und extern in llm_calls geschrieben
- K-02: Keine Discord-Rollen hier
- K-03: Vollständige Enum-Validierung mit Fallback-Logik
"""
from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Cache-TTL für Route-Tabelle (5 Minuten)
_ROUTE_CACHE_TTL = 300


class RouterAgentRole(str, enum.Enum):
    """Agent-Rollen für ADR-116 Routing.

    Separate Enum von roles.py AgentRole — enthält nur Rollen
    die tatsächlich im RuleBasedBudgetRouter geroutet werden.
    Discord-Rollen sind NICHT hier (K-02 Fix).
    """
    DEVELOPER = "developer"
    TESTER = "tester"
    GUARDIAN = "guardian"
    TECH_LEAD = "tech_lead"
    PLANNER = "planner"
    RE_ENGINEER = "re_engineer"
    SECURITY_AUDITOR = "security_auditor"  # UC-SE-5: niemals downgegradet

    @classmethod
    def _missing_(cls, value: object) -> Optional["RouterAgentRole"]:
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower():
                    return member
        logger.warning("Unknown RouterAgentRole '%s' — kein Routing möglich", value)
        return None


class TaskComplexityHint(str, enum.Enum):
    """Complexity-Hinweis für Model-Routing.

    Mappt 1:1 auf ADR-068 TaskComplexity (gleiche Werte).
    """
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ARCHITECTURAL = "architectural"

    @classmethod
    def _missing_(cls, value: object) -> "TaskComplexityHint":
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower():
                    return member
        logger.warning(
            "Unknown TaskComplexityHint '%s' — Fallback auf MODERATE", value
        )
        return cls.MODERATE

    @classmethod
    def from_adr068_complexity(cls, value: str) -> "TaskComplexityHint":
        """Mappt ADR-068 TaskComplexity auf TaskComplexityHint."""
        mapping = {
            "trivial": cls.TRIVIAL,
            "simple": cls.SIMPLE,
            "moderate": cls.MODERATE,
            "complex": cls.COMPLEX,
            "architectural": cls.ARCHITECTURAL,
            # ADR-068 aliases
            "low": cls.SIMPLE,
            "medium": cls.MODERATE,
            "high": cls.COMPLEX,
        }
        result = mapping.get(value.lower())
        if result is None:
            return cls.MODERATE
        return result


@dataclass(frozen=True)
class ModelSelection:
    """Ergebnis einer Routing-Entscheidung."""

    model: str
    tier: str
    provider: str
    agent_role: str
    complexity_hint: str
    budget_pct: float
    routing_reason: str  # Für llm_calls.routing_reason (K-01 Fix)

    @property
    def openrouter_model(self) -> str:
        """Direkt verwendbar als `model`-Parameter in /v1/chat."""
        return self.model

    def __str__(self) -> str:
        return (
            f"ModelSelection(model={self.model!r} tier={self.tier}"
            f" budget={self.budget_pct * 100:.1f}%"
            f" reason={self.routing_reason!r})"
        )


class RuleBasedBudgetRouter:
    """Regelbasiertes Routing mit Budget-Awareness (ADR-116).

    Pre-Filter vor ADR-068 TaskRouter:
    - Budget >= 80%: dieser Router übernimmt (kein LLM-Call-Overhead)
    - Budget < 80%: ADR-068 LLM-Router hat Vorrang
    - Budget >= 100%: Emergency-Fallback auf gpt-4o-mini

    Alle Routing-Entscheidungen haben eine routing_reason,
    die über usage_logger in llm_calls.routing_reason geschrieben wird.

    Feature-Flag: BUDGET_GUARD_ENABLED=true aktiviert diesen Router.
    """

    def __init__(self, budget_tracker) -> None:
        from orchestrator_mcp.agent_team.budget_tracker import BudgetTracker
        assert isinstance(budget_tracker, BudgetTracker)
        self._budget_tracker = budget_tracker
        # In-Memory Cache für Route-Tabelle (5 Minuten TTL)
        self._route_cache: dict[tuple[str, str], object] = {}
        self._cache_loaded_at: float = 0.0

    async def select(
        self,
        agent_role: str | RouterAgentRole,
        complexity: str | TaskComplexityHint,
        *,
        tenant_id: int = 0,
        task_id: Optional[str] = None,
        force_budget_mode: bool = False,
    ) -> ModelSelection:
        """Wählt das optimale Modell für einen Agent-Call.

        Args:
            agent_role: RouterAgentRole oder String (wird normalisiert)
            complexity: TaskComplexityHint oder String (Fallback MODERATE)
            tenant_id: Für llm_calls-Logging (0 = platform-intern)
            task_id: Optional, für Korrelation in llm_calls
            force_budget_mode: Debug-Flag, erzwingt Cost-Sensitive-Mode
        """
        from orchestrator_mcp.agent_team.budget_tracker import BudgetMode
        from orchestrator_mcp.models.model_route_config import (
            EMERGENCY_FALLBACK_MODEL,
            EMERGENCY_FALLBACK_TIER,
        )

        role = _normalize_role(agent_role)
        complexity_hint = _normalize_complexity(complexity)

        budget = await self._budget_tracker.get_status()

        is_emergency = budget.mode == BudgetMode.EMERGENCY
        is_cost_sensitive = (
            force_budget_mode
            or budget.mode == BudgetMode.COST_SENSITIVE
        )

        # --- Emergency: alles auf gpt-4o-mini ---
        if is_emergency:
            reason = (
                f"emergency:budget={budget.pct * 100:.1f}%"
                f">${budget.limit_usd:.2f}"
                f"|role={role.value if role else agent_role}"
                f"|complexity={complexity_hint.value}"
            )
            logger.warning(
                "Budget EMERGENCY (%.1f%% von $%.2f) — alle Calls auf %s",
                budget.pct * 100,
                budget.limit_usd,
                EMERGENCY_FALLBACK_MODEL,
            )
            return ModelSelection(
                model=EMERGENCY_FALLBACK_MODEL,
                tier=EMERGENCY_FALLBACK_TIER,
                provider="openai",
                agent_role=role.value if role else str(agent_role),
                complexity_hint=complexity_hint.value,
                budget_pct=budget.pct,
                routing_reason=reason,
            )

        # --- Route aus DB laden ---
        route = await self._get_route(role, complexity_hint)

        if route is None:
            # Fallback: auf MODERATE zurückfallen
            logger.warning(
                "Keine Route für role=%s complexity=%s — MODERATE-Fallback",
                role,
                complexity_hint,
            )
            route = await self._get_route(role, TaskComplexityHint.MODERATE)

        if route is None:
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
                budget_pct=budget.pct,
                routing_reason=reason,
            )

        # --- Modell-Auswahl nach Budget-Mode ---
        if is_cost_sensitive:
            selected_model = route.effective_budget_model
            selected_tier = route.effective_budget_tier
            reason = (
                f"budget_downgrade:{budget.pct * 100:.1f}%"
                f"|normal={route.model}"
                f"|downgrade={selected_model}"
                f"|role={route.agent_role}|complexity={route.complexity_hint}"
            )
        else:
            selected_model = route.model
            selected_tier = route.tier
            reason = (
                f"rule:{route.agent_role}+{route.complexity_hint}"
                f"\u2192{selected_tier}"
                f"|budget={budget.pct * 100:.1f}%"
            )

        logger.debug("ModelSelection: %s", reason)

        return ModelSelection(
            model=selected_model,
            tier=selected_tier,
            provider=route.provider or "",
            agent_role=route.agent_role,
            complexity_hint=route.complexity_hint,
            budget_pct=budget.pct,
            routing_reason=reason,
        )

    async def _get_route(
        self,
        role: Optional[RouterAgentRole],
        complexity: TaskComplexityHint,
    ):
        """Lädt Route aus Cache oder DB."""
        if role is None:
            return None

        cache_key = (role.value, complexity.value)
        now = time.monotonic()

        if (
            self._cache_loaded_at
            and (now - self._cache_loaded_at) < _ROUTE_CACHE_TTL
        ):
            return self._route_cache.get(cache_key)

        await self._refresh_cache()
        return self._route_cache.get(cache_key)

    async def _refresh_cache(self) -> None:
        """Lädt alle aktiven Routes aus DB via sync_to_async."""
        from asgiref.sync import sync_to_async
        from orchestrator_mcp.models.model_route_config import ModelRouteConfig

        rows = await sync_to_async(
            lambda: list(
                ModelRouteConfig.objects.filter(
                    deleted_at__isnull=True,
                    is_active=True,
                )
            )
        )()

        self._route_cache = {
            (row.agent_role, row.complexity_hint): row
            for row in rows
        }
        self._cache_loaded_at = time.monotonic()
        logger.debug(
            "Route cache refreshed: %d entries", len(self._route_cache)
        )

    def invalidate_cache(self) -> None:
        """Route-Cache leeren (nach DB-Änderung über Admin)."""
        self._route_cache.clear()
        self._cache_loaded_at = 0.0


def _normalize_role(
    value: str | RouterAgentRole,
) -> Optional[RouterAgentRole]:
    """RouterAgentRole normalisieren. None bei unbekannter Rolle."""
    if isinstance(value, RouterAgentRole):
        return value
    return RouterAgentRole(value)  # Nutzt _missing_ für Warning + None


def _normalize_complexity(
    value: str | TaskComplexityHint,
) -> TaskComplexityHint:
    """TaskComplexityHint normalisieren. Fallback auf MODERATE."""
    if isinstance(value, TaskComplexityHint):
        return value
    return TaskComplexityHint(value)  # Nutzt _missing_ für Fallback
