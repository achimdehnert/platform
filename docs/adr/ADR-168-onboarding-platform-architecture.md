---
id: ADR-168
title: "Build Onboarding-Platform as separate repo on coach-hub primitives with billing-hub Stripe pattern"
status: proposed
date: 2026-04-21
amended: 2026-04-21
decision-makers: [achimdehnert]
consulted: []
informed: []
scope: onboarding-platform
product_name: Schulungspass
domains: [schulungspass.de, schulungspass.com]
implementation_status: none
---

<!-- Drift-Detector-Felder
staleness_months: 3
drift_check_paths:
  - "onboarding-hub/apps/onboarding/"
  - "onboarding-hub/apps/billing/"
  - "onboarding-hub/config/settings/"
supersedes_check: null
-->

# ADR-168: Build Onboarding-Platform as separate repo on coach-hub primitives with billing-hub Stripe pattern

## Context and Problem Statement

The Compliance-Onboarding-Platform ("onboarding-hub") needs a technical home. The product is a
white-label SaaS for SME onboarding and mandatory compliance trainings (Pflichtunterweisungen).
~70 % of required primitives exist in coach-hub (Multi-Tenant, RBAC, TenantBranding, LearningModule,
LearningProgress, AssessmentTemplate, WeasyPrint certificates, AuditLog).

Stripe subscription billing is already fully implemented in billing-hub (`apps/store/services.py`:
`create_stripe_checkout`, Webhook handling, `ProductPlan` with `stripe_price_id`).

Three structural options exist: extend coach-hub in-place, fork coach-hub, or create a new repo
that selectively copies proven patterns, or extract coach-hub as an installable package.

## Decision Drivers

- Time-to-MVP: 6–8 weeks target — avoid architectural overhead
- coach-hub is a production system (iil.pet) — no interference with live product
- Stripe subscription logic must be reused, not duplicated from scratch
- Product must be independently deployable and brandable (own domain, own Docker image)
- Multi-Tenant isolation is non-negotiable (row-level `tenant_id` on all models)
- billing-hub Stripe pattern (service layer, Webhook with signature validation) is battle-tested
- Platform CI/CD conventions must apply (`_ci-python.yml`, `_deploy-unified.yml`, ADR-166)
- ADR-167 3-Tier Middleware Standard: `HealthBypassMiddleware` + `SubdomainTenantMiddleware`

## Considered Options

1. **Separate repo `onboarding-hub`** — new repo, copy proven patterns from coach-hub + billing-hub
2. **Extend coach-hub in-place** — add `apps.onboarding` + `apps.ob_billing` directly to coach-hub
3. **Fork coach-hub** — full fork, customize for onboarding product
4. **coach-hub as installable package** — publish coach-hub primitives as pip package, import in new repo

## Decision Outcome

Chosen option: **1. Separate repo `onboarding-hub`**

Rationale:
- coach-hub runs a live production system — adding onboarding development directly risks destabilizing iil.pet (Option 2)
- Forking creates permanent divergence maintenance burden and doubles CI surface (Option 3)
- Publishing coach-hub as package requires ~2 weeks packaging work before any product feature can be built (Option 4)
- Separate repo gives clean separation of concerns, independent CI/CD, own Docker image, own port

## Pros and Cons of the Options

### Option 1 — Separate repo `onboarding-hub` ✅ Chosen

- **Good:** coach-hub production unberührt; eigenständiger Release-Zyklus; klares Ownership
- **Good:** Stripe-Pattern aus billing-hub 1:1 übertragbar
- **Good:** Standard-Platform-CI sofort anwendbar
- **Bad:** ~2–3 Tage initialer Setup-Aufwand
- **Bad:** Code-Duplizierung bei Bugfixes in geteilten Primitives; keine automatische Synchronisierung mit coach-hub

### Option 2 — Extend coach-hub in-place

- **Good:** Null Setup-Aufwand; sofortiger Zugriff auf alle Primitives
- **Bad:** Jeder Onboarding-Bug kann iil.pet destabilisieren (shared Migrations, SETTINGS, DB)
- **Bad:** Strikte Trennung von iil.pet-Content und Compliance-Produkt-Branding nicht möglich
- **Bad:** Unterschiedliche Deployment-Frequenzen (iil.pet vs. KMU-Kunden) erzwingen übergreifende Releases

### Option 3 — Fork coach-hub

- **Good:** Voller Zugriff auf alle Primitives ohne Extraktion
- **Bad:** Sofortige Divergenz — upstream Bugfixes müssen manuell gemergt werden
- **Bad:** Zwei vollständige CI-Pipelines für unterschiedliche Produkte aus derselben Codebasis

### Option 4 — coach-hub als installable package

- **Good:** Sauberstes Architektur-Muster langfristig; kein Code-Duplikat
- **Bad:** ~2 Wochen Packaging-Overhead (pyproject.toml, öffentliches/privates PyPI, Versioning) vor erstem Feature
- **Bad:** Zwingt coach-hub-Team zu stabiler Public API — zu früh im Produktzyklus

## Consequences

### Good

- Eigenständiges Docker-Image `ghcr.io/achimdehnert/onboarding-hub`
- Stripe-Billing-Pattern aus battle-tested billing-hub übernommen (inkl. Webhook-Signatur-Validierung)
- Standard Platform CI/CD (`_deploy-unified.yml`) sofort anwendbar
- Unabhängige Skalierbarkeit und Deployments; Port **8108** (ADR-021 §2.9)
- Klare Trennung: iil.pet (coach-hub) vs. Compliance-Plattform (onboarding-hub)
- ADR-167 Tier-2-Middleware-Stack von Anfang an korrekt eingebaut

### Bad

- Code-Duplizierung bei Bugfixes in geteilten Primitives (kein shared package)
- Zukünftige Divergenz zwischen coach-hub und onboarding-hub bei gemeinsamen Patterns möglich
- Wartung von 2 Stripe-Implementierungen bis billing-hub als shared library refactored wird (Roadmap-Item, kein Blocker)

### Neutral

- Produkt-Name: **Schulungspass** — Domains `schulungspass.de` + `schulungspass.com` gesichert (2026-04-21)
- Repo-Name `onboarding-hub` bleibt technischer Name; Produktname `Schulungspass` für Branding
- Stripe-Account-Frage (IIL GmbH vs. neue Gesellschaft) ist separate Entscheidung

## Architecture

### Repo-Struktur

```
onboarding-hub/
├── apps/
│   ├── core/          ← Tenant, TenantBranding, RBAC (aus coach-hub, bereinigt)
│   ├── content/       ← ContentModule, Quiz, Progress (aus coach-hub LearningModule adaptiert)
│   ├── onboarding/    ← OnboardingTrack, TrackStep, Invitation, Enrollment, Certificate
│   ├── billing/       ← TenantSubscription, SubscriptionPlan, Stripe (aus billing-hub)
│   ├── recert/        ← RecertificationSchedule, Delta-Detection (Phase 2)
│   └── partner/       ← ContentPartner, Payout (Phase 2)
├── config/settings/   ← base.py / prod.py / test.py
├── docker/app/Dockerfile   ← Multi-Stage, python:3.12-slim, USER app:1000
├── docker-compose.prod.yml
├── catalog-info.yaml       ← Platform-Katalog (ADR-167/ADR-166 Pflicht)
├── .ship.conf              ← SSOT: IMAGE, PORT=8108, HEALTH_URL (ADR-166)
└── .github/workflows/      ← ci.yml (_ci-python.yml) + deploy.yml (_deploy-unified.yml)
```

### ADR-167 Middleware-Stack (Tier 2 — Subdomain RLS)

`onboarding-hub` ist ein **Tier-2-Repo** nach ADR-167 (Subdomain → `tenant_id`-RLS,
kein django-tenants Schema-Isolation). Pflicht-Reihenfolge:

```python
MIDDLEWARE = [
    "platform_context.middleware.HealthBypassMiddleware",     # Tier 1 — ADR-167 FIRST
    "platform_context.middleware.SubdomainTenantMiddleware",  # Tier 2 — acme.<domain> → tenant
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

Abhängigkeit: `iil-platform-context >= 0.7.0`

### Stripe-Pattern (aus billing-hub, mit Sicherheits-Fix)

```python
# apps/billing/services.py
def create_stripe_checkout(plan: SubscriptionPlan, tenant: Tenant, base_url: str) -> str:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=tenant.admin_email,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=f"{base_url}/billing/success/?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}/billing/cancel/",
    )
    return session.url

# apps/billing/views.py — Webhook MIT Signatur-Validierung (Pflicht!)
@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)
    # process event.type ...
    return HttpResponse(status=200)
```

`STRIPE_WEBHOOK_SECRET` via `decouple.config()` aus `/opt/shared-secrets/api-keys.env` (ADR-159).

### Datenbank

Eigene PostgreSQL-16-Instanz im `docker-compose.prod.yml` (kein shared DB mit anderen Hubs).
Migrations-Strategie: **Expand-Contract** für alle Schema-Änderungen in Produktion.

### Docker-Konventionen (Pflicht)

```dockerfile
# docker/app/Dockerfile — Multi-Stage, Non-Root
FROM python:3.12-slim AS runtime
RUN groupadd -g 1000 app && useradd -u 1000 -g app app
USER app
# KEIN HEALTHCHECK im Dockerfile — ausschließlich in docker-compose.prod.yml (ADR-167/coach-hub Incident)
```

```yaml
# docker-compose.prod.yml
services:
  web:
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8108/livez/')"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Port-Registrierung

Port **8108** in `platform/docs/adr/ADR-021-unified-deployment-pattern.md` §2.9 eintragen.
`.ship.conf`: `PORT=8108`, `HEALTH_URL=http://localhost:8108/livez/`

### Runner-Registration

Vor erstem CI-Lauf: Self-Hosted Runner für `onboarding-hub` auf `88.198.191.108` registrieren
(analog zu den 21 existierenden Runner-Services, ADR-Runner-Architektur).

### Offene Fragen

1. **Custom Domain (schulungspass.de):** Phase 1 nutzt Nginx (ADR-021 §2.10) mit Let's Encrypt.
   Traefik/Caddy für White-Label-Subdomains wird in Phase 4 als eigenes ADR entschieden.
2. **Stripe-Account:** IIL GmbH oder neue Gesellschaft — separate Entscheidung vor Phase 1.

## Confirmation

ADR als `implemented` gilt wenn:
- `achimdehnert/onboarding-hub` Repo existiert mit Repo-Struktur laut §Architecture
- `iil-platform-context >= 0.7.0` als Dependency + Tier-2-Middleware-Stack aktiv
- CI-Pipeline (`_ci-python.yml`) grün (lint, test, build)
- `/livez/` antwortet `200 ok` ohne DB-Zugriff; `/healthz/` prüft DB + Cache
- Stripe Checkout Session + Webhook-Signatur-Validierung im Test-Modus erfolgreich
- Port 8108 in ADR-021 §2.9 registriert
- Self-Hosted Runner auf Server registriert
- `catalog-info.yaml` vorhanden und valide

## More Information

- Konzept-Dokument: `konzept-onboarding-portal-v2.md` (2026-04-21)
- coach-hub Primitives: `achimdehnert/coach-hub`
- billing-hub Stripe Pattern: `achimdehnert/billing-hub/apps/store/services.py`
- ADR-021: Port-Governance, Deploy-Konventionen, Nginx-Standard
- ADR-041: Service Layer (Views → Services → Models)
- ADR-045: `decouple.config()`, kein `os.environ`
- ADR-159: Shared Secrets `/opt/shared-secrets/api-keys.env`
- ADR-166: `.ship.conf` SSOT
- ADR-167: 3-Tier Middleware Standard (`HealthBypassMiddleware`, `SubdomainTenantMiddleware`)
