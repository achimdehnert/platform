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
3. **Erkennung am DB-Backend, NICHT an `TENANT_MODEL`.** Das Signal ist
   `ENGINE = django_tenants.postgresql_backend` (grep in `config/`). **Begründung
   (Empirie aus dem 2-Repo-Rollout):** `TENANT_MODEL` ist KEIN verlässlicher
   Diskriminator — auch **row-level/RLS-Repos** setzen es (dev-hub
   `core.Organization`, risk-hub `tenancy.Organization`, beide
   `django.db.backends.postgresql`, plain `models.Model`, kein `TenantMixin`).
   Selbst ein vorhandener `TenantMixin`-Import genügt nicht (dev-hub importiert
   ihn, nutzt aber den Standard-Backend). Würde man auf `TENANT_MODEL` triggern,
   liefe `migrate_schemas` (existiert nur unter django_tenants) auf diesen Repos
   ins Leere → `make dev` bräche. **Klassifikation:**

   | Muster | Signal | migrate_schemas + seed_public_tenant? |
   |---|---|---|
   | Schema-per-Tenant (django_tenants) | `ENGINE=django_tenants.postgresql_backend` + `SHARED_APPS` + `TenantMixin/DomainMixin` | **JA** |
   | Row-level / RLS / shared-schema | `ENGINE=django.db.backends.postgresql`, plain `models.Model`-Tenant, ggf. `TENANT_MODEL` | **NEIN** (anderer Pfad) |

   Bestätigte schema-per-tenant-Repos: ausschreibungs-hub, travel-beat, tax-hub.
   Nicht-django_tenants (unberührt): dev-hub, risk-hub.
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
- Schema-per-Tenant-Repos ohne `seed_public_tenant` müssen ihn nachrüsten (dev.sh
  warnt explizit). **Tatsächlicher Audit-Stand (2026-05-28, ENGINE-verifiziert):**
  ausschreibungs-hub ✅ + travel-beat ✅ haben den Command, **tax-hub** fehlt ihn
  (einziger offener Kandidat). Der frühere Verdacht (risk-hub/cad-hub/billing-hub/
  dev-hub/weltenhub/coach-hub aus einem Modell-Kommentar) ist **falsch** — diese
  sind kein django_tenants (s. Klassifikation).
- `migrate_schemas` bei jedem `make dev` kostet wenige Sekunden (idempotent).

## Methode: kanonischer `seed_public_tenant` (Template)

Aus dem Rollout (ausschreibungs-hub + tax-hub, Modell-Namen variieren:
`tenants.Client` vs `tenant.Organization`) abgeleitete **Methoden-Vorgabe** —
ein **modell-agnostisches** Template, das jedes Repo unverändert übernimmt; nur
der `DEFAULTS`-Block wird an die Pflichtfelder des Tenant-Modells angepasst:

```python
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand

DEFAULT_DOMAINS = ["localhost", "127.0.0.1"]
# Pflichtfelder des Tenant-Modells (variiert pro Repo): z. B.
#   ausschreibungs-hub Client: {"name": "Public"}
#   tax-hub Organization: {"name": "Public", "slug": "public", "owner_email": "dev@localhost"}
DEFAULTS = { ... }

class Command(BaseCommand):
    help = "Public-Tenant + Domain(s) anlegen (idempotent) — platform:ADR-219"
    def add_arguments(self, p):
        p.add_argument("--domain", action="append", dest="domains")
    def handle(self, *a, **o):
        Tenant = apps.get_model(settings.TENANT_MODEL)          # modell-agnostisch
        Domain = apps.get_model(settings.TENANT_DOMAIN_MODEL)
        pub, _ = Tenant.objects.get_or_create(schema_name="public", defaults=DEFAULTS)
        for i, d in enumerate(o.get("domains") or DEFAULT_DOMAINS):
            Domain.objects.get_or_create(domain=d, defaults={"tenant": pub, "is_primary": i == 0})
```

**Generisch:** Modell-Auflösung via `settings.TENANT_MODEL`/`TENANT_DOMAIN_MODEL`
(kein hartkodierter Import — funktioniert für `Client` wie `Organization`).
**Pro Repo:** nur `DEFAULTS` (die Nicht-Null-Pflichtfelder des Tenant-Modells).

## Verifikation

## Verifikation
- `cd <multi-tenant-repo> && make dev` → migrate_schemas + seed_public_tenant
  laufen, runserver startet, kein Tenancy-500.
- ausschreibungs-hub (2026-05-28): nach `migrate_schemas --shared` +
  `seed_public_tenant` liefert `/document-intelligence/vergabe/1/analyse/?demo=happy_path`
  **200** (vorher 500); spec-demo-KD rendert + Tab-Switch funktioniert.
- `gen_project_facts.py` → `project-facts.md` zeigt `docker-compose.dev.yml`.
- Regression: `dev.sh` auf Nicht-Tenant-Repo unverändert (kein migrate_schemas).
