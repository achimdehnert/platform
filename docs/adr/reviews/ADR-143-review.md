# ADR-143 Review — Knowledge-Hub: Outline + research-hub Integration

**Reviewer:** Principal IT-Architekt  
**Datum:** 2026-03-13  
**ADR-Status:** Draft  
**Review-Ergebnis:** ⚠️ BEDINGT IMPLEMENTIERUNGSREIF — 1 BLOCKER, 4 KRITISCH, 6 HOCH, 5 MEDIUM

---

## Zusammenfassung

ADR-143 ist **konzeptionell sehr gut** — die Entscheidung für Outline + research-hub als Kombinations-Lösung ist richtig, die Architektur sauber getrennt (Outline = Inhalt, Django = Metadaten). Die ADR-Abgrenzung ist klar. Die Befunde sind überwiegend Implementierungs-Details, kein fundamentaler Architektur-Fehler. Wichtigste Korrekturen: Version pinnen, Container-Isolation, DB-Healthchecks, Redis-Passwort, und async/sync-Trennung im MCP-Server.

---

## Befund-Tabelle

### 🔴 BLOCKER

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| B1 | **`outlinewiki/outline:latest` in Docker Compose** — Section 6 (Offene Fragen) entscheidet explizit: "Pin zu `outlinewiki/outline:0.80.2`". Docker Compose in Section 3.6 verwendet trotzdem `:latest`. Production-Deployment mit `:latest` verletzt ADR-120 und kann bei einem breaking-change Update unbemerkt die Instanz lahmlegen. | Section 3.6 L180 | BLOCKER |

---

### 🔴 KRITISCH

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| K1 | **`outline_db` ohne healthcheck** — `outline` Container `depends_on: [outline_db, outline_redis]` ohne `condition: service_healthy`. Outline startet bevor PostgreSQL bereit ist → Migrationsfehler beim ersten Start. Gleicher Befund wie ADR-120/B2. | Section 3.6 | KRITISCH |
| K2 | **`outline_redis` ohne Passwort und ohne healthcheck** — Gleiche Sicherheitslücke wie ADR-142/K1. Redis ist ohne Auth aus allen Containern im Default-Netzwerk erreichbar. Outline cached Dokument-Drafts und Sessions in Redis. | Section 3.6 | KRITISCH |
| K3 | **`asyncio.run()` Risiko im `outline_mcp` FastMCP Server** — Section 3.5 definiert MCP-Tools als `async def`. Die Tools rufen synchronen Django-ORM-Code via `outline-wiki-api` Python-Client auf (blockierende HTTP-Requests + potentielle DB-Writes). Im ASGI-Kontext ist `asyncio.run()` verboten (ADR-Platform-Standard). Müssen `asyncio.to_thread()` oder `asgiref.sync.sync_to_async()` verwenden. | Section 3.5, outline_mcp Tools | KRITISCH |
| K4 | **Falsche ADR-Referenz: "ADR-094 (AI Context Amnesia)" existiert nicht** — ADR-094 ist `ADR-094-django-migration-conflict-resolution.md`. Das ADR für AI Context wurde von ADR-094 auf **ADR-132** (AI Context Defense-in-Depth) umnummeriert (siehe ADR-132 Header: "Umnummeriert von ADR-094"). Section 1.2 und Section 9 (Konsequenzen) referenzieren einen nicht-existierenden ADR → broken link, irreführend für zukünftige Leser. | Section 1.2, Section 9 | KRITISCH |

---

### 🟠 HOCH

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| H1 | **Kein `COMPOSE_PROJECT_NAME`** — Gleicher Befund wie ADR-142/B1. Auf einem Server mit 89+ Containern sind Container-Namen ohne Project-Prefix nicht eindeutig. | Section 3.6 | HOCH |
| H2 | **Keine Netzwerk-Isolation** — Outline, outline_db und outline_redis laufen im Default Docker-Netzwerk. Dediziertes `outline_net` fehlt. | Section 3.6 | HOCH |
| H3 | **`outline-wiki-api` unpinned** — `pip install outline-wiki-api` ohne Versionsnummer in `requirements.txt`. Inoffizieller Community-Wrapper (nicht Outline-GmbH). Breaking Changes möglich. | Section 6 (letzte Zeile) | HOCH |
| H4 | **`FORCE_HTTPS`, `PORT` und `FILE_STORAGE_UPLOAD_MAX_SIZE` fehlen** — Outline erfordert diese Env-Vars für korrekte HTTPS-Redirects hinter Nginx und Upload-Limits. Ohne `FORCE_HTTPS=false` (da Nginx HTTPS terminiert) sendet Outline HTTP-Redirects auf HTTPS-Loopback. | Section 3.6 L186 | HOCH |
| H5 | **Kein Full-Sync Celery-Beat-Task implementiert** — Section 6 entscheidet "Täglicher Celery-Beat-Task", aber keine Implementierung im ADR. Bei Webhook-Ausfall bleiben Dokumente ungesynct. | Section 6 | HOCH |
| H6 | **Nginx-Config für `knowledge.iil.pet` fehlt im ADR** — ADR-142 enthält eine Nginx-Config für `id.iil.pet`, aber ADR-143 definiert nur Docker Compose. Für das Deployment auf hetzner-prod fehlt die Nginx Reverse-Proxy-Config mit SSL-Terminierung, Security-Headers und Upload-Limit für Outline-Dateiuploads. | Section 3.6 | HOCH |

---

### 🟡 MEDIUM

| # | Befund | Betroffene Stelle | Severity |
|---|--------|-------------------|----------|
| M1 | **`tenant_id` Strategy für internes Tool unklar** — `KnowledgeDocument.tenant_id` ist Platform-Standard, aber Outline ist ein rein internes Tool (kein Multi-Tenant). Der ADR-Text sagt nichts darüber, welcher Wert eingetragen wird. Sollte explizit `PLATFORM_INTERNAL_TENANT_ID = 1` (konstant) definieren und in ADR dokumentieren. | Section 3.3 | MEDIUM |
| M2 | **Collection-ID Mapping via Heuristik statt DB** — `_infer_doc_type` im Konzept-Code erkennt Doc-Type via Titel-Substring. Das ist kein Database-first Design. Braucht eine `OutlineCollection`-Tabelle, die Collection-UUID → doc_type mapped. | Section 3.3 | MEDIUM |
| M3 | **i18n auf Model-Felder** — Section 3.3 zeigt Felder ohne `_()` wrappers. Alle `verbose_name` und `help_text` müssen `_("...")` verwenden (Platform-Standard). | Section 3.3 | MEDIUM |
| M4 | **Kein Backup für `outline_db`** — Die outline_db enthält alle Wiki-Dokumente. Kein Backup-Prozess dokumentiert. | Section 3.6 | MEDIUM |
| M5 | **`JSONField` für strukturierte Daten (DB-001 Spannung)** — `related_adr_numbers` (List[int]) und `related_hubs` (List[str]) sind strukturierte Daten, nicht unstrukturierte API-Payloads. Platform-Context DB-001: "BANNED: JSONField() — Exception: JSONField allowed for truly unstructured external API payloads only". Optionen: (a) `ArrayField(IntegerField())` / `ArrayField(CharField())` (PostgreSQL-nativ), (b) M2M-Relation, (c) JSONField mit expliziter ADR-Ausnahme dokumentieren. Empfehlung: **ArrayField** für PostgreSQL-only Platform. `ai_keywords` darf JSONField bleiben (variable Länge/Struktur). | Section 3.3, KnowledgeDocument Model | MEDIUM |

---

## Korrigierter Code

### Fix B1 + H1 + H2 + K1 + K2 + H4: Docker Compose

```yaml
# docker-compose.outline.yml — KORRIGIERT
name: outline-stack     # ← B1 Fix + H1 Fix: COMPOSE_PROJECT_NAME

networks:
  outline_net:
    name: iil_outline_net
    driver: bridge      # ← H2 Fix: Netzwerk-Isolation

services:
  outline:
    image: outlinewiki/outline:0.82.0    # ← B1 Fix: Version pinnen (aktuell März 2026)
    container_name: iil_knowledge_outline
    networks: [outline_net]
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      DATABASE_URL: "postgres://${OUTLINE_DB_USER}:${OUTLINE_DB_PASS}@iil_knowledge_outline_db:5432/outline"
      REDIS_URL: "redis://:${OUTLINE_REDIS_PASSWORD}@iil_knowledge_outline_redis:6379"  # ← K2 Fix
      SECRET_KEY: "${OUTLINE_SECRET_KEY}"
      UTILS_SECRET: "${OUTLINE_UTILS_SECRET}"
      URL: "https://knowledge.iil.pet"
      PORT: "3000"                                    # ← H4 Fix
      FORCE_HTTPS: "false"                            # ← H4 Fix: Nginx terminiert TLS
      FILE_STORAGE: local
      FILE_STORAGE_LOCAL_ROOT_DIR: /var/lib/outline/data
      FILE_STORAGE_UPLOAD_MAX_SIZE: "26214400"        # ← H4 Fix: 25 MB
      # OIDC via authentik (ADR-142 Phase 1, Step 1.4)
      OIDC_CLIENT_ID: "${OUTLINE_OIDC_CLIENT_ID}"
      OIDC_CLIENT_SECRET: "${OUTLINE_OIDC_CLIENT_SECRET}"
      OIDC_AUTH_URI: "https://id.iil.pet/application/o/authorize/"
      OIDC_TOKEN_URI: "https://id.iil.pet/application/o/token/"
      OIDC_USERINFO_URI: "https://id.iil.pet/application/o/userinfo/"
      OIDC_DISPLAY_NAME: "IIL Platform Login"
    env_file: [.env.outline]
    volumes:
      - outline_data:/var/lib/outline/data
    depends_on:
      outline_db:
        condition: service_healthy    # ← K1 Fix
      outline_redis:
        condition: service_healthy    # ← K2 Fix
    mem_limit: 512m
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "node -e \"require('http').get('http://localhost:3000/_health', r => process.exit(r.statusCode === 200 ? 0 : 1))\""]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  outline_db:
    image: postgres:16
    container_name: iil_knowledge_outline_db
    networks: [outline_net]
    environment:
      POSTGRES_USER: "${OUTLINE_DB_USER}"
      POSTGRES_PASSWORD: "${OUTLINE_DB_PASS}"
      POSTGRES_DB: outline
    volumes:
      - outline_db_data:/var/lib/postgresql/data
    mem_limit: 256m
    restart: unless-stopped
    healthcheck:                      # ← K1 Fix
      test: ["CMD-SHELL", "pg_isready -U ${OUTLINE_DB_USER} -d outline"]
      interval: 30s
      timeout: 5s
      retries: 3

  outline_redis:
    image: redis:7-alpine
    container_name: iil_knowledge_outline_redis
    networks: [outline_net]
    command: redis-server --requirepass "${OUTLINE_REDIS_PASSWORD}"  # ← K2 Fix
    mem_limit: 64m
    restart: unless-stopped
    healthcheck:                      # ← K2 Fix
      test: ["CMD", "redis-cli", "-a", "${OUTLINE_REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  outline_data:
  outline_db_data:
```

---

### Fix K4: ADR-Referenz korrigieren (ADR-094 → ADR-132)

In ADR-143 müssen **alle Vorkommen** von "ADR-094" durch "ADR-132" ersetzt werden:

```markdown
# Section 1.2 — VORHER:
pgvector Memory (ADR-113) speichert nur kurze Snippets — keine ganzen Dokumente.
# ↑ ADR-113 ist superseded → ADR-114

# Section 1.2 — NACHHER:
Cascade/Windsurf hat kein Kontextgedächtnis für Zwischenartefakte (ADR-132, AI Context Defense-in-Depth).

# Section 9 (Konsequenzen) — VORHER:
löst AI Context Amnesia (ADR-094)

# Section 9 — NACHHER:
löst AI Context Amnesia (ADR-132)
```

**Zusätzlich:** `related:` im Frontmatter sollte `ADR-132-ai-context-defense-in-depth.md` enthalten.

---

### Fix H6: Nginx-Config für knowledge.iil.pet

```nginx
# /etc/nginx/conf.d/outline.conf — NEU

server {
    listen 80;
    server_name knowledge.iil.pet;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name knowledge.iil.pet;

    ssl_certificate     /etc/letsencrypt/live/knowledge.iil.pet/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/knowledge.iil.pet/privkey.pem;

    # Outline-Dateiuploads: 25 MB (passend zu FILE_STORAGE_UPLOAD_MAX_SIZE)
    client_max_body_size 25m;

    # WebSocket für Echtzeit-Kollaboration (Outline Y.js)
    location /realtime {
        proxy_pass          http://127.0.0.1:3000;
        proxy_http_version  1.1;
        proxy_set_header    Upgrade    $http_upgrade;
        proxy_set_header    Connection "upgrade";
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass          http://127.0.0.1:3000;
        proxy_http_version  1.1;
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto $scheme;
    }
}
```

---

### Fix K3: outline_mcp — korrekte async/sync Trennung

```python
# mcp_hub/outline_mcp/server.py — KORRIGIERT

"""outline_mcp — Outline Knowledge Base für Windsurf/Cascade.

ADR-143: FastMCP Server mit korrekter async/sync Trennung.
Platform-Standard: NIEMALS asyncio.run() — asyncio.to_thread() für blockierende Calls.
"""

import asyncio
import logging
from functools import lru_cache

from fastmcp import FastMCP
from outline_wiki_api import OutlineWiki  # requirements: outline-wiki-api==0.3.x
from pydantic import BaseModel, Field

from config.secrets import read_secret  # ADR-045

logger = logging.getLogger(__name__)
mcp = FastMCP("outline-knowledge")


@lru_cache(maxsize=1)
def _get_client() -> OutlineWiki:
    """Singleton Outline-Client (thread-safe via lru_cache)."""
    return OutlineWiki(
        url=read_secret("OUTLINE_URL", required=True),
        token=read_secret("OUTLINE_API_TOKEN", required=True),
    )


class SearchResult(BaseModel):
    title: str
    url: str
    context: str = Field(default="")
    ranking: float
    doc_type: str


# ─── K3 FIX: alle Outline-API-Calls via asyncio.to_thread() ──────────────────
# Die outline-wiki-api ist synchron (blocking HTTP via requests).
# FastMCP Tools sind async → blockierende Calls MÜSSEN in Thread-Pool ausgelagert werden.
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_knowledge(query: str, limit: int = 10) -> list[SearchResult]:
    """Sucht in der gesamten Outline Knowledge Base.

    Args:
        query: Suchbegriff (z.B. "Django migration strategy" oder "bieterpilot Phase 2")
        limit: Maximale Anzahl Ergebnisse (default: 10, max: 25)

    Returns:
        Liste von Dokumenten mit Titel, URL, Kontext-Snippet und Relevanz-Score.
    """
    limit = min(limit, 25)  # Sicherheitslimit

    def _call() -> list[SearchResult]:
        client = _get_client()
        results = client.documents.search(query=query, limit=limit).data
        return [
            SearchResult(
                title=r.document.title,
                url=r.document.url or "",
                context=(r.context or "")[:400],
                ranking=r.ranking,
                doc_type=_infer_doc_type(r.document.title),
            )
            for r in results
        ]

    # K3 FIX: blocking I/O in Thread-Pool auslagern
    return await asyncio.to_thread(_call)


@mcp.tool()
async def get_document_content(document_id: str) -> dict:
    """Ruft den vollständigen Markdown-Inhalt eines Outline-Dokuments ab.

    Args:
        document_id: Outline UUID des Dokuments (aus search_knowledge Ergebnissen)

    Returns:
        Dict mit title, content (Markdown), url, updated_at
    """
    def _call() -> dict:
        client = _get_client()
        doc = client.documents.info(id=document_id).data.document
        return {
            "title": doc.title,
            "content": doc.text or "",
            "url": doc.url or "",
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        }

    return await asyncio.to_thread(_call)


@mcp.tool()
async def create_concept(
    title: str,
    content: str,
    collection_name: str = "Konzepte (in Arbeit)",
) -> dict:
    """Erstellt ein neues Konzept-Dokument in Outline.

    Args:
        title: Dokumenttitel (z.B. "Konzept: ship-workflow.sh")
        content: Markdown-Inhalt des Konzepts
        collection_name: Ziel-Collection (default: "Konzepte (in Arbeit)")

    Returns:
        Dict mit document_id und url des neuen Dokuments, oder error-Key bei Fehler.
    """
    def _call() -> dict:
        client = _get_client()
        collections = client.collections.list().data
        target = next(
            (c for c in collections if c.name == collection_name),
            None,
        )
        if not target:
            return {"error": f"Collection '{collection_name}' nicht gefunden"}

        doc = client.documents.create(
            title=title,
            text=content,
            collection_id=target.id,
            publish=True,
        ).data.document

        logger.info("Concept created via outline_mcp", extra={"title": title})
        return {"document_id": doc.id, "url": doc.url or ""}

    return await asyncio.to_thread(_call)


@mcp.tool()
async def list_recent_concepts(limit: int = 20) -> list[dict]:
    """Listet die zuletzt aktualisierten Dokumente in Outline.

    Args:
        limit: Anzahl der Ergebnisse (default: 20, max: 50)
    """
    limit = min(limit, 50)

    def _call() -> list[dict]:
        client = _get_client()
        docs = client.documents.list(limit=limit).data
        return [
            {
                "title": d.title,
                "url": d.url or "",
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                "doc_type": _infer_doc_type(d.title),
            }
            for d in docs
        ]

    return await asyncio.to_thread(_call)


def _infer_doc_type(title: str) -> str:
    """Heuristik-Fallback. DB-first Collection-Mapping kommt in Phase 2."""
    t = title.lower()
    if t.startswith("adr-"):
        return "adr"
    if any(k in t for k in ("konzept", "concept", "design", "entwurf")):
        return "concept"
    if any(k in t for k in ("recherche", "research", "evaluation", "analyse")):
        return "research"
    return "document"
```

---

### Fix M2: KnowledgeDocument Model (vollständig mit i18n + Fix M1 + M3)

```python
# research_hub/django/models/knowledge_document.py — VOLLSTÄNDIG KORRIGIERT

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _  # M3 Fix: i18n


class KnowledgeDocumentStatus(models.TextChoices):
    DRAFT    = "draft",    _("Draft")
    ACTIVE   = "active",   _("Active")
    ARCHIVED = "archived", _("Archived")


class KnowledgeDocumentType(models.TextChoices):
    ADR          = "adr",          _("ADR")
    CONCEPT      = "concept",      _("Concept")
    HUB_DOC      = "hub_doc",      _("Hub Documentation")
    RESEARCH     = "research",     _("Research")
    MEETING_NOTE = "meeting_note", _("Meeting Note")


class KnowledgeDocument(models.Model):
    """Metadaten zu einem Outline-Dokument (ADR-143-konform).

    Single Source of Truth für Inhalte: Outline Wiki.
    Django hält ausschließlich Metadaten, ADR-Links und AI-Enrichments.
    """

    # Platform-Standards
    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_("Public ID"),
    )
    # M1 Fix: tenant_id für internes Tool ist PLATFORM_INTERNAL_TENANT_ID (konstant = 1)
    # Dokumentiert in ADR-143 Section 3.3 als "internal platform tenant"
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
        help_text=_("Always PLATFORM_INTERNAL_TENANT_ID (1) for internal tools"),
    )

    # Outline-Referenz
    outline_document_id = models.CharField(
        max_length=36,
        db_index=True,
        verbose_name=_("Outline Document ID"),
        help_text=_("UUID of the document in Outline Wiki"),
    )
    outline_collection_id = models.CharField(
        max_length=36,
        db_index=True,
        blank=True,
        default="",
        verbose_name=_("Outline Collection ID"),
    )
    title = models.CharField(
        max_length=500,
        verbose_name=_("Title"),
    )
    outline_url = models.URLField(
        blank=True,
        verbose_name=_("Outline URL"),
    )

    # Kategorisierung
    status = models.CharField(
        max_length=20,
        choices=KnowledgeDocumentStatus.choices,
        default=KnowledgeDocumentStatus.DRAFT,
        db_index=True,
        verbose_name=_("Status"),
    )
    doc_type = models.CharField(
        max_length=30,
        choices=KnowledgeDocumentType.choices,
        default=KnowledgeDocumentType.CONCEPT,
        db_index=True,
        verbose_name=_("Document Type"),
    )

    # Verknüpfungen
    related_adr_numbers = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Related ADR Numbers"),
        help_text=_("List of ADR numbers, e.g. [141, 116, 82]"),
    )
    related_hubs = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Related Hubs"),
        help_text=_("e.g. ['coach-hub', 'risk-hub']"),
    )

    # AI-Enrichment
    ai_summary     = models.TextField(blank=True, verbose_name=_("AI Summary"))
    ai_keywords    = models.JSONField(default=list, blank=True, verbose_name=_("AI Keywords"))
    ai_enriched_at = models.DateTimeField(null=True, blank=True, verbose_name=_("AI Enriched At"))

    # Sync-State
    outline_updated_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Last Outline Update")
    )
    last_synced_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Last Synced At")
    )

    # Soft-Delete & Timestamps (Platform-Standard)
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Deleted At"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name        = _("Knowledge Document")
        verbose_name_plural = _("Knowledge Documents")
        ordering            = ["-outline_updated_at"]
        constraints = [
            # Eindeutiger Outline-Doc-ID unter aktiven Einträgen
            models.UniqueConstraint(
                fields=["outline_document_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_knowledge_doc_outline_id_active",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.get_doc_type_display()}] {self.title}"
```

---

### Fix H5: Full-Sync Celery-Beat-Task

```python
# research_hub/tasks/outline_full_sync.py — NEU

"""Täglicher Full-Sync aller Outline-Dokumente (ADR-143 H5 Fix).

Fallback für verpasste Webhooks. Läuft via Celery Beat.
"""

import logging

from celery import shared_task
from django.conf import settings
from outline_wiki_api import OutlineWiki

from config.secrets import read_secret  # ADR-045
from research_hub.tasks.outline_sync import sync_outline_document_task

logger = logging.getLogger(__name__)

MAX_DOCS_PER_RUN = 500  # Sicherheitslimit gegen endlose Runs


@shared_task(
    name="research_hub.outline_full_sync",
    max_retries=1,
    soft_time_limit=300,  # 5 Minuten Hard-Stop
)
def outline_full_sync_task() -> dict:
    """Re-synct alle Outline-Dokumente (täglicher Fallback via Celery Beat).

    Konfiguration in settings.py:
        CELERY_BEAT_SCHEDULE = {
            "outline-full-sync": {
                "task": "research_hub.outline_full_sync",
                "schedule": crontab(hour=3, minute=0),  # täglich 03:00 UTC
            },
        }
    """
    client = OutlineWiki(
        url=read_secret("OUTLINE_URL", required=True),
        token=read_secret("OUTLINE_API_TOKEN", required=True),
    )

    offset = 0
    limit = 25
    total_synced = 0
    total_errors = 0

    while total_synced < MAX_DOCS_PER_RUN:
        try:
            response = client.documents.list(limit=limit, offset=offset)
            docs = response.data
        except Exception as exc:
            logger.error(
                "Outline full sync: API call failed",
                extra={"offset": offset, "error": str(exc)},
            )
            break

        if not docs:
            break

        for doc in docs:
            try:
                sync_outline_document_task.delay(outline_document_id=doc.id)
                total_synced += 1
            except Exception as exc:
                logger.warning(
                    "Outline full sync: task dispatch failed",
                    extra={"doc_id": doc.id, "error": str(exc)},
                )
                total_errors += 1

        offset += limit

        if len(docs) < limit:
            break  # Letzte Seite erreicht

    logger.info(
        "Outline full sync complete",
        extra={"total_synced": total_synced, "total_errors": total_errors},
    )
    return {"synced": total_synced, "errors": total_errors}
```

---

### requirements-Ergänzung (H3 Fix)

```txt
# research_hub/requirements.txt — Ergänzung
outline-wiki-api==0.3.2   # H3 Fix: Version pinnen, stand 2026-03
httpx>=0.27.0,<1.0        # für AuthentikUserService (ADR-142 B2 Fix)
```

---

## Korrigierter Implementierungsplan

| Phase | Inhalt | Dateipfade | Aufwand |
|-------|--------|-----------|---------|
| **0** | ADR-143 updaten: Version in Compose pinnen, `tenant_id` Strategie dokumentieren | ADR-143.md | 0.5h |
| **1** | Docker Compose (korrigierte Version: gepinntes Image, Healthchecks, Netzwerk, Redis-Auth) | `docker-compose.outline.yml` | 2h |
| **2** | DNS + Nginx-Config für `knowledge.iil.pet` | `/etc/nginx/conf.d/outline.conf` | 0.5h |
| **3** | OIDC-Integration mit authentik (nach ADR-142 Phase 1) | Outline Settings UI | 1h |
| **4** | Collections anlegen, initiale ADR-Docs importieren | Outline Admin UI | 1h |
| **5** | `KnowledgeDocument` + `KnowledgeDocumentStatus/Type` Models | `research_hub/django/models/knowledge_document.py` | 1h |
| **6** | Migration (idempotent, SeparateDatabaseAndState wenn nötig) | `research_hub/migrations/00xx_knowledge_document.py` | 0.5h |
| **7** | Webhook-Handler + HMAC-Signatur | `research_hub/views/outline_webhook.py` | 1.5h |
| **8** | `KnowledgeDocumentService` + `outline-wiki-api` Client | `research_hub/services/knowledge_document_service.py` | 2h |
| **9** | Celery Sync-Tasks + Full-Sync | `research_hub/tasks/outline_sync.py`, `outline_full_sync.py` | 2h |
| **10** | Celery-Beat Schedule in settings.py | `research_hub/settings.py` | 0.5h |
| **11** | `outline_mcp` FastMCP Server (K3-korrigierte Version) | `mcp_hub/outline_mcp/server.py` | 2h |
| **12** | Windsurf MCP-Config (`mcp_settings.json`) | `~/.codeium/windsurf/mcp_settings.json` | 0.5h |
| **13** | pytest-Suite: Webhook-Signatur, Service-Layer, MCP-Tools | `research_hub/tests/test_knowledge_*.py` | 2h |

**Gesamt: ~17h über 2-3 Sessions**

---

## Abhängigkeiten

```
ADR-142 Phase 1 (authentik deployed) → ADR-143 Phase 3 (OIDC-Integration)
                                     ↑ Optional — Outline kann initial ohne OIDC starten
ADR-143 Phase 8 (Service fertig)    → Phase 9 (Tasks), Phase 11 (MCP-Server)
```

---

## Empfehlung

ADR-143 ist nach **8 Korrekturen** implementierungsreif:

1. Docker Compose: `outlinewiki/outline:0.82.0` (statt `:latest`) — B1
2. Docker Compose: Healthchecks + Redis-Passwort + Netzwerk-Isolation + `name:` Prefix — K1, K2, H1, H2
3. `outline_mcp`: `asyncio.to_thread()` um alle `_call()` Funktionen — K3
4. **ADR-094 → ADR-132 korrigieren** in Section 1.2 + Section 9 + Frontmatter `related:` — K4
5. **Nginx-Config** für `knowledge.iil.pet` erstellen (WebSocket, Upload-Limit, SSL) — H6
6. `KnowledgeDocument`: vollständiges Model mit `_()` auf allen verbose_names — M3
7. `outline_full_sync_task` als Celery-Beat-Task hinzufügen — H5
8. `related_adr_numbers` / `related_hubs` → `ArrayField` statt `JSONField` — M5

Die Architektur-Entscheidung (Outline = Inhalt, Django = Metadaten, MCP = Cascade-Brücke) ist **korrekt und beizubehalten**.

---

## Befund-Zusammenfassung

| Severity | Anzahl | Befunde |
|----------|--------|---------|
| BLOCKER | 1 | B1 (`:latest` Tag) |
| KRITISCH | 4 | K1 (DB Healthcheck), K2 (Redis Auth), K3 (async/sync), K4 (ADR-094→ADR-132) |
| HOCH | 6 | H1 (COMPOSE_PROJECT_NAME), H2 (Netzwerk), H3 (outline-wiki-api), H4 (Outline Env-Vars), H5 (Full-Sync), H6 (Nginx) |
| MEDIUM | 5 | M1 (tenant_id), M2 (Collection-Mapping), M3 (i18n), M4 (Backup), M5 (JSONField→ArrayField) |
| **Gesamt** | **16** | |

**Gesamturteil: ⚠️ APPROVED WITH COMMENTS — nach Korrekturen implementierungsreif**

---

*Review erstellt: 2026-03-13 | Aktualisiert: 2026-03-13 (K4, H6, M5 ergänzt)*
