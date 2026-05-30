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
| `ORCH_LOCAL=1` | docker-Befehl auf *diesem* Host ausführen (kein ssh) — für den `[self-hosted, prod]`-CI-Runner, wo der Container lokal ist (ADR-209) |
| `CLAUDE_POLICY_DIR` | Policy-Quellverzeichnis (default `~/.claude/policies`); CI setzt `$GITHUB_WORKSPACE/policies` |
| `CLAUDE_POLICY_STUB=1` | altes Stub-Verhalten, für *In-Claude*-Sessions die die `_orch_*`-Stubs durch native `orchestrator__*`-Tool-Calls ersetzen |

## CI-Auto-Sync (ADR-209)

`.github/workflows/sync-policies-to-orchestrator.yml` ruft bei jedem Merge auf
`main` der `policies/**` dieses Skript auf dem `[self-hosted, prod]`-Runner mit
`ORCH_LOCAL=1 CLAUDE_POLICY_DIR=$GITHUB_WORKSPACE/policies` auf. Idempotent
(content_hash), No-Op wenn unverändert.

## Verwendung

```bash
claude-policy list                  # lokale + remote Policies
claude-policy diff                  # Drift anzeigen, keine Writes
claude-policy push                  # Dateien → orchestrator (sichere Richtung)
claude-policy push --only llm-routing
claude-policy pull [--only X] [-y]  # orchestrator → Dateien (advisory)

# Beliebigen Memory-Entry schreiben (jeder entry_type) — MCP-unabhängig:
echo "<content>" | claude-policy remember \
  --key session:2026-05-30:platform --type context \
  --title "Session …" --tags "session,platform"
claude-policy remember --key … --type lesson_learned --title … --content "…"
```

### `remember` — Transport: der `/run`-REST-Shim

Die orchestrator-MCP-Tools sind über die **SSE-Bindung unbrauchbar**:
`list_tools` klappt, aber **jeder `tools/call` → `-32602`** (verifiziert
2026-05-30, auch das argumentlose `workflow_list`). Root Cause ist **nicht**
Signatur/Schema (deployed == source, flat, per Prod-Check bestätigt) und
**nicht** nginx (`/run` liefert sauber 401 → POST wird korrekt proxied),
sondern der **SSE-Per-Prozess-Session-State** (server.py-Lifespan-Kommentar):
bricht der `/sse`-Stream ab, ist die `session_id` verwaist → jeder folgende
`tools/call` scheitert.

`remember` ruft daher `agent_memory_upsert` über den **stateless
`/run`-REST-Endpunkt** des Servers (`handle_run` → `_call_tool_inner`, dieselbe
Dispatch-Tabelle wie die MCP-Tools — Single Source of Truth). Vorteile ggü. dem
ssh+docker-Pfad: **kein Shell-Hop, kein Per-Prozess-Session-State, strukturiertes
JSON in/out, kein base64.** Die robuste Basis für `session-ende` Phase 2.

**Auth/Config (env, nie eingebettet):**

| Var | Default |
|---|---|
| `ORCHESTRATOR_RUN_URL` | `https://orchestrator.iil.pet/run` |
| `ORCHESTRATOR_MCP_API_KEY` | *(erforderlich; ≠ MCP-SSE-Bearer)* — aus `~/.secrets` sourcen |
| `ORCHESTRATOR_RUN_TIMEOUT` | `30` |

Sauber sourcen (Tool ← env ← Secrets-Layer):

```bash
set -a; . ~/.secrets/orchestrator.env; set +a
echo "<content>" | claude-policy remember --key … --type context --title "…"
```

`push`/`pull`/`list`/`diff` nutzen weiterhin den ssh+docker-Pfad; sie können
in einem Folge-PR ebenfalls auf `_orch_run` migrieren, um den docker-Hack ganz
abzulösen.

## Caveat

`agent_memory_*` ist **semantische Suche, kein exaktes KV**. `push` ist die
sichere Primärrichtung; `pull`/`diff` filtern Treffer auf exakten `entry_key`
und sind nur advisory. **Maßgeblich bleibt immer die Datei.**

Voraussetzungen: Python 3.10+ und SSH-Zugang zum Prod-Host.

## Stand

- 2026-05-30: `remember`-Subcommand ergänzt — generischer Memory-Upsert (jeder
  `entry_type`, Enum-validiert) über den **stateless `/run`-REST-Shim**
  (`_orch_run`), nicht das kaputte MCP-SSE. Grund: orchestrator-MCP `tools/call`
  global `-32602` (Root Cause = SSE-Per-Prozess-Session, nicht Signatur/nginx —
  beides per Prod-Check ausgeschlossen). Macht `session-ende` Phase 2
  MCP-unabhängig. Env-getrieben (`ORCHESTRATOR_MCP_API_KEY`). STUB-getestet
  (Syntax, Arg-Parsing, Enum, Unicode, fehlender-Key-Pfad).
- 2026-05-17: Script von Stub → funktionsfähig (SSH/docker-exec, base64-inline,
  idempotent). Argv-Reparse-Bug beim Live-Test gefunden + behoben. README an
  Realität angepasst (vorheriges „autonomes CLI nicht möglich" war falsch).
  Verifiziert: list/push/diff Round-Trip, push idempotent, 6 Policies
  konvergieren (`0 differ`). Tracking: dev-hub#51, ersetzt mcp-hub#60.
