"""outline_mcp FastMCP Server.

Fixes:
  B1: Direct httpx.AsyncClient (no outline-wiki-api, no asyncio.to_thread)
  K1: ADR-044 lifespan hook for OutlineClient
  H2: All tools have try/except with sanitized error output
  H3: tenacity retry built into client._post_with_retry()
  M3: list_recent has offset parameter

Registered in .windsurf/mcp.json as "outline-knowledge".
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastmcp import FastMCP

from .client import OutlineAPIError, OutlineClient
from .models import (
    CreateConceptInput,
    CreateLessonLearnedInput,
    CreateRunbookInput,
    GetDocumentInput,
    ListRecentInput,
    SearchKnowledgeInput,
    UpdateDocumentInput,
)
from .settings import OutlineMCPSettings, get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan — ADR-044 §3.3: all HTTP clients MUST use lifecycle hooks
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(server: FastMCP):  # type: ignore[type-arg]
    settings: OutlineMCPSettings = get_settings()
    client = OutlineClient(settings)
    await client.startup()
    server.state["client"] = client
    server.state["settings"] = settings
    try:
        yield
    finally:
        await client.shutdown()


# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="outline-knowledge",
    version="0.1.0",
    description=(
        "Knowledge Hub MCP Server for the iil-Platform-Stack. "
        "Search, read and write Runbooks, Architecture Concepts and Lessons Learned "
        "in the Outline Knowledge Hub (knowledge.iil.pet)."
    ),
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client(ctx: Any) -> OutlineClient:
    return ctx.fastmcp.state["client"]  # type: ignore[no-any-return]


def _settings(ctx: Any) -> OutlineMCPSettings:
    return ctx.fastmcp.state["settings"]  # type: ignore[no-any-return]


def _error(message: str) -> str:
    """Return a sanitized JSON error string — never expose internals to Cascade."""
    return json.dumps({"success": False, "error": message})


def _ok(data: Any) -> str:
    return json.dumps({"success": True, "data": data})


def _adr_footer(related_adrs: list[str]) -> str:
    if not related_adrs:
        return ""
    links = ", ".join(related_adrs)
    return f"\n\n---\n\n**Verwandte ADRs:** {links}"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def search_knowledge(
    query: str,
    collection_id: str | None = None,
    limit: int = 10,
) -> str:
    """Search the Outline Knowledge Hub (full-text + semantic).

    Use at session start to find relevant Runbooks, Concepts and Lessons Learned.
    Returns a list of matching documents with title, collection and a context snippet.

    Args:
        query: Search query (min 3 characters). Use concrete terms, e.g.
               "OIDC authentik troubleshooting" or "Docker extra_hosts networking".
        collection_id: Optional Outline collection UUID to restrict search scope.
                       Leave empty to search all collections.
        limit: Maximum number of results (1–50, default 10).

    Returns:
        JSON with list of matching documents or error object.
    """
    try:
        inp = SearchKnowledgeInput(query=query, collection_id=collection_id, limit=limit)
    except Exception:
        return _error("Invalid input: query must be at least 3 characters.")

    try:
        # Access client via mcp.state — available after lifespan startup
        client = mcp.state["client"]
        results = await client.search(inp.query, inp.collection_id, inp.limit)

        if not results:
            return _ok({"count": 0, "results": [], "hint": "No matches found. Try broader terms."})

        return _ok(
            {
                "count": len(results),
                "results": [
                    {
                        "document_id": r.document_id,
                        "title": r.title,
                        "collection": r.collection_name,
                        "context": r.context,
                        "url": r.url,
                        "updated_at": r.updated_at,
                    }
                    for r in results
                ],
            }
        )
    except OutlineAPIError as e:
        logger.error("search_knowledge API error: %s", e)
        return _error(f"Outline API error (HTTP {e.status_code}). Check Outline availability.")
    except Exception:
        logger.exception("search_knowledge unexpected error")
        return _error("Interner Fehler bei der Suche. Details im Server-Log.")


@mcp.tool()
async def get_document(document_id: str) -> str:
    """Fetch full Markdown content of a document by its Outline UUID.

    Use after search_knowledge to retrieve the complete Runbook or Concept.

    Args:
        document_id: Outline document UUID (from search_knowledge results).

    Returns:
        JSON with document title, full Markdown content, URL and metadata.
    """
    try:
        inp = GetDocumentInput(document_id=document_id)
    except Exception:
        return _error("Invalid input: document_id must be a non-empty string.")

    try:
        client = mcp.state["client"]
        doc = await client.get_document(inp.document_id)
        return _ok(
            {
                "id": doc.id,
                "title": doc.title,
                "content": doc.text,
                "url": doc.url,
                "collection_id": doc.collection_id,
                "updated_at": doc.updated_at,
                "revision_count": doc.revision_count,
            }
        )
    except OutlineAPIError as e:
        if e.status_code == 404:
            return _error(f"Document {document_id!r} not found in Outline.")
        logger.error("get_document API error: %s", e)
        return _error(f"Outline API error (HTTP {e.status_code}).")
    except Exception:
        logger.exception("get_document unexpected error")
        return _error("Interner Fehler beim Abrufen des Dokuments.")


@mcp.tool()
async def create_runbook(
    title: str,
    content: str,
    related_adrs: list[str] | None = None,
) -> str:
    """Create a new Runbook in the 'Runbooks' Outline collection.

    Use at session end after solving a technical problem (debugging, deployment, OIDC, etc.).
    Runbooks should contain step-by-step instructions, root cause and solution.

    Args:
        title: Descriptive title, e.g. "OIDC authentik: Self-Signed Cert hinter Cloudflare".
        content: Full Markdown content with ## Symptom, ## Root Cause, ## Steps, ## Verification.
        related_adrs: Optional list of related ADR IDs, e.g. ["ADR-142", "ADR-145"].

    Returns:
        JSON with created document ID and URL, or error object.
    """
    try:
        inp = CreateRunbookInput(
            title=title, content=content, related_adrs=related_adrs or []
        )
    except Exception as e:
        return _error(f"Ungültige Eingabe: {e}")

    try:
        client = mcp.state["client"]
        settings = mcp.state["settings"]

        collection_id = settings.collection_runbooks
        if not collection_id:
            return _error(
                "OUTLINE_COLLECTION_RUNBOOKS ist nicht konfiguriert. "
                "Bitte Collection-ID in .env setzen (Phase 5.3)."
            )

        full_content = (
            f"# {inp.title}\n\n"
            f"> **Erstellt:** {datetime.now(UTC).strftime('%Y-%m-%d')}  \n"
            f"> **Typ:** Runbook\n\n"
            f"{inp.content}"
            f"{_adr_footer(inp.related_adrs)}"
        )

        doc = await client.create_document(
            title=inp.title,
            content=full_content,
            collection_id=collection_id,
        )
        return _ok({"id": doc.id, "title": doc.title, "url": doc.url})
    except OutlineAPIError as e:
        logger.error("create_runbook API error: %s", e)
        return _error(f"Outline API error (HTTP {e.status_code}).")
    except Exception:
        logger.exception("create_runbook unexpected error")
        return _error("Interner Fehler beim Erstellen des Runbooks.")


@mcp.tool()
async def create_concept(
    title: str,
    content: str,
    related_adrs: list[str] | None = None,
) -> str:
    """Create a new Architecture Concept document in the 'Architektur-Konzepte' collection.

    Use when a significant architectural decision or design pattern is identified.
    Concepts are pre-ADR documents that capture options, trade-offs and rationale.

    Args:
        title: Concept title, e.g. "Multi-Tenant RLS Strategy v2".
        content: Full Markdown content with ## Kontext, ## Optionen, ## Entscheidung.
        related_adrs: Optional list of related ADR IDs.

    Returns:
        JSON with created document ID and URL, or error object.
    """
    try:
        inp = CreateConceptInput(
            title=title, content=content, related_adrs=related_adrs or []
        )
    except Exception as e:
        return _error(f"Ungültige Eingabe: {e}")

    try:
        client = mcp.state["client"]
        settings = mcp.state["settings"]

        collection_id = settings.collection_concepts
        if not collection_id:
            return _error(
                "OUTLINE_COLLECTION_CONCEPTS ist nicht konfiguriert. "
                "Bitte Collection-ID in .env setzen (Phase 5.3)."
            )

        full_content = (
            f"# {inp.title}\n\n"
            f"> **Erstellt:** {datetime.now(UTC).strftime('%Y-%m-%d')}  \n"
            f"> **Typ:** Architektur-Konzept\n\n"
            f"{inp.content}"
            f"{_adr_footer(inp.related_adrs)}"
        )

        doc = await client.create_document(
            title=inp.title,
            content=full_content,
            collection_id=collection_id,
        )
        return _ok({"id": doc.id, "title": doc.title, "url": doc.url})
    except OutlineAPIError as e:
        logger.error("create_concept API error: %s", e)
        return _error(f"Outline API error (HTTP {e.status_code}).")
    except Exception:
        logger.exception("create_concept unexpected error")
        return _error("Interner Fehler beim Erstellen des Konzepts.")


@mcp.tool()
async def create_lesson_learned(
    title: str,
    content: str,
    session_date: str,
    related_adrs: list[str] | None = None,
) -> str:
    """Create a Lesson Learned entry in the 'Lessons Learned' collection.

    Use at session end when a significant anti-pattern, bug root cause or
    non-obvious finding was identified that should be remembered.

    Args:
        title: Short title, e.g. "OIDC: Kein Slug im /application/o/ Pfad".
        content: Markdown with ## Problem, ## Ursache, ## Lösung, ## Anti-Pattern.
        session_date: Date of the session (YYYY-MM-DD), e.g. "2026-03-14".
        related_adrs: Optional list of related ADR IDs.

    Returns:
        JSON with created document ID and URL, or error object.
    """
    try:
        inp = CreateLessonLearnedInput(
            title=title,
            content=content,
            session_date=session_date,
            related_adrs=related_adrs or [],
        )
    except Exception as e:
        return _error(f"Ungültige Eingabe: {e}")

    try:
        client = mcp.state["client"]
        settings = mcp.state["settings"]

        collection_id = settings.collection_lessons
        if not collection_id:
            return _error(
                "OUTLINE_COLLECTION_LESSONS ist nicht konfiguriert. "
                "Bitte Collection-ID in .env setzen (Phase 5.3)."
            )

        prefixed_title = f"{inp.session_date}: {inp.title}"
        full_content = (
            f"# {prefixed_title}\n\n"
            f"> **Session-Datum:** {inp.session_date}  \n"
            f"> **Typ:** Lesson Learned\n\n"
            f"{inp.content}"
            f"{_adr_footer(inp.related_adrs)}"
        )

        doc = await client.create_document(
            title=prefixed_title,
            content=full_content,
            collection_id=collection_id,
        )
        return _ok({"id": doc.id, "title": doc.title, "url": doc.url})
    except OutlineAPIError as e:
        logger.error("create_lesson_learned API error: %s", e)
        return _error(f"Outline API error (HTTP {e.status_code}).")
    except Exception:
        logger.exception("create_lesson_learned unexpected error")
        return _error("Interner Fehler beim Erstellen des Lesson Learned.")


@mcp.tool()
async def update_document(
    document_id: str,
    content: str,
    append: bool = False,
) -> str:
    """Update an existing document in Outline.

    Use to extend an existing Runbook with new findings or correct outdated information.

    Args:
        document_id: Outline document UUID.
        content: New Markdown content (replaces full document) or content to append.
        append: If True, the content is appended to the existing document
                (separated by horizontal rule). Useful for adding new findings.

    Returns:
        JSON with updated document URL, or error object.
    """
    try:
        inp = UpdateDocumentInput(
            document_id=document_id, content=content, append=append
        )
    except Exception as e:
        return _error(f"Ungültige Eingabe: {e}")

    try:
        client = mcp.state["client"]
        doc = await client.update_document(
            inp.document_id, inp.content, append=inp.append
        )
        return _ok({"id": doc.id, "title": doc.title, "url": doc.url})
    except OutlineAPIError as e:
        if e.status_code == 404:
            return _error(f"Document {document_id!r} not found.")
        logger.error("update_document API error: %s", e)
        return _error(f"Outline API error (HTTP {e.status_code}).")
    except Exception:
        logger.exception("update_document unexpected error")
        return _error("Interner Fehler beim Aktualisieren des Dokuments.")


@mcp.tool()
async def list_recent(
    collection_id: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """List recently updated documents, optionally filtered by collection.

    Use to get an overview of recent Knowledge Hub activity at session start.

    Args:
        collection_id: Optional Outline collection UUID. None = all collections.
        limit: Number of documents to return (1–25, default 10).
        offset: Pagination offset (default 0). M3 fix: added for full pagination support.

    Returns:
        JSON with list of recent documents (id, title, collection, url, updated_at).
    """
    try:
        inp = ListRecentInput(collection_id=collection_id, limit=limit, offset=offset)
    except Exception as e:
        return _error(f"Ungültige Eingabe: {e}")

    try:
        client = mcp.state["client"]
        docs = await client.list_documents(inp.collection_id, inp.limit, inp.offset)
        return _ok(
            {
                "count": len(docs),
                "offset": inp.offset,
                "documents": [
                    {
                        "id": d.id,
                        "title": d.title,
                        "collection_id": d.collection_id,
                        "url": d.url,
                        "updated_at": d.updated_at,
                    }
                    for d in docs
                ],
            }
        )
    except OutlineAPIError as e:
        logger.error("list_recent API error: %s", e)
        return _error(f"Outline API error (HTTP {e.status_code}).")
    except Exception:
        logger.exception("list_recent unexpected error")
        return _error("Interner Fehler beim Abrufen der Dokumentenliste.")
