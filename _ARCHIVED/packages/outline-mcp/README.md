# outline-mcp

MCP Server for Outline Wiki — Knowledge Base access for Cascade.

## Overview

Provides 9 tools for the Windsurf/Cascade AI assistant to interact with Outline Wiki (knowledge.iil.pet):

| Tool | Description |
|------|-------------|
| `search_knowledge` | Fulltext search across all collections |
| `get_document` | Get full Markdown content of a document |
| `create_runbook` | Create a new Runbook (Troubleshooting, Step-by-Step) |
| `create_concept` | Create a new Architecture Concept |
| `create_lesson` | Create a new Lesson Learned |
| `update_document` | Update an existing document |
| `delete_document` | Delete a document (moves to trash) |
| `list_recent` | List recently updated documents |
| `list_collections` | List all collections with IDs |

## Architecture (ADR-145)

- **HTTP Client**: `httpx.AsyncClient` (no third-party Outline SDK)
- **Lifespan**: `@asynccontextmanager` manages client lifecycle (ADR-044)
- **Retry**: `tenacity` with exponential backoff (3 attempts)
- **Config**: `pydantic-settings` with `OUTLINE_MCP_` env prefix
- **Error Handling**: Sanitized JSON responses, no stack traces to client

## Setup

```bash
# Install
pip install -e ".[dev]"

# Environment
export OUTLINE_MCP_OUTLINE_API_TOKEN="ol_api_..."
export OUTLINE_MCP_OUTLINE_URL="https://knowledge.iil.pet"  # default

# Run
python -m outline_mcp
```

## Windsurf Registration

Add to `.windsurf/mcp.json`:
```json
{
  "outline-knowledge": {
    "command": "python",
    "args": ["-m", "outline_mcp"],
    "env": {
      "OUTLINE_MCP_OUTLINE_API_TOKEN": "ol_api_..."
    }
  }
}
```

## References

- ADR-145: Knowledge Management — Cascade ↔ Outline
- ADR-143: Knowledge-Hub — Outline Wiki
- ADR-044: MCP Server Lifecycle Hooks
