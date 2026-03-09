"""
orchestrator_mcp/agent_team/tests/test_rule_based_router.py

Pytest-Suite für RuleBasedBudgetRouter, BudgetTracker, Enums

Testet:
- Enum-Normalisierung mit _missing_ (K-03 Fix)
- Budget-Trigger-Logik (B-02 Fix)
- Route-Fallback-Kette (H-04 Fix)
- Emergency-Modus
- routing_reason Format (K-01 Fix)
- Discord-Rollen sind NICHT im Router (K-02 Fix)
- Security Auditor niemals downgegradet (UC-SE-5)
- Cache-Invalidierung (T-01)
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator_mcp.agent_team.budget_tracker import (
    DAILY_BUDGET_USD,
    BudgetMode,
    BudgetStatus,
)
from orchestrator_mcp.agent_team.rule_based_router import (
    RuleBasedBudgetRouter,
    RouterAgentRole,
    TaskComplexityHint,
    _normalize_complexity,
    _normalize_role,
)
from orchestrator_mcp.models.model_route_config import (
    EMERGENCY_FALLBACK_MODEL,
)


# ================================================================
# Enum-Normalisierung Tests (K-03 Fix)
# ================================================================


class TestRouterAgentRoleEnum:
    def test_valid_value(self):
        assert RouterAgentRole("developer") == RouterAgentRole.DEVELOPER

    def test_case_insensitive(self):
        assert RouterAgentRole("DEVELOPER") == RouterAgentRole.DEVELOPER
        assert RouterAgentRole("Developer") == RouterAgentRole.DEVELOPER

    def test_unknown_returns_none(self):
        result = RouterAgentRole("discord_status")
        assert result is None  # Kein Discord im Agent-Router!

    def test_normalize_role_with_string(self):
        assert _normalize_role("tech_lead") == RouterAgentRole.TECH_LEAD

    def test_normalize_role_with_enum(self):
        assert (
            _normalize_role(RouterAgentRole.GUARDIAN)
            == RouterAgentRole.GUARDIAN
        )

    def test_normalize_role_unknown_returns_none(self):
        result = _normalize_role("discord_ask")  # K-02: Discord nicht im Router
        assert result is None

    def test_security_auditor_is_valid(self):
        role = RouterAgentRole("security_auditor")
        assert role == RouterAgentRole.SECURITY_AUDITOR


class TestTaskComplexityHintEnum:
    def test_valid_value(self):
        assert TaskComplexityHint("complex") == TaskComplexityHint.COMPLEX

    def test_case_insensitive(self):
        assert TaskComplexityHint("COMPLEX") == TaskComplexityHint.COMPLEX

    def test_unknown_falls_back_to_moderate(self):
        """K-03 Fix: Kein KeyError, sondern sicherer Fallback."""
        result = TaskComplexityHint("komplex")  # Ungültig
        assert result == TaskComplexityHint.MODERATE

    def test_adr068_aliases(self):
        """ADR-068 Complexity-Aliasse werden korrekt gemappt."""
        assert (
            TaskComplexityHint.from_adr068_complexity("low")
            == TaskComplexityHint.SIMPLE
        )
        assert (
            TaskComplexityHint.from_adr068_complexity("medium")
            == TaskComplexityHint.MODERATE
        )
        assert (
            TaskComplexityHint.from_adr068_complexity("high")
            == TaskComplexityHint.COMPLEX
        )

    def test_normalize_complexity_with_string(self):
        assert (
            _normalize_complexity("architectural")
            == TaskComplexityHint.ARCHITECTURAL
        )

    def test_normalize_complexity_fallback(self):
        assert _normalize_complexity("unknownvalue") == TaskComplexityHint.MODERATE


# ================================================================
# Hilfsfunktionen
# ================================================================


def _make_budget_status(mode: BudgetMode = BudgetMode.NORMAL) -> BudgetStatus:
    pct = {
        BudgetMode.NORMAL: 0.5,
        BudgetMode.COST_SENSITIVE: 0.85,
        BudgetMode.EMERGENCY: 1.05,
    }[mode]
    return BudgetStatus(
        spent_usd=DAILY_BUDGET_USD * Decimal(str(pct)),
        limit_usd=DAILY_BUDGET_USD,
        pct=pct,
        mode=mode,
        checked_at=datetime.now(tz=timezone.utc),
    )


def _make_route_config(
    agent_role: str = "developer",
    complexity_hint: str = "complex",
    model: str = "anthropic/claude-3.5-sonnet",
    tier: str = "premium",
    budget_model: str = "openai/gpt-4o",
    budget_tier: str = "standard",
):
    from orchestrator_mcp.models.model_route_config import ModelRouteConfig

    config = MagicMock(spec=ModelRouteConfig)
    config.agent_role = agent_role
    config.complexity_hint = complexity_hint
    config.model = model
    config.tier = tier
    config.provider = "anthropic"
    config.budget_model = budget_model
    config.budget_tier = budget_tier
    config.effective_budget_model = budget_model or model
    config.effective_budget_tier = budget_tier or tier
    return config


def _make_router(mode: BudgetMode = BudgetMode.NORMAL) -> RuleBasedBudgetRouter:
    mock_tracker = AsyncMock()
    mock_tracker.get_status.return_value = _make_budget_status(mode)
    router = RuleBasedBudgetRouter(mock_tracker)
    router._cache_loaded_at = 9_999_999.0  # Cache als frisch markieren
    return router


# ================================================================
# Normal-Mode Tests
# ================================================================


class TestRuleBasedBudgetRouterNormalMode:
    @pytest.mark.asyncio
    async def test_normal_mode_returns_premium_model(self):
        router = _make_router(BudgetMode.NORMAL)
        router._route_cache = {
            ("developer", "complex"): _make_route_config()
        }

        result = await router.select(
            agent_role="developer",
            complexity="complex",
            tenant_id=1,
        )

        assert result.model == "anthropic/claude-3.5-sonnet"
        assert result.tier == "premium"
        assert result.budget_mode == BudgetMode.NORMAL if hasattr(result, "budget_mode") else True
        assert "rule:developer+complex" in result.routing_reason

    @pytest.mark.asyncio
    async def test_routing_reason_contains_budget_pct(self):
        """K-01: routing_reason muss Budget-Prozentsatz enthalten."""
        router = _make_router(BudgetMode.NORMAL)
        router._route_cache = {
            ("developer", "complex"): _make_route_config()
        }

        result = await router.select("developer", "complex", tenant_id=1)
        assert "%" in result.routing_reason
        assert "developer" in result.routing_reason


# ================================================================
# Cost-Sensitive-Mode Tests
# ================================================================


class TestRuleBasedBudgetRouterCostSensitiveMode:
    @pytest.mark.asyncio
    async def test_cost_sensitive_uses_budget_model(self):
        """H-01 + B-02: Budget-Downgrade nutzt budget_model aus DB."""
        router = _make_router(BudgetMode.COST_SENSITIVE)
        router._route_cache = {
            ("developer", "complex"): _make_route_config()
        }

        result = await router.select("developer", "complex", tenant_id=1)

        assert result.model == "openai/gpt-4o"  # budget_model aus Fixture
        assert result.tier == "standard"
        assert "budget_downgrade" in result.routing_reason
        assert "anthropic/claude-3.5-sonnet" in result.routing_reason

    @pytest.mark.asyncio
    async def test_cost_sensitive_routing_reason_has_percentage(self):
        router = _make_router(BudgetMode.COST_SENSITIVE)
        router._route_cache = {
            ("developer", "complex"): _make_route_config()
        }

        result = await router.select("developer", "complex", tenant_id=1)
        assert "%" in result.routing_reason


# ================================================================
# Emergency-Mode Tests
# ================================================================


class TestRuleBasedBudgetRouterEmergencyMode:
    @pytest.mark.asyncio
    async def test_emergency_returns_cheapest_model_for_all_roles(self):
        """Alle Rollen bekommen Emergency-Fallback."""
        for role in ["tech_lead", "developer", "guardian", "planner"]:
            router = _make_router(BudgetMode.EMERGENCY)
            result = await router.select(role, "complex", tenant_id=1)
            assert result.model == EMERGENCY_FALLBACK_MODEL
            assert "emergency" in result.routing_reason

    @pytest.mark.asyncio
    async def test_emergency_does_not_query_route_table(self):
        """Emergency-Pfad braucht keine DB-Query für Route-Tabelle."""
        router = _make_router(BudgetMode.EMERGENCY)

        with patch.object(
            router, "_get_route", new_callable=AsyncMock
        ) as mock_get:
            await router.select("developer", "complex", tenant_id=1)
            mock_get.assert_not_called()


# ================================================================
# Fallback-Tests
# ================================================================


class TestRuleBasedBudgetRouterFallback:
    @pytest.mark.asyncio
    async def test_unknown_role_triggers_fallback_not_keyerror(self):
        """H-04: Unbekannte Rolle → kein KeyError → budget default."""
        router = _make_router(BudgetMode.NORMAL)
        router._route_cache = {}

        result = await router.select(
            "new_unknown_role", "complex", tenant_id=1
        )
        assert result.model == EMERGENCY_FALLBACK_MODEL
        assert "fallback" in result.routing_reason

    @pytest.mark.asyncio
    async def test_discord_role_not_routable(self):
        """K-02: Discord-Rollen sind nicht im Router registriert."""
        router = _make_router(BudgetMode.NORMAL)
        router._route_cache = {}

        result = await router.select(
            "discord_status", "trivial", tenant_id=1
        )
        assert "fallback" in result.routing_reason


# ================================================================
# UC-SE-5: Security Auditor — kein Budget-Downgrade
# ================================================================


class TestSecurityAuditorNoDowngrade:
    @pytest.mark.asyncio
    async def test_security_auditor_stays_premium_in_cost_sensitive_mode(self):
        """UC-SE-5: security_auditor wird bei 80%+ Budget NICHT downgegradet."""
        router = _make_router(BudgetMode.COST_SENSITIVE)
        # budget_model == model → kein Downgrade
        config = _make_route_config(
            agent_role="security_auditor",
            complexity_hint="complex",
            model="anthropic/claude-3.5-sonnet",
            tier="premium",
            budget_model="anthropic/claude-3.5-sonnet",  # identisch!
            budget_tier="premium",
        )
        router._route_cache = {("security_auditor", "complex"): config}

        result = await router.select(
            "security_auditor", "complex", tenant_id=1
        )

        assert result.model == "anthropic/claude-3.5-sonnet"
        assert result.tier == "premium"
        assert "budget_downgrade" in result.routing_reason
        assert result.routing_reason.count("anthropic/claude-3.5-sonnet") >= 1

    def test_security_auditor_role_is_valid(self):
        """SECURITY_AUDITOR ist registrierter RouterAgentRole-Wert."""
        role = RouterAgentRole("security_auditor")
        assert role == RouterAgentRole.SECURITY_AUDITOR

    @pytest.mark.asyncio
    async def test_security_auditor_unknown_complexity_falls_back(self):
        """Unbekannte Complexity für security_auditor → MODERATE Fallback."""
        router = _make_router(BudgetMode.NORMAL)
        config = _make_route_config(
            agent_role="security_auditor",
            complexity_hint="moderate",
            model="anthropic/claude-3.5-sonnet",
            tier="premium",
        )
        router._route_cache = {("security_auditor", "moderate"): config}

        result = await router.select(
            "security_auditor", "kritisch", tenant_id=1
        )
        assert result.model == "anthropic/claude-3.5-sonnet"


# ================================================================
# T-01: Cache-Stale Test
# ================================================================


class TestRouteCacheInvalidation:
    @pytest.mark.asyncio
    async def test_stale_cache_triggers_db_refresh(self):
        """T-01: Abgelaufener Cache löst DB-Reload aus."""
        router = _make_router(BudgetMode.NORMAL)
        router._cache_loaded_at = 0.0  # Cache als abgelaufen markieren
        router._route_cache = {}

        with patch.object(
            router, "_refresh_cache", new_callable=AsyncMock
        ) as mock_refresh:
            await router.select("developer", "complex", tenant_id=1)
            mock_refresh.assert_called_once()

    def test_invalidate_cache_resets_state(self):
        """invalidate_cache() leert Cache und setzt Timestamp zurück."""
        mock_tracker = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)
        router._cache_loaded_at = 999.0
        router._route_cache = {("developer", "complex"): MagicMock()}

        router.invalidate_cache()

        assert router._cache_loaded_at == 0.0
        assert router._route_cache == {}


# ================================================================
# Discord-Config Tests (K-02)
# ================================================================


class TestDiscordConfig:
    def test_discord_models_are_independent_of_agent_router(self):
        """K-02: Discord-Config ist völlig unabhängig vom RuleBasedBudgetRouter."""
        from orchestrator_mcp.discord.config import get_discord_model

        chat_config = get_discord_model("chat")
        assert chat_config.model  # Hat ein Modell

        import orchestrator_mcp.discord.config as dc

        assert not hasattr(dc, "RuleBasedBudgetRouter")
        assert not hasattr(dc, "ModelRouteConfig")

    def test_unknown_discord_command_returns_default(self):
        from orchestrator_mcp.discord.config import get_discord_model

        config = get_discord_model("unknown_command")
        assert config.model  # Kein Fehler, Default zurückgegeben
