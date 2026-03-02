# aifw Integration -- Rules

> Glob-Activated: `**/services/*.py`, `**/llm_client.py`, `requirements.txt`, `apps/ai_services/**`
> ADR-089, ADR-093 -- DB-driven LLM routing via aifw package

## Import Pattern (MANDATORY)

```python
# CORRECT -- direct import from aifw
from aifw import sync_completion

result = sync_completion(
    action_code="your_action_code",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ],
    max_tokens=2000,
)
text = result.content if result.success else ""

# BANNED -- deprecated stub
from apps.ai_services.llm_service import sync_completion  # stub, remove this
import urllib.request  # raw HTTP to LLM API, never do this
import urllib.error    # raw HTTP to LLM API, never do this
```

## action_code Requirements (CRITICAL)

Every `action_code` passed to `sync_completion` MUST exist as an `AIActionType`
record in the database. Missing action codes cause silent fallback or errors at runtime.

**Before using a new action_code:**

```bash
# 1. Check if action_code exists
python manage.py shell -c "from aifw.models import AIActionType; print(AIActionType.objects.filter(code='your_code').exists())"

# 2. If missing -- seed it via management command
python manage.py init_aifw_config

# 3. Or add to your app's seed command / fixture
```

**Standard action_codes for bfagent:**

| Code | Usage |
|------|-------|
| `story_writing` | Chapter generation, narrative text |
| `chapter_generation` | Book chapter content |
| `project_enrichment` | Project metadata enrichment |
| `outline_generation` | Outline and structure generation |
| `character_generation` | Character descriptions |

## Migration Checklist (before deploy)

When adding/updating `aifw` in any repo:

```bash
# 1. Run aifw migrations
python manage.py migrate aifw

# 2. Seed initial config (idempotent)
python manage.py init_aifw_config

# 3. Verify action_codes exist for all usages
python manage.py shell -c "
from aifw.models import AIActionType
codes = AIActionType.objects.values_list('code', flat=True)
print(list(codes))
"
```

## LLMServiceWrapper / Legacy Pattern

If a class wraps LLM calls (e.g. `LLMServiceWrapper`), route through `aifw`:

```python
# CORRECT
class LLMServiceWrapper:
    def generate(self, prompt: str, max_tokens: int = 800) -> str:
        from aifw import sync_completion
        result = sync_completion(
            action_code="story_writing",
            messages=[
                {"role": "system", "content": "You are an expert writing assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return result.content if result.success else ""

# BANNED -- raw HTTP wrapper
class LLMServiceWrapper:
    def generate(self, prompt: str, max_tokens: int = 800) -> str:
        return _call_openai_chat(
            api_endpoint=self.llm.api_endpoint,  # raw HTTP
            api_key=self.llm.api_key,
            ...
        )
```

## BANNED Patterns

- `urllib.request.Request(...)` for LLM API calls
- `urllib.request.urlopen(...)` for LLM API calls
- `from apps.ai_services.llm_service import sync_completion` (deprecated stub)
- Passing `action_code` values not seeded in `AIActionType` DB table
- Hardcoded `api_endpoint` or `api_key` in LLM call functions
