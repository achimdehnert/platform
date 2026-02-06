# BF Agent Platform — Architecture Documentation

| Key | Value |
|-----|-------|
| **Version** | 1.0.0 |
| **Updated** | 2026-02-06 |
| **Repo** | achimdehnert/platform |

---

## 1. Overview

The **Platform** repository is the shared mono-repo for the BF Agent ecosystem.
It contains reusable Python packages, deployment concepts, infrastructure code,
ADRs, and documentation tooling consumed by all downstream apps.

### 1.1 Ecosystem

```text
                    ┌─────────────────────┐
                    │     platform/       │  ← This repo
                    │  (packages, ADRs,   │
                    │   docs, concepts)   │
                    └────────┬────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
  ┌───────────┐      ┌─────────────┐      ┌──────────────┐
  │  bfagent  │      │ travel-beat │      │  weltenhub   │
  │ (Django)  │      │  (Django)   │      │  (Django)    │
  └───────────┘      └─────────────┘      └──────────────┘
  Book Writing        Travel Stories       Story Universes
  bfagent.iil.pet     travel-beat.iil.pet  weltenforger.com
```

### 1.2 Additional Repos

| Repo | Purpose | URL |
|------|---------|-----|
| `mcp-hub` | MCP Server Collection | mcp-hub.iil.pet |
| `cad-hub` | CAD Document Processing | cadhub.iil.pet |

---

## 2. Repository Structure

```text
platform/
├── packages/                      # Shared Python packages
│   ├── creative-services/         # LLM client, adapters, generators
│   ├── bfagent-core/              # Core abstractions
│   ├── bfagent-llm/               # LLM utilities
│   ├── cad-services/              # CAD processing
│   ├── sphinx-export/             # Sphinx → Markdown export
│   ├── adr-review/                # ADR review tooling
│   └── inception-mcp/             # MCP server for inception
├── concepts/                      # Architecture concepts & proposals
│   ├── PLATFORM_ARCHITECTURE_MASTER.md
│   ├── cad-services-architecture.md
│   ├── deployment-architecture/
│   ├── illustration services/
│   └── pptx-hub/
├── docs/                          # Sphinx documentation projects
│   ├── adr/                       # All ADRs (007–019)
│   ├── governance/                # DDL Governance Sphinx docs
│   ├── concepts/
│   └── reviews/
├── governance-deploy/             # Standalone governance Django app
├── admin/                         # Static admin panel (HTML/JS)
├── landing/                       # Landing page assets
├── templates/                     # Shared templates
└── scripts/                       # Utility scripts
```

---

## 3. Packages

### 3.1 creative-services

Shared LLM client library with provider abstraction and usage tracking.

```text
creative_services/
├── core/         # LLMClient, LLMRegistry, UsageTracker
├── adapters/     # Django, BFAgent integration adapters
├── character/    # Character generation services
├── scene/        # Scene generation services
├── story/        # Story generation services
├── world/        # World building services
└── prompts/      # Prompt templates
```

**Install**: `pip install -e packages/creative-services`

### 3.2 sphinx-export

Django app + CLI for converting Sphinx documentation to single Markdown files.

| Component | Purpose |
|-----------|---------|
| `export_service.py` | Core Sphinx → Markdown conversion |
| `sphinx_converter.py` | RST feature converter (autodoc, tables) |
| `sync_service.py` | Bidirectional sync (Sphinx ↔ Markdown) |
| `views.py` | Django views for web-based export |
| `management/commands/` | `sphinx_to_markdown` CLI command |

### 3.3 bfagent-core

Core abstractions and base classes shared across BF Agent apps.

### 3.4 inception-mcp

MCP server for the inception workflow — AI-driven requirements gathering
through structured conversations.

---

## 4. Governance System (ADR-017)

### 4.1 Architecture

The DDL (Domain Development Lifecycle) governance system tracks Business Cases,
Use Cases, and ADRs in PostgreSQL with a fully database-driven lookup pattern.

```text
lkp_domain → lkp_choice
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
dom_business    dom_use       dom_adr
   _case         _case
    │             │             │
    └──────┐      │      ┌─────┘
           ▼      ▼      ▼
         dom_review  dom_status_history
```

### 4.2 Database Schema (platform schema)

| Table | Model | Purpose |
|-------|-------|---------|
| `platform.lkp_domain` | LookupDomain | Choice categories |
| `platform.lkp_choice` | LookupChoice | Choice values (status, priority, etc.) |
| `platform.dom_business_case` | BusinessCase | Feature/change requests |
| `platform.dom_use_case` | UseCase | User interaction specs |
| `platform.dom_adr` | ADR | Architecture Decision Records |
| `platform.dom_adr_use_case` | ADRUseCaseLink | M:N links |
| `platform.dom_conversation` | Conversation | Inception dialogs |
| `platform.dom_review` | Review | Approval workflow |
| `platform.dom_status_history` | StatusHistory | Audit trail |

### 4.3 Key Principle: No Hardcoded Enums

All status, category, priority, and type fields reference `lkp_choice`
via foreign key. New values are added via DB insert, not code changes.

### 4.4 Deployments

| Variant | Path | Purpose |
|---------|------|---------|
| `governance-deploy/` | Standalone Django app | Dedicated governance instance |
| `apps/governance/` in weltenhub | Integrated app | Shared with weltenhub |

---

## 5. ADR Registry

| ADR | Title | Scope |
|-----|-------|-------|
| ADR-007 | Final Production Architecture | Infrastructure |
| ADR-008 | Infrastructure & Deployment | Hetzner, Docker |
| ADR-009 | IFC/DXF Processing | CAD services |
| ADR-010 | 3D Viewer Strategy | CAD frontend |
| ADR-012 | MCP Quality Standards | MCP servers |
| ADR-013 | Team Organization & MCP Ownership | Organization |
| ADR-014 | AI-Native Development Teams | AI workflows |
| ADR-015 | Platform Governance System | Lookup pattern |
| ADR-016 | Trip Plan Import | Travel-beat |
| ADR-017 | Domain Development Lifecycle | DDL system |
| ADR-018 | Weltenhub Architecture | Story platform |
| ADR-019 | Weltenhub UI, Templates, APIs | Frontend |

---

## 6. Documentation Infrastructure

### 6.1 Existing Sphinx Setup

Location: `docs/governance/`

- `conf.py` — Sphinx config with RTD theme, MyST parser, Napoleon
- `index.rst` — Table of contents
- Sections: overview, architecture, deployment, api, database

### 6.2 Sphinx Extensions

| Extension | Purpose |
|-----------|---------|
| `sphinx.ext.autodoc` | Auto-generate from docstrings |
| `sphinx.ext.viewcode` | Link to source code |
| `sphinx.ext.napoleon` | Google/NumPy docstring support |
| `myst_parser` | Markdown support in Sphinx |

---

## 7. Infrastructure

### 7.1 Shared Server

All apps run on a single Hetzner VM (`88.198.191.108`) with:

- **Traefik**: Reverse proxy, TLS termination
- **PostgreSQL 16**: Shared database (`bfagent_db` container)
- **Redis 7**: Shared cache/broker (`bfagent_redis` container)
- **Docker Compose**: Per-app compose files
- **Network**: `bf_platform_prod` (external Docker network)

### 7.2 App Deployment Map

| App | Port | Domain | Path |
|-----|------|--------|------|
| bfagent | 8000 | bfagent.iil.pet | /opt/bfagent-app |
| travel-beat | 8002 | travel-beat.iil.pet | /opt/travel-beat |
| weltenhub | 8081 | weltenforger.com | /opt/weltenhub |
| mcp-hub | 8003 | mcp-hub.iil.pet | /opt/mcp-hub |
| cad-hub | 8004 | cadhub.iil.pet | /opt/cad-hub |
