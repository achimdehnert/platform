---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
implementation_status: implemented
implementation_evidence:
  - "bfagent, weltenhub, risk-hub: tenant + RBAC models in production"
---

# ADR-007 FINAL: Tenant- & RBAC-Architektur (Production Ready)

**Status:** ACCEPTED  
**Datum:** 2026-02-01  
**Version:** 2.0 (konsolidiert aus ADR-007-Tenant-RBAC.md + adr_007_optimized_tenant_rbac.md + concepts/)  
**Autoren:** Platform Architecture Team  
**Reviewer:** Cascade AI

---

## Executive Summary

Dieses ADR definiert die **vollständige Multi-Tenancy & RBAC-Architektur** für die Platform. Es konsolidiert alle bisherigen Entwürfe und folgt strikt den Platform-Prinzipien:

| Prinzip | Umsetzung |
|---------|-----------|
| **Database-First** | Constraints, RLS, Permission-Tabellen in PostgreSQL |
| **Strikte Normalisierung** | Keine JSONB für kritische Daten (Permissions, Quotas) |
| **Separation of Concerns** | DB → Repository → Service → Handler → View |
| **Handler-Pattern** | Command/Result für alle Use Cases |
| **Zero Breaking Changes** | Soft-Delete, additive Migrationen |

---

## Inhaltsverzeichnis

1. [Kontext](#1-kontext)
2. [Ziele & Nicht-Ziele](#2-ziele--nicht-ziele)
3. [Architektur-Übersicht](#3-architektur-übersicht)
4. [Datenmodell (Normalisiert)](#4-datenmodell-normalisiert)
5. [Layer-Architektur & Separation of Concerns](#5-layer-architektur--separation-of-concerns)
6. [Handler-Pattern](#6-handler-pattern)
7. [Permission-System](#7-permission-system)
8. [Row Level Security (RLS)](#8-row-level-security-rls)
9. [Naming Conventions](#9-naming-conventions)
10. [Caching-Strategie](#10-caching-strategie)
11. [Events & Audit](#11-events--audit)
12. [Exceptions & Error Handling](#12-exceptions--error-handling)
13. [Migration & Rollout](#13-migration--rollout)
14. [API & Decorators](#14-api--decorators)
15. [Implementierung](#15-implementierung)
16. [Konsequenzen](#16-konsequenzen)

---

## 1. Kontext

### Problemstellung

Die Platform entwickelt sich zu einem **echten Multi-Tenant-System** mit steigenden Anforderungen an Security, Compliance und Skalierbarkeit. Die aktuelle Implementierung in `bfagent-core` bietet:

**Stärken:**
- ✅ Contextvars-Pattern (tenant_id, user_id, request_id)
- ✅ RLS-Integration funktioniert
- ✅ Middleware-Konzept ist solide

**Lücken:**
- ❌ Kein zentrales Tenant-Model
- ❌ Keine User-Tenant-Zuordnung (Memberships)
- ❌ Kein Permission-System
- ❌ Kein Lifecycle-Management

### Bestehende Architektur

```
packages/bfagent-core/
├── context.py          # ✅ Contextvars (tenant_id, user_id, request_id)
├── db.py               # ✅ set_db_tenant() für RLS
├── middleware.py       # ✅ SubdomainTenantMiddleware
├── models.py           # ✅ AuditEvent, OutboxMessage
└── audit.py            # ✅ emit_audit_event()
```

---

## 2. Ziele & Nicht-Ziele

### Ziele

| ID | Anforderung | Priorität |
|----|-------------|-----------|
| R1 | Zentrales Tenant-Model mit Lifecycle-Management | **Must** |
| R2 | User-Tenant-Zuordnung mit Rollen (RBAC) | **Must** |
| R3 | Voll normalisierte Permissions (keine JSONB) | **Must** |
| R4 | Permission-Overrides auf Membership-Ebene | **Should** |
| R5 | Integration mit bestehendem RLS-System | **Must** |
| R6 | Handler-Pattern für alle Use Cases | **Must** |
| R7 | Event-System für Audit & Integration | **Should** |
| R8 | Caching mit Fail-Closed | **Should** |
| R9 | Zero Breaking Changes | **Must** |

### Nicht-Ziele

- Object-Level-Permissions (Phase >1)
- UI/UX-Details
- Externe IAM-Integration (Phase >1)

---

## 3. Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MULTI-TENANCY ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PRESENTATION LAYER                                                  │   │
│  │ • Django Views (CBV/FBV) mit @require_permission                    │   │
│  │ • DRF APIViews mit TenantAPIPermissionMixin                        │   │
│  │ • HTMX Partials                                                     │   │
│  │ • WebSocket Consumers                                               │   │
│  │ Verantwortung: HTTP-Handling, Serialization, Responses              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ APPLICATION LAYER (Handlers)                                        │   │
│  │ • TenantCreateHandler                                               │   │
│  │ • MembershipInviteHandler                                           │   │
│  │ • PermissionGrantHandler                                            │   │
│  │ Verantwortung: Use Case Orchestration, Command/Result               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DOMAIN LAYER (Services)                                             │   │
│  │ • AuthorizationService                                              │   │
│  │ • TenantLifecycleService                                            │   │
│  │ • PermissionResolver                                                │   │
│  │ Verantwortung: Business Logic, Domain Rules                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ INFRASTRUCTURE LAYER                                                │   │
│  │ • Repositories (TenantRepository, MembershipRepository)             │   │
│  │ • Cache (PermissionCache)                                           │   │
│  │ • EventBus (emit_tenant_created, emit_permission_changed)           │   │
│  │ Verantwortung: Data Access, External Services, Caching              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DATABASE LAYER (PostgreSQL)                                         │   │
│  │ • Row Level Security (RLS)                                          │   │
│  │ • CHECK Constraints (Status, Lifecycle)                             │   │
│  │ • Foreign Keys (Referential Integrity)                              │   │
│  │ • Triggers (updated_at, audit)                                      │   │
│  │ Verantwortung: Data Integrity, Isolation, Enforcement               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Datenmodell (Normalisiert)

### 4.1 Entity-Relationship-Diagramm

```
┌─────────────────┐       ┌────────────────────────┐       ┌─────────────────┐
│  core_tenant    │       │ core_tenant_membership │       │   auth_user     │
├─────────────────┤       ├────────────────────────┤       ├─────────────────┤
│ id (UUID) PK    │◀──────│ tenant_id FK           │       │ id (INT) PK     │
│ slug            │       │ user_id FK             │──────▶│ username        │
│ name            │       │ role                   │       │ email           │
│ status          │       │ created_at             │       └─────────────────┘
│ plan_code       │       │ updated_at             │
│ created_at      │       └────────────────────────┘
│ updated_at      │                 │
└─────────────────┘                 │
        │                           │
        ▼                           ▼
┌─────────────────┐       ┌────────────────────────────────┐
│ core_tenant_    │       │ core_membership_permission_    │
│ quota           │       │ override                       │
├─────────────────┤       ├────────────────────────────────┤
│ tenant_id FK    │       │ membership_id FK               │
│ quota_code      │       │ permission_code FK             │
│ limit_value     │       │ allowed BOOLEAN                │
│ current_value   │       │ created_at                     │
│ reset_at        │       └────────────────────────────────┘
└─────────────────┘                   │
        │                             │
        ▼                             ▼
┌─────────────────┐       ┌─────────────────────────────────┐
│ core_tenant_    │       │ core_permission                 │
│ feature         │       ├─────────────────────────────────┤
├─────────────────┤       │ code (PK)                       │
│ tenant_id FK    │       │ description                     │
│ feature_code    │       └─────────────────────────────────┘
│ enabled         │                   ▲
└─────────────────┘                   │
                          ┌─────────────────────────────────┐
                          │ core_role_permission            │
                          ├─────────────────────────────────┤
                          │ role                            │
                          │ permission_code FK              │
                          └─────────────────────────────────┘
```

### 4.2 Core Tenant (PostgreSQL)

```sql
CREATE TABLE core_tenant (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'trial',
    plan_code TEXT NOT NULL DEFAULT 'free',
    
    -- Lifecycle Timestamps
    trial_ends_at TIMESTAMPTZ,
    suspended_at TIMESTAMPTZ,
    suspended_reason TEXT DEFAULT '',
    deleted_at TIMESTAMPTZ,
    
    -- Billing (Optional)
    stripe_customer_id TEXT UNIQUE,
    
    -- Settings (OK: nicht-kritische Konfiguration)
    settings JSONB NOT NULL DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Lifecycle-Constraints (DB-enforced!)
    CONSTRAINT tenant_status_chk CHECK (
        status IN ('trial', 'active', 'suspended', 'deleted')
    ),
    CONSTRAINT tenant_trial_chk CHECK (
        status <> 'trial' OR trial_ends_at IS NOT NULL
    ),
    CONSTRAINT tenant_suspended_chk CHECK (
        status <> 'suspended' OR suspended_at IS NOT NULL
    ),
    CONSTRAINT tenant_deleted_chk CHECK (
        status <> 'deleted' OR deleted_at IS NOT NULL
    )
);

CREATE INDEX core_tenant_slug_idx ON core_tenant(slug);
CREATE INDEX core_tenant_status_idx ON core_tenant(status);
CREATE INDEX core_tenant_plan_idx ON core_tenant(plan_code);
```

### 4.3 Tenant Quota (Normalisiert)

```sql
-- Ersetzt: quotas JSONB
CREATE TABLE core_tenant_quota (
    tenant_id UUID NOT NULL REFERENCES core_tenant(id) ON DELETE CASCADE,
    quota_code TEXT NOT NULL,  -- 'api_calls_monthly', 'storage_gb'
    limit_value BIGINT NOT NULL,
    current_value BIGINT NOT NULL DEFAULT 0,
    reset_at TIMESTAMPTZ,
    
    PRIMARY KEY (tenant_id, quota_code)
);

CREATE INDEX core_tenant_quota_reset_idx ON core_tenant_quota(reset_at);
```

### 4.4 Tenant Feature (Normalisiert)

```sql
-- Ersetzt: features JSONB
CREATE TABLE core_tenant_feature (
    tenant_id UUID NOT NULL REFERENCES core_tenant(id) ON DELETE CASCADE,
    feature_code TEXT NOT NULL,  -- 'ai_generation', 'export_pdf'
    enabled BOOLEAN NOT NULL DEFAULT false,
    
    PRIMARY KEY (tenant_id, feature_code)
);
```

### 4.5 Tenant Membership

```sql
CREATE TABLE core_tenant_membership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES core_tenant(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member',
    
    -- Invitation
    invited_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    invited_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    CONSTRAINT membership_role_chk CHECK (
        role IN ('owner', 'admin', 'member', 'viewer')
    ),
    CONSTRAINT membership_unique UNIQUE (tenant_id, user_id)
);

CREATE INDEX core_membership_tenant_idx ON core_tenant_membership(tenant_id);
CREATE INDEX core_membership_user_idx ON core_tenant_membership(user_id);
CREATE INDEX core_membership_role_idx ON core_tenant_membership(role);
```

### 4.6 Permission System (Voll Normalisiert)

```sql
-- Permission-Registry
CREATE TABLE core_permission (
    code TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general'
);

-- Role-Permission-Mapping (statisch)
CREATE TABLE core_role_permission (
    role TEXT NOT NULL,
    permission_code TEXT NOT NULL REFERENCES core_permission(code) ON DELETE CASCADE,
    
    PRIMARY KEY (role, permission_code),
    CONSTRAINT role_chk CHECK (role IN ('owner', 'admin', 'member', 'viewer'))
);

-- Membership-Override (dynamisch)
CREATE TABLE core_membership_permission_override (
    membership_id UUID NOT NULL REFERENCES core_tenant_membership(id) ON DELETE CASCADE,
    permission_code TEXT NOT NULL REFERENCES core_permission(code) ON DELETE CASCADE,
    allowed BOOLEAN NOT NULL,
    granted_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    PRIMARY KEY (membership_id, permission_code)
);
```

### 4.7 Plan-based Features & Quotas

```sql
-- Plan → Features Mapping
CREATE TABLE core_plan_feature (
    plan_code TEXT NOT NULL,
    feature_code TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT false,
    
    PRIMARY KEY (plan_code, feature_code)
);

-- Plan → Quota Defaults
CREATE TABLE core_plan_quota (
    plan_code TEXT NOT NULL,
    quota_code TEXT NOT NULL,
    default_limit BIGINT NOT NULL,
    
    PRIMARY KEY (plan_code, quota_code)
);
```

---

## 5. Layer-Architektur & Separation of Concerns

### 5.1 Layer-Verantwortlichkeiten

| Layer | Verantwortung | Beispiele |
|-------|---------------|-----------|
| **Database** | Constraints, RLS, Referential Integrity | CHECK, FK, RLS Policies |
| **Repository** | Data Access, Queries | `TenantRepository.get_by_slug()` |
| **Service** | Business Logic, Domain Rules | `PermissionResolver.resolve()` |
| **Handler** | Use Case Orchestration | `TenantCreateHandler.handle()` |
| **View** | HTTP, Serialization | `@require_permission` |
| **Template** | Darstellung | `{% if perm in perms %}` |

### 5.2 Dependency Rule

```
View → Handler → Service → Repository → Database
  ↓        ↓         ↓          ↓
  ────────────────────────────────────────────▶ Keine Rückwärts-Deps!
```

### 5.3 Repository-Interface

```python
# packages/bfagent-core/src/bfagent_core/repositories/tenant.py

from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional, List
from bfagent_core.models import Tenant

class TenantRepositoryInterface(ABC):
    """Repository-Interface für Tenant-Zugriff."""
    
    @abstractmethod
    def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """Tenant by ID laden."""
        pass
    
    @abstractmethod
    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Tenant by Slug laden."""
        pass
    
    @abstractmethod
    def slug_exists(self, slug: str) -> bool:
        """Prüft ob Slug bereits existiert."""
        pass
    
    @abstractmethod
    def save(self, tenant: Tenant) -> Tenant:
        """Tenant speichern (create/update)."""
        pass
    
    @abstractmethod
    def list_active(self) -> List[Tenant]:
        """Alle aktiven Tenants."""
        pass


class DjangoTenantRepository(TenantRepositoryInterface):
    """Django ORM Implementation."""
    
    def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        return Tenant.objects.filter(id=tenant_id).first()
    
    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        return Tenant.objects.active().filter(slug=slug).first()
    
    def slug_exists(self, slug: str) -> bool:
        return Tenant.objects.filter(slug=slug).exists()
    
    def save(self, tenant: Tenant) -> Tenant:
        tenant.save()
        return tenant
    
    def list_active(self) -> List[Tenant]:
        return list(Tenant.objects.active())
```

---

## 6. Handler-Pattern

### 6.1 Command-Result-Pattern

```python
# packages/bfagent-core/src/bfagent_core/handlers/tenant.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from bfagent_core.models import Tenant, TenantMembership, TenantRole, TenantStatus
from bfagent_core.repositories import TenantRepository, MembershipRepository
from bfagent_core.events import EventBus, TenantCreatedEvent
from bfagent_core.exceptions import TenantSlugExistsError


@dataclass(frozen=True)
class TenantCreateCommand:
    """Command für Tenant-Erstellung."""
    slug: str
    name: str
    plan_code: str
    owner_user_id: int
    trial_days: int = 14


@dataclass(frozen=True)
class TenantCreateResult:
    """Ergebnis der Tenant-Erstellung."""
    tenant_id: UUID
    membership_id: UUID
    trial_ends_at: datetime


class TenantCreateHandler:
    """
    Handler für Tenant-Erstellung Use Case.
    
    Verantwortung:
    1. Validierung
    2. Tenant erstellen
    3. Owner-Membership erstellen
    4. Events emittieren
    """
    
    def __init__(
        self,
        tenant_repo: TenantRepository,
        membership_repo: MembershipRepository,
        event_bus: EventBus,
    ):
        self.tenant_repo = tenant_repo
        self.membership_repo = membership_repo
        self.event_bus = event_bus
    
    def handle(self, cmd: TenantCreateCommand) -> TenantCreateResult:
        # 1. Validierung
        if self.tenant_repo.slug_exists(cmd.slug):
            raise TenantSlugExistsError(cmd.slug)
        
        # 2. Tenant erstellen
        trial_ends = datetime.now() + timedelta(days=cmd.trial_days)
        tenant = Tenant(
            slug=cmd.slug,
            name=cmd.name,
            plan_code=cmd.plan_code,
            status=TenantStatus.TRIAL,
            trial_ends_at=trial_ends,
        )
        self.tenant_repo.save(tenant)
        
        # 3. Owner-Membership erstellen
        membership = TenantMembership(
            tenant_id=tenant.id,
            user_id=cmd.owner_user_id,
            role=TenantRole.OWNER,
        )
        self.membership_repo.save(membership)
        
        # 4. Events emittieren
        self.event_bus.publish(TenantCreatedEvent(
            tenant_id=tenant.id,
            owner_id=cmd.owner_user_id,
            plan_code=cmd.plan_code,
        ))
        
        return TenantCreateResult(
            tenant_id=tenant.id,
            membership_id=membership.id,
            trial_ends_at=trial_ends,
        )
```

### 6.2 Permission Grant Handler

```python
@dataclass(frozen=True)
class PermissionGrantCommand:
    """Command für Permission-Vergabe."""
    membership_id: UUID
    permission_code: str
    granted_by_id: int


class PermissionGrantHandler:
    """Handler für Permission-Vergabe."""
    
    def __init__(
        self,
        membership_repo: MembershipRepository,
        permission_repo: PermissionRepository,
        override_repo: PermissionOverrideRepository,
        auth_service: AuthorizationService,
        cache: PermissionCache,
        audit: AuditService,
    ):
        self.membership_repo = membership_repo
        self.permission_repo = permission_repo
        self.override_repo = override_repo
        self.auth_service = auth_service
        self.cache = cache
        self.audit = audit
    
    def handle(self, cmd: PermissionGrantCommand) -> None:
        # 1. Validieren: Permission existiert
        if not self.permission_repo.exists(cmd.permission_code):
            raise PermissionNotFoundError(cmd.permission_code)
        
        # 2. Validieren: Granter hat Berechtigung
        if not self.auth_service.can(cmd.granted_by_id, "members.edit"):
            raise PermissionDeniedError("Cannot grant permissions")
        
        # 3. Membership laden
        membership = self.membership_repo.get_by_id(cmd.membership_id)
        if not membership:
            raise MembershipNotFoundError(cmd.membership_id)
        
        # 4. Override erstellen/aktualisieren
        self.override_repo.upsert(
            membership_id=cmd.membership_id,
            permission_code=cmd.permission_code,
            allowed=True,
            granted_by_id=cmd.granted_by_id,
        )
        
        # 5. Cache invalidieren
        self.cache.invalidate(membership.tenant_id, membership.user_id)
        
        # 6. Audit
        self.audit.log(
            event="permission.granted",
            membership_id=cmd.membership_id,
            permission=cmd.permission_code,
            granted_by=cmd.granted_by_id,
        )
```

### 6.3 Tenant Lifecycle Handler

```python
@dataclass(frozen=True)
class TenantSuspendCommand:
    tenant_id: UUID
    reason: str
    suspended_by_id: int


class TenantSuspendHandler:
    """Handler für Tenant-Suspendierung."""
    
    def handle(self, cmd: TenantSuspendCommand) -> None:
        tenant = self.tenant_repo.get_by_id(cmd.tenant_id)
        if not tenant:
            raise TenantNotFoundError(cmd.tenant_id)
        
        if tenant.status == TenantStatus.DELETED:
            raise TenantError("Cannot suspend deleted tenant")
        
        tenant.suspend(reason=cmd.reason)
        
        self.event_bus.publish(TenantStatusChangedEvent(
            tenant_id=cmd.tenant_id,
            old_status=tenant.status,
            new_status=TenantStatus.SUSPENDED,
            changed_by=cmd.suspended_by_id,
            reason=cmd.reason,
        ))
```

---

## 7. Permission-System

### 7.1 Permission-Naming-Konvention

**Format:** `<resource>.<action>`

```python
class Permission(str, Enum):
    """Permission-Codes mit Kategorien."""
    
    # ═══════════════════════════════════════════════════════════════
    # TENANT
    # ═══════════════════════════════════════════════════════════════
    TENANT_VIEW = "tenant.view"
    TENANT_EDIT = "tenant.edit"
    TENANT_MANAGE = "tenant.manage"
    TENANT_DELETE = "tenant.delete"
    
    # ═══════════════════════════════════════════════════════════════
    # MEMBERS
    # ═══════════════════════════════════════════════════════════════
    MEMBERS_VIEW = "members.view"
    MEMBERS_INVITE = "members.invite"
    MEMBERS_EDIT = "members.edit"
    MEMBERS_REMOVE = "members.remove"
    
    # ═══════════════════════════════════════════════════════════════
    # STORIES (Domain-spezifisch)
    # ═══════════════════════════════════════════════════════════════
    STORIES_VIEW = "stories.view"
    STORIES_CREATE = "stories.create"
    STORIES_EDIT = "stories.edit"
    STORIES_DELETE = "stories.delete"
    STORIES_PUBLISH = "stories.publish"
    STORIES_EXPORT = "stories.export"
    
    # ═══════════════════════════════════════════════════════════════
    # AI FEATURES
    # ═══════════════════════════════════════════════════════════════
    AI_GENERATE = "ai.generate"
    AI_USE_PREMIUM = "ai.use_premium"
    
    # ═══════════════════════════════════════════════════════════════
    # SETTINGS & AUDIT
    # ═══════════════════════════════════════════════════════════════
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"
    AUDIT_VIEW = "audit.view"
    API_KEYS_MANAGE = "api_keys.manage"
```

### 7.2 Action-Vokabular

| Action | Bedeutung |
|--------|-----------|
| `view` | Lesen |
| `create` | Erstellen |
| `edit` | Bearbeiten |
| `delete` | Löschen |
| `manage` | Vollzugriff (CRUD + Admin) |
| `export` | Exportieren |
| `publish` | Veröffentlichen |
| `invite` | Einladen |
| `use_*` | Feature nutzen |

### 7.3 Role-Permission-Matrix

| Permission | Owner | Admin | Member | Viewer |
|------------|:-----:|:-----:|:------:|:------:|
| **Tenant** |
| `tenant.view` | ✅ | ✅ | ✅ | ✅ |
| `tenant.edit` | ✅ | ✅ | ❌ | ❌ |
| `tenant.manage` | ✅ | ✅ | ❌ | ❌ |
| `tenant.delete` | ✅ | ❌ | ❌ | ❌ |
| **Members** |
| `members.view` | ✅ | ✅ | ✅ | ✅ |
| `members.invite` | ✅ | ✅ | ❌ | ❌ |
| `members.edit` | ✅ | ✅ | ❌ | ❌ |
| `members.remove` | ✅ | ✅ | ❌ | ❌ |
| **Stories** |
| `stories.view` | ✅ | ✅ | ✅ | ✅ |
| `stories.create` | ✅ | ✅ | ✅ | ❌ |
| `stories.edit` | ✅ | ✅ | ✅ | ❌ |
| `stories.delete` | ✅ | ✅ | ❌ | ❌ |
| `stories.publish` | ✅ | ✅ | ❌ | ❌ |
| **AI** |
| `ai.generate` | ✅ | ✅ | ✅ | ❌ |
| `ai.use_premium` | ✅ | ✅ | ❌ | ❌ |

### 7.4 Permission-Resolution-Algorithmus

```python
class PermissionResolver:
    """
    Deterministische Permission-Resolution.
    
    Reihenfolge:
    1. Override DENY → DENIED
    2. Override ALLOW → GRANTED
    3. Role Permission → GRANTED/DENIED
    """
    
    def resolve(
        self,
        membership: TenantMembership,
        permission_code: str,
    ) -> PermissionResult:
        # 1. Override prüfen
        override = self.override_repo.get(
            membership.id,
            permission_code,
        )
        
        if override is not None:
            return PermissionResult(
                granted=override.allowed,
                permission=permission_code,
                source="override",
            )
        
        # 2. Role-Permission prüfen
        has_role_perm = self.role_permission_repo.has(
            membership.role,
            permission_code,
        )
        
        return PermissionResult(
            granted=has_role_perm,
            permission=permission_code,
            source="role",
        )
```

---

## 8. Row Level Security (RLS)

### 8.1 RLS-Policies

```sql
-- Enable RLS on tenant-scoped tables
ALTER TABLE some_domain_table ENABLE ROW LEVEL SECURITY;

-- SELECT Policy
CREATE POLICY tenant_isolation_select
    ON some_domain_table
    FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- INSERT Policy (oft vergessen!)
CREATE POLICY tenant_isolation_insert
    ON some_domain_table
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

-- UPDATE Policy
CREATE POLICY tenant_isolation_update
    ON some_domain_table
    FOR UPDATE
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- DELETE Policy
CREATE POLICY tenant_isolation_delete
    ON some_domain_table
    FOR DELETE
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### 8.2 Session-Context (Django Middleware)

```python
class TenantContextMiddleware:
    """Setzt PostgreSQL Session-Variablen für RLS."""
    
    def __call__(self, request):
        if request.tenant and request.user.is_authenticated:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.tenant_id = %s",
                    [str(request.tenant.id)]
                )
                cursor.execute(
                    "SET LOCAL app.user_id = %s",
                    [str(request.user.id)]
                )
        
        return self.get_response(request)
```

### 8.3 Bypass für Admin/Migrations

```sql
-- Admin-Rolle ohne RLS
CREATE ROLE platform_admin BYPASSRLS;

-- Für Migrationen
GRANT platform_admin TO migration_user;
```

---

## 9. Naming Conventions

### 9.1 Tabellen

| Convention | Format | Beispiel |
|------------|--------|----------|
| Django-Default | `{app_label}_{model_name}` | `bfagent_core_tenant` |
| Kurzform | `core_{entity}` | `core_tenant` |
| Join-Tabelle | `core_{entity1}_{entity2}` | `core_tenant_membership` |

**Entscheidung:** Kurzform `core_*` für bessere Lesbarkeit.

### 9.2 Felder

| Typ | Convention | Beispiel |
|-----|------------|----------|
| Primary Key | `id` | `id UUID` |
| Foreign Key | `{entity}_id` | `tenant_id` |
| Status | `status` | `status TEXT` |
| Timestamps | `{action}_at` | `created_at`, `deleted_at` |
| Booleans | `is_{state}` oder `{action}ed` | `is_active`, `enabled` |
| Codes | `{entity}_code` | `plan_code`, `permission_code` |

### 9.3 Enums/Choices

```python
class TenantStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"

class TenantRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
```

**Convention:** `snake_case` für Values, `UPPER_CASE` für Python-Namen.

### 9.4 Handler/Commands

| Type | Format | Beispiel |
|------|--------|----------|
| Command | `{Entity}{Action}Command` | `TenantCreateCommand` |
| Result | `{Entity}{Action}Result` | `TenantCreateResult` |
| Handler | `{Entity}{Action}Handler` | `TenantCreateHandler` |
| Event | `{Entity}{Action}Event` | `TenantCreatedEvent` |

---

## 10. Caching-Strategie

### 10.1 Cache-Design

```python
class PermissionCache:
    """
    Permission-Cache mit Fail-Closed.
    
    Design:
    - Key: (tenant_id, user_id)
    - Value: frozenset[str] (effective permissions)
    - TTL: 60 Sekunden
    - Fail-Closed: Bei Fehler → deny
    """
    
    TTL = 60  # Sekunden
    
    def get(self, tenant_id: UUID, user_id: int) -> frozenset[str] | None:
        key = f"perms:{tenant_id}:{user_id}"
        try:
            cached = cache.get(key)
            if cached:
                return frozenset(cached)
        except Exception:
            logger.warning("Cache read failed, falling back to DB")
        return None
    
    def set(self, tenant_id: UUID, user_id: int, perms: frozenset[str]) -> None:
        key = f"perms:{tenant_id}:{user_id}"
        try:
            cache.set(key, list(perms), timeout=self.TTL)
        except Exception:
            logger.warning("Cache write failed")
    
    def invalidate(self, tenant_id: UUID, user_id: int) -> None:
        key = f"perms:{tenant_id}:{user_id}"
        cache.delete(key)
```

### 10.2 Invalidierung

```python
# Nach Permission-Änderung
from django.db import transaction

@transaction.on_commit
def invalidate_on_permission_change():
    permission_cache.invalidate(tenant_id, user_id)
```

---

## 11. Events & Audit

### 11.1 Domain Events

```python
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True)
class TenantCreatedEvent:
    tenant_id: UUID
    owner_id: int
    plan_code: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class TenantStatusChangedEvent:
    tenant_id: UUID
    old_status: str
    new_status: str
    changed_by: int
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class MembershipCreatedEvent:
    membership_id: UUID
    tenant_id: UUID
    user_id: int
    role: str
    invited_by: int | None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class PermissionGrantedEvent:
    membership_id: UUID
    permission_code: str
    granted_by: int
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class PermissionRevokedEvent:
    membership_id: UUID
    permission_code: str
    revoked_by: int
    timestamp: datetime = field(default_factory=datetime.now)
```

### 11.2 Audit-Tabelle

```sql
CREATE TABLE core_permission_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id UUID NOT NULL REFERENCES core_tenant_membership(id),
    permission_code TEXT NOT NULL,
    action TEXT NOT NULL,  -- 'grant', 'revoke', 'clear'
    performed_by INTEGER REFERENCES auth_user(id),
    performed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    previous_value BOOLEAN,
    new_value BOOLEAN
);

CREATE INDEX core_permission_audit_membership_idx 
    ON core_permission_audit(membership_id);
CREATE INDEX core_permission_audit_performed_at_idx 
    ON core_permission_audit(performed_at);
```

---

## 12. Exceptions & Error Handling

### 12.1 Exception-Hierarchy

```python
# packages/bfagent-core/src/bfagent_core/exceptions.py

class PlatformError(Exception):
    """Base class für alle Platform-Fehler."""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# TENANT ERRORS
# ═══════════════════════════════════════════════════════════════════════════

class TenantError(PlatformError):
    """Basis für Tenant-bezogene Fehler."""
    pass

class TenantNotFoundError(TenantError):
    def __init__(self, tenant_id):
        super().__init__(f"Tenant not found: {tenant_id}")
        self.tenant_id = tenant_id

class TenantSlugExistsError(TenantError):
    def __init__(self, slug):
        super().__init__(f"Tenant slug already exists: {slug}")
        self.slug = slug

class TenantSuspendedError(TenantError):
    def __init__(self, tenant_id):
        super().__init__(f"Tenant is suspended: {tenant_id}")
        self.tenant_id = tenant_id

class TenantDeletedError(TenantError):
    def __init__(self, tenant_id):
        super().__init__(f"Tenant is deleted: {tenant_id}")
        self.tenant_id = tenant_id


# ═══════════════════════════════════════════════════════════════════════════
# MEMBERSHIP ERRORS
# ═══════════════════════════════════════════════════════════════════════════

class MembershipError(PlatformError):
    """Basis für Membership-bezogene Fehler."""
    pass

class MembershipNotFoundError(MembershipError):
    def __init__(self, membership_id):
        super().__init__(f"Membership not found: {membership_id}")
        self.membership_id = membership_id

class MembershipExistsError(MembershipError):
    def __init__(self, tenant_id, user_id):
        super().__init__(f"User {user_id} is already member of tenant {tenant_id}")
        self.tenant_id = tenant_id
        self.user_id = user_id

class NoMembershipError(MembershipError):
    def __init__(self, tenant_id, user_id):
        super().__init__(f"User {user_id} has no membership in tenant {tenant_id}")
        self.tenant_id = tenant_id
        self.user_id = user_id


# ═══════════════════════════════════════════════════════════════════════════
# PERMISSION ERRORS
# ═══════════════════════════════════════════════════════════════════════════

class PermissionError(PlatformError):
    """Basis für Permission-bezogene Fehler."""
    pass

class PermissionDeniedError(PermissionError):
    def __init__(self, permission: str, message: str = None):
        super().__init__(message or f"Permission denied: {permission}")
        self.permission = permission

class PermissionNotFoundError(PermissionError):
    def __init__(self, permission_code):
        super().__init__(f"Permission not found: {permission_code}")
        self.permission_code = permission_code
```

### 12.2 Exception-Handling in Views

```python
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from bfagent_core.exceptions import PermissionDeniedError

class ExceptionMiddleware:
    """Konvertiert Platform-Exceptions zu HTTP-Responses."""
    
    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDeniedError):
            raise DjangoPermissionDenied(str(exception))
        
        if isinstance(exception, TenantNotFoundError):
            return HttpResponseNotFound("Tenant not found")
        
        if isinstance(exception, TenantSuspendedError):
            return HttpResponseForbidden("Tenant is suspended")
        
        return None
```

---

## 13. Migration & Rollout

### 13.1 Zero-Breaking-Change-Strategie

```
Phase 1: Schema (Tag 1)
├── Tabellen additiv einführen
├── Keine bestehenden Tabellen ändern
└── Verifizieren: Neue Tabellen existieren

Phase 2: Default-Tenant (Tag 1-2)
├── Default-Tenant für bestehende Daten erstellen
├── Bestehende User als Owner zuweisen
└── Backfill in Batches

Phase 3: Dual-Write (Tag 2-3)
├── Neue Writes gehen in neue Tabellen
├── Alte Pfade bleiben aktiv
└── Monitoring beider Systeme

Phase 4: Migration (Tag 3-4)
├── Bestehende Daten migrieren
├── Constraints aktivieren
└── RLS-Policies aktivieren

Phase 5: Cleanup (Tag 5)
├── Alte Pfade entfernen
├── Alte Tabellen archivieren
└── Dokumentation aktualisieren
```

### 13.2 Rollback-Strategie

```sql
-- Im Notfall: RLS deaktivieren
ALTER TABLE some_table DISABLE ROW LEVEL SECURITY;

-- Constraint entfernen
ALTER TABLE core_tenant DROP CONSTRAINT tenant_status_chk;

-- Dokumentiert in: ops/runbooks/rbac-rollback.md
```

---

## 14. API & Decorators

### 14.1 Decorators für Function-Based Views

```python
from bfagent_core.permissions import require_permission, require_role, Permission

@require_permission(Permission.STORIES_CREATE)
def create_story(request):
    """User hat Permission."""
    ...

@require_role("owner", "admin")
def admin_dashboard(request):
    """Nur Owner/Admin."""
    ...

@require_any_permission(Permission.STORIES_EDIT, Permission.STORIES_DELETE)
def modify_story(request, story_id):
    """Mindestens eine Permission."""
    ...

@require_all_permissions(Permission.STORIES_EDIT, Permission.STORIES_PUBLISH)
def publish_story(request, story_id):
    """Alle Permissions nötig."""
    ...

@require_tenant_access
def tenant_dashboard(request):
    """Nur Membership nötig."""
    ...
```

### 14.2 Mixins für Class-Based Views

```python
from django.views.generic import ListView, DeleteView
from bfagent_core.permissions import TenantPermissionMixin, Permission

class StoryListView(TenantPermissionMixin, ListView):
    required_permission = Permission.STORIES_VIEW
    model = Story

class StoryDeleteView(TenantPermissionMixin, DeleteView):
    required_role = "admin"
    model = Story
```

### 14.3 DRF Integration

```python
from rest_framework.generics import ListAPIView
from bfagent_core.permissions import TenantAPIPermissionMixin, Permission

class StoryListAPI(TenantAPIPermissionMixin, ListAPIView):
    required_permission = Permission.STORIES_VIEW
    serializer_class = StorySerializer
```

### 14.4 Template-Integration

```html
{% if 'stories.delete' in view.get_user_permissions %}
    <button class="btn-danger">Delete</button>
{% endif %}

{% if 'stories.publish' in view.get_user_permissions %}
    <button class="btn-primary">Publish</button>
{% endif %}
```

---

## 15. Implementierung

### 15.1 Package-Struktur

```
packages/bfagent-core/src/bfagent_core/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── tenant.py           # Tenant, TenantStatus
│   └── membership.py       # TenantMembership, TenantRole
├── repositories/
│   ├── __init__.py
│   ├── tenant.py           # TenantRepository
│   ├── membership.py       # MembershipRepository
│   └── permission.py       # PermissionRepository
├── handlers/
│   ├── __init__.py
│   ├── tenant.py           # TenantCreateHandler, etc.
│   ├── membership.py       # MembershipInviteHandler, etc.
│   └── permission.py       # PermissionGrantHandler, etc.
├── services/
│   ├── __init__.py
│   ├── authorization.py    # AuthorizationService
│   └── lifecycle.py        # TenantLifecycleService
├── permissions/
│   ├── __init__.py
│   ├── enums.py            # Permission Enum, ROLE_PERMISSIONS
│   ├── checker.py          # PermissionChecker (mit Cache)
│   ├── resolver.py         # PermissionResolver
│   ├── decorators.py       # @require_permission, @require_role
│   └── mixins.py           # TenantPermissionMixin, etc.
├── events/
│   ├── __init__.py
│   ├── tenant.py           # TenantCreatedEvent, etc.
│   └── bus.py              # EventBus
├── exceptions.py           # Exception-Hierarchy
├── cache.py                # PermissionCache
└── migrations/
    ├── 0002_tenant.py
    ├── 0003_membership.py
    └── 0004_permissions.py
```

### 15.2 Aufwandschätzung

| Komponente | Aufwand |
|------------|---------|
| Models & Migrations | 1 Tag |
| Repositories | 0.5 Tag |
| Handlers | 1 Tag |
| Services | 1 Tag |
| Permissions/Decorators | 1 Tag |
| Events & Audit | 0.5 Tag |
| Tests | 1.5 Tag |
| Dokumentation | 0.5 Tag |
| **Gesamt** | **7 Tage** |

---

## 16. Konsequenzen

### 16.1 Positive Konsequenzen

1. **Strikte Isolation** – RLS garantiert Tenant-Separation
2. **Auditierbar** – Alle Permission-Änderungen nachvollziehbar
3. **Skalierbar** – O(1) Permission-Checks durch Caching
4. **Testbar** – Klare Interfaces, Dependency Injection
5. **Erweiterbar** – Neue Permissions ohne Schema-Änderung
6. **DB-Enforced** – Lifecycle-Constraints in PostgreSQL

### 16.2 Negative Konsequenzen

1. **Mehr Tabellen** – 10+ statt 2-3
2. **Höherer Initialaufwand** – ~7 Tage
3. **Komplexität** – Handler-Pattern, Events, Repositories

### 16.3 Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Cache stale | Mittel | Mittel | TTL=60s + on_commit invalidation |
| Performance bei vielen Permissions | Niedrig | Mittel | FrozenSet für O(1) Lookup |
| Breaking Changes | Niedrig | Hoch | Additives Design, Dual-Write |
| RLS-Bypass | Niedrig | Kritisch | platform_admin Role dokumentiert |

---

## Appendix A: Fixture-Daten für Permissions

```sql
-- core_permission
INSERT INTO core_permission (code, description, category) VALUES
('tenant.view', 'Tenant-Info sehen', 'tenant'),
('tenant.edit', 'Tenant-Einstellungen ändern', 'tenant'),
('tenant.manage', 'Tenant verwalten (Billing, Plan)', 'tenant'),
('tenant.delete', 'Tenant löschen', 'tenant'),
('members.view', 'Mitgliederliste sehen', 'members'),
('members.invite', 'Mitglieder einladen', 'members'),
('members.edit', 'Mitglieder-Rollen ändern', 'members'),
('members.remove', 'Mitglieder entfernen', 'members'),
('stories.view', 'Stories lesen', 'stories'),
('stories.create', 'Stories erstellen', 'stories'),
('stories.edit', 'Stories bearbeiten', 'stories'),
('stories.delete', 'Stories löschen', 'stories'),
('stories.publish', 'Stories veröffentlichen', 'stories'),
('stories.export', 'Stories exportieren', 'stories'),
('ai.generate', 'AI-Generierung nutzen', 'ai'),
('ai.use_premium', 'Premium-AI-Models nutzen', 'ai'),
('settings.view', 'Einstellungen sehen', 'settings'),
('settings.edit', 'Einstellungen ändern', 'settings'),
('audit.view', 'Audit-Log einsehen', 'audit'),
('api_keys.manage', 'API-Keys verwalten', 'api');

-- core_role_permission (Owner)
INSERT INTO core_role_permission (role, permission_code)
SELECT 'owner', code FROM core_permission;

-- core_role_permission (Admin) - alle außer tenant.delete
INSERT INTO core_role_permission (role, permission_code)
SELECT 'admin', code FROM core_permission WHERE code <> 'tenant.delete';

-- core_role_permission (Member)
INSERT INTO core_role_permission (role, permission_code)
SELECT 'member', code FROM core_permission 
WHERE code IN (
    'tenant.view', 'members.view', 
    'stories.view', 'stories.create', 'stories.edit', 'stories.export',
    'ai.generate', 'settings.view'
);

-- core_role_permission (Viewer)
INSERT INTO core_role_permission (role, permission_code)
SELECT 'viewer', code FROM core_permission 
WHERE code IN ('tenant.view', 'members.view', 'stories.view', 'settings.view');
```

---

## Appendix B: Settings

```python
# settings.py

# Tenant-Model für Middleware
TENANT_MODEL = "bfagent_core.Tenant"
TENANT_SLUG_FIELD = "slug"
TENANT_ID_FIELD = "id"

# Base Domain für Subdomains
TENANT_BASE_DOMAIN = "platform.io"  # demo.platform.io, acme.platform.io

# Dev-Mode: Admin ohne Tenant erlauben
TENANT_ALLOW_LOCALHOST = DEBUG

# Permission-Cache
PERMISSION_CACHE_TTL = 60  # Sekunden
PERMISSION_CACHE_BACKEND = "default"
```

---

**Letzte Aktualisierung:** 2026-02-01  
**Nächste Review:** 2026-03-01  
**Referenzen:**
- `docs/concepts/README.md`
- `docs/concepts/tenant.py`
- `docs/concepts/decorators.py`
