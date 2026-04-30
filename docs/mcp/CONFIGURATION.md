# MCP-Konfiguration

> Wie `~/.codeium/windsurf/mcp_config.json` aufgebaut ist und gepflegt wird (ADR-176).

## Grundprinzip

**Nie direkt editieren** — sondern aus Template + lokalen Secrets generieren:

```bash
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-mcp-config.sh
```

## Template-Dateien

| Template | Zielumgebung |
|---|---|
| `platform/templates/mcp_config.wsl.json` | WSL (Ubuntu in Windows) + Prod-Server |
| `platform/templates/mcp_config.dev-desktop.json` | Dev Desktop (Linux nativ) |

Templates enthalten **keine Secrets** — nur Platzhalter wie `${OUTLINE_API_TOKEN}`.

## Secrets-Quelle

Templates referenzieren Secrets über **Start-Scripts** (nicht via `env:` Block in Config):

```json
{
  "outline-knowledge": {
    "command": "bash",
    "args": [
      "-c",
      "$GITHUB_DIR/mcp-hub/scripts/start-outline-mcp.sh"
    ]
  }
}
```

Start-Script lädt Secret intern:

```bash
#!/bin/bash
set -euo pipefail
export OUTLINE_API_TOKEN="$(cat ~/.secrets/outline_api_token)"
cd "${GITHUB_DIR:-$HOME/github}/mcp-hub"
source .venv/bin/activate
python -m outline_mcp
```

## Prefix-Zuordnung

Prefix (`mcp0_`, `mcp1_`, ...) = **Reihenfolge** der Einträge in `mcp_config.json`.

→ **Reihenfolge im Template ändern = alle Cascade-Prompts, die Prefixes referenzieren, müssen angepasst werden.**

Deshalb: Prefix-Stabilität ist wichtiger als Alphabetik.

## Pro Environment kann Reihenfolge abweichen

| Environment | `mcp0_` | `mcp1_` | `mcp2_` | ... |
|---|---|---|---|---|
| WSL / Prod | deployment-mcp | github | orchestrator | ... |
| Dev Desktop | github | orchestrator | — | ... |

Dokumentiert in `docs/mcp/SERVERS.md`.

Cascade-Regeln (wie `project-facts.md` in jedem Repo) dokumentieren den Prefix immer per Environment.

## Sync-Script

`platform/scripts/sync-mcp-config.sh`:

1. Liest `platform/templates/mcp_config.<env>.json` (je nach detektierter Umgebung)
2. Validiert: alle referenzierten Start-Scripts in `mcp-hub/scripts/` existieren
3. Validiert: alle `~/.secrets/*`-Dateien die verwendet werden existieren (warnt bei Fehlen)
4. Schreibt `~/.codeium/windsurf/mcp_config.json`
5. Gibt Prefix-Mapping aus (zum Abgleich mit Rules)

## Disabling Servern

Ein Server in der Config, der nicht gestartet werden soll:

```json
"deployment-mcp": {
  "disabled": true,
  ...
}
```

→ Server bleibt im Template, wird lokal deaktiviert. Alternativ: aus Template entfernen.

## Neu hinzufügen

1. Server-Code: `mcp-hub/<name>_mcp/`
2. Start-Script: `mcp-hub/scripts/start-<name>-mcp.sh`
3. Template-Eintrag: `platform/templates/mcp_config.<env>.json`
4. Inventar: `platform/docs/mcp/SERVERS.md`
5. Cascade-Rule: `platform/.windsurf/rules/mcp-tools.md` (falls Tools neu sind)
6. `sync-mcp-config.sh` laufen lassen
7. Windsurf neu laden
