# claude-policy

Sync `~/.claude/policies/*.md` ↔ orchestrator shared memory (ADR-113 pgvector).

**Canonical source = this file** (versioned). `~/.claude/bin/claude-policy` ist
eine untrackte Kopie — sollte hierauf zeigen:

```bash
ln -sf "$(git rev-parse --show-toplevel)/tools/claude-policy/claude-policy" \
       ~/.claude/bin/claude-policy
```

## Warum „Skeleton"

Die Orchestrator-Memory ist **MCP-only** (SSE, `orchestrator.iil.pet`) — es
gibt **keine shell-aufrufbare HTTP/KV-API**. Ein vollständig autonomes CLI ist
darum nicht möglich. Design: aus einer **Claude-Code-Session mit geladenem
`orchestrator__*`** (dev-hub/mcp-hub/bfagent) „run `claude-policy <cmd>`" —
Claude ersetzt die `_orch_*`-Stubs durch echte `agent_memory_*`-Tool-Calls
(Mapping im Skript-Docstring). Vorher (vor diesem Fix) referenzierte das
Skript die **entfernten** `memory_get/_set/_list`-Tools → unbrauchbar.

## Caveat

`agent_memory_*` ist **semantische Suche, kein exaktes KV**. `push` ist die
sichere Primärrichtung; `pull`/`diff` filtern Treffer auf exakten `entry_key`
und sind nur advisory. **Maßgeblich bleibt immer die Datei.**

## Runbook — qwen-EOL Punkt (3) schließen

Aus einer **dev-hub/mcp-hub-Claude-Session** (Orchestrator-MCP gesund):

```
claude-policy push --only llm-routing
```
Claude übersetzt das in **ein** `orchestrator__agent_memory_upsert`
(`entry_key="policy:llm-routing"`, `entry_type="decision"`, content =
`~/.claude/policies/llm-routing.md`). Danach verifizieren:

```
orchestrator__agent_memory_search(query="policy:llm-routing")
```
muss den aktualisierten Eintrag liefern (Tier-1a Cerebras = `gpt-oss-120b`;
`qwen-3-235b` deprecated 2026-05-27). Damit ist qwen-EOL **(3)** erledigt.
