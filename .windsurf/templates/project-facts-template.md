---
trigger: always_on
---

# Project Facts: <REPO_NAME>

> Diese Datei ist die **einzige Source of Truth** für alle repo-spezifischen Werte.
> Workflows lesen GH_PREFIX, ORC_PREFIX, ADR_PATH etc. aus dieser Datei.
> Kein Hardcoding in Workflows erlaubt.

## Identität

- **REPO_OWNER**: `<github-owner>`         (z.B. `achimdehnert` oder `meiki-lra`)
- **REPO_NAME**: `<repo-name>`              (z.B. `travel-beat`)
- **GitHub**: `https://github.com/<REPO_OWNER>/<REPO_NAME>`
- **Branch**: `main`
- **Type**: `<django-app | python-package | docs | infra>`

## MCP-Konfiguration (Umgebung: Dev Desktop / WSL)

> ⚠️ Diese Tabelle MUSS korrekt ausgefüllt sein — alle Workflows lesen Prefixe von hier.
> Prefix-Reihenfolge aus `~/.codeium/windsurf/mcp_config.json` bestimmen.

| Variable | Wert | Server |
|----------|------|--------|
| **GH_PREFIX** | `mcp?_` | github MCP |
| **ORC_PREFIX** | `mcp?_` | orchestrator MCP |
| **DEPLOY_PREFIX** | `mcp?_` | deployment-mcp (falls verfügbar) |

**Beispiel WSL:** `GH_PREFIX=mcp1_`, `ORC_PREFIX=mcp2_`
**Beispiel Dev Desktop:** `GH_PREFIX=mcp0_`, `ORC_PREFIX=mcp1_`

```bash
# Aktuellen Prefix ermitteln:
cat ~/.codeium/windsurf/mcp_config.json | python3 -c "
import json, sys
cfg = json.load(sys.stdin)
for i, s in enumerate(cfg.get('mcpServers', {}).keys()): print(f'mcp{i}_ = {s}')
"
```

## pgvector (Memory-Backend)

- **Tunnel-Check**: `ss -tlnp | grep 15435`
- **Fix bei Fehler**: `sudo systemctl start ssh-tunnel-postgres`
- **KEIN Fallback erlaubt** — pgvector MUSS laufen

## ADR-Konfiguration

- **ADR_PATH**: `<pfad-zum-adr-verzeichnis>`  (z.B. `docs/adr` oder `docs/03-technisches-handbuch/architektur`)
- **ADR-Script**: `scripts/adr_next_number.py` vorhanden? `<ja/nein>`
- **Fallback**: GitHub API via `{GH_PREFIX}_get_file_contents` (immer möglich)

## Environments

| Env | Compose File | Host Port | Health URL | Public URL |
|-----|-------------|-----------|------------|------------|
| local | `docker-compose.local.yml` | `<LOCAL_PORT>` | `http://localhost:<LOCAL_PORT>/livez/` | http://localhost:<LOCAL_PORT> |
| staging | `docker-compose.staging.yml` | `<STAGING_PORT>` | `http://localhost:<STAGING_PORT>/livez/` | https://<STAGING_DOMAIN> |
| prod | `docker-compose.prod.yml` | `<PROD_PORT>` | `http://localhost:<PROD_PORT>/livez/` | https://<PROD_DOMAIN> |

## Docker Containers

| Container | Name | Purpose |
|-----------|------|---------|
| web | `<PREFIX>_web` | gunicorn:8000 |
| db | `<PREFIX>_db` | postgres:16 |
| redis | `<PREFIX>_redis` | redis:7 |

## Django Settings

- Local: `config.settings.local`
- Prod: `config.settings.production`
- **ROOT_URLCONF**: `config.urls`
- **WSGI**: `config.wsgi.application`

## Besonderheiten

- HTMX-Detection: `<request.htmx | request.headers.get("HX-Request")>`
- Multi-Tenancy: `<ja/nein>`
- Secrets: `.env` (nicht in Git) — Template: `.env.example`

## Nicht anwendbar (bei Docs/Infra-Repos)

- `django-models-views.md`, `htmx-templates.md`, `testing.md`, `docker-deployment.md` → inaktiv
