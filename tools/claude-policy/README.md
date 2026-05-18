# claude-policy

Sync `~/.claude/policies/*.md` ↔ orchestrator shared memory (ADR-113 pgvector).

**Canonical source = this file** (versioned). `~/.claude/bin/claude-policy` ist
eine untrackte Kopie — sollte hierauf zeigen:

```bash
ln -sf "$(git rev-parse --show-toplevel)/tools/claude-policy/claude-policy" \
       ~/.claude/bin/claude-policy
```

## Transport (funktioniert standalone — kein „Skeleton" mehr)

Die Orchestrator-Memory hat **keine shell-aufrufbare HTTP/KV-API** und
`orchestrator_mcp` ist auf Dev-Maschinen nicht importierbar. Der bewiesene
standalone-Pfad (CC-Memory „Orchestrator MCP dead-session workaround",
angewandt 2026-05-13) ist **SSH + `docker exec`** gegen den Prod-Container
`mcp_hub_orchestrator_http`, der dasselbe Postgres-Backend wie die MCP-Tools
nutzt. Aufruf von `orchestrator_mcp.memory.store.upsert/search`.

- Python-Script vollständig via **stdin** in `docker exec -i … python -`
  (kein nested Quoting).
- Policy-Inhalt **base64-inline** im Script — **kein** File-Staging via
  `cat >`: ssh bewahrt argv-Grenzen nicht, der Remote-Shell re-parst die
  Args, ein `>` landet sonst auf dem Prod-Host statt im Container.
- Idempotent via `content_hash`-Dedup in `store.upsert`.

Env-Overrides:

| Var | Default |
|---|---|
| `ORCH_PROD_HOST` | `88.198.191.108` |
| `ORCH_CONTAINER` | `mcp_hub_orchestrator_http` |
| `ORCH_SSH_USER` | `root` |
| `CLAUDE_POLICY_STUB=1` | altes Stub-Verhalten, für *In-Claude*-Sessions die die `_orch_*`-Stubs durch native `orchestrator__*`-Tool-Calls ersetzen |

## Verwendung

```bash
claude-policy list                  # lokale + remote Policies
claude-policy diff                  # Drift anzeigen, keine Writes
claude-policy push                  # Dateien → orchestrator (sichere Richtung)
claude-policy push --only llm-routing
claude-policy pull [--only X] [-y]  # orchestrator → Dateien (advisory)
```

## Caveat

`agent_memory_*` ist **semantische Suche, kein exaktes KV**. `push` ist die
sichere Primärrichtung; `pull`/`diff` filtern Treffer auf exakten `entry_key`
und sind nur advisory. **Maßgeblich bleibt immer die Datei.**

Voraussetzungen: Python 3.10+ und SSH-Zugang zum Prod-Host.

## Stand

- 2026-05-17: Script von Stub → funktionsfähig (SSH/docker-exec, base64-inline,
  idempotent). Argv-Reparse-Bug beim Live-Test gefunden + behoben. README an
  Realität angepasst (vorheriges „autonomes CLI nicht möglich" war falsch).
  Verifiziert: list/push/diff Round-Trip, push idempotent, 6 Policies
  konvergieren (`0 differ`). Tracking: dev-hub#51, ersetzt mcp-hub#60.
