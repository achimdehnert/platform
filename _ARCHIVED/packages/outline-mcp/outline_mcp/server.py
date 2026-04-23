"""FastMCP server for Outline Wiki knowledge access (ADR-145).

Lifespan hook manages httpx.AsyncClient lifecycle (ADR-044 §3.3, Review-Fix K1).
Error handling returns sanitized JSON — no stack traces (Review-Fix H2).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastmcp import FastMCP

from outline_mcp.client import OutlineClient
from outline_mcp.settings import Settings

logger = logging.getLogger(__name__)


_client: OutlineClient | None = None
_settings: Settings | None = None


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Create and teardown OutlineClient (ADR-044 §3.3)."""
    global _client, _settings  # noqa: PLW0603
    _settings = Settings()
    _client = OutlineClient(
        base_url=_settings.outline_url,
        api_token=_settings.outline_api_token,
    )
    try:
        logger.info("outline_mcp connected to %s", _settings.outline_url)
        yield
    finally:
        await _client.close()
        _client = None
        logger.info("outline_mcp client closed")


mcp = FastMCP("outline-knowledge", lifespan=lifespan)


def _get_client() -> OutlineClient:
    assert _client is not None, "OutlineClient not initialized — lifespan not started"
    return _client


def _get_settings() -> Settings:
    assert _settings is not None, "Settings not initialized — lifespan not started"
    return _settings


def _error(msg: str) -> list[dict[str, Any]]:
    """Return sanitized error (Review-Fix H2)."""
    return [{"error": msg}]


# --- Helpers ---


def _append_adr_refs(text: str, related_adrs: str | None) -> str:
    """Append ADR references to document text."""
    if related_adrs:
        refs = ", ".join(f"ADR-{n.strip()}" for n in related_adrs.split(","))
        text += f"\n\n---\n\n**Referenzen:** {refs}\n"
    return text


async def _create_in_collection(
    collection_id: str,
    title: str,
    content: str,
    related_adrs: str | None,
    tool_name: str,
) -> dict[str, Any]:
    """Create a document in a specific Outline collection."""
    text = _append_adr_refs(content, related_adrs)
    try:
        result = await _get_client().create_document(
            title=title,
            text=text,
            collection_id=collection_id,
        )
        doc = result.get("data", {})
        return {
            "status": "created",
            "id": doc.get("id", ""),
            "url": doc.get("url", ""),
            "title": doc.get("title", ""),
        }
    except httpx.HTTPStatusError as e:
        return {"error": f"Outline API returned {e.response.status_code}"}
    except httpx.ConnectError:
        return {"error": "Outline not reachable"}
    except Exception:
        logger.exception("%s failed", tool_name)
        return {"error": f"Internal error in {tool_name}"}


# --- Tools ---


@mcp.tool()
async def search_knowledge(
    query: str,
    collection: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Search the entire knowledge base (Outline Wiki).

    Use at session start or before starting a new task to find
    relevant runbooks, concepts, and lessons learned.

    Args:
        query: Search term (fulltext + semantic)
        collection: Optional collection ID to narrow search
        limit: Max results (default 10)
        offset: Pagination offset (default 0)
    """
    try:
        result = await _get_client().search_documents(
            query=query,
            collection_id=collection,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "title": r["document"]["title"],
                "id": r["document"]["id"],
                "url": r["document"].get("url", ""),
                "context": (r.get("context") or "")[:300],
                "ranking": r.get("ranking", 0),
            }
            for r in result.get("data", [])
        ]
    except httpx.HTTPStatusError as e:
        return _error(f"Outline API returned {e.response.status_code}")
    except httpx.ConnectError:
        return _error("Outline not reachable — check knowledge.iil.pet")
    except Exception:
        logger.exception("search_knowledge failed")
        return _error("Internal error during search")


@mcp.tool()
async def get_document(document_id: str) -> dict[str, Any]:
    """Get the full Markdown content of an Outline document.

    Use when a search result looks relevant and you need the full content.

    Args:
        document_id: Outline document UUID (from search results)
    """
    try:
        result = await _get_client().get_document(document_id)
        doc = result.get("data", {})
        return {
            "title": doc.get("title", ""),
            "id": doc.get("id", ""),
            "text": doc.get("text", ""),
            "url": doc.get("url", ""),
            "updatedAt": doc.get("updatedAt", ""),
            "collectionId": doc.get("collectionId", ""),
        }
    except httpx.HTTPStatusError as e:
        return {"error": f"Outline API returned {e.response.status_code}"}
    except httpx.ConnectError:
        return {"error": "Outline not reachable"}
    except Exception:
        logger.exception("get_document failed")
        return {"error": "Internal error"}


@mcp.tool()
async def create_runbook(
    title: str,
    content: str,
    related_adrs: str | None = None,
) -> dict[str, Any]:
    """Create a new Runbook in the Runbooks collection.

    Use at session end after troubleshooting to capture step-by-step guides.

    Args:
        title: Runbook title (e.g. "OIDC authentik Troubleshooting")
        content: Full Markdown content
        related_adrs: Optional comma-separated ADR numbers (e.g. "142,143")
    """
    return await _create_in_collection(
        collection_id=_get_settings().collection_runbooks,
        title=title,
        content=content,
        related_adrs=related_adrs,
        tool_name="create_runbook",
    )


@mcp.tool()
async def create_concept(
    title: str,
    content: str,
    related_adrs: str | None = None,
) -> dict[str, Any]:
    """Create a new Architecture Concept in the Konzepte collection.

    Use when documenting design decisions, evaluations, or technical concepts.

    Args:
        title: Concept title
        content: Full Markdown content
        related_adrs: Optional comma-separated ADR numbers
    """
    return await _create_in_collection(
        collection_id=_get_settings().collection_concepts,
        title=title,
        content=content,
        related_adrs=related_adrs,
        tool_name="create_concept",
    )


@mcp.tool()
async def create_lesson(
    title: str,
    content: str,
    related_adrs: str | None = None,
) -> dict[str, Any]:
    """Create a new Lesson Learned in the Lessons Learned collection.

    Use when documenting anti-patterns, unexpected errors, or root causes
    discovered during debugging.

    Args:
        title: Lesson title (e.g. "2026-03-15: pytester INTERNALERROR")
        content: Full Markdown content (Kontext, Root Cause, Merksatz, Vermeidung)
        related_adrs: Optional comma-separated ADR numbers
    """
    return await _create_in_collection(
        collection_id=_get_settings().collection_lessons,
        title=title,
        content=content,
        related_adrs=related_adrs,
        tool_name="create_lesson",
    )


@mcp.tool()
async def update_document(
    document_id: str,
    content: str,
    title: str | None = None,
) -> dict[str, Any]:
    """Update an existing Outline document.

    Use when extending a runbook or updating a concept with new information.

    Args:
        document_id: Outline document UUID
        content: New full Markdown content (replaces existing)
        title: Optional new title
    """
    try:
        result = await _get_client().update_document(
            document_id=document_id,
            text=content,
            title=title,
        )
        doc = result.get("data", {})
        return {
            "status": "updated",
            "id": doc.get("id", ""),
            "url": doc.get("url", ""),
            "title": doc.get("title", ""),
        }
    except httpx.HTTPStatusError as e:
        return {"error": f"Outline API returned {e.response.status_code}"}
    except httpx.ConnectError:
        return {"error": "Outline not reachable"}
    except Exception:
        logger.exception("update_document failed")
        return {"error": "Internal error updating document"}


@mcp.tool()
async def list_recent(
    collection: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List recently updated documents.

    Use to get an overview of recent knowledge base activity.

    Args:
        collection: Optional collection ID to filter
        limit: Max results (default 10)
        offset: Pagination offset (default 0, Review-Fix M3)
    """
    try:
        result = await _get_client().list_documents(
            collection_id=collection,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "title": doc.get("title", ""),
                "id": doc.get("id", ""),
                "url": doc.get("url", ""),
                "updatedAt": doc.get("updatedAt", ""),
                "collectionId": doc.get("collectionId", ""),
            }
            for doc in result.get("data", [])
        ]
    except httpx.HTTPStatusError as e:
        return _error(f"Outline API returned {e.response.status_code}")
    except httpx.ConnectError:
        return _error("Outline not reachable")
    except Exception:
        logger.exception("list_recent failed")
        return _error("Internal error listing documents")


@mcp.tool()
async def list_collections() -> list[dict[str, Any]]:
    """List all collections in the knowledge base.

    Use to discover available collections and their IDs.
    """
    try:
        result = await _get_client().list_collections()
        return [
            {
                "name": col.get("name", ""),
                "id": col.get("id", ""),
                "description": col.get("description", ""),
                "documents": col.get("documents", []),
            }
            for col in result.get("data", [])
        ]
    except httpx.HTTPStatusError as e:
        return _error(f"Outline API returned {e.response.status_code}")
    except httpx.ConnectError:
        return _error("Outline not reachable")
    except Exception:
        logger.exception("list_collections failed")
        return _error("Internal error listing collections")


@mcp.tool()
async def get_document_by_url(url: str) -> dict[str, Any]:
    """Get an Outline document by its URL (no web request needed).

    Extracts the urlId from the URL and fetches via Outline API.
    Accepts full URLs like https://knowledge.iil.pet/doc/adr-156-0dRaORoWff
    or just the path like /doc/adr-156-0dRaORoWff.

    Args:
        url: Outline document URL or path
             (e.g. https://knowledge.iil.pet/doc/slug-AbCdEf)
    """
    try:
        # Extract slug from URL
        path = url.rstrip("/")
        if "/doc/" in path:
            slug = path.split("/doc/")[-1]
        else:
            slug = path.split("/")[-1]

        if not slug:
            return {"error": f"No slug found in: {url}"}

        # Strategy 1: search by keywords from slug
        parts = slug.split("-")
        # Remove urlId suffix (last alphanumeric part)
        keywords = " ".join(
            p for p in parts[:-1]
            if len(p) > 1 and not p.isdigit()
        )
        if not keywords:
            keywords = " ".join(parts)

        client = _get_client()
        result = await client.search_documents(
            query=keywords, limit=10,
        )
        # Match by URL suffix
        for r in result.get("data", []):
            doc = r.get("document", {})
            doc_url = doc.get("url", "")
            if doc_url.endswith(slug):
                full = await client.get_document(
                    doc["id"],
                )
                d = full.get("data", {})
                return {
                    "title": d.get("title", ""),
                    "id": d.get("id", ""),
                    "text": d.get("text", ""),
                    "url": d.get("url", ""),
                    "updatedAt": d.get("updatedAt", ""),
                    "collectionId": d.get("collectionId", ""),
                }

        # Strategy 2: list recent + match URL
        recent = await client.list_documents(limit=50)
        for doc in recent.get("data", []):
            doc_url = doc.get("url", "")
            if doc_url.endswith(slug):
                full = await client.get_document(
                    doc["id"],
                )
                d = full.get("data", {})
                return {
                    "title": d.get("title", ""),
                    "id": d.get("id", ""),
                    "text": d.get("text", ""),
                    "url": d.get("url", ""),
                    "updatedAt": d.get("updatedAt", ""),
                    "collectionId": d.get("collectionId", ""),
                }

        return {
            "error": (
                f"Document not found for {url}. "
                "It may be a draft or in a private "
                "collection not accessible via API."
            ),
        }
    except httpx.HTTPStatusError as e:
        return {
            "error": f"Outline API {e.response.status_code}",
        }
    except httpx.ConnectError:
        return {"error": "Outline not reachable"}
    except Exception:
        logger.exception(
            "get_document_by_url failed for %s", url,
        )
        return {"error": f"Error resolving: {url}"}


@mcp.tool()
async def delete_document(document_id: str) -> dict[str, Any]:
    """Delete a document from the knowledge base.

    Use for cleanup of test documents or outdated content.
    This is a destructive operation — the document will be moved to trash.

    Args:
        document_id: Outline document UUID to delete
    """
    try:
        await _get_client().delete_document(document_id)
        return {"status": "deleted", "id": document_id}
    except httpx.HTTPStatusError as e:
        return {"error": f"Outline API returned {e.response.status_code}"}
    except httpx.ConnectError:
        return {"error": "Outline not reachable"}
    except Exception:
        logger.exception("delete_document failed")
        return {"error": "Internal error deleting document"}
