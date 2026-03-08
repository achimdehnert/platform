# ADR-109: Multi-Tenancy als Plattform-Standard für alle UI-Hubs

- **Status:** Accepted
- **Datum:** 2026-03-08
- **Amends:** ADR-035 (shared-django-tenancy)
- **Betrifft:** alle Django-Hub-Repos mit Frontend-UI

---

## Kontext

Drei Hubs (coach-hub, risk-hub, research-hub) haben Multi-Tenancy bereits implementiert:
- `django_tenancy.Organization` als Tenant-Entity
- `SubdomainTenantMiddleware` setzt `request.tenant_id`
- `_tenant_workspace_qs()` isoliert alle Queries
- Org-UI für Wechsel und Erstellung

Dieses Muster ist erprobt und soll für **alle** UI-Hubs verbindlich werden.

## Entscheidung

Multi-Tenancy nach dem etablierten `django_tenancy`-Muster ist **Pflichtstandard** für alle Django-Hub-Repos mit Frontend-UI.

### Betroffene Repos (Rollout-Reihenfolge)

| Prio | Repo | Begründung |
|------|------|------------|
| ✅ Done | `coach-hub` | Referenz-Implementierung |
| ✅ Done | `risk-hub` | Referenz-Implementierung |
| ✅ Done | `research-hub` | Abgeschlossen 2026-03-08 |
| 1 | `weltenhub` | Produktiv, User-Content |
| 2 | `pptx-hub` | Produktiv, User-Content |
| 3 | `trading-hub` | Produktiv, User-Content |
| 4 | `cad-hub` | Produktiv, User-Content |
| 5 | `wedding-hub` | Produktiv, User-Content |
| 6 | `137-hub` | Produktiv, User-Content |
| 7 | `illustration-hub` | Produktiv, User-Content |
| 8 | `billing-hub` | Spezialfall: cross-tenant Billing — separates ADR nötig |
| – | `dev-hub` | Internes Ops-Tool, single-tenant ausreichend |

### Pflicht-Komponenten je Hub

```python
# models/tenant.py (via django_tenancy)
from django_tenancy.models import Organization

# middleware (settings.py MIDDLEWARE)
"django_tenancy.middleware.SubdomainTenantMiddleware"

# base queryset mixin (alle Models mit User-Content)
def _tenant_workspace_qs(self, request):
    return self.filter(tenant_id=request.tenant_id)

# org switcher (base template)
{% include "tenancy/org_switcher.html" %}
```

### Migration-Checkliste je Repo

- [ ] `Organization`-Model via `django_tenancy` einbinden
- [ ] `tenant_id` FK auf alle relevanten Models (Migration!)
- [ ] `SubdomainTenantMiddleware` in `MIDDLEWARE` eintragen
- [ ] Alle Views: `_tenant_workspace_qs()` oder `TenantQuerySetMixin`
- [ ] Org-UI im Base-Template einbinden
- [ ] Tests: `TenantTestMixin` aus `iil-testkit`
- [ ] Subdomain-DNS-Eintrag (Cloudflare Wildcard `*.domain.tld`)
- [ ] ADR-109-Compliance in PR-Checklist vermerken

### Ausnahmen

- `billing-hub`: Cross-tenant Billing erfordert separates ADR (ADR-11x)
- `dev-hub`: Single-tenant, interne Nutzung — kein Rollout geplant

## Konsequenzen

**Positiv:**
- Konsistente Datenisolation plattformweit
- Kein versehentlicher Cross-Tenant-Datenleak
- Einheitliches UX für Org-Wechsel in allen Hubs
- Testbarkeit via `iil-testkit` `TenantTestMixin`

**Negativ / Aufwand:**
- Jeder Hub braucht eine Migration (einmalig, ~1h)
- Bestehende Daten müssen einem Default-Tenant zugewiesen werden
- Subdomain-Routing erfordert Wildcard-DNS (bereits via Cloudflare vorhanden)

## Implementierungs-Workflow

```bash
# Pro Hub (Beispiel weltenhub):
# 1. django_tenancy installieren (falls nicht vorhanden)
# 2. Models ergänzen
# 3. python manage.py makemigrations
# 4. python manage.py migrate
# 5. Default-Org anlegen (management command oder Admin)
# 6. sync-repo.sh --server weltenhub
```

---
*ADR-109 | Platform Architecture | 2026-03-08*
