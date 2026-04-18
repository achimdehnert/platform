---
title: "ADR-165: Adopt Plugin-based REFLEX Review Engine with Grafana Controlling"
status: accepted
date: 2026-04-18
deciders: [achimdehnert]
depends_on: [ADR-163, ADR-164, ADR-082, ADR-066]
implementation_status: partial
implementation_evidence:
  - "iil-reflex/reflex/review/ — ReviewEngine, 4 plugins, CLI (Stage 1)"
  - "platform/.windsurf/workflows/onboard-repo.md — Step 6.7 REFLEX Setup"
  - "230/230 tests passing incl. 45 review tests"
tags: [reflex, review, grafana, controlling, llm-routing, quality]
---

# ADR-165: Adopt Plugin-based REFLEX Review Engine with Grafana Controlling

## 1. Kontext

ADR-163 definiert den REFLEX Quality Standard mit drei Tiers für 22 Platform-Repos.
Die manuelle Durchsetzung über 10 Cascade-Workflows (.md) ist instabil —
Controlling und Dokumentation passieren "selten und nicht stabil"
(Erfahrungswert aus 6 Monaten Betrieb).

Gleichzeitig existiert bereits Infrastruktur:

| Komponente | Status | Details |
|-----------|--------|---------|
| Grafana 11.4 | ✅ Läuft | `mcp_hub_grafana`, Port 3000 |
| PostgreSQL 16 + pgvector | ✅ Läuft | `mcp_hub_db`, DB `orchestrator_mcp` |
| Datasource | ✅ Provisioniert | `orchestrator_pg` → Grafana |
| Dashboard | ✅ 10 Panels | "Agent Controlling — LLM-Kosten & Qualität" |
| `llm_calls` Tabelle | ✅ Schema fertig | model, tokens, cost_usd, duration_ms, repo |
| `agent_memory_entries` | ✅ 79 Einträge | pgvector embeddings, 4 entry_types |

**Problem:** Die Infrastruktur existiert, aber es fließen kaum Daten hinein
(`llm_calls`: 11 Einträge seit März), weil alles manuell getriggert werden muss.

## 2. Decision Drivers

- **D-1:** Controlling muss **Side-Effect** sein, nie Extra-Schritt
- **D-2:** Review-Regeln müssen **erweiterbar** sein (1 Datei = 1 Plugin)
- **D-3:** Triviale Fixes sollen **günstigere LLMs** nutzen (Token-Einsparung)
- **D-4:** Stage-2-Entscheidung (eigener MCP-Server) muss **datenbasiert** sein
- **D-5:** Bestehende Infra (Grafana, PostgreSQL, aifw) maximal nutzen
- **D-6:** First-Run darf nicht **überwältigen** (Baseline-Konzept)
- **D-7:** False Positives müssen **trackbar** sein (Plugin-Qualität)

## 3. Considered Options

### Option A: Eigener reflex-mcp Server sofort

Neuer MCP-Server (`reflex-mcp`) mit eigener Prozessinstanz, eigenem Port,
vollständiger Autonomie (auto-trigger, auto-issue, auto-report).

- Good: Maximale Autonomie, kein Cascade nötig für Reviews
- Good: Saubere Separation of Concerns
- Bad: Hoher initialer Aufwand (Server-Setup, Port-Registrierung, Auth, Monitoring)
- Bad: Overhead ohne Beweis, dass Reviews regelmäßig genutzt werden
- Bad: Neuer Prozess auf ohnehin belastetem Server (106 Container)

### Option B: Plugins in iil-reflex mit Stage 1→2 Evolution (gewählt)

Plugin-Engine in bestehendem `iil-reflex` Package. Stage 1: platform-context
importiert `reflex.review`, Cascade orchestriert. Stage 2 (datenbasiert): Eigener
Server wenn Controlling-Schwellwerte erreicht.

- Good: Minimaler initialer Aufwand (kein neuer Server/Port/Prozess)
- Good: Sofort nutzbar via CLI und MCP
- Good: Datenbasierte Stage-2-Entscheidung statt Spekulation
- Good: 0 Code-Migration bei Stage 2 (Wrapper-Pattern)
- Bad: Stage 1 noch Cascade-abhängig für Issues/Outline-Reports
- Bad: platform-context muss iil-reflex als Dependency installieren

### Option C: Reine Workflow-Automatisierung (bestehende .md Workflows verbessern)

Keine Plugin-Engine. Stattdessen bestehende Cascade-Workflows (.md) verbessern
und strukturierter gestalten.

- Good: Kein neuer Code nötig
- Good: Sofort einsetzbar
- Bad: Bleibt Cascade-abhängig (kein CI-Integration)
- Bad: Kein strukturiertes Finding-Format (Prosa-Output)
- Bad: Kein Controlling, kein Grafana, keine Metriken
- Bad: Nicht erweiterbar — jede neue Prüfung = neues Workflow-Dokument
- Bad: Genau das Pattern das "selten und nicht stabil" ist

## 4. Decision Outcome

**Chosen Option: B — Plugins in iil-reflex mit Stage 1→2 Evolution**, weil:

1. Es die bestehende Infrastruktur (Grafana, PostgreSQL, aifw) maximal nutzt (D-5)
2. Der initiale Aufwand minimal ist — kein neuer Server nötig (vs. Option A)
3. Controlling als Side-Effect statt Extra-Schritt ermöglicht (D-1)
4. Die Stage-2-Entscheidung datenbasiert getroffen wird (D-4)
5. Es sofort in CI/CLI nutzbar ist, anders als Option C
6. 0 Code-Migration bei Stage 2 — nur ein neuer Server-Wrapper

Option A wird nicht verworfen sondern ist das explizite Stage-2-Ziel,
sobald Controlling-Schwellwerte (§5.7) dies rechtfertigen.

## 5. Entscheidungsdetails

### 5.1 Plugin-basierte Review Engine in iil-reflex

Plugin-Interface in `reflex/review/`:

```python
class ReviewPlugin:
    name: str                    # z.B. "compose"
    applicable_tiers: list[int]  # z.B. [1, 2] — nur für Tier 1+2

    def check(self, repo: str, context: dict) -> list[Finding]:
        ...

@dataclass
class Finding:
    rule_id: str          # "compose.port_matches_yaml"
    severity: str         # "block" | "warn" | "info"
    message: str          # Menschenlesbar
    adr_ref: str | None   # "ADR-164 §3.3"
    fix_hint: str | None  # Code-Snippet oder Befehl
    file_path: str | None # Betroffene Datei
    auto_fixable: bool    # Kann automatisch gefixt werden?
    fix_complexity: str   # "trivial" | "simple" | "moderate" | "complex"
```

Package-Struktur:

```
iil-reflex/reflex/
├── review/
│   ├── __init__.py          # run_review(), ReviewEngine
│   ├── types.py             # Finding, ReviewResult, ReviewMetrics
│   ├── engine.py            # Plugin-Discovery, Execution, Metrics
│   ├── plugins/
│   │   ├── repo_plugin.py       # Repo-Vollständigkeit
│   │   ├── compose_plugin.py    # Compose-Audit
│   │   ├── adr_plugin.py        # ADR-Checklist
│   │   └── port_plugin.py       # Port-Drift (ports.yaml)
│   └── rules/
│       ├── base_rules.yaml      # Gemeinsame Regeln
│       └── per_repo/            # Repo-spezifische Overrides
```

Starter-Plugins: `repo`, `compose`, `adr`, `port`.
Neues Plugin = 1 Python-Datei in `plugins/`, keine Server-Änderung.

### 5.2 Dual-Interface: CLI + MCP

**CLI** (CI/lokal):

```bash
python -m reflex review repo risk-hub
python -m reflex review compose risk-hub
python -m reflex review adr ADR-163
python -m reflex review platform
python -m reflex review repo risk-hub --json --fail-on block
```

**MCP** (Cascade):

platform-context importiert `reflex.review`:

```python
# platform_context_mcp — 1 neues Tool
from reflex.review import run_review

result = run_review(repo="risk-hub", types=["repo", "compose"])
# → Strukturiertes JSON, kein Prosa
```

Ein Regelwerk, zwei Interfaces.

### 5.3 Finding → Model-Tier Routing

Basierend auf den bestehenden Model-Tiers (agent_team_config.yaml, ADR-066):

| fix_complexity | Model-Tier | Kosten | Executor |
|----------------|-----------|--------|----------|
| trivial | lean_local (qwen2.5-coder:32b) | $0 | Developer Agent |
| simple | budget_cloud (MiniMax-M2.5) | $ | Developer Agent |
| moderate | standard_coding (claude-sonnet) | $$ | Cascade |
| complex | high_reasoning (claude-opus) | $$$ | Cascade + Human |

Anbindung über bestehenden `delegate_subtask`:

```python
mcp2_delegate_subtask(
    subtask_description=f"Fix: {finding.message}\nHint: {finding.fix_hint}",
    project_path=f"/home/devuser/github/{repo}",
    affected_paths=[finding.file_path],
    task_type="bugfix",
)
```

### 5.4 Automatisches Controlling via Grafana

**Neue DB-Tabellen** in `orchestrator_mcp`:

```sql
CREATE TABLE review_metrics (
    id              BIGSERIAL PRIMARY KEY,
    repo            TEXT NOT NULL,
    review_type     TEXT NOT NULL,        -- "repo", "compose", "adr", "port"
    findings_total  INTEGER NOT NULL DEFAULT 0,
    findings_block  INTEGER NOT NULL DEFAULT 0,
    findings_warn   INTEGER NOT NULL DEFAULT 0,
    findings_info   INTEGER NOT NULL DEFAULT 0,
    findings_auto_fixable INTEGER NOT NULL DEFAULT 0,
    false_positives INTEGER NOT NULL DEFAULT 0,
    score_pct       NUMERIC(5,2),         -- 0.00 - 100.00
    duration_s      NUMERIC(8,2),
    triggered_by    TEXT DEFAULT 'manual', -- "session_start", "ship", "ci", "cron"
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE deploy_events (
    id              BIGSERIAL PRIMARY KEY,
    repo            TEXT NOT NULL,
    image_tag       TEXT,
    duration_s      NUMERIC(8,2),
    success         BOOLEAN NOT NULL DEFAULT true,
    triggered_by    TEXT DEFAULT 'manual',
    review_score    NUMERIC(5,2),         -- Score vor Deploy
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE health_checks (
    id              BIGSERIAL PRIMARY KEY,
    repo            TEXT NOT NULL,
    domain          TEXT NOT NULL,
    http_status     INTEGER,
    latency_ms      INTEGER,
    healthy         BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_review_metrics_repo_date ON review_metrics(repo, created_at DESC);
CREATE INDEX idx_deploy_events_repo_date ON deploy_events(repo, created_at DESC);
CREATE INDEX idx_health_checks_repo_date ON health_checks(repo, created_at DESC);
```

**Instrumentierungspunkte** (alles Side-Effects):

| Datenstrom | Trigger | Tabelle |
|-----------|---------|---------|
| LLM-Token-Nutzung | Side-Effect in `aifw.sync_completion()` | `llm_calls` |
| Review-Findings | Side-Effect in `reflex.review.engine` | `review_metrics` |
| Deploy-Events | Side-Effect in `ship.sh` / CI | `deploy_events` |
| Container-Health | CronJob (5 min) | `health_checks` |

**Grafana-Dashboards:**

1. **Agent Controlling** (existiert, erweitern mit aifw-Daten)
2. **Platform Health** (NEU): Container-Status, Port-Drift, Health-Endpoints
3. **Review Controlling** (NEU): Findings over Time, Auto-Fix-Rate, Score per Repo
4. **LLM Cost Intelligence** (NEU): Token pro Model-Tier, Einsparung durch Routing
5. **Stage 2 Readiness** (NEU): Schwellwerte-Panel (siehe §5.7)

### 5.5 aifw-Instrumentierung

`iil-aifw/aifw/service.py` — `sync_completion()` ist der Bottleneck für alle
22 Apps. Eine Instrumentierung dort erfasst automatisch alle App-LLM-Calls:

```python
def sync_completion(...):
    start = time.monotonic()
    result = _call_provider(...)
    duration_ms = int((time.monotonic() - start) * 1000)

    # Side-Effect: Metrics (fire-and-forget, darf nicht failen)
    _log_llm_call(model, result.usage, duration_ms, repo=_get_repo_context())
    return result
```

Rollout: aifw Version bump → alle Apps bekommen Metrics beim nächsten Deploy.

### 5.6 Stufenmodell: Stage 1 → Stage 2

**Stage 1: Plugins in iil-reflex, Cascade orchestriert**

```
┌──────────┐  import   ┌─────────────┐  CLI    ┌──────────┐
│ platform-│ ────────→ │ iil-reflex  │ ←───── │ CI / Dev │
│ context  │           │ reflex/     │        └──────────┘
│ (MCP)    │           │  review/    │
└────┬─────┘           │  plugins/   │
     │                 └──────┬──────┘
     ▼                        │ Side-Effect
┌──────────┐           ┌──────┴──────┐
│ Cascade  │           │ PostgreSQL  │──→ Grafana
│ → Memory │           │ (metrics)   │
│ → Issues │           └─────────────┘
└──────────┘
```

- Plugins + Finding-Format + Regeln leben in `iil-reflex`
- platform-context macht `from reflex.review import run_review`
- Cascade entscheidet: Finding → Memory / GitHub Issue / Auto-Fix
- Metriken als Side-Effect → PostgreSQL → Grafana

**Stage 2: Eigener reflex-mcp Server**

```
┌──────────┐  MCP      ┌─────────────┐  CLI    ┌──────────┐
│ Cascade  │ ────────→ │ reflex-mcp  │ ←───── │ CI / Dev │
│          │ ←──JSON── │  server.py  │        └──────────┘
└──────────┘           │ importiert: │
                       │ iil-reflex  │
                       └──────┬──────┘
                              │ Automatisch
                       ┌──────┴──────┐
                       │ → Memory    │
                       │ → Issues    │
                       │ → Outline   │
                       │ → Grafana   │
                       └─────────────┘
```

- reflex-mcp = neuer MCP-Server, importiert dieselben Plugins
- Auto-Trigger: Git-Hook → Review (ohne Cascade)
- Auto-Issue: BLOCK-Findings → GitHub Issue (ohne Cascade)
- Auto-Report: Outline Runbook (ohne Cascade)
- Cascade wird nur bei `complex` Findings involviert

**Migration Stage 1 → 2:**

| Komponente | Stage 1 → 2 Aufwand |
|-----------|---------------------|
| Plugin-Code | 0 (unverändert) |
| Regeln (YAML) | 0 (unverändert) |
| Finding-Format | 0 (unverändert) |
| CLI | 0 (unverändert) |
| Metriken | 0 (unverändert) |
| MCP-Zugang | 1 neuer `server.py` |
| Cascade-Rolle | Workflow-Update |
| Outline-Reports | Server-Feature |
| GitHub Issues | Server-Feature |
| Auto-Trigger | Server-Feature |

5 von 10 Zeilen = "0 Aufwand". Stage 2 ist kein Rewrite sondern ein Wrapper.

### 5.7 Stage-2-Schwellwerte (Controlling-basiert)

Grafana Dashboard "Stage 2 Readiness" zeigt live:

| Metrik | Quelle | Schwellwert | Gewicht |
|--------|--------|-------------|---------|
| Plugin-Anzahl | `reflex review --info` | ≥ 8 | 1x |
| Reviews/Woche | `review_metrics` | ≥ 20 | 2x |
| Findings/Review Ø | `AVG(findings_total)` | ≥ 5 | 1x |
| Auto-Fix-Quote | `SUM(auto_fixable)/count` | ≥ 40% | 2x |
| Cascade-Token für Reviews | `llm_calls WHERE source='review'` | ≥ 15% | 2x |
| Review-Dauer Ø | `AVG(duration_s)` | > 30s | 1x |

**Entscheidungsregel:** Stage 2 wenn ≥ 4 von 6 Schwellwerten erreicht.
Grafana-Alert bei Erreichen → Outline Konzept-Dokument wird erstellt.

### 5.8 Baseline + Suppression (UX)

**Baseline:** Erster Review-Lauf speichert alle Findings als Baseline.
Folge-Runs melden nur Delta (neue Findings). Baseline ist separat abarbeitbar.

```bash
reflex review repo risk-hub --init-baseline   # Baseline setzen
reflex review repo risk-hub                    # Nur neue Findings
reflex review repo risk-hub --include-baseline # Alles anzeigen
```

Speicherort: `.reflex/baseline.json` (committed, pro Repo).

**Suppression:** Findings können pro Repo unterdrückt werden:

```yaml
# .reflex/suppressions.yaml (committed, reviewbar)
suppressions:
  - rule_id: repo.readme_outdated
    reason: "Sprint 12 — wird in Doku-Woche gefixt"
    until: 2026-05-01     # Temporär, auto-reopen nach Ablauf

  - rule_id: compose.no_logging_config
    reason: "Logging via Loki geplant (ADR-TBD)"
    permanent: true        # Permanent, mit Begründung
```

**False-Positive-Tracking:**
- Jedes abgelehnte Finding → `review_metrics.false_positives += 1`
- Grafana Panel: False-Positive-Rate pro Plugin
- Schwellwert: > 10% FP-Rate → Plugin wird auto-disabled + Issue erstellt

## 6. Konsequenzen

### 6.1 Positiv

- Controlling als Side-Effect → stabil ohne manuelle Disziplin
- Plugin-System → erweiterbar ohne Server-Neustart
- Model-Routing → Token-Einsparung bei trivialen Fixes (~46% lokal/kostenlos)
- Datenbasierte Stage-2-Entscheidung statt Bauchgefühl
- Baseline-Konzept → kein First-Run-Schock
- FP-Tracking → selbstkorrigierende Plugin-Qualität

### 6.2 Negativ / Trade-offs

- aifw-Instrumentierung betrifft alle 22 Apps (Rollout über Version-Bump)
- 3 neue DB-Tabellen zu pflegen
- Grafana muss zugänglich gemacht werden (Nginx/Auth oder CF Tunnel)
- Baseline-Init ist 1x manueller Schritt pro Repo

### 6.3 Evolutionspfad

Stage 1 → Stage 2 erfordert null Plugin-Code-Änderung.
Einziger Aufwand: neuer `reflex-mcp/server.py` als MCP-Wrapper.
platform-context `review()` Tool wird bei Stage 2 deprecated.

### 6.4 Not in Scope

- Playwright-Integration in Reviews (bleibt per ADR-162)
- Grafana-Alerting nach Slack/Discord (kann später ergänzt werden)
- Multi-Tenant Review-Isolation (nicht benötigt bei Solo-Entwickler)

## 7. Risiken

| Risiko | Eintrittswahrscheinlichkeit | Mitigation |
|--------|---------------------------|-----------|
| aifw-Instrumentierung verlangsamt LLM-Calls | Gering | Fire-and-forget, async, kein await |
| False Positives untergraben Vertrauen | Mittel | FP-Tracking + auto-disable bei > 10% |
| Grafana-DB wird zu groß | Gering | Retention-Policy: health_checks > 90d löschen |
| iil-reflex nicht in mcp-hub venv installiert | Mittel | `pip install iil-reflex` in mcp-hub Setup-Script |

## 8. Developer Experience

### Erster Kontakt (einmalig pro Repo)

```
$ reflex review repo risk-hub --init-baseline

  37 Findings gefunden. Baseline gespeichert in .reflex/baseline.json
  Ab jetzt werden nur NEUE Findings gemeldet.
  Bestehende sichten: reflex review repo risk-hub --show-baseline
```

### Session-Start (automatisch)

```
/session-start → Lade Kontext für risk-hub...

  📋 2 offene Review-Findings:
  🔴 BLOCK  compose.port_drift — 8001:8000 → 8090:8000 (auto-fixable, trivial)
  🟡 WARN   repo.no_memory_limit — mem_limit fehlt (auto-fixable, simple)

  → Soll ich die 2 auto-fixable Findings beheben?
```

### Auto-Fix (0 Cascade-Tokens)

```
User: ja

  ✅ compose.port_drift → Developer Agent (qwen local) → fixed
  ✅ repo.no_memory_limit → Developer Agent (MiniMax) → fixed
  Verification: reflex review compose risk-hub → 0 BLOCK ✅
  0 Cascade-Tokens verbraucht.
```

### Vor Ship (Gate)

```
/ship risk-hub → Pre-Ship Review...

  ✅ 7/8 Checks passed, Score: 87%
  🟡 1 WARN (repo.readme_outdated) — nicht blockierend
  → SHIP ALLOWED. Weiter? [ja/nein]
```

### CI (automatisch, ohne Cascade)

```yaml
- name: REFLEX Review
  run: |
    pip install iil-reflex
    python -m reflex review repo . --json --fail-on block
```

### Feedback bei False Positive

```
Cascade: 🔴 BLOCK compose.port_drift — 8090 ≠ 8090
User: Das ist falsch.
Cascade: False Positive geloggt → review_metrics.false_positives += 1
```

## 9. Implementierungsplan

| Phase | Aufwand | Deliverable | Metriken-Impact | Status |
|-------|---------|-------------|-----------------|--------|
| 0 | 0.5 Session | DB-Schema (3 Tabellen) + Grafana RO-User verifizieren | Infrastruktur | ⬜ |
| 1a | 0.5 Session | Plugin-Engine + Finding-Format + 2 Plugins (repo, compose) | Review-Daten | ⬜ |
| 1b | 0.5 Session | aifw instrumentieren → `llm_calls` für alle Apps | LLM-Daten | ⬜ |
| 1c | 0.5 Session | Grafana Dashboards 2-5 provisionieren | Sichtbarkeit | ⬜ |
| 1d | 0.5 Session | CronJobs (health_checks) + CLI `reflex review` | Platform-Health | ⬜ |
| 2 | 0.5 Session | Auto-Fix-Routing + Stage-2-Readiness Panel | Entlastung | ⬜ |

**Gesamtaufwand: 3 Sessions**

## 10. Open Questions

| # | Frage | Status | Entscheidung |
|---|-------|--------|--------------|
| Q-1 | Wie reportet aifw an orchestrator_mcp DB? Direct DB, HTTP-Endpoint, oder Message Queue? | Offen | Empfehlung: Lightweight HTTP-Endpoint im mcp-hub, kein Direct-DB aus Apps |
| Q-2 | Grafana-Zugang: Nginx-Proxy mit Basic Auth oder CF-Tunnel mit Access? | Offen | Abhängig von Nutzerkreis — Solo: Nginx genügt, Team: CF Access |
| Q-3 | Bestehende 10 Cascade-Workflow-Dateien (.md): Deprecated oder migriert? | Offen | Empfehlung: Deprecated nach Plugin-Äquivalent vorhanden, nicht löschen |
| Q-4 | CronJob für health_checks: systemd timer, Docker container, oder Celery beat? | Offen | Empfehlung: systemd timer (existierendes Pattern: docker-cleanup.sh) |
| Q-5 | Migrations-Werkzeug für neue Tabellen: Alembic (mcp-hub) oder Raw SQL? | Offen | Empfehlung: Raw SQL via deploy-script (mcp-hub nutzt kein Alembic bisher) |

## 11. Confirmation

ADR-165 ist bestätigt wenn:

- [ ] `reflex review repo risk-hub` gibt strukturiertes JSON zurück
- [ ] ≥ 4 Plugins implementiert (repo, compose, adr, port)
- [ ] Findings erscheinen in `review_metrics` Tabelle
- [ ] Grafana Dashboard "Review Controlling" zeigt Live-Daten
- [ ] `llm_calls` enthält Daten von ≥ 3 verschiedenen Apps
- [ ] Baseline-Init funktioniert (`.reflex/baseline.json`)
- [ ] Suppressions werden respektiert (`.reflex/suppressions.yaml`)
- [ ] Auto-Fix eines trivialen Findings via Developer Agent erfolgreich

## 12. More Information

- **ADR-163**: REFLEX Tiering — definiert die 3 Quality-Tiers die diese Review-Engine durchsetzt
- **ADR-164**: Port Strategy — `ports.yaml` als Datenquelle für port_plugin
- **ADR-162**: REFLEX UI Testing — Playwright-Integration (bleibt separat, §6.4)
- **ADR-066**: Agent Team Architecture — Developer Agent für Auto-Fixes (§5.3)
- **ADR-082**: Model Routing — Model-Tiers lean_local/budget_cloud/standard/high (§5.3)
- **ADR-045**: Config via decouple — Secrets-Pattern für DB-Credentials

<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths: ["iil-reflex/reflex/review/", "mcp-hub/orchestrator_mcp/", "platform/infra/ports.yaml"]
supersedes_check: null
-->

## Changelog

| Datum | Änderung |
|-------|---------|
| 2026-04-18 | Initiale Version (proposed) |
| 2026-04-18 | Review-Fixes: MADR 4.0 Considered Options, Decision Outcome, Open Questions, Drift-Detector, Phase-Tracking |
