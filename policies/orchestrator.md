# Policy: Orchestrator MCP
<!-- rule_class: B | assessed_with: claude-fable-5 | reassess_by: 2027-08-01 (KONZ-038 D4) -->

**Trigger words:** orchestrator, mcp, memory, routing, headless

## What it is

The orchestrator is an MCP server at `https://orchestrator.iil.pet/sse`
hosted by `~/github/mcp-hub/orchestrator_mcp/`.

**Rolle seit ADR-300 (accepted 2026-09-02): Gedächtnis + Audit — nicht Ausführung.**

- **Memory** (authoritative): cross-session shared state — current API is
  `agent_memory_search/upsert/context` (pgvector + temporal decay, ADR-113).
  The legacy `memory_get/set/list` key-value tools no longer exist.
- **Audit/Kosten** (authoritative): `session_stats`, `record_job_measurement`,
  `estimate_job`, `get_cost_estimate`, `check_recurring_errors`,
  `find_similar_errors`, `log_error_pattern`, `log_action`, `get_audit_log`,
  `discord_notify`. Routing-Wissen (welches Modell für welchen action_code)
  bleibt DB-getrieben via `aifw`.
- **Gate** (`check_gate`, `request_approval`): erst Autorität, wenn die Naht
  gebaut ist — blockierender `check_gate`-Hook in ≥ 2 Repos plus ein
  `log_action`-Konsument (ADR-300 D1, Kill-Gate-Bedingung). Bis dahin wirken
  Gates lokal über Claude-Code-Hooks.
- **Ausführung/Planung — deprecated (ADR-300 D2):** `plan_and_execute`,
  `delegate_subtask`, `agent_plan_task`, `agent_team_status`, `headless_run`,
  `workflow_*`, `run_*`, `deploy_check`, `review_adr`, `analyze_task`,
  `get_full_context`, `list_job_types`, `cascade_log_response`. Ersatz sind die
  Harness-Primitiven: Subagenten (Agent/Fork/Worktree), Workflows (Opt-in),
  `/loop`, Plan-Modus; unbeaufsichtigte Nachtläufe auf eigener Infrastruktur
  laufen als Actions-Cron auf self-hosted Runner mit `orchestrator_mcp.headless`
  als Bibliothek (ADR-186 OQ4). Ein deprecated Tool ohne benannten Konsumenten
  in `platform/skills/` oder `.windsurf/workflows/` wird zum Kill-Gate
  **2026-11-01** aus der Registrierung entfernt — Umsetzung mcp-hub#244.
  **Neue Skills dürfen diese Tools nicht mehr aufrufen.**

Tool-prefix when loaded: `mcp__orchestrator__*` (in der Tool-Liste der Session;
der frühere Eintrag `orchestrator__*` war der Windsurf-Ära-Prefix).

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

- Kein Verlass auf die Workspace-Herkunft: maßgeblich ist die Tool-Liste bei
  Session-Start (`mcp__orchestrator__*` vorhanden?), nicht das Repo.
- Headless/CI runs always have it (that's its main consumer).
- Seit der Aufnahme in die globalen `mcpServers` in `~/.claude/settings.json`
  ist der Server in **jedem** Workspace gebunden — auch `meiki-hub`
  (dessen `.mcp.json` bindet nur `atlassian`). Der frühere Eintrag
  "`meiki-hub` bindet ihn nicht (Stand 2026-05-11)" ist überholt.

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
- 2026-09-01: "Where it is NOT loaded" korrigiert — Orchestrator ist über die
  globalen `mcpServers` in `~/.claude/settings.json` workspace-übergreifend
  gebunden; in einer meiki-hub-Session sind die `mcp__orchestrator__*`-Tools
  nachweislich vorhanden.
- 2026-09-02: **Rolle nach ADR-300 (accepted) neu geschnitten** — Gedächtnis +
  Audit authoritative, Gate an die gebaute Naht gebunden, Ausführungs-/Planungs-
  Familie (19 Tools) deprecated mit Kill-Gate 2026-11-01 (mcp-hub#244); neue
  Skills rufen sie nicht mehr auf. Tool-Prefix auf `mcp__orchestrator__*`
  korrigiert (Audit 2026-09-02, platform#2606 E2).
