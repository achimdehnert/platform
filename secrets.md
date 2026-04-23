---
description: Secrets verwalten — rotieren, prüfen, neu anlegen für alle Repos
---

# /secrets — Secrets Management Workflow

> Quelle: `platform/infra/secrets-management.md` + `platform/infra/secrets-inventory.yaml`
> Lokale Secrets: `~/.secrets/` — NIEMALS in Git committen.

---

## Übersicht: Wo liegen Secrets?

| Ort | Verwendung | Zugriff |
|-----|-----------|---------|
| `~/.secrets/<name>` | Lokale Dev-Secrets (GitHub Token, Outline API) | `cat ~/.secrets/<name>` |
| `/opt/<repo>/.env.prod` | Production Secrets (Server) | SSH root@88.198.191.108 |
| GitHub Repo Secrets | CI/CD (DEPLOY_SSH_KEY, GHCR_TOKEN) | GitHub → Settings → Secrets |
| `~/.codeium/windsurf/mcp_config.json` | MCP-Server env vars | Lokal |

---

## Secret prüfen (lokal)

// turbo
```bash
# Vorhandene Secrets auflisten
ls ~/.secrets/

# Secret-Wert prüfen (Vorsicht: nicht ins Terminal-Log)
cat ~/.secrets/github_token | head -c 20 && echo "...[OK]"
cat ~/.secrets/outline_api_token | head -c 20 && echo "...[OK]"
```

---

## Secret rotieren

### GitHub Token (github_token)

1. → https://github.com/settings/tokens
2. Token regenerieren oder neuen erstellen
3. Lokal speichern:
```bash
echo "ghp_NEUER_TOKEN" > ~/.secrets/github_token
chmod 600 ~/.secrets/github_token
```
4. MCP-Config aktualisieren → `/refresh-github-token`

### Outline API Token (outline_api_token)

1. → https://outline.iil.pet/settings/tokens
2. Neuen Token erstellen
3. Lokal speichern:
```bash
echo "ol_NEUER_TOKEN" > ~/.secrets/outline_api_token
chmod 600 ~/.secrets/outline_api_token
```
4. MCP-Wrapper neu starten (Windsurf neustarten)

### Production .env.prod rotieren

```bash
# Secret auf dem Server aktualisieren
ssh root@88.198.191.108 "nano /opt/<REPO>/.env.prod"
# Dann Container neustarten:
ssh root@88.198.191.108 "docker restart <REPO>_web"
```

---

## Neues Secret anlegen

```bash
# Lokal
echo "<WERT>" > ~/.secrets/<name>
chmod 600 ~/.secrets/<name>

# In mcp-wrapper.sh referenzieren (falls für MCP-Server):
# export VARNAME="$(load_secret <name>)"
```

---

## Secret-Inventar prüfen

```bash
# Vollständiges Inventar
cat "${GITHUB_DIR:-$HOME/github}/platform/infra/secrets-inventory.yaml"

# Welche Secrets fehlen lokal?
python3 "${GITHUB_DIR:-$HOME/github}/platform/infra/scripts/check_secrets.py" 2>/dev/null \
  || echo "ℹ️  check_secrets.py nicht vorhanden — manuell prüfen"
```

---

## Sicherheitsregeln (ADR-045)

- `chmod 600` auf alle Secret-Dateien
- NIEMALS Secrets in Git committen (`.gitignore` prüfen)
- NIEMALS Secrets als Env-Var in `docker-compose.yml` (→ `env_file: .env.prod`)
- Rotation: GitHub Token alle 90 Tage, API-Tokens alle 180 Tage
- Bei Verdacht auf Leak: sofort rotieren + GitHub → Settings → Sessions prüfen
