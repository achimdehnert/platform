# MCP Hub

**Status:** ✅ Production  
**Domain:** `mcp_hub`  
**URL:** `/mcp-hub/`

---

## Übersicht

Der MCP Hub verwaltet Model Context Protocol (MCP) Server und deren Tools.

## Features

- **Server-Verwaltung:** Start/Stop von MCP-Servern
- **Tool-Übersicht:** Alle verfügbaren MCP-Tools
- **Monitoring:** Server-Status und Logs
- **Konfiguration:** Server-Parameter

## Models

### MCPServer

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `name` | CharField | Server-Name |
| `command` | CharField | Start-Befehl |
| `args` | JSONField | Argumente |
| `env` | JSONField | Umgebungsvariablen |
| `is_active` | BooleanField | Aktiv |

### MCPTool

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `server` | ForeignKey | Zugehöriger Server |
| `name` | CharField | Tool-Name |
| `description` | TextField | Beschreibung |
| `input_schema` | JSONField | Input-Schema |

## Views & URLs

| URL | View | Beschreibung |
|-----|------|--------------|
| `/mcp-hub/` | `dashboard` | Dashboard |
| `/mcp-hub/servers/` | `server_list` | Server-Liste |
| `/mcp-hub/tools/` | `tool_list` | Tool-Übersicht |

## BFAgent MCP Tools

Der `bfagent` MCP-Server bietet folgende Tools:

- `bfagent_list_domains` - Domains auflisten
- `bfagent_get_domain` - Domain-Details
- `bfagent_search_handlers` - Handler suchen
- `bfagent_get_requirement` - Requirement abrufen
- `bfagent_update_requirement_status` - Status aktualisieren
- `bfagent_record_task_result` - Ergebnis aufzeichnen
