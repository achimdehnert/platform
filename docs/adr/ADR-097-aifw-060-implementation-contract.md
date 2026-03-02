---
id: ADR-097
title: "aifw 0.6.0 Implementation Contract — Models, Migration, Service Layer, and Public API"
status: proposed
date: 2026-03-02
author: Achim Dehnert
owner: Achim Dehnert
decision-makers: [Achim Dehnert]
consulted: []
informed: [bfagent, travel-beat, weltenhub, pptx-hub, risk-hub, authoringfw teams]
scope: aifw package (iil-aifw) — version 0.6.0
tags: [aifw, implementation, models, migration, service, api, django, postgresql]
related: [ADR-057, ADR-089, ADR-093, ADR-094, ADR-095, ADR-096]
supersedes: []
amends: [ADR-089, ADR-093, ADR-095]
last_verified: 2026-03-02
---

# ADR-097: aifw 0.6.0 Implementation Contract — Models, Migration, Service Layer, and Public API

| Field | Value |
|-------|-------|
| Status | **Proposed** |
| Date | 2026-03-02 |
| Author | Achim Dehnert |
| Scope | `aifw` package — version 0.6.0 |
| Amends | ADR-089 (LiteLLM Architecture — extends `AIActionType`), ADR-093 (AI Config App — adds `TierQualityMapping`), ADR-095 (Quality-Level Routing — implementation specification) |
| Related | ADR-057 (Test Strategy), ADR-094 (Migration Conflict Resolution), ADR-096 (authoringfw Architecture) |

---

## 1. Context and Problem Statement

ADR-095 (Quality-Level Routing) defines **what** `aifw` 0.6.0 must implement. This ADR defines **how** — the exact Django models, PostgreSQL migration, service layer code, public API surface, and acceptance criteria that constitute a complete and correct implementation.

This separation exists because:
1. ADR-095 is an architecture decision subject to external review; it must remain stable during implementation
2. Implementation details (exact field names, index names, cache key formats, Django migration numbers) should not pollute the architecture document
3. This ADR serves as the implementation contract — a developer can implement `aifw` 0.6.0 from this document alone

### 1.1 What 0.6.0 Must Deliver

From ADR-095, three categories of changes:

| Category | Changes |
|----------|---------|
| **Model extension** | `AIActionType` +3 nullable columns; new `TierQualityMapping` model; `AIUsageLog` +1 column |
| **Migration** | 4 partial unique indexes; CHECK constraint on `priority`; no breaking schema changes |
| **Service + API** | `_lookup_cascade()`, `get_action_config()` with Redis cache, `get_quality_level_for_tier()`, `QualityLevel` constants; all exported from `aifw.__init__` |

### 1.2 Backwards Compatibility Contract

**Non-negotiable:** Every existing call site of the form:

```python
sync_completion(action_code="...", messages=[...])
```

must continue to work identically after upgrading to `iil-aifw==0.6.0`. No consumer app changes are required for the upgrade.

---

## 2. Model Specification

### 2.1 `AIActionType` Extension

Three new nullable columns added to the existing `AIActionType` model:

```python
# aifw/models.py — additions to existing AIActionType class

class AIActionType(models.Model):
    # --- Existing fields (unchanged) ---
    code = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    default_model = models.ForeignKey("LLMModel", on_delete=models.PROTECT,
                                       related_name="default_action_types")
    fallback_model = models.ForeignKey("LLMModel", on_delete=models.PROTECT,
                                        related_name="fallback_action_types",
                                        null=True, blank=True)
    max_tokens = models.IntegerField(default=2048)
    temperature = models.FloatField(default=0.7)
    is_active = models.BooleanField(default=True, db_index=True)
    budget_per_day = models.DecimalField(max_digits=10, decimal_places=4,
                                          null=True, blank=True)

    # --- New fields (0.6.0) ---
    quality_level = models.IntegerField(
        null=True, blank=True,
        help_text="1-9 quality scale. NULL = catch-all for any quality_level."
    )
    priority = models.CharField(
        max_length=16, null=True, blank=True,
        help_text="'fast'|'balanced'|'quality'. NULL = catch-all. "
                  "Enforced by DB CHECK constraint."
    )
    prompt_template_key = models.CharField(
        max_length=128, null=True, blank=True,
        help_text="promptfw template key. Plain string — aifw never imports promptfw."
    )

    class Meta:
        app_label = "aifw"
        # NOTE: No unique_together — replaced by 4 partial indexes in migration.
        # See ADR-095 §5.2 for PostgreSQL NULL semantics explanation.
        indexes = [
            models.Index(fields=["code", "is_active"], name="idx_action_code_active"),
        ]

    def __str__(self) -> str:
        parts = [self.code]
        if self.quality_level is not None:
            parts.append(f"ql={self.quality_level}")
        if self.priority is not None:
            parts.append(f"p={self.priority}")
        return ":".join(parts)
```

### 2.2 New Model: `TierQualityMapping`

```python
# aifw/models.py — new model

class TierQualityMapping(models.Model):
    """
    DB-driven mapping from subscription tier names to quality_level integers.
    Replaces hardcoded TIER_QUALITY_MAP dicts in consumer apps (ADR-095 H-01).
    """
    tier = models.CharField(
        max_length=64, unique=True,
        help_text="Subscription tier name e.g. 'premium', 'pro', 'freemium'."
    )
    quality_level = models.IntegerField(
        help_text="Quality level 1-9 assigned to this tier. "
                  "Use QualityLevel constants (ECONOMY=2, BALANCED=5, PREMIUM=8)."
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
```

### 2.3 `AIUsageLog` Extension

One new column to support direct cost-per-tier SQL analytics (ADR-095 OQ-2):

```python
# Addition to existing AIUsageLog model
quality_level = models.IntegerField(
    null=True, blank=True,
    help_text="Quality level of the request (1-9). NULL for legacy entries."
)
```

---

## 3. Migration Specification

### 3.1 Migration File Structure

```
aifw/migrations/
├── 0001_initial.py
├── ...
└── 000X_quality_level_routing.py    ← new migration for 0.6.0
```

Per ADR-094 (Migration Conflict Resolution): migration number must be `max(existing) + 1`.

### 3.2 Complete Migration Content

```python
# aifw/migrations/000X_quality_level_routing.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aifw", "000W_previous_migration"),  # replace with actual predecessor
    ]

    operations = [
        # --- 1. Add nullable columns to AIActionType ---
        migrations.AddField(
            model_name="aiactiontype",
            name="quality_level",
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="aiactiontype",
            name="priority",
            field=models.CharField(max_length=16, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="aiactiontype",
            name="prompt_template_key",
            field=models.CharField(max_length=128, null=True, blank=True),
        ),

        # --- 2. CHECK constraint on priority column ---
        migrations.RunSQL(
            sql="""
                ALTER TABLE aifw_aiactiontype
                ADD CONSTRAINT chk_priority_values
                CHECK (priority IN ('fast', 'balanced', 'quality') OR priority IS NULL);
            """,
            reverse_sql="""
                ALTER TABLE aifw_aiactiontype
                DROP CONSTRAINT IF EXISTS chk_priority_values;
            """,
        ),

        # --- 3. Four partial unique indexes (B-01 fix from ADR-095 review) ---
        # Replaces conceptual UNIQUE(code, quality_level, priority) which fails
        # for NULL values in PostgreSQL (NULL != NULL per ISO/IEC 9075).

        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX uix_aiaction_catchall
                ON aifw_aiactiontype (code)
                WHERE quality_level IS NULL AND priority IS NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS uix_aiaction_catchall;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX uix_aiaction_ql_only
                ON aifw_aiactiontype (code, quality_level)
                WHERE priority IS NULL AND quality_level IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS uix_aiaction_ql_only;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX uix_aiaction_prio_only
                ON aifw_aiactiontype (code, priority)
                WHERE quality_level IS NULL AND priority IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS uix_aiaction_prio_only;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX uix_aiaction_exact
                ON aifw_aiactiontype (code, quality_level, priority)
                WHERE quality_level IS NOT NULL AND priority IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS uix_aiaction_exact;",
        ),

        # --- 4. Create TierQualityMapping table ---
        migrations.CreateModel(
            name="TierQualityMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("tier", models.CharField(max_length=64, unique=True)),
                ("quality_level", models.IntegerField()),
                ("is_active", models.BooleanField(default=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"app_label": "aifw", "ordering": ["-quality_level"]},
        ),

        # --- 5. Seed default TierQualityMapping rows ---
        migrations.RunSQL(
            sql="""
                INSERT INTO aifw_tierqualitymapping (tier, quality_level, is_active, created_at, updated_at)
                VALUES
                    ('premium',  8, TRUE, NOW(), NOW()),
                    ('pro',      5, TRUE, NOW(), NOW()),
                    ('freemium', 2, TRUE, NOW(), NOW())
                ON CONFLICT (tier) DO NOTHING;
            """,
            reverse_sql="DELETE FROM aifw_tierqualitymapping WHERE tier IN ('premium','pro','freemium');",
        ),

        # --- 6. Add quality_level column to AIUsageLog ---
        migrations.AddField(
            model_name="aiusagelog",
            name="quality_level",
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
```

---

## 4. Constants Specification

```python
# aifw/constants.py

class QualityLevel:
    """
    Named constants for the quality_level integer scale (ADR-095 §5.1).

    Use these constants instead of raw integers in all consumer code:
        quality = QualityLevel.PREMIUM   # 8
        quality = QualityLevel.BALANCED  # 5
        quality = QualityLevel.ECONOMY   # 2

    The full 1-9 scale is valid; these constants represent canonical
    midpoints for each band:
        Economy:  1-3 → Together AI / Groq / budget models
        Balanced: 4-6 → GPT-4o-mini / Gemini Flash / Llama 3.3 70B
        Premium:  7-9 → Claude Sonnet/Opus / GPT-4o full
    """
    ECONOMY: int = 2
    BALANCED: int = 5
    PREMIUM: int = 8
```

---

## 5. Service Layer Specification

### 5.1 Lookup Cascade

```python
# aifw/service.py

from __future__ import annotations
from django.db.models import Q
from .models import AIActionType
from .exceptions import ConfigurationError


def _lookup_cascade(
    code: str,
    quality_level: int | None,
    priority: str | None,
) -> AIActionType:
    """
    4-level deterministic lookup cascade (ADR-095 §5.4).

    Steps are evaluated in order; first non-None result wins.
    Steps involving a None caller parameter are structurally equivalent
    to a lower-level step and are therefore skipped.

    Uniqueness at each step is guaranteed by the 4 partial unique indexes
    in the migration; .first() is a safety net, not the source of determinism.
    """
    base_qs = AIActionType.objects.filter(is_active=True)

    # Step 1 — Exact match (only meaningful when both params are non-None)
    if quality_level is not None and priority is not None:
        obj = base_qs.filter(
            code=code, quality_level=quality_level, priority=priority
        ).first()
        if obj is not None:
            return obj

    # Step 2 — Level match: priority catch-all
    if quality_level is not None:
        obj = base_qs.filter(
            code=code, quality_level=quality_level, priority__isnull=True
        ).first()
        if obj is not None:
            return obj

    # Step 3 — Priority match: quality catch-all (only when priority non-None)
    if priority is not None:
        obj = base_qs.filter(
            code=code, quality_level__isnull=True, priority=priority
        ).first()
        if obj is not None:
            return obj

    # Step 4 — Full catch-all (both NULL)
    obj = base_qs.filter(
        code=code, quality_level__isnull=True, priority__isnull=True
    ).first()
    if obj is not None:
        return obj

    raise ConfigurationError(
        f"No active AIActionType for code={code!r}, quality_level={quality_level}, "
        f"priority={priority!r}. "
        f"A catch-all row (quality_level=NULL, priority=NULL) must always exist. "
        f"Run 'check_aifw_config --fix' to seed missing entries."
    )
```

### 5.2 `get_action_config()` with Cache

```python
# aifw/service.py (continued)

from typing import TypedDict
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class ActionConfig(TypedDict):
    action_id: int
    model_id: int
    model: str
    provider: str
    base_url: str
    api_key_env_var: str
    prompt_template_key: str | None
    max_tokens: int
    temperature: float


_CACHE_TTL = 300  # 5 minutes — AIActionType rows change rarely


def _action_cache_key(code: str, quality_level: int | None, priority: str | None) -> str:
    return f"aifw:action:{code}:{quality_level}:{priority}"


def get_action_config(
    action_code: str,
    quality_level: int | None = None,
    priority: str | None = None,
) -> ActionConfig:
    """
    Resolve and return the full action configuration for a given action_code,
    quality_level, and priority. Result is cached in Redis for _CACHE_TTL seconds.

    This is the primary read path for authoringfw and consumer apps (ADR-095 §5.5).
    """
    cache_key = _action_cache_key(action_code, quality_level, priority)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    obj = _lookup_cascade(action_code, quality_level, priority)
    model = obj.default_model

    result: ActionConfig = {
        "action_id": obj.pk,
        "model_id": model.pk,
        "model": model.model_identifier,
        "provider": model.provider,
        "base_url": model.base_url or "",
        "api_key_env_var": model.api_key_env_var or "",
        "prompt_template_key": obj.prompt_template_key,
        "max_tokens": obj.max_tokens,
        "temperature": obj.temperature,
    }
    cache.set(cache_key, result, timeout=_CACHE_TTL)
    return result


@receiver([post_save, post_delete], sender=AIActionType)
def _invalidate_action_cache(sender, instance: AIActionType, **kwargs) -> None:
    """Invalidate all cache entries for this action_code on any change."""
    # Pattern-delete: invalidate all quality_level/priority combinations
    # Uses cache.delete_many with known key patterns; Redis SCAN if needed.
    for ql in [None, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
        for prio in [None, "fast", "balanced", "quality"]:
            cache.delete(_action_cache_key(instance.code, ql, prio))
```

### 5.3 `get_quality_level_for_tier()` with Cache

```python
# aifw/service.py (continued)

from .models import TierQualityMapping
from .constants import QualityLevel


_TIER_CACHE_TTL = 300


def get_quality_level_for_tier(tier: str | None) -> int:
    """
    DB-driven tier → quality_level resolution (ADR-095 §5.6, H-01 fix).

    Replaces hardcoded TIER_QUALITY_MAP dicts in consumer apps.
    Falls back to QualityLevel.BALANCED (5) if tier is None or not found in DB.

    Args:
        tier: Subscription tier name e.g. "premium", "pro", "freemium".
              Typically from user.subscription or equivalent field.

    Returns:
        int: quality_level 1-9
    """
    if not tier:
        return QualityLevel.BALANCED

    cache_key = f"aifw:tier:{tier}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    obj = TierQualityMapping.objects.filter(tier=tier, is_active=True).first()
    result = obj.quality_level if obj is not None else QualityLevel.BALANCED
    cache.set(cache_key, result, timeout=_TIER_CACHE_TTL)
    return result


@receiver([post_save, post_delete], sender=TierQualityMapping)
def _invalidate_tier_cache(sender, instance: TierQualityMapping, **kwargs) -> None:
    cache.delete(f"aifw:tier:{instance.tier}")
```

### 5.4 Extended `sync_completion()` Signature

The existing `sync_completion()` function is extended with two optional parameters, both defaulting to `None`. Existing call sites require zero changes:

```python
# aifw/service.py (continued)

def sync_completion(
    action_code: str,
    messages: list[dict],
    quality_level: int | None = None,    # NEW — optional
    priority: str | None = None,          # NEW — optional
    **kwargs,                              # forward compatibility
) -> LLMResult:
    """
    Execute a synchronous LLM completion.

    quality_level and priority are used for config lookup only (get_action_config).
    quality_level is also stored in AIUsageLog for cost attribution.
    """
    config = get_action_config(action_code, quality_level, priority)

    # ... existing litellm call logic, using config["model"], config["max_tokens"] etc.

    # AIUsageLog entry now includes quality_level
    AIUsageLog.objects.create(
        action_code=action_code,
        model=config["model"],
        quality_level=quality_level,   # NEW column
        # ... existing fields
    )
```

---

## 6. Public API Surface (`aifw/__init__.py`)

The complete set of names exported from `aifw` after 0.6.0:

```python
# aifw/__init__.py

# Existing exports (unchanged)
from .service import sync_completion
from .exceptions import ConfigurationError, AIFWError

# New exports (0.6.0)
from .service import get_action_config, get_quality_level_for_tier
from .constants import QualityLevel
from .types import ActionConfig  # TypedDict for type checkers

__version__ = "0.6.0"
__all__ = [
    # Core
    "sync_completion",
    # New 0.6.0
    "get_action_config",
    "get_quality_level_for_tier",
    "QualityLevel",
    "ActionConfig",
    # Exceptions
    "ConfigurationError",
    "AIFWError",
]
```

---

## 7. Admin Registration

```python
# aifw/admin.py — additions

from django.contrib import admin
from .models import AIActionType, TierQualityMapping


@admin.register(AIActionType)
class AIActionTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "quality_level", "priority", "default_model",
                    "prompt_template_key", "is_active"]
    list_filter = ["is_active", "quality_level", "priority"]
    search_fields = ["code", "name", "prompt_template_key"]
    ordering = ["code", "quality_level", "priority"]


@admin.register(TierQualityMapping)
class TierQualityMappingAdmin(admin.ModelAdmin):
    list_display = ["tier", "quality_level", "is_active", "updated_at"]
    list_filter = ["is_active"]
    ordering = ["-quality_level"]
```

---

## 8. Acceptance Criteria

A `aifw` 0.6.0 release is complete when ALL of the following pass:

### 8.1 Functional

| # | Criterion | How to verify |
|---|-----------|--------------|
| F-01 | `sync_completion(action_code="x", messages=[])` works without quality_level/priority | Existing test suite green |
| F-02 | `_lookup_cascade("x", 8, "quality")` returns exact-match row when it exists | Unit test |
| F-03 | `_lookup_cascade("x", 8, None)` returns level-match row when exact absent | Unit test |
| F-04 | `_lookup_cascade("x", None, "fast")` returns priority-match row | Unit test |
| F-05 | `_lookup_cascade("x", None, None)` returns catch-all row | Unit test |
| F-06 | `_lookup_cascade("x", 8, "quality")` raises `ConfigurationError` when no row matches at any level | Unit test |
| F-07 | Duplicate catch-all row rejected by DB | Integration test: second INSERT raises `IntegrityError` |
| F-08 | `priority="invalid"` rejected by DB CHECK constraint | Integration test |
| F-09 | `get_action_config()` returns cached result on second call (no DB query) | Unit test with `assertNumQueries(0)` on second call |
| F-10 | `AIActionType.save()` invalidates all cache keys for that `code` | Integration test |
| F-11 | `get_quality_level_for_tier("premium")` returns 8 after seed migration | Integration test |
| F-12 | `get_quality_level_for_tier(None)` returns `QualityLevel.BALANCED` (5) | Unit test |
| F-13 | `AIUsageLog` entry has `quality_level` populated after `sync_completion(..., quality_level=7)` | Integration test |

### 8.2 Schema

| # | Criterion | How to verify |
|---|-----------|--------------|
| S-01 | `makemigrations --check` exits 0 (no undetected model changes) | CI |
| S-02 | `migrate` applies cleanly on empty DB | CI |
| S-03 | `migrate` applies cleanly on existing DB with data | Staging test |
| S-04 | All 4 partial unique indexes present in DB after migration | `\d aifw_aiactiontype` in psql |
| S-05 | `TierQualityMapping` table has 3 seed rows after fresh migration | SQL query |

### 8.3 Backwards Compatibility

| # | Criterion |
|---|-----------|
| B-01 | All consumer apps (`bfagent`, `travel-beat`, etc.) run their existing test suites green after upgrading to `iil-aifw==0.6.0` without any code changes |
| B-02 | Existing `AIActionType` rows with `quality_level=NULL, priority=NULL` continue to be found by catch-all lookup |

---

## 9. Testing Requirements (ADR-057)

```
aifw/tests/
├── test_constants.py          # QualityLevel values correct
├── test_service.py            # _lookup_cascade all 4 steps + ConfigurationError
├── test_cache.py              # get_action_config cache hit/miss + invalidation
├── test_tier.py               # get_quality_level_for_tier hit/miss/None/inactive
├── test_models.py             # partial unique index integrity
├── test_contracts.py          # ActionConfig TypedDict shape
└── integration/
    └── test_sync_completion.py  # end-to-end with catch-all AIActionType row
```

Minimum coverage target: **90%** for `service.py`, `constants.py`, `models.py`.

---

## 10. Release Checklist

| Step | Action | Owner |
|------|--------|-------|
| 1 | Implement models + migration | `aifw` |
| 2 | Implement `constants.py` | `aifw` |
| 3 | Implement `service.py` (_lookup_cascade, get_action_config, get_quality_level_for_tier) | `aifw` |
| 4 | Extend `sync_completion()` signature | `aifw` |
| 5 | Update `admin.py` | `aifw` |
| 6 | Update `__init__.py` exports | `aifw` |
| 7 | All acceptance criteria F-01..F-13, S-01..S-05, B-01..B-02 pass | `aifw` |
| 8 | Bump version to `0.6.0` in `pyproject.toml` | `aifw` |
| 9 | Tag `v0.6.0` in GitHub | `aifw` |
| 10 | Update `iil-aifw` in `bfagent/requirements.txt` | `bfagent` |
| 11 | Run `init_bfagent_aifw_config` with quality-level seeds | `bfagent` server |
| 12 | Run `check_aifw_config --strict` | `bfagent` server |

---

## 11. References

- [ADR-057: Four-Level Test Strategy](ADR-057-platform-test-strategy.md) — coverage targets, test taxonomy
- [ADR-089: bfagent-llm LiteLLM Architecture](ADR-089-bfagent-llm-litellm-db-driven-architecture.md) — `AIActionType` origin
- [ADR-093: AI Config App](ADR-093-ai-config-app.md) — `AIActionType` as shared Django app
- [ADR-094: Django Migration Conflict Resolution](ADR-094-django-migration-conflict-resolution.md) — migration numbering rules
- [ADR-095: aifw Quality-Level Routing](ADR-095-aifw-quality-level-routing.md) — architecture decisions this ADR implements
- [ADR-096: authoringfw Scope and Architecture](ADR-096-authoringfw-scope-and-architecture.md) — primary consumer of 0.6.0 API
- `iil-aifw`: https://github.com/achimdehnert/aifw
