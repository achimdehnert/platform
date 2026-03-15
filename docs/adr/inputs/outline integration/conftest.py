"""Test fixtures for outline_mcp."""

from __future__ import annotations

import pytest
import pytest_asyncio
from pytest_httpx import HTTPXMock

from outline_mcp.client import OutlineClient
from outline_mcp.settings import OutlineMCPSettings


@pytest.fixture
def settings() -> OutlineMCPSettings:
    return OutlineMCPSettings(
        url="https://knowledge.test.iil.pet",
        api_token="test-token-000",
        timeout=5.0,
        retry_attempts=1,
        collection_runbooks="col-runbooks-uuid",
        collection_concepts="col-concepts-uuid",
        collection_lessons="col-lessons-uuid",
        collection_adr_drafts="col-adr-drafts-uuid",
        collection_adr_mirror="col-adr-mirror-uuid",
        collection_hub_docs="col-hub-docs-uuid",
    )


@pytest_asyncio.fixture
async def client(settings: OutlineMCPSettings) -> OutlineClient:  # type: ignore[misc]
    c = OutlineClient(settings)
    await c.startup()
    yield c
    await c.shutdown()


# Canonical Outline API response payloads for tests
SEARCH_RESPONSE = {
    "data": [
        {
            "document": {
                "id": "doc-uuid-001",
                "title": "OIDC authentik Troubleshooting",
                "collectionId": "col-runbooks-uuid",
                "collection": {"name": "Runbooks"},
                "url": "https://knowledge.test.iil.pet/doc/oidc-001",
                "updatedAt": "2026-03-14T10:00:00Z",
            },
            "context": "...self-signed cert hinter Cloudflare Tunnel...",
        }
    ],
    "pagination": {"total": 1, "limit": 10, "offset": 0},
}

DOCUMENT_INFO_RESPONSE = {
    "data": {
        "id": "doc-uuid-001",
        "title": "OIDC authentik Troubleshooting",
        "text": "## Symptom\n\nself-signed cert error...\n\n## Fix\n\nNODE_TLS_REJECT_UNAUTHORIZED=0",
        "collectionId": "col-runbooks-uuid",
        "url": "https://knowledge.test.iil.pet/doc/oidc-001",
        "createdAt": "2026-03-10T08:00:00Z",
        "updatedAt": "2026-03-14T10:00:00Z",
        "revisionCount": 3,
    }
}

CREATE_DOCUMENT_RESPONSE = {
    "data": {
        "id": "doc-uuid-new",
        "title": "New Runbook",
        "collectionId": "col-runbooks-uuid",
        "url": "https://knowledge.test.iil.pet/doc/new-runbook",
        "updatedAt": "2026-03-14T12:00:00Z",
    }
}

LIST_DOCUMENTS_RESPONSE = {
    "data": [
        {
            "id": "doc-uuid-001",
            "title": "OIDC authentik Troubleshooting",
            "collectionId": "col-runbooks-uuid",
            "url": "https://knowledge.test.iil.pet/doc/oidc-001",
            "updatedAt": "2026-03-14T10:00:00Z",
        }
    ],
    "pagination": {"total": 1, "limit": 10, "offset": 0},
}
