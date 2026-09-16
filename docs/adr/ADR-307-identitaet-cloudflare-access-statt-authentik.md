---
id: ADR-307
title: "Identität über Cloudflare Access und lokales Login — Ablösung von Authentik (ADR-142)"
status: proposed
decision_date: 2026-09-16
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [Repo-Owner dev-hub, writing-hub, trading-hub, weltenhub, 137-hub, risk-hub, cad-hub, research-hub]
supersedes: [ADR-142]
amends: []
related: [ADR-102, ADR-118, ADR-198, ADR-264, ADR-292]
repo: platform
implementation_status: none
last_reviewed: 2026-09-16
staleness_months: 6
drift_check_paths:
  - infra/ports.yaml
---

<!--
  ADR-307 — Basis: docs/templates/adr-template.md v2.1
-->

# ADR-307: Identität über Cloudflare Access und lokales Login — Ablösung von Authentik (ADR-142)

## Metadaten

| Attribut | Wert |
|---|---|
| **Status** | Proposed |
| **Scope** | platform (cross-repo) |
| **Erstellt** | 2026-09-16 |
| **Autor** | Achim Dehnert (Entscheid), Claude Code (Entwurf) |
| **Reviewer** | – (Challenger-Lauf steht aus) |
| **Supersedes** | ADR-142 (Unified Identity — Authentik als Platform-IdP) |
| **Relates to** | ADR-102 (Cloudflare DNS/CDN), ADR-118, ADR-198 (Staging Edge), ADR-292 (Two-Lane Deployment) |
| **Auslöser** | Owner-Entscheid 2026-09-16, Kapitäns-Kanal: „wir verwenden authentik nicht mehr → statt dessen cloudflare“ (platform#3256, aus der Sichtung #3226 E4) |

## Repo-Zugehörigkeit

| Repo | Rolle | Betroffene Pfade / Komponenten |
|---|---|---|
| `platform` | Primär | `docs/adr/`, `infra/ports.yaml` (`authentik`, `id.iil.pet`), `registry/`, Betriebsakten |
| `dev-hub`, `writing-hub`, `trading-hub`, `weltenhub`, `137-hub` | Primär | `mozilla_django_oidc`-Konfiguration, Login-Routen (**live gegen `id.iil.pet`**, gemessen 2026-09-16) |
| `risk-hub`, `cad-hub`, `research-hub`, `illustration-hub`, `pptx-hub`, `travel-beat`, `wedding-hub` | Sekundär | OIDC-Konfiguration im Code, in Prod **nicht** auf Authentik geleitet oder nicht erreichbar |
| `dev-hub` (Portal) | Referenz | TechDocs zu ADR-142 |

---

## Decision Drivers

| # | Treiber |
|---|---|
| D-1 | Ein Identitätssystem weniger zu betreiben: Authentik läuft als vier Container (`server`, `worker`, `db`, `redis`) auf `hetzner-prod`, seit zwei Monaten ohne Rollout-Fortschritt (KONZ-platform-024 „eingemottet“ seit 2026-07-17) |
| D-2 | Cloudflare Access ist bereits der gelebte Zugriffsschutz für interne Oberflächen (decks-hub, news, tax, staging, kd) — mit Service-Tokens für Agenten-Prüfungen (`playwright-verify`, `tools/cf-access-fetch.sh`) |
| D-3 | Zugriffsschutz am Edge braucht keinen App-Code: kein OIDC-Client, keine Redirect-URIs, keine Provider-Pflege je Repo (Anlass #221) |
| D-4 | Kunden-Hubs mit echten Nutzern (137herz.de, weltenhub, bieterpilot.de) dürfen durch die Ablösung **keinen** Login verlieren |

## 1. Context and Problem Statement

### 1.1 Ist-Zustand (gemessen 2026-09-16)

- **Authentik läuft** (`docker ps` auf `hetzner-prod`: `iil_authentik_server` Up 2 months, healthy) unter `id.iil.pet` (`infra/ports.yaml`, Port 9000).
- **Fünf Prod-Hubs leiten ihren OIDC-Login live auf Authentik:** `curl https://<host>/oidc/authenticate/` → 302 `https://id.iil.pet/application/o/…/authorize` bei dev-hub.iil.pet, writing.iil.pet, trading.iil.pet, weltenhub.iil.pet, 137herz.de. Ob diese Route der einzige Login ist, unterscheidet sich je Hub: dev-hub zeigt unangemeldet `accounts/login/` (Django-lokal), writing-hub leitet direkt in die App.
- **Sieben weitere Repos** tragen `mozilla_django_oidc`-Konfiguration im Code, ohne dass Prod darauf leitet (risk-hub, cad-hub: Host antwortet nicht auf der Route; schutztat.de 404).
- **Cloudflare Access** schützt bereits decks-hub, news, tax, kd, staging-Hosts; Service-Token-Muster ist dokumentiert (AGENT_HANDOVER 2026-09-15).
- **ADR-142** ist `accepted`; 13 ADRs referenzieren es, 6 akzeptierte ADRs nennen Authentik. Der OIDC-Rollout auf Staging ist seit 2026-07-17 eingemottet (KONZ-platform-024).

### 1.2 Warum jetzt

Der Owner hat entschieden. Was fehlt, ist das Artefakt, das die Folgen ordnet: welche Hubs betroffen sind, welcher Login an die Stelle tritt, in welcher Reihenfolge Authentik verschwindet — und was ausdrücklich **nicht** über Cloudflare Access geht.

## 2. Considered Options

### Option A: Cloudflare Access am Edge + lokales Django-Login in den Hubs ✅

Interne Oberflächen (Agenten-Werkzeuge, Dashboards, Staging, Klickdummies) liegen hinter Cloudflare-Access-Apps mit Owner-Identität und Service-Tokens. Kunden-Hubs führen ihre Nutzer **lokal** (Django `auth`/allauth mit Passwort bzw. Magic-Link), ohne externen IdP. Authentik wird nach Umstellung der fünf Live-Hubs stillgelegt.

- ✅ Ein Betriebssystem weniger, kein OIDC-Client-Code, kein Provider-Register
- ✅ Zugriffsschutz und Bot-Abwehr am Edge ohne App-Änderung
- ⚠️ Cloudflare Access ist **kein** Nutzer-Identitätssystem für Endkunden: kein Self-Service-Konto, kein Rollenmodell in der App. Kunden-Hubs brauchen das lokale Login **vor** dem Abschalten.
- ⚠️ Nutzer, die heute nur über Authentik existieren, müssen migriert werden (E-Mail-Identität, Passwort-Reset statt Passwort-Kopie)

### Option B: Authentik behalten, Rollout wieder aufnehmen

Wäre die Fortsetzung von ADR-142/KONZ-024. Widerspricht dem Owner-Entscheid; der Rollout ist seit zwei Monaten eingemottet, ohne dass ein Hub ihn vermisst hat.

### Option C: Cloudflare Access mit „Access for SaaS“ als OIDC-Provider für die Hubs

Cloudflare kann selbst als IdP auftreten (Access for SaaS, OIDC). Das behielte den OIDC-Client-Code in den Hubs und tauschte nur den Provider. Nicht gewählt: es ersetzt eine Provider-Pflege durch eine andere, bindet Endkunden-Identität an einen Cloudflare-Zero-Trust-Sitz und löst D-3 nicht. Bleibt als Rückfall für einen einzelnen Hub, der zwingend SSO braucht.

## 3. Decision Outcome

**Option A.** Identität wird zweigeteilt: **Zugriff** auf interne Oberflächen entscheidet Cloudflare Access am Edge; **Nutzerkonten** in Kunden-Hubs sind lokal im jeweiligen Hub. Authentik (`id.iil.pet`) wird stillgelegt, sobald kein Prod-Hub mehr dorthin leitet. ADR-142 wird `superseded_by: ADR-307`.

## 4. Implementation Details

### 4.1 Inventar und Reihenfolge

| Schritt | Hub | Was |
|---|---|---|
| 1 | dev-hub | OIDC-Route entfernen, lokales Login ist bereits Default (`accounts/login/`); Cloudflare-Access-App vor `dev-hub.iil.pet` |
| 2 | writing-hub, trading-hub | lokales Login aktivieren, OIDC-Route entfernen; Nutzerkonten aus Authentik per E-Mail migrieren (Passwort-Reset-Mail) |
| 3 | weltenhub, 137-hub | wie 2, mit Owner-Freigabe je Hub (echte Nutzer) |
| 4 | Code-Reste | `mozilla_django_oidc` aus den sieben nicht-live Repos entfernen (kein Prod-Risiko, reine Aufräumarbeit) |
| 5 | Authentik | `betriebsstatus: stillgelegt` in `ports.yaml`, Container stoppen (`restart=no`, Volumes bleiben 30 Tage), DNS `id.iil.pet` weg, Reste-Issue nach Muster #2480 |

### 4.2 Cloudflare Access als Standard für interne Oberflächen

Jede interne Oberfläche ohne Endkunden bekommt eine Access-App (Owner-E-Mail-Policy) und, wo Agenten prüfen, den Service-Token `playwright-verify` (Muster tax.iil.pet/decks-hub). `/livez/` bleibt per Bypass erreichbar (Uptime-Canary). `tools/cf-access-fetch.sh --coverage` ist der Beleg.

## 5. Migration Tracking

Je Hub ein Issue im Ziel-Repo (Schritt 1–3), gesammelt unter platform#3256. Prod-Umstellungen sind Gate 2 (Prod) — je Hub eine Freigabe-Zeile.

## 6. Consequences

### 6.1 Good
- Ein Betriebssystem weniger (vier Container, eine Domain, ein Provider-Register)
- Kein OIDC-Client-Code in den Hubs, keine Redirect-URI-Pflege (schließt die Klasse von #221)
- Zugriffsschutz und Agenten-Prüfungen laufen über denselben Mechanismus

### 6.2 Bad
- Kein plattformweites SSO für Endkunden mehr; wer zwei Hubs nutzt, hat zwei Konten
- Nutzer-Migration mit Passwort-Reset in drei Hubs mit echten Nutzern
- Sechs akzeptierte ADRs nennen Authentik als Voraussetzung und brauchen einen Nachtrag (Fleet-Scan vor Accept)

### 6.3 Nicht in Scope
- Ein späterer Endkunden-IdP (falls SSO wieder gebraucht wird) — dann neuer ADR, nicht Wiederbelebung von ADR-142
- Rollen-/Berechtigungsmodelle innerhalb der Hubs

## 7. Risks

| Risiko | Gegenmaßnahme |
|---|---|
| Ein Hub hat Nutzer, die **nur** über Authentik existieren, und wird ohne lokales Login umgestellt | Schritt-Reihenfolge: lokales Login zuerst, Abnahme = Login eines Test-Nutzers **vor** Entfernen der OIDC-Route; Authentik-Volumes 30 Tage behalten |
| Cloudflare Access wird für einen Endkunden-Hub als Login missverstanden | §3 grenzt das aus; Access-Apps nur für interne Oberflächen |
| ADR-142-Verweise in anderen Repos bleiben stehen | Fleet-Scan (`adr_cross_repo_refs`) vor Accept; Nachträge je ADR |

## Offen bis zum Accept

1. Challenger-Lauf (`/adr-challenger ADR-307`).
2. Je Live-Hub: gibt es Nutzer, die nur in Authentik angelegt sind? (Zählung in der Authentik-DB, read-only.)
3. Owner-Bestätigung der Zweiteilung in §3 — sie ist die eigentliche Entscheidung dieses ADR.
