---
id: ADR-219
title: "Lokaler Bring-up von Multi-Tenant-Repos (django_tenants) — migrate_schemas + seed_public_tenant als Local-Run-Konvention"
status: accepted
date: 2026-05-28
deciders: [Achim Dehnert]
consulted: [self-advocatus-diabolus]
informed: [achimdehnert, bahn-sqf, meiki-lra, ttz-lif, iilgmbh]
domains: [infrastructure, developer-experience, multi-tenancy, process, drift-prevention]
implementation_status: complete
implementation_evidence:
  - "platform: scripts/dev.sh — Multi-Tenant-Block (migrate_schemas + seed_public_tenant) vor runserver"
  - "platform: scripts/gen_project_facts.py — compose_local-Fallback um docker-compose.dev.yml erweitert"
  - "platform: .windsurf/workflows/run-local.md — Compose-Detection + Host/Docker-Modus + Multi-Tenant-Step"
  - "ausschreibungs-hub: apps/tenants/management/commands/seed_public_tenant.py (idempotent)"
  - "Präzedenz: travel-beat/apps/tenants/management/commands/seed_public_tenant.py"
scope:
  include_paths:
    - "scripts/dev.sh"
    - "scripts/gen_project_facts.py"
    - ".windsurf/workflows/run-local.md"
    - "**/apps/tenants/management/commands/seed_public_tenant.py"
---

# ADR-219: Lokaler Bring-up von Multi-Tenant-Repos (django_tenants)

## Kontext

Beim lokalen Testen des ausschreibungs-hub-Klickdummys (2026-05-28) zeigte sich:
die Local-Run-Konvention bringt `django_tenants`-Repos **nicht** lauffähig hoch.
Ein roher `manage.py runserver` gegen eine frische Dev-DB liefert auf **jedem**
Request `500` — die `TenantMainMiddleware` fragt vor jeder View
`tenants_domain` ab (`relation "tenants_domain" does not exist`), weil die DB
unmigriert und kein Tenant geseedet ist. Selbst DB-freie Pfade (z. B. ein
spec-demo-`?demo=`-View) sind betroffen, da die Middleware vor dem View läuft.

Drei Drift-Stellen verschärften das:
- `scripts/dev.sh` führte nur `exec runserver` aus — kein `migrate_schemas`,
  kein Tenant-Seed.
- `.windsurf/workflows/run-local.md` (`/run-local`) hardcodete
  `docker-compose.local.yml` — existiert bei vielen Repos nicht (nur `dev`/`prod`).
- `scripts/gen_project_facts.py` wählte `docker-compose.local.yml` sonst
  `docker-compose.yml` — `docker-compose.dev.yml` fehlte in der Kette, also
  emittierte `project-facts.md` eine nicht existente Compose-Datei.

Folge: Agenten/Entwickler improvisieren einen manuellen `runserver` und laufen
reproduzierbar in den Tenancy-500. Das ist ein Konventions-Defekt, kein
Einzelfall.

## Entscheidung

**Der lokale Bring-up von Multi-Tenant-Repos ist Teil der Konvention und wird
vom Tooling übernommen — nicht von Hand.**

1. **Jedes `django_tenants`-Repo MUSS einen idempotenten Management-Command
   `seed_public_tenant` führen** (legt `Client(schema_name="public")` + Primär-
   Domain(s) via `get_or_create` an). Präzedenz: `travel-beat`. Default-Domains
   für lokal: `localhost` + `127.0.0.1`.
2. **Das Local-Run-Tooling MUSS für Multi-Tenant-Repos vor dem Serven
   `migrate_schemas --shared --noinput` + `seed_public_tenant` ausführen.**
   Umgesetzt in `scripts/dev.sh` (Host-Run) und `.windsurf/workflows/run-local.md`
   (Docker-Run; bzw. Verweis auf `make dev`, wenn das Compose keinen App-Service
   hat — nur DB/Redis).
3. **Multi-Tenant-Erkennung** = `TENANT_MODEL`/`django_tenants` in
   `config/settings/`. Nicht-Tenant-Repos sind unberührt (kein migrate_schemas).
4. **`gen_project_facts.py` Compose-Detection MUSS `docker-compose.dev.yml`
   in der Fallback-Kette führen** (`local` → `dev` → generisch).

## Begründung

- Der Tenant-Bootstrap ist eine **deterministische Voraussetzung** des Servens,
  kein optionaler Schritt — gehört also ins Bring-up-Tooling, nicht in
  Tribal-Knowledge.
- Idempotenz (`get_or_create`, `migrate_schemas`) macht den Schritt bei jedem
  Start sicher wiederholbar.
- Das Muster existiert bereits (travel-beat) — die Entscheidung **verallgemeinert
  Bestehendes**, erfindet nichts Neues.

## Konsequenzen

### Positiv
- `make dev` / `/run-local` bringen Multi-Tenant-Repos turnkey hoch; kein
  manueller `runserver`, kein reproduzierbarer Tenancy-500.
- `project-facts.md` referenziert die real existierende Compose-Datei.

### Aufwand / Negativ
- Repos ohne `seed_public_tenant` müssen ihn nachrüsten (dev.sh warnt explizit
  mit Verweis auf diese ADR). Betroffen: alle `django_tenants`-Repos ohne den
  Command (Audit-Kandidat: risk-hub, cad-hub, billing-hub, dev-hub, weltenhub,
  coach-hub — gemäß apps/tenants/models.py-Kommentar).
- `migrate_schemas` bei jedem `make dev` kostet wenige Sekunden (idempotent).

## Verifikation
- `cd <multi-tenant-repo> && make dev` → migrate_schemas + seed_public_tenant
  laufen, runserver startet, kein Tenancy-500.
- ausschreibungs-hub (2026-05-28): nach `migrate_schemas --shared` +
  `seed_public_tenant` liefert `/document-intelligence/vergabe/1/analyse/?demo=happy_path`
  **200** (vorher 500); spec-demo-KD rendert + Tab-Switch funktioniert.
- `gen_project_facts.py` → `project-facts.md` zeigt `docker-compose.dev.yml`.
- Regression: `dev.sh` auf Nicht-Tenant-Repo unverändert (kein migrate_schemas).
