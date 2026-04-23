# Travel MCP

Travel Beat Integration Server.

## Installation

```bash
cd mcp-hub/travel_mcp
pip install -e .
```

## Konfiguration

```json
{
  "mcpServers": {
    "travel-mcp": {
      "command": "python",
      "args": ["-m", "travel_mcp.server"],
      "env": {
        "TRAVEL_BEAT_API_URL": "http://localhost:8001"
      }
    }
  }
}
```

## Tools

### get_destination

Reiseziel-Informationen abrufen.

```python
result = await get_destination(
    destination="Tokyo",
    include_pois=True,
)
```

### generate_itinerary

Reiseplan generieren.

```python
result = await generate_itinerary(
    destination="Paris",
    days=3,
    interests=["art", "food", "history"],
)
```

### search_destinations

Reiseziele suchen.

```python
result = await search_destinations(
    query="beach vacation",
    region="europe",
    budget="medium",
)
```
