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


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Create and teardown OutlineClient (ADR-044 §3.3)."""
    settings = Settings()
    client = OutlineClient(
        base_url=settings.outline_url,
        api_token=settings.outline_api_token,
    )
    try:
        server.state["client"] = client
        server.state["settings"] = settings
        logger.info("outline_mcp connected to %s", settings.outline_url)
        yield
    finally:
        await client.close()
        logger.info("outline_mcp client closed")


mcp = FastMCP("outline-knowledge", lifespan=lifespan)


def _get_client() -> OutlineClient:
    return mcp.state["client"]


def _get_settings() -> Settings:
    return mcp.state["settings"]


def _error(msg: str) -> list[dict[str, Any]]:
    """Return sanitized error (Review-Fix H2)."""
    return [{"error": msg}]


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
    settings = _get_settings()
    text = content
    if related_adrs:
        refs = ", ".join(f"ADR-{n.strip()}" for n in related_adrs.split(","))
        text += f"\n\n---\n\n**Referenzen:** {refs}\n"

    try:
        result = await _get_client().create_document(
            title=title,
            text=text,
            collection_id=settings.collection_runbooks,
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
        logger.exception("create_runbook failed")
        return {"error": "Internal error creating runbook"}


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
    settings = _get_settings()
    text = content
    if related_adrs:
        refs = ", ".join(f"ADR-{n.strip()}" for n in related_adrs.split(","))
        text += f"\n\n---\n\n**Referenzen:** {refs}\n"

    try:
        result = await _get_client().create_document(
            title=title,
            text=text,
            collection_id=settings.collection_concepts,
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
        logger.exception("create_concept failed")
        return {"error": "Internal error creating concept"}


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
