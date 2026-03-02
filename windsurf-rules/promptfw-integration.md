# promptfw Integration — Rules

> Glob-Activated: `**/services/*.py`, `**/prompts/*.py`, `**/llm_client.py`, `requirements.txt`
> PyPI: `iil-promptfw>=0.5.1` — 5-layer Jinja2 prompt engine

## What promptfw Provides

| Export | Purpose |
|---|---|
| `PromptStack` | Assemble multi-layer prompt from templates |
| `PromptTemplate` | Single template definition (Pydantic model) |
| `RenderedPrompt` | Output of rendering — ready for `aifw` |
| `TemplateRegistry` | In-memory template store |
| `DjangoTemplateRegistry` | DB-backed registry (Django ORM) |
| `PromptRenderer` | Renders a `PromptStack` to `RenderedPrompt` |
| `get_writing_stack` | Pre-built stack for creative writing |
| `get_planning_stack` | Pre-built stack for story planning |
| `get_lektorat_stack` | Pre-built stack for editorial review |
| `extract_json` / `extract_field` | Parse structured LLM responses |

## Import Pattern (MANDATORY)

```python
# CORRECT — use promptfw for all structured prompt assembly
from promptfw import PromptStack, PromptRenderer, RenderedPrompt
from promptfw import get_writing_stack, get_planning_stack
from promptfw import extract_json, extract_field

# Combine with aifw for the full pipeline
from aifw import sync_completion

stack = get_writing_stack()
rendered: RenderedPrompt = PromptRenderer().render(stack, context={"title": "..."})
result = sync_completion(rendered)
text = result.content if result.success else ""

# BANNED — inline prompt assembly for complex prompts
system = f"You are a writer. Style: {style}. Rules: {rules}. World: {world}..."
messages = [{"role": "system", "content": system}, ...]
```

## 5-Layer Architecture

promptfw uses a strict 5-layer model. **Never collapse these into a single string.**

| Layer | `TemplateLayer` | Content |
|---|---|---|
| 1 | `SYSTEM` | Persona, role, constraints |
| 2 | `STYLE` | Tone, language, format rules |
| 3 | `CONTEXT` | World/story/character context |
| 4 | `TASK` | Concrete instruction |
| 5 | `OUTPUT` | Output format specification |

## Django Integration

```python
# CORRECT — DB-backed registry for Django projects
from promptfw import DjangoTemplateRegistry, BFAGENT_FIELD_MAP

registry = DjangoTemplateRegistry(field_map=BFAGENT_FIELD_MAP)
stack = registry.get_stack("writing_chapter")

# BANNED — hardcoded template strings in Django views/services
def generate_chapter(title: str) -> str:
    prompt = f"Write a chapter about {title}..."  # never in a service
```

## Refactoring Trigger Patterns

| Found Pattern | Replace With |
|---|---|
| Multi-line `f-string` system prompt (>3 lines) | `get_writing_stack()` or custom `PromptStack` |
| `messages = [{"role": "system", ...}, {"role": "user", ...}]` inline | `PromptRenderer().render(stack, context)` |
| `json.loads(result.content)` without error handling | `extract_json(result.content)` |
| `result.content.split("FIELD:")` | `extract_field(result.content, "FIELD")` |
| Prompt strings stored in Django model fields raw | `DjangoTemplateRegistry` |

## BANNED

- Inline f-string prompts with >3 variables in service functions
- `json.loads()` directly on LLM output (use `extract_json`)
- Duplicating layer logic that `PromptStack` already handles
- Storing raw prompt strings in code instead of registry
