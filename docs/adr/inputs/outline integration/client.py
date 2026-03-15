"""Async HTTP client for the Outline REST API.

Fixes B1: replaces unmaintained outline-wiki-api PyPI package with
direct httpx.AsyncClient — no asyncio.to_thread() needed.

ADR-044 §3.3: Client is managed via lifespan hook in server.py.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from .models import (
    OutlineDocument,
    OutlineDocumentStub,
    OutlineSearchResult,
)
from .settings import OutlineMCPSettings

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Retry on network errors and HTTP 429/5xx only."""
    if isinstance(exc, httpx.TimeoutException | httpx.ConnectError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return False


class OutlineAPIError(Exception):
    """Raised when the Outline API returns an unexpected error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Outline API error {status_code}: {message}")


class OutlineClient:
    """Async Outline REST API client.

    Lifecycle: must be used inside the FastMCP lifespan context.
    Created via startup(), closed via shutdown().

    Usage:
        client = OutlineClient(settings)
        await client.startup()
        ...
        await client.shutdown()
    """

    def __init__(self, settings: OutlineMCPSettings) -> None:
        self._settings = settings
        self._http: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        """Initialize the HTTP client. Called in lifespan hook."""
        self._http = httpx.AsyncClient(
            base_url=self._settings.base_url,
            headers={
                "Authorization": f"Bearer {self._settings.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(self._settings.timeout),
            follow_redirects=True,
        )
        logger.info("OutlineClient started (base_url=%s)", self._settings.base_url)

    async def shutdown(self) -> None:
        """Close the HTTP client. Called in lifespan hook."""
        if self._http is not None:
            await self._http.aclose()
            self._http = None
            logger.info("OutlineClient shutdown complete.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            raise RuntimeError(
                "OutlineClient is not started. Ensure lifespan hook is active."
            )
        return self._http

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", response.text)
            except Exception:
                detail = response.text
            raise OutlineAPIError(response.status_code, detail)

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to Outline API with retry."""
        return await self._post_with_retry(path, payload)

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
        reraise=True,
    )
    async def _post_with_retry(
        self, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        response = await self._client().post(f"/api/{path}", json=payload)
        self._raise_for_status(response)
        return response.json()

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        collection_id: str | None = None,
        limit: int = 10,
    ) -> list[OutlineSearchResult]:
        """Search documents via Outline full-text + semantic search."""
        payload: dict[str, Any] = {"query": query, "limit": limit}
        if collection_id:
            payload["collectionId"] = collection_id

        data = await self._post("documents.search", payload)
        results = []
        for item in data.get("data", []):
            doc = item.get("document", {})
            results.append(
                OutlineSearchResult(
                    document_id=doc.get("id", ""),
                    title=doc.get("title", ""),
                    collection_id=doc.get("collectionId", ""),
                    collection_name=doc.get("collection", {}).get("name", ""),
                    url=doc.get("url", ""),
                    context=item.get("context", ""),
                    updated_at=doc.get("updatedAt", ""),
                )
            )
        return results

    async def get_document(self, document_id: str) -> OutlineDocument:
        """Fetch full document content by ID."""
        data = await self._post("documents.info", {"id": document_id})
        doc = data.get("data", {})
        return OutlineDocument(
            id=doc["id"],
            title=doc["title"],
            text=doc.get("text", ""),
            collection_id=doc.get("collectionId", ""),
            url=doc.get("url", ""),
            created_at=doc.get("createdAt", ""),
            updated_at=doc.get("updatedAt", ""),
            revision_count=doc.get("revisionCount", 0),
        )

    async def create_document(
        self,
        title: str,
        content: str,
        collection_id: str,
        parent_document_id: str | None = None,
    ) -> OutlineDocumentStub:
        """Create a new document in the specified collection."""
        payload: dict[str, Any] = {
            "title": title,
            "text": content,
            "collectionId": collection_id,
            "publish": True,
        }
        if parent_document_id:
            payload["parentDocumentId"] = parent_document_id

        data = await self._post("documents.create", payload)
        doc = data.get("data", {})
        return OutlineDocumentStub(
            id=doc["id"],
            title=doc["title"],
            collection_id=doc.get("collectionId", collection_id),
            url=doc.get("url", ""),
            updated_at=doc.get("updatedAt", ""),
        )

    async def update_document(
        self,
        document_id: str,
        content: str,
        append: bool = False,
    ) -> OutlineDocumentStub:
        """Update document content. If append=True, fetch existing and prepend."""
        if append:
            existing = await self.get_document(document_id)
            separator = "\n\n---\n\n"
            content = existing.text + separator + content

        data = await self._post(
            "documents.update",
            {"id": document_id, "text": content, "done": True},
        )
        doc = data.get("data", {})
        return OutlineDocumentStub(
            id=doc["id"],
            title=doc["title"],
            collection_id=doc.get("collectionId", ""),
            url=doc.get("url", ""),
            updated_at=doc.get("updatedAt", ""),
        )

    async def list_documents(
        self,
        collection_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[OutlineDocumentStub]:
        """List recently updated documents, optionally filtered by collection."""
        payload: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "sort": "updatedAt",
            "direction": "DESC",
        }
        if collection_id:
            payload["collectionId"] = collection_id

        data = await self._post("documents.list", payload)
        results = []
        for doc in data.get("data", []):
            results.append(
                OutlineDocumentStub(
                    id=doc["id"],
                    title=doc["title"],
                    collection_id=doc.get("collectionId", ""),
                    url=doc.get("url", ""),
                    updated_at=doc.get("updatedAt", ""),
                )
            )
        return results
