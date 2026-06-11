---
status: proposed
date: 2026-06-06
decision-makers: Achim Dehnert
consulted: –
informed: –
implementation_status: not-started
domains: [architecture, multi-tenancy, security, data-sovereignty]
scope: platform
amends: [ADR-072, ADR-074]
relates_to: [ADR-035, ADR-109, ADR-137, ADR-092, ADR-219]
tags: [multi-tenancy, tenant-id, schema-isolation, django-tenants, row-level, dsgvo, consistency]
---

# ADR-237 — Multi-Tenancy: row-level `tenant_id` als Plattform-Default, schema-per-tenant als Compliance-Ausnahme

> **Amends ADR-072 / ADR-074**: hebt deren *universellen* „schema-per-tenant für alle SaaS"-Anspruch auf
> und re-scoped sie zur **bewussten Ausnahme** für regulierte Hart-Isolation. Schreibt die bereits
> gelebte Realität als Standard fest und schließt die ADR↔Code-Drift.

## Kontext

Eine geerdete Bestandsaufnahme (file:line-verifiziert über alle Django-Repos, 2026-06-06)
zeigt: die Plattform fährt **faktisch zwei sich ausschließende Tenancy-Strategien**, und die
bestehenden ADRs behaupten Universalität, die der Code widerlegt.

| Strategie | Repos (real, verifiziert) | tenant_id-Typ |
|---|---|---|
| **row-level `tenant_id`** (1 Schema, gefiltert) | risk-hub (`django_tenancy`), dev-hub, recruiting-hub, coach-hub, billing-hub | UUID (meist), **BigInteger** (recruiting-hub) |
| **schema-per-tenant** (`django_tenants`) | travel-beat, tax-hub | — (Schema-Trennung) |
| nicht multi-tenant | dms-hub | — |

Drei Befunde treiben diese Entscheidung:

1. **ADR↔Realität-Drift.** ADR-072 listet als Evidenz „6/9 Hubs mit django_tenants: travel-beat,
   weltenhub, coach-hub, cad-hub, billing-hub, dev-hub" — aber **coach-hub, billing-hub und dev-hub
   sind verifiziert row-level**, nicht schema-isoliert. Das schema-Lager ist real klein
   (travel-beat, tax-hub).
2. **Widersprüchliche, nicht erzwungene Regel.** ADR-074 beschreibt einen CI-Linter, der
   `filter(tenant_id=...)` *verbietet* — sinnvoll **nur** unter Schema-Isolation, aber direkt
   gegensätzlich zur row-level-Realität (wo dieser Filter Pflicht ist). Verifiziert: die Regel ist
   **Paper-only**, in keiner CI implementiert. Sie darf nicht plattformweit gelten.
3. **Compliance ist der echte Unterscheider.** ADR-072s Decision Drivers sind explizit
   **DSGVO Art. 17/20** (automatisierbare Löschung/Portabilität pro Mandant) und **strukturelle
   Isolation** („kein vergessener Filter darf zu Datenleck führen"). Das ist für regulierte SaaS
   (tax-hub = Steuerberatungskanzlei-Daten) ein **legitimer, nicht verhandelbarer** Treiber — aber
   kein Grund, allen Services Schema-Isolation aufzuzwingen.

## Entscheidung

1. **row-level `tenant_id` ist der kanonische Plattform-Default** für Multi-Tenancy
   (ADR-035 / ADR-109 / ADR-137 sind der maßgebliche Standard). Neue multi-tenant Repos
   verwenden row-level, sofern nicht das Ausnahme-Kriterium greift.

2. **schema-per-tenant (`django_tenants`) ist eine bewusste Ausnahme**, zulässig genau dann,
   wenn **mindestens eines** gilt:
   - regulatorisch getriebene **strukturelle** Mandanten-Isolation (DSGVO Art. 17/20
     automatisierbare Löschung/Portabilität als Pflicht; sektorale Compliance: Steuer/Recht/
     Gesundheit/öffentliche Hand);
   - vertraglich zugesicherte physische/logische Datentrennung pro Mandant.

   Die Ausnahme wird **pro Repo im ADR/CORE_CONTEXT begründet** (welches Kriterium, welcher Treiber).
   **tax-hub bleibt schema-per-tenant** (DSGVO/Steuerdaten). **travel-beat** wird separat bewertet
   (Story-/Reise-Content; kein offensichtlicher Compliance-Treiber → Migrations-Kandidat, nicht
   automatisch Ausnahme).

3. **`tenant_id`-Typ-Standard = `UUIDField`** (nicht-enumerierbar = security-besser). Bestehendes
   `BigIntegerField` (recruiting-hub) ist **grandfathered** (keine Zwangs-Migration); neue Repos
   nehmen UUID.

4. **ADR-074s Forbid-Regel wird re-scoped**: `filter(tenant_id=...)`-Verbot gilt **nur** in
   schema-per-tenant TENANT_APPS, nicht plattformweit. In row-level-Repos ist der explizite
   tenant-Filter (bzw. ein erzwingender Manager/RLS) der **vorgeschriebene** Pfad, nicht der
   verbotene.

## Konsequenzen

**Sofort (Doku, keine Migration):**
- ADR-072 / ADR-074 Frontmatter + Body re-scopen auf „Ausnahme-Pfad" (dieses ADR via `amends`).
- ADR-072s faktisch falsche `implementation_evidence`-Liste korrigieren (coach-hub/billing-hub/
  dev-hub = row-level).
- Die als schema gemeldeten, real row-level Repos sind bereits konform — **kein Migrationsaufwand**.

**Folge-Arbeit (eigene Vorgänge):**
- **travel-beat**: Migrations-Assessment schema→row-level (Aufwand + ob ein Compliance-Treiber
  existiert) als eigenes KONZ/Issue; nur bei Bestätigung migrieren.
- **tax-hub**: bleibt schema-per-tenant; Ausnahme-Begründung in tax-hub/CORE_CONTEXT verankern.
- row-level-Isolation **strukturell absichern** (erzwingender Tenant-Manager und/oder Postgres-RLS),
  damit der DSGVO-Einwand aus ADR-072 (§„kein vergessener Filter") auch im Default-Pfad adressiert
  ist — das ist die Bedingung dafür, dass row-level für nicht-regulierte SaaS überhaupt tragfähig ist.

**Kill-Gate / offene Prämisse:** Wenn sich für ein als „Default-row-level" geführtes Repo ein
DSGVO-Art.-17/20-Pflichtfall zeigt, den row-level+RLS **nicht** strukturell erfüllt, ist dieses Repo
ein Ausnahme-Fall — nicht der Default ist dann falsch, sondern die Repo-Einordnung.

## Verifikation

- Repo-Strategie-Tabelle: file:line-Audit 2026-06-06 (travel-beat `config/settings/base.py:23`
  `SHARED_APPS=["django_tenants"]`; coach-hub `apps/core/models.py:36` `tenant_id=UUIDField`;
  risk-hub `src/tenancy/models.py` row-level via `django_tenancy`; recruiting-hub
  `apps/identity/models.py` `BigIntegerField`).
- ADR-074-Forbid-Regel als Paper-only verifiziert (kein `_ci-python.yml`-Step, keine
  iil-codeguard-Regel).
- ADR-072 Decision Drivers (DSGVO Art. 17/20) zitiert aus
  `docs/adr/ADR-072-multi-tenancy-schema-isolation.md` §Decision Drivers.
