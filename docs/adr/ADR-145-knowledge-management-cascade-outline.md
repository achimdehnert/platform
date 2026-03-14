---
status: "proposed"
date: 2026-03-14
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: ["ADR-143-knowledge-hub-outline-integration.md"]
related: ["ADR-143-knowledge-hub-outline-integration.md", "ADR-142-unified-identity-authentik-platform-idp.md", "ADR-132-ai-context-defense-in-depth.md", "ADR-114-discord-ide-like-communication-gateway.md", "ADR-116-dynamic-model-router.md", "ADR-044-mcp-server-lifecycle.md", "ADR-045-secrets-management.md", "ADR-050-hub-to-hub-webhook-auth.md", "ADR-062-celery-async-patterns.md", "ADR-095-aifw-quality-routing.md"]
implementation_status: not_started
review_status: "reviewed — 12 findings (3B/3K/3H/3M), all addressed in v2"
---

# ADR-145: Knowledge Management — Cascade ↔ Outline Anti-Knowledge-Drain

---

## 1. Kontext & Problemstellung

### 1.1 Das Knowledge-Drain-Problem

AI Coding Assistants (Cascade/Windsurf) generieren pro Session **enormes implizites Wissen**:

| Wissenstyp | Beispiel (aus OIDC-Session 2026-03-14) | Halbwertszeit |
|-------------|----------------------------------------|---------------|
| **Architektur-Entscheidungen** | "authentik braucht Signing Key + Scope Mappings auf jedem Provider" | Wochen |
| **Troubleshooting-Wissen** | "self-signed cert hinter Cloudflare Tunnel → NODE_TLS_REJECT_UNAUTHORIZED=0" | Monate |
| **Deployment-Patterns** | "extra_hosts: host-gateway für Container→Host→Nginx Routing" | Permanent |
| **Anti-Patterns** | "OIDC URIs: KEIN Slug im Pfad (/application/o/authorize/)" | Permanent |

Dieses Wissen existiert aktuell in **vier Silos**:

```
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE SILOS (Status Quo)              │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Chat-Verläufe│  │ Cascade      │  │ Entwickler-Kopf   │  │
│  │ (Windsurf)   │  │ Memories     │  │ (nicht skalierbar)│  │
│  │              │  │              │  │                    │  │
│  │ • Vergänglich│  │ • Kurze      │  │ • Single Point    │  │
│  │ • Nicht      │  │   Snippets   │  │   of Failure      │  │
│  │   durchsuch- │  │ • Nicht      │  │ • Nicht teilbar   │  │
│  │   bar        │  │   teilbar    │  │                    │  │
│  │ • Kontext    │  │ • Kein       │  │                    │  │
│  │   geht       │  │   Struktur-  │  │                    │  │
│  │   verloren   │  │   wissen     │  │                    │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ ADRs + Code (Git)                                     │    │
│  │ • Nur finales Ergebnis, nicht der Weg dorthin         │    │
│  │ • Kein Troubleshooting-Wissen, keine Lessons Learned  │    │
│  │ • Nicht von Cascade durchsuchbar (kein API-Zugriff)   │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Konkretes Problem: Session-Amnesie

**Szenario A — ohne Knowledge Hub:**
1. Session 1: OIDC-Integration debugging (3h) → Lösung gefunden
2. Session 2 (nächste Woche): doc-hub OIDC-Integration → gleiche Probleme, gleiches Debugging
3. Cascade hat Memories, aber: *"self-signed cert fix"* ist ein 10-Wort-Snippet — nicht das Runbook

**Szenario B — mit Knowledge Hub:**
1. Session 1: OIDC-Integration → Lösung als Runbook in Outline gespeichert
2. Session 2: `search_knowledge("OIDC authentik troubleshooting")` → Runbook gefunden → 10 Min statt 3h

### 1.3 Cascade Memory vs. strukturiertes Wissen

| Aspekt | Cascade Memory | Outline Knowledge Hub |
|--------|---------------|----------------------|
| **Format** | Kurze Text-Snippets (~500 Zeichen) | Vollständige Markdown-Dokumente |
| **Struktur** | Flach, Tag-basiert | Hierarchisch (Collections, Subcollections) |
| **Durchsuchbar** | Semantisch (Vektor) | Volltext + semantisch (AI-Keywords) |
| **Teilbar** | Nein (an Cascade-User gebunden) | Ja (OIDC-Login, Team-Zugang) |
| **Versioniert** | Nein | Ja (Outline hat Versionshistorie) |
| **Editierbar** | Nur via Cascade | Browser + API + Cascade |
| **Trigger** | Automatisch/manuell in Cascade | Bewusste Entscheidung |

**Beide ergänzen sich** — Memories für kurzfristigen Session-Kontext, Outline für langfristiges Strukturwissen.

---

## 2. Entscheidung

**Outline als Knowledge Hub für langfristiges, strukturiertes Wissen** — ergänzend zu Cascade Memories. Integration über drei Kanäle:

1. **Mensch → Outline**: Browser-Editor (knowledge.iil.pet)
2. **Cascade → Outline**: outline_mcp (MCP-Tools: suchen, lesen, schreiben)
3. **Outline → Cascade**: Session-Start-Ritual mit Knowledge-Lookup

### 2.1 Knowledge-Kategorien und Speicherort

| Kategorie | Speicherort | Trigger |
|-----------|-------------|---------|
| **Session-Kontext** (Variablennamen, aktuelle Aufgabe) | Cascade Memory | Automatisch |
| **Deployment-Facts** (Container, Ports, Domains) | Cascade Memory | Automatisch |
| **Runbooks** (Troubleshooting, Step-by-Step) | **Outline** | Manuell am Session-Ende |
| **Architektur-Konzepte** (Designs, Evaluationen) | **Outline** | Manuell beim Konzipieren |
| **Lessons Learned** (Anti-Patterns, Stolperfallen) | **Outline** | Manuell am Session-Ende |
| **ADR-Drafts** (in Arbeit) | **Outline** → Git | Manuell |
| **ADRs (final)** | Git (platform/docs/adr/) | Git-Workflow |
| **Hub-Dokumentation** (Setup, API, Konfiguration) | **Outline** | Bei Deployment/Änderungen |

### 2.2 Verworfene Alternative: Git-only Knowledge Store

Strukturierte Markdown-Dateien direkt in `platform/docs/knowledge/` + MCP-Server mit grep/ripgrep.

| Kriterium | Outline-Approach (gewählt) | Git-only |
|-----------|---------------------------|----------|
| **Kein Extra-Dependency** | ❌ Outline als Service | ✅ Nur Git |
| **Rich Editor** | ✅ Browser-Editor | ❌ Nur IDE |
| **Team-Sharing** | ✅ (OIDC) | ✅ (via Git) |
| **Versionshistorie** | ✅ Outline-intern | ✅ Git-nativ (besser) |
| **Single Source of Truth** | ⚠️ 2 SSOTs | ✅ Git = einziger SSOT |
| **Adoptions-Hürde** | ✅ Niedrig (Browser) | ❌ Hoch (IDE nötig) |

**Entscheidung**: Outline — weil der Browser-Editor die kritische Hürde "Disziplin für Session-Ende-Ritual" senkt. Der Nachteil (zwei SSOTs) wird durch klare Abgrenzung beherrschbar. **Git-only ist valider Fallback** wenn Outline-Betrieb zu aufwendig wird.

---

## 3. Architektur: Knowledge-Loop

### 3.1 Der Knowledge-Loop

```
                    ┌──────────────────────────┐
                    │     SESSION START          │
                    │                            │
                    │  1. Cascade Memory laden   │
                    │  2. outline_mcp:           │
                    │     search_knowledge()     │
                    │     → relevante Runbooks   │
                    │     → Konzepte             │
                    └──────────┬─────────────────┘
                               │
                    ┌──────────▼─────────────────┐
                    │     ARBEITEN                │
                    │                            │
                    │  • Code schreiben          │
                    │  • Debugging               │
                    │  • Architektur-Entscheide  │
                    │  • Troubleshooting         │
                    └──────────┬─────────────────┘
                               │
                    ┌──────────▼─────────────────┐
                    │     SESSION ENDE            │
                    │                            │
                    │  3. Cascade Memory update   │
                    │  4. outline_mcp:            │
                    │     create_or_update_doc()  │
                    │     → Runbook               │
                    │     → Lessons Learned        │
                    │     → Konzept-Update         │
                    └──────────┬─────────────────┘
                               │
                    ┌──────────▼─────────────────┐
                    │     ASYNC ENRICHMENT        │
                    │                            │
                    │  5. Webhook → research-hub  │
                    │     (HMAC-SHA256 signiert)  │
                    │  6. Celery: AI-Summary      │
                    │     (via aifw, ADR-095)     │
                    │  7. Celery: Keyword-Extract  │
                    │  8. Celery: ADR-Linking      │
                    └──────────────────────────────┘
```

### 3.2 outline_mcp — MCP Server Design

Registriert als `outline-knowledge` MCP-Server in Windsurf.

#### 3.2.1 HTTP-Client: `httpx.AsyncClient` direkt (kein `outline-wiki-api`)

> **Review-Fix B1**: `outline-wiki-api` (PyPI) ist unmaintained (letzter Commit 2022), keine
> Python 3.12-Kompatibilität, kein async-Support. Platform-Standard: `httpx.AsyncClient` direkt
> gegen die Outline REST-API. Keine Drittbibliothek.

```python
# outline_mcp/client.py — httpx.AsyncClient gegen Outline REST-API
import httpx

class OutlineClient:
    """Async HTTP-Client für Outline REST-API."""

    def __init__(self, base_url: str, api_token: str):
        self._client = httpx.AsyncClient(
            base_url=f"{base_url}/api",
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=httpx.Timeout(30.0),
        )

    async def search(self, query: str, collection_id: str | None = None,
                     limit: int = 10, offset: int = 0) -> dict:
        payload = {"query": query, "limit": limit, "offset": offset}
        if collection_id:
            payload["collectionId"] = collection_id
        resp = await self._client.post("documents.search", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def get_document(self, document_id: str) -> dict:
        resp = await self._client.post("documents.info", json={"id": document_id})
        resp.raise_for_status()
        return resp.json()

    async def create_document(self, title: str, text: str,
                              collection_id: str, publish: bool = True) -> dict:
        resp = await self._client.post("documents.create", json={
            "title": title, "text": text,
            "collectionId": collection_id, "publish": publish,
        })
        resp.raise_for_status()
        return resp.json()

    async def update_document(self, document_id: str, text: str) -> dict:
        resp = await self._client.post("documents.update", json={
            "id": document_id, "text": text, "done": True,
        })
        resp.raise_for_status()
        return resp.json()

    async def list_documents(self, limit: int = 20, offset: int = 0) -> dict:
        resp = await self._client.post("documents.list", json={
            "limit": limit, "offset": offset,
        })
        resp.raise_for_status()
        return resp.json()

    async def list_collections(self) -> dict:
        resp = await self._client.post("collections.list", json={})
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self._client.aclose()
```

#### 3.2.2 Lifespan-Hook (ADR-044 §3.3)

> **Review-Fix K1**: Alle MCP-Server mit HTTP-Clients MÜSSEN Lifecycle-Hooks via
> `@asynccontextmanager lifespan` nutzen. `httpx.AsyncClient` wird in `lifespan()` erstellt
> und in `server.state["client"]` gespeichert.

```python
# outline_mcp/server.py
from contextlib import asynccontextmanager
from fastmcp import FastMCP
from outline_mcp.client import OutlineClient
from outline_mcp.settings import Settings

@asynccontextmanager
async def lifespan(server: FastMCP):
    settings = Settings()
    client = OutlineClient(
        base_url=settings.outline_url,
        api_token=settings.outline_api_token,
    )
    try:
        server.state["client"] = client
        yield
    finally:
        await client.close()

mcp = FastMCP("outline-knowledge", lifespan=lifespan)
```

#### 3.2.3 Tools

| Tool | Parameter | Beschreibung | Wann nutzen |
|------|-----------|-------------|-------------|
| `search_knowledge` | `query, collection?, limit, offset` | Volltext-Suche | Session-Start, vor neuer Aufgabe |
| `get_document` | `document_id` | Vollständigen Markdown-Inhalt | Wenn Suchergebnis relevant |
| `create_runbook` | `title, content, related_adrs?` | Neues Runbook | Session-Ende nach Troubleshooting |
| `update_document` | `document_id, content` | Dokument aktualisieren | Wenn Runbook erweitert wird |
| `create_concept` | `title, content, related_adrs?` | Neues Konzept | Beim Konzipieren |
| `list_recent` | `collection?, limit, offset` | Zuletzt geänderte Docs | Überblick gewinnen |

> **Review-Fix M3**: `list_recent` erhält `offset: int = 0` Parameter für Pagination.

#### 3.2.4 Error Handling (ADR-044 §3.4)

> **Review-Fix H2**: Keine Exception-Messages oder Stack-Traces an Client. Jedes Tool hat
> `try/except` mit sanitisiertem JSON-Error-Objekt.

```python
@mcp.tool()
async def search_knowledge(query: str, collection: str | None = None,
                           limit: int = 10, offset: int = 0) -> list[dict]:
    """Sucht in der gesamten Knowledge Base."""
    client: OutlineClient = mcp.state["client"]
    try:
        result = await client.search(query, collection_id=collection,
                                      limit=limit, offset=offset)
        return [
            {"title": r["document"]["title"],
             "id": r["document"]["id"],
             "url": r["document"].get("url", ""),
             "context": (r.get("context") or "")[:300],
             "ranking": r.get("ranking", 0)}
            for r in result.get("data", [])
        ]
    except httpx.HTTPStatusError as e:
        return [{"error": f"Outline API returned {e.response.status_code}"}]
    except httpx.ConnectError:
        return [{"error": "Outline not reachable — check knowledge.iil.pet"}]
```

#### 3.2.5 Rate Limiting & Retry

> **Review-Fix H3**: `httpx`-Client mit `tenacity`-Retry (3 Versuche, exponential backoff).

```python
# In client.py — Retry-Decorator auf allen API-Methoden
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
    reraise=True,
)

class OutlineClient:
    @RETRY
    async def search(self, query: str, ...) -> dict: ...
```

#### 3.2.6 Settings (pydantic-settings)

```python
# outline_mcp/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    outline_url: str = "https://knowledge.iil.pet"
    outline_api_token: str
    model_config = {"env_prefix": "OUTLINE_MCP_"}
```

### 3.3 Collections-Struktur

```
📁 Runbooks
    ├── 📄 OIDC authentik Troubleshooting
    ├── 📄 Cloudflare Tunnel + Self-signed Cert
    ├── 📄 Docker Cross-Stack Networking (extra_hosts)
    ├── 📄 RLS Rollout Checklist
    └── 📄 Deployment: Neuen Hub aufsetzen
📁 Architektur-Konzepte
    ├── 📄 Knowledge-Loop: Cascade ↔ Outline
    ├── 📄 Multi-Tenant RLS Strategy
    └── 📄 Content-Store Architecture
📁 Lessons Learned
    ├── 📄 2026-03-14: OIDC 3 Root Causes
    ├── 📄 2026-03-12: RLS SQL-Split Bug
    └── 📄 2026-03-11: Cloudflare Tunnel TLS
📁 ADR-Drafts
    └── 📄 [In-Progress ADRs vor Git-Commit]
📁 Hub-Dokumentation
    ├── 📁 risk-hub
    ├── 📁 travel-beat
    ├── 📁 coach-hub
    └── 📁 ...
📁 ADRs (Read-Only Mirror)
    └── 📄 [AUTO-GENERATED — Änderungen werden beim Sync überschrieben]
```

> **Review-Fix H1**: ADR-Mirror-Dokumente erhalten automatisch den Header
> `<!-- AUTO-GENERATED — Änderungen werden beim nächsten Sync überschrieben. -->`
> Der Sync-Lauf (`sync_adrs_to_outline.sh`) überschreibt alle Outline-Änderungen —
> Git ist SSOT für finale ADRs. Outline hat kein natives Read-Only-Konzept für
> einzelne Collections, daher wird die Enforcement über den Sync-Mechanismus sichergestellt.

### 3.4 Session-Start Workflow

> **Review-Fix M1**: Workflow-Dateipfad gemäß ADR-043: `.windsurf/workflows/agent-session-start.md`

Erweiterung des bestehenden `/agent-session-start` Workflows um **Schritt 5 (Knowledge-Lookup)**:

```markdown
## Schritt 5 (NEU): Knowledge-Lookup

1. Identifiziere das Thema der aktuellen Aufgabe
2. outline_mcp: search_knowledge("<thema>")
3. Wenn Treffer:
   - Relevante Runbooks als Kontext laden (get_document)
   - Lessons Learned beachten
   - Konzepte als Basis nutzen
4. Wenn kein Treffer:
   - Neues Wissensgebiet — am Ende Runbook erstellen
```

### 3.5 Session-Ende Workflow

> **Review-Fix M1**: Workflow-Dateipfad: `.windsurf/workflows/knowledge-capture.md`

```markdown
## /knowledge-capture — Am Ende jeder produktiven Session

1. Prüfe: Wurde neues Troubleshooting-Wissen generiert?
   → Ja: create_runbook() mit Step-by-Step-Anleitung
2. Prüfe: Wurden Architektur-Entscheidungen getroffen?
   → Ja: create_concept() oder update_document()
3. Prüfe: Wurden Lessons Learned identifiziert?
   → Ja: create_runbook() in "Lessons Learned" Collection
4. Cascade Memory wie bisher updaten
```

---

## 4. Datenmodell: KnowledgeDocument (research-hub)

> **Review-Fix B3**: Vollständiges Django-Model mit allen Platform-Standards:
> `BigAutoField PK`, `public_id` UUIDField, `tenant_id` BigIntegerField,
> `deleted_at` DateTimeField, `UniqueConstraint`.

Platform-Standards: `BigAutoField PK`, `public_id`, `tenant_id`, `deleted_at`, `UniqueConstraint`.
Alle `verbose_name` und `help_text` mit `_()` (i18n ab Tag 1).
`related_adr_numbers` und `related_hubs` als `ArrayField` (DB-001: kein JSONField für strukturierte Listen).

Outline ist die **Single Source of Truth** für Inhalte. Django hält Metadaten, ADR-Links und AI-Enrichments.

**tenant_id-Strategie:** Outline ist ein internes Tool. `tenant_id = PLATFORM_INTERNAL_TENANT_ID` (Konstante `1`), definiert in `settings.py`.

```python
# research-hub/apps/knowledge/models.py

import uuid
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _


class KnowledgeDocumentStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    ARCHIVED = "archived", _("Archived")


class KnowledgeDocType(models.TextChoices):
    ADR = "adr", _("ADR")
    CONCEPT = "concept", _("Concept")
    HUB_DOC = "hub_doc", _("Hub Documentation")
    RESEARCH = "research", _("Research")
    MEETING_NOTE = "meeting_note", _("Meeting Note")
    RUNBOOK = "runbook", _("Runbook")
    LESSON = "lesson", _("Lesson Learned")


class KnowledgeDocument(models.Model):
    """Metadaten zu einem Outline-Dokument.

    Outline ist der Editor/Store — Django hält Metadaten,
    ADR-Links, AI-Enrichments und Platform-Kontext.
    """

    # Platform-Standards (BigAutoField PK implicit)
    public_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True,
        verbose_name=_("Public ID"),
    )
    tenant_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Tenant ID"),
        help_text=_("Always PLATFORM_INTERNAL_TENANT_ID (1) for knowledge docs"),
    )

    # Outline-Referenz
    outline_document_id = models.CharField(
        max_length=36, unique=True, db_index=True,
        verbose_name=_("Outline Document ID"),
    )
    outline_collection_id = models.CharField(
        max_length=36, db_index=True,
        verbose_name=_("Outline Collection ID"),
    )
    title = models.CharField(max_length=500, verbose_name=_("Title"))
    outline_url = models.URLField(blank=True, verbose_name=_("Outline URL"))

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
        choices=KnowledgeDocType.choices,
        db_index=True,
        verbose_name=_("Document Type"),
    )

    # ADR-Verknüpfung — ArrayField (DB-001 konform, kein JSONField)
    related_adr_numbers = ArrayField(
        models.IntegerField(),
        default=list, blank=True,
        verbose_name=_("Related ADR Numbers"),
        help_text=_("e.g. [141, 116, 82]"),
    )
    related_hubs = ArrayField(
        models.CharField(max_length=50),
        default=list, blank=True,
        verbose_name=_("Related Hubs"),
        help_text=_("e.g. ['coach-hub', 'risk-hub']"),
    )

    # AI-Enrichment
    ai_summary = models.TextField(blank=True, verbose_name=_("AI Summary"))
    ai_keywords = models.JSONField(
        default=list, blank=True, verbose_name=_("AI Keywords"),
        help_text=_("Variable structure — JSONField exception per DB-001"),
    )
    ai_enriched_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("AI Enriched At"),
    )

    # Sync-State
    outline_updated_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Last Outline Update"),
    )
    last_synced_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Last Synced"),
    )

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

---

## 5. Webhook: Outline → research-hub

> **Review-Fix B2**: HMAC-SHA256-Signatur-Verifikation (ADR-050). Webhook-Secret aus
> `.env` via `decouple.config()`. Ohne gültige Signatur → 401.

```python
# research-hub/apps/knowledge/views.py

import hashlib
import hmac
import json
import logging

from decouple import config
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

OUTLINE_WEBHOOK_SECRET = config("OUTLINE_WEBHOOK_SECRET")


@csrf_exempt
@require_POST
def outline_webhook(request):
    """Empfängt Outline-Webhooks mit HMAC-SHA256 Signatur-Verifikation."""
    signature_header = request.headers.get("Outline-Signature", "")
    if not _verify_signature(request.body, signature_header):
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

    if event in ("documents.create", "documents.update"):
        from apps.knowledge.tasks import sync_outline_document_task
        sync_outline_document_task.delay(outline_document_id=doc_id)
    elif event == "documents.delete":
        from apps.knowledge.services import KnowledgeDocumentService
        KnowledgeDocumentService.soft_delete(outline_document_id=doc_id)

    logger.info("Outline webhook processed", extra={"event": event, "doc_id": doc_id})
    return JsonResponse({"status": "ok"})


def _verify_signature(body: bytes, header: str) -> bool:
    """HMAC-SHA256 (ADR-050)."""
    if not header:
        return False
    try:
        parts = dict(part.split("=", 1) for part in header.split(","))
        timestamp = parts.get("t", "")
        received_sig = parts.get("v0", "")
    except (ValueError, AttributeError):
        return False

    expected = hmac.new(
        OUTLINE_WEBHOOK_SECRET.encode(),
        f"{timestamp}.{body.decode()}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received_sig)
```

---

## 6. Celery Tasks: Sync + AI-Enrichment

> **Review-Fix K2**: Kein `asyncio.run()` im Celery-Worker. Stattdessen
> `asgiref.sync.async_to_sync` für alle async Aufrufe (ADR-062, ADR-079).

> **Review-Fix M2**: AI-Enrichment über `aifw.generate()` mit
> `quality_level=QualityLevel.MEDIUM` (ADR-095-097 Quality-Level-Routing).
> Kein direkter LLM-Call.

```python
# research-hub/apps/knowledge/tasks.py

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30,
             name="knowledge.sync_outline_document")
def sync_outline_document_task(self, outline_document_id: str) -> dict:
    """Sync Outline-Dokument → KnowledgeDocument + trigger AI-Enrichment."""
    try:
        from apps.knowledge.services import KnowledgeDocumentService
        service = KnowledgeDocumentService()
        doc = service.sync_from_outline(outline_document_id)

        if service.needs_enrichment(doc):
            enrich_knowledge_document_task.delay(str(doc.public_id))

        return {"status": "synced", "public_id": str(doc.public_id)}
    except Exception as exc:
        logger.error("Outline sync failed",
                     extra={"doc_id": outline_document_id, "error": str(exc)})
        raise self.retry(exc=exc)


@shared_task(name="knowledge.enrich_document", max_retries=2)
def enrich_knowledge_document_task(public_id: str) -> dict:
    """AI-Enrichment via aifw (ADR-095)."""
    from asgiref.sync import async_to_sync
    from apps.knowledge.services import KnowledgeEnrichmentService

    service = KnowledgeEnrichmentService()
    # async_to_sync wraps aifw's async generate() for Celery context
    return async_to_sync(service.enrich)(public_id=public_id)
```

### 6.1 AI-Enrichment Service (aifw-Integration)

```python
# research-hub/apps/knowledge/services/enrichment_service.py

import logging
from django.utils import timezone

from aifw import generate, QualityLevel  # ADR-095

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Fasse das folgende Dokument in 2-3 Sätzen zusammen.
Fokus: Was ist die Kernentscheidung oder das Kernproblem?

---
{content}
"""

KEYWORDS_PROMPT = """Extrahiere 5-10 technische Keywords aus dem folgenden Dokument.
Gib sie als JSON-Liste zurück: ["keyword1", "keyword2", ...]

---
{content}
"""


class KnowledgeEnrichmentService:
    async def enrich(self, public_id: str) -> dict:
        from apps.knowledge.models import KnowledgeDocument
        doc = KnowledgeDocument.objects.get(public_id=public_id)

        # Hole Outline-Inhalt via httpx (sync, im Celery-Worker ok)
        content = await self._fetch_content(doc.outline_document_id)
        if not content:
            return {"status": "skipped", "reason": "empty content"}

        summary = await generate(
            prompt=SUMMARY_PROMPT.format(content=content[:4000]),
            quality_level=QualityLevel.MEDIUM,
        )
        keywords_raw = await generate(
            prompt=KEYWORDS_PROMPT.format(content=content[:4000]),
            quality_level=QualityLevel.FAST,
        )

        doc.ai_summary = summary.text
        doc.ai_keywords = self._parse_keywords(keywords_raw.text)
        doc.ai_enriched_at = timezone.now()
        doc.save(update_fields=["ai_summary", "ai_keywords", "ai_enriched_at", "updated_at"])

        return {"status": "enriched", "keywords": doc.ai_keywords}
```

---

## 7. ADR-Git-Sync Script

> **Review-Fix K3**: `set -euo pipefail`, idempotente Ausführung, explizite Exit-Codes.
> Script: `platform/scripts/sync_adrs_to_outline.sh`

Das Script ist vollständig implementiert in `docs/adr/inputs/outline integration/sync_adrs_to_outline.sh` und wird nach `platform/scripts/sync_adrs_to_outline.sh` deployed.

**Features:**
- `set -euo pipefail` (Platform-Standard)
- `--dry-run` und `--adr ADR-XXX` Flags
- Idempotent: `documents.search` → vorhanden? `update` : `create`
- `READONLY_HEADER` wird automatisch eingefügt
- Umgebungsvariablen: `OUTLINE_URL`, `OUTLINE_API_TOKEN`, `OUTLINE_COLLECTION_ADR_MIRROR`
- Explizite Exit-Codes: 0=ok, 2=missing env, 3=missing tool, 4=ADR not found, 5=sync errors

**ADR Mirror Enforcement (H1):**
```bash
readonly READONLY_HEADER="<!-- AUTO-GENERATED — Änderungen werden beim nächsten Sync
überschrieben. Bearbeite die Quelldatei in Git: platform/docs/adr/ -->"
```

---

## 8. Abgrenzung: Was NICHT in Outline gehört

| Was | Warum nicht | Wo stattdessen |
|-----|-------------|----------------|
| **Finalisierte ADRs** | Git ist Source of Truth für finale Entscheidungen | `platform/docs/adr/` |
| **Code-Snippets** | Gehören in den Code, nicht ins Wiki | Git Repos |
| **Secrets/Credentials** | Sicherheitsrisiko | `.env` Dateien (ADR-045) |
| **Temporäre Session-Notizen** | Zu kurzlebig für Wiki | Cascade Memory |
| **Automatisch generierte Logs** | Noise → Signal-Ratio zerstören | Grafana/Prometheus |

---

## 9. Implementierungsplan

### Phase 5.1–5.3: Collections + Runbooks + API-Token (1h 45min)

Keine Änderungen gegenüber v1.

### Phase 5.4: outline_mcp Server (4h)

> Aufwand +1h wegen Review-Fixes B1, K1, H2, H3, M3.

**Dateipfade (aus Review-Implementierungsplan):**

```
mcp-hub/
└── outline_mcp/
    ├── src/
    │   └── outline_mcp/
    │       ├── __init__.py         # __version__ = "0.1.0"
    │       ├── __main__.py         # python -m outline_mcp → mcp.run()
    │       ├── server.py           # FastMCP + lifespan + @mcp.tool()
    │       ├── settings.py         # pydantic-settings, env-basiert
    │       ├── models.py           # Pydantic I/O-Modelle
    │       └── client.py           # httpx.AsyncClient + tenacity retry
    ├── tests/
    │   ├── conftest.py
    │   └── test_tools.py
    └── pyproject.toml
```

### Phase 5.5: Windsurf-Registrierung (1h)

`.windsurf/mcp.json` Update + Integration-Test aller 6 Tools.

### Phase 5.6–5.7: Workflow-Dateien (1h)

- `.windsurf/workflows/agent-session-start.md` (update: Schritt 5 ergänzen)
- `.windsurf/workflows/knowledge-capture.md` (new)

### Phase 5.8: research-hub KnowledgeDocument + Webhook (3h)

**Dateipfade:**

```
research-hub/
└── apps/
    └── knowledge/
        ├── __init__.py
        ├── apps.py
        ├── models.py               # KnowledgeDocument (alle Platform-Standards)
        ├── services.py             # Service-Layer (ADR-041)
        ├── views.py                # Webhook mit HMAC-Auth (ADR-050)
        ├── urls.py
        └── migrations/
            └── 0001_initial.py
```

### Phase 5.9: Celery Enrichment (2h)

```
research-hub/
└── apps/
    └── knowledge/
        ├── tasks.py                # async_to_sync + aifw (ADR-095)
        └── services/
            └── enrichment_service.py
```

### Phase 5.10: ADR-Git-Sync (1h — Script bereits fertig)

```
platform/
└── scripts/
    └── sync_adrs_to_outline.sh     # set -euo pipefail, idempotent
```

### Übersicht

| Phase | Inhalt | Aufwand | Abhängigkeit |
|-------|--------|---------|-------------|
| **5.1** | Collections-Struktur in Outline anlegen | 30 min | Outline OIDC ✅ |
| **5.2** | Erste Runbooks manuell erstellen (OIDC, RLS, Tunnel) | 1h | 5.1 |
| **5.3** | Outline API-Token erstellen (für outline_mcp) | 15 min | 5.1 |
| **5.4** | outline_mcp FastMCP Server (httpx, lifespan, retry) | **4h** | 5.3 |
| **5.5** | outline_mcp in Windsurf registrieren + testen | 1h | 5.4 |
| **5.6** | `/agent-session-start` Knowledge-Lookup ergänzen | 30 min | 5.5 |
| **5.7** | `/knowledge-capture` Workflow erstellen | 30 min | 5.5 |
| **5.8** | research-hub: KnowledgeDocument + HMAC-Webhook | 3h | ADR-143 |
| **5.9** | Celery: AI-Enrichment via aifw (async_to_sync) | 2h | 5.8 |
| **5.10** | ADR-Git-Sync (Script vorhanden, deploy + test) | **1h** | 5.8 |

**Gesamt: ~15h** (Quick Wins nach 5.1-5.2, Cascade-Integration nach 5.5)

---

## 10. Metriken: Ist der Knowledge-Loop wirksam?

| Metrik | Messung | Ziel |
|--------|---------|------|
| **Runbooks erstellt** | Outline API: Dokumente in "Runbooks" Collection | ≥ 2 pro Woche |
| **Knowledge-Hits** | outline_mcp search_knowledge() calls mit relevanten Treffern | ≥ 50% Hit-Rate |
| **Wiederholtes Debugging** | Subjektiv: Gleiches Problem erneut gelöst? | 0 nach 4 Wochen |
| **Session-Startup-Zeit** | Zeit bis produktive Arbeit beginnt | < 5 Min (mit Kontext) |
| **Outline Engagement** | Logins pro Woche (authentik Logs) | ≥ 3 pro Woche |

---

## 11. Risiken & Gegenmaßnahmen

| Risiko | Wahrscheinlichkeit | Gegenmaßnahme |
|--------|-------------------|---------------|
| **Runbooks veralten** | Hoch | AI-Enrichment markiert Alter, Review-Reminder nach 90 Tagen |
| **Zu viel Noise** | Mittel | Klare Collections-Struktur, Quality Gate: nur echte Lessons Learned |
| **Outline-Ausfall** | Niedrig | Cascade Memories als Fallback, tägliches Backup |
| **Adoption scheitert** | Mittel | Quick Wins zuerst (Phase 5.1-5.2), Wert beweisen vor Automatisierung |
| **Duplizierung mit Memories** | Mittel | Klare Abgrenzung: Memories = Session-Kontext, Outline = Strukturwissen |

---

## 12. Konsequenzen

### Positiv

- **Knowledge Drain → Knowledge Loop**: Wissen bleibt erhalten und wächst
- **Cascade wird schlauer**: Zugriff auf Runbooks, Konzepte, Lessons Learned
- **Team-ready**: Wissen ist teilbar (OIDC-Login), nicht an eine Person gebunden
- **ADR-132 gelöst**: AI Context Amnesia durch strukturiertes Wissensmanagement adressiert
- **Skaliert**: Pattern funktioniert für 1 Person genauso wie für 10

### Negativ

- **Disziplin nötig**: Session-Ende-Ritual muss konsequent durchgeführt werden
- **Pflege-Aufwand**: Runbooks müssen aktuell gehalten werden
- **Zusätzliches Tool**: Outline neben Git, Discord, Grafana — Toolchain wird größer

---

## 13. Review-Findings Tracker

| # | Finding | Severity | Status | Adressiert in |
|---|---------|----------|--------|---------------|
| B1 | `outline-wiki-api` unmaintained → `httpx.AsyncClient` | 🔴 BLOCKER | ✅ Fixed | §3.2.1 |
| B2 | Webhook ohne Auth → HMAC-SHA256 | 🔴 BLOCKER | ✅ Fixed | §5 |
| B3 | KnowledgeDocument Platform-Standards | 🔴 BLOCKER | ✅ Fixed | §4 |
| K1 | Lifespan-Hook für httpx.AsyncClient | 🟠 KRITISCH | ✅ Fixed | §3.2.2 |
| K2 | Celery `asyncio.run()` → `async_to_sync` | 🟠 KRITISCH | ✅ Fixed | §6 |
| K3 | Git-Sync `set -euo pipefail` + Idempotenz | 🟠 KRITISCH | ✅ Fixed | §7 |
| H1 | ADR Mirror Read-Only Enforcement | 🟡 HOCH | ✅ Fixed | §3.3, §7 |
| H2 | Error Handling sanitisiert | 🟡 HOCH | ✅ Fixed | §3.2.4 |
| H3 | Rate Limiting + Retry | 🟡 HOCH | ✅ Fixed | §3.2.5 |
| M1 | Workflow-Dateipfade spezifiziert | 🟢 MEDIUM | ✅ Fixed | §3.4, §3.5 |
| M2 | AI-Enrichment via aifw | 🟢 MEDIUM | ✅ Fixed | §6.1 |
| M3 | `list_recent` offset-Parameter | 🟢 MEDIUM | ✅ Fixed | §3.2.3 |

---

## 14. Referenzen

- ADR-143: Knowledge-Hub — Outline Wiki (technische Architektur)
- ADR-142: Unified Identity — authentik als Platform IdP
- ADR-132: AI Context Defense-in-Depth
- ADR-044: MCP Server Lifecycle Hooks
- ADR-045: Secrets Management
- ADR-050: Hub-to-Hub Webhook Auth (HMAC)
- ADR-062: Celery Async Patterns
- ADR-095: aifw Quality-Level-Routing
- docs/guides/oidc-authentik-integration.md — OIDC Pattern Guide
- docs/adr/inputs/dms/konzept-outline-research-hub.md — Ursprungs-Konzept
- docs/adr/inputs/outline integration/sync_adrs_to_outline.sh — Git-Sync Script
