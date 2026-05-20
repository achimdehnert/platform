---
adr: 212
title: Staging-Hostname-Konvention (Präfix `staging-`, Demo-Tenant für Subdomain-Tenancy)
status: accepted
date: 2026-05-20
deciders: [achim.dehnert]
tags: [staging, dns, naming, tenancy, oidc, registry, ingress]
supersedes: []
amends: []
relates: [ADR-142, ADR-210]
---

# Staging-Hostname-Konvention

## Kontext

Heute (2026-05-19/20) lief ein SSO-Fix-Versuch auf `staging.schutztat.de` über
mehrere Ebenen ins Leere, weil **keine** verbindliche Hostname-Konvention für
Staging existiert. Verifizierte Symptome dieser Session:

- `registry/repos.yaml` führt für risk-hub **zwei** Staging-Hostnames parallel
  (`staging.schutztat.de`, `staging-riskhub.iil.pet`) — keine ist als
  Canonical markiert. Niemand wusste, welche SSoT ist.
- `staging.schutztat.de` war seit März 2026 nginx-konfiguriert für **bfagent**
  (Container :8091), nicht risk-hub — exakter Namenskonflikt, der ohne Regel
  nicht erkennbar war.
- Existierende Staging-Apps mischen Präfix und Suffix:
  - `staging-devhub.iil.pet`, `staging-riskhub.iil.pet` (Präfix)
  - `billing-staging.iil.pet`, `learn-staging.iil.pet`,
    `wedding-staging.iil.pet`, `welten-staging.iil.pet` (Suffix)
- Subdomain-Tenancy-Repos (risk-hub) haben heute **keinen** Demo-Tenant in
  der DB: `demo.schutztat.de` → 403 (kein `Organization(slug="demo")`), obwohl
  Cert-SAN und DNS-Setup vorhanden sind.

## Entscheidung

Drei Klauseln, je nach Repo-Eigenschaft:

### Klausel 1 — Domain-Repo MIT Subdomain-Tenancy

Repos mit eigener Domain (`<domain>`) und Subdomain-Tenancy bekommen genau
**einen** Canonical-Staging-Hostname:

```
staging-demo.<domain>
```

Begleitende Pflichten:

1. **Mandatory Org `demo`** in Prod-DB (per Daten-Migration im Repo).
2. **Mandatory Org `staging-demo`** in Staging-DB (per Daten-Migration im Repo,
   guarded by `DJANGO_SETTINGS` / Env).
3. Cert-SAN muss `staging-demo.<domain>` enthalten (Wildcard `*.domain` oder
   explizit).
4. `TENANT_RESERVED_SUBDOMAINS` braucht **keinen** `staging`-Workaround —
   der Hostname löst sich über echte Tenant-Auflösung.

### Klausel 2 — Domain-Repo OHNE Subdomain-Tenancy

```
staging.<domain>
```

Keine Demo-Tenant-Pflicht, da keine Tenant-Middleware blockt.

### Klausel 3 — Repo OHNE eigene Domain

```
staging-<system-slug>.iil.pet
```

Konsequent Präfix `staging-`, damit alle Klauseln dieselbe Wortrichtung
benutzen. `<system-slug>` = der **brand-/funktions-orientierte** Slug aus
`registry/repos.yaml` (z. B. `learn` für coach-hub, nicht `coach-hub`),
nicht zwangsläufig der Repo-Name.

**Routing-Zielarchitektur:** Klausel-3-Hostnames werden langfristig über
einen **zentralen Ingress** (Traefik o. Ä.) auf dem Wildcard-Apex
`*-staging.iil.pet` mit einem Wildcard-Cert (DNS-01) geroutet.
Inkrementelle Migration repo-für-repo; Per-Repo-nginx bleibt erlaubt,
bis das jeweilige Repo auf den Ingress umgestellt ist. Status- und
Reihenfolge-Tracking: [`docs/staging-ingress-migration.md`](../staging-ingress-migration.md).

Klauseln 1 und 2 (Domain-Repos mit eigener Domain) bleiben **außerhalb**
des Wildcards und behalten Per-Repo-nginx-Vhost.

### Klausel 4 — Lokales Dev für Subdomain-Tenancy

```
demo.localhost:<port>
```

Env-bewusste Seed-Migration für Klausel-1-Repos:

| Env | Pflicht-Org-Slug | Erreichbar via |
|---|---|---|
| `local`   | `demo`         | `demo.localhost:<port>` |
| `staging` | `staging-demo` | `staging-demo.<domain>`  |
| `prod`    | `demo`         | `demo.<domain>`          |

Voraussetzung: `TENANT_BASE_DOMAINS=localhost` in der Dev-Env. Verifiziert:
`*.localhost` wird laut RFC 6761 nativ aufgelöst (kein `/etc/hosts` nötig);
die Middleware strippt den Port. Authentik bekommt für lokales Testen einen
eigenen Provider-Eintrag pro Repo (`<repo>-dev`) mit gelockerter
Redirect-URI-Liste (`http://demo.localhost:*/oidc/callback/`).

## Demo-Org-Fixture (Plattform-Package)

Die in Klausel 1 geforderten Demo-Organisationen (`demo`, `staging-demo`)
werden durch ein dediziertes Plattform-Package versorgt:

**Package:** `iil-demo-fixture` (eigenes Repo + PyPI-Paket, Pattern analog
`iil-platform-context`).

**Scope (Identitäts-Fixture, im Package):**

- `Organization(slug="demo"|"staging-demo", name="Demo GmbH", …)`
- Standard-User mit Authentik-OIDC-`sub` (3 Rollen: Admin, Member, Guest)
- Standard-Adresse / Kontaktdaten
- Hook: `apply_demo_fixture(env)` — idempotent, aufrufbar aus repo-lokaler
  Daten-Migration

**Stammdaten-Separation (NICHT im Package):**

- **Fachliche Sample-Daten** (risk-hub: GBU-Beispiele; coach-hub: Demo-Kurse;
  billing-hub: Demo-Rechnungen) bleiben **repo-lokal** in einer eigenen
  Daten-Migration. Konvention: `0NNN_demo_sample_data.py`, separat von der
  Identitäts-Fixture-Migration `0NNN_demo_identity_fixture.py`.
- **Tester-erzeugte Daten** (vom Demo-User in der UI angelegt) werden vom
  täglichen idempotenten Reset (Kritik 1) entfernt; Identitäts-Fixture
  und repo-lokale Sample-Daten bleiben.
- **Lifecycle:** Schema-Updates der Identitäts-Fixture lösen ein
  Package-Release aus → Consumer-Repos bumpen die Version. Sample-Daten-
  Updates sind repo-interne Migrationen, kein Plattform-Event.

**Opt-Out** für ttz-lif / meiki-lra: Repos mit Datensouveränitäts-
Restriktionen dürfen `iil-demo-fixture` nicht nutzen; ihre Demo-Orgs
werden komplett repo-lokal in der Daten-Migration definiert. CI-Lint
akzeptiert beides, sofern `Organization(slug="demo")` und
`Organization(slug="staging-demo")` existieren.

## Registry-SSoT

Pro System in `registry/repos.yaml`:

```yaml
staging:
  canonical_hostname: staging-demo.schutztat.de   # neue Pflicht-Spalte
  hostnames:                                       # bestehende Liste; nur Aliase
    - staging-demo.schutztat.de
```

`canonical_hostname` ist das **einzige** offizielle Staging-Ziel
(DNS, nginx, Cert, Authentik-Redirect, OIDC-Env). `hostnames` bleibt für
historische Aliase / Redirect-URI-Listen in Authentik.

## CI-Lint (companion)

Ein Repo-Health-Check schlägt fehl, wenn:

- `staging.canonical_hostname` fehlt oder nicht zur Klausel passt.
- Repo hat Subdomain-Tenancy + Klausel 1, aber **keine** Migration mit
  `Organization(slug="demo")` und `Organization(slug="staging-demo")`.
- nginx-Vhost für `canonical_hostname` fehlt oder hat falschen Upstream.
- Cert-SAN deckt `canonical_hostname` nicht ab.

## Migrationsinventar (verifizierter Stand 2026-05-20)

| System | Heute | Soll | Aktion |
|---|---|---|---|
| risk-hub | `staging.schutztat.de` + `staging-riskhub.iil.pet` (registry); nginx routet `staging.schutztat.de` → bfagent | `staging-demo.schutztat.de` | (a) nginx-Vhost ersetzen, (b) Cert-SAN, (c) Demo-Tenant-Migration, (d) DNS, (e) Authentik-Redirect, (f) Aliase entfernen |
| dev-hub | `staging-devhub.iil.pet` | unverändert (Klausel 3, Präfix bereits) | keine |
| billing-hub | `billing-staging.iil.pet` (STAGING-OIDC.md) | `staging-billing.iil.pet` | nginx + Cert + Authentik-Redirect + Doc-Sync |
| coach-hub | `learn-staging.iil.pet` | `staging-learn.iil.pet` (system-slug) | dito |
| wedding-hub | `wedding-staging.iil.pet` | `staging-wedding.iil.pet` | dito |
| weltenhub | `welten-staging.iil.pet` | `staging-welten.iil.pet` | dito |

Tenancy-Eigenschaft je Repo ist beim ADR-Schreiben **nicht durchgehend
verifiziert** — risk-hub hat Subdomain-Tenancy bewiesen
(`SubdomainTenantMiddleware`); für die anderen 4 muss der CI-Lint die
Klausel-Zuordnung bestimmen, bevor migriert wird.

## Konsequenzen

**Positiv:**

- Eine Person liest den Hostnamen und kennt damit DNS-Ziel, Cert-SAN,
  Authentik-Slug, Demo-Tenant, Reserved-Liste-Bedarf — ohne Per-Repo-Recherche.
- Demo-Tenant-Pflicht zwingt jedes Subdomain-Tenancy-Repo zu einem
  testbaren Demo-Flow (heute fehlt der zugehörige Org-Eintrag bei risk-hub).
- Kein Reserved-Subdomain-Workaround mehr nötig (Klausel 1 löst Tenant
  echt auf).

**Negativ:**

- 4 produktive Suffix-Apps müssen migriert werden (Authentik-Slug,
  nginx-Vhost, Cert, Bookmarks, Dokumentation, Browser-Sessions der User).
- Daten-Migrationen für Demo-Tenant je Subdomain-Tenancy-Repo.
- Risiko von Inkonsistenz, wenn nur ein Teil der Stelle aktualisiert wird
  (Registry vs. nginx vs. Cert vs. Authentik) — CI-Lint pflicht.

## Offene Punkte (vor Acceptance zu klären)

1. **Tenancy-Inventar** — welche der 5 betroffenen Repos (außer risk-hub)
   nutzen tatsächlich Subdomain-Tenancy? Migration je nach Antwort
   Klausel 1 vs. Klausel 3. Pflicht-Feld `tenancy_mode` in
   `registry/repos.yaml` (`subdomain` / `path` / `header` / `none`) als
   maschinell prüfbarer Marker.
2. ~~**Demo-Tenant Datenmodell**~~ — **entschieden 2026-05-20:**
   Plattform-Fixture `iil-demo-fixture` für Identität (Org/User/OIDC-sub),
   repo-lokale Migration für fachliche Sample-Daten. Siehe Abschnitt
   „Demo-Org-Fixture".
3. **Rollout-Reihenfolge** — Big-Bang oder Repo-für-Repo? Pflicht-Übergangs-
   redirect (301 alt → neu) für mind. 90 Tage; Authentik behält beide
   Redirect-URIs während der Übergangsfrist, danach Cleanup-Ticket.
4. **Cert-Strategie** — Empfehlung: **Wildcard-Cert pro Domain via
   ACME DNS-01** (CF-Token vorhanden). Heute fehlende SAN war der zentrale
   Blocker; Wildcard entkoppelt Cert-Verwaltung von Hostname-Konvention.

## Advocatus-Diaboli Review (2026-05-20)

Identifizierte Schwächen + ggf. integrierte Optimierungen:

### Kritik 1 — Demo-Tenant in Prod ist ein Sicherheits-Smell

Eine per Konvention bei jedem Repo öffentlich erreichbare Demo-URL ist ein
konstantes Aufklärungsziel. „Demo" suggeriert Test-Daten = weniger
Schutz-Annahme. **Mitigation (verpflichtend für Klausel 1):**

- Demo-Org **read-only** (per Tenant-Flag oder durch
  `ReadOnlyTenantMiddleware`).
- Keine produktiven E-Mails, keine Stripe-Live-Keys.
- Login zur Demo nur über Authentik (keine lokalen Demo-Passwords).
- Täglicher idempotenter Reset des Demo-DB-Subsets (Celery-Beat oder Cron).

### Kritik 2 — DB-Seed-Pflicht ist invasiver als nötig (OOB-Alternative)

Die Pflicht-Migration `Organization(slug="demo")` und `staging-demo` ist
**eine** Lösung, nicht die einzige. Out-of-the-box-Alternative:

**Middleware-Fallback-Flag** statt DB-Seed: bei
`subdomain in {"staging-demo","demo"}` und passender Env-Flagge die
Tenant-Auflösung als „virtueller Demo-Tenant" mit hartcodierten Defaults
durchführen (kein DB-Row). Vorteile: keine Migrationen, keine Datenpflege,
sofort einheitlich; Nachteile: virtueller Tenant braucht eigene Code-Pfade
für Berechtigungen + isolierte Datenanzeige.

⟹ **Entschieden 2026-05-20:** Klausel 1 via **DB-Seed** (ADR-Stand).
Begründung: Klausel-1-Repos wie risk-hub haben viele Write-Pfade (GBU,
Risiko, Dokumente); ein Middleware-Fallback hätte das Klassenproblem
„eine vergessene Code-Stelle ⟹ Cross-Tenant-Leak". Die Reset-Pflicht
(Kritik 1) federt das Demo-Daten-Korruptions-Risiko ab.

### Kritik 3 — Cert-Krise wiederholt sich pro neuem Repo

Heute (2026-05-19) scheiterte die Cert-Erweiterung für
`staging.schutztat.de`, weil:
(a) LE-Cert deckte SAN nicht ab, (b) HTTP-01-Challenge unter
Cloudflare-Proxy lieferte 400. ADR-212 ohne Cert-Klausel reproduziert das.
**Optimierung in Klausel-4-Ergänzung integriert** (Wildcard-Cert via
DNS-01 als Standard).

### Kritik 4 — Definition von „Subdomain-Tenancy" fehlt

Repos mit Path-Tenancy (`/<tenant>/…`), Header-Tenancy, oder
JWT-Claim-Tenancy fallen wohin? **Optimierung in Offene Punkte #1
integriert:** `tenancy_mode` als Pflicht-Feld in `registry/repos.yaml`
mit endlicher Enumeration.

### Kritik 5 — CI-Lint spezifiziert, nicht implementiert

ADR fordert Lint, definiert ihn aber nicht. **Konkretisierung:**

- Repo-Health-Agent (heute live) erweitern um Dimension
  `staging_hostname_convention` mit Checks:
  1. `staging.canonical_hostname` vorhanden + matcht passende Klausel
     anhand `tenancy_mode`.
  2. Falls Klausel 1: Migration mit `Organization(slug="demo")` und
     `Organization(slug="staging-demo")` (oder Middleware-Fallback-Flag
     gesetzt, je nach Kritik-2-Entscheidung) auffindbar.
  3. nginx-Vhost mit `canonical_hostname` als `server_name` existiert
     (cross-repo check via SSH zum Server oder via Stack-Manifest).
  4. Cert-SAN deckt `canonical_hostname` (per `openssl` gegen aktiven
     Server oder gegen CF Origin CA).
  5. Authentik-Provider hat Redirect-URI für `canonical_hostname`.

### Kritik 6 — Radikalere Out-of-the-box-Alternativen (zur Abwägung)

| Alternative | Idee | Trade-off |
|---|---|---|
| **A) Wildcard-Apex `*-staging.iil.pet` + zentraler Ingress** | Ein Cert, ein nginx-Block; jede App registriert sich per Label/Compose | Vendor-Lock-in an Ingress-Layer; aber **erspart pro-Repo-nginx-Config** |
| **B) Kein separates Staging — CF Access mit `X-Env: staging` Header** | Staging-Aufruf via Prod-URL mit signiertem Header; App schaltet auf Staging-DB/Worker | Radikal einfach, aber kein DNS-isoliertes Staging mehr; nicht für jeden Use-Case |
| **C) Per-Env-Subdomain `<env>.<system>.<scope>`** (`staging.billing.iil.pet`) | Zwei Labels, jedes mit klarer Semantik | Lange Hostnames, Wildcard-Cert braucht zwei Ebenen (`*.billing.iil.pet` ODER `*.iil.pet`) |

A) reduziert den Migrationsaufwand massiv und ist die ernsthafteste
OOB-Alternative zur aktuellen 3-Klauseln-Variante.

⟹ **Entschieden 2026-05-20:** A) **angenommen als Zielarchitektur**
für Klausel 3 — nicht als Pflicht ab Tag 1, sondern als inkrementelle
Migration repo-für-repo. Per-Repo-nginx bleibt erlaubt, bis das jeweilige
Repo auf den zentralen Ingress umgestellt ist. Status- und Reihenfolge-
Tracking: [`docs/staging-ingress-migration.md`](../staging-ingress-migration.md).
Klauseln 1/2 (Domain-Repos) bleiben außerhalb des Wildcards.

### Kritik 7 — Anti-Kritik: ADR ist gerechtfertigt

Nach ADR-Threshold-Policy: cross-cutting (≥6 Repos), nicht trivial
ablesbar aus Code, dokumentierte Trade-offs nötig. ADR ist die korrekte
Form, nicht CHANGELOG.
