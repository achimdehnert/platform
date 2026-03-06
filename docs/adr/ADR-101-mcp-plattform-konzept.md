# ADR-101: MCP-Plattformkonzept — Optimale Nutzung von Model Context Protocol

- **Status**: PROPOSED
- **Datum**: 2026-03-06
- **Autor**: Cascade + AD
- **Scope**: Alle 23 GitHub-Repos der BF Platform

---

## 1. Kontext

Die BF Platform umfasst 23 aktive GitHub-Repos, die auf einem gemeinsamen
Hetzner-Server (88.198.191.108) deployed werden. Windsurf/Cascade nutzt MCP-Server
als Brücke zwischen KI-Agent und Infrastruktur. Aktuell existieren 12 MCP-Server
(4 aktiv, 8 disabled). Die Frage ist: **Welche MCP-Server fehlen, welche sollten
konsolidiert werden, und wie sieht die optimale MCP-Architektur aus?**

---

## 2. Repo-Inventar

### 2.1 Django-Apps (14 Repos, deployed auf Hetzner)

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
| odoo-hub | — | — | — | — |

### 2.2 Python-Packages (6 Repos, PyPI/lokal)

| Repo | Typ | Konsumenten |
|------|-----|-------------|
| aifw | AI-Framework | bfagent, weltenhub, illustration-hub |
| promptfw | Prompt-Framework | bfagent, weltenhub |
| authoringfw | Authoring-Framework | weltenhub |
| weltenfw | Welten-Framework | weltenhub |
| nl2cad | NL-to-CAD | cad-hub |
| illustration-fw | Illustration-Framework | illustration-hub |

### 2.3 Infrastruktur (3 Repos)

| Repo | Zweck |
|------|-------|
| platform | ADRs, Workflows, shared Config, Governance |
| mcp-hub | Alle MCP-Server (Source) |
| infra-deploy | Deployment-Scripts, Nginx-Configs |

---

## 3. MCP-Server Ist-Zustand

### 3.1 Aktive Server (4)

| Server | Source | Scope | Tools |
|--------|--------|-------|-------|
| **deployment-mcp** | mcp-hub | Alle Repos | SSH, Docker, DB, Git, CI/CD, Env, Server, Firewall, System, Network, Pip |
| **github** | @modelcontextprotocol | Alle Repos | Issues, PRs, Repos, Files, Code Search |
| **platform-context** | mcp-hub | Alle Repos | Architecture Rules, Banned Patterns, Project Facts |
| **test-generator** | bfagent/packages | Alle Repos | Test-Generierung aus Code-Analyse |

### 3.2 Disabled Server (8, per Toggle aktivierbar)

| Server | Source | Scope | Zweck |
|--------|--------|-------|-------|
| bfagent | bfagent/packages | bfagent | Initiative-Management, Task-Delegation |
| bfagent-db | bfagent/packages | bfagent | Direkte DB-Queries |
| bfagent-monitoring | bfagent/packages | bfagent | Container-/Service-Monitoring |
| cadhub | platform/packages | cad-hub | CAD-spezifische Operationen |
| code-quality | bfagent/packages | Alle Repos | Lint, Naming, HTMX-Patterns |
| illustration | bfagent/packages | illustration-hub/fw | ComfyUI, Style-Management |
| llm-mcp | mcp-hub | Alle Repos | LLM-Gateway (multi-provider) |
| orchestrator | mcp-hub | Alle Repos | Cross-Repo Orchestrierung |

### 3.3 Verfuegbare aber nicht konfigurierte Server (in mcp-hub)

| Server | Source | Status | Zweck |
|--------|--------|--------|-------|
| query_agent_mcp | mcp-hub | Lauffaehig | RAG ueber Platform-Docs (pgvector) |
| registry_mcp | mcp-hub | Lauffaehig | Modul-Registry Abfragen |
| web_intelligence_mcp | mcp-hub | Prototyp | Web-Fetch, Extract, Wikipedia |
| travel_mcp | mcp-hub | Prototyp | Multi-Provider Travel Search |
| ifc_mcp | mcp-hub | Prototyp | IFC-Datei-Analyse (Bauwesen) |

---

## 4. Gap-Analyse

### 4.1 Fehlende plattformweite MCP-Server

| Gap | Problem | Loesung | Prioritaet |
|-----|---------|---------|------------|
| **G-01: Docs-Search** | 23 Repos, 100+ ADRs — kein semantischer Zugriff | `query_agent_mcp` aktivieren + Index erweitern | P0 |
| **G-02: Health-Monitor** | 14 deployed Apps — kein zentrales Health-Dashboard via MCP | Neuer `health_mcp`: alle /healthz/ Endpoints, Container-Stats, Uptime | P0 |
| **G-03: Cross-Repo Dependencies** | Package-Updates in aifw brechen weltenhub — keine Sichtbarkeit | Neuer `dependency_mcp`: pip freeze diff, breaking-change detection | P1 |
| **G-04: Log-Aggregation** | Logs nur per `container_logs` einzeln — keine Cross-App-Suche | Neuer `log_mcp` oder deployment-mcp erweitern: grep ueber alle Container-Logs | P1 |
| **G-05: Migration-Safety** | DB-Migrations koennen sich zwischen Repos beissen (shared DB) | Neuer `migration_mcp`: showmigrations fuer alle Apps, Konflikt-Check | P2 |
| **G-06: Secret-Rotation** | 14 .env.prod Dateien — kein Ueberblick ueber Alter/Konsistenz | deployment-mcp erweitern: secret_audit Action | P2 |
| **G-07: Performance-Baseline** | Keine Response-Time-Baselines pro App | `health_mcp` erweitern: response_time Tracking, Anomalie-Alarm | P2 |
| **G-08: Registry-Sync** | Modul-Registry existiert aber nicht in MCP-Config | `registry_mcp` aktivieren | P1 |

### 4.2 Verbesserungen bestehender Server

| ID | Server | Verbesserung | Prioritaet |
|----|--------|-------------|------------|
| **I-01** | deployment-mcp | `compose_logs` Cross-App: alle Container-Logs mit Suchbegriff | P1 |
| **I-02** | deployment-mcp | `health_dashboard` Action: alle 14 /healthz/ in einem Call | P0 |
| **I-03** | platform-context | Project-Facts fuer alle 23 Repos statt nur 7 | P1 |
| **I-04** | platform-context | ADR-Suche: semantisch ueber alle ADRs | P1 |
| **I-05** | code-quality | HTMX-Pattern-Check aktualisieren, ruff statt flake8 | P2 |
| **I-06** | test-generator | Django-spezifische Fixtures, Factory-Boy Support | P2 |
| **I-07** | llm-mcp | Migration auf PyPI-Packages (iil-aifw etc.) | P1 |

---

## 5. Ziel-Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                    Windsurf / Cascade Agent                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌── Always-On (4) ──────────────────────────────────────────┐  │
│  │  deployment-mcp    Infrastructure + Ops fuer alle Repos   │  │
│  │  github            Code + Issues + PRs fuer alle Repos    │  │
│  │  platform-context  Architecture Rules + ADRs              │  │
│  │  test-generator    Test-Scaffolding fuer alle Repos       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌── Plattform-Erweiterungen (neu) ─────────────────────────┐  │
│  │  health-mcp        Zentrales Health-Dashboard (P0)        │  │
│  │  docs-search-mcp   RAG ueber ADRs + Docs (P0)            │  │
│  │  registry-mcp      Modul-Registry Queries (P1)            │  │
│  │  dependency-mcp    Cross-Repo Dependency-Checks (P1)      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌── Repo-spezifisch (per Toggle) ──────────────────────────┐  │
│  │  bfagent[-db|-mon] Nur bei bfagent-Arbeit                │  │
│  │  cadhub            Nur bei cad-hub-Arbeit                 │  │
│  │  illustration      Nur bei illustration-hub-Arbeit        │  │
│  │  llm-mcp           Bei LLM-Provider-Arbeit               │  │
│  │  orchestrator      Bei Cross-Repo-Orchestrierung          │  │
│  │  code-quality      Bei Quality-Reviews                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.1 Schichten-Prinzip

1. **Always-On (Tier 1)**: Plattformweite Server, immer aktiv,
   geringe Ressourcen. Max 6 Server.
2. **Plattform-Erweiterung (Tier 2)**: Spezialserver fuer plattformweite
   Aufgaben, default disabled, bei Bedarf aktivierbar.
3. **Repo-spezifisch (Tier 3)**: Nur aktivieren wenn am jeweiligen
   Repo gearbeitet wird. Max 2-3 gleichzeitig.

### 5.2 Ressourcen-Budget

- **Ziel**: Max 8 MCP-Server gleichzeitig aktiv
- **Grund**: Jeder Server = 1 Prozess + MCP-Handshake + Tool-Registrierung
- **Regel**: Tier 1 (4-6) + Tier 2 (0-2) + Tier 3 (0-2) = max 8

---

## 6. Weiterentwicklungs-Roadmap

### Phase 1: Quick Wins (KW 11, 2026)

| ID | Task | Aufwand | Impact |
|----|------|---------|--------|
| R-01 | `health-mcp` bauen: alle 14 /healthz/ Endpoints + Response-Times | 2h | Hoch |
| R-02 | `query_agent_mcp` in MCP-Config aufnehmen + aktivieren | 30min | Hoch |
| R-03 | `registry_mcp` in MCP-Config aufnehmen | 30min | Mittel |
| R-04 | deployment-mcp: `health_dashboard` Action hinzufuegen | 1h | Hoch |
| R-05 | platform-context: Project-Facts fuer alle 23 Repos | 2h | Mittel |

### Phase 2: Cross-Repo Intelligence (KW 12-13, 2026)

| ID | Task | Aufwand | Impact |
|----|------|---------|--------|
| R-06 | `dependency_mcp` bauen: pip freeze + breaking-change detection | 4h | Hoch |
| R-07 | deployment-mcp: Cross-Container Log-Suche | 2h | Mittel |
| R-08 | llm-mcp: Migration auf PyPI-Packages | 2h | Mittel |
| R-09 | platform-context: Semantische ADR-Suche | 3h | Hoch |
| R-10 | code-quality: ruff-Integration, HTMX-Update | 2h | Mittel |

### Phase 3: Automatisierung (KW 14-15, 2026)

| ID | Task | Aufwand | Impact |
|----|------|---------|--------|
| R-11 | `migration_mcp`: Cross-App Migration-Konflikt-Check | 3h | Mittel |
| R-12 | deployment-mcp: `secret_audit` — Alter, Konsistenz aller .env.prod | 2h | Mittel |
| R-13 | health-mcp: Performance-Baselines + Anomalie-Detection | 4h | Hoch |
| R-14 | Auto-Activation: MCP-Server per Workspace-Ordner automatisch togglen | 3h | Hoch |
| R-15 | MCP-Dashboard: Web-UI in dev-hub fuer Server-Status + Metriken | 4h | Mittel |

---

## 7. health-mcp Spezifikation (P0, R-01)

Neuer plattformweiter MCP-Server fuer zentrales Health-Monitoring.

### Tools

| Tool | Action | Beschreibung |
|------|--------|-------------|
| `health_manage` | `dashboard` | Alle 14 Apps: Status, Response-Time, Container-State |
| `health_manage` | `check` | Einzelne App pruefen (name oder URL) |
| `health_manage` | `history` | Letzten N Health-Checks einer App |
| `health_manage` | `compare` | Response-Times vergleichen (heute vs. gestern) |
| `health_manage` | `alerts` | Apps mit Status != 200 oder Response > 2s |

### App-Registry

```python
APPS = {
    "coach-hub":        {"port": 8007, "domain": "kiohnerisiko.de"},
    "bfagent":          {"port": 8091, "domain": "bfagent.iil.pet"},
    "billing-hub":      {"port": 8092, "domain": "billing.iil.pet"},
    "wedding-hub":      {"port": 8093, "domain": "wedding.iil.pet"},
    "cad-hub":          {"port": 8094, "domain": "cad.iil.pet"},
    "137-hub":          {"port": 8095, "domain": "137.iil.pet"},
    "illustration-hub": {"port": 8096, "domain": "illustration.iil.pet"},
    "weltenhub":        {"port": 8081, "domain": "welten.iil.pet"},
    "dev-hub":          {"port": 8085, "domain": "dev.iil.pet"},
    "trading-hub":      {"port": 8088, "domain": "trading.iil.pet"},
    "travel-beat":      {"port": 8089, "domain": "travel.iil.pet"},
    "risk-hub":         {"port": 8090, "domain": "risk.iil.pet"},
    "pptx-hub":         {"port": 8020, "domain": "pptx.iil.pet"},
}
```

---

## 8. dependency-mcp Spezifikation (P1, R-06)

Neuer MCP-Server fuer Cross-Repo Dependency-Management.

### Tools

| Tool | Action | Beschreibung |
|------|--------|-------------|
| `dep_manage` | `matrix` | Welches Repo nutzt welches Package (mit Versionen) |
| `dep_manage` | `outdated` | Packages die in manchen Repos veraltet sind |
| `dep_manage` | `breaking` | Breaking-Change-Check: Was bricht wenn aifw v0.6 released wird? |
| `dep_manage` | `security` | pip-audit ueber alle Repos aggregiert |
| `dep_manage` | `sync` | Vorschlag: requirements.txt Alignment |

### Datenquellen

- `requirements.txt` / `pyproject.toml` aller 23 Repos
- PyPI API fuer aktuelle Versionen
- pip-audit fuer Security-Checks

---

## 9. MCP-Config Ziel-Zustand

```json
{
  "mcpServers": {
    "deployment-mcp":  { "disabled": false, "comment": "Tier 1 — Infra" },
    "github":          { "disabled": false, "comment": "Tier 1 — Code" },
    "platform-context":{ "disabled": false, "comment": "Tier 1 — Rules" },
    "test-generator":  { "disabled": false, "comment": "Tier 1 — Tests" },
    "health-mcp":      { "disabled": false, "comment": "Tier 1 — Monitoring (NEU)" },
    "docs-search-mcp": { "disabled": false, "comment": "Tier 1 — RAG Docs (NEU)" },

    "registry-mcp":    { "disabled": true, "comment": "Tier 2 — bei Bedarf" },
    "dependency-mcp":  { "disabled": true, "comment": "Tier 2 — bei Bedarf" },
    "code-quality":    { "disabled": true, "comment": "Tier 2 — bei Reviews" },
    "llm-mcp":         { "disabled": true, "comment": "Tier 2 — bei LLM-Arbeit" },
    "orchestrator":    { "disabled": true, "comment": "Tier 2 — bei Orchestrierung" },

    "bfagent":         { "disabled": true, "comment": "Tier 3 — repo-spezifisch" },
    "bfagent-db":      { "disabled": true, "comment": "Tier 3 — repo-spezifisch" },
    "bfagent-monitoring":{ "disabled": true, "comment": "Tier 3 — repo-spezifisch" },
    "cadhub":          { "disabled": true, "comment": "Tier 3 — repo-spezifisch" },
    "illustration":    { "disabled": true, "comment": "Tier 3 — repo-spezifisch" }
  }
}
```

**Ergebnis**: 16 Server total, 6 Always-On, 5 Tier-2, 5 Tier-3.

---

## 10. Entscheidungen

| ID | Entscheidung | Begruendung |
|----|-------------|-------------|
| E-01 | Max 8 MCP-Server gleichzeitig aktiv | Ressourcen-Budget, Windsurf-Stabilitaet |
| E-02 | Tier-1-Server muessen stateless sein | Kein lokales PostgreSQL erforderlich |
| E-03 | Neue Server in mcp-hub entwickeln | Zentrales Repo, gemeinsame mcp_base |
| E-04 | health-mcp nutzt deployment-mcp SSH intern | Kein eigener SSH-Zugang noetig |
| E-05 | filesystem-MCP dauerhaft entfernt | Redundant mit Windsurf built-in Tools |
| E-06 | postgres-MCP-Server dauerhaft entfernt | Redundant mit deployment-mcp database_manage |
| E-07 | GITHUB_TOKEN nur in Secrets-File, nie in JSON | Security Best Practice |

---

## 11. Metriken

| Metrik | Ist | Ziel (KW 15) |
|--------|-----|-------------|
| MCP-Server total | 12 | 16 |
| Always-On Server | 4 | 6 |
| Repo-Coverage (Project-Facts) | 7/23 | 23/23 |
| Health-Check Coverage | 0/14 | 14/14 |
| ADR-Suche | manuell | semantisch via RAG |
| Dependency-Sichtbarkeit | keine | vollstaendig |
| Secret-Audit | manuell | automatisiert |

---

## 12. Referenzen

- ADR-054: MCP-Architektur Grundlagen
- ADR-062: Central Billing Service (billing-hub)
- ADR-069: Web Intelligence MCP
- ADR-083: collectstatic Docker Pattern
- ADR-100: iil-testkit Shared Package
