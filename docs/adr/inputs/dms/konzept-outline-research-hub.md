# Konzept: Knowledge-Hub — Outline + research-hub Integration

**Status:** Konzept zur Entscheidung  
**Datum:** 2026-03-13  
**Autor:** Principal IT-Architekt  
**Scope:** iil-Platform-Stack — neuer `knowledge-hub` (oder Erweiterung `research-hub`)

---

## 1. Problemstellung

Dein aktueller Arbeitsalltag erzeugt drei Kategorien von Wissen:

| Kategorie | Aktueller Ort | Problem |
|-----------|--------------|---------|
| ADRs (final) | Git-Repo Markdown | ✅ Gut — aber kein Editor, kein Kommentar-Workflow |
| Konzepte (in Arbeit) | Irgendwo lokal / im Kopf | ❌ Kein zentraler Ort, kein Suchindex |
| Erweiterte Unterlagen | Verschiedene Dateien | ❌ Nicht durchsuchbar, kein ADR-Bezug |

Cascade/Windsurf hat **kein Kontextgedächtnis** für diese Zwischenartefakte → 
ADR-094 (AI Context Amnesia) ist teilweise ein Knowledge-Retrieval-Problem.

---

## 2. Lösungsidee: Outline als Frontend, research-hub als Backend-Erweiterung

```
┌─────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE-HUB ARCHITEKTUR                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐      Webhook       ┌──────────────────┐  │
│  │  Outline Wiki    │ ─────────────────▶ │  research-hub    │  │
│  │  (Docker, :3000) │                    │  (Django)        │  │
│  │                  │                    │                  │  │
│  │  • Markdown-Ed.  │  REST API (Bearer) │  • KnowledgeDoc  │  │
│  │  • Collections   │ ◀────────────────▶ │  • ADR-Sync      │  │
│  │  • Full-Text     │                    │  • AI-Enrichment │  │
│  │  • Echtzeit-     │                    │  • Celery Tasks  │  │
│  │    Kollaboration │                    │                  │  │
│  └──────────────────┘                    └────────┬─────────┘  │
│                                                   │            │
│                                          ┌────────▼─────────┐  │
│                                          │  outline_mcp     │  │
│                                          │  (FastMCP Server)│  │
│                                          │                  │  │
│                                          │  search_knowledge│  │
│                                          │  get_document    │  │
│                                          │  create_concept  │  │
│                                          │  link_adr        │  │
│                                          └──────────────────┘  │
│                                                   │            │
│                                          Windsurf/Cascade       │
│                                          (AI Context Feed)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Outline — Was es ist und was es kann

**Outline** ist ein Open-Source Wiki (BSL 1.1 Lizenz), selbst-gehostet via Docker Compose.

### 3.1 Kernfeatures für deinen Use Case

| Feature | Nutzen für dich |
|---------|----------------|
| **Markdown-Editor** | Konzepte, ADR-Drafts direkt im Browser schreiben |
| **Collections** | Strukturierung: ADRs / Konzepte / Platform-Docs / Hub-Doku |
| **Full-Text-Suche** | Alle Konzepte und Unterlagen sofort durchsuchbar |
| **REST API (Bearer Token)** | Programmatischer Zugriff für research-hub und MCP |
| **Webhooks (HMAC-SHA256)** | Events bei document.create/update/delete → Django-Sync |
| **Slash-Commands** | `/adr`, `/concept`, Custom-Templates via Extension |
| **Python-Client (PyPI)** | `outline-wiki-api` — direkter Einsatz in Django-Services |

### 3.2 Collections-Struktur (Empfehlung)

```
📁 ADRs (Platform)
    └── ADR-001 bis ADR-14x (gespiegelt aus Git)
📁 Konzepte (in Arbeit)
    └── Konzept-001: bieterpilot Phase 2
    └── Konzept-002: ship-workflow.sh
📁 Hub-Dokumentation
    └── coach-hub / risk-hub / travel-beat ...
📁 Recherchen & Unterlagen
    └── Technologie-Evaluationen
    └── Referenz-Links
📁 Meeting-Notes & Entscheidungen
```

### 3.3 Docker Compose Integration (auf bestehendem CPX52)

```yaml
# docker-compose.outline.yml — auf hetzner-prod
services:
  outline:
    image: outlinewiki/outline:latest
    container_name: knowledge_outline
    ports:
      - "3000:3000"   # hinter Cloudflare Access (nur @iil.gmbh)
    environment:
      DATABASE_URL: "postgres://${OUTLINE_DB_USER}:${OUTLINE_DB_PASS}@outline_db:5432/outline"
      REDIS_URL: "redis://outline_redis:6379"
      SECRET_KEY: "${OUTLINE_SECRET_KEY}"
      UTILS_SECRET: "${OUTLINE_UTILS_SECRET}"
      URL: "https://knowledge.iil.pet"
      FILE_STORAGE: local
      FILE_STORAGE_LOCAL_ROOT_DIR: /var/lib/outline/data
      # OIDC via Cloudflare Access (SSO mit @iil.gmbh)
      OIDC_CLIENT_ID: "${CLOUDFLARE_OIDC_CLIENT_ID}"
      OIDC_CLIENT_SECRET: "${CLOUDFLARE_OIDC_CLIENT_SECRET}"
      OIDC_AUTH_URI: "https://<team>.cloudflareaccess.com/cdn-cgi/access/sso/oidc/..."
    volumes:
      - outline_data:/var/lib/outline/data
    depends_on: [outline_db, outline_redis]

  outline_db:
    image: postgres:16
    container_name: knowledge_outline_db
    environment:
      POSTGRES_USER: "${OUTLINE_DB_USER}"
      POSTGRES_PASSWORD: "${OUTLINE_DB_PASS}"
      POSTGRES_DB: outline
    volumes:
      - outline_db_data:/var/lib/postgresql/data

  outline_redis:
    image: redis:7-alpine
    container_name: knowledge_outline_redis

volumes:
  outline_data:
  outline_db_data:
```

**Hinweis:** Outline nutzt eine **eigene PostgreSQL-Instanz** (kein Mischen mit 
Platform-DBs) — saubere Trennung, einfacheres Backup.

---

## 4. research-hub Erweiterung — Django Backend

### 4.1 Neue Models (ADR-konform)

```python
# research_hub/django/models/knowledge_document.py

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class KnowledgeDocumentStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    ARCHIVED = "archived", _("Archived")


class KnowledgeDocument(models.Model):
    """Metadaten zu einem Outline-Dokument (ADR-konform).

    Outline ist der Editor/Store — Django hält Metadaten,
    ADR-Links, AI-Enrichments und Platform-Kontext.
    """

    # Platform-Standards
    public_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )
    tenant_id = models.BigIntegerField(db_index=True, verbose_name=_("Tenant ID"))

    # Outline-Referenz
    outline_document_id = models.CharField(
        max_length=36, unique=True, db_index=True,
        verbose_name=_("Outline Document ID")
    )
    outline_collection_id = models.CharField(
        max_length=36, db_index=True,
        verbose_name=_("Outline Collection ID")
    )
    title = models.CharField(max_length=500, verbose_name=_("Title"))
    outline_url = models.URLField(blank=True, verbose_name=_("Outline URL"))

    # Kategorisierung
    status = models.CharField(
        max_length=20,
        choices=KnowledgeDocumentStatus.choices,
        default=KnowledgeDocumentStatus.DRAFT,
        db_index=True,
    )
    doc_type = models.CharField(
        max_length=30,
        choices=[
            ("adr", _("ADR")),
            ("concept", _("Concept")),
            ("hub_doc", _("Hub Documentation")),
            ("research", _("Research")),
            ("meeting_note", _("Meeting Note")),
        ],
        db_index=True,
        verbose_name=_("Document Type"),
    )

    # ADR-Verknüpfung (optional)
    related_adr_numbers = models.JSONField(
        default=list, blank=True,
        verbose_name=_("Related ADR Numbers"),
        help_text=_("List of ADR numbers, e.g. [141, 116, 82]")
    )
    related_hubs = models.JSONField(
        default=list, blank=True,
        verbose_name=_("Related Hubs"),
        help_text=_("e.g. ['coach-hub', 'risk-hub']")
    )

    # AI-Enrichment
    ai_summary = models.TextField(blank=True, verbose_name=_("AI Summary"))
    ai_keywords = models.JSONField(default=list, blank=True)
    ai_enriched_at = models.DateTimeField(null=True, blank=True)

    # Sync-State
    outline_updated_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("Last Outline Update")
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)

    # Soft-Delete & Timestamps
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Knowledge Document")
        verbose_name_plural = _("Knowledge Documents")
        ordering = ["-outline_updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["outline_document_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_knowledge_doc_outline_id_active",
            )
        ]
```

### 4.2 Webhook-Handler (Outline → Django)

```python
# research_hub/views/outline_webhook.py

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from research_hub.tasks.outline_sync import sync_outline_document_task

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def outline_webhook(request):
    """Empfängt Outline-Webhooks und löst Sync-Tasks aus.

    Outline sendet: document.create, document.update, document.delete
    Signatur-Verifikation via HMAC-SHA256 (Outline-Signature Header).
    """
    # 1. Signatur prüfen
    signature_header = request.headers.get("Outline-Signature", "")
    if not _verify_outline_signature(request.body, signature_header):
        logger.warning("Outline webhook: invalid signature")
        return HttpResponse(status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event = payload.get("event", "")
    doc_id = payload.get("payload", {}).get("id")

    if not doc_id:
        return JsonResponse({"status": "ignored", "reason": "no document id"})

    # 2. Async-Task triggern (nicht blockierend)
    if event in ("documents.create", "documents.update"):
        sync_outline_document_task.delay(outline_document_id=doc_id)
    elif event == "documents.delete":
        _soft_delete_knowledge_document(outline_document_id=doc_id)

    logger.info("Outline webhook processed", extra={"event": event, "doc_id": doc_id})
    return JsonResponse({"status": "ok"})


def _verify_outline_signature(body: bytes, header: str) -> bool:
    """HMAC-SHA256-Verifikation der Outline-Webhook-Signatur."""
    if not header:
        return False
    try:
        parts = dict(part.split("=", 1) for part in header.split(","))
        timestamp = parts.get("t", "")
        received_sig = parts.get("v0", "")
    except (ValueError, AttributeError):
        return False

    secret = settings.OUTLINE_WEBHOOK_SECRET.encode()
    expected = hmac.new(
        secret,
        f"{timestamp}.{body.decode()}".encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, received_sig)


def _soft_delete_knowledge_document(outline_document_id: str) -> None:
    from django.utils import timezone
    from research_hub.django.models.knowledge_document import KnowledgeDocument
    KnowledgeDocument.objects.filter(
        outline_document_id=outline_document_id,
        deleted_at__isnull=True,
    ).update(deleted_at=timezone.now())
```

### 4.3 Sync-Service + AI-Enrichment (Celery)

```python
# research_hub/tasks/outline_sync.py

import logging
from celery import shared_task
from outline_wiki_api import OutlineWiki  # pip: outline-wiki-api

from research_hub.services.knowledge_document_service import KnowledgeDocumentService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="research_hub.sync_outline_document",
)
def sync_outline_document_task(self, outline_document_id: str) -> dict:
    """Synct ein Outline-Dokument in KnowledgeDocument + löst AI-Enrichment aus."""
    try:
        service = KnowledgeDocumentService()
        doc = service.sync_from_outline(outline_document_id)

        # AI-Enrichment nur wenn noch nicht enriched oder veraltet
        if service.needs_enrichment(doc):
            enrich_knowledge_document_task.delay(str(doc.public_id))

        return {"status": "synced", "public_id": str(doc.public_id)}

    except Exception as exc:
        logger.error(
            "Outline sync failed",
            extra={"outline_document_id": outline_document_id, "error": str(exc)},
        )
        raise self.retry(exc=exc)


@shared_task(
    name="research_hub.enrich_knowledge_document",
    max_retries=2,
)
def enrich_knowledge_document_task(public_id: str) -> dict:
    """Erstellt AI-Summary und Keywords via llm_mcp (ADR-116 Kosten-Tracking)."""
    from research_hub.services.knowledge_enrichment_service import (
        KnowledgeEnrichmentService,
    )
    service = KnowledgeEnrichmentService()
    return service.enrich(public_id=public_id)
```

### 4.4 Service-Layer

```python
# research_hub/services/knowledge_document_service.py

import logging
from datetime import timedelta

from asgiref.sync import async_to_sync  # NIEMALS asyncio.run()
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from outline_wiki_api import OutlineWiki

from research_hub.django.models.knowledge_document import (
    KnowledgeDocument,
    KnowledgeDocumentStatus,
)

logger = logging.getLogger(__name__)

ENRICHMENT_STALENESS_HOURS = 24


class KnowledgeDocumentService:
    """Sync zwischen Outline und KnowledgeDocument-Model.

    Outline ist die Single Source of Truth für Inhalte.
    Django hält Metadaten, ADR-Links und AI-Enrichments.
    """

    def __init__(self):
        self._client = OutlineWiki(
            url=settings.OUTLINE_URL,
            token=settings.OUTLINE_API_TOKEN,
        )

    def sync_from_outline(self, outline_document_id: str) -> KnowledgeDocument:
        """Holt Dokument von Outline API und upserted KnowledgeDocument."""
        # Outline API aufrufen
        result = self._client.documents.info(id=outline_document_id)
        doc_data = result.data.document

        with transaction.atomic():
            obj, created = KnowledgeDocument.objects.update_or_create(
                outline_document_id=outline_document_id,
                defaults={
                    "tenant_id": settings.PLATFORM_DEFAULT_TENANT_ID,
                    "outline_collection_id": doc_data.collection_id or "",
                    "title": doc_data.title,
                    "outline_url": doc_data.url or "",
                    "doc_type": self._infer_doc_type(doc_data.title, doc_data.collection_id),
                    "status": KnowledgeDocumentStatus.ACTIVE,
                    "outline_updated_at": doc_data.updated_at,
                    "last_synced_at": timezone.now(),
                    "deleted_at": None,  # Reaktivierung bei erneutem Sync
                },
            )

        action = "created" if created else "updated"
        logger.info(
            f"KnowledgeDocument {action}",
            extra={"outline_document_id": outline_document_id, "title": doc_data.title},
        )
        return obj

    def needs_enrichment(self, doc: KnowledgeDocument) -> bool:
        """True wenn AI-Enrichment fehlt oder älter als ENRICHMENT_STALENESS_HOURS."""
        if not doc.ai_enriched_at:
            return True
        staleness = timezone.now() - timedelta(hours=ENRICHMENT_STALENESS_HOURS)
        return doc.ai_enriched_at < staleness

    @staticmethod
    def _infer_doc_type(title: str, collection_id: str | None) -> str:
        """Einfache Heuristik — später via Collection-Mapping in DB (Database-first)."""
        title_lower = title.lower()
        if title_lower.startswith("adr-"):
            return "adr"
        if any(kw in title_lower for kw in ("konzept", "concept", "design")):
            return "concept"
        if any(kw in title_lower for kw in ("recherche", "research", "evaluation")):
            return "research"
        return "concept"  # Default
```

---

## 5. outline_mcp — FastMCP Server (Windsurf-Integration)

Der zentrale Mehrwert: Windsurf/Cascade kann auf alle Konzepte und Unterlagen zugreifen.

```python
# mcp_hub/outline_mcp/server.py

"""outline_mcp — Outline Knowledge Base für Windsurf/Cascade (ADR-141 Kontext)."""

import logging
from functools import lru_cache

from fastmcp import FastMCP
from outline_wiki_api import OutlineWiki
from pydantic import BaseModel

from config.secrets import read_secret  # ADR-045

logger = logging.getLogger(__name__)
mcp = FastMCP("outline-knowledge")


@lru_cache(maxsize=1)
def _get_client() -> OutlineWiki:
    return OutlineWiki(
        url=read_secret("OUTLINE_URL", required=True),
        token=read_secret("OUTLINE_API_TOKEN", required=True),
    )


class SearchResult(BaseModel):
    title: str
    url: str
    context: str
    ranking: float
    doc_type: str


@mcp.tool()
async def search_knowledge(query: str, limit: int = 10) -> list[SearchResult]:
    """Sucht in der gesamten Knowledge Base (Konzepte, ADRs, Unterlagen).

    Args:
        query: Suchbegriff, z.B. "Django migration strategy" oder "bieterpilot Phase 2"
        limit: Max. Anzahl Ergebnisse (default: 10)

    Returns:
        Liste von Dokumenten mit Titel, URL, Kontext-Snippet und Ranking
    """
    client = _get_client()
    results = client.documents.search(query=query, limit=limit).data

    return [
        SearchResult(
            title=r.document.title,
            url=r.document.url or "",
            context=r.context[:300] if r.context else "",
            ranking=r.ranking,
            doc_type=_infer_doc_type(r.document.title),
        )
        for r in results
    ]


@mcp.tool()
async def get_document_content(document_id: str) -> dict:
    """Ruft den vollständigen Inhalt eines Outline-Dokuments ab.

    Args:
        document_id: Outline UUID des Dokuments

    Returns:
        Dict mit title, content (Markdown), url, updated_at
    """
    client = _get_client()
    doc = client.documents.info(id=document_id).data.document
    return {
        "title": doc.title,
        "content": doc.text or "",
        "url": doc.url or "",
        "updated_at": str(doc.updated_at) if doc.updated_at else None,
    }


@mcp.tool()
async def create_concept(
    title: str,
    content: str,
    collection_name: str = "Konzepte (in Arbeit)",
) -> dict:
    """Erstellt ein neues Konzept-Dokument in Outline.

    Args:
        title: Dokumenttitel, z.B. "Konzept: ship-workflow.sh"
        content: Markdown-Inhalt
        collection_name: Ziel-Collection (default: "Konzepte (in Arbeit)")

    Returns:
        Dict mit document_id und url des neuen Dokuments
    """
    client = _get_client()
    # Collection-ID aus Name auflösen
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

    return {"document_id": doc.id, "url": doc.url or ""}


@mcp.tool()
async def list_recent_concepts(limit: int = 20) -> list[dict]:
    """Listet die zuletzt aktualisierten Konzepte und Unterlagen.

    Args:
        limit: Anzahl der Ergebnisse (default: 20)
    """
    client = _get_client()
    docs = client.documents.list(limit=limit).data
    return [
        {
            "title": d.title,
            "url": d.url or "",
            "updated_at": str(d.updated_at) if d.updated_at else None,
        }
        for d in docs
    ]


def _infer_doc_type(title: str) -> str:
    t = title.lower()
    if t.startswith("adr-"):
        return "adr"
    if any(k in t for k in ("konzept", "concept")):
        return "concept"
    return "document"
```

---

## 6. Konkreter Mehrwert für deinen Arbeitsalltag

### 6.1 Workflow: Neues Konzept schreiben

```
Vorher:
  Notiz im Kopf → lokal irgendwo → Cascade kennt es nicht → Wiederholen

Nachher:
  Outline öffnen (knowledge.iil.pet) →
  Konzept in Markdown schreiben →
  Webhook → research-hub sync →
  Cascade: "search_knowledge('bieterpilot phase 2')" → findet Konzept sofort
```

### 6.2 Workflow: ADR-Draft → finales ADR

```
Outline: ADR-Draft in Collection "ADRs (in Arbeit)" →
Wenn fertig: Webhook → Celery-Task →
  Git-Commit in iil-platform-stack (automatisch via GitHub API) →
  PR für Review → nach Merge: Outline-Doc in "ADRs (final)" verschoben
```

### 6.3 Workflow: Recherche-Ergebnis festhalten

```
Recherche fertig →
Outline: Neues Doc in "Recherchen & Unterlagen" →
AI-Enrichment (Celery): Automatische Zusammenfassung + Keywords →
Nächste Woche: Cascade findet es via outline_mcp search_knowledge()
```

### 6.4 Was Cascade dann kann

Mit `outline_mcp` registriert in Windsurf:

```
Cascade: "Gibt es ein Konzept zur ship-workflow.sh?"
→ search_knowledge("ship-workflow staging production promote")
→ Findet dein Konzept aus letzter Woche
→ Implementiert direkt darauf aufbauend
```

---

## 7. Implementierungsplan

| Phase | Inhalt | Aufwand |
|-------|--------|---------|
| **1** | Outline Docker Compose auf CPX52, Cloudflare Access (knowledge.iil.pet) | 2h |
| **2** | Collections-Struktur anlegen, initiale Docs importieren | 1h |
| **3** | `KnowledgeDocument` Model + Migration in research-hub | 1h |
| **4** | Webhook-Handler + Outline-Signatur-Verifikation | 1h |
| **5** | `KnowledgeDocumentService` + `outline-wiki-api` Client | 2h |
| **6** | Celery-Tasks: sync + AI-Enrichment via llm_mcp | 2h |
| **7** | `outline_mcp` FastMCP Server + Windsurf-Integration | 2h |
| **8** | Tests + ADR-141-Ergänzung (outline_mcp als MCP-Server) | 1h |

**Gesamt: ~12h** — verteilt auf 2 Sessions

---

## 8. Was du brauchst (Voraussetzungen)

- [ ] Outline Docker Image: `outlinewiki/outline:latest` (kostenlos, BSL 1.1)
- [ ] `pip install outline-wiki-api` in research-hub
- [ ] Neues Subdomain: `knowledge.iil.pet` (Cloudflare DNS + Access)
- [ ] 2 neue Secrets: `OUTLINE_API_TOKEN`, `OUTLINE_WEBHOOK_SECRET`
- [ ] Outline braucht eigene PostgreSQL-DB (~200MB Basis)
- [ ] RAM-Bedarf: ~300MB für Outline + Redis

---

## 9. Lizenz & Kosten

| Komponente | Lizenz | Kosten |
|------------|--------|--------|
| Outline (self-hosted) | BSL 1.1 (kostenlos für <10 User) | **0 €** |
| outline-wiki-api (Python) | MIT | **0 €** |
| Hetzner CPX52 (bereits vorhanden) | — | **0 €** extra |
| Cloudflare Access | Free tier | **0 €** |

**Gesamtkosten: 0 €** — nur Entwicklungszeit.

---

## 10. Abgrenzung & Risiken

| Aspekt | Entscheidung |
|--------|-------------|
| Outline = Editor, Django = Metadaten | Single Source of Truth: Outline für Inhalt |
| Kein Ersetzen von ADR-Git-Workflow | Outline-ADRs sind Drafts — final bleibt Git |
| Outline-Enterprise nicht nötig | BSL 1.1 für Solo/kleines Team kostenlos |
| Webhook-Ausfall | Celery-Retry (max. 3x) + täglicher Full-Sync als Fallback |

---

*Konzept erstellt: 2026-03-13 | Bereit zur Entscheidung und Implementierung*
