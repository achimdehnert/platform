# Project Facts: tax-hub

> ⚠️ AUTO-GENERATED — Nur in `platform/.windsurf/project-facts/tax-hub.md` editieren!
> Neu generieren: `python3 platform/scripts/generate_project_facts.py tax-hub`

---

## Projekt

- **Beschreibung**: –
- **GitHub**: `achimdehnert/tax-hub` → https://github.com/achimdehnert/tax-hub
- **Typ**: Django · Lifecycle: experimental
- **URL**: –
- **Staging**: `staging-tax.iil.pet`
- **Services**: Celery · Redis · Docker

---

## Deploy

| Variable | Wert |
|----------|------|
| **Server** | `88.198.191.108` |
| **Pfad** | `/opt/tax-hub` |
| **Port** | `8099` |
| **Container** | `tax_hub_web` |
| **Migrate** | `python manage.py migrate --noinput` |
| **Compose** | `docker-compose.prod.yml` |
| **Image** | `ghcr.io/achimdehnert/tax-hub-web:${IMAGE_TAG:-latest}` |

---

## Django Settings

| Variable | Wert |
|----------|------|
| `DJANGO_SETTINGS_MODULE` | `config.settings` |
| `ROOT_URLCONF` | `config.urls` |
| `WSGI` | `config.wsgi.application` |
| `DEFAULT_AUTO_FIELD` | `BigAutoField` |
| **DB-Name** | `tax_hub` |

## HTMX Detection

```python
request.headers.get("HX-Request") == "true"  # django-htmx NICHT installiert
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
| Lokaler Pfad | `/home/devuser/github/tax-hub` |
| Venv | `/home/devuser/github/tax-hub/.venv/bin/python` |
| DB (lokal) | `localhost:5432/tax_hub` |
| Health | `/livez/` (liveness) · `/healthz/` (readiness) |
