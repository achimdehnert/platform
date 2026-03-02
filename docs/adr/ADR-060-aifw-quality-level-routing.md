# ADR-060: aifw Quality-Level Routing API

**Status:** Accepted  
**Date:** 2026-03-02  
**Repos affected:** `aifw`, `promptfw`, `authoringfw`, `bfagent`, `travel-beat`, `weltenhub`, `pptx-hub`, `risk-hub`

---

## Context

All consumer apps (bfagent, travel-beat, weltenhub, …) call `aifw.sync_completion(action_code=..., messages=...)` to execute LLM tasks. The current `AIActionType` model maps `action_code` → `(default_model, fallback_model)` — a single fixed mapping.

**Problems this ADR solves:**

1. **Tier-based quality:** Premium users in travel-beat should get GPT-4o or Claude Sonnet; freemium users get Qwen/Llama (cheaper). Currently impossible without code changes.
2. **Speed vs. quality trade-off:** Some use cases need fast responses (Groq, Together AI), others need maximum quality (Claude, GPT-4o). Not expressible via current API.
3. **Prompt complexity:** Complex tasks require better models AND more sophisticated prompts. `promptfw` template selection and `aifw` model selection are currently independent — they should be driven by the same `quality_level`.
4. **Rapid change cycles:** AI-assisted development means frequent model upgrades. The API must be stable even as models change.

---

## Decision

### 1. Extend `sync_completion` API with optional parameters (backwards-compatible)

```python
# Current API — unchanged, still works:
result = sync_completion(action_code="story_writing", messages=[...])

# Extended API — all new params are optional with defaults:
result = sync_completion(
    action_code="story_writing",
    messages=[...],
    quality_level=7,        # int 1-9, default=None (catch-all)
    priority="quality",     # "fast" | "balanced" | "quality", default=None (catch-all)
)
```

**Contract:**
- `quality_level=None` (default) → use the catch-all `AIActionType` entry (current behavior, zero breaking change)
- `quality_level=1..3` → cheap/fast models (Together AI, Groq, OpenRouter open models)
- `quality_level=4..6` → balanced (GPT-4o-mini, Gemini Flash, Llama 3.3 70B)
- `quality_level=7..9` → premium (GPT-4o, Claude Sonnet, Claude Opus)
- `priority="fast"` → prefer low-latency providers (Groq < 500ms, Together AI Turbo)
- `priority="quality"` → prefer highest-quality model at that level

### 2. Extend `AIActionType` DB model

```
AIActionType
├── code              VARCHAR  — action identifier (e.g. "story_writing")
├── quality_level     INT NULL — 1-9 or NULL (catch-all)
├── priority          VARCHAR NULL — "fast"|"balanced"|"quality" or NULL (catch-all)
├── default_model     FK → LLMModel
├── fallback_model    FK → LLMModel (nullable)
├── max_tokens        INT
├── temperature       FLOAT
└── is_active         BOOL
```

**Lookup logic (priority order):**
1. Exact match: `(code, quality_level, priority)`
2. Partial match: `(code, quality_level, NULL)`
3. Partial match: `(code, NULL, priority)`
4. Catch-all: `(code, NULL, NULL)` ← current behavior, always exists

Full backwards compatibility — existing entries with `quality_level=NULL, priority=NULL` are always found.

### 3. Unique constraint

```sql
UNIQUE (code, quality_level, priority)
```

### 4. Consumer-app usage pattern

```python
# In a view/service, resolve quality_level from user tier:
def get_quality_level(user) -> int:
    if user.subscription == "premium":
        return 8
    elif user.subscription == "pro":
        return 5
    return 2  # freemium

# Call aifw:
result = sync_completion(
    action_code="story_writing",
    messages=messages,
    quality_level=get_quality_level(request.user),
    priority="balanced",
)
```

The tier → quality_level mapping lives in the **consumer app**, not in aifw. aifw is tier-agnostic.

---

## Package Orchestration Architecture

### Role of each package

```
promptfw     → "HOW to formulate?" — Template rendering, variable injection
              Input:  template_key + context + quality_level
              Output: messages: list[dict]  (ready for LLM)

aifw         → "WHO executes?" — Model routing + execution + logging
              Input:  action_code + messages + quality_level + priority
              Output: LLMResult

authoringfw  → "WHAT + WITH WHICH QUALITY?" — Writing workflow orchestration
              Input:  task (ChapterRequest, OutlineRequest, …) + quality_level
              Calls:  promptfw.render(...) → then aifw.sync_completion(...)
              Output: domain result (ChapterResult, OutlineResult, …)

consumer-app → "FOR WHOM?" — User tier → quality_level resolution
              Input:  request + user
              Calls:  authoringfw (for writing tasks) or aifw directly (simple tasks)
```

### `authoringfw` as Writing Orchestrator

`authoringfw` is the **only component that combines** prompt complexity and model quality for writing tasks:

```python
# authoringfw example — ChapterWriter:
class ChapterWriter:
    def write(self, request: ChapterRequest, quality_level: int = 5) -> ChapterResult:
        # 1. Select prompt template based on complexity + quality_level
        template_key = self._select_template(request, quality_level)
        messages = promptfw.render(template_key, context=request.to_context())

        # 2. Call aifw with matching quality_level
        result = sync_completion(
            action_code="chapter_generation",
            messages=messages,
            quality_level=quality_level,
            priority="quality" if quality_level >= 7 else "balanced",
        )
        return ChapterResult.from_llm_result(result)

    def _select_template(self, request, quality_level: int) -> str:
        if quality_level >= 7:
            return "chapter_generation_detailed"   # longer, more structured prompt
        elif quality_level >= 4:
            return "chapter_generation_standard"
        return "chapter_generation_fast"           # minimal prompt for speed
```

**Key insight:** `quality_level` drives **both** prompt selection (in `promptfw`) and model selection (in `aifw`) through the same single value. No separate coordination needed.

### `promptfw` role with quality_level

`promptfw` templates can optionally use `quality_level` as a variable — or the caller selects the template key based on level:

```python
# Option A: Template key varies by level (recommended)
template_key = f"story_writing_q{quality_level // 3}"  # q0, q1, q2, q3

# Option B: quality_level as template variable
messages = promptfw.render("story_writing", context={
    "quality_level": quality_level,
    "use_chain_of_thought": quality_level >= 7,
    ...
})
```

### Data flow diagram

```
consumer-app (travel-beat)
    │  user.tier → quality_level=8
    ▼
authoringfw.ChapterWriter.write(request, quality_level=8)
    │
    ├─► promptfw.render("chapter_generation_detailed", context)
    │       └─► messages: [system, user]  (complex, structured prompt)
    │
    └─► aifw.sync_completion(
            action_code="chapter_generation",
            messages=messages,
            quality_level=8,
            priority="quality"
        )
            └─► AIActionType lookup: (chapter_generation, 8, quality)
                    └─► LLMModel: anthropic/claude-sonnet-4
                            └─► LLMResult
```

### When to call `aifw` directly (without `authoringfw`)

Not all tasks need `authoringfw`. Simple, non-writing tasks call `aifw` directly:

```python
# Simple tasks — direct aifw call is correct:
sync_completion(action_code="book_description", messages=messages, quality_level=quality_level)
sync_completion(action_code="research_assistant", messages=messages)

# Complex writing tasks — go through authoringfw:
authoringfw.ChapterWriter().write(request, quality_level=quality_level)
```

---

## Consequences

### Positive
- **Zero breaking changes:** All existing `sync_completion()` calls work unchanged.
- **Single control variable:** `quality_level` drives both prompt complexity AND model quality — no dual-configuration.
- **DB-driven:** Model assignments per quality level editable in Django Admin without deploys.
- **Package separation:** `promptfw`, `aifw`, `authoringfw` remain independently deployable.
- **Cost transparency:** `AIUsageLog` records model used per quality level → cost analysis per user tier.

### Negative
- **DB entries multiply:** 20 action codes × 3 quality tiers = up to 60 `AIActionType` rows.
- **aifw migration required:** `iil-aifw` 0.6.0 needs new columns + lookup logic.
- **authoringfw must be updated** to accept + propagate `quality_level`.
- **promptfw template naming convention** needs to be defined (see Option A above).

---

## Migration Path

1. `iil-aifw` 0.6.0: `quality_level` + `priority` columns, updated `sync_completion` lookup
2. `promptfw`: optional — add quality-level template variants for key writing tasks
3. `authoringfw`: accept `quality_level` parameter, select templates + pass to aifw
4. `init_bfagent_aifw_config`: seed quality-level `AIActionType` entries
5. Consumer apps: `travel-beat` first — tier → quality_level in views/services

---

## Alternatives Considered

### A: `authoringfw` as single entry point (hub pattern)
All LLM calls go through `authoringfw`, which internally calls `promptfw` + `aifw`.
**Rejected:** Too tight coupling. Non-writing apps (risk-hub, pptx-hub) would have wrong dependency. `aifw` must remain callable directly.

### B: action_code suffixes (`story_writing_premium`, `story_writing_free`)
**Rejected:** Pollutes namespace, no structured speed preference, combinatorial explosion.

### C: Separate `routing-fw` package
**Rejected:** Unnecessary complexity. `quality_level` as a parameter is sufficient.

---

## Implementation Note

`priority="fast"` provider preference:
- `groq` → sub-500ms P50
- `together_ai` Turbo → ~1s
- `openrouter` open models → ~2s

`priority="quality"` at level 7-9:
- `anthropic/claude-sonnet-4` (creative writing)
- `openai/gpt-4o` (structured/analytical)

Model assignments per `(code, quality_level, priority)` configured in DB via Django Admin or `init_bfagent_aifw_config --force`.
