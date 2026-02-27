# Architecture Decision Records — Index

> **Last updated:** 2026-02-27  
> **Next free ADR number:** 095

## Legend

| Status | Bedeutung |
|--------|-----------|
| `Proposed` | Vorgeschlagen, noch nicht akzeptiert |
| `Accepted` | Akzeptiert und gültig |
| `Deprecated` | Veraltet, ersetzt durch neueres ADR |
| `Superseded` | Vollständig ersetzt |
| `Archived` | In `_archive/superseded/` verschoben — nicht mehr aktiv |

| Repository | Kürzel |
|-----------|--------|
| platform | `platform` |
| bfagent | `bfagent` |
| risk-hub | `risk-hub` |
| weltenhub | `weltenhub` |
| travel-beat | `travel-beat` |
| mcp-hub | `mcp-hub` |
| wedding-hub | `wedding-hub` |
| pptx-hub | `pptx-hub` |
| cad-hub | `cad-hub` |
| coach-hub | `coach-hub` |
| trading-hub | `trading-hub` |

---

## ADR Index

> Alle Links zeigen auf die echten Dateien im Filesystem. Generiert via `scripts/adr_next_number.py`.

| # | Title | Status | Link |
|---|-------|--------|------|
| 007 | Tenant- & RBAC-Architektur (Production Ready) | `Accepted` | [ADR-007](ADR-007-FINAL-PRODUCTION.md) |
| 008 | Infrastructure Services & Self-Healing Deployment | `Deprecated` | [ADR-008](ADR-008-INFRASTRUCTURE.md) |
| 009 | Platform Architecture — Optimized | `Deprecated` | [ADR-009](ADR-009-PLATFORM-ARCHITECTURE-OPTIMIZED.md) |
| 010 | MCP Tool Governance — Specification Standard, Service Discovery | `Accepted` | [ADR-010](ADR-010-mcp-tool-governance.md) |
| 012 | MCP Server Quality Standards | `Accepted` | [ADR-012](ADR-012-mcp-quality-standards.md) |
| 013 | Team Organization & MCP Ownership | `Deprecated` | [ADR-013](ADR-013-team-organization-mcp-ownership.md) |
| 014 | AI-Native Development Teams | `Accepted` | [ADR-014](ADR-014-ai-native-development-teams.md) |
| 015 | Platform Governance System | `Accepted` | [ADR-015](ADR-015-platform-governance-system.md) |
| 016 | Import von Reiseplänen als Trip-Stops | `Archived` | [ADR-016](_archive/superseded/ADR-016-trip-plan-import.md) |
| 017 | Domain Development Lifecycle (DDL) | `Superseded` | [ADR-017](ADR-017-domain-development-lifecycle.md) |
| 018 | Weltenhub — Zentrale Story-Universe Plattform | `Archived` | [ADR-018](_archive/superseded/ADR-018-weltenhub-architecture.md) |
| 019 | Weltenhub UI, Templates, Views & APIs | `Archived` | [ADR-019](_archive/superseded/ADR-019-weltenhub-ui-templates-apis.md) |
| 020 | Dokumentationsstrategie — Sphinx, DB-driven, ADR-basiert | `Superseded` | [ADR-020](ADR-020-documentation-strategy.md) |
| 021 | Unified Single-Service Deployment Pipeline | `Accepted` | [ADR-021](ADR-021-unified-deployment-pattern.md) |
| 022 | Platform Consistency Standard (v3) | `Accepted` | [ADR-022](ADR-022-platform-consistency-standard.md) |
| 023 | Shared Scoring and Routing Engine | `Deprecated` | [ADR-023](ADR-023-shared-scoring-routing-engine.md) |
| 024 | Location-Recherche als Weltenhub-Modul | `Archived` | [ADR-024](_archive/superseded/ADR-024-recherche-hub-weltenhub-integration.md) |
| 027 | Shared Backend Services für Django-Projekte | `Accepted` | [ADR-027](ADR-027-shared-backend-services.md) |
| 028 | Platform Context — Konsolidierung der Platform Foundation | `Accepted` | [ADR-028](ADR-028-platform-context.md) |
| 029 | CAD Hub Extraction from bfagent | `Archived` | [ADR-029](_archive/superseded/ADR-029-cad-hub-extraction.md) |
| 030 | Erste Odoo Management-App — Dual-Framework-Governance | `Accepted` | [ADR-030](ADR-030-odoo-management-app.md) |
| 031 | Static Asset Versioning & Landing Page Registry | `Accepted` | [ADR-031](ADR-031-static-asset-versioning.md) |
| 032 | Domain Development Lifecycle (DDL) | `Deprecated` | [ADR-032](ADR-032-domain-development-lifecycle.md) |
| 033 | Dual-Framework-Governance (Django + Odoo) | `Superseded` | [ADR-033](ADR-033-dual-framework-governance.md) |
| 034 | CAD-Daten ETL-Pipeline + Chat-Agent als Platform-Service | `Archived` | [ADR-034](_archive/superseded/ADR-034-cad-etl-chat-agent.md) |
| 035 | Shared Django Tenancy Package | `Accepted` | [ADR-035](ADR-035-shared-django-tenancy.md) |
| 036 | Chat-Agent Ecosystem — DomainToolkits, Research Integration | `Accepted` | [ADR-036](ADR-036-chat-agent-ecosystem.md) |
| 037 | Chat Conversation Logging & Quality Management | `Accepted` | [ADR-037](ADR-037-chat-conversation-logging.md) |
| 038 | DSB Datenschutzbeauftragter Module | `Archived` | [ADR-038](_archive/superseded/ADR-038-dsb-datenschutzbeauftragter-module.md) |
| 039 | Seating Drag & Drop Layout-Editor | `Archived` | [ADR-039](_archive/superseded/ADR-039-seating-drag-drop-layout-editor.md) |
| 040 | Frontend Completeness Gate | `Accepted` | [ADR-040](ADR-040-frontend-completeness-gate.md) |
| 041 | Django Component Pattern — Reusable UI Blocks | `Accepted` | [ADR-041](ADR-041-django-component-pattern.md) |
| 042 | Development Environment & Deployment Workflow | `Accepted` | [ADR-042](ADR-042-dev-environment-deploy-workflow.md) |
| 043 | AI-Assisted Development — Context & Workflow Optimization | `Accepted` | [ADR-043](ADR-043-ai-assisted-development.md) |
| 044 | MCP-Hub Architecture Consolidation | `Accepted` | [ADR-044](ADR-044-mcp-hub-architecture-consolidation.md) |
| 045 | Secrets & Environment Management | `Accepted` | [ADR-045](ADR-045-secrets-management.md) |
| 046 | Documentation Governance — Hygiene, DIATAXIS & Docs Agent | `Accepted` | [ADR-046](ADR-046-docs-hygiene.md) |
| 047 | Sphinx Documentation Hub (sphinx.iil.pet) | `Superseded` | [ADR-047](ADR-047-sphinx-documentation-hub.md) |
| 048 | HTMX Playbook — Canonical Patterns for Django-HTMX | `Accepted` | [ADR-048](ADR-048-htmx-playbook.md) |
| 049 | Design Token System — CSS Custom Properties + Tailwind Bridge | `Accepted` | [ADR-049](ADR-049-design-token-system.md) |
| 050 | Platform Decomposition — Hub Landscape & Developer Portal | `Accepted` | [ADR-050](ADR-050-platform-decomposition-hub-landscape.md) |
| 051 | Concept-to-ADR Pipeline — Idea Capture & AI-Assisted Promotion | `Accepted` | [ADR-051](ADR-051-concept-to-adr-pipeline.md) |
| 052 | Trading Hub — Broker-Adapter-Architektur | `Archived` | [ADR-052](_archive/superseded/ADR-052-trading-hub-broker-adapter-architecture.md) |
| 053 | deployment-mcp Robustness — Circuit Breaker & Timeout-Fixes | `Superseded` | [ADR-053](ADR-053-deployment-mcp-robustness.md) |
| 054 | Deployment Pre-Flight Validation & platform-context | `Superseded` | [ADR-054](ADR-054-deployment-preflight-validation.md) |
| 055 | Cross-App Bug & Feature Management | `Accepted` | [ADR-055](ADR-055-cross-app-bug-management.md) |
| 056 | Deployment Pre-Flight Validation & Pipeline Hardening | `Accepted` | [ADR-056](ADR-056-deployment-preflight-and-pipeline-hardening.md) |
| 057 | Four-Level Test Strategy with Contract Testing | `Accepted` | [ADR-057](ADR-057-platform-test-strategy.md) |
| 058 | 28-Type Test Taxonomy as Platform Binding Standard | `Accepted` | [ADR-058](ADR-058-platform-test-taxonomy.md) |
| 059 | Automated ADR Drift Detection and Staleness Management | `Accepted` | [ADR-059](ADR-059-adr-drift-detector.md) |
| 060 | Developer Workstation SSH Key Configuration Standard | `Accepted` | [ADR-060](ADR-060-developer-workstation-ssh-configuration.md) |
| 061 | Adopt hardcode_scanner.py as Platform-wide Tooling | `Accepted` | [ADR-061](ADR-061-hardcoding-elimination-strategy.md) |
| 062 | Shared PostgreSQL Schema `content_store` for AI-generated Content | `Accepted` | [ADR-062](ADR-062-content-store-shared-persistence.md) |
| 063 | Staging Environment Strategy | `Accepted` | [ADR-063](ADR-063-staging-environment-strategy.md) |
| 064 | coach-hub „KI ohne Risiko™" Architecture | `Archived` | [ADR-064](_archive/superseded/ADR-064-coach-hub-ki-ohne-risiko-architecture.md) |
| 065 | Filesystem-first ADR Numbering — max(existing) + 1 | `Accepted` | [ADR-065](ADR-065-adr-numbering-filesystem-first.md) |
| 066 | AI Engineering Squad with Role-based Agents | `Accepted` | [ADR-066](ADR-066-ai-engineering-team.md) |
| 067 | GitHub Issues + Projects as Single Source of Truth | `Accepted` | [ADR-067](ADR-067-work-management-strategy.md) |
| 068 | Adaptive Model Routing and Quality Feedback Loop | `Accepted` | [ADR-068](ADR-068-adaptive-model-routing.md) |
| 069 | Web Intelligence MCP — Plattformweiter Web-Zugriff | `Accepted` | [ADR-069](ADR-069-web-intelligence-mcp.md) |
| 070 | Progressive Autonomy Pattern für den Developer-Agenten | `Accepted` | [ADR-070](ADR-070-progressive-autonomy-developer-agent.md) |
| 071 | Amendment: Code Quality Tooling (amends ADR-022) | `Accepted` | [ADR-071](ADR-071-amendment-code-quality-tooling.md) |
| 072 | PostgreSQL Schema Isolation for SaaS Multi-Tenancy | `Accepted` | [ADR-072](ADR-072-multi-tenancy-schema-isolation.md) |
| 073 | Repo Scope & Migration Status (all 10 repos) | `Accepted` | [ADR-073](ADR-073-repo-scope.md) |
| 074 | Multi-Tenancy Testing Strategy — Isolation, Propagation & CI | `Accepted` | [ADR-074](ADR-074-multi-tenancy-testing-strategy.md) |
| 075 | Split Deployment Execution: Read-only MCP + Server-side Writes | `Accepted` | [ADR-075](ADR-075-deployment-execution-strategy.md) |
| 076 | bfagent CI Test Strategy | `Archived` | [ADR-076](_archive/superseded/ADR-076-bfagent-ci-test-strategy.md) |
| 077 | Infrastructure Context System: catalog-info.yaml → dev-hub API | `Accepted` | [ADR-077](ADR-077-infrastructure-context-system.md) |
| 078 | Amendment: Docker HEALTHCHECK ausschließlich in docker-compose | `Accepted` | [ADR-078](ADR-078-amendment-docker-healthcheck-convention.md) |
| 079 | Adopt Temporal Self-Hosted as Primary Durable Workflow Engine | `Accepted` | [ADR-079](ADR-079-temporal-workflow-engine.md) |
| 080 | Multi-Agent Coding Team Pattern | `Accepted` | [ADR-080](ADR-080-multi-agent-coding-team-pattern.md) |
| 081 | Agent Guardrails & Code Safety — Scope-Lock, Pre/Post-Gates | `Accepted` | [ADR-081](ADR-081-agent-guardrails-code-safety.md) |
| 082 | LLM Tool Integration — Autonomous Coding Agent | `Accepted` | [ADR-082](ADR-082-llm-tool-integration-autonomous-coding.md) |
| 083 | Hybrid ADR Governance — Platform + Repo-lokale ADRs | `Accepted` | [ADR-083](ADR-083-hybrid-adr-governance.md) |
| 084 | Model Registry — Dynamisches LLM-Modell-Routing | `Accepted` | [ADR-084](ADR-084-model-registry-dynamic-llm-routing.md) |
| 085 | Use Case Pipeline — Natural Language → Structured TaskGraph | `Accepted` | [ADR-085](ADR-085-use-case-pipeline-nl-to-taskgraph.md) |
| 086 | Agent Team Workflow — Cross-Repo Sprint Execution Pattern | `Accepted` | [ADR-086](ADR-086-agent-team-workflow.md) |
| 087 | Hybrid Search: pgvector + FTS Platform-wide | `Accepted` | [ADR-087](ADR-087-hybrid-search-architecture.md) |
| 088 | Shared Notification Registry — Multi-Channel Messaging | `Accepted` | [ADR-088](ADR-088-notification-registry.md) |
| 089 | bfagent-llm — LiteLLM-Backend + DB-driven Model-Routing | `Accepted` | [ADR-089](ADR-089-bfagent-llm-litellm-db-driven-architecture.md) |
| 090 | Abstract CI/CD Pipeline — Python + PostgreSQL → Docker Deploy | `Accepted` | [ADR-090](ADR-090-cicd-pipeline-python-postgres.md) |
| 091 | Shared Backend Services Library für Django-Projekte | `Accepted` | [ADR-091](ADR-091-shared-backend-services.md) |
| 092 | Tenant-Aware Seed Commands | `Accepted` | [ADR-092](ADR-092-tenant-aware-seed-commands.md) |
| 093 | AI Config App | `Accepted` | [ADR-093](ADR-093-ai-config-app.md) |
| 094 | AI Context Defense-in-Depth — 4-Layer RAP Architecture | `Accepted` | [ADR-094](ADR-094-ai-context-defense-in-depth.md) |

## Gaps (intentional — deleted/archived ADRs)

> Lücken werden nie wiederverwendet (ADR-065). Folgende Nummern sind permanent frei:  
> ADR-001 bis ADR-006 (pre-filesystem era), ADR-011, ADR-025, ADR-026  
> Archivierte ADRs (016, 018, 019, 024, 029, 034, 038, 039, 052, 064, 076, 400, 401): siehe `_archive/superseded/`

---

## Open Points / Hygiene Backlog

- [x] ADR-054 (Deployment Pre-Flight): `Superseded` by ADR-056 ✅
- [x] ADR-083 (Hybrid ADR Governance): `Accepted` ✅
- [x] ADR-091 (Shared Backend Services): `Accepted` ✅
- [x] ADRs archiviert (016, 018, 019, 024, 029, 034, 038, 039, 052, 064, 076, 400, 401): in `_archive/superseded/` verschoben ✅
- [x] ADR-063 (Staging): `Accepted` — Branch-basiertes Staging, Port-Offset +100, Q2–Q4 2026 ✅
- [x] ADR-094 (AI Context Defense-in-Depth): `Accepted` — 4 Layer vollständig implementiert ✅
