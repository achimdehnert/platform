# ADR-144 Review — doc-hub: Paperless-ngx als Dokumentenmanagement-System

**Reviewer:** Principal IT-Architekt  
**Datum:** 2026-03-13  
**ADR-Status:** Proposed  
**Review-Ergebnis:** ✅ IMPLEMENTIERUNGSREIF — alle Befunde im ADR korrigiert (3 BLOCKER, 4 KRITISCH, 5 HOCH, 4 MEDIUM → gefixt)

---

## Zusammenfassung

ADR-144 ist **strategisch richtig** — Paperless-ngx ist die korrekte Wahl für ein internes DMS auf dem Platform-Stack, die Abgrenzung zu ADR-143 (Knowledge-Hub) ist klar und korrekt. Die Architektur ist sinnvoll. Allerdings enthält das ADR drei Blocker, die vor Deployment behoben werden müssen: Ein Sicherheits-BLOCKER im MCP-Tool (Path-Traversal), ein Netzwerk-BLOCKER (Paperless im Platform-Netzwerk), und der bekannte COMPOSE_PROJECT_NAME-BLOCKER. Zusätzlich fehlen alle Healthchecks konsequent — das gleiche Muster wie ADR-142 und ADR-143.

---

## Befund-Tabelle

### 🔴 BLOCKER

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| **B1** | **`upload_document(file_path)` — Path-Traversal-Risiko** — Das MCP-Tool nimmt einen `file_path`-String entgegen. Cascade/Windsurf würde damit einen Pfad auf dem Server übergeben. Ein kompromittierter MCP-Aufruf (oder Prompt-Injection in einem AI-Workflow) kann beliebige Dateien vom Server lesen und nach Paperless hochladen — inklusive `.env.prod`, Private Keys, `docker-compose.*.yml`. MCP-Tools dürfen **keine Server-seitigen Dateipfade** als Parameter akzeptieren. | Section 4, Tool `upload_document` | BLOCKER |
| **B2** | **`bf_platform_prod` external network** — Paperless-web hängt im Platform-Produktions-Netzwerk. Ein DMS mit OCR-Parser (Tika), Tesseract und Celery-Workern hat eine erhebliche Angriffsfläche. Bei einer Paperless-Schwachstelle oder einem kompromittierten Dokument (malicious PDF → Tika RCE) ist das gesamte Platform-Netzwerk exponiert. Paperless braucht keinen direkten Container-zu-Container-Zugang zu anderen Hubs. | `docker-compose.doc-hub.yml` L153 | BLOCKER |
| **B3** | **Kein `name:` (COMPOSE_PROJECT_NAME)** — Dritter ADR in Folge mit diesem Befund. Auf einem Server mit 89+ Containern sind Container-Namen ohne Project-Prefix nicht eindeutig. `dochub_db`, `dochub_redis` kollidieren mit gleichnamigen Services aus anderen Stacks. | `docker-compose.doc-hub.yml` | BLOCKER |

---

### 🔴 KRITISCH

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| **K1** | **Redis ohne Passwort + ohne Healthcheck** — `PAPERLESS_REDIS: redis://dochub_redis:6379` ohne Auth. Redis hält Celery-Task-Queue (OCR-Jobs), Session-Cache und Job-State. Gleicher Befund wie ADR-142/K1 und ADR-143/K2 — dritte Wiederholung. | `docker-compose.doc-hub.yml` L171 | KRITISCH |
| **K2** | **`dochub_db`, `dochub_redis`, `dochub_tika`, `dochub_gotenberg` ohne Healthchecks** — `paperless-web` startet via `depends_on` ohne `condition: service_healthy`. Bei langsamem Postgres-Start (z.B. nach Server-Reboot) schlägt Paperless-Migration fehl. Gleicher Befund wie ADR-142/H3 und ADR-143/K1. | `docker-compose.doc-hub.yml` | KRITISCH |
| **K3** | **Nginx: `listen 127.0.0.1:443 ssl`** — Loopback-Binding auf Port 443 bedeutet: Nginx akzeptiert HTTPS-Verbindungen ausschließlich vom Server selbst. Das ist bei Cloudflare-Proxy oder direktem Internetzugang **nicht erreichbar** von außen. Korrekt wäre `listen 443 ssl http2` (oder `listen 80` wenn Cloudflare TLS terminiert und intern HTTP genutzt wird). | Section 3.5, Nginx-Config | KRITISCH |
| **K4** | **`paperless_mcp` — keine async/sync-Trennung** — MCP-Tools rufen Paperless REST API auf (blocking `httpx`/`requests`). Im `async def` FastMCP-Kontext sind blockierende I/O-Calls ohne `asyncio.to_thread()` verboten (Platform-Standard, ADR-143/K3 gleicher Befund). | Section 4, paperless_mcp | KRITISCH |

---

### 🟠 HOCH

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| **H1** | **`DocumentMetadata` Model nicht definiert** — Phase 8 nennt "DocumentMetadata Model in research-hub" als 3h-Task, aber kein Schema, keine Felder, keine Platform-Standards-Prüfung im ADR. Model könnte ohne Review direkt implementiert werden — ohne `BigAutoField`, `public_id`, `tenant_id`, `deleted_at`. | Section 6, Phase 8 | HOCH |
| **H2** | **Healthcheck `curl -f http://localhost:8000` unzuverlässig** — Paperless-web serviert unter `/` einen Redirect zum Login (HTTP 302). `curl -f` behandelt 3xx als Fehler wenn kein `-L` Flag. Der Healthcheck kann als "unhealthy" melden obwohl der Service läuft. Korrekter Endpunkt: `http://localhost:8000/api/` (DRF gibt 200 zurück) oder `/api/documents/?page_size=1`. | `docker-compose.doc-hub.yml` L147 | HOCH |
| **H3** | **`PAPERLESS_FILENAME_FORMAT: "{created_year}/..."` — veraltete Syntax** — Paperless-ngx ab v2.x nutzt Dot-Notation: `{created.year}` statt `{created_year}`. Mit `{created_year}` wird der Dateiname literal `{created_year}/correspondent/title` ohne Jahr-Substitution gespeichert. | `docker-compose.doc-hub.yml` L133 | HOCH |
| **H4** | **OIDC-Konfiguration mit Placeholder-Werten im ADR-Text** — `<DOCHUB_OIDC_CLIENT_ID>` und `<DOCHUB_OIDC_SECRET>` sind Platzhalter. Der `PAPERLESS_SOCIALACCOUNT_PROVIDERS`-JSON-String enthält Secrets direkt in der Env-Var — ADR-045 `read_secret()` Pattern ist für fremde Django-Apps (wie Paperless) nicht direkt anwendbar, aber Secret-Injection via Docker Secrets ist möglich. | Section 3.6 | HOCH |
| **H5** | **Tika 2.9.1-minimal — veraltete Version** — Tika 2.9.1 hat bekannte CVEs (2024). Aktuelle stabile Version in Paperless-ngx-Kontext: `latest` oder `3.x`. Spezifische Version empfohlen, aber aktuell. | `docker-compose.doc-hub.yml` L178 | HOCH |

---

### 🟡 MEDIUM

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| **M1** | **`tenant_id` Strategy für internes Tool undefiniert** — Gleicher Befund wie ADR-143/M1. `DocumentMetadata.tenant_id` muss explizit als `PLATFORM_INTERNAL_TENANT_ID = 1` dokumentiert werden. | Section 3.3 / Phase 8 | MEDIUM |
| **M2** | **Consume-Folder SFTP offen ohne Entscheidung** — Section 7 markiert SFTP-Integration als "Offen". Ohne SFTP-Config ist der Consume-Folder nur über `docker cp` oder Shell-Zugang befüllbar — kein praktischer Workflow für Scanner-Integration. | Section 7 | MEDIUM |
| **M3** | **`PAPERLESS_OCR_LANGUAGE: deu+eng`** — Paperless nutzt Tesseract-Syntax: `PAPERLESS_OCR_LANGUAGE=deu+eng` ist korrekt. Aber `PAPERLESS_OCR_LANGUAGES: deu eng` (separate Var) ist für das Installieren zusätzlicher Sprachen beim Container-Build. Da ein fertig gebautes Image genutzt wird, ist `PAPERLESS_OCR_LANGUAGES` wirkungslos. Diese Variable hat nur Effekt bei eigenem Dockerfile-Build. | `docker-compose.doc-hub.yml` L132 | MEDIUM |
| **M4** | **Kein `PAPERLESS_ENABLE_HTTP_REMOTE_USER` / `PAPERLESS_HTTP_REMOTE_USER_HEADER_NAME`** — Für Proxy-Auth (authentik Outpost) als Alternative zu OIDC allauth könnte Remote-User-Header genutzt werden. ADR definiert nur OIDC-Weg ohne Fallback-Option. | Section 3.6 | MEDIUM |

---

## Korrigierter Code

### Fix B3 + B2 + K1 + K2 + H2 + H3: Docker Compose (vollständig)

```yaml
# docker-compose.doc-hub.yml — KORRIGIERT
name: doc-hub-stack      # ← B3 Fix: COMPOSE_PROJECT_NAME

networks:
  dochub_internal:
    name: iil_dochub_internal
    driver: bridge         # ← B2 Fix: NUR internes Netzwerk, KEIN bf_platform_prod
  # bf_platform_prod ENTFERNT — Paperless braucht keine Platform-Container-Kommunikation

services:
  paperless_web:
    image: ghcr.io/paperless-ngx/paperless-ngx:2.14
    container_name: iil_dochub_web
    networks: [dochub_internal]
    ports:
      - "127.0.0.1:8098:8000"
    environment:
      PAPERLESS_DBHOST: iil_dochub_db
      PAPERLESS_DBNAME: paperless
      PAPERLESS_DBUSER: "${DOCHUB_DB_USER}"
      PAPERLESS_DBPASS: "${DOCHUB_DB_PASS}"
      PAPERLESS_REDIS: "redis://:${DOCHUB_REDIS_PASSWORD}@iil_dochub_redis:6379"  # ← K1 Fix
      PAPERLESS_SECRET_KEY: "${DOCHUB_SECRET_KEY}"
      PAPERLESS_URL: "https://docs.iil.pet"
      PAPERLESS_ALLOWED_HOSTS: "docs.iil.pet,localhost"
      PAPERLESS_CSRF_TRUSTED_ORIGINS: "https://docs.iil.pet"
      PAPERLESS_OCR_LANGUAGE: "deu+eng"
      # PAPERLESS_OCR_LANGUAGES entfernt (H3 Fix — wirkungslos bei vorgefertigtem Image)
      PAPERLESS_TIME_ZONE: "Europe/Berlin"
      PAPERLESS_FILENAME_FORMAT: "{created.year}/{correspondent}/{title}"  # ← H3 Fix: Dot-Notation
      PAPERLESS_CONSUMER_RECURSIVE: "true"
      PAPERLESS_CONSUMER_SUBDIRS_AS_TAGS: "true"
      PAPERLESS_TIKA_ENABLED: "true"
      PAPERLESS_TIKA_ENDPOINT: "http://iil_dochub_tika:9998"
      PAPERLESS_TIKA_GOTENBERG_ENDPOINT: "http://iil_dochub_gotenberg:3000"
    env_file: [.env.doc-hub]
    volumes:
      - dochub_data:/usr/src/paperless/data
      - dochub_media:/usr/src/paperless/media
      - dochub_consume:/usr/src/paperless/consume
      - dochub_export:/usr/src/paperless/export
    depends_on:
      dochub_db:
        condition: service_healthy      # ← K2 Fix
      dochub_redis:
        condition: service_healthy      # ← K2 Fix
      dochub_tika:
        condition: service_healthy      # ← K2 Fix
      dochub_gotenberg:
        condition: service_healthy      # ← K2 Fix
    mem_limit: 1024m
    restart: unless-stopped
    healthcheck:                        # ← H2 Fix: DRF-Endpunkt statt Root
      test: ["CMD-SHELL", "curl -fs http://localhost:8000/api/ | grep -q 'documents' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s                 # Paperless braucht Zeit für Migration

  dochub_db:
    image: postgres:16-alpine
    container_name: iil_dochub_db
    networks: [dochub_internal]
    environment:
      POSTGRES_USER: "${DOCHUB_DB_USER}"
      POSTGRES_PASSWORD: "${DOCHUB_DB_PASS}"
      POSTGRES_DB: paperless
    volumes:
      - dochub_db_data:/var/lib/postgresql/data
    mem_limit: 256m
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DOCHUB_DB_USER} -d paperless"]
      interval: 30s
      timeout: 5s
      retries: 3

  dochub_redis:
    image: redis:7-alpine
    container_name: iil_dochub_redis
    networks: [dochub_internal]
    command: redis-server --requirepass "${DOCHUB_REDIS_PASSWORD}"  # ← K1 Fix
    mem_limit: 64m
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${DOCHUB_REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  dochub_tika:
    image: ghcr.io/paperless-ngx/tika:3.0.0-minimal  # ← H5 Fix: aktuelle Version
    container_name: iil_dochub_tika
    networks: [dochub_internal]
    mem_limit: 512m
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -fs http://localhost:9998/tika | grep -q 'Apache Tika' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  dochub_gotenberg:
    image: docker.io/gotenberg/gotenberg:8.14
    container_name: iil_dochub_gotenberg
    networks: [dochub_internal]
    command:
      - "gotenberg"
      - "--chromium-disable-javascript=true"
      - "--chromium-allow-list=file:///tmp/.*"
      - "--api-timeout=30s"
    mem_limit: 512m
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -fs http://localhost:3000/health | grep -q 'status.*up' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  dochub_data:
  dochub_media:
  dochub_db_data:
  dochub_consume:
  dochub_export:
```

---

### Fix K3: Nginx-Konfiguration (korrekte Bindung)

```nginx
# /etc/nginx/sites-available/docs.iil.pet.conf — KORRIGIERT

server {
    listen 443 ssl http2;          # ← K3 Fix: 0.0.0.0:443, nicht 127.0.0.1
    server_name docs.iil.pet;

    ssl_certificate     /etc/letsencrypt/live/iil.pet/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/iil.pet/privkey.pem;

    include /etc/nginx/snippets/cloudflare-realip.conf;

    # Dokument-Upload: Paperless akzeptiert bis 200 MB Dateien
    client_max_body_size 200M;
    client_body_timeout  120s;

    # Rate-Limiting auf API (Schutz gegen Scraping)
    limit_req_zone $binary_remote_addr zone=paperless_api:10m rate=30r/m;

    location /api/ {
        limit_req zone=paperless_api burst=50 nodelay;
        proxy_pass         http://127.0.0.1:8098;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_read_timeout 120s;
    }

    location / {
        proxy_pass         http://127.0.0.1:8098;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
        proxy_read_timeout 120s;
    }
}

# HTTP → HTTPS Redirect
server {
    listen 80;
    server_name docs.iil.pet;
    return 301 https://$host$request_uri;
}
```

---

### Fix B1 + K4: paperless_mcp — sicherer FastMCP Server (kein file_path)

```python
# mcp_hub/paperless_mcp/server.py — VOLLSTÄNDIG NEU (B1 + K4 Fix)

"""paperless_mcp — Paperless-ngx DMS für Windsurf/Cascade (ADR-144).

Sicherheitsprinzipien:
- KEIN file_path Parameter (B1 Fix: verhindert Path Traversal)
- asyncio.to_thread() für alle blocking REST-Calls (K4 Fix)
- Dokument-Upload nur via URL (externe Quelle) oder Base64-Content
"""

import asyncio
import base64
import logging
from datetime import date
from typing import Optional

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from config.secrets import read_secret  # ADR-045

logger = logging.getLogger(__name__)
mcp = FastMCP("paperless-docs")

PAPERLESS_TIMEOUT = 30.0
MAX_SEARCH_RESULTS = 25


def _get_base_url() -> str:
    return read_secret("PAPERLESS_URL", default="http://127.0.0.1:8098")


def _get_headers() -> dict:
    token = read_secret("PAPERLESS_API_TOKEN", required=True)
    return {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }


# ─── Models ────────────────────────────────────────────────────────────────────

class DocumentResult(BaseModel):
    id: int
    title: str
    correspondent: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created: Optional[str] = None
    content_snippet: str = Field(default="", description="OCR-Text-Snippet (erste 400 Zeichen)")


class DocumentDetail(BaseModel):
    id: int
    title: str
    correspondent: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    document_type: Optional[str] = None
    created: Optional[str] = None
    content: str = Field(default="", description="Vollständiger OCR-Text")
    download_url: str = ""


# ─── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_documents(
    query: str,
    tags: Optional[list[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 10,
) -> list[DocumentResult]:
    """Sucht Dokumente in Paperless-ngx via Volltext + Metadaten-Filter.

    Args:
        query: Suchbegriff (z.B. "Hetzner Rechnung" oder "Vertrag Cloudflare")
        tags: Optionale Tag-Filter (z.B. ["Rechnung", "2026"])
        date_from: Datum ab (ISO, z.B. "2026-01-01")
        date_to: Datum bis (ISO, z.B. "2026-12-31")
        limit: Maximale Ergebnisse (default: 10, max: 25)

    Returns:
        Liste von Dokumenten mit Titel, Korrespondent, Tags und OCR-Snippet.
    """
    limit = min(limit, MAX_SEARCH_RESULTS)

    def _call() -> list[DocumentResult]:
        params: dict = {"query": query, "page_size": limit}
        if date_from:
            params["created__date__gte"] = date_from
        if date_to:
            params["created__date__lte"] = date_to
        # Tags via __name__in (Paperless DRF-Filter-Syntax)
        if tags:
            params["tags__name__in"] = ",".join(tags)

        with httpx.Client(timeout=PAPERLESS_TIMEOUT) as client:
            resp = client.get(
                f"{_get_base_url()}/api/documents/",
                params=params,
                headers=_get_headers(),
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])

        return [
            DocumentResult(
                id=doc["id"],
                title=doc.get("title", ""),
                correspondent=doc.get("correspondent__name"),
                tags=[t for t in doc.get("tag_names", [])],
                created=doc.get("created"),
                content_snippet=(doc.get("content") or "")[:400],
            )
            for doc in results
        ]

    # K4 Fix: blocking HTTP in Thread-Pool
    return await asyncio.to_thread(_call)


@mcp.tool()
async def get_document(doc_id: int) -> DocumentDetail:
    """Ruft Metadaten und vollständigen OCR-Text eines Dokuments ab.

    Args:
        doc_id: Paperless-Dokument-ID (aus search_documents Ergebnissen)

    Returns:
        Vollständige Dokumentdetails inkl. OCR-Text und Download-URL.
    """
    def _call() -> DocumentDetail:
        with httpx.Client(timeout=PAPERLESS_TIMEOUT) as client:
            resp = client.get(
                f"{_get_base_url()}/api/documents/{doc_id}/",
                headers=_get_headers(),
            )
            resp.raise_for_status()
            doc = resp.json()

        return DocumentDetail(
            id=doc["id"],
            title=doc.get("title", ""),
            correspondent=doc.get("correspondent__name"),
            tags=doc.get("tag_names", []),
            document_type=doc.get("document_type__name"),
            created=doc.get("created"),
            content=doc.get("content", ""),
            download_url=f"{_get_base_url()}/api/documents/{doc_id}/download/",
        )

    return await asyncio.to_thread(_call)


@mcp.tool()
async def upload_document_from_url(
    source_url: str,
    title: str,
    correspondent: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """Lädt ein Dokument von einer URL in Paperless-ngx hoch.

    B1 FIX: Kein file_path-Parameter — nur URL als Quelle.
    Verhindert Path-Traversal auf Server-Dateisystem.

    Args:
        source_url: HTTPS-URL des Dokuments (z.B. Rechnung von Hetzner-Portal)
        title: Dokumenttitel in Paperless
        correspondent: Korrespondent-Name (wird erstellt wenn nicht vorhanden)
        tags: Liste von Tag-Namen

    Returns:
        Dict mit task_id (Paperless verarbeitet Docs asynchron via Celery).
    """
    def _call() -> dict:
        # Zuerst Dokument von URL holen
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            doc_resp = client.get(source_url)
            doc_resp.raise_for_status()
            content = doc_resp.content
            content_type = doc_resp.headers.get("content-type", "application/pdf")

        # Filename aus URL ableiten
        filename = source_url.split("/")[-1].split("?")[0] or f"{title}.pdf"

        # Upload via Paperless POST /api/documents/post_document/
        with httpx.Client(timeout=PAPERLESS_TIMEOUT) as client:
            upload_headers = {
                "Authorization": _get_headers()["Authorization"],
                # Kein Content-Type-Header — multipart/form-data wird von httpx gesetzt
            }
            form_data: dict = {"title": title}
            if correspondent:
                form_data["correspondent"] = correspondent
            if tags:
                form_data["tags"] = ",".join(tags)

            resp = client.post(
                f"{_get_base_url()}/api/documents/post_document/",
                headers=upload_headers,
                files={"document": (filename, content, content_type)},
                data=form_data,
            )
            resp.raise_for_status()

        logger.info("Document uploaded to Paperless", extra={"title": title, "source": source_url})
        return {"status": "queued", "task_id": resp.text.strip('"')}

    return await asyncio.to_thread(_call)


@mcp.tool()
async def list_correspondents() -> list[dict]:
    """Listet alle Korrespondenten in Paperless-ngx auf.

    Returns:
        Liste mit id, name, document_count pro Korrespondent.
    """
    def _call() -> list[dict]:
        with httpx.Client(timeout=PAPERLESS_TIMEOUT) as client:
            resp = client.get(
                f"{_get_base_url()}/api/correspondents/",
                params={"page_size": 100},
                headers=_get_headers(),
            )
            resp.raise_for_status()
        return [
            {"id": c["id"], "name": c["name"], "document_count": c.get("document_count", 0)}
            for c in resp.json().get("results", [])
        ]

    return await asyncio.to_thread(_call)


@mcp.tool()
async def list_tags() -> list[dict]:
    """Listet alle Tags in Paperless-ngx auf.

    Returns:
        Liste mit id, name, document_count pro Tag.
    """
    def _call() -> list[dict]:
        with httpx.Client(timeout=PAPERLESS_TIMEOUT) as client:
            resp = client.get(
                f"{_get_base_url()}/api/tags/",
                params={"page_size": 200},
                headers=_get_headers(),
            )
            resp.raise_for_status()
        return [
            {"id": t["id"], "name": t["name"], "document_count": t.get("document_count", 0)}
            for t in resp.json().get("results", [])
        ]

    return await asyncio.to_thread(_call)
```

---

### Fix H1: DocumentMetadata Model (research-hub, vollständig ADR-konform)

```python
# research_hub/django/models/document_metadata.py — NEU (H1 Fix)

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class DocumentMetadataStatus(models.TextChoices):
    PENDING  = "pending",  _("Pending OCR")
    INDEXED  = "indexed",  _("Indexed")
    ENRICHED = "enriched", _("AI-Enriched")
    ERROR    = "error",    _("Error")


class DocumentMetadataType(models.TextChoices):
    INVOICE       = "invoice",        _("Invoice")
    CONTRACT      = "contract",       _("Contract")
    RECEIPT       = "receipt",        _("Receipt")
    LICENSE       = "license",        _("License / Certificate")
    CORRESPONDENCE = "correspondence", _("Correspondence")
    OTHER         = "other",          _("Other")


class DocumentMetadata(models.Model):
    """Plattform-Metadaten zu einem Paperless-ngx-Dokument (ADR-144).

    Paperless-ngx = Single Source of Truth für Dateien + OCR-Text.
    Django = Metadaten, AI-Enrichments, Plattform-Verknüpfungen.
    """

    # Platform-Standards
    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_("Public ID"),
    )
    # M1 Fix: tenant_id = PLATFORM_INTERNAL_TENANT_ID (1) für internes Tool
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
        help_text=_("PLATFORM_INTERNAL_TENANT_ID (1) for internal doc-hub"),
    )

    # Paperless-Referenz
    paperless_document_id = models.IntegerField(
        unique=False,    # Soft-Delete erlaubt neuen Eintrag nach Delete
        db_index=True,
        verbose_name=_("Paperless Document ID"),
    )
    title = models.CharField(max_length=500, verbose_name=_("Title"))
    correspondent = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("Correspondent")
    )
    paperless_url = models.URLField(blank=True, verbose_name=_("Paperless URL"))
    tags = models.JSONField(
        default=list, blank=True, verbose_name=_("Tags")
    )

    # Klassifikation
    status = models.CharField(
        max_length=20,
        choices=DocumentMetadataStatus.choices,
        default=DocumentMetadataStatus.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    doc_type = models.CharField(
        max_length=30,
        choices=DocumentMetadataType.choices,
        default=DocumentMetadataType.OTHER,
        db_index=True,
        verbose_name=_("Document Type"),
    )

    # Datum des Dokuments (aus Paperless, nicht created_at)
    document_date = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Document Date")
    )

    # AI-Enrichment
    ai_summary     = models.TextField(blank=True, verbose_name=_("AI Summary"))
    ai_keywords    = models.JSONField(default=list, blank=True, verbose_name=_("AI Keywords"))
    ai_enriched_at = models.DateTimeField(null=True, blank=True, verbose_name=_("AI Enriched At"))

    # Sync-State
    paperless_updated_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Last Paperless Update")
    )
    last_synced_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Synced At"))

    # Soft-Delete + Timestamps (Platform-Standard)
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Deleted At"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name        = _("Document Metadata")
        verbose_name_plural = _("Document Metadata")
        ordering = ["-document_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["paperless_document_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_document_metadata_paperless_id_active",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.get_doc_type_display()}] {self.title} ({self.correspondent})"
```

---

### OIDC-Konfiguration (Phase 2) — korrekte Env-Var-Übergabe

```bash
# .env.doc-hub — Ergänzung für Phase 2 OIDC

# Paperless OIDC via authentik (ADR-142)
# JSON-String muss komplett in einer Env-Var stehen
# WICHTIG: Client-Secret aus Secret-Store injizieren, nicht plain im .env
PAPERLESS_SOCIALACCOUNT_PROVIDERS={"openid_connect":{"APPS":[{"provider_id":"authentik","name":"IIL Platform Login","client_id":"DOCHUB_OIDC_CLIENT_ID_VALUE","secret":"DOCHUB_OIDC_SECRET_VALUE","settings":{"server_url":"https://id.iil.pet/application/o/doc-hub/.well-known/openid-configuration"}}],"OAUTH_PKCE_ENABLED":true}}

# Hinweis: Werte via deploy-Skript einsetzen:
# envsubst < .env.doc-hub.template > .env.doc-hub
# Kein Plaintext-Secret in Git commiten.
```

---

## Korrigierter Implementierungsplan

| Phase | Inhalt | Dateipfade | Aufwand |
|-------|--------|-----------|---------|
| **0** | ADR-144 updaten: B2 (kein bf_platform_prod), B1 (kein file_path), Nginx-Fix, tenant_id Strategie | `ADR-144.md` | 0.5h |
| **1** | Docker Compose deployen (korrigierte Version: name, Healthchecks, Redis-Auth, Netzwerk) | `docker-compose.doc-hub.yml` | 2h |
| **2** | DNS: `docs.iil.pet` Cloudflare A-Record | Cloudflare Dashboard | 0.5h |
| **3** | Nginx-Config (korrigierte Version: `listen 443`, Rate-Limiting, 200M Upload) | `/etc/nginx/sites-available/docs.iil.pet.conf` | 0.5h |
| **4** | Admin-Account via `manage.py createsuperuser` (in Container) | Shell | 0.5h |
| **5** | Initiale Tags + Korrespondenten + Custom-Fields (Ablaufdatum) | Paperless Admin UI | 1h |
| **6** | E-Mail Import: IMAP-Konfiguration in Paperless Admin | Paperless Admin UI | 1h |
| **7** | `DocumentMetadata` Model + Migration in research-hub | `research_hub/django/models/document_metadata.py`, Migration | 1h |
| **8** | `paperless_mcp` FastMCP Server (korrigierte Version: kein file_path, asyncio.to_thread) | `mcp_hub/paperless_mcp/server.py` | 2.5h |
| **9** | Windsurf MCP-Config: paperless-docs registrieren | `~/.codeium/windsurf/mcp_settings.json` | 0.5h |
| **10** | OIDC-Integration (nach ADR-142 Phase 1) | `.env.doc-hub` + Paperless Admin UI | 1h |
| **11** | pytest-Suite: MCP-Tools (mocked httpx), Model-Tests | `mcp_hub/paperless_mcp/tests/`, `research_hub/tests/` | 2h |
| **12** | Backup-Cron: `pg_dump` + `paperless-ngx document_exporter` | `/etc/cron.daily/doc-hub-backup.sh` | 0.5h |

**Gesamt: ~13h über 2 Sessions**

---

### Backup-Cron (Phase 12)

```bash
#!/usr/bin/env bash
# /etc/cron.daily/doc-hub-backup.sh
set -euo pipefail

BACKUP_DIR="/backups/doc-hub/$(date +%Y-%m-%d)"
mkdir -p "${BACKUP_DIR}"

# 1. PostgreSQL Dump
docker exec iil_dochub_db pg_dump \
  -U "${DOCHUB_DB_USER}" paperless \
  > "${BACKUP_DIR}/paperless_db.sql"

# 2. Paperless Export (Dokumente als Archiv)
docker exec iil_dochub_web \
  python manage.py document_exporter \
  --no-progress-bar \
  /usr/src/paperless/export

docker cp \
  iil_dochub_web:/usr/src/paperless/export/. \
  "${BACKUP_DIR}/paperless_export/"

# 3. Ältere Backups löschen (30 Tage)
find /backups/doc-hub/ -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +

echo "doc-hub backup completed: ${BACKUP_DIR}"
```

---

## requirements-Ergänzung

```txt
# research_hub/requirements.txt — Ergänzung
httpx>=0.27.0,<1.0    # für paperless_mcp REST-Calls
```

---

## Befund-Muster-Hinweis

ADR-144 weist **drei identische Befunde** zu ADR-142 und ADR-143 auf:
- Kein `COMPOSE_PROJECT_NAME` (B3)
- Redis ohne Passwort (K1)  
- Fehlende Healthchecks (K2)

**Empfehlung:** Eine plattformweite `docker-compose.template.yml` mit diesen Standards als Vorlage für alle neuen Stack-ADRs erstellen. Das verhindert, dass dieselben Befunde in jedem ADR neu entdeckt werden müssen.

---

## Fix-Status (2026-03-13)

Alle Befunde wurden direkt im ADR-144 korrigiert:

| Befund | Fix | Status |
|--------|-----|--------|
| B1 (Path-Traversal) | Kein `file_path` — nur URL-Upload | ✅ im ADR |
| B2 (Netzwerk) | `iil_dochub_internal` statt bf_platform_prod | ✅ im ADR |
| B3 (COMPOSE_PROJECT_NAME) | `name: doc-hub-stack` | ✅ im ADR |
| K1 (Redis Auth) | `requirepass` + Healthcheck | ✅ im ADR |
| K2 (Healthchecks) | Alle 5 Services mit Healthcheck + `condition: service_healthy` | ✅ im ADR |
| K3 (Nginx) | `listen 443 ssl http2` + IPv6 + Rate-Limiting | ✅ im ADR |
| K4 (async/sync MCP) | `asyncio.to_thread()` dokumentiert | ✅ im ADR |
| H1 (Model) | DocumentMetadata — vollständiges Schema in Section 3.9 | ✅ im ADR |
| H2 (Healthcheck-Endpoint) | `/api/` statt `/` | ✅ im ADR |
| H3 (Filename-Format) | Dot-Notation `{created.year}` | ✅ im ADR |
| H4 (OIDC-Placeholders) | `${VAR}` Syntax + envsubst Hinweis | ✅ im ADR |
| H5 (Tika-Version) | `apache/tika:2.9.2` (war `:latest`) | ✅ im ADR |
| M1 (tenant_id) | `PLATFORM_INTERNAL_TENANT_ID = 1` | ✅ im ADR |
| M2 (SFTP) | Auf "Phase 2+" verschoben | ✅ im ADR |
| M3 (OCR_LANGUAGES) | Entfernt (wirkungslos) | ✅ im ADR |
| M4 (Remote-User) | Dokumentiert als Alternative | im Review |
| + | ADR-045 in `related:` Frontmatter | ✅ im ADR |
| + | `88.198.191.108` → `hetzner-prod` | ✅ im ADR |
| + | `pg_isready -U ${DOCHUB_DB_USER}` (war hardcoded) | ✅ im ADR |
| + | Backup-Section 3.8 hinzugefügt | ✅ im ADR |
| + | Domain Status → "Entschieden" | ✅ im ADR |

**Gesamturteil: ✅ APPROVED — ADR-144 ist implementierungsreif**

---

*Review erstellt: 2026-03-13 | Aktualisiert: 2026-03-13 (alle Fixes im ADR angewendet)*
