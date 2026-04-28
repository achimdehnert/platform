---
description: GitHub Personal Access Token (PAT) erneuern — alle 3 Stellen aktualisieren + MCP-Server neustarten
---

# Refresh GitHub Token

Wenn der GitHub MCP Server `Bad credentials` meldet oder `gh auth status` den `GITHUB_TOKEN`
als invalid anzeigt, muss der PAT erneuert werden.

## Voraussetzungen

- Browser-Zugang zu https://github.com/settings/tokens
- Windsurf IDE läuft

## Symptome

- GitHub MCP Tools (`mcp8_*`) geben `Authentication Failed: Bad credentials`
- `gh auth status` zeigt `X Failed to log in to github.com using token (GITHUB_TOKEN)`
- `GITHUB_TOKEN= gh auth status` funktioniert aber (gh CLI hat eigenen Token)

## Token-Stellen (3 Dateien + 1 CLI)

| # | Datei | Geladen von | Konsument |
|---|-------|-------------|-----------|
| 1 | `~/.github_token` | `.bashrc` → `$GITHUB_TOKEN` | Shell, `gh` CLI (überschreibt gh login) |
| 2 | `~/.secrets/github_token` | `start-deployment-mcp.sh` | deployment-mcp (CI/CD Actions) |
| 3 | `~/.codeium/windsurf/mcp_config.json` | Windsurf direkt | GitHub MCP Server (`@modelcontextprotocol/server-github`) |
| 4 | `~/.config/gh/hosts.yml` | `gh auth login` | gh CLI (nur wenn `$GITHUB_TOKEN` nicht gesetzt) |

## Schritt 0 — Token aus laufendem MCP-Prozess holen (schnellster Weg)

Wenn Windsurf noch läuft, hat der `server-github` Prozess den Token im Environment:

```bash
TOKEN=$(tr '\0' '\n' < /proc/$(pgrep -f "server-github" | head -1)/environ 2>/dev/null \
        | grep "^GITHUB_PERSONAL_ACCESS_TOKEN=" | cut -d= -f2-)

# Verify
curl -s -H "Authorization: token $TOKEN" https://api.github.com/user \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('login'))"

# Sync in alle Stellen
echo -n "$TOKEN" > ~/.secrets/github_PAT   && chmod 600 ~/.secrets/github_PAT
echo -n "$TOKEN" > ~/.secrets/github_token && chmod 600 ~/.secrets/github_token
```

Wenn Login = `achimdehnert` → fertig. Schritt 1-4 nicht nötig.

---

## Schritt 1 — Neuen PAT erstellen

1. Öffne https://github.com/settings/tokens?type=beta (Fine-grained) oder
   https://github.com/settings/tokens (Classic)
2. **Classic PAT empfohlen** — Scopes: `repo`, `read:org`, `admin:public_key`, `gist`, `project`
3. Expiration: **90 Tage** (Kalendereintrag setzen!)
4. Token kopieren (beginnt mit `ghp_`)

## Schritt 2 — Alle 3 Dateien aktualisieren

Ersetze `NEW_TOKEN_HERE` mit dem neuen Token:

```bash
# Variablen
NEW_TOKEN="ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

# 1. Shell-Token
echo -n "$NEW_TOKEN" > ~/.github_token
chmod 600 ~/.github_token

# 2. Secrets-Token (deployment-mcp)
echo -n "$NEW_TOKEN" > ~/.secrets/github_token
chmod 600 ~/.secrets/github_token

# 3. Windsurf MCP Config (JSON — Token-Wert ersetzen)
python3 -c "
import json
p = '$HOME/.codeium/windsurf/mcp_config.json'
with open(p) as f:
    d = json.load(f)
d['mcpServers']['github']['env']['GITHUB_PERSONAL_ACCESS_TOKEN'] = '$NEW_TOKEN'
with open(p, 'w') as f:
    json.dump(d, f, indent=2)
print('mcp_config.json updated')
"

# 4. Aktuelle Shell-Session aktualisieren
export GITHUB_TOKEN="$NEW_TOKEN"
```

## Schritt 3 — Verifizieren

```bash
# Shell-Token prüfen
echo "GITHUB_TOKEN starts with: $(echo $GITHUB_TOKEN | head -c 10)..."

# gh CLI prüfen (sollte GITHUB_TOKEN nutzen)
gh auth status

# API-Call testen
gh api user --jq '.login'
```

Erwartete Ausgabe: `achimdehnert`

## Schritt 4 — Windsurf MCP neustarten

1. **Windsurf komplett neustarten** (Cmd+Shift+P → "Reload Window" reicht NICHT für MCP)
2. Nach Neustart testen: beliebiges `mcp8_*` Tool aufrufen, z.B. `mcp8_list_issues`

## Schritt 5 — Deployment-MCP neustarten (optional)

Falls deployment-mcp CI/CD Tools auch betroffen:

```bash
# deployment-mcp Prozess finden und neustarten
pkill -f "start-deployment-mcp"
~/.local/bin/start-deployment-mcp.sh &
```

## Checkliste

- [ ] Neuer PAT erstellt (90 Tage Expiry)
- [ ] `~/.github_token` aktualisiert
- [ ] `~/.secrets/github_token` aktualisiert
- [ ] `mcp_config.json` aktualisiert
- [ ] `gh auth status` zeigt ✓
- [ ] `gh api user` gibt `achimdehnert` zurück
- [ ] Windsurf neugestartet
- [ ] `mcp8_*` Tool funktioniert
- [ ] Kalendereintrag für Token-Ablauf gesetzt

## Verbesserungsvorschlag

Die `mcp_config.json` sollte den Token nicht hardcoden, sondern aus der Datei lesen.
Leider unterstützt das `@modelcontextprotocol/server-github` Paket nur Env-Vars, keine
File-Referenzen. Workaround: Ein Wrapper-Script als `command` nutzen:

```json
{
  "github": {
    "command": "bash",
    "args": ["-c", "GITHUB_PERSONAL_ACCESS_TOKEN=$(cat ~/.secrets/github_token) npx -y @modelcontextprotocol/server-github"],
    "disabled": false
  }
}
```

Damit muss bei Token-Refresh nur noch **2 Dateien** (statt 3) aktualisiert werden.
