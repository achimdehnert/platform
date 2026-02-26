# ADR Index — Platform Architecture Decision Records

> **Pflege**: Wird automatisch aktualisiert beim Erstellen/Ändern eines ADR via `/adr` Workflow.  
> **Letzte Aktualisierung**: 2026-02-26 (ADR-087 + ADR-088: OpenClaw-Übernahme)
> **ADR-Template**: v2.0 — `docs/templates/adr-template.md`

> 🔢 **Nächste freie Nummer (platform-weit):** `ADR-089`  
> 🔢 **Nächste freie Nummer (trading-hub):** `ADR-402`

---

## Status-Legende

| Status | Bedeutung |
|--------|----------|
| `Proposed` | Entwurf — Review ausstehend |
| `Accepted` | Angenommen — gilt als verbindlich |
| `Deprecated` | Veraltet — durch neueres ADR ersetzt |
| `Superseded` | Explizit abgelöst (siehe `Supersedes`-Feld) |
| `Draft` | Zurück in Bearbeitung nach Review |
| `Moved` | In Ziel-Repo migriert — Stub verbleibt hier als Redirect |
| `?` | Metadaten fehlen — Normalisierung ausstehend |

## Repo-Legende

| Repo | Beschreibung | ADR-Nummernbereich |
|------|-------------|-------------------|
| `platform` | CI/CD, Deployment, Docker, DB, Security, Governance, Work Management | 001–099 |
| `bfagent` | Agent, Handler, Tool, Memory, LLM, Prompt | 100–149 |
| `travel-beat` | Story, Travel, Trip, Timing, Content | 150–199 |
| `mcp-hub` | MCP, Server, Protocol, Registry | 200–249 |
| `risk-hub` | Risk, Assessment, Scoring, Compliance | 250–299 |
| `cad-hub` | CAD, IFC, XGF, Viewer, BIM | 300–349 |
| `pptx-hub` | PPTX, PowerPoint, Slide, Presentation | 350–399 |
| `trading-hub` | Trading, Market, Exchange, Bot | 400–449 |
| `shared` | API, Auth, Logging, Shared, Cross-App | 450–499 |
| `coach-hub` | Coach, KI, Multi-Tenant SaaS | 500–549 |

---

## ADR-Katalog

### Core Platform (001–099)

| Nr | Titel | Status | Repo | Datei |
|----|-------|--------|------|-------|
| 007 | Tenant- & RBAC-Architektur | `Accepted` | `platform` | [ADR-007-FINAL-PRODUCTION.md](ADR-007-FINAL-PRODUCTION.md) |
| 008 | Infrastructure Services & Self-Healing Deployment | `Deprecated` | `platform` | [ADR-008-INFRASTRUCTURE.md](ADR-008-INFRASTRUCTURE.md) |
| 009 | Platform Architecture - Optimized | `Deprecated` | `platform` | [ADR-009-PLATFORM-ARCHITECTURE-OPTIMIZED.md](ADR-009-PLATFORM-ARCHITECTURE-OPTIMIZED.md) |
| 010 | MCP Tool Governance | `Accepted` | `mcp-hub` | [ADR-010-mcp-tool-governance.md](ADR-010-mcp-tool-governance.md) |
| 012 | MCP Server Quality Standards | `Accepted` | `mcp-hub` | [ADR-012-mcp-quality-standards.md](ADR-012-mcp-quality-standards.md) |
| 013 | Team Organization & MCP Ownership | `Deprecated` | `platform` | [ADR-013-team-organization-mcp-ownership.md](ADR-013-team-organization-mcp-ownership.md) |
| 014 | AI-Native Development Teams | `Superseded` | `platform` | [ADR-014-ai-native-development-teams.md](ADR-014-ai-native-development-teams.md) |
| 015 | Platform Governance System | `Accepted` | `platform` | [ADR-015-platform-governance-system.md](ADR-015-platform-governance-system.md) |
| **016** | ~~Import von Reiseplänen als Trip-Stops~~ | `Moved` | → `travel-beat` | [Redirect-Stub](ADR-016-trip-plan-import.md) |
| 017 | Domain Development Lifecycle (DDL) | `Superseded` | `platform` | [ADR-017-domain-development-lifecycle.md](ADR-017-domain-development-lifecycle.md) |
| **018** | ~~Weltenhub — Zentrale Story-Universe Plattform~~ | `Moved` | → `weltenhub` | [Redirect-Stub](ADR-018-weltenhub-architecture.md) |
| **019** | ~~Weltenhub UI, Templates, Views & APIs~~ | `Moved` | → `weltenhub` | [Redirect-Stub](ADR-019-weltenhub-ui-templates-apis.md) |
| 020 | Dokumentationsstrategie — Sphinx, DB-driven, ADR-basiert | `Superseded` | `platform` | [ADR-020-documentation-strategy.md](ADR-020-documentation-strategy.md) |
| 021 | Unified Deployment Architecture | `Accepted` | `platform` | [ADR-021-unified-deployment-pattern.md](ADR-021-unified-deployment-pattern.md) |
| 022 | Platform Consistency Standard (v3) | `Accepted` | `platform` | [ADR-022-platform-consistency-standard.md](ADR-022-platform-consistency-standard.md) |
| **024** | ~~Location-Recherche als Weltenhub-Modul~~ | `Moved` | → `weltenhub` | [Redirect-Stub](ADR-024-recherche-hub-weltenhub-integration.md) |
| 027 | Shared Backend Services | `Accepted` | `shared` | [ADR-027-shared-backend-services.md](ADR-027-shared-backend-services.md) |
| 028 | Platform Context — Konsolidierung der Platform Foundation | `Accepted` | `platform` | [ADR-028-platform-context.md](ADR-028-platform-context.md) |
| **029** | ~~CAD Hub Extraction from bfagent~~ | `Moved` | → `cad-hub` | [Redirect-Stub](ADR-029-cad-hub-extraction.md) |
| 031 | Static Asset Versioning & Landing Page Registry | `Accepted` | `platform` | [ADR-031-static-asset-versioning.md](ADR-031-static-asset-versioning.md) |
| 032 | Domain Development Lifecycle (DDL) | `Deprecated` | `platform` | [ADR-032-domain-development-lifecycle.md](ADR-032-domain-development-lifecycle.md) |
| 033 | Dual-Framework-Governance (Django + Odoo) | `Superseded` | `platform` | [ADR-033-dual-framework-governance.md](ADR-033-dual-framework-governance.md) |
| **034** | ~~CAD-Daten ETL-Pipeline + Chat-Agent~~ | `Moved` | → `cad-hub` | [Redirect-Stub](ADR-034-cad-etl-chat-agent.md) |
| 035 | Shared Django Tenancy Package | `Accepted` | `shared` | [ADR-035-shared-django-tenancy.md](ADR-035-shared-django-tenancy.md) |
| **038** | ~~DSB-Modul — Externer Datenschutzbeauftragter~~ | `Moved` | → `risk-hub` | [Redirect-Stub](ADR-038-dsb-datenschutzbeauftragter-module.md) |
| **039** | ~~Seating Drag & Drop Layout-Editor~~ | `Moved` | → `wedding-hub` | [Redirect-Stub](ADR-039-seating-drag-drop-layout-editor.md) |
| 040 | Frontend Completeness Gate | `Accepted` | `platform` | [ADR-040-frontend-completeness-gate.md](ADR-040-frontend-completeness-gate.md) |
| 041 | Django Component Pattern — Reusable UI Blocks | `Accepted` | `platform` | [ADR-041-django-component-pattern.md](ADR-041-django-component-pattern.md) |
| 042 | Development Environment & Deployment Workflow | `Accepted` | `platform` | [ADR-042-dev-environment-deploy-workflow.md](ADR-042-dev-environment-deploy-workflow.md) |
| 043 | AI-Assisted Development — Context & Workflow Optimization | `Accepted` | `platform` | [ADR-043-ai-assisted-development.md](ADR-043-ai-assisted-development.md) |
| 045 | Secrets & Environment Management | `Accepted` | `platform` | [ADR-045-secrets-management.md](ADR-045-secrets-management.md) |
| 046 | Documentation Governance — Hygiene, DIATAXIS & Docs Agent | `Accepted` | `platform` | [ADR-046-docs-hygiene.md](ADR-046-docs-hygiene.md) |
| **047** | ~~Sphinx Documentation Hub~~ | `Moved` | → `bfagent` | [Redirect-Stub](ADR-047-sphinx-documentation-hub.md) |
| 048 | HTMX Playbook — Canonical Patterns for Django-HTMX | `Accepted` | `platform` | [ADR-048-htmx-playbook.md](ADR-048-htmx-playbook.md) |
| 049 | Design Token System — CSS Custom Properties + Tailwind Bridge | `Accepted` | `platform` | [ADR-049-design-token-system.md](ADR-049-design-token-system.md) |
| 050 | Platform Decomposition — Hub Landscape & Developer Portal | `Accepted` | `platform` | [ADR-050-platform-decomposition-hub-landscape.md](ADR-050-platform-decomposition-hub-landscape.md) |
| 051 | Concept-to-ADR Pipeline — Idea Capture & Promotion Workflow | `Accepted` | `platform` | [ADR-051-concept-to-adr-pipeline.md](ADR-051-concept-to-adr-pipeline.md) |
| **052** | ~~Trading Hub — Broker-Adapter-Architektur~~ | `Moved` | → `trading-hub` | [Redirect-Stub](ADR-052-trading-hub-broker-adapter-architecture.md) |
| 053 | deployment-mcp Robustness — Circuit Breaker, Timeout-Fixes | `Superseded` | `platform` | [ADR-053-deployment-mcp-robustness.md](ADR-053-deployment-mcp-robustness.md) |
| 054 | Deployment Pre-Flight Validation & platform-context als Managed Package | `Proposed` | `platform` | [ADR-054-deployment-preflight-validation.md](ADR-054-deployment-preflight-validation.md) |
| 055 | Cross-App Bug & Feature Management | `Accepted` | `platform` | [ADR-055-cross-app-bug-management.md](ADR-055-cross-app-bug-management.md) |
| 056 | Deployment Preflight & Pipeline Hardening | `Accepted` | `platform` | [ADR-056-deployment-preflight-and-pipeline-hardening.md](ADR-056-deployment-preflight-and-pipeline-hardening.md) |
| 057 | Platform Test Strategy — 4-Ebenen-Pyramide | `Accepted` | `platform` | [ADR-057-platform-test-strategy.md](ADR-057-platform-test-strategy.md) |
| 058 | Platform Test Taxonomy — 28-Typen-Katalog | `Accepted` | `platform` | [ADR-058-platform-test-taxonomy.md](ADR-058-platform-test-taxonomy.md) |
| 059 | Adopt Automated ADR Drift Detection and Staleness Management | `Accepted` | `platform` | [ADR-059-adr-drift-detector.md](ADR-059-adr-drift-detector.md) |
| 060 | Developer Workstation SSH Configuration | `Accepted` | `platform` | [ADR-060-developer-workstation-ssh-configuration.md](ADR-060-developer-workstation-ssh-configuration.md) |
| 061 | Hardcoding Elimination Strategy — Platform-wide | `Accepted` | `platform` | [ADR-061-hardcoding-elimination-strategy.md](ADR-061-hardcoding-elimination-strategy.md) |
| 062 | Content Store — Shared PostgreSQL Schema für AI-Inhalte | `Accepted` | `platform` | [ADR-062-content-store-shared-persistence.md](ADR-062-content-store-shared-persistence.md) |
| 063 | Staging Environment Strategy | `Accepted` | `platform` | [ADR-063-staging-environment-strategy.md](ADR-063-staging-environment-strategy.md) |
| **064** | ~~Coach-Hub KI ohne Risiko — Row-Level Multi-Tenant SaaS~~ | `Moved` | → `coach-hub` | [Redirect-Stub](ADR-064-coach-hub-ki-ohne-risiko-architecture.md) |
| 065 | ADR Numbering — Filesystem-First Vergabe-Strategie | `Accepted` | `platform` | [ADR-065-adr-numbering-filesystem-first.md](ADR-065-adr-numbering-filesystem-first.md) |
| 066 | AI Engineering Squad — Rollenbasierte Agenten + Gate-Workflows | `Accepted` | `platform` | [ADR-066-ai-engineering-team.md](ADR-066-ai-engineering-team.md) |
| 067 | Work Management Strategy — GitHub Issues + Projects + AI-Agent-Protokoll | `Accepted` | `platform` | [ADR-067-work-management-strategy.md](ADR-067-work-management-strategy.md) |
| 068 | Adaptive Model Routing + Quality Feedback Loop | `Accepted` | `platform` | [ADR-068-adaptive-model-routing.md](ADR-068-adaptive-model-routing.md) |
| 069 | Web Intelligence MCP — Plattformweiter Web-Zugriff für KI-Agenten | `Accepted` | `mcp-hub` | [ADR-069-web-intelligence-mcp.md](ADR-069-web-intelligence-mcp.md) |
| 070 | Progressive Autonomy Pattern für den Developer-Agenten | `Accepted` | `platform` | [ADR-070-progressive-autonomy-developer-agent.md](ADR-070-progressive-autonomy-developer-agent.md) |
| 071 | Amendment: Code Quality Tooling (amends ADR-022) | `Accepted` | `platform` | [ADR-071-amendment-code-quality-tooling.md](ADR-071-amendment-code-quality-tooling.md) |
| 072 | Adopt PostgreSQL Schema Isolation for SaaS Multi-Tenancy | `Accepted` | `platform` | [ADR-072-multi-tenancy-schema-isolation.md](ADR-072-multi-tenancy-schema-isolation.md) |
| 073 | Repo Scope & Migration Status | `Accepted` | `platform` | [ADR-073-repo-scope.md](ADR-073-repo-scope.md) |
| 074 | Multi-Tenancy Testing Strategy — Isolation, Propagation & CI Gates | `Accepted` | `platform` | [ADR-074-multi-tenancy-testing-strategy.md](ADR-074-multi-tenancy-testing-strategy.md) |
| 075 | Deployment Execution Strategy — Read/Write-Split MCP vs GitHub Actions | `Accepted` | `platform` | [ADR-075-deployment-execution-strategy.md](ADR-075-deployment-execution-strategy.md) |
| **076** | ~~bfagent CI Test Strategy~~ | `Moved` | → `bfagent` | [Redirect-Stub](ADR-076-bfagent-ci-test-strategy.md) |
| 077 | Infrastructure Context System — catalog-info.yaml + Webhook Auto-Import | `Accepted` | `platform` | [ADR-077-infrastructure-context-system.md](ADR-077-infrastructure-context-system.md) |
| 078 | Amendment: Docker HEALTHCHECK ausschließlich in docker-compose.prod.yml | `Accepted` | `platform` | [ADR-078-amendment-docker-healthcheck-convention.md](ADR-078-amendment-docker-healthcheck-convention.md) |
| 079 | Adopt Temporal Self-Hosted as Primary Durable Workflow Engine | `Accepted` | `platform` | [ADR-079-temporal-workflow-engine.md](ADR-079-temporal-workflow-engine.md) |
| 080 | Multi-Agent Coding Team Pattern — Handoff, Parallelisierung, Rollback | `Accepted` | `platform` | [ADR-080-multi-agent-coding-team-pattern.md](ADR-080-multi-agent-coding-team-pattern.md) |
| 081 | Agent Guardrails & Code Safety — Scope-Lock, Pre/Post-Gates, Rollback | `Accepted` | `platform` | [ADR-081-agent-guardrails-code-safety.md](ADR-081-agent-guardrails-code-safety.md) |
| 082 | LLM-Tool-Integration — Autonome Coding-Tasks via StepExecutor + ToolRegistry | `Accepted` | `platform` | [ADR-082-llm-tool-integration-autonomous-coding.md](ADR-082-llm-tool-integration-autonomous-coding.md) |
| 083 | Hybrid ADR Governance — Platform + Repo-lokale ADRs | `Proposed` | `platform` | [ADR-083-hybrid-adr-governance.md](ADR-083-hybrid-adr-governance.md) |
| 084 | Model Registry — Dynamisches LLM-Modell-Routing mit datenbankgestützter Tier-Verwaltung | `Accepted` | `platform` / `mcp-hub` | [ADR-084-model-registry-dynamic-llm-routing.md](ADR-084-model-registry-dynamic-llm-routing.md) |
| 085 | Use Case Pipeline — Natural Language → Structured TaskGraph | `Accepted` | `platform` / `mcp-hub` | [ADR-085-use-case-pipeline-nl-to-taskgraph.md](ADR-085-use-case-pipeline-nl-to-taskgraph.md) |
| 086 | Agent Team Workflow Definition | `Accepted` | `platform` | [ADR-086-agent-team-workflow-definition.md](ADR-086-agent-team-workflow-definition.md) |
| 087 | Hybrid Search Architecture — pgvector + FTS + Reciprocal Rank Fusion | `Proposed` | `platform` | [ADR-087-hybrid-search-architecture.md](ADR-087-hybrid-search-architecture.md) |
| 088 | Notification Registry — Einheitliches Multi-Channel-Benachrichtigungssystem | `Proposed` | `platform` | [ADR-088-notification-registry.md](ADR-088-notification-registry.md) |

> ✅ **Nächste freie Nummer (Core Platform):** `ADR-089`

### MCP Hub (150–199)

| Nr | Titel | Status | Repo | Datei |
|----|-------|--------|------|-------|
| 023 | Shared Scoring and Routing Engine | `Accepted` | `mcp-hub` | [ADR-023-shared-scoring-routing-engine.md](ADR-023-shared-scoring-routing-engine.md) |
| 044 | MCP-Hub Architecture Consolidation | `Accepted` | `mcp-hub` | [ADR-044-mcp-hub-architecture-consolidation.md](ADR-044-mcp-hub-architecture-consolidation.md) |

### Migrierte ADRs — Repo-Referenzen

> Diese ADRs wurden in ihre Ziel-Repos verschoben. In `platform/docs/adr/` existieren nur noch Redirect-Stubs.

| Nr | Titel | Ziel-Repo | Stub |
|----|-------|-----------|------|
| **016** | Import von Reiseplänen als Trip-Stops | [`travel-beat`](https://github.com/achimdehnert/travel-beat/blob/main/docs/adr/ADR-016-trip-plan-import.md) | [Stub](ADR-016-trip-plan-import.md) |
| **018** | Weltenhub — Zentrale Story-Universe Plattform | [`weltenhub`](https://github.com/achimdehnert/weltenhub/blob/main/docs/adr/ADR-018-weltenhub-architecture.md) | [Stub](ADR-018-weltenhub-architecture.md) |
| **019** | Weltenhub UI, Templates, Views & APIs | [`weltenhub`](https://github.com/achimdehnert/weltenhub/blob/main/docs/adr/ADR-019-weltenhub-ui-templates-apis.md) | [Stub](ADR-019-weltenhub-ui-templates-apis.md) |
| **024** | Location-Recherche als Weltenhub-Modul | [`weltenhub`](https://github.com/achimdehnert/weltenhub/blob/main/docs/adr/ADR-024-recherche-hub-weltenhub-integration.md) | [Stub](ADR-024-recherche-hub-weltenhub-integration.md) |
| **029** | CAD Hub Extraction from bfagent | [`cad-hub`](https://github.com/achimdehnert/cad-hub/blob/main/docs/adr/ADR-029-cad-hub-extraction.md) | [Stub](ADR-029-cad-hub-extraction.md) |
| **034** | CAD-Daten ETL-Pipeline + Chat-Agent | [`cad-hub`](https://github.com/achimdehnert/cad-hub/blob/main/docs/adr/ADR-034-cad-etl-chat-agent.md) | [Stub](ADR-034-cad-etl-chat-agent.md) |
| **038** | DSB-Modul — Externer Datenschutzbeauftragter | [`risk-hub`](https://github.com/achimdehnert/risk-hub/blob/main/docs/adr/ADR-038-dsb-datenschutzbeauftragter-module.md) | [Stub](ADR-038-dsb-datenschutzbeauftragter-module.md) |
| **039** | Seating Drag & Drop Layout-Editor | [`wedding-hub`](https://github.com/achimdehnert/wedding-hub/blob/main/docs/adr/ADR-039-seating-drag-drop-layout-editor.md) | [Stub](ADR-039-seating-drag-drop-layout-editor.md) |
| **047** | Sphinx Documentation Hub | [`bfagent`](https://github.com/achimdehnert/bfagent/blob/main/docs/adr/ADR-047-sphinx-documentation-hub.md) | [Stub](ADR-047-sphinx-documentation-hub.md) |
| **052** | Trading Hub — Broker-Adapter-Architektur | [`trading-hub`](https://github.com/achimdehnert/trading-hub/blob/main/docs/adr/ADR-052-trading-hub-broker-adapter-architecture.md) | [Stub](ADR-052-trading-hub-broker-adapter-architecture.md) |
| **064** | Coach-Hub KI ohne Risiko Architecture | [`coach-hub`](https://github.com/achimdehnert/coach-hub/blob/main/docs/adr/ADR-064-coach-hub-ki-ohne-risiko-architecture.md) | [Stub](ADR-064-coach-hub-ki-ohne-risiko-architecture.md) |
| **076** | bfagent CI Test Strategy | [`bfagent`](https://github.com/achimdehnert/bfagent/blob/main/docs/adr/ADR-076-bfagent-ci-test-strategy.md) | [Stub](ADR-076-bfagent-ci-test-strategy.md) |
| **400** | Hybrid-Architektur für Market Scanner Module | [`trading-hub`](https://github.com/achimdehnert/trading-hub/blob/main/docs/adr/ADR-400-market-scanner-hybrid-architecture.md) | [Stub](ADR-400-market-scanner-hybrid-architecture.md) |
| **401** | Autonomer Trading Bot — Execution-Loop & Bot-Architektur | [`trading-hub`](https://github.com/achimdehnert/trading-hub/blob/main/docs/adr/ADR-401-autonomous-trading-bot.md) | [Stub](ADR-401-autonomous-trading-bot.md) |

### bfagent — in platform verbleibend

| Nr | Titel | Status | Datei |
|----|-------|--------|-------|
| 036 | Chat-Agent Ecosystem — DomainToolkits, Research Integration | `Accepted` | [ADR-036-chat-agent-ecosystem.md](ADR-036-chat-agent-ecosystem.md) |
| 037 | Chat Conversation Logging & Quality Management | `Accepted` | [ADR-037-chat-conversation-logging.md](ADR-037-chat-conversation-logging.md) |

### Shared / Cross-App

| Nr | Titel | Status | Datei |
|----|-------|--------|-------|
| 030 | Erste Odoo Management-App — Dual-Framework-Governance | `Accepted` | [ADR-030-odoo-management-app.md](ADR-030-odoo-management-app.md) |

---

## Offene Punkte / Hygiene-Backlog

### ⚠️ Metadaten fehlen (`?`-Status)

Die folgenden ADRs haben keine maschinenlesbaren Metadaten-Felder. Bei nächster Bearbeitung normalisieren:

- ADR-010 bis ADR-049 (Großteil der älteren Platform-ADRs)

### ⚠️ Review-Dateien als Satelliten

Die folgenden Dateien sind Review-Protokolle, keine eigenständigen ADRs — sollten in `reviews/`-Unterverzeichnis verschoben werden:

- `ADR-022-REVIEW.md`, `ADR-023-REVIEW.md`, `ADR-029-REVIEW.md`
- `ADR-038-REVIEW.md`, `ADR-038-R3-REVIEW.md`
- `ADR-044-review-deployment-mcp.md`, `ADR-046-merged-REVIEW.md`

> **Guard**: `python3 scripts/adr_next_number.py --check`
> **Audit**: `python3 scripts/adr_audit.py --fix-hints`

---

## Pflege-Anleitung

Beim Erstellen eines neuen ADR via `/adr` Workflow:

1. Neue Zeile in der passenden Sektion eintragen
2. Status initial: `Proposed`
3. Repo aus Scope-Erkennung übernehmen
4. Datum in "Letzte Aktualisierung" aktualisieren

Beim Status-Wechsel (z.B. `Proposed` → `Accepted`):

1. Status-Spalte in INDEX.md aktualisieren
2. `**Status**`-Feld in der ADR-Datei selbst aktualisieren
3. Changelog-Eintrag im ADR ergänzen
