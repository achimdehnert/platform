# ADR Index — Platform Architecture Decision Records

> **Pflege**: Wird automatisch aktualisiert beim Erstellen/Ändern eines ADR via `/adr` Workflow.  
> **Letzte Aktualisierung**: 2026-02-22 (Review + Überarbeitung ADR-062/065/066)
> **ADR-Template**: v2.0 — `docs/templates/adr-template.md`

---

## Status-Legende

| Status | Bedeutung |
|--------|-----------|
| `Proposed` | Entwurf — Review ausstehend |
| `Accepted` | Angenommen — gilt als verbindlich |
| `Deprecated` | Veraltet — durch neueres ADR ersetzt |
| `Superseded` | Explizit abgelöst (siehe `Supersedes`-Feld) |
| `Draft` | Zurück in Bearbeitung nach Review |
| `?` | Metadaten fehlen — Normalisierung ausstehend |

## Repo-Legende

| Repo | Beschreibung | ADR-Nummernbereich |
|------|-------------|-------------------|
| `platform` | CI/CD, Deployment, Docker, DB, Security, Cross-App | 001–049 |
| `bfagent` | Agent, Handler, Tool, Memory, LLM, Prompt | 050–099 |
| `travel-beat` | Story, Travel, Trip, Timing, Content | 100–149 |
| `mcp-hub` | MCP, Server, Protocol, Registry | 150–199 |
| `risk-hub` | Risk, Assessment, Scoring, Compliance | 200–249 |
| `cad-hub` | CAD, IFC, XGF, Viewer, BIM | 250–299 |
| `pptx-hub` | PPTX, PowerPoint, Slide, Presentation | 300–349 |
| `shared` | API, Auth, Logging, Shared, Cross-App | 350–399 |
| `trading-hub` | Trading, Market, Exchange, Bot | 400–449 |

---

## ADR-Katalog

### Core Platform (001–049)

| Nr | Titel | Status | Repo | Datei |
|----|-------|--------|------|-------|
| 007 | Tenant- & RBAC-Architektur | `?` | `platform` | [ADR-007-FINAL-PRODUCTION.md](ADR-007-FINAL-PRODUCTION.md) |
| 008 | Infrastructure Services & Self-Healing Deployment | `?` | `platform` | [ADR-008-INFRASTRUCTURE.md](ADR-008-INFRASTRUCTURE.md) |
| 009 | Platform Architecture - Optimized | `?` | `platform` | [ADR-009-PLATFORM-ARCHITECTURE-OPTIMIZED.md](ADR-009-PLATFORM-ARCHITECTURE-OPTIMIZED.md) |
| 010 | MCP Tool Governance | `?` | `mcp-hub` | [ADR-010-mcp-tool-governance.md](ADR-010-mcp-tool-governance.md) |
| 012 | MCP Server Quality Standards | `?` | `mcp-hub` | [ADR-012-mcp-quality-standards.md](ADR-012-mcp-quality-standards.md) |
| 013 | Team Organization & MCP Ownership | `?` | `platform` | [ADR-013-team-organization-mcp-ownership.md](ADR-013-team-organization-mcp-ownership.md) |
| 014 | AI-Native Development Teams | `Superseded` | `platform` | [ADR-014-ai-native-development-teams.md](ADR-014-ai-native-development-teams.md) |
| 015 | Platform Governance System | `?` | `platform` | [ADR-015-platform-governance-system.md](ADR-015-platform-governance-system.md) |
| 017 | Domain Development Lifecycle (DDL) | `?` | `platform` | [ADR-017-domain-development-lifecycle.md](ADR-017-domain-development-lifecycle.md) |
| 020 | Dokumentationsstrategie — Sphinx, DB-driven, ADR-basiert | `?` | `platform` | [ADR-020-documentation-strategy.md](ADR-020-documentation-strategy.md) |
| 021 | Unified Deployment Architecture | `Accepted` | `platform` | [ADR-021-unified-deployment-pattern.md](ADR-021-unified-deployment-pattern.md) |
| 022 | Platform Consistency Standard (v3) | `?` | `platform` | [ADR-022-platform-consistency-standard.md](ADR-022-platform-consistency-standard.md) |
| 027 | Shared Backend Services | `?` | `shared` | [ADR-027-shared-backend-services.md](ADR-027-shared-backend-services.md) |
| 028 | Platform Context — Konsolidierung der Platform Foundation | `?` | `platform` | [ADR-028-platform-context.md](ADR-028-platform-context.md) |
| 031 | Static Asset Versioning & Landing Page Registry | `?` | `platform` | [ADR-031-static-asset-versioning.md](ADR-031-static-asset-versioning.md) |
| 032 | Domain Development Lifecycle (DDL) | `?` | `platform` | [ADR-032-domain-development-lifecycle.md](ADR-032-domain-development-lifecycle.md) |
| 033 | Dual-Framework-Governance (Django + Odoo) | `?` | `platform` | [ADR-033-dual-framework-governance.md](ADR-033-dual-framework-governance.md) |
| 035 | Shared Django Tenancy Package | `?` | `shared` | [ADR-035-shared-django-tenancy.md](ADR-035-shared-django-tenancy.md) |
| 040 | Frontend Completeness Gate | `?` | `platform` | [ADR-040-frontend-completeness-gate.md](ADR-040-frontend-completeness-gate.md) |
| 041 | Django Component Pattern — Reusable UI Blocks | `?` | `platform` | [ADR-041-django-component-pattern.md](ADR-041-django-component-pattern.md) |
| 042 | Development Environment & Deployment Workflow | `?` | `platform` | [ADR-042-dev-environment-deploy-workflow.md](ADR-042-dev-environment-deploy-workflow.md) |
| 043 | AI-Assisted Development — Context & Workflow Optimization | `?` | `platform` | [ADR-043-ai-assisted-development.md](ADR-043-ai-assisted-development.md) |
| 045 | Secrets & Environment Management | `?` | `platform` | [ADR-045-secrets-management.md](ADR-045-secrets-management.md) |
| 046 | Documentation Governance — Hygiene, DIATAXIS & Docs Agent | `?` | `platform` | [ADR-046-docs-hygiene.md](ADR-046-docs-hygiene.md) |
| 047 | Sphinx Documentation Hub | `?` | `platform` | [ADR-047-sphinx-documentation-hub.md](ADR-047-sphinx-documentation-hub.md) |
| 048 | HTMX Playbook — Canonical Patterns for Django-HTMX | `?` | `platform` | [ADR-048-htmx-playbook.md](ADR-048-htmx-playbook.md) |
| 049 | Design Token System — CSS Custom Properties + Tailwind Bridge | `?` | `platform` | [ADR-049-design-token-system.md](ADR-049-design-token-system.md) |
| 050 | Platform Decomposition — Hub Landscape & Developer Portal | `?` | `platform` | [ADR-050-platform-decomposition-hub-landscape.md](ADR-050-platform-decomposition-hub-landscape.md) |
| 051 | Concept-to-ADR Pipeline — Idea Capture & Promotion Workflow | `?` | `platform` | [ADR-051-concept-to-adr-pipeline.md](ADR-051-concept-to-adr-pipeline.md) |
| 053 | deployment-mcp Robustness — Circuit Breaker, Timeout-Fixes | `?` | `platform` | [ADR-053-deployment-mcp-robustness.md](ADR-053-deployment-mcp-robustness.md) |
| 054 | Deployment Pre-Flight Validation & platform-context als Managed Package | `Draft` | `platform` | [ADR-054-deployment-preflight-validation.md](ADR-054-deployment-preflight-validation.md) |
| 055 | Cross-App Bug & Feature Management | `Accepted` | `platform` | [ADR-055-cross-app-bug-management.md](ADR-055-cross-app-bug-management.md) |
<<<<<<< HEAD
| 056 | Adopt PostgreSQL Schema Isolation for SaaS Multi-Tenancy | `Proposed` | `platform` | [ADR-056-multi-tenancy-schema-isolation.md](ADR-056-multi-tenancy-schema-isolation.md) |
| 058 | Multi-Tenancy Testing Strategy — Isolation, Propagation & CI Gates | `Proposed` | `platform` | [ADR-058-multi-tenancy-testing-strategy.md](ADR-058-multi-tenancy-testing-strategy.md) |
| 059 | Adopt Automated ADR Drift Detection and Staleness Management | `Proposed` | `platform` | [ADR-059-adr-drift-detector.md](ADR-059-adr-drift-detector.md) |
| 060 | Developer Workstation SSH Configuration | `Proposed` | `platform` | [ADR-060-developer-workstation-ssh-configuration.md](ADR-060-developer-workstation-ssh-configuration.md) |
| 061 | Hardcoding Elimination Strategy — Platform-wide | `Proposed` | `platform` | [ADR-061-hardcoding-elimination-strategy.md](ADR-061-hardcoding-elimination-strategy.md) |
=======
| 056 | Deployment Preflight & Pipeline Hardening | `Accepted` | `platform` | [ADR-056-deployment-preflight-and-pipeline-hardening.md](ADR-056-deployment-preflight-and-pipeline-hardening.md) |
| 057 | Platform Test Strategy — 4-Ebenen-Pyramide | `Accepted` | `platform` | [ADR-057-platform-test-strategy.md](ADR-057-platform-test-strategy.md) |
| 058 | Platform Test Taxonomy — 28-Typen-Katalog | `Accepted` | `platform` | [ADR-058-platform-test-taxonomy.md](ADR-058-platform-test-taxonomy.md) |
| 062 | Content Store — Shared PostgreSQL Schema für AI-Inhalte | `Proposed` | `platform` | [ADR-062-content-store-shared-persistence.md](ADR-062-content-store-shared-persistence.md) |
| 064 | Coach-Hub KI ohne Risiko — Row-Level Multi-Tenant SaaS | `Proposed` | `platform` | [ADR-064-coach-hub-ki-ohne-risiko-architecture.md](ADR-064-coach-hub-ki-ohne-risiko-architecture.md) |
| 065 | ADR Numbering — Filesystem-First Vergabe-Strategie | `Accepted` | `platform` | [ADR-065-adr-numbering-filesystem-first.md](ADR-065-adr-numbering-filesystem-first.md) |
| 066 | AI Engineering Squad — Rollenbasierte Agenten + Gate-Workflows | `Proposed` | `platform` | [ADR-066-ai-engineering-team.md](ADR-066-ai-engineering-team.md) |
>>>>>>> 152900e (docs: ADR-062 content-store (reviewed), ADR-065 filesystem-first numbering, ADR-066 ai-engineering-squad + INDEX.md aktualisiert)

### MCP Hub (150–199)

| Nr | Titel | Status | Repo | Datei |
|----|-------|--------|------|-------|
| 023 | Shared Scoring and Routing Engine | `?` | `mcp-hub` | [ADR-023-shared-scoring-routing-engine.md](ADR-023-shared-scoring-routing-engine.md) |
| 044 | MCP-Hub Architecture Consolidation | `?` | `mcp-hub` | [ADR-044-mcp-hub-architecture-consolidation.md](ADR-044-mcp-hub-architecture-consolidation.md) |

### Travel Beat (100–149)

| Nr | Titel | Status | Repo | Datei |
|----|-------|--------|------|-------|
| 016 | Import von Reiseplänen als Trip-Stops | `?` | `travel-beat` | [ADR-016-trip-plan-import.md](ADR-016-trip-plan-import.md) |

### Weltenhub / Story

| Nr | Titel | Status | Repo | Datei |
|----|-------|--------|------|-------|
| 018 | Weltenhub — Zentrale Story-Universe Plattform | `?` | `weltenhub` | [ADR-018-weltenhub-architecture.md](ADR-018-weltenhub-architecture.md) |
| 019 | Weltenhub UI, Templates, Views & APIs | `?` | `weltenhub` | [ADR-019-weltenhub-ui-templates-apis.md](ADR-019-weltenhub-ui-templates-apis.md) |
| 024 | Location-Recherche als Weltenhub-Modul | `?` | `weltenhub` | [ADR-024-recherche-hub-weltenhub-integration.md](ADR-024-recherche-hub-weltenhub-integration.md) |

### CAD Hub (250–299)

| Nr | Titel | Status | Repo | Datei |
|----|-------|--------|------|-------|
| 029 | CAD Hub Extraction from bfagent | `Accepted` | `cad-hub` | [ADR-029-cad-hub-extraction.md](ADR-029-cad-hub-extraction.md) |
| 034 | CAD-Daten ETL-Pipeline + Chat-Agent als Platform-Service | `?` | `cad-hub` | [ADR-034-cad-etl-chat-agent.md](ADR-034-cad-etl-chat-agent.md) |

### bfagent (050–099)

| Nr | Titel | Status | Repo | Datei |
|----|-------|--------|------|-------|
| 036 | Chat-Agent Ecosystem — DomainToolkits, Research Integration | `?` | `bfagent` | [ADR-036-chat-agent-ecosystem.md](ADR-036-chat-agent-ecosystem.md) |
| 037 | Chat Conversation Logging & Quality Management | `?` | `bfagent` | [ADR-037-chat-conversation-logging.md](ADR-037-chat-conversation-logging.md) |
| 065 | bfagent CI Test Strategy | `Accepted` | `bfagent` | [ADR-065-bfagent-ci-test-strategy.md](ADR-065-bfagent-ci-test-strategy.md) |

### Shared / Cross-App (350–399)

| Nr | Titel | Status | Repo | Datei |
|----|-------|--------|------|-------|
| 030 | Erste Odoo Management-App — Dual-Framework-Governance | `?` | `shared` | [ADR-030-odoo-management-app.md](ADR-030-odoo-management-app.md) |
| 038 | DSB-Modul — Externer Datenschutzbeauftragter | `Draft` | `shared` | [ADR-038-dsb-datenschutzbeauftragter-module.md](ADR-038-dsb-datenschutzbeauftragter-module.md) |
| 039 | Seating Drag & Drop Layout-Editor | `?` | `shared` | [ADR-039-seating-drag-drop-layout-editor.md](ADR-039-seating-drag-drop-layout-editor.md) |
| 052 | Trading Hub — Broker-Adapter-Architektur | `?` | `trading-hub` | [ADR-052-trading-hub-broker-adapter-architecture.md](ADR-052-trading-hub-broker-adapter-architecture.md) |

### Trading Hub (400–449)

| Nr | Titel | Status | Repo | Datei |
|----|-------|--------|------|-------|
| 400 | Hybrid-Architektur für Market Scanner Module | `Proposed` | `trading-hub` | [ADR-400-market-scanner-hybrid-architecture.md](ADR-400-market-scanner-hybrid-architecture.md) |
| 401 | Autonomer Trading Bot — Execution-Loop & Bot-Architektur | `Proposed` | `trading-hub` | [ADR-401-autonomous-trading-bot.md](ADR-401-autonomous-trading-bot.md) |

---

## Offene Punkte / Hygiene-Backlog

### ⚠️ Metadaten fehlen (`?`-Status)

Die folgenden ADRs haben keine maschinenlesbaren `**Status**`- und `**Scope**`/`**Repo**`-Felder in der Metadaten-Tabelle. Bei der nächsten Bearbeitung des jeweiligen ADR bitte normalisieren:

- ADR-010 bis ADR-049 (Großteil der Platform-ADRs)
- ADR-052 (Trading Hub — falsche Nummernreihe, gehört in 400er)

### ⚠️ Doppelte Dateien

| Problem | Dateien |
|---------|---------|
| ADR-038 existiert zweimal mit unterschiedlichem Status | `ADR-038-dsb-datenschutzbeauftragter-module.md` (2x) |
| ADR-022 hat ein Amendment als separate Datei | `ADR-022-amendment-code-quality-tooling.md` |

### ⚠️ Review-Dateien als Satelliten

Die folgenden Dateien sind Review-Protokolle, keine eigenständigen ADRs — sollten in ein `reviews/`-Unterverzeichnis oder in den Changelog des jeweiligen ADR integriert werden:

- `ADR-022-REVIEW.md`
- `ADR-023-REVIEW.md`
- `ADR-029-REVIEW.md`
- `ADR-038-REVIEW.md`
- `ADR-038-R3-REVIEW.md`
- `ADR-044-review-deployment-mcp.md`
- `ADR-046-merged-REVIEW.md`

### ⚠️ Nummernkonflikt

ADR-052 (`Trading Hub — Broker-Adapter-Architektur`) liegt in der `platform`-Nummernreihe (001–049), gehört aber zu `trading-hub` (400–449). Empfehlung: Umbenennen zu ADR-402.

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
