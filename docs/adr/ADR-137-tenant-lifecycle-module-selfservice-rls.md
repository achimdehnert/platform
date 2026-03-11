---
status: accepted
date: 2026-03-11
decision-makers: [Achim Dehnert]
implementation_status: partial
implementation_evidence:
  - "Phase 1 (TenantManager + Lifecycle): DONE — risk-hub packages/django-tenancy/ v0.2.0"
  - "1.1 TenantManager Dual-Mode: managers.py (auto-filter, for_tenant, unscoped, TenantQuerySet)"
  - "1.2 TenantModelAdmin: admin.py (get_queryset → unscoped)"
  - "1.3 TenantLifecycleMiddleware: lifecycle.py (suspended/trial-expired → 403, EXEMPT_PATHS)"
  - "1.4 ModuleSubscription.is_accessible: module_models.py (status + trial_ends_at + expires_at)"
  - "1.5 Session-Persistenz: middleware.py (_resolve_from_session + Membership-Check)"
  - "1.6 Tests: 13 Testdateien (managers, lifecycle, middleware, models, module_access, module_models, enable_rls, etc.)"
  - "Phase 2 (RLS-Policies): DONE — enable_rls + setup_rls_roles Management Commands"
  - "2.1 enable_rls: Cast-Introspection (UUID→uuid, BigInt→bigint), --dry-run, --disable, --table"
  - "2.3 setup_rls_roles: App-User vs Migrations-User (Table Owner = RLS-exempt)"
  - "Bonus: module_access.py — ModuleAccessMiddleware + require_module() Decorator + Role-Hierarchy"
  - "Phase 3 (Self-Service Module-Shop): DONE — packages/django-module-shop/ in risk-hub"
  - "3.1 Views: catalogue_view, detail_view, activate_view, cancel_view (login_required)"
  - "3.1 Templates: catalogue.html, detail.html"
  - "3.1 Catalogue-Service: catalogue.py (enrich mit ModuleSubscription-Status pro Tenant)"
  - "3.2 Activate-Redirect: billing-hub Checkout URL mit product/module/tenant_id/return_url"
  - "3.2 Settings: BILLING_HUB_CHECKOUT_URL, MODULE_SHOP_PRODUCT_NAME, MODULE_SHOP_CATALOGUE (8 Module)"
  - "3.x Tests: test_catalogue.py, test_views.py"
  - "3.x URLs: /billing/modules/ → django_module_shop.urls (INSTALLED_APPS + urls.py)"
  - "3.x Cancel: Stub (Log + Message), volle HMAC-Integration → Phase 4"
  - "Phase 4.1 TenantManager in alle Models: DONE — 11 Model-Dateien in src/ nutzen TenantManager"
  - "Phase 4.2 RLS auf Prod aktivieren: ausstehend — manage.py setup_rls_roles + enable_rls"
  - "Phase 4.3 billing/ App entfernen: ausstehend — nach billing-hub Migration"
  - "Phase 4.4 Template für weitere Hubs: ausstehend"
---

# ADR-137: Tenant-Lifecycle, Self-Service Module-Buchung und Row-Level Security

> **Umnummeriert von ADR-121** (ADR-121 jetzt für iil-outlinefw reserviert)

| Attribut       | Wert                                    |
|----------------|-----------------------------------------|
| **Status**     | Accepted                                |
| **Scope**      | platform, risk-hub, alle Django-Hub-Repos |
| **Repo**       | platform                                |
| **Erstellt**   | 2026-03-11                              |
| **Autor**      | Achim Dehnert                           |
| **Reviewer**   | –                                       |
| **Supersedes** | –                                       |
| **Relates to** | ADR-003 (risk-hub Tenancy), ADR-035 (Shared Django Tenancy), ADR-099 (Module-Monetarisierung), ADR-109 (Multi-Tenancy Standard), ADR-118 (billing-hub Platform Store) |

---

## 1. Kontext

### 1.1 Ausgangslage

Die Platform verfügt über ein solides Tenancy-Fundament:

- **ADR-035** definiert das `django-tenancy` Package (Organization, Membership, Middleware)
- **ADR-099** beschreibt ModuleSubscription/ModuleMembership als shared Package (Status: Proposed)
- **ADR-109** macht Multi-Tenancy zum Pflichtstandard für alle UI-Hubs (TenantModel, TenancyMode)
- **ADR-118** etabliert billing-hub als zentralen Platform Store (Registrierung, Stripe, activate/deactivate)

### 1.2 Problem / Lücken

Eine Analyse der risk-hub Codebase (Referenz-Implementierung) hat folgende **operativen Lücken** identifiziert, die von keinem bestehenden ADR abgedeckt werden:

| # | Lücke | Risiko | Betroffene ADRs |
|---|-------|--------|-----------------|
| L-1 | **Kein automatisches tenant_id-Filtering auf Query-Ebene** — jede View muss manuell `.filter(tenant_id=...)` aufrufen. Ein vergessener Filter = Cross-Tenant-Datenleck | **Kritisch (Security)** | ADR-035 §2.2 sagt explizit `for_tenant()`, ADR-109 definiert `TenantManager` — aber kein auto-filter |
| L-2 | **Keine PostgreSQL Row-Level Security Policies** — `set_db_tenant()` setzt Session-Variable, aber ohne RLS-Policies ist das wirkungslos | **Kritisch (Security)** | ADR-035 §2.2 erwähnt RLS, aber keine konkreten Policies definiert |
| L-3 | **Trial-Ablauf wird nicht enforced** — `trial_ends_at` existiert als Feld, wird aber nirgends geprüft | **Hoch (Revenue)** | ADR-118 §Trial-Ablauf definiert billing-hub Celery Beat, aber risk-hub hat eigene Stripe-Integration |
| L-4 | **Kein Self-Service Module-Shop innerhalb der App** — Kunden können Module nicht à la carte buchen, nur Plan-Bundles | **Hoch (Revenue)** | ADR-099 definiert Package-Struktur, aber keine UI/UX für Endkunden |
| L-5 | **Tenant-Picker nicht Session-persistent** — nach Login mit Multi-Org wird Tenant-Wahl nicht gespeichert | **Mittel (UX)** | Nicht adressiert |
| L-6 | **Drift: risk-hub verwendet UUIDField(primary_key=True)** statt BigAutoField + public_id wie ADR-109 vorschreibt | **Mittel (Konsistenz)** | ADR-109 Fix H-1 |

> **Priorisierung L-1 vs L-2**: TenantManager (L-1, Phase 1) ist schneller wirksam und
> deckt ~95% der Fälle ab. RLS (L-2, Phase 2) ist Defense-in-Depth für die restlichen 5%
> (raw SQL, Third-Party-Packages, Admin Custom Actions).

### 1.3 Constraints

- risk-hub ist die am weitesten fortgeschrittene Tenancy-Implementierung und dient als Pilot
- billing-hub (ADR-118) ist der zentrale Store für Neuregistrierungen — dieses ADR ergänzt den **In-App-Flow** für bestehende Tenants
- Eine Migration von UUID-PKs auf BigAutoField in risk-hub ist disruptiv und wird als separater Schritt behandelt
- RLS-Policies dürfen bestehende Queries nicht brechen (Defense-in-Depth, nicht Primary Guard)

---

## 2. Entscheidung

### 2.1 TenantManager mit Dual-Mode (auto-filter + explizit)

Alle `TenantModel`-Subklassen erhalten einen `TenantManager` als Default-Manager, der **zwei Modi** unterstützt:

```python
# django_tenancy/managers.py

class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant_id):
        """Expliziter Tenant-Filter (Celery, Management Commands)."""
        return self.filter(tenant_id=tenant_id)

    def unscoped(self):
        """Ohne auto-filter (Admin, Migrations, Cross-Tenant-Reports)."""
        return self.all()


class TenantManager(models.Manager):
    """Default Manager mit Context-basiertem auto-filter.

    In Request-Kontext (Middleware hat tenant_id gesetzt):
        MyModel.objects.all()  → automatisch gefiltert
    Ohne Kontext (Celery, Shell, Tests):
        MyModel.objects.all()  → ungefiltert (Fallback)
        MyModel.objects.for_tenant(uuid)  → explizit
    Admin/Reports:
        MyModel.objects.unscoped()  → explizit ungefiltert
    """

    def get_queryset(self):
        qs = TenantQuerySet(self.model, using=self._db)
        from django_tenancy.context import get_tenant_id
        tenant_id = get_tenant_id()
        if tenant_id is not None:
            return qs.filter(tenant_id=tenant_id)
        return qs

    def for_tenant(self, tenant_id):
        return TenantQuerySet(self.model, using=self._db).filter(tenant_id=tenant_id)

    def unscoped(self):
        return TenantQuerySet(self.model, using=self._db)
```

**Begründung**: ADR-035 entschied sich gegen auto-filter wegen Celery/Management-Command-Problemen. Dieser Entwurf löst das durch Fallback: ohne Context-Variable kein Filter. Admin-Queries nutzen `.unscoped()` explizit.

**Django Admin**: Der auto-filter Manager betrifft auch den Django Admin. Damit Staff-User alle Tenants sehen können, stellt das Package eine `TenantModelAdmin` Base-Class bereit:

```python
# django_tenancy/admin.py
class TenantModelAdmin(admin.ModelAdmin):
    """Admin Base-Class die den auto-filter bypassed."""
    def get_queryset(self, request):
        return self.model.objects.unscoped()
```

Alle Admin-Registrierungen für TenantModel-Subklassen sollten von `TenantModelAdmin` erben.

**Migration**: Bestehende `.filter(tenant_id=...)` Aufrufe in Views werden redundant aber nicht schädlich. Schrittweise Entfernung nach Rollout.

### 2.2 PostgreSQL Row-Level Security (Defense-in-Depth)

RLS als **zweite Schutzschicht** neben dem Application-Level-Filter:

#### Voraussetzung: Separater DB-User für Migrations

RLS erfordert **zwei PostgreSQL Rollen**:

| Rolle | Zweck | RLS-Verhalten |
|-------|-------|---------------|
| `risk_hub` (App-User) | Gunicorn, Celery | RLS aktiv — sieht nur eigenen Tenant |
| `risk_hub_admin` (Migrations-User) | `migrate`, `createsuperuser`, `loaddata` | RLS-exempt (Table Owner, kein `FORCE`) |

Der App-User darf **nicht** Table Owner sein. Tables gehören `risk_hub_admin`, der App-User bekommt `GRANT ALL ON ALL TABLES` ohne Ownership.

#### RLS-Policy (parametrischer Cast)

```sql
-- Migration: 0003_enable_rls.py (django_tenancy)
-- Für jede Tabelle, die TenantModel erbt:

ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

-- Policy: App-User sieht nur eigenen Tenant
-- Cast-Typ wird vom Management Command introspektiert:
--   BigIntegerField → ::bigint
--   UUIDField       → ::uuid
CREATE POLICY tenant_isolation_{table} ON {table}
    FOR ALL
    USING (
        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::{cast_type}
        OR current_setting('app.tenant_id', true) IS NULL
        OR current_setting('app.tenant_id', true) = ''
    );

-- KEIN FORCE ROW LEVEL SECURITY — der Migrations-User (Table Owner)
-- bleibt RLS-exempt. Nur der App-User (non-owner) wird durch RLS eingeschränkt.
```

**Wichtig**: Die `OR current_setting IS NULL` Klausel stellt sicher, dass:
- Celery Tasks, die `set_db_tenant()` nicht aufrufen, nicht geblockt werden
- Nur wenn `app.tenant_id` **explizit gesetzt** ist, wird gefiltert
- Der Migrations-User (Table Owner) ist automatisch RLS-exempt (kein `FORCE`)

**Cast-Typ-Erkennung**: Das `enable_rls` Management Command introspektiert den `tenant_id`-Feld-Typ jedes Models:
- `models.BigIntegerField` → `::bigint` (ADR-109-konforme Models)
- `models.UUIDField` → `::uuid` (risk-hub Legacy-Models)

**Management Command** für Rollout:

```bash
python manage.py enable_rls --dry-run     # zeigt SQL mit korrektem Cast pro Tabelle
python manage.py enable_rls               # führt aus
python manage.py enable_rls --table=risk_assessment  # einzelne Tabelle
```

**DB-Setup** (einmalig pro Repo):

```sql
-- Separaten App-User anlegen (falls noch nicht vorhanden)
CREATE ROLE risk_hub LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE risk_hub TO risk_hub;
GRANT USAGE ON SCHEMA public TO risk_hub;
GRANT ALL ON ALL TABLES IN SCHEMA public TO risk_hub;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO risk_hub;
-- Tables bleiben im Besitz von risk_hub_admin (Migrations-User)
```

### 2.3 Tenant-Lifecycle Enforcement

#### 2.3.1 Trial-Ablauf (In-App + billing-hub)

Zwei komplementäre Mechanismen:

**A) billing-hub Celery Beat** (ADR-118, bereits definiert):
- Täglicher Job prüft `Subscription.trial_ends_at`
- Sendet Reminder (3 Tage vorher) und deactivate-Call

**B) In-App Middleware Guard** (NEU — für den Fall, dass billing-hub den deactivate-Call nicht rechtzeitig sendet):

```python
# django_tenancy/lifecycle.py

from django.conf import settings

class TenantLifecycleMiddleware(MiddlewareMixin):
    """Prüft ob der aktuelle Tenant aktiv ist.

    Läuft NACH SubdomainTenantMiddleware.
    Blockt Requests für suspended/expired Tenants mit Info-Seite.
    """

    EXEMPT_PATHS = frozenset([
        "/livez/", "/healthz/", "/static/", "/accounts/",
        "/api/internal/", "/billing/", "/admin/",
    ])

    def process_request(self, request):
        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            return None

        org = getattr(request, "tenant", None)
        if org is None:
            return None

        if org.status == "suspended":
            return render(request, "tenancy/suspended.html", status=403)

        if org.status == "trial" and org.trial_ends_at:
            from django.utils import timezone
            if org.trial_ends_at < timezone.now():
                return render(request, "tenancy/trial_expired.html", {
                    "org": org,
                    "upgrade_url": getattr(settings, "BILLING_UPGRADE_URL", "/billing/"),
                }, status=403)

        return None
```

> **Hinweis**: HTTP 403 statt 402 — HTTP 402 ("Payment Required") ist offiziell
> "reserved for future use" und wird von manchen Proxies/CDNs unerwartet behandelt.
> Die Template-Seite enthält den Upgrade-CTA, der Status-Code signalisiert "Zugriff verweigert".

#### 2.3.2 ModuleSubscription.is_accessible mit Zeitprüfung

```python
# django_tenancy/module_models.py — Erweiterung

@property
def is_accessible(self) -> bool:
    from django.utils import timezone
    now = timezone.now()

    if self.status == self.Status.SUSPENDED:
        return False

    if self.status == self.Status.TRIAL:
        if self.trial_ends_at and self.trial_ends_at < now:
            return False

    if self.expires_at and self.expires_at < now:
        return False

    return self.status in (self.Status.TRIAL, self.Status.ACTIVE)
```

### 2.4 Self-Service Module-Buchung (In-App)

Ergänzt ADR-118 (billing-hub für Neuregistrierung) um **In-App Module-Verwaltung** für bestehende Tenants.

> **Abgrenzung zu ADR-118**: billing-hub bleibt die **einzige Stripe-Integration**.
> Der In-App Module-Shop zeigt den Katalog und leitet für Checkout/Bezahlung
> an billing-hub weiter. Keine eigene Stripe-Integration in der Ziel-App.
> risk-hub's bestehende `billing/`-App wird nach billing-hub-Migration entfernt.

#### 2.4.1 Module-Shop View (In-App, kein eigenes Stripe)

```
/modules/                          → Modul-Katalog (aktive, verfügbare, gesperrte Module)
/modules/<code>/                   → Modul-Detail + "Jetzt aktivieren" Button
/modules/<code>/activate/          → POST: Redirect zu billing-hub Checkout
/modules/<code>/cancel/            → POST: Deactivation-Request an billing-hub
```

Der Activate-Flow delegiert an billing-hub:

```
POST /modules/ex/activate/
  → App generiert Redirect-URL:
    billing.iil.pet/checkout?product=risk-hub&module=ex&tenant_id=<uuid>
  → billing-hub: Stripe Checkout Session
  → Stripe Webhook → billing-hub
  → billing-hub → POST /api/internal/activate/ an risk-hub (HMAC-signiert, ADR-118)
  → risk-hub: ModuleSubscription + ModuleMembership erstellt
  → User wird zurückgeleitet: /modules/?activated=ex
```

**Stripe Price-Objekte** werden in billing-hub's `ProductCatalog` verwaltet (nicht in der Ziel-App).
**Webhooks** gehen an billing-hub, der die Ziel-App via `/api/internal/activate/` benachrichtigt.

#### 2.4.2 Preismodell: Bundle + À-la-carte

```python
# settings.py — MODULE_SHOP_CATALOGUE (nur Katalog-Metadaten, keine Stripe-IDs)

MODULE_SHOP_CATALOGUE = {
    "risk": {
        "name": "Risikobewertung",
        "description": "Gefährdungsbeurteilungen erstellen und verwalten",
        "included_in_plans": ["professional", "business", "enterprise"],
        "standalone_bookable": True,  # à la carte buchbar via billing-hub
        "trial_days": 14,
        "icon": "shield-alert",
    },
    ...
}

# Plan-Bundles (wie bisher)
PLAN_MODULES = {
    "starter": ["gbu"],
    "professional": ["risk", "dsb", "gbu", "actions", "documents"],
    "business": ["risk", "ex", "substances", "dsb", "gbu", "documents", "actions", "brandschutz"],
}
```

Preise und Stripe-IDs liegen ausschließlich in billing-hub's `Product`-Model (ADR-118 §Neue Komponenten).

#### 2.4.3 Flow

```
Bestehender Tenant (eingeloggt) → /modules/
    → Sieht: aktive Module (grün), verfügbare Module (blau), gesperrte (grau)
    → Klickt "Explosionsschutz aktivieren"
    → Redirect zu billing.iil.pet/checkout?product=risk-hub&module=ex&tenant_id=<uuid>
    → billing-hub: Stripe Checkout
    → Webhook → billing-hub → POST /api/internal/activate/ (HMAC)
    → risk-hub: ModuleSubscription.status = active + ModuleMembership für Admin
    → Redirect zurück: /modules/?activated=ex mit Erfolgsmeldung
```

### 2.5 Tenant-Picker Session-Persistenz

```python
# django_tenancy/middleware.py — Erweiterung SubdomainTenantMiddleware

# Nach erfolgreicher Tenant-Resolution:
request.session["_tenant_id"] = str(org.tenant_id)

# Vor Subdomain-Lookup (Fallback wenn kein Subdomain):
session_tid = request.session.get("_tenant_id")
if session_tid and request.user.is_authenticated:
    # Security: Membership-Check verhindert Session-Manipulation
    from django_tenancy.models import Membership
    has_access = Membership.objects.filter(
        user=request.user,
        organization__tenant_id=session_tid,
    ).exists()
    if has_access:
        org = Organization.objects.filter(tenant_id=session_tid).first()
        if org and org.is_active:
            # Session-basierte Resolution
            ...
```

> **Security**: Der Membership-Check ist zwingend — ohne ihn könnte ein User
> seine Session manipulieren und sich Zugang zu einem fremden Tenant verschaffen.

### 2.6 risk-hub Drift-Konsolidierung (UUID → BigAutoField)

**Langfrist-Ziel**: Alle Models auf `BigAutoField` PK + `public_id UUID` (ADR-109 Fix H-1).

**Pragmatischer Ansatz für risk-hub** (Phase 1 — kein PK-Wechsel):

1. `tenant_id` bleibt `UUIDField` (Wechsel auf BigIntegerField zu disruptiv bei laufender Prod)
2. Neue Models verwenden `TenantModel` aus ADR-109 (BigAutoField PK)
3. Bestehende Models erhalten `TenantManager` als Default-Manager
4. RLS-Policies verwenden `::uuid` Cast statt `::bigint`

**Phase 2** (separates ADR, nach Produktionsstart): Schrittweise Migration bestehender UUID-PKs auf BigAutoField + public_id. Nicht in Scope dieses ADR → Hygiene Backlog.

---

## 3. Betrachtete Alternativen

### 3.1 Kein auto-filter (Status quo, ADR-035 Entscheidung)

- **Abgelehnt**: Die risk-hub Analyse zeigt ~40 Views mit manuellen `.filter(tenant_id=...)` Aufrufen. Jeder vergessene Filter ist ein potenzielles Datenleck. Der Dual-Mode-Manager löst die Celery/Shell-Problematik.

### 3.2 RLS als Primary Guard (kein Application-Level-Filter)

- **Abgelehnt**: RLS allein ist nicht ausreichend — Django Admin, Management Commands und bestimmte ORM-Patterns können RLS umgehen. RLS ist Defense-in-Depth, nicht Ersatz.

### 3.3 Module-Buchung nur über billing-hub (kein In-App-Shop)

- **Abgelehnt**: billing-hub (ADR-118) ist für Neuregistrierung optimiert. Bestehende Tenants, die ein zusätzliches Modul buchen wollen, müssen das innerhalb ihrer App tun können — UX-Bruch bei Redirect zu billing-hub für Einzelmodul-Upgrade. Der In-App Module-Shop zeigt den Katalog, die Bezahlung delegiert an billing-hub.

### 3.4 Sofortige UUID → BigAutoField Migration in risk-hub

- **Abgelehnt**: Zu disruptiv bei laufender Produktion. Schrittweise Migration in separatem ADR.

---

## 4. Begründung im Detail

### 4.1 Warum Dual-Mode TenantManager?

Die Entscheidung in ADR-035 gegen auto-filter war korrekt für den damaligen Stand. Inzwischen zeigt die Praxis:

- **40+ Views** in risk-hub mit manuellen Filtern — hohe Fehleranfälligkeit
- **Celery Tasks** können `for_tenant()` explizit aufrufen
- **Django Admin** nutzt `TenantModelAdmin` mit `.unscoped()` (explizite Base-Class)
- **Management Commands** laufen ohne Context → kein Filter (sicherer Fallback)

### 4.2 Warum RLS zusätzlich zum Application-Filter?

Defense-in-Depth-Prinzip: Selbst wenn ein Bug im Python-Code den tenant_id-Filter vergisst, verhindert die DB-Ebene Cross-Tenant-Zugriff. Das ist besonders wichtig für:

- Third-Party-Packages die raw SQL verwenden
- Django Admin Custom Actions
- Management Commands die versehentlich ohne Tenant-Kontext laufen

### 4.3 Warum In-App Module-Shop UND billing-hub?

| Szenario | Zuständig | Stripe |
|----------|-----------|--------|
| Neuer Kunde registriert sich | billing-hub (ADR-118) | billing-hub |
| Bestehender Kunde bucht Modul dazu | **In-App Module-Shop** → billing-hub Checkout | billing-hub |
| Trial läuft ab → Upgrade | billing-hub Reminder + In-App Upgrade-Wall | billing-hub |
| Plan-Wechsel (Starter → Professional) | billing-hub Customer Portal | billing-hub |

**Stripe bleibt ausschließlich in billing-hub** — die Ziel-App zeigt nur den Katalog und leitet für Checkout weiter. Kein Widerspruch zu ADR-118.

---

## 5. Implementation Plan

### Phase 1: TenantManager + Lifecycle (Woche 1-2)

| # | Task | Repo | Aufwand |
|---|------|------|---------|
| 1.1 | `TenantManager` Dual-Mode in `django_tenancy/managers.py` | platform | 2h |
| 1.2 | `TenantModelAdmin` in `django_tenancy/admin.py` | platform | 1h |
| 1.3 | `TenantLifecycleMiddleware` in `django_tenancy/lifecycle.py` | platform | 2h |
| 1.4 | `ModuleSubscription.is_accessible` Zeitprüfung | platform | 1h |
| 1.5 | Tenant-Picker Session-Persistenz in Middleware (mit Membership-Check) | platform | 1h |
| 1.6 | Tests für alle neuen Komponenten | platform | 4h |

### Phase 2: RLS-Policies (Woche 2-3)

| # | Task | Repo | Aufwand |
|---|------|------|---------|
| 2.1 | Management Command `enable_rls` (mit Cast-Typ-Introspection) | platform | 3h |
| 2.2 | RLS-Migration Template (generisch für alle TenantModel-Tabellen) | platform | 2h |
| 2.3 | DB-User-Separation (App-User vs Migrations-User) dokumentieren | platform | 1h |
| 2.4 | Rollout auf risk-hub Staging | risk-hub | 2h |
| 2.5 | Validierung: kein Query-Bruch in bestehenden Views | risk-hub | 4h |

### Phase 3: Self-Service Module-Shop (Woche 3-4)

| # | Task | Repo | Aufwand |
|---|------|------|---------|
| 3.1 | Module-Shop Views + Templates (Katalog, Detail) | risk-hub | 6h |
| 3.2 | Activate-Redirect zu billing-hub Checkout | risk-hub | 2h |
| 3.3 | billing-hub: `Product` für risk-hub Module anlegen | billing-hub | 2h |
| 3.4 | Auto-Provision ModuleMembership im activate-Endpoint | risk-hub | 2h |
| 3.5 | Self-Service Registration auf Production freischalten | risk-hub | 2h |
| 3.6 | End-to-End Test (Stripe Testmodus) | risk-hub | 4h |

### Phase 4: Rollout auf weitere Repos (Woche 5+)

| # | Task | Repo | Aufwand |
|---|------|------|---------|
| 4.1 | TenantManager in bestehende Models integrieren | risk-hub | 4h |
| 4.2 | RLS auf alle risk-hub Tabellen (inkl. DB-User-Separation) | risk-hub | 3h |
| 4.3 | risk-hub `billing/` App entfernen → billing-hub Migration | risk-hub | 4h |
| 4.4 | Template für weitere Hubs dokumentieren | platform | 2h |

---

## 6. Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| auto-filter bricht bestehende Admin-Queries | Mittel | Mittel | `TenantModelAdmin` Base-Class mit `.unscoped()`, Feature-Flag `TENANT_MANAGER_AUTO_FILTER=True/False` |
| RLS-Policies blockieren Migrations | Niedrig | Hoch | Kein `FORCE RLS`, separater Migrations-User (Table Owner), `enable_rls --dry-run` |
| billing-hub Ausfall blockiert Modul-Buchungen | Niedrig | Mittel | Bestehende Module funktionieren weiter, nur neue Buchungen betroffen. Health-Monitoring |
| UUID→BigAutoField Migration in Phase 2 scheitert | Mittel | Hoch | Nicht in Scope dieses ADR, separates ADR |

---

## 7. Konsequenzen

### 7.1 Positiv

- **Security**: Zwei unabhängige Schutzschichten (Application + DB) gegen Cross-Tenant-Datenlecks
- **Revenue**: Self-Service Module-Buchung ermöglicht skalierbare Kundengewinnung
- **DX**: TenantManager auto-filter reduziert Boilerplate und Fehlerquellen in Views
- **UX**: Trial-Ablauf wird sichtbar (Upgrade-Wall statt stiller Weiterbetrieb)
- **Konsistenz**: Lifecycle-Enforcement als Platform-Standard, nicht pro-Repo-Logik

### 7.2 Trade-offs

- **Komplexität**: TenantManager auto-filter erfordert Verständnis des Dual-Mode-Patterns
- **Migration**: RLS-Rollout muss pro Tabelle validiert werden
- **billing-hub Dependency**: In-App Module-Shop hängt von billing-hub Checkout ab — billing-hub Ausfall blockiert neue Modul-Buchungen (nicht bestehende)

### 7.3 Nicht in Scope

- UUID → BigAutoField PK-Migration in risk-hub (separates ADR → Hygiene Backlog)
- SSO / Cross-App Identity (ADR-118 explizit ausgeschlossen)
- Metered Billing / Usage-Quotas (Zukunft, wenn Bedarf)
- billing-hub Implementierung (ADR-118)
- Stripe-Integration in der Ziel-App (liegt bei billing-hub, ADR-118)

---

## 8. Validation Criteria

### Phase 1 (TenantManager + Lifecycle)

- [ ] `TenantManager.get_queryset()` filtert automatisch wenn Context gesetzt
- [ ] `TenantManager.get_queryset()` filtert NICHT wenn kein Context (Celery, Shell)
- [ ] `TenantManager.unscoped()` liefert immer alle Records
- [ ] `TenantModelAdmin.get_queryset()` liefert alle Records (Admin)
- [ ] `TenantLifecycleMiddleware` blockt suspended Tenants mit Info-Seite
- [ ] `TenantLifecycleMiddleware` zeigt Upgrade-Wall bei abgelaufenem Trial (HTTP 403)
- [ ] `ModuleSubscription.is_accessible` gibt False bei abgelaufenem Trial
- [ ] Tenant-Picker Wahl überlebt Page-Refresh (Session)
- [ ] Session-Tenant wird nur akzeptiert wenn User Membership hat (Security)

### Phase 2 (RLS)

- [ ] `enable_rls --dry-run` zeigt korrekte SQL mit passendem Cast-Typ pro Tabelle
- [ ] Mit gesetztem `app.tenant_id`: nur eigene Tenant-Daten sichtbar (App-User)
- [ ] Ohne `app.tenant_id` (Celery, Shell): alle Daten sichtbar (App-User, Fallback)
- [ ] Migrations-User (Table Owner): alle Daten sichtbar (RLS-exempt, kein FORCE)
- [ ] Django Admin funktioniert uneingeschränkt
- [ ] Bestehende risk-hub Views + API liefern identische Ergebnisse

### Phase 3 (Module-Shop)

- [ ] Module-Katalog zeigt alle verfügbaren Module mit Status (aktiv/verfügbar/gesperrt)
- [ ] "Aktivieren"-Button leitet korrekt an billing-hub Checkout weiter
- [ ] billing-hub activate-Webhook erstellt ModuleSubscription + ModuleMembership
- [ ] Modul-Kündigung sendet Deactivation-Request an billing-hub
- [ ] Redirect zurück zur App nach erfolgreichem Checkout

---

## 9. Referenzen

- **ADR-003**: risk-hub Tenancy (Ursprungs-Design für tenant_id-Pattern)
- **ADR-035**: Shared Django Tenancy Package (Package-Struktur)
- **ADR-099**: Modul-Konfiguration und Monetarisierungsstrategie (Proposed)
- **ADR-109**: Multi-Tenancy als Platform-Standard (TenantModel, TenancyMode)
- **ADR-118**: billing-hub als Platform Store (Registrierung, Stripe, activate/deactivate)
- **risk-hub Codebase-Analyse**: `packages/django-tenancy/`, `src/tenancy/`, `src/billing/`, `src/common/middleware.py`

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-03-11 | Achim Dehnert | Initial draft — basierend auf risk-hub Codebase-Analyse |
| 2026-03-11 | Achim Dehnert | Review-Fixes v1.1: B-1 RLS Policy (kein FORCE, separater DB-User), B-2 parametrischer Cast (bigint/uuid), B-3 settings.get→getattr, B-4 Stripe nur in billing-hub (ADR-118-konform), S-1 TenantModelAdmin, S-2 Session-Membership-Check, S-5 HTTP 403 statt 402, N-2 ADR-003 Referenz, N-3 Priorisierung L-1 vs L-2 |
