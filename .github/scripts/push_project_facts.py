#!/usr/bin/env python3
"""push_project_facts.py — Generiert und pusht project-facts.md in alle Django-Repos.

Liest repo-registry.yaml + pyproject.toml per GitHub API.
Erkennt: Settings-Modul, HTMX, pythonpath, Apps, Django-Version.
Pusht project-facts.md an Repo-Root via GitHub API.

Usage (GitHub Actions oder lokal):
    python3 push_project_facts.py                    # alle django-Repos
    python3 push_project_facts.py risk-hub           # einzelnes Repo
    python3 push_project_facts.py risk-hub --dry-run # nur Ausgabe, kein Push

Env-Vars:
    GITHUB_TOKEN  — Personal Access Token (repo scope)
    GITHUB_ORG    — Organisation (default: achimdehnert)
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
REGISTRY_PATH = SCRIPT_DIR.parent.parent / "scripts" / "repo-registry.yaml"
ORG = os.environ.get("GITHUB_ORG", "achimdehnert")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# GitHub API helpers (stdlib only)
# ---------------------------------------------------------------------------

def _req(url: str, method: str = "GET", body: bytes | None = None) -> dict | list | None:
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def gh_get_file(repo: str, path: str) -> str | None:
    """Return decoded file content or None if not found."""
    data = _req(f"{API}/repos/{ORG}/{repo}/contents/{path}")
    if data and isinstance(data, dict) and data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode()
    return None


def gh_get_dir(repo: str, path: str) -> list[str]:
    """Return list of entry names in directory, or [] if not found."""
    data = _req(f"{API}/repos/{ORG}/{repo}/contents/{path}")
    if isinstance(data, list):
        return [e["name"] for e in data]
    return []


def gh_push_file(repo: str, path: str, content: str, message: str) -> bool:
    """Create or update a file in the repo. Returns True on success."""
    existing = _req(f"{API}/repos/{ORG}/{repo}/contents/{path}")
    sha = existing.get("sha") if isinstance(existing, dict) else None
    payload: dict = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha
    body = json.dumps(payload).encode()
    result = _req(f"{API}/repos/{ORG}/{repo}/contents/{path}", method="PUT", body=body)
    return bool(result)


# ---------------------------------------------------------------------------
# Registry loader (plain text parse, no yaml dep needed)
# ---------------------------------------------------------------------------

def load_registry() -> dict[str, dict]:
    """Minimal YAML parser — reads repo-registry.yaml into flat dict."""
    try:
        import yaml  # noqa: PLC0415
        with open(REGISTRY_PATH) as f:
            data = yaml.safe_load(f)
        return data.get("repos", {})
    except ImportError:
        pass

    # Fallback: hand-parse the simple YAML structure
    repos: dict[str, dict] = {}
    current: str | None = None
    with open(REGISTRY_PATH) as f:
        for raw in f:
            line = raw.rstrip()
            # Top-level repo key: "  risk-hub:"
            m = re.match(r"^  ([a-zA-Z0-9_-]+):\s*$", line)
            if m:
                current = m.group(1)
                repos[current] = {}
                continue
            if current:
                # Sub-key: "    port: 8090"
                m2 = re.match(r"^    ([a-zA-Z_]+):\s*(.*)", line)
                if m2:
                    k, v = m2.group(1), m2.group(2).strip().strip("\"'")
                    if k != "note":  # skip notes for now
                        repos[current][k] = v
    return repos


# ---------------------------------------------------------------------------
# Django-specific detection
# ---------------------------------------------------------------------------

def detect_from_pyproject(content: str) -> dict:
    """Extract Django facts from pyproject.toml content."""
    info: dict = {}

    # DJANGO_SETTINGS_MODULE (test)
    m = re.search(r'DJANGO_SETTINGS_MODULE\s*=\s*["\']([^"\']+)["\']', content)
    if m:
        info["test_settings"] = m.group(1)

    # pythonpath
    m = re.search(r'pythonpath\s*=\s*\[([^\]]+)\]', content)
    if m:
        paths = re.findall(r'["\']([^"\']+)["\']', m.group(1))
        info["pythonpath"] = paths[0] if paths else ""

    # testpaths
    m = re.search(r'testpaths\s*=\s*\[([^\]]+)\]', content)
    if m:
        paths = re.findall(r'["\']([^"\']+)["\']', m.group(1))
        info["testpaths"] = paths[0] if paths else "tests"

    # Django version
    m = re.search(r'["\']?Django["\']?\s*>=?\s*([\d.]+)', content, re.I)
    if m:
        info["django_version"] = m.group(1)

    # Python version
    m = re.search(r'requires-python\s*=\s*["\']>=?\s*([\d.]+)', content)
    if m:
        info["python_version"] = m.group(1)

    # HTMX: django-htmx in deps?
    info["has_django_htmx"] = bool(re.search(r'django-htmx', content, re.I))

    # Celery?
    info["has_celery"] = bool(re.search(r'\bcelery\b', content, re.I))

    return info


def detect_htmx_method(repo: str, has_django_htmx: bool) -> str:
    """Check if request.htmx or raw header is used."""
    if has_django_htmx:
        return "request.htmx"
    # Try to find usage in views
    for path in ["apps", "src/apps", "src"]:
        content = gh_get_file(repo, f"{path}/views.py") or ""
        if "request.htmx" in content:
            return "request.htmx"
    return 'request.headers.get("HX-Request") == "true"'


def detect_src_root(repo: str) -> str:
    """Detect if manage.py is in root or src/."""
    root_files = gh_get_dir(repo, ".")
    if "src" in root_files:
        src_files = gh_get_dir(repo, "src")
        if "manage.py" in src_files:
            return "src"
    if "manage.py" in root_files:
        return "."
    return "."


_NON_APP_DIRS = {
    "config", "templates", "static", "staticfiles", "media",
    "__pycache__", "tests", "fixtures", "migrations", "locale",
    "management", "templatetags", "node_modules", ".hypothesis",
}


def detect_apps(repo: str, src_root: str) -> list[str]:
    """List Django app directories (checks src/apps/ AND src/ level)."""
    found: list[str] = []

    # 1. Conventional src/apps/ directory
    for apps_path in [f"{src_root}/apps", "apps"]:
        entries = gh_get_dir(repo, apps_path)
        apps = [
            e for e in entries
            if not e.startswith(".") and "." not in e and e not in _NON_APP_DIRS
        ]
        if len(apps) >= 2:
            found.extend(apps)

    # 2. Scan src_root directly for Django app dirs (have models.py or apps.py)
    src_entries = gh_get_dir(repo, src_root)
    for entry in src_entries:
        if entry.startswith(".") or "." in entry or entry in _NON_APP_DIRS:
            continue
        # Check if it's a Django app (has models.py or apps.py) — sample one
        sub = gh_get_dir(repo, f"{src_root}/{entry}")
        if "models.py" in sub or "apps.py" in sub or "views.py" in sub:
            if entry not in found:
                found.append(entry)

    return sorted(found) if found else []


def detect_settings_module(repo: str, src_root: str, test_settings: str) -> str:
    """Try to find the production settings module name."""
    # 1. Look in settings directory (subdirectory pattern)
    for settings_path in [f"{src_root}/config/settings", "config/settings",
                          f"{src_root}/settings", "settings"]:
        entries = gh_get_dir(repo, settings_path)
        if not entries:
            continue
        for candidate in ("production.py", "prod.py", "settings_production.py"):
            if candidate in entries:
                # e.g. src/config/settings → config.settings
                module_base = settings_path.replace(f"{src_root}/", "").replace("/", ".")
                return f"{module_base}.{candidate.replace('.py', '')}"

    # 2. Single-file settings (settings.py next to other settings_*.py)
    for parent_path in [f"{src_root}/config", "config", src_root, "."]:
        entries = gh_get_dir(repo, parent_path)
        for candidate in ("settings_production.py", "settings_prod.py",
                          "settings.production.py"):
            if candidate in entries:
                module_base = parent_path.replace(f"{src_root}/", "").replace("/", ".")
                return f"{module_base}.{candidate.replace('.py', '')}"

    # 3. Derive from test settings
    if test_settings:
        for old, new in (("_test", "_production"), (".test", ".production"),
                         ("_tests", "_production")):
            if old in test_settings:
                return test_settings.replace(old, new)
    return "[TODO: manuell prüfen — production settings nicht auto-detektiert]"


# ---------------------------------------------------------------------------
# Markdown generator
# ---------------------------------------------------------------------------

def build_project_facts(repo: str, reg: dict, info: dict, src_root: str, apps: list[str]) -> str:
    prod_url = reg.get("prod_url", f"{repo}.iil.pet")
    staging_url = reg.get("staging_url", f"staging.{prod_url}")
    port = reg.get("port", "8000")
    health = reg.get("health", "/livez/")
    db = reg.get("db", repo.replace("-", "_"))
    rtype = reg.get("type", "django")

    django_v = info.get("django_version", "5.x")
    python_v = info.get("python_version", "3.12")
    pythonpath = info.get("pythonpath", src_root if src_root != "." else ".")
    testpaths = info.get("testpaths", "tests")
    test_settings = info.get("test_settings", "[TODO: aus pyproject.toml lesen]")
    prod_settings = info.get("prod_settings", "[TODO: manuell prüfen]")
    htmx_detection = info.get("htmx_detection", 'request.headers.get("HX-Request")')
    has_htmx = info.get("has_django_htmx", False)
    has_celery = info.get("has_celery", False)

    src_root_display = f"`{src_root}/`" if src_root != "." else "`./` (root)"

    apps_str = "\n".join(f"- `{a}`" for a in apps) if apps else "- [TODO: manuell ergänzen]"

    celery_line = "\n- **Celery**: ja (Worker + Beat)" if has_celery else ""

    lines = [
        f"# Project Facts: {repo}",
        "",
        f"> Auto-generiert von `platform/.github/scripts/push_project_facts.py`",
        f"> Letzte Aktualisierung: {TODAY} — bei Änderungen: `platform/gen-project-facts.yml` triggern",
        "",
        "## Meta",
        "",
        f"- **Type**: `{rtype}`",
        f"- **GitHub**: `https://github.com/{ORG}/{repo}`",
        "- **Branch**: `main` — push: `git push` (SSH-Key konfiguriert)",
        "",
        "## Lokale Umgebung (Dev Desktop — adehnert)",
        "",
        f"- **Pfad**: `~/CascadeProjects/{repo}` → `$GITHUB_DIR` = `~/CascadeProjects`",
        f"- **src_root**: {src_root_display} — `manage.py` liegt dort",
        f"- **pythonpath**: `{pythonpath}/`",
        f"- **Venv**: `~/CascadeProjects/{repo}/.venv/bin/python`",
        "- **MCP aktiv**: `mcp0_` = github · `mcp1_` = orchestrator",
        "",
        "## Settings",
        "",
        f"- **Prod-Modul**: `{prod_settings}`",
        f"- **Test-Modul**: `{test_settings}`",
        f"- **Testpfad**: `{testpaths}/`",
        "",
        "## Stack",
        "",
        f"- **Django**: `{django_v}`",
        f"- **Python**: `{python_v}`",
        f"- **PostgreSQL**: `16`",
        f"- **HTMX installiert**: {'ja (`django-htmx`)' if has_htmx else 'nein'}",
        f"- **HTMX-Detection**: `{htmx_detection}`",
        celery_line,
        "",
        "## Apps",
        "",
        apps_str,
        "",
        "## Infrastruktur",
        "",
        f"- **Prod-URL**: `{prod_url}`",
        f"- **Staging-URL**: `{staging_url}`",
        f"- **Port**: `{port}`",
        f"- **Health-Endpoint**: `{health}`",
        f"- **DB-Name**: `{db}`",
        "",
        "## System (Hetzner Server)",
        "",
        "- devuser hat **KEIN sudo-Passwort** → System-Pakete immer via SSH als root:",
        "  ```bash",
        "  ssh root@localhost \"apt-get install -y <package>\"",
        "  ```",
    ]

    return "\n".join(line for line in lines) + "\n"


# ---------------------------------------------------------------------------
# Main per-repo logic
# ---------------------------------------------------------------------------

def process_repo(repo: str, reg: dict, dry_run: bool) -> str:
    print(f"\n→ {repo} ...", flush=True)

    # Fetch pyproject.toml
    pyproject_content = (
        gh_get_file(repo, "pyproject.toml") or
        gh_get_file(repo, "src/pyproject.toml") or
        ""
    )

    info = detect_from_pyproject(pyproject_content) if pyproject_content else {}

    # Detect structure
    src_root = detect_src_root(repo)
    apps = detect_apps(repo, src_root)

    # Prod settings
    info["prod_settings"] = detect_settings_module(
        repo, src_root, info.get("test_settings", "")
    )

    # HTMX detection method
    info["htmx_detection"] = detect_htmx_method(repo, info.get("has_django_htmx", False))

    # Build content
    content = build_project_facts(repo, reg, info, src_root, apps)

    if dry_run:
        print(content)
        return f"DRY-RUN: {repo}"

    # Push to repo root
    ok = gh_push_file(
        repo,
        "project-facts.md",
        content,
        f"docs: project-facts.md aktualisiert ({TODAY}) [skip ci]",
    )
    return f"{'✅' if ok else '❌'} {repo}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    target = next((a for a in args if not a.startswith("-")), "")

    if not TOKEN and not dry_run:
        print("ERROR: GITHUB_TOKEN nicht gesetzt. Export: export GITHUB_TOKEN=$(cat ~/.secrets/github_PAT)")
        sys.exit(1)

    repos = load_registry()
    django_repos = {
        name: cfg for name, cfg in repos.items()
        if (cfg or {}).get("type", "django") == "django"
    }

    targets = {target: repos.get(target, {})} if target else django_repos

    print(f"=== push_project_facts.py — {TODAY} ===")
    print(f"Repos: {list(targets.keys())}")
    print(f"Dry-run: {dry_run}")

    results = []
    for repo_name, reg_cfg in targets.items():
        try:
            result = process_repo(repo_name, reg_cfg or {}, dry_run)
            results.append(result)
            print(f"  {result}", flush=True)
        except Exception as exc:
            msg = f"❌ {repo_name}: {exc}"
            results.append(msg)
            print(f"  {msg}", flush=True)

    ok = sum(1 for r in results if r.startswith("✅"))
    fail = sum(1 for r in results if r.startswith("❌"))
    print(f"\n=== Fertig: {ok} ok, {fail} fehler ===")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
