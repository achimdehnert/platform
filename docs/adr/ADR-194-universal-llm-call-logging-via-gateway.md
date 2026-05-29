---
status: superseded
superseded-by: ADR-195 (LiteLLM-Proxy as Logging Engine + Anthropic Admin API as Truth Anchor)
date: 2026-05-11
decision-makers:
  - Achim Dehnert
reviewed-by:
  - Claude Opus 4.7 (Sparring Review, 2026-05-11) — REVISIONS REQUIRED, see reviews/ADR-194-review.md
  - Claude Opus 4.7 (Out-of-the-Box Critique, 2026-05-11) — fundamental concerns: SPoF, bootstrap paradox, Admin API + OSS proxy not considered
depends-on:
  - ADR-115 (Grafana Agent Controlling Dashboard — llm_calls table)
  - ADR-116 (Dynamic Model Router — budget-aware routing)
  - ADR-178 (LLM Gateway Consolidation — V2 as canonical)
supersedes: []
repo: platform
consumers:
  - mcp-hub (llm_gateway service)
  - aifw
  - dev-hub
  - travel-beat
  - bfagent
  - risk-hub
  - coach-hub
  - weltenhub
  - wedding-hub
domains:
  - llm
  - observability
  - cost-control
  - security
implementation_status: none
staleness_months: 12
last_reviewed: 2026-05-11
drift_check_paths:
  - "mcp-hub/llm_gateway/main.py"
  - "aifw/src/aifw/service.py"
  - "~/.claude/hooks/log_llm_call.py"
  - "~/.codeium/windsurf/memories/global_rules.md"
---

# ADR-194: Universal LLM Call Logging via Gateway Choke-Point

> **⚠ SUPERSEDED by [ADR-195](./ADR-195-litellm-proxy-engine-plus-admin-api-truth.md) on 2026-05-11.**
> Adversarial review + out-of-the-box critique surfaced fundamental issues (SPoF on prod, bootstrap paradox, missing evaluation of Anthropic Admin API and OSS proxies). ADR-195 chooses LiteLLM-Proxy as engine + Anthropic Admin API as truth anchor + local sidecar deployment. The pain analysis in this document (658 invisible calls = $125 / 4 days) remains valid and motivates ADR-195. Kept for historical context.

| Metadata | |
|----------|---|
| **Status** | Superseded (by ADR-195) |
| **Date** | 2026-05-11 |
| **Author** | Achim Dehnert |
| **Reviewer** | — |
| **Depends On** | ADR-115, ADR-116, ADR-178 |
| **Consumers** | mcp-hub, aifw, all 19 platform repos |

---

## Context

Per ADR-115 lives our cost/quality visibility on the `llm_calls` PostgreSQL table. As of 2026-05-11 four independent ingestion paths feed it:

| Source | Path | Coverage |
|--------|------|----------|
| `aifw.sync_completion()` | Django code → `aifw.service` → INSERT | Deterministic when used |
| `agent_team` | `mcp-hub/orchestrator_mcp/agent_team/llm_adapter.py` direct INSERT | Deterministic |
| Headless CLI runs | `mcp-hub/orchestrator_mcp/headless/services/bridge.py` | Deterministic |
| Cascade (Windsurf chat) | MCP tool `cascade_log_response` called by the agent | **Best-effort, ~80% compliance** |
| Claude Code (interactive) | `~/.claude/hooks/log_llm_call.py` Stop hook (added 2026-05-11) | Deterministic on workstation only |
| Direct `anthropic`/`openai` SDK calls in scripts | — | **Invisible** |

This creates three structural problems:

1. **Coverage gaps.** Any LLM call that bypasses `aifw` and is not made from a deployment we own (Windsurf desktop chat, ad-hoc Python scripts, future agent integrations) is invisible to controlling. As of 2026-05-11 the backfill of 4 days of Claude Code transcripts recovered **658 previously-invisible API calls = $125 USD** that had never appeared in any dashboard.
2. **Five logging code paths.** `aifw`, `agent_team`, `bridge.py`, `cascade_logger.py`, and the new Claude Code hook each re-implement the same INSERT plus per-source pricing math. ADR-115 specified one table, not five writers.
3. **Best-effort instrumentation does not scale.** `cascade_log_response` relies on the model remembering a Windsurf rule. Adding a similar hook to every new agent integration (Devin chat, Aider interactive, future tools) is a maintenance treadmill.

ADR-178 already established `llm_gateway` (V2, `mcp-hub/llm_gateway/`) as the canonical HTTP gateway with built-in `usage_logger.py` that writes to `llm_calls`. Today it is consumed only by `agent_team/llm_adapter.py` — the other four code paths bypass it.

## Decision Drivers

- **Single source of truth for cost data.** ADR-115's controlling dashboard is only as honest as the underlying ingestion.
- **Provider-agnostic.** Anthropic, OpenAI, OpenRouter, and Cerebras must all funnel through the same logging surface.
- **No agent cooperation required.** Coverage must not depend on the model "remembering to log."
- **Defense in depth.** When the gateway is unreachable, the system should degrade to direct provider calls plus best-effort local logging — never block work.
- **Compliance/auditing.** Sec/legal need a reliable record of every prompt and token spend, including those routed through third-party agents (Cascade BYOK mode, future SaaS integrations).

## Considered Options

### Option A: Status quo + iterate per-source

Keep `aifw`, `agent_team`, `bridge.py`, `cascade_logger.py`, the Claude Code hook, plus add a Python `sitecustomize.py` monkey-patch for SDK bypass calls.

- **Pro**: Incremental, no infrastructure changes.
- **Pro**: Each path can use its own pricing table (already true).
- **Con**: Five+ writers, divergent pricing, divergent schemas. Recently `cache_creation_input_tokens` field varied in shape between the cascade logger (legacy flat) and the Claude Code hook (nested `cache_creation.ephemeral_5m_input_tokens`).
- **Con**: Cascade desktop chat stays best-effort.
- **Con**: Monkey-patching fragile under SDK upgrades (Anthropic SDK v0.40 changed `messages.create` signature; OpenAI v2 changed client factory).

### Option B: Promote `llm_gateway` to single choke-point (chosen)

All LLM consumers — `aifw`, Claude Code, Cascade BYOK, ad-hoc scripts, headless CLI — route their API calls through `llm_gateway`, which logs and forwards. Provider-format passthrough endpoints (`/v1/messages` for Anthropic, `/v1/chat/completions` for OpenAI) keep client SDKs unmodified.

- **Pro**: Single writer. Pricing, schema evolution, retries, budget enforcement (ADR-116) all in one place.
- **Pro**: `ANTHROPIC_BASE_URL` and `OPENAI_BASE_URL` env vars are honored by every official SDK and by Claude Code — zero client code changes.
- **Pro**: Adding a new agent (Devin, Aider, custom) auto-inherits logging.
- **Con**: Single point of failure unless made HA. Mitigation: gateway returns provider response unmodified, has 99.x SLO target, plus fallback (see Decision below).
- **Con**: Windsurf Pro-plan (non-BYOK) Cascade calls still untraceable — that traffic is billed by Anthropic-to-Windsurf, not to us, so it is outside our control regardless.
- **Con**: One-time migration effort across ~19 repos.

### Option C: Network-level capture

eBPF or Envoy sidecar intercepts all outbound HTTPS to `api.anthropic.com` and `api.openai.com`.

- **Pro**: Truly transparent; works even for code we did not write.
- **Con**: Requires TLS termination (MITM cert installed on every workstation) or relies on SDK base-URL override anyway — at which point Option B is simpler.
- **Con**: Operationally hostile; surprising for new contributors; security review burden.

## Decision Outcome

**Chosen: Option B — `llm_gateway` as universal choke-point.**

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Clients                                                         │
│  ┌───────────┐  ┌──────────┐  ┌────────┐  ┌──────────────────┐  │
│  │Claude Code│  │ Cascade  │  │ aifw   │  │ Ad-hoc scripts   │  │
│  │           │  │  (BYOK)  │  │        │  │ (anthropic SDK)  │  │
│  └─────┬─────┘  └────┬─────┘  └───┬────┘  └────────┬─────────┘  │
│        │             │            │                 │            │
│        │ ANTHROPIC_BASE_URL set to llm-gateway.iil.pet           │
│        ▼             ▼            ▼                 ▼            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  llm_gateway (V2, FastAPI, mcp-hub)                          ││
│  │  ─ /v1/messages           ← Anthropic passthrough  [NEW]     ││
│  │  ─ /v1/chat/completions   ← OpenAI passthrough     [EXISTS]  ││
│  │  ─ /v1/agent              ← agent_team             [EXISTS]  ││
│  │  ─ usage_logger.py        → INSERT INTO llm_calls            ││
│  │  ─ budget_tracker         → ADR-116 budget enforcement       ││
│  │  ─ rate_limit + retries                                      ││
│  └────────────────────────┬─────────────────────────────────────┘│
│                           │                                       │
│                           ▼                                       │
│  ┌──────────────────────────────────────────┐                    │
│  │  Upstream providers: api.anthropic.com,  │                    │
│  │  api.openai.com, openrouter.ai, ...      │                    │
│  └──────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

### Required changes by client

| Client | Today | After ADR-194 |
|--------|-------|---------------|
| `aifw` | Calls Anthropic/OpenAI directly, INSERTs from its service layer | `ANTHROPIC_BASE_URL` env points to gateway; `aifw.service` removes its INSERT path |
| Claude Code | Stop hook reads transcripts, INSERTs | `ANTHROPIC_BASE_URL` env in shell profile points to gateway; hook deleted after stabilisation |
| Cascade in BYOK mode | MCP `cascade_log_response` called by agent | BYOK URL set to gateway; rule deleted |
| Cascade in Pro mode | (unchanged) | Out of scope — Anthropic-Windsurf billing |
| Headless CLI (Claude, Devin) | `bridge.py` writes INSERT post-hoc from CLI stdout | Same — these wrap CLIs we do not control. Logging via gateway is preferred when CLI honors `ANTHROPIC_BASE_URL`; fallback remains `bridge.py` |
| `agent_team` | Already via gateway | Unchanged |
| Ad-hoc scripts | Direct SDK + invisible | `ANTHROPIC_BASE_URL` inherited from venv-level config |

### Gateway extensions required

1. **Anthropic `/v1/messages` passthrough endpoint** — accept the exact Anthropic request shape, forward to `api.anthropic.com`, parse the response's `usage` block (input/output/cache_creation/cache_read), INSERT one row, return upstream response byte-for-byte.
2. **Streaming support** — Anthropic and Claude Code use SSE streams. Gateway must proxy stream chunks while accumulating usage from the final `message_delta` event.
3. **Auth model** — gateway accepts the user's `x-api-key` header, validates it locally if we issue our own keys, or forwards verbatim for BYOK. Keys are not stored beyond a salted hash for attribution.
4. **Cache-tier pricing** — extend `pricing.py` with the 1.25x/2x/0.1x multipliers for `cache_creation_5m`, `cache_creation_1h`, `cache_read` (the Claude Code hook proves these are the correct billing rates per Anthropic 2026-05).
5. **Degraded mode** — if upstream is unreachable, return 503 (do not silently drop). If the INSERT fails, log the call and continue (logging must never block a working LLM request).

### Migration plan

| Phase | Scope | Effort | Risk |
|-------|-------|--------|------|
| **P1** | Gateway: add `/v1/messages` passthrough + streaming + cache pricing. Deploy alongside existing `/v1/agent` route. | 3 d | Low — additive |
| **P2** | Claude Code: set `ANTHROPIC_BASE_URL` in workstation `~/.bashrc`. Stop hook stays as defense-in-depth for 4 weeks; logs duplicate calls become a comparison check. | 0.5 d | Low — env var override, instant rollback |
| **P3** | `aifw`: switch base URL to gateway; remove `aifw.service` INSERT path; keep cost-computation utility for compatibility. Add a `aifw.service` flag `bypass_gateway=True` for offline testing. | 2 d | Medium — touches 19 consumer repos via the same dependency, but call signature unchanged |
| **P4** | Cascade BYOK setup documented in onboarding; `cascade_log_response` MCP tool kept available but deprecated. | 0.5 d | Low |
| **P5** | Retire dual writers: delete Claude Code Stop hook, delete `cascade_logger.py` after one billing cycle with zero discrepancy. | 0.5 d | Low |

Total estimated effort: **6.5 person-days**, spread over 2–3 weeks (P1 → P5 are mostly sequential).

### Non-goals

- **Replacing `aifw`'s prompt/quality-level abstraction.** `aifw` still owns prompt templates, model-selection logic (ADR-116), and the `action_code` taxonomy. ADR-194 only redirects the actual HTTP call.
- **Windsurf Pro-plan visibility.** Out of scope — that traffic is Anthropic-billed-to-Windsurf, not visible to us by design.
- **Token-level prompt inspection / DLP.** A future ADR may add prompt-content auditing in the gateway; this ADR limits scope to usage/cost.

## Consequences

### Positive

- **100% logging coverage** for every LLM API call originating from our infrastructure (workstation, dev server, prod, headless runs, agent_team).
- **Single pricing table.** Cache-tier pricing math lives in one place. Cost discrepancies between sources become impossible.
- **ADR-116 budget enforcement** automatically covers Claude Code and Cascade BYOK — currently they can blow the budget invisibly.
- **Vendor portability.** Switching from Anthropic direct to AWS Bedrock or Vertex needs a config change in the gateway, not in 19 repos.
- **Audit trail.** Sec/legal can inspect prompts + responses centrally (with retention/redaction policies set in one place).

### Negative

- **Gateway availability becomes critical.** If `llm-gateway.iil.pet` is down, all Claude Code / Cascade interactive work halts. Mitigation: documented escape hatch — `unset ANTHROPIC_BASE_URL` to bypass gateway in degraded mode.
- **Latency tax.** Adding one HTTP hop. Measure during P1; budget +30–50 ms p95.
- **Migration touches 19 repos** indirectly via `aifw`. Risk surface is real even if each change is small.

### Risks and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Streaming proxy loses last `message_delta` event → wrong cost | Medium | P1 includes streaming-correctness tests against `anthropic-sdk` test fixtures |
| Anthropic API breaks (e.g. new auth header) | Low | Gateway passthrough is byte-faithful; new headers flow through; pricing tables versioned |
| Gateway becomes single point of failure | Medium | HA: deploy 2 replicas behind nginx; degraded mode bypasses gateway via env unset |
| Migration P3 breaks an unknown aifw caller | Medium | Phase P3 ships behind `AIFW_USE_GATEWAY` feature flag, off by default for 1 week |
| Cost double-counting during P2 transition | Low | Use `request_id` for global dedupe; add UNIQUE INDEX `(source, request_id)` to `llm_calls` as part of P1 |

## Compliance / Drift Checks

Add to `iil-codeguard` (per ADR-191):

- `LLM-001` (error): Direct `import anthropic` or `from openai import` outside `aifw/`, `llm_gateway/`, and `tests/` — must use `aifw` or set `ANTHROPIC_BASE_URL`.
- `LLM-002` (warning): Workstation shell profile missing `ANTHROPIC_BASE_URL` once P2 ships.
- `LLM-003` (info): `llm_calls` row missing `request_id` — indicates a writer that bypassed the gateway.

## Open Questions

1. **Authentication**: do we issue our own per-user API keys at the gateway, or pass through the user's Anthropic key? Per-user keys enable attribution beyond `source` but require a key-management surface.
2. **PII redaction**: Should the gateway redact prompts before INSERT, or store full prompt content (with retention policy)? Defer to a follow-up ADR.
3. **Multi-tenancy**: Today `tenant_id=0` everywhere. If we onboard external tenants (e.g. weltenhub customers), gateway must propagate tenant attribution.

## Implementation Status

**None.** This ADR is the proposal; implementation begins after acceptance.
