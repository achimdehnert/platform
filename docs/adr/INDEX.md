# Architecture Decision Records -- Index

> **Last updated:** 2026-03-11
> **Next free ADR number:** 138

## Legend

| Status | Bedeutung |
|--------|-----------|
| `Proposed` | Vorgeschlagen, noch nicht akzeptiert |
| `Accepted` | Akzeptiert und gueltig |
| `Deprecated` | Veraltet, ersetzt durch neueres ADR |
| `Superseded` | Vollstaendig ersetzt |
| `Archived` | In `_archive/superseded/` verschoben -- nicht mehr aktiv |

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

| # | Title | Status | Link |
|---|-------|--------|------|
| 007 | Tenant- & RBAC-Architektur (Production Ready) | `Accepted` | [ADR-007](ADR-007-FINAL-PRODUCTION.md) |
| 008 | Infrastructure Services & Self-Healing Deployment | `Deprecated` | [ADR-008](ADR-008-INFRASTRUCTURE.md) |
| 009 | Platform Architecture -- Optimized | `Deprecated` | [ADR-009](ADR-009-PLATFORM-ARCHITECTURE-OPTIMIZED.md) |
| 010 | MCP Tool Governance -- Specification Standard, Service Discovery | `Accepted` | [ADR-010](ADR-010-mcp-tool-governance.md) |
| 012 | MCP Server Quality Standards | `Accepted` | [ADR-012](ADR-012-mcp-quality-standards.md) |
| 013 | Team Organization & MCP Ownership | `Deprecated` | [ADR-013](ADR-013-team-organization-mcp-ownership.md) |
| 014 | AI-Native Development Teams | `Accepted` | [ADR-014](ADR-014-ai-native-development-teams.md) |
| 015 | Platform Governance System | `Accepted` | [ADR-015](ADR-015-platform-governance-system.md) |
| 016 | Import von Reiseplaenen als Trip-Stops | `Archived` | [ADR-016](_archive/superseded/ADR-016-trip-plan-import.md) |
| 017 | Domain Development Lifecycle (DDL) | `Superseded` | [ADR-017](ADR-017-domain-development-lifecycle.md) |
| 018 | Weltenhub -- Zentrale Story-Universe Plattform | `Archived` | [ADR-018](_archive/superseded/ADR-018-weltenhub-architecture.md) |
| 019 | Weltenhub UI, Templates, Views & APIs | `Archived` | [ADR-019](_archive/superseded/ADR-019-weltenhub-ui-templates-apis.md) |
| 020 | Dokumentationsstrategie -- Sphinx, DB-driven, ADR-basiert | `Superseded` | [ADR-020](ADR-020-documentation-strategy.md) |
| 021 | Unified Single-Service Deployment Pipeline | `Accepted` | [ADR-021](ADR-021-unified-deployment-pattern.md) |
| 022 | Platform Consistency Standard (v3) | `Accepted` | [ADR-022](ADR-022-platform-consistency-standard.md) |
| 023 | Shared Scoring and Routing Engine | `Deprecated` | [ADR-023](ADR-023-shared-scoring-routing-engine.md) |
| 024 | Location-Recherche als Weltenhub-Modul | `Archived` | [ADR-024](_archive/superseded/ADR-024-recherche-hub-weltenhub-integration.md) |
| 027 | Shared Backend Services fuer Django-Projekte | `Accepted` | [ADR-027](ADR-027-shared-backend-services.md) |
| 028 | Platform Context -- Konsolidierung der Platform Foundation | `Accepted` | [ADR-028](ADR-028-platform-context.md) |
| 029 | CAD Hub Extraction from bfagent | `Archived` | [ADR-029](_archive/superseded/ADR-029-cad-hub-extraction.md) |
| 030 | Erste Odoo Management-App -- Dual-Framework-Governance | `Accepted` | [ADR-030](ADR-030-odoo-management-app.md) |
| 031 | Static Asset Versioning & Landing Page Registry | `Accepted` | [ADR-031](ADR-031-static-asset-versioning.md) |
| 032 | Domain Development Lifecycle (DDL) | `Deprecated` | [ADR-032](ADR-032-domain-development-lifecycle.md) |
| 033 | Dual-Framework-Governance (Django + Odoo) | `Superseded` | [ADR-033](ADR-033-dual-framework-governance.md) |
| 034 | CAD-Daten ETL-Pipeline + Chat-Agent als Platform-Service | `Archived` | [ADR-034](_archive/superseded/ADR-034-cad-etl-chat-agent.md) |
| 035 | Shared Django Tenancy Package | `Accepted` | [ADR-035](ADR-035-shared-django-tenancy.md) |
| 036 | Chat-Agent Ecosystem -- DomainToolkits, Research Integration | `Accepted` | [ADR-036](ADR-036-chat-agent-ecosystem.md) |
| 037 | Chat Conversation Logging & Quality Management | `Accepted` | [ADR-037](ADR-037-chat-conversation-logging.md) |
| 038 | DSB Datenschutzbeauftragter Module | `Archived` | [ADR-038](_archive/superseded/ADR-038-dsb-datenschutzbeauftragter-module.md) |
| 039 | Seating Drag & Drop Layout-Editor | `Archived` | [ADR-039](_archive/superseded/ADR-039-seating-drag-drop-layout-editor.md) |
| 040 | Frontend Completeness Gate | `Accepted` | [ADR-040](ADR-040-frontend-completeness-gate.md) |
| 041 | Django Component Pattern -- Reusable UI Blocks | `Accepted` | [ADR-041](ADR-041-django-component-pattern.md) |
| 042 | Development Environment & Deployment Workflow | `Accepted` | [ADR-042](ADR-042-dev-environment-deploy-workflow.md) |
| 043 | AI-Assisted Development -- Context & Workflow Optimization | `Accepted` | [ADR-043](ADR-043-ai-assisted-development.md) |
| 044 | MCP-Hub Architecture Consolidation | `Accepted` | [ADR-044](ADR-044-mcp-hub-architecture-consolidation.md) |
| 045 | Secrets & Environment Management | `Accepted` | [ADR-045](ADR-045-secrets-management.md) |
| 046 | Documentation Governance -- Hygiene, DIATAXIS & Docs Agent | `Accepted` | [ADR-046](ADR-046-docs-hygiene.md) |
| 047 | Sphinx Documentation Hub (sphinx.iil.pet) | `Superseded` | [ADR-047](ADR-047-sphinx-documentation-hub.md) |
| 048 | HTMX Playbook -- Canonical Patterns for Django-HTMX | `Accepted` | [ADR-048](ADR-048-htmx-playbook.md) |
| 049 | Design Token System -- CSS Custom Properties + Tailwind Bridge | `Accepted` | [ADR-049](ADR-049-design-token-system.md) |
| 050 | Platform Decomposition -- Hub Landscape & Developer Portal | `Accepted` | [ADR-050](ADR-050-platform-decomposition-hub-landscape.md) |
| 051 | Concept-to-ADR Pipeline -- Idea Capture & AI-Assisted Promotion | `Accepted` | [ADR-051](ADR-051-concept-to-adr-pipeline.md) |
| 052 | Trading Hub -- Broker-Adapter-Architektur | `Archived` | [ADR-052](_archive/superseded/ADR-052-trading-hub-broker-adapter-architecture.md) |
| 053 | deployment-mcp Robustness -- Circuit Breaker & Timeout-Fixes | `Superseded` | [ADR-053](ADR-053-deployment-mcp-robustness.md) |
| 054 | Deployment Pre-Flight Validation & platform-context | `Superseded` | [ADR-054](ADR-054-deployment-preflight-validation.md) |
| 055 | Cross-App Bug & Feature Management | `Accepted` | [ADR-055](ADR-055-cross-app-bug-management.md) |
| 056 | Deployment Pre-Flight Validation & Pipeline Hardening | `Accepted` | [ADR-056](ADR-056-deployment-preflight-and-pipeline-hardening.md) |
| 057 | Four-Level Test Strategy with Contract Testing | `Accepted` | [ADR-057](ADR-057-platform-test-strategy.md) |
| 058 | 28-Type Test Taxonomy as Platform Binding Standard | `Accepted` | [ADR-058](ADR-058-platform-test-taxonomy.md) |
| 059 | Automated ADR Drift Detection and Staleness Management | `Accepted` | [ADR-059](ADR-059-adr-drift-detector.md) |
| 060 | Developer Workstation SSH Key Configuration Standard | `Accepted` | [ADR-060](ADR-060-developer-workstation-ssh-configuration.md) |
| 061 | Adopt hardcode_scanner.py as Platform-wide Tooling | `Accepted` | [ADR-061](ADR-061-hardcoding-elimination-strategy.md) |
| 062 | Central Billing Service (billing-hub) | `Accepted` | [ADR-062](ADR-062-central-billing-service.md) |
| 063 | Staging Environment Strategy | `Accepted` | [ADR-063](ADR-063-staging-environment-strategy.md) |
| 064 | coach-hub Architecture | `Archived` | [ADR-064](_archive/superseded/ADR-064-coach-hub-ki-ohne-risiko-architecture.md) |
| 065 | Filesystem-first ADR Numbering -- max(existing) + 1 | `Accepted` | [ADR-065](ADR-065-adr-numbering-filesystem-first.md) |
| 066 | AI Engineering Squad with Role-based Agents | `Accepted` | [ADR-066](ADR-066-ai-engineering-team.md) |
| 067 | GitHub Issues + Projects as Single Source of Truth | `Accepted` | [ADR-067](ADR-067-work-management-strategy.md) |
| 068 | Adaptive Model Routing and Quality Feedback Loop | `Accepted` | [ADR-068](ADR-068-adaptive-model-routing.md) |
| 069 | Web Intelligence MCP -- Plattformweiter Web-Zugriff | `Accepted` | [ADR-069](ADR-069-web-intelligence-mcp.md) |
| 070 | Progressive Autonomy Pattern fuer den Developer-Agenten | `Accepted` | [ADR-070](ADR-070-progressive-autonomy-developer-agent.md) |
| 071 | Amendment: Code Quality Tooling (amends ADR-022) | `Accepted` | [ADR-071](ADR-071-amendment-code-quality-tooling.md) |
| 072 | PostgreSQL Schema Isolation for SaaS Multi-Tenancy | `Accepted` | [ADR-072](ADR-072-multi-tenancy-schema-isolation.md) |
| 073 | Repo Scope & Migration Status (all 10 repos) | `Accepted` | [ADR-073](ADR-073-repo-scope.md) |
| 074 | Multi-Tenancy Testing Strategy -- Isolation, Propagation & CI | `Accepted` | [ADR-074](ADR-074-multi-tenancy-testing-strategy.md) |
| 075 | Split Deployment Execution: Read-only MCP + Server-side Writes | `Accepted` | [ADR-075](ADR-075-deployment-execution-strategy.md) |
| 076 | bfagent CI Test Strategy | `Archived` | [ADR-076](_archive/superseded/ADR-076-bfagent-ci-test-strategy.md) |
| 077 | Infrastructure Context System: catalog-info.yaml -> dev-hub API | `Accepted` | [ADR-077](ADR-077-infrastructure-context-system.md) |
| 078 | Amendment: Docker HEALTHCHECK ausschliesslich in docker-compose | `Accepted` | [ADR-078](ADR-078-amendment-docker-healthcheck-convention.md) |
| 079 | Adopt Temporal Self-Hosted as Primary Durable Workflow Engine | `Accepted` | [ADR-079](ADR-079-temporal-workflow-engine.md) |
| 080 | Multi-Agent Coding Team Pattern | `Accepted` | [ADR-080](ADR-080-multi-agent-coding-team-pattern.md) |
| 081 | Agent Guardrails & Code Safety -- Scope-Lock, Pre/Post-Gates | `Accepted` | [ADR-081](ADR-081-agent-guardrails-code-safety.md) |
| 082 | LLM Tool Integration -- Autonomous Coding Agent | `Accepted` | [ADR-082](ADR-082-llm-tool-integration-autonomous-coding.md) |
| 083 | Hybrid ADR Governance -- Platform + Repo-lokale ADRs | `Accepted` | [ADR-083](ADR-083-hybrid-adr-governance.md) |
| 084 | Model Registry -- Dynamisches LLM-Modell-Routing | `Accepted` | [ADR-084](ADR-084-model-registry-dynamic-llm-routing.md) |
| 085 | Use Case Pipeline -- Natural Language -> Structured TaskGraph | `Accepted` | [ADR-085](ADR-085-use-case-pipeline-nl-to-taskgraph.md) |
| 086 | Agent Team Workflow -- Cross-Repo Sprint Execution Pattern | `Accepted` | [ADR-086](ADR-086-agent-team-workflow.md) |
| 087 | Hybrid Search: pgvector + FTS Platform-wide | `Accepted` | [ADR-087](ADR-087-hybrid-search-architecture.md) |
| 088 | Shared Notification Registry -- Multi-Channel Messaging | `Accepted` | [ADR-088](ADR-088-notification-registry.md) |
| 089 | bfagent-llm -- LiteLLM-Backend + DB-driven Model-Routing | `Accepted` | [ADR-089](ADR-089-bfagent-llm-litellm-db-driven-architecture.md) |
| 090 | Abstract CI/CD Pipeline -- Python + PostgreSQL -> Docker Deploy | `Accepted` | [ADR-090](ADR-090-cicd-pipeline-python-postgres.md) |
| 091 | Platform Operations Hub Consolidation | `Proposed` | [ADR-091](ADR-091-platform-operations-hub-consolidation.md) |
| 093 | AI Config App -- aifw als shared Django-App | `Accepted` | [ADR-093](ADR-093-ai-config-app.md) |
| 094 | Django Migration Conflict Resolution Pattern | `Accepted` | [ADR-094](ADR-094-django-migration-conflict-resolution.md) |
| 095 | aifw Quality-Level Routing -- Multi-Dimensional LLM Dispatch with Prompt-Template Coordination | `Accepted` | [ADR-095](ADR-095-aifw-quality-level-routing.md) |
| 096 | authoringfw -- Content Orchestration Scope, Architecture, and Domain Boundaries | `Proposed` | [ADR-096](ADR-096-authoringfw-scope-and-architecture.md) |
| 097 | aifw 0.6.0 Implementation Contract -- Models, Migration, Service Layer, and Public API | `Proposed` | [ADR-097](ADR-097-aifw-060-implementation-contract.md) |
| 098 | Adopt 3-Layer Tuning Standard for PROD/DEV Hetzner Infrastructure | `Accepted` | [ADR-098](ADR-098-production-infrastructure-tuning-standard.md) |
| 099 | dev-hub Release Management UI -- PyPI Publishing & GitHub Tag Workflow via devhub.iil.pet | `Proposed` | [ADR-099](ADR-099-devhub-release-management-ui.md) |
| 100 | iil-testkit -- Shared Test Factory Package | `Accepted` | [ADR-100](ADR-100-iil-testkit-shared-test-factory-package.md) |
| 107 | Extended Agent Team -- Deployment Agent | `Accepted` | [ADR-107](ADR-107-extended-agent-team-deployment-agent.md) |
| 108 | Agent QA Cycle -- Quality Evaluator, Completion, AuditStore | `Accepted` | [ADR-108](ADR-108-agent-qa-cycle.md) |
| 109 | Multi-Tenancy Platform Standard (alle UI-Hubs) | `Accepted` | [ADR-109](ADR-109-multi-tenancy-platform-standard.md) |
| 110 | i18n Platform Standard (alle UI-Hubs) | `Accepted` | [ADR-110](ADR-110-i18n-platform-standard.md) |
| 111 | Private Package Distribution via GitHub Packages | `Superseded` | [ADR-111](ADR-111-private-package-distribution.md) |
| 112 | Agent Skill Registry + Persistent Context | `Accepted` | [ADR-112](ADR-112-agent-skill-registry-persistent-context.md) |
| 113 | Telegram Gateway + pgvector Memory | `Accepted` | [ADR-113](ADR-113-telegram-gateway-pgvector-memory.md) |
| 114 | Discord IDE-like Communication Gateway | `Accepted` | [ADR-114](ADR-114-discord-ide-like-communication-gateway.md) |
| 115 | Grafana Agent Controlling Dashboard | `Accepted` | [ADR-115](ADR-115-grafana-agent-controlling-dashboard.md) |
| 116 | Dynamic Model Router | `Accepted` | [ADR-116](ADR-116-dynamic-model-router.md) |
| 117 | Shared World Layer (worldfw) | `Accepted` | [ADR-117](ADR-117-shared-world-layer-worldfw.md) |
| 118 | billing-hub als Platform Store | `Accepted` | [ADR-118](ADR-118-platform-store-billing-hub-user-registration.md) |
| 119 | Authored Content Pipeline (Neutral Lore → Style) | `Accepted` | [ADR-119](ADR-119-authored-content-pipeline-neutral-lore-to-style.md) |
| 120 | Unified Deployment Pipeline | `Accepted` | [ADR-120](ADR-120-unified-deployment-pipeline.md) |
| 121 | iil-outlinefw Story-Outline-Framework (ehem. ADR-100) | `Accepted` | [ADR-121](ADR-121-iil-outlinefw-story-outline-framework.md) |
| 130 | Shared PostgreSQL Schema `content_store` (ehem. ADR-062) | `Accepted` | [ADR-130](ADR-130-content-store-shared-persistence.md) |
| 131 | Shared Backend Services Library (ehem. ADR-091) | `Accepted` | [ADR-131](ADR-131-shared-backend-services.md) |
| 132 | AI Context Defense-in-Depth (ehem. ADR-094) | `Accepted` | [ADR-132](ADR-132-ai-context-defense-in-depth.md) |
| 133 | Shared AI Services Package (ehem. ADR-094) | `Proposed` | [ADR-133](ADR-133-shared-ai-services-package.md) |
| 134 | Module Monetization Strategy (ehem. ADR-099) | `Proposed` | [ADR-134](ADR-134-module-monetization-strategy.md) |
| 136 | Shared Backend Services Original (ehem. ADR-2026-001) — **Deprecated**, siehe ADR-131 | `Deprecated` | [ADR-136](ADR-136-shared-backend-services-original.md) |
| 137 | Tenant-Lifecycle, Self-Service Module-Buchung und RLS (ehem. ADR-121) | `Accepted` | [ADR-137](ADR-137-tenant-lifecycle-module-selfservice-rls.md) |

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
- [ ] ADR-096: Review + `Accepted` → kann jetzt starten (ADR-095 ist Accepted)
- [ ] ADR-097: Review + `Accepted` → dann aifw 0.6.0 implementieren
- [ ] ADR-099: Review + `Accepted` → dann dev-hub `releases` App implementieren
- [ ] catalog-info.yaml in allen 30 Repos pruefen/erstellen (ADR-077 compliance)
