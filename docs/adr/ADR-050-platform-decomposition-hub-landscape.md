---
id: ADR-050
title: "Platform Decomposition — Hub Landscape & Developer Portal"
status: accepted
date: 2026-02-19
author: Achim Dehnert
owner: Achim Dehnert
scope: Platform-wide (all repositories)
tags: [architecture, decomposition, multi-tenancy, developer-portal, migration]
related: [ADR-021, ADR-035, ADR-041, ADR-044, ADR-047, ADR-048, ADR-049, ADR-054]
last_verified: 2026-02-19
implementation_status: implemented
implementation_evidence:
  - "29 repos: hub landscape decomposed per ADR-050"
---

# ADR-050: Platform Decomposition — Hub Landscape & Developer Portal

| Status | Proposed |
| ------ | -------- |
| Date | 2026-02-19 |
| Author | Achim Dehnert |
| Scope | Platform-wide (all repositories) |
| Related | ADR-021 (Unified Deployment), ADR-035 (Shared Tenancy), ADR-038 (DSB), ADR-044 (MCP Hub), ADR-048 (HTMX Playbook), ADR-054 (Platform Agents) |

## 1. Context

### 1.1 Problem

The `bfagent` repository has grown into an **18-app monolith** mixing
platform-wide infrastructure with domain-specific features:

| Problem | Impact |
| ------- | ------ |
| 18 Django apps in one repo, 786+ lines in single view files | Cognitive overload, slow CI, merge conflicts |
| Platform tools (LLM Config, MCP Dashboard) coupled to Book Factory | Cannot reuse without importing all of bfagent |
| No consistent multi-tenancy across apps | Some apps have `org_id`, some don't, no shared middleware |
| Domain-specific apps cannot be deployed independently | All-or-nothing deployments |
| No central Developer Portal | Service status, agent results, docs scattered across repos |
| Deprecated modules still in codebase | MedTrans, GenAgent, PresentationStudio |
| Business logic lives in views, no service layer | Untestable, tightly coupled to HTTP |

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

### 1.4 Existing Shared Infrastructure

The `platform-context` package (v0.2.0) already provides production-ready
components that **must be reused, not reinvented**:

- `SubdomainTenantMiddleware` — Subdomain-based tenant resolution with
  DB-verified tenant lookup and Postgres RLS session variable integration
- `RequestContextMiddleware` — Thread-safe context propagation via
  `contextvars` (request_id, tenant_id, user_id)
- `set_db_tenant()` / `get_db_tenant()` — Postgres RLS session variables
- `HtmxResponseMixin` / `HtmxErrorMiddleware` — HTMX utilities (ADR-048)
- `emit_audit_event()` — Structured audit trail for compliance
- `emit_outbox_event()` — Reliable event publishing (outbox pattern)

## 2. Decision

### 2.1 Five Core Decisions

1. **Decompose bfagent** into purpose-built hub repositories.
2. **Create `dev-hub`** as the central Developer Portal, inspired by
   Backstage concepts but implemented in Django (HTMX, Tailwind).
3. **All hubs are tenant-capable** from day one via the existing
   `platform-context` multi-tenancy stack (SubdomainTenantMiddleware,
   Postgres RLS, TenantAwareManager).
4. **Database is Source of Truth** for all managed entities. YAML files
   (e.g., `catalog-info.yaml`) are import formats, not canonical sources.
5. **Strict Service Layer** — every hub follows `views → services → models`.
   Views handle HTTP only; business logic lives exclusively in services.

### 2.2 Why Django, Not Backstage

| Criterion | Backstage (Node.js) | Django dev-hub |
| --------- | ------------------- | -------------- |
| Tech stack | TypeScript, React, Express | Python, Django, HTMX, Tailwind |
| Consistency | New stack to maintain | Same stack as all other hubs |
| Agent integration | REST adapter needed (Python → Node) | Native Python import |
| Plugin ecosystem | 200+ plugins (Kubernetes, PagerDuty...) | Not needed for 14 hubs |
| Docker image size | ~500 MB | ~50 MB |
| Team expertise | TypeScript learning curve | Existing Django expertise |
| Deployment | Different pipeline | Same Docker Compose pattern |

**Decision**: Adopt Backstage's **data model and conventions**
(`catalog-info.yaml` format, Entity taxonomy) but implement in Django. The
DB is the authoritative source; YAML is an import/export format that
preserves Backstage compatibility for potential future migration.

### 2.3 Source of Truth: Database

| Aspect | Source of Truth | Rationale |
| ------ | -------------- | --------- |
| Service Catalog entities | **DB** (dev-hub PostgreSQL) | Relationships, audit, real-time queries |
| LLM / Agent configuration | **DB** (dev-hub PostgreSQL) | CRUD via UI, version history, tenant-scoped |
| Hub health status | **DB** (dev-hub PostgreSQL) | Polled periodically, cached, alertable |
| ADR documents | **Git** (platform repo) | Markdown, versioned via Git |
| Deployment config | **Git** (per-hub repo) | docker-compose.prod.yml, Dockerfile |

`catalog-info.yaml` files in each repo serve as **import seeds**: a CI
pipeline or management command reads them and upserts into the DB. After
import, the DB record is authoritative. Manual edits via dev-hub UI take
precedence over stale YAML.

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
| 2 | `writing-hub` | Book Factory | ✅ | `writing_hub_db` | writing.iil.pet | **NEW** (ex-bfagent) |
| 3 | `media-hub` | Media Generation (ComfyUI, TTS) | ✅ | `media_hub_db` | media.iil.pet | **NEW** (ex-bfagent) |
| 4 | `research-hub` | Research (Brave, Facts, Citations) | ✅ | `research_hub_db` | research.iil.pet | **NEW** (ex-bfagent) |
| 5 | `weltenhub` | Story Universe (Weltenforger) | ✅ | `weltenhub_db` | weltenforger.com | Exists |
| 6 | `risk-hub` | Compliance & Safety (Schutztat + Expert Hub + DSB) | ✅ | `risk_hub_db` | schutztat.de | Exists |
| 7 | `travel-beat` | Travel Stories (DriftTales) | ✅ | `travel_beat_db` | drifttales.app | Exists |
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

- **Service-to-service auth**: Shared HMAC secret per hub pair,
  `X-Hub-Signature` header, verified in DRF authentication class
- **Tenant propagation**: Calling hub passes `X-Tenant-ID` header;
  receiving hub validates tenant exists in its own DB before processing
- **API versioning**: `/api/v1/` namespace, DRF Spectacular schema
- **Timeout + retry**: 5s connect, 30s read, 3 retries with backoff

## 4. dev-hub Architecture

### 4.1 Phased App Deployment

To avoid recreating a monolith, dev-hub apps are deployed in phases.
Each phase has a clear bounded context. An app is split when its
`services.py` exceeds 500 lines.

```text
Phase A (MVP — 3 apps):
  core              Base models, TenantAwareManager, shared utilities
  catalog           Service Catalog (Backstage Entity Model)
  health            Server, Container, DB health polling

Phase B (Management — 2 apps):
  ai_config         LLM + Agent CRUD (from bfagent)
  controlling       Usage tracking, costs, alerts (from bfagent)

Phase C (Full Portal — 4 apps):
  mcp_management    MCP Server Management (from bfagent)
  agents_dashboard  Platform Agents UI (ADR-054)
  techdocs          ADR Browser + Sphinx Integration (ADR-047)
  onboarding        Onboarding Coach Web UI
```

**Monolith Guard Rule**: If any app accumulates >3 models with no FK
relationship to other models in the same app, it is a candidate for
extraction into its own hub.

### 4.2 App Structure

```text
dev-hub/
├── config/
│   └── settings/
│       ├── base.py                  # Django 5.x, platform-context
│       ├── development.py
│       └── production.py
├── apps/
│   ├── core/                        # Shared foundation
│   │   ├── models.py               # TenantAwareModel, TenantAwareManager
│   │   └── auth.py                 # HubServiceAuthentication (HMAC)
│   ├── catalog/                     # Service Catalog
│   │   ├── models.py               # Normalized entity models
│   │   ├── services.py             # CatalogImportService, CatalogSyncService
│   │   └── importers.py            # catalog-info.yaml parser
│   ├── health/                      # Health Dashboard
│   │   ├── models.py               # HealthCheck, HealthCheckResult
│   │   └── services.py             # HealthPollingService
│   ├── ai_config/                   # Phase B
│   │   ├── models.py               # LLMProvider, AgentConfig
│   │   └── services.py             # LLMTestService, AgentConfigService
│   ├── controlling/                 # Phase B
│   │   ├── models.py               # UsageRecord, CostAlert
│   │   └── services.py             # UsageAggregationService
│   ├── mcp_management/              # Phase C
│   ├── agents_dashboard/            # Phase C
│   ├── techdocs/                    # Phase C
│   └── onboarding/                  # Phase C
├── templates/                       # Tailwind + HTMX
├── docker-compose.prod.yml
├── catalog-info.yaml                # Self-describing
└── Dockerfile
```

Every app with business logic **must** have a `services.py`. Views
import services, never models directly for mutations.

### 4.3 Service Catalog — Normalized Entity Model

The catalog adopts Backstage's entity taxonomy with **strict
normalization**: no denormalized strings, proper FKs, DB constraints.

```python
from django.db import models


class ComponentType(models.TextChoices):
    SERVICE = "service", "Service"
    WEBSITE = "website", "Website"
    LIBRARY = "library", "Library"
    MCP_SERVER = "mcp_server", "MCP Server"


class Lifecycle(models.TextChoices):
    PRODUCTION = "production", "Production"
    EXPERIMENTAL = "experimental", "Experimental"
    DEPRECATED = "deprecated", "Deprecated"


class APIType(models.TextChoices):
    OPENAPI = "openapi", "OpenAPI"
    GRPC = "grpc", "gRPC"
    GRAPHQL = "graphql", "GraphQL"
    DJANGO_REST = "drf", "Django REST Framework"


class DependencyKind(models.TextChoices):
    RUNTIME = "runtime", "Runtime"
    BUILD_TIME = "build_time", "Build-Time"
    OPTIONAL = "optional", "Optional"


class Domain(TenantAwareModel):
    """Top-level business domain grouping systems."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_domain_tenant_name",
            )
        ]


class Owner(TenantAwareModel):
    """Team or person owning components."""
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_owner_tenant_name",
            )
        ]


class System(TenantAwareModel):
    """A collection of components forming a system."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    domain = models.ForeignKey(Domain, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_system_tenant_name",
            )
        ]


class Component(TenantAwareModel):
    """A software component (service, website, library)."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    type = models.CharField(
        max_length=50, choices=ComponentType.choices,
    )
    lifecycle = models.CharField(
        max_length=50, choices=Lifecycle.choices,
    )
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    system = models.ForeignKey(
        System, on_delete=models.SET_NULL, null=True, blank=True,
    )
    repo_url = models.URLField(blank=True)
    provides_apis = models.ManyToManyField(
        "API", blank=True, related_name="provided_by",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_component_tenant_name",
            )
        ]


class ComponentDependency(TenantAwareModel):
    """Typed dependency between components (through-model)."""
    source = models.ForeignKey(
        Component, on_delete=models.CASCADE, related_name="dependencies",
    )
    target = models.ForeignKey(
        Component, on_delete=models.CASCADE, related_name="dependents",
    )
    kind = models.CharField(
        max_length=50, choices=DependencyKind.choices,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "source", "target"],
                name="uq_dependency_source_target",
            )
        ]


class API(TenantAwareModel):
    """An API provided by a component."""
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=50, choices=APIType.choices)
    definition_url = models.URLField(blank=True)
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_api_tenant_name",
            )
        ]


class Resource(TenantAwareModel):
    """Infrastructure resource (database, cache, queue)."""
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=50)  # postgres, redis, s3
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    system = models.ForeignKey(
        System, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_resource_tenant_name",
            )
        ]
```

### 4.4 catalog-info.yaml (Import Format)

Each repository contains a `catalog-info.yaml` in Backstage-compatible
format. This file is **not** the source of truth — it is an import seed.

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

**Sync trigger**: CI pipeline on push to `main` runs
`python manage.py import_catalog --repo <url>`. The importer upserts
into the DB and logs changes via `emit_audit_event()`.

### 4.5 Features Migrated from bfagent Control Center

| bfagent Source | dev-hub App | Migration Notes |
| -------------- | ----------- | --------------- |
| `views_ai_config.py` | `ai_config` | Extract business logic into `services.py` |
| `views_mcp.py` | `mcp_management` | SSE pattern from `platform-context` |
| `views_hub_management.py` | `catalog` | Replace with normalized Entity Model |
| `views_controlling.py` | `controlling` | Extract aggregation into `services.py` |

**Not migrated** (already in `platform-context` v0.2.0):
- `HTMXResponseMixin` → `platform_context.htmx.HtmxResponseMixin`
- `HtmxErrorMiddleware` → `platform_context.htmx.HtmxErrorMiddleware`
- `SSE pattern` → `platform_context.htmx.is_htmx_request()`

## 5. Service Layer Standard

### 5.1 Architecture Rule

Every hub **must** follow the service layer pattern. This is non-negotiable
for all new code and required for all migrated bfagent code:

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   views.py  │────►│ services.py  │────►│  models.py  │
│  HTTP only  │     │ Business     │     │  Data only  │
│  No logic   │     │ Logic        │     │  No HTTP    │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │                    │
   Validates           Orchestrates          Persists
   HTTP input          Domain rules          via ORM
   Returns             Calls models          Defines
   Response            Emits events          Schema
```

### 5.2 Rules

| Rule | Enforcement |
| ---- | ----------- |
| Views may not import models directly for mutations | Code review + Guardian |
| Views may not contain `if/else` business logic | Code review |
| Services receive typed dataclasses or Pydantic models, not `request` | Code review |
| Services call `emit_audit_event()` for all mutations | Code review + tests |
| Services are independently testable without HTTP | pytest |
| Maximum `services.py` length: 500 lines | Linter |

### 5.3 Example: Catalog Import

```python
# apps/catalog/views.py
class CatalogImportView(LoginRequiredMixin, View):
    """Trigger catalog-info.yaml import for a repository."""

    def post(self, request: HttpRequest, component_id: int) -> HttpResponse:
        component = get_object_or_404(
            Component.objects.for_tenant(request.tenant_id),
            pk=component_id,
        )
        result = catalog_import_service.import_from_repo(
            tenant_id=request.tenant_id,
            component=component,
            actor_user_id=request.user.id,
        )
        if is_htmx_request(request):
            return render(request, "catalog/partials/_import_result.html", {
                "result": result,
            })
        return redirect("catalog:component-detail", pk=component.pk)


# apps/catalog/services.py
@dataclass(frozen=True)
class ImportResult:
    created: int
    updated: int
    errors: list[str]


def import_from_repo(
    *,
    tenant_id: UUID,
    component: Component,
    actor_user_id: int,
) -> ImportResult:
    """Import catalog-info.yaml from component's repo."""
    yaml_data = _fetch_catalog_yaml(component.repo_url)
    parsed = _parse_catalog_yaml(yaml_data)

    created, updated, errors = 0, 0, []
    for entity in parsed.entities:
        try:
            _upsert_entity(tenant_id, entity)
            # ... count created/updated
        except ValidationError as exc:
            errors.append(str(exc))

    emit_audit_event(
        tenant_id=tenant_id,
        category="catalog",
        action="imported",
        entity_type="catalog.Component",
        entity_id=component.pk,
        payload={"created": created, "updated": updated},
    )
    return ImportResult(created=created, updated=updated, errors=errors)
```

## 6. Multi-Tenancy Standard

### 6.1 Two-Layer Isolation

Tenant isolation is enforced at **two independent layers**. Neither layer
may be skipped.

```text
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Application (Python / Django ORM)              │
│  ─────────────────────────────────────────               │
│  TenantAwareManager.for_tenant(tid) filters queries      │
│  SubdomainTenantMiddleware sets request.tenant_id         │
│  Guardian rule G-003 blocks models without tenant_id      │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────┐
│  Layer 2: Database (Postgres Row Level Security)         │
│  ─────────────────────────────────────────               │
│  set_db_tenant() sets session variable                   │
│  RLS policy: tenant_id = current_setting(...)            │
│  Even raw SQL or ORM bugs cannot leak cross-tenant       │
└─────────────────────────────────────────────────────────┘
```

### 6.2 TenantAwareModel + TenantAwareManager

Provided by `platform-context` (extended in this ADR):

```python
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from uuid import UUID


class TenantAwareQuerySet(models.QuerySet):
    """QuerySet that enforces tenant filtering."""

    def for_tenant(self, tenant_id: UUID) -> TenantAwareQuerySet:
        """Filter by tenant. Primary entry point for all queries."""
        return self.filter(tenant_id=tenant_id)


class TenantAwareManager(models.Manager):
    """Manager that provides tenant-scoped queries."""

    def get_queryset(self) -> TenantAwareQuerySet:
        return TenantAwareQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant_id: UUID) -> TenantAwareQuerySet:
        """Convenience: Model.objects.for_tenant(tid)."""
        return self.get_queryset().for_tenant(tenant_id)


class TenantAwareModel(models.Model):
    """Abstract base for all tenant-scoped models."""

    tenant_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        abstract = True
```

**Usage** (the only acceptable pattern):

```python
# ✅ Correct — explicit tenant scope
projects = Project.objects.for_tenant(request.tenant_id)
project = get_object_or_404(
    Project.objects.for_tenant(request.tenant_id), pk=pk
)

# ❌ FORBIDDEN — bypasses tenant isolation
projects = Project.objects.all()
projects = Project.objects.filter(name="foo")
```

### 6.3 Middleware Stack

Every hub uses `platform-context` middleware. **No custom tenant
middleware allowed.**

```python
# config/settings/base.py
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # --- Platform middleware (this order) ---
    "platform_context.middleware.RequestContextMiddleware",
    "platform_context.middleware.SubdomainTenantMiddleware",
    "platform_context.htmx.HtmxErrorMiddleware",
]

# Required settings for SubdomainTenantMiddleware
TENANT_BASE_DOMAIN = "iil.pet"          # or "localhost" in dev
TENANT_MODEL = "core.Organization"       # per-hub tenant model
TENANT_SLUG_FIELD = "slug"
TENANT_ID_FIELD = "tenant_id"
TENANT_ALLOW_LOCALHOST = DEBUG           # admin access in dev only
```

### 6.4 Postgres Row Level Security (RLS)

Every hub **must** enable RLS on all tenant-scoped tables:

```sql
-- Migration: enable RLS on a table
ALTER TABLE catalog_component ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalog_component FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON catalog_component
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

The `SubdomainTenantMiddleware` calls `set_db_tenant()` which sets the
Postgres session variable `app.current_tenant`. This ensures that even
raw SQL or ORM `.all()` bugs cannot leak cross-tenant data.

### 6.5 Audit Trail

All mutations in all hubs **must** emit audit events via
`platform_context.audit.emit_audit_event()`:

```python
from platform_context.audit import emit_audit_event

emit_audit_event(
    tenant_id=tenant_id,
    category="ai_config",
    action="updated",
    entity_type="ai_config.LLMProvider",
    entity_id=provider.pk,
    payload={"field": "api_key", "changed_by": actor_user_id},
)
```

The audit model is configured per hub via `PLATFORM_AUDIT_MODEL` in
Django settings.

## 7. Deployment Pattern

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
- **Database**: PostgreSQL 16 (one database per hub, RLS enabled)
- **Cache/Broker**: Redis 7

## 8. bfagent Migration Plan

### 8.1 Migration Phases

| Phase | What | Target | Priority |
| ----- | ---- | ------ | -------- |
| **M0** | Remove MedTrans, GenAgent, PresentationStudio | bfagent cleanup | Immediate |
| **M1** | Create `dev-hub` (core + catalog + health) | New repo | High |
| **M2** | Migrate AI Config, Controlling → dev-hub | dev-hub Phase B | High |
| **M3** | Extract Writing Hub → `writing-hub` | New repo | Medium |
| **M4** | Extract Media Hub → `media-hub` | New repo | Medium |
| **M5** | Extract Research → `research-hub` | New repo | Medium |
| **M6** | Migrate Expert Hub + DSB → `risk-hub` | Existing repo | Medium |
| **M7** | Migrate MCP Dashboard, Agents UI → dev-hub | dev-hub Phase C | Low |
| **M8** | Migrate DLM Hub → dev-hub `techdocs` | dev-hub Phase C | Low |
| **M9** | Archive `bfagent` repository | GitHub archive | Final |

### 8.2 Migration Strategy Per Module

For each module extraction:

1. **Backup** source database via `pg_dump`
2. **Create target repo** with Django skeleton + Docker + CI
3. **Copy models** with fresh migrations (no migration history)
4. **Introduce service layer**: Extract business logic from views into
   `services.py`. Views become thin HTTP handlers.
5. **Add `TenantAwareModel`** base to all models, add `tenant_id` where
   missing
6. **Enable Postgres RLS** on all tenant-scoped tables
7. **Data migration** via `pg_dump` / `pg_restore` of relevant tables,
   backfill `tenant_id` for existing rows
8. **Add `catalog-info.yaml`** for service catalog registration
9. **Deploy** and verify with health checks
10. **Deprecate** in bfagent (redirect or remove)

### 8.3 bfagent Deprecated Modules

| Module | Reason | Action |
| ------ | ------ | ------ |
| `medtrans` | Migrated to prezimo | Remove immediately |
| `genagent` | Replaced by MCP Orchestrator (`mcp-hub`) | Remove immediately |
| `presentation_studio` | Extracted to `pptx-hub` | Remove immediately |

## 9. Shared Infrastructure

### 9.1 platform Repository

Remains the home for:

- **ADRs** (`docs/adr/`)
- **Platform Agents** (`agents/` — Guardian, Drift Detector, ADR Scribe,
  Onboarding Coach, Context Reviewer; see ADR-054)
- **Shared Packages** (`packages/platform-context`, `packages/docs-agent`)
- **CI/CD Workflows** (`.github/workflows/`)

### 9.2 platform-context Package (v0.2.0+)

Already provides and will be extended with:

| Module | Status | Provides |
| ------ | ------ | -------- |
| `context.py` | ✅ Exists | `RequestContext`, `set_tenant()`, `get_context()` |
| `middleware.py` | ✅ Exists | `SubdomainTenantMiddleware`, `RequestContextMiddleware` |
| `db.py` | ✅ Exists | `set_db_tenant()`, `get_db_tenant()` (RLS) |
| `htmx.py` | ✅ Exists | `HtmxResponseMixin`, `HtmxErrorMiddleware`, `is_htmx_request()` |
| `audit.py` | ✅ Exists | `emit_audit_event()` |
| `outbox.py` | ✅ Exists | `emit_outbox_event()` |
| `exceptions.py` | ✅ Exists | Platform exception hierarchy |
| `models.py` | **NEW** | `TenantAwareModel`, `TenantAwareManager`, `TenantAwareQuerySet` |
| `auth.py` | **NEW** | `HubServiceAuthentication` (HMAC for inter-hub calls) |

**Versioning rule**: Breaking changes to `platform-context` require a
major version bump and must be documented in a new ADR. Non-breaking
additions (new functions, new optional fields) use minor bumps.

### 9.3 mcp-hub Repository

Remains the home for:

- **MCP Servers** (deployment, orchestrator, LLM, database, filesystem)
- **Orchestrator** with `AGENT_GATE_MAP` for all platform agents

## 10. Consequences

### 10.1 Positive

- **Clear ownership**: Each hub has a single purpose and independent lifecycle
- **Independent deployment**: Update writing-hub without touching risk-hub
- **Two-layer tenant isolation**: Application-level `TenantAwareManager` +
  DB-level Postgres RLS — defense in depth
- **Central management**: dev-hub provides single pane of glass for all hubs
- **Smaller codebases**: Faster CI, easier onboarding, fewer merge conflicts
- **Testable business logic**: Service layer enables unit testing without HTTP
- **Audit trail**: All mutations tracked via `emit_audit_event()`
- **API-first**: Hubs communicate via REST, enabling future scaling
- **No reinvention**: Reuses existing `platform-context` infrastructure

### 10.2 Negative

- **More repositories**: 14 hubs + 2 infra = 16 repos to manage
- **Migration effort**: Extracting from bfagent requires careful data
  migration and service layer introduction
- **Cross-hub queries**: No direct DB joins; must use API calls
- **Shared package versioning**: `platform-context` changes affect all hubs
- **RLS overhead**: Postgres RLS adds ~1-2% query overhead per table

### 10.3 Risks

| Risk | Mitigation |
| ---- | ---------- |
| Data loss during migration | `pg_dump` backups before every migration step |
| Inconsistent patterns across hubs | ADR-050 defines standards, Guardian enforces |
| API latency for cross-hub calls | Cache frequently accessed data, async where possible |
| Too many repos for small team | dev-hub Service Catalog provides central overview |
| `platform-context` breaking change | Major version bumps, ADR required, phased rollout |
| 14 hubs on single server | Monitor resources; horizontal scaling via second VM when needed |

## 11. Implementation Priority

```text
Phase 1 — Foundation (Immediate):
  ├── ADR-050 ✅ (this document)
  ├── Add TenantAwareModel + TenantAwareManager to platform-context
  ├── Create dev-hub repo + Django skeleton
  └── Implement core + catalog + health (Phase A apps)

Phase 2 — Management (Short-term):
  ├── Migrate AI Config → dev-hub (with service layer)
  ├── Migrate Controlling → dev-hub (with service layer)
  └── Add catalog-info.yaml to all existing repos

Phase 3 — Extraction (Medium-term):
  ├── Extract writing-hub from bfagent
  ├── Extract media-hub from bfagent
  ├── Extract research-hub from bfagent
  └── Migrate Expert Hub + DSB → risk-hub

Phase 4 — Completion (Final):
  ├── Migrate MCP Dashboard, Agents UI → dev-hub (Phase C apps)
  ├── Migrate DLM Hub → dev-hub techdocs
  ├── Remove deprecated modules from bfagent
  └── Archive bfagent repository
```
