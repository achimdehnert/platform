---
trigger: always_on
---

# iil Package Ecosystem — Usage Rules

> Always-On Rule — loaded in every Cascade session.
> Applies to: ALL repos (bfagent, travel-beat, weltenhub, pptx-hub, risk-hub,
>   cad-hub, trading-hub, mcp-hub, coach-hub, dev-hub, 137-hub, odoo-hub,
>   wedding-hub, aifw, authoringfw, promptfw, weltenfw, nl2cad, outlinefw,
>   researchfw, illustration-fw, learnfw, riskfw, infra-deploy)
> Source: PyPI account `iildehnert`

## Package Registry

| PyPI Package | Import As | Purpose | Use When |
|---|---|---|---|
| `aifw>=0.5.0` | `from aifw import ...` | LLM completions, DB-driven routing | Any LLM call |
| `iil-promptfw>=0.5.1` | `from promptfw import ...` | Jinja2 5-layer prompt templates | Prompt rendering |
| `iil-authoringfw>=0.3.0` | `from authoringfw import ...` | Creative writing domain schemas | Story/character/world models |
| `iil-weltenfw>=0.1.0` | `from weltenfw import ...` | WeltenHub REST client + Pydantic schemas | WeltenHub API calls |
| `iil-nl2cadfw>=0.1.0` | `from nl2cadfw import ...` | IFC/DXF parsing, DIN 277, GAEB, NLP-to-CAD | CAD/BIM processing |
| `iil-outlinefw>=0.3.2` | `from outlinefw import ...` | Story outline generation (5 frameworks) | Scene/outline planning in writing/story apps |
| `iil-researchfw>=0.6.0` | `from iil_researchfw import ...` | Academic search, citations, AI analysis | Research features in any Django app |
| `iil-illustrationfw>=0.2.0` | `from illustrationfw import ...` | Provider-agnostic image generation (DALL·E, SD) | Illustration pipelines |
| `iil-learnfw>=0.5.4` | `from iil_learnfw import ...` | Django LMS — quizzes, grading, certificates | Learning/training platforms |
| `riskfw>=0.1.0` | `from riskfw import ...` | Safety calculations (TRGS 721/722, ATEX, EN 1127-1) | Explosion protection, risk-hub |
| `iil-testkit>=0.4.0` | `from iil_testkit import ...` | Test fixtures, assertions, smoke testing | Testing in ALL Django repos |

## Publishing New Versions — PYPI_API_TOKEN Location

`PYPI_API_TOKEN` ist **NUR in GitHub Actions Secrets** hinterlegt — NICHT lokal.

**Korrekte Publish-Methode (autonom, kein lokaler Token nötig):**

```bash
# 1. Workflow im platform-Repo triggern — nutzt platform's PYPI_API_TOKEN Secret
TOKEN=$(cat ~/.secrets/github_PAT)
curl -s -X POST \
  -H "Authorization: token ${TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/achimdehnert/platform/actions/workflows/publish-iil-testkit.yml/dispatches" \
  -d '{"ref":"main","inputs":{"dry_run":"false"}}'

# 2. Status prüfen
sleep 30
curl -s -H "Authorization: token ${TOKEN}" \
  "https://api.github.com/repos/achimdehnert/platform/actions/runs?per_page=3" \
  | python3 -c "import json,sys; [print(r['name'],'|',r['conclusion'] or 'running') for r in json.load(sys.stdin)['workflow_runs'][:3]]"

# 3. PyPI verifizieren
curl -s "https://pypi.org/pypi/iil-testkit/json" | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
```

**Für andere Packages** (aifw, promptfw etc.) — deren Repos haben PYPI_API_TOKEN direkt als eigenes Secret.
Publish via `workflow_dispatch` auf `publish.yml` im jeweiligen Repo.

## MANDATORY: Use iil-packages Instead of Reinventing

### LLM Calls → aifw

```python
# CORRECT — Django apps (views, services, tasks, management commands)
from aifw import sync_completion, completion_with_fallback

result = sync_completion(
    action_code="story_writing",
    messages=[{"role": "user", "content": prompt}],
    # NO model= override — DB-driven routing decides
)
text = result.content if result.success else ""

# BANNED in Django apps — reinventing what aifw already provides
import litellm          # use aifw instead
import openai           # use aifw instead
import anthropic        # use aifw instead
import urllib.request   # raw HTTP to LLM APIs
```

### Ausnahme: Standalone CI-Scripts (kein Django)

`aifw` benötigt Django + DB (`AIActionType`-Lookup). In CI-Scripts ohne Django-Setup
ist `aifw.sync_completion()` **nicht verwendbar** — der Aufruf schlägt lautlos fehl.

`litellm` ist eine **direkte Abhängigkeit von aifw** (`aifw/pyproject.toml: litellm>=1.30`)
und darf in Standalone-Scripts direkt verwendet werden:

```python
# CORRECT — Standalone CI-Script (.github/scripts/*.py, keine Django-DB)
import litellm

def _call_llm(prompt: str, max_tokens: int = 600) -> str | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        response = litellm.completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            api_key=api_key,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None

# BANNED in CI-Scripts:
# from aifw import sync_completion  ← schlägt fehl ohne Django-DB
# from aifw.service import ...      ← internes Submodul, nie direkt importieren
```

**Erkennungsmerkmal**: Script hat kein `DJANGO_SETTINGS_MODULE`, kein `manage.py`, läuft in
GitHub Actions ohne Django-Setup → litellm direkt erlaubt.

### Prompt Templates → promptfw

```python
# CORRECT
from promptfw import PromptTemplate, render_prompt

# BANNED — inline f-strings for complex prompts
system = f"You are {role}. Rules: {rules}. Context: {context}..."
```

### Story/Character/World Schemas → authoringfw

```python
# CORRECT
from authoringfw.schemas import StorySchema, CharacterSchema, WorldSchema

# BANNED — duplicating domain models
class Character:
    name: str
    description: str  # already exists in authoringfw
```

### WeltenHub API → weltenfw

```python
# CORRECT
from weltenfw import WeltenClient

# BANNED — raw httpx/requests calls to WeltenHub API
import httpx
resp = httpx.get("https://api.weltenhub.de/v1/worlds/...")
```

## Refactoring Trigger Patterns

When you see any of these patterns in existing code → **refactor to iil-package**:

| Found Pattern | Replace With |
|---|---|
| `import litellm` | `from aifw import sync_completion` |
| `import openai` (direct LLM call) | `from aifw import sync_completion` |
| `urllib.request` to LLM endpoint | `from aifw import sync_completion` |
| `from apps.ai_services.llm_service import` | `from aifw import ...` directly |
| Inline Jinja2 multi-layer prompt logic | `from promptfw import PromptTemplate` |
| Raw `httpx` calls to WeltenHub URLs | `from weltenfw import WeltenClient` |
| Local `Character`, `Story`, `World` dataclasses | `from authoringfw.schemas import ...` |
| Local outline/beat/story-structure code | `from outlinefw import OutlineGenerator, FRAMEWORKS` |
| Raw `httpx` calls to arXiv/Semantic Scholar | `from iil_researchfw import ...` |
| Local `openai.images.generate()` / `requests` to image API | `from illustrationfw import IllustrationPipeline` |
| Local quiz/grading/certificate logic | `from iil_learnfw import ...` |
| Local TRGS/ATEX/explosion-protection calculations | `from riskfw import ...` |

## Requirements.txt / pyproject.toml

Always pin with minimum version and upper bound:

```txt
aifw>=0.5.0,<1
iil-promptfw>=0.5.1,<1
iil-authoringfw>=0.3.0,<1
iil-weltenfw>=0.1.0,<1
iil-nl2cadfw>=0.1.0,<1
iil-outlinefw>=0.3.2,<1
iil-researchfw>=0.6.0,<1
iil-illustrationfw>=0.2.0,<1
iil-learnfw>=0.5.4,<1
riskfw>=0.1.0,<1
```

## Publishing New Versions

Each repo has a `publish.yml` GitHub Actions workflow (trigger: `workflow_dispatch`).
Secret `PYPI_API_TOKEN` must be set per repo under Settings → Secrets → Actions.

**Build command (local):**
```bash
rm -rf dist && python -m hatchling build && twine upload dist/*
# NEVER: python -m build  (falls back to setuptools, wrong package name)
```

## BANNED

- Duplicating LLM call logic that `aifw` already covers
- Duplicating domain schemas that `authoringfw` or `weltenfw` already define
- Using `python -m build` for hatchling-based packages (use `python -m hatchling build`)
- Publishing to PyPI under any account other than `iildehnert`
- Hardcoding LLM API keys, model names, or endpoints (use `aifw` DB-driven config)
