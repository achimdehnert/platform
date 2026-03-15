"""Tests for outline_mcp server tool functions.

Tests the MCP tool layer (search_knowledge, get_document, create_*,
update_document, list_recent) with mocked OutlineClient.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from outline_mcp.server import (
    _append_adr_refs,
    _create_in_collection,
)

# FastMCP wraps @mcp.tool() functions into FunctionTool objects.
# Access the underlying coroutine via .fn for direct testing.
from outline_mcp.server import (
    create_concept as _create_concept_tool,
    create_lesson as _create_lesson_tool,
    create_runbook as _create_runbook_tool,
    delete_document as _delete_document_tool,
    get_document as _get_document_tool,
    list_collections as _list_collections_tool,
    list_recent as _list_recent_tool,
    search_knowledge as _search_knowledge_tool,
    update_document as _update_document_tool,
)

search_knowledge = _search_knowledge_tool.fn
get_document = _get_document_tool.fn
create_runbook = _create_runbook_tool.fn
create_concept = _create_concept_tool.fn
create_lesson = _create_lesson_tool.fn
update_document = _update_document_tool.fn
list_recent = _list_recent_tool.fn
list_collections = _list_collections_tool.fn
delete_document = _delete_document_tool.fn


# --- Helper tests ---


def test_append_adr_refs_with_refs():
    result = _append_adr_refs("Content", "142,143")
    assert "ADR-142" in result
    assert "ADR-143" in result
    assert "---" in result


def test_append_adr_refs_without_refs():
    result = _append_adr_refs("Content", None)
    assert result == "Content"


def test_append_adr_refs_empty_string():
    result = _append_adr_refs("Content", "")
    assert result == "Content"


# --- Fixtures ---


@pytest.fixture(autouse=True)
def _mock_settings():
    """Mock settings for all tests."""
    with patch("outline_mcp.server._settings") as mock:
        mock.collection_runbooks = "col-runbooks"
        mock.collection_concepts = "col-concepts"
        mock.collection_lessons = "col-lessons"
        yield mock


@pytest.fixture
def mock_client():
    """Mock OutlineClient for all tests."""
    client = AsyncMock()
    with patch("outline_mcp.server._client", client):
        yield client


# --- search_knowledge ---


async def test_search_knowledge_success(mock_client):
    mock_client.search_documents.return_value = {
        "data": [
            {
                "document": {
                    "id": "doc-1",
                    "title": "Test Doc",
                    "url": "/doc/test",
                },
                "context": "Some context here",
                "ranking": 0.95,
            },
        ],
    }

    result = await search_knowledge("test query")
    assert len(result) == 1
    assert result[0]["title"] == "Test Doc"
    assert result[0]["ranking"] == 0.95


async def test_search_knowledge_connect_error(mock_client):
    mock_client.search_documents.side_effect = httpx.ConnectError("fail")

    result = await search_knowledge("test")
    assert len(result) == 1
    assert "not reachable" in result[0]["error"]


async def test_search_knowledge_http_error(mock_client):
    resp = httpx.Response(401, request=httpx.Request("POST", "http://x"))
    mock_client.search_documents.side_effect = httpx.HTTPStatusError(
        "unauthorized", request=resp.request, response=resp,
    )

    result = await search_knowledge("test")
    assert "401" in result[0]["error"]


# --- get_document ---


async def test_get_document_success(mock_client):
    mock_client.get_document.return_value = {
        "data": {
            "id": "doc-1",
            "title": "Full Doc",
            "text": "# Content",
            "url": "/doc/full",
            "updatedAt": "2026-03-15T08:00:00Z",
            "collectionId": "col-1",
        },
    }

    result = await get_document("doc-1")
    assert result["title"] == "Full Doc"
    assert result["text"] == "# Content"


async def test_get_document_connect_error(mock_client):
    mock_client.get_document.side_effect = httpx.ConnectError("fail")

    result = await get_document("doc-1")
    assert "error" in result
    assert "not reachable" in result["error"]


# --- _create_in_collection ---


async def test_create_in_collection_success(mock_client):
    mock_client.create_document.return_value = {
        "data": {
            "id": "new-1",
            "title": "New Doc",
            "url": "/doc/new",
        },
    }

    result = await _create_in_collection(
        collection_id="col-test",
        title="New Doc",
        content="# Content",
        related_adrs="145",
        tool_name="test_tool",
    )
    assert result["status"] == "created"
    assert result["id"] == "new-1"

    # Verify ADR refs were appended
    call_args = mock_client.create_document.call_args
    assert "ADR-145" in call_args.kwargs["text"]


async def test_create_in_collection_connect_error(mock_client):
    mock_client.create_document.side_effect = httpx.ConnectError("fail")

    result = await _create_in_collection(
        collection_id="col-test",
        title="New",
        content="x",
        related_adrs=None,
        tool_name="test_tool",
    )
    assert "error" in result
    assert "not reachable" in result["error"]


# --- create_runbook / create_concept / create_lesson ---


async def test_create_runbook_uses_runbooks_collection(mock_client):
    mock_client.create_document.return_value = {
        "data": {"id": "rb-1", "title": "RB", "url": "/doc/rb"},
    }

    result = await create_runbook("My Runbook", "# Steps")
    assert result["status"] == "created"

    call_args = mock_client.create_document.call_args
    assert call_args.kwargs["collection_id"] == "col-runbooks"


async def test_create_concept_uses_concepts_collection(mock_client):
    mock_client.create_document.return_value = {
        "data": {"id": "c-1", "title": "C", "url": "/doc/c"},
    }

    result = await create_concept("My Concept", "# Design")
    assert result["status"] == "created"

    call_args = mock_client.create_document.call_args
    assert call_args.kwargs["collection_id"] == "col-concepts"


async def test_create_lesson_uses_lessons_collection(mock_client):
    mock_client.create_document.return_value = {
        "data": {"id": "l-1", "title": "L", "url": "/doc/l"},
    }

    result = await create_lesson("My Lesson", "# Root Cause")
    assert result["status"] == "created"

    call_args = mock_client.create_document.call_args
    assert call_args.kwargs["collection_id"] == "col-lessons"


# --- update_document ---


async def test_update_document_success(mock_client):
    mock_client.update_document.return_value = {
        "data": {
            "id": "doc-1",
            "title": "Updated",
            "url": "/doc/updated",
        },
    }

    result = await update_document("doc-1", "# New content")
    assert result["status"] == "updated"
    assert result["title"] == "Updated"


async def test_update_document_with_title(mock_client):
    mock_client.update_document.return_value = {
        "data": {"id": "doc-1", "title": "New Title", "url": "/doc/1"},
    }

    await update_document("doc-1", "# Content", title="New Title")

    call_args = mock_client.update_document.call_args
    assert call_args.kwargs["title"] == "New Title"


# --- list_recent ---


async def test_list_recent_success(mock_client):
    mock_client.list_documents.return_value = {
        "data": [
            {
                "id": "doc-1",
                "title": "Recent 1",
                "url": "/doc/1",
                "updatedAt": "2026-03-15T08:00:00Z",
                "collectionId": "col-1",
            },
        ],
    }

    result = await list_recent()
    assert len(result) == 1
    assert result[0]["title"] == "Recent 1"


async def test_list_recent_connect_error(mock_client):
    mock_client.list_documents.side_effect = httpx.ConnectError("fail")

    result = await list_recent()
    assert len(result) == 1
    assert "not reachable" in result[0]["error"]


# --- Generic exception handlers (Review-Fix H2: sanitized errors) ---


async def test_search_knowledge_generic_exception(mock_client):
    mock_client.search_documents.side_effect = RuntimeError("unexpected")

    result = await search_knowledge("test")
    assert len(result) == 1
    assert "Internal error" in result[0]["error"]


async def test_get_document_generic_exception(mock_client):
    mock_client.get_document.side_effect = RuntimeError("unexpected")

    result = await get_document("doc-1")
    assert "error" in result
    assert "Internal error" in result["error"]


async def test_update_document_connect_error(mock_client):
    mock_client.update_document.side_effect = httpx.ConnectError("fail")

    result = await update_document("doc-1", "# Content")
    assert "error" in result
    assert "not reachable" in result["error"]


async def test_update_document_http_error(mock_client):
    resp = httpx.Response(403, request=httpx.Request("POST", "http://x"))
    mock_client.update_document.side_effect = httpx.HTTPStatusError(
        "forbidden", request=resp.request, response=resp,
    )

    result = await update_document("doc-1", "# Content")
    assert "403" in result["error"]


async def test_update_document_generic_exception(mock_client):
    mock_client.update_document.side_effect = RuntimeError("unexpected")

    result = await update_document("doc-1", "# Content")
    assert "error" in result
    assert "Internal error" in result["error"]


async def test_list_recent_http_error(mock_client):
    resp = httpx.Response(500, request=httpx.Request("POST", "http://x"))
    mock_client.list_documents.side_effect = httpx.HTTPStatusError(
        "server error", request=resp.request, response=resp,
    )

    result = await list_recent()
    assert len(result) == 1
    assert "500" in result[0]["error"]


async def test_list_recent_generic_exception(mock_client):
    mock_client.list_documents.side_effect = RuntimeError("unexpected")

    result = await list_recent()
    assert len(result) == 1
    assert "Internal error" in result[0]["error"]


async def test_create_in_collection_http_error(mock_client):
    resp = httpx.Response(422, request=httpx.Request("POST", "http://x"))
    mock_client.create_document.side_effect = httpx.HTTPStatusError(
        "unprocessable", request=resp.request, response=resp,
    )

    result = await _create_in_collection(
        collection_id="col-test",
        title="Fail",
        content="x",
        related_adrs=None,
        tool_name="test_tool",
    )
    assert "422" in result["error"]


async def test_create_in_collection_generic_exception(mock_client):
    mock_client.create_document.side_effect = RuntimeError("unexpected")

    result = await _create_in_collection(
        collection_id="col-test",
        title="Fail",
        content="x",
        related_adrs=None,
        tool_name="test_tool",
    )
    assert "Internal error" in result["error"]


# --- search with collection filter ---


async def test_search_knowledge_with_collection(mock_client):
    mock_client.search_documents.return_value = {"data": []}

    result = await search_knowledge("test", collection="col-123")
    assert result == []
    call_args = mock_client.search_documents.call_args
    assert call_args.kwargs["collection_id"] == "col-123"


# --- list_collections ---


async def test_list_collections_success(mock_client):
    mock_client.list_collections.return_value = {
        "data": [
            {"id": "col-1", "name": "Runbooks", "description": "How-to guides", "documents": []},
            {"id": "col-2", "name": "Concepts", "description": "Architecture", "documents": []},
        ],
    }

    result = await list_collections()
    assert len(result) == 2
    assert result[0]["name"] == "Runbooks"
    assert result[1]["id"] == "col-2"


async def test_list_collections_connect_error(mock_client):
    mock_client.list_collections.side_effect = httpx.ConnectError("fail")

    result = await list_collections()
    assert len(result) == 1
    assert "not reachable" in result[0]["error"]


# --- delete_document ---


async def test_delete_document_success(mock_client):
    mock_client.delete_document.return_value = {"success": True}

    result = await delete_document("doc-to-delete")
    assert result["status"] == "deleted"
    assert result["id"] == "doc-to-delete"


async def test_delete_document_connect_error(mock_client):
    mock_client.delete_document.side_effect = httpx.ConnectError("fail")

    result = await delete_document("doc-1")
    assert "not reachable" in result["error"]


async def test_delete_document_http_error(mock_client):
    resp = httpx.Response(404, request=httpx.Request("POST", "http://x"))
    mock_client.delete_document.side_effect = httpx.HTTPStatusError(
        "not found", request=resp.request, response=resp,
    )

    result = await delete_document("doc-nonexistent")
    assert "404" in result["error"]


async def test_list_recent_with_collection(mock_client):
    mock_client.list_documents.return_value = {"data": []}

    result = await list_recent(collection="col-456", limit=5, offset=10)
    assert result == []
    call_args = mock_client.list_documents.call_args
    assert call_args.kwargs["collection_id"] == "col-456"
    assert call_args.kwargs["limit"] == 5
    assert call_args.kwargs["offset"] == 10
