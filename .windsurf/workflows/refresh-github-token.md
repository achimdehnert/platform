---
description: GitHub Personal Access Token (PAT) erneuern — lokale Dateien UND Server-Kopien, mit Verifikation
---

# Refresh GitHub Token

Wenn der GitHub MCP Server `Bad credentials` meldet oder `gh auth status` den `GITHUB_TOKEN`
als invalid anzeigt, muss der PAT erneuert werden.

## Voraussetzungen

- Browser-Zugang zu https://github.com/settings/tokens
- SSH-Zugang zu prod (88.198.191.108) und staging-platform (178.104.184.168)

## Symptome

- GitHub MCP Tools (`mcp8_*`) geben `Authentication Failed: Bad credentials`
- `gh auth status` zeigt `X Failed to log in to github.com using token (GITHUB_TOKEN)`
- `GITHUB_TOKEN= gh auth status` funktioniert aber (gh CLI hat eigenen Token)

## Token-Stellen (Inventar, verifiziert 2026-07-22)

**Lokal — dieselbe Datei dreimal:** `~/.github_token`, `~/.secrets/github_PAT` und
`~/.secrets/github_token` waren am 2026-07-22 **byte-identisch** (gleicher SHA256). Es ist
EIN Token in drei Dateien; wer nur eine erneuert, hinterlässt zwei stille Altbestände.

| # | Ort | Konsument | Status |
|---|-----|-----------|--------|
| 1 | `~/.secrets/github_PAT` | GitHub-MCP-Server (`mcp-hub/scripts/start-github-mcp.sh`, primär) | **lebend** |
| 2 | `~/.secrets/github_token` | dasselbe Skript als Fallback + `platform/bootstrap.sh` | **lebend** |
| 3 | **prod** `/root/.secrets/github_token` | `/opt/dev-hub/ghcr-login.sh` (GHCR-Login), `/opt/platform/bootstrap.sh` | **lebend** |
| 4 | **staging-platform** `/root/.secrets/github_token` | vorhanden; Zweck nicht abschließend geprüft | **lebend** |
| 5 | `~/.github_token` | **kein lebender Leser gefunden** — `.bashrc` referenziert die Datei nicht | Karteileiche |
| 6 | `~/.codeium/windsurf/mcp_config.json` | Windsurf-MCP | enthielt 2026-07-22 **keinen** `GITHUB_PERSONAL_ACCESS_TOKEN` |

**Nicht betroffen — bewusst nicht mitrotieren:**
- `~/.config/gh/hosts.yml` — die `gh`-CLI hat einen eigenen OAuth-Token (`gho_…`) aus
  `gh auth login`, unabhängig vom PAT.
- **prod-b** (`89.167.43.30`) — dessen GHCR-Login läuft über `~/.secrets/github_write_packages`,
  ein separater Token mit eigenem Ablaufdatum.
- Pulls **innerhalb** von GitHub Actions — die nutzen den `GITHUB_TOKEN` des Workflows.

**Ungeklärt (Werte sind von aussen nicht lesbar):** die Repo-Secrets `PLATFORM_DEPLOY_TOKEN`,
`PLATFORM_GITHUB_TOKEN` und `PROJECT_PAT` in `achimdehnert/platform`. Ob eines davon denselben
PAT enthält, lässt sich nicht prüfen — im Zweifel bei der Rotation mit erneuern.

> **Warum dieses Inventar so ausführlich ist:** Die frühere Fassung nannte vier Stellen, von
> denen drei nicht mehr stimmten (`.bashrc`-Ladepfad, Windsurf-Config, gh-CLI), und die beiden
> Server-Kopien fehlten ganz. Wer danach vorging, aktualisierte Phantome und übersah prod.

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

Wenn Login = `achimdehnert` → der alte Token lebt noch. **Schritt 3 (Server-Kopien) trotzdem
prüfen** — die laufen auseinander, wenn sie einmal vergessen wurden.

---

## Schritt 1 — Neuen PAT erstellen

1. Öffne https://github.com/settings/tokens?type=beta (Fine-grained) oder
   https://github.com/settings/tokens (Classic)
2. **Classic PAT empfohlen** — Scopes: `repo`, `read:org`, `admin:public_key`, `gist`, `project`
3. Expiration: **90 Tage** (Kalendereintrag setzen!)
4. Token kopieren (beginnt mit `ghp_`)

## Schritt 2 — Lokale Dateien aktualisieren

```bash
umask 077
read -rsp "Neuer PAT: " NEW_TOKEN; echo

printf '%s' "$NEW_TOKEN" > ~/.secrets/github_PAT
printf '%s' "$NEW_TOKEN" > ~/.secrets/github_token
printf '%s' "$NEW_TOKEN" > ~/.github_token      # Karteileiche, aber konsistent halten
chmod 600 ~/.secrets/github_PAT ~/.secrets/github_token ~/.github_token
```

`read -rsp` statt `NEW_TOKEN="ghp_…"` im Klartext: so landet der Token nicht in der
Shell-History und nicht im Terminal-Scrollback.

## Schritt 3 — Server-Kopien aktualisieren (WIRD LEICHT VERGESSEN)

Ohne diesen Schritt scheitert der GHCR-Login auf prod, sobald der alte Token abläuft —
und das fällt erst beim nächsten Image-Pull auf.

```bash
for H in root@88.198.191.108 root@178.104.184.168; do
  printf '%s' "$NEW_TOKEN" | ssh "$H" 'umask 077; cat > /root/.secrets/github_token'
done

# GHCR-Login auf prod scharf ziehen
ssh root@88.198.191.108 'bash /opt/dev-hub/ghcr-login.sh'
```

## Schritt 4 — Verifizieren

```bash
# 1. Token gültig + Scopes + Ablaufdatum (ohne den Wert auszugeben)
curl -s -D - -o /dev/null -H "Authorization: Bearer $(tr -d '\n' < ~/.secrets/github_PAT)" \
  https://api.github.com/user | grep -iE "^HTTP|^x-oauth-scopes|^github-authentication-token-expiration"

# 2. Alle drei lokalen Dateien identisch?
sha256sum ~/.github_token ~/.secrets/github_PAT ~/.secrets/github_token | awk '{print $1}' | sort -u | wc -l
#   Erwartung: 1

# 3. gh CLI (nutzt eigenen OAuth-Token, muss weiter gruen sein)
GITHUB_TOKEN= gh auth status

# 4. GHCR auf prod
ssh root@88.198.191.108 'docker pull -q ghcr.io/achimdehnert/illustration-hub:main-f2a4345 >/dev/null && echo "GHCR-Pull ok"'
```

Erwartet: `HTTP/2 200`, Scopes enthalten `repo` und `write:packages`, ein einziger Hash,
`gh auth status` gruen, `GHCR-Pull ok`.

## Schritt 5 — MCP-Server neustarten

1. **Windsurf komplett neustarten** (Cmd+Shift+P → "Reload Window" reicht NICHT für MCP)
2. Nach Neustart testen: beliebiges `mcp8_*` Tool aufrufen, z.B. `mcp__github__list_issues`

## Schritt 6 — Deployment-MCP neustarten (optional)

Falls deployment-mcp CI/CD Tools auch betroffen:

```bash
# deployment-mcp Prozess finden und neustarten
pkill -f "start-deployment-mcp"
~/.local/bin/start-deployment-mcp.sh &
```

## Checkliste

- [ ] Neuer PAT erstellt, Scopes `repo` + `write:packages` (+ `read:org`, `gist`, `project`)
- [ ] `~/.secrets/github_PAT` aktualisiert
- [ ] `~/.secrets/github_token` aktualisiert
- [ ] `~/.github_token` aktualisiert (oder bewusst gelöscht — siehe Inventar #5)
- [ ] **prod** `/root/.secrets/github_token` aktualisiert
- [ ] **staging-platform** `/root/.secrets/github_token` aktualisiert
- [ ] `ghcr-login.sh` auf prod gelaufen
- [ ] Verifikation: HTTP 200 + Scopes + genau **ein** SHA256 über die drei lokalen Dateien
- [ ] Verifikation: GHCR-Pull auf prod erfolgreich
- [ ] `GITHUB_TOKEN= gh auth status` weiterhin grün (eigener OAuth-Token, darf sich nicht ändern)
- [ ] Repo-Secrets geprüft: `PLATFORM_DEPLOY_TOKEN`, `PLATFORM_GITHUB_TOKEN`, `PROJECT_PAT`
- [ ] MCP-Server neugestartet, ein `mcp__github__*`-Tool getestet
- [ ] Kalendereintrag für das nächste Ablaufdatum gesetzt

## Was NICHT mitrotiert wird

- `~/.config/gh/hosts.yml` — eigener `gho_`-OAuth-Token der `gh`-CLI.
- **prod-b** — nutzt `~/.secrets/github_write_packages` mit eigenem Ablaufdatum.
- Actions-interne Pulls — laufen über den `GITHUB_TOKEN` des Workflows.

## Tote Token erkennen, bevor sie Zeit kosten

Zwei Dateien im Bestand waren am 2026-07-22 unbrauchbar (`GHCR_pull`,
`github_read_packages_PAT` — beide HTTP 401) und haben in einer Session zwei Anläufe
gekostet, bevor der Grund klar war. Der Schnelltest über alle Token-Dateien:

```bash
for f in ~/.secrets/*PAT* ~/.secrets/github_* ~/.secrets/GHCR*; do
  [ -f "$f" ] || continue
  H=$(curl -s -D - -o /dev/null -H "Authorization: Bearer $(tr -d '\n' < "$f")" https://api.github.com/user)
  printf "%-40s %s\n" "$(basename "$f")" "$(echo "$H" | head -1)"
done
```

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
