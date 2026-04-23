"""Tests for outline_mcp tools using respx to mock httpx calls."""

import httpx
import pytest
import respx

from outline_mcp.client import OutlineClient


@pytest.fixture
def client():
    return OutlineClient(
        base_url="https://knowledge.iil.pet",
        api_token="ol_api_test_token_12345",
    )


@respx.mock
@pytest.mark.asyncio
async def test_search_documents(client, sample_search_response):
    respx.post("https://knowledge.iil.pet/api/documents.search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    result = await client.search_documents("OIDC troubleshooting")
    assert result["data"][0]["document"]["title"] == "OIDC Troubleshooting"
    assert len(result["data"]) == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_document(client, sample_document_response):
    respx.post("https://knowledge.iil.pet/api/documents.info").mock(
        return_value=httpx.Response(200, json=sample_document_response)
    )

    result = await client.get_document("doc-001")
    assert result["data"]["id"] == "doc-001"
    assert "OIDC Troubleshooting" in result["data"]["text"]


@respx.mock
@pytest.mark.asyncio
async def test_create_document(client, sample_create_response):
    respx.post("https://knowledge.iil.pet/api/documents.create").mock(
        return_value=httpx.Response(200, json=sample_create_response)
    )

    result = await client.create_document(
        title="New Runbook",
        text="# New Runbook\n\nContent here.",
        collection_id="a67c9777-3bc3-401a-9de3-91f0cc6c56d9",
    )
    assert result["data"]["id"] == "doc-new-001"


@respx.mock
@pytest.mark.asyncio
async def test_update_document(client, sample_document_response):
    respx.post("https://knowledge.iil.pet/api/documents.update").mock(
        return_value=httpx.Response(200, json=sample_document_response)
    )

    result = await client.update_document(
        document_id="doc-001",
        text="# Updated content",
    )
    assert result["data"]["id"] == "doc-001"


@respx.mock
@pytest.mark.asyncio
async def test_list_documents(client):
    mock_response = {
        "data": [
            {
                "id": "doc-001", "title": "Doc 1",
                "url": "/doc/1", "updatedAt": "2026-03-14T08:00:00Z",
            },
            {
                "id": "doc-002", "title": "Doc 2",
                "url": "/doc/2", "updatedAt": "2026-03-14T07:00:00Z",
            },
        ]
    }
    respx.post("https://knowledge.iil.pet/api/documents.list").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result = await client.list_documents(limit=5, offset=0)
    assert len(result["data"]) == 2


@respx.mock
@pytest.mark.asyncio
async def test_search_returns_error_on_401(client):
    respx.post("https://knowledge.iil.pet/api/documents.search").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.search_documents("test")


@respx.mock
@pytest.mark.asyncio
async def test_delete_document(client):
    respx.post("https://knowledge.iil.pet/api/documents.delete").mock(
        return_value=httpx.Response(200, json={"success": True})
    )

    result = await client.delete_document("doc-001")
    assert result["success"] is True


@respx.mock
@pytest.mark.asyncio
async def test_search_with_collection_filter(client, sample_search_response):
    route = respx.post("https://knowledge.iil.pet/api/documents.search").mock(
        return_value=httpx.Response(200, json=sample_search_response)
    )

    await client.search_documents("test", collection_id="col-123")
    assert route.called
    body = route.calls.last.request.content
    import json
    payload = json.loads(body)
    assert payload["collectionId"] == "col-123"


@respx.mock
@pytest.mark.asyncio
async def test_list_with_collection_filter(client):
    mock_response = {"data": []}
    route = respx.post("https://knowledge.iil.pet/api/documents.list").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    await client.list_documents(collection_id="col-456", limit=5, offset=10)
    assert route.called
    import json
    payload = json.loads(route.calls.last.request.content)
    assert payload["collectionId"] == "col-456"
    assert payload["limit"] == 5
    assert payload["offset"] == 10


@respx.mock
@pytest.mark.asyncio
async def test_list_collections(client):
    mock_response = {
        "data": [
            {"id": "col-001", "name": "Runbooks"},
            {"id": "col-002", "name": "Lessons Learned"},
        ]
    }
    respx.post("https://knowledge.iil.pet/api/collections.list").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result = await client.list_collections()
    assert len(result["data"]) == 2
    assert result["data"][0]["name"] == "Runbooks"
