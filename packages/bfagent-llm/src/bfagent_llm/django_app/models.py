"""
DB-driven LLM Configuration Models (ADR-089).

Provides:
- LLMProvider: Global provider config (shared across tenants)
- LLMModel: Global model config with cost tracking
- AIActionType: Per-tenant action → model routing
- AIUsageLog: Per-tenant usage + cost tracking
- LLMConfigurationError: Raised when no model configured (no silent fallback)

Invariants:
- LLMProvider/LLMModel: NO tenant_id (global infrastructure)
- AIActionType/AIUsageLog: MUST have tenant_id (ADR-056)
- Active AIActionType without default_model → LLMConfigurationError
- AIActionType.code: snake_case (^[a-z][a-z0-9_]{2,49}$)
- DB tables: bfllm_ prefix
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


class LLMConfigurationError(Exception):
    """Raised when no active LLM model is configured for an action.

    This is an EXPLICIT error — there is no silent fallback to a
    global default model. Every active AIActionType MUST have a
    default_model assigned.
    """


ACTION_CODE_VALIDATOR = RegexValidator(
    r"^[a-z][a-z0-9_]{2,49}$",
    "Code muss snake_case sein (3-50 Zeichen, a-z/0-9/_).",
)

PROVIDER_NAME_VALIDATOR = RegexValidator(
    r"^[a-z][a-z0-9_-]*$",
    "Name muss lowercase sein (a-z, 0-9, -, _).",
)


class LLMProvider(models.Model):
    """Global LLM provider (shared across tenants).

    No tenant_id — providers are infrastructure resources.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        validators=[PROVIDER_NAME_VALIDATOR],
        help_text='Provider-Identifier, z.B. "openai", "anthropic", "groq".',
    )
    display_name = models.CharField(max_length=100)
    api_key_env_var = models.CharField(
        max_length=100,
        default="",
        help_text="Env-Var Name, z.B. OPENAI_API_KEY. "
        "Wird via read_secret() aufgelöst (ADR-045).",
    )
    base_url = models.URLField(
        blank=True,
        default="",
        help_text="Custom endpoint URL. Leer = Provider-Default.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "bfllm_providers"
        verbose_name = "LLM Provider"
        verbose_name_plural = "LLM Providers"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.display_name


class LLMModel(models.Model):
    """Global LLM model (shared across tenants).

    No tenant_id — models are infrastructure resources.
    Cost data enables per-tenant cost attribution via AIUsageLog.
    """

    provider = models.ForeignKey(
        LLMProvider,
        on_delete=models.CASCADE,
        related_name="models",
    )
    name = models.CharField(
        max_length=100,
        help_text='Model-ID beim Provider, z.B. "gpt-4o", "claude-sonnet-4".',
    )
    display_name = models.CharField(max_length=150)

    max_tokens = models.IntegerField(default=4096)
    context_window = models.IntegerField(
        default=128_000,
        help_text="Max context window in tokens.",
    )
    supports_vision = models.BooleanField(default=False)
    supports_tools = models.BooleanField(default=True)

    input_cost_per_million = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="USD per 1M input tokens.",
    )
    output_cost_per_million = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="USD per 1M output tokens.",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Markierung für init_llm_config Seed-Daten. "
        "Wird NICHT als stiller Fallback genutzt.",
    )

    class Meta:
        db_table = "bfllm_models"
        verbose_name = "LLM Model"
        verbose_name_plural = "LLM Models"
        unique_together = [("provider", "name")]
        ordering = ["provider__name", "name"]

    def __str__(self) -> str:
        return f"{self.provider.name}:{self.name}"

    def litellm_model_string(self) -> str:
        """Build LiteLLM-compatible model string: 'provider/model'."""
        return f"{self.provider.name}/{self.name}"


class AIActionType(models.Model):
    """Per-action LLM routing — tenant-specific (ADR-056).

    Each tenant can have their own model assignments per action.
    Without default_model → LLMConfigurationError (no silent fallback).
    """

    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Tenant-ID (ADR-056). Pflicht für Multi-Tenancy.",
    )

    code = models.CharField(
        max_length=50,
        validators=[ACTION_CODE_VALIDATOR],
        help_text="Eindeutiger Action-Code pro Tenant, z.B. "
        "'character_generation', 'hazard_analysis'.",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")

    default_model = models.ForeignKey(
        LLMModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_actions",
        help_text="Pflicht für aktive Actions. "
        "Ohne Model → LLMConfigurationError.",
    )
    fallback_model = models.ForeignKey(
        LLMModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fallback_for_actions",
        help_text="Fallback wenn default_model fehlschlägt.",
    )

    max_tokens = models.IntegerField(default=2000)
    temperature = models.FloatField(default=0.7)

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "bfllm_action_types"
        verbose_name = "AI Action Type"
        verbose_name_plural = "AI Action Types"
        unique_together = [("tenant_id", "code")]
        indexes = [
            models.Index(
                fields=["tenant_id", "code", "is_active"],
                name="bfllm_action_tenant_code_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.name})"

    def clean(self) -> None:
        if self.is_active and not self.default_model_id:
            raise ValidationError(
                {"default_model": "Aktive Actions MÜSSEN ein default_model haben."}
            )
        if (
            self.default_model_id
            and self.default_model
            and not self.default_model.is_active
        ):
            raise ValidationError(
                {"default_model": "default_model muss aktiv sein."}
            )

    def get_model(self) -> LLMModel:
        """Explicit model lookup. No silent fallback.

        Returns:
            LLMModel instance for this action.

        Raises:
            LLMConfigurationError: If no active model is configured.
        """
        if self.default_model and self.default_model.is_active:
            return self.default_model
        if self.fallback_model and self.fallback_model.is_active:
            return self.fallback_model
        raise LLMConfigurationError(
            f"Kein aktives Model für Action '{self.code}' konfiguriert. "
            f"Setze default_model in Admin → AI Action Types."
        )


class AIUsageLog(models.Model):
    """LLM usage tracking — tenant-specific (ADR-056).

    Every LLM call is logged for cost attribution and monitoring.
    """

    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Tenant-ID für Cost-Zuordnung.",
    )

    action_type = models.ForeignKey(
        AIActionType,
        on_delete=models.SET_NULL,
        null=True,
    )
    model_used = models.ForeignKey(
        LLMModel,
        on_delete=models.SET_NULL,
        null=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
    )

    latency_ms = models.IntegerField(default=0)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bfllm_usage_logs"
        verbose_name = "AI Usage Log"
        verbose_name_plural = "AI Usage Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "-created_at"],
                name="bfllm_usage_tenant_date_idx",
            ),
            models.Index(
                fields=["action_type", "-created_at"],
                name="bfllm_usage_action_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.action_type} / {self.model_used} "
            f"({self.created_at:%Y-%m-%d %H:%M})"
        )

    def save(self, *args, **kwargs) -> None:
        self.total_tokens = self.input_tokens + self.output_tokens
        if self.model_used:
            input_cost = (
                self.input_tokens / 1_000_000
            ) * float(self.model_used.input_cost_per_million)
            output_cost = (
                self.output_tokens / 1_000_000
            ) * float(self.model_used.output_cost_per_million)
            self.estimated_cost = input_cost + output_cost
        super().save(*args, **kwargs)
