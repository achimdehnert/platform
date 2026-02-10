# ADR-007 Konsolidierung: Änderungsübersicht

## Zusammenfassung der Integration

Die konsolidierte Version vereint das Beste aus beiden ADRs:

| Quelle | Übernommen |
|--------|------------|
| **ADR-007-FINAL** | Handler-Pattern, Events, Audit, Exception-Hierarchy, Decorators, Implementierungsdetails |
| **ADR-007-Optimized** | UUID für user_id, permission_version, explizite Separation of Concerns, deterministischer Resolution-Algorithmus |
| **Kritische Review** | Alle 13 identifizierten Issues behoben |

---

## 🔴 Kritische Fixes (alle behoben)

### 1. RLS Session Variable ✅
```diff
- USING (tenant_id = current_setting('app.tenant_id')::uuid);
+ USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
```
Konsistent mit bestehendem `bfagent-core/db.py`.

### 2. core_plan Tabelle ✅
```sql
-- NEU hinzugefügt
CREATE TABLE core_plan (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT true,
    sort_order INTEGER NOT NULL DEFAULT 0,
    ...
);
```

### 3. Middleware-Konflikt ✅
- `TenantPermissionMiddleware` als ERGÄNZUNG zu `SubdomainTenantMiddleware`
- Klare Reihenfolge dokumentiert
- Keine Überlappung mehr

### 4. @transaction.atomic ✅
```python
class TenantCreateHandler:
    @transaction.atomic  # HINZUGEFÜGT
    def handle(self, cmd: TenantCreateCommand) -> TenantCreateResult:
        ...
```

### 5. Cache-Key mit Namespace ✅
```diff
- key = f"perms:{tenant_id}:{user_id}"
+ key = f"bfagent:perms:v1:{tenant_id}:{user_id}"
```

---

## 🟡 Wichtige Verbesserungen (alle integriert)

### 6. Membership-Status ✅
```sql
ALTER TABLE core_tenant_membership ADD COLUMN status TEXT NOT NULL DEFAULT 'active';
-- CHECK status IN ('pending', 'active', 'deactivated')
```

### 7. Permission-Override expires_at ✅
```sql
ALTER TABLE core_membership_permission_override
    ADD COLUMN expires_at TIMESTAMPTZ,
    ADD COLUMN reason TEXT;
```

### 8. Verbesserte Indexes ✅
```sql
CREATE INDEX core_membership_pending_idx ON core_tenant_membership(invitation_expires_at) 
    WHERE status = 'pending';
CREATE INDEX core_override_expires_idx ON core_membership_permission_override(expires_at) 
    WHERE expires_at IS NOT NULL;
```

### 9. Timezone-aware Timestamps ✅
```python
from datetime import datetime, timezone

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
```

### 10. Repository Batch-Operationen ✅
```python
@abstractmethod
def get_by_ids(self, tenant_ids: Sequence[UUID]) -> list[Tenant]:
    """Bulk-Load für N+1-Vermeidung."""
    ...
```

---

## 🟢 Architektur-Optimierungen (alle integriert)

### 11. Permission Enum ↔ DB Sync ✅
```python
def sync_permissions_to_db():
    """Sync Python Enum → DB. In Migrations aufrufen."""
    for perm in Permission:
        CorePermission.objects.update_or_create(
            code=perm.value,
            defaults={"description": ..., "category": ...}
        )
```

### 12. UUID für user_id (SSO-Ready) ✅
```sql
-- NEU: core_user Tabelle mit UUID
CREATE TABLE core_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE,  -- SSO: Auth0 sub, Okta uid
    provider TEXT,
    legacy_user_id INTEGER UNIQUE,  -- Bridge zu auth_user
    ...
);
```

### 13. permission_version für Cache ✅
```sql
ALTER TABLE core_tenant_membership 
    ADD COLUMN permission_version INTEGER NOT NULL DEFAULT 1;

-- Trigger für auto-increment bei Role-Änderung
CREATE TRIGGER membership_permission_version_trigger
    BEFORE UPDATE OF role ON core_tenant_membership
    FOR EACH ROW
    EXECUTE FUNCTION trg_membership_permission_version();
```

---

## Neue Features (aus Optimized-ADR)

### Deterministische Permission-Resolution
```python
def resolve(self, membership, permission_code) -> PermissionResult:
    # 1. Override DENY → DENIED
    # 2. Override ALLOW (nicht expired) → GRANTED
    # 3. Role Permission → GRANTED/DENIED
```

### Version-basiertes Caching
```python
def get(self, tenant_id, user_id, expected_version) -> frozenset[str] | None:
    cached = cache.get(key)
    if cached.get("version") != expected_version:
        return None  # Cache invalid
    return frozenset(cached.get("permissions", []))
```

### Invitation mit Expiration
```sql
CONSTRAINT membership_pending_chk CHECK (
    status <> 'pending' OR invitation_expires_at IS NOT NULL
)
```

---

## Aufwandsvergleich

| Version | Geschätzter Aufwand |
|---------|---------------------|
| ADR-007-FINAL (original) | 7 Tage |
| ADR-007-CONSOLIDATED | 10 Tage |
| **Delta** | +3 Tage für SSO-Ready, Version-Cache, robustere Migration |

---

## Checkliste für Implementation

| Item | Status |
|------|--------|
| core_plan Tabelle + Fixtures | ⬜ |
| core_user Tabelle + Bridge zu auth_user | ⬜ |
| core_tenant mit FK zu core_plan | ⬜ |
| core_tenant_membership mit status, permission_version | ⬜ |
| Permission-Tabellen mit expires_at | ⬜ |
| Audit-Tabelle mit denormalized fields | ⬜ |
| Trigger für permission_version | ⬜ |
| PermissionCache mit Version-Check | ⬜ |
| TenantPermissionMiddleware | ⬜ |
| Decorators & Mixins | ⬜ |
| Permission Enum → DB Sync | ⬜ |
| Context Processor für Templates | ⬜ |
| Unit Tests | ⬜ |
| Integration Tests | ⬜ |
| Migration Runbook | ⬜ |
| Rollback Runbook | ⬜ |
