"""
orchestrator_mcp/models/model_route_config.py

ModelRouteConfig — DB-backed Route-Tabelle für ADR-116.

Ersetzt hardcodierte Python-Dict. Änderungen über Django Admin
oder Migration — kein Code-Deployment nötig.

Platform-Standards:
- BigAutoField PK + public_id UUID
- Kein tenant_id: globale System-Config (wie llm_model_pricing)
- deleted_at Soft-Delete
- Partial Unique via Index (agent_role, complexity_hint)
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class ModelRouteConfig(models.Model):
    """DB-backed Route-Tabelle für regelbasiertes LLM-Routing (ADR-116).

    Jeder Eintrag definiert welches Modell für eine
    (agent_role, complexity_hint)-Kombination im Normal-Betrieb
    verwendet wird. Im Cost-Sensitive-Mode werden budget_*-Felder
    genutzt. Im Emergency-Mode übernimmt ein globaler Fallback.

    Verwaltung: Django Admin. Kein Code-Deployment für Modell-Wechsel.
    """

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Public ID"),
    )

    # --- Kein tenant_id: globale System-Konfiguration ---

    # --- Routing-Key ---
    agent_role = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_("Agent Role"),
        help_text=_(
            "AgentRole value: developer|tester|guardian|tech_lead|"
            "planner|re_engineer|security_auditor"
        ),
    )
    complexity_hint = models.CharField(
        max_length=20,
        verbose_name=_("Complexity Hint"),
        help_text=_(
            "TaskComplexityHint: trivial|simple|moderate|complex|architectural"
        ),
    )

    # --- Normal-Mode Modell ---
    model = models.CharField(
        max_length=200,
        verbose_name=_("Model"),
        help_text=_("OpenRouter Model-ID, z.B. 'anthropic/claude-3.5-sonnet'"),
    )
    tier = models.CharField(
        max_length=20,
        verbose_name=_("Tier"),
        help_text=_("budget | standard | premium | local"),
    )
    provider = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Provider"),
        help_text=_("openai | anthropic | meta | google | ..."),
    )

    # --- Cost-Sensitive-Mode Fallback (Budget 80-100%) ---
    budget_model = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Budget Model"),
        help_text=_(
            "Downgrade-Modell bei Budget >= 80%. "
            "Leer = kein Downgrade (z.B. security_auditor)."
        ),
    )
    budget_tier = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Budget Tier"),
        help_text=_("Tier im Cost-Sensitive-Mode"),
    )

    # --- Metadaten ---
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Optionale Begründung für diese Route"),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
        help_text=_("Inaktive Einträge werden nicht für Routing genutzt"),
    )

    # --- Timestamps & Soft-Delete ---
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created At")
    )
    deleted_at = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name=_("Deleted At")
    )

    class Meta:
        app_label = "orchestrator_mcp"
        verbose_name = _("Model Route Config")
        verbose_name_plural = _("Model Route Configs")
        ordering = ["agent_role", "complexity_hint"]
        indexes = [
            models.Index(
                fields=["agent_role", "complexity_hint"],
                name="modelroute_role_complexity_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["agent_role", "complexity_hint"],
                condition=models.Q(deleted_at__isnull=True, is_active=True),
                name="uq_model_route_active",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"ModelRouteConfig({self.agent_role}+{self.complexity_hint}"
            f" → {self.model} [{self.tier}])"
        )

    @property
    def effective_budget_model(self) -> str:
        """Budget-Modell für Cost-Sensitive-Mode.

        Falls budget_model leer (z.B. security_auditor):
        bleibt beim normalen Modell — kein Downgrade.
        """
        return self.budget_model or self.model

    @property
    def effective_budget_tier(self) -> str:
        """Budget-Tier für Cost-Sensitive-Mode."""
        return self.budget_tier or self.tier


# --- Seed-Daten (werden in Migration eingespielt) ---
# Discord-Rollen NICHT enthalten — Discord nutzt eigene ENV-Config.
INITIAL_ROUTE_SEED: list[dict] = [
    # Developer
    {
        "agent_role": "developer", "complexity_hint": "simple",
        "model": "openai/gpt-4o-mini", "tier": "budget",
        "provider": "openai",
        "budget_model": "meta-llama/llama-3.1-8b-instruct",
        "budget_tier": "local",
        "description": "Einfache Dev-Tasks",
    },
    {
        "agent_role": "developer", "complexity_hint": "moderate",
        "model": "openai/gpt-4o", "tier": "standard",
        "provider": "openai",
        "budget_model": "openai/gpt-4o-mini", "budget_tier": "budget",
        "description": "Standard Dev-Tasks",
    },
    {
        "agent_role": "developer", "complexity_hint": "complex",
        "model": "anthropic/claude-3.5-sonnet", "tier": "premium",
        "provider": "anthropic",
        "budget_model": "openai/gpt-4o", "budget_tier": "standard",
        "description": "Komplexe Dev-Tasks",
    },
    # Tester
    {
        "agent_role": "tester", "complexity_hint": "simple",
        "model": "openai/gpt-4o-mini", "tier": "budget",
        "provider": "openai",
        "budget_model": "meta-llama/llama-3.1-8b-instruct",
        "budget_tier": "local",
        "description": "Einfache Test-Generierung",
    },
    {
        "agent_role": "tester", "complexity_hint": "moderate",
        "model": "openai/gpt-4o-mini", "tier": "budget",
        "provider": "openai",
        "budget_model": "meta-llama/llama-3.1-8b-instruct",
        "budget_tier": "local",
        "description": "Standard Test-Generierung",
    },
    {
        "agent_role": "tester", "complexity_hint": "complex",
        "model": "openai/gpt-4o", "tier": "standard",
        "provider": "openai",
        "budget_model": "openai/gpt-4o-mini", "budget_tier": "budget",
        "description": "Komplexe Test-Suites",
    },
    # Guardian
    {
        "agent_role": "guardian", "complexity_hint": "trivial",
        "model": "openai/gpt-4o-mini", "tier": "budget",
        "provider": "openai",
        "budget_model": "meta-llama/llama-3.1-8b-instruct",
        "budget_tier": "local",
        "description": "Guardian Format-Checks (UC-SE-2)",
    },
    {
        "agent_role": "guardian", "complexity_hint": "moderate",
        "model": "openai/gpt-4o", "tier": "standard",
        "provider": "openai",
        "budget_model": "openai/gpt-4o-mini", "budget_tier": "budget",
        "description": "Guardian Code Review",
    },
    {
        "agent_role": "guardian", "complexity_hint": "complex",
        "model": "anthropic/claude-3.5-sonnet", "tier": "premium",
        "provider": "anthropic",
        "budget_model": "openai/gpt-4o", "budget_tier": "standard",
        "description": "Guardian kritischer Code",
    },
    # Tech Lead
    {
        "agent_role": "tech_lead", "complexity_hint": "complex",
        "model": "anthropic/claude-3.5-sonnet", "tier": "premium",
        "provider": "anthropic",
        "budget_model": "openai/gpt-4o", "budget_tier": "standard",
        "description": "Tech Lead Review",
    },
    {
        "agent_role": "tech_lead", "complexity_hint": "architectural",
        "model": "anthropic/claude-3.5-sonnet", "tier": "premium",
        "provider": "anthropic",
        "budget_model": "openai/gpt-4o", "budget_tier": "standard",
        "description": "Architektur-Entscheidungen",
    },
    # Planner
    {
        "agent_role": "planner", "complexity_hint": "complex",
        "model": "anthropic/claude-3.5-sonnet", "tier": "premium",
        "provider": "anthropic",
        "budget_model": "openai/gpt-4o", "budget_tier": "standard",
        "description": "Task-Planung",
    },
    # Re-Engineer
    {
        "agent_role": "re_engineer", "complexity_hint": "moderate",
        "model": "openai/gpt-4o", "tier": "standard",
        "provider": "openai",
        "budget_model": "openai/gpt-4o-mini", "budget_tier": "budget",
        "description": "Refactoring Standard",
    },
    {
        "agent_role": "re_engineer", "complexity_hint": "complex",
        "model": "anthropic/claude-3.5-sonnet", "tier": "premium",
        "provider": "anthropic",
        "budget_model": "openai/gpt-4o", "budget_tier": "standard",
        "description": "Komplexes Re-Engineering",
    },
    # Security Auditor (UC-SE-5) — kein Downgrade: budget_model == model
    {
        "agent_role": "security_auditor", "complexity_hint": "moderate",
        "model": "anthropic/claude-3.5-sonnet", "tier": "premium",
        "provider": "anthropic",
        "budget_model": "anthropic/claude-3.5-sonnet",
        "budget_tier": "premium",
        "description": "Security Audit Standard — niemals downgegradet",
    },
    {
        "agent_role": "security_auditor", "complexity_hint": "complex",
        "model": "anthropic/claude-3.5-sonnet", "tier": "premium",
        "provider": "anthropic",
        "budget_model": "anthropic/claude-3.5-sonnet",
        "budget_tier": "premium",
        "description": "Security Audit komplex — niemals downgegradet",
    },
]

# Emergency-Fallback: Budget > 100% überschritten
EMERGENCY_FALLBACK_MODEL = "openai/gpt-4o-mini"
EMERGENCY_FALLBACK_TIER = "budget"
