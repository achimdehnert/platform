# ADR-137: Tenant-Lifecycle, Self-Service Module-Buchung und Row-Level Security

> **Umnummeriert von ADR-121** (ADR-121 jetzt für iil-outlinefw reserviert)

| Attribut       | Wert                                    |
|----------------|-----------------------------------------|
| **Status**     | Proposed                                |
| **Scope**      | platform, risk-hub, alle Django-Hub-Repos |
| **Repo**       | platform                                |
| **Erstellt**   | 2026-03-11                              |
| **Autor**      | Achim Dehnert                           |
| **Reviewer**   | –                                       |
| **Supersedes** | –                                       |
| **Relates to** | ADR-035 (Shared Django Tenancy), ADR-099 (Module-Monetarisierung), ADR-109 (Multi-Tenancy Standard), ADR-118 (billing-hub Platform Store) |

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

**Migration**: Bestehende `.filter(tenant_id=...)` Aufrufe in Views werden redundant aber nicht schädlich. Schrittweise Entfernung nach Rollout.

### 2.2 PostgreSQL Row-Level Security (Defense-in-Depth)

RLS als **zweite Schutzschicht** neben dem Application-Level-Filter:

```sql
-- Migration: 0003_enable_rls.py (django_tenancy)
-- Für jede Tabelle, die TenantModel erbt:

ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

-- Policy: App-User sieht nur eigenen Tenant
CREATE POLICY tenant_isolation_{table} ON {table}
    FOR ALL
    TO current_user
    USING (
        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
        OR current_setting('app.tenant_id', true) IS NULL
        OR current_setting('app.tenant_id', true) = ''
    );

-- FORCE RLS auch für Table Owner (wichtig!)
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
```

**Wichtig**: Die `OR current_setting IS NULL` Klausel stellt sicher, dass:
- Migrations und Management Commands (ohne Session-Variable) weiterhin funktionieren
- Celery Tasks, die `set_db_tenant()` nicht aufrufen, nicht geblockt werden
- Nur wenn `app.tenant_id` **explizit gesetzt** ist, wird gefiltert

**Management Command** für Rollout:

```bash
python manage.py enable_rls --dry-run     # zeigt SQL
python manage.py enable_rls               # führt aus
python manage.py enable_rls --table=risk_assessment  # einzelne Tabelle
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
                    "upgrade_url": settings.get("BILLING_UPGRADE_URL", "/billing/"),
                }, status=402)

        return None
```

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

Ergänzt ADR-118 (billing-hub für Neuregistrierung) um **In-App Module-Verwaltung** für bestehende Tenants:

#### 2.4.1 Module-Shop View (django-module-shop oder in-app)

```
/billing/modules/                  → Modul-Katalog (alle verfügbaren Module mit Preisen)
/billing/modules/<code>/           → Modul-Detail + "Jetzt aktivieren" Button
/billing/modules/<code>/activate/  → POST: Stripe Checkout für Einzelmodul
/billing/modules/<code>/cancel/    → POST: Modul-Kündigung (Soft-Deactivate)
```

#### 2.4.2 Preismodell: Bundle + À-la-carte

```python
# settings.py — Erweiterte MODULE_SHOP_CATALOGUE

MODULE_SHOP_CATALOGUE = {
    "risk": {
        "name": "Risikobewertung",
        "price_month": 29.0,
        "price_year": 290.0,
        "stripe_price_monthly": "price_...",
        "stripe_price_yearly": "price_...",
        "included_in_plans": ["professional", "business", "enterprise"],
        "standalone_bookable": True,  # NEU: à la carte buchbar
        "trial_days": 14,
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

#### 2.4.3 Flow

```
Bestehender Tenant (eingeloggt) → /billing/modules/
    → Sieht: aktive Module (grün), verfügbare Module (blau), gesperrte (grau)
    → Klickt "Explosionsschutz aktivieren"
    → Stripe Checkout (Einzelmodul-Preis oder Upgrade auf höheren Plan)
    → Webhook: ModuleSubscription.status = active
    → ModuleMembership für Admin-User automatisch erstellt
    → Redirect: /billing/modules/ mit Erfolgsmeldung
```

### 2.5 Tenant-Picker Session-Persistenz

```python
# django_tenancy/middleware.py — Erweiterung SubdomainTenantMiddleware

# Nach erfolgreicher Tenant-Resolution:
request.session["_tenant_id"] = str(org.tenant_id)

# Vor Subdomain-Lookup (Fallback wenn kein Subdomain):
session_tid = request.session.get("_tenant_id")
if session_tid:
    org = Organization.objects.filter(tenant_id=session_tid).first()
    if org and org.is_active:
        # Session-basierte Resolution
        ...
```

### 2.6 risk-hub Drift-Konsolidierung (UUID → BigAutoField)

**Langfrist-Ziel**: Alle Models auf `BigAutoField` PK + `public_id UUID` (ADR-109 Fix H-1).

**Pragmatischer Ansatz für risk-hub** (Phase 1 — kein PK-Wechsel):

1. `tenant_id` bleibt `UUIDField` (Wechsel auf BigIntegerField zu disruptiv bei laufender Prod)
2. Neue Models verwenden `TenantModel` aus ADR-109 (BigAutoField PK)
3. Bestehende Models erhalten `TenantManager` als Default-Manager
4. RLS-Policies verwenden `::uuid` Cast statt `::bigint`

**Phase 2** (separates ADR, nach Produktionsstart): Schrittweise Migration bestehender UUID-PKs auf BigAutoField + public_id. Nicht in Scope dieses ADR.

---

## 3. Betrachtete Alternativen

### 3.1 Kein auto-filter (Status quo, ADR-035 Entscheidung)

- **Abgelehnt**: Die risk-hub Analyse zeigt ~40 Views mit manuellen `.filter(tenant_id=...)` Aufrufen. Jeder vergessene Filter ist ein potenzielles Datenleck. Der Dual-Mode-Manager löst die Celery/Shell-Problematik.

### 3.2 RLS als Primary Guard (kein Application-Level-Filter)

- **Abgelehnt**: RLS allein ist nicht ausreichend — Django Admin, Management Commands und bestimmte ORM-Patterns können RLS umgehen. RLS ist Defense-in-Depth, nicht Ersatz.

### 3.3 Module-Buchung nur über billing-hub (kein In-App-Shop)

- **Abgelehnt**: billing-hub (ADR-118) ist für Neuregistrierung optimiert. Bestehende Tenants, die ein zusätzliches Modul buchen wollen, müssen das innerhalb ihrer App tun können — UX-Bruch bei Redirect zu billing-hub für Einzelmodul-Upgrade.

### 3.4 Sofortige UUID → BigAutoField Migration in risk-hub

- **Abgelehnt**: Zu disruptiv bei laufender Produktion. Schrittweise Migration in separatem ADR.

---

## 4. Begründung im Detail

### 4.1 Warum Dual-Mode TenantManager?

Die Entscheidung in ADR-035 gegen auto-filter war korrekt für den damaligen Stand. Inzwischen zeigt die Praxis:

- **40+ Views** in risk-hub mit manuellen Filtern — hohe Fehleranfälligkeit
- **Celery Tasks** können `for_tenant()` explizit aufrufen
- **Django Admin** nutzt `.unscoped()` automatisch (Admin-ModelAdmin-Konfiguration)
- **Management Commands** laufen ohne Context → kein Filter (sicherer Fallback)

### 4.2 Warum RLS zusätzlich zum Application-Filter?

Defense-in-Depth-Prinzip: Selbst wenn ein Bug im Python-Code den tenant_id-Filter vergisst, verhindert die DB-Ebene Cross-Tenant-Zugriff. Das ist besonders wichtig für:

- Third-Party-Packages die raw SQL verwenden
- Django Admin Custom Actions
- Management Commands die versehentlich ohne Tenant-Kontext laufen

### 4.3 Warum In-App Module-Shop UND billing-hub?

| Szenario | Zuständig |
|----------|-----------|
| Neuer Kunde registriert sich | billing-hub (ADR-118) |
| Bestehender Kunde bucht Modul dazu | **In-App Module-Shop** (dieses ADR) |
| Trial läuft ab → Upgrade | billing-hub Reminder + In-App Upgrade-Wall |
| Plan-Wechsel (Starter → Professional) | billing-hub Customer Portal |

---

## 5. Implementation Plan

### Phase 1: TenantManager + Lifecycle (Woche 1-2)

| # | Task | Repo | Aufwand |
|---|------|------|---------|
| 1.1 | `TenantManager` Dual-Mode in `django_tenancy/managers.py` | platform | 2h |
| 1.2 | `TenantLifecycleMiddleware` in `django_tenancy/lifecycle.py` | platform | 2h |
| 1.3 | `ModuleSubscription.is_accessible` Zeitprüfung | platform | 1h |
| 1.4 | Tenant-Picker Session-Persistenz in Middleware | platform | 1h |
| 1.5 | Tests für alle neuen Komponenten | platform | 4h |

### Phase 2: RLS-Policies (Woche 2-3)

| # | Task | Repo | Aufwand |
|---|------|------|---------|
| 2.1 | Management Command `enable_rls` | platform | 3h |
| 2.2 | RLS-Migration Template (generisch für alle TenantModel-Tabellen) | platform | 2h |
| 2.3 | Rollout auf risk-hub Staging | risk-hub | 2h |
| 2.4 | Validierung: kein Query-Bruch in bestehenden Views | risk-hub | 4h |

### Phase 3: Self-Service Module-Shop (Woche 3-4)

| # | Task | Repo | Aufwand |
|---|------|------|---------|
| 3.1 | Module-Shop Views + Templates | risk-hub | 6h |
| 3.2 | Stripe Checkout für Einzelmodule | risk-hub | 4h |
| 3.3 | Auto-Provision ModuleMembership nach Checkout | risk-hub | 2h |
| 3.4 | Self-Service Registration auf Production | risk-hub | 2h |
| 3.5 | End-to-End Test (Stripe Testmodus) | risk-hub | 4h |

### Phase 4: Rollout auf weitere Repos (Woche 5+)

| # | Task | Repo | Aufwand |
|---|------|------|---------|
| 4.1 | TenantManager in bestehende Models integrieren | risk-hub | 4h |
| 4.2 | RLS auf alle risk-hub Tabellen | risk-hub | 2h |
| 4.3 | Template für weitere Hubs dokumentieren | platform | 2h |

---

## 6. Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| auto-filter bricht bestehende Admin-Queries | Mittel | Mittel | `.unscoped()` für Admin, Feature-Flag `TENANT_MANAGER_AUTO_FILTER=True/False` |
| RLS-Policies blockieren Migrations | Niedrig | Hoch | `OR current_setting IS NULL` Klausel, `enable_rls --dry-run` |
| Stripe Checkout für Einzelmodule komplex | Niedrig | Mittel | Bereits in risk-hub/billing vorhanden, nur Erweiterung |
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
- **Dual-Billing**: In-App Stripe + billing-hub müssen konsistent bleiben (Module-Status-Sync)

### 7.3 Nicht in Scope

- UUID → BigAutoField PK-Migration in risk-hub (separates ADR)
- SSO / Cross-App Identity (ADR-118 explizit ausgeschlossen)
- Metered Billing / Usage-Quotas (Zukunft, wenn Bedarf)
- billing-hub Implementierung (ADR-118)

---

## 8. Validation Criteria

### Phase 1 (TenantManager + Lifecycle)

- [ ] `TenantManager.get_queryset()` filtert automatisch wenn Context gesetzt
- [ ] `TenantManager.get_queryset()` filtert NICHT wenn kein Context (Celery, Shell)
- [ ] `TenantManager.unscoped()` liefert immer alle Records
- [ ] `TenantLifecycleMiddleware` blockt suspended Tenants mit Info-Seite
- [ ] `TenantLifecycleMiddleware` zeigt Upgrade-Wall bei abgelaufenem Trial
- [ ] `ModuleSubscription.is_accessible` gibt False bei abgelaufenem Trial
- [ ] Tenant-Picker Wahl überlebt Page-Refresh (Session)

### Phase 2 (RLS)

- [ ] `enable_rls --dry-run` zeigt korrekte SQL für alle TenantModel-Tabellen
- [ ] Mit gesetztem `app.tenant_id`: nur eigene Tenant-Daten sichtbar
- [ ] Ohne `app.tenant_id` (Celery, Migrations): alle Daten sichtbar
- [ ] Django Admin funktioniert uneingeschränkt
- [ ] Bestehende risk-hub Views + API liefern identische Ergebnisse

### Phase 3 (Module-Shop)

- [ ] Module-Katalog zeigt alle verfügbaren Module mit Preisen
- [ ] Einzelmodul-Checkout erzeugt Stripe Session
- [ ] Nach Checkout: ModuleSubscription + ModuleMembership automatisch erstellt
- [ ] Modul-Kündigung setzt Status auf suspended (nicht gelöscht)

---

## 9. Referenzen

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
