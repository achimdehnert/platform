# Project Facts: iil-django-commons

> ⚠️ AUTO-GENERATED — Nur in `platform/.windsurf/project-facts/iil-django-commons.md` editieren!
> Neu generieren: `python3 platform/scripts/generate_project_facts.py iil-django-commons`

---

## Projekt

- **Beschreibung**: Shared backend services library for Django projects — Logging, Health, Cache, Rate Limiting, Security, Email, Tasks, Monitoring (ADR-131)
- **GitHub**: `achimdehnert/iil-django-commons` → https://github.com/achimdehnert/iil-django-commons
- **Typ**: Python (kein Django)
- **Port**: – · **Container**: `–`

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
| Lokaler Pfad | `/home/devuser/github/iil-django-commons` |
| Python | `/home/devuser/github/iil-django-commons/.venv/bin/python` |
