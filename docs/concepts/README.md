# 🏢 Tenant-Model & RBAC-System

**Version:** 1.0  
**Für:** `packages/bfagent-core`  
**Aufwand:** ~5-7 Tage  

---

## 📁 Dateien

```
tenant-rbac/
├── models/
│   ├── __init__.py          # Export
│   ├── tenant.py            # Tenant Model
│   └── membership.py        # TenantMembership Model
├── permissions/
│   ├── __init__.py          # Export
│   ├── enums.py             # Permission Enum + Role-Mapping
│   ├── checker.py           # PermissionChecker (mit Cache)
│   ├── decorators.py        # @require_permission, @require_role
│   └── mixins.py            # CBV Mixins
├── migrations/
│   ├── 0002_tenant.py       # Tenant Migration
│   └── 0003_tenantmembership.py
└── tests/
    └── test_tenant_rbac.py  # Comprehensive Tests
```

---

## 🚀 Installation

### 1. Dateien kopieren

```bash
# In bfagent-core Package
cp -r tenant-rbac/models/* packages/bfagent-core/src/bfagent_core/models/
cp -r tenant-rbac/permissions/* packages/bfagent-core/src/bfagent_core/permissions/
cp tenant-rbac/migrations/* packages/bfagent-core/src/bfagent_core/migrations/
cp tenant-rbac/tests/* packages/bfagent-core/tests/
```

### 2. __init__.py aktualisieren

```python
# packages/bfagent-core/src/bfagent_core/__init__.py

from bfagent_core.models import (
    Tenant,
    TenantStatus,
    TenantMembership,
    TenantRole,
)
from bfagent_core.permissions import (
    Permission,
    has_permission,
    check_permission,
    require_permission,
    require_role,
    TenantPermissionMixin,
)

__all__ = [
    # Models
    "Tenant",
    "TenantStatus",
    "TenantMembership",
    "TenantRole",
    
    # Permissions
    "Permission",
    "has_permission",
    "check_permission",
    "require_permission",
    "require_role",
    "TenantPermissionMixin",
    # ... etc
]
```

### 3. Migrationen ausführen

```bash
cd apps/your-app
python manage.py migrate bfagent_core
```

---

## 📖 Verwendung

### Function-Based Views

```python
from bfagent_core.permissions import require_permission, Permission

@require_permission(Permission.STORIES_CREATE)
def create_story(request):
    # User hat Permission
    ...

@require_role("owner", "admin")
def admin_dashboard(request):
    # Nur Owner/Admin
    ...
```

### Class-Based Views

```python
from django.views.generic import ListView, DeleteView
from bfagent_core.permissions import TenantPermissionMixin, Permission

class StoryListView(TenantPermissionMixin, ListView):
    required_permission = Permission.STORIES_VIEW
    model = Story

class StoryDeleteView(TenantPermissionMixin, DeleteView):
    required_role = "admin"  # Nur Admin+
    model = Story
```

### Services

```python
from bfagent_core.permissions import check_permission, Permission

def publish_story(user_id: int, story_id: int) -> Story:
    # Wirft PermissionDenied wenn nicht erlaubt
    check_permission(user_id, Permission.STORIES_PUBLISH)
    
    story = Story.objects.get(id=story_id)
    story.status = "published"
    story.save()
    return story
```

### Templates

```html
<!-- Mit Mixin: view.get_user_permissions() -->
{% if 'stories.delete' in view.get_user_permissions %}
    <button class="btn-danger">Delete</button>
{% endif %}

{% if 'stories.publish' in view.get_user_permissions %}
    <button class="btn-primary">Publish</button>
{% endif %}
```

### DRF APIs

```python
from rest_framework.generics import ListAPIView
from bfagent_core.permissions import TenantAPIPermissionMixin, Permission

class StoryListAPI(TenantAPIPermissionMixin, ListAPIView):
    required_permission = Permission.STORIES_VIEW
    serializer_class = StorySerializer
```

---

## 🔐 Rollen & Permissions

### Rollen-Hierarchie

| Rolle | Level | Beschreibung |
|-------|-------|--------------|
| `owner` | 100 | Vollzugriff, kann Tenant löschen |
| `admin` | 75 | Fast alles, außer Tenant-Delete |
| `member` | 50 | Arbeiten (Create/Edit), kein Delete |
| `viewer` | 25 | Nur Lesen |

### Permission-Matrix

| Permission | Owner | Admin | Member | Viewer |
|------------|-------|-------|--------|--------|
| `stories.view` | ✅ | ✅ | ✅ | ✅ |
| `stories.create` | ✅ | ✅ | ✅ | ❌ |
| `stories.edit` | ✅ | ✅ | ✅ | ❌ |
| `stories.delete` | ✅ | ✅ | ❌ | ❌ |
| `stories.publish` | ✅ | ✅ | ❌ | ❌ |
| `tenant.delete` | ✅ | ❌ | ❌ | ❌ |
| `ai.premium` | ✅ | ✅ | ❌ | ❌ |

### Permission Override

```python
# Viewer bekommt zusätzlich CREATE
membership.grant_permission("stories.create")

# Owner verliert DELETE
membership.revoke_permission("stories.delete")

# Zurück zu Role-Default
membership.clear_permission_override("stories.delete")
```

---

## 🏗️ Tenant Lifecycle

```
┌─────────┐     activate()     ┌─────────┐
│  TRIAL  │ ─────────────────▶ │ ACTIVE  │
└─────────┘                    └─────────┘
     │                              │
     │ soft_delete()                │ suspend()
     ▼                              ▼
┌─────────┐                    ┌───────────┐
│ DELETED │ ◀────────────────  │ SUSPENDED │
└─────────┘    soft_delete()   └───────────┘
                                    │
                                    │ activate()
                                    ▼
                               ┌─────────┐
                               │ ACTIVE  │
                               └─────────┘
```

```python
# Trial → Active
tenant.activate()

# Suspend (z.B. Zahlung fehlgeschlagen)
tenant.suspend(reason="Payment failed")

# Soft-Delete (Daten bleiben für Compliance)
tenant.soft_delete()
```

---

## 🧪 Tests ausführen

```bash
cd packages/bfagent-core
pytest tests/test_tenant_rbac.py -v
```

---

## ⚙️ Settings

```python
# settings.py

# Tenant-Model für Middleware
TENANT_MODEL = "bfagent_core.Tenant"
TENANT_SLUG_FIELD = "slug"
TENANT_ID_FIELD = "id"

# Base Domain für Subdomains
TENANT_BASE_DOMAIN = "myapp.io"  # demo.myapp.io, acme.myapp.io

# Dev-Mode: Admin ohne Tenant erlauben
TENANT_ALLOW_LOCALHOST = DEBUG
```

---

## 📊 Caching

Der PermissionChecker cached Memberships für 5 Minuten:

```python
from bfagent_core.permissions import invalidate_permission_cache

# Nach Rollen-/Permission-Änderung:
invalidate_permission_cache(tenant_id, user_id)
```

---

## 🔄 Migration Checklist

- [ ] Dateien kopieren
- [ ] `__init__.py` aktualisieren
- [ ] `python manage.py makemigrations` (falls nötig)
- [ ] `python manage.py migrate`
- [ ] Tests ausführen
- [ ] Settings anpassen
- [ ] Middleware prüfen

---

*Erstellt für Platform Multi-Tenancy - 2025-01-31*
