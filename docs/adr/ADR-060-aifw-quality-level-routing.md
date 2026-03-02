# ADR-060: aifw Quality-Level Routing API

**Status:** Accepted  
**Date:** 2026-03-02  
**Repos affected:** `aifw`, `promptfw`, `authoringfw`, `bfagent`, `travel-beat`, `weltenhub`, `pptx-hub`, `risk-hub`

---

## Context

All consumer apps call `aifw.sync_completion(action_code=..., messages=...)` to execute LLM tasks.  
The current `AIActionType` maps `action_code → (default_model, fallback_model)` — a single fixed mapping.

**Problems this ADR solves:**

1. **Tier-based quality:** Premium users get GPT-4o/Claude; freemium gets Qwen/Llama.
2. **Speed vs. quality:** Some use cases need fast (Groq), others need max quality (Claude).
3. **Prompt complexity:** Complex tasks need better models AND more sophisticated prompts. `promptfw` template selection and `aifw` model selection must be driven by the same `quality_level`.
4. **Rapid change cycles:** API must be stable while models change frequently.
5. **Template-key coordination:** Orchestrators (authoringfw) must know which `promptfw` template to use per action + quality level — currently hardcoded, should be DB-driven.

---

## Package Dependency Graph

```
promptfw    deps: jinja2, pyyaml          (no aifw dependency — safe)
aifw        deps: Django, litellm         (no promptfw dependency — safe)
authoringfw deps: aifw, promptfw          (orchestrates both)
consumer    deps: authoringfw + aifw      (for writing/research/analysis tasks)
```

No circular dependencies. `AIActionType.prompt_template_key` is a plain string — `aifw` never imports `promptfw`.

---

## Decision

### 1. Extend `sync_completion` API (backwards-compatible)

```python
# Current — unchanged:
result = sync_completion(action_code="story_writing", messages=[...])

# Extended — all new params optional with None defaults:
result = sync_completion(
    action_code="story_writing",
    messages=[...],
    quality_level=7,        # int 1-9, default=None (catch-all, current behavior)
    priority="quality",     # "fast"|"balanced"|"quality", default=None (catch-all)
)
```

**quality_level contract:**
- `None` → catch-all entry (zero breaking change)
- `1..3` → cheap/fast (Together AI, Groq, OpenRouter open models)
- `4..6` → balanced (GPT-4o-mini, Gemini Flash, Llama 3.3 70B)
- `7..9` → premium (GPT-4o, Claude Sonnet, Claude Opus)

**priority contract:**
- `"fast"` → lowest-latency provider (Groq < 500ms, Together AI Turbo ~1s)
- `"balanced"` → default tradeoff
- `"quality"` → highest-quality model at given level

### 2. Extend `AIActionType` DB model

```
AIActionType
├── code                 VARCHAR  — e.g. "story_writing", "research_assistant"
├── quality_level        INT NULL — 1-9 or NULL (catch-all)
├── priority             VARCHAR NULL — "fast"|"balanced"|"quality"|NULL
├── prompt_template_key  VARCHAR NULL — promptfw template key, e.g. "story_writing_detailed"
├── default_model        FK → LLMModel
├── fallback_model       FK → LLMModel (nullable)
├── max_tokens           INT
├── temperature          FLOAT
└── is_active            BOOL
```

**`prompt_template_key`** is a plain string (not a FK). It is passed to `promptfw.render()` by the caller. `aifw` stores it but never imports `promptfw`. The caller (authoringfw / consumer-app) reads it from the returned config and uses it for prompt rendering.

**Lookup logic (cascade):**
1. Exact: `(code, quality_level, priority)`
2. Partial: `(code, quality_level, NULL)`
3. Partial: `(code, NULL, priority)`
4. Catch-all: `(code, NULL, NULL)` ← always exists, current behavior

**Unique constraint:** `UNIQUE (code, quality_level, priority)`

### 3. `check_action_code()` returns config including template key

```python
# New helper — returns full config dict:
config = get_action_config(
    action_code="story_writing",
    quality_level=8,
    priority="quality",
)
# config = {
#   "model": "anthropic/claude-sonnet-4-20250514",
#   "prompt_template_key": "story_writing_detailed",
#   "max_tokens": 4096,
#   "temperature": 0.8,
# }
```

---

## Orchestrator Scope: `authoringfw`

`authoringfw` orchestrates **Writing + Research + Analysis** — not just writing.

```
authoringfw scope:
├── Writing:   ChapterWriter, OutlineWriter, CharacterBuilder
├── Research:  ResearchOrchestrator, FactChecker
└── Analysis:  ContentAnalyzer, StyleAnalyzer, SentimentAnalyzer
```

It is **not** a master that "triggers" `promptfw` and `aifw` — it is a **domain orchestrator** that uses both as tools:

```python
# authoringfw — generic pattern for all task types:
class BaseContentOrchestrator:
    def execute(self, task, quality_level: int = 5) -> ContentResult:
        # 1. Get action config from aifw (includes template key)
        config = get_action_config(
            action_code=task.action_code,
            quality_level=quality_level,
        )
        # 2. Render prompt via promptfw using template from config
        messages = promptfw.render(
            config["prompt_template_key"] or task.action_code,
            context=task.to_context(),
        )
        # 3. Execute LLM call
        result = sync_completion(
            action_code=task.action_code,
            messages=messages,
            quality_level=quality_level,
        )
        return ContentResult.from_llm_result(result)
```

**Non-writing apps** (risk-hub, pptx-hub) call `aifw` directly — no `authoringfw` dependency needed.

---

## Consumer-App Pattern

```python
# In any consumer-app view/service:
def get_quality_level(user) -> int:
    tiers = {"premium": 8, "pro": 5, "freemium": 2}
    return tiers.get(user.subscription, 5)

# Writing/Research/Analysis → via authoringfw:
result = authoringfw.execute(
    task=ChapterRequest(...),
    quality_level=get_quality_level(request.user),
)

# Simple tasks → direct aifw:
result = sync_completion(
    action_code="book_description",
    messages=messages,
    quality_level=get_quality_level(request.user),
)
```

---

## Data Flow

```
consumer-app
    │  user.tier → quality_level=8
    ▼
authoringfw.execute(task, quality_level=8)
    │
    ├─► aifw.get_action_config("story_writing", quality_level=8)
    │       └─► AIActionType lookup → {model: claude-sonnet-4, template: "story_writing_detailed"}
    │
    ├─► promptfw.render("story_writing_detailed", context)
    │       └─► messages: [system_prompt, user_prompt]  (complex, structured)
    │
    └─► aifw.sync_completion("story_writing", messages, quality_level=8)
            └─► LLMResult (claude-sonnet-4)
```

---

## Consequences

### Positive
- Zero breaking changes — all existing calls work unchanged
- Single `quality_level` drives both prompt complexity AND model quality
- `prompt_template_key` DB-driven — no code deploy needed to change templates
- `authoringfw` scope covers Writing + Research + Analysis uniformly
- `promptfw` and `aifw` remain independently deployable (no cross-dependency)
- `AIUsageLog` records model + quality_level → cost analysis per tier

### Negative
- `AIActionType` rows multiply (20 codes × 3 levels = ~60 rows)
- `aifw` 0.6.0 migration required (new columns)
- `authoringfw` must be updated to use `get_action_config()`
- `promptfw` template naming convention must be defined

---

## Migration Path

1. `iil-aifw` 0.6.0: `quality_level`, `priority`, `prompt_template_key` columns + lookup logic + `get_action_config()`
2. `iil-promptfw`: add quality-level template variants for key action codes
3. `authoringfw`: adopt `BaseContentOrchestrator` pattern with `get_action_config()`
4. `init_bfagent_aifw_config`: seed quality-level `AIActionType` entries with template keys
5. Consumer apps: `travel-beat` first — tier → quality_level resolution

---

## Alternatives Rejected

- **`authoringfw` as master hub:** Too tight coupling — non-writing apps would need wrong dependency.
- **action_code suffixes:** Pollutes namespace, no structured speed preference.
- **`aifw` imports `promptfw`:** Circular risk — rejected. Template key is a plain string only.
- **Separate `routing-fw`:** Unnecessary — `quality_level` parameter is sufficient.
