---
status: proposed
date: 2026-04-03
decision-makers: [Achim Dehnert]
consulted: [Cascade (Principal IT-Architekt)]
informed: []
supersedes: ["ADR-020-documentation-strategy.md"]
amends: ["ADR-046-docs-hygiene.md"]
related:
  - ADR-020-documentation-strategy.md
  - ADR-046-docs-hygiene.md
  - ADR-047-sphinx-documentation-hub.md
  - ADR-143-knowledge-hub-outline-integration.md
  - ADR-144-doc-hub-paperless-ngx.md
  - ADR-154-autonomous-coding-optimization.md
  - ADR-156-reliable-deployment-pipeline.md
implementation_status: partial
implementation_evidence:
  - "dev-hub/apps/portal/models.py: AudienceConfig, AudienceSource, DocHealthMetric, DocHealthProfile"
  - "dev-hub/apps/portal/services.py: AudienceService, CrossLinkService, DocHealthService"
  - "dev-hub/apps/portal/views.py: AudienceNavigatorView, AudienceRoleDetailView, DocHealthDashboardView"
  - "dev-hub/apps/portal/tasks.py: scan_repo_doc_health, scan_all_doc_health"
  - "dev-hub/apps/portal/migrations/0002_audience_dochealth.py"
  - "platform/packages/docs-agent/src/docs_agent/extractors/"
  - "platform/packages/docs-agent/src/docs_agent/git_utils.py"
  - "platform/packages/docs-agent/src/docs_agent/cli.py: reference()"
---

# ADR-158: Adopt dev-hub as Unified Documentation Portal with Audience Navigator and AI-Generated Reference Docs

<!-- Drift-Detector-Felder (ADR-059)
staleness_months: 3
drift_check_paths:
  - .windsurf/workflows/session-docu.md
  - platform/scripts/docu-audit.sh
  - packages/docs-agent/
supersedes_check: ADR-020 (superseded), ADR-046 (amends)
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

## Decision Outcome

**Chosen option: C — dev-hub als Portal erweitern**, because dev-hub bereits TechDocs Sync (389 Seiten), ADR Lifecycle, Software Catalog und Health Dashboard hat. Es fehlen nur Audience Navigator und Reference-Doc Generator. Kein neues System nötig, maximale Wiederverwendung bestehender Infrastruktur.

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
| **ADRs** | GitHub `docs/adr/*.md` | dev-hub ADR Lifecycle, Outline (Deep-Links only) | Celery hourly + `/session-docu` |
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

**Konfiguration via `audience.yaml`** pro Repo (Pydantic v2 validiert, `schema_version: 1`):

```yaml
# platform/docs/audience.yaml
schema_version: 1

audiences:
  user:
    title: "Für Anwender"    # i18n: _() in DB-Model (K-03)
    icon: "users"
    sources:
      - type: github
        paths: ["docs/tutorials/", "README.md"]
      - type: outline
        collections: ["User Guides", "FAQ"]    # H-02: collections statt query

  developer:
    title: "Für Entwickler"
    icon: "code"
    sources:
      - type: github
        paths: ["CORE_CONTEXT.md", "AGENT_HANDOVER.md", "docs/guides/", "docs/reference/"]
      - type: techdocs
        site_slug: "platform"

  architect:
    title: "Für Architekten"
    icon: "building"
    sources:
      - type: github
        paths: ["docs/adr/", "docs/explanation/"]
      - type: outline
        collections: ["Konzepte", "Lessons Learned"]
      - type: techdocs
        site_slug: "platform"
        filter: "explanation/"

  operator:
    title: "Für Betreiber"
    icon: "server"
    sources:
      - type: outline
        collections: ["Runbooks", "Operations", "Incident Reports"]
      - type: devhub
        apps: ["health", "operations"]
      - type: github
        paths: ["docs/guides/deployment.md"]
        # M-04: AGENT_HANDOVER.md ist Agent-Kontext (ADR-154), nicht Operator-Doku
```

**Hybridansatz:** `audience.yaml` als Seed-Datei → via `manage.py load_audience_config` in DB importiert → Änderungen danach über Admin-UI. Gibt Tenant-Isolation + Git-Nachvollziehbarkeit.

**Validierung:** Pydantic v2 Schema (`audience_validator.py`) mit typisierten Sources, Discriminated Union und M-04-Prüfung. Schema-Validierung als Architecture-Guardian-Rule integrierbar (`check_violations` für audience.yaml).

**Schema-Isolation (ADR-072):** Neue portal-Models sind `django_tenants`-kompatibel (dev-hub nutzt Schema-Isolation). `tenant_id` dient als Fallback-Filter für shared-Schema-Queries.

### D-2: Reference-Doc Generator (docs-agent Integration)

AI-generierte Reference-Docs für jedes Repo, basierend auf Code-Introspection:

| Doc-Typ | Quelle | Generator | Output |
|---------|--------|-----------|--------|
| `models.md` | Django Models (AST + DB Schema) | docs-agent + MCP | `docs/reference/models.md` |
| `api.md` | URL-Patterns (urlpatterns) | docs-agent | `docs/reference/api.md` |
| `config.md` | settings.py + .env.example | docs-agent | `docs/reference/config.md` |
| `lookups.md` | Lookup-Tabellen (DB) | database_manage MCP | `docs/reference/lookups.md` (⚠️ nur intern: in `.gitignore`, nur in dev-hub sichtbar hinter Cloudflare Access — M-02) |
| `architecture.md` | platform-context Rules | platform-context MCP | `docs/reference/architecture.md` |

**Generierung erfolgt via `/session-docu --generate` Workflow** (Dry-Run Default, K-02). Commit nur mit explizitem `--commit` Flag nach manuellem Review. Generator-Output enthält Timestamp + Version-Header. Diff gegen bestehende Datei vor Commit (Idempotenz, A-2).

Alle Reference-Docs haben Header: `<!-- AUTO-GENERATED by /session-docu — DO NOT EDIT MANUALLY -->`

### D-3: Documentation Health Score

Messbare Metriken pro Repo, aggregiert in dev-hub. **Gewichtungen in DB konfigurierbar** (`DocHealthMetric` Model), nicht hart kodiert (H-03):

| Metrik | Default-Gewicht | Quelle | Ziel |
|--------|----------------|--------|------|
| README.md vorhanden + >500 Zeichen | 10% | GitHub | 100% |
| CORE_CONTEXT.md vorhanden | 10% | GitHub | 100% |
| docs/adr/ mit ≥1 ADR | 10% | GitHub | 100% |
| DIATAXIS-Struktur (tutorials/, guides/, reference/) | 15% | docs-agent audit | ≥3 Quadranten |
| Docstring-Coverage | 20% | docs-agent AST Scanner | ≥60% |
| Reference-Docs aktuell (<7 Tage) | 15% | GitHub commit date | 100% |
| Audience Navigator konfiguriert | 10% | audience.yaml | 100% |
| Keine Banned Files in docs/ | 10% | docs-agent / ADR-046 | 0 Violations |

**Health Score = gewichteter Durchschnitt → 0-100%** (History bleibt für Trend-Analyse erhalten, kein Upsert).

Wird in dev-hub Health Dashboard angezeigt (analog zu Service Health).

### D-4: `/session-docu` Workflow

Analog zu `/ship` (Deploy) und `/session-start` (Kontext), aber für Dokumentation:

```
/session-docu [repo|all] [--generate] [--audit] [--sync] [--commit] [--fail-under SCORE]
```

**⚠️ K-02 Safety:** `--generate` ohne `--commit` = **Dry-Run**. Zeigt was generiert würde, schreibt nichts. Erst nach manuellem Review: `/session-docu --generate --commit`.

**Phasen:**

| Phase | Aktion | Tool |
|-------|--------|------|
| 1. Audit | Docstring-Coverage + DIATAXIS-Compliance prüfen | `docu-audit.sh` + docs-agent |
| 2. Generate | Reference-Docs erzeugen (Dry-Run Default!) | docs-agent generate + MCP |
| 3. Commit | Generierte Docs committen (nur mit `--commit`) | git add + commit |
| 4. Sync | Outline Deep-Links aktualisieren (unidirektional) | outline-knowledge MCP |
| 5. Report | Documentation Health Score berechnen + anzeigen | dev-hub API / `docu-audit.sh --json` |

### D-5: Cross-System Sync Rules (alle unidirektional)

| Sync-Richtung | Trigger | Mechanismus | Kanonische Quelle |
|---------------|---------|-------------|-------------------|
| GitHub ADRs → dev-hub | Celery hourly | `adr_lifecycle.sync_all_adr_repos` | GitHub |
| GitHub docs/ → dev-hub TechDocs | Celery daily | `techdocs.sync_all_docs` | GitHub |
| Outline Runbooks → dev-hub | `/session-docu --sync` | **Deep-Links only** (kein Content-Copy!) | Outline |
| Reference-Docs → GitHub | `/session-docu --generate --commit` | AI-generiert, Diff + Review | AI-generiert |
| Error-Patterns → Outline Lessons | `/session-ende` | pgvector → Outline export | pgvector |
| AGENT_HANDOVER.md → dev-hub | Celery daily | TechDocs sync | GitHub |

**Grundregel: KEINE bidirektionalen Syncs. Jede Information hat genau EINE kanonische Quelle.**

> **K-01 Klarstellung:** Outline zeigt ADRs nur als **Deep-Links** zu dev-hub ADR Lifecycle.
> Outline bekommt keinen ADR-Inhalt kopiert. Kein Sync GitHub → Outline für ADRs.

---

## Implementation Plan

### Phase 0: Model Foundation (2h) — NEU

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| `AudienceConfig` + `AudienceSource` Models (BigAutoField, public_id, tenant_id, deleted_at, i18n) | 0.5h | `apps/portal/models.py` |
| `DocHealthProfile` + `DocHealthMetric` Models | 0.5h | `apps/portal/models.py` |
| Migrationen (idempotent, `SeparateDatabaseAndState`) | 0.5h | `apps/portal/migrations/` |
| `locale/de/LC_MESSAGES/portal.po` Grundstruktur (K-03) | 0.5h | i18n Setup |

### Phase 1: Foundation (3h, korrigiert von 2h)

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| `/session-docu` Workflow erstellen (mit `--dry-run` Default, K-02) | 1h | `.windsurf/workflows/session-docu.md` |
| `audience.yaml` Schema + Pydantic v2 Validator (H-01, H-02) | 1h | `packages/docs-agent/audience_validator.py` |
| `docu-audit.sh` Script (Coverage + DIATAXIS + `--json` + `--fail-under`) | 1h | `platform/scripts/docu-audit.sh` |

### Phase 2: Reference-Doc Generation (12h, korrigiert von 4h)

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| docs-agent CLI `generate reference` Subcommand | 4h | `packages/docs-agent/commands/generate.py` |
| Django AST-Introspection (Models, URLs, Settings) | 4h | `packages/docs-agent/extractors/` |
| Idempotenter Git-Diff-Check vor Commit (A-2) | 2h | `packages/docs-agent/git_utils.py` |
| Pilot: risk-hub Reference-Docs | 2h | `risk-hub/docs/reference/*.md` |

### Phase 3: Audience Navigator in dev-hub (8h, korrigiert von 4h)

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| `portal` App: Models + Migrations | 1h | `apps/portal/models.py` |
| `portal` App: Services (AudienceService, CrossLinkService, DocHealthService) | 2h | `apps/portal/services.py` |
| `portal` App: Views + Templates (i18n, `@login_required`) (K-03, M-01) | 2h | `apps/portal/views.py` + Templates |
| `load_audience_config` Management Command | 1h | `apps/portal/management/commands/` |
| TechDocs Sync: README + CORE_CONTEXT einbeziehen | 1h | `techdocs/services.py` erweitern |
| Cloudflare Access Konfiguration für `/docs/*` Pfade (M-01) | 1h | Settings + Middleware |

### Phase 4: Documentation Health Score (4h, korrigiert von 3h)

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| `DocHealthService` Score-Berechnung (konfigurierbare Gewichtungen) | 2h | `apps/portal/services.py` |
| Health Dashboard Integration (Kachel + Trend-Chart) | 1h | Template + View |
| Celery Beat: Weekly Doc-Health-Scan (idempotent) | 1h | `apps/portal/tasks.py` |

### Phase 5: Outline Link-Sync (2h, umbenannt von "Bi-Sync", K-01)

| Task | Aufwand | Deliverable |
|------|---------|-------------|
| Outline Runbook-Links in Audience Navigator (Deep-Links only) | 1h | `apps/portal/services.py` |
| ADR-Links aus ADR Lifecycle → Outline Navigator (kein Content-Copy!) | 1h | `apps/portal/services.py` |

**Gesamt: ~31h über 4-5 Sessions (korrigiert von 15h, H-04)**

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

### Good

- **Ein Einstiegspunkt** (devhub.iil.pet) für alle Dokumentation
- **Audience-Routing**: Jede Rolle findet sofort relevante Inhalte
- **AI-generierte Reference-Docs**: Immer aktuell, kein manueller Aufwand
- **Messbarer Quality Gate**: Documentation Health Score als Governance-Metrik
- **Kein neues System**: Erweitert dev-hub, nutzt Outline + docs-agent
- **Workflow-gesteuert**: `/session-docu` macht Doku-Arbeit reproduzierbar

### Bad

- **dev-hub wird zum SPOF**: Wenn dev-hub down ist, fehlt der Portal-Zugang (Mitigation: GitHub-Docs direkt erreichbar + `docs/portal-fallback.md` mit direkten URLs zu GitHub/Outline, A-3)
- **Audience Navigator braucht Pflege**: `audience.yaml` pro Repo muss aktuell sein (Mitigation: `/session-docu` prüft)
- **Reference-Doc Qualität**: AI-generiert = potenziell ungenau (Mitigation: `--generate` = Dry-Run Default, Commit nur mit explizitem `--commit` nach Review, K-02)
- **Outline bleibt separates System**: Kein Full-Merge möglich (Mitigation: Deep-Links statt Kopieren)

### Risiko-Mitigation

| Risiko | Mitigation |
|--------|------------|
| dev-hub Downtime | GitHub-Docs direkt erreichbar, Outline eigenständig, `docs/portal-fallback.md` mit direkten URLs |
| AI generiert falsche Docs | `--generate` = Dry-Run, `--commit` erfordert Review, Diff-Anzeige vor Commit |
| audience.yaml nicht gepflegt | `/session-docu --audit` prüft + warnt |
| Sync-Konflikte | Unidirektionale Syncs, kanonische Quelle definiert |
| Zu viele Systems of Record | Source-of-Truth Matrix (Section D) = verbindlich |

### Confirmation

Die Einhaltung dieser Architektur-Entscheidung wird verifiziert durch:

1. **`/session-docu --audit`**: Prüft audience.yaml-Präsenz, DIATAXIS-Struktur, Docstring-Coverage pro Repo
2. **Documentation Health Score ≥ 50%**: Quality Gate im dev-hub Health Dashboard (Phase 4)
3. **`docu-audit.sh --json --fail-under 50`**: CI-integrierbarer Check
4. **ADR-059 Drift-Detector**: `staleness_months: 3` + `drift_check_paths` überwachen die Aktualität
5. **Architecture Guardian**: `audience.yaml` Pydantic-Validierung via `audience_validator.py`

---

## Open Questions

| # | Frage | Status | Entscheidung |
|---|-------|--------|-------------|
| Q-1 | **Schema-Versionierung**: Wie wird `audience.yaml` bei `schema_version: 2` migriert? | Deferred | Migrationsskript in docs-agent; Abwärtskompatibilität über Pydantic Union-Types. Entscheidung wenn v2 nötig. |
| Q-2 | **docs-agent Availability**: Was passiert wenn docs-agent nicht installiert ist? | Decided | `docu-audit.sh` prüft Verfügbarkeit und degradiert graceful (AST-Checks werden übersprungen, Score-Metrik = 0). |
| Q-3 | **Celery Performance**: Beeinflussen die Sync-Jobs (hourly ADR, daily TechDocs) die dev-hub Performance? | Decided | Jobs laufen in separater Worker-Queue (`docs`). Beat-Schedule + `max_retries=2` + `soft_time_limit=300s`. |
| Q-4 | **DocHealthMetric Seed**: Wie werden die Default-Gewichtungen initial befüllt? | Decided | `manage.py seed_hubs` erweitern oder neues `seed_doc_metrics` Command. Defaults aus ADR-158 D-3 Tabelle. |
| Q-5 | **Full-Text Search**: Cross-System-Suche über alle Doc-Systeme? | Deferred | Out of scope. Ggf. eigenes ADR wenn Outline + TechDocs + GitHub durchsucht werden soll. |
| Q-6 | **OUTLINE_BASE_URL**: Woher kommt die Umgebungsvariable? | Decided | Via `decouple.config()` aus `.env.prod` (ADR-045). Default: `https://knowledge.iil.pet`. Benötigt für CrossLinkService. |

---

## Implementation Tracking

| Phase | Status | Deliverable | Evidenz |
|-------|--------|-------------|--------|
| Phase 0: Model Foundation | ✅ Done | `AudienceConfig`, `AudienceSource`, `DocHealthMetric`, `DocHealthProfile` | `dev-hub/apps/portal/models.py` |
| Phase 0: Services | ✅ Done | `AudienceService`, `CrossLinkService`, `DocHealthService` | `dev-hub/apps/portal/services.py` |
| Phase 0: Management Command | ✅ Done | `load_audience_config` | `dev-hub/apps/portal/management/commands/` |
| Phase 0: Admin Registration | ✅ Done | 4 ModelAdmins | `dev-hub/apps/portal/admin.py` |
| Phase 0: Migrationen | ✅ Done | `0002_audience_dochealth.py` | `dev-hub/apps/portal/migrations/` |
| Phase 0: i18n Setup | ✅ Done | `locale/de/LC_MESSAGES/django.po` | `dev-hub/apps/portal/locale/de/` |
| Phase 1: `/session-docu` Workflow | ✅ Done | Workflow mit Flags | `.windsurf/workflows/session-docu.md` |
| Phase 1: `audience.yaml` + Validator | ✅ Done | Pydantic v2 Schema | `packages/docs-agent/audience_validator.py` |
| Phase 1: `docu-audit.sh` | ✅ Done | `--json` + `--fail-under` | `platform/scripts/docu-audit.sh` |
| Phase 2: Reference-Doc Generation | ✅ Done | `reference` CLI + 3 Extractors + `git_utils` | `packages/docs-agent/src/docs_agent/extractors/`, `cli.py` |
| Phase 3: Audience Navigator UI | ✅ Done | Views + Templates + URLs + Nav-Link | `dev-hub/apps/portal/views.py`, `templates/portal/` |
| Phase 4: Health Score Dashboard | ✅ Done | Dashboard + Celery + `seed_doc_metrics` | `dev-hub/apps/portal/tasks.py`, `management/commands/` |
| Phase 5: Outline Link-Sync | ✅ Done | Deep-Links via `CrossLinkService` | `dev-hub/apps/portal/services.py`, `views.py` |

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

## More Information

- [ADR-020: Documentation Strategy](./ADR-020-documentation-strategy.md) — Status: Superseded by this ADR
- [ADR-046: Documentation Governance — Hygiene & Docs Agent](./ADR-046-docs-hygiene.md)
- [ADR-143: Knowledge Hub — Outline Integration](./ADR-143-knowledge-hub-outline-integration.md)
- [ADR-144: doc-hub — Paperless-ngx](./ADR-144-doc-hub-paperless-ngx.md)
- [ADR-154: Autonomous Coding Optimization](./ADR-154-autonomous-coding-optimization.md)
- [DIATAXIS Framework](https://diataxis.fr/)
- [Backstage TechDocs](https://backstage.io/docs/features/techdocs/)
- dev-hub TechDocs: `apps/techdocs/services.py` (GitHub → DB sync)
- docs-agent: `platform/packages/docs-agent/` (AST Scanner, DIATAXIS Classifier)

### Required Environment Variables

| Variable | Source | Default | Used by |
|----------|--------|---------|---------|
| `OUTLINE_BASE_URL` | `.env.prod` via `decouple.config()` | `https://knowledge.iil.pet` | `CrossLinkService` |
| `REPO_BASE_DIR` | Django settings | `/workspace` | `load_audience_config` Command |
