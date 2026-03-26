---
status: "accepted"
date: 2026-03-26
updated: 2026-03-26
version: 2
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related:
  - ADR-022-platform-consistency-standard.md
  - ADR-045-secrets-management.md
  - ADR-050-platform-decomposition-hub-landscape.md
  - ADR-072-multi-tenancy-schema-isolation.md
  - ADR-075-deployment-execution-strategy.md
  - ADR-078-docker-healthcheck-convention.md
  - ADR-146-package-consolidation-strategy.md
  - ADR-148-recruiting-hub-architecture.md
implementation_status: partial
implementation_evidence:
  - "v2: Review-Findings B1-B3 + S1-S10 eingearbeitet (ADR-149-review.md)"
review_status: "reviewed — v1 reviewed, v2 addresses all findings from ADR-149-review.md"
staleness_months: 12
drift_check_paths:
  - packages/dvelop-client/
  - dms-hub/
---

# ADR-149: Adopt d.velop Cloud DMS as Platform Document Archive Service (dms-hub)

## Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| v1 | 2026-03-26 | Initialer Entwurf — 2-Schicht-Architektur (Package + Hub) |
| v2 | 2026-03-26 | Review-Findings: B1 depends_on, B2 migrate-Service, B3 FileField/Blob-Storage, S1–S10 (Auth, Consumer-Resilience, Open Questions, Schema-Isolation, PII) |

---

## Decision Drivers

- **Gesetzliche Aufbewahrungspflicht**: DSGVO Art. 5(2), ArbSchG §3, GoBD §147 AO verlangen revisionssichere, unveränderliche Dokumentenablage — Hub-Datenbanken allein sind hierfür ungeeignet.
- **Behördenkunde Landratsamt**: Erster Produktiv-Mandant betreibt d.velop DMS on-premises und erwartet alle Compliance-Dokumente darin.
- **Mehrere Consumer-Hubs**: risk-hub (Compliance), billing-hub (Rechnungen), recruiting-hub (Verträge) benötigen DMS-Archivierung — eine eingebettete App pro Hub wäre Codeduplizierung.
- **d.velop REST API verfügbar**: IIL hat d.velop Cloud gebucht (`https://iil.d-velop.cloud/`); API produktionsreif (JSON-HAL, Bearer-Auth, Webhook-Support).
- **Entkopplung von Paperless-ngx**: Paperless-ngx (ADR-144) ist für IIL-interne Dokumente. d.velop ist für behördliche/kundenseitige revisionssichere Archivierung.
- **Platform-Konsistenz**: Neuer Hub nach ADR-050-Pattern, neues Package nach ADR-146-Pattern.

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand

Mehrere Platform-Hubs erzeugen Dokumente die revisionssicher archiviert werden müssen:

| Hub | Dokumenttypen | Volumen/Monat |
|-----|--------------|---------------|
| **risk-hub** | Datenschutz-Audits, Datenpannen-Meldungen, Gefährdungsbeurteilungen, Jahresberichte, VVT | 10–50 |
| **billing-hub** | Rechnungen, Gutschriften, Mahnungen | 50–200 |
| **recruiting-hub** | Arbeitsverträge, Zeugnisse, Datenschutzerklärungen | 10–30 |

Diese Dokumente werden als PDF exportiert, existieren aber nicht in einem revisionssicheren Archiv außerhalb der jeweiligen Hub-Datenbank.

### 1.2 Auslösendes Ereignis

Ein Landratsamt beauftragt IIL mit dem Betrieb der risk-hub Compliance-Plattform. Der Kunde betreibt d.velop d.3ecm als zertifiziertes DMS und erwartet automatische Archivierung aller Compliance-Dokumente.

### 1.3 Technische Rahmenbedingungen

```
Consumer-Hubs (risk-hub, billing-hub, ...)
    │
    │  REST API (intern, Hub-zu-Hub)
    ▼
dms-hub (Django 5, Celery, PostgreSQL 16)
    │
    │  iil-dvelop-client (httpx)
    ▼
d.velop Cloud REST API
    https://iil.d-velop.cloud/
    Auth: Bearer Token
    Format: JSON-HAL
```

---

## 2. Considered Options

### Option A — Eigener dms-hub als Platform-Service + iil-dvelop-client Package (empfohlen)

Zwei-Schicht-Architektur:
1. **`iil-dvelop-client`** — Reines Python-Package (httpx) für die d.velop REST API
2. **`dms-hub`** — Django Service-Hub der Archivierung orchestriert, Audit-Trail führt und Consumer-API bereitstellt

### Option B — Eingebettete `dms_archive` App in risk-hub

Eine Django-App innerhalb von risk-hub (wie im Input-Dokument ADR-XXX vorgeschlagen). Jeder weitere Consumer müsste die App duplizieren.

### Option C — Shared Package `iil-dms-archive` ohne Hub

Ein installierbares Django-Package das in jeden Consumer-Hub eingebettet wird. Jeder Hub bringt eigenen Celery-Worker, eigene DB-Tabellen, eigene Konfiguration mit.

### Option D — Direkter d.velop-Client pro Hub (kein zentraler Service)

Jeder Hub implementiert seinen eigenen httpx-Client. Keine zentrale Konfiguration, kein gemeinsamer Audit-Trail.

---

## 3. Decision Outcome

**Gewählt: Option A** — Eigener dms-hub als Platform-Service + iil-dvelop-client Package.

### 3.1 Begründung

1. **Single Responsibility**: DMS-Archivierung ist eine Platform-Querschnittsfunktion — kein Belang eines einzelnen Hubs. Analog zu billing-hub (Zahlungen) oder notifications (Benachrichtigungen).

2. **N Consumer, 1 Service**: risk-hub, billing-hub, recruiting-hub und zukünftige Hubs rufen eine einzige REST-API auf. Kein Copy-Paste von Celery-Tasks, Models, und d.velop-Konfiguration.

3. **Zentraler Audit-Trail**: Alle Archivierungen aller Hubs in einer Tabelle — mandantenfähig, durchsuchbar, mit Retry-Management.

4. **Mandantenfähige DMS-Konfiguration**: Tenant A nutzt d.velop Cloud, Tenant B hat d.velop on-premises, Tenant C hat (zukünftig) DocuWare. Die `DmsConnection`-Tabelle im dms-hub macht das möglich — in einem embedded Package wäre das nicht sinnvoll.

5. **Package + Hub Synergie**: Das `iil-dvelop-client` Package ist auch ohne den Hub nutzbar (z.B. in MCP-Servern, Scripts, Tests). Der Hub nutzt das Package intern.

### 3.2 Abgewiesene Alternativen

| Option | Hauptablehnungsgrund |
|--------|----------------------|
| B — embedded in risk-hub | Nicht reusable; jeder weitere Consumer dupliziert Code. RiskHubPdfExporter ist hartcodiert auf risk-hub Domain-Models. |
| C — shared Package | Jeder Hub braucht eigenen Celery-Worker + eigene DB-Tabellen für denselben Zweck. Mandanten-übergreifende Konfiguration unmöglich. |
| D — Client pro Hub | Maximale Codeduplizierung, kein zentraler Audit-Trail, kein Retry-Management. |

---

## 4. Pros and Cons of the Options

### Option A — dms-hub + iil-dvelop-client ✅

**Pro:**
- Single source of truth für alle DMS-Archivierungen (1 DB, 1 Audit-Trail)
- Consumer-Hubs brauchen nur 5 Zeilen HTTP-Call statt eigener Celery-Infrastruktur
- Mandantenfähige DMS-Konfiguration (d.velop Cloud vs. on-premises vs. andere Provider)
- `iil-dvelop-client` Package unabhängig testbar und nutzbar (MCP, Scripts)
- Zentrales Retry-Management und Monitoring-Dashboard
- Provider-Abstraktion: zukünftig DocuWare/ELO/SharePoint hinter gleicher API

**Con:**
- Neues Repo + neuer Docker-Stack (Web + Worker + DB + Redis = 5 Container)
- Hub-zu-Hub Kommunikation mit Auth und Timeout/Retry-Handling
- Bei dms-hub-Ausfall: Archivierungen stauen sich (aber Consumer-Hubs laufen weiter)

### Option B — embedded in risk-hub

**Pro:**
- Keine neue Infrastruktur; risk-hub Celery-Worker übernimmt
- Einfachster PoC für einen einzelnen Consumer

**Con:**
- Nicht reusable: billing-hub/recruiting-hub müssten App duplizieren
- `RiskHubPdfExporter` hartcodiert auf `dsb.models`, `risk.models`
- Mandanten-Konfiguration nur für risk-hub-Mandanten

### Option C — Shared Package

**Pro:**
- Einmal implementieren, überall installieren
- Kein Hub-zu-Hub-Network-Call

**Con:**
- Jeder Hub: eigener Worker, eigene DB-Tabellen, eigene DMS-Config
- Kein zentraler Audit-Trail über alle Hubs
- Package muss Django-Migrations mitbringen (komplex)

### Option D — Client pro Hub

**Pro:**
- Maximale Unabhängigkeit

**Con:**
- Maximale Codeduplizierung
- Kein zentrales Monitoring, kein gemeinsamer Audit-Trail

---

## 5. Architecture

### 5.1 Schicht 1: iil-dvelop-client (Platform-Package)

```
platform/packages/dvelop-client/
├── pyproject.toml               # iil-dvelop-client, Python ≥3.11
├── src/dvelop_client/
│   ├── __init__.py              # Public API Exports
│   ├── client.py                # DvelopClient (httpx, sync+async)
│   ├── auth.py                  # BearerAuth + Origin-Header (CSRF)
│   ├── models.py                # Pydantic v2: Repository, DmsObject, Category, BlobRef
│   ├── exceptions.py            # DvelopError, AuthError, RateLimitError, NotFoundError
│   └── hal.py                   # JSON-HAL Response Parser (_links, _embedded)
└── tests/
    ├── test_client.py           # pytest-httpx: Upload, List, Search
    ├── test_auth.py             # Header-Konstruktion
    └── test_hal.py              # HAL-Parsing Edge Cases
```

**Public API:**

```python
from dvelop_client import DvelopClient, DvelopError, Repository, DmsObject

async with DvelopClient(base_url="https://iil.d-velop.cloud", api_key="...") as client:
    # Repositories auflisten
    repos = await client.list_repositories()

    # Dokument archivieren (2-Step: Blob + Object)
    doc = await client.upload_document(
        repo_id="...",
        filename="Audit_2026-03-01.pdf",
        content=pdf_bytes,
        category="DSGVO_AUDIT",
        properties={"Mandant": "Landratsamt", "Datum": "2026-03-01"},
    )
    print(doc.id, doc.location_uri)

    # Dokument suchen
    results = await client.search(repo_id="...", query="Datenpanne 2026")

    # Kategorien abfragen
    categories = await client.list_categories(repo_id="...")
```

**d.velop Upload-Sequenz (API v2.15):**

```
1. POST /dms/r/{repo_id}/b
   Body: raw PDF bytes
   Headers: Content-Disposition: attachment; filename="..."
   Response: 201, Location: /dms/r/{id}/b/{blob_id}

2. POST /dms/r/{repo_id}/o
   Body: {"sourceCategory": "...", "sourceProperties": [...],
          "contentLocationUri": "/dms/r/{repo_id}/b/{blob_id}"}
   Response: 201, Location: /dms/r/{id}/o/{doc_id}
```

**Pflicht-Header:**

```python
# Alle Requests:
Authorization: Bearer {api_key}
Accept: application/hal+json

# Schreibende Requests (POST/PUT/DELETE/PATCH) — CSRF:
Origin: https://iil.d-velop.cloud
Content-Type: application/hal+json
```

### 5.2 Schicht 2: dms-hub (Django Service-Hub)

```
dms-hub/
├── config/
│   ├── settings/
│   │   ├── base.py              # INSTALLED_APPS, CELERY, etc.
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── apps/
│   ├── common/                  # Health endpoints (/livez/, /healthz/)
│   ├── connections/
│   │   ├── models.py            # DmsConnection (Tenant → d.velop Config)
│   │   ├── services.py          # ConnectionService
│   │   └── admin.py             # Django Admin für Konfiguration
│   ├── categories/
│   │   ├── models.py            # DmsCategoryMapping (Tenant → Kategorie-IDs)
│   │   ├── services.py          # CategoryService
│   │   └── admin.py
│   └── archive/
│       ├── models.py            # DmsArchiveRecord (Audit-Trail)
│       ├── services.py          # ArchiveService (schedule, retry, status)
│       ├── tasks.py             # Celery: archive_to_dms (Queue: "dms")
│       ├── api.py               # Django Ninja: Consumer-API
│       └── admin.py             # Admin: Status, Failed, Retry
├── docker/app/Dockerfile        # Multi-stage, python:3.12-slim, non-root
├── docker-compose.prod.yml
├── requirements.txt
└── scripts/ship.sh
```

### 5.3 Models (BigAutoField — ADR-022)

```python
# apps/connections/models.py
class DmsConnection(models.Model):
    """Tenant-spezifische DMS-Verbindungskonfiguration."""
    tenant_id       = models.UUIDField(unique=True, db_index=True)
    tenant_name     = models.CharField(max_length=200)
    provider        = models.CharField(max_length=20, default="dvelop")  # Zukunft: docuware, elo
    base_url        = models.URLField()                # https://iil.d-velop.cloud
    repo_id         = models.CharField(max_length=100)
    api_key_env_var = models.CharField(max_length=100, default="DVELOP_API_KEY")
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dms_connection"


# apps/categories/models.py
class DmsCategoryMapping(models.Model):
    """Mapping: lokaler Dokumenttyp → d.velop Kategorie-ID pro Tenant."""
    connection      = models.ForeignKey("connections.DmsConnection", on_delete=models.CASCADE)
    source_type     = models.CharField(max_length=50)  # PRIVACY_AUDIT, INVOICE, ...
    dvelop_category = models.CharField(max_length=100)  # Tatsächliche d.velop Kategorie-ID
    is_active       = models.BooleanField(default=True)

    class Meta:
        db_table = "dms_category_mapping"
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "source_type"],
                name="uq_category_per_connection_type",
            ),
        ]


# apps/archive/models.py
class DmsArchiveRecord(models.Model):
    """Lückenloser Audit-Trail jeder DMS-Archivierung."""

    class Status(models.TextChoices):
        PENDING  = "PENDING",  "Ausstehend"
        SUCCESS  = "SUCCESS",  "Erfolgreich"
        FAILED   = "FAILED",   "Fehlgeschlagen"
        RETRYING = "RETRYING", "Wird wiederholt"

    tenant_id         = models.UUIDField(db_index=True)
    source_hub        = models.CharField(max_length=50)    # risk-hub, billing-hub, ...
    source_type       = models.CharField(max_length=50)    # PRIVACY_AUDIT, INVOICE, ...
    source_id         = models.CharField(max_length=255)   # ID im Consumer-Hub
    source_label      = models.CharField(max_length=500)
    file_name         = models.CharField(max_length=255)
    file              = models.FileField(upload_to="dms_archive/%Y/%m/", max_length=500)
    file_size_bytes   = models.PositiveIntegerField(default=0)
    properties        = models.JSONField(default=dict, blank=True, help_text="Freitext-Metadaten für d.velop")

    # DMS-Seite (nach Upload befüllt)
    dms_document_id   = models.CharField(max_length=255, blank=True, db_index=True)
    dms_repository_id = models.CharField(max_length=255, blank=True)
    dms_category      = models.CharField(max_length=100, blank=True)

    # Status
    status            = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    retry_count       = models.PositiveSmallIntegerField(default=0)
    error_message     = models.TextField(blank=True)

    # Wer / Wann
    requested_by      = models.CharField(max_length=255, blank=True)  # User oder Service
    celery_task_id    = models.CharField(max_length=255, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dms_archive_record"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "source_hub", "status"]),
            models.Index(fields=["tenant_id", "source_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "source_id", "status"],
                condition=models.Q(status="SUCCESS"),
                name="uq_dmsarchive_one_success_per_source",
            ),
        ]
```

### 5.4 Consumer-API (Django Ninja)

```
POST /api/v1/archive/
  Body: multipart/form-data
    - tenant_id: UUID
    - source_hub: str         (risk-hub, billing-hub)
    - source_type: str        (PRIVACY_AUDIT, INVOICE)
    - source_id: str          (ID im Consumer)
    - source_label: str       (Lesbarer Titel)
    - file: UploadedFile      (PDF bytes)
    - properties: JSON        (Optional: Freitext-Metadaten)
    - requested_by: str       (User-ID oder Service-Name)
  Response: 201 {"record_id": 42, "status": "PENDING"}

GET /api/v1/archive/{record_id}/
  Response: {"record_id": 42, "status": "SUCCESS", "dms_document_id": "..."}

GET /api/v1/archive/?tenant_id={uuid}&source_id={id}
  Response: Status für ein bestimmtes Quell-Dokument

POST /api/v1/archive/{record_id}/retry/
  Response: {"record_id": 42, "status": "RETRYING"}

GET /api/v1/archive/failed/?tenant_id={uuid}
  Response: Liste aller fehlgeschlagenen Archivierungen

GET /api/v1/connections/?tenant_id={uuid}
  Response: DMS-Verbindungs-Info (ohne API-Key)
```

**Auth**: Service-to-Service via `Authorization: Bearer {DMS_HUB_TOKEN}`. Jeder Consumer-Hub erhält einen eigenen Token (generiert via `secrets.token_urlsafe(32)`, gespeichert in `.env.prod` beider Hubs). dms-hub validiert den Token gegen eine Whitelist in seiner `.env.prod` (`DMS_HUB_ALLOWED_TOKENS`). Kein User-Auth nötig.

### 5.5 Consumer-Integration (risk-hub Beispiel)

```python
# risk-hub: src/dms_archive/client.py (dünn, ~30 Zeilen)
import httpx
import logging
from decouple import config

logger = logging.getLogger(__name__)

DMS_HUB_URL = config("DMS_HUB_URL", default="http://dms-hub-web:8000")
DMS_HUB_TOKEN = config("DMS_HUB_TOKEN")

class DmsHubClient:
    @staticmethod
    def archive(tenant_id, source_type, source_id, label, pdf_bytes, filename, properties=None):
        try:
            response = httpx.post(
                f"{DMS_HUB_URL}/api/v1/archive/",
                headers={"Authorization": f"Bearer {DMS_HUB_TOKEN}"},
                data={
                    "tenant_id": str(tenant_id),
                    "source_hub": "risk-hub",
                    "source_type": source_type,
                    "source_id": str(source_id),
                    "source_label": label,
                    "properties": json.dumps(properties or {}),
                    "requested_by": "risk-hub-service",
                },
                files={"file": (filename, pdf_bytes, "application/pdf")},
                timeout=10.0,  # kurzer Timeout — dms-hub queued intern
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("DMS-Hub Archivierung fehlgeschlagen: %s %s", type(exc).__name__, exc)
            return None  # Graceful degradation — Consumer läuft weiter
```

```python
# risk-hub: src/dms_archive/tasks.py (Consumer-seitiger Celery-Task)
from celery import shared_task
from src.dms_archive.client import DmsHubClient

@shared_task(bind=True, max_retries=3, default_retry_delay=120, queue="default")
def send_to_dms_hub(self, *, tenant_id, source_type, source_id, label, pdf_bytes, filename, properties=None):
    """Consumer-seitiger Retry: bei dms-hub-Ausfall wird automatisch wiederholt."""
    result = DmsHubClient.archive(tenant_id, source_type, source_id, label, pdf_bytes, filename, properties)
    if result is None:
        raise self.retry(exc=Exception("dms-hub nicht erreichbar"))
    return result
```

```python
# risk-hub: src/dsb/services/audit_service.py — am Ende von finalize_audit()
from src.dms_archive.tasks import send_to_dms_hub

pdf_bytes = DsbReportService.export_audit_pdf(audit)
transaction.on_commit(lambda: send_to_dms_hub.delay(
    tenant_id=str(audit.tenant_id),
    source_type="PRIVACY_AUDIT",
    source_id=str(audit.id),
    label=f"Datenschutz-Audit {audit.mandate.name} {audit.audit_date:%Y-%m-%d}",
    pdf_bytes=pdf_bytes,
    filename=f"Audit_{audit.audit_date:%Y-%m-%d}.pdf",
    properties={"Mandant": audit.mandate.name, "Audit-Datum": audit.audit_date.isoformat()},
))
```

### 5.6 Celery Task (dms-hub intern)

```python
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="dms",
    acks_late=True,
    reject_on_worker_lost=True,
)
def archive_to_dms(self, *, record_id: int) -> dict:
    record = DmsArchiveRecord.objects.get(id=record_id)
    connection = DmsConnection.objects.get(tenant_id=record.tenant_id, is_active=True)
    category = DmsCategoryMapping.objects.get(
        connection=connection, source_type=record.source_type,
    ).dvelop_category

    api_key = config(connection.api_key_env_var)

    from dvelop_client import DvelopClient
    with DvelopClient(base_url=connection.base_url, api_key=api_key) as client:
        doc = client.upload_document_sync(
            repo_id=connection.repo_id,
            filename=record.file_name,
            content=record.file.read(),  # FileField → bytes
            category=category,
            properties=record.properties,
        )
    record.dms_document_id = doc.id
    record.dms_repository_id = connection.repo_id
    record.dms_category = category
    record.status = DmsArchiveRecord.Status.SUCCESS
    record.error_message = ""
    record.save(update_fields=[
        "dms_document_id", "dms_repository_id", "dms_category",
        "status", "error_message", "updated_at",
    ])
```

### 5.7 Docker Compose

```yaml
# docker-compose.prod.yml
# COMPOSE_PROJECT_NAME=dms-hub (in .env)

x-common: &common
  image: ghcr.io/achimdehnert/dms-hub:${IMAGE_TAG:-latest}
  env_file: .env.prod
  restart: unless-stopped
  logging:
    driver: json-file
    options: { max-size: "10m", max-file: "3" }

services:
  dms-hub-migrate:
    <<: *common
    container_name: dms_hub_migrate
    command: python manage.py migrate --noinput
    depends_on:
      dms-hub-db: { condition: service_healthy }
    restart: "no"

  dms-hub-web:
    <<: *common
    container_name: dms_hub_web
    command: gunicorn config.wsgi:application -b 0.0.0.0:8000 -w 2
    ports: ["8107:8000"]
    volumes: ["dms_hub_media:/app/media"]
    depends_on:
      dms-hub-db: { condition: service_healthy }
      dms-hub-redis: { condition: service_healthy }
      dms-hub-migrate: { condition: service_completed_successfully }
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    deploy:
      resources:
        limits:
          memory: 512M

  dms-hub-worker:
    <<: *common
    container_name: dms_hub_worker
    command: celery -A config worker -Q dms -c 2 -l info --without-gossip
    volumes: ["dms_hub_media:/app/media"]
    depends_on:
      dms-hub-db: { condition: service_healthy }
      dms-hub-redis: { condition: service_healthy }
      dms-hub-migrate: { condition: service_completed_successfully }
    healthcheck:
      test: ["CMD", "sh", "-c", "pidof python3.12"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 512M

  dms-hub-db:
    image: postgres:16-alpine
    container_name: dms_hub_db
    env_file: .env.prod
    shm_size: 128m
    volumes: ["dms_hub_pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 10s
      timeout: 5s
      retries: 5

  dms-hub-redis:
    image: redis:7-alpine
    container_name: dms_hub_redis
    command: redis-server --requirepass $${REDIS_PASSWORD}
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "$${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  dms_hub_pgdata:
  dms_hub_media:
```

---

## 6. Sicherheitsanalyse

### 6.1 API-Key-Management

Der d.velop API-Key wird ausschließlich via `decouple.config()` aus `.env.prod` geladen (ADR-045). **Niemals** als Klartext in Settings, Compose oder Code.

Minimale Berechtigungen im d.velop-System:
- `dms:read` (Repository-Listing, Kategorie-Abfrage, Suche)
- `dms:write` (Blob-Upload + DMS-Objekt-Anlage)
- **Kein** `admin`, **kein** `delete`, **kein** `user-management`

Key-Rotation: mindestens jährlich, nach jedem Mitarbeiter-Offboarding.

### 6.2 Hub-zu-Hub Auth

Consumer-Hubs authentifizieren sich am dms-hub via `Authorization: Bearer {token}` (shared secret pro Consumer). Jeder Consumer erhält einen eigenen Token. dms-hub validiert gegen `DMS_HUB_ALLOWED_TOKENS` (kommaseparierte Liste in `.env.prod`). Token-Rotation: mindestens jährlich, nach jedem Consumer-Offboarding.

### 6.3 CSRF-Schutz (d.velop)

d.velop erfordert `Origin`-Header bei allen schreibenden Requests. Der `iil-dvelop-client` setzt diesen automatisch basierend auf `base_url`.

### 6.4 Datenschutz

Alle übertragenen PDFs enthalten potentiell personenbezogene Daten. Übertragung ausschließlich über HTTPS (TLS 1.2+). Zwischen Consumer-Hub und dms-hub: Docker-internes Netzwerk (kein Internet-Hop).

### 6.5 Mandantentrennung

`DmsConnection` ist per `tenant_id` (unique) getrennt. Der Celery-Task liest `tenant_id` aus dem `DmsArchiveRecord` und holt die zugehörige Connection — es ist strukturell ausgeschlossen, dass Mandant A in das Repository von Mandant B archiviert.

### 6.6 Schema-Isolation (bewusste Entscheidung)

ADR-072 fordert PostgreSQL-Schema-Isolation für neue Multi-Tenant-Apps. Für dms-hub ist **Row-Level-Isolation via `tenant_id`** ausreichend, weil:
- Geringes Datenvolumen (~100–500 Records/Monat gesamt)
- Kein Cross-Tenant Reporting nötig
- `DmsArchiveRecord` ist Audit-Trail, keine operativen Daten
- Partial-Unique-Index auf `(tenant_id, source_id, status)` garantiert Isolation auf DB-Ebene

Bei signifikantem Wachstum (>10 Mandanten, >10.000 Records/Monat): erneut evaluieren.

### 6.7 PII in Logs und error_message

`DmsArchiveRecord.error_message` darf **ausschließlich technische Fehlermeldungen** enthalten (HTTP-Statuscode, Timeout-Dauer, d.velop-Error-Code). **Keine** Dokumentinhalte, keine Personennamen, keine Adressen. Der Celery-Task muss PII aus Exception-Messages filtern bevor `error_message` gespeichert wird.

---

## 7. Fehlerszenarien

| Szenario | Erkennung | Mitigation |
|----------|-----------|------------|
| d.velop-API nicht erreichbar | `httpx.ConnectTimeout` | 3× Retry (60/120/240s); danach FAILED |
| d.velop HTTP 429 (Rate Limit) | `httpx.HTTPStatusError` | Retry mit `Retry-After`-Header |
| d.velop HTTP 403 (fehlender Origin) | `httpx.HTTPStatusError` | Kein Retry (Config-Fehler); sofort FAILED + Alert |
| d.velop HTTP 401 (Key abgelaufen) | `httpx.HTTPStatusError` | Kein Retry (Auth-Fehler); sofort FAILED + Alert |
| Consumer sendet ungültiges PDF | Validierung im API-Endpoint | HTTP 400, kein Task dispatcht |
| DmsConnection fehlt für Tenant | `DoesNotExist` | HTTP 404 an Consumer; kein Task |
| dms-hub selbst nicht erreichbar | Consumer `httpx.ConnectTimeout` | Consumer loggt Fehler; Retry über Consumer möglich |
| Worker-Absturz während Upload | `acks_late` + `reject_on_worker_lost` | Task zurück in Queue |

---

## 8. Implementation Plan

### Phase 0 — iil-dvelop-client Package (2–3 Tage)

```
platform/packages/dvelop-client/
Deliverables:
  - DvelopClient: list_repositories(), upload_document(), search(), list_categories()
  - Sync + Async Support (httpx)
  - Pydantic v2 Models für API-Responses
  - Verify-Script gegen https://iil.d-velop.cloud/
  - ≥ 10 Tests (pytest-httpx)
```

**Akzeptanzkriterien:**
- Verify-Script authentifiziert sich und listet Repositories
- Upload eines Test-PDFs erfolgreich
- Alle Tests grün (kein echtes Netz in CI)

### Phase 1 — dms-hub Skeleton (3–4 Tage)

```
Neues Repo: achimdehnert/dms-hub
Deliverables:
  - Django-Projekt mit config/settings/base|dev|prod
  - 3 Apps: connections, categories, archive
  - Celery + Redis Konfiguration
  - Django Ninja Consumer-API
  - Django Admin für Connections + Categories
  - Dockerfile + docker-compose.prod.yml
  - Health endpoints (/livez/, /healthz/)
  - ≥ 15 Tests
```

**Akzeptanzkriterien:**
- `POST /api/v1/archive/` → `DmsArchiveRecord(PENDING)` → Celery-Task → d.velop Upload → `SUCCESS`
- Admin-UI zeigt Connections, Categories, Archive Records
- `docker compose up` startet Web + Worker + DB + Redis healthy

### Phase 2 — risk-hub Integration (1–2 Tage)

```
risk-hub/src/dms_archive/client.py (neuer dünner Client)
Chirurgische Patches in 4 Service-Methoden
```

**Akzeptanzkriterien:**
- `finalize_audit()` → dms-hub API → `DmsArchiveRecord(SUCCESS)` → Dokument in d.velop
- Kein bestehender risk-hub Test bricht

### Phase 3 — Produktiv-Deployment (1 Tag)

```
Server: Prod-Server (ADR-021 §2.1)
Deploy-Path: /opt/dms-hub
Port: 8107
DNS: dms.iil.pet → Cloudflare Proxy
Nginx: /etc/nginx/sites-enabled/dms.iil.pet.conf
```

### Phase 4 — Weitere Consumer (nach Bedarf)

- billing-hub: Rechnungs-Archivierung
- recruiting-hub: Vertrags-Archivierung

---

## 8.5 Open Questions

| # | Frage | Optionen | Entscheidung |
|---|-------|----------|-------------|
| OQ-1 | **Max. PDF-Größe?** Upload-Limit für Consumer-API | (a) 10 MB, (b) 25 MB, (c) 50 MB | 25 MB (d.velop Cloud Limit: 100 MB; 25 MB ist konservativ für Compliance-PDFs) |
| OQ-2 | **File-Retention nach Upload?** Wie lange bleibt die PDF im dms-hub MEDIA_ROOT? | (a) sofort löschen nach SUCCESS, (b) 7 Tage, (c) 30 Tage | 7 Tage — danach Cleanup-Task löscht lokale Kopie (d.velop ist Source-of-Truth) |
| OQ-3 | **Provider-Abstraktion Zeitpunkt?** Wann DocuWare/ELO/SharePoint? | (a) Phase 1 schon abstrahieren, (b) erst bei konkretem Bedarf | (b) — YAGNI; `DmsConnection.provider` Feld ist vorbereitet, Abstraktion erst bei 2. Provider |
| OQ-4 | **Consumer-Token-Rotation?** Wie werden Hub-Tokens generiert und rotiert? | (a) manuell, (b) automatisch via Celery-Beat | (a) manuell — `secrets.token_urlsafe(32)`, in `.env.prod` beider Hubs, jährliche Rotation |
| OQ-5 | **Inbound-Scan (d.velop → dms-hub)?** ADR-149-input für Scan-to-DMS | Eigenes ADR | Deferred — separates ADR (nächste freie Nummer) nach Phase 2 Produktiv-Test |

---

## 9. Confirmation

Diese ADR gilt als implementiert, wenn:

1. `iil-dvelop-client` auf PyPI veröffentlicht, Verify-Script läuft gegen `iil.d-velop.cloud`
2. `dms-hub` deployed auf 88.198.191.108, Port 8107, Health-Endpoints 200
3. `DmsConnection` für Landratsamt-Mandant in Admin konfiguriert
4. `DmsCategoryMapping` für alle risk-hub Dokumenttypen angelegt
5. risk-hub `finalize_audit()` → Dokument in d.velop nachweisbar
6. `DmsArchiveRecord` Audit-Trail vollständig (PENDING → SUCCESS)
7. Celery-Worker auf Queue `"dms"` mit Healthcheck `pidof python3.12`
8. API-Key ausschließlich via `decouple.config()` — kein Klartext in Config
9. `catalog-info.yaml` in dms-hub vorhanden

---

## 10. Konsequenzen

### 10.1 Positiv

- Revisionssichere Archivierung für **alle** Platform-Hubs über eine zentrale API
- Mandantenfähige DMS-Konfiguration (verschiedene d.velop-Instanzen pro Tenant)
- Zentraler Audit-Trail: wer hat wann was archiviert, aus welchem Hub
- Provider-Abstraktion: d.velop heute, DocuWare/ELO/SharePoint morgen
- Consumer-Hubs minimal invasiv: 1 dünner Client + 3 Zeilen pro Service-Methode

### 10.2 Negativ

- Neuer Docker-Stack (5 Container) auf dem Server
- Hub-zu-Hub Latenz (~50ms pro Archivierungsaufruf, aber async via `on_commit`)
- Abhängigkeit: dms-hub-Ausfall blockiert Archivierung (nicht Consumer-Betrieb)

### 10.3 Risiken

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|------------|
| d.velop API Breaking Change | Niedrig | Hoch | `iil-dvelop-client` isoliert; `staleness_months: 12` |
| API-Key Leak | Mittel | Kritisch | `decouple.config()` Pflicht; Key-Rotation |
| Hohe Dokumentvolumen (>500/Tag) | Niedrig | Mittel | Worker `concurrency` erhöhen |
| Mandant ohne d.velop | Mittel | Niedrig | `DmsConnection.is_active=False`; Consumer prüft vorab |

---

## 11. More Information

### Externe Quellen

| Quelle | URL |
|--------|-----|
| d.velop DMS API Docs (v2.15) | https://help.d-velop.de/docs/api/documentations/de/dms-developer/2.15.0 |
| d.velop Developer Portal | https://portal.d-velop.de/documentation/dmsap/en |
| IIL d.velop Cloud | https://iil.d-velop.cloud/ |

### Input-Dokumente

| Dokument | Pfad |
|----------|------|
| ADR-XXX (risk-hub-spezifisch, Input) | `docs/adr/inputs/dms-d-evelop/ADR-XXX-risk-hub-dms-audit-trail.md` |
| ADR-XXX Review | `docs/adr/inputs/dms-d-evelop/ADR-XXX-review.md` |
| Source-Code (Prototyp) | `docs/adr/inputs/dms-d-evelop/risk-hub-dms/` |

### Verwandte ADRs

| ADR | Relevanz |
|-----|----------|
| ADR-022 | BigAutoField Standard — kein UUID-PK |
| ADR-045 | Secrets via `decouple.config()` |
| ADR-050 | Hub Landscape, Service-Layer-Pflicht |
| ADR-072 | Multi-Tenancy Schema Isolation |
| ADR-075 | Deployment via GitHub Actions |
| ADR-078 | Docker HEALTHCHECK Convention |
| ADR-144 | Paperless-ngx (IIL-intern) — Abgrenzung zu d.velop (Kunden-DMS) |
| ADR-146 | Package Consolidation (iil-dvelop-client als neues Package) |

---

## 12. Migration Tracking

| Schritt | Status | Datum | Notiz |
|---------|--------|-------|-------|
| ADR-149 erstellt | ✅ Done | 2026-03-26 | |
| ADR-149 Review | ⏳ Pending | — | |
| Phase 0: iil-dvelop-client Package | ⏳ Pending | — | |
| Phase 1: dms-hub Skeleton | ⏳ Pending | — | |
| Phase 2: risk-hub Integration | ⏳ Pending | — | |
| Phase 3: Produktiv-Deployment | ⏳ Pending | — | Port 8107, dms.iil.pet |
| Phase 4: billing-hub Integration | ⏳ Pending | — | |
| ADR-149 Status → Accepted | ⏳ Pending | — | Nach Phase 2 Produktiv-Test |

---

*Erstellt: 2026-03-26 · Autor: Achim Dehnert · Review: ausstehend*
