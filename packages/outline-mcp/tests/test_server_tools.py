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
    create_concept,
    create_lesson,
    create_runbook,
    get_document,
    list_recent,
    search_knowledge,
    update_document,
)


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
