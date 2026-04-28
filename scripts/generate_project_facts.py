#!/usr/bin/env python3
"""
Generate .windsurf/project-facts/{repo}.md for ALL repos from repos.yaml + ports.yaml.

Usage:
    python3 scripts/generate_project_facts.py            # generate all
    python3 scripts/generate_project_facts.py travel-beat  # single repo

Output: platform/.windsurf/project-facts/{repo}.md
"""

import sys
from pathlib import Path

import yaml

PLATFORM_DIR = Path(__file__).parent.parent
REPOS_YAML = PLATFORM_DIR / "registry" / "repos.yaml"
PORTS_YAML = PLATFORM_DIR / "infra" / "ports.yaml"
OUTPUT_DIR = PLATFORM_DIR / ".windsurf" / "project-facts"

SECRETS_BLOCK = """## Secrets — ZWEI Pfade (beide prüfen!)

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
```"""

MCP_BLOCK = """## MCP-Konfiguration (devuser)

| Prefix | Server | Wichtigste Tools |
|--------|--------|-----------------|
| `mcp0_` | **github** | `get_file_contents`, `push_files`, `create_issue`, `list_issues` |
| `mcp1_` | **orchestrator** | `agent_memory_context`, `agent_memory_upsert`, `discord_notify` |"""


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_repo_index(repos_data: dict) -> dict:
    """repo_name → repo_dict"""
    index = {}
    for domain in repos_data.get("domains", []):
        for system in domain.get("systems", []):
            index[system["repo"]] = system
    return index


def build_ports_index(ports_data: dict) -> dict:
    """repo_name → port_dict"""
    index = {}
    for name, info in ports_data.get("services", {}).items():
        index[name] = info
    return index


def generate_django_facts(repo: str, info: dict, port_info: dict) -> str:
    deploy = info.get("deploy", {})
    url = info.get("url", "")
    port = port_info.get("prod", deploy.get("port", "?"))
    container = port_info.get("container_name", deploy.get("web_container", "?"))
    server_path = deploy.get("server_path", f"/opt/{repo}")
    migrate_cmd = deploy.get("migrate_cmd", "python manage.py migrate --noinput")
    multi_tenant = deploy.get("multi_tenant", False)
    domain_staging = port_info.get("domain_staging", "")
    domain_aliases = port_info.get("domain_aliases", [])
    lifecycle = info.get("lifecycle", "production")
    description = info.get("description", "")

    tenant_warning = ""
    if multi_tenant:
        tenant_warning = f"""
> ⚠️ **Multi-Tenant (django-tenants)** — NIEMALS `migrate --noinput` allein!
> Immer: `migrate_schemas --shared` + `migrate_schemas --tenant`
"""

    aliases_str = ""
    if domain_aliases:
        aliases_str = "\n- **Aliases**: " + ", ".join(domain_aliases)

    staging_str = f"\n- **Staging**: `{domain_staging}`" if domain_staging else ""

    return f"""# Project Facts: {repo}

> ⚠️ AUTO-GENERATED — Nur in `platform/.windsurf/project-facts/{repo}.md` editieren!
> Neu generieren: `python3 platform/scripts/generate_project_facts.py {repo}`

---

## Projekt

- **Beschreibung**: {description}
- **GitHub**: `achimdehnert/{repo}` → https://github.com/achimdehnert/{repo}
- **Typ**: Django · Lifecycle: {lifecycle}
- **URL**: {url or "–"}{staging_str}{aliases_str}
{tenant_warning}
---

## Deploy

| Variable | Wert |
|----------|------|
| **Server** | `88.198.191.108` |
| **Pfad** | `{server_path}` |
| **Port** | `{port}` |
| **Container** | `{container}` |
| **Migrate** | `{migrate_cmd}` |
| **Compose** | `docker-compose.prod.yml` |
| **Image** | `ghcr.io/achimdehnert/{repo}-web:${{IMAGE_TAG:-latest}}` |

---

## Settings

| Variable | Wert |
|----------|------|
| `DJANGO_SETTINGS_MODULE` | `config.settings` |
| `ROOT_URLCONF` | `config.urls` |
| `WSGI` | `config.wsgi.application` |
| `DEFAULT_AUTO_FIELD` | `BigAutoField` |

---

{SECRETS_BLOCK}

---

{MCP_BLOCK}

---

## Lokale Umgebung

| Variable | Wert |
|----------|------|
| Lokaler Pfad | `/home/devuser/github/{repo}` |
| Venv | `/home/devuser/github/{repo}/.venv/bin/python` |
| DB (lokal) | `localhost:5432` |
| Health | `/livez/` (liveness) · `/healthz/` (readiness) |
"""


def generate_library_facts(repo: str, info: dict) -> str:
    description = info.get("description", "")
    return f"""# Project Facts: {repo}

> ⚠️ AUTO-GENERATED — Nur in `platform/.windsurf/project-facts/{repo}.md` editieren!
> Neu generieren: `python3 platform/scripts/generate_project_facts.py {repo}`

---

## Projekt

- **Beschreibung**: {description}
- **GitHub**: `achimdehnert/{repo}` → https://github.com/achimdehnert/{repo}
- **Typ**: Library / Infra (kein Deployment)

---

{SECRETS_BLOCK}

---

{MCP_BLOCK}

---

## Lokale Umgebung

| Variable | Wert |
|----------|------|
| Lokaler Pfad | `/home/devuser/github/{repo}` |
| Python | `/home/devuser/github/{repo}/.venv/bin/python` |
"""


def generate_python_facts(repo: str, info: dict, port_info: dict) -> str:
    description = info.get("description", "")
    port = port_info.get("prod", "?") if port_info else "–"
    container = port_info.get("container_name", "?") if port_info else "–"
    return f"""# Project Facts: {repo}

> ⚠️ AUTO-GENERATED — Nur in `platform/.windsurf/project-facts/{repo}.md` editieren!
> Neu generieren: `python3 platform/scripts/generate_project_facts.py {repo}`

---

## Projekt

- **Beschreibung**: {description}
- **GitHub**: `achimdehnert/{repo}` → https://github.com/achimdehnert/{repo}
- **Typ**: Python (kein Django)
- **Port**: {port} · **Container**: `{container}`

---

{SECRETS_BLOCK}

---

{MCP_BLOCK}

---

## Lokale Umgebung

| Variable | Wert |
|----------|------|
| Lokaler Pfad | `/home/devuser/github/{repo}` |
| Python | `/home/devuser/github/{repo}/.venv/bin/python` |
"""


def generate_facts(repo: str, info: dict, port_info: dict) -> str:
    repo_type = info.get("type", "django")
    if repo_type == "django":
        return generate_django_facts(repo, info, port_info)
    elif repo_type == "library":
        return generate_library_facts(repo, info)
    else:
        return generate_python_facts(repo, info, port_info)


def main():
    repos_data = load_yaml(REPOS_YAML)
    ports_data = load_yaml(PORTS_YAML)

    repo_index = build_repo_index(repos_data)
    ports_index = build_ports_index(ports_data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Alle Repos aus beiden Quellen zusammenführen
    all_repos = set(repo_index.keys()) | {
        info["repo"].split("/")[-1]
        for info in ports_data.get("services", {}).values()
        if info.get("repo") and info["repo"] != "null"
    }

    target = sys.argv[1] if len(sys.argv) > 1 else None
    repos_to_process = [target] if target else sorted(all_repos)

    generated = []
    skipped = []

    for repo in repos_to_process:
        if repo == "meiki-hub":
            skipped.append(f"  ⏭  {repo} (eigene org — manuell pflegen)")
            continue

        info = repo_index.get(repo)
        if not info:
            # Repo nur in ports.yaml — Minimal-Info erzeugen
            port_info = ports_index.get(repo, {})
            info = {
                "repo": repo,
                "description": port_info.get("domain_prod", "–"),
                "github": f"achimdehnert/{repo}",
                "type": "django",
                "lifecycle": "experimental",
                "url": f"https://{port_info.get('domain_prod', '')}" if port_info.get("domain_prod") else "",
            }

        port_info = ports_index.get(repo, {})
        content = generate_facts(repo, info, port_info)

        out_path = OUTPUT_DIR / f"{repo}.md"
        # meiki-hub already manually maintained — don't overwrite
        if out_path.exists() and repo == "meiki-hub":
            skipped.append(f"  ⏭  {repo} (manuell gepflegt — übersprungen)")
            continue

        out_path.write_text(content, encoding="utf-8")
        generated.append(f"  ✅ {repo}")

    print(f"\n📁 Output: {OUTPUT_DIR}")
    print(f"\nGeneriert ({len(generated)}):")
    for g in generated:
        print(g)
    if skipped:
        print(f"\nÜbersprungen ({len(skipped)}):")
        for s in skipped:
            print(s)


if __name__ == "__main__":
    main()
