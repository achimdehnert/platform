---
status: proposed
date: 2026-05-14
decision-makers: [Achim Dehnert]
implementation_status: none
related: [ADR-068, ADR-084, ADR-115, ADR-116, ADR-196, mcp-hub#37, mcp-hub#39, mcp-hub#47, dev-hub#39, dev-hub#40, platform#135]
supersedes-draft: ADR-199 v1 (file renamed from `routing-decision-service` after advocatus-diaboli review surfaced cross-DB, push-outcome, self-attestation-compliance and 6th-surface contradictions)
---

# ADR-199 v2: Model-Routing-Library — Library-First, Service-Optional, Decision-as-Code

## Status

Proposed — v2 nach interner advocatus-diaboli Review der v1-Version (siehe Changelog).

## Context

ADR-068 + ADR-116 + ADR-196 etablierten **statische Routing-Tabelle → adaptive Telemetrie → Bandit-Framework**. ADR-084 ergänzte Model-Registry-Workflows. Die Drift-Inventur 2026-05-13 (dev-hub#39, mcp-hub#47, dev-hub#40) zeigte fünf parallele Surfaces — Phase 0 Hygiene-Migrationen brachten sie data-side in Einklang.

Der **ursprüngliche v1-Vorschlag** dieses ADRs war ein zentraler `/v1/route`-HTTP-Service. Die advocatus-diaboli Review hat folgende Schwächen identifiziert:

| # | Schwäche v1 | Schwere |
|---|---|---|
| 1 | Cross-DB-Lookup (AIFW in devhub_db, Service in orchestrator-DB) ungelöst | **blocker** |
| 2 | Push-basiertes Outcome-Reporting → Datenfriedhof | **blocker** |
| 3 | Compliance-Class als Caller-Self-Attestation = Security-Loch | **blocker** |
| 4 | `complexity_hint` Caller-Subjektivität → Bandit-Cell-Verwässerung | hoch |
| 5 | Per-Repo `.iil-routing.yaml` in Phase 4 fügt 6. Surface hinzu statt eliminieren | hoch |
| 6 | 5 Wochen Engineering für ein Problem mit 0 % Downtime | hoch |
| 7 | $1577/48 h Opus-Spend wird durch ADR gar nicht adressiert (Session-Choice) | hoch |
| 8 | „Orchestrator wählt automatisch" widerspricht „Caller liefert complexity_hint" | hoch |
| 9 | Single-Point-of-Failure semantisch vs. Single-Point-of-Truth-Bug | mittel |
| 10 | action_code Namensraum-Chaos (`orchestrator.developer` vs `headless_edit`) | mittel |
| 11 | Latenz auf jedem cold-start hit auf jedem Caller-Container | mittel |
| 12 | `/v1`-Versioning ohne v2-Story | niedrig |

Diese Schwächen sind nicht durch Iteration auf v1 fixbar — sie folgen aus der Grundentscheidung „live HTTP-Service als Authority". Daher **v2 mit anderer Architektur**.

## Decision

Die kanonische Antwort auf „welches Modell für diese Aufgabe in diesem Repo" ist **eine versionierte Python-Library** (`iil-routing`), nicht ein HTTP-Endpoint. Die Library wird **aus AIFW per nightly Codegen erzeugt** und über PRs verteilt. Ein optionaler **Read-only-Diagnose-Endpoint** existiert nur für interaktive Use-Cases (Claude-Code-`/route`-Command). Outcome-Lernen erfolgt **pull-basiert aus `llm_calls`**. Compliance-Gates sind **server-side über tenant→class-Mapping**, nicht Caller-input.

### Architektur in fünf Schichten

```
┌─────────────────────────────────────────────────────────┐
│  Layer 5: Compliance & Budget Guard                     │
│  tenant_compliance_class (orchestrator-DB)              │
│  → Library liest beim Import, refused non-conform model │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ verify at decide()
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Outcome-Korrelation (PULL aus llm_calls)      │
│  task_id ↔ chosen_model JOIN → Bandit-Posteriors        │
│  Output: weekly drift report — NO write-path required   │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ Bandit-Empfehlung als PR-Comment
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Sync-Pipeline (nightly cron in mcp-hub)       │
│  AIFW (devhub_db) → codegen → iil-routing tag + PR      │
│  + UPDATE model_route_configs (orchestrator-DB)         │
│  → routing-as-code: jeder Change ist PR-auditierbar     │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ release on accepted PR
┌─────────────────────────────────────────────────────────┐
│  Layer 2: iil-routing Python Library                    │
│  from iil_routing import decide                         │
│  d = decide(action_code="...", repo="...", task_text=...)│
│  d.model / d.fallback / d.reason / d.policy_version      │
└─────────────────────────────────────────────────────────┘
                          ▲                          ▲
                          │ import                   │ optional HTTP fanout
┌────────────────────────────────────┐  ┌────────────────────────────┐
│ Every consumer:                    │  │  Layer 1 (optional)        │
│  orchestrator_mcp internals        │  │  GET /v1/route — read-only │
│  headless_run adapters             │  │  for interactive use cases │
│  Claude Code hooks                 │  │  (Claude Code /route cmd)  │
│  ad-hoc scripts                    │  │  Falls back to library if  │
│                                    │  │  offline. NOT on critical  │
│                                    │  │  path of any LLM call.     │
└────────────────────────────────────┘  └────────────────────────────┘
```

### Was sich gegen v1 ändert (Korrespondenz zur Kritik-Tabelle)

| Kritik # | v2-Antwort |
|---|---|
| 1 (Cross-DB) | **Codegen-Snapshot** statt Live-Lookup. AIFW wird nightly gelesen → Library compiled → PR. Library wird in alle Caller-Repos via `pip` deployed. Kein runtime cross-DB-hop. |
| 2 (Push-Outcome) | **Pull aus `llm_calls`**. Decision-id == task_id (existiert schon via Stop-hook). Bandit-Job läuft als wöchentlicher PR mit Empfehlungen, nicht als Live-Service. |
| 3 (Compliance-Self-Attestation) | **Server-side tenant→compliance_class Tabelle** in orchestrator-DB. Library fetched einmal beim Import, refused dann automatisch nicht-konforme Modelle. Caller kann das nicht überschreiben. |
| 4 (complexity_hint Subjektivität) | **Optional ableitende Klassifikation**: wenn Caller `task_text` mitgibt, klassifiziert Cerebras llama3.1-8b → tier. Wenn Caller explizit `force_tier=` setzt, wird das **geloggt** + im Outcome-Report sichtbar. |
| 5 (Per-Repo YAML als 6. Surface) | **Entfernt**. Per-Repo-Differenzierung ist nur über `tenant_compliance_class` + `repo_action_code_overrides`-Tabelle (singular: ein DB-Surface, kein File-Surface). |
| 6 (5 Wochen Engineering) | **Phase 1 = 1 Tag** (nightly codegen-PR). Phase 2 = 1 Woche (Library). Phase 3 = optional. Insgesamt 1-2 Wochen + optionale Erweiterungen. |
| 7 (Session-Spend) | Library hat `decide_session_model(workload_hint)` — wird im Claude-Code-PreToolUse-Hook beim ersten Bash/Edit aufgerufen + empfiehlt `/model`-Switch wenn Tier-Mismatch. **Routing wirkt jetzt auf Session-Layer**, nicht nur agent-intern. |
| 8 (Auto-vs-Caller-Input) | **„Optimal" wird differenziert**: bei action_code → deterministisch. Bei freier Aufgabe → klassifiziert. Beides läuft in der Library, keine Mischung. |
| 9 (SPOF) | Library = lokal in jedem Caller. Service-Down ≠ Routing-Down. Diagnostic-Endpoint optional. |
| 10 (Namensraum) | **Enforced naming**: `<scope>.<verb>` Schema. Scopes: `orchestrator.*`, `repo.<name>.*`, `skill.*`, `headless.*`. Codegen-PR fails wenn Pattern verletzt. |
| 11 (Latenz cold-start) | Library = `O(dict-lookup)`. Kein RTT. |
| 12 (/v1 ohne v2-story) | Library-Version ist die Versions-Story (`iil_routing.__version__`). Endpoint braucht keine eigene Versionierung. |

### Library-API (Layer 2 — der Hauptkontrakt)

```python
from iil_routing import decide, decide_session_model, RoutingDecision

# Action-code-basiert (deterministisch)
d: RoutingDecision = decide(
    action_code="review_adr",
    tenant_id=1,
    repo="mcp-hub",
)
# d.model            == "anthropic/claude-sonnet-4-6"
# d.fallback_model   == "anthropic/claude-haiku-4-5"
# d.tier             == "standard"
# d.reason           == "AIFW action_code 'review_adr' → Tier 3"
# d.source           == "aifw"
# d.policy_version   == "2026-05-14.1"
# d.task_id          == None  # caller sets if integrating with llm_calls

# Freitext-Task (Cerebras-klassifiziert)
d = decide(
    task_text="Refactor the auth middleware to use the new token format",
    tenant_id=1,
    repo="mcp-hub",
)
# Library: classify(task_text) via cheap Cerebras → tier="standard"
#                                                → model="anthropic/claude-sonnet-4-6"

# Session-Empfehlung (für Claude-Code-Pre-Hook)
rec = decide_session_model(workload_hint="lint cleanup, no architecture")
# rec.recommended == "anthropic/claude-sonnet-4-6" (Tier 3)
# rec.advice      == "Currently on Opus 4.7 (Tier 4). /model swap saves ~5x."

# Compliance refused — Caller bekommt Exception, kein silent-bypass möglich
decide(action_code="review_adr", tenant_id=2, repo="ttz-hub")
# raises ComplianceViolation: tenant_id=2 (ttz-lif) requires EU-hosted;
# anthropic/claude-sonnet-4-6 is US-hosted. Fallback to mistral/mistral-large-latest.
```

### Layer 3 — Codegen Sync-Pipeline

Nightly GitHub Action in mcp-hub:

```yaml
on:
  schedule: [{ cron: "17 3 * * *" }]
  workflow_dispatch:
jobs:
  routing-codegen:
    runs-on: self-hosted
    steps:
      - reads aifw_action_types from devhub_db
      - reads tenant_compliance_class from orchestrator-DB
      - validates action_code naming pattern (<scope>.<verb>)
      - validates every model exists in aifw_llm_models + is_active
      - regenerates packages/iil-routing/iil_routing/_generated.py
      - bumps version, opens PR if diff
      - includes Bandit-recommendation report in PR description
```

Ergebnis: jede Routing-Änderung ist ein PR mit git blame, Diff-Review, optionalem Bandit-Argument. **Decision-as-Code.**

### Layer 1 — Diagnostic Endpoint (optional)

```
GET /v1/route?action_code=review_adr&tenant_id=1&repo=mcp-hub
→ 200 { same shape as RoutingDecision }
```

- **Read-only**, kein side-effect, kein Write-Path
- Für interaktive Tools: Claude-Code `/route` slash-command, Debug-UI
- Falls Service down: Caller kann Library direkt nutzen
- **Nicht auf critical path** eines einzigen LLM-Calls

### Layer 4 — Outcome-Korrelation aus `llm_calls`

Heutige Realität: jeder LLM-Call wird in `llm_calls` mit `task_id`, `model`, `duration_ms` (seit gestern), `cost_usd` persistiert. Der Bandit braucht **kein neues Write-Interface** — er JOIN'd:

```sql
SELECT
  c.task_id,
  c.model AS chosen,
  c.duration_ms, c.cost_usd, c.error,
  -- aus llm_call_tasks: was war die Aufgabe?
  t.repo, t.description
FROM llm_calls c
LEFT JOIN llm_call_tasks t ON t.task_id = c.task_id
WHERE c.created_at >= now() - interval '7 days';
```

Bandit-Job rechnet pro `(action_code, tier)` Cell die observed Success-Rate (durch Heuristiken: kein error, kein retry, niedrige duration_ms gegen Tokens) und schreibt das Ergebnis als **Empfehlung in den nächsten Codegen-PR**. Kein Auto-Apply.

### Layer 5 — Compliance & Budget (server-side)

Neue Tabelle in orchestrator-DB:

```sql
CREATE TABLE tenant_compliance_class (
    tenant_id           BIGINT PRIMARY KEY,
    class               TEXT NOT NULL CHECK (class IN ('none','eu','pii','air_gap')),
    allowed_providers   TEXT[],
    daily_budget_usd    NUMERIC(10,2),
    notes               TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Initial seed:
- `tenant_id=1` (achimdehnert) → `class='none'`, alle providers
- `tenant_id=2` (ttz-lif) → `class='eu'`, `allowed_providers={mistral,ollama}`
- `tenant_id=3` (meiki-lra) → `class='pii'`, `allowed_providers={ollama}`

Library fetched diese Tabelle einmal beim Import + cached 5 min. Jeder `decide(...)`-Call refused automatisch nicht-konforme Modelle. **Caller kann nicht falsch deklarieren** — Server-side enforcement.

## Consequences

### Positive

- **Keine Cross-DB-Latenz im Hot-Path.** Library lookup ist nanoseconds.
- **Outcome-Pipeline ab Tag 1 voll** (llm_calls existiert seit Wochen mit task_id).
- **Compliance ist nicht umgehbar** — Library refused Modelle die nicht in `tenant.allowed_providers` sind.
- **Decision-as-Code**: jede Routing-Änderung ist ein nachvollziehbarer PR mit git history.
- **Phase 1 = 1 Tag**: nur die nightly codegen action. Sofortwert: alle Surfaces atomar gesynct.
- **Session-Layer adressiert**: `decide_session_model` schließt die $1577-Lücke aus dev-hub#39.
- **ADR-196 Bandit-Framework bekommt sauberen Hook** (PR-Comment, nicht Auto-Apply — Mensch entscheidet).
- **Ad-hoc Skripte aus beliebigem Repo** brauchen nur `pip install iil-routing`, nichts an Service-Konnektivität.

### Negative

- **Library-Versions-Disziplin nötig**: jeder Caller muss `iil-routing` aktuell halten. Mitigiert durch Dependabot/Renovate (existiert pro Repo).
- **Codegen-PRs als noise**: nightly PR kann verspätet sein → kurze Drift-Fenster. Akzeptiert: maximal 24 h Drift, gemessen via existierendem mcp-hub#41-Drift-Workflow.
- **Diagnostic-Endpoint hat eingeschränkten Nutzen**: nur für interactive UX. Akzeptiert: vermeidet alle Service-Failure-Modes.
- **Complexity-Klassifikation hat noch eine LLM-Abhängigkeit** (Cerebras). Mitigiert durch Cache (7-Tage TTL pro task_text Hash) + Fallback auf deterministische Heuristik (Wortzahl, Code-Keywords).

### Neutral

- ADR-068 + ADR-116 + ADR-196 werden **nicht reversed**, sondern in die Library-Architektur eingebettet. Routing-Matrix bleibt; sie lebt jetzt in `iil_routing/_generated.py`.
- AIFW bleibt **write-side canonical**. Codegen reads, Library compiles.
- `model_route_configs` wird sekundärer Authority-Layer (für agent_role/complexity-Lookups die kein action_code haben), bleibt aber durch Sync-Job in Einklang.

## Implementierungs-Phasen

| Phase | Dauer | Lieferobjekt | Was es löst |
|---|---|---|---|
| **1** | 1 Tag | nightly `routing-codegen.yml` workflow + `iil-routing` package skeleton + Sync `aifw → model_route_configs` | 4 Surfaces atomar synchron, dauerhaft |
| **2** | 1 Woche | `iil-routing` v1.0 mit `decide()` + `decide_session_model()` + Compliance-Tabelle + Server-side enforce | Library produktionsreif, Compliance hart |
| **3** | 1 Woche | ModelSelector wird Library-Konsument, Claude-Code-PreToolUse-Hook empfiehlt Session-Modell | $1577-Lücke geschlossen |
| **4** | optional, nach Telemetrie-Lern-Periode (4-6 Wochen) | Bandit-Job als wöchentlicher Codegen-PR mit observed-success-rate-Empfehlungen | ADR-196 Stage 3 aktiviert ohne Auto-Apply |
| **5** | optional, bei Bedarf | `GET /v1/route` Diagnose-Endpoint für interaktive UX | Nice-to-have |
| **6** | optional | Per-action_code Repo-Override (`repo_action_code_overrides`-Tabelle) | Echte Repo-Diff falls nötig — nur **eine** Surface |

## Sicherheits- & Compliance-Argument

| Risiko | Mitigation |
|---|---|
| Caller deklariert falsche compliance_class | Server-side `tenant_compliance_class` ist Source of Truth, Caller-Input ignoriert |
| Library ist veraltet im Caller (security-relevantes Modell stirbt) | Drift-Workflow (mcp-hub#41) findet das innerhalb 24 h; iil-routing-Release-Cadence ist nightly |
| Outcome-Daten enthalten Prompt-Inhalt (PII) | Bandit liest nur `task_id`, `model`, `duration_ms`, `error` aus `llm_calls` — keine Prompts |
| Codegen-PR wird ohne Review gemerged | Branch-Protection auf platform + mcp-hub erzwingt Review |

## Action-Code Namens-Konvention

| Scope | Beispiele | Owner |
|---|---|---|
| `orchestrator.*` | `orchestrator.developer`, `orchestrator.plan`, `orchestrator.review` | mcp-hub orchestrator_mcp Maintainer |
| `headless.*` | `headless.edit`, `headless.quality_sweep`, `headless.drift_narrate` | mcp-hub headless Maintainer |
| `skill.*` | `skill.review_adr`, `skill.repo_health_summary` | jeweiliger Skill-Owner |
| `repo.<repo>.*` | `repo.mcp-hub.audit`, `repo.platform.adr_check` | Repo-Maintainer |

Codegen-Validierung erzwingt das Pattern + verhindert Kollisionen. ADR-198 (Subdomain-Konvention) hat einen analogen Vorschlag für Hostnames — wir folgen demselben Geist.

## Acceptance Criteria

- [ ] Phase 1 merged: nightly codegen-PR existiert, schließt sich auf grünen Tag-Bump, schreibt synchronisierte `model_route_configs` Updates
- [ ] Phase 2 merged: `pip install iil-routing` in mcp-hub + dev-hub + bfagent funktioniert, alle Compliance-Tests gegen alle 3 Tenants grün
- [ ] Phase 3 merged: PreToolUse-Hook reports Session-Tier-Mismatch (objektiv messbar: pro Claude-Code-Session-Start ein log-event mit recommended vs current)
- [ ] Phase 1-3 zusammen reduzieren **Average opus_per_session_ratio** um >50 % (gemessen über 14 Tage post-Phase-3)

## Drift Check Paths

```
mcp-hub/.github/workflows/routing-codegen.yml          # Layer 3, neue Datei
mcp-hub/packages/iil-routing/                          # Layer 2, neuer Sub-Package
mcp-hub/orchestrator_mcp/model_selector.py             # wird Library-Konsument
mcp-hub/orchestrator_mcp/model_registry.py             # bleibt Fallback
dev-hub/sql_migrations/0003_tenant_compliance_class.sql # neue Tabelle
~/.claude/hooks/route_session_advisor.py               # neuer Pre-Tool-Use hook
~/.claude/policies/llm-routing.md                       # bleibt source-of-truth für Tier-Liste
~/.claude/policies/session-routing.md                   # bleibt source-of-truth für Session-Choice
```

## Open Questions

1. **`iil-routing` als pip-package oder als platform-internal package?** Empfehlung: zunächst platform-internal (`packages/iil-routing/` im mcp-hub-Mono), später als eigenes Repo wenn Cross-Org-Konsumenten kommen. Kein PyPI-Release initial — vermeidet sensible-data Leaks.
2. **Diagnose-Endpoint Auth?** Bearer-Token (existiert) reicht für read-only Diagnose. Niemand kann darüber etwas ändern.
3. **Cerebras-Klassifizierer-Fallback wenn Cerebras down?** Heuristik (Wortzahl > 200 + Code-Block → standard; sonst budget). Library-internal, kein external dep.
4. **Codegen-PR Auto-Merge oder Review-Pflicht?** Empfehlung: Review-Pflicht, aber 1-Approver reicht. So bleibt Decision-as-Code auditierbar ohne Bremsklotz.

## Changelog

- 2026-05-13: **v1** (file: `routing-decision-service.md`) — zentraler HTTP-Service `/v1/route`. Status: proposed.
- 2026-05-14: **v2** (file renamed to `model-routing-library.md`) — komplett-rewrite nach advocatus-diaboli Review. Kern-Architektur kippt von HTTP-Service auf versionierte Python-Library mit codegen-PR-Pipeline. 12 dokumentierte v1-Schwächen adressiert. Compliance server-side. Outcome pull aus `llm_calls`. Session-Layer als Hauptbeneficiary einbezogen. Per-Repo-YAML eliminiert (war Phase 4 in v1, würde 6. Surface anlegen). Phase-Anzahl von 4 verbindlichen auf 3 verbindliche + 3 optionale reduziert. Geschätzter Aufwand sinkt von ~5 Wochen auf 2 Wochen + optionale Stretches. Status: proposed.
