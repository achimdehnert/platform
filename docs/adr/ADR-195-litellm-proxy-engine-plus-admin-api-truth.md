---
status: proposed
decision_date: 2026-05-11
deciders:
  - Achim Dehnert
reviewed_by:
  - Claude Opus 4.7 (Sparring Review, 2026-05-11) — REVISIONS REQUIRED, see reviews/ADR-195-review.md
depends_on:
  - ADR-115 (Grafana Agent Controlling Dashboard — llm_calls table)
  - ADR-116 (Dynamic Model Router — budget-aware routing)
  - ADR-178 (LLM Gateway Consolidation — V2 as canonical)
supersedes:
  - ADR-194 (Universal LLM Call Logging via Gateway Choke-Point)
repo: platform
consumers:
  - mcp-hub (llm_gateway, callback module)
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
  - "mcp-hub/llm_gateway/callbacks/litellm_callback.py"
  - "mcp-hub/llm_gateway/admin_api/reconcile.py"
  - "mcp-hub/llm_gateway/pricing.py"
  - "~/.claude/hooks/log_llm_call.py"
---

# ADR-195: LiteLLM-Proxy as Logging Engine + Anthropic Admin API as Truth Anchor

| Metadata | |
|----------|---|
| **Status** | Proposed (v1.0) |
| **Date** | 2026-05-11 |
| **Author** | Achim Dehnert |
| **Supersedes** | ADR-194 v1.0 (Universal LLM Call Logging via Gateway Choke-Point) |
| **Depends On** | ADR-115, ADR-116, ADR-178 |

---

## Context

ADR-194 v1.0 proposed building a custom `llm_gateway` as universal HTTP choke-point for all LLM calls. The adversarial review (`reviews/ADR-194-review.md`) flagged a Blocker plus two Critical issues. A subsequent out-of-the-box critique surfaced three deeper concerns the v1 ADR did not address:

1. **Bootstrap paradox** — gateway runs on prod-server `88.198.191.108`. When prod is down, Claude Code is unusable (BASE_URL points nowhere), which is exactly when developers need it to fix prod.
2. **Threat model regression** — gateway TLS-terminates all prompts in-memory. Adds a compromise surface (our Hetzner container) on top of Anthropic's.
3. **Build-vs-buy gap** — Anthropic now exposes an Admin API (`/v1/organizations/usage_report/messages` + `/v1/organizations/cost_report`) that delivers 100 % cost coverage at aggregate level without any code changes. OSS proxies (LiteLLM, Helicone) deliver per-call logging with 1 PT of setup vs. the 6.5 PT custom build.

The original pain remains valid: as of 2026-05-11, 658 LLM calls = $125 over 4 days were invisible to controlling.

Confirmed via live test against the Anthropic API (2026-05-11):

| Probe | Result |
|---|---|
| Anthropic Admin API endpoint structure | Aggregate-only (minute/hour/day buckets), all token fields incl. `cache_creation.ephemeral_5m/1h_input_tokens`, group-by `api_key_id`/`workspace_id`/`model`/`speed` |
| Existing `~/shared/secrets-inbox/anthropic_api_key` against admin endpoint | HTTP 401 — regular workspace key, **separate admin key required** |
| Existing key against `/v1/messages` | HTTP 200 — confirms baseline auth path works |

## Decision Drivers

Inherited from ADR-194 (still valid):

- Single source of truth for cost data
- Provider-agnostic
- No agent cooperation required for coverage
- Compliance/auditing record of cost (prompt-content auditing remains a separate future ADR)

New drivers exposed by the review process:

- **No SPoF for interactive developer tools.** Claude Code must keep working when prod-server is down.
- **Minimum new compromise surface.** Adding a TLS-terminating service we operate is a security cost; only justified if the value is real and irreplaceable.
- **Optionality.** A speculative 6.5 PT build is more expensive than a 1.5 PT incremental step that converts the C-build decision from speculative to data-driven.

## Considered Options

### Option A — ADR-194 v1.0: custom `llm_gateway` as central choke-point

Rejected. Detailed critique in `reviews/ADR-194-review.md` and out-of-the-box analysis (this session). Headline issues: SPoF on prod, bootstrap paradox, ignores Admin API + OSS proxies, 6.5 PT speculative build.

### Option B — Anthropic Admin API only

Daily polling of Admin API + per-source API keys (one each for `aifw`, Claude Code, Cascade BYOK, agent_team, ad-hoc scripts). 100 % cost coverage by Anthropic as truth-source. Existing self-loggers (aifw, agent_team, Stop hook) provide `action_code` attribution.

- **Pro**: ~1.5 PT, zero new components, zero SPoF, zero migration across 19 repos, Anthropic-side spend limits replace most of ADR-116 budget enforcement.
- **Pro**: Cascade BYOK becomes 100 % observable (today: ~80 % best-effort).
- **Con**: No per-request granularity. "Which conversation was expensive?" cannot be answered without a self-logger on that path.
- **Con**: Cost-data lags ~1 minute (Admin API minute-bucket polling cadence).

### Option C — Custom gateway (ADR-194)

See Option A.

### Option D — Adopt OSS proxy (LiteLLM, Helicone, Langfuse)

Adopt a battle-tested proxy as the per-call logging engine.

- **Pro**: Streaming, retries, multi-provider passthrough all already correct.
- **Pro**: ~1 PT setup, much less than 6.5 PT.
- **Con (avoidable)**: schema lock-in, UI lock-in, pricing-update lag — only if naively adopted.
- **Con (unavoidable)**: external roadmap dependency; possible supply-chain risk.

### Option E (chosen) — D + B with explicit C-preparation

LiteLLM-Proxy as **engine** (HTTP, streaming, retries) + Anthropic Admin API as **truth anchor** (settled cost reconciliation) + existing self-loggers (`aifw`, `agent_team`, Stop hook) as **attribution layer** (`action_code`). Architected explicitly so a later switch to a custom gateway (C) is a process swap, not a re-build.

## Decision Outcome

**Chosen: Option E.**

### Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│  Clients (Workstation + Servers)                                    │
│  ┌───────────┐  ┌──────────┐  ┌────────┐  ┌──────────────────┐    │
│  │Claude Code│  │ Cascade  │  │ aifw   │  │ Ad-hoc scripts   │    │
│  │           │  │  (BYOK)  │  │        │  │ (anthropic SDK)  │    │
│  └─────┬─────┘  └────┬─────┘  └───┬────┘  └────────┬─────────┘    │
│        │             │            │                 │              │
│        │ ANTHROPIC_BASE_URL=http://127.0.0.1:4000   │              │
│        ▼             ▼            ▼                 ▼              │
│  ┌───────────────────────────────────────────────────────────────┐│
│  │  Local LiteLLM-Proxy sidecar (per host, 127.0.0.1:4000)        ││
│  │  - HTTP passthrough + streaming + retries                      ││
│  │  - success_callback → our custom callback module               ││
│  └────────────────────────┬───────────────────────────────────────┘│
│                           │                                         │
│  ┌────────────────────────▼───────────────────────────────────────┐│
│  │  Our callback module (mcp-hub/llm_gateway/callbacks/)          ││
│  │  - INSERT into llm_calls (OUR schema, ADR-115)                 ││
│  │  - Pricing via mcp-hub/llm_gateway/pricing.py (OURS)           ││
│  │  - Reads action_code from x-litellm-metadata header            ││
│  └────────────────────────┬───────────────────────────────────────┘│
│                           │                                         │
│                           ▼                                         │
│        api.anthropic.com / api.openai.com / openrouter.ai          │
└────────────────────────────────────────────────────────────────────┘

Parallel: daily reconcile job
  Anthropic Admin API → llm_calls_reconcile → diff vs llm_calls → alert if drift > 1%
```

### Why local sidecar, not central

- Prod-server down → workstation LiteLLM still reachable on `127.0.0.1` → Claude Code keeps working.
- Compromise surface = local process on developer machine, not shared internet-facing service.
- Trivial config (one Docker container or one binary per host); no HA/Load-Balancer needed.

### Layer ownership (the key anti-lock-in commitment)

| Layer | Owner |
|---|---|
| HTTP / streaming / retries | LiteLLM |
| `llm_calls` schema (ADR-115) | **us** |
| `pricing.py` (cache-tier multipliers, model prices) | **us** |
| `action_code` taxonomy | **us** (via metadata header) |
| Dashboard | **us** (Grafana on `llm_calls`) |
| Truth-of-spend | Anthropic (Admin API) |

LiteLLM owns nothing of value. If we replace it with a custom `/v1/messages` passthrough later, clients see no change (BASE_URL stays the same), schema/pricing/dashboard are untouched.

### Per-source API keys

Create one Anthropic API key per source via Anthropic Console (manual, ~5 min total):

- `key_aifw` — used by aifw service
- `key_cc` — used by Claude Code (workstation + headless)
- `key_cascade` — used by Cascade BYOK
- `key_agent_team` — used by orchestrator agent_team
- `key_scripts` — used by ad-hoc Python scripts

Each key gets an Anthropic-side spend limit (Console feature, free). Per-key spend visible via Admin API `group_by=api_key_id` — solves the 658-invisible-calls problem.

### Migration plan

| Phase | Scope | Effort | Risk |
|-------|-------|--------|------|
| **P1** | Create Admin API key (Anthropic Console — manual, requires browser). Store as `~/shared/secrets-inbox/anthropic_admin_api_key`. | 0.1 d | None |
| **P2** | Smoke test: poll Admin API for last 24h; verify all expected token fields present. Document Admin API client in `mcp-hub/llm_gateway/admin_api/`. | 0.3 d | None |
| **P3** | Create per-source Anthropic keys + set Anthropic-side spend limits. Inventory which keys land where. | 0.2 d | Low |
| **P4** | Deploy LiteLLM-Proxy as sidecar on workstation + dev + prod (Docker compose). Set `ANTHROPIC_BASE_URL=http://127.0.0.1:4000`. Stop hook stays active as DEFENSE-IN-DEPTH but **self-disables** when `ANTHROPIC_BASE_URL` is set (resolves K-01 from ADR-194 review). | 0.5 d | Medium — first-time proxy setup |
| **P5** | Write callback module (`callbacks/litellm_callback.py`): reads LiteLLM `success_callback` payload → applies `pricing.py` → INSERT into `llm_calls` with `source='litellm'` + `action_code` from header. | 1 d | Low |
| **P6** | Daily reconcile cron: Admin API → `llm_calls_reconcile` table. Grafana panel "Cost Reconcile" with drift alarm at >1 % deviation over 7 days (resolves M-06 from ADR-194 review). | 0.4 d | Low |
| **P7** | Observe 4 weeks: stop hook + LiteLLM callback both write (different `source`), reconcile shows whether LiteLLM coverage is complete. Then retire Stop hook. | 0.0 d (observation) | Low |

**Total: ~2.5 PT** (vs ADR-194's 6.5 PT).

### Phase-D-to-C migration path (preparation, no work in this ADR)

Codified so we don't get stuck:

1. Use Anthropic-format passthrough only (`/v1/messages`), not LiteLLM's OpenAI translator
2. Callback module talks to **our** schema, never LiteLLM's DB
3. No LiteLLM Web-UI in operational workflows (Grafana only)
4. No LiteLLM forks/patches — workarounds via external code only
5. Pricing math in `mcp-hub/llm_gateway/pricing.py`, not LiteLLM's pricing tables

If after 3 months observation a custom gateway becomes warranted (concrete pain, not speculation), the C-build is then estimated ~5 PT (engine-swap behind unchanged BASE_URL).

### Non-goals

- **Per-prompt content storage / DLP** — separate ADR with Legal review. (Resolves K-02 from ADR-194 review by removing the "audit trail" claim.)
- **Windsurf Pro-mode visibility** — billed Windsurf↔Anthropic, structurally invisible to us. Same as ADR-194.
- **HA gateway** — sidecar architecture removes the need.

## Consequences

### Positive

- **100 % cost coverage** via Admin API regardless of which client or host
- **100 % per-call coverage** via LiteLLM sidecar for instrumented hosts
- **No central SPoF** — local sidecar means workstation works even with prod-server down
- **Datadriven decision** for a later custom gateway: 3 months of LiteLLM data tells us if/what to build
- **Anthropic-side spend limits** replace most of ADR-116 enforcement complexity
- **Cascade BYOK becomes 100 % observable** without agent cooperation (today: ~80 %)
- **Reconcile against Anthropic invoice** — drift detection is mathematically possible (Admin API = settled truth)

### Negative

- **External dependency on LiteLLM-Proxy** — supply-chain and roadmap risk. Mitigation: layer ownership above.
- **Latency tax** — sidecar adds local hop (~1–3 ms, not network hop). To be measured in P4.
- **Two writers during P7 transition** — Stop hook + LiteLLM callback both INSERT. Mitigation: hook self-disables when `ANTHROPIC_BASE_URL` is set; reconcile detects any drift.
- **Per-source key management** — 5 keys to rotate. Mitigation: Anthropic Console + secrets-inbox process is unchanged.

### Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| LiteLLM streaming bug loses usage data | Medium | Reconcile against Admin API catches this within 24 h |
| Stop hook + LiteLLM double-write same call | Medium | Hook self-disables when `ANTHROPIC_BASE_URL` is set (no overlap) |
| Admin API rate-limit on large workloads | Low | Bucket-width=1h, 24 calls/day per workspace; well under limits |
| LiteLLM pivots / drops self-hosted | Low | Layer ownership = engine swap, not system swap; ~5 PT to replace |
| Admin key leak | Medium | Admin keys are highest privilege — store with same care as production secrets; rotation procedure documented |

## Compliance / Drift Checks

Replaces ADR-194's LLM-001/002/003:

- `LLM-001` (error): Direct `import anthropic` outside `aifw/`, `llm_gateway/`, `tests/` without `ANTHROPIC_BASE_URL` set in the calling context.
- `LLM-002` (info, runtime): `llm-doctor` CLI in `mcp-hub/llm_gateway/` checks at session start that `ANTHROPIC_BASE_URL` points to a reachable proxy. (Replaces ADR-194's unenforceable `~/.bashrc` check from review-H-04.)
- `LLM-003` (warning): `llm_calls_reconcile` drift > 1 % over 7 days → alert. Indicates a writer bypassed the proxy or a callback dropped events.

## Open Questions

1. **LiteLLM-Proxy vs Helicone** — final choice deferred to P4 spike (½ day). Both fit the engine role; LiteLLM is already in our Python deps (orchestrator MCP), which weighs toward LiteLLM.
2. **Workspace mapping** — should each source have its own Anthropic Workspace, or just its own API key? Workspaces enable group-by; keys alone are simpler. Decide in P3.
3. **Reconcile threshold** — 1 % drift for alert is initial; tune after first month of observation data.

## Implementation Status

**None.** This ADR is the proposal; implementation begins at P1 after acceptance.

## Changelog

- 2026-05-11: v1.0 proposed. Supersedes ADR-194 v1.0. Driven by adversarial review (`reviews/ADR-194-review.md`) + out-of-the-box critique surfacing Admin API + OSS-proxy options. Decision: LiteLLM-as-engine + Admin-API-as-truth + sidecar deployment, with explicit anti-lock-in commitments enabling a later custom-gateway build at ~5 PT if needed.
