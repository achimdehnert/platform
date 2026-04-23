"""Async HTTP client for Outline REST API (ADR-145, Review-Fix B1).

Uses httpx.AsyncClient directly — no outline-wiki-api dependency.
Retry via tenacity (Review-Fix H3).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

RETRY_POLICY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
    reraise=True,
)


class OutlineClient:
    """Async HTTP client for Outline REST API."""

    def __init__(self, base_url: str, api_token: str, timeout: float = 30.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/api",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )

    # --- Documents ---

    @RETRY_POLICY
    async def search_documents(
        self,
        query: str,
        collection_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"query": query, "limit": limit, "offset": offset}
        if collection_id:
            payload["collectionId"] = collection_id
        resp = await self._client.post("documents.search", json=payload)
        resp.raise_for_status()
        return resp.json()

    @RETRY_POLICY
    async def get_document(self, document_id: str) -> dict[str, Any]:
        resp = await self._client.post("documents.info", json={"id": document_id})
        resp.raise_for_status()
        return resp.json()

    @RETRY_POLICY
    async def create_document(
        self,
        title: str,
        text: str,
        collection_id: str,
        publish: bool = True,
    ) -> dict[str, Any]:
        resp = await self._client.post(
            "documents.create",
            json={
                "title": title,
                "text": text,
                "collectionId": collection_id,
                "publish": publish,
            },
        )
        resp.raise_for_status()
        return resp.json()

    @RETRY_POLICY
    async def update_document(
        self,
        document_id: str,
        text: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"id": document_id, "text": text}
        if title:
            payload["title"] = title
        resp = await self._client.post("documents.update", json=payload)
        resp.raise_for_status()
        return resp.json()

    @RETRY_POLICY
    async def list_documents(
        self,
        collection_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"limit": limit, "offset": offset}
        if collection_id:
            payload["collectionId"] = collection_id
        resp = await self._client.post("documents.list", json=payload)
        resp.raise_for_status()
        return resp.json()

    @RETRY_POLICY
    async def delete_document(self, document_id: str) -> dict[str, Any]:
        resp = await self._client.post("documents.delete", json={"id": document_id})
        resp.raise_for_status()
        return resp.json()

    @RETRY_POLICY
    async def get_document_by_url_id(
        self, url_id: str,
    ) -> dict[str, Any]:
        """Fetch document by Outline urlId (slug suffix)."""
        resp = await self._client.post(
            "documents.info", json={"urlId": url_id},
        )
        resp.raise_for_status()
        return resp.json()

    # --- Collections ---

    @RETRY_POLICY
    async def list_collections(self) -> dict[str, Any]:
        resp = await self._client.post("collections.list", json={})
        resp.raise_for_status()
        return resp.json()

    # --- Lifecycle ---

    async def close(self) -> None:
        await self._client.aclose()
