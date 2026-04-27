---
trigger: always_on
---

# Project Facts: platform

> ADRs, architecture docs, shared workflows, repo-registry

## Meta

- **Type**: `infra`
- **GitHub**: `https://github.com/achimdehnert/platform`
- **Branch**: `main` — push: `git push` (SSH-Key konfiguriert)

## Lokale Umgebung (Dev Desktop — adehnert)

- **Pfad**: `~/CascadeProjects/platform` → `$GITHUB_DIR` = `~/CascadeProjects`
- **Venv**: `~/CascadeProjects/platform/.venv/bin/python`
- **MCP-Config**: `~/.codeium/windsurf/mcp_config.json`
- **MCP aktiv**: `mcp0_` = github · `mcp1_` = orchestrator
- **Prod-Server**: `root@88.198.191.108` (SSH-Key hinterlegt)

## System (Hetzner Server)

- devuser hat **KEIN sudo-Passwort** → System-Pakete immer via SSH als root:
  ```bash
  ssh root@localhost "apt-get install -y <package>"
  ```

## Secrets — Single Source of Truth

**Alle Secrets lokal in `~/.secrets/`** — eine Datei pro Secret, Dateiname = lowercase Env-Var-Name.

| Datei | Env-Var | Inhalt | Status |
|-------|---------|--------|--------|
| `~/.secrets/github_token` | `PROJECT_PAT` / `GITHUB_TOKEN` | GitHub PAT (repo+workflow scope) | ✅ vorhanden |
| `~/.secrets/outline_api_token` | `OUTLINE_API_TOKEN` | Outline Wiki API Key | ✅ vorhanden |
| `~/.secrets/cloudflare_api_token` | `CLOUDFLARE_API_TOKEN` | Cloudflare API Token | ✅ vorhanden |
| `~/.secrets/cloudflare_access_token` | `CLOUDFLARE_ACCESS_TOKEN` | Cloudflare Access Token | ✅ vorhanden |
| `~/.secrets/cloudflare_write_token` | `CLOUDFLARE_WRITE_TOKEN` | Cloudflare Write Token | ✅ vorhanden |
| `~/.secrets/openai_api_key` | `OPENAI_API_KEY` | OpenAI API Key (sk-...) | ⚠️ nur in GitHub Actions |

> **Fehlender lokaler Key:** `openai_api_key` existiert nur in GitHub Actions Secrets.
> Um LLM-Calls lokal zu testen: `echo "sk-..." > ~/.secrets/openai_api_key && chmod 600 ~/.secrets/openai_api_key`

### Standard-Discovery in Scripts

```bash
# Shell-Scripts: ~/.secrets/ als Fallback
TOKEN=${PROJECT_PAT:-$(cat ~/.secrets/github_token 2>/dev/null)}
OPENAI_API_KEY=${OPENAI_API_KEY:-$(cat ~/.secrets/openai_api_key 2>/dev/null)}
```

```python
# Python-Scripts: selbes Pattern
import os
from pathlib import Path

def get_secret(name: str, env_var: str | None = None) -> str | None:
    """Read secret from env var, fallback to ~/.secrets/{name}."""
    val = os.environ.get(env_var or name.upper())
    if val:
        return val
    path = Path.home() / ".secrets" / name.lower()
    return path.read_text().strip() if path.exists() else None
```

### GitHub Actions Secrets (Prod CI)

Alle Secrets sind zusätzlich in GitHub Actions hinterlegt:
`OPENAI_API_KEY`, `PROJECT_PAT`, `PLATFORM_DEPLOY_TOKEN`, `CLOUDFLARE_*`
→ Settings → Secrets → Actions im jeweiligen Repo
