---
status: accepted
date: 2026-03-25
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []  # ADR-152 (tax-hub Pilot) never published — see related
amends: []
related:
  - ADR-007   # Tenant, Plan, Feature-Tabellen (Vorbildmuster)
  - ADR-050   # Hub Landscape
  - ADR-072   # PostgreSQL Schema-Isolation für SaaS
  - ADR-035   # Shared Django Tenancy
  - ADR-021   # Unified Deployment
  - ADR-078   # Docker HEALTHCHECK
  - ADR-146   # DvelopDmsClient
  - ADR-152   # Pilot-ADR (superseded)
  - ADR-079   # Temporal Workflow-Engine (bfagent)
last_reviewed: 2026-05-08
staleness_months: 6
drift_check_paths:
  - tax-hub/apps/modules/
  - tax-hub/apps/billing/
  - tax-hub/apps/tenant/
  - tax-hub/apps/workflows/
---

# ADR-153: Adopt Module-basierte SaaS-Architektur für tax-hub (Multi-Mandant, buchbare Module)

## Metadaten

| Attribut       | Wert                                                                        |
|----------------|-----------------------------------------------------------------------------|
| **Status**     | Accepted                                                                    |
| **Scope**      | platform + service                                                          |
| **Erstellt**   | 2026-03-25                                                                  |
| **Autor**      | Achim Dehnert                                                               |
| **Supersedes** | ADR-152 (tax-hub Pilot — Scope zu eng für SaaS)                             |
| **Relates to** | ADR-007, ADR-050, ADR-072, ADR-035, ADR-021, ADR-079, ADR-146               |

## Repo-Zugehörigkeit

| Repo       | Rolle    | Betroffene Pfade                                       |
|------------|----------|--------------------------------------------------------|
| `tax-hub`  | Primär   | komplett — SaaS-Architektur von Grund auf              |
| `platform` | Referenz | `docs/adr/`, ADR-021 Port-Tabelle (Port 8096)          |

---

## Decision Drivers

- **Mehrere Steuerberatungsbüros**: tax-hub soll nicht nur für einen Piloten laufen,
  sondern als vollständiges B2B-SaaS für Steuerberatungskanzleien vermarktbar sein.
- **Unterschiedliche Budgets und Bedürfnisse**: Kleinkanzlei (2 Berater, 50 Mandanten)
  hat andere Anforderungen als mittelgroße Kanzlei (20 Berater, 500 Mandanten).
  Buchbare Module erlauben passende Einstiegspunkte.
- **Incrementeller Umsatz**: Jede gebuchte Zusatzfunktion ist direkter Umsatz —
  kein All-or-Nothing-Pricing.
- **ADR-072-Muster verfügbar**: PostgreSQL-Schema-Isolation für SaaS ist bereits
  als Plattformstandard etabliert (django-tenants).
- **ADR-007-Muster verfügbar**: `core_tenant_feature` und `core_plan_quota` Tabellen
  bieten die Feature-Flag-Infrastruktur die ein Modulsystem braucht.

---

## 1. Context and Problem Statement

### 1.1 Warum ADR-152 ersetzt wird

ADR-152 beschreibt tax-hub als Pilotprojekt für **ein** Steuerberatungsbüro —
Single-Tenant-Fokus, keine Buchungslogik, keine Modul-Grenzen. Das Ziel hat
sich erweitert: tax-hub soll ein vollständiges SaaS-Produkt werden.

Die Kernfragen, die ADR-152 nicht beantwortet:
1. Wie werden mehrere Kanzleien isoliert? (→ Schema-Isolation via ADR-072)
2. Wie werden Module aktiviert/deaktiviert? (→ Feature-Flag-Tabelle via ADR-007)
3. Wie wird abgerechnet? (→ Stripe + `billing`-App)
4. Was ist im Basis-Paket, was kostet extra?

### 1.2 Zielgruppe und Marktsegmente

| Segment | Berater | Mandanten | Erwartete Module |
|---------|---------|-----------|------------------|
| **Mikrokanzlei** | 1–3 | bis 100 | Core + Fristen |
| **Kleinste Kanzlei** | 4–10 | 100–300 | Core + Fristen + DMS |
| **Mittlere Kanzlei** | 11–25 | 300–1.000 | Core + alle Module |
| **Große Kanzlei** | 25+ | 1.000+ | Enterprise (individuell) |

### 1.3 Architektur-Überblick

```
                    ┌─────────────────────────┐
                    │   tax.iil.pet            │
                    │   (Public Landing/Login) │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
   ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
   │ kanzlei-a.tax    │ │ kanzlei-b.tax    │ │ kanzlei-c.tax    │
   │ .iil.pet         │ │ .iil.pet         │ │ .iil.pet         │
   │ Schema: tenant_a │ │ Schema: tenant_b │ │ Schema: tenant_c │
   │ Module: Core,    │ │ Module: Core,    │ │ Module: Core,    │
   │         Fristen, │ │         DMS,KI   │ │         alle     │
   │         DMS      │ │                  │ │                  │
   └──────────────────┘ └──────────────────┘ └──────────────────┘
              │                  │                  │
              └──────────────────┴──────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   PostgreSQL             │
                    │   public schema:         │
                    │   Tenant, Plan, Feature  │
                    │   tenant_a schema: ...   │
                    │   tenant_b schema: ...   │
                    └──────────────────────────┘
```

---

## 2. Considered Options

### Option A — Module als Django-Apps mit Feature-Gate (gewählt) ✅

Jedes Modul ist eine eigenständige Django-App. Ein zentraler `ModuleGuard`
prüft beim Request ob das Modul für den Tenant aktiv ist.

### Option B — Separate Microservices pro Modul

Jedes Modul als eigener Docker-Container mit eigenem DB-Schema.

**Abgelehnt**: Für ein SaaS mit 1 Entwickler ist eine Microservice-Architektur
Overengineering. 8 Container pro Kanzlei × 50 Kanzleien = 400 Container.
Nicht betreibbar auf Hetzner VPS.

### Option C — Alle Module immer aktiv, Billing per Nutzung

Einheitlicher Funktionsumfang, Abrechnung nach tatsächlichem Verbrauch.

**Abgelehnt**: Steuerberatungsbüros buchen lieber feste Monatspauschalen als
usage-based Billing. Unvorhersehbare Kosten sind ein Kaufhindernis im KMU-Markt.

---

## 3. Decision Outcome

**Gewählt: Option A** — Module als Django-Apps mit Feature-Gate + Schema-Isolation.

---

## 4. Modul-Katalog

### 4.1 Modulübersicht

| Code | Modul | Inhalt | Preis-Tier |
|------|-------|--------|------------|
| `CORE` | **Kern** | Mandantenverwaltung, Bescheide-Grundfunktionen, Dashboard, Benutzer | **immer inklusive** |
| `FRISTEN` | **Fristenmanagement** | Einspruchsfristen, Abgabetermine, Celery-Beat-Reminder, Fristenkalender | Starter |
| `DMS` | **DMS-Integration** | d.velop-Anbindung, Dokumenten-Archivierung, Scan-Eingang | Business |
| `KI` | **KI-Assistent** | d.velop pilot Chat, Bescheid-Zusammenfassung, Jahresabschluss-Vergleich | Business |
| `BELEGE` | **Belegverwaltung** | EÜR-Belege, Bewirtungsbelege, Fahrtkosten, OCR-Import | Business |
| `ERECHNUNG` | **E-Rechnung** | ZUGFeRD/XRechnung empfangen & senden (§ 14 UStG ab 2025) | Business |
| `PORTAL` | **Mandantenportal** | Self-Service: Mandant lädt Belege hoch, Nachrichten, Freigaben | Enterprise |
| `API` | **REST-API** | Externe Anbindung (DATEV-Export, ERP-Schnittstelle) | Enterprise |
| `WORKFLOW` | **Workflow-Engine** | Automatisierte Prozesse: Freigaben, E-Mail, Konnektoren, DSB-Workflows | Enterprise |

### 4.2 Pläne

```python
# apps/billing/plans.py
PLANS = {
    "trial": {
        "label": "30-Tage-Test",
        "price_monthly": 0,
        "modules": ["CORE", "FRISTEN"],
        "mandanten_limit": 10,
        "berater_limit": 2,
        "trial_days": 30,
    },
    "starter": {
        "label": "Starter",
        "price_monthly": 49,      # € / Monat
        "modules": ["CORE", "FRISTEN"],
        "mandanten_limit": 100,
        "berater_limit": 5,
    },
    "business": {
        "label": "Business",
        "price_monthly": 149,
        "modules": ["CORE", "FRISTEN", "DMS", "KI", "BELEGE", "ERECHNUNG"],
        "mandanten_limit": 500,
        "berater_limit": 20,
    },
    "enterprise": {
        "label": "Enterprise",
        "price_monthly": None,    # individuell
        "modules": ["CORE", "FRISTEN", "DMS", "KI", "BELEGE",
                    "ERECHNUNG", "PORTAL", "API", "WORKFLOW"],
        "mandanten_limit": None,  # unbegrenzt
        "berater_limit": None,
    },
}
```

### 4.3 Modul-Abhängigkeiten

Module können voneinander abhängen. Ein Modul darf nur aktiviert werden,
wenn alle seine Abhängigkeiten ebenfalls aktiv sind.

```python
# apps/billing/plans.py
MODULE_DEPS: dict[str, list[str]] = {
    # Modul → benötigt diese Module
    "KI":       ["DMS"],        # KI-Assistent braucht DMS für Dokumentzugriff
    "PORTAL":   ["FRISTEN"],    # Mandantenportal zeigt Fristenkalender
    "WORKFLOW": ["API"],        # Workflow-Engine nutzt API-Gateway für Webhooks
    "BELEGE":   [],             # standalone
    "ERECHNUNG": [],            # standalone
    "API":      [],             # standalone
}


def resolve_dependencies(module_codes: set[str]) -> set[str]:
    """Erweitert Module um ihre transitiven Abhängigkeiten."""
    resolved = set(module_codes)
    changed = True
    while changed:
        changed = False
        for code in list(resolved):
            for dep in MODULE_DEPS.get(code, []):
                if dep not in resolved:
                    resolved.add(dep)
                    changed = True
    return resolved
```

**Validierung in `activate_plan()`**: Vor der Modul-Synchronisierung wird
`resolve_dependencies()` aufgerufen — fehlende Dependencies werden automatisch
mitaktiviert. Bei Downgrade werden Module nur deaktiviert, wenn kein anderes
aktives Modul sie als Dependency referenziert.

### 4.4 Downgrade-Strategie

Wenn ein Tenant von einem höheren Plan (z.B. Business) auf einen niedrigeren
(z.B. Starter) wechselt:

| Aspekt | Verhalten |
|--------|-----------|
| **Modul-Daten** | Bleiben in der DB erhalten (Soft-Deactivation) |
| **UI-Zugang** | Wird via `ModuleGuard` gesperrt — 403 mit Upgrade-Hinweis |
| **API-Zugang** | `@require_module()` blockiert Requests |
| **Laufende Workflows** | Werden abgeschlossen, neue blockiert |
| **Celery-Tasks** | Tasks für deaktivierte Module werden übersprungen |
| **Re-Upgrade** | Alle Daten sofort wieder verfügbar (kein Datenverlust) |
| **Daten-Retention** | 90 Tage nach Deaktivierung, dann Archivierung (konfigurierbar) |

```python
# apps/billing/services.py — Ergänzung in activate_plan()
# Vor der Modul-Deaktivierung:
for code in to_deactivate:
    # Laufende Workflows für dieses Modul beenden
    WorkflowExecution.objects.filter(
        template__category=MODULE_TO_CATEGORY.get(code, ""),
        status="running",
    ).update(status="cancelled", finished_at=timezone.now())
```

---

## 5. Technische Architektur

### 5.1 Repository-Struktur

```
tax-hub/
├── apps/
│   ├── tenant/             # Organization, Membership, SubdomainMiddleware
│   ├── billing/            # Plan, Subscription, Stripe-Webhook
│   ├── modules/            # ModuleRegistry, ModuleGuard, Decorator
│   │
│   │   # === Kern (immer aktiv) ===
│   ├── core/               # Dashboard, Healthz
│   ├── mandanten/          # Mandant, MandantenAkte
│   ├── bescheide/          # Bescheid, BescheidArt
│   │
│   │   # === Buchbare Module ===
│   ├── fristen/            # Frist, FristArt, Celery-Beat-Tasks
│   ├── dms/                # DvelopClient, DmsArchivService, PilotService
│   ├── ki_assistent/       # BescheidSummaryService, JahresabschlussChat
│   ├── belege/             # Beleg, BelegKategorie, OCR-Import
│   ├── erechnung/          # EInvoice, ZUGFeRD-Parser, XRechnung-Generator
│   ├── mandantenportal/    # PortalUser, UploadRequest, Freigabe
│   ├── api_gateway/        # DRF ViewSets, OpenAPI, API-Key-Auth
│   └── workflows/          # Workflow-Engine, Handler, Konnektoren
│
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
│
├── templates/tax_hub/
├── docker-compose.prod.yml
├── docker/app/Dockerfile
├── requirements.txt
└── catalog-info.yaml
```

### 5.2 Multi-Tenancy (ADR-072)

```python
# config/settings/base.py
SHARED_APPS = [
    "django_tenants",
    "apps.tenant",    # Organization (öffentliches Schema)
    "apps.billing",   # Plan, Subscription (öffentliches Schema)
    "django.contrib.contenttypes",
    "django.contrib.auth",
]

TENANT_APPS = [
    "apps.modules",
    "apps.core",
    "apps.mandanten",
    "apps.bescheide",
    "apps.fristen",
    "apps.dms",
    "apps.ki_assistent",
    "apps.belege",
    "apps.erechnung",
    "apps.mandantenportal",
    "apps.api_gateway",
    "apps.workflows",
]

TENANT_MODEL = "tenant.Organization"
TENANT_DOMAIN_MODEL = "tenant.Domain"
```

### 5.3 Module-Guard System

```python
# apps/modules/guard.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from apps.modules.registry import ModuleRegistry


def require_module(module_code: str):
    """
    Decorator für Views und Service-Methoden.
    Wirft PermissionDenied wenn das Modul für den Tenant nicht aktiv ist.

    Verwendung:
        @require_module("KI")
        def summarize_bescheid(request, bescheid_id): ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Request aus args[0] (View) oder kwargs (Service)
            request = args[0] if args and hasattr(args[0], 'tenant') else None
            tenant_id = getattr(request, 'tenant_id', None)

            if not ModuleRegistry.is_active(tenant_id, module_code):
                raise PermissionDenied(
                    f"Modul '{module_code}' ist für Ihre Kanzlei nicht gebucht. "
                    f"Upgrade unter /billing/upgrade/"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator

```

```python
# apps/modules/registry.py
class ModuleRegistry:
    """Prüft ob ein Modul für einen Tenant aktiv ist."""

    @staticmethod
    def is_active(tenant_id, module_code: str) -> bool:
        """
        Cached Check — Redis TTL 5 Min.
        Fällt auf DB zurück wenn Cache kalt ist.
        """
        from django.core.cache import cache
        cache_key = f"module:{tenant_id}:{module_code}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        from apps.billing.models import TenantModule
        active = TenantModule.objects.filter(
            tenant_id=tenant_id,
            module_code=module_code,
            is_active=True,
        ).exists()
        cache.set(cache_key, active, timeout=300)
        return active

    @staticmethod
    def active_modules(tenant_id) -> list[str]:
        """Alle aktiven Modul-Codes für einen Tenant."""
        from apps.billing.models import TenantModule
        return list(
            TenantModule.objects.filter(
                tenant_id=tenant_id, is_active=True
            ).values_list("module_code", flat=True)
        )

    @staticmethod
    def invalidate(tenant_id, module_code: str) -> None:
        """Cache invalidieren nach Plan-Änderung."""
        from django.core.cache import cache
        cache.delete(f"module:{tenant_id}:{module_code}")
```

### 5.4 Quota-Enforcement

Neben Modul-Gates werden auch **Limits** (Mandanten, Berater) durchgesetzt:

```python
# apps/modules/quota.py
from functools import wraps
from django.core.exceptions import PermissionDenied


def check_quota(resource: str):
    """
    Decorator für Create-Views: prüft ob Tenant sein Limit erreicht hat.

    Verwendung:
        @check_quota("mandanten")
        def create_mandant(request): ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            from apps.billing.models import Subscription
            sub = Subscription.objects.get(tenant_id=request.tenant.id)
            current = _count_resource(request.tenant.id, resource)
            limit = getattr(sub, f"{resource}_limit", 0)

            if limit and current >= limit:
                raise PermissionDenied(
                    f"Limit erreicht: {current}/{limit} {resource}. "
                    f"Upgrade unter /billing/upgrade/"
                )
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def _count_resource(tenant_id, resource: str) -> int:
    """Zählt aktive Ressourcen für einen Tenant."""
    if resource == "mandanten":
        from apps.mandanten.models import Mandant
        return Mandant.objects.filter(is_active=True).count()
    elif resource == "berater":
        from django.contrib.auth import get_user_model
        return get_user_model().objects.filter(is_active=True).count()
    return 0
```

**Hinweis**: Die Zählung läuft automatisch im richtigen Tenant-Schema
(`django-tenants` setzt das Schema via Middleware), daher kein expliziter
`tenant_id`-Filter in den Queries nötig.

### 5.5 Billing-Modelle

```python
# apps/billing/models.py
from django.db import models


class Subscription(models.Model):
    """SaaS-Subscription eines Steuerberatungsbüros."""
    # PK: BigAutoField (DEFAULT_AUTO_FIELD — Platform-Standard)

    class Status(models.TextChoices):
        TRIAL    = "trial",    "Testphase"
        ACTIVE   = "active",   "Aktiv"
        PAST_DUE = "past_due", "Zahlung überfällig"
        CANCELED = "canceled", "Gekündigt"

    # tenant_id kommt vom öffentlichen Schema — FK als Integer
    tenant_id          = models.PositiveBigIntegerField(unique=True, db_index=True)
    plan_code          = models.CharField(max_length=20)
    status             = models.CharField(max_length=10, choices=Status.choices,
                           default=Status.TRIAL)
    trial_ends_at      = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=50, blank=True, db_index=True)
    stripe_sub_id      = models.CharField(max_length=50, blank=True, db_index=True)
    mandanten_limit    = models.PositiveIntegerField(default=10)
    berater_limit      = models.PositiveIntegerField(default=2)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_subscription"


class TenantModule(models.Model):
    """Welche Module sind für einen Tenant aktiv."""

    # PK: BigAutoField (DEFAULT_AUTO_FIELD)
    tenant_id   = models.PositiveBigIntegerField(db_index=True)
    module_code = models.CharField(max_length=20)  # "FRISTEN", "DMS", "KI", ...
    is_active   = models.BooleanField(default=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "billing_tenant_module"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "module_code"],
                condition=models.Q(is_active=True),
                name="uq_billing_active_module_per_tenant",
            )
        ]


class AddOn(models.Model):
    """Optional einzeln buchbare Zusatzmodule (über Plan hinaus)."""

    # PK: BigAutoField (DEFAULT_AUTO_FIELD)
    tenant_id   = models.PositiveBigIntegerField(db_index=True)
    module_code = models.CharField(max_length=20)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2)
    stripe_price_id = models.CharField(max_length=50, blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_addon"
```

### 5.5 Billing-Service: Plan-Aktivierung

```python
# apps/billing/services.py
from __future__ import annotations
import logging
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class SubscriptionService:

    @staticmethod
    @transaction.atomic
    def activate_plan(tenant_id, plan_code: str) -> "Subscription":
        """
        Aktiviert Plan + alle inkludierten Module.
        Deaktiviert Module die nicht mehr im Plan enthalten sind.
        """
        from .plans import PLANS
        from .models import Subscription, TenantModule
        from apps.modules.guard import ModuleRegistry

        plan = PLANS.get(plan_code)
        if not plan:
            raise ValueError(f"Unbekannter Plan: {plan_code}")

        # Subscription aktualisieren
        sub, _ = Subscription.objects.update_or_create(
            tenant_id=tenant_id,
            defaults={
                "plan_code":       plan_code,
                "status":          Subscription.Status.ACTIVE,
                "mandanten_limit": plan["mandanten_limit"] or 9999,
                "berater_limit":   plan["berater_limit"] or 9999,
            },
        )

        # Module synchronisieren
        new_modules = set(plan["modules"])
        existing = set(TenantModule.objects.filter(
            tenant_id=tenant_id, is_active=True
        ).values_list("module_code", flat=True))

        # Neue Module aktivieren
        for code in new_modules - existing:
            TenantModule.objects.update_or_create(
                tenant_id=tenant_id,
                module_code=code,
                defaults={"is_active": True, "deactivated_at": None},
            )
            ModuleRegistry.invalidate(tenant_id, code)
            logger.info("billing.module_activated tenant=%s module=%s", tenant_id, code)

        # Entfernte Module deaktivieren (außer CORE — immer aktiv)
        for code in existing - new_modules - {"CORE"}:
            TenantModule.objects.filter(
                tenant_id=tenant_id, module_code=code
            ).update(is_active=False, deactivated_at=timezone.now())
            ModuleRegistry.invalidate(tenant_id, code)
            logger.info("billing.module_deactivated tenant=%s module=%s", tenant_id, code)

        return sub

    @staticmethod
    def provision_trial(tenant_id, kanzlei_name: str) -> "Subscription":
        """30-Tage-Trial mit Core + Fristen."""
        from datetime import timedelta
        sub = SubscriptionService.activate_plan(tenant_id, "trial")
        sub.trial_ends_at = timezone.now() + timedelta(days=30)
        sub.status = "trial"
        sub.save(update_fields=["trial_ends_at", "status", "updated_at"])
        logger.info("billing.trial_started tenant=%s kanzlei=%s", tenant_id, kanzlei_name)
        return sub

    @staticmethod
    def mark_past_due(stripe_customer_id: str) -> None:
        """Markiert Subscription als überfällig nach fehlgeschlagener Zahlung."""
        from .models import Subscription
        updated = Subscription.objects.filter(
            stripe_customer_id=stripe_customer_id
        ).update(status=Subscription.Status.PAST_DUE, updated_at=timezone.now())
        if updated:
            logger.warning("billing.payment_failed customer=%s", stripe_customer_id)

    @staticmethod
    def cancel_by_stripe_id(stripe_sub_id: str) -> None:
        """Kündigt Subscription nach Stripe-Webhook."""
        from .models import Subscription
        updated = Subscription.objects.filter(
            stripe_sub_id=stripe_sub_id
        ).update(status=Subscription.Status.CANCELED, updated_at=timezone.now())
        if updated:
            logger.info("billing.subscription_canceled stripe_sub=%s", stripe_sub_id)
```

### 5.6 HTMX Modul-Guard in Templates

```html
<!-- templates/tax_hub/base.html — Navigation nur mit aktivem Modul -->
{% load module_tags %}

<nav>
  <a href="/mandanten/">Mandanten</a>          {# CORE — immer #}
  <a href="/bescheide/">Bescheide</a>          {# CORE — immer #}

  {% if_module "FRISTEN" %}
  <a href="/fristen/">Fristenkalender</a>
  {% endif_module %}

  {% if_module "DMS" %}
  <a href="/dms/">Dokumentenarchiv</a>
  {% endif_module %}

  {% if_module "KI" %}
  <a href="/ki/">KI-Assistent</a>
  {% endif_module %}

  {% if_module "BELEGE" %}
  <a href="/belege/">Belegverwaltung</a>
  {% endif_module %}

  {% if_module "ERECHNUNG" %}
  <a href="/erechnung/">E-Rechnungen</a>
  {% endif_module %}

  {% if_module "PORTAL" %}
  <a href="/portal/">Mandantenportal</a>
  {% endif_module %}
</nav>
```

```python
# apps/modules/templatetags/module_tags.py
from django import template
from apps.modules.guard import ModuleRegistry

register = template.Library()

class IfModuleNode(template.Node):
    def __init__(self, module_code, nodelist_true, nodelist_false):
        self.module_code = module_code
        self.nodelist_true = nodelist_true
        self.nodelist_false = nodelist_false

    def render(self, context):
        request = context.get("request")
        tenant_id = getattr(request, "tenant_id", None)
        if tenant_id and ModuleRegistry.is_active(tenant_id, self.module_code):
            return self.nodelist_true.render(context)
        return self.nodelist_false.render(context)

@register.tag
def if_module(parser, token):
    _, module_code = token.split_contents()
    module_code = module_code.strip('"\'')
    nodelist_true = parser.parse(("else_module", "endif_module"))
    token = parser.next_token()
    if token.contents == "else_module":
        nodelist_false = parser.parse(("endif_module",))
        parser.delete_first_token()
    else:
        nodelist_false = template.NodeList()
    return IfModuleNode(module_code, nodelist_true, nodelist_false)
```

### 5.7 Stripe-Webhook Handler

```python
# apps/billing/views.py
import json, stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def stripe_webhook(request):
    """Verarbeitet Stripe-Events: checkout, payment, cancel."""
    payload = request.body
    sig    = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.STRIPE_WEBHOOK_SECRET
        )
    except (stripe.error.SignatureVerificationError, ValueError):
        return HttpResponse(status=400)

    handlers = {
        "checkout.session.completed":      _handle_checkout,
        "invoice.payment_succeeded":       _handle_payment_ok,
        "invoice.payment_failed":          _handle_payment_failed,
        "customer.subscription.deleted":   _handle_canceled,
    }
    # NOTE: _handle_payment_ok intentionally no-op — Subscription already active after checkout
    handler = handlers.get(event["type"])
    if handler:
        handler(event["data"]["object"])
    return HttpResponse(status=200)


def _handle_payment_ok(invoice):
    """No-op: Subscription ist bereits nach checkout aktiv."""
    pass


def _handle_checkout(session):
    tenant_id  = session["metadata"]["tenant_id"]
    plan_code  = session["metadata"]["plan_code"]
    SubscriptionService.activate_plan(tenant_id, plan_code)


def _handle_payment_failed(invoice):
    SubscriptionService.mark_past_due(invoice["customer"])


def _handle_canceled(subscription):
    SubscriptionService.cancel_by_stripe_id(subscription["id"])
```

---

## 6. Modul-Beschreibungen (Implementierungs-Scope)

### MOD-01: CORE (immer aktiv)

```
apps/mandanten/   Mandant, MandantenAkte, Steuernummer, Finanzamt
apps/bescheide/   Bescheid (BescheidArt: EST/KST/GewSt/UST/Vorz)
apps/core/        Dashboard, Kanzlei-Einstellungen, Benutzer
```

### MOD-02: FRISTEN

```
apps/fristen/
  models.py    Frist (FristArt: Einspruch/VoranmeldungUST/Jahreserklärung/Aufbewahrung)
  tasks.py     frist_reminder_check — täglich Celery Beat, 14/7/1 Tag Vorlauf
  services.py  FristenExtractor.from_bescheid() — AO §355: bescheid_datum + 30 Tage
  views.py     Fristenkalender (Monats-/Wochenansicht per HTMX)
```

### MOD-03: DMS

```
apps/dms/
  client.py    DvelopClient (4 Methoden — analog ADR-146)
  services.py  DmsArchivService.archive_bescheid(), DmsPilotService.chat()
  tasks.py     archive_tax_document (Celery Queue "dms")
  categories.py BESCHEID_EST, BESCHEID_UST, VOLLMACHT, JAHRESABSCHLUSS, ...
```

### MOD-04: KI (hängt von DMS ab)

```
apps/ki_assistent/
  services.py  BescheidSummaryService — d.velop pilot summarize
               JahresabschlussService — Multi-Doc-Chat
               FristExtractionService — KI extrahiert Fristen aus Bescheid-Text
  views.py     Chat-Widget (HTMX SSE für Streaming-Antworten)
```

### MOD-05: BELEGE

```
apps/belege/
  models.py    Beleg (BelegKategorie: Bewirtung/Fahrt/Lohn/Sonstig)
               BelegUpload, OCRResult
  services.py  BelegClassifier — aifw MEDIUM (analog ADR-148)
               EURBerechnung — Monatssummen per Kategorie
  tasks.py     ocr_classify_beleg (Celery Queue "ai")
```

### MOD-06: ERECHNUNG

```
apps/erechnung/
  models.py    EInvoice (Format: ZUGFERD_2_1, XRECHNUNG_3_0)
  services.py  ZUGFeRDParser  — liest eingehende ZUGFeRD-PDFs
               XRechnungGenerator — erstellt ausgehende XRechnungen
               Pflicht ab 2025: § 14 Abs. 1 UStG n.F.
```

### MOD-07: PORTAL (Enterprise)

```
apps/mandantenportal/
  models.py    PortalUser, PortalInvite, BelegUploadRequest, Freigabe
  services.py  PortalInviteService — E-Mail mit Token-Link
               UploadService — Mandant lädt Belege hoch → direkt in DMS
  views.py     Separater Login (/portal/) mit eingeschränkter Ansicht
```

### MOD-08: API (Enterprise)

```
apps/api_gateway/
  serializers.py  Mandant, Bescheid, Frist, Beleg (DRF)
  viewsets.py     Read-only + Write nach Plan
  authentication.py  API-Key-Auth (kein JWT für externe Systeme)
  Verwendung:  DATEV-Export, ERP-Schnittstelle, Eigenentwicklung
```

### MOD-09: WORKFLOW (Enterprise)

```
apps/workflows/
  models.py       WorkflowTemplate, Phase, Action, ExecutionLog, ConnectorConfig
  handlers/       BaseHandler + alle Konnektoren (E-Mail, Paperless, DATEV, ...)
  services.py     WorkflowExecutor (ACID-sicher), ConnectorRegistry
  views.py        Workflow-Dashboard, Template-Editor (HTMX)
  tasks.py        execute_workflow_async (Celery Queue "workflow")
```

---

## 7. Deployment-Parameter (ADR-021 konform)

### 7.1 Service-Inventar

| Parameter | Wert | ADR-021 Referenz |
|-----------|------|------------------|
| **Repository** | `achimdehnert/tax-hub` | — |
| **Image** | `ghcr.io/achimdehnert/tax-hub:latest` + SHA-Tag | §2.2 |
| **Host-Port** | **8099** | §2.9 — **MUSS dort eingetragen werden** (8096 belegt durch illustration-hub) |
| **Deploy-Pfad** | `/opt/tax-hub` | §2.2 (`/opt/<repo>`) |
| **Compose-File** | `docker-compose.prod.yml` (Projekt-Root) | §2.2 |
| **Dockerfile** | `docker/app/Dockerfile` | §2.2 |
| **Settings-Modul** | `config.settings.production` | §2.3 |

### 7.2 Container & Services (ADR-021 §2.2 Naming)

| Service | Container-Name | Image | Funktion |
|---------|---------------|-------|----------|
| `tax-hub-web` | `tax_hub_web` | `ghcr.io/achimdehnert/tax-hub` | Gunicorn :8000 |
| `tax-hub-worker` | `tax_hub_worker` | (gleich) | Celery Worker |
| `tax-hub-beat` | `tax_hub_beat` | (gleich) | Celery Beat (Fristen-Reminder) |
| `tax-hub-db` | `tax_hub_db` | `postgres:16-alpine` | PostgreSQL (Schema per Tenant) |
| `tax-hub-redis` | `tax_hub_redis` | `redis:7-alpine` | Cache (ModuleRegistry) + Celery Broker |

### 7.3 Netzwerk & DNS

| Parameter | Wert |
|-----------|------|
| **Domain (Prod)** | `*.tax.iil.pet` (Wildcard — eine Subdomain pro Kanzlei) |
| **Domain (Public)** | `tax.iil.pet` (Landing + Registrierung) |
| **Cloudflare DNS** | CNAME `*.tax` → Tunnel (proxied) + CNAME `tax` → Tunnel (proxied) |
| **Wildcard-SSL** | Cloudflare Universal SSL (automatisch bei Proxy-Modus) |
| **Nginx** | `server_name *.tax.iil.pet;` → `proxy_pass http://127.0.0.1:8099;` |

### 7.4 Health & Monitoring (ADR-021 §2.2, ADR-078)

| Endpoint | Zweck | Implementierung |
|----------|-------|-----------------|
| `/livez/` | Docker HEALTHCHECK (Liveness) | `@csrf_exempt @require_GET` → `{"status": "ok"}` |
| `/healthz/` | Deploy-Verifikation + Monitoring | DB-Check + Redis-Check + Tenant-Count |

```dockerfile
# docker/app/Dockerfile — HEALTHCHECK (ADR-021 §2.2)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')"
```

### 7.5 Compose-Hardening (ADR-021 §2.11)

| Maßnahme | Wert |
|----------|------|
| **Logging** | `json-file`, `max-size: "20m"`, `max-file: "5"` |
| **Memory-Limits** | Web: `512M`, Worker: `384M`, Beat: `256M` |
| **Restart-Policy** | `unless-stopped` |
| **PostgreSQL shm_size** | `128m` |
| **env_file** | `.env.prod` (nie im Git, nie `environment: ${VAR}`) |

### 7.6 Celery & Async

| Queue | Verwendung | Worker-Concurrency |
|-------|-----------|-------------------|
| `default` | Standard-Tasks, Trial-Expiry | 4 |
| `dms` | DvelopClient-Calls, Archivierung | 2 |
| `ai` | LLM-Calls via aifw, OCR | 2 |
| `workflow` | Workflow-Execution (Actions, Handler) | 2 |

### 7.7 CI/CD (ADR-021 §2.1)

```
_ci-python.yml@v1 → _build-docker.yml@v1 → _deploy-hetzner.yml@v1
```

Trigger: Push auf `main` → Auto-Deploy auf Prod-Server (`88.198.191.108`).

### 7.8 Sonstiges

| Parameter | Wert |
|-----------|------|
| **Stripe-Webhook** | `/billing/stripe/webhook/` (öffentlich via Cloudflare Tunnel) |
| **Backup** | Per-Tenant: `pg_dump --schema=tenant_<id>` (ADR-072 §4) |
| **Backup Full** | Nightly `pg_dumpall` → `/opt/tax-hub/backups/` |

---

## 8. Rollout-Phasen

### Phase 1 — Pilot (4 Wochen)

Basis für das Steuerberatungsbüro-Pilotprojekt aus ADR-152.

```
✅ CORE (Mandanten, Bescheide, Dashboard)
✅ FRISTEN (Fristenkalender, Celery-Reminder)
✅ DMS (d.velop-Anbindung, Archivierung)
✅ KI (d.velop pilot Chat, Zusammenfassung)
□  Billing (noch nicht — Pilot ist kostenlos)
□  Multi-Tenancy (Single-Tenant reicht für Pilot)
```

### Phase 2 — SaaS-Unterbau (4 Wochen)

```
✅ Schema-Isolation (django-tenants, ADR-072)
✅ Subdomain-Routing (kanzlei-x.tax.iil.pet)
✅ Billing-App + Stripe-Integration
✅ ModuleRegistry + ModuleGuard
✅ Trial-Provisionierung (30 Tage, Core + Fristen)
□  BELEGE, ERECHNUNG, PORTAL, API
```

### Phase 3 — Vollständiger Modul-Katalog (6 Wochen)

```
✅ BELEGE (OCR-Klassifikation via aifw, ADR-148)
✅ ERECHNUNG (ZUGFeRD/XRechnung)
✅ PORTAL (Mandanten-Self-Service)
✅ API-Gateway (DATEV-Export)
✅ Upgrade/Downgrade im Billing-Dashboard
```

### Phase 4 — Go-to-Market (2 Wochen)

```
✅ Öffentliche Landing-Page tax.iil.pet
✅ Self-Service-Registrierung + Trial-Start
✅ Stripe-Checkout für Plan-Upgrade
✅ Onboarding-Tour (HTMX-Stepper)
```

---

## 9. Migration Tracking

| Phase | Schritt | Status | Datum |
|-------|---------|--------|-------|
| 1 | ADR-153 erstellt | ✅ Done | 2026-03-25 |
| 1 | ADR-152 als superseded markieren | ⬜ Pending | – |
| 1 | Port 8099 in ADR-021 §2.9 Port-Registry eintragen | ⬜ Pending | – |
| 1 | Health-Endpoints `/livez/` + `/healthz/` implementieren | ⬜ Pending | – |
| 1 | Django-Skeleton + Split Settings | ⬜ Pending | – |
| 1 | apps/tenant/ + apps/billing/ Grundgerüst | ⬜ Pending | – |
| 1 | apps/mandanten/ + apps/bescheide/ + apps/core/ | ⬜ Pending | – |
| 1 | apps/fristen/ + Celery Beat | ⬜ Pending | – |
| 1 | apps/dms/ (DvelopClient + DmsPilotService) | ⬜ Pending | – |
| 1 | apps/ki_assistent/ | ⬜ Pending | – |
| 1 | Pilot-Demo UC-1 lauffähig | ⬜ Pending | – |
| 2 | django-tenants + Schema-Migration | ⬜ Pending | – |
| 2 | ModuleRegistry + ModuleGuard | ⬜ Pending | – |
| 2 | Stripe-Integration + Webhook | ⬜ Pending | – |
| 2 | Trial-Provisionierung | ⬜ Pending | – |
| 3 | BELEGE + ERECHNUNG Module | ⬜ Pending | – |
| 3 | PORTAL + API Module | ⬜ Pending | – |
| 3 | apps/workflows/ Grundgerüst + BaseHandler | ⬜ Pending | – |
| 3 | E-Mail + Paperless + DATEV Konnektoren | ⬜ Pending | – |
| 3 | Rechnungsfreigabe-Workflow (Pilot) | ⬜ Pending | – |
| 4 | Landing Page + Self-Service-Registration | ⬜ Pending | – |
| 4 | n8n Bridge-Handler | ⬜ Pending | – |

---

## 10. Consequences

### 10.1 Good

- Klar buchbare Module → direkter Umsatz pro Feature
- Trial-to-Paid-Funnel vollständig automatisiert (Stripe + ModuleGuard)
- ADR-072 Schema-Isolation: DSGVO-konforme Datentrennung pro Kanzlei
- ModuleGuard als Decorator: Module-Check in 1 Zeile, überall anwendbar
- Phase 1 (Pilot) bleibt einfach — Multi-Tenancy und Billing kommen in Phase 2

### 10.2 Bad

- `django-tenants` erfordert alle Migrations-Komplexitäten aus ADR-072
- Wildcard-SSL für `*.tax.iil.pet` — Cloudflare kann das, aber DNS-Setup nötig
- Stripe-Webhook über Cloudflare Tunnel: WAF-Regel für Stripe-IPs nötig (Bot-Protection kann Webhooks blockieren)
- 9 Module × Tests = signifikanter Test-Aufwand

### 10.3 Nicht in Scope

- iOS/Android-App für Mandantenportal (Phase 5+)
- DATEV-Direktschnittstelle (proprietäres Protokoll, separate ADR)
- Automatische Steuerberechnung (das macht DATEV, nicht tax-hub)

---

## 11. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|------------|
| d.velop pilot Chat-API ändert sich | Mittel | Hoch | Endpunkte via Postman testen; `DmsPilotService` isoliert |
| Stripe-Preismodell zu komplex für KMU | Mittel | Mittel | Einfache Monatspauschalen, kein usage-based |
| `django-tenants` Migration bei >50 Kanzleien langsam | Niedrig | Mittel | ADR-072 Parallelisierungs-Strategie anwenden |
| ERECHNUNG-Pflicht unklar (gesetzliche Übergangsfrist) | Mittel | Niedrig | Modul als "ab 2025 relevant" kennzeichnen |
| Handler-Ausführung: beliebiger Python-Pfad in `handler_class` | Niedrig | Hoch | Allowlist in `HandlerRegistry` — nur registrierte Handler ausführbar |
| n8n-Ausfall blockiert Workflows mit `TriggerN8nHandler` | Mittel | Mittel | `continue_on_error=True` + Fallback-E-Mail-Notification |
| Workflow-Execution bei Tenant-Downgrade läuft weiter | Niedrig | Niedrig | Laufende Executions beenden, neue blockieren via `ModuleGuard` |

---

## 12. Confirmation

1. `ModuleRegistry.is_active(tenant_id, "KI")` gibt `False` für Starter-Plan
2. `@require_module("KI")` wirft `PermissionDenied` wenn Modul inaktiv
3. `SubscriptionService.activate_plan(tenant_id, "business")` aktiviert alle Business-Module
4. Schema-Isolation: Kanzlei A kann keine Mandanten von Kanzlei B sehen
5. Stripe-Webhook: `checkout.session.completed` → Module aktiviert
6. Trial: 30 Tage → automatisch `status="trial"`, dann Downgrade-Warning
7. Port 8099 in ADR-021 §2.9 eintragen (**noch offen** — Migration Tracking Phase 1)
8. `catalog-info.yaml` vorhanden, `lifecycle: production` nach Phase 4
9. `HandlerRegistry.get_handler_class("apps.workflows.handlers.email.SendEmailHandler")` liefert registrierten Handler
10. `ExecutionLog.objects.filter(execution_id=X)` zeigt vollständiges Audit-Log mit Input/Output pro Action
11. `WorkflowExecution` mit Status `waiting` pausiert bis Callback (`WaitForApprovalHandler`)

---

## 13. Workflow-Engine & Konnektoren-Architektur

### 13.0 Considered Options (Workflow-Ansatz)

| Option | Beschreibung | Bewertung |
|--------|-------------|-----------|
| **A — GenAgent-basierte Handler-Pipeline (gewählt) ✅** | Eigene Python-Handler mit `BaseHandler`-ABC, DB-backed Templates, ACID-Executor aus bfagent | Volle Kontrolle, kein externer Dienst nötig, wiederverwendbar als `iil-workflowfw` |
| **B — Temporal.io (ADR-079)** | Durable Workflow Engine mit Replay, Saga-Pattern | Overkill für tax-hub: eigener Temporal-Server, Go/Java SDKs, hohe Ops-Komplexität |
| **C — n8n als primäre Engine** | Alle Workflows in n8n modellieren, Django nur als API-Backend | Vendor-Lock-in, keine DSGVO-Audit-Logs in eigener DB, schwer testbar |
| **D — Celery-Tasks ohne Abstraktion** | Jeder Workflow als verkettete Celery-Tasks | Kein Template-System, kein UI, kein Audit-Trail, schwer wartbar ab 5+ Workflows |

**Begründung Option A**: GenAgent ist bereits produktiv in bfagent, bietet
Handler-Registry + Executor + Pydantic-Validierung + ExecutionLog. Die
Übernahme in tax-hub erfordert nur Model-Anpassungen (→ `WorkflowTemplate`),
keine neuen Infrastruktur-Abhängigkeiten. n8n ergänzt als optionale Bridge
für 400+ externe Konnektoren (§13.8).

### 13.1 Herkunft und Grundlage

Die Workflow-Engine basiert auf dem **GenAgent-Framework** aus `bfagent/apps/genagent/`,
das als generische, Hub-unabhängige Handler-Pipeline konzipiert wurde.
Die Kernkomponenten werden als wiederverwendbare Basis übernommen:

| GenAgent-Komponente | tax-hub Übernahme | Zweck |
|---------------------|-------------------|-------|
| `BaseHandler` (ABC) | 1:1 | Abstrakte Basis für alle Konnektoren |
| `Phase` / `Action` Models | adaptiert → `WorkflowTemplate` | DB-backed Workflow-Definition |
| `ExecutionLog` | 1:1 | Vollständiges Audit-Log (DSGVO Art. 30) |
| `ActionExecutor` (ACID) | 1:1 | Transaktionssichere Ausführung mit Rollback |
| `HandlerRegistry` | 1:1 | Dynamische Konnektor-Registrierung |
| `ContextManager` | 1:1 | Isolierte Ausführungskontexte |
| Pydantic Schemas | 1:1 | Input/Output-Validierung pro Handler |

### 13.2 Architektur-Überblick

```
┌─────────────────────────────────────────────────────────┐
│                  Workflow-Engine                         │
│                                                         │
│  WorkflowTemplate ──→ Phase 1 ──→ Phase 2 ──→ Phase N  │
│                        │            │            │      │
│                      Action 1    Action 1    Action 1   │
│                      Action 2    Action 2      ...      │
│                        │            │                   │
│                    ┌───┴───┐    ┌───┴───┐               │
│                    │Handler│    │Handler│               │
│                    └───┬───┘    └───┬───┘               │
└────────────────────────┼────────────┼───────────────────┘
                         │            │
            ┌────────────┼────────────┼────────────┐
            ▼            ▼            ▼            ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  E-Mail  │ │Paperless │ │  DATEV   │ │   LLM    │
     │  (SMTP)  │ │  (REST)  │ │ (Export) │ │  (aifw)  │
     └──────────┘ └──────────┘ └──────────┘ └──────────┘
     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  d.velop │ │  Stripe  │ │ Webhook  │ │   n8n    │
     │  (DMS)   │ │ (Billing)│ │ (Custom) │ │ (Bridge) │
     └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 13.3 Handler-Kontrakt

Jeder Konnektor implementiert `BaseHandler` — dieselbe Schnittstelle wie in GenAgent:

```python
# apps/workflows/handlers/__init__.py
from abc import ABC, abstractmethod
from typing import Any

class BaseHandler(ABC):
    """Basis für alle Workflow-Konnektoren."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
    def execute(self, context: dict[str, Any], test_mode: bool = False) -> dict[str, Any]:
        """Ausführen — muss {success: bool, output: Any} zurückgeben."""
        ...

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """JSON-Schema für Handler-Konfiguration (UI-Validierung)."""
        return {"type": "object", "properties": {}}
```

### 13.4 Konnektor-Katalog

| Konnektor | Handler-Klasse | Extern | Aufwand | Prio |
|-----------|---------------|--------|---------|------|
| **E-Mail (SMTP)** | `SendEmailHandler` | `django.core.mail` | 1h | P1 |
| **E-Mail (IMAP)** | `FetchEmailHandler` | `imaplib` | 2h | P2 |
| **Paperless API** | `PaperlessDocHandler` | REST → docs.iil.pet | 1h | P1 |
| **d.velop DMS** | `DvelopArchiveHandler` | REST → ADR-146 Client | 1h | P1 |
| **PDF-Erzeugung** | `GeneratePDFHandler` | `weasyprint` | 2h | P2 |
| **DATEV-Export** | `DATEVExportHandler` | CSV/ASCII Datei | 4h | P2 |
| **LLM/KI** | `LLMAnalyzeHandler` | `aifw.service.sync_completion` | vorhanden | P1 |
| **Webhook** | `WebhookHandler` | `requests.post()` | 30min | P1 |
| **Stripe** | `StripeActionHandler` | Stripe API | 2h | P3 |
| **Slack/Teams** | `ChatNotifyHandler` | Webhook | 30min | P3 |
| **ELSTER** | `ElsterSubmitHandler` | ERiC-API | komplex | P4 |
| **eSign** | `ESignHandler` | DocuSign/Adobe Sign | 4h | P4 |
| **n8n Bridge** | `TriggerN8nHandler` | Webhook → n8n | 1h | P2 |
| **Freigabe (HitL)** | `WaitForApprovalHandler` | Interner Callback | 2h | P1 |

### 13.5 Human-in-the-Loop (Freigabe-Pattern)

Viele Workflows erfordern menschliche Entscheidungen (z.B. Rechnungsfreigabe).
Der `WaitForApprovalHandler` pausiert die Execution und wartet auf einen Callback:

```python
# apps/workflows/handlers/approval.py
from apps.workflows.handlers import BaseHandler


class WaitForApprovalHandler(BaseHandler):
    """Pausiert Workflow bis ein Mensch freigibt oder ablehnt."""

    def execute(self, context: dict, test_mode: bool = False) -> dict:
        if test_mode:
            return {"success": True, "output": "auto-approved (test)"}

        # Execution in Wartestatus setzen
        execution_id = context["execution_id"]
        from apps.workflows.models import WorkflowExecution
        WorkflowExecution.objects.filter(id=execution_id).update(status="waiting")

        # E-Mail an Freigeber senden
        from apps.workflows.services import WorkflowNotificationService
        WorkflowNotificationService.send_approval_request(
            execution_id=execution_id,
            approver_email=self.config.get("approver_email"),
            subject=self.config.get("subject", "Freigabe erforderlich"),
            context=context,
        )

        return {
            "success": True,
            "output": "waiting_for_approval",
            "waiting": True,  # Signal an Executor: nicht zur nächsten Action
        }
```

```python
# apps/workflows/views.py — Callback-Endpoint
@csrf_exempt
@require_POST
def approval_callback(request, execution_id):
    """Wird aufgerufen wenn Berater die Freigabe erteilt/ablehnt."""
    token = request.POST.get("token", "")
    decision = request.POST.get("decision", "")  # "approved" | "rejected"

    from apps.workflows.services import WorkflowExecutionService
    result = WorkflowExecutionService.resume_execution(
        execution_id=execution_id,
        token=token,
        decision=decision,
    )
    if not result["valid"]:
        return HttpResponseForbidden("Ungültiger oder abgelaufener Token")

    return redirect("workflows:execution_detail", pk=execution_id)
```

**Flow**: Action setzt Status `waiting` → E-Mail mit Freigabe-Link → Berater
klickt → Callback resumed Execution → nächste Phase wird ausgeführt.

### 13.6 Workflow-Modelle

```python
# apps/workflows/models.py
from django.db import models
from django.utils import timezone


class WorkflowTemplate(models.Model):
    """Wiederverwendbare Workflow-Vorlage (z.B. Rechnungsfreigabe)."""
    name         = models.CharField(max_length=200)
    description  = models.TextField(blank=True)
    category     = models.CharField(max_length=50,
                     choices=[("tax", "Steuer"), ("dms", "Dokumente"),
                              ("dsb", "Datenschutz"), ("billing", "Abrechnung"),
                              ("custom", "Benutzerdefiniert")])
    is_active    = models.BooleanField(default=True)
    created_by   = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflow_templates"
        ordering = ["category", "name"]


class WorkflowPhase(models.Model):
    """Phase innerhalb eines Workflows (sequentiell)."""
    template     = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE,
                     related_name="phases")
    name         = models.CharField(max_length=100)
    order        = models.IntegerField(default=0)
    is_active    = models.BooleanField(default=True)

    class Meta:
        db_table = "workflow_phases"
        ordering = ["template", "order"]
        unique_together = [["template", "order"]]


class WorkflowAction(models.Model):
    """Einzelne Aktion in einer Phase — verweist auf einen Handler."""
    phase           = models.ForeignKey(WorkflowPhase, on_delete=models.CASCADE,
                       related_name="actions")
    name            = models.CharField(max_length=100)
    handler_class   = models.CharField(max_length=200,
                       help_text="Python-Pfad, z.B. apps.workflows.handlers.email.SendEmailHandler")
    config          = models.JSONField(default=dict, blank=True,
                       help_text="Handler-Konfiguration (Empfänger, Template, etc.)")
    order           = models.IntegerField(default=0)
    is_required     = models.BooleanField(default=True)
    continue_on_error = models.BooleanField(default=False)
    timeout_seconds = models.IntegerField(null=True, blank=True)
    retry_count     = models.IntegerField(default=0)

    class Meta:
        db_table = "workflow_actions"
        ordering = ["phase", "order"]


class WorkflowExecution(models.Model):
    """Laufende oder abgeschlossene Workflow-Instanz."""
    template     = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE)
    status       = models.CharField(max_length=20,
                     choices=[("running", "Läuft"), ("waiting", "Wartet auf Freigabe"),
                              ("completed", "Abgeschlossen"),
                              ("failed", "Fehlgeschlagen"), ("cancelled", "Abgebrochen")])
    context_data = models.JSONField(default=dict,
                     help_text="Workflow-Kontext (Input-Daten, Zwischenergebnisse)")
    started_at   = models.DateTimeField(auto_now_add=True)
    finished_at  = models.DateTimeField(null=True, blank=True)
    triggered_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = "workflow_executions"
        ordering = ["-started_at"]


class ExecutionLog(models.Model):
    """Audit-Log für jede einzelne Action-Ausführung (DSGVO Art. 30)."""
    execution    = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE,
                     related_name="logs")
    action       = models.ForeignKey(WorkflowAction, on_delete=models.CASCADE)
    status       = models.CharField(max_length=20)
    input_data   = models.JSONField(default=dict)
    output_data  = models.JSONField(default=dict)
    error_message = models.TextField(blank=True, default="")
    duration_seconds = models.FloatField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow_execution_logs"
        ordering = ["created_at"]
```

### 13.7 Beispiel-Workflows

#### Rechnungsfreigabe (tax-hub)

```
WorkflowTemplate: "Rechnungsfreigabe"
├── Phase 1: Eingang
│   └── Action: PaperlessDocHandler      # Dokument aus Paperless holen
│   └── Action: DvelopArchiveHandler     # In d.velop archivieren
├── Phase 2: Prüfung
│   └── Action: LLMAnalyzeHandler        # KI: Betrag, Lieferant, Frist extrahieren
│   └── Action: DataValidationHandler    # Pflichtfelder prüfen
├── Phase 3: Freigabe
│   └── Action: WaitForApprovalHandler   # Pausiert — E-Mail an Berater, wartet auf Callback
│   └── Action: SendEmailHandler         # Bestätigung: "Rechnung freigegeben"
└── Phase 4: Buchung
    └── Action: DATEVExportHandler       # DATEV-Buchungssatz erzeugen
    └── Action: SendEmailHandler         # Bestätigung an Mandant
```

#### DSGVO-Löschanfrage (risk-hub, Cross-Hub)

```
WorkflowTemplate: "DSB Löschanfrage Art. 17"
├── Phase 1: Antrag validieren
│   └── Action: DataValidationHandler    # Name, E-Mail, Rechtsgrund prüfen
│   └── Action: SendEmailHandler         # Eingangsbestätigung an Betroffenen
├── Phase 2: Systeme durchsuchen
│   └── Action: PaperlessDocHandler      # Paperless nach Name durchsuchen
│   └── Action: WebhookHandler           # tax-hub API: Mandantendaten suchen
│   └── Action: WebhookHandler           # risk-hub API: Verarbeitungsverzeichnis
├── Phase 3: Löschung durchführen
│   └── Action: WebhookHandler           # DELETE-Calls an betroffene Systeme
│   └── Action: DvelopArchiveHandler     # Löschprotokoll in DMS archivieren
└── Phase 4: Abschluss
    └── Action: SendEmailHandler         # Löschbestätigung an Betroffenen
    └── Action: SendEmailHandler         # Protokoll an DSB (intern)
```

### 13.8 n8n-Integration (optional)

n8n läuft bereits auf dem Server (`/opt/bfagent/docker-compose.n8n.yml`) und bietet
**400+ vorgefertigte Konnektoren** als Ergänzung zu den eigenen Python-Handlern.

```
┌───────────────────────┐          ┌──────────────────────┐
│  tax-hub Workflow      │          │  n8n (self-hosted)   │
│                        │  HTTP    │                      │
│  TriggerN8nHandler ────┼──POST──→│  Webhook-Trigger     │
│                        │          │  ├── Gmail senden    │
│  N8nCallbackView  ←────┼──POST───│  ├── Slack Notify    │
│                        │          │  ├── Google Drive    │
│                        │          │  └── 400+ weitere    │
└───────────────────────┘          └──────────────────────┘
```

**Abgrenzung**: Eigene Handler für Business-Logik (E-Mail, Paperless, DATEV, LLM).
n8n nur für **externe Systeme**, die keine eigene API-Integration rechtfertigen
(z.B. Slack, Google Drive, Trello, Jira).

### 13.9 Cross-Hub-Fähigkeit

Die Workflow-Engine ist nicht auf tax-hub beschränkt. Dasselbe Handler-Pattern
kann in andere Hubs übernommen werden:

| Hub | Workflow-Beispiele |
|-----|-------------------|
| **tax-hub** | Rechnungsfreigabe, Frist-Eskalation, Mandanten-Onboarding |
| **risk-hub** | DSGVO-Löschanfrage, Auskunftsanfrage, DSFA-Durchführung |
| **pptx-hub** | Präsentations-Review, Übersetzungs-Pipeline |
| **travel-beat** | Reise-Genehmigung, Buchungs-Bestätigung |

**Langfrist-Option**: Extraktion als `iil-workflowfw` PyPI-Package
(analog `iil-aifw`, `iil-promptfw`) wenn mindestens 2 Hubs die Engine produktiv nutzen.

---

## 14. More Information

| Referenz | Inhalt |
|----------|--------|
| ADR-007 | Tenant/Plan/Feature-Tabellen — Vorbildmuster für Billing-Modelle |
| ADR-072 | Schema-Isolation — `django-tenants` Implementierungsdetails |
| ADR-035 | Shared Tenancy Package — Organization, Membership |
| ADR-146 | DvelopDmsClient — DMS-App Implementierungsvorlage |
| ADR-148 | KI-Klassifikation — BELEGE-Modul nutzt aifw MEDIUM |
| ADR-152 | Pilot-ADR — durch dieses ADR superseded |
| ADR-079 | Temporal Workflow-Engine — Alternative (abgelehnt für tax-hub, §13.0 Option B) |
| GenAgent (bfagent) | Basis-Framework für Workflow-Engine (Handler, Registry, Executor) |
| Stripe Docs | https://stripe.com/docs/billing/subscriptions |
| django-tenants | https://django-tenants.readthedocs.io/ |

---

*Erstellt: 2026-03-25 · Autor: Achim Dehnert · Review: 2026-03-30 (Cascade)*
