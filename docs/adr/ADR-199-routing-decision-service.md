---
status: proposed
date: 2026-05-13
decision-makers: [Achim Dehnert]
implementation_status: none
related: [ADR-068, ADR-084, ADR-116, ADR-115, ADR-196, mcp-hub#37, mcp-hub#39, mcp-hub#47, dev-hub#39, dev-hub#40]
---

# ADR-199: Routing Decision Service — Single Source of Truth für Model-Choice

## Status

Proposed — basiert auf der Drift-Inventur 2026-05-13 (siehe dev-hub#39 + mcp-hub#47).

## Context

ADR-068 etablierte eine deterministische Routing-Tabelle. ADR-116 + ADR-196 erweiterten sie um Outcome-Telemetrie und einen (Feature-Flag-OFF) Bandit. ADR-084 baut darauf Model-Registry + Quality-Tier-Workflows. **Drei separate ADRs für eine Frage** — und die Implementierung ist heute auf **fünf parallele Surfaces** verteilt:

| # | Surface | Authority | Konsumenten |
|---|---|---|---|
| 1 | `aifw_action_types` (devhub_db) | per-action_code DB-Lookup | aifw_bridge in orchestrator_mcp/headless |
| 2 | `model_route_configs` (orchestrator-DB) | per-(agent_role, complexity) DB-Lookup | orchestrator agent_team |
| 3 | `orchestrator_mcp/model_selector.py:_ROUTE_TABLE` | Code-Konstante | agent_team Workflows |
| 4 | `orchestrator_mcp/model_registry._FALLBACK` | Code-Konstante | DB-Fallback der ModelRegistry |
| 5 | Claude Code Sessions | User-`/model` | menschliche Bedienoberfläche |

Pre-Audit-Stand 2026-05-13:
- Surface 1: **1** action_code, default-Modell nicht auf Account verfügbar
- Surface 2: **8 von 16** Zeilen zeigten auf totes `claude-3.5-sonnet`
- Surface 3 + 4: live (PR #40), aber nicht synchron mit Surface 2
- Surface 5: $1577 / 48 h auf Opus 4.7 für überwiegend Tier-3-Arbeit (dev-hub#39)

Phase 0 (PR #47 + dev-hub#40) hat Surfaces 1+2 mit Surfaces 3+4 in Einklang gebracht. **4 von 5 Surfaces stimmen jetzt für `(developer, complex)` überein.** Aber das ist eine Daten-Hygiene-Korrektur, kein Architektur-Fix — die Surfaces existieren weiter parallel.

## Decision

Ein **Routing Decision Service** im orchestrator-MCP wird die kanonische Quelle der Model-Choice für *alle* Konsumenten — orchestrator-intern, Claude-Code-Sessions, Headless-Runs, ad-hoc Skripte aus beliebigem Repo.

### API-Kontrakt

```
POST /v1/route
Content-Type: application/json

{
  "caller":        "claude_code" | "headless" | "ad_hoc" | "agent_team" | "skill",
  "repo":          "mcp-hub",
  "task": {
    "action_code":         "review_adr",          // optional — wenn gesetzt, primary lookup-key
    "agent_role":          "developer",           // optional — secondary fallback-key
    "complexity_hint":     "complex",             // trivial|simple|moderate|complex|architectural
    "description":         "...",                 // optional — für Bandit-Feature-Extraction
    "expected_tokens_in":  50000,                 // optional — für Cost-Estimate
    "expected_tokens_out": 5000
  },
  "tenant_id":     1,
  "policy_overrides": {                            // optional — Repo-spezifisch
    "max_tier":           4,
    "compliance_class":   "none" | "eu" | "pii"
  }
}

→ 200 OK
{
  "model":          "anthropic/claude-sonnet-4-6",
  "fallback_model": "groq/llama-3.3-70b-versatile",
  "tier":           "standard",
  "provider":       "anthropic",
  "reason":         "AIFW action_code 'review_adr' → Tier 3 (multi-step reasoning)",
  "source":         "aifw" | "model_route_configs" | "policy_default",
  "cost_estimate_usd": 0.165,
  "decision_id":    "uuid",
  "policy_version": "2026-05-13"
}
```

### Resolution-Reihenfolge (deterministisch, fallback-cascade)

1. `aifw_action_types.code == task.action_code AND is_active` (Authority Tier 1)
2. `model_route_configs WHERE agent_role=… AND complexity_hint=…` (Authority Tier 2)
3. `model_registry._FALLBACK[tier_from_policy(complexity_hint)]` (Authority Tier 3 — code-Fallback)
4. `_DEFAULT_REVIEW_MODEL`-Style Hardcode (Authority Tier 4 — emergency)

Jeder Lookup-Hop wird in `source` festgehalten + in `routing_decisions` persistiert.

### Schema

```sql
CREATE TABLE routing_decisions (
    id              BIGSERIAL PRIMARY KEY,
    decision_id     UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    caller          TEXT NOT NULL,
    repo            TEXT,
    tenant_id       BIGINT NOT NULL,
    action_code     TEXT,
    agent_role      TEXT,
    complexity_hint TEXT,
    chosen_model    TEXT NOT NULL,
    fallback_model  TEXT,
    tier            TEXT NOT NULL,
    source          TEXT NOT NULL,   -- 'aifw'|'model_route_configs'|'policy_default'|'emergency'
    reason          TEXT,
    cost_estimate_usd NUMERIC(12,6),
    policy_version  TEXT,
    outcome_success    BOOLEAN,       -- nullable, set by caller after completion
    outcome_duration_ms INTEGER,
    outcome_cost_usd   NUMERIC(12,6),
    outcome_reported_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Outcome-Felder optional und werden vom Caller via `POST /v1/route/{decision_id}/outcome` nachgereicht. ADR-196 Stufe 3 (Bandit) kann dann darüber lernen.

### Migration der bestehenden Surfaces

| Phase | Surface | Aktion |
|---|---|---|
| **1** | aifw_action_types | bleibt Authority Tier 1 — wird über `/v1/route` *gelesen* |
| **1** | model_route_configs | bleibt Authority Tier 2 — wird über `/v1/route` *gelesen* |
| **2** | model_selector._ROUTE_TABLE | wird zu **Cache** des `/v1/route`-Output (DB lookup einmal pro Prozessstart) |
| **2** | model_registry._FALLBACK | bleibt als Tier-3-Fallback (Service kann offline sein) |
| **3** | Claude Code Session | Pre-session Hook + `/route`-Slash-Command, Routing-API gibt initial `/model`-Empfehlung |
| **4** | Per-Repo `.iil-routing.yaml` | Reads als `policy_overrides`-Parameter — optional, repo-spezifisch |

### Compliance + Budget-Gates

Die Routing-Decision wird sofort *abgelehnt* (HTTP 422 + `reason`), wenn:
- `compliance_class=eu` aber chosen_model ist nicht in `mistral/|ollama/`
- `compliance_class=pii` aber chosen_model verlässt das eigene Rechenzentrum
- Per-tenant-Daily-Budget bereits überschritten → automatisches Downgrade auf Tier 2 oder lower

## Consequences

### Positive
- **1 Antwort auf 1 Frage**: jede Komponente sieht die gleiche Routing-Entscheidung.
- **Auditierbar**: jede Decision ist mit decision_id rückverfolgbar; ADR-196's Outcome-Tracking bekommt einen sauberen Hook.
- **Compliance-fähig**: Repo-Override für `ttz-hub`/`meiki-hub` wird Datenmodell, nicht Code-Konvention.
- **Bandit-bereit**: Stufe 3 von ADR-196 kann live geschaltet werden ohne neue Datenmodell-Änderung.

### Negative
- **Neuer Service** = neue Failure-Mode. Mitigiert durch deterministischen Fallback-Cascade (Tier 3 + Tier 4 sind code-lokal).
- **Caller-Migration**: 5 bestehende Konsumenten müssen umgestellt werden. Über Phasen 1-4 verteilt (siehe oben), nicht im Big-Bang.
- **Initiale Latenz** pro entry-point: +1 DB-Round-Trip pro Routing-Entscheidung. Mitigiert durch 5-min in-memory Cache (analog zu ModelRegistry).

### Neutral
- ADR-068 wird nicht reversed, aber **subsumed**: die _ROUTE_TABLE bleibt als Default-Mapping bestehen, sie ist nur nicht mehr direkte Authority.
- ADR-084's Model-Registry-Workflows bleiben unverändert — sie schreiben in die DB-Tabellen die `/v1/route` jetzt liest.

## Implementierungs-Phasen

1. **Phase 1** (~1 Woche): Endpoint + `routing_decisions` Tabelle + headless_run als erster Konsument.
2. **Phase 2** (~1 Woche): ModelSelector wird Cache; agent_team Workflows lesen `/v1/route`. Plus `/route`-Slash-Command in Claude Code + Pre-session-Hook.
3. **Phase 3** (~2 Wochen): ADR-196 Stufe 3 Bandit aktiviert; Outcome-Reporting durch alle Caller; Drift-Cards im Controlling-Dashboard.
4. **Phase 4** (~1 Woche): Per-Repo `.iil-routing.yaml` overrides; Compliance-Gates + Daily-Budget-Caps live.

## Open Questions

1. **Routing-API in orchestrator-MCP oder eigener Service?** Empfehlung: zunächst Mount in orchestrator-MCP (gleiches Deploy, gleiche DB-Connection). Später Spin-off möglich wenn Cross-Cutting Concern groß genug.
2. **Caller-Authentication.** Heute: orchestrator-API-Key Bearer (PR #31). Reicht für Phase 1; für Phase 4 (Per-Repo-Overrides) braucht es Tenant-Scoping.
3. **AIFW vs model_route_configs Konflikt-Auflösung.** Was wenn Surface 1 *und* Surface 2 für die gleiche Achse antworten? Empfehlung: action_code (Surface 1) wins, weil semantischer Code stärkere Signal trägt als die Achse (agent_role, complexity_hint).

## Drift Check Paths

```
mcp-hub/orchestrator_mcp/model_selector.py
mcp-hub/orchestrator_mcp/model_registry.py
mcp-hub/orchestrator_mcp/models/model_route_config.py
mcp-hub/orchestrator_mcp/headless/services/aifw_bridge.py
mcp-hub/llm_gateway/migrations/0044_*.sql
dev-hub/sql_migrations/0001_aifw_*.sql
dev-hub/sql_migrations/0002_aifw_seed_*.sql
~/.claude/policies/llm-routing.md
~/.claude/policies/session-routing.md
```

## Changelog

- 2026-05-13: Initial. Geschrieben nach Drift-Inventur (5 Surfaces, 4 mit live-Drift), Phase 0 Hygiene-Migration (mcp-hub#47 + dev-hub#40) und dem $1577/48h Spend-Befund (dev-hub#39).
