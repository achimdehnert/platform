---
status: accepted
date: 2026-03-10
updated: 2026-03-11-v1.2
decision-makers: Achim Dehnert
---

# ADR-118: billing-hub als Platform Store

## Status

Accepted — v1.2 (2026-03-11, Follow-Up-Review Fixes)

## Context

Die IIL-Plattform besteht aus mehreren öffentlich zugänglichen Django-Hub-Anwendungen mit
unterschiedlichen Zielgruppen und Preismodellen:

| Repo | Domain | Zielgruppe | Modell |
|------|--------|------------|--------|
| `risk-hub` | schutztat.de | Arbeitsschutzbeauftragte (B2B) | Modul-Kauf |
| `ausschreibungs-hub` | bieterpilot.de | KMU, Baufirmen, Ingenieurbüros (B2B) | Starter/Pro/Enterprise |
| `pptx-hub` | prezimo.de | Agenturen, Unternehmen (B2B) | Subscription |
| `weltenhub` | weltenforger.com | Autoren, Kreative (B2C) | Free/Pro |
| `trading-hub` | — | Trader (B2C) | Subscription |
| `coach-hub` | — | Coaches (B2B/B2C) | Subscription |
| `wedding-hub` | — | Hochzeitsplaner (B2C) | Einmal/Subscription |

> **Hinweis:** `research-hub` (research.iil.pet) ist noch in der Konzeptphase ohne
> festes Preismodell. Wird nach Pilot-Validierung ergänzt, sobald das Modell steht.

Bisher gibt es keinen Self-Service-Registrierungsflow: neue User werden manuell per
Django-Admin angelegt. Das verhindert skalierbare Kundengewinnung.

### Abgewogene Alternativen

**Option A — SSO (Zentraler Identity Provider)**
- Keycloak, Auth0 oder django-oauth-toolkit als eigener Service
- Ein Account für alle IIL-Apps
- **Abgelehnt**: Hohe Komplexität, eigene Infrastruktur, Multi-Tenant-Isolation
  erschwert. Jede App hat eine andere Zielgruppe — gemeinsame Identität bringt
  keinen Mehrwert. GDPR: getrennte User-Stores sind einfacher zu begründen.

**Option B — Pro-App Registrierung (vollständig dezentral)**
- Jede App hat eigenen Signup-Flow und eigene Zahlungsabwicklung
- **Abgelehnt**: Stripe-Integration 8× implementieren, kein zentrales
  Subscription-Management, kein produktübergreifender Überblick.

**Option C — billing-hub als zentraler Store (gewählt)**
- Registrierung und Zahlung zentral auf `billing-hub`
- Jede App hat eigene Auth-DB (keine gemeinsame Identität)
- billing-hub aktiviert per internem API-Call nach Zahlung/Trial-Start

## Decision

**billing-hub ist der zentrale Platform Store.** Er übernimmt:
1. **Self-Service-Registrierung** für alle Produkte
2. **Stripe-Checkout** (Infrastruktur bereits vorhanden)
3. **Trial-Management** (14 Tage, per Celery Beat überwacht)
4. **Aktivierungs-Webhook** an die Ziel-App nach erfolgreicher Zahlung/Trial-Start

Jede Ziel-App bleibt **eigenständig** mit eigener User-DB und eigenem Auth-System.
Sie bekommt lediglich einen internen Aktivierungs-Endpoint.

### Registrierungs-Flow

```
User auf risk-hub / pptx-hub / weltenhub etc.
    → "Jetzt testen" / "Modul kaufen" Button
    → Redirect: billing.iil.pet/checkout?product=<repo>&plan=<plan>
    → billing-hub validiert product+plan gegen ProductCatalog
      (ungültig → Fehlerseite mit Link zur Produktübersicht)
    → Formular: E-Mail, Firmenname (bei B2B: USt-IdNr)
    → E-Mail-Verifikation (Bestätigungslink, billing-hub sendet via Celery)
    → Stripe Checkout Session (oder Trial ohne Zahlung)
    → Webhook: billing-hub → POST /api/internal/activate/ auf Ziel-App
    → Ziel-App legt Tenant + Admin-User an, sendet "Set Password"-Mail
    → User wird weitergeleitet: billing.iil.pet/success/?redirect=<app-url>
```

**E-Mail-Verifikation:** billing-hub verifiziert die E-Mail **vor** dem
activate-Call. Kein activate ohne bestätigte E-Mail. Verhindert Spam-Tenants.

**Passwort-Handling:** billing-hub speichert **kein Passwort** des Users.
Die Ziel-App generiert beim activate-Call einen Admin-User mit zufälligem
Passwort und sendet eine "Set Password"-Mail über ihren eigenen E-Mail-Service.
So bleibt jede App eigenständig in ihrer Auth-DB.

### billing-hub: Neue Komponenten

```python
# apps/catalog/models.py
class Product(models.Model):
    repo = models.CharField(max_length=50)                      # z.B. "risk-hub"
    name = models.CharField(max_length=200)                     # z.B. "Schutztat Professional"
    plan_key = models.CharField(max_length=50)                  # z.B. "professional"
    price_monthly_eur = models.DecimalField(max_digits=8, decimal_places=2)
    trial_days = models.PositiveIntegerField(default=14)
    activate_url = models.URLField()                            # https://schutztat.de/api/internal/activate/
    deactivate_url = models.URLField()                          # https://schutztat.de/api/internal/deactivate/
    stripe_price_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["repo", "plan_key"]

class Subscription(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    email = models.EmailField()
    email_verified = models.BooleanField(default=False)
    tenant_id = models.UUIDField(unique=True, default=uuid.uuid4)  # sekundärer Identifier, NICHT PK
    status = models.CharField(max_length=20, choices=[
        ("pending", "Pending"),         # E-Mail noch nicht verifiziert
        ("trial", "Trial"),
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ], default="pending")
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

> **Hinweis:** `tenant_id` ist ein `UUIDField(unique=True)` als **sekundärer Identifier**
> für die Inter-Service-Kommunikation. Der Primärschlüssel bleibt `BigAutoField`
> (Platform-Konvention / ADR-022). In der Ziel-App ebenfalls: `tenant_id = UUIDField(unique=True)`,
> niemals als `primary_key=True`.

### Ziel-App: Aktivierungs-Endpoint (Standard)

```python
# POST /api/internal/activate/
# Auth: HMAC-Signatur (siehe Security-Abschnitt)
# Response: 201 Created | 200 OK (idempotent) | 400 Bad Request | 403 Forbidden

{
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@firma.de",
    "plan": "professional",
    "modules": ["ex", "risk", "dsb"],   # optional, repo-spezifisch
    "trial_ends_at": "2026-03-24T00:00:00Z"
}
```

**Idempotenz:** Bei erneutem Aufruf mit gleicher `tenant_id` wird kein zweiter
Tenant angelegt. Response: `200 OK` mit bestehenden Daten. Kein `409 Conflict`.

**Reaktivierung:** Ein zuvor deaktivierter Tenant wird durch erneuten activate-Call
reaktiviert (Status: Read-Only → Active). Ein separater `/reactivate/`-Endpoint ist
nicht nötig — activate ist idempotent und deckt Neuanlage + Reaktivierung ab.

### Ziel-App: Deaktivierungs-Endpoint (Standard)

```python
# POST /api/internal/deactivate/
# Auth: HMAC-Signatur (siehe Security-Abschnitt)
# Response: 200 OK | 404 Not Found | 403 Forbidden

{
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "reason": "trial_expired"   # trial_expired | cancelled | payment_failed
}
```

**Verhalten bei Deaktivierung:**
- Tenant wird auf **Read-Only** gesetzt (Soft-Deactivate, kein Datenverlust)
- User können sich einloggen und Daten exportieren, aber nicht mehr bearbeiten
- Daten werden **nicht gelöscht** — Reaktivierung bei Zahlung möglich
- Nach 90 Tagen ohne Reaktivierung: GDPR-Löschung (separater Celery-Job)

### Security: Defense-in-Depth

Die internen Endpoints `/api/internal/activate/` und `/api/internal/deactivate/`
werden durch **drei Schutzschichten** gesichert:

**1. HMAC-Signatur (primär)**

billing-hub signiert jeden Request mit HMAC-SHA256 über den Request-Body + Timestamp:

```python
# billing-hub (Sender)
import hmac, hashlib, time, json

def sign_request(payload: dict, secret: str) -> dict:
    timestamp = str(int(time.time()))
    body = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    return {"X-Billing-Timestamp": timestamp, "X-Billing-Signature": signature}

# Ziel-App (Empfänger) — prüft Signatur + Timestamp (max 5 min alt)
def verify_request(request, secret: str) -> bool:
    timestamp = request.headers.get("X-Billing-Timestamp", "")
    signature = request.headers.get("X-Billing-Signature", "")
    if abs(time.time() - int(timestamp)) > 300:  # max 5 min
        return False
    body = request.body.decode()
    expected = hmac.new(
        secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

Env-Variable: `BILLING_HMAC_SECRET` — ein shared Secret zwischen billing-hub
und der jeweiligen Ziel-App. Konfiguriert via `decouple.config('BILLING_HMAC_SECRET')`
in beiden Apps. Jede Ziel-App hat denselben Secret-Wert wie billing-hub.

**Secret-Rotation:** Dual-Secret-Support während Übergang. Ziel-App akzeptiert
für 24h sowohl altes als auch neues Secret. Reihenfolge: (1) neues Secret in
Ziel-App deployen, (2) neues Secret in billing-hub deployen, (3) altes Secret
nach 24h entfernen.

**2. Rate-Limiting**

`django-ratelimit` auf den internen Endpoints: **10 Requests/Minute** pro IP.
Verhindert Brute-Force auch bei kompromittiertem Secret.

**3. Netzwerk-Isolation**

Auf dem Hetzner-Server laufen alle Apps im selben Docker-Netzwerk. Die internen
Endpoints binden auf `127.0.0.1` und sind **nicht** von außen erreichbar.
Nginx leitet `/api/internal/*` nur von localhost weiter.

### Trial-Ablauf

```
billing-hub Celery Beat (täglich, 02:00 UTC):
    → Subscriptions mit trial_ends_at < now() + 3 days, status=trial
        → Reminder-Mail an User ("Trial endet in 3 Tagen")
    → Subscriptions mit trial_ends_at < now(), status=trial
        → Status = expired
        → POST /api/internal/deactivate/ an Ziel-App (reason=trial_expired)
        → Bei Fehler: Retry mit exponential backoff (3 Versuche über 24h)
```

**Fallback bei Ziel-App-Ausfall:** Deactivate-Calls werden über eine Celery-Queue
mit exponential backoff (1h, 4h, 24h) wiederholt. Nach 3 Fehlversuchen: Alert an
Ops-Channel (Discord via mcp-hub) + manueller Eingriff.

### Referenz-Implementierung

`ausschreibungs-hub` hat bereits `apps/core/plan_gates.py` und `apps/core/billing.py`
mit Plan-Tier-Logik (Starter/Professional/Enterprise). Diese Implementierung gilt als
**Referenz** für alle anderen Repos.

## Consequences

### Positiv
- Stripe nur einmal integriert (billing-hub)
- Zentrales Subscription-Dashboard für IIL-intern (Umsatz, Trials, Churns)
- Jede App bleibt einfach und eigenständig
- ausschreibungs-hub bereits konform — minimaler Aufwand dort
- E-Mail-Verifikation verhindert Spam-Tenants

### Negativ / Risiken
- billing-hub wird **Single Point of Failure für Neuregistrierungen** — Ausfall
  blockiert keine bestehenden User, aber neue Anmeldungen. Mitigation: Health-Monitoring,
  Celery-Retry-Queue für fehlgeschlagene activate/deactivate-Calls.
- Jede App muss `/api/internal/activate/` + `/api/internal/deactivate/` implementieren
  (einmalig, überschaubar — Standard-Template wird bereitgestellt)
- HMAC-Secret-Rotation erfordert koordinierten Deploy (Dual-Secret löst das)

### Nicht in Scope dieses ADR
- SSO / geteilte Sessions zwischen Apps
- Wiederverwendung von User-Accounts über Apps hinweg
- App-übergreifende Rollen/Permissions
- research-hub Integration (eigenes ADR nach Preismodell-Festlegung)

## Pilot

**risk-hub** ist der Pilot-Repo für diesen Flow:
1. billing-hub: `Product` für risk-hub anlegen (Module: ex, risk, dsb, gbu, brandschutz)
2. risk-hub: `POST /api/internal/activate/` + `/deactivate/` implementieren
3. risk-hub Landing-Page: "Jetzt testen"-Button → billing.iil.pet
4. End-to-End Test mit Stripe-Testmodus
5. HMAC-Signatur-Verifikation testen (Happy Path + Replay-Schutz)

## Betroffene Repos

- `billing-hub` — Hauptimplementierung (ProductCatalog, Checkout, Webhooks, HMAC-Signing)
- `risk-hub` — Pilot (activate/deactivate-Endpoint + Landing-Page-Button)
- `ausschreibungs-hub` — bereits konform, Migration auf HMAC + Standard-Endpoints
- alle anderen Hub-Repos — folgen nach Pilot-Validierung

## Review-History

| Datum | Version | Reviewer | Urteil | Link |
|-------|---------|----------|--------|------|
| 2026-03-11 | v1.0 → v1.1 | Cascade | ❌ → Fixes applied | [Review](../reviews/ADR-118-review-2026-03-11.md) · [Issue #23](https://github.com/achimdehnert/platform/issues/23) |
| 2026-03-11 | v1.1 → v1.2 | Cascade | ✅ APPROVED WITH COMMENTS → Fixes applied | Follow-Up: unique-Bug, verify_request(), Reaktivierung, URL-Validierung |
