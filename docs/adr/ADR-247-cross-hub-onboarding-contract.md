---
id: ADR-247
title: "Cross-Hub Onboarding-Contract: billing-hub → Produkt-Hub Auto-Login (HMAC + Magic-Link)"
status: proposed
decision_date: 2026-06-17
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh, meiki-lra, ttz-lif]
domains: [billing, onboarding, auth, tenancy, cross-repo]
supersedes: []
amends: []
depends_on: []
related: [ADR-156, ADR-157]
tags: [billing, onboarding, magic-link, hmac, cross-repo, security]
scope:
  include_paths:
    - "docs/adr/ADR-247-*"
---

# ADR-247 — Cross-Hub Onboarding-Contract: billing-hub → Produkt-Hub Auto-Login (HMAC + Magic-Link)

## 1. Kontext

Mit dem Lizenzprodukt kauft ein Kunde in **billing-hub** (Stripe-Checkout / Trial) ein
Abo und soll **ohne manuellen zweiten Schritt** im jeweiligen Produkt-Hub (zuerst
**risk-hub**) landen — bereits eingeloggt, im richtigen Tenant, mit den zum Plan
gehörenden Modulen.

In der Session 2026-06-16 wurde dieser Fluss erstmals end-to-end gebaut und live
geschaltet. Er scheiterte in Produktion **hop-für-hop** an Integrationspunkten, die
zwischen zwei getrennt deployten Hubs liegen und in keinem einzelnen Repo vollständig
sichtbar sind:

1. **Netz/DNS** — getrennte Compose-Projekte = getrennte Docker-Netze; der interne
   `activate`-Call von billing → risk-hub war nicht auflösbar, bis beide am geteilten
   externen Netz `bf_platform_prod` hingen.
2. **Auth** — der interne API-Call ist HMAC-geschützt: billing `Platform.internal_api_secret`
   MUSS gleich risk-hub `BILLING_HMAC_SECRET` sein; ein `HttpBearer` erwartet zwingend den
   `Authorization`-Header.
3. **ALLOWED_HOSTS** — der interne Container-Hostname (`risk-hub-web`) musste in
   risk-hubs `ALLOWED_HOSTS`, sonst `DisallowedHost` (400).
4. **Tenant-Routing** — nach Magic-Login muss `user.tenant_id` gesetzt sein, damit die
   `SubdomainTenantMiddleware` auf Base-Domain/localhost den Tenant auflöst (sonst
   Dashboard-Loop).
5. **Plan-Taxonomie** — die Modul-Registry im Produkt-Hub keyt auf `ProductPlan.slug`
   (`starter`/`professional`/`business`), **nicht** auf den billing-Tier
   (`registered`/`premium`/`enterprise`). Falscher Wert → leere Module.

Diese fünf Punkte sind ein **impliziter Vertrag** zwischen zwei Repos. Heute ist er
nirgends als Contract dokumentiert — er wurde reaktiv in Prod entdeckt (User-Kritik:
„viele vermeidbare Schleifen"). Ohne Festschreibung wiederholt sich das beim **nächsten
Produkt-Hub** (cad-hub, coach-hub, …), der denselben Onboarding-Fluss anbindet.

## 2. Entscheidung

Der **Cross-Hub Onboarding-Contract** wird als verbindliche Schnittstelle festgeschrieben.
Jeder Produkt-Hub, der billing-getriebenes Auto-Login-Onboarding anbietet, implementiert
exakt diese fünf Hops; billing-hub ruft sie einheitlich auf.

**2.1 Internal Activation API (Produkt-Hub stellt bereit)**
- Endpoint `POST /api/v1/internal/billing/activate`, geschützt per **HMAC-Bearer**
  (`Authorization: Bearer <secret>`); Secret-Quelle: ein einziges gemountetes Secret,
  identisch auf beiden Seiten (billing `internal_api_secret` == hub `BILLING_HMAC_SECRET`).
- Request-Contract: `{ tenant_id: UUID, email: str, plan: <slug> }` — `plan` ist der
  **Hub-seitige ProductPlan-Slug**, nicht der billing-Tier. billing mappt Tier→Slug
  **vor** dem Call (`metadata.plan_slug`).
- Response: `{ login_token: <signed>, ... }`. `activate` legt/aktualisiert den User,
  **setzt `user.tenant_id`** und gewährt die Plan-Module.

**2.2 Magic-Link Auto-Login (Produkt-Hub stellt bereit)**
- `GET /auth/magic/?token=<login_token>` validiert den kurzlebigen, **einmaligen**
  Token und routet in das Tenant-Dashboard. Single-Use ist Pflicht (Token steht in der
  URL → Log/Referer-Leak); Bindung an einen serverseitig nach Login wechselnden Wert
  (z. B. `last_login`), kein prozess-lokaler Cache-Marker (Multi-Worker-Korrektheit).
- billing redirectet nach erfolgreicher Provisionierung auf
  `{hub.base_url}/auth/magic/?token=<login_token>`.

**2.3 Netz & Hosts (Deploy-Vertrag)**
- billing-hub und Produkt-Hub teilen das externe Netz **`bf_platform_prod`** (Container↔
  Container-Auflösung des internen `activate`-Calls).
- Der **interne Container-Hostname** des Produkt-Hubs steht in dessen `ALLOWED_HOSTS`.

## 3. Betrachtete Alternativen

- **OIDC/SSO-Redirect statt Magic-Link** — schwergewichtiger, erzwingt einen interaktiven
  IdP-Schritt direkt nach dem Kauf (genau der Bruch, den wir vermeiden wollen). Auto-Login
  per signiertem Einmal-Token ist für den Post-Purchase-Moment leichter und ausreichend.
- **Shared Session/Cookie über Domain-Grenze** — scheitert an getrennten Domains
  (billing.iil.pet vs schutztat.de) und Cookie-Scope; verwirft sich selbst.
- **Kein Contract, weiter pro Hub ad-hoc** — der Status quo, der die hop-für-hop-Schleifen
  erzeugt hat. Verworfen.

## 4. Begründung im Detail

Der Wert liegt nicht in neuem Code, sondern in der **Vorab-Prüfbarkeit**: Alle fünf Hops
sind eine Checkliste, die ein anbindender Hub VOR „fertig" abhakt (Pre-Flight-Audit statt
reaktiver Prod-Debug). Das ist die direkte Umsetzung der Session-Lehre
(`feedback_cross_system_preflight_and_verified_claims`).

## 5. Implementation Plan

- risk-hub: bereits live (Referenz-Implementierung) — `tenancy/internal_api.py::activate`,
  `tenancy/magic.py`, `/auth/magic/`-Route, Middleware-Exemption (eng auf `/auth/magic/`).
- Single-Use des Magic-Tokens: risk-hub PR #208.
- billing-hub: Tier→Slug-Mapping in `store/services.py` (`plan_slug` in Stripe-Metadata),
  `Authorization`-Header im `_call_platform`.
- Nächster Hub: diese ADR als Anbinde-Checkliste verwenden.

## 6. Risiken

- **Secret-Drift** zwischen den Hubs → 401; Mitigation: ein einziges gemountetes Secret,
  per SHA-Hash verglichen, nie zwei Quellen.
- **Token-Leak** (URL in Logs) → Single-Use + kurze TTL (15 min) begrenzt das Fenster.
- **Plan-Slug-Mapping** divergiert von der Hub-Registry → leere Module; Mitigation:
  Mapping-Test je Plan im Produkt-Hub.

## 7. Konsequenzen

- (+) Nächster Produkt-Hub bindet in Stunden statt in einer Prod-Debug-Schleife an.
- (+) Sicherheits-Surface (HMAC, Single-Use, ALLOWED_HOSTS) ist explizit statt implizit.
- (−) Zwei Hubs müssen ein gemeinsames Secret + Netz koordinieren (Deploy-Kopplung).

## 8. Validation Criteria

- Ein neuer Hub kann allein anhand dieser ADR end-to-end anbinden (kein Prod-Hop-Debug).
- E2E-Test spiegelt das Prod-Wiring (gleiche internal_url-Form, Host, Secret-Quelle, Netz),
  sonst gilt „grün" nicht als Prod-Abdeckung.

## 9. Glossar

- **Tier** — billing-seitige Abo-Stufe (`registered/premium/enterprise`).
- **Plan-Slug** — Hub-seitiger `ProductPlan.slug` (`starter/professional/business`), Key der Modul-Registry.

## 10. Referenzen

- risk-hub: `tenancy/internal_api.py`, `tenancy/magic.py`, PR #205/#208.
- billing-hub: `store/services.py`, `services/subscription_service.py`.
- Memory: `feedback_cross_system_preflight_and_verified_claims`.

## 11. Changelog

- 2026-06-17: Initial (proposed) — aus session-retro 2026-06-17 (Finding #1, Magic-Link
  hop-für-hop in Prod).
