"""
aifw/models.py — Django models for aifw 0.6.0.

IMPORTANT: This file shows ONLY the additions to existing models (marked NEW)
and the new TierQualityMapping model. The existing fields are shown for context.

ADR-097 §2 — Model Specification.
"""
from __future__ import annotations

from django.db import models


# ──────────────────────────────────────────────────────────────────────────────
# EXISTING MODEL EXTENSION: AIActionType
# ──────────────────────────────────────────────────────────────────────────────

class AIActionType(models.Model):
    """
    Konfigurationstabelle für LLM-Calls.

    Each row defines model + template for a (code, quality_level, priority) combination.
    NULL in quality_level or priority means "catch-all" for that dimension.

    Uniqueness: NOT enforced by unique_together (PostgreSQL NULL != NULL semantics).
    Enforced instead by 4 partial unique indexes in the migration:
        uix_aiaction_exact     — both non-NULL
        uix_aiaction_ql_only   — quality_level non-NULL, priority NULL
        uix_aiaction_prio_only — priority non-NULL, quality_level NULL
        uix_aiaction_catchall  — both NULL

    See ADR-095 §5.2 for NULL semantics explanation.
    """

    # ── Existing fields (unchanged) ───────────────────────────────────────────
    code = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Action identifier e.g. 'story_writing', 'chapter_export'.",
    )
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    default_model = models.ForeignKey(
        "LLMModel",
        on_delete=models.PROTECT,
        related_name="default_action_types",
    )
    fallback_model = models.ForeignKey(
        "LLMModel",
        on_delete=models.PROTECT,
        related_name="fallback_action_types",
        null=True,
        blank=True,
    )
    max_tokens = models.IntegerField(default=2048)
    temperature = models.FloatField(default=0.7)
    is_active = models.BooleanField(default=True, db_index=True)
    budget_per_day = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Daily token budget in USD. NULL = no limit.",
    )

    # ── NEW fields (0.6.0 — ADR-095) ─────────────────────────────────────────
    quality_level = models.IntegerField(
        null=True,
        blank=True,
        help_text=(
            "Quality band (1–9) or NULL (catch-all). "
            "1–3=Economy, 4–6=Balanced, 7–9=Premium. "
            "Use QualityLevel constants: ECONOMY=2, BALANCED=5, PREMIUM=8."
        ),
    )
    priority = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        help_text=(
            "'fast'|'balanced'|'quality' or NULL (catch-all). "
            "Enforced by DB CHECK constraint chk_aiaction_priority."
        ),
    )
    prompt_template_key = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text=(
            "promptfw template key e.g. 'story_writing_premium'. "
            "NULL = consumer code must use action_code as fallback. "
            "Convention: <action_code>[_economy|_balanced|_premium]. "
            "aifw never imports promptfw — this is a plain string."
        ),
    )

    class Meta:
        app_label = "aifw"
        # NO unique_together — replaced by 4 partial indexes in migration.
        indexes = [
            models.Index(fields=["code", "is_active"], name="idx_aiaction_code_active"),
        ]
        verbose_name = "AI Action Type"
        verbose_name_plural = "AI Action Types"
        ordering = ["code", "quality_level", "priority"]

    def __str__(self) -> str:
        parts = [self.code]
        if self.quality_level is not None:
            parts.append(f"ql={self.quality_level}")
        if self.priority is not None:
            parts.append(f"p={self.priority}")
        return ":".join(parts)

    def clean(self) -> None:
        """Django-level validation as secondary guard (DB CHECK is primary)."""
        from django.core.exceptions import ValidationError
        from .constants import VALID_PRIORITIES

        if self.priority is not None and self.priority not in VALID_PRIORITIES:
            raise ValidationError(
                f"Invalid priority {self.priority!r}. "
                f"Valid values: {sorted(VALID_PRIORITIES)} or None."
            )
        if self.quality_level is not None:
            if not (1 <= self.quality_level <= 9):
                raise ValidationError(
                    f"quality_level must be 1–9 or None, got {self.quality_level}."
                )


# ──────────────────────────────────────────────────────────────────────────────
# NEW MODEL: TierQualityMapping (ADR-095 H-01 fix)
# ──────────────────────────────────────────────────────────────────────────────

class TierQualityMapping(models.Model):
    """
    DB-driven mapping from subscription tier names to quality_level integers.

    Replaces hardcoded TIER_QUALITY_MAP dicts in consumer apps (ADR-095 H-01).
    Changeable via Django Admin without code deployment.

    Default seed (applied in migration):
        premium  → 8 (QualityLevel.PREMIUM)
        pro      → 5 (QualityLevel.BALANCED)
        freemium → 2 (QualityLevel.ECONOMY)

    Consumer apps use:
        from aifw import get_quality_level_for_tier
        quality = get_quality_level_for_tier(user.subscription)  # "premium" → 8
    """

    tier = models.CharField(
        max_length=64,
        unique=True,
        help_text="Subscription tier name e.g. 'premium', 'pro', 'freemium'.",
    )
    quality_level = models.IntegerField(
        help_text=(
            "Quality level 1–9 assigned to this tier. "
            "Use QualityLevel constants: ECONOMY=2, BALANCED=5, PREMIUM=8."
        ),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "aifw"
        verbose_name = "Tier Quality Mapping"
        verbose_name_plural = "Tier Quality Mappings"
        ordering = ["-quality_level"]

    def __str__(self) -> str:
        return f"{self.tier} → ql={self.quality_level}"


# ──────────────────────────────────────────────────────────────────────────────
# EXISTING MODEL EXTENSION: AIUsageLog
# ──────────────────────────────────────────────────────────────────────────────

class AIUsageLog(models.Model):
    """
    Usage log for every sync_completion() call.

    NEW in 0.6.0: quality_level as dedicated column for direct SQL cost-per-tier
    analytics without joins. (ADR-095 OQ-2 resolved.)

    Example query:
        SELECT quality_level, SUM(cost_usd), COUNT(*)
        FROM aifw_aiusagelog
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY quality_level;
    """

    # ── Existing fields (unchanged) ───────────────────────────────────────────
    action_code = models.CharField(max_length=64, db_index=True)
    model = models.CharField(max_length=128)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    latency_ms = models.IntegerField(default=0)
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # ── NEW field (0.6.0 — ADR-095 OQ-2) ─────────────────────────────────────
    quality_level = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Quality level of the request (1–9). "
            "NULL for legacy entries created before 0.6.0. "
            "Dedicated column — never use join to AIActionType for cost analytics."
        ),
    )

    class Meta:
        app_label = "aifw"
        verbose_name = "AI Usage Log"
        verbose_name_plural = "AI Usage Logs"
        indexes = [
            models.Index(fields=["quality_level", "created_at"]),
            models.Index(fields=["action_code", "created_at"]),
        ]
