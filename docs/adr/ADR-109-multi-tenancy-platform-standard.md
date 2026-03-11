---
status: accepted
date: 2026-03-08
decision-makers: [Achim Dehnert]
implementation_status: partial
implementation_evidence:
  - "6/9 UI-Hubs mit tenant: travel-beat, weltenhub, coach-hub, cad-hub, billing-hub, dev-hub"
  - "Fehlend: risk-hub, pptx-hub, trading-hub (kein django_tenants installiert)"
---

# ADR-109: Multi-Tenancy als Plattform-Standard für alle UI-Hubs

- **Status:** Accepted (updated 2026-03-08 — REVIEW-ADR-109-110 BLOCKER fixes)
- **Datum:** 2026-03-08
- **Amends:** ADR-035 (shared-django-tenancy)
- **Betrifft:** alle Django-Hub-Repos mit Frontend-UI
- **Review:** `docs/adr/reviews/REVIEW-ADR-109-110.md`

---

## Kontext

Drei Hubs (coach-hub, risk-hub, research-hub) haben Multi-Tenancy bereits implementiert
nach ADR-035. Dieses Muster wird für **alle** UI-Hubs verbindlich.

**Referenz-Implementierung:** `docs/adr/inputs/Input ADR 109 110/`

## Entscheidung

Multi-Tenancy nach dem `django_tenancy`-Muster (ADR-035) ist **Pflichtstandard** für alle Django-Hub-Repos mit Frontend-UI.

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
| 8 | `billing-hub` | Spezialfall: `TENANCY_MODE=disabled` interim, separates ADR |
| – | `dev-hub` | Internes Ops-Tool, `TENANCY_MODE=disabled` |

### Pflicht-Komponenten je Hub

#### Fix B-1: `tenant_id` ist `BigIntegerField` — KEIN ForeignKey

```python
# Alle User-Data-Models erben von TenantModel (abstract base)
# aus: docs/adr/inputs/Input ADR 109 110/models_django_tenancy.py

class MyModel(TenantModel):
    name = models.CharField(max_length=200)
    # tenant_id (BigIntegerField), public_id (UUID), deleted_at automatisch

# Fix B-1: BigIntegerField, KEIN FK zu Organization
# Rationale: FK würde ON DELETE CASCADE/RESTRICT erzwingen,
#            bricht Celery/Cross-DB-Szenarien, widerspricht ADR-035 §2.2
tenant_id = models.BigIntegerField(db_index=True, verbose_name=_("Tenant ID"))
```

#### Fix H-1: Platform-Standard-Model-Felder

```python
# TenantModel Abstract Base (aus django_tenancy.models):
class TenantModel(models.Model):
    id = models.BigAutoField(primary_key=True)        # Platform-Pflicht
    public_id = models.UUIDField(...)                 # Platform-Pflicht
    tenant_id = models.BigIntegerField(db_index=True) # KEIN FK
    deleted_at = models.DateTimeField(null=True, ...)  # Soft-Delete
    objects = TenantManager()                          # for_tenant() QuerySet

    class Meta:
        abstract = True
```

#### Fix H-3: TenancyMode Strategy (kein fest verkabeltes Subdomain-Routing)

```python
# settings.py
TENANCY_MODE = os.environ.get("TENANCY_MODE", "session")
# "subdomain" = Prod
# "session"   = Dev (default — kein Subdomain-Setup nötig)
# "header"    = API/CI (X-Tenant-ID Header)
# "disabled"  = billing-hub, dev-hub

TENANCY_FALLBACK_URL = "/onboarding/"  # Fix B-3: kein 500 bei unbekannter Subdomain
```

#### Fix B-3: Middleware-Fallback für unbekannte Subdomain

```python
# SubdomainTenantMiddleware (aus middleware.py):
# Unbekannte Subdomain → Redirect zu TENANCY_FALLBACK_URL (kein 500)
try:
    tenant = resolver(request)
except TenantNotFound as e:
    return HttpResponseRedirect(settings.TENANCY_FALLBACK_URL)
```

#### MIDDLEWARE-Reihenfolge (kritisch — Fix B-4 aus ADR-110)

```python
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",    # ← 1: Pflicht vor Locale
    "django.middleware.locale.LocaleMiddleware",               # ← 2: nach Session
    "django_tenancy.middleware.SubdomainTenantMiddleware",     # ← 3: nach Locale
    "django.middleware.common.CommonMiddleware",               # ← 4
    # ...
]
```

#### Context Processor (Fix L-1)

```python
# TEMPLATES[0]["OPTIONS"]["context_processors"]
"django_tenancy.context_processors.tenant",  # request.tenant im Template verfügbar
"django.template.context_processors.i18n",   # {% trans %} Support
```

### Migration-Checkliste je Repo

- [ ] `django_tenancy` in `INSTALLED_APPS` + pip install
- [ ] Alle User-Data-Models von `TenantModel` erben (oder `tenant_id BigIntegerField` manuell)
- [ ] `TENANCY_MODE` + `TENANCY_FALLBACK_URL` in settings
- [ ] `SubdomainTenantMiddleware` in `MIDDLEWARE` (nach `LocaleMiddleware`)
- [ ] `django_tenancy.context_processors.tenant` in TEMPLATES
- [ ] Org-UI im Base-Template: `{% include "tenancy/org_switcher.html" %}`
- [ ] **Fix H-4: Migration für bestehende Prod-Daten** (s.u.)
- [ ] Tests: `TenantTestMixin` aus `iil-testkit` (Issue ISS-1)
- [ ] Subdomain-DNS: Cloudflare Wildcard + Test: `curl -H "Host: test.hub.domain.tld" .../health/`
- [ ] ADR-109-Compliance in PR-Checklist

### Fix H-4: Migration-Pattern für bestehende Prod-Daten

Bestehende Hubs mit Prod-Daten **müssen** dieses 3-Stufen-Pattern verwenden:

```python
# Template: docs/adr/inputs/Input ADR 109 110/0002_add_tenant_id.py
operations = [
    # Step 1: Spalte als NULL hinzufügen (kein NOT NULL Fehler auf bestehenden Rows)
    migrations.AddField("mymodel", "tenant_id",
        models.BigIntegerField(null=True, db_index=True)),
    # Step 2: Bestehende Rows → Default-Tenant
    migrations.RunPython(assign_default_tenant, reverse_code=remove_tenant_assignment),
    # Step 3: NOT NULL setzen via SeparateDatabaseAndState + RunSQL
    migrations.SeparateDatabaseAndState(
        database_operations=[migrations.RunSQL(
            'ALTER TABLE "core_mymodel" ALTER COLUMN "tenant_id" SET NOT NULL',
            reverse_sql='... DROP NOT NULL',
        )],
        state_operations=[migrations.AlterField(...)],
    ),
]
```

Rollback: `python manage.py migrate core 0001` (vollständig reversibel via `reverse_code`)

### Ausnahmen

- `billing-hub`: `TENANCY_MODE=disabled` + `TENANT_ISOLATION_MODE=disabled` interim bis separates ADR
- `dev-hub`: `TENANCY_MODE=disabled`, kein Rollout geplant

## Konsequenzen

**Positiv:**
- Konsistente Datenisolation plattformweit
- Kein versehentlicher Cross-Tenant-Datenleak
- `TenancyMode` ermöglicht lokale Entwicklung ohne Subdomain-Setup
- Testbarkeit via `iil-testkit` `TenantTestMixin`

**Negativ / Aufwand:**
- Jeder Hub braucht eine Migration (einmalig, ~1–2h inkl. Staging-Test)
- Bestehende Daten müssen Default-Tenant zugewiesen werden (via `create_default_tenant`)
- Subdomain-Routing erfordert Wildcard-DNS (bereits via Cloudflare vorhanden)

## Implementierungs-Referenz

```bash
# Pro Hub (Beispiel weltenhub):
# 0. Voraussetzung: Default-Tenant in Prod-DB anlegen
python manage.py create_default_tenant --name="Default" --slug="default"
# 1. django_tenancy installieren
# 2. Settings, Middleware, Context Processor
# 3. Models auf TenantModel umstellen
# 4. python manage.py makemigrations
# 5. Migration-Review: SeparateDatabaseAndState + reverse_func vorhanden?
# 6. Staging-Test vor Prod
# 7. sync-repo.sh --server weltenhub
```

---
*ADR-109 | Platform Architecture | 2026-03-08 | Updated after REVIEW-ADR-109-110*
