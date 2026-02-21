---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
consulted: –
informed: –
---

# ADR-056: Adopt PostgreSQL Schema Isolation for SaaS Multi-Tenancy

| Attribut       | Wert                                                                 |
|----------------|----------------------------------------------------------------------|
| **Status**     | Proposed                                                             |
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

Das Portfolio besteht aus mehreren unabhängigen Django/HTMX-Services (bfagent, cad-hub, travel-beat, trading-hub, risk-hub u.a.), die jeweils auf einem einzelnen Hetzner VPS laufen. Jeder Service hat seine eigene PostgreSQL-Datenbank und kommuniziert über drei Kanäle:

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
- **Nginx** auf Prod-Server (88.198.191.108) proxied zu Dev-Server (46.225.113.1)
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

Service-zu-Service-Calls über das interne Docker-Netzwerk (nicht über Subdomain) nutzen einen `X-Tenant-Schema`-Header:

```python
# In platform_context/tenant_utils/http_client.py
class TenantAwareHttpClient:
    def _headers(self) -> dict:
        from django.db import connection
        return {"X-Tenant-Schema": connection.schema_name}
```

**Kanal 2: Shared DB Views**

Bestehende Cross-DB-Views werden durch REST-API-Calls ersetzt (Option 2a). Für Performance-kritische Fälle: Materialized Views per Celery-Sync im lokalen Tenant-Schema.

**Kanal 3: Celery Tasks**

`tenant-schemas-celery` serialisiert den Schema-Namen automatisch in die Celery-Message. Cross-Service-Tasks übergeben `_tenant_schema` im Payload.

### 4.4 Wildcard-DNS und SSL

Subdomain-basiertes Routing (`tenant1.bfa.example.com`) erfordert:
- Wildcard-DNS-Eintrag (`*.bfa.example.com → 88.198.191.108`)
- Wildcard-SSL via Let's Encrypt DNS-Challenge (nicht HTTP-Challenge)
- **Nginx** als Wildcard-Reverse-Proxy (ADR-021 §2.10: Traefik deferred — gilt weiterhin)

```nginx
# /etc/nginx/sites-enabled/bfa-wildcard.conf
server {
    listen 443 ssl;
    server_name ~^(?<tenant>[^.]+)\.bfa\.example\.com$;
    ssl_certificate /etc/letsencrypt/live/bfa.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bfa.example.com/privkey.pem;
    location / {
        proxy_pass http://46.225.113.1:8000;
        proxy_set_header Host $host;  # django-tenants liest Host-Header
    }
}
```

**Traefik bleibt deferred** gemäß ADR-021. Eine Traefik-Einführung erfordert ein eigenes ADR (ADR-057 reserviert). Ops-Task: Wildcard-Certbot-DNS-Challenge in ADR-042-Checkliste ergänzen.

### 4.5 Health-Endpoints bei Subdomain-Routing

`/livez/` und `/healthz/` (ADR-021 §2.8) müssen im `public`-Schema laufen, nicht im Tenant-Schema. `django-tenants` bietet dafür `PUBLIC_SCHEMA_URLCONF`:

```python
# config/settings/base.py
PUBLIC_SCHEMA_URLCONF = "config.urls_public"  # enthält /livez/ + /healthz/
ROOT_URLCONF = "config.urls_tenant"           # tenant-spezifische URLs
```

Health-Endpoints antworten damit unabhängig vom Tenant-Context — kein Einfluss auf bestehende Deployment-Pipeline.

### 4.6 weltenhub/bfagent Shared Database

`weltenhub` und `bfagent` teilen aktuell `bfagent_db` (dokumentiert in ADR-035). Dies ist eine **Voraussetzung** für die Schema-Isolation in `bfagent`:

**Pflicht vor Phase 2 (`bfagent`):** `weltenhub` muss in eine eigene Datenbank (`weltenhub_db`) migriert werden. Solange `weltenhub` und `bfagent` dieselbe DB teilen, kann `bfagent` keine Schema-Isolation einführen — `django-tenants` erwartet exklusive Kontrolle über die DB-Schemas.

| Schritt | Aufwand | Zeitpunkt |
|---------|---------|----------|
| `weltenhub_db` anlegen | Niedrig | Vor Phase 2 |
| `weltenhub` Django-Settings auf neue DB umstellen | Niedrig | Vor Phase 2 |
| Datenmigration `bfagent_db` → `weltenhub_db` | Mittel | Vor Phase 2 |
| `bfagent_db` bereinigen | Niedrig | Nach Verifikation |

Dieser Schritt ist **nicht optional** und wird als Phase 1.5 in den Implementation Plan aufgenommen.

### 4.7 Migrations-Performance

Bei 100 Mandanten × 3 Services = 300 Schema-Migrationen pro Deployment. Der Self-Hosted Runner läuft auf demselben VPS — Migrations-Parallelisierung darf CPU nicht saturieren (max. 2 Workers in CI, 4 Workers im manuellen Deploy):

```bash
# Parallelisierung via multiprocessing executor
python manage.py migrate_schemas --executor=multiprocessing
# Nur wenn nötig
python manage.py migrate_schemas --check 2>&1 | grep -q "unapplied" && \
  python manage.py migrate_schemas --executor=multiprocessing
```

Erwartete Dauer bei 100 Mandanten, 4 Workers: ~2 Minuten. Akzeptabel für Deployment-Fenster.

---

## 5. Migration Tracking

Status pro Service — wird bei jedem Phase-Abschluss aktualisiert:

| Service | Phase | Status | Datum | Notizen |
|---------|-------|--------|-------|---------|
| `cad-hub` | Phase 1 (Pilot) | ⬜ Ausstehend | – | Einfachste Struktur, keine Shared Views |
| `travel-beat` | Phase 2 | ⬜ Ausstehend | – | – |
| `risk-hub` | Phase 2 | ⬜ Ausstehend | – | Hat bereits Tenancy-Infrastruktur (ADR-035) |
| `weltenhub` | Phase 1.5 (DB-Trennung) | ⬜ Ausstehend | – | Voraussetzung für bfagent |
| `bfagent` | Phase 2 | ⬜ Ausstehend | – | Erst nach weltenhub DB-Trennung |
| `trading-hub` | Out of Scope | ➖ | – | Internes Tool, kein SaaS-Bedarf Phase 1 |
| `mcp-hub` | Out of Scope | ➖ | – | Internes Tool, kein SaaS-Bedarf Phase 1 |
| `dev-hub` | Out of Scope | ➖ | – | Internes Tool |

---

## 6. Implementation Plan

### Phase 0: Vorbereitung (Woche 1–2)

- [ ] `platform_context` um `tenant_utils/` erweitern (Middleware, HTTP-Client, Celery-Helpers, Test-Fixtures)
- [ ] Shared DB Views inventarisieren (alle Services)
- [ ] Wildcard-DNS + SSL für Pilot-Domain konfigurieren
- [ ] PgBouncer-Konfiguration für alle Service-DBs vorbereiten

### Phase 1: Pilot-Service — `cad-hub` (Woche 3–5)

Pilot: **`cad-hub`** (einfachste Datenstruktur, keine Shared DB Views)

- [ ] `django-tenants` + `tenant-schemas-celery` installieren
- [ ] `Client`- und `Domain`-Model im `public`-Schema
- [ ] `SHARED_APPS` / `TENANT_APPS` trennen
- [ ] Bestehende Daten in Default-Tenant-Schema migrieren
- [ ] Tenant-Isolation-Tests schreiben und in CI integrieren
- [ ] Smoke-Test: 2 Mandanten parallel auf Staging

### Phase 1.5: weltenhub DB-Trennung (Woche 5–6, Voraussetzung für bfagent)

- [ ] `weltenhub_db` auf dev-server anlegen
- [ ] `weltenhub` Django-Settings auf neue DB umstellen
- [ ] Datenmigration `bfagent_db.weltenhub_*` → `weltenhub_db`
- [ ] `bfagent_db` bereinigen und verifizieren

### Phase 2: Weitere Services (Woche 6–9)

Reihenfolge nach Komplexität: `travel-beat` → `risk-hub` → `bfagent` (nach Phase 1.5)

- [ ] Shared DB Views durch REST-APIs ersetzen (inkrementell: erst API parallel, dann View entfernen)
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
| Tenant-Context geht bei Cross-Service-Call verloren | Mittel | Kritisch | `platform_context` Shared Library, Isolation-Tests im CI als Gate |
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

### Phase 1 (Pilot cad-hub)

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
- ADR-058: Multi-Tenancy Testing-Strategie
- Konzeptpapier: Multi-Tenancy für das Multi-Repo Django-Portfolio (2026-02-20, Achim Dehnert)

---

## 12. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-21 | Achim Dehnert | Initial: Status Proposed |
| 2026-02-21 | Achim Dehnert | Review-Fixes: YAML-Frontmatter, Decision Drivers, Traefik→Nginx, weltenhub DB-Trennung, Health-Endpoints, Confirmation, Migration-Tracking |
