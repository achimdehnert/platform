#!/usr/bin/env python3
"""
Generate .windsurf/project-facts/{repo}.md for ALL repos.

SSoT-Hierarchie (Priorität absteigend):
  1. GitHub API  — vollständige, aktuelle Repo-Liste (nie veraltet)
  2. ports.yaml  — Port, Container, Domain, Staging-URL
  3. repos.yaml  — Beschreibung, Lifecycle, Deploy-Details

Usage:
    python3 scripts/generate_project_facts.py            # alle Repos
    python3 scripts/generate_project_facts.py travel-beat  # einzelnes Repo
    python3 scripts/generate_project_facts.py --list       # nur auflisten

Output: platform/.windsurf/project-facts/{repo}.md
"""

import sys
import json
import urllib.request
import urllib.error
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


GITHUB_ORGS = ["achimdehnert", "meiki-lra", "ttz-lif"]
SECRETS_DIRS = [Path("/home/devuser/shared/secrets"), Path.home() / ".secrets"]

MANUALLY_MAINTAINED = {"meiki-hub", "ttz-hub"}  # eigene Orgs — nicht überschreiben


def get_token() -> str | None:
    for base in SECRETS_DIRS:
        p = base / "github_token"
        if p.exists():
            return p.read_text().strip()
    return None


def github_api(path: str, token: str) -> list | dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _fetch_pages(path: str, token: str) -> list[dict]:
    """Alle Seiten einer paginierten GitHub API Route laden."""
    results = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        data = github_api(f"{path}{sep}per_page=100&page={page}", token)
        if not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
        page += 1
    return results


def get_all_repos_api(token: str) -> list[dict]:
    """Alle Repos via GitHub API — authenticated user + orgs."""
    all_repos = []

    # 1. Alle Repos des authentifizierten Users (inkl. private)
    try:
        repos = _fetch_pages("/user/repos?affiliation=owner,collaborator&sort=full_name", token)
        all_repos.extend(repos)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError(f"Token ungültig/abgelaufen (HTTP {e.code})")

    # 2. Zusätzlich Orgs (meiki-lra, ttz-lif — nicht owner des Tokens)
    extra_orgs = [o for o in GITHUB_ORGS if o != "achimdehnert"]
    for org in extra_orgs:
        try:
            repos = _fetch_pages(f"/orgs/{org}/repos?sort=name", token)
            all_repos.extend(repos)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise RuntimeError(f"Token ungültig/abgelaufen (HTTP {e.code})")
            # 404 = org nicht gefunden, überspringen
    return all_repos


def get_all_repos_local(github_dir: Path = Path("/home/devuser/github")) -> list[dict]:
    """Fallback: lokale git-Clones scannen und Owner aus remote-URL lesen."""
    import subprocess
    repos = []
    for entry in sorted(github_dir.iterdir()):
        if not entry.is_dir():
            continue
        git_dir = entry / ".git"
        if not git_dir.exists():
            continue
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=entry, capture_output=True, text=True, timeout=3
            )
            remote = result.stdout.strip()
            # Parst git@github.com:owner/repo.git  oder  https://...@github.com/owner/repo.git
            if "github.com" in remote:
                # Normalisieren: entfernt https://token@ prefix
                if "@github.com:" in remote:
                    path = remote.split("@github.com:")[-1]
                elif "github.com/" in remote:
                    path = remote.split("github.com/")[-1]
                else:
                    path = ""
                path = path.removesuffix(".git")
                parts = path.split("/")
                if len(parts) == 2:
                    owner, name = parts
                    repos.append({
                        "name": name,
                        "owner": owner,
                        "description": "",
                        "language": "",
                        "url": "",
                        "private": False,
                        "archived": False,
                    })
        except Exception:
            continue
    return repos


def get_all_repos(token: str | None) -> tuple[list[dict], str]:
    """Repos laden — API zuerst, bei Fehler lokaler Fallback.
    Returns: (repos_list, source_description)
    """
    if token:
        try:
            repos = get_all_repos_api(token)
            if repos:
                return repos, "GitHub API"
        except RuntimeError as e:
            print(f"⚠️  {e} — verwende lokalen Fallback")
        except Exception as e:
            print(f"⚠️  GitHub API nicht erreichbar: {e} — verwende lokalen Fallback")

    repos = get_all_repos_local()
    return repos, "lokale git-Clones (Fallback)"


GITHUB_DIR = Path("/home/devuser/github")


def detect_repo_details(repo: str) -> dict:
    """Auto-detect repo details from local clone."""
    repo_dir = GITHUB_DIR / repo
    details = {
        "db_name": repo.replace("-", "_"),          # travel-beat → travel_beat
        "settings_module": "config.settings",        # ADR-Konvention, immer gleich
        "htmx_method": None,
        "has_celery": False,
        "has_redis": False,
        "has_docker": False,
    }

    if not repo_dir.exists():
        return details

    # HTMX-Detection aus requirements.txt / pyproject.toml
    for req_file in ["requirements.txt", "requirements/base.txt",
                     "requirements/production.txt", "pyproject.toml"]:
        req_path = repo_dir / req_file
        if req_path.exists():
            content = req_path.read_text(encoding="utf-8", errors="ignore").lower()
            if "django-htmx" in content:
                details["htmx_method"] = "request.htmx  # django-htmx installed"
                break
            elif "htmx" in content:
                details["htmx_method"] = 'request.headers.get("HX-Request") == "true"'
                break
    if not details["htmx_method"]:
        # Fallback: settings.py auf django_htmx prüfen
        for settings_path in [repo_dir / "config" / "settings.py",
                               repo_dir / "config" / "settings" / "base.py"]:
            if settings_path.exists():
                content = settings_path.read_text(encoding="utf-8", errors="ignore")
                if "django_htmx" in content:
                    details["htmx_method"] = "request.htmx  # django-htmx installed"
                    break

    # Celery / Redis aus requirements
    for req_file in ["requirements.txt", "requirements/base.txt"]:
        req_path = repo_dir / req_file
        if req_path.exists():
            content = req_path.read_text(encoding="utf-8", errors="ignore").lower()
            details["has_celery"] = "celery" in content
            details["has_redis"] = "redis" in content
            break

    # Docker
    details["has_docker"] = (repo_dir / "Dockerfile").exists() or \
                             (repo_dir / "docker").is_dir()

    return details


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_repo_index(repos_data: dict) -> dict:
    """repo_name → repo_dict aus repos.yaml"""
    index = {}
    for domain in repos_data.get("domains", []):
        for system in domain.get("systems", []):
            index[system["repo"]] = system
    return index


def build_ports_index(ports_data: dict) -> dict:
    """repo_name → port_dict aus ports.yaml"""
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
    owner = info.get("owner", "achimdehnert")

    # Auto-detect aus lokalem Clone
    detected = detect_repo_details(repo)
    db_name = detected["db_name"]
    settings_module = detected["settings_module"]
    htmx_method = detected["htmx_method"] or 'request.headers.get("HX-Request") == "true"  # django-htmx NICHT installiert'
    services_line = " · ".join(filter(None, [
        "Celery" if detected["has_celery"] else "",
        "Redis" if detected["has_redis"] else "",
        "Docker" if detected["has_docker"] else "",
    ])) or "–"

    tenant_warning = ""
    if multi_tenant:
        tenant_warning = """
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
- **GitHub**: `{owner}/{repo}` → https://github.com/{owner}/{repo}
- **Typ**: Django · Lifecycle: {lifecycle}
- **URL**: {url or "–"}{staging_str}{aliases_str}
- **Services**: {services_line}
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
| **Image** | `ghcr.io/{owner}/{repo}-web:${{IMAGE_TAG:-latest}}` |

---

## Django Settings

| Variable | Wert |
|----------|------|
| `DJANGO_SETTINGS_MODULE` | `{settings_module}` |
| `ROOT_URLCONF` | `config.urls` |
| `WSGI` | `config.wsgi.application` |
| `DEFAULT_AUTO_FIELD` | `BigAutoField` |
| **DB-Name** | `{db_name}` |

## HTMX Detection

```python
{htmx_method}
```

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
| DB (lokal) | `localhost:5432/{db_name}` |
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
    args = sys.argv[1:]
    list_only = "--list" in args
    target = next((a for a in args if not a.startswith("--")), None)

    # --- Token ---
    token = get_token()
    if not token:
        print("⚠️  Kein GitHub-Token — nutze lokale git-Clones als Quelle")

    # --- Lokale Metadaten ---
    repos_data = load_yaml(REPOS_YAML)
    ports_data = load_yaml(PORTS_YAML)
    repo_index = build_repo_index(repos_data)
    ports_index = build_ports_index(ports_data)

    # --- SSoT: GitHub API (Fallback: lokale Clones) ---
    print("🔍 Lade Repo-Liste …")
    gh_repos, source = get_all_repos(token)
    print(f"   Quelle: {source} — {len(gh_repos)} Repos gefunden")

    # Repos deduplicieren (Name → {name, owner, description, language, archived})
    repo_map: dict[str, dict] = {}
    for r in gh_repos:
        name = r["name"]
        if r.get("archived"):
            continue
        owner_raw = r.get("owner", "achimdehnert")
        owner = owner_raw["login"] if isinstance(owner_raw, dict) else owner_raw
        repo_map[name] = {
            "name": name,
            "owner": owner,
            "description": r.get("description") or "",
            "language": r.get("language") or "",
            "url": r.get("homepage") or "",
            "private": r.get("private", False),
        }

    repos_to_process = sorted(repo_map.keys()) if not target else [target]

    if list_only:
        print(f"\n📋 Alle Repos ({len(repo_map)}) via GitHub API:\n")
        for name, r in sorted(repo_map.items()):
            org = r["owner"]
            print(f"  {org}/{name:<35} {r['language']:<12} {r['description'][:60]}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generated, skipped = [], []

    for repo in repos_to_process:
        if repo not in repo_map:
            skipped.append(f"  ⚠️  {repo} (nicht auf GitHub)")
            continue

        gh = repo_map[repo]
        reg = repo_index.get(repo, {})
        port_info = ports_index.get(repo, {})

        # Beschreibung: GitHub API > repos.yaml
        description = gh["description"] or reg.get("description", "–")
        # URL: homepage > repos.yaml url
        url = gh["url"] or reg.get("url", "")
        # Typ bestimmen
        if gh["language"] in ("", None) and not port_info:
            repo_type = reg.get("type", "library")
        elif port_info:
            repo_type = "django"
        else:
            repo_type = reg.get("type", "python")

        info = {
            **reg,
            "repo": repo,
            "description": description,
            "url": url,
            "type": repo_type,
            "lifecycle": reg.get("lifecycle", "experimental"),
            "owner": gh["owner"],
        }

        # Manuell gepflegte Repos: nur generieren wenn explizit angefragt
        if repo in MANUALLY_MAINTAINED and not target:
            skipped.append(f"  ⏭  {repo} (manuell gepflegt — skip, explizit mit arg aufrufen)")
            continue

        content = generate_facts(repo, info, port_info)
        out_path = OUTPUT_DIR / f"{repo}.md"
        out_path.write_text(content, encoding="utf-8")
        generated.append(f"  ✅ {gh['owner']}/{repo}")

    print(f"\n📁 Output: {OUTPUT_DIR}")
    print(f"\nGeneriert ({len(generated)}):")
    for g in generated:
        print(g)
    if skipped:
        print(f"\nÜbersprungen ({len(skipped)}):")
        for s in skipped:
            print(s)
    print(f"\n✅ Gesamt: {len(generated)} generiert, {len(skipped)} übersprungen")


if __name__ == "__main__":
    main()
