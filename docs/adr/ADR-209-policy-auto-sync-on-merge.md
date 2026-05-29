---
status: accepted
date: 2026-05-18
decision-makers: [Achim Dehnert]
implementation_status: in-progress
related: [ADR-113, dev-hub#51, platform#190, platform#193]
---

# ADR-209: Org-Policy Auto-Sync to Orchestrator Memory on Merge

## Status

Accepted.

## Context

Org-wide policies live in `platform/policies/*.md` (SSoT, vendored in
platform#193). Headless/CI agents do **not** read these files — they read the
orchestrator pgvector memory (ADR-113) via
`agent_memory_search(query="policy:<topic>")`. The bridge between the two is
`tools/claude-policy/claude-policy push` (platform#190).

Today that bridge is **manual**: a human runs `claude-policy push` from a
session with prod access. Failure mode: a policy change is merged but nobody
pushes it — agents keep acting on the stale policy until someone remembers.
This is exactly the drift the whole dev-hub#51 thread set out to remove.

## Decision

A GitHub Action **auto-syncs on merge**:

- `on: push` to `main`, `paths: ["policies/**"]` (+ `workflow_dispatch`).
- `runs-on: [self-hosted, prod]` — the orchestrator container is local on
  that host, so the sync uses **local `docker exec`, no SSH, no key**
  (new `ORCH_LOCAL=1` mode in the CLI; `CLAUDE_POLICY_DIR` points at the
  checked-out `policies/`).
- Step = `claude-policy push`. Idempotent: `store.upsert` skips on unchanged
  `content_hash`, so re-runs and no-op merges cost nothing.

The merge-time **PR review remains the human gate**. The Action only
propagates what was already approved into git.

## Considered Options

1. **Status quo (manual push)** — drift-prone; the recurring failure above.
2. **Cron poll** — bounded drift window + still needs the same tool; no
   advantage over push-triggered, just latency.
3. **Push-triggered Action (chosen)** — immediate, idempotent, minimal.
4. **Orchestrator pulls from git** — inverts ownership, new infra in the MCP
   service; disproportionate for a 6-file mirror.

## Consequences

**Positive**

- No policy drift between git SSoT and the memory agents consume.
- Single tool (`claude-policy`) for manual *and* automated sync — the
  `ORCH_LOCAL` / `CLAUDE_POLICY_DIR` additions are backward-compatible.

**Negative / risk** (the trade-off this ADR exists to record)

- An approved-but-wrong policy merge **auto-propagates to all agents**.
  Mitigations: PR review is the gate; the orchestrator entry is *advisory*
  while the file stays authoritative (per `policy:orchestrator`); rollback
  is `git revert` → the Action re-runs and re-converges (idempotent).
- Hard dependency on the `[self-hosted, prod]` runner being online. Failure
  is **visible** in the Actions tab and **safe to re-run** (`workflow_dispatch`
  or re-push); no silent partial state (`upsert` is per-file idempotent).

## Scope

No new external dependency, no new service boundary, reversible (delete the
workflow). Lightweight per `policy:adr-threshold`, recorded only because it
introduces an **automated cross-cutting write path** into shared agent memory
— worth a future challenger's attention. The file-vendoring half (Phase 2a)
deliberately shipped without an ADR (pure pattern-following, platform#193).
