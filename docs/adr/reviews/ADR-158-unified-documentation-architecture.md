---
status: proposed
date: 2026-04-03
decision-makers: [Achim Dehnert]
consulted: [Cascade (Principal IT-Architekt)]
informed: []
supersedes: []
amends: ["ADR-046-docs-hygiene.md"]
related:
  - ADR-020-documentation-strategy.md
  - ADR-046-docs-hygiene.md
  - ADR-047-sphinx-documentation-hub.md
  - ADR-143-knowledge-hub-outline-integration.md
  - ADR-144-doc-hub-paperless-ngx.md
  - ADR-154-autonomous-coding-optimization.md
  - ADR-156-reliable-deployment-pipeline.md
implementation_status: proposed
implementation_evidence: []
---

# ADR-158: Unified Documentation Architecture — Single Source, Multi-Audience, AI-Generated

<!-- Drift-Detector-Felder (ADR-059)
staleness_months: 6
drift_check_paths:
  - .windsurf/workflows/session-docu.md
  - platform/scripts/docu-audit.sh
  - packages/docs-agent/
supersedes_check: ADR-020 (deferred), ADR-046 (amends)
-->

## Context and Problem Statement

### Kernproblem

Die Platform-Dokumentation ist über **6 unverbundene Systeme** verstreut. Keines davon liefert eine vollständige Sicht für eine Zielgruppe.

| System | URL / Ort | Inhalt | Zielgruppe | Problem |
|--------|-----------|--------|------------|---------|
| **GitHub** (per-repo) | `docs/`, README, CORE_CONTEXT | ADRs, Code-Docs, Guides | Entwickler | Verstreut über 18+ Repos, kein Gesamtindex |
| **Outline** | knowledge.iil.pet | Runbooks, Konzepte, Lessons Learned | Architekten, Betreiber | Kein Auto-Sync mit Code, manuelle Pflege |
| **dev-hub TechDocs** | devhub.iil.pet | 389 Seiten aus 10 Repos (Celery Beat) | Entwickler | Nur docs/-Ordner, keine README/CORE_CONTEXT |
| **dev-hub ADR Lifecycle** | devhub.iil.pet/adr/ | ADR State Machine, Drift Detection | Architekten | Separate DB, nicht mit GitHub-ADRs synchron |
| **Paperless (doc-hub)** | docs.iil.pet | Rechnungen, Verträge, Belege | Betreiber, Finance | Kein Bezug zu Tech-Doku |
| **platform-context MCP** | Knowledge Graph | Architektur-Regeln, Banned Patterns, Project Facts | Agents (Cascade) | Nur maschinenlesbar, kein Human-UI |
| **pgvector Memory** | orchestrator MCP | Session-Memories, Error-Patterns | Agents (Cascade) | Nicht für Menschen zugänglich |
| **Sphinx** (deferred) | platform/packages/docs-agent/ | Docstring-Coverage, AST-Analyse | — | Nicht deployed, nicht in Pipeline |

### Auswirkungen

1. **Kein Single Entry Point**: Ein Entwickler muss 4 Systeme durchsuchen um ein Feature zu verstehen
2. **Audience-Blindheit**: Betreiber finden ADRs in GitHub nicht, Entwickler finden Runbooks in Outline nicht
3. **Stale-Drift**: GitHub-ADRs, Outline-Konzepte und dev-hub ADR Lifecycle divergieren
4. **Keine Reference-Docs**: Models, API-Endpoints, Config-Variablen sind nur im Code dokumentiert
5. **Kein Dokumentations-Workflow**: Es gibt kein Äquivalent zu `/ship` für Dokumentation
6. **Docs-Agent nicht integriert**: `packages/docs-agent/` existiert, wird aber nicht routinemäßig genutzt

### Bestehende Bausteine (was funktioniert)

| Baustein | Status | Stärke |
|----------|--------|--------|
| dev-hub TechDocs Sync | ✅ Deployed | GitHub → DB, Celery Beat, 389 Seiten |
| dev-hub ADR Lifecycle | ✅ Deployed | State Machine, hourly Sync |
| dev-hub Health Dashboard | ✅ Deployed | 9 Endpoints, 5-min Polling |
| dev-hub Software Catalog | ✅ Deployed | 16 Components, 6 Domains |
| Outline Wiki | ✅ Deployed | Runbooks, Konzepte, fulltext Search |
| Paperless DMS | ✅ Deployed | OCR, Auto-Tagging, MCP-Integration |
| docs-agent (AST Scanner) | ⚠️ Existiert | Docstring-Coverage, DIATAXIS-Classifier |
| platform-context MCP | ✅ Deployed | Rules, Facts, Violations |
| pgvector Memory | ✅ Deployed | Session-Context, Error-Patterns |
| DIATAXIS-Struktur | ⚠️ Definiert | In ADR-046, nicht enforced |

---

## Decision Drivers

1. **Single Entry Point**: Eine URL pro Zielgruppe — nicht 6 Systeme durchsuchen
2. **Always Current**: Dokumentation muss automatisch aktuell sein (max. 24h Drift)
3. **Audience-Routing**: User, Entwickler, Architekten, Betreiber bekommen relevante Inhalte
4. **AI-generierbar**: Reference-Docs (Models, API, Config) werden aus Code/DB erzeugt
5. **Bestehende Infrastruktur nutzen**: dev-hub, Outline, docs-agent — kein neues System
6. **Workflow-integriert**: `/session-docu` analog zu `/ship` und `/session-start`
7. **Messbar**: Dokumentations-Coverage als Quality Gate

---

## Decision

### Architektur-Übersicht: Hub-and-Spoke Documentation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOCUMENTATION ARCHITECTURE                            │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    dev-hub (devhub.iil.pet)                          │   │
│  │                    = UNIFIED DOCUMENTATION PORTAL                     │   │
│  │                                                                      │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────────┐    │   │
│  │  │  TechDocs  │ │    ADR     │ │  Reference │ │   Audience    │    │   │
│  │  │   (sync)   │ │ Lifecycle  │ │   (gen.)   │ │   Navigator   │    │   │
│  │  │  389 pages │ │  hourly    │ │  AI-gen.   │ │   NEW         │    │   │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └──────┬────────┘    │   │
│  │        │              │              │               │              │   │
│  └────────┼──────────────┼──────────────┼───────────────┼──────────────┘   │
│           │              │              │               │                   │
│  ┌────────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐ ┌─────▼──────────────┐   │
│  │  GitHub Repos │ │  GitHub  │ │  Code +    │ │  Audience Config   │   │
│  │  docs/ sync   │ │  ADRs    │ │  DB + MCP  │ │  (audience.yaml)   │   │
│  │  (18 Repos)   │ │  (*.md)  │ │  introspect│ │                    │   │
│  └───────────────┘ └──────────┘ └────────────┘ └────────────────────┘   │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐     │
│  │  Outline Wiki    │  │  Paperless DMS   │  │  platform-context    │     │
│  │  (knowledge)     │  │  (documents)     │  │  MCP (rules)         │     │
│  │  Runbooks,       │  │  Rechnungen,     │  │  ADR-Compliance,     │     │
│  │  Konzepte,       │  │  Verträge        │  │  Banned Patterns,    │     │
│  │  Lessons         │  │                  │  │  Project Facts       │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘     │
│           │                    │                        │                   │
│           └────────────────────┴────────────────────────┘                   │
│                    Cross-linked via dev-hub Audience Navigator              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Prinzip: Source-of-Truth Matrix

Jedes Informationsstück hat **genau eine kanonische Quelle**. Andere Systeme spiegeln oder verlinken.

| Informationstyp | Canonical Source | Sync-Ziel(e) | Sync-Mechanismus |
|-----------------|-----------------|---------------|------------------|
| **ADRs** | GitHub `docs/adr/*.md` | dev-hub ADR Lifecycle, Outline | Celery hourly + `/session-docu` |
| **Code-Docs** (README, Guides) | GitHub `docs/` | dev-hub TechDocs | Celery daily + `/session-docu` |
| **CORE_CONTEXT / AGENT_HANDOVER** | GitHub (per-repo) | dev-hub TechDocs | Celery daily |
| **Reference-Docs** (Models, API, Config) | **AI-generiert** aus Code + DB | GitHub `docs/reference/` → dev-hub | `/session-docu` generate |
| **Runbooks** | Outline | dev-hub (Link) | Audience Navigator links |
| **Konzepte** | Outline | dev-hub (Link) | Audience Navigator links |
| **Lessons Learned** | Outline / pgvector | dev-hub (Link) | Audience Navigator links |
| **Architektur-Regeln** | platform-context MCP | dev-hub (rendered) | `/session-docu` export |
| **Geschäftsdokumente** | Paperless (doc-hub) | — | Eigenständig |
| **Project Facts** | `repos.json` (Knowledge Graph) | dev-hub Catalog | Celery daily |
| **Error-Patterns** | pgvector Memory | Outline (als Lessons) | `/session-ende` |

### D-1: Audience Navigator (Neues Feature in dev-hub)

Zentrale Navigationsseite in dev-hub mit Audience-Routing:

| Audience | Einstieg | Sieht |
|----------|----------|-------|
| **User / Stakeholder** | `/docs/user/` | Product-Beschreibungen, Feature-Guides, FAQ |
| **Entwickler** | `/docs/developer/` | CORE_CONTEXT, API-Reference, Models, Getting Started |
| **Architekt** | `/docs/architect/` | ADRs, Konzepte (→ Outline), Architektur-Diagramme |
| **Betreiber / DevOps** | `/docs/operator/` | Runbooks (→ Outline), Health Dashboard, Deploy-Guides |

**Konfiguration via `audience.yaml`** pro Repo:

```yaml
# platform/docs/audience.yaml
audiences:
  user:
    title: "Für Anwender"
    icon: "users"
    sources:
      - type: github
        paths: ["docs/tutorials/", "README.md"]
      - type: outline
        query: "User Guide"

  developer:
    title: "Für Entwickler"
    icon: "code"
    sources:
      - type: github
        paths: ["CORE_CONTEXT.md", "docs/guides/", "docs/reference/"]
      - type: techdocs
        site_slug: "platform"

  architect:
    title: "Für Architekten"
    icon: "building"
    sources:
      - type: github
        paths: ["docs/adr/"]
      - type: outline
        collections: ["Konzepte", "ADR"]
      - type: techdocs
        site_slug: "platform"
        filter: "explanation/"

  operator:
    title: "Für Betreiber"
    icon: "server"
    sources:
      - type: outline
        collections: ["Runbooks", "Lessons Learned"]
      - type: devhub
        apps: ["health", "operations"]
      - type: github
        paths: ["docs/guides/deployment.md", "AGENT_HANDOVER.md"]
```

### D-2: Reference-Doc Generator (docs-agent Integration)

AI-generierte Reference-Docs für jedes Repo, basierend auf Code-Introspection:

| Doc-Typ | Quelle | Generator | Output |
|---------|--------|-----------|--------|
| `models.md` | Django Models (AST + DB Schema) | docs-agent + MCP | `docs/reference/models.md` |
| `api.md` | URL-Patterns (urlpatterns) | docs-agent | `docs/reference/api.md` |
| `config.md` | settings.py + .env.example | docs-agent | `docs/reference/config.md` |
| `lookups.md` | Lookup-Tabellen (DB) | database_manage MCP | `docs/reference/lookups.md` |
| `architecture.md` | platform-context Rules | platform-context MCP | `docs/reference/architecture.md` |

**Generierung erfolgt via `/session-docu` Workflow**, nicht automatisch im CI.

### D-3: Documentation Health Score

Messbare Metriken pro Repo, aggregiert in dev-hub:

| Metrik | Gewicht | Quelle | Ziel |
|--------|---------|--------|------|
| README.md vorhanden + >500 Zeichen | 10% | GitHub | 100% |
| CORE_CONTEXT.md vorhanden | 10% | GitHub | 100% |
| docs/adr/ mit ≥1 ADR | 10% | GitHub | 100% |
| DIATAXIS-Struktur (tutorials/, guides/, reference/) | 15% | docs-agent audit | ≥3 Quadranten |
| Docstring-Coverage | 20% | docs-agent AST Scanner | ≥60% |
| Reference-Docs aktuell (<7 Tage) | 15% | GitHub commit date | 100% |
| Audience Navigator konfiguriert | 10% | audience.yaml | 100% |
| Keine Banned Files in docs/ | 10% | docs-agent / ADR-046 | 0 Violations |

**Health Score = gewichteter Durchschnitt → 0-100%**

Wird in dev-hub Health Dashboard angezeigt (analog zu Service Health).

### D-4: `/session-docu` Workflow

Analog zu `/ship` (Deploy) und `/session-start` (Kontext), aber für Dokumentation:

```
/session-docu [repo|all] [--generate] [--audit] [--sync]
```

**Phasen:**

| Phase | Aktion | Tool |
|-------|--------|------|
| 1. Audit | Docstring-Coverage + DIATAXIS-Compliance prüfen | docs-agent audit |
| 2. Generate | Reference-Docs erzeugen (models, api, config) | docs-agent generate + MCP |
| 3. Sync | Outline ↔ GitHub ADR-Sync prüfen | outline-knowledge MCP + GitHub MCP |
| 4. Commit | Generierte Docs committen | git add + commit |
| 5. Report | Documentation Health Score berechnen + anzeigen | dev-hub API / MCP |

### D-5: Cross-System Sync Rules

| Sync-Richtung | Trigger | Mechanismus | Konflikt-Resolution |
|---------------|---------|-------------|---------------------|
| GitHub ADRs → dev-hub | Celery hourly | `adr_lifecycle.sync_all_adr_repos` | GitHub wins |
| GitHub docs/ → dev-hub TechDocs | Celery daily | `techdocs.sync_all_docs` | GitHub wins |
| Outline Runbooks → dev-hub | `/session-docu` | Link-Sync (kein Inhalt kopieren) | Outline wins |
| Reference-Docs → GitHub | `/session-docu --generate` | AI-generiert, Git commit | Generated wins (overwrite) |
| Error-Patterns → Outline Lessons | `/session-ende` | pgvector → Outline export | pgvector wins |
| AGENT_HANDOVER.md → dev-hub | Celery daily | TechDocs sync | GitHub wins |

**Grundregel: Jede Information hat EINE kanonische Quelle. Sync ist unidirektional.**

---

## Implementation Plan

### Phase 1: Foundation (2h)

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| `/session-docu` Workflow erstellen | 1h | `.windsurf/workflows/session-docu.md` |
| `audience.yaml` Schema + Beispiel für platform | 0.5h | `platform/docs/audience.yaml` |
| `docu-audit.sh` Script (Coverage + DIATAXIS) | 0.5h | `platform/scripts/docu-audit.sh` |

### Phase 2: Reference-Doc Generation (4h)

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| docs-agent CLI um `generate reference` erweitern | 2h | `packages/docs-agent/` |
| MCP-basierte Model-/API-/Config-Introspection | 1.5h | Generator-Module |
| Pilot: Reference-Docs für risk-hub generieren | 0.5h | `risk-hub/docs/reference/*.md` |

### Phase 3: Audience Navigator in dev-hub (4h)

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| `portal` App: AudienceView + Templates | 2h | `apps/portal/` |
| audience.yaml Parser + Cross-System Links | 1h | Service-Layer |
| TechDocs Sync: README + CORE_CONTEXT einbeziehen | 1h | `techdocs/services.py` erweitern |

### Phase 4: Documentation Health Score (3h)

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| DocHealth Model + Service in dev-hub | 1.5h | `apps/techdocs/doc_health.py` |
| Health Dashboard Integration (Kachel) | 1h | Template + View |
| Celery Beat: Weekly Doc-Health-Scan | 0.5h | Task |

### Phase 5: Outline Bi-Sync (2h)

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| ADR → Outline Sync (neue ADRs als Outline-Docs) | 1h | `adr_lifecycle/services.py` |
| Outline Runbook-Links in Audience Navigator | 1h | `portal/services.py` |

**Gesamt: ~15h über 3-4 Sessions**

---

## Considered Options

### Option A: Neues Portal bauen (z.B. Docusaurus, MkDocs)

- ❌ **Noch ein System** — verschärft das Problem statt es zu lösen
- ❌ Kein Django-Stack, keine Tenant-Isolation
- ❌ Keine Integration mit dev-hub Catalog/Health/ADR

### Option B: Alles nach Outline migrieren

- ❌ Outline hat keinen Code-Sync, keine Auto-Generation
- ❌ ADRs müssten manuell gepflegt werden
- ❌ Kein Docstring-Coverage, kein Health Score

### Option C: dev-hub als Portal erweitern (GEWÄHLT)

- ✅ Bestehendes System, Django/HTMX Stack
- ✅ TechDocs Sync bereits funktional (389 Seiten)
- ✅ ADR Lifecycle bereits deployed
- ✅ Software Catalog + Health bereits da
- ✅ Nur **Audience Navigator + Reference Generator** fehlen

---

## Consequences

### Positiv

- **Ein Einstiegspunkt** (devhub.iil.pet) für alle Dokumentation
- **Audience-Routing**: Jede Rolle findet sofort relevante Inhalte
- **AI-generierte Reference-Docs**: Immer aktuell, kein manueller Aufwand
- **Messbarer Quality Gate**: Documentation Health Score als Governance-Metrik
- **Kein neues System**: Erweitert dev-hub, nutzt Outline + docs-agent
- **Workflow-gesteuert**: `/session-docu` macht Doku-Arbeit reproduzierbar

### Negativ

- **dev-hub wird zum SPOF**: Wenn dev-hub down ist, fehlt der Portal-Zugang (Mitigation: GitHub-Docs direkt erreichbar)
- **Audience Navigator braucht Pflege**: `audience.yaml` pro Repo muss aktuell sein (Mitigation: `/session-docu` prüft)
- **Reference-Doc Qualität**: AI-generiert = potenziell ungenau (Mitigation: Dry-Run Default, Review in `/session-docu`)
- **Outline bleibt separates System**: Kein Full-Merge möglich (Mitigation: Deep-Links statt Kopieren)

### Risiko-Mitigation

| Risiko | Mitigation |
|--------|------------|
| dev-hub Downtime | GitHub-Docs direkt erreichbar, Outline eigenständig |
| AI generiert falsche Docs | Dry-Run Default, manuelle Review-Phase |
| audience.yaml nicht gepflegt | `/session-docu --audit` prüft + warnt |
| Sync-Konflikte | Unidirektionale Syncs, kanonische Quelle definiert |
| Zu viele Systems of Record | Source-of-Truth Matrix (Section D) = verbindlich |

---

## Success Criteria

| Metrik | Vorher (Ist) | Ziel Phase 3 | Ziel Phase 5 |
|--------|-------------|--------------|--------------|
| Systeme für Doku-Suche | 6 | 2 (dev-hub + Outline) | 1 (dev-hub als Portal) |
| Repos mit Reference-Docs | 0/18 | 5/18 | 12/18 |
| Repos mit audience.yaml | 0/18 | 3/18 | 10/18 |
| Ø Documentation Health Score | unbekannt | ≥50% | ≥70% |
| Docstring-Coverage (Ø) | geschätzt ~40% | 50% | 65% |
| Time-to-find (Entwickler) | ~5 min | ~1 min | ~30s |

---

## References

- [ADR-020: Documentation Strategy](./ADR-020-documentation-strategy.md) — Status: Deferred
- [ADR-046: Documentation Governance — Hygiene & Docs Agent](./ADR-046-docs-hygiene.md)
- [ADR-143: Knowledge Hub — Outline Integration](./ADR-143-knowledge-hub-outline-integration.md)
- [ADR-144: doc-hub — Paperless-ngx](./ADR-144-doc-hub-paperless-ngx.md)
- [ADR-154: Autonomous Coding Optimization](./ADR-154-autonomous-coding-optimization.md)
- [DIATAXIS Framework](https://diataxis.fr/)
- [Backstage TechDocs](https://backstage.io/docs/features/techdocs/)
- dev-hub TechDocs: `apps/techdocs/services.py` (GitHub → DB sync)
- docs-agent: `platform/packages/docs-agent/` (AST Scanner, DIATAXIS Classifier)
