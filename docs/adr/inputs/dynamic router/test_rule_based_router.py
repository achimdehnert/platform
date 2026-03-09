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
"""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator_mcp.models.model_route_config import (
    AgentRole,
    BudgetMode,
    EMERGENCY_FALLBACK_MODEL,
    TaskComplexityHint,
)
from orchestrator_mcp.agent_team.budget_tracker import (
    BudgetStatus,
    BudgetTracker,
    DAILY_BUDGET_USD,
)
from orchestrator_mcp.agent_team.rule_based_router import (
    RuleBasedBudgetRouter,
    _normalize_role,
    _normalize_complexity,
)


# ================================================================
# Enum-Normalisierung Tests (K-03 Fix)
# ================================================================

class TestAgentRoleEnum:
    def test_valid_value(self):
        assert AgentRole("developer") == AgentRole.DEVELOPER

    def test_case_insensitive(self):
        assert AgentRole("DEVELOPER") == AgentRole.DEVELOPER
        assert AgentRole("Developer") == AgentRole.DEVELOPER

    def test_unknown_returns_none(self):
        result = AgentRole("discord_status")  # Kein Discord im Agent-Router!
        assert result is None

    def test_normalize_role_with_string(self):
        assert _normalize_role("tech_lead") == AgentRole.TECH_LEAD

    def test_normalize_role_with_enum(self):
        assert _normalize_role(AgentRole.GUARDIAN) == AgentRole.GUARDIAN

    def test_normalize_role_unknown_returns_none(self):
        result = _normalize_role("discord_ask")  # K-02: Discord nicht im Router
        assert result is None


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
        assert TaskComplexityHint.from_adr068_complexity("low") == TaskComplexityHint.SIMPLE
        assert TaskComplexityHint.from_adr068_complexity("medium") == TaskComplexityHint.MODERATE
        assert TaskComplexityHint.from_adr068_complexity("high") == TaskComplexityHint.COMPLEX

    def test_normalize_complexity_with_string(self):
        assert _normalize_complexity("architectural") == TaskComplexityHint.ARCHITECTURAL

    def test_normalize_complexity_fallback(self):
        assert _normalize_complexity("unknownvalue") == TaskComplexityHint.MODERATE


# ================================================================
# BudgetTracker Tests (B-02 Fix)
# ================================================================

class TestBudgetTracker:
    def _make_status(self, pct: float) -> BudgetStatus:
        spent = DAILY_BUDGET_USD * Decimal(str(pct))
        return BudgetStatus(
            spent_usd=spent,
            limit_usd=DAILY_BUDGET_USD,
            pct=pct,
            mode=BudgetMode.NORMAL if pct < 0.80
                 else (BudgetMode.EMERGENCY if pct >= 1.0 else BudgetMode.COST_SENSITIVE),
            checked_at=datetime.now(tz=timezone.utc),
        )

    def test_normal_mode_below_threshold(self):
        status = self._make_status(0.50)
        assert status.mode == BudgetMode.NORMAL
        assert not status.is_cost_sensitive

    def test_cost_sensitive_at_threshold(self):
        status = self._make_status(0.80)
        assert status.mode == BudgetMode.COST_SENSITIVE
        assert status.is_cost_sensitive

    def test_emergency_at_100pct(self):
        status = self._make_status(1.00)
        assert status.mode == BudgetMode.EMERGENCY
        assert status.is_cost_sensitive

    def test_remaining_usd_calculation(self):
        status = self._make_status(0.60)
        expected = DAILY_BUDGET_USD * Decimal("0.40")
        assert abs(status.remaining_usd - expected) < Decimal("0.0001")

    def test_remaining_usd_zero_at_emergency(self):
        status = self._make_status(1.10)
        assert status.remaining_usd == Decimal("0")

    @pytest.mark.asyncio
    async def test_db_query_returns_correct_mode(self):
        """BudgetTracker liest aus DB, nicht aus in-memory counter (B-02)."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(spent_today=Decimal("8.50"))
        mock_session.execute.return_value = mock_result

        tracker = BudgetTracker(redis_client=None)  # Kein Redis im Test
        status = await tracker._query_db(mock_session)

        assert status.mode == BudgetMode.COST_SENSITIVE
        assert status.spent_usd == Decimal("8.50")

    @pytest.mark.asyncio
    async def test_redis_fallback_on_error(self):
        """Bei Redis-Ausfall: direkter DB-Fallback ohne Exception."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(spent_today=Decimal("2.00"))
        mock_session.execute.return_value = mock_result

        tracker = BudgetTracker(redis_client=mock_redis)
        # Kein Fehler — Fallback auf DB
        status = await tracker.get_status(mock_session)
        assert status.mode == BudgetMode.NORMAL


# ================================================================
# RuleBasedBudgetRouter Tests
# ================================================================

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
    return config


def _make_budget_status(mode: BudgetMode = BudgetMode.NORMAL) -> BudgetStatus:
    pct = 0.5 if mode == BudgetMode.NORMAL else (0.85 if mode == BudgetMode.COST_SENSITIVE else 1.05)
    return BudgetStatus(
        spent_usd=DAILY_BUDGET_USD * Decimal(str(pct)),
        limit_usd=DAILY_BUDGET_USD,
        pct=pct,
        mode=mode,
        checked_at=datetime.now(tz=timezone.utc),
    )


class TestRuleBasedBudgetRouterNormalMode:
    @pytest.mark.asyncio
    async def test_normal_mode_returns_premium_model(self):
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(BudgetMode.NORMAL)

        mock_session = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)
        router._route_cache = {
            ("developer", "complex"): _make_route_config()
        }
        router._cache_loaded_at = 9_999_999.0  # Frischer Cache

        result = await router.select(
            session=mock_session,
            agent_role="developer",
            complexity="complex",
            tenant_id=1,
        )

        assert result.model == "anthropic/claude-3.5-sonnet"
        assert result.tier == "premium"
        assert result.budget_mode == BudgetMode.NORMAL
        assert "rule:developer+complex→premium" in result.routing_reason

    @pytest.mark.asyncio
    async def test_normal_mode_routing_reason_format(self):
        """K-01: routing_reason muss lesbar und strukturiert sein."""
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(BudgetMode.NORMAL)

        mock_session = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)
        router._route_cache = {("tester", "simple"): _make_route_config("tester", "simple", "openai/gpt-4o-mini", "budget")}
        router._cache_loaded_at = 9_999_999.0

        result = await router.select(
            mock_session, "tester", "simple", tenant_id=42, task_id="task-001"
        )

        # routing_reason muss role, complexity, tier und budget-pct enthalten
        assert "tester" in result.routing_reason
        assert "simple" in result.routing_reason
        assert "budget" in result.routing_reason


class TestRuleBasedBudgetRouterCostSensitiveMode:
    @pytest.mark.asyncio
    async def test_cost_sensitive_uses_budget_model(self):
        """H-01 + B-02: Budget-Downgrade nutzt budget_model aus DB."""
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(BudgetMode.COST_SENSITIVE)

        mock_session = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)
        router._route_cache = {("developer", "complex"): _make_route_config()}
        router._cache_loaded_at = 9_999_999.0

        result = await router.select(mock_session, "developer", "complex", tenant_id=1)

        # Downgrade auf budget_model
        assert result.model == "openai/gpt-4o"  # budget_model aus Fixture
        assert result.tier == "standard"         # budget_tier aus Fixture
        assert result.budget_mode == BudgetMode.COST_SENSITIVE
        assert "budget_downgrade" in result.routing_reason
        assert "anthropic/claude-3.5-sonnet" in result.routing_reason  # Original erwähnt

    @pytest.mark.asyncio
    async def test_cost_sensitive_routing_reason_has_percentage(self):
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(BudgetMode.COST_SENSITIVE)

        mock_session = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)
        router._route_cache = {("developer", "complex"): _make_route_config()}
        router._cache_loaded_at = 9_999_999.0

        result = await router.select(mock_session, "developer", "complex", tenant_id=1)
        # Budget-Prozentsatz muss in routing_reason stehen
        assert "%" in result.routing_reason


class TestRuleBasedBudgetRouterEmergencyMode:
    @pytest.mark.asyncio
    async def test_emergency_returns_cheapest_model_for_all_roles(self):
        """Alle Rollen bekommen Emergency-Fallback."""
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(BudgetMode.EMERGENCY)

        mock_session = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)

        for role in ["tech_lead", "developer", "guardian", "planner"]:
            result = await router.select(mock_session, role, "complex", tenant_id=1)
            assert result.model == EMERGENCY_FALLBACK_MODEL
            assert "emergency" in result.routing_reason

    @pytest.mark.asyncio
    async def test_emergency_does_not_query_db_route_table(self):
        """Emergency-Pfad braucht keine DB-Query für Route-Tabelle."""
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(BudgetMode.EMERGENCY)

        mock_session = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)

        with patch.object(router, "_get_route", new_callable=AsyncMock) as mock_get:
            await router.select(mock_session, "developer", "complex", tenant_id=1)
            mock_get.assert_not_called()  # Kein Route-Lookup im Emergency-Modus


class TestRuleBasedBudgetRouterFallback:
    @pytest.mark.asyncio
    async def test_unknown_role_triggers_fallback_not_keyerror(self):
        """H-04: Unbekannte Rolle → kein KeyError → budget default."""
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(BudgetMode.NORMAL)

        mock_session = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)
        router._route_cache = {}  # Keine Routes
        router._cache_loaded_at = 9_999_999.0

        # Kein pytest.raises — kein Exception erwartet
        result = await router.select(
            mock_session, "new_unknown_role", "complex", tenant_id=1
        )
        assert result.model == EMERGENCY_FALLBACK_MODEL
        assert "fallback:no_route" in result.routing_reason

    @pytest.mark.asyncio
    async def test_discord_role_not_routable(self):
        """K-02: Discord-Rollen sind nicht im Router registriert."""
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(BudgetMode.NORMAL)

        mock_session = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)
        router._route_cache = {}
        router._cache_loaded_at = 9_999_999.0

        # discord_status ist kein AgentRole → Fallback, kein Fehler
        result = await router.select(
            mock_session, "discord_status", "trivial", tenant_id=1
        )
        # Landet im Fallback — nie in einer echten Route
        assert "fallback" in result.routing_reason


# ================================================================
# Discord-Config Tests (K-02)
# ================================================================

class TestDiscordConfig:
    def test_discord_models_are_independent_of_agent_router(self):
        """K-02: Discord-Config ist völlig unabhängig vom RuleBasedBudgetRouter."""
        from orchestrator_mcp.discord.config import get_discord_model

        chat_config = get_discord_model("chat")
        assert chat_config.model  # Hat ein Modell
        # Discord-Config darf keine ADR-116 Router-Imports haben
        import orchestrator_mcp.discord.config as dc
        assert not hasattr(dc, "RuleBasedBudgetRouter")
        assert not hasattr(dc, "ModelRouteConfig")

    def test_unknown_discord_command_returns_default(self):
        from orchestrator_mcp.discord.config import get_discord_model
        config = get_discord_model("unknown_command")
        assert config.model  # Kein Fehler, Default zurückgegeben


# ================================================================
# UC-SE-5: Security Auditor — kein Budget-Downgrade
# ================================================================

class TestSecurityAuditorNoDowngrade:
    @pytest.mark.asyncio
    async def test_security_auditor_stays_premium_in_cost_sensitive_mode(self):
        """UC-SE-5: security_auditor wird bei 80%+ Budget NICHT downgegradet."""
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(
            BudgetMode.COST_SENSITIVE
        )

        mock_session = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)
        # budget_model == model → kein Downgrade
        router._route_cache = {
            ("security_auditor", "complex"): _make_route_config(
                agent_role="security_auditor",
                complexity_hint="complex",
                model="anthropic/claude-3.5-sonnet",
                tier="premium",
                budget_model="anthropic/claude-3.5-sonnet",  # identisch!
                budget_tier="premium",
            )
        }
        router._cache_loaded_at = 9_999_999.0

        result = await router.select(
            mock_session,
            "security_auditor",
            "complex",
            tenant_id=1,
        )

        # Trotz COST_SENSITIVE-Mode: Premium-Modell bleibt
        assert result.model == "anthropic/claude-3.5-sonnet"
        assert result.tier == "premium"
        assert result.budget_mode == BudgetMode.COST_SENSITIVE
        # routing_reason zeigt budget_downgrade — aber Modell bleibt gleich
        assert "budget_downgrade" in result.routing_reason
        # Original und downgrade sind identisch
        assert result.routing_reason.count("anthropic/claude-3.5-sonnet") >= 1

    @pytest.mark.asyncio
    async def test_security_auditor_role_is_valid_agent_role(self):
        """SECURITY_AUDITOR ist registrierter AgentRole-Wert."""
        role = AgentRole("security_auditor")
        assert role == AgentRole.SECURITY_AUDITOR

    @pytest.mark.asyncio
    async def test_security_auditor_unknown_complexity_falls_back(
        self,
    ):
        """Unbekannte Complexity für security_auditor → MODERATE Fallback."""
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(
            BudgetMode.NORMAL
        )

        mock_session = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)
        router._route_cache = {
            ("security_auditor", "moderate"): _make_route_config(
                agent_role="security_auditor",
                complexity_hint="moderate",
                model="anthropic/claude-3.5-sonnet",
                tier="premium",
            )
        }
        router._cache_loaded_at = 9_999_999.0

        # "kritisch" ist keine gültige Complexity → fällt auf MODERATE
        result = await router.select(
            mock_session,
            "security_auditor",
            "kritisch",
            tenant_id=1,
        )
        assert result.model == "anthropic/claude-3.5-sonnet"


# ================================================================
# T-01: Cache-Stale Test
# ================================================================

class TestRouteCacheInvalidation:
    @pytest.mark.asyncio
    async def test_stale_cache_triggers_db_refresh(self):
        """T-01: Abgelaufener Cache löst DB-Reload aus."""
        mock_tracker = AsyncMock()
        mock_tracker.get_status.return_value = _make_budget_status(
            BudgetMode.NORMAL
        )

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        router = RuleBasedBudgetRouter(mock_tracker)
        # Cache als abgelaufen markieren (0 = nie gefüllt)
        router._cache_loaded_at = 0.0
        router._route_cache = {}

        result = await router.select(
            mock_session, "developer", "complex", tenant_id=1
        )

        # DB wurde abgefragt (cache refresh)
        mock_session.execute.assert_called_once()
        # Kein Match → Fallback
        assert "fallback" in result.routing_reason

    def test_invalidate_cache_resets_timestamp(self):
        """invalidate_cache() setzt _cache_loaded_at auf 0."""
        mock_tracker = AsyncMock()
        router = RuleBasedBudgetRouter(mock_tracker)
        router._cache_loaded_at = 999.0
        router._route_cache = {("developer", "complex"): MagicMock()}

        router.invalidate_cache()

        assert router._cache_loaded_at == 0.0
        assert router._route_cache == {}
