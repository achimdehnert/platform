# PostgreSQL MCP Setup für BF Agent

## 🎯 Warum PostgreSQL MCP?

Mit PostgreSQL MCP Server kann Cascade:
- ✅ Direkt auf PostgreSQL zugreifen
- ✅ Schema automatisch erstellen
- ✅ Daten von SQLite migrieren
- ✅ Settings anpassen
- ✅ Alles autonom testen

## 📦 Installation

### Schritt 1: PostgreSQL MCP Server installieren

```powershell
# Via npm (empfohlen)
npm install -g @modelcontextprotocol/server-postgres

# Oder via npx (keine Installation nötig)
npx @modelcontextprotocol/server-postgres
```

### Schritt 2: Docker PostgreSQL starten

```powershell
# Aus dem Projekt-Root
docker-compose up -d postgres
```

Warte bis PostgreSQL läuft:
```powershell
docker ps
# Sollte zeigen: bfagent_db ... Up
```

### Schritt 3: MCP Server Configuration

Die PostgreSQL MCP Config für Cascade (wird automatisch erkannt):

**Windows:** `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://bfagent:bfagent_dev_2024@localhost:5432/bfagent_dev"
      ]
    }
  }
}
```

Oder mit installiertem Server:
```json
{
  "mcpServers": {
    "postgres": {
      "command": "mcp-server-postgres",
      "args": [
        "postgresql://bfagent:bfagent_dev_2024@localhost:5432/bfagent_dev"
      ]
    }
  }
}
```

### Schritt 4: Cascade neu starten

1. VSCode schließen
2. VSCode neu öffnen
3. Cascade öffnen
4. Prüfen ob PostgreSQL MCP verfügbar ist

## 🧪 Testen

```powershell
# Cascade sollte nun diese Tools haben:
# - query: SQL Queries ausführen
# - list_tables: Tabellen auflisten
# - describe_table: Tabellen-Schema anzeigen
# - create_table: Tabellen erstellen
```

## ✅ Dann kann Cascade autonom:

1. **PostgreSQL Schema erstellen**
   - Django Migrations nach PostgreSQL übertragen
   - Alle Tabellen anlegen

2. **Daten migrieren**
   - SQLite auslesen
   - Nach PostgreSQL schreiben
   - Integrität prüfen

3. **Settings anpassen**
   - `config/settings/development.py` → PostgreSQL
   - `.env` Datei erstellen
   - URLs für Health Checks einrichten

4. **Testen & Verifizieren**
   - `python manage.py migrate` ausführen
   - `python manage.py runserver` starten
   - Funktionalität prüfen

## 🔗 Alternative: PostgreSQL MCP Servers

Falls der offizielle nicht funktioniert:

### Option 1: @modelcontextprotocol/server-postgres (Empfohlen)
```bash
npm install -g @modelcontextprotocol/server-postgres
```

### Option 2: mcp-server-postgresql
```bash
npm install -g mcp-server-postgresql
```

### Option 3: Direkter npx-Call (keine Installation)
```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://bfagent:bfagent_dev_2024@localhost:5432/bfagent_dev"
      ]
    }
  }
}
```

## 📝 Connection String Format

```
postgresql://[user]:[password]@[host]:[port]/[database]
```

Für BF Agent Development:
```
postgresql://bfagent:bfagent_dev_2024@localhost:5432/bfagent_dev
```

## 🔐 Sicherheit

⚠️ **Wichtig:** Die Connection String enthält das Passwort!

- Development: OK (lokaler Docker)
- Production: **Niemals** in MCP Config! (Nur lokal verbinden)

## 🚀 Nach der Installation

Sage Cascade:
> "PostgreSQL MCP ist jetzt installiert. Bitte führe die Migration von SQLite zu PostgreSQL autonom durch."

Cascade wird dann:
1. ✅ Docker PostgreSQL Status prüfen
2. ✅ Django Migrations nach PostgreSQL laufen lassen
3. ✅ SQLite Daten exportieren
4. ✅ Nach PostgreSQL importieren
5. ✅ Settings für PostgreSQL anpassen
6. ✅ Alles testen

## 🆘 Troubleshooting

### MCP Server wird nicht erkannt
```powershell
# Prüfe ob npx funktioniert
npx -y @modelcontextprotocol/server-postgres --help

# Falls nicht: Node.js installieren
winget install OpenJS.NodeJS
```

### PostgreSQL Connection Error
```powershell
# Prüfe ob Container läuft
docker ps | findstr bfagent_db

# Prüfe Logs
docker logs bfagent_db

# Prüfe Connection
docker exec -it bfagent_db psql -U bfagent -d bfagent_dev -c "SELECT version();"
```

### Port 5432 belegt
```powershell
# Andere PostgreSQL stoppen
net stop postgresql-x64-14

# Oder anderen Port in docker-compose.yml:
ports:
  - "5433:5432"
```

## ✅ Bereit?

Wenn PostgreSQL MCP läuft, sage einfach:
> "ok weiter"

Und ich führe die komplette Migration autonom durch! 🚀
