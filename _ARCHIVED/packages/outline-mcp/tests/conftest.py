"""Test fixtures for outline_mcp."""

import pytest


@pytest.fixture
def sample_search_response():
    return {
        "data": [
            {
                "document": {
                    "id": "doc-001",
                    "title": "OIDC Troubleshooting",
                    "url": "/doc/oidc-troubleshooting-abc123",
                },
                "context": "Signing Key is required for OAuth2 providers...",
                "ranking": 0.95,
            },
            {
                "document": {
                    "id": "doc-002",
                    "title": "Cloudflare Tunnel Setup",
                    "url": "/doc/cloudflare-tunnel-def456",
                },
                "context": "Use extra_hosts for container-to-host routing...",
                "ranking": 0.72,
            },
        ],
    }


@pytest.fixture
def sample_document_response():
    return {
        "data": {
            "id": "doc-001",
            "title": "OIDC Troubleshooting",
            "text": "# OIDC Troubleshooting\n\nStep 1: Check signing key...",
            "url": "/doc/oidc-troubleshooting-abc123",
            "updatedAt": "2026-03-14T08:30:00Z",
            "collectionId": "a67c9777-3bc3-401a-9de3-91f0cc6c56d9",
        },
    }


@pytest.fixture
def sample_create_response():
    return {
        "data": {
            "id": "doc-new-001",
            "title": "New Runbook",
            "url": "/doc/new-runbook-xyz789",
            "collectionId": "a67c9777-3bc3-401a-9de3-91f0cc6c56d9",
        },
    }
