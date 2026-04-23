#!/usr/bin/env python3
"""
gen_project_facts.py — MASTER REPO IDENTIFIER & project-facts.md Generator

Usage:
    python3 gen_project_facts.py              # all repos (skip existing)
    python3 gen_project_facts.py risk-hub     # single repo
    python3 gen_project_facts.py --force      # overwrite all
    python3 gen_project_facts.py risk-hub --force

Source of truth: repo-registry.yaml (same directory)
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).parent
REGISTRY_FILE = SCRIPT_DIR / "repo-registry.yaml"
GITHUB = Path("/home/devuser/github")
WORKFLOWS_SRC = GITHUB / "platform" / ".windsurf" / "workflows"
RULES_SRC = GITHUB / "platform" / ".windsurf" / "rules"

# Global rules distributed to ALL repos as symlinks
GLOBAL_RULES = [
    "mcp-tools.md",
    "reviewer.md",
    "platform-principles.md",
    "iil-packages.md",
    "testing.md",
    "django-models-views.md",
    "docker-deployment.md",
    "htmx-templates.md",
]


# ── Registry ─────────────────────────────────────────────────────────────────

def load_registry() -> dict:
    with open(REGISTRY_FILE) as f:
        return yaml.safe_load(f)


# ── Auto-detect from docker-compose files ────────────────────────────────────

def compose_files(repo_path: Path) -> list[Path]:
    return list(repo_path.glob("docker-compose*.yml"))


def detect(repo_path: Path, pattern: str) -> str:
    """Grep all compose files for pattern, return first match group 1."""
    for cf in compose_files(repo_path):
        try:
            text = cf.read_text()
            m = re.search(pattern, text)
            if m:
                return m.group(1)
        except Exception:
            pass
    return ""


def detect_port(repo_path: Path) -> str:
    return detect(repo_path, r'"127\.0\.0\.1:(\d{4,5}):\d+')


def detect_db(repo_path: Path) -> str:
    v = detect(repo_path, r"POSTGRES_DB:\s+\$\{[^:]+:-([a-zA-Z_]+)\}")
    if not v:
        v = detect(repo_path, r"POSTGRES_DB:\s+([a-zA-Z_][a-zA-Z0-9_]*)\s")
    return v


def detect_health(repo_path: Path) -> str:
    v = detect(repo_path, r"(/(livez|health|readyz)/)")
    return v or "/livez/"


def detect_prod_url(repo_path: Path) -> str:
    files = compose_files(repo_path)
    env_example = repo_path / ".env.example"
    if env_example.exists():
        files.append(env_example)
    for f in files:
        try:
            text = f.read_text()
            for line in text.splitlines():
                if any(k in line for k in ("ALLOWED_HOSTS", "DJANGO_ALLOWED_HOSTS", "CSRF_TRUSTED")):
                    urls = re.findall(r"[a-z0-9.-]+\.(de|com|pet|io|net)", line)
                    for url, _ in [(u, None) for u in urls]:
                        if "localhost" not in url and "127.0" not in url:
                            return url
        except Exception:
            pass
    return ""


def detect_container_prefix(repo_path: Path) -> str:
    v = detect(repo_path, r"container_name:\s+([a-zA-Z0-9_]+)_(web|db|worker|redis)")
    return v or ""


def detect_pypi_name(repo_path: Path) -> str:
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        m = re.search(r'^name\s*=\s*["\']?([a-zA-Z0-9_-]+)', pyproject.read_text(), re.M)
        if m:
            return m.group(1)
    return ""


# ── Generate project-facts.md ────────────────────────────────────────────────

def gen_facts(repo: str, reg_entry: dict, force: bool = False) -> str:
    repo_path = GITHUB / repo
    if not repo_path.is_dir():
        return f"❌ NOT FOUND: {repo}"

    facts_file = repo_path / ".windsurf" / "rules" / "project-facts.md"
    facts_file.parent.mkdir(parents=True, exist_ok=True)

    # Copy workflows to every repo (except platform itself)
    wf_dest = repo_path / ".windsurf" / "workflows"
    wf_dest.mkdir(parents=True, exist_ok=True)
    if repo != "platform" and WORKFLOWS_SRC.is_dir():
        for wf in ["run-local.md", "run-staging.md", "run-prod.md"]:
            src = WORKFLOWS_SRC / wf
            if src.exists():
                shutil.copy2(src, wf_dest / wf)

    # Symlink global rules to every repo (except platform itself)
    rules_dest = repo_path / ".windsurf" / "rules"
    rules_dest.mkdir(parents=True, exist_ok=True)
    if repo != "platform" and RULES_SRC.is_dir():
        for rule in GLOBAL_RULES:
            src = RULES_SRC / rule
            link = rules_dest / rule
            if src.exists():
                if link.is_symlink():
                    link.unlink()
                elif link.exists():
                    link.unlink()  # replace stale copy with symlink
                link.symlink_to(src)

    if facts_file.exists() and not force:
        return f"SKIP (exists): {repo}"

    # Read registry values (take precedence)
    rtype      = reg_entry.get("type", "")
    prod_url   = str(reg_entry.get("prod_url", ""))
    staging_url= str(reg_entry.get("staging_url", ""))
    port       = str(reg_entry.get("port", ""))
    db         = str(reg_entry.get("db", ""))
    health     = str(reg_entry.get("health", ""))
    pypi       = str(reg_entry.get("pypi", ""))
    note       = str(reg_entry.get("note", ""))

    # Auto-detect fallbacks
    if not port:     port = detect_port(repo_path)
    if not port:     port = "8000"
    if not db:       db = detect_db(repo_path)
    if not db:       db = repo.replace("-", "_")
    if not health:   health = detect_health(repo_path)
    if not prod_url: prod_url = detect_prod_url(repo_path)
    if not prod_url: prod_url = f"{repo}.iil.pet"
    if not staging_url: staging_url = f"staging.{prod_url}"
    if not pypi:     pypi = detect_pypi_name(repo_path)
    if not rtype:    rtype = "unknown"

    prefix = detect_container_prefix(repo_path) or repo.replace("-", "_")
    has_compose = bool(compose_files(repo_path))

    compose_local   = "docker-compose.local.yml" if (repo_path / "docker-compose.local.yml").exists() else "docker-compose.yml"
    compose_staging = "docker-compose.staging.yml"
    compose_prod    = "docker-compose.prod.yml" if (repo_path / "docker-compose.prod.yml").exists() else "docker-compose.yml"

    lines = [
        "---",
        "trigger: always_on",
        "---",
        "",
        f"# Project Facts: {repo}",
    ]
    if note:
        lines += ["", f"> {note}"]

    lines += [
        "",
        "## Meta",
        "",
        f"- **Type**: `{rtype}`",
        f"- **GitHub**: `https://github.com/achimdehnert/{repo}`",
        "- **Branch**: `main` — push: `git push` (SSH-Key konfiguriert)",
    ]
    if pypi:
        lines += [
            f"- **PyPI**: `{pypi}`",
            "- **Venv**: `.venv/` — test: `.venv/bin/python -m pytest`",
        ]

    if has_compose:
        lines += [
            "",
            "## Environments",
            "",
            "| Env | Compose File | Host Port | Health URL | Public URL |",
            "|-----|-------------|-----------|------------|------------|",
            f"| local   | `{compose_local}`   | `{port}` | `http://localhost:{port}{health}` | http://localhost:{port} |",
            f"| staging | `{compose_staging}` | `{port}` | `http://localhost:{port}{health}` | https://{staging_url} |",
            f"| prod    | `{compose_prod}`    | `{port}` | `http://localhost:{port}{health}` | https://{prod_url} |",
            "",
            "## Docker Containers",
            "",
            "| Container | Name | Purpose |",
            "|-----------|------|---------|",
            f"| web    | `{prefix}_web`    | gunicorn:8000 |",
            f"| db     | `{prefix}_db`     | postgres:16   |",
            f"| redis  | `{prefix}_redis`  | redis:7       |",
            f"| worker | `{prefix}_worker` | celery (if present) |",
            "",
            "## Database",
            "",
            f"- **DB name**: `{db}`",
            f"- **DB container**: `{prefix}_db`",
            f"- **Migrations**: `docker exec {prefix}_web python manage.py migrate`",
            f"- **Shell**: `docker exec -it {prefix}_web python manage.py shell`",
        ]

    lines += [
        "",
        "## System (Hetzner Server)",
        "",
        "- devuser hat **KEIN sudo-Passwort** → System-Pakete immer via SSH als root:",
        "  ```bash",
        "  ssh root@localhost \"apt-get install -y <package>\"",
        "  ```",
        "",
        "## Secrets / Config",
        "",
        "- **Secrets**: `.env` (nicht in Git) — Template: `.env.example`",
    ]

    facts_file.write_text("\n".join(lines) + "\n")
    return f"✅ {repo} (type={rtype}, port={port}, prod={prod_url})"


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    force = "--force" in args
    target = next((a for a in args if not a.startswith("-")), "")

    registry = load_registry()
    reg_repos = registry.get("repos", {})
    server_cfg = registry.get("server", {})

    print("=== gen_project_facts.py — Master Repo Identifier ===")
    print(f"Registry: {REGISTRY_FILE}")
    print(f"Force:    {force}")
    print(f"Server:   {server_cfg.get('github_base', GITHUB)}")
    print()

    results = []

    if target:
        entry = reg_repos.get(target, {})
        results.append(gen_facts(target, entry, force=force))
    else:
        # 1. All repos from registry (with overrides)
        for repo, entry in reg_repos.items():
            results.append(gen_facts(repo, entry or {}, force=force))

        # 2. Unregistered repos on disk
        print("\n--- Scanning for unregistered repos ---")
        for repo_path in sorted(GITHUB.iterdir()):
            if not repo_path.is_dir():
                continue
            repo = repo_path.name
            if "." in repo:  # skip .code-workspace etc
                continue
            if repo not in reg_repos:
                print(f"⚠️  UNREGISTERED: {repo} — add to repo-registry.yaml")
                results.append(gen_facts(repo, {}, force=force))

    print("\n".join(results))
    print(f"\n=== Done ({sum(1 for r in results if r.startswith('✅'))} generated, "
          f"{sum(1 for r in results if 'SKIP' in r)} skipped) ===")
    print("Run with --force to regenerate all.")


if __name__ == "__main__":
    main()

# NOTE: GLOBAL_RULES is defined at module level above — update it there
