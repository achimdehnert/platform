# Policy: LLM Routing
<!-- rule_class: B | assessed_with: claude-fable-5 | reassess_by: 2027-08-01 (KONZ-038 D4) -->

**Trigger words:** welches modell, which model, günstig, cheap, free, kosten,
cost, llm, provider, haiku, opus, sonnet, groq, llama, cerebras, qwen,
together, openai

## Rule

For routine background and summarization tasks, **default to a fast-inference
provider (Cerebras / Groq)** before suggesting any frontier model from
Anthropic / OpenAI. The user has paid accounts for Cerebras and Groq —
free-tier rate limits are not the binding constraint, but **cost-per-token
on these providers is roughly 1-2 orders of magnitude lower** than frontier
models for equivalent quality on mechanical tasks.

## Available providers (keys in `~/.secrets/`)

| Provider | Key file | aifw prefix | Notes |
|---|---|---|---|
| **Cerebras** | `cerebras_api_key` | `cerebras/` | ~1000+ tok/s, paid tier available |
| **Groq** | `groq_api_key` | `groq/` | ~500+ tok/s, paid tier available |
| **Anthropic** | `anthropic_api_key` | `anthropic/` | Frontier reasoning + tool use |
| **OpenAI** | `openai_api_key` | `openai/` | GPT-4o / o-series |
| **Together** | `together_api_key` | `together_ai/` | Long-tail open models |

## Tier list

Same rungs as `session-routing.md` — one ladder for actions and sessions alike.

| Tier | Default model | $/1M in → out | Use case |
|---|---|---|---|
| **T1a** | `cerebras/gpt-oss-120b` *(Vorrang, schneller)* · `groq/openai/gpt-oss-120b` | 0,25 → 0,69 · 0,15 → 0,75 | Background jobs, summaries, classification, reports — prefer when output is user-visible prose |
| **T1b** | `groq/openai/gpt-oss-20b` | 0,10 → 0,50 | Same rung, when the smaller model is sufficient and you want lower spend |
| **T2** | `anthropic/claude-haiku-4-5` | 1 → 5 | If T1a/T1b fail on instruction following or nuance |
| **T3** | `anthropic/claude-sonnet-5` | 3 → 15 (intro 2 → 10 until 2026-08-31) | Code review, planning, multi-step reasoning |
| **T4** | `anthropic/claude-opus-5` | 5 → 25 | Only with explicit justification — agentic flows, complex synthesis |
| **T5** | `anthropic/claude-fable-5` | 10 → 50 | Top rung — deepest reasoning, long-horizon agentic work; needs a named reason |

**Verified available** as of 2026-08-25 (via `GET /models`, all six providers asked
in one run). Diese Liste ist eine **Messung mit Datum**, keine Zusage — sie veraltet,
und genau deshalb laeuft in `mcp-hub` naechtlich `check-model-liveness.py` gegen den
ADR-208-Resolver. Was dort rot wird, gehoert hier nachgezogen.

- **Groq** (13 IDs): `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.6-27b`,
  `groq/compound`, `groq/compound-mini`, `whisper-large-v3` (+ Guard-/Audio-Modelle).
  **Die gesamte Llama-Familie ist weg** — `llama-3.3-70b-versatile` und
  `llama-3.1-8b-instant` waren bis zu diesem Datum T1a bzw. T1b und existieren nicht mehr.
- **Cerebras** (2 IDs): `gpt-oss-120b`, `gemma-4-31b`.
  `zai-glm-4.7` und `llama3.1-8b` sind ebenfalls **weg**.
- **Anthropic** (10 IDs): `claude-fable-5`, `claude-opus-5`, `claude-sonnet-5`,
  `claude-haiku-4-5-20251001` sowie die 4-x-Vorgaenger.
- **OpenAI** (136 IDs): u.a. die `gpt-5.x`-Familie und `gpt-4.1`/`gpt-4o`.
- **Together** (169 Chat-Modelle).

**EU-/Datensouveränität: Mistral ist kein Weg mehr** (Owner-Entscheid 2026-08-25).
Der Schlüssel in `~/.secrets/mistral_api_key` wurde am selben Tag mit
`Invalid API Key` (HTTP 401) abgelehnt, und statt ihn zu erneuern, fällt der
Anbieter aus dieser Policy. Damit steht hier **kein** EU-gehosteter Anbieter mehr
— wer einen Workload hat, der das braucht, entscheidet ihn einzeln und schreibt
die Entscheidung als Repo-Override fest, statt sich auf eine Zeile zu verlassen,
deren Schlüssel niemand geprüft hat.

Für `ttz-lif` / `meiki-lra` gilt weiterhin der lokale Weg (Ollama) laut den
Repo-Overrides unten — der ist von dieser Streichung nicht berührt.

## Preise — Herkunft und zwei Fallen

Die Zahlen der Spalte stammen aus der litellm-Preistabelle, die unser eigener
Stack fuer `cost_per_token` benutzt (`model_prices_and_context_window_backup.json`,
Stand **2026-06-03**). Sie sind damit **eine Messung mit Datum**, keine Zusage —
dieselbe Einschraenkung wie bei der Verfuegbarkeitsliste oben.

**Falle 1 — die echte Cerebras-ID heisst `gpt-oss-120b`, nicht `openai/gpt-oss-120b`.**
Live geprueft am 2026-08-29: der Cerebras-Katalog fuehrt genau zwei IDs,
`gpt-oss-120b` und `gemma-4-31b`. Der Groq-Katalog fuehrt `openai/gpt-oss-120b`.
Wer die Groq-Schreibweise bei Cerebras verdrahtet, bekommt `model_not_found`.

**Falle 2 — fuer die echte Cerebras-ID kennt litellm keinen Preis.** In der Tabelle
steht nur `cerebras/openai/gpt-oss-120b`; `cerebras/gpt-oss-120b` fehlt. Eine
Verdrahtung auf die korrekte ID liefert also funktionierende Aufrufe **und**
Kosten von null in der Auswertung — und null sieht aus wie „billig", nicht wie
„nicht gefunden". Vor jeder Kostenaussage ueber den Cerebras-Pfad diesen Punkt
pruefen (Realfall: writing-hub, 2026-08-29).

**Vorrang innerhalb T1a: Cerebras vor Groq** (Owner-Entscheid 2026-08-29, Begruendung
Geschwindigkeit). Groq bleibt der Ausweichweg — zwei Anbieter, damit Drosselung oder
5xx nicht beide Wege zugleich treffen.

## Choosing between Cerebras and Groq (Tier 1)

- **Cerebras**: ultra-fast; der Katalog ist auf diesem Konto sehr schmal (2 Modelle),
  die T1a-Wahl ist `gpt-oss-120b`
- **Groq**: breiterer Katalog, dieselbe T1a-Familie (`openai/gpt-oss-120b`) plus
  `openai/gpt-oss-20b` fuer den guenstigen schnellen Pfad
- **Round-robin / fallback**: configure both in aifw with one as `default_model`
  and the other as `fallback_model` — automatic failover on rate-limit or 5xx

## How to apply

Before recommending an LLM target for a new `action_code`, present the tier
list above. Default = T1a. Skip a tier only with a stated reason.

When seeding an aifw action code (single provider, T1a on Groq):

```python
from aifw.models import Provider, Model, ActionType
groq, _ = Provider.objects.get_or_create(
    name="groq",
    defaults={"api_key_env_var": "GROQ_API_KEY"},
)
m, _ = Model.objects.get_or_create(
    provider=groq, name="openai/gpt-oss-120b",
    defaults={"display_name": "GPT-OSS 120B (Groq)"},
)
ActionType.objects.update_or_create(
    code="<your_action_code>",
    defaults={"default_model": m, "fallback_model": m},
)
```

With Groq→Cerebras failover (gleiche Modellfamilie bei beiden Anbietern):

```python
cerebras, _ = Provider.objects.get_or_create(
    name="cerebras", defaults={"api_key_env_var": "CEREBRAS_API_KEY"},
)
m_cb, _ = Model.objects.get_or_create(
    provider=cerebras, name="gpt-oss-120b",
)
ActionType.objects.update_or_create(
    code="<your_action_code>",
    defaults={"default_model": m, "fallback_model": m_cb},
)
```

`CEREBRAS_API_KEY` / `GROQ_API_KEY` need to be in the host project's `.env`.
Source values from `~/.secrets/cerebras_api_key` and
`~/.secrets/groq_api_key` (never echo to stdout).

Cerebras quickstart reference: https://inference-docs.cerebras.ai/quickstart

## Per-repo override examples

- **ttz-hub** (ttz-lif org): compliance requires no external LLM — only Ollama
  local. Override in `ttz-hub/CLAUDE.md` `## Policy Overrides`.
- **meiki-hub** (meiki-lra): citizen-data — same applies if PII touched.

## Changelog

- 2026-08-29: **Preisspalte fuer T1a/T1b gefuellt** (vorher „—") und **Cerebras als
  Vorrang** innerhalb T1a gesetzt (Owner-Entscheid, Begruendung Geschwindigkeit).
  Quelle der Zahlen ist die litellm-Tabelle vom 2026-06-03. Neu dokumentiert sind
  zwei Fallen, die beim Verdrahten in writing-hub auffielen: die echte Cerebras-ID
  lautet `gpt-oss-120b` (nicht `openai/gpt-oss-120b`), und genau fuer diese ID kennt
  litellm keinen Preis — Kostenauswertungen ueber den Cerebras-Pfad zeigen sonst
  still null. Umsetzung auf Prod haengt an drei Voraussetzungen
  (writing-hub#879: Schluessel, Provider-Zeile, Preis-Schluessel).

- 2026-08-25: **Reality-Check ueber alle sechs Anbieter** — T1a und T1b waren auf
  BEIDEN Anbietern tot: `groq/llama-3.3-70b-versatile`, `groq/llama-3.1-8b-instant`,
  `cerebras/llama3.1-8b`, `cerebras/zai-glm-4.7` werden nicht mehr gelistet. Neue
  Sprossen: T1a `groq/openai/gpt-oss-120b` oder `cerebras/gpt-oss-120b`, T1b
  `groq/openai/gpt-oss-20b`. Der Fund kam nicht aus dieser Datei, sondern aus einem
  fehlgeschlagenen `/prompt`-Lauf (`model_not_found`) — die Policy selbst hatte den
  toten Pin seit dem 2026-05-17 gefuehrt. Konsumenten nachgezogen: ADR-208-Resolver
  (mcp-hub#230), aifw-Seed + neuer `check_aifw_config --liveness` (aifw#51),
  `run_prompt.py` liest jetzt den Resolver statt eines eigenen Pins, adr-review-CLI
  repinned. **Neu und der eigentliche Punkt:** eine naechtliche Liveness-Pruefung
  (mcp-hub `check-model-liveness.py`) fragt die Anbieter, statt Deklarationen zu
  vergleichen — es war der zweite Fall dieser Klasse. **Mistral ist raus**
  (Owner-Entscheid, aifw#50): der Schluessel wurde mit HTTP 401 abgelehnt, und
  statt einer Rotation faellt der Anbieter aus der Policy. Ein EU-gehosteter
  Anbieter steht damit nicht mehr drin.

- 2026-07-04: Secret-Pfad-Fix — Keys liegen real in `~/.secrets/`, nicht
  `~/shared/secrets-inbox/` (seit 2026-05-30 konsolidiert, existiert nicht mehr).
  Fix lag seit 2026-06-20 nur im pinned Policy-Worktree; mit diesem PR in die SSoT
  übernommen. (Changelog-Einträge unten nennen historisch den alten Pfad.)
- 2026-05-11: Initial. Promoted from meiki-hub local memory after user feedback
  ("wieso nicht Groq free of cost?") during repo_health agent design.
- 2026-05-11: Added Cerebras as Tier 1a peer to Groq, noted paid Groq access,
  documented Cerebras→Groq failover pattern, listed all available provider
  keys in `~/shared/secrets-inbox/`.
- 2026-05-13: Reality-check via `/v1/models` — `cerebras/llama-3.3-70b` is
  not on this account; Tier 1a defaults switched to `groq/llama-3.3-70b-versatile`
  (or `cerebras/qwen-3-235b-a22b-instruct-2507`). Tier 1b Cerebras model ID
  fixed to `cerebras/llama3.1-8b` (no dash). Seed examples updated.
- 2026-05-17: `cerebras/qwen-3-235b-a22b-instruct-2507` von Cerebras zum
  **2026-05-27 abgekündigt**. Tier-1a Cerebras-Slot → `cerebras/gpt-oss-120b`;
  qwen aus „Verified available" entfernt. Konsumenten umgestellt: ADR-208
  Resolver (mcp-hub #55), adr-review-CLI (platform #185), Orchestrator-Routing
  (mcp-hub #56), aifw-Migration 0003 (dev-hub #48, **DB-Apply ausstehend**).
- 2026-07-31: Tier list renumbered to the shared **T1a–T5** ladder (same rungs
  as `session-routing.md`) and refreshed to current models: T3 `claude-sonnet-4-6`
  → `claude-sonnet-5`, T4 `claude-opus-4-7` → `claude-opus-5`, new top rung
  **T5 `claude-fable-5`**. Added a price column; both replaced IDs were stale
  against the current lineup.
