---
status: proposed
date: 2026-06-09
decision-makers: Achim Dehnert
consulted: Externe Zweitmeinung (Advocatus-Diabolus-Review 2026-06-09, ~/shared/adr-handoff-ADR-240-2026-06-09.md)
informed: –
implementation_status: not_started
domains: [platform, observability, health, agents, mcp]
scope: cross-repo
relates_to: [ADR-196, ADR-201, ADR-222, ADR-231, ADR-239]
tags: [repo-health, health-check, probe, narration, mcp-hub, orchestrator-db, plugin-architecture]
---

# ADR-240: Repo-Health-Framework über alle Plattform-Repos

## Kontext

Über drei GitHub-Orgs (~15 Repos) verteilt liegen heute **isolierte Health-Surfaces**, jede mit
eigener Datenhaltung, eigener Eskalation und eigener Cadence:

| Surface | Repo | Prüft | Cadence | LLM? |
|---|---|---|---|---|
| `apps/repo_health/` | dev-hub | Git-State aller Repos, Markdown-Report | Daily 07:00 | optional |
| `apps/quality_agent/` | dev-hub | Hub-Code-Quality via Headless-LLM-Run | Daily, ~$0.50/Nacht | ja |
| `apps/health/` | dev-hub | Externe HTTP-Endpoints + CI-Status | Polling | nein |
| `llm-model-drift.yml` | mcp-hub | Modell-Strings gegen Provider proben | Daily | ja (Probe) |
| `compliance-check.yml` | mcp-hub | ADR-Drift-Detektor | Push+PR | nein |
| ADR-MCP-Tools | platform | ADR Validate/Freshness/Staleness | on-demand | ja |

**Problem:** Jede neue Health-Dimension wächst als eigene Insel → kein einheitliches Datenmodell,
keine konsistente Eskalation, keine gemeinsame Trend-Sicht über Zeit. Bestehende Funktion
`persist_health_score` (dev-hub Portal-App) schreibt Health-Daten isoliert ohne
geteilte Semantik.

**Nicht abgedeckte Gaps (nach Schmerz sortiert):** Dependency-CVEs, Test-Coverage-Drift,
Flaky-Tests, CI-Hygiene, Documentation-Drift, Secret-Rotation, Container-Health,
DB-Schema-Drift, Cost-Drift, Performance-Regression, Onboarding-Readiness, Repo-Konsistenz.

## Entscheidung

Ein **einheitliches Repo-Health-Framework** mit Core + Dimension-Plugin-Schnittstelle:

### 1. `HealthCheck` als first-class Datenobjekt

```python
name: str            # z.B. "dependency_cve"
repo: str            # z.B. "achimdehnert/dev-hub"
severity: enum       # ok / warn / fail / critical
detected_at: datetime
metric: dict         # check-spezifisch (strukturiert per Dimension)
metric_schema: str   # Schema-Bezeichner, z.B. "cve_v1"  ← REC-6
metric_version: int  # incrementiert bei Breaking Changes  ← REC-6
llm_summary: str?    # optional LLM-Narrative
suggested_fix: str?  # optional LLM-Vorschlag
narration_provider: str?  # welcher Provider → Audit-Log  ← REC-7
```

Persistiert in Tabelle `health_check_results` in der **shared orchestrator-DB** (`mcp_hub_db`).
`metric` wird pro Dimension gegen ein registriertes Schema validiert — unbekannte Schemas
werden abgewiesen, nicht still akzeptiert. Breaking Changes incrementieren `metric_version`.

### 2. Probe + Narration je Dimension (Tools-first)

**Probe** = mechanischer, deterministischer Check. **Bevorzugt** werden bestehende
Spezialtools (pip-audit, Trivy, pip-licenses, etc.) als Primärquelle; Eigenlogik wird
nur gebaut, wenn kein passendes Tool existiert (REC-12). Probe-Output → strukturiertes
`metric`-Dict.

**Narration** = optionaler LLM-Call, **nur bei Severity ≥ warn**. Narration-Provider
wird im Ergebnis protokolliert. Für Public-Sector-Repos: technischer Hard-Fail bei
externem LLM-Routing (REC-7, siehe Souveränitäts-Guardrails).

### 3. 5 Cadence-Tiers

A=Push (Lint, Secret-Scan, ADR-Drift) · B=Hourly (External-Health, Container-Restart) ·
C=Daily (Modell-Drift, Git-State, Dep-Versions, Cost, Coverage) ·
D=Weekly (CI-Hygiene, Doc-Drift, Repo-Konsistenz) · E=Monthly (Onboarding-Readiness,
Secret-Rotation, DB-Schema-Drift).

### 4. Eskalation

ok=silent · warn=Persistenz+Wochenreport · fail=+Notif+Auto-Issue (`health-drift`) ·
critical=+Ping+Auto-Issue (`health-drift`+`critical`).
Auto-Issues dedup'd pro Dimension/Repo/Tag (gleicher Tag → nur Kommentar, kein zweites Issue).

### 5. Budget-Gates pro Dimension (REC-9)

Jede Dimension deklariert beim Registrieren: `max_narrations_per_day` (Default: 3) und
`cost_ceiling_usd_per_day` (Default: $0.10). Wird das Ceiling überschritten: Dimension
fällt in Degradationsmodus (Probe läuft, Narration deaktiviert, kein LLM-Call). Das
Gesamt-Budget bleibt damit einstellig $/Tag mit Cerebras-Tier-1a. Cerebras wird per
LLM-Routing-Policy (ADR-196/ADR-201) priorisiert; kein Tier-4/Opus für Health-Checks.

### 6. Souveränitäts-Guardrails für Public-Sector-Repos (REC-7)

Org-Präfix-Allowlist (`ttz-lif/*`, `meiki-lra/*`) wird beim Narrations-Call geprüft:
- Externer LLM-Provider → **Hard-Fail** (Exception, kein Fallback-Narration)
- Erlaubt: lokaler Ollama-Endpoint oder `narration=disabled`
- Jeder Narrations-Call schreibt einen Audit-Log-Eintrag (Repo, Provider, Timestamp, Cost)

### 7. Lokation: mcp-hub (Konventionsbruch — bewusstes Reversal) (REC-1)

Die Konvention lautet: *Cross-cutting headless/scheduled Agents → `dev-hub/apps/`*.
Dieses ADR bricht diese Konvention bewusst. Begründung des Reversals:

**Warum `mcp-hub` statt `dev-hub`:**
- Die Health-Daten werden in `mcp_hub_db` persistiert (von mcp-hub besessen); der
  schreibende Code gehört in denselben Trust-Boundary, um Netzwerkhops und
  Credential-Weitergabe an dev-hub zu vermeiden.
- Probes und Narration sind headless Jobs ohne Django-Request-Zyklus; sie passen
  strukturell besser zum Python-Skript/Workflow-Muster in mcp-hub als zum Django-ORM-
  und Service-Layer-Muster in dev-hub.
- MCP-Tools (`health_check_run`, `health_check_query`) können das Framework direkt
  aufrufen, ohne eine HTTP-API über dev-hub zu routen.
- `dev-hub/apps/` wächst bereits mit repo_health + quality_agent + health — ein weiterer
  Schreibendpunkt würde die SSoT-Situation verschlimmern, nicht verbessern.

**Was dieses Reversal NICHT bedeutet:** Die bestehenden dev-hub-Apps (repo_health,
quality_agent, health) werden **nicht** nach mcp-hub migriert. Sie werden als Dimensions
registriert (Phase 4), ihr Code bleibt in dev-hub.

Das Reversal ersetzt nicht die Konvention im Allgemeinen — neue Django-basierte,
request-getriggerte Agents bleiben in dev-hub.

### 8. Service-Grenzziehung (REC-3)

| Schicht | Ort | Verantwortung |
|---|---|---|
| **Health-Domain-Core** | mcp-hub (`health_framework/`) | `HealthCheck`-Datenmodell, DB-Migration, Dimension-Plugin-Registry, Budget-Gate-Logik, Souveränitäts-Guardrail |
| **Probe + Narration** | mcp-hub (je Dimension ein Modul) | Spezifische Check-Logik, Tool-Aufrufe, Metric-Schema-Validierung |
| **Scheduler / GH-Actions** | mcp-hub (`.github/workflows/`) | Cadence-Tiers A–E als nightly/push-Workflows |
| **MCP-Tools** | mcp-hub (orchestrator MCP-Server) | `health_check_run`, `health_check_query` — Query/Trigger-Interface für externe Konsumenten |
| **Dashboard** | dev-hub (Controlling-Dashboard) | **Read-only** — liest `health_check_results` aus shared DB; keine Schreiblogik |

### 9. Migration von `persist_health_score` (REC-8)

`persist_health_score` (dev-hub Portal-App) schreibt heute Health-Daten außerhalb des
neuen Datenmodells. Migrationsplan:
1. Phase 1: `health_check_results`-Tabelle einführen; `persist_health_score` bleibt
   parallel aktiv.
2. Nach Phase 2: Schreiblogik von `persist_health_score` auf das neue Framework umstellen
   (ein Shim, der `HealthCheck`-Objekte erzeugt).
3. Nach Phase 3: `persist_health_score` als Deprecated markieren + Shim entfernen.
Kein zweiter Wahrheitsstand nach Phase 3.

### 10. Ownership + Kompatibilitätsregeln für `health_check_results` (REC-10)

- **Owner:** mcp-hub (Schema-Migrationen via Alembic im mcp-hub-Repo).
- **Lesende Consumers** (dev-hub Dashboard): dürfen nur auf Felder zugreifen, die in
  `health_check_results_public_v1` (DB-View) exponiert sind. Direkte Tabellen-Joins
  sind deprecated und werden in Phase 2 per View-Guard erzwungen.
- **Breaking-Schema-Changes** erfordern: incrementierten `metric_version` + Changelog-Eintrag
  + Migrations-Skript + max. 2 Wochen Parallelbetrieb alter/neuer Schema-Version.

## Verworfene Alternativen (REC-2/AD-4)

| Alternative | Warum verworfen |
|---|---|
| **Schreiblogik in `dev-hub`, MCP-Tools nur als Query-/Trigger-Client** | Hätte die SSoT-Situation in dev-hub verschlimmert (4. Health-App) und erfordert eine HTTP-API als Schnittstelle zwischen dev-hub und mcp-hub — mehr Komplexität, nicht weniger. |
| **Framework-Core in `platform` als shared Package** | Richtige Trennung von Domain-Core, aber: `platform` ist ein Python-Package ohne eigene Runtime; der Core braucht DB-Zugriff und Workflow-Ausführung, was in `platform`-Package-Form nicht passt. Als Option für zukünftige Extraktion, falls ein dritter Consumer entsteht. |
| **Managed Observability (Datadog/Grafana Cloud)** | Kein vorausgesetztes SaaS-Budget; Souveränitätsanforderungen der Public-Sector-Orgs schließen externen SaaS für Code-Daten aus. |
| **Gemeinsames Issue-Label-Schema ohne Framework** | Löst Persistenz und Trend-Sicht nicht — zu schwach für das beschriebene Problem. |

## Phasierung (aktualisiert nach REC-4/REC-5)

- **Phase 1 (~2h, 1 PR):**
  Framework-Core + Plugin-Registry + `health_check_results`-Tabelle + **drei**
  repräsentative Referenz-Dimensionen end-to-end:
  (1) Dependency-CVE (`pip-audit` → DB → Cerebras-Narrative → Auto-Issue bei `fail`),
  (2) Modell-Drift (bestehenden Workflow als Dimension registrieren),
  (3) ADR-Freshness (bestehenden MCP-Tool-Output als Dimension registrieren).
  → Danach: **Reifegrad-Gate** — Review ob Core-Schnittstelle stabil genug für weitere
  Dimensionen. Erst nach positivem Gate beginnt Phase 2.

- **Phase 2 (2–3 PRs):**
  Weitere Tier-C-Dimensionen (Coverage, Cost, Container, Repo-Konsistenz) + Wochenreport.
  Migration `persist_health_score` auf Shim.

- **Phase 3 (3–4 PRs):**
  Tier-D/E-Dimensionen (CI-Hygiene, Doc-Drift, Onboarding-Readiness, Secret-Rotation)
  + Trend-Visualisierung im Controlling-Dashboard + `persist_health_score`-Deprecation.

- **Phase 4 (schrittweise):**
  Bestehende Surfaces als Dimensions einreihen — **nicht** replatformieren.

  | Surface | Ziel-Dimension | Datenquelle | Cadence | Eskalation | Migrationsrisiko |
  |---|---|---|---|---|---|
  | `apps/repo_health/` | `git_state` | Bestehender Job-Output → `metric` | Daily | warn→Wochenreport | niedrig (read-only Konverter) |
  | `apps/quality_agent/` | `code_quality` | Headless-LLM-Report-JSON | Daily | fail→Auto-Issue | mittel (eigene LLM-Kosten) |
  | `apps/health/` | `external_health` | HTTP-Probe-Ergebnis | Hourly | fail→Notif | niedrig (stateless Probe) |
  | `llm-model-drift.yml` | `model_drift` | Baseline-Diff-Output | Daily | fail→Auto-Issue | niedrig (Phase-1-Referenz) |

  Jede Phase-4-Integration erfordert: bestehende Semantik-Mapping-Dokument +
  Pilot (1 Repo) + 2-Wochen-Beobachtung vor Rollout.

## Akzeptanzkriterien (REC-5)

- Einheitliche `HealthCheck`-Struktur mit `metric_schema`/`metric_version` persistiert in `health_check_results`
- **3 Referenz-Dimensionen** (CVE, Modell-Drift, ADR-Freshness) end-to-end, inkl. Narration + Auto-Issue
- Reifegrad-Gate nach Phase 1 explizit dokumentiert und bestanden
- Alle Auto-Issues über `health-drift`-Schema dedup'd
- LLM-Routing pro Dimension explizit (kein Opus-Drift), Budget-Gates konfiguriert
- Souveränitäts-Guardrail: Public-Sector-Repos lehnen externen LLM mit Hard-Fail ab + Audit-Log
- `persist_health_score` nach Phase 3 deprecated + Shim-Entfernung vollständig

## Konsequenzen

**+** Eine Sicht, ein Datenmodell, konsistente Eskalation, Trend über Zeit, kostenkontrolliert.

**+** Core + Plugin-Registry verhindert premature Abstraktion; neue Dimensions können
schrittweise hinzukommen, ohne Core anzufassen.

**+** Tools-first-Prinzip (pip-audit, Trivy etc.) reduziert Eigenentwicklungsaufwand und
nutzt battle-tested Toolqualität.

**−** Bewusstes Reversal der „headless Agents → dev-hub"-Konvention — neue Maintainer
müssen darauf hingewiesen werden (Kommentar im dev-hub `CLAUDE.md` + dieses ADR als Quelle).

**−** Neue shared-DB-Tabelle = neuer Kopplungspunkt zwischen mcp-hub (schreibt) und
dev-hub (liest). View-Gate und Ownership-Regeln mindern das Risiko (→ Abschnitt 10).

**−** LLM-Kosten skalieren mit Dimension-Anzahl. Budget-Gates pro Dimension halten
Gesamtkosten einstellig $/Tag (Cerebras-Tier-1a); Degradationsmodus als Fallback.
