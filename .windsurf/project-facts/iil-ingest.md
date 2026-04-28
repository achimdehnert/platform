# Project Facts: iil-ingest

> ⚠️ AUTO-GENERATED — Nur in `platform/.windsurf/project-facts/iil-ingest.md` editieren!
> Neu generieren: `python3 platform/scripts/generate_project_facts.py iil-ingest`

---

## Projekt

- **Beschreibung**: –
- **GitHub**: `achimdehnert/iil-ingest` → https://github.com/achimdehnert/iil-ingest
- **Typ**: Library / Infra (kein Deployment)

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
| Lokaler Pfad | `/home/devuser/github/iil-ingest` |
| Python | `/home/devuser/github/iil-ingest/.venv/bin/python` |
