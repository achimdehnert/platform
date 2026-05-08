# Architecture Decision Records -- Index

> **Last updated:** 2026-05-08
> **Next free ADR number:** 190

## Legend

| Status | Bedeutung |
|--------|-----------|
| `Proposed` | Vorgeschlagen, noch nicht akzeptiert |
| `Accepted` | Akzeptiert und gueltig |
| `Deprecated` | Veraltet, ersetzt durch neueres ADR |
| `Superseded` | Vollstaendig ersetzt |
| `Archived` | In `_archive/superseded/` verschoben -- nicht mehr aktiv |

### Impl Column (ADR-138)

| Emoji | Meaning |
|-------|---------|
| — | Not applicable (deprecated/superseded/governance) |
| ⬜ | `none` — not started |
| 🔶 | `partial` — in progress |
| ✅ | `implemented` |
| ✅✅ | `verified` in production |

## Repository Registry (20 Repos)

> Source of truth: filesystem `u:\home\dehnert\github\*.*`
> Canonical live catalog: `https://devhub.iil.pet/api/v1/context/`

### Django Apps
| Repository | Kuerzel | URL | Status |
|-----------|---------|-----|--------|
| platform | `platform` | — | Production |
| bfagent | `bfagent` | bfagent.iil.pet | Production |
| risk-hub | `risk-hub` | demo.schutztat.de | Production |
| weltenhub | `weltenhub` | weltenforger.com | Production |
| travel-beat | `travel-beat` | drifttales.com | Production |
| dev-hub | `dev-hub` | devhub.iil.pet | Production |
| pptx-hub | `pptx-hub` | prezimo.com | Production |
| cad-hub | `cad-hub` | nl2cad.de | Active |
| coach-hub | `coach-hub` | kiohnerisiko.de | Active |
| trading-hub | `trading-hub` | ai-trades.de | Active |
| wedding-hub | `wedding-hub` | wedding-hub.iil.pet | Active |
| 137-hub | `137-hub` | 137herz.de | Active |
| odoo-hub | `odoo-hub` | intern (Odoo) | Production |

### Platform & Infrastructure
| Repository | Kuerzel | Beschreibung | Status |
|-----------|---------|-------------|--------|
| mcp-hub | `mcp-hub` | MCP Servers (deployment, llm, orchestrator) | Production |
| infra-deploy | `infra-deploy` | GitHub Actions infra deploy runner | Production |

### Python Frameworks & Libraries
| Repository | Kuerzel | Package | Status |
|-----------|---------|---------|--------|
| aifw | `aifw` | iil-aifw | Active |
| authoringfw | `authoringfw` | authoringfw | Active |
| promptfw | `promptfw` | promptfw | Active |
| weltenfw | `weltenfw` | weltenfw | Active |
| nl2cad | `nl2cad` | nl2cad | Active |

---

## ADR Index

> Alle Links zeigen auf die echten Dateien im Filesystem. Generiert via `scripts/adr_next_number.py`.
> **Impl** column: implementation_status per ADR-138.

| # | Title | Status | Impl | Link |
|---|-------|--------|------|------|
| 007 | Tenant- & RBAC-Architektur (Production Ready) | `Accepted` | ✅ | [ADR-007](ADR-007-FINAL-PRODUCTION.md) |
| 008 | Infrastructure Services & Self-Healing Deployment | `Deprecated` | — | [ADR-008](ADR-008-INFRASTRUCTURE.md) |
| 009 | Platform Architecture -- Optimized | `Deprecated` | — | [ADR-009](ADR-009-PLATFORM-ARCHITECTURE-OPTIMIZED.md) |
| 010 | MCP Tool Governance -- Specification Standard, Service Discovery | `Accepted` | ✅ | [ADR-010](ADR-010-mcp-tool-governance.md) |
| 012 | MCP Server Quality Standards | `Accepted` | ✅ | [ADR-012](ADR-012-mcp-quality-standards.md) |
| 013 | Team Organization & MCP Ownership | `Deprecated` | — | [ADR-013](ADR-013-team-organization-mcp-ownership.md) |
| 014 | AI-Native Development Teams | `Accepted` | ✅ | [ADR-014](ADR-014-ai-native-development-teams.md) |
| 015 | Platform Governance System | `Accepted` | ✅ | [ADR-015](ADR-015-platform-governance-system.md) |
| 016 | Import von Reiseplaenen als Trip-Stops | `Archived` | — | [ADR-016](_archive/superseded/ADR-016-trip-plan-import.md) |
| 017 | Domain Development Lifecycle (DDL) | `Superseded` | — | [ADR-017](ADR-017-domain-development-lifecycle.md) |
| 018 | Weltenhub -- Zentrale Story-Universe Plattform | `Archived` | — | [ADR-018](_archive/superseded/ADR-018-weltenhub-architecture.md) |
| 019 | Weltenhub UI, Templates, Views & APIs | `Archived` | — | [ADR-019](_archive/superseded/ADR-019-weltenhub-ui-templates-apis.md) |
| 020 | Dokumentationsstrategie -- Sphinx, DB-driven, ADR-basiert | `Superseded` | — | [ADR-020](ADR-020-documentation-strategy.md) |
| 021 | Unified Single-Service Deployment Pipeline | `Accepted` | ✅ | [ADR-021](ADR-021-unified-deployment-pattern.md) |
| 022 | Platform Consistency Standard (v3) | `Accepted` | ✅ | [ADR-022](ADR-022-platform-consistency-standard.md) |
| 023 | Shared Scoring and Routing Engine | `Deprecated` | — | [ADR-023](ADR-023-shared-scoring-routing-engine.md) |
| 024 | Location-Recherche als Weltenhub-Modul | `Archived` | — | [ADR-024](_archive/superseded/ADR-024-recherche-hub-weltenhub-integration.md) |
| 027 | Shared Backend Services fuer Django-Projekte | `Accepted` | ✅ | [ADR-027](ADR-027-shared-backend-services.md) |
| 028 | Platform Context -- Konsolidierung der Platform Foundation | `Accepted` | ✅ | [ADR-028](ADR-028-platform-context.md) |
| 029 | CAD Hub Extraction from bfagent | `Archived` | — | [ADR-029](_archive/superseded/ADR-029-cad-hub-extraction.md) |
| 030 | Erste Odoo Management-App -- Dual-Framework-Governance | `Accepted` | ✅ | [ADR-030](ADR-030-odoo-management-app.md) |
| 031 | Static Asset Versioning & Landing Page Registry | `Accepted` | ✅ | [ADR-031](ADR-031-static-asset-versioning.md) |
| 032 | Domain Development Lifecycle (DDL) | `Deprecated` | — | [ADR-032](ADR-032-domain-development-lifecycle.md) |
| 033 | Dual-Framework-Governance (Django + Odoo) | `Superseded` | — | [ADR-033](ADR-033-dual-framework-governance.md) |
| 034 | CAD-Daten ETL-Pipeline + Chat-Agent als Platform-Service | `Archived` | — | [ADR-034](_archive/superseded/ADR-034-cad-etl-chat-agent.md) |
| 035 | Shared Django Tenancy Package | `Accepted` | ✅ | [ADR-035](ADR-035-shared-django-tenancy.md) |
| 036 | Chat-Agent Ecosystem -- DomainToolkits, Research Integration | `Accepted` | ✅ | [ADR-036](ADR-036-chat-agent-ecosystem.md) |
| 037 | Chat Conversation Logging & Quality Management | `Accepted` | ✅ | [ADR-037](ADR-037-chat-conversation-logging.md) |
| 038 | DSB Datenschutzbeauftragter Module | `Archived` | — | [ADR-038](_archive/superseded/ADR-038-dsb-datenschutzbeauftragter-module.md) |
| 039 | Seating Drag & Drop Layout-Editor | `Archived` | — | [ADR-039](_archive/superseded/ADR-039-seating-drag-drop-layout-editor.md) |
| 040 | Frontend Completeness Gate | `Accepted` | ✅ | [ADR-040](ADR-040-frontend-completeness-gate.md) |
| 041 | Django Component Pattern -- Reusable UI Blocks | `Accepted` | ✅ | [ADR-041](ADR-041-django-component-pattern.md) |
| 042 | Development Environment & Deployment Workflow | `Accepted` | ✅ | [ADR-042](ADR-042-dev-environment-deploy-workflow.md) |
| 043 | AI-Assisted Development -- Context & Workflow Optimization | `Accepted` | ✅ | [ADR-043](ADR-043-ai-assisted-development.md) |
| 044 | MCP-Hub Architecture Consolidation | `Accepted` | ✅ | [ADR-044](ADR-044-mcp-hub-architecture-consolidation.md) |
| 045 | Secrets & Environment Management | `Accepted` | ✅ | [ADR-045](ADR-045-secrets-management.md) |
| 046 | Documentation Governance -- Hygiene, DIATAXIS & Docs Agent | `Accepted` | ✅ | [ADR-046](ADR-046-docs-hygiene.md) |
| 047 | Sphinx Documentation Hub (sphinx.iil.pet) | `Superseded` | — | [ADR-047](ADR-047-sphinx-documentation-hub.md) |
| 048 | HTMX Playbook -- Canonical Patterns for Django-HTMX | `Accepted` | ✅ | [ADR-048](ADR-048-htmx-playbook.md) |
| 049 | Design Token System -- CSS Custom Properties + Tailwind Bridge | `Accepted` | ✅ | [ADR-049](ADR-049-design-token-system.md) |
| 050 | Platform Decomposition -- Hub Landscape & Developer Portal | `Accepted` | ✅ | [ADR-050](ADR-050-platform-decomposition-hub-landscape.md) |
| 051 | Concept-to-ADR Pipeline -- Idea Capture & AI-Assisted Promotion | `Accepted` | ✅ | [ADR-051](ADR-051-concept-to-adr-pipeline.md) |
| 052 | Trading Hub -- Broker-Adapter-Architektur | `Archived` | — | [ADR-052](_archive/superseded/ADR-052-trading-hub-broker-adapter-architecture.md) |
| 053 | deployment-mcp Robustness -- Circuit Breaker & Timeout-Fixes | `Superseded` | — | [ADR-053](ADR-053-deployment-mcp-robustness.md) |
| 054 | Deployment Pre-Flight Validation & platform-context | `Superseded` | — | [ADR-054](ADR-054-deployment-preflight-validation.md) |
| 055 | Cross-App Bug & Feature Management | `Accepted` | ✅ | [ADR-055](ADR-055-cross-app-bug-management.md) |
| 056 | Deployment Pre-Flight Validation & Pipeline Hardening | `Accepted` | ✅ | [ADR-056](ADR-056-deployment-preflight-and-pipeline-hardening.md) |
| 057 | Four-Level Test Strategy with Contract Testing | `Accepted` | 🔶 | [ADR-057](ADR-057-platform-test-strategy.md) |
| 058 | 28-Type Test Taxonomy as Platform Binding Standard | `Accepted` | 🔶 | [ADR-058](ADR-058-platform-test-taxonomy.md) |
| 059 | Automated ADR Drift Detection and Staleness Management | `Accepted` | ✅ | [ADR-059](ADR-059-adr-drift-detector.md) |
| 060 | Developer Workstation SSH Key Configuration Standard | `Accepted` | ✅ | [ADR-060](ADR-060-developer-workstation-ssh-configuration.md) |
| 061 | Adopt hardcode_scanner.py as Platform-wide Tooling | `Accepted` | ✅ | [ADR-061](ADR-061-hardcoding-elimination-strategy.md) |
| 062 | Central Billing Service (billing-hub) | `Accepted` | ✅ | [ADR-062](ADR-062-central-billing-service.md) |
| 063 | Staging Environment Strategy | `Superseded` | — | [ADR-063](ADR-063-staging-environment-strategy.md) |
| 064 | coach-hub Architecture | `Archived` | — | [ADR-064](_archive/superseded/ADR-064-coach-hub-ki-ohne-risiko-architecture.md) |
| 137 | Tenant Lifecycle Module Self-Service RLS | `Accepted` | ✅ | [ADR-137](ADR-137-tenant-lifecycle-module-selfservice-rls.md) |
| 138 | ADR Implementation Tracking Standard -- Lifecycle, Frontmatter Fields, Verification | `Accepted` | ✅ | [ADR-138](ADR-138-implementation-tracking-standard.md) |
| 148 | Adopt Django Multi-Tenant SaaS Architecture for Recruiting Hub | `Proposed` | ⬜ | [ADR-148](ADR-148-recruiting-hub-architecture.md) |
| 149 | Adopt d.velop Cloud DMS as Platform Document Archive Service (dms-hub) | `Accepted` | 🔶 | [ADR-149](ADR-149-dms-hub-dvelop-platform-service.md) |
| 153 | Tax-Hub SaaS Architecture | `Accepted` | 🔶 | [ADR-153](ADR-153-tax-hub-saas-architecture.md) |
| 155 | Three-Layer Contract Testing Strategy (all function/method calls) | `Accepted` | 🔶 | [ADR-155](ADR-155-contract-testing-strategy.md) |
| 156 | Adopt Server-Side Deploy Scripts with Short-Trigger Pattern for Reliable Pipeline | `Accepted` | ✅ | [ADR-156](ADR-156-reliable-deployment-pipeline.md) |
| 157 | Adopt same-port staging on Dev Desktop with automated port governance and onboarding | `Accepted` | ✅ | [ADR-157](ADR-157-staging-production-split-and-port-governance.md) |
| 158 | Adopt dev-hub as Unified Documentation Portal with Audience Navigator and AI-Generated Reference Docs | `Proposed` | 🔶 | [ADR-158](ADR-158-unified-documentation-architecture.md) |
| 160 | Adopt Standardized Two-File CI/CD Pipeline for All Hub Repositories | `Accepted` | 🔶 | [ADR-160](../../mcp-hub/docs/ADR-160-standardized-hub-deployment.md) |
| 161 | Adopt Two-Layer-Schema with Hybrid-RLS for Tenant-Spanning SDS Data | `Proposed` | ⬜ | [ADR-161](ADR-161-shared-sds-library.md) |
| 162 | Adopt REFLEX as Standard Methodology for Evidence-based UI Development | `Accepted` | 🔶 | [ADR-162](ADR-162-reflex-ui-testing-and-scraping.md) |
| 163 | Adopt Three-Tier REFLEX Quality Standard for All Platform Repositories | `Accepted` | 🔶 | [ADR-163](ADR-163-reflex-tiering-platform-quality-standard.md) |
| 164 | Unified Port Strategy — Conflict-free dev, staging, and production port assignments | `Accepted` | 🔶 | [ADR-164](ADR-164-port-strategy-conflict-free-dev-staging-prod.md) |
| 165 | Adopt Plugin-based REFLEX Review Engine with Grafana Controlling | `Proposed` | ⬜ | [ADR-165](ADR-165-reflex-review-engine-with-grafana-controlling.md) |
| 166 | Standardize deployment config via .ship.conf SSOT with /livez/ health checks | `Accepted` | ✅ | [ADR-166](ADR-166-deployment-configuration-standard.md) |
| 167 | Adopt 3-Tier Middleware Standard for Health Probes and Tenant Resolution | `Accepted` | 🔶 | [ADR-167](ADR-167-three-tier-middleware-architecture.md) |
| 168 | Build Onboarding-Platform as separate repo on coach-hub primitives with billing-hub Stripe pattern | `Proposed` | ⬜ | [ADR-168](ADR-168-onboarding-platform-architecture.md) |
| 169 | Adopt iil-enrichment as generic pattern for bridging managed records with external knowledge sources | `Proposed` | 🔶 | [ADR-169](ADR-169-enrichment-agent-pattern.md) |
| 170 | Adopt iil-ingest as Reusable Document Ingestion Package (Tier 3) | `Accepted` | 🔶 | [ADR-170](ADR-170-iil-ingest-document-ingestion-package.md) |
| 174 | Workflow Enforcement: CI Gate + PR Checklist + Symlink Policy | `Accepted` | 🔶 | [ADR-174](ADR-174-workflow-enforcement-ci-gate.md) |
| 175 | Adopt selective modularization for .windsurf/workflows/ files | `Accepted` | ✅ | [ADR-175](ADR-175-workflow-modularization-pattern.md) |
| 177 | Agent Role Specialization — Split Developer into 5 specialized agents (DocBot, TestBot, FeatureBot, ReEngineerBot, ArchitectBot) | `Proposed` | ⬜ | [ADR-177](ADR-177-agent-role-specialization.md) |
| 185 | Adopt Gate-controlled Deploy-Agent for automated Staging→Prod deployments | `Proposed` | ⬜ | [ADR-185](ADR-185-deploy-agent-pattern.md) |
| 186 | Adopt Headless Agent-Coding Pipeline via Devin CLI + Orchestrator Bridge for Polyrepo Automation | `Proposed` | ⬜ | [ADR-186](ADR-186-headless-agent-coding-pipeline.md) |
| 187 | Document Intelligence Pipeline — iil-ingest erweitern um VectorStore, Multi-Tool Ensemble & RAG | `Accepted` | 🔶 | [ADR-187](ADR-187-document-intelligence-pipeline.md) |
| 188 | Adopt ADR-171 Schema with multilingual-e5-large as Platform-Wide Unified Vector Store | `Proposed` | ⬜ | [ADR-188](ADR-188-unified-vector-store.md) |
| 189 | Einführung eines automatisierten LLM Model Screener & Provider Research Systems | `Proposed` | ⬜ | [ADR-189](ADR-189-llm-model-screener.md) |

## Gaps (intentional -- deleted/archived ADRs)

> Luecken werden nie wiederverwendet (ADR-065). Folgende Nummern sind permanent frei:
> ADR-001 bis ADR-006 (pre-filesystem era), ADR-011, ADR-025, ADR-026, ADR-092
> Archivierte ADRs (016, 018, 019, 024, 029, 034, 038, 039, 052, 064, 076, 400, 401): siehe `_archive/superseded/`
> ADR-060-aifw-quality-level-routing.md: gelöscht (Tombstone, ersetzt durch ADR-095)
> ADR-100-extended-agent-team-deployment-agent.md: gelöscht (deprecated, ersetzt durch ADR-107)
> ADR-103-ausschreibungs-hub-architektur.md: gelöscht (superseded by v3)
> ADR-062-REVIEW.md: verschoben nach docs/reviews/
> ADR-2026-001: umnummeriert zu ADR-136 (ungültige Nummerierung)
> Nummernkonflikte aufgelöst (2026-03-11): ADR-062, ADR-091, ADR-094, ADR-099, ADR-100 → ADR-130–136

---

## Open Points / Hygiene Backlog

- [ ] ADR-174: Rollout qm-gate auf weitere Repos (bulk via /onboard-repo)
- [ ] ADR-174: Track 3 Workflow-Metriken (Issue erstellen nach risk-hub Praxiserfahrung)
- [x] ADR-189: LLM Model Screener & Provider Research — Proposed, External Review 4.9/5 — 2026-05-08

- [x] ADR-094 (Migration Conflict Resolution): `Accepted` -- 2026-03-02
- [x] ADR-095 rev1: alle Blocker + Highs aus externem Review resolved -- 2026-03-02
- [x] ADR-096 (authoringfw Scope): `Proposed` -- 2026-03-02
- [x] ADR-097 (aifw 0.6.0 Contract): `Proposed` -- 2026-03-02
- [x] ADR-098 (3-Layer Tuning Standard): `Accepted` -- 2026-03-04
- [x] ADR-099 (dev-hub Release Management UI): `Proposed` -- 2026-03-04
- [x] ADR-100 (iil-testkit): `Accepted` -- 2026-03-05
- [x] ADR-121 (iil-outlinefw, ehem. ADR-100/135): `Accepted` -- 2026-03-08
- [x] ADR-107 (Extended Agent Team): `Accepted` -- 2026-03-08
- [x] ADR-108 (Agent QA Cycle): `Accepted` -- 2026-03-08
- [x] ADR-109 (Multi-Tenancy Platform Standard): `Accepted` -- 2026-03-08
- [x] ADR-110 (i18n Platform Standard): `Accepted` -- 2026-03-08
- [x] ADR-111 (Private Package Distribution): `Accepted` → `Superseded` -- 2026-03-11
- [x] Repo-Tabelle auf 20 Repos aktualisiert -- 2026-03-04
- [x] ADR-095: zweites Review ✅ APPROVED → Status `Accepted` -- 2026-03-11
- [x] ADR-073: Repo Scope aktualisiert (10 → 30 Repos) -- 2026-03-11
- [x] ADR-060-aifw-quality-level-routing.md: gelöscht (2026-03-11)
- [x] Nummernkonflikte aufgelöst: 7 Duplikate → ADR-130–136 (2026-03-11)
- [x] ADR-136: Deprecated (Duplikat von ADR-131) -- 2026-03-11
- [x] Review-Verdicts aktualisiert: ADR-114 ✅ v2.2, ADR-117 ✅ v1.1, ADR-119 ✅ v1.1 -- 2026-03-11
- [x] ADR-103 BLOCK gefixt (Poetry → hatchling, Tippfehler) -- 2026-03-11
- [x] ADR-104 BLOCK gefixt (MADR Frontmatter) -- 2026-03-11
- [x] ADR-096: ✅ APPROVED → `Accepted` -- 2026-03-11
- [x] ADR-097: ✅ APPROVED → `Accepted` → aifw 0.6.0 kann implementiert werden -- 2026-03-11
- [x] ADR-099: INDEX-Status korrigiert (`Proposed` → `Accepted`, war bereits im ADR) -- 2026-03-11
- [x] aifw 0.6.0: bereits vollständig implementiert (Models, Migration, Service, Tests) — __version__ sync gefixt -- 2026-03-11
- [x] catalog-info.yaml: 29/29 Repos haben jetzt catalog-info.yaml (8 fehlende erstellt) -- 2026-03-11
- [x] ADR-138: Implementation Tracking Standard geschrieben + 61 ADRs mit implementation_status backfilled -- 2026-03-11
- [x] ADR-138: INDEX.md Impl-Spalte hinzugefügt -- 2026-03-11
- [x] ADR-130: Review-Amend (UUID→BigAutoField, Alembic→Django ORM, creative-services→content_store) -- 2026-03-11
- [x] ADR-138: Review-Amend (status partial, Ausnahme für Governance-ADRs mit Artefakten) -- 2026-03-11
- [x] ADR-138 Backfill: 24 Accepted ADRs mit implementation_status versehen (15 YAML + 8 neues Frontmatter + 1 API) -- 2026-03-11
- [x] INDEX.md Impl-Spalte aktualisiert auf Backfill-Werte -- 2026-03-11
- [x] ADR-108: Datei ADR-108-agent-qa-cycle.md erstellt + implementation_status: implemented -- 2026-03-11
- [x] ADR-138: /adr-review Workflow Check auf fehlende implementation_status -- 2026-03-11
- [x] ADR-138: implementation_status partial→implemented (alle Schritte erledigt) -- 2026-03-11
- [x] ADR-062+118: billing-hub deployed (https://billing.iil.pet), CI green, 7 Platforms + 31 Plans seeded -- 2026-03-11
- [x] ADR-118: EmailVerification model + service + checkout flow implementiert + deployed -- 2026-03-11
- [x] ADR-062: partial→implemented, ADR-118: partial→implemented -- 2026-03-11
- [x] ADR-132: partial→implemented (Phase 0+1+2 alle ✅, platform_context_mcp live) -- 2026-03-11
- [x] billing-hub: deploy.yml entfernt (ci-cd.yml deckt alles ab, startup_failure behoben) -- 2026-03-11
- [x] ADR-131: partial→implemented — billing-hub ist erster Consumer (INSTALLED_APPS, MIDDLEWARE, health URLs, IIL_COMMONS config) -- 2026-03-11
- [x] ADR-098: partial→implemented — Redis maxmemory 15/15, PG random_page_cost 17/17, 6 Repos compose-hardened, shm_size+logging -- 2026-03-11
- [x] ADR-088: partial→implemented — 5 Channels (Email, SMS, Webhook, Discord, Telegram), 21 Tests, BigAutoField-Fix, Celery-First -- 2026-03-11
- [x] ADR-121: Frontmatter repariert (war komplett kaputt), implemented→partial (Phase 3 pending), INDEX ✅→🔶 -- 2026-03-11
- [x] ADR-121: partial→implemented — ci.yml erstellt, ruff lint clean (94→0), v0.1.1 tagged, writing-hub bereits migriert -- 2026-03-11
- [x] ADR-087: partial→implemented — platform-search Package komplett (SearchService, RRF, MMR, Decay), 10 Tests, 5 DB-Indexes -- 2026-03-11
- [x] ADR-117: partial→implemented — weltenfw v0.2.0 komplett (Backends, Schema, Resources, Auth, 50 Tests, CI+Publish) -- 2026-03-11
