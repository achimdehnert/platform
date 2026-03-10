# ADR-118: Platform Store — billing-hub als zentraler Registrierungs- und Zahlungspunkt

## Status

Accepted — v1.0 (2026-03-10)

## Context

Die IIL-Plattform besteht aus mehreren öffentlich zugänglichen Django-Hub-Anwendungen mit
unterschiedlichen Zielgruppen und Preismodellen:

| Repo | Domain | Zielgruppe | Modell |
|------|--------|------------|--------|
| `risk-hub` | schutztat.de | Arbeitsschutzbeauftragte (B2B) | Modul-Kauf |
| `ausschreibungs-hub` | bieterpilot.de | KMU, Baufirmen, Ingenieurbüros (B2B) | Starter/Pro/Enterprise |
| `pptx-hub` | prezimo.de | Agenturen, Unternehmen (B2B) | Subscription |
| `weltenhub` | weltenforger.com | Autoren, Kreative (B2C) | Free/Pro |
| `research-hub` | research.iil.pet | Autoren, Kreative (B2C) | Free/Pro |
| `trading-hub` | — | Trader (B2C) | Subscription |
| `coach-hub` | — | Coaches (B2B/B2C) | Subscription |
| `wedding-hub` | — | Hochzeitsplaner (B2C) | Einmal/Subscription |

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
    → Formular: E-Mail, Passwort, Firmenname (bei B2B: USt-IdNr)
    → Stripe Checkout Session (oder Trial ohne Zahlung)
    → Webhook: billing-hub → POST /api/internal/activate/ auf Ziel-App
    → Ziel-App legt Tenant + User an, aktiviert Module/Plan
    → User wird weitergeleitet: billing.iil.pet/success/?redirect=<app-url>
```

### billing-hub: Neue Komponenten

```python
# apps/catalog/models.py
class Product(models.Model):
    repo         # z.B. "risk-hub", "pptx-hub"
    name         # z.B. "Schutztat Professional"
    plan_key     # z.B. "professional", "starter", "pro"
    price_monthly_eur
    trial_days   # default: 14
    activate_url # z.B. https://schutztat.de/api/internal/activate/
    stripe_price_id

class Subscription(models.Model):
    product
    email
    tenant_id    # UUID, billing-hub generiert und übergibt
    status       # trial | active | cancelled | expired
    trial_ends_at
    stripe_subscription_id
```

### Ziel-App: Aktivierungs-Endpoint (Standard)

```python
# POST /api/internal/activate/
# Auth: BILLING_INTERNAL_SECRET Header
{
    "tenant_id": "<uuid>",
    "email": "<email>",
    "plan": "professional",
    "modules": ["ex", "risk", "dsb"],   # optional, repo-spezifisch
    "trial_ends_at": "2026-03-24T00:00:00Z"
}
```

Jede App implementiert diesen Endpoint. `BILLING_INTERNAL_SECRET` ist bereits
in allen Apps als Env-Variable vorgesehen.

### Trial-Ablauf

```
billing-hub Celery Beat (täglich):
    → Subscriptions mit trial_ends_at < now() + 3 days → Reminder-Mail
    → Subscriptions mit trial_ends_at < now() → Status = expired
    → POST /api/internal/deactivate/ an Ziel-App
```

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

### Negativ / Risiken
- billing-hub wird kritische Infrastruktur — Ausfall blockiert Neuregistrierungen
- Jede App muss `/api/internal/activate/` implementieren (einmalig, überschaubar)
- Bei sehr vielen Produkten: ProductCatalog-Pflege in billing-hub

### Nicht in Scope dieses ADR
- SSO / geteilte Sessions zwischen Apps
- Wiederverwendung von User-Accounts über Apps hinweg
- App-übergreifende Rollen/Permissions

## Pilot

**risk-hub** ist der Pilot-Repo für diesen Flow:
1. billing-hub: `Product` für risk-hub anlegen (Module: ex, risk, dsb, gbu, brandschutz)
2. risk-hub: `POST /api/internal/activate/` implementieren
3. risk-hub Landing-Page: "Jetzt testen"-Button → billing.iil.pet
4. End-to-End Test mit Stripe-Testmodus

## Betroffene Repos

- `billing-hub` — Hauptimplementierung (ProductCatalog, Checkout, Webhooks)
- `risk-hub` — Pilot (activate-Endpoint + Landing-Page-Button)
- `ausschreibungs-hub` — bereits konform, ggf. minimize auf Standard-Endpoint
- alle anderen Hub-Repos — folgen nach Pilot-Validierung
