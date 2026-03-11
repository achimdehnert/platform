---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
consulted: –
informed: –
implementation_status: partial
implementation_evidence:
  - "weltenhub, risk-hub: schema isolation, other hubs pending"
---

# ADR-072: Adopt PostgreSQL Schema Isolation for SaaS Multi-Tenancy

| Attribut       | Wert                                                                 |
|----------------|----------------------------------------------------------------------|
| **Status**     | Accepted                                                             |
| **Scope**      | platform                                                             |
| **Repo**       | platform                                                             |
| **Erstellt**   | 2026-02-21                                                           |
| **Autor**      | Achim Dehnert                                                        |
| **Reviewer**   | –                                                                    |
| **Supersedes** | –                                                                    |
| **Relates to** | ADR-035 (Shared Django Tenancy Package), ADR-021 (Unified Deployment), ADR-042 (Dev Environment), ADR-045 (Secrets Management) |

---

## Decision Drivers

- **DSGVO Art. 17/20**: Recht auf Löschung und Datenportabilität müssen pro Mandant automatisierbar sein
- **SaaS-Isolation**: Kein vergessener `.filter(tenant_id=...)` darf zu Datenleck führen — strukturelle Erzwingung nötig
- **VPS-Constraint**: 1 Hetzner VPS — keine 100 separaten DB-Instanzen betreibbar
- **1 Entwickler**: Minimaler Code-Overhead, bewährtes Tooling (`django-tenants` seit 2013 aktiv)
- **Bestehende Infrastruktur**: Docker Compose, Nginx, Self-Hosted Runner — keine Kubernetes-Einführung
- **Skalierungsziel**: 20–100+ Mandanten in 12–24 Monaten auf bestehender Hardware

---

## 1. Kontext

### 1.1 Ausgangslage

Das Portfolio besteht aus mehreren unabhängigen Django/HTMX-Services (bfagent, travel-beat, trading-hub, risk-hub u.a.), die jeweils auf einem einzelnen Hetzner VPS laufen. Jeder Service hat seine eigene PostgreSQL-Datenbank und kommuniziert über drei Kanäle:

- **REST/JSON APIs** zwischen Services
- **Shared Database Views** (Cross-DB-Zugriffe)
- **Celery Tasks** cross-service

ADR-035 hat die Tenancy-Infrastruktur auf Row-Level-Basis (UUID `tenant_id`) konsolidiert. Diese Entscheidung war korrekt für den damaligen Kontext (interne Nutzung, kein SaaS).

### 1.2 Neue Anforderung: SaaS-Lizenzierung

Das Portfolio soll als SaaS an Dritte angeboten werden:

- **Skalierungsziel:** 20–100+ Mandanten in 12–24 Monaten
- **Isolation:** Strikt getrennt — Mandant darf niemals Daten anderer sehen (DSGVO/BDSG)
- **Betrieb:** Weiterhin auf einem Hetzner VPS (kein Kubernetes, kein Managed Cloud)

### 1.3 Lücken des bestehenden Ansatzes (ADR-035)

| Problem | Beschreibung |
|---------|-------------|
| **DSGVO-Risiko** | Row-Level-Isolation: Ein vergessenes `.filter(tenant_id=...)` in einem QuerySet verursacht Datenleck. Bei 1–3 Entwicklern kein Review-Prozess der jede Query abfängt. |
| **Kein Backup pro Mandant** | `pg_dump` sichert immer die gesamte DB; mandantenspezifischer Export ist aufwändig |
| **Kein Recht auf Löschung** | Art. 17 DSGVO: Mandantendaten löschen erfordert DELETE über alle Tabellen |
| **Keine Datenportabilität** | Art. 20 DSGVO: Export eines einzelnen Mandanten ist nicht standardisiert |
| **Skalierungs-Ceiling** | Row-Level-Isolation skaliert gut, aber bietet keine physische Trennung für Enterprise-Kunden |

### 1.4 Constraints

- **1 Hetzner VPS** (4 Cores, 16 GB RAM) — kein horizontales Scaling in Phase 1
- **Self-Hosted GitHub Actions Runner** auf demselben VPS
- **Docker Compose** als Deployment-Mechanismus (kein Kubernetes)
- **Nginx** auf Prod-Server (88.198.191.108)
- **`platform_context`** als vendored Shared Library in allen Services
- **1 Entwickler** — Implementierungsaufwand muss realistisch sein

---

## 2. Entscheidung

**PostgreSQL-Schema-Isolation via `django-tenants`** als Tenancy-Strategie für alle Services die SaaS-fähig werden sollen.

Jeder Mandant erhält ein eigenes PostgreSQL-Schema pro Service-Datenbank. Der `search_path` wird automatisch per `django-tenants`-Middleware auf das Mandanten-Schema gesetzt — kein manuelles `.filter(tenant_id=...)` erforderlich.

```
PostgreSQL DB (pro Service):
├── public/          ← Shared: Tenant-Registry, Auth, Billing
├── tenant_acme/     ← Mandant ACME Corp — alle App-Tabellen
├── tenant_contoso/  ← Mandant Contoso — alle App-Tabellen
└── tenant_N/        ← ...
```

**Geltungsbereich:** Diese Entscheidung gilt für alle Services die SaaS-Mandanten bedienen. Interne Tools (dev-hub, mcp-hub) sind ausgenommen.

---

## 3. Betrachtete Alternativen

### Option A: Schema per Mandant (gewählt)

- `django-tenants` setzt `search_path` automatisch
- Strikte DB-Isolation ohne manuelle Filter
- 1 PostgreSQL-Instanz pro Service (VPS-kompatibel)
- Backup/Restore pro Mandant: `pg_dump --schema=tenant_X`
- Recht auf Löschung: `DROP SCHEMA tenant_X CASCADE`

### Option B: Separate Datenbank pro Mandant

**Abgelehnt.** 100 Mandanten × 3 Services = 300 PostgreSQL-Instanzen auf einem VPS. Nicht betreibbar. Shared DB Views funktionieren nicht cross-database.

### Option C: Row-Level-Isolation (bestehender ADR-035-Ansatz)

**Für SaaS-Kontext abgelehnt.** Vergessener Filter = Datenleck. DSGVO Art. 17/20 schwer erfüllbar. Kein mandantenspezifisches Backup. Bleibt gültig für interne Tools.

### Option D: Row-Level Security (PostgreSQL RLS)

**Nicht gewählt.** RLS bietet DB-seitige Absicherung, aber erfordert `SET app.tenant_id` in jeder Connection — komplex bei Connection Pooling (PgBouncer transaction mode). `django-tenants` ist ausgereifter und hat besseres Django-Ökosystem.

---

## 4. Begründung im Detail

### 4.1 Warum Schema-Isolation DSGVO-sicher ist

PostgreSQL `search_path` ist eine Connection-Property. Sobald die `django-tenants`-Middleware den `search_path` auf `tenant_acme` setzt, sind alle SQL-Queries automatisch auf dieses Schema beschränkt — ohne Anwendungscode-Änderungen. Ein vergessener Filter ist strukturell unmöglich.

```python
# VORHER (ADR-035, Row-Level):
assessments = Assessment.objects.filter(tenant_id=request.tenant.id)  # Vergessen → Datenleck

# NACHHER (ADR-056, Schema-Isolation):
assessments = Assessment.objects.all()  # Automatisch im richtigen Schema
```

### 4.2 Verhältnis zu ADR-035

ADR-035 bleibt gültig für:
- Interne Tools (dev-hub, mcp-hub) die keine SaaS-Mandanten bedienen
- Services in der Übergangsphase vor Schema-Migration

ADR-056 **erweitert** ADR-035 für SaaS-fähige Services. Die `platform_context`-Shared-Library (vendored) wird um Tenant-Utilities erweitert — kein neues separates Package.

### 4.3 Tenant-Context-Propagation über alle 3 Kanäle

**Kanal 1: REST/JSON APIs**

Service-zu-Service-Calls über das interne Docker-Netzwerk nutzen einen `X-Tenant-Schema`-Header:

```python
# In platform_context/tenant_utils/http_client.py
TENANT_HEADER = "X-Tenant-Schema"

class TenantAwareHttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def _headers(self) -> dict:
        from django.db import connection
        return {
            TENANT_HEADER: connection.schema_name,
            "Content-Type": "application/json",
        }

    def get(self, path: str, **kwargs):
        import httpx
        return httpx.get(f"{self.base_url}{path}", headers=self._headers(), **kwargs)

    def post(self, path: str, **kwargs):
        import httpx
        return httpx.post(f"{self.base_url}{path}", headers=self._headers(), **kwargs)
```

Empfangender Service liest den Header via `TenantPropagationMiddleware` (nur für Service-zu-Service-Calls, nicht für User-Requests die über Subdomain kommen):

```python
# In platform_context/tenant_utils/middleware.py
class TenantPropagationMiddleware:
    def __call__(self, request):
        if not hasattr(request, "tenant") and TENANT_HEADER in request.headers:
            from django.db import connection
            connection.set_schema(request.headers[TENANT_HEADER])
        return self.get_response(request)
```

**Kanal 2: Shared DB Views**

Bestehende Cross-DB-Views werden durch REST-API-Calls ersetzt (Standard). Für Performance-kritische Fälle: Materialized Views per Celery-Sync im lokalen Tenant-Schema.

```
VORHER:  Service A → SQL View → Service B's DB
NACHHER: Service A → REST API (X-Tenant-Schema Header) → Service B → Service B's DB
```

**Kanal 3: Celery Tasks**

`tenant-schemas-celery` serialisiert den Schema-Namen automatisch in die Celery-Message. Cross-Service-Tasks übergeben `_tenant_schema` im Payload:

```python
# Cross-Service-Task senden
def send_cross_service_task(task_name: str, **kwargs):
    from django.db import connection
    from celery import current_app
    kwargs["_tenant_schema"] = connection.schema_name
    current_app.send_task(task_name, kwargs=kwargs)

# Empfangender Service: Basis-Task mit Schema-Switching
from celery import Task
from django_tenants.utils import schema_context

class TenantAwareTask(Task):
    def __call__(self, *args, **kwargs):
        schema = kwargs.pop("_tenant_schema", "public")
        with schema_context(schema):
            return super().__call__(*args, **kwargs)
```

### 4.4 `platform_context` Tenant-Utils Struktur

Alle tenant-spezifische Logik die in jedem Service identisch ist, wird in `platform_context` als `tenant_utils`-Modul ausgeliefert:

```
platform_context/
└── tenant_utils/
    ├── __init__.py
    ├── middleware.py       # TenantPropagationMiddleware (Service-zu-Service)
    ├── http_client.py      # TenantAwareHttpClient
    ├── celery.py           # send_cross_service_task, TenantAwareTask
    ├── testing.py          # pytest fixtures: tenant_a, tenant_b, tenant_a_client
    └── provisioning.py     # provision_tenant() — erstellt Schema in allen Service-DBs
```

**Installation:** Bereits in allen Services via `platform-context[testing]>=0.3.1` — kein neues Package nötig.

### 4.5 Wildcard-DNS und SSL

Subdomain-basiertes Routing (`tenant1.bfa.example.com`) erfordert:
- Wildcard-DNS-Eintrag (`*.bfa.example.com → 88.198.191.108`)
- Wildcard-SSL via Let's Encrypt DNS-Challenge (nicht HTTP-Challenge)
- **Nginx** als Wildcard-Reverse-Proxy

```nginx
# /etc/nginx/sites-enabled/bfa-wildcard.conf
server {
    listen 443 ssl;
    server_name ~^(?<tenant>[^.]+)\.bfa\.example\.com$;
    ssl_certificate /etc/letsencrypt/live/bfa.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bfa.example.com/privkey.pem;
    location / {
        proxy_pass http://127.0.0.1:<PORT>;
        proxy_set_header Host $host;  # django-tenants liest Host-Header
    }
}
```

**Traefik bleibt deferred** gemäß ADR-021. ADR-057 reserviert für Traefik-Einführung.

### 4.6 Health-Endpoints bei Subdomain-Routing

`/livez/` und `/healthz/` (ADR-021) müssen im `public`-Schema laufen:

```python
# config/settings/base.py
PUBLIC_SCHEMA_URLCONF = "config.urls_public"  # enthält /livez/ + /healthz/
ROOT_URLCONF = "config.urls_tenant"           # tenant-spezifische URLs
```

### 4.7 weltenhub/bfagent Shared Database

`weltenhub` und `bfagent` teilen aktuell `bfagent_db`. **Pflicht vor Phase 2 (`bfagent`):** `weltenhub` muss in eine eigene `weltenhub_db` migriert werden — `django-tenants` erwartet exklusive Kontrolle über die DB-Schemas.

| Schritt | Aufwand | Zeitpunkt |
|---------|---------|----------|
| `weltenhub_db` anlegen | Niedrig | Vor Phase 2 |
| `weltenhub` Django-Settings umstellen | Niedrig | Vor Phase 2 |
| Datenmigration `bfagent_db` → `weltenhub_db` | Mittel | Vor Phase 2 |
| `bfagent_db` bereinigen | Niedrig | Nach Verifikation |

### 4.8 Migrations-Performance und Expand-Contract-Pattern

Bei 100 Mandanten × 3 Services = 300 Schema-Migrationen pro Deployment.

**Parallelisierung:**

```bash
# Nur migrieren wenn nötig
if python manage.py migrate_schemas --check 2>&1 | grep -q "unapplied migration"; then
    python manage.py migrate_schemas --executor=multiprocessing
fi
```

**Expand-Contract-Pattern** für Schema-Änderungen (verhindert Downtime):

1. **Expand:** Neue Spalte hinzufügen (nullable), Code liest beide Spalten
2. **Migrate:** Daten in neue Spalte kopieren
3. **Contract:** Alte Spalte entfernen, Code liest nur neue Spalte

**Erwartete Migrations-Dauer:**

| Anzahl Mandanten | Sequentiell | 4 Workers |
|-----------------|-------------|-----------|
| 10 | ~30 Sek | ~10 Sek |
| 50 | ~2–3 Min | ~45 Sek |
| 100 | ~5–8 Min | ~2 Min |
| 500 | ~25–40 Min | ~8 Min |

Bei 100 Mandanten auf einem 4-Core VPS: ~2 Minuten — akzeptabel. Migration Squashing alle 6 Monate empfohlen.

### 4.9 VPS-Ressourcen-Impact

PostgreSQL-Schemas sind leichtgewichtig — sie teilen sich Buffer Pool und Connections:

| Ressource | Single-Tenant | 10 Mandanten | 50 Mandanten | 100 Mandanten |
|-----------|--------------|--------------|--------------|---------------|
| DB-Connections (Pool) | ~20 | ~30 | ~50 | ~80 |
| DB Storage | 500 MB | 2 GB | 8 GB | 15 GB |
| RAM (PostgreSQL) | 2 GB | 2,5 GB | 3 GB | 4 GB |
| Migration-Dauer | 10 Sek | 30 Sek | 1,5 Min | 3 Min |
| Container-Count | Unverändert — gleiche Container, nur mehr Schemas |

**Connection Pooling ist kritisch:** PgBouncer (transaction mode) vor jeder PostgreSQL-Instanz ist Pflicht ab Phase 2.

```yaml
# docker-compose.prod.yml — PgBouncer
pgbouncer:
  image: bitnami/pgbouncer:latest
  environment:
    POSTGRESQL_HOST: db
    PGBOUNCER_POOL_MODE: transaction
    PGBOUNCER_MAX_CLIENT_CONN: 200
    PGBOUNCER_DEFAULT_POOL_SIZE: 20
  depends_on:
    - db
```

### 4.10 Skalierungsschwellen

| Schwellwert | Symptom | Nächster Schritt |
|------------|---------|-----------------|
| >50 Mandanten | DB spürbar langsamer | Hetzner Managed DB (dedizierter DB-Server) |
| >100 Mandanten | Migration >5 Min | Background-Migration, Worker-Scaling |
| >200 Mandanten | VPS reicht nicht | 2. VPS + Load Balancer |
| >500 Mandanten | Architektur-Grenze | Kubernetes oder Managed Platform |

---

## 5. Migration Tracking

Status pro Service — wird bei jedem Phase-Abschluss aktualisiert:

| Service | Phase | Status | Datum | Notizen |
|---------|-------|--------|-------|---------|
| `travel-beat` | Phase 0 (Vorbereitung) | ✅ Abgeschlossen | 2026-02-21 | `platform_context[tenants]>=0.4.0` verfügbar |
| `travel-beat` | Phase 1 (Pilot) | In Arbeit | – | Pilot-Service bestätigt |
| `risk-hub` | Phase 2 | ⬜ Ausstehend | – | Hat bereits Tenancy-Infrastruktur (ADR-035) |
| `weltenhub` | Phase 1.5 (DB-Trennung) | ⬜ Ausstehend | – | Voraussetzung für bfagent |
| `bfagent` | Phase 2 | ⬜ Ausstehend | – | Erst nach weltenhub DB-Trennung |
| `trading-hub` | Out of Scope | ➖ | – | Internes Tool, kein SaaS-Bedarf Phase 1 |
| `mcp-hub` | Out of Scope | ➖ | – | Internes Tool |
| `dev-hub` | Out of Scope | ➖ | – | Internes Tool |

---

## 6. Implementation Plan

### Phase 0: Vorbereitung ✅ ABGESCHLOSSEN (2026-02-21)

- [x] `platform_context` um `tenant_utils/` erweitern — v0.4.0 released
  - `middleware.py` — TenantPropagationMiddleware
  - `http_client.py` — TenantAwareHttpClient
  - `celery.py` — TenantAwareTask, send_cross_service_task
  - `testing.py` — tenant_a, tenant_b, tenant_a_client fixtures
  - `provisioning.py` — TenantProvisioningRequest, provision_tenant()
  - Tests: `tests/test_tenant_utils.py` (18 test cases)
- [x] Pilot-Service festgelegt: `travel-beat` (DriftTales)
- [ ] Shared DB Views in travel-beat inventarisieren
- [ ] Wildcard-DNS + SSL für `*.drifttales.app` konfigurieren
- [ ] PgBouncer-Konfiguration für travel-beat-db vorbereiten

### Phase 1: Pilot-Service — `travel-beat` (Woche 3–5)

**Voraussetzungen:** Phase 0 vollständig abgeschlossen

- [ ] `apps/tenants/` App erstellen: `Client`- und `Domain`-Model
- [ ] `SHARED_APPS` / `TENANT_APPS` in `config/settings/base.py` trennen
- [ ] `DATABASE_ENGINE` auf `django_tenants.postgresql_backend` umstellen
- [ ] `TenantMainMiddleware` als erste Middleware eintragen
- [ ] `PUBLIC_SCHEMA_URLCONF = "config.urls_public"` für `/livez/` + `/healthz/`
- [ ] Bestehende Daten in Default-Tenant-Schema `drifttales` migrieren
- [ ] `config/celery.py` auf `TenantAwareCeleryApp` umstellen
- [ ] Tenant-Isolation-Tests schreiben (aus `platform_context.tenant_utils.testing`)
- [ ] CI: Tenant-Isolation-Test als Pflicht-Gate eintragen
- [ ] Smoke-Test: 2 Mandanten parallel auf Staging
### Phase 1.5: weltenhub DB-Trennung (Woche 5–6, Voraussetzung für bfagent)

- [ ] `weltenhub_db` auf Server anlegen
- [ ] `weltenhub` Django-Settings auf neue DB umstellen
- [ ] Datenmigration `bfagent_db.weltenhub_*` → `weltenhub_db`
- [ ] `bfagent_db` bereinigen und verifizieren

### Phase 2: Weitere Services (Woche 6–9)

Reihenfolge: `risk-hub` → `bfagent` (nach Phase 1.5)

- [ ] Shared DB Views durch REST-APIs ersetzen (inkrementell)
- [ ] `TenantAwareHttpClient` in alle Service-zu-Service-Calls einbauen
- [ ] `tenant-schemas-celery` in alle Services integrieren
- [ ] PgBouncer vor jede PostgreSQL-Instanz

### Phase 3: Tenant-Management (Woche 10–12)

- [ ] Tenant-Provisionierungs-CLI (erstellt Schema in ALLEN Service-DBs)
- [ ] Tenant-Admin-Portal: User-Verwaltung, Datenexport (Art. 20 DSGVO)
- [ ] DSGVO-Dokumentation: TOM-Beschreibung Schema-Isolation
- [ ] Backup-Strategie pro Mandant (`pg_dump --schema=tenant_X`)

### Phase 4: Hardening (Woche 13–14)

- [ ] Tenant-Isolation-Tests in CI-Pipeline (KRITISCH — blockiert Merge bei Fehler)
- [ ] Load-Test mit 20+ simulierten Mandanten
- [ ] Monitoring: Mandantenspezifische Metriken (DB-Size, Request-Count)
- [ ] Migration-Performance-Optimierung (Squashing, Parallelisierung)

**Realistischer Gesamtaufwand:** 4–6 Monate bei 1 Entwickler mit parallelen Aufgaben.

---

## 7. Risiken

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Migration-Dauer explodiert bei 100+ Mandanten | Mittel | Hoch | Parallel-Executor, Skip-wenn-aktuell, Squashing alle 6 Monate |
| Shared DB Views sind schwer umzubauen | Hoch | Mittel | Inkrementell: REST-API parallel aufbauen, dann View entfernen |
| Tenant-Context geht bei Cross-Service-Call verloren | Mittel | Kritisch | `platform_context.tenant_utils`, Isolation-Tests im CI als Gate |
| VPS-Ressourcen reichen nicht (>100 Mandanten) | Niedrig | Hoch | PgBouncer, Monitoring, Migrationspfad zu Hetzner Managed DB |
| `django-tenants` Breaking Change | Niedrig | Mittel | Version pinnen, Changelog monitoren |
| Wildcard-SSL DNS-Challenge schlägt fehl | Niedrig | Mittel | Fallback: manuelle Zertifikate pro Subdomain |
| Tenant-Provisionierung in einer Service-DB schlägt fehl | Mittel | Hoch | Transaktionale Provisionierung mit Rollback-Plan |

---

## 8. Konsequenzen

### 8.1 Good

- **DSGVO-Compliance strukturell erzwungen** — kein vergessener Filter möglich
- **Recht auf Löschung (Art. 17):** `DROP SCHEMA tenant_X CASCADE` — vollständig und auditierbar
- **Datenportabilität (Art. 20):** `pg_dump --schema=tenant_X` — standardisierter Export
- **Backup pro Mandant:** Granulares Restore ohne andere Mandanten zu beeinflussen
- **Skalierung bis 100+ Mandanten** auf einem VPS mit PgBouncer
- **Kein Anwendungscode-Overhead** — `django-tenants` handhabt `search_path` transparent

### 8.2 Bad

- **Migrations-Komplexität:** N Mandanten × M Services Migrationen pro Deployment
- **Wildcard-DNS/SSL:** Ops-Aufwand für DNS-Challenge-Zertifikate
- **Tenant-Provisionierung:** Muss in allen Service-DBs koordiniert werden
- **Shared DB Views:** Müssen durch REST-APIs ersetzt werden (Latenz-Overhead)
- **`django-tenants` Dependency:** Externe Library mit eigenem Release-Zyklus

### 8.3 Nicht in Scope

- `trading-hub` und `mcp-hub` — interne Tools, kein SaaS-Bedarf in Phase 1
- Kubernetes oder Managed Cloud — explizit ausgeschlossen für Phase 1–2
- Mandantenspezifische Preismodelle / Billing-System — separates ADR
- Mandantenspezifische Konfiguration (Feature Flags) — separates ADR

---

## 9. Confirmation

Compliance mit diesem ADR wird wie folgt verifiziert:

1. **CI-Gate (Pflicht):** Tenant-Isolation-Test in jedem SaaS-Service — blockiert Merge bei Fehler (ADR-058)
2. **Linter-Check:** `ruff`/`grep` prüft auf direktes `.filter(tenant_id=...)` in `TENANT_APPS` — verboten nach Migration
3. **Migration-Tracking-Tabelle** (§5 dieses ADR) wird bei jedem Phase-Abschluss aktualisiert
4. **Deployment-Check:** `migrate_schemas --check` im Deploy-Step — schlägt fehl wenn unapplied Migrations existieren
5. **DSGVO-Verifikation:** `DROP SCHEMA tenant_test CASCADE` + Restore-Test im Staging vor jedem Produktions-Onboarding

---

## 10. Validation Criteria

### Phase 1 (Pilot)

- [ ] 2 Mandanten laufen parallel ohne Datenleck (Isolation-Test grün)
- [ ] `pg_dump --schema=tenant_X` liefert vollständigen Mandanten-Export
- [ ] `DROP SCHEMA tenant_X CASCADE` entfernt alle Mandantendaten
- [ ] CI-Pipeline enthält Tenant-Isolation-Test als Pflicht-Gate

### Phase 2 (Alle Services)

- [ ] Alle Shared DB Views durch REST-APIs ersetzt
- [ ] Cross-Service-Celery-Tasks propagieren Tenant-Context korrekt
- [ ] Tenant-Isolation-Tests für alle Services grün

### Phase 3 (Tenant-Management)

- [ ] Neuer Mandant wird in < 60 Sekunden in allen Service-DBs provisioniert
- [ ] DSGVO-Anfragen (Löschung, Export) vollständig automatisierbar

### Phase 4 (Hardening)

- [ ] Load-Test: 20 simultane Mandanten ohne Performance-Degradation
- [ ] Migrations-Dauer bei 50 Mandanten < 2 Minuten (4 Workers)

---

## 11. More Information

- [django-tenants Dokumentation](https://django-tenants.readthedocs.io/)
- [tenant-schemas-celery](https://github.com/maciej-gol/tenant-schemas-celery)
- ADR-021: Unified Deployment Architecture (Nginx retained, Traefik deferred)
- ADR-035: Shared Django Tenancy Package (Row-Level-Basis, bleibt gültig für interne Tools)
- ADR-042: Development Environment & Deployment Workflow
- ADR-045: Secrets & Environment Management
- ADR-057: Traefik-Einführung (reserviert, deferred)
- ADR-058: Platform Test Taxonomy
- Konzeptpapier: Multi-Tenancy für das Multi-Repo Django-Portfolio (2026-02-20, Achim Dehnert)

---

## 12. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-21 | Achim Dehnert | Initial: Status Proposed |
| 2026-02-21 | Achim Dehnert | Review-Fixes: YAML-Frontmatter, Decision Drivers, Traefik→Nginx, weltenhub DB-Trennung, Health-Endpoints, Confirmation, Migration-Tracking |
| 2026-02-21 | Achim Dehnert | Accepted: VPS-Ressourcen-Tabelle, Skalierungsschwellen, platform_context tenant_utils Struktur, Expand-Contract-Pattern, TenantAwareHttpClient vollständig, PgBouncer Compose-Snippet |
| 2026-02-21 | Achim Dehnert | Phase 0 abgeschlossen: platform_context v0.4.0 tenant_utils/ shipped, travel-beat als Pilot bestätigt |
