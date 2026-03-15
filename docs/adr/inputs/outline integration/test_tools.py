"""Tests for outline_mcp client and server tools.

Coverage target: ≥80% on client.py and server.py (ADR-044 §3.6).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from outline_mcp.client import OutlineAPIError, OutlineClient
from outline_mcp.models import OutlineDocument, OutlineDocumentStub, OutlineSearchResult
from outline_mcp.settings import OutlineMCPSettings

from .conftest import (
    CREATE_DOCUMENT_RESPONSE,
    DOCUMENT_INFO_RESPONSE,
    LIST_DOCUMENTS_RESPONSE,
    SEARCH_RESPONSE,
)


# ---------------------------------------------------------------------------
# OutlineClient unit tests (via pytest-httpx mock)
# ---------------------------------------------------------------------------


class TestOutlineClientSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.search",
            json=SEARCH_RESPONSE,
        )
        results = await client.search("OIDC troubleshooting", limit=10)

        assert len(results) == 1
        assert isinstance(results[0], OutlineSearchResult)
        assert results[0].document_id == "doc-uuid-001"
        assert results[0].title == "OIDC authentik Troubleshooting"
        assert results[0].collection_name == "Runbooks"

    @pytest.mark.asyncio
    async def test_search_with_collection_id_passes_param(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.search",
            json=SEARCH_RESPONSE,
        )
        await client.search("OIDC", collection_id="col-runbooks-uuid")
        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["collectionId"] == "col-runbooks-uuid"

    @pytest.mark.asyncio
    async def test_search_empty_results(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.search",
            json={"data": [], "pagination": {"total": 0}},
        )
        results = await client.search("nonexistent topic xyz")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_api_error_raises(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.search",
            status_code=401,
            json={"error": "Unauthorized"},
        )
        with pytest.raises(OutlineAPIError) as exc_info:
            await client.search("test")
        assert exc_info.value.status_code == 401


class TestOutlineClientGetDocument:
    @pytest.mark.asyncio
    async def test_get_document_returns_full_content(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.info",
            json=DOCUMENT_INFO_RESPONSE,
        )
        doc = await client.get_document("doc-uuid-001")

        assert isinstance(doc, OutlineDocument)
        assert doc.id == "doc-uuid-001"
        assert "NODE_TLS_REJECT_UNAUTHORIZED" in doc.text
        assert doc.revision_count == 3

    @pytest.mark.asyncio
    async def test_get_document_not_found_raises(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.info",
            status_code=404,
            json={"error": "Not found"},
        )
        with pytest.raises(OutlineAPIError) as exc_info:
            await client.get_document("nonexistent-id")
        assert exc_info.value.status_code == 404


class TestOutlineClientCreateDocument:
    @pytest.mark.asyncio
    async def test_create_document_returns_stub(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.create",
            json=CREATE_DOCUMENT_RESPONSE,
        )
        stub = await client.create_document(
            title="New Runbook",
            content="## Content",
            collection_id="col-runbooks-uuid",
        )

        assert isinstance(stub, OutlineDocumentStub)
        assert stub.id == "doc-uuid-new"
        assert stub.url.startswith("https://")

    @pytest.mark.asyncio
    async def test_create_document_sends_publish_true(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.create",
            json=CREATE_DOCUMENT_RESPONSE,
        )
        await client.create_document("T", "C", "col-uuid")
        body = json.loads(httpx_mock.get_request().content)
        assert body["publish"] is True


class TestOutlineClientUpdateDocument:
    @pytest.mark.asyncio
    async def test_update_replace_mode(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.update",
            json=CREATE_DOCUMENT_RESPONSE,
        )
        stub = await client.update_document("doc-uuid-001", "New content", append=False)
        assert isinstance(stub, OutlineDocumentStub)
        body = json.loads(httpx_mock.get_request().content)
        assert body["text"] == "New content"

    @pytest.mark.asyncio
    async def test_update_append_mode_fetches_existing(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        # First call: documents.info (for existing content)
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.info",
            json=DOCUMENT_INFO_RESPONSE,
        )
        # Second call: documents.update
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.update",
            json=CREATE_DOCUMENT_RESPONSE,
        )
        await client.update_document("doc-uuid-001", "## New Finding", append=True)

        update_request = httpx_mock.get_requests()[-1]
        body = json.loads(update_request.content)
        assert "## New Finding" in body["text"]
        assert "NODE_TLS_REJECT_UNAUTHORIZED" in body["text"]  # original content preserved


class TestOutlineClientListDocuments:
    @pytest.mark.asyncio
    async def test_list_returns_stubs(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.list",
            json=LIST_DOCUMENTS_RESPONSE,
        )
        docs = await client.list_documents(limit=10, offset=0)
        assert len(docs) == 1
        assert isinstance(docs[0], OutlineDocumentStub)

    @pytest.mark.asyncio
    async def test_list_passes_offset(
        self, client: OutlineClient, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://knowledge.test.iil.pet/api/documents.list",
            json=LIST_DOCUMENTS_RESPONSE,
        )
        await client.list_documents(offset=20)
        body = json.loads(httpx_mock.get_request().content)
        assert body["offset"] == 20


# ---------------------------------------------------------------------------
# Server tool tests (mocked client via mcp.state)
# ---------------------------------------------------------------------------


def _make_mock_state(settings: OutlineMCPSettings) -> dict:
    mock_client = AsyncMock(spec=OutlineClient)
    return {"client": mock_client, "settings": settings}


class TestSearchKnowledgeTool:
    @pytest.mark.asyncio
    async def test_returns_results_json(self, settings: OutlineMCPSettings) -> None:
        from outline_mcp import server

        mock_results = [
            OutlineSearchResult(
                document_id="d1",
                title="OIDC Runbook",
                collection_id="col-runbooks-uuid",
                collection_name="Runbooks",
                url="https://knowledge.iil.pet/d1",
                context="...authentik OIDC...",
                updated_at="2026-03-14T10:00:00Z",
            )
        ]
        with patch.object(server.mcp, "state", _make_mock_state(settings)) as state:
            state["client"].search = AsyncMock(return_value=mock_results)
            result = await server.search_knowledge("OIDC authentik")

        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["count"] == 1
        assert data["data"]["results"][0]["title"] == "OIDC Runbook"

    @pytest.mark.asyncio
    async def test_short_query_returns_error(self, settings: OutlineMCPSettings) -> None:
        from outline_mcp import server

        with patch.object(server.mcp, "state", _make_mock_state(settings)):
            result = await server.search_knowledge("ab")  # too short

        data = json.loads(result)
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_api_error_returns_sanitized_message(
        self, settings: OutlineMCPSettings
    ) -> None:
        from outline_mcp import server

        with patch.object(server.mcp, "state", _make_mock_state(settings)) as state:
            state["client"].search = AsyncMock(
                side_effect=OutlineAPIError(503, "Service Unavailable")
            )
            result = await server.search_knowledge("OIDC troubleshooting")

        data = json.loads(result)
        assert data["success"] is False
        # Must NOT expose internal details
        assert "503" in data["error"]
        assert "Service Unavailable" not in data["error"]  # internal detail hidden


class TestCreateRunbookTool:
    @pytest.mark.asyncio
    async def test_creates_runbook_with_collection(
        self, settings: OutlineMCPSettings
    ) -> None:
        from outline_mcp import server

        stub = OutlineDocumentStub(
            id="new-doc",
            title="Test Runbook",
            collection_id="col-runbooks-uuid",
            url="https://knowledge.iil.pet/new-doc",
            updated_at="2026-03-14T12:00:00Z",
        )
        with patch.object(server.mcp, "state", _make_mock_state(settings)) as state:
            state["client"].create_document = AsyncMock(return_value=stub)
            result = await server.create_runbook(
                title="Docker extra_hosts Networking",
                content="## Steps\n1. Add extra_hosts...",
                related_adrs=["ADR-145"],
            )

        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["url"] == "https://knowledge.iil.pet/new-doc"

    @pytest.mark.asyncio
    async def test_missing_collection_id_returns_error(
        self, settings: OutlineMCPSettings
    ) -> None:
        from outline_mcp import server

        settings_no_col = settings.model_copy(update={"collection_runbooks": ""})
        with patch.object(
            server.mcp, "state", {"client": AsyncMock(), "settings": settings_no_col}
        ):
            result = await server.create_runbook("T", "Content here...", [])

        data = json.loads(result)
        assert data["success"] is False
        assert "OUTLINE_COLLECTION_RUNBOOKS" in data["error"]


class TestListRecentTool:
    @pytest.mark.asyncio
    async def test_list_recent_with_offset(self, settings: OutlineMCPSettings) -> None:
        from outline_mcp import server

        stub = OutlineDocumentStub(
            id="d1",
            title="Recent Doc",
            collection_id="col-runbooks-uuid",
            url="https://knowledge.iil.pet/d1",
            updated_at="2026-03-14T10:00:00Z",
        )
        with patch.object(server.mcp, "state", _make_mock_state(settings)) as state:
            state["client"].list_documents = AsyncMock(return_value=[stub])
            result = await server.list_recent(offset=10, limit=5)

        data = json.loads(result)
        assert data["success"] is True
        assert data["data"]["offset"] == 10
        assert len(data["data"]["documents"]) == 1
