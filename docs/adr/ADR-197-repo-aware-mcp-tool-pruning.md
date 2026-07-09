---
status: proposed
decision_date: 2026-05-12
deciders:
  - Achim Dehnert
reviewed_by: []
depends_on:
  - ADR-113 (Agent Memory — pgvector store + temporal decay)
  - ADR-176 (MCP Server SSoT — templates + sync-mcp-config.sh)
  - ADR-186 (Headless Agent Pipeline — tool-usage telemetry source)
related:
  - docs/concepts/token-reduction-strategy.md
  - PR #131 (fix(session-ende): correct MCP prefixes + agent_memory API for WSL)
repo: platform
consumers:
  - all repos using Cascade IDE
  - dev-hub (potential host for catalog-refresh cron)
domains:
  - tooling
  - token-budget
  - mcp
  - developer-experience
implementation_status: none
staleness_months: 6
last_reviewed: 2026-05-12
drift_check_paths:
  - "platform/templates/mcp_config.wsl.json"
  - "platform/templates/mcp_config.dev-desktop.json"
  - "platform/scripts/sync-mcp-config.sh"
  - "platform/scripts/gen-mcp-config.sh"
  - "platform/.windsurf/workflows/session-start.md"
---

# ADR-197: Repo-aware MCP Tool Pruning for Cascade

| Metadata | |
|----------|---|
| **Status** | Proposed (v1.0) |
| **Date** | 2026-05-12 |
| **Author** | Achim Dehnert |
| **Depends On** | ADR-113, ADR-176, ADR-186 |
| **Complements** | `docs/concepts/token-reduction-strategy.md` |

---

## Context

The Windsurf/Cascade IDE loads JSON schemas of all enabled MCP tools into every conversation's system prompt. Order-of-magnitude estimate:

| Source | Tokens (approx.) |
|---|---|
| Orchestrator MCP alone (~32 tools) | 15–50 k |
| All 9 MCP servers combined | 30–100 k |
| Tools typically used per session | 5–15 (= ~5–15 k tokens) |

Net result: **50–85 % of the tool-schema budget is dead weight** in any given session.

### Current mitigation and its failure modes

The user's `~/.codeium/windsurf/mcp_config.json` carries a hand-curated `disabledTools` array per server. Observed problems:

1. **Drift from SSoT.** The list lives in the user-local config file. The platform-SSoT template (`platform/templates/mcp_config.wsl.json`) has no `disabledTools`. The `sync-mcp-config.sh` script overwrites the user-local file from the template via `sed > target`, so the next sync would erase the list silently. The current curation only survives by *not* running the sync script.

2. **One-size-fits-all.** The same disabled set applies to every workspace. A risk-hub session and a meiki-hub session see identical tool inventories, even though their tool usage diverges.

3. **Silent breakage.** On 2026-05-12, `/session-ende` for pptx-hub appeared to run cleanly and report `Created memory ...`, but pgvector remained empty. Root cause: `agent_memory_search/upsert/context` was in `disabledTools`, so Cascade silently fell back to its built-in `create_memory` (Windsurf-internal store, **not** orchestrator pgvector). Phase 2 of the workflow was unreachable. Verified by checking pgvector before and after the workflow run — no `session:2026-05-12:*-pptx-hub` entry was created. The workflow fix in PR #131 corrects the prefix and API, but does not address the underlying disabledTools fragility.

### Why this is the right next step

This ADR is one of three complementary token-reduction levers tracked in `docs/concepts/token-reduction-strategy.md`:

| Lever | Mechanism | Status |
|---|---|---|
| **Session-discipline** | shorter turns, fewer rollovers | doc, manual |
| **Model routing** | `/model sonnet` for cheap turns | doc + ADR-195 |
| **MCP tool pruning** | this ADR | proposed |

Tool-schema bloat is the only one of the three not yet addressed by an architectural decision.

## Decision Drivers

- **Token-budget reduction** is the primary goal — quota-bound on Max-plan, paid per-token on overflow.
- **Source-of-truth restoration**: `disabledTools` should be *computed*, not hand-edited, so it survives `sync-mcp-config.sh` and remains reviewable.
- **Repo-specific tailoring**: a session in meiki-hub does not need playwright; a session in a frontend repo does not need iil-adrfw.
- **Self-healing**: the system should learn which tools each repo uses from actual session data, not require manual curation per repo.
- **Fail-safe over fail-fast**: a missing tool must degrade gracefully (Cascade still works, possibly with a "tool unavailable" message and a one-line re-enable hint), not block the session.
- **Bootstrap-friendliness**: a new repo with no profile data must still work — degrade to the full catalog rather than fail closed.

## Considered Options

### Option A — Status quo (hand-maintained `disabledTools`)

**Pro:** zero engineering work.
**Con:** drift-prone (just demonstrated, twice — drift from template SSoT plus silent agent_memory breakage), one-size-fits-all, requires manual updates as the catalog evolves.

Rejected. Already in production; failure modes are now documented.

### Option B — Static `disabledTools` in the platform template

Push the current `disabledTools` list into `platform/templates/mcp_config.wsl.json` and update `sync-mcp-config.sh` to preserve it.

**Pro:** restores SSoT, ~0.5 PT effort.
**Con:** still one-size-fits-all; still requires manual curation; still requires user-visible workflow edits when a new tool is needed.

Partially mitigates problem 1, ignores problems 2 and 3. Rejected as a stand-alone solution.

### Option C — Repo-aware pgvector-backed pruning *(chosen)*

3-layer system that generates `mcp_config.json` per `/session-start` based on the active repo's tool usage profile in pgvector.

```
┌─ Layer 1: Tool Catalog (pgvector) ─────────────────────┐
│  entry_id = tool:<server>:<name>                        │
│  entry_type = repo_context                              │
│  content = name, description, server, ~params summary   │
│  tags = ["tool-catalog", server, action_codes...]       │
│  Refresh: daily cron, tools/list per MCP server         │
└─────────────────────────────────────────────────────────┘
                │
                ▼ joined per repo profile
┌─ Layer 2: Repo→Tool Profile (pgvector) ────────────────┐
│  entry_id = profile:<repo>                              │
│  entry_type = repo_context                              │
│  content = ranked tool list                             │
│  Source A (cold): grep .windsurf/workflows/*.md for     │
│                   mcp[N]_* and orchestrator/* tokens    │
│  Source B (warm): "tools-used" tags on session memory   │
│                   entries from /session-ende workflow   │
│  Ranking: frequency × 30d half-life decay (ADR-113)     │
└─────────────────────────────────────────────────────────┘
                │
                ▼ generated
┌─ Layer 3: mcp_config.json Generator ───────────────────┐
│  Script: platform/scripts/gen-mcp-config.sh             │
│  Input:  TARGET_REPO + Catalog + Profile + Whitelist    │
│  Output: ~/.codeium/windsurf/mcp_config.json            │
│          with disabledTools = catalog ∖ (profile ∪ WL)  │
│  Trigger: new Phase in /session-start workflow          │
│  Cascade hot-reloads (verified 2026-05-12, this ADR)    │
└─────────────────────────────────────────────────────────┘
```

#### Whitelist (never pruned)

Tools that are cross-repo essential and would cause visible breakage if missing:

| Tool group | Rationale |
|---|---|
| `mcp__github__*` | issue/PR/file management is cross-repo |
| `mcp__orchestrator__agent_memory_*` | session-start/end Phase 2 + cross-session memory |
| `mcp__outline__*` | shared knowledge base, used in nearly every workflow |
| `mcp__iil-adrfw__*` | ADR creation/validation — used wherever ADRs are touched |

The whitelist is configurable in `platform/templates/mcp_pruning_whitelist.yaml`; ADRs are not the right granularity to maintain it.

#### Cold-start strategy

A new repo with no `profile:<repo>` entry falls back to the full catalog (i.e. no pruning, identical to status quo). After 3–5 sessions of warm-source data accumulation, the profile reaches usable density.

A conservative default cap is applied: keep **Top-30** by score even if more tools appeared in the workflow grep. This trades some token savings for fewer false-negatives during the warm-up window.

#### Hot-reload (verified)

In a controlled test on 2026-05-12: removing three tools from `disabledTools` and saving the file made those tools available in the active Cascade window without a window reload. Cascade re-reads `mcp_config.json` opportunistically. This means the generator can write at `/session-start` time without UX friction.

Caveat: the test covered the `disabledTools` array specifically. Other config-level changes (e.g. adding/removing servers) may behave differently and have not been verified — out of scope for this ADR.

### Option D — Server-side filtering

Modify the orchestrator MCP server to expose a filtered tool list based on an auth header carrying the active repo.

**Pro:** centralised, no client-side complexity.
**Con:** requires server changes per MCP. The MCP protocol does not have a standard "filter tools per session" concept. Other servers (github, outline, playwright) are out of our control. Invasive, fragile, partial coverage.

Rejected.

## Decision

Adopt **Option C — Repo-aware pgvector-backed pruning** as designed above.

## Consequences

### Positive

- Token savings: estimated 50–70 % on tool-schema budget. Concrete measurement pending Cascade telemetry instrumentation (see Open Questions).
- SSoT restoration: `disabledTools` becomes a *computed artifact* per session — surviving the next `sync-mcp-config.sh` run because it is rebuilt at `/session-start`.
- Self-learning: profile improves automatically as sessions accumulate `tools-used` tags in memory.
- Repo-specific tailoring: meiki-hub session does not pay for playwright tokens; risk-hub does not pay for citizen-portal tokens.
- Diagnostic surface: generator can log "tool X is in catalog but not in any profile" or "tool Y is required by a workflow but absent from catalog" — surfaces drift earlier.
- Companion benefit for PR #131-class bugs: if a workflow references a tool that the profile would have disabled, the generator can refuse to write the config and emit a warning — prefix-mismatch and API-version-drift become observable.

### Negative

- **Cold-start tax**: a new repo gets full catalog for the first 3–5 sessions (no savings). Mitigated by the warm-source learning curve being fast.
- **False negatives**: if a tool is needed mid-session but absent from profile, Cascade reports "tool not available". User must then either re-enable manually or wait for the profile to update at next session. Mitigated by Top-30 default cap and Whitelist.
- **New runtime dependency**: `/session-start` now requires pgvector reachability. If pgvector is down, the generator must degrade gracefully — fall back to "write full catalog" rather than "block session start".
- **Generator complexity**: ~150–250 LOC across three scripts. Maintained in `platform/scripts/`, covered by drift_check_paths above.

### Risks

- Cascade hot-reload semantics could change in a future Windsurf release. Mitigation: keep the generator's output identical in shape to the existing manually curated config; failure mode regresses to status quo, not worse.
- pgvector storage costs grow with `tool:*` catalog size, but the catalog is bounded (~200 entries × ~500 tokens content ≈ 100 k vector cells — negligible).
- Profile poisoning by an unusual session (one-off use of an obscure tool) is bounded by the 30 d decay — a tool used once will fall out of the top ranks within ~2 months of inactivity.

## Implementation Plan

| Phase | Effort | Deliverable | Path |
|---|---|---|---|
| 1 | 1.0 PT | Catalog builder script + first run | `platform/scripts/build-tool-catalog.py` |
| 2 | 0.5 PT | Profile builder (cold = grep workflows, warm = session memory `tools-used` tags) | `platform/scripts/build-repo-tool-profile.py` |
| 3 | 0.5 PT | Generator script | `platform/scripts/gen-mcp-config.sh` |
| 4 | 0.3 PT | `/session-start` workflow Phase 0.x integration | `platform/.windsurf/workflows/session-start.md` |
| 5 | 0.5 PT | `/session-ende` workflow extension — write `tools-used` tag onto session memory entries | `platform/.windsurf/workflows/session-ende.md` |
| 6 | tbd | Telemetry: log per-session tool-token-usage to validate savings | downstream |

**Total to operational MVP: ~2.3 PT.** Phase 6 is monitoring and can lag.

### Dependencies

- Phase 5 depends on the PR #131 fix being merged — Phase 2 must write to pgvector at all before we can extract `tools-used` from those entries.
- Phase 1 requires that the orchestrator MCP `agent_memory_upsert` is reachable from the catalog-builder host (cron host TBD — see Open Questions).

## Confirmation (Definition of Done)

1. `~/.codeium/windsurf/mcp_config.json` is generated from `gen-mcp-config.sh` at every `/session-start`, never hand-edited.
2. `platform/templates/mcp_config.wsl.json` carries no `disabledTools` array; the computed list lives only in the generated user file.
3. A new repo gets full catalog on its first session; by its 5th session, its profile in pgvector contains at least 10 tool entries with non-zero frequency.
4. Measured token-budget reduction post-deploy: at least 30 % drop in tool-schema tokens per session vs. baseline (full-catalog equivalent). Method: per-session log of schema token count before/after.
5. Generator fails-safe: when pgvector is unreachable, it writes the full catalog (status quo) and logs a warning, instead of blocking session start.

## Open Questions

- [ ] **Telemetry source** for concrete token-reduction measurement. Cascade does not expose schema token counts directly. Option: estimate from `tiktoken`-counting the rendered config file.
- [ ] **Cron-host for catalog refresh**. Candidates:
  - dev-hub Celery beat (already runs ADR-186 nightly cron) — preferred, consistent with existing platform agent pattern
  - GitHub Actions cron — works but adds external coupling
  - Hetzner systemd timer — simplest, but lives outside the platform-agents framework
- [ ] **Whitelist as ADR or as config?** Decision: config (`platform/templates/mcp_pruning_whitelist.yaml`), reviewable in PR. ADR amendments are the wrong granularity for tweaking which tools are essential.
- [ ] **Per-server granularity**: should the generator also set `disabled: true` for an entire MCP server when its profile contribution is 0? Would save not just schemas but the server's startup cost. Defer to Phase 1 measurement.
- [ ] **Cold-source coverage**: grepping `.windsurf/workflows/*.md` finds tools mentioned in workflows, but misses tools used ad-hoc by Cascade. Is the workflow grep enough as cold-source, or do we also need a one-off seed pass scanning `~/.codeium/windsurf/cascade_log/` or similar?

## Changelog

- 2026-05-12: Initial proposal. Triggered by diagnosis of pptx-hub `/session-ende` Phase 2 silent failure (see PR #131) — surfaced the deeper structural problem of `disabledTools` drift and one-size-fits-all curation. Reload-test verified hot-reload behavior, enabling aggressive pruning without UX friction.
