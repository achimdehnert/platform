# Policy: Orchestrator MCP

**Trigger words:** orchestrator, mcp, memory, routing, headless

## What it is

The orchestrator is an MCP server at `https://orchestrator.iil.pet/sse`
hosted by `~/github/mcp-hub/orchestrator_mcp/`. It provides:

- **Routing**: which LLM/model for a given action_code (DB-driven, via `aifw`)
- **Memory**: cross-session shared state — current API is
  `agent_memory_search/upsert/context` (pgvector + temporal decay, ADR-113).
  The legacy `memory_get/set/list` key-value tools no longer exist.
- **LLM-Calls**: dispatch via aifw with usage tracking
- **Headless runs**: long-running Claude Code agents in containers

Tool-prefix when loaded: `orchestrator__*`.

## When to query it

**Before** suggesting an org-specific default, check whether the orchestrator
has a live policy that overrides the file-based default in
`~/.claude/policies/`. Specifically: any `policy:*` or `convention:*` entry.

Pseudocode:

```
if orchestrator MCP available:
    hits = orchestrator__agent_memory_search(query="policy:<topic>")
    if hits: use top hit
    else: fall back to ~/.claude/policies/<topic>.md
else:
    use ~/.claude/policies/<topic>.md
    explicitly tell user "orchestrator not loaded in this session"
```

## Where it is NOT loaded

- Sessions started outside of dev-hub/bfagent/mcp-hub workspaces may not have
  the MCP bound. Check tool list at session start.
- Headless/CI runs always have it (that's its main consumer).
- The `meiki-hub` workspace currently does **not** bind it (as of 2026-05-11).

## Syncing files ↔ orchestrator

`~/.claude/bin/claude-policy` (`push`/`pull`/`diff`/`list`) is the sync CLI
and is **functional standalone** since 2026-05-17. Transport: SSH +
`docker exec` against the prod container `mcp_hub_orchestrator_http`, which
shares the Postgres backend with the MCP tools; it calls
`orchestrator_mcp.memory.store.upsert/search` directly. Idempotent
(content_hash dedup). `push` writes `entry_key=policy:<topic>`,
`entry_type=decision`, tag `synced-from-file`.

- Standalone: `claude-policy push` from any shell with SSH access to prod.
- In a Claude session with `orchestrator__*`: set `CLAUDE_POLICY_STUB=1` and
  Claude substitutes the stubs with native `agent_memory_upsert` calls.
- Env overrides: `ORCH_PROD_HOST` / `ORCH_CONTAINER` / `ORCH_SSH_USER`.

Versioning home of the CLI: `platform/tools/claude-policy/` (canonical,
merged via platform#190; `~/.claude/bin/claude-policy` should symlink there).
The legacy `memory_get/set/list` API it once stubbed no longer exists —
irrelevant now, the CLI targets `agent_memory_*`/`store`. See dev-hub#51.

## Schlüssel-Rotation (Pflichtweg — Lehre aus mcp-hub#179)

Der API-Schlüssel des Orchestrators existiert an genau **zwei** Orten:
Schlüsselkasten (`~/.secrets/orchestrator_mcp_api_key`, **kanonisch**) und
Server-Schloss (`hetzner-prod:/opt/mcp-hub/.env.prod`, `ORCHESTRATOR_MCP_API_KEY`).

**Regel:** Eine Rotation ändert IMMER beide Orte im selben Arbeitsgang —
Schlüsselkasten zuerst (kanonisch), dann Server + Container-Recreate. Ein Tausch
nur auf dem Server ist die Fehlerklasse, die den Orchestrator vom
13.–17.07.2026 vier Tage still lahmlegte (Rotation am 12.07. ohne
Heimat-Nachzug; Chronik: mcp-hub#179).

**Wächter:** `platform/tools/orchestrator_key_sync_check.sh` vergleicht beide
Orte per Prüfsumme (Werte erscheinen nie; `--selftest` beweist die
Rot-Fixture). Empfohlen: bei Session-Start in Orchestrator-nahen Repos und
nach jeder Rotation einmal laufen lassen. Exit 1 = Drift-Alarm.

## Changelog

- 2026-05-11: Initial reference. Documented after session miss where I should
  have queried orchestrator for LLM-routing default but didn't.
- 2026-05-12: Updated to reflect current Memory API (`agent_memory_*`, ADR-113);
  noted CLI/API mismatch. Pushed from `~/.claude/policies/orchestrator.md` to
  orchestrator memory.
- 2026-05-17: claude-policy rewritten stub→functional (SSH/docker-exec
  transport, base64-inline, idempotent). "Known limitation" removed.
- 2026-05-18: Versioning home corrected to `platform/tools/claude-policy/`
  (merged platform#190; supersedes the briefly-recommended `mcp-hub/scripts/`
  which collided with platform#186). Double-vendor reconciliation, dev-hub#51.
