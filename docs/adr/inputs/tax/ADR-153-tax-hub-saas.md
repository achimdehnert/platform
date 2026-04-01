---
status: "proposed"
date: 2026-03-25
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes:
  - ADR-152   # tax-hub als Pilot-Repo — durch SaaS-Architektur ersetzt
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
staleness_months: 6
drift_check_paths:
  - tax-hub/apps/modules/
  - tax-hub/apps/billing/
  - tax-hub/apps/tenant/
---

# ADR-153: Adopt Module-basierte SaaS-Architektur für tax-hub (Multi-Mandant, buchbare Module)

## Metadaten

| Attribut       | Wert                                                                        |
|----------------|-----------------------------------------------------------------------------|
| **Status**     | Proposed                                                                    |
| **Scope**      | platform + service                                                          |
| **Erstellt**   | 2026-03-25                                                                  |
| **Autor**      | Achim Dehnert                                                               |
| **Supersedes** | ADR-152 (tax-hub Pilot — Scope zu eng für SaaS)                             |
| **Relates to** | ADR-007, ADR-050, ADR-072, ADR-035, ADR-021, ADR-146                        |

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
                    "ERECHNUNG", "PORTAL", "API"],
        "mandanten_limit": None,  # unbegrenzt
        "berater_limit": None,
    },
}
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
│   └── api_gateway/        # DRF ViewSets, OpenAPI, API-Key-Auth
│
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
│
├── templates/tax_hub/
├── docker-compose.yml
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
]

TENANT_MODEL = "tenant.Organization"
TENANT_DOMAIN_MODEL = "tenant.Domain"
```

### 5.3 Module-Guard System

```python
# apps/modules/guard.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from .registry import ModuleRegistry


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

### 5.4 Billing-Modelle

```python
# apps/billing/models.py
import uuid
from django.db import models


class Subscription(models.Model):
    """SaaS-Subscription eines Steuerberatungsbüros."""

    class Status(models.TextChoices):
        TRIAL    = "trial",    "Testphase"
        ACTIVE   = "active",   "Aktiv"
        PAST_DUE = "past_due", "Zahlung überfällig"
        CANCELED = "canceled", "Gekündigt"

    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # tenant_id kommt vom öffentlichen Schema — kein FK, UUID-Referenz
    tenant_id          = models.UUIDField(unique=True, db_index=True)
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

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id   = models.UUIDField(db_index=True)
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

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id   = models.UUIDField(db_index=True)
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
            from django.utils import timezone
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
        from django.utils import timezone
        sub = SubscriptionService.activate_plan(tenant_id, "trial")
        sub.trial_ends_at = timezone.now() + timedelta(days=30)
        sub.status = "trial"
        sub.save(update_fields=["trial_ends_at", "status", "updated_at"])
        logger.info("billing.trial_started tenant=%s kanzlei=%s", tenant_id, kanzlei_name)
        return sub
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
    handler = handlers.get(event["type"])
    if handler:
        handler(event["data"]["object"])
    return HttpResponse(status=200)


def _handle_checkout(session):
    tenant_id  = session["metadata"]["tenant_id"]
    plan_code  = session["metadata"]["plan_code"]
    SubscriptionService.activate_plan(tenant_id, plan_code)


def _handle_payment_failed(invoice):
    from .models import Subscription
    Subscription.objects.filter(
        stripe_customer_id=invoice["customer"]
    ).update(status="past_due")


def _handle_canceled(subscription):
    from .models import Subscription
    Subscription.objects.filter(
        stripe_sub_id=subscription["id"]
    ).update(status="canceled")
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

---

## 7. Deployment-Parameter

| Parameter | Wert |
|-----------|------|
| **Repository** | `achimdehnert/tax-hub` |
| **Image** | `ghcr.io/achimdehnert/tax-hub:latest` |
| **Port** | **8096** |
| **Domain (Prod)** | `*.tax.iil.pet` (Wildcard — eine Domain pro Kanzlei) |
| **Domain (Public)** | `tax.iil.pet` (Landing + Registrierung) |
| **DB** | `tax_hub_db` (PostgreSQL 16, Schema per Tenant) |
| **Celery-Queues** | `default`, `dms`, `ai` |
| **Stripe** | Webhook unter `/billing/stripe/webhook/` |

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
| 4 | Landing Page + Self-Service-Registration | ⬜ Pending | – |

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
- Stripe-Webhook muss öffentlich erreichbar sein (kein Cloudflare-Tunnel)
- 8 Module × Tests = signifikanter Test-Aufwand

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

---

## 12. Confirmation

1. `ModuleRegistry.is_active(tenant_id, "KI")` gibt `False` für Starter-Plan
2. `@require_module("KI")` wirft `PermissionDenied` wenn Modul inaktiv
3. `SubscriptionService.activate_plan(tenant_id, "business")` aktiviert alle Business-Module
4. Schema-Isolation: Kanzlei A kann keine Mandanten von Kanzlei B sehen
5. Stripe-Webhook: `checkout.session.completed` → Module aktiviert
6. Trial: 30 Tage → automatisch `status="trial"`, dann Downgrade-Warning
7. Port 8096 in ADR-021 §2.9 eingetragen
8. `catalog-info.yaml` vorhanden, `lifecycle: production` nach Phase 4

---

## 13. More Information

| Referenz | Inhalt |
|----------|--------|
| ADR-007 | Tenant/Plan/Feature-Tabellen — Vorbildmuster für Billing-Modelle |
| ADR-072 | Schema-Isolation — `django-tenants` Implementierungsdetails |
| ADR-035 | Shared Tenancy Package — Organization, Membership |
| ADR-146 | DvelopDmsClient — DMS-App Implementierungsvorlage |
| ADR-148 | KI-Klassifikation — BELEGE-Modul nutzt aifw MEDIUM |
| ADR-152 | Pilot-ADR — durch dieses ADR superseded |
| Stripe Docs | https://stripe.com/docs/billing/subscriptions |
| django-tenants | https://django-tenants.readthedocs.io/ |

---

*Erstellt: 2026-03-25 · Autor: Achim Dehnert · Review: ausstehend*
