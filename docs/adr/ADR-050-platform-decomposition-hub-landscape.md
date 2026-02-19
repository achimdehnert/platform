---
id: ADR-050
title: "Platform Decomposition — Hub Landscape & Developer Portal"
status: proposed
date: 2026-02-19
author: Achim Dehnert
owner: Achim Dehnert
scope: Platform-wide (all repositories)
tags: [architecture, decomposition, multi-tenancy, developer-portal, migration]
related: [ADR-021, ADR-035, ADR-041, ADR-044, ADR-047, ADR-048, ADR-049]
last_verified: 2026-02-19
---

# ADR-050: Platform Decomposition — Hub Landscape & Developer Portal

| Status | Proposed |
| ------ | -------- |
| Date | 2026-02-19 |
| Author | Achim Dehnert |
| Scope | Platform-wide (all repositories) |
| Related | ADR-021 (Unified Deployment), ADR-035 (Shared Tenancy), ADR-038 (DSB Module), ADR-044 (MCP Hub Architecture), ADR-047 (Sphinx Docs Hub) |

## 1. Context

### 1.1 Problem

The `bfagent` repository has grown into an **18-app monolith** mixing
platform-wide infrastructure with domain-specific features:

| Problem | Impact |
| ------- | ------ |
| 18 Django apps in one repo, 786+ lines in single view files | Cognitive overload, slow CI, merge conflicts |
| Platform tools (LLM Config, MCP Dashboard) coupled to Book Factory | Cannot reuse in other apps without importing all of bfagent |
| No consistent multi-tenancy across apps | Some apps have `org_id`, some don't, no shared middleware |
| Domain-specific apps cannot be deployed independently | All-or-nothing deployments |
| No central Developer Portal | Service status, agent results, and docs scattered across repos |
| Deprecated modules still in codebase | MedTrans, GenAgent, PresentationStudio |

### 1.2 Current bfagent Structure

```text
bfagent (monolith — 18 apps):
├── core, bfagent, control_center     # Platform + Book Factory mixed
├── writing_hub (34 files!)            # Book production
├── media_hub                          # ComfyUI / TTS generation
├── expert_hub                         # Explosion protection (ATEX)
├── research                           # Web search + fact checking
├── dlm_hub                            # Documentation lifecycle
├── genagent                           # Phase/Action workflow (legacy)
├── medtrans                           # Medical translation (deprecated)
├── presentation_studio                # PPTX (extracted to pptx-hub)
├── mcp_hub, graph_core, hub           # Various utilities
└── workflow_system, api, sphinx_export # Supporting modules
```

### 1.3 Existing Independent Repositories

Eight repositories already follow the hub pattern but with inconsistent
multi-tenancy and no central management:

`weltenhub`, `risk-hub`, `travel-beat`, `pptx-hub`, `wedding-hub`,
`trading-hub`, `odoo-hub`, `cad-hub`.

## 2. Decision

### 2.1 Three Core Decisions

1. **Decompose bfagent** into purpose-built hub repositories.
2. **Create `dev-hub`** as the central Developer Portal and Management
   platform, inspired by Backstage concepts but implemented in Django.
3. **All hubs are tenant-capable** from day one via shared `tenant_id`
   pattern (ADR-035).

### 2.2 Why Django, Not Backstage

| Criterion | Backstage (Node.js) | Django dev-hub |
| --------- | ------------------- | -------------- |
| Tech stack | TypeScript, React, Express | Python, Django, HTMX, Tailwind |
| Consistency | New stack to maintain | Same stack as all other hubs |
| Agent integration | REST adapter needed (Python → Node) | Native `from agents import guardian` |
| Plugin ecosystem | 200+ plugins (Kubernetes, PagerDuty...) | Not needed for 14 hubs |
| Docker image size | ~500 MB | ~50 MB |
| Team expertise | TypeScript learning curve | Existing Django expertise |
| Deployment | Different pipeline | Same Docker Compose pattern |

**Decision**: Adopt Backstage's **data model and conventions**
(`catalog-info.yaml`, Entity taxonomy) but implement in Django. This
preserves future migration compatibility without the TypeScript overhead.

## 3. Hub Landscape

### 3.1 Repository Map

```text
┌─────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                       │
│                                                              │
│  platform          ADRs, Agents, Shared Packages             │
│  mcp-hub           MCP Server Collection (Orchestrator)      │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────┐
│                    DEVELOPER PORTAL                           │
│                                                              │
│  dev-hub           Central Management & Documentation        │
│                    AI Config · MCP Mgmt · Controlling        │
│                    Agents Dashboard · Health · Catalog        │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST API
     ┌─────────┬───────────┼───────────┬─────────┐
     ▼         ▼           ▼           ▼         ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐
│writing- │ │media-   │ │research-│ │welten-  │ │risk-hub  │
│hub      │ │hub      │ │hub      │ │hub      │ │Schutztat │
│Books    │ │ComfyUI  │ │Brave    │ │Welten-  │ │ExpertHub │
│Prompts  │ │TTS      │ │Facts    │ │forger   │ │DSB       │
│Publish  │ │Assets   │ │Cites    │ │         │ │          │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────┘

┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐
│travel-  │ │pptx-hub │ │wedding- │ │trading- │ │odoo-hub  │
│beat     │ │Präsent. │ │hub      │ │hub      │ │Odoo Mgmt │
│Drift-   │ │         │ │         │ │Market   │ │          │
│Tales    │ │         │ │         │ │Scanner  │ │          │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────┘

┌──────────┐
│cad-hub   │
│CAD/Eng.  │
│          │
└──────────┘
```

### 3.2 Repository Details

| # | Repository | Domain | Tenant | Database | Production URL | Source |
| --- | --------- | ------ | ------ | -------- | -------------- | ------ |
| 1 | `dev-hub` | Developer Portal & Management | ✅ | `devhub_db` | devhub.iil.pet | **NEW** |
| 2 | `writing-hub` | Book Factory (Stories, Prompts, Publishing, Lektorat) | ✅ | `writing_hub_db` | writing.iil.pet | **NEW** (ex-bfagent) |
| 3 | `media-hub` | Media Generation (ComfyUI, TTS, Assets) | ✅ | `media_hub_db` | media.iil.pet | **NEW** (ex-bfagent) |
| 4 | `research-hub` | Research (Brave Search, Facts, Citations) | ✅ | `research_hub_db` | research.iil.pet | **NEW** (ex-bfagent) |
| 5 | `weltenhub` | Story Universe Platform (Weltenforger) | ✅ | `weltenhub_db` | weltenforger.com | Exists |
| 6 | `risk-hub` | Compliance & Safety (Schutztat + Expert Hub + DSB) | ✅ | `risk_hub_db` | schutztat.de | Exists |
| 7 | `travel-beat` | Travel Story Platform (DriftTales) | ✅ | `travel_beat_db` | drifttales.app | Exists |
| 8 | `pptx-hub` | Presentation Studio | ✅ | `pptx_hub_db` | pptx.iil.pet | Exists |
| 9 | `wedding-hub` | Wedding Planning | ✅ | `wedding_hub_db` | wedding.iil.pet | Exists |
| 10 | `trading-hub` | Trading / Market Scanner | ✅ | `trading_hub_db` | trading.iil.pet | Exists |
| 11 | `odoo-hub` | Odoo Management | ✅ | `odoo_hub_db` | odoo.iil.pet | Exists |
| 12 | `cad-hub` | CAD / Engineering | ✅ | `cad_hub_db` | cad.iil.pet | Exists |
| — | `platform` | ADRs, Agents, Shared Packages | — | — | — | Infra |
| — | `mcp-hub` | MCP Server Collection | — | — | — | Infra |

### 3.3 Inter-Hub Communication

```text
writing-hub  ──REST──►  media-hub       Book cover rendering
weltenhub    ──REST──►  media-hub       Character portraits
writing-hub  ──REST──►  research-hub    Fact-checking for books
dev-hub      ──REST──►  all hubs        Health checks, catalog sync
all hubs     ──REST──►  dev-hub         LLM config, agent results
```

All inter-hub calls use **REST API** with:

- JWT token authentication (tenant-aware)
- API versioning (`/api/v1/`)
- DRF Spectacular for schema generation

## 4. dev-hub Architecture

### 4.1 App Structure

```text
dev-hub/
├── config/
│   └── settings/
│       ├── base.py                  # Django 5.x, HTMX, Tailwind
│       ├── development.py
│       └── production.py
├── apps/
│   ├── core/                        # Base models, HTMX mixins, SSE
│   │   ├── middleware.py            # TenantMiddleware
│   │   ├── mixins.py               # HTMXResponseMixin (from bfagent)
│   │   └── models.py               # TenantAwareModel (abstract)
│   ├── catalog/                     # Service Catalog
│   │   ├── models.py               # Component, API, System, Resource
│   │   └── importers.py            # catalog-info.yaml → DB sync
│   ├── techdocs/                    # ADR Browser + Sphinx Integration
│   ├── agents_dashboard/            # Platform Agents UI
│   ├── ai_config/                   # LLM + Agent CRUD (from bfagent)
│   ├── mcp_management/              # MCP Server Management (from bfagent)
│   ├── controlling/                 # Usage, Costs, Alerts (from bfagent)
│   ├── health/                      # Server, Container, DB Health
│   └── onboarding/                  # Onboarding Coach Web UI
├── templates/                       # Tailwind + HTMX
├── docker-compose.prod.yml
├── catalog-info.yaml                # Self-describing
└── Dockerfile
```

### 4.2 Service Catalog — Backstage Entity Model

dev-hub adopts Backstage's entity taxonomy as Django models:

```python
class Component(TenantAwareModel):
    """A software component (service, website, library)."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=50)  # service, website, library
    lifecycle = models.CharField(max_length=50)  # production, experimental
    owner = models.CharField(max_length=200)
    system = models.ForeignKey("System", on_delete=models.SET_NULL, null=True)
    repo_url = models.URLField(blank=True)
    provides_apis = models.ManyToManyField("API", blank=True)
    depends_on = models.ManyToManyField("self", blank=True)


class API(TenantAwareModel):
    """An API provided by a component."""
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=50)  # openapi, grpc, graphql
    definition_url = models.URLField(blank=True)
    owner = models.CharField(max_length=200)


class System(TenantAwareModel):
    """A collection of components forming a system."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.CharField(max_length=200)
    domain = models.CharField(max_length=200)
```

Each repository contains a `catalog-info.yaml`:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: weltenhub
  description: Story Universe Platform (Weltenforger)
  tags: [django, htmx, tailwind]
  annotations:
    github.com/project-slug: achimdehnert/weltenhub
spec:
  type: service
  lifecycle: production
  owner: achim
  system: content-platform
  providesApis:
    - weltenhub-api
  dependsOn:
    - resource:weltenhub-db
    - resource:weltenhub-redis
```

### 4.3 Features Migrated from bfagent Control Center

| bfagent Module | dev-hub App | Key Features |
| -------------- | ----------- | ------------ |
| `views_ai_config.py` | `ai_config` | LLM CRUD, Agent CRUD, Live Test |
| `views_mcp.py` | `mcp_management` | MCP Domains, Sessions, SSE Real-time |
| `views_hub_management.py` | `catalog` | Hub Registry, Feature Flags, Event Bus |
| `views_controlling.py` | `controlling` | LLM Usage, Orchestration Logs, Alerts |
| `HTMXResponseMixin` | `core.mixins` | Partial rendering, OOB Swaps, Toasts |
| `MCPSessionSSEView` | `core.mixins` | Server-Sent Events pattern |
| `tool_registry` | `core` | Tool registration + execution + health |

## 5. Multi-Tenancy Standard

### 5.1 Base Model

Every hub uses the same abstract base model:

```python
import uuid
from django.db import models


class TenantAwareModel(models.Model):
    """Abstract base for all tenant-scoped models."""
    tenant_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### 5.2 TenantMiddleware

```python
class TenantMiddleware:
    """Sets request.tenant_id from subdomain or header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Priority: X-Tenant-ID header > subdomain > default
        tenant_id = (
            request.headers.get("X-Tenant-ID")
            or self._resolve_from_subdomain(request)
            or settings.DEFAULT_TENANT_ID
        )
        request.tenant_id = uuid.UUID(tenant_id)
        return self.get_response(request)
```

### 5.3 Query Filter Rule

**CRITICAL**: All queries MUST filter by `tenant_id`:

```python
# ✅ Correct
projects = Project.objects.filter(tenant_id=request.tenant_id)

# ❌ NEVER — exposes cross-tenant data
projects = Project.objects.all()
```

The Architecture Guardian agent (A2) enforces this via rule G-003.

## 6. Deployment Pattern

Every hub follows ADR-021 (Unified Deployment):

```text
Hub Repository
├── docker-compose.prod.yml      # Web + DB + Redis + Celery
├── .env.prod                    # env_file (NEVER ${VAR} interpolation)
├── docker/app/Dockerfile        # or Dockerfile at root
├── catalog-info.yaml            # Backstage-compatible service descriptor
└── .github/workflows/
    ├── ci.yml                   # Tests + Lint
    └── deploy.yml               # Build → GHCR → Pull → Up
```

Infrastructure:

- **Server**: Hetzner VM `88.198.191.108`
- **Reverse Proxy**: Nginx + Let's Encrypt TLS
- **Registry**: `ghcr.io/achimdehnert/<hub>:latest`
- **Database**: PostgreSQL 16 (one database per hub)
- **Cache/Broker**: Redis 7

## 7. bfagent Migration Plan

### 7.1 Migration Phases

| Phase | What | Target | Priority |
| ----- | ---- | ------ | -------- |
| **M0** | Deprecate MedTrans, GenAgent, PresentationStudio | Remove from bfagent | Immediate |
| **M1** | Create `dev-hub` with core + catalog + health | New repo | High |
| **M2** | Migrate AI Config, MCP Dashboard, Controlling → dev-hub | dev-hub apps | High |
| **M3** | Extract Writing Hub → `writing-hub` | New repo | Medium |
| **M4** | Extract Media Hub → `media-hub` | New repo | Medium |
| **M5** | Extract Research → `research-hub` | New repo | Medium |
| **M6** | Migrate Expert Hub + DSB → `risk-hub` | Existing repo | Medium |
| **M7** | Migrate DLM Hub → dev-hub `techdocs` | dev-hub app | Low |
| **M8** | Archive `bfagent` repository | GitHub archive | Final |

### 7.2 Migration Strategy Per Module

For each module extraction:

1. **Create target repo** with Django skeleton + Docker + CI
2. **Copy models** with fresh migrations (no migration history)
3. **Data migration** via `pg_dump` / `pg_restore` of relevant tables
4. **Adapt views** to follow current patterns (Service Layer, HTMX)
5. **Add `catalog-info.yaml`** for service catalog registration
6. **Deploy** and verify with health checks
7. **Deprecate** in bfagent (redirect or remove)

### 7.3 bfagent Deprecated Modules

| Module | Reason | Action |
| ------ | ------ | ------ |
| `medtrans` | Migrated to prezimo | Remove immediately |
| `genagent` | Replaced by MCP Orchestrator (`mcp-hub`) | Remove immediately |
| `presentation_studio` | Extracted to `pptx-hub` | Remove immediately |

## 8. Shared Infrastructure

### 8.1 platform Repository

Remains the home for:

- **ADRs** (`docs/adr/`)
- **Platform Agents** (`agents/` — Guardian, Drift Detector, ADR Scribe, Onboarding Coach, Context Reviewer)
- **Shared Packages** (`packages/platform-context`, `packages/docs-agent`)
- **CI/CD Workflows** (`.github/workflows/`)

### 8.2 mcp-hub Repository

Remains the home for:

- **MCP Servers** (deployment, orchestrator, LLM, database, filesystem, etc.)
- **Orchestrator** with `AGENT_GATE_MAP` for all platform agents

### 8.3 Shared Python Package

`platform-context` (already exists in `platform/packages/platform-context/`)
is extended with:

- `TenantAwareModel` abstract base
- `TenantMiddleware`
- `HTMXResponseMixin` (extracted from bfagent)
- Common API authentication utilities

## 9. Consequences

### 9.1 Positive

- **Clear ownership**: Each hub has a single purpose and independent lifecycle
- **Independent deployment**: Update writing-hub without touching risk-hub
- **Consistent multi-tenancy**: `tenant_id` on every model, enforced by Guardian
- **Central management**: dev-hub provides single pane of glass for all hubs
- **Smaller codebases**: Faster CI, easier onboarding, fewer merge conflicts
- **API-first**: Hubs communicate via REST, enabling future microservice scaling

### 9.2 Negative

- **More repositories**: 14 hubs + 2 infra = 16 repos to manage
- **Migration effort**: Extracting from bfagent requires careful data migration
- **Cross-hub queries**: No direct DB joins; must use API calls
- **Shared package versioning**: platform-context changes affect all hubs

### 9.3 Risks

| Risk | Mitigation |
| ---- | ---------- |
| Data loss during migration | `pg_dump` backups before every migration step |
| Inconsistent patterns across hubs | ADR-050 defines standards, Guardian enforces |
| API latency for cross-hub calls | Cache frequently accessed data, async where possible |
| Too many repos for small team | dev-hub Service Catalog provides central overview |

## 10. Implementation Priority

```text
Phase 1 (Immediate):
  ├── ADR-050 ✅ (this document)
  ├── Create dev-hub repo + Django skeleton
  ├── Implement core app (HTMX Mixins, TenantMiddleware)
  └── Implement health app (Server/Container status)

Phase 2 (Short-term):
  ├── Migrate AI Config → dev-hub
  ├── Migrate MCP Dashboard → dev-hub
  ├── Implement Service Catalog with catalog-info.yaml
  └── Add catalog-info.yaml to all existing repos

Phase 3 (Medium-term):
  ├── Extract writing-hub from bfagent
  ├── Extract media-hub from bfagent
  ├── Extract research-hub from bfagent
  └── Migrate Expert Hub + DSB → risk-hub

Phase 4 (Final):
  ├── Migrate DLM Hub → dev-hub techdocs
  ├── Remove deprecated modules from bfagent
  └── Archive bfagent repository
```
