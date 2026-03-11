# ADR-062 Review: Zentraler Billing-Service

**Reviewer:** Claude (Senior Architect)
**Datum:** 2026-03-05
**ADR-Status:** Proposed → **ACCEPTED** (v2 — alle Blocker behoben)
**Verifikation:** Cascade (2026-03-05) — 2 Korrekturen am Review, alle Findings ins ADR v2 übernommen

---

## Gesamtbewertung

Die strategische Entscheidung für einen zentralen Billing-Hub ist **architektonisch korrekt** und notwendig für die Plattform-Skalierung. Das ADR leidet jedoch an **zwei kritischen Sicherheitslücken**, **einem harten Infrastruktur-Blocker** und mehreren Platform-Standard-Verletzungen, die vor jeder Implementierung behoben werden müssen.

| Kategorie | Anzahl Findings |
|-----------|-----------------|
| 🔴 KRITISCH (Blocker) | 5 |
| 🟠 HOCH | 6 |
| 🟡 MITTEL | 5 |
| 🔵 NIEDRIG | 4 |

---

## 🔴 KRITISCHE FINDINGS (Blocker)

### K-01 — Port-Konflikt: 8020 bereits durch pptx-hub belegt

**Betroffene Sektion:** §5 Infrastruktur

**Befund:** ADR-021 §2.9 (Port Registry, kanonisch) und ADR-022 §3.8 weisen Port `8020` explizit `pptx-hub (prezimo.com)` zu. Das ADR-062 beansprucht denselben Port für `billing-hub`.

```
ADR-021 §2.9 Port Registry:
  8020 | pptx-hub | prezimo.com  ← BESETZT
  
ADR-062 §5:
  Port: 8020 (billing-hub)       ← KONFLIKT
```

**Impact:** Beide Services können nicht gleichzeitig starten. Das `bf_platform_prod`-Netzwerk würde beim Deploy einen Port-Binding-Fehler werfen.

**Korrektur:** Nächsten freien Port nach ADR-021-Regel wählen und dort registrieren:

```markdown
# §5 korrigiert:
Port: 8092  (nächster freier Port — 8091 ist ebenfalls belegt, verifiziert via `ss -tlnp`)

# ADR-021 §2.9 muss ergänzt werden:
| 8092 | billing-hub | billing.iil.pet |

# ⚠️ Cascade-Korrektur: Reviewer schlug 8091 vor, aber Port 8091 ist bereits belegt.
# Verifiziert am 2026-03-05 via `ss -tlnp | grep 8091` → LISTEN 0.0.0.0:8091
```

---

### K-02 — Sicherheitslücke: Fail-open ist ein finanzielles Risiko

**Betroffene Sektion:** §2.4 Zugriffslogik (Client-Seite)

**Befund:** Der `can_access()`-Client gibt bei Billing-Hub-Ausfall `(True, "billing_unavailable")` zurück. Das bedeutet: **wenn billing-hub down ist, erhalten ALLE User auf ALLEN Hubs kostenlosen Zugang zu ALLEN Paid-Modulen**. Dieses Pattern ist für Content-Delivery (CDN-Ausfall → weiter ausliefern) akzeptabel, aber nicht für Payment-Gates.

```python
# AKTUELL — kritisch falsch:
except Exception:
    return True, "billing_unavailable"  # Alle zahlen nichts mehr
```

**Korrekte Architektur — Dreistufige Degradation:**

```python
# apps/billing/client.py
import hashlib
import logging
import time
from django.core.cache import cache
import httpx

logger = logging.getLogger(__name__)
BILLING_URL = "http://billing-hub-web:8000"
CACHE_TTL = 300  # 5 Minuten
CACHE_STALE_TTL = 3600  # 1 Stunde für Stale-Cache


def _cache_key(platform: str, email: str, module: str) -> str:
    raw = f"billing:{platform}:{email}:{module}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def can_access(platform: str, email: str, module: str) -> tuple[bool, str]:
    """
    Zugriffsprüfung mit dreistufiger Degradation:
      1. Primär: billing-hub API (frisch)
      2. Fallback: lokaler Cache (bis 5 min stale)
      3. Notfall: stale Cache (bis 1h) → sonst DENY
    """
    key = _cache_key(platform, email, module)

    # Stufe 1: API-Call
    try:
        r = httpx.get(
            f"{BILLING_URL}/api/access/{platform}/{email}/{module}/",
            timeout=1.5,
            headers={"X-Internal-Token": settings.BILLING_INTERNAL_TOKEN},
        )
        r.raise_for_status()
        data = r.json()
        result = (data.get("allowed", False), data.get("reason", "unknown"))
        # Frisches Ergebnis cachen (both TTLs)
        cache.set(key, result, timeout=CACHE_TTL)
        cache.set(f"{key}:stale", result, timeout=CACHE_STALE_TTL)
        return result

    except Exception as exc:
        logger.warning("billing-hub unreachable: %s", exc)

    # Stufe 2: Frischer Cache (< 5 min)
    cached = cache.get(key)
    if cached is not None:
        return cached[0], f"{cached[1]}:cached"

    # Stufe 3: Stale Cache (< 1h) — konservativ: nur bei vorherigem allow
    stale = cache.get(f"{key}:stale")
    if stale is not None and stale[0] is True:
        logger.error("billing-hub down, using stale cache for %s/%s", platform, email)
        return True, "billing_stale_cache"

    # Kein Cache → DENY (fail-closed)
    logger.error("billing-hub down, no cache available — denying %s/%s/%s",
                 platform, email, module)
    return False, "billing_unavailable"
```

**Zusätzlich erforderlich:** Cache-Warm-up beim Hub-Start und Cache-Invalidierung via Webhook/Signal.

---

### K-03 — Sicherheitslücke: Keine Authentifizierung auf interner API

**Betroffene Sektion:** §2.3 Interne API

**Befund:** Das ADR verlässt sich ausschließlich auf die Docker-Network-Isolation (`bf_platform_prod`). Das ist unzureichend:
- Jeder kompromittierte Container im Netzwerk kann beliebige Kundendaten abfragen
- `GET /api/customer/{email}/` liefert sensible Kundendaten ohne Auth
- `POST /api/webhook/stripe/` ist ein offenes Einfallstor für Replay-Angriffe

**Korrektur — HMAC-basiertes Shared Secret (kein OAuth-Overhead):**

```python
# billing-hub: apps/api/authentication.py
import hashlib
import hmac
import time
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class InternalServiceAuthentication(BaseAuthentication):
    """HMAC-basierte Authentifizierung für interne Service-zu-Service Calls.
    
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

        # Replay-Schutz
        if abs(time.time() - timestamp) > self.MAX_AGE_SECONDS:
            raise AuthenticationFailed("Token expired (replay protection)")

        # HMAC validieren
        expected = hmac.new(
            settings.BILLING_INTERNAL_SECRET.encode(),
            f"{platform_id}:{timestamp_str}".encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, provided_hmac):
            raise AuthenticationFailed("Invalid HMAC")

        return (platform_id, None)  # (user, auth)
```

```python
# Jeder Hub-Client generiert so:
import hashlib, hmac, time
from django.conf import settings

def _internal_token(platform_id: str) -> str:
    ts = str(int(time.time()))
    sig = hmac.new(
        settings.BILLING_INTERNAL_SECRET.encode(),
        f"{platform_id}:{ts}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{platform_id}:{ts}:{sig}"
```

**Stripe-Webhook** muss zusätzlich `stripe.Webhook.construct_event()` verwenden (siehe K-04).

---

### K-04 — Stripe-Webhook-Signatur nicht spezifiziert

**Betroffene Sektion:** §2.5 Stripe-Konfiguration, §2.2 Datenmodell (`BillingEvent`)

**Befund:** Das ADR erwähnt kein `stripe.Webhook.construct_event()`. Ohne Signaturprüfung kann jeder beliebige POST an den Webhook-Endpoint gefälschte Events senden (z.B. `customer.subscription.updated → tier=enterprise` für einen Free-User).

**Korrektur — Vollständiger Webhook-Handler:**

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
    """Stripe-Webhook: Signaturprüfung → sofortiges 200 → async Verarbeitung."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:  # SDK v14+ (kein .error. Submodul mehr)
        return HttpResponse(status=400)
    except ValueError:
        return HttpResponse(status=400)

    # Sofort 200 zurückgeben, async verarbeiten (Stripe-Timeout: 30s)
    process_stripe_event_async.delay(event["id"], event["type"], event)
    return HttpResponse(status=200)
```

```python
# apps/billing/tasks.py (Celery)
from celery import shared_task
from .services import billing_event_service


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def process_stripe_event_async(self, event_id: str, event_type: str, payload: dict):
    """Idempotente Stripe-Event-Verarbeitung."""
    billing_event_service.process_event(event_id, event_type, payload)
```

---

### K-05 — Platform-Standard-Verletzung: SlugField als Primary Key

**Betroffene Sektion:** §2.2 Datenmodell (`Platform`)

**Befund:** `Platform` verwendet `id = models.SlugField(primary_key=True)`. Dies verletzt den Plattform-Standard (ADR-009, ADR-050): **BigAutoField Integer PKs für alle User-Data-Modelle**. Slug-PKs erzeugen Probleme bei FK-Performance-Indizes, Django Admin und ORM-JOINs.

**Korrektur (Option C — analoges Muster zu quickcheck ADR-Review):**

```python
class Platform(models.Model):
    """Registrierte Hub-Plattformen."""
    # Standard: BigAutoField PK (ADR-009)
    id = models.BigAutoField(primary_key=True)
    # Öffentlicher Bezeichner als separates Feld
    slug = models.SlugField(unique=True, max_length=50, db_index=True)
    name = models.CharField(max_length=100)
    base_url = models.URLField()
    internal_url = models.URLField()
    webhook_secret = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_platform"

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"
```

**Konsequenz:** Alle FKs auf `Platform` verwenden `platform_id` (BigInt), nicht den Slug. API-URLs nutzen den `slug` als Identifier.

---

## 🟠 HOHE FINDINGS

### H-01 — Subscription-History geht verloren

**Betroffene Sektion:** §2.2 (`Subscription.unique_together`)

**Befund:** `unique_together = [("customer", "platform")]` erlaubt nur **ein** aktives Abo pro Kunde pro Plattform. Beim Upgrade (Free → Premium) wird das alte Abo überschrieben. **Keine Auditierbarkeit, kein DSGVO-Export der Zahlungshistorie möglich.**

**Korrektur — Soft-Versioning:**

```python
class Subscription(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                  related_name="subscriptions")
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    tier = models.CharField(max_length=20, choices=TierChoices.choices)
    status = models.CharField(max_length=20, choices=StatusChoices.choices,
                               db_index=True)
    stripe_subscription_id = models.CharField(max_length=100, unique=True, null=True)
    current_period_start = models.DateTimeField(null=True)
    current_period_end = models.DateTimeField(null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Statt unique_together: aktives Abo per Query
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "billing_subscription"
        indexes = [
            models.Index(fields=["customer", "platform", "is_active"],
                         name="billing_sub_active_idx"),
        ]

    @classmethod
    def get_active(cls, customer_id: int, platform_id: int):
        return cls.objects.filter(
            customer_id=customer_id,
            platform_id=platform_id,
            is_active=True,
        ).first()
```

---

### H-02 — Keine `updated_at` Timestamps auf kritischen Modellen

**Befund:** `Customer`, `Subscription`, `ModulePurchase`, `Invoice`, `BillingEvent` haben kein `updated_at`. Für DSGVO-Audit-Trail, Debugging und Stripe-Reconciliation ist `updated_at` zwingend erforderlich.

**Korrektur:** Alle Modelle erben von einer Basis-Klasse:

```python
class BillingBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

---

### H-03 — Async Webhook-Processing fehlt im Design

**Befund:** Das ADR beschreibt keinen async Verarbeitungsfluss. Stripe erwartet eine `200`-Antwort innerhalb von **30 Sekunden**. Bei:
- DB-Locks (bei gleichzeitigen Subscriptions)
- Netzwerk-Calls zu anderen Hubs (DSGVO-Propagation)
- Celery-Rückstau

... kann der Webhook-Handler timeoutn. Stripe wiederholt dann das Event — ohne Idempotenz-Check werden Daten doppelt geschrieben.

**Lösung:** Async-first Pattern (bereits in K-04 beschrieben). Die `BillingEvent`-Tabelle fungiert als **Idempotenz-Deduplication-Table**:

```python
# apps/billing/services/billing_event_service.py
from django.db import transaction
from ..models import BillingEvent

HANDLERS = {
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    "invoice.paid": handle_invoice_paid,
    "checkout.session.completed": handle_checkout_completed,
}

def process_event(event_id: str, event_type: str, payload: dict) -> None:
    """Idempotente Event-Verarbeitung mit Deduplication."""
    with transaction.atomic():
        created = BillingEvent.objects.get_or_create(
            event_id=event_id,
            defaults={"event_type": event_type},
        )[1]
        
        if not created:
            return  # Already processed — idempotent skip
        
        handler = HANDLERS.get(event_type)
        if handler:
            handler(payload)
```

---

### H-04 — DSGVO-Propagation an Hubs unspezifiziert

**Betroffene Sektion:** §2.6 Admin-Dashboard ("propagiert an alle Hubs")

**Befund:** Die DSGVO-Pflicht (Art. 17 DSGVO, Recht auf Löschung) erfordert, dass bei Löschung eines `Customer` in billing-hub auch alle Hubs ihre User-Daten löschen/pseudonymisieren. Das ADR beschreibt diesen Mechanismus nicht. "Propagiert an alle Hubs" ist keine Architektur.

**Korrektur — Spezifikation des Propagations-Mechanismus:**

```python
# apps/billing/services/gdpr_service.py
from celery import group
from .tasks import propagate_gdpr_deletion_to_hub

def initiate_customer_deletion(customer_id: int) -> dict:
    """
    DSGVO-Löschung: 
    1. Customer in billing-hub pseudonymisieren
    2. Lösch-Tasks an alle aktiven Plattformen senden
    3. Audit-Log erstellen
    
    Returns: task_ids für Monitoring
    """
    customer = Customer.objects.get(pk=customer_id)
    platforms = Platform.objects.filter(
        subscription__customer=customer,
        is_active=True,
    ).distinct()

    # Parallel an alle Hubs propagieren
    task_group = group(
        propagate_gdpr_deletion_to_hub.s(
            platform_slug=p.slug,
            internal_url=p.internal_url,
            customer_email=customer.email,
        )
        for p in platforms
    )
    result = task_group.apply_async()

    # Pseudonymisierung in billing-hub
    _pseudonymize_customer(customer)

    return {"group_id": result.id, "platform_count": len(platforms)}
```

**Jeder Hub** muss einen internen DSGVO-Endpoint implementieren:
```
DELETE /api/internal/gdpr/customer/{email}/
```

---

### H-05 — Fehlende Datenbankindizes

**Befund:** Kritische Query-Pfade haben keine expliziten Indizes:

```python
# Häufigste Query: Zugriffsprüfung pro Request
# SELECT * FROM billing_subscription WHERE customer_id=? AND platform_id=? AND is_active=True
# → Benötigt: (customer_id, platform_id, is_active)

# ModulePurchase Lookup:
# SELECT * FROM billing_modulepurchase WHERE customer_id=? AND platform_id=? AND module_id=?
# → Benötigt: (customer_id, platform_id, module_id)

# Korrektur in den Models:
class Meta:
    indexes = [
        models.Index(
            fields=["customer", "platform", "is_active"],
            name="billing_sub_customer_platform_active_idx",
        ),
        models.Index(
            fields=["stripe_subscription_id"],
            name="billing_sub_stripe_id_idx",
        ),
    ]
```

---

### H-06 — Fehlendes MADR-Abschnitt 8 (ADR-Standard)

**Befund:** Die Plattform verwendet MADR 4.0 mit 8 Pflichtabschnitten. ADR-062 endet bei §7 (Offene Fragen). **Abschnitt 8 "Positive und negative Konsequenzen" fehlt.**

**Korrektur:**

```markdown
## 8. Konsequenzen

### Positive Konsequenzen
- Ein Stripe-Account → eine Rechnung, eine Steuerberichterstattung
- DSGVO-Compliance zentralisiert: Ein Lösch-Endpoint für alle Hubs
- Cross-Platform-Bundles werden möglich (ADR-Anforderung 4)
- Neue Hubs monetarisierbar in < 1 Tag (Platform registrieren + Stripe Product anlegen)
- MRR-Dashboard über alle Hubs hinweg ohne manuelle Aggregation

### Negative Konsequenzen
- Neuer Single Point of Failure: billing-hub Ausfall → Zugriffsprüfung fällt auf Cache zurück
- Netzwerk-Latenz: Jeder Module-Access-Check kostet ~1ms (intern Docker)
- Migrationskomplexität: coach-hub Stripe-Integration muss vollständig migriert werden
- Operationeller Overhead: Ein weiterer Service zu betreiben, monitoren, updaten
- Höhere Anforderungen an Deployment-Reihenfolge: billing-hub muss vor Hubs starten
```

---

## 🟡 MITTLERE FINDINGS

### M-01 — `webhook_secret` auf Platform-Ebene vs. Stripe-Reality

**Befund:** Stripe unterstützt **einen** `STRIPE_WEBHOOK_SECRET` pro Webhook-Endpoint. Das Feld `Platform.webhook_secret` impliziert per-Platform-Secrets, was mit Stripe nicht direkt umzusetzen ist. Das Feld ist jedoch sinnvoll für **Hub-zu-Billing-Hub interne Calls** (nicht für Stripe). Das ADR muss diesen Doppelzweck klarstellen.

**Korrektur:** Umbenennen und dokumentieren:
```python
# Platform.webhook_secret → Platform.internal_api_secret
# Stripe Webhook Secret: settings.STRIPE_WEBHOOK_SECRET (ein globales Secret)
internal_api_secret = models.CharField(
    max_length=255,
    help_text="HMAC-Secret für Hub→BillingHub interne API-Calls"
)
```

---

### M-02 — `httpx` nicht im Platform-Stack definiert

**Befund:** Das ADR verwendet `httpx` ohne es als Dependency zu spezifizieren. Die Plattform nutzt bisher keinen vereinheitlichten HTTP-Client für Service-zu-Service Calls. `requests` ist in einigen Hubs bereits vorhanden.

**Empfehlung:** `httpx` ist die bessere Wahl (async-fähig, moderne API), aber muss explizit als **Platform-Standard für inter-service HTTP** in ADR-050 oder einem eigenen ADR definiert werden. Alternativ: `requests` mit Connection-Pooling.

---

### M-03 — Health-Endpoints nicht definiert

**Befund:** ADR-021 §2.3 und ADR-022 §2.4 fordern `/livez/` und `/healthz/` für jeden Hub. billing-hub erwähnt diese nicht.

**Korrektur:** Explizit in §5 aufnehmen:
```markdown
Health Endpoints:
- GET /livez/  → 200 (Prozess läuft)
- GET /healthz/ → 200 (DB, Redis, Stripe-API erreichbar) | 503
```

---

### M-04 — Keine Choices-Klassen für Status-Felder

**Befund:** `Subscription.tier`, `Subscription.status`, `ModulePurchase.reason` sind freie `CharField`s ohne `choices`. Das ist anfällig für Tippfehler und verhindert automatische Validierung.

**Korrektur:**
```python
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

class PurchaseReason(models.TextChoices):
    REDEEM_CODE = "redeem_code", "Einlösecode"
    MANUAL = "manual", "Manuell (Admin)"
    BUNDLE = "bundle", "Bundle-Kauf"
    BETA = "beta", "Beta-Tester"
    PARTNER = "partner", "Partner"
```

---

### M-05 — Revenue-Dashboard technisch unspezifiziert

**Befund:** §2.6 listet ein "Revenue-Dashboard" (MRR, Churn-Rate, Conversion-Funnel) ohne technische Spezifikation. Das ist entweder:
- Eine Django Admin Custom View (einfach, kein zusätzliches Tooling)
- Ein separates BI-Tool (Metabase, Redash)
- Stripe Dashboard (bereits vorhanden, kostenlos)

Für eine "Proposed" ADR sollte die Entscheidung getroffen oder explizit als offene Frage markiert sein.

**Empfehlung:** Für MVP → Stripe Dashboard (kein Code). Mittelfristig → dedizierter ADR für Analytics-Strategy.

---

## 🔵 NIEDRIGE FINDINGS

### N-01 — Fehlende `__str__` Methoden

Alle Modelle benötigen `__str__` für Django Admin Lesbarkeit:
```python
class Customer(models.Model):
    def __str__(self) -> str:
        return f"{self.email} ({self.name or 'kein Name'})"

class Subscription(models.Model):
    def __str__(self) -> str:
        return f"{self.customer.email} @ {self.platform.slug}: {self.tier}/{self.status}"
```

---

### N-02 — `Customer.stripe_customer_id` unique + null Edge Case

`unique=True` + `null=True` ist in PostgreSQL korrekt (NULLs gelten als ungleich in UNIQUE-Constraints), aber Django zeigt in Forms eine irreführende Validation. Explizit dokumentieren:
```python
stripe_customer_id = models.CharField(
    max_length=100,
    unique=True,
    null=True,
    blank=True,
    db_index=True,
    # PostgreSQL: multiple NULLs allowed in UNIQUE constraint
    help_text="Stripe Customer ID (cus_xxx). NULL vor erstem Kauf."
)
```

---

### N-03 — Keine `db_table` Definitionen

Alle Modelle sollten explizite `db_table` Namen haben, um spätere Namenskollisionen mit anderen Apps zu vermeiden:
```python
class Meta:
    db_table = "billing_customer"  # billing_platform, billing_subscription, etc.
```

---

### N-04 — `BillingEvent.platform` darf nicht `SET_NULL` sein

`BillingEvent` dient als Idempotenz-Guard. Bei `on_delete=SET_NULL` verliert man die Plattform-Zuordnung für historische Events, was Debugging und Reconciliation erschwert:
```python
platform = models.ForeignKey(
    Platform,
    on_delete=models.PROTECT,  # Plattformen nie löschen, nur deaktivieren
    null=True,
    blank=True,
)
```

---

## Architekturalternativen (Ergänzung zu §3)

Das ADR behandelt drei Alternativen. Zwei wichtige fehlen:

### A-04 — Stripe Billing Portal + Minimal Backend (nicht gewählt)

Stripe bietet ein gehostetes **Customer Portal** mit vollständiger Abo-Verwaltung. Kunden können dort selbst kündigen, upgraden, Zahlungsmethoden ändern. Die eigene Admin-UI wäre nur für Support-Overrides notwendig.

**Vorteil:** ~60% weniger Code im billing-hub MVP
**Nachteil:** Kein Cross-Platform-Bundle-Support, kein Custom-Branding ohne Paid Plan
**Empfehlung:** Für Phase 1 als temporäre Lösung evaluieren, bevor die eigene Admin-UI gebaut wird.

### A-05 — Lago (Open Source Metering & Billing, nicht gewählt)

[Lago](https://www.getlago.com/) ist ein Open-Source-Alternative zu Stripe Billing für komplexe Usage-Based-Billing-Szenarien.

**Relevant wenn:** Trading-Hub (Bot-Strategien) oder dev-hub (API-Zugang) usage-based abgerechnet werden sollen.
**Aktuell:** Overkill für subscription-based Modelle. Für zukünftige Evaluierung vormerken.

---

## Korrigiertes Datenmodell (vollständig)

```python
# apps/billing/models.py

from django.db import models
from django.utils import timezone


class BillingBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Platform(BillingBaseModel):
    slug = models.SlugField(unique=True, max_length=50, db_index=True)
    name = models.CharField(max_length=100)
    base_url = models.URLField()
    internal_url = models.URLField()
    internal_api_secret = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "billing_platform"

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"


class Customer(BillingBaseModel):
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    stripe_customer_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True, db_index=True
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

    def __str__(self) -> str:
        return f"{self.customer_id} @ {self.platform.slug}: {self.tier}/{self.status}"


class PurchaseReason(models.TextChoices):
    REDEEM_CODE = "redeem_code", "Einlösecode"
    MANUAL = "manual", "Manuell (Admin)"
    BUNDLE = "bundle", "Bundle-Kauf"
    BETA = "beta", "Beta-Tester"
    PARTNER = "partner", "Partner"


class ModulePurchase(BillingBaseModel):
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
        return f"{self.customer_id} → {self.platform.slug}/{self.module_id}"


class Invoice(BillingBaseModel):
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
        return f"{self.stripe_invoice_id}: {self.amount_cents/100:.2f} {self.currency}"


class BillingEvent(models.Model):
    """Idempotenz-Deduplication für Stripe-Webhooks. Nie löschen."""
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

---

## Zusammenfassung: Pflichtänderungen vor Freigabe

| # | Finding | Priorität | Aufwand |
|---|---------|-----------|---------|
| K-01 | Port 8020 → 8091 (ADR-021 aktualisieren) | 🔴 Blocker | 10 min |
| K-02 | Fail-open → Fail-closed mit Cache-Stufen | 🔴 Blocker | 2h |
| K-03 | HMAC-Auth für interne API | 🔴 Blocker | 3h |
| K-04 | Stripe-Webhook-Signatur + async (Celery) | 🔴 Blocker | 2h |
| K-05 | SlugField PK → BigAutoField + slug-Feld | 🔴 Blocker | 1h |
| H-01 | Subscription History (is_active statt unique_together) | 🟠 Hoch | 30 min |
| H-02 | updated_at auf allen Modellen | 🟠 Hoch | 15 min |
| H-03 | Async Webhook Pattern (Celery) | 🟠 Hoch | Mit K-04 |
| H-04 | DSGVO-Propagation spezifizieren | 🟠 Hoch | 1h (ADR) |
| H-05 | Datenbankindizes explizit | 🟠 Hoch | 30 min |
| H-06 | MADR Abschnitt 8 ergänzen | 🟠 Hoch | 30 min |

**Status nach Behebung aller Blocker und Hohen Findings: FREIGEGEBEN**

---

*Review erstellt nach MADR-4.0-Standard. Plattform-Referenzen: ADR-009, ADR-021, ADR-022, ADR-050.*
