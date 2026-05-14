---
status: rejected
date: 2026-05-14
decision-makers: [Achim Dehnert]
implementation_status: none
related: [ADR-068, ADR-084, ADR-115, ADR-116, ADR-196, mcp-hub#37, mcp-hub#39, mcp-hub#47, dev-hub#39, dev-hub#40, platform#135]
rejected-after: 4 internal advocatus-diaboli review rounds across 3 architecture iterations (HTTP-Service → Python-Library → GitOps-YAML). Each round surfaced new structural issues. Convergence-failure is the actual signal — the problem isn't "better routing architecture", it's awareness/observability in the consumer UX. Phase 0 hygiene (mcp-hub#47 + dev-hub#40, already merged) addressed ~80 % of operational pain; the remaining 20 % is split into 3 smaller follow-up ADRs. See "Rejection Rationale".
---

# ADR-199 (rejected): Model-Routing-Authority — Three Iterations, No Convergence

## Status

**Rejected** after four review rounds. Each iteration (v1 HTTP-Service → v2 Python-Library + Codegen → v3 GitOps-YAML) fixed prior weaknesses but surfaced new structural issues. Below: the rejection rationale and the three smaller successor-ADRs that take its place.

## Rejection Rationale

Three architecture-family attempts. Four review rounds. **Convergence failed.** That is the signal — the problem framing is wrong, not the architecture.

Real problem framing:

| What v1/v2/v3 tried to solve | What's actually broken |
|---|---|
| „Orchestrator wählt automatisch optimal" | Optimization-Ziel ist subjektiv (Cost vs Quality vs Latency) — kein fixiertes „optimal" möglich |
| „Alle Routing-Surfaces synchron" | Phase 0 Hygiene-PRs (mcp-hub#47 + dev-hub#40) hat das **bereits gelöst**; Drift-Workflow (mcp-hub#41) hält sie synchron mit <24h Latenz |
| „$1577/48h Opus-Spend" | Backend-Tracking existiert (Grafana 105+211+152, llm_calls.cost_usd live). **Was fehlt: UX-Feedback im Claude-Code-Session-Layer.** Routing-Authority schließt diese Lücke nicht — Visibility schließt sie. |
| „Compliance enforced server-side" | Tenant×Class-Mapping ist eine 4-Zeilen-DB-Tabelle, kein 274-Zeilen-ADR |
| „Bandit-Learning aus Outcomes" | 7 action_codes × 5 Tiers = 35 Cells; bei 20-50 Samples/Cell/Woche statistisch nutzlos |

Vier OOB-Alternativen aus dem 4. Review schlagen alle ADR-199-Familien:

1. **Anthropic Model-Alias-Pattern** (`claude-sonnet-4-latest`) — verschiebt Drift in Provider-Verantwortung. ~1 Tag.
2. **JIT-Tier-Reassignment** — start cheap, escalate on insufficient response. ~3 Tage.
3. **Pricing-Visibility in der Claude-Code-UX** — Statusline + Session-End-Summary + cost-aware `/model`-Prompt. **Heute komplett fehlend** — nur Backend-Dashboards existieren. ~1-2 Tage.
4. **Routing-as-Decorator-Pattern** — `@route(tier=3)` Python-Decorator, Routing-Wahl ist Code-Diff statt Config-File.

## Successor-ADRs (statt monolithisches ADR-199)

- **ADR-201 (planned)** — Claude-Code Pricing Visibility (Statusline + Session-End + /model-Prompt). Adressiert das teuerste Symptom direkt. ~1-2 Tage.
- **ADR-202 (optional)** — JIT-Tier-Reassignment Library-Pattern. Nur wenn ADR-201 nicht reicht. ~3 Tage.
- **ADR-203 (optional)** — Anthropic Model-Alias-Adoption. Verschiebt Drift-Wartung zu Anthropic. ~1 Tag.

## Was bleibt aus Phase 0 (akzeptiert + deployed)

- mcp-hub#47 — `model_route_configs` Refresh (8 dead Strings entfernt)
- dev-hub#40 — AIFW LLMModels Cleanup + 7 action_codes Seed
- `~/.claude/policies/llm-routing.md` — Tier-Liste, file-based source-of-truth
- `~/.claude/policies/session-routing.md` — Session-Modell-Disziplin
- mcp-hub#41 Drift-Workflow — täglich Probe, Auto-Issue bei dead model

Diese fünf Bausteine zusammen lösen ~80 % des dokumentierten Schmerzes ohne den ADR-199-Service.

---

# Historische Architektur-Skizzen (Archiv)

Unten: die v3-Architektur die geprüft + verworfen wurde. Wir lassen sie im Repo für zukünftige Reviewer die verstehen wollen warum diese Familie nicht funktioniert.

## v3 (rejected): GitOps Routing — `routing.yaml` als einziger Wahrheitsträger

(Original v3-Status: Proposed — nach zweiter advocatus-diaboli Review)

## Context

Zwei vorangegangene Iterationen + zwei Reviews haben das Problem-Set präzisiert:

- **Was wirklich kaputt war:** 5 unabhängige Routing-Surfaces mit Drift untereinander. Phase 0 Hygiene (mcp-hub#47 + dev-hub#40) hat die Surfaces einmalig synchron gebracht; ohne Single-Source bleibt das Problem strukturell.
- **Was nicht der ADR adressiert:** der $1577/48h Opus-Spend (dev-hub#39) ist primär ein **Bewusstseins**-Problem (User-`/model`-Wahl), kein Routing-Architektur-Problem. Der ADR macht Routing-Empfehlungen verfügbar, erzwingt aber keine Session-Wahl.

v1 → v2 → v3 Architektur-Evolution:

| Iteration | Authority | Wieso verworfen |
|---|---|---|
| v1 | zentraler HTTP-Service `/v1/route` | Cross-DB, Push-Outcome, Self-Attestation Compliance |
| v2 | Python-Library `iil-routing` + codegen-PR | Library-Versions-Drift in N Konsumenten, 5-min Compliance-Cache-Loch, DB-Credentials in jedem Caller, Codegen-PR-Rubber-Stamping |
| **v3** | **`routing.yaml` Single-File + GitOps** | siehe Decision unten |

## Decision

Die kanonische Routing-Wahrheit ist **eine einzige Datei**: `~/github/platform/routing.yaml`. Konsumenten lesen die Datei via HTTP-Fetch (mit Cloudflare-CDN davor), validieren beim Refresh, und treffen lokal die Entscheidung. Änderung der Routing-Wahrheit = PR gegen platform. Das ist der **einzige** Update-Pfad. AIFW wird zur Downstream-View. Keine Codegen-Pipeline, keine Bandit-Auto-Magic, keine Compliance-DB-Tabelle.

### `routing.yaml` — der einzige Vertrag

```yaml
# ~/github/platform/routing.yaml — Single Source of Truth für Model-Routing.
# Änderung NUR über PR. Validation-Workflow erzwingt Schema + Modell-Liveness.

policy_version: "2026-05-14.1"
schema_version: 1

# Per-Tenant Compliance-Klasse + Provider-Allowlist (server-side, im File).
tenants:
  1: { class: none,    allowed_providers: ["*"] }
  2: { class: eu,      allowed_providers: [mistral, ollama] }
  3: { class: pii,     allowed_providers: [ollama] }
  4: { class: air_gap, allowed_providers: [ollama] }

# Modell-Registry — was wir kennen + ihr Status. Drift-Workflow (mcp-hub#41)
# probt jede dieser Strings nightly und öffnet Issue bei dead.
models:
  anthropic/claude-sonnet-4-6: { tier: 3, in_per_1m_usd: 3.0,  out_per_1m_usd: 15.0 }
  anthropic/claude-opus-4-7:   { tier: 4, in_per_1m_usd: 15.0, out_per_1m_usd: 75.0 }
  anthropic/claude-haiku-4-5:  { tier: 2, in_per_1m_usd: 1.0,  out_per_1m_usd: 5.0 }
  groq/llama-3.3-70b-versatile: { tier: 1a, in_per_1m_usd: 0.59, out_per_1m_usd: 0.79 }
  cerebras/llama3.1-8b:         { tier: 1b, in_per_1m_usd: 0.10, out_per_1m_usd: 0.10 }
  cerebras/qwen-3-235b-a22b-instruct-2507: { tier: 1a, in_per_1m_usd: 0.60, out_per_1m_usd: 1.20 }
  openai/gpt-4o-mini:           { tier: 2, in_per_1m_usd: 0.15, out_per_1m_usd: 0.60 }
  mistral/mistral-large-latest: { tier: 3, in_per_1m_usd: 2.0,  out_per_1m_usd: 6.0  }

# action_code → exakte Modell-Wahl. Naming-Konvention: <scope>.<verb> enforced
# via routing-yaml-validate.yml CI workflow.
action_codes:
  orchestrator.developer:    { tier: 3, model: anthropic/claude-sonnet-4-6, fallback: groq/llama-3.3-70b-versatile }
  orchestrator.plan:         { tier: 2, model: anthropic/claude-haiku-4-5,  fallback: cerebras/llama3.1-8b }
  headless.edit:             { tier: 3, model: anthropic/claude-sonnet-4-6, fallback: groq/llama-3.3-70b-versatile }
  skill.review_adr:          { tier: 3, model: anthropic/claude-sonnet-4-6, fallback: anthropic/claude-haiku-4-5 }
  skill.drift_narrate:       { tier: 1a, model: groq/llama-3.3-70b-versatile, fallback: cerebras/qwen-3-235b-a22b-instruct-2507 }
  skill.repo_health_summary: { tier: 1a, model: groq/llama-3.3-70b-versatile, fallback: groq/llama-3.1-8b-instant }
  headless.quality_sweep:    { tier: 3, model: anthropic/claude-sonnet-4-6, fallback: groq/llama-3.3-70b-versatile }

# Tier → Default-Modell wenn action_code fehlt. Used by free-text classification.
tier_defaults:
  1a: groq/llama-3.3-70b-versatile
  1b: cerebras/llama3.1-8b
  2:  anthropic/claude-haiku-4-5
  3:  anthropic/claude-sonnet-4-6
  4:  anthropic/claude-opus-4-7

# Session-Workload-Tags (für Claude-Code session_advisor).
session_workloads:
  architectural:      { tier: 4, note: "ADR drafting, cross-cutting refactor planning" }
  code_review:        { tier: 3, note: "Multi-file PR review with implications analysis" }
  implementation:     { tier: 3, note: "Single-PR feature/bug-fix with test coverage" }
  refactor_mechanical: { tier: 2, note: "Rename, lint-cleanup, format pass" }
  inspection:         { tier: 1b, note: "Log/DB queries, deploy monitoring" }
  status_check:       { tier: 1b, note: "What does this do, current state lookups" }
```

### Distribution

`routing.yaml` ist **eine Datei**, serviert über drei Wege (Konsument pickt was passt):

1. **GitHub Raw URL** (für externe Konsumenten ohne Cluster-Access):
   `https://raw.githubusercontent.com/achimdehnert/platform/main/routing.yaml`
2. **CDN-cached über orchestrator** (für Cluster-interne Konsumenten — schneller, single fetch domain):
   `GET https://orchestrator.iil.pet/routing.yaml` → Cloudflare-cached 60s, origin pullt von GitHub
3. **Lokales Submodul** (für air-gapped Konsumenten):
   `~/github/platform/routing.yaml` als git-submodule oder symlink

**Refresh-Policy** (Konsumenten-Library implementiert):
- Initial fetch beim ersten `decide()`-Call
- Re-fetch wenn YAML > 5 min alt
- Re-fetch wenn LLM-Call mit `chosen_model` → 404 zurückgibt (sofortige Reaktion auf dead model)
- Disk-Cache (`~/.cache/iil-routing/routing.yaml.cache`) für Offline-Fallback

### Library-Wrapper — minimal

`iil-routing` Python-Package wird auf **~80 Zeilen** geschrumpft. Kein Codegen, keine embedded data, keine DB-Connection.

```python
# Konzeptuell:
from iil_routing import decide, decide_session, RoutingDecision

# action_code-basiert (deterministisch, 100% offline nach erstem fetch)
d: RoutingDecision = decide(action_code="skill.review_adr", tenant_id=1)
# d.model            == "anthropic/claude-sonnet-4-6"
# d.fallback_model   == "anthropic/claude-haiku-4-5"
# d.tier             == 3
# d.policy_version   == "2026-05-14.1"
# d.source           == "routing.yaml"

# free-text → tier-tag (für PreToolUse-Hook)
rec = decide_session(workload="implementation")
# rec.tier      == 3
# rec.model     == "anthropic/claude-sonnet-4-6"
# rec.note      == "Single-PR feature/bug-fix with test coverage"

# Compliance enforced: tenant=2 (ttz-hub) bekommt automatisch EU-Modell
d = decide(action_code="skill.review_adr", tenant_id=2)
# d.model == "mistral/mistral-large-latest"  (Tier 3 EU)
# d.reason == "tenant=2 class=eu; downgraded from anthropic/claude-sonnet-4-6"
```

Implementierung ist konzeptuell ein paar-Dutzend Zeilen Python:

```python
class RoutingClient:
    def __init__(self, source_url: str, cache_path: Path | None = None): ...
    def _fetch_or_cache(self) -> dict: ...  # GET + 5min TTL + disk fallback
    def decide(self, action_code: str, tenant_id: int) -> RoutingDecision:
        cfg = self._fetch_or_cache()
        entry = cfg["action_codes"].get(action_code)
        tenant = cfg["tenants"].get(str(tenant_id))
        # 1. Lookup entry
        # 2. Check entry.model.provider in tenant.allowed_providers
        # 3. If not allowed: pick a tier-equivalent model that IS allowed
        # 4. Return RoutingDecision with full reason
```

Keine Cerebras-Dependency. Keine DB. Keine Codegen.

### AIFW wird Downstream-View, nicht Source

Phase 0 hat AIFW (`aifw_action_types`) mit Daten gefüllt. v3 **kehrt die Richtung um**:

- `routing.yaml` ist Source-of-Truth
- Optionaler Sync-Job liest `routing.yaml` und UPDATEt `aifw_action_types` für Konsumenten die heute AIFW abfragen (`headless/services/aifw_bridge.py`)
- Dieser Sync-Job ist **read-only** auf routing.yaml — kein Schreibpfad zurück
- AIFW Django Admin bleibt für Visualisierung + Usage-Logs (`aifw_usage_logs`), aber **kein Routing-Write-Pfad** mehr

Damit fällt die Kritik #4 (Codegen-Rubber-Stamping in v2) weg: die echte Entscheidung passiert im PR auf `routing.yaml`, nicht in AIFW-Admin.

### Validation Workflow

`.github/workflows/routing-yaml-validate.yml` in platform-Repo, läuft on:[push, pull_request] für routing.yaml:

- YAML-Schema validieren (Pydantic / JSONSchema)
- Jeder `action_codes.<code>` matched `<scope>.<verb>` Regex
- Jedes `.model` und `.fallback` existiert in `models:` mapping
- Jeder tenant.allowed_providers Eintrag matched einen real provider
- Jeder action_code hat tenant-1-compatible fallback (sonst PR rejected)
- Optional: probe jeden Modell-String gegen Provider-API (analog mcp-hub#41) — green vor merge

PR-Workflow: jede Routing-Änderung ist ein PR, validiert, von einem 2. Mensch reviewed. **Decision-as-Code echt, nicht generated**.

### Was v3 *nicht* macht

| Bewusst weggelassen | Begründung |
|---|---|
| Bandit / Outcome-Learning Pipeline | 7 action_codes × 5 tiers × 7 days = zu wenige Samples für sinnvolle Posteriors. ADR-196 Stage 3 bleibt OFF. Reaktivierung wenn Action-Code-Coverage 3× wächst. |
| Codegen-PR-Pipeline (v2 Layer 3) | Reverse-Richtung: humans schreiben routing.yaml, AIFW liest. Kein nightly automation, keine cross-repo PATs. |
| Cerebras-Klassifikator für free-text Tasks | Library hat nur deterministische Lookups. Free-text → Tier ist Aufgabe des Aufrufers (z.B. Claude-Code PreToolUse-Hook mit user-bestimmtem `workload_hint`). |
| Discord-Notify / Daily-Cost-Reports | aktuell nicht prioritisiert. Grafana-Panels (id 105 + 211) decken Observability ab. |
| HTTP `POST /v1/route/{id}/outcome` Endpoint | Outcome lebt bereits in `llm_calls`. Wenn man später lernen will: SQL JOIN, kein neuer Schreibpfad. |
| Per-Repo `.iil-routing.yaml` overrides | YAML-File pro Repo wäre 6. Surface. Stattdessen: ein `repo_overrides:` Block in der zentralen `routing.yaml` wenn überhaupt nötig (vermutlich Phase 6, evidence-based). |

### Was v3 *macht* — Phasen

| Phase | Dauer | Lieferobjekt |
|---|---|---|
| **1** | 1 Tag | `routing.yaml` initial (aus Phase-0-Daten + dev-hub#40 AIFW state) + validation-workflow + HTTP-Endpoint `GET /routing.yaml` im orchestrator (rein static serve, no logic) |
| **2** | 2 Tage | `iil-routing` minimal library (~80 Zeilen + Tests) + ein erster Konsument (orchestrator-internal `model_selector` ersetzen) |
| **3** | 3 Tage | Weitere Konsumenten: headless-adapter, skill/review_adr, aifw_bridge (read-only sync zu AIFW) |
| **4** | optional | Claude-Code `PreToolUse` Hook: liest routing.yaml + user-`workload_hint` → empfiehlt `/model` (soft-nudge, kein enforce). Adressiert dev-hub#39 als Bewusstseins-Hebel ohne Spend-Erzwingung. |

**Gesamt verbindlich: 6 Arbeitstage** (statt v2's 1-2 Wochen, statt v1's 5 Wochen).

## Wie v3 die v2-Kritik adressiert

| v2-Schwäche | v3-Antwort |
|---|---|
| Library-Versions-Drift in N Konsumenten | Library ist ~80 Zeilen, ändert sich praktisch nie. Routing-Daten kommen aus dem fetched YAML, nicht aus dem Library-Code. Update = YAML-PR, nicht Library-Release. |
| 5-min Compliance-Cache-Loch | Cache-TTL ist konfigurierbar (Default 5 min). Compliance-Push: kritische Tenant-Class-Änderungen werden via `Cache-Control: no-cache` Header auf orchestrator-Endpoint + manuellem Library-`refresh()` propagiert (~10 sek statt 5 min). |
| DB-Credentials in jedem Caller | Eliminiert. Konsument fetched HTTP von public-cached URL. Kein DB-Hop, kein DB-Secret. |
| Codegen-PR-Rubber-Stamping | Reversiert: PR auf `routing.yaml` ist die menschliche Entscheidung. Kein generated file, kein „1 file changed: _generated.py". Reviewer sieht die echte Diff. |
| Codegen-Pipeline Failure-Mode-Ownership | Keine Pipeline. `routing.yaml` ist eine Datei mit git history. Owner = platform-repo-Maintainer (klar definiert via CODEOWNERS). |
| Cerebras Runtime-Dependency | Eliminiert. Free-text klassifikation ist Aufgabe des Aufrufers, nicht der Library. Wenn ein Caller (z.B. PreToolUse-Hook) Cerebras nutzen will, ist das seine Wahl. |
| PreToolUse-Hook schließt $1577 nicht | v3 macht ehrlich: Hook ist Phase 4 *optional* und explizit **soft-nudge**, nicht enforce. Die echte Lösung für Session-Spend ist Bewusstsein + Disziplin (siehe `~/.claude/policies/session-routing.md`), nicht Architektur. |
| Bandit-Daten zu dünn | Bandit aus v3 gestrichen. Wenn Telemetrie-Volumen wächst (3×), kann ADR-196 Stage 3 separat angegangen werden. |

## Out-of-the-Box-Hebel, die v3 beibehält

1. **Routing-as-File** statt Routing-as-Service: einzelne YAML mit git history übertrifft Service-State in Auditability.
2. **Reverse-Sync**: AIFW liest von routing.yaml, nicht umgekehrt. Phase 0 Daten bleiben in AIFW als View, aber die Macht über Routing liegt im PR.
3. **Compliance im Datenmodell, nicht im Code**: `tenants.X.allowed_providers` ist deklarativ, vom Validation-Workflow geprüft, im PR sichtbar.
4. **Refresh-on-error**: dead model → automatischer YAML re-fetch + retry. Selbstheilung bei minimaler Drift-Latenz.
5. **CDN-fronted Distribution**: orchestrator endpoint ist nur ein dünner Proxy zu GitHub raw. Cloudflare cached. Air-gap-Fallback via Submodul.

## Consequences

### Positive

- **Eine Datei, eine Wahrheit, ein Update-Pfad** (PR).
- **Distribution kostenfrei**: HTTP GET + Cloudflare-Cache. Keine pip-Disziplin, kein Codegen.
- **Compliance ist Daten, nicht Code**: Reviewer sieht in der PR direkt was geändert wird; CI validates.
- **6 Arbeitstage Engineering** verbindlich, dann optional Phase 4 für Session-Soft-Nudge.
- **Audit-Trail ist git log auf einer Datei** — maximal lesbar.
- **Library ist trivial** (~80 LOC), debug-bar, in jeder Sprache portierbar.

### Negative

- **Kein automatisches Learning aus Outcomes** (kein Bandit). Akzeptiert: Datenmenge reicht heute nicht; wir können später hinzufügen.
- **YAML-Schema-Evolution** braucht Disziplin: jedes neues Feld muss schema_version bumpen + Library upgraden. Mitigiert durch JSONSchema + CI-Validation.
- **Sync zu AIFW ist Einbahnstraße**: AIFW Admin-UI Änderungen werden silent überschrieben. Akzeptiert: AIFW ist Visualisierung, nicht Authority.
- **Refresh-Latenz für Compliance**: ohne explicit refresh-trigger sind kritische Compliance-Updates max 5 min eventually consistent. Mitigiert durch `Cache-Control: no-cache` + Library-`refresh()` API für emergency-Push.

### Neutral

- v1's HTTP-Endpoint und v2's Library bleiben als **Konsumenten-Pattern** verfügbar, aber sind nicht Authority.
- ADR-068 + ADR-116 + ADR-196 werden nicht reversed, ihre Daten leben in `routing.yaml`.

## Risk Register

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|---|---|---|---|
| `routing.yaml` wird ohne CI gemerged (CI broken) | mittel | hoch | Branch-Protection auf main; CI ist required-check |
| Orchestrator-CDN-Endpoint ist down | niedrig | mittel | Konsument fällt zurück auf GitHub Raw URL |
| GitHub Raw ist down | sehr niedrig | mittel | Konsument fällt auf Disk-Cache + warnt |
| Konsument cached stale | dauerhaft | niedrig | Refresh-on-error + 5-min TTL; Drift-Workflow (mcp-hub#41) findet dead-models in <24h |
| Air-gap-Tenant kann YAML nicht fetchen | niedrig | hoch | Submodul oder geclonter Snapshot im Repo |
| `routing.yaml` wird zu groß für inline (1000+ action_codes) | irgendwann | niedrig | Split per scope: `routing/orchestrator.yaml`, `routing/skill.yaml` etc. Schema-Erweiterung. |

## Acceptance Criteria

- [ ] Phase 1: `routing.yaml` exists in platform main, validate-workflow blockt schema-violations
- [ ] Phase 2: `iil-routing` Library + orchestrator `model_selector` ersetzt, Test-Suite grün
- [ ] Phase 3: alle vier wesentlichen Konsumenten (orchestrator, headless, skill, aifw_bridge) lesen `routing.yaml`
- [ ] Spot-test: PR der `models.anthropic/claude-sonnet-4-6` auf dead-string ändert, schlägt im Validation-Workflow fehl

## Open Questions

1. **`routing.yaml` Owner**: Default-Approver für PRs gegen routing.yaml? Empfehlung: platform-CODEOWNERS = primary, mit cross-team-courtesy-Review aus mcp-hub für action_codes.
2. **Submodul vs HTTP für mcp-hub**: orchestrator selbst soll routing.yaml lesen — von wo? Submodul (zero runtime dep) vs eigenes endpoint (self-reference). Empfehlung: read `/opt/platform/routing.yaml` als bind-mount; fallback HTTP nur falls Mount fehlt.
3. **Compliance-Refresh-Mechanismus**: brauchen wir tatsächlich einen <1-min Path? Wenn ja, separater Webhook-Push-Endpoint. Wenn 5 min reicht (vermutlich): Default-TTL.
4. **Wer schreibt die initiale routing.yaml?** Vorschlag: Phase 1 generiert sie *einmal* aus Phase-0 AIFW state + Hand-Edit. Danach AIFW-Sync ist read-only von YAML.

## Changelog

- 2026-05-13: **v1** (`ADR-199-routing-decision-service.md`) — zentraler HTTP-Service `/v1/route`. Verworfen wegen Cross-DB, Push-Outcome, Self-Attestation-Compliance.
- 2026-05-14 morning: **v2** (`ADR-199-model-routing-library.md`) — Python-Library + Codegen-PR-Pipeline. Verworfen wegen Library-Versions-Drift, Compliance-Cache-Loch, N×DB-Credentials, Codegen-Rubber-Stamping.
- 2026-05-14 evening: **v3** (`ADR-199-gitops-routing.md`) — file-based GitOps. `routing.yaml` als alleinige Authority, AIFW wird Downstream-View, Library auf ~80 LOC reduziert, Bandit aus dem Scope geworfen. Engineering von 5 Wochen (v1) über 2 Wochen (v2) auf 6 Arbeitstage. Status: proposed.
