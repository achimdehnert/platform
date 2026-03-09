"""
orchestrator_mcp/models/model_route_config.py

ModelRouteConfig — DB-backed Route-Tabelle für ADR-116

Ersetzt hardcodierte Python-Dict in model_selector.py.
Änderungen über Django Admin oder DB-Migration — kein Code-Deployment.

Platform-Standards:
- BIGSERIAL PK + public_id UUID
- Kein tenant_id: globale System-Config (wie llm_model_pricing aus ADR-115)
- deleted_at Soft-Delete
- UniqueConstraint via partial index
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from orchestrator_mcp.db import Base


class AgentRole(str, enum.Enum):
    """Agent-Rollen im AI Engineering Squad (ADR-100).

    Discord-Rollen sind NICHT hier — Discord-Commands nutzen eigene Config.
    """
    DEVELOPER = "developer"
    TESTER = "tester"
    GUARDIAN = "guardian"
    TECH_LEAD = "tech_lead"
    PLANNER = "planner"
    RE_ENGINEER = "re_engineer"
    SECURITY_AUDITOR = "security_auditor"  # UC-SE-5: Security & Dependency Audit

    @classmethod
    def _missing_(cls, value: object) -> Optional["AgentRole"]:
        import logging
        logger = logging.getLogger(__name__)
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower():
                    return member
        logger.warning("Unknown AgentRole '%s'", value)
        return None


class TaskComplexityHint(str, enum.Enum):
    """Complexity-Hinweis für Model-Routing.

    Mappt auf ADR-068 TaskComplexity via _map_from_adr068().
    """
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ARCHITECTURAL = "architectural"

    @classmethod
    def _missing_(cls, value: object) -> "TaskComplexityHint":
        import logging
        logger = logging.getLogger(__name__)
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower():
                    return member
        logger.warning(
            "Unknown TaskComplexityHint '%s', falling back to MODERATE", value
        )
        return cls.MODERATE

    @classmethod
    def from_adr068_complexity(cls, adr068_complexity: str) -> "TaskComplexityHint":
        """Mappt ADR-068 TaskComplexity auf TaskComplexityHint.

        ADR-068 TaskComplexity Werte:
            trivial, simple, moderate, complex, architectural
        Mapping ist 1:1 (gleiche Werte), aber explizit für Traceability.
        """
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
        result = mapping.get(adr068_complexity.lower())
        if result is None:
            return cls.MODERATE
        return result


class BudgetMode(str, enum.Enum):
    """Budget-Zustand des Model Selectors."""
    NORMAL = "normal"             # < 80% Budget
    COST_SENSITIVE = "cost_sensitive"  # 80-100% Budget
    EMERGENCY = "emergency"       # > 100% Budget


class ModelRouteConfig(Base):
    """DB-backed Route-Tabelle für regelbasiertes LLM-Routing (ADR-116).

    Jeder Eintrag definiert welches Modell für eine (AgentRole, Complexity)-
    Kombination im Normal-Betrieb verwendet wird.

    Im Cost-Sensitive-Mode werden die `budget_*`-Felder genutzt.
    Im Emergency-Mode übernimmt ein globaler Fallback (EMERGENCY_DEFAULT).

    Verwaltung: DB-Admin oder Django Admin (dev-hub).
    Kein Code-Deployment für Modell-Wechsel nötig.
    """

    __tablename__ = "model_route_configs"

    # --- PKs & Identifiers ---
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
        unique=True,
    )

    # --- Kein tenant_id: globale System-Konfiguration ---

    # --- Routing-Key ---
    agent_role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AgentRole enum value: developer|tester|guardian|tech_lead|...",
    )
    complexity_hint: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="TaskComplexityHint: trivial|simple|moderate|complex|architectural",
    )

    # --- Normal-Mode Modell ---
    model: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="OpenRouter Model-ID, z.B. 'anthropic/claude-3.5-sonnet'",
    )
    tier: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="budget | standard | premium | local",
    )
    provider: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Provider-Name: openai | anthropic | meta | google | ...",
    )

    # --- Cost-Sensitive-Mode Fallback (Budget 80-100%) ---
    budget_model: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Downgrade-Modell bei Budget >= 80%. NULL = kein Downgrade",
    )
    budget_tier: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Tier im Cost-Sensitive-Mode",
    )

    # --- Metadaten ---
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optionale Begründung für diese Route (für Admin-UI)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Inaktive Einträge werden nicht für Routing genutzt",
    )

    # --- Timestamps & Soft-Delete ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    __table_args__ = (
        # Partial unique index: nur eine aktive Route pro (role, complexity)
        Index(
            "uq_model_route_configs_active",
            "agent_role",
            "complexity_hint",
            unique=True,
            postgresql_where="deleted_at IS NULL AND is_active = TRUE",
        ),
        Index("model_route_configs_role_idx", "agent_role"),
    )

    def __repr__(self) -> str:
        return (
            f"<ModelRouteConfig {self.agent_role}+{self.complexity_hint}"
            f" → {self.model} [{self.tier}]>"
        )


# --- Seed-Daten (Stand 2026-03, ADR-116 Route-Tabelle) ---
# Discord-Rollen NICHT enthalten — Discord nutzt eigene ENV-Config
INITIAL_ROUTE_SEED = [
    # Developer
    {"agent_role": "developer", "complexity_hint": "simple",
     "model": "openai/gpt-4o-mini", "tier": "budget", "provider": "openai",
     "budget_model": "meta-llama/llama-3.1-8b-instruct", "budget_tier": "local"},
    {"agent_role": "developer", "complexity_hint": "moderate",
     "model": "openai/gpt-4o", "tier": "standard", "provider": "openai",
     "budget_model": "openai/gpt-4o-mini", "budget_tier": "budget"},
    {"agent_role": "developer", "complexity_hint": "complex",
     "model": "anthropic/claude-3.5-sonnet", "tier": "premium", "provider": "anthropic",
     "budget_model": "openai/gpt-4o", "budget_tier": "standard"},

    # Tester
    {"agent_role": "tester", "complexity_hint": "simple",
     "model": "openai/gpt-4o-mini", "tier": "budget", "provider": "openai",
     "budget_model": "meta-llama/llama-3.1-8b-instruct", "budget_tier": "local"},
    {"agent_role": "tester", "complexity_hint": "moderate",
     "model": "openai/gpt-4o-mini", "tier": "budget", "provider": "openai",
     "budget_model": "meta-llama/llama-3.1-8b-instruct", "budget_tier": "local"},
    {"agent_role": "tester", "complexity_hint": "complex",
     "model": "openai/gpt-4o", "tier": "standard", "provider": "openai",
     "budget_model": "openai/gpt-4o-mini", "budget_tier": "budget"},

    # Guardian
    {"agent_role": "guardian", "complexity_hint": "moderate",
     "model": "openai/gpt-4o", "tier": "standard", "provider": "openai",
     "budget_model": "openai/gpt-4o-mini", "budget_tier": "budget"},
    {"agent_role": "guardian", "complexity_hint": "complex",
     "model": "anthropic/claude-3.5-sonnet", "tier": "premium", "provider": "anthropic",
     "budget_model": "openai/gpt-4o", "budget_tier": "standard"},

    # Tech Lead / Planner (immer premium)
    {"agent_role": "tech_lead", "complexity_hint": "complex",
     "model": "anthropic/claude-3.5-sonnet", "tier": "premium", "provider": "anthropic",
     "budget_model": "openai/gpt-4o", "budget_tier": "standard"},
    {"agent_role": "tech_lead", "complexity_hint": "architectural",
     "model": "anthropic/claude-3.5-sonnet", "tier": "premium", "provider": "anthropic",
     "budget_model": "openai/gpt-4o", "budget_tier": "standard"},
    {"agent_role": "planner", "complexity_hint": "complex",
     "model": "anthropic/claude-3.5-sonnet", "tier": "premium", "provider": "anthropic",
     "budget_model": "openai/gpt-4o", "budget_tier": "standard"},

    # Re-Engineer
    {"agent_role": "re_engineer", "complexity_hint": "moderate",
     "model": "openai/gpt-4o", "tier": "standard", "provider": "openai",
     "budget_model": "openai/gpt-4o-mini", "budget_tier": "budget"},
    {"agent_role": "re_engineer", "complexity_hint": "complex",
     "model": "anthropic/claude-3.5-sonnet", "tier": "premium", "provider": "anthropic",
     "budget_model": "openai/gpt-4o", "budget_tier": "standard"},

    # Security Auditor (UC-SE-5) — kein Budget-Downgrade: budget_model == model
    # Sicherheitskritische Analyse darf nie auf günstigere Modelle degradiert werden
    {"agent_role": "security_auditor", "complexity_hint": "moderate",
     "model": "anthropic/claude-3.5-sonnet", "tier": "premium", "provider": "anthropic",
     "budget_model": "anthropic/claude-3.5-sonnet", "budget_tier": "premium"},
    {"agent_role": "security_auditor", "complexity_hint": "complex",
     "model": "anthropic/claude-3.5-sonnet", "tier": "premium", "provider": "anthropic",
     "budget_model": "anthropic/claude-3.5-sonnet", "budget_tier": "premium"},

    # Guardian trivial (UC-SE-2: Whitespace/Format-Checks im Code Review)
    {"agent_role": "guardian", "complexity_hint": "trivial",
     "model": "openai/gpt-4o-mini", "tier": "budget", "provider": "openai",
     "budget_model": "meta-llama/llama-3.1-8b-instruct", "budget_tier": "local"},
]

# Emergency-Fallback: Wird genutzt wenn Budget 100% überschritten
EMERGENCY_FALLBACK_MODEL = "openai/gpt-4o-mini"
EMERGENCY_FALLBACK_TIER = "budget"
