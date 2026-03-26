"""d.velop DMS REST API client (sync + async)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from dvelop_client.auth import DvelopAuth
from dvelop_client.exceptions import (
    DvelopAuthError,
    DvelopError,
    DvelopForbiddenError,
    DvelopNotFoundError,
    DvelopRateLimitError,
)
from dvelop_client.hal import extract_embedded, extract_location
from dvelop_client.models import (
    BlobRef,
    Category,
    DmsObject,
    DmsProperty,
    Repository,
    SearchResponse,
    SearchResult,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0


class DvelopClient:
    """Synchronous + async client for d.velop DMS REST API.

    Usage (sync context manager)::

        with DvelopClient(base_url="https://iil.d-velop.cloud",
                          api_key="...") as client:
            repos = client.list_repositories()

    Usage (async context manager)::

        async with DvelopClient(base_url="https://iil.d-velop.cloud",
                                api_key="...") as client:
            repos = await client.list_repositories_async()
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = DvelopAuth(api_key=api_key, base_url=self._base_url)
        self._timeout = timeout
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

    # -- Context managers --

    def __enter__(self) -> DvelopClient:
        self._sync_client = httpx.Client(
            base_url=self._base_url,
            auth=self._auth,
            timeout=self._timeout,
        )
        return self

    def __exit__(self, *exc: object) -> None:
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    async def __aenter__(self) -> DvelopClient:
        self._async_client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=self._auth,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    # -- Internal helpers --

    @property
    def _sc(self) -> httpx.Client:
        if self._sync_client is None:
            msg = "Use DvelopClient as context manager"
            raise RuntimeError(msg)
        return self._sync_client

    @property
    def _ac(self) -> httpx.AsyncClient:
        if self._async_client is None:
            msg = "Use DvelopClient as async context manager"
            raise RuntimeError(msg)
        return self._async_client

    def _handle_error(self, response: httpx.Response) -> None:
        """Raise typed exception based on HTTP status."""
        if response.is_success:
            return

        status = response.status_code
        body = response.text[:500]
        msg = f"d.velop API error {status}: {body}"

        if status == 401:
            raise DvelopAuthError(
                msg, status_code=status, response_body=body,
            )
        if status == 403:
            raise DvelopForbiddenError(
                msg, status_code=status, response_body=body,
            )
        if status == 404:
            raise DvelopNotFoundError(
                msg, status_code=status, response_body=body,
            )
        if status == 429:
            retry_after = response.headers.get("Retry-After")
            raise DvelopRateLimitError(
                msg,
                status_code=status,
                response_body=body,
                retry_after=(
                    int(retry_after) if retry_after else None
                ),
            )
        raise DvelopError(
            msg, status_code=status, response_body=body,
        )

    # -- Sync API --

    def list_repositories(self) -> list[Repository]:
        """List all DMS repositories."""
        response = self._sc.get("/dms/r")
        self._handle_error(response)
        data = response.json()
        # d.velop returns {"repositories": [...]} at /dms/r
        repos_data = data.get("repositories", [])
        if not repos_data:
            # Fallback: try _embedded
            repos_data = extract_embedded(data, "repositories")
        return [
            Repository(
                id=r.get("id", ""),
                name=r.get("name", ""),
                href=r.get("_links", {}).get("self", {}).get(
                    "href", "",
                ),
            )
            for r in repos_data
        ]

    def list_categories(
        self, repo_id: str,
    ) -> list[Category]:
        """List document definitions (categories) for a repo."""
        response = self._sc.get(
            f"/dms/r/{repo_id}/objdef",
        )
        self._handle_error(response)
        data = response.json()
        # Try multiple response shapes
        cats_data = data.get("objectDefinitions", [])
        if not cats_data:
            cats_data = extract_embedded(data, "sources")
        return [
            Category(
                key=c.get("id", c.get("key", "")),
                display_name=c.get("displayName", c.get("name", "")),
            )
            for c in cats_data
        ]

    def upload_blob(
        self,
        repo_id: str,
        content: bytes,
        filename: str,
        content_type: str = "application/pdf",
    ) -> BlobRef:
        """Step 1: Upload binary content as blob."""
        response = self._sc.post(
            f"/dms/r/{repo_id}/b",
            content=content,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                ),
            },
        )
        self._handle_error(response)
        location = extract_location(dict(response.headers))
        blob_id = location.rsplit("/", 1)[-1] if location else ""
        return BlobRef(
            blob_id=blob_id,
            location_uri=location,
            content_type=content_type,
        )

    def create_document(
        self,
        repo_id: str,
        blob_ref: BlobRef,
        category: str,
        properties: dict[str, str] | None = None,
    ) -> DmsObject:
        """Step 2: Create DMS object from uploaded blob."""
        source_properties = [
            {"key": k, "value": v}
            for k, v in (properties or {}).items()
        ]
        payload: dict[str, Any] = {
            "sourceCategory": category,
            "sourceProperties": source_properties,
            "contentLocationUri": blob_ref.location_uri,
        }
        response = self._sc.post(
            f"/dms/r/{repo_id}/o2",
            json=payload,
        )
        self._handle_error(response)
        location = extract_location(dict(response.headers))
        doc_id = location.rsplit("/", 1)[-1] if location else ""
        return DmsObject(
            id=doc_id,
            location_uri=location,
            repo_id=repo_id,
            category=category,
            properties=[
                DmsProperty(key=k, value=v)
                for k, v in (properties or {}).items()
            ],
        )

    def upload_document(
        self,
        repo_id: str,
        filename: str,
        content: bytes,
        category: str,
        properties: dict[str, str] | None = None,
        content_type: str = "application/pdf",
    ) -> DmsObject:
        """Convenience: 2-step upload (blob + object) in one call."""
        blob = self.upload_blob(
            repo_id, content, filename, content_type,
        )
        return self.create_document(
            repo_id, blob, category, properties,
        )

    def search(
        self,
        repo_id: str,
        query: str,
        *,
        max_results: int = 50,
    ) -> SearchResponse:
        """Full-text search in a repository."""
        response = self._sc.get(
            f"/dms/r/{repo_id}/sr",
            params={"fulltext": query, "maxresults": max_results},
        )
        self._handle_error(response)
        data = response.json()
        items_data = extract_embedded(data, "searchResults")
        items = [
            SearchResult(
                id=item.get("id", ""),
                title=item.get("title", ""),
                category=item.get("sourceCategory", ""),
                location_uri=item.get(
                    "_links", {},
                ).get("self", {}).get("href", ""),
            )
            for item in items_data
        ]
        return SearchResponse(
            items=items,
            total=data.get("total", len(items)),
        )

    def get_document(
        self, repo_id: str, doc_id: str,
    ) -> DmsObject:
        """Get a single document by ID."""
        response = self._sc.get(f"/dms/r/{repo_id}/o2/{doc_id}")
        self._handle_error(response)
        data = response.json()
        props = [
            DmsProperty(
                key=p.get("key", ""),
                value=p.get("value", ""),
                display_name=p.get("displayName", ""),
            )
            for p in data.get("sourceProperties", [])
        ]
        return DmsObject(
            id=doc_id,
            location_uri=data.get(
                "_links", {},
            ).get("self", {}).get("href", ""),
            repo_id=repo_id,
            category=data.get("sourceCategory", ""),
            properties=props,
        )

    # -- Async API --

    async def list_repositories_async(self) -> list[Repository]:
        """List all DMS repositories (async)."""
        response = await self._ac.get("/dms/r")
        self._handle_error(response)
        data = response.json()
        repos_data = data.get("repositories", [])
        if not repos_data:
            repos_data = extract_embedded(data, "repositories")
        return [
            Repository(
                id=r.get("id", ""),
                name=r.get("name", ""),
                href=r.get("_links", {}).get("self", {}).get(
                    "href", "",
                ),
            )
            for r in repos_data
        ]

    async def upload_blob_async(
        self,
        repo_id: str,
        content: bytes,
        filename: str,
        content_type: str = "application/pdf",
    ) -> BlobRef:
        """Step 1: Upload binary content as blob (async)."""
        response = await self._ac.post(
            f"/dms/r/{repo_id}/b",
            content=content,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                ),
            },
        )
        self._handle_error(response)
        location = extract_location(dict(response.headers))
        blob_id = location.rsplit("/", 1)[-1] if location else ""
        return BlobRef(
            blob_id=blob_id,
            location_uri=location,
            content_type=content_type,
        )

    async def create_document_async(
        self,
        repo_id: str,
        blob_ref: BlobRef,
        category: str,
        properties: dict[str, str] | None = None,
    ) -> DmsObject:
        """Step 2: Create DMS object from blob (async)."""
        source_properties = [
            {"key": k, "value": v}
            for k, v in (properties or {}).items()
        ]
        payload: dict[str, Any] = {
            "sourceCategory": category,
            "sourceProperties": source_properties,
            "contentLocationUri": blob_ref.location_uri,
        }
        response = await self._ac.post(
            f"/dms/r/{repo_id}/o2",
            json=payload,
        )
        self._handle_error(response)
        location = extract_location(dict(response.headers))
        doc_id = location.rsplit("/", 1)[-1] if location else ""
        return DmsObject(
            id=doc_id,
            location_uri=location,
            repo_id=repo_id,
            category=category,
            properties=[
                DmsProperty(key=k, value=v)
                for k, v in (properties or {}).items()
            ],
        )

    async def upload_document_async(
        self,
        repo_id: str,
        filename: str,
        content: bytes,
        category: str,
        properties: dict[str, str] | None = None,
        content_type: str = "application/pdf",
    ) -> DmsObject:
        """Convenience: 2-step upload (async)."""
        blob = await self.upload_blob_async(
            repo_id, content, filename, content_type,
        )
        return await self.create_document_async(
            repo_id, blob, category, properties,
        )

    # -- Sync wrappers for Celery tasks --

    def upload_document_sync(
        self,
        repo_id: str,
        filename: str,
        content: bytes,
        category: str,
        properties: dict[str, str] | None = None,
        content_type: str = "application/pdf",
    ) -> DmsObject:
        """Alias for upload_document (explicit sync naming)."""
        return self.upload_document(
            repo_id, filename, content,
            category, properties, content_type,
        )
