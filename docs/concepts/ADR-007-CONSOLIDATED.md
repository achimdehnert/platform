# ADR-007: Tenant- & RBAC-Architektur (Konsolidiert)

**Status:** ACCEPTED  
**Version:** 3.0  
**Datum:** 2026-02-01  
**Ersetzt:** ADR-007-FINAL-PRODUCTION.md, adr_007_optimized_tenant_rbac.md

---

## Executive Summary

Dieses ADR definiert die **vollständige Multi-Tenancy & RBAC-Architektur** für die Platform. Es konsolidiert alle bisherigen Entwürfe und folgt strikt den Platform-Prinzipien:

| Prinzip | Umsetzung |
|---------|-----------|
| **Database-First** | Constraints, RLS, Permission-Tabellen in PostgreSQL |
| **Strikte Normalisierung** | Keine JSONB für kritische Daten |
| **Separation of Concerns** | DB → Repository → Service → Handler → View |
| **Handler-Pattern** | Command/Result für alle Use Cases |
| **Zero Breaking Changes** | Soft-Delete, additive Migrationen |
| **SSO-Ready** | UUID für user_id (nicht INTEGER) |

---

## Inhaltsverzeichnis

1. [Kontext & Problemstellung](#1-kontext--problemstellung)
2. [Ziele & Nicht-Ziele](#2-ziele--nicht-ziele)
3. [Architektur-Übersicht](#3-architektur-übersicht)
4. [Datenmodell](#4-datenmodell)
5. [Layer-Architektur](#5-layer-architektur)
6. [Handler-Pattern](#6-handler-pattern)
7. [Permission-System](#7-permission-system)
8. [Row Level Security](#8-row-level-security)
9. [Caching-Strategie](#9-caching-strategie)
10. [Events & Audit](#10-events--audit)
11. [Exceptions](#11-exceptions)
12. [API & Decorators](#12-api--decorators)
13. [Migration & Rollout](#13-migration--rollout)
14. [Implementierung](#14-implementierung)
15. [Konsequenzen](#15-konsequenzen)

---

## 1. Kontext & Problemstellung

### Bestehende Architektur (bfagent-core)

```
packages/bfagent-core/
├── context.py          # ✅ Contextvars (tenant_id, user_id, request_id)
├── db.py               # ✅ set_db_tenant() für RLS (app.current_tenant)
├── middleware.py       # ✅ SubdomainTenantMiddleware
├── models.py           # ✅ AuditEvent, OutboxMessage
└── audit.py            # ✅ emit_audit_event()
```

**Stärken:**
- ✅ Contextvars-Pattern funktioniert
- ✅ RLS-Integration mit `app.current_tenant`
- ✅ Middleware-Konzept ist solide

**Lücken:**
- ❌ Kein zentrales Tenant-Model
- ❌ Keine User-Tenant-Zuordnung (Memberships)
- ❌ Kein Permission-System
- ❌ Kein Lifecycle-Management
- ❌ user_id als INTEGER (nicht SSO-ready)

---

## 2. Ziele & Nicht-Ziele

### Ziele

| ID | Anforderung | Priorität |
|----|-------------|-----------|
| R1 | Zentrales Tenant-Model mit Lifecycle-Management | **Must** |
| R2 | User-Tenant-Zuordnung mit Rollen (RBAC) | **Must** |
| R3 | Voll normalisierte Permissions (keine JSONB) | **Must** |
| R4 | Permission-Overrides auf Membership-Ebene | **Should** |
| R5 | Integration mit bestehendem RLS (`app.current_tenant`) | **Must** |
| R6 | Handler-Pattern für alle Use Cases | **Must** |
| R7 | Event-System für Audit & Integration | **Should** |
| R8 | Caching mit Fail-Closed & Version-Tag | **Should** |
| R9 | Zero Breaking Changes | **Must** |
| R10 | SSO-Ready (UUID für user_id) | **Must** |

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
│  │ • Django Views mit @require_permission                              │   │
│  │ • DRF APIViews mit TenantAPIPermissionMixin                        │   │
│  │ • HTMX Partials (Progressive Enhancement)                          │   │
│  │ Verantwortung: HTTP-Handling, Serialization - KEINE Security-Logik │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ APPLICATION LAYER (Handlers)                                        │   │
│  │ • TenantCreateHandler, MembershipInviteHandler                      │   │
│  │ • Command/Result Pattern mit @transaction.atomic                    │   │
│  │ Verantwortung: Use Case Orchestration                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DOMAIN LAYER (Services)                                             │   │
│  │ • AuthorizationService.can(user, tenant, permission)                │   │
│  │ • TenantLifecycleService                                            │   │
│  │ Verantwortung: Business Logic - KEINE HTTP-/Template-Abhängigkeit   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ INFRASTRUCTURE LAYER                                                │   │
│  │ • Repositories (TenantRepository, MembershipRepository)             │   │
│  │ • PermissionCache (mit Version-Tag)                                 │   │
│  │ • EventBus                                                          │   │
│  │ Verantwortung: Data Access, External Services                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DATABASE LAYER (PostgreSQL) - FINAL ENFORCER                        │   │
│  │ • Row Level Security (app.current_tenant)                           │   │
│  │ • CHECK Constraints (Lifecycle-Invarianten)                         │   │
│  │ • Foreign Keys (Referential Integrity)                              │   │
│  │ • Triggers (updated_at, permission_version)                         │   │
│  │ Verantwortung: Data Integrity, Isolation, Enforcement               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Datenmodell

### 4.1 Entity-Relationship-Diagramm

```
┌─────────────────┐       ┌────────────────────────┐       ┌─────────────────┐
│   core_plan     │       │ core_tenant_membership │       │   core_user     │
├─────────────────┤       ├────────────────────────┤       ├─────────────────┤
│ code (PK)       │       │ id (UUID) PK           │       │ id (UUID) PK    │
│ name            │       │ tenant_id FK           │──────▶│ external_id     │
│ is_public       │       │ user_id FK             │       │ email           │
│ sort_order      │       │ role                   │       └─────────────────┘
└────────┬────────┘       │ status                 │
         │                │ permission_version     │
         │                └──────────┬─────────────┘
         ▼                           │
┌─────────────────┐                  │
│  core_tenant    │                  ▼
├─────────────────┤       ┌────────────────────────────────┐
│ id (UUID) PK    │       │ core_membership_permission_    │
│ slug            │       │ override                       │
│ name            │       ├────────────────────────────────┤
│ status          │       │ membership_id FK               │
│ plan_code FK    │───────│ permission_code FK             │
│ created_at      │       │ allowed BOOLEAN                │
│ updated_at      │       │ expires_at                     │
└─────────────────┘       │ reason                         │
        │                 └────────────────────────────────┘
        │                             │
        ▼                             ▼
┌─────────────────┐       ┌─────────────────────────────────┐
│ core_tenant_    │       │ core_permission                 │
│ quota           │       ├─────────────────────────────────┤
├─────────────────┤       │ code (PK)                       │
│ tenant_id FK    │       │ description                     │
│ quota_code      │       │ category                        │
│ limit_value     │       └─────────────────────────────────┘
│ current_value   │                   ▲
└─────────────────┘                   │
                          ┌─────────────────────────────────┐
                          │ core_role_permission            │
                          ├─────────────────────────────────┤
                          │ role                            │
                          │ permission_code FK              │
                          └─────────────────────────────────┘
```

### 4.2 Core Plan (NEU - fehlte im Original)

```sql
-- Plan-Registry (Single Source of Truth für Pricing/Features)
CREATE TABLE core_plan (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN NOT NULL DEFAULT true,
    monthly_price_cents INTEGER,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Default-Pläne
INSERT INTO core_plan (code, name, sort_order) VALUES
    ('free', 'Free', 0),
    ('starter', 'Starter', 10),
    ('professional', 'Professional', 20),
    ('enterprise', 'Enterprise', 30);
```

### 4.3 Core Tenant

```sql
CREATE TABLE core_tenant (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'trial',
    plan_code TEXT NOT NULL DEFAULT 'free' REFERENCES core_plan(code),
    
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
CREATE INDEX core_tenant_status_idx ON core_tenant(status) WHERE status <> 'deleted';
CREATE INDEX core_tenant_plan_idx ON core_tenant(plan_code);
```

### 4.4 Core User (SSO-Ready)

```sql
-- Eigene User-Tabelle für SSO-Flexibilität
-- Kann parallel zu auth_user existieren (Migration später)
CREATE TABLE core_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- SSO/IAM Integration
    external_id TEXT UNIQUE,  -- Auth0 sub, Okta uid, etc.
    provider TEXT,            -- 'auth0', 'okta', 'local'
    
    -- Profile
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    email_verified_at TIMESTAMPTZ,
    
    -- Legacy Bridge (für Migration von auth_user)
    legacy_user_id INTEGER UNIQUE,  -- FK zu auth_user.id
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX core_user_email_idx ON core_user(email);
CREATE INDEX core_user_external_idx ON core_user(provider, external_id) WHERE external_id IS NOT NULL;
```

### 4.5 Tenant Membership

```sql
CREATE TABLE core_tenant_membership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES core_tenant(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member',
    status TEXT NOT NULL DEFAULT 'active',
    
    -- Permission-Cache-Invalidierung
    permission_version INTEGER NOT NULL DEFAULT 1,
    
    -- Invitation
    invited_by_id UUID REFERENCES core_user(id) ON DELETE SET NULL,
    invited_at TIMESTAMPTZ,
    invitation_expires_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    CONSTRAINT membership_role_chk CHECK (
        role IN ('owner', 'admin', 'member', 'viewer')
    ),
    CONSTRAINT membership_status_chk CHECK (
        status IN ('pending', 'active', 'deactivated')
    ),
    CONSTRAINT membership_unique UNIQUE (tenant_id, user_id),
    -- Pending muss expires_at haben
    CONSTRAINT membership_pending_chk CHECK (
        status <> 'pending' OR invitation_expires_at IS NOT NULL
    )
);

CREATE INDEX core_membership_tenant_idx ON core_tenant_membership(tenant_id);
CREATE INDEX core_membership_user_idx ON core_tenant_membership(user_id);
CREATE INDEX core_membership_role_idx ON core_tenant_membership(role);
CREATE INDEX core_membership_status_idx ON core_tenant_membership(status) WHERE status = 'active';
CREATE INDEX core_membership_pending_idx ON core_tenant_membership(invitation_expires_at) 
    WHERE status = 'pending';

-- Trigger für permission_version increment
CREATE OR REPLACE FUNCTION trg_membership_permission_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.permission_version := OLD.permission_version + 1;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER membership_permission_version_trigger
    BEFORE UPDATE OF role ON core_tenant_membership
    FOR EACH ROW
    EXECUTE FUNCTION trg_membership_permission_version();
```

### 4.6 Permission System (Voll Normalisiert)

```sql
-- Permission-Registry
CREATE TABLE core_permission (
    code TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX core_permission_category_idx ON core_permission(category);

-- Role-Permission-Mapping (statisch)
CREATE TABLE core_role_permission (
    role TEXT NOT NULL,
    permission_code TEXT NOT NULL REFERENCES core_permission(code) ON DELETE CASCADE,
    
    PRIMARY KEY (role, permission_code),
    CONSTRAINT role_chk CHECK (role IN ('owner', 'admin', 'member', 'viewer'))
);

-- Membership-Override (dynamisch, mit Expiration)
CREATE TABLE core_membership_permission_override (
    membership_id UUID NOT NULL REFERENCES core_tenant_membership(id) ON DELETE CASCADE,
    permission_code TEXT NOT NULL REFERENCES core_permission(code) ON DELETE CASCADE,
    allowed BOOLEAN NOT NULL,
    
    -- Expiration (optional)
    expires_at TIMESTAMPTZ,
    reason TEXT,
    
    -- Audit
    granted_by_id UUID REFERENCES core_user(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    PRIMARY KEY (membership_id, permission_code)
);

CREATE INDEX core_override_expires_idx ON core_membership_permission_override(expires_at) 
    WHERE expires_at IS NOT NULL;

-- Trigger: Override ändert permission_version
CREATE OR REPLACE FUNCTION trg_override_bump_version()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE core_tenant_membership 
    SET permission_version = permission_version + 1,
        updated_at = now()
    WHERE id = COALESCE(NEW.membership_id, OLD.membership_id);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER override_bump_version_trigger
    AFTER INSERT OR UPDATE OR DELETE ON core_membership_permission_override
    FOR EACH ROW
    EXECUTE FUNCTION trg_override_bump_version();
```

### 4.7 Quota & Feature Tables

```sql
-- Plan → Features Mapping
CREATE TABLE core_plan_feature (
    plan_code TEXT NOT NULL REFERENCES core_plan(code) ON DELETE CASCADE,
    feature_code TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT false,
    
    PRIMARY KEY (plan_code, feature_code)
);

-- Plan → Quota Defaults
CREATE TABLE core_plan_quota (
    plan_code TEXT NOT NULL REFERENCES core_plan(code) ON DELETE CASCADE,
    quota_code TEXT NOT NULL,
    default_limit BIGINT NOT NULL,
    
    PRIMARY KEY (plan_code, quota_code)
);

-- Tenant-spezifische Quotas (überschreibt Plan-Defaults)
CREATE TABLE core_tenant_quota (
    tenant_id UUID NOT NULL REFERENCES core_tenant(id) ON DELETE CASCADE,
    quota_code TEXT NOT NULL,
    limit_value BIGINT NOT NULL,
    current_value BIGINT NOT NULL DEFAULT 0,
    reset_at TIMESTAMPTZ,
    
    PRIMARY KEY (tenant_id, quota_code)
);

CREATE INDEX core_tenant_quota_reset_idx ON core_tenant_quota(reset_at) WHERE reset_at IS NOT NULL;

-- Tenant-spezifische Features (überschreibt Plan-Defaults)
CREATE TABLE core_tenant_feature (
    tenant_id UUID NOT NULL REFERENCES core_tenant(id) ON DELETE CASCADE,
    feature_code TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT false,
    
    PRIMARY KEY (tenant_id, feature_code)
);
```

### 4.8 Audit-Tabelle

```sql
CREATE TABLE core_permission_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id UUID NOT NULL REFERENCES core_tenant_membership(id) ON DELETE CASCADE,
    permission_code TEXT NOT NULL,
    action TEXT NOT NULL,  -- 'grant', 'revoke', 'expire'
    performed_by_id UUID REFERENCES core_user(id) ON DELETE SET NULL,
    performed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    previous_value BOOLEAN,
    new_value BOOLEAN,
    reason TEXT,
    
    -- Denormalized for query performance
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL
);

CREATE INDEX core_permission_audit_membership_idx ON core_permission_audit(membership_id);
CREATE INDEX core_permission_audit_tenant_idx ON core_permission_audit(tenant_id, performed_at DESC);
CREATE INDEX core_permission_audit_performed_at_idx ON core_permission_audit(performed_at DESC);
```

---

## 5. Layer-Architektur

### 5.1 Separation of Concerns

| Layer | Verantwortung | Darf NICHT |
|-------|---------------|------------|
| **Database** | Constraints, RLS, Referential Integrity | - |
| **Repository** | Data Access, Queries, Batch-Ops | Business Logic |
| **Service** | Business Logic, Domain Rules | HTTP-Handling |
| **Handler** | Use Case Orchestration, Transactions | Direct DB Access |
| **View** | HTTP, Serialization | Permission Logic |
| **Template/JS** | Darstellung, Progressive Enhancement | Business/Security Logic |

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
from typing import Optional, Sequence
from bfagent_core.models import Tenant

class TenantRepositoryInterface(ABC):
    """Repository-Interface für Tenant-Zugriff."""
    
    @abstractmethod
    def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """Tenant by ID laden."""
        ...
    
    @abstractmethod
    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Tenant by Slug laden."""
        ...
    
    @abstractmethod
    def get_by_ids(self, tenant_ids: Sequence[UUID]) -> list[Tenant]:
        """Bulk-Load für N+1-Vermeidung."""
        ...
    
    @abstractmethod
    def slug_exists(self, slug: str) -> bool:
        """Prüft ob Slug bereits existiert."""
        ...
    
    @abstractmethod
    def save(self, tenant: Tenant) -> Tenant:
        """Tenant speichern (create/update)."""
        ...
    
    @abstractmethod
    def list_active(self, *, limit: int = 100, offset: int = 0) -> list[Tenant]:
        """Alle aktiven Tenants (paginiert)."""
        ...


class DjangoTenantRepository(TenantRepositoryInterface):
    """Django ORM Implementation."""
    
    def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        return Tenant.objects.filter(id=tenant_id).first()
    
    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        return Tenant.objects.active().filter(slug=slug).first()
    
    def get_by_ids(self, tenant_ids: Sequence[UUID]) -> list[Tenant]:
        return list(Tenant.objects.filter(id__in=tenant_ids))
    
    def slug_exists(self, slug: str) -> bool:
        return Tenant.objects.filter(slug=slug).exists()
    
    def save(self, tenant: Tenant) -> Tenant:
        tenant.full_clean()
        tenant.save()
        return tenant
    
    def list_active(self, *, limit: int = 100, offset: int = 0) -> list[Tenant]:
        return list(Tenant.objects.active()[offset:offset + limit])
```

---

## 6. Handler-Pattern

### 6.1 Command-Result-Pattern mit Transaction

```python
# packages/bfagent-core/src/bfagent_core/handlers/tenant.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from django.db import transaction

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
    owner_user_id: UUID
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
    4. Events emittieren (on_commit)
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
    
    @transaction.atomic
    def handle(self, cmd: TenantCreateCommand) -> TenantCreateResult:
        # 1. Validierung
        if self.tenant_repo.slug_exists(cmd.slug):
            raise TenantSlugExistsError(cmd.slug)
        
        # 2. Tenant erstellen
        trial_ends = datetime.now(timezone.utc) + timedelta(days=cmd.trial_days)
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
            status='active',
            accepted_at=datetime.now(timezone.utc),
        )
        self.membership_repo.save(membership)
        
        # 4. Events emittieren (nach Commit!)
        transaction.on_commit(lambda: self.event_bus.publish(TenantCreatedEvent(
            tenant_id=tenant.id,
            owner_id=cmd.owner_user_id,
            plan_code=cmd.plan_code,
        )))
        
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
    granted_by_id: UUID
    expires_at: datetime | None = None
    reason: str | None = None


class PermissionGrantHandler:
    """Handler für Permission-Vergabe."""
    
    def __init__(
        self,
        membership_repo: MembershipRepository,
        permission_repo: PermissionRepository,
        override_repo: PermissionOverrideRepository,
        auth_service: AuthorizationService,
        audit: AuditService,
    ):
        self.membership_repo = membership_repo
        self.permission_repo = permission_repo
        self.override_repo = override_repo
        self.auth_service = auth_service
        self.audit = audit
    
    @transaction.atomic
    def handle(self, cmd: PermissionGrantCommand) -> None:
        # 1. Validieren: Permission existiert
        if not self.permission_repo.exists(cmd.permission_code):
            raise PermissionNotFoundError(cmd.permission_code)
        
        # 2. Validieren: Granter hat Berechtigung
        if not self.auth_service.can(cmd.granted_by_id, "members.edit"):
            raise PermissionDeniedError("Cannot grant permissions")
        
        # 3. Membership laden (mit Lock)
        membership = self.membership_repo.get_by_id_for_update(cmd.membership_id)
        if not membership:
            raise MembershipNotFoundError(cmd.membership_id)
        
        # 4. Override erstellen/aktualisieren
        # (permission_version wird automatisch via Trigger erhöht)
        self.override_repo.upsert(
            membership_id=cmd.membership_id,
            permission_code=cmd.permission_code,
            allowed=True,
            granted_by_id=cmd.granted_by_id,
            expires_at=cmd.expires_at,
            reason=cmd.reason,
        )
        
        # 5. Audit (nach Commit)
        transaction.on_commit(lambda: self.audit.log(
            event="permission.granted",
            membership_id=cmd.membership_id,
            tenant_id=membership.tenant_id,
            user_id=membership.user_id,
            permission=cmd.permission_code,
            granted_by=cmd.granted_by_id,
            expires_at=cmd.expires_at,
        ))
```

---

## 7. Permission-System

### 7.1 Permission-Naming-Konvention

**Format:** `<resource>.<action>`

```python
class Permission(str, Enum):
    """Permission-Codes mit Kategorien."""
    
    # TENANT
    TENANT_VIEW = "tenant.view"
    TENANT_EDIT = "tenant.edit"
    TENANT_MANAGE = "tenant.manage"
    TENANT_DELETE = "tenant.delete"
    
    # MEMBERS
    MEMBERS_VIEW = "members.view"
    MEMBERS_INVITE = "members.invite"
    MEMBERS_EDIT = "members.edit"
    MEMBERS_REMOVE = "members.remove"
    
    # STORIES (Domain-spezifisch)
    STORIES_VIEW = "stories.view"
    STORIES_CREATE = "stories.create"
    STORIES_EDIT = "stories.edit"
    STORIES_DELETE = "stories.delete"
    STORIES_PUBLISH = "stories.publish"
    STORIES_EXPORT = "stories.export"
    
    # AI FEATURES
    AI_GENERATE = "ai.generate"
    AI_USE_PREMIUM = "ai.use_premium"
    
    # SETTINGS & AUDIT
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"
    AUDIT_VIEW = "audit.view"
    API_KEYS_MANAGE = "api_keys.manage"
```

### 7.2 Action-Vokabular (Einheitlich!)

| Action | Bedeutung | Keine Synonyme! |
|--------|-----------|-----------------|
| `view` | Lesen | ~~read, get, list~~ |
| `create` | Erstellen | ~~add, new~~ |
| `edit` | Bearbeiten | ~~update, modify~~ |
| `delete` | Löschen | ~~remove, destroy~~ |
| `manage` | Vollzugriff | ~~admin, full~~ |
| `export` | Exportieren | |
| `publish` | Veröffentlichen | |
| `invite` | Einladen | |
| `use_*` | Feature nutzen | |

### 7.3 Permission-Resolution-Algorithmus

```python
class PermissionResolver:
    """
    Deterministische Permission-Resolution.
    
    Reihenfolge:
    1. Override DENY → DENIED
    2. Override ALLOW (nicht expired) → GRANTED
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
            # Check expiration
            if override.expires_at and override.expires_at < datetime.now(timezone.utc):
                # Expired override = ignorieren
                pass
            else:
                return PermissionResult(
                    granted=override.allowed,
                    permission=permission_code,
                    source="override",
                    expires_at=override.expires_at,
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


# Für Batch-Checks (effizient!)
def resolve_all(self, membership: TenantMembership) -> frozenset[str]:
    """Alle effektiven Permissions als FrozenSet."""
    # 1. Basis: Role-Permissions
    perms = set(self.role_permission_repo.get_all(membership.role))
    
    # 2. Overrides anwenden
    now = datetime.now(timezone.utc)
    for override in self.override_repo.get_all(membership.id):
        if override.expires_at and override.expires_at < now:
            continue  # Expired
        if override.allowed:
            perms.add(override.permission_code)
        else:
            perms.discard(override.permission_code)
    
    return frozenset(perms)
```

### 7.4 Enum ↔ DB Sync-Strategie

```python
# permissions/sync.py
from django.db import transaction

def sync_permissions_to_db():
    """
    Sync Python Enum → DB.
    In Migrations oder Management-Command aufrufen.
    """
    from bfagent_core.models import CorePermission
    from bfagent_core.permissions import Permission
    
    with transaction.atomic():
        existing = set(CorePermission.objects.values_list('code', flat=True))
        
        for perm in Permission:
            category = perm.value.split(".")[0]
            CorePermission.objects.update_or_create(
                code=perm.value,
                defaults={
                    "description": perm.name.replace("_", " ").title(),
                    "category": category,
                    "is_active": True,
                }
            )
        
        # Warnung für DB-only Permissions
        enum_codes = {p.value for p in Permission}
        orphaned = existing - enum_codes
        if orphaned:
            logger.warning(f"DB-only permissions (not in Enum): {orphaned}")
```

---

## 8. Row Level Security

### 8.1 RLS-Policies

**WICHTIG:** Session-Variable ist `app.current_tenant` (konsistent mit bfagent-core!)

```sql
-- Enable RLS on tenant-scoped tables
ALTER TABLE some_domain_table ENABLE ROW LEVEL SECURITY;

-- SELECT Policy
CREATE POLICY tenant_isolation_select
    ON some_domain_table
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

-- INSERT Policy
CREATE POLICY tenant_isolation_insert
    ON some_domain_table
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);

-- UPDATE Policy
CREATE POLICY tenant_isolation_update
    ON some_domain_table
    FOR UPDATE
    USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

-- DELETE Policy
CREATE POLICY tenant_isolation_delete
    ON some_domain_table
    FOR DELETE
    USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
```

### 8.2 Middleware (erweitert bestehende)

```python
# bfagent_core/middleware.py - Erweiterung

class TenantPermissionMiddleware(MiddlewareMixin):
    """
    Erweitert SubdomainTenantMiddleware um Permission-Check.
    Reihenfolge: NACH SubdomainTenantMiddleware, NACH AuthenticationMiddleware.
    """
    
    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        # Skip wenn kein Tenant (Admin-Bereich)
        if not hasattr(request, 'tenant') or not request.tenant:
            return None
        
        # Skip wenn nicht authentifiziert
        if not request.user or not request.user.is_authenticated:
            return None
        
        # Membership laden
        user_id = self._get_user_uuid(request.user)
        membership = TenantMembership.objects.filter(
            tenant_id=request.tenant_id,
            user_id=user_id,
            status='active',
        ).first()
        
        if not membership:
            return HttpResponseForbidden("No membership in this tenant")
        
        # Membership an Request hängen
        request.membership = membership
        request.membership_id = membership.id
        request.user_role = membership.role
        
        return None
    
    def _get_user_uuid(self, user) -> UUID:
        """Bridge: Django User → Core User UUID."""
        # Wenn core_user.legacy_user_id gesetzt ist
        core_user = CoreUser.objects.filter(legacy_user_id=user.id).first()
        if core_user:
            return core_user.id
        # Fallback: User-ID als UUID (Migration pending)
        return UUID(int=user.id)
```

### 8.3 Bypass für Admin/Migrations

```sql
-- Admin-Rolle ohne RLS (für Migrationen, Background-Jobs)
CREATE ROLE platform_admin BYPASSRLS;

-- Für Migrationen
GRANT platform_admin TO migration_user;

-- Für Celery-Worker mit Cross-Tenant-Zugriff
GRANT platform_admin TO celery_worker;
```

---

## 9. Caching-Strategie

### 9.1 Cache-Design mit Version-Tag

```python
class PermissionCache:
    """
    Permission-Cache mit Version-Tag und Fail-Closed.
    
    Design:
    - Key: bfagent:perms:v1:{tenant_id}:{user_id}
    - Value: {"version": int, "permissions": list[str]}
    - TTL: 60 Sekunden
    - Fail-Closed: Bei Fehler → deny
    - Version-Check: Cache invalid wenn version != membership.permission_version
    """
    
    CACHE_KEY_PREFIX = "bfagent:perms:v1"
    TTL = 60  # Sekunden
    
    def _key(self, tenant_id: UUID, user_id: UUID) -> str:
        return f"{self.CACHE_KEY_PREFIX}:{tenant_id}:{user_id}"
    
    def get(
        self,
        tenant_id: UUID,
        user_id: UUID,
        expected_version: int,
    ) -> frozenset[str] | None:
        """
        Cache lesen mit Version-Check.
        Returns None wenn:
        - Cache miss
        - Version mismatch
        - Cache error (Fail-Closed)
        """
        key = self._key(tenant_id, user_id)
        try:
            cached = cache.get(key)
            if not cached:
                return None
            
            # Version-Check
            if cached.get("version") != expected_version:
                logger.debug(f"Cache version mismatch for {key}")
                return None
            
            return frozenset(cached.get("permissions", []))
            
        except Exception:
            logger.warning(f"Cache read failed for {key}", exc_info=True)
            return None  # Fail-Closed
    
    def set(
        self,
        tenant_id: UUID,
        user_id: UUID,
        version: int,
        permissions: frozenset[str],
    ) -> None:
        """Cache schreiben mit Version."""
        key = self._key(tenant_id, user_id)
        try:
            cache.set(
                key,
                {"version": version, "permissions": list(permissions)},
                timeout=self.TTL,
            )
        except Exception:
            logger.warning(f"Cache write failed for {key}", exc_info=True)
    
    def invalidate(self, tenant_id: UUID, user_id: UUID) -> None:
        """Explizite Invalidierung (Backup zu Version-Check)."""
        key = self._key(tenant_id, user_id)
        try:
            cache.delete(key)
        except Exception:
            pass  # Best-effort
```

### 9.2 Usage in AuthorizationService

```python
class AuthorizationService:
    """Service für Permission-Checks."""
    
    def __init__(
        self,
        membership_repo: MembershipRepository,
        resolver: PermissionResolver,
        cache: PermissionCache,
    ):
        self.membership_repo = membership_repo
        self.resolver = resolver
        self.cache = cache
    
    def get_permissions(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> frozenset[str]:
        """Alle effektiven Permissions laden (cached)."""
        membership = self.membership_repo.get_active(tenant_id, user_id)
        if not membership:
            return frozenset()
        
        # Cache-Check mit Version
        cached = self.cache.get(tenant_id, user_id, membership.permission_version)
        if cached is not None:
            return cached
        
        # Cache-Miss: Resolve und cachen
        permissions = self.resolver.resolve_all(membership)
        self.cache.set(tenant_id, user_id, membership.permission_version, permissions)
        
        return permissions
    
    def can(
        self,
        tenant_id: UUID,
        user_id: UUID,
        permission: str,
    ) -> bool:
        """Einzelne Permission prüfen."""
        permissions = self.get_permissions(tenant_id, user_id)
        return permission in permissions
    
    def require(
        self,
        tenant_id: UUID,
        user_id: UUID,
        permission: str,
    ) -> None:
        """Permission prüfen, Exception bei Fehler."""
        if not self.can(tenant_id, user_id, permission):
            raise PermissionDeniedError(permission)
```

---

## 10. Events & Audit

### 10.1 Domain Events

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TenantCreatedEvent:
    tenant_id: UUID
    owner_id: UUID
    plan_code: str
    timestamp: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class TenantStatusChangedEvent:
    tenant_id: UUID
    old_status: str
    new_status: str
    changed_by: UUID
    reason: str
    timestamp: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class MembershipCreatedEvent:
    membership_id: UUID
    tenant_id: UUID
    user_id: UUID
    role: str
    invited_by: UUID | None
    timestamp: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class PermissionGrantedEvent:
    membership_id: UUID
    tenant_id: UUID
    user_id: UUID
    permission_code: str
    granted_by: UUID
    expires_at: datetime | None
    timestamp: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class PermissionRevokedEvent:
    membership_id: UUID
    tenant_id: UUID
    user_id: UUID
    permission_code: str
    revoked_by: UUID
    timestamp: datetime = field(default_factory=_utc_now)
```

### 10.2 EventBus mit Outbox-Pattern

```python
class EventBus:
    """
    Event-Publishing via Outbox-Pattern.
    Events werden in core_outbox_message gespeichert und
    asynchron von Worker verarbeitet.
    """
    
    def publish(self, event: Any) -> None:
        """Event zur Outbox hinzufügen."""
        from bfagent_core.outbox import emit_outbox_event
        from bfagent_core.context import get_context
        
        ctx = get_context()
        event_type = type(event).__name__
        
        emit_outbox_event(
            tenant_id=ctx.tenant_id,
            topic=f"platform.{event_type}",
            payload=asdict(event) if hasattr(event, '__dataclass_fields__') else vars(event),
        )
```

---

## 11. Exceptions

```python
# packages/bfagent-core/src/bfagent_core/exceptions.py

class PlatformError(Exception):
    """Base class für alle Platform-Fehler."""
    
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code or self.__class__.__name__


# TENANT ERRORS
class TenantError(PlatformError):
    """Basis für Tenant-bezogene Fehler."""
    pass

class TenantNotFoundError(TenantError):
    def __init__(self, tenant_id: UUID):
        super().__init__(f"Tenant not found: {tenant_id}", "TENANT_NOT_FOUND")
        self.tenant_id = tenant_id

class TenantSlugExistsError(TenantError):
    def __init__(self, slug: str):
        super().__init__(f"Tenant slug already exists: {slug}", "TENANT_SLUG_EXISTS")
        self.slug = slug

class TenantSuspendedError(TenantError):
    def __init__(self, tenant_id: UUID):
        super().__init__(f"Tenant is suspended: {tenant_id}", "TENANT_SUSPENDED")
        self.tenant_id = tenant_id

class TenantDeletedError(TenantError):
    def __init__(self, tenant_id: UUID):
        super().__init__(f"Tenant is deleted: {tenant_id}", "TENANT_DELETED")
        self.tenant_id = tenant_id


# MEMBERSHIP ERRORS
class MembershipError(PlatformError):
    """Basis für Membership-bezogene Fehler."""
    pass

class MembershipNotFoundError(MembershipError):
    def __init__(self, membership_id: UUID):
        super().__init__(f"Membership not found: {membership_id}", "MEMBERSHIP_NOT_FOUND")
        self.membership_id = membership_id

class MembershipExistsError(MembershipError):
    def __init__(self, tenant_id: UUID, user_id: UUID):
        super().__init__(
            f"User {user_id} is already member of tenant {tenant_id}",
            "MEMBERSHIP_EXISTS"
        )
        self.tenant_id = tenant_id
        self.user_id = user_id

class NoMembershipError(MembershipError):
    def __init__(self, tenant_id: UUID, user_id: UUID):
        super().__init__(
            f"User {user_id} has no membership in tenant {tenant_id}",
            "NO_MEMBERSHIP"
        )
        self.tenant_id = tenant_id
        self.user_id = user_id

class InvitationExpiredError(MembershipError):
    def __init__(self, membership_id: UUID):
        super().__init__(f"Invitation expired: {membership_id}", "INVITATION_EXPIRED")
        self.membership_id = membership_id


# PERMISSION ERRORS
class PermissionError(PlatformError):
    """Basis für Permission-bezogene Fehler."""
    pass

class PermissionDeniedError(PermissionError):
    def __init__(self, permission: str, message: str | None = None):
        super().__init__(
            message or f"Permission denied: {permission}",
            "PERMISSION_DENIED"
        )
        self.permission = permission

class PermissionNotFoundError(PermissionError):
    def __init__(self, permission_code: str):
        super().__init__(f"Permission not found: {permission_code}", "PERMISSION_NOT_FOUND")
        self.permission_code = permission_code
```

---

## 12. API & Decorators

### 12.1 Decorators für FBV

```python
# packages/bfagent-core/src/bfagent_core/permissions/decorators.py

from functools import wraps
from typing import Callable, Union
from django.http import HttpRequest
from bfagent_core.exceptions import PermissionDeniedError, NoMembershipError

def require_permission(permission: Union[str, "Permission"]):
    """
    Decorator: Erfordert spezifische Permission.
    
    Usage:
        @require_permission(Permission.STORIES_CREATE)
        def create_story(request):
            ...
    """
    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if not hasattr(request, 'membership'):
                raise NoMembershipError(request.tenant_id, request.user.id)
            
            perm_code = permission.value if hasattr(permission, 'value') else permission
            
            from bfagent_core.services import get_authorization_service
            auth = get_authorization_service()
            
            if not auth.can(request.tenant_id, request.membership.user_id, perm_code):
                raise PermissionDeniedError(perm_code)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: str):
    """
    Decorator: Erfordert eine der angegebenen Rollen.
    
    Usage:
        @require_role("owner", "admin")
        def admin_dashboard(request):
            ...
    """
    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if not hasattr(request, 'membership'):
                raise NoMembershipError(request.tenant_id, request.user.id)
            
            if request.membership.role not in roles:
                raise PermissionDeniedError(
                    f"role:{','.join(roles)}",
                    f"Required role: {' or '.join(roles)}"
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions):
    """Mindestens eine der Permissions muss vorhanden sein."""
    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if not hasattr(request, 'membership'):
                raise NoMembershipError(request.tenant_id, request.user.id)
            
            from bfagent_core.services import get_authorization_service
            auth = get_authorization_service()
            user_perms = auth.get_permissions(request.tenant_id, request.membership.user_id)
            
            perm_codes = [p.value if hasattr(p, 'value') else p for p in permissions]
            
            if not any(p in user_perms for p in perm_codes):
                raise PermissionDeniedError(perm_codes[0], f"Need one of: {perm_codes}")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### 12.2 Mixins für CBV

```python
# packages/bfagent-core/src/bfagent_core/permissions/mixins.py

from django.views import View
from django.core.exceptions import PermissionDenied
from bfagent_core.exceptions import PermissionDeniedError, NoMembershipError

class TenantPermissionMixin:
    """
    Mixin für Class-Based Views mit Permission-Check.
    
    Usage:
        class StoryListView(TenantPermissionMixin, ListView):
            required_permission = Permission.STORIES_VIEW
            model = Story
    """
    required_permission = None
    required_role = None
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, 'membership') or not request.membership:
            raise PermissionDenied("No membership")
        
        # Role-Check
        if self.required_role:
            roles = (self.required_role,) if isinstance(self.required_role, str) else self.required_role
            if request.membership.role not in roles:
                raise PermissionDenied(f"Required role: {roles}")
        
        # Permission-Check
        if self.required_permission:
            perm = self.required_permission
            perm_code = perm.value if hasattr(perm, 'value') else perm
            
            from bfagent_core.services import get_authorization_service
            auth = get_authorization_service()
            
            if not auth.can(request.tenant_id, request.membership.user_id, perm_code):
                raise PermissionDenied(f"Permission denied: {perm_code}")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_user_permissions(self) -> frozenset[str]:
        """Für Template-Nutzung: Alle User-Permissions."""
        if not hasattr(self.request, 'membership'):
            return frozenset()
        
        from bfagent_core.services import get_authorization_service
        auth = get_authorization_service()
        return auth.get_permissions(
            self.request.tenant_id,
            self.request.membership.user_id
        )
```

### 12.3 DRF Integration

```python
from rest_framework.permissions import BasePermission

class HasTenantPermission(BasePermission):
    """
    DRF Permission-Class.
    
    Usage:
        class StoryViewSet(viewsets.ModelViewSet):
            permission_classes = [HasTenantPermission]
            required_permission = Permission.STORIES_VIEW
    """
    
    def has_permission(self, request, view):
        if not hasattr(request, 'membership') or not request.membership:
            return False
        
        required = getattr(view, 'required_permission', None)
        if not required:
            return True  # No specific permission required
        
        perm_code = required.value if hasattr(required, 'value') else required
        
        from bfagent_core.services import get_authorization_service
        auth = get_authorization_service()
        
        return auth.can(
            request.tenant_id,
            request.membership.user_id,
            perm_code
        )
```

### 12.4 Template-Integration

```html
<!-- Via Context Processor -->
{% if 'stories.delete' in user_permissions %}
    <button class="btn-danger">Delete</button>
{% endif %}

{% if 'stories.publish' in user_permissions %}
    <button class="btn-primary">Publish</button>
{% endif %}

<!-- Oder via View-Methode -->
{% if 'stories.delete' in view.get_user_permissions %}
    <button class="btn-danger">Delete</button>
{% endif %}
```

```python
# Context Processor
def permissions_context(request):
    if not hasattr(request, 'membership') or not request.membership:
        return {'user_permissions': frozenset()}
    
    from bfagent_core.services import get_authorization_service
    auth = get_authorization_service()
    
    return {
        'user_permissions': auth.get_permissions(
            request.tenant_id,
            request.membership.user_id
        ),
        'user_role': request.membership.role,
    }
```

---

## 13. Migration & Rollout

### 13.1 Zero-Breaking-Change-Strategie

```
Phase 1: Schema (Tag 1)
├── core_plan Tabelle
├── core_user Tabelle (parallel zu auth_user)
├── core_tenant Tabelle
├── core_tenant_membership Tabelle
├── Permission-Tabellen
└── Verifizieren: Neue Tabellen existieren, keine FK-Violations

Phase 2: User-Bridge (Tag 1-2)
├── core_user.legacy_user_id → auth_user.id Mapping
├── Sync-Trigger für neue User
└── Backfill existierende User

Phase 3: Default-Tenant (Tag 2)
├── Default-Tenant für bestehende Daten erstellen
├── Bestehende User als Owner zuweisen
└── Backfill Memberships in Batches

Phase 4: Dual-Write (Tag 2-3)
├── Neue Writes gehen in neue Tabellen
├── Alte Pfade bleiben aktiv
└── Monitoring beider Systeme

Phase 5: Permission-Sync (Tag 3)
├── Permission-Enum → DB sync
├── Role-Permission-Mapping laden
└── Verifizieren via Tests

Phase 6: Middleware aktivieren (Tag 3-4)
├── TenantPermissionMiddleware einbinden
├── Feature-Flag für schrittweises Rollout
└── Monitoring Permission-Checks

Phase 7: RLS aktivieren (Tag 4)
├── RLS-Policies erstellen (DEAKTIVIERT)
├── Test mit app.current_tenant manuell
├── RLS aktivieren pro Tabelle
└── Monitoring Query-Performance

Phase 8: Cleanup (Tag 5)
├── Alte Pfade entfernen
├── Feature-Flags entfernen
└── Dokumentation aktualisieren
```

### 13.2 Rollback-Strategie

```sql
-- Level 1: Middleware deaktivieren (sofort)
-- In settings.py: TENANT_PERMISSION_ENABLED = False

-- Level 2: RLS deaktivieren (sofort)
ALTER TABLE some_table DISABLE ROW LEVEL SECURITY;

-- Level 3: Constraints entfernen (kritisch)
ALTER TABLE core_tenant DROP CONSTRAINT tenant_status_chk;

-- Dokumentiert in: ops/runbooks/rbac-rollback.md
```

---

## 14. Implementierung

### 14.1 Package-Struktur

```
packages/bfagent-core/src/bfagent_core/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── plan.py             # Plan
│   ├── user.py             # CoreUser
│   ├── tenant.py           # Tenant, TenantStatus
│   └── membership.py       # TenantMembership, TenantRole
├── repositories/
│   ├── __init__.py
│   ├── plan.py             # PlanRepository
│   ├── user.py             # UserRepository
│   ├── tenant.py           # TenantRepository
│   ├── membership.py       # MembershipRepository
│   └── permission.py       # PermissionRepository, OverrideRepository
├── handlers/
│   ├── __init__.py
│   ├── tenant.py           # TenantCreateHandler, TenantSuspendHandler
│   ├── membership.py       # MembershipInviteHandler, MembershipAcceptHandler
│   └── permission.py       # PermissionGrantHandler, PermissionRevokeHandler
├── services/
│   ├── __init__.py
│   ├── authorization.py    # AuthorizationService
│   ├── lifecycle.py        # TenantLifecycleService
│   └── resolver.py         # PermissionResolver
├── permissions/
│   ├── __init__.py
│   ├── enums.py            # Permission Enum, ROLE_PERMISSIONS
│   ├── cache.py            # PermissionCache
│   ├── decorators.py       # @require_permission, @require_role
│   ├── mixins.py           # TenantPermissionMixin
│   └── sync.py             # sync_permissions_to_db()
├── events/
│   ├── __init__.py
│   ├── tenant.py           # TenantCreatedEvent, etc.
│   ├── membership.py       # MembershipCreatedEvent, etc.
│   └── bus.py              # EventBus
├── exceptions.py           # Exception-Hierarchy
├── context.py              # Existing contextvars
├── db.py                   # Existing RLS helpers
├── middleware.py           # Extended middleware
├── audit.py                # Existing audit
├── outbox.py               # Existing outbox
└── migrations/
    ├── 0002_plan.py
    ├── 0003_user.py
    ├── 0004_tenant.py
    ├── 0005_membership.py
    ├── 0006_permissions.py
    └── 0007_audit.py
```

### 14.2 Aufwandschätzung

| Komponente | Aufwand |
|------------|---------|
| Models & Migrations | 1.5 Tage |
| Repositories | 1 Tag |
| Handlers | 1.5 Tage |
| Services (Auth, Resolver) | 1 Tag |
| Permissions/Decorators/Cache | 1.5 Tage |
| Events & Audit | 0.5 Tag |
| Middleware Integration | 0.5 Tag |
| Tests | 2 Tage |
| Dokumentation | 0.5 Tag |
| **Gesamt** | **10 Tage** |

---

## 15. Konsequenzen

### 15.1 Positive Konsequenzen

1. **Strikte Isolation** – RLS + UUID garantiert Tenant-Separation
2. **SSO-Ready** – UUID user_id ermöglicht externe IAM-Integration
3. **Auditierbar** – Alle Permission-Änderungen mit Version-Tag nachvollziehbar
4. **Performant** – O(1) Permission-Checks durch Version-basiertes Caching
5. **Testbar** – Klare Interfaces, Dependency Injection
6. **Erweiterbar** – Neue Permissions ohne Schema-Änderung
7. **DB-Enforced** – Lifecycle-Constraints in PostgreSQL
8. **Konsistent** – `app.current_tenant` durchgängig

### 15.2 Negative Konsequenzen

1. **Mehr Tabellen** – 12+ statt 2-3
2. **Höherer Initialaufwand** – ~10 Tage
3. **Komplexität** – Handler-Pattern, Events, Version-Cache

### 15.3 Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Cache stale | Niedrig | Niedrig | Version-Tag + TTL=60s |
| Performance bei vielen Permissions | Niedrig | Mittel | FrozenSet für O(1) Lookup |
| Breaking Changes | Niedrig | Hoch | Additives Design, Dual-Write |
| RLS-Bypass | Niedrig | Kritisch | platform_admin Role dokumentiert, Audit |
| User-Migration Fehler | Mittel | Mittel | Dual-Write, Rollback-Plan |

---

## Appendix A: Fixture-Daten

```sql
-- core_plan
INSERT INTO core_plan (code, name, is_public, sort_order) VALUES
    ('free', 'Free', true, 0),
    ('starter', 'Starter', true, 10),
    ('professional', 'Professional', true, 20),
    ('enterprise', 'Enterprise', false, 30);

-- core_permission
INSERT INTO core_permission (code, description, category) VALUES
    ('tenant.view', 'View tenant info', 'tenant'),
    ('tenant.edit', 'Edit tenant settings', 'tenant'),
    ('tenant.manage', 'Manage tenant (billing, plan)', 'tenant'),
    ('tenant.delete', 'Delete tenant', 'tenant'),
    ('members.view', 'View member list', 'members'),
    ('members.invite', 'Invite members', 'members'),
    ('members.edit', 'Edit member roles', 'members'),
    ('members.remove', 'Remove members', 'members'),
    ('stories.view', 'View stories', 'stories'),
    ('stories.create', 'Create stories', 'stories'),
    ('stories.edit', 'Edit stories', 'stories'),
    ('stories.delete', 'Delete stories', 'stories'),
    ('stories.publish', 'Publish stories', 'stories'),
    ('stories.export', 'Export stories', 'stories'),
    ('ai.generate', 'Use AI generation', 'ai'),
    ('ai.use_premium', 'Use premium AI models', 'ai'),
    ('settings.view', 'View settings', 'settings'),
    ('settings.edit', 'Edit settings', 'settings'),
    ('audit.view', 'View audit log', 'audit'),
    ('api_keys.manage', 'Manage API keys', 'api');

-- core_role_permission (Owner = all)
INSERT INTO core_role_permission (role, permission_code)
SELECT 'owner', code FROM core_permission;

-- core_role_permission (Admin = all except tenant.delete)
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
TENANT_BASE_DOMAIN = "platform.io"

# Dev-Mode: Admin ohne Tenant erlauben
TENANT_ALLOW_LOCALHOST = DEBUG

# Permission-Cache
PERMISSION_CACHE_TTL = 60  # Sekunden
PERMISSION_CACHE_BACKEND = "default"

# Feature-Flags für schrittweises Rollout
TENANT_PERMISSION_ENABLED = True  # Set False for rollback

# Middleware-Reihenfolge
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'bfagent_core.middleware.RequestContextMiddleware',
    'bfagent_core.middleware.SubdomainTenantMiddleware',
    'bfagent_core.middleware.TenantPermissionMiddleware',  # NEU
    # ...
]

# Context Processors
TEMPLATES = [{
    # ...
    'OPTIONS': {
        'context_processors': [
            # ...
            'bfagent_core.permissions.context_processors.permissions_context',
        ],
    },
}]
```

---

**Letzte Aktualisierung:** 2026-02-01  
**Nächste Review:** 2026-03-01  
**Autoren:** Platform Architecture Team  
**Konsolidiert aus:** ADR-007-FINAL-PRODUCTION.md, adr_007_optimized_tenant_rbac.md
