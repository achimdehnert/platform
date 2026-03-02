---
id: ADR-095
title: "aifw Quality-Level Routing — Multi-Dimensional LLM Dispatch with Prompt-Template Coordination"
status: accepted
date: 2026-03-02
author: Achim Dehnert
owner: Achim Dehnert
scope: Platform-wide (aifw, promptfw, authoringfw, all consumer apps)
tags: [llm, routing, quality, aifw, promptfw, authoringfw, api-design, backwards-compatibility]
related: [ADR-027, ADR-043, ADR-050, ADR-057, ADR-084, ADR-089, ADR-093]
last_verified: 2026-03-02
---

# ADR-095: aifw Quality-Level Routing — Multi-Dimensional LLM Dispatch with Prompt-Template Coordination

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-03-02 |
| Author | Achim Dehnert |
| Scope | `aifw`, `promptfw`, `authoringfw`, `bfagent`, `travel-beat`, `weltenhub`, `pptx-hub`, `risk-hub` |
| Related | ADR-027 (Shared Backend Services), ADR-043 (AI-Assisted Dev), ADR-050 (Platform Decomposition), ADR-084 (Model Registry), ADR-089 (bfagent-llm LiteLLM), ADR-093 (AI Config App) |

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
| `promptfw` | Prompt template engine | Template naming convention (OQ-1) |
| `authoringfw` | Content orchestration (Writing, Research, Analysis) | Adopt `get_action_config()` API |
| `bfagent` | Book Factory — primary consumer | tier → quality_level resolution |
| `travel-beat` | DriftTales travel stories | tier → quality_level resolution |
| `weltenhub` | Weltenforger story universe | tier → quality_level resolution |
| `pptx-hub` | Presentation Studio | tier → quality_level resolution |
| `risk-hub` | Occupational safety SaaS | tier → quality_level resolution |

---

## 2. Decision Drivers

- **Backwards compatibility is non-negotiable** — zero breaking changes to existing `sync_completion()` call sites across 8 repos
- **DB-driven configuration** — model and template assignments must be changeable via Django Admin without code deployment
- **Single control variable** — one parameter (`quality_level`) must drive both prompt complexity and model quality; dual configuration is a maintenance liability
- **Package independence** — `promptfw` and `aifw` must remain independently deployable without circular imports
- **Transparency** — every LLM call must be logged with the resolved model and quality level for cost attribution per user tier
- **Incrementalism** — implementation phased across packages; consumer apps adopt at their own pace

---

## 3. Considered Options

### Option 1 — Status quo: action_code suffixes
Add quality variants as separate `action_code` entries: `story_writing_premium`, `story_writing_free`, `story_writing_fast`.

**Assessment:** Pollutes the `action_code` namespace. 20 codes × 3 tiers × 2 priorities = 120 codes with no structure. `check_aifw_config` becomes unmanageable. Speed preference cannot be expressed orthogonally to quality. **Rejected.**

### Option 2 — Per-user model override in DB
Store a `preferred_model_id` on the user or subscription object. Consumer apps pass the model directly.

**Assessment:** Granularity is wrong — per-user is too fine for infrastructure-level routing. Requires all consumer apps to resolve model IDs, coupling them to `aifw` internals. Admin overhead scales with user count. **Rejected.**

### Option 3 — Separate `routing-fw` package
Extract routing logic into a new `routing-fw` package between consumer apps and `aifw`.

**Assessment:** Adds a fourth package dependency to every consumer app. Routing is inherently `aifw`'s responsibility. Unnecessary indirection. **Rejected.**

### Option 4 — `authoringfw` as universal LLM gateway
All LLM calls, including from non-writing apps, are routed through `authoringfw`.

**Assessment:** Creates a wrong cross-domain dependency. `risk-hub` (occupational safety) would depend on `authoringfw` (content creation). Violates domain separation established in ADR-050. **Rejected.**

### Option 5 — Extend `sync_completion` with `quality_level` + `priority`; extend `AIActionType` with `quality_level`, `priority`, `prompt_template_key` *(chosen)*

**Assessment:** Fully backwards-compatible (all new parameters default to `None`). Single `quality_level` integer drives both model selection and prompt template selection. `prompt_template_key` stored as a plain string — no cross-package import. DB-driven. Incrementally adoptable. **Accepted.**

---

## 4. Decision

### 4.1 Extended `sync_completion` API

The public API of `aifw.sync_completion()` is extended with two optional parameters, both defaulting to `None`:

```python
# Existing call sites — unchanged, zero migration required:
result = sync_completion(action_code="story_writing", messages=[...])

# Extended call — all new parameters are optional with None defaults:
result = sync_completion(
    action_code="story_writing",
    messages=[...],
    quality_level=7,      # int | None, default=None
    priority="quality",   # Literal["fast","balanced","quality"] | None, default=None
)
```

**`quality_level` semantics (1–9 integer scale):**

| Range | Label | Target model tier | Typical use case |
|-------|-------|-------------------|-----------------|
| 1–3 | Economy | Together AI Qwen, OpenRouter Mistral Nemo, Groq Llama | Freemium users, UI autocomplete, bulk metadata extraction |
| 4–6 | Balanced | GPT-4o-mini, Gemini 2.0 Flash, Llama 3.3 70B | Pro users, standard generation tasks |
| 7–9 | Premium | GPT-4o, Claude Sonnet 4, Claude Opus | Premium users, chapter export, editorial quality |
| `None` | Catch-all | Current default model | All existing call sites — unchanged behavior |

**`priority` semantics:**

| Value | Meaning | Provider preference |
|-------|---------|-------------------|
| `"fast"` | Minimise latency | Groq (< 500 ms P50), Together AI Turbo (~1 s) |
| `"balanced"` | Default trade-off | OpenAI, Google, OpenRouter |
| `"quality"` | Maximise output quality at given level | Anthropic, OpenAI GPT-4o |
| `None` | Catch-all | Current default — unchanged behavior |

### 4.2 Extended `AIActionType` Model

Three new nullable columns are added to `aifw.AIActionType`:

```
AIActionType
├── code                  VARCHAR NOT NULL   — e.g. "story_writing"
├── name                  VARCHAR NOT NULL
├── description           TEXT
├── quality_level         INTEGER NULL       — 1-9 or NULL (catch-all)          ← NEW
├── priority              VARCHAR(16) NULL   — "fast"|"balanced"|"quality"|NULL  ← NEW
├── prompt_template_key   VARCHAR(128) NULL  — promptfw template key             ← NEW
├── default_model         FK → LLMModel NOT NULL
├── fallback_model        FK → LLMModel NULL
├── max_tokens            INTEGER NOT NULL
├── temperature           FLOAT NOT NULL
├── is_active             BOOLEAN NOT NULL
└── budget_per_day        DECIMAL NULL
```

**Unique constraint:** `UNIQUE (code, quality_level, priority)` — enforced at DB and Django Admin level.

**Null semantics:** `NULL` in `quality_level` or `priority` means "catch-all" — matches any caller value for that dimension. Existing rows with both `NULL` continue to function exactly as today.

### 4.3 Lookup Cascade

When `sync_completion(action_code, quality_level, priority)` is called, the following cascade is applied in order. The **first matching row wins**:

```
1. Exact match:    WHERE code=X AND quality_level=Q AND priority=P
2. Level match:    WHERE code=X AND quality_level=Q AND priority IS NULL
3. Priority match: WHERE code=X AND quality_level IS NULL AND priority=P
4. Catch-all:      WHERE code=X AND quality_level IS NULL AND priority IS NULL
```

If no row is found at level 4, a `ConfigurationError` is raised (catch-all must always exist — enforced by `check_aifw_config`).

### 4.4 New Public API: `get_action_config()`

A new function `get_action_config()` is exported from `aifw`, returning the fully resolved configuration dict including `prompt_template_key`:

```python
from aifw import get_action_config

config = get_action_config(
    action_code="story_writing",
    quality_level=8,
    priority="quality",
)
# Returns TypedDict:
# {
#   "action_id":           14,
#   "model_id":            3,
#   "model":               "anthropic/claude-sonnet-4-20250514",
#   "provider":            "anthropic",
#   "base_url":            "",
#   "api_key_env_var":     "ANTHROPIC_API_KEY",
#   "prompt_template_key": "story_writing_detailed",   # or None
#   "max_tokens":          4096,
#   "temperature":         0.8,
# }
```

`prompt_template_key` is a plain string. `aifw` stores it but **never imports `promptfw`**. The caller passes it to `promptfw.render()`. This preserves full package independence.

### 4.5 Package Dependency Graph

```
promptfw    deps: jinja2, pyyaml
            (no aifw dependency — independently deployable)
    │
    │  prompt_template_key: plain string passed by caller
    │
aifw        deps: Django, litellm
            (no promptfw dependency — independently deployable)
    │
    │  get_action_config() + sync_completion()
    ▼
authoringfw deps: aifw, promptfw
            (content workflow orchestrator — Writing, Research, Analysis)
    │
    │  quality_level resolved from user tier by consumer app
    ▼
consumer-app (travel-beat, bfagent, weltenhub, …)
```

No circular dependencies exist or are introduced by this ADR.

### 4.6 `authoringfw` Scope and Orchestration Pattern

`authoringfw` is the platform's **content workflow orchestrator**, covering three domains:

| Domain | Examples |
|--------|---------|
| **Writing** | Chapter generation, outline, character creation, world-building |
| **Research** | Fact-checking, source synthesis, knowledge extraction |
| **Analysis** | Content analysis, style analysis, sentiment, readability scoring |

It is not a master that "controls" `aifw` or `promptfw` — it is a domain orchestrator that uses both as independent tools. Non-content apps (`risk-hub`, `pptx-hub`) call `aifw` directly without an `authoringfw` dependency.

Canonical `authoringfw` orchestration pattern:

```python
class BaseContentOrchestrator:
    def execute(self, task: ContentTask, quality_level: int = 5) -> ContentResult:
        # Step 1 — resolve model + template from aifw DB (single DB call)
        config = get_action_config(
            action_code=task.action_code,
            quality_level=quality_level,
            priority="quality" if quality_level >= 7 else "balanced",
        )

        # Step 2 — render prompt via promptfw using template key from config
        template_key = config.get("prompt_template_key") or task.action_code
        messages = promptfw.render(template_key, context=task.to_context())

        # Step 3 — execute LLM call (model already resolved in step 1)
        result = sync_completion(
            action_code=task.action_code,
            messages=messages,
            quality_level=quality_level,
        )
        return ContentResult.from_llm_result(result)
```

### 4.7 Consumer-App Tier Mapping

The mapping from user subscription tier to `quality_level` lives exclusively in the consumer app. `aifw` is tier-agnostic.

```python
# Canonical pattern — implement once per consumer app:
TIER_QUALITY_MAP: dict[str, int] = {
    "premium": 8,
    "pro":     5,
    "freemium": 2,
}

def get_quality_level(user) -> int:
    return TIER_QUALITY_MAP.get(getattr(user, "subscription", None), 5)
```

---

## 5. Complete Data Flow Example

```
travel-beat: user.subscription = "premium" → quality_level = 8

authoringfw.execute(StoryRequest(action_code="story_writing"), quality_level=8)
    │
    ├─ get_action_config("story_writing", quality_level=8, priority="quality")
    │   └─ DB lookup cascade:
    │       1. (story_writing, 8, "quality") → HIT
    │          model:               anthropic/claude-sonnet-4-20250514
    │          prompt_template_key: "story_writing_detailed"
    │          max_tokens: 4096,    temperature: 0.8
    │
    ├─ promptfw.render("story_writing_detailed", context={title, genre, outline, …})
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
               quality_level=8,
               user=<premium_user>,
               cost_usd=0.054
           )
```

---

## 6. Consequences

### 6.1 Positive

- **Zero breaking changes** — all existing `sync_completion()` call sites work unchanged without any modification
- **Single control variable** — `quality_level` (1–9) drives both prompt complexity (via `prompt_template_key`) and model quality simultaneously; no dual configuration
- **DB-driven without deployments** — model and template assignments per quality level are editable in Django Admin at runtime
- **Full cost transparency** — `AIUsageLog` records `quality_level` per call; cost-per-tier analysis is directly queryable via SQL
- **Package independence preserved** — `aifw` and `promptfw` remain independently deployable; `prompt_template_key` is a plain string, never a FK or import
- **Incremental adoption** — consumer apps adopt `quality_level` at their own pace; catch-all entries guarantee continuous operation during migration
- **Groq/Together AI leverage** — `priority="fast"` enables sub-second responses for latency-sensitive UI interactions without model hardcoding

### 6.2 Negative

- **`AIActionType` row count grows** — full configuration: 20 action codes × 3 quality tiers × 2 priorities = up to 120 rows. Manageable with `init_bfagent_aifw_config` seeding, but Django Admin list view requires pagination.
- **`iil-aifw` 0.6.0 migration required** — three new nullable columns need a Django migration. Backwards-compatible (nullable, no default), but a container restart is required per consumer app after upgrade.
- **`authoringfw` refactoring** — must adopt `BaseContentOrchestrator` + `get_action_config()` pattern; existing hardcoded template keys must be migrated to DB entries.
- **`promptfw` naming convention** — quality-level template variants need a platform-wide naming convention. Not defined in this ADR — tracked as OQ-1 → ADR-096.
- **`check_aifw_config` extension** — the validation management command in `bfagent` must be extended to verify quality-level entries; current implementation validates catch-all entries only.

---

## 7. Migration Path

| Phase | Action | Repo | Target version | Breaking? |
|-------|--------|------|----------------|-----------|
| 1 | Add `quality_level`, `priority`, `prompt_template_key` nullable columns | `aifw` | 0.6.0 | No |
| 1 | Implement 4-level lookup cascade in `service.py` | `aifw` | 0.6.0 | No |
| 1 | Export `get_action_config()` from `aifw.__init__` | `aifw` | 0.6.0 | No |
| 2 | Extend `init_bfagent_aifw_config` with quality-level `AIActionType` seeds | `bfagent` | next | No |
| 2 | Extend `check_aifw_config` to verify quality-level entries | `bfagent` | next | No |
| 3 | Add quality-level `promptfw` template variants for key action codes | `promptfw` | 0.6.x | No |
| 4 | Adopt `BaseContentOrchestrator` + `get_action_config()` pattern | `authoringfw` | next | No |
| 5 | Add `get_quality_level(user)` + pass to `sync_completion` | `travel-beat` | next | No |
| 5 | Same for all remaining consumer apps | all others | — | No |

All phases are independent. **Phase 1 is a prerequisite for all others.** Phases 2–5 can proceed in parallel once Phase 1 is deployed and `iil-aifw==0.6.0` is available on PyPI/GitHub.

---

## 8. Open Questions

| ID | Question | Owner | Tracking |
|----|----------|-------|---------|
| OQ-1 | `promptfw` template naming convention for quality-level variants — suffix `_detailed`/`_standard`/`_fast`, or separate namespace per level? | Achim Dehnert | → ADR-096 |
| OQ-2 | Should `quality_level` be stored as a dedicated column in `AIUsageLog` for SQL cost-per-tier analytics, or derived from `AIActionType` join? | Achim Dehnert | → `aifw` 0.6.0 implementation |
| OQ-3 | `authoringfw` scope formalisation — separate ADR for Research + Analysis orchestration patterns beyond Writing? | Achim Dehnert | → ADR-097 |

---

## 9. References

- [ADR-027: Shared Backend Services](ADR-027-shared-backend-services.md) — established `aifw` as the platform LLM execution framework
- [ADR-043: AI-Assisted Development](ADR-043-ai-assisted-development.md) — rapid change cycle requirements motivating API stability
- [ADR-050: Platform Decomposition](ADR-050-platform-decomposition-hub-landscape.md) — package landscape defining `aifw`, `promptfw`, `authoringfw` as independent packages
- [ADR-084: Model Registry](ADR-084-model-registry-dynamic-llm-routing.md) — dynamic LLM model routing (predecessor concept)
- [ADR-089: bfagent-llm LiteLLM Architecture](ADR-089-bfagent-llm-litellm-db-driven-architecture.md) — DB-driven model routing in `aifw`
- [ADR-093: AI Config App](ADR-093-ai-config-app.md) — `AIActionType` model as shared Django app
- `iil-aifw` package: https://github.com/achimdehnert/aifw
- `iil-promptfw` package: https://github.com/achimdehnert/promptfw
- `iil-authoringfw` package: https://github.com/achimdehnert/authoringfw
