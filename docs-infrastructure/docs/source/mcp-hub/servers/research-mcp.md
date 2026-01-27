# Research MCP

Web Search & Research Tools Server.

## Installation

```bash
cd mcp-hub/research_mcp
pip install -e .
```

## Konfiguration

```json
{
  "mcpServers": {
    "research-mcp": {
      "command": "python",
      "args": ["-m", "research_mcp.server"],
      "env": {
        "SERPER_API_KEY": "...",
        "TAVILY_API_KEY": "..."
      }
    }
  }
}
```

## Tools

### search_web

Web-Suche durchführen.

```python
result = await search_web(
    query="Python best practices 2024",
    num_results=10,
)
```

### fetch_url

URL-Inhalt abrufen und parsen.

```python
result = await fetch_url(
    url="https://docs.python.org/3/",
    extract_text=True,
)
```

### summarize_url

URL-Inhalt zusammenfassen.

```python
result = await summarize_url(
    url="https://example.com/article",
    max_length=500,
)
```
