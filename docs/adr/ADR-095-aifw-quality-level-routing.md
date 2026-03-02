---
id: ADR-095
title: "aifw Quality-Level Routing — Multi-Dimensional LLM Dispatch with Prompt-Template Coordination"
status: proposed
date: 2026-03-02
revised: 2026-03-02
revision: "1 — post external review"
author: Achim Dehnert
owner: Achim Dehnert
decision-makers: [Achim Dehnert]
consulted: [Senior IT-Architekt / Platform Review]
informed: [bfagent, travel-beat, weltenhub, pptx-hub, risk-hub, authoringfw, promptfw teams]
scope: Platform-wide (aifw, promptfw, authoringfw, all consumer apps)
tags: [llm, routing, quality, aifw, promptfw, authoringfw, api-design, backwards-compatibility]
related: [ADR-027, ADR-043, ADR-050, ADR-057, ADR-068, ADR-084, ADR-089, ADR-093]
supersedes: []
amends: [ADR-089, ADR-093]
last_verified: 2026-03-02
---

# ADR-095: aifw Quality-Level Routing — Multi-Dimensional LLM Dispatch with Prompt-Template Coordination

| Field | Value |
|-------|-------|
| Status | **Proposed** (rev1 — awaiting second review after blocker resolution) |
| Date | 2026-03-02 |
| Revised | 2026-03-02 (rev1 — resolved B-01, B-02, B-03, H-01..H-05, M-01..M-05, L-01..L-04) |
| Author | Achim Dehnert |
| Consulted | Senior IT-Architekt / Platform Review |
| Scope | `aifw`, `promptfw`, `authoringfw`, `bfagent`, `travel-beat`, `weltenhub`, `pptx-hub`, `risk-hub` |
| Amends | ADR-089 (bfagent-llm LiteLLM), ADR-093 (AI Config App) |
| Related | ADR-027, ADR-043, ADR-050, ADR-057, ADR-068, ADR-084, ADR-089, ADR-093 |

---

## Revision History

| Rev | Date | Author | Changes |
|-----|------|--------|---------|
| 0 | 2026-03-02 | Achim Dehnert | Initial draft |
| 1 | 2026-03-02 | Achim Dehnert | B-01: partial unique indexes; B-02: deterministic lookup; B-03: ADR-068 abgrenzung; H-01: TierQualityMapping model; H-02: Redis caching; H-03: priority explicit-only; H-04: row count corrected (180); H-05: OQ-1 resolved inline; M-01: status→proposed; M-02: CHECK constraint; M-03: QualityLevel constants; M-04: ConfigurationError kept (graceful degradation rejected); M-05: links cleaned; L-01..L-04: MADR compliance, ADR-057 ref, OQ-2 decided, semver confirmed |

---

## 1. Context and Problem Statement

### 1.1 Current State

All consumer apps on the platform call `aifw.sync_completion(action_code=..., messages=[...])` to execute LLM tasks. The `AIActionType` model currently maps each `action_code` to exactly one `(default_model, fallback_model)` pair — a flat, single-dimensional configuration established in ADR-089 and ADR-093.

Prompt templates are selected independently in the calling code — either hardcoded or looked up separately — without any coordination with the model selection.

### 1.2 Problems

| # | Problem | Impact |
|---|---------|--------|
| 1 | **No tier-based quality routing** | Premium users in travel-beat, bfagent, weltenhub receive the same model as freemium users. Impossible to monetise quality differential without code deployments. |
| 2 | **No speed/quality trade-off** | Time-sensitive tasks (live UI interactions) and quality-critical tasks (book chapter export) use the same model. Groq/Together AI cannot be leveraged for latency-sensitive paths. |
| 3 | **Prompt complexity decoupled from model quality** | A high-quality model receiving a minimal prompt, or a cheap model receiving a complex chain-of-thought prompt, both produce suboptimal results. `promptfw` template selection and `aifw` model selection are currently independent and uncoordinated. |
| 4 | **Template keys hardcoded in orchestrators** | `authoringfw` and consumer services hardcode `promptfw` template keys. Changing the template for a task requires a code deployment. |
| 5 | **Rapid change cycles demand API stability** | AI-assisted development (ADR-043) produces frequent model and prompt updates. Any API change that breaks consumer apps is disproportionately costly. |

### 1.3 Scope of Impact

| Repository | Role | Impact |
|-----------|------|--------|
| `aifw` | LLM execution framework | Schema + API change → v0.6.0 |
| `promptfw` | Prompt template engine | Template naming convention (resolved inline — §4.8) |
| `authoringfw` | Content orchestration (Writing, Research, Analysis) | Adopt `get_action_config()` API |
| `bfagent` | Book Factory — primary consumer | tier → quality_level via `get_quality_level_for_tier()` |
| `travel-beat` | DriftTales travel stories | tier → quality_level via `get_quality_level_for_tier()` |
| `weltenhub` | Weltenforger story universe | tier → quality_level via `get_quality_level_for_tier()` |
| `pptx-hub` | Presentation Studio | tier → quality_level via `get_quality_level_for_tier()` |
| `risk-hub` | Occupational safety SaaS | tier → quality_level via `get_quality_level_for_tier()` |

---

## 2. Relationship to ADR-068 (Adaptive Model Routing)

> **B-03 resolution** — ADR-068 was missing from all references in rev0. This section defines the explicit boundary.

ADR-068 (Adaptive Model Routing + Quality Feedback Loop) and ADR-095 address **orthogonal problems** at different layers:

| Dimension | ADR-068 | ADR-095 |
|-----------|---------|---------|
| **Layer** | Agent orchestration (`orchestrator_mcp`) | Consumer-app tier differentiation (platform-wide) |
| **Routing trigger** | LLM-based TaskRouter with confidence scoring | Explicit `quality_level` integer from consumer app |
| **Quality measurement** | Automatic `QualityEvaluator` feedback loop (N≥20 tasks) | None — quality is caller's responsibility |
| **Feedback loop** | Yes — routing matrix updates automatically | No — DB config updated by admin |
| **Primary goal** | Cost-optimal agent execution within `bfagent` workflows | Revenue-differentiated LLM quality across all consumer apps |
| **Scope** | `orchestrator_mcp/agent_team/` only | All 8 consumer repos + 3 framework packages |
| **Tier vocabulary** | `high_reasoning / standard_coding / budget_cloud / lean_local` | `quality_level` integer 1–9 |

**Coexistence rule:** ADR-068 routing operates *inside* the AI Engineering Squad workflow. When ADR-068's TaskRouter selects `standard_coding` tier for a task, `aifw` executes that task using ADR-095 routing to select the correct model for the current quality_level. ADR-068 answers "which agent tier?" — ADR-095 answers "which model for this consumer's quality expectation?". They are not in conflict.

---

## 3. Decision Drivers

- **Backwards compatibility is non-negotiable** — zero breaking changes to existing `sync_completion()` call sites across 8 repos
- **DB-driven configuration end-to-end** — model assignments, template keys, *and tier→quality mappings* must be changeable via Django Admin without code deployment
- **Single control variable** — one parameter (`quality_level`) drives both prompt complexity and model quality; dual configuration is a maintenance liability
- **Package independence** — `promptfw` and `aifw` must remain independently deployable without circular imports
- **Transparency** — every LLM call must be logged with `quality_level` as a dedicated column for cost-per-tier SQL analytics
- **Incrementalism** — implementation phased; consumer apps adopt at their own pace via catch-all guarantee
- **Determinism** — lookup must return exactly one row under any input; non-deterministic results are a deployment defect

---

## 4. Considered Options

### Option 1 — Status quo: action_code suffixes
Add quality variants as separate `action_code` entries: `story_writing_premium`, `story_writing_free`, `story_writing_fast`.

**Assessment:** Pollutes the `action_code` namespace. 20 codes × 3 tiers × 3 priorities = 180 rows with no structure. `check_aifw_config` becomes unmanageable. Speed preference cannot be expressed orthogonally to quality. **Rejected.**

### Option 2 — Per-user model override in DB
Store a `preferred_model_id` on the user or subscription object.

**Assessment:** Granularity is wrong — per-user is too fine. Requires consumer apps to resolve model IDs, coupling them to `aifw` internals. Admin overhead scales with user count. **Rejected.**

### Option 3 — Separate `routing-fw` package
Extract routing logic into a new package between consumer apps and `aifw`.

**Assessment:** Adds a fourth package dependency to every consumer app. Routing is inherently `aifw`'s responsibility. Unnecessary indirection. **Rejected.**

### Option 4 — `authoringfw` as universal LLM gateway
All LLM calls routed through `authoringfw`.

**Assessment:** Creates wrong cross-domain dependency. `risk-hub` (occupational safety) would depend on `authoringfw` (content creation). Violates ADR-050. **Rejected.**

### Option 5 — Extend `sync_completion` + `AIActionType` + new `TierQualityMapping` model *(chosen)*

**Assessment:** Fully backwards-compatible. Single `quality_level` integer drives both model and template selection. `TierQualityMapping` makes tier→quality DB-driven (no hardcoded maps in consumer apps). Partial unique indexes fix NULL semantics. Deterministic lookup via 4-step cascade with `.first()`. **Accepted.**

---

## 5. Decision

### 5.1 Extended `sync_completion` API

The public API of `aifw.sync_completion()` is extended with two optional parameters, both defaulting to `None`. **All existing call sites are unchanged.**

```python
# Existing call sites — zero migration required:
result = sync_completion(action_code="story_writing", messages=[...])

# Extended call — new parameters are optional:
result = sync_completion(
    action_code="story_writing",
    messages=[...],
    quality_level=7,      # int | None, default=None
    priority="quality",   # Literal["fast","balanced","quality"] | None, default=None
)
```

**`quality_level` semantics (1–9 integer scale):**

| Range | Label | Constant | Target model tier | Typical use case |
|-------|-------|----------|-------------------|-----------------|
| 1–3 | Economy | `QualityLevel.ECONOMY = 2` | Together AI Qwen, OpenRouter Mistral Nemo, Groq Llama | Freemium users, UI autocomplete, bulk metadata |
| 4–6 | Balanced | `QualityLevel.BALANCED = 5` | GPT-4o-mini, Gemini 2.0 Flash, Llama 3.3 70B | Pro users, standard generation |
| 7–9 | Premium | `QualityLevel.PREMIUM = 8` | GPT-4o, Claude Sonnet 4, Claude Opus | Premium users, chapter export, editorial quality |
| `None` | Catch-all | — | Current default model | All existing call sites — unchanged |

**`priority` semantics — explicit override only** (see §5.6 for authoringfw pattern):

| Value | Meaning | Provider preference |
|-------|---------|-------------------|
| `"fast"` | Minimise latency | Groq (< 500 ms P50), Together AI Turbo (~1 s) |
| `"balanced"` | Default trade-off | OpenAI, Google, OpenRouter |
| `"quality"` | Maximise output quality at given level | Anthropic, OpenAI GPT-4o |
| `None` | Catch-all | Existing default — unchanged |

`priority` is a **caller-supplied override only**. No automatic derivation from `quality_level` happens inside `aifw` or `authoringfw`. If the caller passes `priority=None`, the DB lookup falls through to the catch-all row for that `code` + `quality_level` combination.

### 5.2 Extended `AIActionType` Model

Three new nullable columns are added to `aifw.AIActionType`:

```
AIActionType
├── code                  VARCHAR NOT NULL   — e.g. "story_writing"
├── name                  VARCHAR NOT NULL
├── description           TEXT
├── quality_level         INTEGER NULL       — 1-9 or NULL (catch-all)          ← NEW
├── priority              VARCHAR(16) NULL   — "fast"|"balanced"|"quality"|NULL  ← NEW
│                         CHECK (priority IN ('fast', 'balanced', 'quality'))
├── prompt_template_key   VARCHAR(128) NULL  — promptfw template key             ← NEW
├── default_model         FK → LLMModel NOT NULL
├── fallback_model        FK → LLMModel NULL
├── max_tokens            INTEGER NOT NULL
├── temperature           FLOAT NOT NULL
├── is_active             BOOLEAN NOT NULL
└── budget_per_day        DECIMAL NULL
```

**Uniqueness — partial indexes (B-01 fix):**

Standard `UNIQUE (code, quality_level, priority)` fails in PostgreSQL because `NULL != NULL` per ISO/IEC 9075. Four partial unique indexes replace it:

```sql
-- 1. Exact match rows (both dimensions specified)
CREATE UNIQUE INDEX uix_action_exact ON ai_action_type (code, quality_level, priority)
  WHERE quality_level IS NOT NULL AND priority IS NOT NULL;

-- 2. Level-only rows (priority catch-all)
CREATE UNIQUE INDEX uix_action_ql_only ON ai_action_type (code, quality_level)
  WHERE priority IS NULL;

-- 3. Priority-only rows (quality catch-all)
CREATE UNIQUE INDEX uix_action_prio_only ON ai_action_type (code, priority)
  WHERE quality_level IS NULL;

-- 4. Full catch-all rows (both NULL)
CREATE UNIQUE INDEX uix_action_catchall ON ai_action_type (code)
  WHERE quality_level IS NULL AND priority IS NULL;
```

**Null semantics:** `NULL` in either dimension means "catch-all" — matches any caller value for that dimension. Existing rows with both `NULL` function exactly as before.

### 5.3 New Model: `TierQualityMapping` (H-01 fix)

Replaces hardcoded `TIER_QUALITY_MAP` dictionaries in consumer apps. Tier→quality mapping is now DB-driven and changeable via Django Admin without deployment.

```
TierQualityMapping
├── tier            VARCHAR(64) UNIQUE NOT NULL  — "premium", "pro", "freemium"
├── quality_level   INTEGER NOT NULL             — 1-9
└── is_active       BOOLEAN NOT NULL DEFAULT TRUE
```

Default seed values:

| tier | quality_level |
|------|--------------|
| `premium` | 8 |
| `pro` | 5 |
| `freemium` | 2 |

### 5.4 Lookup Cascade — Deterministic (B-02 fix)

When `sync_completion(action_code, quality_level, priority)` is called, the following cascade is applied. **The first matching row wins. `.first()` is used at each step as a safety net; uniqueness is guaranteed by the partial indexes in §5.2.**

```python
def _lookup_cascade(
    code: str,
    quality_level: int | None,
    priority: str | None,
) -> AIActionType:
    steps = [
        # Step 1 — Exact match
        dict(code=code, quality_level=quality_level, priority=priority),
        # Step 2 — Level match (priority catch-all)
        dict(code=code, quality_level=quality_level, priority__isnull=True),
        # Step 3 — Priority match (quality catch-all)
        dict(code=code, quality_level__isnull=True, priority=priority),
        # Step 4 — Full catch-all
        dict(code=code, quality_level__isnull=True, priority__isnull=True),
    ]
    for step in steps:
        obj = AIActionType.objects.filter(**step, is_active=True).first()
        if obj is not None:
            return obj
    raise ConfigurationError(
        f"No active AIActionType for code={code!r}, quality_level={quality_level}, "
        f"priority={priority!r}. Ensure a catch-all row exists."
    )
```

Steps 1 and 3 are skipped when the corresponding parameter is `None` (they would be equivalent to step 2 and 4 respectively).

**`ConfigurationError` is not caught silently** — a missing catch-all row is a configuration defect that must fail loudly (HTTP 500). Graceful degradation to an unknown model would silently route premium users to a freemium model. `check_aifw_config` prevents this in CI.

### 5.5 New Public API: `get_action_config()` with Caching (H-02 fix)

```python
from aifw import get_action_config, get_quality_level_for_tier, QualityLevel

# Returns resolved config including prompt_template_key:
config = get_action_config(
    action_code="story_writing",
    quality_level=QualityLevel.PREMIUM,   # 8
    priority="quality",
)
# ActionConfig TypedDict:
# {
#   "action_id":           14,
#   "model_id":            3,
#   "model":               "anthropic/claude-sonnet-4-20250514",
#   "provider":            "anthropic",
#   "base_url":            "",
#   "api_key_env_var":     "ANTHROPIC_API_KEY",
#   "prompt_template_key": "story_writing_premium",
#   "max_tokens":          4096,
#   "temperature":         0.8,
# }
```

**Cache implementation (Django cache framework, Redis backend):**

```python
from django.core.cache import cache

def get_action_config(
    action_code: str,
    quality_level: int | None = None,
    priority: str | None = None,
) -> ActionConfig:
    cache_key = f"aifw:action:{action_code}:{quality_level}:{priority}"
    if cached := cache.get(cache_key):
        return cached
    obj = _lookup_cascade(action_code, quality_level, priority)
    result = _to_action_config(obj)
    cache.set(cache_key, result, timeout=300)
    return result
```

Cache is invalidated on `AIActionType` save/delete signals.

### 5.6 `QualityLevel` Constants and `get_quality_level_for_tier()` (M-03 + H-01)

```python
# aifw/constants.py
class QualityLevel:
    ECONOMY  = 2   # 1–3: Together AI / Groq / OpenRouter budget models
    BALANCED = 5   # 4–6: GPT-4o-mini, Gemini Flash, Llama 3.3 70B
    PREMIUM  = 8   # 7–9: Claude Sonnet/Opus, GPT-4o full

# aifw/service.py
def get_quality_level_for_tier(tier: str) -> int:
    """DB-driven tier→quality_level lookup. No hardcoded maps in consumer apps."""
    cache_key = f"aifw:tier:{tier}"
    if cached := cache.get(cache_key):
        return cached
    obj = TierQualityMapping.objects.filter(tier=tier, is_active=True).first()
    result = obj.quality_level if obj else QualityLevel.BALANCED
    cache.set(cache_key, result, timeout=300)
    return result
```

Consumer apps replace hardcoded tier maps with:

```python
from aifw import get_quality_level_for_tier

quality = get_quality_level_for_tier(user.subscription)  # "premium" → 8
```

### 5.7 Package Dependency Graph

```
promptfw    deps: jinja2, pyyaml
            (no aifw dependency — independently deployable)
    │
    │  prompt_template_key: plain string passed by caller
    │
aifw        deps: Django, litellm, redis
            (no promptfw dependency — independently deployable)
    │
    │  get_action_config() + get_quality_level_for_tier() + sync_completion()
    ▼
authoringfw deps: aifw, promptfw
            (content workflow orchestrator — Writing, Research, Analysis)
    │
    │  quality_level resolved from user tier by consumer app
    ▼
consumer-app (travel-beat, bfagent, weltenhub, …)
```

No circular dependencies exist or are introduced by this ADR.

### 5.8 `authoringfw` Scope and Canonical Orchestration Pattern

`authoringfw` is the platform's **content workflow orchestrator** for three domains:

| Domain | Examples |
|--------|---------|
| **Writing** | Chapter generation, outline, character creation, world-building |
| **Research** | Fact-checking, source synthesis, knowledge extraction |
| **Analysis** | Content analysis, style analysis, sentiment, readability scoring |

`priority` is **not derived automatically** from `quality_level` in `authoringfw`. It is passed explicitly by the caller or left as `None` (catch-all):

```python
class BaseContentOrchestrator:
    def execute(
        self,
        task: ContentTask,
        quality_level: int = QualityLevel.BALANCED,
        priority: str | None = None,   # explicit override only — no auto-derivation
    ) -> ContentResult:
        # Step 1 — resolve model + template (single cached DB call)
        config = get_action_config(
            action_code=task.action_code,
            quality_level=quality_level,
            priority=priority,
        )

        # Step 2 — render prompt via promptfw
        template_key = config.get("prompt_template_key") or task.action_code
        messages = promptfw.render(template_key, context=task.to_context())

        # Step 3 — execute LLM call
        result = sync_completion(
            action_code=task.action_code,
            messages=messages,
            quality_level=quality_level,
            priority=priority,
        )
        return ContentResult.from_llm_result(result)
```

### 5.9 `promptfw` Template Naming Convention (OQ-1 — resolved inline)

Quality-level template variants use a **quality-band suffix**:

| Band | `quality_level` range | Suffix | Example |
|------|-----------------------|--------|---------|
| economy | 1–3 | `_economy` | `story_writing_economy` |
| balanced | 4–6 | `_balanced` | `story_writing_balanced` |
| premium | 7–9 | `_premium` | `story_writing_premium` |
| (default) | `None` / catch-all | none | `story_writing` |

Rules:
1. Every `action_code` **must** have a base template with no suffix (= catch-all fallback).
2. Quality-band variants are optional. If a variant does not exist, `authoringfw` falls back to the base template.
3. The suffix is derived from `quality_level` by the **consumer app or orchestrator** before calling `promptfw.render()` — not by `aifw`.

This resolves OQ-1. No separate ADR-096 is needed.

### 5.10 Consumer-App Tier Mapping Pattern

```python
# In any consumer app view or service — single line, no hardcoded map:
from aifw import get_quality_level_for_tier, QualityLevel

quality = get_quality_level_for_tier(user.subscription)
# Falls back to QualityLevel.BALANCED (5) if tier not in DB
```

---

## 6. Complete Data Flow Example

```
travel-beat: user.subscription = "premium"

quality = get_quality_level_for_tier("premium")  # DB → 8

authoringfw.execute(StoryRequest(action_code="story_writing"), quality_level=8)
    │
    ├─ get_action_config("story_writing", quality_level=8, priority=None)
    │   Redis cache MISS → DB lookup cascade:
    │   Step 1: (story_writing, 8, None=priority) → quality_level=8, priority IS NULL
    │   → HIT: model=anthropic/claude-sonnet-4-20250514, template="story_writing_premium"
    │   → cached 300s
    │
    ├─ promptfw.render("story_writing_premium", context={title, genre, outline, …})
    │   └─ messages: [
    │       {role: "system", content: "You are a professional novelist…"},
    │       {role: "user",   content: "Write chapter 3… [2400 tokens context]"}
    │     ]
    │
    └─ sync_completion("story_writing", messages, quality_level=8)
        └─ LLMResult(
               content="… chapter text …",
               model="anthropic/claude-sonnet-4-20250514",
               input_tokens=2400, output_tokens=1800,
               latency_ms=4200, success=True
           )
        └─ AIUsageLog(
               action="story_writing",
               model="claude-sonnet-4-20250514",
               quality_level=8,          ← dedicated column (OQ-2 resolved)
               user=<premium_user>,
               cost_usd=0.054
           )
```

---

## 7. Consequences

### 7.1 Positive

- **Zero breaking changes** — all existing `sync_completion()` call sites work unchanged
- **DB-driven end-to-end** — models, templates, *and* tier→quality mappings are admin-editable at runtime
- **Single control variable** — `quality_level` (1–9) drives both prompt complexity and model quality
- **Deterministic lookup** — partial unique indexes guarantee exactly one row per (code, ql, priority) combination
- **Cached** — `get_action_config()` and `get_quality_level_for_tier()` hit Redis; DB load is negligible
- **Full cost transparency** — `AIUsageLog.quality_level` dedicated column enables direct SQL cost-per-tier analytics
- **Package independence preserved** — `aifw` and `promptfw` remain independently deployable
- **Explicit priority** — no hidden auto-derivation; caller controls priority or leaves `None` for catch-all
- **Groq/Together AI leverage** — `priority="fast"` enables sub-second responses without model hardcoding

### 7.2 Negative

- **`AIActionType` row count grows** — full configuration: 20 action codes × 3 quality bands × 3 priorities = up to 180 rows. Manageable with `init_bfagent_aifw_config` seeding; Django Admin list view requires pagination.
- **`iil-aifw` 0.6.0 migration required** — three new nullable columns + two new tables + four partial indexes. Backwards-compatible, but container restart required per consumer app.
- **`authoringfw` refactoring** — must adopt `BaseContentOrchestrator`; existing hardcoded template keys migrate to DB entries.
- **`check_aifw_config` extension** — must be extended to verify quality-level entries and `TierQualityMapping` seeds.
- **Redis dependency strengthened** — `get_action_config()` caching assumes Redis is available (already platform standard per ADR-045).

---

## 8. Migration Path

| Phase | Action | Repo | Target | Breaking? |
|-------|--------|------|--------|-----------|
| 1 | Add nullable columns, `TierQualityMapping`, partial indexes, CHECK constraint | `aifw` | 0.6.0 | No |
| 1 | Implement `_lookup_cascade()` + `get_action_config()` + `get_quality_level_for_tier()` | `aifw` | 0.6.0 | No |
| 1 | Export `QualityLevel`, `get_action_config`, `get_quality_level_for_tier` from `aifw.__init__` | `aifw` | 0.6.0 | No |
| 1 | Add `quality_level` dedicated column to `AIUsageLog` | `aifw` | 0.6.0 | No |
| 2 | Seed `TierQualityMapping` + quality-level `AIActionType` rows | `bfagent` | next | No |
| 2 | Extend `check_aifw_config` to verify quality-level + tier mapping entries | `bfagent` | next | No |
| 3 | Add quality-band `promptfw` template variants for key action codes | `promptfw` | 0.6.x | No |
| 4 | Adopt `BaseContentOrchestrator` + `get_action_config()` | `authoringfw` | next | No |
| 5 | Replace `TIER_QUALITY_MAP` with `get_quality_level_for_tier()` | all consumer apps | — | No |

**Phase 1 is a prerequisite for all others.** Phases 2–5 proceed in parallel after Phase 1 is deployed.

---

## 9. Testing Requirements (ADR-057)

Per ADR-057 (Four-Level Test Strategy), the following tests are required before Phase 1 is merged:

| Level | Test | Location |
|-------|------|---------|
| Unit | `_lookup_cascade()` — all 4 cascade steps, `ConfigurationError` on miss | `aifw/tests/test_service.py` |
| Unit | `get_quality_level_for_tier()` — hit, miss (fallback to BALANCED), inactive | `aifw/tests/test_service.py` |
| Unit | `QualityLevel` constants — values correct | `aifw/tests/test_constants.py` |
| Integration | Partial unique indexes — duplicate catch-all row rejected by DB | `aifw/tests/test_models.py` |
| Integration | Cache invalidation on `AIActionType.save()` | `aifw/tests/test_cache.py` |
| Contract | `get_action_config()` return shape matches `ActionConfig` TypedDict | `aifw/tests/test_contracts.py` |
| Management | `check_aifw_config` detects missing `TierQualityMapping` rows | `bfagent/tests/test_check_aifw_config.py` |

---

## 10. Open Questions

| ID | Question | Status | Tracking |
|----|----------|--------|---------|
| OQ-1 | `promptfw` template naming convention | **Resolved inline** — §5.9 | — |
| OQ-2 | `quality_level` dedicated column in `AIUsageLog`? | **Resolved** — yes, dedicated column | Phase 1 |
| OQ-3 | `authoringfw` scope ADR for Research + Analysis? | Open | → ADR-096 |

---

## 11. References

- [ADR-027: Shared Backend Services](ADR-027-shared-backend-services.md) — `aifw` as platform LLM execution framework
- [ADR-043: AI-Assisted Development](ADR-043-ai-assisted-development.md) — API stability requirement driving backwards compatibility
- [ADR-050: Platform Decomposition](ADR-050-platform-decomposition-hub-landscape.md) — package landscape; domain separation preventing authoringfw gateway anti-pattern
- [ADR-057: Four-Level Test Strategy](ADR-057-platform-test-strategy.md) — test requirements (§9)
- [ADR-068: Adaptive Model Routing](ADR-068-adaptive-model-routing.md) — agent-tier routing (orthogonal — see §2 for boundary definition)
- [ADR-084: Model Registry](ADR-084-model-registry-dynamic-llm-routing.md) — predecessor dynamic routing concept
- [ADR-089: bfagent-llm LiteLLM Architecture](ADR-089-bfagent-llm-litellm-db-driven-architecture.md) — DB-driven model routing; this ADR amends §4 (AIActionType schema)
- [ADR-093: AI Config App](ADR-093-ai-config-app.md) — `AIActionType` as shared Django app; this ADR extends the model
- [ADR-045: Secrets & Environment Management](ADR-045-secrets-management.md) — Redis as platform cache standard
- `iil-aifw`: https://github.com/achimdehnert/aifw
- `iil-promptfw`: https://github.com/achimdehnert/promptfw
- `iil-authoringfw`: https://github.com/achimdehnert/authoringfw
- External review: `platform/docs/adr/inputs/REVIEW-ADR-095.md` (2026-03-02)
