# Project Facts: billing-hub

> ⚠️ AUTO-GENERATED — Nur in `platform/.windsurf/project-facts/billing-hub.md` editieren!
> Neu generieren: `python3 platform/scripts/generate_project_facts.py billing-hub`

---

## Projekt

- **Beschreibung**: –
- **GitHub**: `achimdehnert/billing-hub` → https://github.com/achimdehnert/billing-hub
- **Typ**: Django · Lifecycle: experimental
- **URL**: –
- **Staging**: `staging-billing.iil.pet`

---

## Deploy

| Variable | Wert |
|----------|------|
| **Server** | `88.198.191.108` |
| **Pfad** | `/opt/billing-hub` |
| **Port** | `8092` |
| **Container** | `billing-hub-web` |
| **Migrate** | `python manage.py migrate --noinput` |
| **Compose** | `docker-compose.prod.yml` |
| **Image** | `ghcr.io/achimdehnert/billing-hub-web:${IMAGE_TAG:-latest}` |

---

## Settings

| Variable | Wert |
|----------|------|
| `DJANGO_SETTINGS_MODULE` | `config.settings` |
| `ROOT_URLCONF` | `config.urls` |
| `WSGI` | `config.wsgi.application` |
| `DEFAULT_AUTO_FIELD` | `BigAutoField` |

---

## Secrets — ZWEI Pfade (beide prüfen!)

| Pfad | Keys |
|------|------|
| `/home/devuser/shared/secrets/` | `openai_api_key`, `anthropic_api_key` |
| `~/.secrets/` | `github_token`, `cloudflare_*`, `hetzner_cloud_token`, `orchestrator_mcp_db_password` |

```python
SECRETS_DIRS = [Path("/home/devuser/shared/secrets"), Path.home() / ".secrets"]

def get_secret(name):
    if val := os.environ.get(name.upper()): return val
    for base in SECRETS_DIRS:
        if (p := base / name.lower()).exists(): return p.read_text().strip()
    return None
```

---

## MCP-Konfiguration (devuser)

| Prefix | Server | Wichtigste Tools |
|--------|--------|-----------------|
| `mcp0_` | **github** | `get_file_contents`, `push_files`, `create_issue`, `list_issues` |
| `mcp1_` | **orchestrator** | `agent_memory_context`, `agent_memory_upsert`, `discord_notify` |

---

## Lokale Umgebung

| Variable | Wert |
|----------|------|
| Lokaler Pfad | `/home/devuser/github/billing-hub` |
| Venv | `/home/devuser/github/billing-hub/.venv/bin/python` |
| DB (lokal) | `localhost:5432` |
| Health | `/livez/` (liveness) · `/healthz/` (readiness) |
