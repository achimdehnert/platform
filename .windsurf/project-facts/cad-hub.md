# Project Facts: cad-hub

> ⚠️ AUTO-GENERATED — Nur in `platform/.windsurf/project-facts/cad-hub.md` editieren!
> Neu generieren: `python3 platform/scripts/generate_project_facts.py cad-hub`

---

## Projekt

- **Beschreibung**: CAD Hub - Construction/CAD platform for IFC parsing, DXF/DWG analysis, DIN 277, fire safety (Brandschutz), tendering (AVB), and NL2CAD. Extracted from bfagent per ADR-029.
- **GitHub**: `achimdehnert/cad-hub` → https://github.com/achimdehnert/cad-hub
- **Typ**: Django · Lifecycle: experimental
- **URL**: –
- **Staging**: `staging.nl2cad.de`
- **Services**: Celery · Redis · Docker

---

## Deploy

| Variable | Wert |
|----------|------|
| **Server** | `88.198.191.108` |
| **Pfad** | `/opt/cad-hub` |
| **Port** | `8094` |
| **Container** | `cad_hub_web` |
| **Migrate** | `python manage.py migrate --noinput` |
| **Compose** | `docker-compose.prod.yml` |
| **Image** | `ghcr.io/achimdehnert/cad-hub-web:${IMAGE_TAG:-latest}` |

---

## Django Settings

| Variable | Wert |
|----------|------|
| `DJANGO_SETTINGS_MODULE` | `config.settings` |
| `ROOT_URLCONF` | `config.urls` |
| `WSGI` | `config.wsgi.application` |
| `DEFAULT_AUTO_FIELD` | `BigAutoField` |
| **DB-Name** | `cad_hub` |

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
| Lokaler Pfad | `/home/devuser/github/cad-hub` |
| Venv | `/home/devuser/github/cad-hub/.venv/bin/python` |
| DB (lokal) | `localhost:5432/cad_hub` |
| Health | `/livez/` (liveness) · `/healthz/` (readiness) |
