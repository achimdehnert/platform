# 🌊 Windsurf IDE - BF Agent MCP Setup

## Quick Setup (3 Minuten)

### 1. MCP Config Datei öffnen

**macOS/Linux:**
```bash
# Config-Datei öffnen (wird erstellt falls nicht vorhanden)
mkdir -p ~/.codeium/windsurf
nano ~/.codeium/windsurf/mcp_config.json
```

**Windows:**
```powershell
# Config-Datei öffnen
notepad %USERPROFILE%\.codeium\windsurf\mcp_config.json
```

**Oder in Windsurf:**
1. `Cmd+Shift+P` (Mac) / `Ctrl+Shift+P` (Windows)
2. "Open Windsurf Settings"
3. Scroll zu "Cascade" → "Manage MCPs"
4. "View raw config"

---

### 2. BF Agent Server hinzufügen

**Variante A: Python direkt (empfohlen für Development)**

```json
{
  "mcpServers": {
    "bfagent": {
      "command": "python",
      "args": [
        "-m", "bfagent_mcp.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "/path/to/your/bfagent_mcp",
        "DJANGO_SETTINGS_MODULE": "config.settings"
      }
    }
  }
}
```

**Variante B: UV Package Manager**

```json
{
  "mcpServers": {
    "bfagent": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/bfagent_mcp",
        "python", "-m", "bfagent_mcp.mcp_server"
      ]
    }
  }
}
```

**Variante C: Docker Container**

```json
{
  "mcpServers": {
    "bfagent": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/project:/app",
        "-e", "DJANGO_SETTINGS_MODULE=config.settings",
        "bfagent-mcp:latest"
      ]
    }
  }
}
```

---

### 3. Server aktivieren

1. In Windsurf: Cascade Panel öffnen (rechte Seite)
2. Klick auf **Hammer-Icon** (MCP Servers)
3. Klick auf **Refresh** Button
4. "bfagent" sollte jetzt erscheinen

---

## 📋 Vollständige Config (mit mehreren Servern)

```json
{
  "mcpServers": {
    
    "bfagent": {
      "command": "python",
      "args": ["-m", "bfagent_mcp.mcp_server"],
      "env": {
        "PYTHONPATH": "/Users/achim/projects/bf_agent",
        "DJANGO_SETTINGS_MODULE": "config.settings"
      }
    },
    
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"
      }
    },
    
    "filesystem": {
      "command": "npx",
      "args": [
        "-y", "@modelcontextprotocol/server-filesystem",
        "/Users/achim/projects"
      ]
    }
    
  }
}
```

---

## 🛠️ Verfügbare Tools nach Setup

| Tool | Beschreibung | Beispiel |
|------|--------------|----------|
| `bfagent` | Universal Interface | "Erstelle einen IFC Parser" |
| `bfagent_generate_handler` | Handler generieren | Strukturierte Generierung |
| `bfagent_validate_code` | Code validieren | Standards prüfen |
| `bfagent_list_standards` | Standards auflisten | Alle Standards zeigen |

---

## 💬 Nutzung in Windsurf Cascade

Nach dem Setup kannst du direkt in Cascade tippen:

```
@bfagent Zeig mir alle verfügbaren Domains
```

```
@bfagent Erstelle einen Handler der IFC Dateien parst und alle Räume extrahiert
```

```
@bfagent Validiere diesen Code:
class MyHandler:
    def process(self):
        pass
```

```
@bfagent Best Practices für Pydantic Schemas
```

---

## 🔧 Troubleshooting

### Server erscheint nicht?

1. **Refresh klicken** im MCP Panel
2. **Logs prüfen:**
   - `Cmd+Shift+P` → "Developer: Show Logs"
   - Suche nach "MCP" oder "bfagent"
3. **Python Pfad prüfen:**
   ```bash
   which python
   python -c "import bfagent_mcp; print('OK')"
   ```

### "Module not found"?

```bash
# PYTHONPATH setzen
export PYTHONPATH=/path/to/bfagent_mcp:$PYTHONPATH

# Oder in Config:
"env": {
  "PYTHONPATH": "/path/to/bfagent_mcp"
}
```

### Django Fehler?

```bash
# Django Settings prüfen
export DJANGO_SETTINGS_MODULE=config.settings
python -c "import django; django.setup(); print('OK')"
```

### MCP SDK fehlt?

```bash
pip install mcp
# oder
uv add mcp
```

---

## 📁 Projektstruktur für Development

```
~/projects/bf_agent/
├── packages/
│   └── bfagent_mcp/           # MCP Server Package
│       ├── __init__.py
│       ├── mcp_server.py      # ← Haupteinstieg
│       ├── django_orm.py
│       ├── metaprompter/
│       └── standards/
├── apps/                       # Django Apps
│   ├── core/
│   ├── cad_analysis/
│   └── ...
├── config/
│   └── settings.py
└── manage.py
```

**Config für diese Struktur:**

```json
{
  "mcpServers": {
    "bfagent": {
      "command": "python",
      "args": ["-m", "packages.bfagent_mcp.mcp_server"],
      "env": {
        "PYTHONPATH": "/Users/achim/projects/bf_agent",
        "DJANGO_SETTINGS_MODULE": "config.settings"
      }
    }
  }
}
```

---

## 🚀 Erweiterte Features

### Mit Django verbinden (echte Daten)

```json
{
  "mcpServers": {
    "bfagent": {
      "command": "/Users/achim/projects/bf_agent/.venv/bin/python",
      "args": ["-m", "bfagent_mcp.mcp_server"],
      "env": {
        "PYTHONPATH": "/Users/achim/projects/bf_agent",
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "DATABASE_URL": "postgres://user:pass@localhost:5432/bfagent"
      }
    }
  }
}
```

### HTTP Server (Remote Access)

Für HTTP-basierten Zugriff (nicht stdio):

```json
{
  "mcpServers": {
    "bfagent-remote": {
      "serverUrl": "http://localhost:8080/mcp"
    }
  }
}
```

---

## ✅ Checkliste

- [ ] MCP SDK installiert (`pip install mcp`)
- [ ] `mcp_config.json` erstellt
- [ ] Pfade in Config angepasst
- [ ] Windsurf neugestartet
- [ ] Refresh im MCP Panel geklickt
- [ ] "bfagent" in Tool-Liste sichtbar
- [ ] Test: "@bfagent Hilfe" funktioniert
