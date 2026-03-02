# ADR-060: aifw Quality-Level Routing API

**Status:** Accepted  
**Date:** 2026-03-02  
**Repos affected:** `aifw`, `bfagent`, `travel-beat`, `weltenhub`, `pptx-hub`, `risk-hub`

---

## Context

All consumer apps (bfagent, travel-beat, weltenhub, …) call `aifw.sync_completion(action_code=..., messages=...)` to execute LLM tasks. The current `AIActionType` model maps `action_code` → `(default_model, fallback_model)` — a single fixed mapping.

**Problems this ADR solves:**

1. **Tier-based quality:** Premium users in travel-beat should get GPT-4o or Claude Sonnet; freemium users get Qwen/Llama (cheaper). Currently impossible without code changes.
2. **Speed vs. quality trade-off:** Some use cases need fast responses (Groq, Together AI), others need maximum quality (Claude, GPT-4o). Not expressible via current API.
3. **Rapid change cycles:** AI-assisted development means frequent model upgrades. The API must be stable even as models change.

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
    quality_level=7,        # int 1-9, default=5 (balanced)
    priority="quality",     # "fast" | "balanced" | "quality", default="balanced"
)
```

**Contract:**
- `quality_level=None` (default) → use the catch-all `AIActionType` entry (current behavior)
- `quality_level=1..4` → prefer cheap/fast models (Together AI, Groq, OpenRouter open models)
- `quality_level=5..7` → balanced (GPT-4o-mini, Gemini Flash, Llama 3.3 70B)
- `quality_level=8..9` → premium (GPT-4o, Claude Sonnet, Claude Opus)
- `priority="fast"` → prefer Groq models regardless of quality_level
- `priority="quality"` → prefer highest-quality model available at that level

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

This ensures **full backwards compatibility** — existing entries with `quality_level=NULL, priority=NULL` are always found.

### 3. Unique constraint

```sql
UNIQUE (code, quality_level, priority)
```

Prevents duplicate routing rules. Django Admin enforces this.

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

## Consequences

### Positive
- **Zero breaking changes:** All existing `sync_completion()` calls work unchanged.
- **DB-driven:** Model assignments per quality level are editable in Django Admin without deploys.
- **Extensible:** New quality levels or priorities can be added without API changes.
- **App-agnostic:** travel-beat, bfagent, weltenhub all use the same API — only their tier→level mapping differs.
- **Transparent:** `AIUsageLog` records the actual model used, enabling cost analysis per quality level.

### Negative
- **DB entries multiply:** For 20 action codes × 3 quality levels = up to 60 `AIActionType` rows. Manageable.
- **aifw migration required:** New columns need a Django migration in `iil-aifw` (version 0.6.0).
- **Consumer apps must be updated** to pass `quality_level` — but this is additive, not breaking.

---

## Migration Path

1. `iil-aifw` 0.6.0: Add `quality_level` + `priority` columns (nullable, no default required)
2. Update `init_bfagent_aifw_config` to seed quality-level variants for key action codes
3. Update `check_aifw_config` to verify quality-level entries
4. Update `sync_completion` lookup logic
5. Consumer apps (travel-beat first): add tier → quality_level resolution

---

## Alternatives Considered

### A: action_code suffixes (`story_writing_premium`, `story_writing_free`)
Rejected: pollutes action_code namespace, makes `check_aifw_config` hard to maintain, no structured way to express speed preference.

### B: Per-user model override in DB
Rejected: too granular, doesn't scale, admin overhead per user.

### C: Hardcode model in view
Rejected: requires code deploy for model changes, defeats aifw's purpose.

---

## Implementation Note

`priority="fast"` maps to providers with lowest P50 latency:
- `groq` (if available) → sub-500ms
- `together_ai` Turbo models → ~1s
- `openrouter` open models → ~2s

`priority="quality"` at level 8-9 maps to:
- `anthropic/claude-sonnet-4` or `openai/gpt-4o` depending on task type

The exact model assignments per `(code, quality_level, priority)` are configured in DB via Django Admin or `init_bfagent_aifw_config --force`.
