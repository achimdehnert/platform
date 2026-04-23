# Development

## Neuen MCP Server erstellen

### 1. Struktur anlegen

```bash
cd mcp-hub
mkdir my_new_mcp
cd my_new_mcp
```

### 2. pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-new-mcp"
version = "0.1.0"
description = "My new MCP server"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.25.0",
]

[project.scripts]
my-new-mcp = "my_new_mcp.server:main"
```

### 3. Server implementieren

```python
# server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("my-new-mcp")

@app.tool()
async def my_tool(param: str) -> str:
    """Description of my tool."""
    return f"Result: {param}"

@app.resource("data://info")
async def get_info() -> str:
    """Get server info."""
    return "My MCP Server v0.1.0"

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 4. Installieren & Testen

```bash
pip install -e .

# Testen
python -m my_new_mcp.server
```

## Windsurf/Cascade Konfiguration

```json
{
  "mcpServers": {
    "my-new-mcp": {
      "command": "python",
      "args": ["-m", "my_new_mcp.server"],
      "env": {
        "MY_API_KEY": "..."
      }
    }
  }
}
```

## Best Practices

### Tool Design

```python
@app.tool()
async def good_tool(
    query: str,
    limit: int = 10,
    include_metadata: bool = False,
) -> str:
    """
    Search for items matching the query.
    
    Args:
        query: Search query string
        limit: Maximum number of results (default: 10)
        include_metadata: Include additional metadata
    
    Returns:
        JSON string with search results
    """
    # Implementation
    pass
```

### Error Handling

```python
@app.tool()
async def safe_tool(param: str) -> str:
    """Tool with proper error handling."""
    try:
        result = await do_something(param)
        return json.dumps({"success": True, "data": result})
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return json.dumps({"success": False, "error": "Internal error"})
```

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mcp_server.log"),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)
```

## Testing

### Unit Tests

```python
# test_server.py
import pytest
from my_new_mcp.server import my_tool

@pytest.mark.asyncio
async def test_my_tool():
    result = await my_tool("test")
    assert "Result: test" in result
```

### Integration Tests

```python
# test_mcp_protocol.py
import asyncio
from mcp.client import Client

async def test_mcp_connection():
    client = Client()
    await client.connect("my-new-mcp")
    
    # List tools
    tools = await client.list_tools()
    assert "my_tool" in [t.name for t in tools]
    
    # Call tool
    result = await client.call_tool("my_tool", {"param": "test"})
    assert result is not None
```

### Manueller Test

```bash
# Server starten
python -m my_new_mcp.server

# In anderem Terminal
python test_mcp_protocol.py
```
