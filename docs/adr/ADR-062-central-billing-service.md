---
status: accepted
date: 2026-03-05
decision-makers: Achim Dehnert
implementation_status: partial
implementation_evidence:
  - "billing-hub: exists but Stripe integration incomplete"
---

# ADR-062: Zentraler Billing-Service für die Plattform

_Ein Service für Kundenverwaltung, Abonnements und Modulkäufe über alle Hubs hinweg_

| Feld | Wert |
| --- | --- |
| **ADR-ID** | ADR-062 |
| **Titel** | Zentraler Billing-Service |
| **Status** | Accepted (v2 — nach Review überarbeitet) |
| **Datum** | 2026-03-05 |
| **Review-Datum** | 2026-03-05 |
| **Autor** | Achim Dehnert / Cascade |
| **Reviewer** | Claude (Senior Architect) |
| **Betrifft** | Alle Hubs: coach-hub, risk-hub, travel-beat, weltenhub, trading-hub, pptx-hub, cad-hub, illustration-hub, dev-hub |
| **Related ADRs** | ADR-021 (Unified Deployment), ADR-027 (Shared Backend Services), ADR-035 (Shared Django Tenancy), ADR-081 (coach-hub Stripe), ADR-082 (coach-hub DSGVO) |

---

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| v1 | 2026-03-05 | Initialer Entwurf |
| v2 | 2026-03-05 | Überarbeitung nach Architecture Review: 5 Blocker, 6 hohe, 5 mittlere, 4 niedrige Findings adressiert. Port-Konflikt behoben (8020→8092), Fail-open→Fail-closed, HMAC-Auth, Stripe-Signatur, BigAutoField PKs, Subscription-History, DSGVO-Propagation, async Webhook, §8 Konsequenzen ergänzt. |

---

## 1. Kontext und Problemstellung

### 1.1 Ausgangslage

Die Plattform umfasst **9+ Django-basierte Hubs** auf einem Server (`88.198.191.108`), die jeweils kostenpflichtige Module anbieten werden. Aktuell existiert eine Stripe-Integration nur in **coach-hub** (ADR-081).

| Aspekt | Ist-Zustand | Problem |
| --- | --- | --- |
| Kundenverwaltung | Keiner der Hubs hat eine zentrale Kundenansicht | Kein Überblick, wer was bezahlt |
| Bezahlung | Nur coach-hub hat Stripe (5 Webhook-Handler) | Jeder Hub müsste Stripe neu implementieren |
| Admin-Dashboard | Django-Admin in coach-hub (`UserTier`, `ModuleAccess`) | Pro Hub isoliert, kein Gesamtbild |
| Cross-Platform | Nicht möglich | Kunde kann kein Bundle über mehrere Hubs kaufen |
| DSGVO | Pro Hub implementiert (ADR-082) | Datenexport/Löschung pro Hub manuell |

### 1.2 Betroffene Hubs und geplante Monetarisierung

| Hub | Brand | Geplante Module | Status |
| --- | --- | --- | --- |
| coach-hub | KI ohne Risiko | 15 Module (Free → Enterprise) | ✅ Stripe aktiv |
| risk-hub | Schutztat | Risk-Assessment, Reports | 🟡 Geplant |
| travel-beat | DriftTales | Trip-Planung, Premium-Routen | 🟡 Geplant |
| weltenhub | Weltenforger | Kampagnen, Premium-Content | 🟡 Geplant |
| cad-hub | CAD Portal | CAD-Konvertierung, Batch-Export | 🟡 Geplant |
| trading-hub | AI-Trades | Bot-Strategien, Market-Scanner | 🟡 Geplant |
| pptx-hub | Prezimo | Premium-Templates, AI-Slides | 🟡 Geplant |
| illustration-hub | — | AI-Illustration, Batch-Generation | 🟡 Geplant |
| dev-hub | — | Dev-Tools, API-Zugang | 🟡 Geplant |

### 1.3 Anforderungen

1. **Ein Stripe-Account** für alle Hubs (ein Webhook-Endpoint)
2. **Zentrale Kundenansicht**: Wer hat welches Abo auf welchem Hub?
3. **Modul-Zugriffsprüfung** per interner API (Hub fragt Billing-Service)
4. **Cross-Platform-Bundles**: z.B. "Premium All-Access" für coach-hub + risk-hub
5. **Admin-Dashboard** für Support und Verwaltung
6. **DSGVO-konform**: Ein Ort für Datenexport und Löschung (mit Propagation an Hubs)
7. **PayPal als Zahlungsmethode** via Stripe Checkout (keine separate Integration)

---

## 2. Entscheidung

### 2.1 Architektur: Zentraler Billing-Service als eigener Hub

Ein eigenständiger Django-Service (`billing-hub`) im bestehenden Docker-Netzwerk (`bf_platform_prod`), der alle Zahlungs- und Kundenverwaltungslogik zentralisiert.

```
┌──────────────────────────────────────────────────────────┐
│                    Stripe (extern)                        │
│   Products · Subscriptions · Checkout · Customer Portal   │
└────────────────────────┬─────────────────────────────────┘
                         │ Webhook POST (Signatur-geprüft)
                         ▼
┌──────────────────────────────────────────────────────────┐
│              billing-hub (zentral, Port 8092)             │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Customer │  │ Subscription │  │ ModulePurchase    │  │
│  │ Platform │  │ Invoice      │  │ BillingEvent      │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Internal API (HMAC-Auth + Docker-Network)          │ │
│  │  GET /api/access/{platform}/{email}/{module}/       │ │
│  │  GET /api/customer/{email}/                         │ │
│  │  POST /api/webhook/stripe/   (Stripe-Signatur)     │ │
│  │  DELETE /api/internal/gdpr/customer/{email}/        │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Health: GET /livez/ · GET /healthz/                │ │
│  │  Admin:  /admin/ (eigener Django-Admin, Superuser)  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
         ▲              ▲              ▲
         │ HMAC-Auth    │ HMAC-Auth    │ HMAC-Auth
    ┌────┴───┐    ┌────┴───┐    ┌────┴───┐
    │coach   │    │risk    │    │travel  │  ...
    │hub     │    │hub     │    │beat    │
    │:8007   │    │:8090   │    │:8002   │
    └────────┘    └────────┘    └────────┘
```

### 2.2 Datenmodell

```python
# apps/billing/models.py

from django.db import models
from django.utils import timezone


class BillingBaseModel(models.Model):
    """Abstrakte Basisklasse: created_at + updated_at auf allen Modellen (H-02)."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Platform(BillingBaseModel):
    """Registrierte Hub-Plattformen. BigAutoField PK per ADR-009 (K-05)."""
    slug = models.SlugField(unique=True, max_length=50, db_index=True)
    name = models.CharField(max_length=100)
    base_url = models.URLField()
    internal_url = models.URLField()
    internal_api_secret = models.CharField(
        max_length=255,
        help_text="HMAC-Secret für Hub→BillingHub interne API-Calls (M-01)"
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "billing_platform"

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"


class Customer(BillingBaseModel):
    """Plattformübergreifender Kunde."""
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    stripe_customer_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True, db_index=True,
        help_text="Stripe Customer ID (cus_xxx). NULL vor erstem Kauf."
    )
    gdpr_consent_at = models.DateTimeField(null=True, blank=True)
    gdpr_deletion_requested_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_pseudonymized = models.BooleanField(default=False)

    class Meta:
        db_table = "billing_customer"

    def __str__(self) -> str:
        return self.email if not self.is_pseudonymized else "[pseudonymized]"


class SubscriptionTier(models.TextChoices):
    FREE = "free", "Free"
    REGISTERED = "registered", "Registered"
    PREMIUM = "premium", "Premium"
    ENTERPRISE = "enterprise", "Enterprise"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Aktiv"
    PAST_DUE = "past_due", "Überfällig"
    CANCELED = "canceled", "Gekündigt"
    TRIALING = "trialing", "Testphase"
    INCOMPLETE = "incomplete", "Unvollständig"


class Subscription(BillingBaseModel):
    """Abo eines Kunden auf einer Plattform. Soft-Versioning statt unique_together (H-01)."""
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="subscriptions"
    )
    platform = models.ForeignKey(
        Platform, on_delete=models.PROTECT, related_name="subscriptions"
    )
    tier = models.CharField(
        max_length=20, choices=SubscriptionTier.choices, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=SubscriptionStatus.choices, db_index=True
    )
    stripe_subscription_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "billing_subscription"
        indexes = [
            models.Index(
                fields=["customer", "platform", "is_active"],
                name="billing_sub_active_idx",
            ),
        ]

    @classmethod
    def get_active(cls, customer_id: int, platform_id: int):
        return cls.objects.filter(
            customer_id=customer_id,
            platform_id=platform_id,
            is_active=True,
        ).first()

    def __str__(self) -> str:
        return f"{self.customer.email} @ {self.platform.slug}: {self.tier}/{self.status}"


class PurchaseReason(models.TextChoices):
    REDEEM_CODE = "redeem_code", "Einlösecode"
    MANUAL = "manual", "Manuell (Admin)"
    BUNDLE = "bundle", "Bundle-Kauf"
    BETA = "beta", "Beta-Tester"
    PARTNER = "partner", "Partner"


class ModulePurchase(BillingBaseModel):
    """Einzelkauf oder Override: Kunde hat Zugriff auf ein bestimmtes Modul."""
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="module_purchases"
    )
    platform = models.ForeignKey(
        Platform, on_delete=models.PROTECT, related_name="module_purchases"
    )
    module_id = models.SlugField(db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=50, choices=PurchaseReason.choices)

    class Meta:
        db_table = "billing_modulepurchase"
        indexes = [
            models.Index(
                fields=["customer", "platform", "module_id"],
                name="billing_mp_lookup_idx",
            ),
        ]

    def is_valid(self) -> bool:
        if self.expires_at is None:
            return True
        return timezone.now() < self.expires_at

    def __str__(self) -> str:
        return f"{self.customer.email} → {self.platform.slug}/{self.module_id}"


class Invoice(BillingBaseModel):
    """Rechnungshistorie."""
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="invoices"
    )
    stripe_invoice_id = models.CharField(max_length=100, unique=True, db_index=True)
    amount_cents = models.IntegerField()
    currency = models.CharField(max_length=3, default="eur")
    status = models.CharField(max_length=20, db_index=True)
    platform = models.ForeignKey(
        Platform, on_delete=models.PROTECT, null=True, blank=True
    )

    class Meta:
        db_table = "billing_invoice"

    def __str__(self) -> str:
        return f"{self.stripe_invoice_id}: {self.amount_cents / 100:.2f} {self.currency}"


class BillingEvent(models.Model):
    """Idempotenz-Deduplication für Stripe-Webhooks. Nie löschen (N-04: PROTECT)."""
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    platform = models.ForeignKey(
        Platform, on_delete=models.PROTECT, null=True, blank=True
    )
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_event"

    def __str__(self) -> str:
        return f"{self.event_type}: {self.event_id}"
```

### 2.3 Interne API (HMAC-authentifiziert)

Alle API-Endpoints sind per HMAC-basiertem Shared Secret geschützt (K-03). Docker-Network-Isolation allein reicht nicht als Security-Boundary.

| Endpoint | Methode | Beschreibung |
| --- | --- | --- |
| `/api/access/{platform}/{email}/{module}/` | GET | Zugriffsprüfung → `{"allowed": true, "reason": "subscription"}` |
| `/api/customer/{email}/` | GET | Kundendetails + alle Abos über alle Plattformen |
| `/api/customer/{email}/subscriptions/` | GET | Alle Abos eines Kunden |
| `/api/webhook/stripe/` | POST | Zentraler Stripe-Webhook (Stripe-Signatur, nicht HMAC) |
| `/api/platforms/` | GET | Registrierte Plattformen |
| `/api/sync/{platform}/` | POST | Bulk-Sync von Modulkatalog einer Plattform |
| `/api/internal/gdpr/customer/{email}/` | DELETE | DSGVO-Löschung auslösen |
| `/livez/` | GET | Liveness-Probe (Prozess läuft) |
| `/healthz/` | GET | Readiness-Probe (DB + Redis + Stripe erreichbar) |

**HMAC-Authentifizierung (K-03):**

```python
# billing-hub: apps/api/authentication.py
import hashlib
import hmac
import time
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class InternalServiceAuthentication(BaseAuthentication):
    """HMAC-basierte Auth für Service-zu-Service Calls.

    Header: X-Internal-Token: <platform_id>:<timestamp>:<hmac_sha256>
    Replay-Schutz: Timestamp darf max. 30s alt sein.
    """
    MAX_AGE_SECONDS = 30

    def authenticate(self, request):
        token = request.headers.get("X-Internal-Token")
        if not token:
            raise AuthenticationFailed("Missing X-Internal-Token")

        try:
            platform_id, timestamp_str, provided_hmac = token.split(":", 2)
            timestamp = int(timestamp_str)
        except (ValueError, TypeError):
            raise AuthenticationFailed("Invalid token format")

        if abs(time.time() - timestamp) > self.MAX_AGE_SECONDS:
            raise AuthenticationFailed("Token expired (replay protection)")

        expected = hmac.new(
            settings.BILLING_INTERNAL_SECRET.encode(),
            f"{platform_id}:{timestamp_str}".encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, provided_hmac):
            raise AuthenticationFailed("Invalid HMAC")

        return (platform_id, None)
```

### 2.4 Zugriffslogik in den Hubs (Client-Seite)

Dreistufige Degradation — **Fail-closed** bei Billing-Ausfall (K-02):

```python
# apps/billing/client.py (Shared Package für jeden Hub)
import hashlib
import hmac
import logging
import time

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)
BILLING_URL = "http://billing-hub-web:8000"
CACHE_TTL = 300       # 5 Minuten
CACHE_STALE_TTL = 3600  # 1 Stunde für Stale-Cache


def _cache_key(platform: str, email: str, module: str) -> str:
    raw = f"billing:{platform}:{email}:{module}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _internal_token(platform_id: str) -> str:
    ts = str(int(time.time()))
    sig = hmac.new(
        settings.BILLING_INTERNAL_SECRET.encode(),
        f"{platform_id}:{ts}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{platform_id}:{ts}:{sig}"


def can_access(platform: str, email: str, module: str) -> tuple[bool, str]:
    """
    Zugriffsprüfung mit dreistufiger Degradation:
      1. Primär: billing-hub API (frisch)
      2. Fallback: lokaler Cache (bis 5 min stale)
      3. Notfall: stale Cache (bis 1h, nur bei vorherigem allow) → sonst DENY
    """
    key = _cache_key(platform, email, module)

    # Stufe 1: API-Call
    try:
        r = httpx.get(
            f"{BILLING_URL}/api/access/{platform}/{email}/{module}/",
            timeout=1.5,
            headers={"X-Internal-Token": _internal_token(platform)},
        )
        r.raise_for_status()
        data = r.json()
        result = (data.get("allowed", False), data.get("reason", "unknown"))
        cache.set(key, result, timeout=CACHE_TTL)
        cache.set(f"{key}:stale", result, timeout=CACHE_STALE_TTL)
        return result
    except Exception as exc:
        logger.warning("billing-hub unreachable: %s", exc)

    # Stufe 2: Frischer Cache (< 5 min)
    cached = cache.get(key)
    if cached is not None:
        return cached[0], f"{cached[1]}:cached"

    # Stufe 3: Stale Cache (< 1h) — nur bei vorherigem allow
    stale = cache.get(f"{key}:stale")
    if stale is not None and stale[0] is True:
        logger.error("billing-hub down, using stale cache for %s/%s", platform, email)
        return True, "billing_stale_cache"

    # Kein Cache → DENY (fail-closed)
    logger.error(
        "billing-hub down, no cache — denying %s/%s/%s", platform, email, module
    )
    return False, "billing_unavailable"
```

### 2.5 Stripe-Konfiguration

- **Ein Stripe-Account** mit Products pro Plattform (Metadata: `platform_id`)
- **Ein Webhook-Endpoint**: `https://billing.iil.pet/api/webhook/stripe/`
- **Stripe-Signaturprüfung** via `stripe.Webhook.construct_event()` (K-04)
- **Async Verarbeitung**: Webhook gibt sofort `200` zurück, Celery verarbeitet async (H-03)
- **PayPal**: Aktiviert als Zahlungsmethode im Stripe Dashboard (kein Code nötig)
- **Stripe Products Naming**: `{platform} — {tier}` (z.B. "KI ohne Risiko — Premium Monthly")
- **Stripe Webhook Secret**: Ein globales `STRIPE_WEBHOOK_SECRET` in `.env.prod`

**Webhook-Handler (K-04, H-03):**

```python
# apps/billing/views.py
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .tasks import process_stripe_event_async


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Stripe-Webhook: Signaturprüfung → sofort 200 → async Verarbeitung."""
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.META.get("HTTP_STRIPE_SIGNATURE", ""),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.SignatureVerificationError:
        return HttpResponse(status=400)
    except ValueError:
        return HttpResponse(status=400)

    process_stripe_event_async.delay(event["id"], event["type"], event)
    return HttpResponse(status=200)
```

```python
# apps/billing/tasks.py
from celery import shared_task
from .services import billing_event_service


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def process_stripe_event_async(self, event_id, event_type, payload):
    """Idempotente Stripe-Event-Verarbeitung via BillingEvent-Deduplication."""
    billing_event_service.process_event(event_id, event_type, payload)
```

### 2.6 DSGVO-Propagation (H-04)

Bei Löschung eines Kunden propagiert billing-hub die Löschung an alle betroffenen Hubs:

```python
# apps/billing/services/gdpr_service.py
from celery import group
from .tasks import propagate_gdpr_deletion_to_hub


def initiate_customer_deletion(customer_id: int) -> dict:
    """
    DSGVO-Löschung (Art. 17):
    1. Lösch-Tasks an alle aktiven Plattformen senden
    2. Customer in billing-hub pseudonymisieren
    3. Audit-Log erstellen
    """
    customer = Customer.objects.get(pk=customer_id)
    platforms = Platform.objects.filter(
        subscriptions__customer=customer, is_active=True
    ).distinct()

    task_group = group(
        propagate_gdpr_deletion_to_hub.s(
            platform_slug=p.slug,
            internal_url=p.internal_url,
            customer_email=customer.email,
        )
        for p in platforms
    )
    result = task_group.apply_async()
    _pseudonymize_customer(customer)
    return {"group_id": result.id, "platform_count": platforms.count()}
```

Jeder Hub muss einen internen DSGVO-Endpoint implementieren:

```
DELETE /api/internal/gdpr/customer/{email}/
```

### 2.7 Admin-Dashboard

Django Admin mit eigenen Superusern (kein SSO):

- **Kundensuche** nach E-Mail, Name, Company
- **Kundendetail**: Alle Abos, alle Plattformen, Rechnungshistorie, Module
- **Abo-Verwaltung**: Tier manuell setzen, Grace Period, Cancel
- **Modul-Override**: Einzelnem Kunden Modul freischalten (z.B. für Partner, Beta-Tester)
- **Redeem-Codes**: Plattformübergreifende Gutscheincodes
- **DSGVO**: Datenexport und Löschung pro Kunde (propagiert an alle Hubs)
- **Revenue-Dashboard**: Stripe Dashboard für MVP (kein eigenes BI-Tool)

---

## 3. Alternativen (nicht gewählt)

### 3.1 Pro-Hub Stripe-Integration (Ist-Zustand)

- Jeder Hub implementiert Stripe separat
- **Abgelehnt**: Nicht skalierbar, kein Gesamtbild, Code-Duplikation

### 3.2 Shared Django App als pip-Package

- `bf-billing` als Package in jeden Hub installiert
- **Abgelehnt**: Kein plattformübergreifender Überblick ohne Shared DB; bei Shared DB verliert man die Service-Isolation

### 3.3 Stripe Dashboard als Admin

- Stripe's eigene UI für Kundenverwaltung nutzen
- **Abgelehnt**: Keine Zuordnung zu Plattform-Modulen, keine Custom-Logik, kein DSGVO-Export

### 3.4 Stripe Billing Portal + Minimal Backend

- Stripe's gehostetes Customer Portal für Abo-Verwaltung, eigener Code nur für Support-Overrides
- **Abgelehnt für Langfrist**: Kein Cross-Platform-Bundle-Support, kein Custom-Branding ohne Paid Plan
- **Evaluierung für Phase 1**: Als temporäre Kunden-Self-Service-Lösung nutzbar

### 3.5 Lago (Open Source Metering & Billing)

- [Lago](https://www.getlago.com/) für Usage-Based-Billing
- **Vorgemerkt**: Relevant wenn trading-hub oder dev-hub usage-based abgerechnet werden
- **Aktuell**: Overkill für subscription-based Modelle

---

## 4. Migration von coach-hub

### Phase 1: Billing-Hub aufsetzen (Woche 1)

- Repo `billing-hub` erstellen
- Datenmodell, Admin, Stripe-Webhook (async), HMAC-Auth
- Docker Compose in `bf_platform_prod`
- Health-Endpoints `/livez/`, `/healthz/`

### Phase 2: Datenmigration (Woche 2)

- coach-hub `UserTier` + `ModuleAccess` + `StripeEvent` → billing-hub migrieren
- Stripe-Webhook von coach-hub auf billing-hub umleiten
- coach-hub: `can_access_module()` → billing-hub API Call (mit Cache-Fallback)
- **Dual-Write-Phase**: Beide Systeme parallel, Feature-Flag steuert Quelle

### Phase 3: Weitere Hubs anbinden (Woche 3+)

- risk-hub, travel-beat etc. registrieren ihre Module im billing-hub
- Stripe Products für weitere Hubs anlegen
- Pricing-Pages in den Hubs verlinken auf billing-hub Checkout

### Phase 4: coach-hub Payment-Code entfernen

- `apps/payments/` in coach-hub entfernen (Webhook, Views)
- `apps/registry/models.py`: `UserTier`, `ModuleAccess` durch billing-hub API ersetzen
- Feature-Flag entfernen nach erfolgreicher Validierung

---

## 5. Infrastruktur

| Komponente | Wert |
| --- | --- |
| **Repo** | `achimdehnert/billing-hub` |
| **Deploy-Path** | `/opt/billing-hub` |
| **Port** | **8092** (nächster freier Port, ADR-021 §2.9 aktualisieren) |
| **Externe URL** | `https://billing.iil.pet` (Admin + Stripe-Webhook) |
| **DNS** | A + AAAA → `88.198.191.108` (bereits eingerichtet) |
| **DB** | `billing_hub_db` (PostgreSQL 16, eigener Container) |
| **Cache** | Redis (shared `coach_hub_redis` oder eigener Container) |
| **Network** | `bf_platform_prod` (shared mit allen Hubs) |
| **CI/CD** | `_ci-python.yml` → `_build-docker.yml` → `_deploy-hetzner.yml` |
| **Health** | `GET /livez/` (liveness), `GET /healthz/` (readiness) |
| **HTTP-Client** | `httpx` (Platform-Standard für inter-service HTTP) |

---

## 6. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
| --- | --- | --- | --- |
| Billing-Hub Ausfall → alle Hubs betroffen | Mittel | Hoch | **Fail-closed** mit dreistufigem Cache (5 min frisch, 1h stale, dann DENY) |
| Kompromittierter Container liest Kundendaten | Niedrig | Hoch | HMAC-Auth auf allen internen API-Endpoints |
| Gefälschte Stripe-Webhooks | Niedrig | Hoch | `stripe.Webhook.construct_event()` Signaturprüfung |
| Webhook-Timeout (>30s) → Doppelverarbeitung | Mittel | Mittel | Async Celery + `BillingEvent` Idempotenz-Deduplication |
| Latenz durch Netzwerk-Call | Niedrig | Niedrig | Internes Docker-Netzwerk (~1ms), httpx mit 1.5s Timeout |
| Datenmigration bricht coach-hub | Mittel | Hoch | Feature-Flag, Dual-Write-Phase, Rollback-Plan |
| DSGVO-Löschung schlägt bei einem Hub fehl | Niedrig | Hoch | Celery-Retry (5x), Audit-Log, manueller Fallback im Admin |

---

## 7. Entschiedene Fragen

| Frage | Entscheidung |
| --- | --- |
| **Domain** | `billing.iil.pet` (DNS bereits eingerichtet) |
| **Auth für Admin** | Eigener Django-Admin mit Superusern (Option A) |
| **Revenue-Split** | Derzeit nicht relevant |
| **Timing** | Sofort — Implementierung startet nach ADR-Freigabe |

---

## 8. Konsequenzen

### Positive Konsequenzen

- Ein Stripe-Account → eine Rechnung, eine Steuerberichterstattung
- DSGVO-Compliance zentralisiert: Ein Lösch-Endpoint für alle Hubs
- Cross-Platform-Bundles werden möglich (Anforderung 4)
- Neue Hubs monetarisierbar in < 1 Tag (Platform registrieren + Stripe Product anlegen)
- MRR-Übersicht über alle Hubs via Stripe Dashboard ohne manuelle Aggregation

### Negative Konsequenzen

- Neuer Single Point of Failure: billing-hub Ausfall → Zugriffsprüfung fällt auf Cache zurück
- Netzwerk-Latenz: Jeder Module-Access-Check kostet ~1ms (intern Docker)
- Migrationskomplexität: coach-hub Stripe-Integration muss vollständig migriert werden
- Operationeller Overhead: Ein weiterer Service zu betreiben, monitoren, updaten
- Höhere Anforderungen an Deployment-Reihenfolge: billing-hub muss vor Hubs starten
