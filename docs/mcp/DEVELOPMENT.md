# MCP-Server Development

> Wie ein neuer MCP-Server angelegt und aktiviert wird (ADR-176).

## Voraussetzungen

- `mcp-hub` lokal geklont in `${GITHUB_DIR}/mcp-hub/`
- `.venv/` existiert und ist aktuell (`pip install -r requirements.txt`)
- `platform` lokal geklont

## Neuer MCP-Server — Schritt für Schritt

### 1. Modulstruktur anlegen

```bash
cd ${GITHUB_DIR:-$HOME/github}/mcp-hub
mkdir -p my_new_mcp
touch my_new_mcp/__init__.py
```

### 2. `__main__.py` als Entry-Point

```python
"""my_new_mcp — <Zweck in 1 Satz>."""
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


server = Server("my-new-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="my_tool",
            description="...",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "my_tool":
        return [TextContent(type="text", text="Hello from my_new_mcp")]
    raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 3. README.md

```markdown
# my_new_mcp — <Kurztitel>

> **Status:** 🚧 In Entwicklung — aktive Weiterentwicklung

<2-3 Sätze Zweck>

## Tools
| Tool | Zweck |
|---|---|
| `my_tool` | ... |

## Start
```bash
cd mcp-hub && source .venv/bin/activate && python -m my_new_mcp
```

## Environment
| Variable | Pflicht | Beschreibung |
|---|---|---|
| `MY_NEW_MCP_...` | ja/nein | ... |
```

### 4. Start-Script

```bash
# mcp-hub/scripts/start-my-new-mcp.sh
#!/bin/bash
set -euo pipefail
export MY_NEW_MCP_TOKEN="$(cat ~/.secrets/my_new_mcp_token 2>/dev/null || echo "")"
cd "${GITHUB_DIR:-$HOME/github}/mcp-hub"
source .venv/bin/activate
exec python -m my_new_mcp
```

`chmod +x` nicht vergessen.

### 5. Template-Eintrag

In `platform/templates/mcp_config.wsl.json` (und/oder `.dev-desktop.json`):

```json
"my-new": {
  "command": "bash",
  "args": ["-c", "$GITHUB_DIR/mcp-hub/scripts/start-my-new-mcp.sh"],
  "disabled": true
}
```

`disabled: true` beim ersten Registrieren — nach Verifikation auf `false`.

### 6. Inventar-Eintrag

In `platform/docs/mcp/SERVERS.md` unter "In Entwicklung" eintragen.

### 7. Cascade-Rule (optional)

Wenn neue Tools exportiert werden, in `platform/.windsurf/rules/mcp-tools.md` die Tool-Tabelle erweitern.

### 8. Commit + Sync

```bash
# in mcp-hub
git add my_new_mcp/ scripts/start-my-new-mcp.sh
git commit -m "feat(mcp): neuer MCP-Server my_new_mcp"
git push

# in platform
git add docs/mcp/SERVERS.md templates/mcp_config.*.json
git commit -m "feat(mcp): my_new_mcp zum Inventar + Template"
git push

# lokal Config aktualisieren
bash $GITHUB_DIR/platform/scripts/sync-mcp-config.sh

# Windsurf neu laden → Prefix prüfen
```

## Tests

Tests liegen in `mcp-hub/<name>_mcp/tests/` (konventionell) oder `mcp-hub/tests/<name>_mcp/`.

```bash
cd mcp-hub
source .venv/bin/activate
pytest <name>_mcp/tests/ -v
```

Naming: `test_should_<expected_behavior>` (ADR-058).

## Promotion von 🚧 → ✅

Wenn ein Server von "In Entwicklung" zu "Production" wechseln soll:

- [ ] Mindestens 5 Tools funktional
- [ ] Tests mit ≥80% Coverage
- [ ] README vollständig (alle Env-Vars, alle Tools dokumentiert)
- [ ] `disabled: true` → `disabled: false` im Template (oder entfernen)
- [ ] Status-Banner im README: `> **Status:** ✅ Production`
- [ ] Eintrag in `SERVERS.md` von "In Entwicklung" zu "Produktive Server" verschieben
- [ ] Git-Commits mit `[FEAT]`/`[FIX]` statt `[WIP]`

## Archivierung

Wenn ein Server nicht mehr gebraucht wird:

- [ ] README-Banner: `> **Status:** ❌ Archiviert (Begründung)`
- [ ] Aus `mcp_config.json` Templates entfernen
- [ ] In `SERVERS.md` unter "Archiviert" eintragen
- [ ] Code in `mcp-hub/_archive/<name>_mcp/` verschieben (nicht löschen — History preserven)
