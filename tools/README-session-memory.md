# session-memory

Schreibt Session-Summaries / Error-Patterns in den pgvector-Store (ADR-113),
**ohne** dass der Orchestrator-MCP in der Session gebunden sein muss.

## Warum

`/session-ende` Phase 2 hing bislang an `mcp__orchestrator__agent_memory_upsert`.
Ist der MCP nicht gebunden (häufig ausserhalb dev-hub/mcp-hub/CI), wurde die
Summary **still übersprungen** und nur verbal auf „später nachziehen" vertagt →
Drift-Loch. Der pgvector-Container ist dagegen harter Pflicht-Check
(session-start Phase 0.5) — die zuverlässigere Schicht.

## Transport

Identisch zu `platform/tools/claude-policy` (ADR-209, „functional standalone"):
SSH + `docker exec` in den Prod-Container `mcp_hub_orchestrator_http`, der denselben
Postgres teilt wie die MCP-Tools. Container-seitig läuft der **authoritative**
`orchestrator_mcp.memory.store.upsert` → Embedding (`compute_embedding=True`) +
`content_hash`-Dedup macht der Container, nicht das Skript. Payload base64-inline.

## Nutzung

```bash
# Session-Summary
python3 platform/tools/session-memory write \
  --repo <repo> --title "Session <date> — <repo>" \
  --tag session --tag <repo> --content-file summary.md

# Error-Pattern
python3 platform/tools/session-memory write --repo <repo> --type error_pattern \
  --key "error:<repo>:<date>-<id>" --title "<symptom>" --content "Symptom…Fix…"

# Verifikation (exakter Key)
python3 platform/tools/session-memory get --key session:<repo>:<YYYYMMDD>
```

Content via `--content`, `--content-file FILE`, oder stdin (`… | session-memory write`).

## Env

| Var | Default | Zweck |
|---|---|---|
| `ORCH_PROD_HOST` | `88.198.191.108` | Prod-Host |
| `ORCH_SSH_USER` | `root` | SSH-User |
| `ORCH_CONTAINER` | `mcp_hub_orchestrator_http` | Orchestrator-Container |
| `ORCH_LOCAL` | — | `=1` → docker lokal (auf Prod-Host, kein ssh) |

## Grenzen

- Braucht SSH-Zugriff auf den Prod-Host (jeder Dev-Host hat ihn). Im Auto-Mode
  kann der Prod-Exec gated sein → einmalig freigeben oder via `!`.
- Fehlt zeitweise der Embedding-Provider, schreibt `store.upsert` die Zeile ohne
  Embedding; `memory_backfill_tool` (MCP) holt es idempotent nach.
