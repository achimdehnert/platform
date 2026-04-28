# Project Facts: bfagent

> ⚠️ AUTO-GENERATED — Nur in `platform/.windsurf/project-facts/bfagent.md` editieren!
> Neu generieren: `python3 platform/scripts/generate_project_facts.py bfagent`

---

## Projekt

- **Beschreibung**: Book Factory Agent — AI-assisted book creation
- **GitHub**: `achimdehnert/bfagent` → https://github.com/achimdehnert/bfagent
- **Typ**: Django · Lifecycle: production
- **URL**: https://bfagent.iil.pet
- **Staging**: `staging.iil.pet`
- **Services**: Celery · Redis · Docker

---

## Deploy

| Variable | Wert |
|----------|------|
| **Server** | `88.198.191.108` |
| **Pfad** | `/opt/bfagent` |
| **Port** | `8091` |
| **Container** | `bfagent_web` |
| **Migrate** | `python manage.py migrate --noinput` |
| **Compose** | `docker-compose.prod.yml` |
| **Image** | `ghcr.io/achimdehnert/bfagent-web:${IMAGE_TAG:-latest}` |

---

## Django Settings

| Variable | Wert |
|----------|------|
| `DJANGO_SETTINGS_MODULE` | `config.settings` |
| `ROOT_URLCONF` | `config.urls` |
| `WSGI` | `config.wsgi.application` |
| `DEFAULT_AUTO_FIELD` | `BigAutoField` |
| **DB-Name** | `bfagent` |

## HTMX Detection

```python
request.htmx  # django-htmx installed
```

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
| Lokaler Pfad | `/home/devuser/github/bfagent` |
| Venv | `/home/devuser/github/bfagent/.venv/bin/python` |
| DB (lokal) | `localhost:5432/bfagent` |
| Health | `/livez/` (liveness) · `/healthz/` (readiness) |
