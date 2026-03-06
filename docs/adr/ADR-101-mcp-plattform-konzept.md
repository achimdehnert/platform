---
status: proposed
date: 2026-03-06
decision-makers: Achim Dehnert
consulted: Cascade (KI-Agent)
informed: –
---

# ADR-101: Adopt 3-Tier MCP Architecture for Platform-Wide Tool Orchestration

## Metadaten

| Attribut        | Wert |
|-----------------|------|
| **Status**      | Proposed |
| **Scope**       | platform |
| **Erstellt**    | 2026-03-06 |
| **Autor**       | Cascade + Achim Dehnert |
| **Reviewer**    | Claude (2026-03-06) |
| **Supersedes**  | – |
| **Relates to**  | ADR-044 (FastMCP-Standard), ADR-054 (MCP-Architektur), ADR-059 (Drift-Detector) |

## Repo-Zugehoerigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten |
|----------------|------------|--------------------------------|
| `platform`     | Referenz   | `docs/adr/ADR-101-*` |
| `mcp-hub`      | Primaer    | `deployment_mcp/`, `query_agent_mcp/`, `registry_mcp/` |
| `bfagent`      | Sekundaer  | `packages/*_mcp/` |
| Alle 13 Hubs   | Sekundaer  | `/healthz/` Endpoints, `.env.prod` |

---

## Decision Drivers

- **D-01 Tool-Limit**: Windsurf hat ein 100-Tool-Limit (Stand 2026-03). Aktuell 45/100 belegt — jeder neue MCP-Server muss das Budget beruecksichtigen.
- **D-02 Plattform-Scope**: 23 Repos, 13 deployed Django-Apps, 6 Python-Packages — MCP-Config ist global, nicht repo-spezifisch.
- **D-03 Keine Health-Sichtbarkeit**: 13 deployed Apps ohne zentrales Health-Monitoring via MCP. Ausfaelle werden erst bei User-Beschwerden bemerkt.
- **D-04 Cross-Repo Blindheit**: Package-Updates (aifw, promptfw) koennen konsumnierende Repos brechen — keine Abhaengigkeits-Sichtbarkeit.
- **D-05 Tool-Routing unklar**: Entwickler nutzen `ssh_manage exec curl` statt `cicd_manage run_logs` — kein definiertes Routing MCP-Tool vs. SSH.
- **D-06 MCP Spec Baseline**: MCP Spec 2025-11-25 bringt Tasks Primitive (async long-running ops) und Structured Tool Outputs — nicht genutzt.

---

## 1. Context and Problem Statement

Die BF Platform betreibt 23 GitHub-Repos auf einem Hetzner-Server (88.198.191.108)
mit Windsurf/Cascade als KI-gestützter Entwicklungsumgebung. MCP-Server verbinden
den KI-Agent mit Infrastruktur, Code und Daten.

### 1.1 Ist-Zustand

14 MCP-Server konfiguriert (4 aktiv, 10 disabled), 45 von 100 Tool-Slots belegt.

| Tier | Server | Status | Tools |
|------|--------|--------|-------|
| Aktiv | deployment-mcp | ✅ | 12 (SSH, Docker, DB, Git, CI/CD, Env, Server, Firewall, System, Network, Pip) |
| Aktiv | github | ✅ | 26 (Issues, PRs, Repos, Files, Code Search) |
| Aktiv | platform-context | ✅ | 4 (Architecture Rules, Banned Patterns, Project Facts) |
| Aktiv | test-generator | ✅ | 3 (Test-Generierung) |
| Disabled | bfagent, bfagent-db, bfagent-monitoring | ⏸ | 9 |
| Disabled | cadhub, illustration | ⏸ | 6 |
| Disabled | code-quality, llm-mcp, orchestrator | ⏸ | 6 |
| Disabled | docs-search, registry | ⏸ | 10 |

### 1.2 Warum jetzt

1. Coach-hub CI/CD, governance Features und billing-hub Integration gerade deployed — Plattform ist in aktivem Ausbau
2. Health-Monitoring ist nach 13 deployed Apps nicht mehr optional
3. MCP-Config wurde gerade bereinigt (18→14 Server) — optimaler Zeitpunkt fuer Strukturierung

### 1.3 MCP Spec Baseline

Dieses ADR basiert auf **MCP Specification 2025-11-25**. Relevante Features:

| Feature | Relevanz | Status |
|---------|----------|--------|
| Tasks Primitive (async long-running) | health_dashboard parallel, Deploy-Jobs | Evaluieren in Phase 2 |
| Structured Tool Outputs | Typisierte Returns statt str | Neue Server nutzen es |
| `.well-known` Server Discovery | registry_mcp Auto-Discovery | Beobachten |

### 1.4 Transport-Entscheidung

Alle MCP-Server nutzen **stdio-Transport** (Prozess-Spawn pro Session via Windsurf).
Streamable HTTP Transport wird evaluiert sobald MCP-SDK-Implementierung stabil ist.

**Konsequenz**: MCP-Server laufen auf der **lokalen Dev-Maschine**, nicht auf Hetzner.
Server-seitige Operationen (Health-Checks, Docker, DB) erfordern zwingend SSH.

### 1.5 Entwicklungsstandard

Alle neuen MCP-Server folgen **ADR-044**: FastMCP, `pyproject.toml`, `src/`-Layout,
`lifespan`-Hook fuer Clients. Source-Repo: `mcp-hub`.

---

## 2. Considered Options

### Option A: 3-Tier Consolidated Architecture ✅

Health-Monitoring als Actions in bestehende `system_manage` (0 neue Tool-Slots),
neue Server nur wo eigene Kategorie zwingend (docs-search, registry).

**Pros:**
- Minimaler Tool-Budget-Verbrauch (45 aktiv, 76 max)
- Health-Dashboard ohne neuen MCP-Server-Prozess
- Klare Tier-Zuordnung (Always-On / Plattform / Repo-spezifisch)
- SSH-Abhaengigkeit fuer Server-Ops ist architektonisch korrekt (stdio-Transport)

**Cons:**
- Health-Dashboard ist an deployment-mcp Verfuegbarkeit gebunden
- Kein Tasks-Primitive fuer async Dashboard (blockierender Call)
- In-Memory-State fuer History geht bei Restart verloren

### Option B: Separate MCP-Server pro Capability

Eigener `health-mcp`, `dependency-mcp`, `log-mcp` etc. als standalone Server.

**Pros:**
- Unabhaengige Server, kein Single-Point-of-Failure
- Saubere Separation of Concerns

**Cons:**
- +4-5 Tool-Slots pro Server → Budget schnell erschoepft
- Mehr Prozesse, laengere Startzeit, hoehere Ressourcenlast
- Health-Server braucht TROTZDEM SSH (stdio-Transport, Apps auf Hetzner) → **Abgelehnt weil:** Kein Vorteil gegenueber Actions in deployment-mcp, aber hoeherer Overhead

### Option C: Status quo beibehalten

4 aktive Server, manuelle SSH-Commands fuer Health/Dependencies.

**Pros:**
- Kein Aufwand
- Bewaeahrt sich seit Monaten

**Cons:**
- Kein Health-Dashboard → Ausfaelle werden zu spaet erkannt
- Kein Dependency-Tracking → Breaking Changes unbemerkt
- SSH-Workarounds statt strukturierter MCP-Tools → **Abgelehnt weil:** Skaliert nicht mit 23 Repos und 13+ deployed Apps

---

## 3. Decision Outcome

**Gewaehlte Option: Option A — 3-Tier Consolidated Architecture**

Health-Monitoring wird als Action in `system_manage` integriert (bereits implementiert).
Neue MCP-Server entstehen nur fuer eigenstaendige Domaenen (docs-search via pgvector,
registry via Platform-DB). Das Tool-Budget bleibt bei 76/100 max, mit 24 Slots Reserve.

---

## 4. Implementation Details

### 4.1 Repo-Inventar

#### Django-Apps (13 deployed auf Hetzner)

| Repo | Port | Celery | DB | Domain |
|------|------|--------|----|--------|
| coach-hub | 8007 | ✓ | postgres | kiohnerisiko.de |
| bfagent | 8091 | ✓ | pgvector | bfagent.iil.pet |
| billing-hub | 8092 | ✓ | postgres | billing.iil.pet |
| wedding-hub | 8093 | ✓ | postgres | wedding.iil.pet |
| cad-hub | 8094 | ✓ | postgres | cad.iil.pet |
| 137-hub | 8095 | ✓ | postgres | 137.iil.pet |
| illustration-hub | 8096 | ✓ | postgres | illustration.iil.pet |
| weltenhub | 8081 | ✓ | postgres | welten.iil.pet |
| dev-hub | 8085 | ✓ | postgres | dev.iil.pet |
| trading-hub | 8088 | ✓ | postgres | trading.iil.pet |
| travel-beat | 8089 | — | postgres | travel.iil.pet |
| risk-hub | 8090 | ✓ | postgres | risk.iil.pet |
| pptx-hub | 8020 | — | postgres | pptx.iil.pet |

*odoo-hub: in Planung, noch nicht deployed — wird in separatem ADR adressiert.*

#### Python-Packages (6 Repos)

| Repo | Typ | Konsumenten |
|------|-----|-------------|
| aifw | AI-Framework | bfagent, weltenhub, illustration-hub |
| promptfw | Prompt-Framework | bfagent, weltenhub |
| authoringfw | Authoring-Framework | weltenhub |
| weltenfw | Welten-Framework | weltenhub |
| nl2cad | NL-to-CAD | cad-hub |
| illustration-fw | Illustration-Framework | illustration-hub |

#### Infrastruktur (3 Repos)

| Repo | Zweck |
|------|-------|
| platform | ADRs, Workflows, shared Config, Governance |
| mcp-hub | Alle MCP-Server (Source) |
| infra-deploy | Deployment-Scripts, Nginx-Configs |

### 4.2 Ziel-Architektur

```
┌──────────────────────────────────────────────────────────────────┐
│                     Windsurf / Cascade Agent                      │
│                     (lokal, stdio-Transport)                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌── Tier 1: Always-On (3) ──────────────────────────────────┐   │
│  │  deployment-mcp   Infra + Ops + Health (via SSH)          │   │
│  │  github           Code + Issues + PRs (via GitHub API)    │   │
│  │  platform-context Architecture Rules + ADRs               │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌── Tier 2: Plattform (disabled, bei Bedarf) ───────────────┐   │
│  │  docs-search      RAG ueber ADRs + Docs (pgvector)       │   │
│  │  registry          Modul-Registry (Platform-DB)           │   │
│  │  test-generator   Test-Scaffolding                        │   │
│  │  code-quality     Lint, Naming, HTMX-Patterns             │   │
│  │  llm-mcp          LLM-Gateway (multi-provider)            │   │
│  │  orchestrator     Cross-Repo Orchestrierung               │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌── Tier 3: Repo-spezifisch (per Toggle) ───────────────────┐   │
│  │  bfagent[-db|-mon] Nur bei bfagent-Arbeit                 │   │
│  │  cadhub            Nur bei cad-hub-Arbeit                  │   │
│  │  illustration      Nur bei illustration-hub-Arbeit         │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│                         │ SSH │                                    │
│                         ▼     ▼                                   │
│              ┌────────────────────────┐                           │
│              │  Hetzner 88.198.191.108 │                          │
│              │  13 Django-Apps         │                           │
│              │  Docker Compose         │                           │
│              │  PostgreSQL             │                           │
│              └────────────────────────┘                           │
└──────────────────────────────────────────────────────────────────┘
```

**Schichten-Prinzip:**
1. **Tier 1 (Always-On, 3 Server)**: Plattformweit, immer aktiv, keine DB-Abhaengigkeit
2. **Tier 2 (Plattform, 6 Server)**: Default disabled, bei Bedarf aktivierbar
3. **Tier 3 (Repo-spezifisch, 5 Server)**: Nur bei Arbeit am jeweiligen Repo

**Ressourcen-Budget**: Max 8 MCP-Server gleichzeitig aktiv.
Tier 1 (3) + Tier 2 (0-3) + Tier 3 (0-2) = max 8.

### 4.3 Tool-Routing: Wann welches MCP-Tool?

| Aufgabe | Falsch (SSH-Workaround) | Richtig (strukturiert) |
|---------|------------------------|----------------------|
| Workflow-Logs lesen | `ssh_manage exec curl ...` | `cicd_manage run_logs` |
| Workflow triggern | `ssh_manage exec curl ...` | `cicd_manage dispatch` |
| Workflow-Status | `ssh_manage exec curl ...` | `cicd_manage run_status` |
| GitHub Dateien lesen | `ssh_manage` + git | `github get_file_contents` |
| GitHub Dateien schreiben | `ssh_manage` + git | `github push_files` |
| Issues/PRs verwalten | — | `github *` |
| Docker compose restart | `ssh_manage exec` | `docker_manage compose_restart` |
| Nginx reload | `ssh_manage exec` | `system_manage nginx_reload` |
| DB queries | `ssh_manage exec psql` | `database_manage query` |
| Health aller Apps | `ssh_manage` + Schleife | `system_manage health_dashboard` |

**SSH bleibt noetig fuer** (~30% der bisherigen Nutzung):
- Server-seitige Operationen ohne MCP-Tool (Custom-Scripts, Token-Files)
- Workarounds bei MCP-Tool-Bugs (z.B. workflow_runs branch-Parameter)
- Skripte die nicht ueber GitHub Actions gehen

### 4.4 Gap-Analyse

| Gap | Problem | Loesung | Prio |
|-----|---------|---------|------|
| **G-01: Docs-Search** | 100+ ADRs, kein semantischer Zugriff | `docs-search` (query_agent_mcp) aktivieren | P0 |
| **G-02: Health-Monitor** | 13 Apps, kein Health-Dashboard | `system_manage health_dashboard` (implementiert) | P0 ✅ |
| **G-03: Dependencies** | aifw-Update bricht weltenhub | `dep_manage` Actions: `pip check` + `pip-audit` | P1 |
| **G-04: Log-Aggregation** | Logs nur einzeln per `container_logs` | `system_manage` erweitern: cross-container grep | P1 |
| **G-05: Migration-Safety** | DB-Migrations koennen kollidieren | `system_manage` erweitern: showmigrations cross-app | P2 |
| **G-06: Secret-Rotation** | 13× `.env.prod` ohne Audit | Tier-2 `secret_audit` Tool (nicht Always-On) | P2 |
| **G-07: Performance** | Keine Response-Time-Baselines | In-Memory Ring Buffer in health_dashboard | P2 |
| **G-08: Registry** | Modul-Registry nicht in MCP-Config | `registry` Server aufnehmen (disabled) | P1 |
| **G-09: Library Docs** | AI halluziniert Django 6.0, Tailwind 4 APIs | Context7 MCP evaluieren | P1 |

### 4.5 Verbesserungen bestehender Server

| ID | Server | Verbesserung | Prio |
|----|--------|-------------|------|
| **I-01** | deployment-mcp | Cross-Container Log-Suche | P1 |
| **I-02** | deployment-mcp | `health_dashboard` + `health_check` Actions | P0 ✅ |
| **I-03** | platform-context | Project-Facts fuer alle 23 Repos statt 7 | P1 |
| **I-04** | platform-context | Semantische ADR-Suche | P1 |
| **I-05** | code-quality | ruff statt flake8, HTMX-Update | P2 |
| **I-06** | test-generator | Factory-Boy, Django-Fixtures | P2 |
| **I-07** | llm-mcp | Migration auf PyPI (iil-aifw) | P1 |

### 4.6 health_dashboard Implementierung

Health-Monitoring ist als Action in `system_manage` implementiert (0 neue Tool-Slots).
Nutzt SSH + parallel curl auf dem Hetzner-Server.

```python
# deployment_mcp/consolidated/system_tool.py
@action("health_dashboard", "Health check ALL 13 platform apps", read_only=True)
async def health_dashboard_action(self, host=None):
    from ..tools.system_tools import health_dashboard
    return await health_dashboard(host=host)

@action("health_check", "Health check single platform app", read_only=True)
async def health_check_action(self, app_name, host=None):
    from ..tools.system_tools import health_check
    return await health_check(app_name=app_name, host=host)
```

**Storage fuer history/compare**: In-Memory Ring Buffer (letzte 100 Checks pro App).
Bei Restart frischer State — akzeptabel fuer Tier-1, keine DB-Abhaengigkeit.

### 4.7 dependency_mcp Scope (korrigiert)

| Action | Scope | Aufwand |
|--------|-------|---------|
| `matrix` | Welches Repo nutzt welches Package (Versionen) | 2h |
| `outdated` | Packages die in Repos veraltet sind | 1h |
| `security` | `pip-audit` ueber alle Repos aggregiert | 1h |
| `sync` | requirements.txt Alignment-Vorschlag | 2h |

**Nicht in Scope**: Semantische Breaking-Change-Analyse (AST-Parsing, API-Vergleich).
Das erfordert 2-3 Tage Aufwand und wird in separatem ADR adressiert.

---

## 5. Migration Tracking

| Task | Phase | Status | Datum | Notizen |
|------|-------|--------|-------|---------|
| health_dashboard + health_check | 1 | ✅ Abgeschlossen | 2026-03-06 | system_tool.py |
| docs-search in MCP-Config | 1 | ✅ Abgeschlossen | 2026-03-06 | disabled, Tier 2 |
| registry in MCP-Config | 1 | ✅ Abgeschlossen | 2026-03-06 | disabled, Tier 2 |
| test-generator → Tier 2 | 1 | ⬜ Ausstehend | – | 3 Tool-Slots frei |
| platform-context: 23 Repos | 2 | ⬜ Ausstehend | – | |
| dependency Actions | 2 | ⬜ Ausstehend | – | |
| Context7 Evaluation | 2 | ⬜ Ausstehend | – | G-09 |
| Cross-Container Logs | 2 | ⬜ Ausstehend | – | |
| secret_audit (Tier 2) | 3 | ⬜ Ausstehend | – | Explizite Aktivierung |
| Performance-Baselines | 3 | ⬜ Ausstehend | – | In-Memory Ring Buffer |

---

## 6. Consequences

### 6.1 Good

- Health-Dashboard fuer alle 13 Apps in einem MCP-Call (implementiert)
- Tool-Budget optimal genutzt: 42 aktiv (Tier 1), 76 max, 24 Reserve
- Klare Tier-Zuordnung verhindert MCP-Server-Wildwuchs
- SSH-Nutzung sinkt um ~70% durch strukturiertes Tool-Routing
- Jeder neue Server wird gegen Tool-Budget geprueft

### 6.2 Bad

- Health-Dashboard an deployment-mcp gebunden (Single Point of Dependency)
- In-Memory Health-History geht bei MCP-Restart verloren
- Dependency-Tracking auf pip check/audit begrenzt (kein AST-basiertes Breaking-Change)
- docs-search und registry brauchen lokale PostgreSQL (nicht immer verfuegbar)

### 6.3 Nicht in Scope

- Streamable HTTP Transport (evaluieren wenn SDK stabil)
- Tasks Primitive fuer async long-running ops (Windsurf unterstuetzt es noch nicht)
- MCP Auto-Activation per Workspace-Ordner (Phase 3, separates Konzept)
- Semantische Breaking-Change-Analyse (separates ADR)
- Context7 Integration (Evaluation in Phase 2, ggf. eigenes ADR)

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Tool-Budget erschoepft (>100) | Niedrig | Hoch | Budget-Pruefung vor jedem neuen Server; Actions > Server |
| deployment-mcp Ausfall → kein Health | Mittel | Mittel | Nginx-basierter Fallback-Monitor (cron); MCP-Restart via Windsurf Reload |
| stdio-Transport Latenz bei vielen Servern | Niedrig | Mittel | Max 8 gleichzeitig aktiv; Streamable HTTP als Escape-Hatch |
| docs-search/registry DB nicht verfuegbar | Mittel | Niedrig | Tier-2 (disabled by default); Graceful Degradation |
| secret_audit exponiert .env.prod Metadaten | Niedrig | Hoch | Nur als Tier-2, explizite Aktivierung, User-Confirmation |

---

## 8. Confirmation

1. **Tool-Budget-Check**: Bei jedem neuen MCP-Server wird `python3 -c "import json; ..."` auf mcp_config.json ausgefuehrt — Budget muss unter 100 bleiben
2. **Health-Dashboard Smoke-Test**: Nach jedem deployment-mcp Update: `system_manage health_dashboard` ausfuehren, 13/13 healthy erwarten
3. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualitaet geprueft — Staleness-Schwelle: 6 Monate

---

## 9. Tool-Budget (Windsurf 100-Tool-Limit)

> **Hinweis**: Das 100-Tool-Limit ist ein **Windsurf-Cascade-Constraint** (Stand 2026-03).
> Andere MCP-Clients (Claude Desktop, Cursor) haben eigene Limits.
> Dieses ADR optimiert primaer fuer Windsurf.

```
Tier 1 (Always-On):    42 Tools / 100
  deployment-mcp:      12 (inkl. health_dashboard, health_check)
  github:              26
  platform-context:     4

Tier 2 (disabled):     34 Tools
  docs-search:          5 (query_agent_mcp)
  registry:             5
  test-generator:       3
  code-quality:         1
  llm-mcp:              2
  orchestrator:         3

Tier 3 (disabled):     15 Tools
  bfagent:              5
  bfagent-db:           2
  bfagent-monitoring:   2
  cadhub:               3
  illustration:         3
                       ──
Max bei allen aktiv:   76 / 100 (24 Reserve)
```

**Regel**: Neue Capabilities als Actions in bestehende Tools einbauen
wenn moeglich (0 neue Tool-Slots). Standalone-Server nur wenn
eigene Kategorie zwingend (z.B. docs-search braucht pgvector).

---

## 10. Entscheidungen

| ID | Entscheidung | Begruendung |
|----|-------------|-------------|
| E-01 | Max 8 MCP-Server gleichzeitig aktiv | Ressourcen-Budget, Windsurf-Stabilitaet |
| E-02 | Tier-1-Server: keine schreibende eigene Persistenz. Read-only DB und In-Memory erlaubt | Robustheit; docs-search liest nur pgvector |
| E-03 | Neue Server in mcp-hub entwickeln (ADR-044: FastMCP) | Zentrales Repo, gemeinsame mcp_base |
| E-04 | Health-Monitoring als Actions in system_manage (nicht eigener Server) | 0 neue Tool-Slots; SSH ist architektonisch korrekt weil MCP lokal laeuft (stdio) |
| E-05 | filesystem-MCP dauerhaft entfernt | Redundant mit Windsurf built-in Tools |
| E-06 | postgres-MCP-Server dauerhaft entfernt | Redundant mit deployment-mcp database_manage |
| E-07 | GITHUB_TOKEN nur in Secrets-File, nie in JSON | Security Best Practice |
| E-08 | test-generator von Tier 1 nach Tier 2 | 3 Tool-Slots fuer seltene Nutzung; bei Bedarf aktivierbar |
| E-09 | secret_audit nur als Tier-2-Tool, nicht Always-On | Security: .env.prod Metadaten nicht im Always-On-Scope |
| E-10 | stdio-Transport fuer alle Server (kein HTTP) | Streamable HTTP noch nicht stabil; Evaluation in Phase 3 |
| E-11 | dependency_mcp: kein semantisches Breaking-Change (nur pip check/audit) | 4h-Scope realistisch; AST-Analyse = separates ADR |

---

## 11. Metriken

| Metrik | Ist | Ziel (KW 15) |
|--------|-----|-------------|
| MCP-Server total | 14 | 14 (konsolidiert) |
| Tier-1-Server (Always-On) | 4 | 3 (test-gen → Tier 2) |
| Tool-Slots aktiv | 45 | 42 |
| Repo-Coverage (Project-Facts) | 7/23 | 23/23 |
| Health-Check Coverage | 0/13 | 13/13 |
| ADR-Suche | manuell | semantisch via RAG |
| Dependency-Sichtbarkeit | keine | pip check + pip-audit |
| SSH-Anteil an Tool-Nutzung | ~90% | ~30% |

---

## 12. More Information

- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- ADR-044: MCP-Hub Architecture Consolidation (FastMCP-Standard)
- ADR-054: MCP-Architektur Grundlagen
- ADR-059: Drift-Detector
- ADR-062: Central Billing Service (billing-hub)
- ADR-069: Web Intelligence MCP
- ADR-083: collectstatic Docker Pattern
- ADR-100: iil-testkit Shared Package

---

## 13. Changelog

| Datum | Autor | Aenderung |
|-------|-------|-----------|
| 2026-03-06 | Cascade + AD | Initial: Konzeptpapier als ADR |
| 2026-03-06 | Cascade | v2: MADR 4.0 Migration, Review-Findings K-01..M-06, SSH-vs-MCP Routing, Tool-Budget Windsurf-Constraint, test-generator → Tier 2, E-08..E-11 |
