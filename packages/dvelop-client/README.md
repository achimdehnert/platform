# iil-dvelop-client

Python client for the [d.velop DMS REST API](https://help.d-velop.de/dev) (JSON-HAL, Bearer Auth, 2-Step Blob Upload).

## Installation

```bash
pip install iil-dvelop-client
```

## Quick Start

```python
from dvelop_client import DvelopClient

with DvelopClient(base_url="https://iil.d-velop.cloud", api_key="...") as client:
    # List repositories
    repos = client.list_repositories()

    # Upload document (2-step: blob + object)
    doc = client.upload_document(
        repo_id="...",
        filename="Audit_2026-03-26.pdf",
        content=pdf_bytes,
        category="DSGVO_AUDIT",
        properties={"Mandant": "Landratsamt", "Datum": "2026-03-26"},
    )
    print(doc.id, doc.location_uri)

    # Search
    results = client.search(repo_id="...", query="Datenpanne 2026")

    # List categories
    categories = client.list_categories(repo_id="...")
```

### Async

```python
async with DvelopClient(base_url="https://iil.d-velop.cloud", api_key="...") as client:
    repos = await client.list_repositories_async()
    doc = await client.upload_document_async(repo_id="...", ...)
```

## API Reference

### DvelopClient

| Method | Description |
|--------|-------------|
| `list_repositories()` | List all DMS repositories |
| `list_categories(repo_id)` | List categories for a repository |
| `upload_blob(repo_id, content, filename)` | Step 1: Upload binary blob |
| `create_document(repo_id, blob_ref, category, properties)` | Step 2: Create DMS object |
| `upload_document(repo_id, filename, content, category, properties)` | Convenience: Steps 1+2 |
| `search(repo_id, query)` | Full-text search |
| `get_document(repo_id, doc_id)` | Get document by ID |

All methods have `_async` variants for async usage.

### Exceptions

| Exception | HTTP Status | Retry? |
|-----------|-------------|--------|
| `DvelopAuthError` | 401 | No — key invalid/expired |
| `DvelopForbiddenError` | 403 | No — missing Origin or permissions |
| `DvelopNotFoundError` | 404 | No |
| `DvelopRateLimitError` | 429 | Yes — check `retry_after` attribute |
| `DvelopError` | other | Depends |

### d.velop Upload Sequence

```
1. POST /dms/r/{repo_id}/b        → 201 + Location: /dms/r/{id}/b/{blob_id}
2. POST /dms/r/{repo_id}/o        → 201 + Location: /dms/r/{id}/o/{doc_id}
```

### Required Headers (handled automatically)

- `Authorization: Bearer {api_key}` — all requests
- `Accept: application/hal+json` — all requests
- `Origin: {base_url}` — write requests (CSRF)

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Related

- **ADR-149**: DMS-Hub Architecture Decision
- **dms-hub**: Django Service-Hub consuming this package
- **Platform**: `platform/packages/dvelop-client/`
