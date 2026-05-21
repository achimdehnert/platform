# Policy: LLM Routing

**Trigger words:** welches modell, which model, günstig, cheap, free, kosten,
cost, llm, provider, haiku, opus, sonnet, groq, llama, cerebras, qwen,
mistral, together, openai

## Rule

For routine background and summarization tasks, **default to a fast-inference
provider (Cerebras / Groq)** before suggesting any frontier model from
Anthropic / OpenAI. The user has paid accounts for Cerebras and Groq —
free-tier rate limits are not the binding constraint, but **cost-per-token
on these providers is roughly 1-2 orders of magnitude lower** than frontier
models for equivalent quality on mechanical tasks.

## Available providers (keys in `~/shared/inbox/secrets/`)

| Provider | Key file | aifw prefix | Notes |
|---|---|---|---|
| **Cerebras** | `cerebras_api_key` | `cerebras/` | ~1000+ tok/s, paid tier available |
| **Groq** | `groq_api_key` | `groq/` | ~500+ tok/s, paid tier available |
| **Anthropic** | `anthropic_api_key` | `anthropic/` | Frontier reasoning + tool use |
| **OpenAI** | `openai_api_key` | `openai/` | GPT-4o / o-series |
| **Mistral** | `mistral_api_key` | `mistral/` | EU-hosted alternative |
| **Together** | `together_api_key` | `together_ai/` | Long-tail open models |

## Tier list

| Tier | Default model | Use case |
|---|---|---|
| **1a** | `groq/llama-3.3-70b-versatile` *or* `cerebras/gpt-oss-120b` | Background jobs, summaries, classification, reports — prefer when output is user-visible prose |
| **1b** | `cerebras/llama3.1-8b` *or* `groq/llama-3.1-8b-instant` | Same tier, when 8B is sufficient and you want lower spend |
| **2** | `anthropic/claude-haiku-4-5` | If 1a/1b fail on instruction following or nuance |
| **3** | `anthropic/claude-sonnet-4-6` | Code review, planning, multi-step reasoning |
| **4** | `anthropic/claude-opus-4-7` | Only with explicit justification — agentic flows, complex synthesis |

**Verified available** as of 2026-05-13 (via `GET /v1/models`):
- Cerebras account: `gpt-oss-120b`, `zai-glm-4.7`, `llama3.1-8b`
  (`qwen-3-235b-a22b-instruct-2507` **DEPRECATED 2026-05-27** — nicht mehr nutzen)
  (no Llama-3.3-70b on this Cerebras account — use Groq for the 70B Llama instead)
- Groq Llama family: `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`,
  `meta-llama/llama-4-scout-17b-16e-instruct`

EU-/data-sovereignty workloads → `mistral/mistral-large-latest` instead of any
US-hosted provider. For `ttz-lif` / `meiki-lra` repos see per-repo overrides.

## Choosing between Cerebras and Groq (Tier 1)

- **Cerebras**: ultra-fast on its hosted models; Llama family currently 8B only,
  high-quality option is `gpt-oss-120b` (qwen-3-235b deprecated 2026-05-27)
- **Groq**: broader Llama catalogue (incl. 70B), `llama-3.1-8b-instant` for cheap fast paths
- **Round-robin / fallback**: configure both in aifw with one as `default_model`
  and the other as `fallback_model` — automatic failover on rate-limit or 5xx

## How to apply

Before recommending an LLM target for a new `action_code`, present the tier
list above. Default = Tier 1a. Skip a tier only with a stated reason.

When seeding an aifw action code (single provider, Tier 1a on Groq):

```python
from aifw.models import Provider, Model, ActionType
groq, _ = Provider.objects.get_or_create(
    name="groq",
    defaults={"api_key_env_var": "GROQ_API_KEY"},
)
m, _ = Model.objects.get_or_create(
    provider=groq, name="llama-3.3-70b-versatile",
    defaults={"display_name": "Groq Llama 3.3 70B Versatile"},
)
ActionType.objects.update_or_create(
    code="<your_action_code>",
    defaults={"default_model": m, "fallback_model": m},
)
```

With Groq→Cerebras failover (70B → 8B fallback):

```python
cerebras, _ = Provider.objects.get_or_create(
    name="cerebras", defaults={"api_key_env_var": "CEREBRAS_API_KEY"},
)
m_cb, _ = Model.objects.get_or_create(
    provider=cerebras, name="llama3.1-8b",
)
ActionType.objects.update_or_create(
    code="<your_action_code>",
    defaults={"default_model": m, "fallback_model": m_cb},
)
```

`CEREBRAS_API_KEY` / `GROQ_API_KEY` need to be in the host project's `.env`.
Source values from `~/shared/inbox/secrets/cerebras_api_key` and
`~/shared/inbox/secrets/groq_api_key` (never echo to stdout).

Cerebras quickstart reference: https://inference-docs.cerebras.ai/quickstart

## Per-repo override examples

- **ttz-hub** (ttz-lif org): compliance requires no external LLM — only Ollama
  local. Override in `ttz-hub/CLAUDE.md` `## Policy Overrides`.
- **meiki-hub** (meiki-lra): citizen-data — same applies if PII touched.

## Changelog

- 2026-05-11: Initial. Promoted from meiki-hub local memory after user feedback
  ("wieso nicht Groq free of cost?") during repo_health agent design.
- 2026-05-11: Added Cerebras as Tier 1a peer to Groq, noted paid Groq access,
  documented Cerebras→Groq failover pattern, listed all available provider
  keys in `~/shared/inbox/secrets/`.
- 2026-05-13: Reality-check via `/v1/models` — `cerebras/llama-3.3-70b` is
  not on this account; Tier 1a defaults switched to `groq/llama-3.3-70b-versatile`
  (or `cerebras/qwen-3-235b-a22b-instruct-2507`). Tier 1b Cerebras model ID
  fixed to `cerebras/llama3.1-8b` (no dash). Seed examples updated.
- 2026-05-17: `cerebras/qwen-3-235b-a22b-instruct-2507` von Cerebras zum
  **2026-05-27 abgekündigt**. Tier-1a Cerebras-Slot → `cerebras/gpt-oss-120b`;
  qwen aus „Verified available" entfernt. Konsumenten umgestellt: ADR-208
  Resolver (mcp-hub #55), adr-review-CLI (platform #185), Orchestrator-Routing
  (mcp-hub #56), aifw-Migration 0003 (dev-hub #48, **DB-Apply ausstehend**).
