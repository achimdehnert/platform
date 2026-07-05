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
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).parent
REGISTRY_FILE = SCRIPT_DIR / "repo-registry.yaml"

# Owner-Auflösung aus der kanonischen Registry (ADR-234/255) statt Hardcode.
sys.path.insert(0, str(SCRIPT_DIR.parent / "tools"))
import registry_api as reg  # noqa: E402

GITHUB = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))
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
    """Findet die erste plausible Produktions-Domain in Compose/`.env.example`.

    F-9 (repo-optimize 2026-07-03): die alte Regex `[a-z0-9.-]+\\.(de|com|pet|io|net)`
    hatte GENAU EINE Capture-Group (die TLD-Alternation) — `re.findall` liefert dann
    NUR die Gruppen-Treffer zurück (also `pet`, `com`, ...), nicht den vollen Match
    (Repro: frist-hub → `'pet'` statt `'frist-hub.pet'`). Fix: die Gruppe umschließt
    jetzt den GANZEN Match, die TLD-Alternation selbst ist non-capturing.
    """
    files = compose_files(repo_path)
    env_example = repo_path / ".env.example"
    if env_example.exists():
        files.append(env_example)
    for f in files:
        try:
            text = f.read_text()
            for line in text.splitlines():
                if any(k in line for k in ("ALLOWED_HOSTS", "DJANGO_ALLOWED_HOSTS", "CSRF_TRUSTED")):
                    urls = re.findall(r"([a-z0-9.-]+\.(?:de|com|pet|io|net))", line)
                    for url in urls:
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


# ── ADR-265 Guards (1:1-Muster aus scripts/sync-workflows.sh, #907/#950) ──────
#
# gen_facts() ist neben sync-workflows.sh ein zweiter Distributor von
# GLOBAL_RULES-Symlinks + Workflow-Kopien. Ohne dieselben drei Guards
# reproduziert er dieselben Schäden: Typechanges in platform-Pins/-Worktrees
# (SSoT-Skip), ??-Symlink-Noise in Repos ohne .windsurf-Ignore (Ignore-Guard),
# und permanenten Typechange-Dirt beim Ersetzen getrackter Dateien durch
# Symlinks (Tracked-Guard). project-facts.md selbst ist legitimer Per-Repo-
# Inhalt und bleibt außerhalb des SSoT-Skips von diesen Guards unberührt.


def _repo_origin_url(repo_path: Path) -> str:
    """Git-Remote-URL von `origin`, leer wenn nicht auflösbar (kein Repo/kein Remote)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
            capture_output=True, text=True, check=False,
        )
        return result.stdout.strip()
    except OSError:
        return ""


def _is_platform_ssot(repo_path: Path) -> bool:
    """SSoT-Skip (ADR-265): über den git-ORIGIN, nicht den Repo-Namen.

    Deckt sowohl `platform` selbst als auch Pins/Worktrees (z. B.
    `platform-pinned`) ab, die ein reiner Namensvergleich `repo != "platform"`
    verfehlt (Realfall: 8 T-Typechanges in platform-pinned, #931).
    """
    origin = _repo_origin_url(repo_path)
    return origin.endswith("/platform") or origin.endswith("/platform.git")


def _distribution_allowed(repo_path: Path) -> bool:
    """Ignore-Guard (ADR-265): Distribution nur, wenn `.windsurf/` im Ziel-Repo
    wirksam git-ignored ist — sonst erzeugt jeder neue Symlink/jede neue Kopie
    ??-Dirt im Ziel-Repo (Realfall: 6 Repos mit ??-rules-Symlinks, #931).
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "check-ignore", "-q",
             ".windsurf/workflows/__adr265_probe__.md"],
            capture_output=True, check=False,
        )
        return result.returncode == 0
    except OSError:
        return False


def _is_tracked(repo_path: Path, relpath: str) -> bool:
    """Tracked-Guard (ADR-265): True wenn `relpath` im Ziel-Repo-Index steht —
    eine getrackte Datei darf nie durch einen Symlink ersetzt werden (das
    erzeugt permanenten Typechange-Dirt)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "ls-files", "--error-unmatch", relpath],
            capture_output=True, check=False,
        )
        return result.returncode == 0
    except OSError:
        return False


# ── Generate project-facts.md ────────────────────────────────────────────────

def gen_facts(repo: str, reg_entry: dict, force: bool = False, dry_run: bool = False) -> str:
    repo_path = GITHUB / repo
    if not repo_path.is_dir():
        return f"❌ NOT FOUND: {repo}"

    # SSoT-Skip (ADR-265) — vor JEDEM mkdir/Schreiben: Repo komplett
    # überspringen, nichts anfassen (auch kein leeres .windsurf/ erzeugen).
    if _is_platform_ssot(repo_path):
        return f"SKIP (platform SSoT): {repo}"

    facts_file = repo_path / ".windsurf" / "rules" / "project-facts.md"
    if not dry_run:
        facts_file.parent.mkdir(parents=True, exist_ok=True)

    # Distribution (Workflow-Kopien + Rules-Symlinks) nur mit Ignore-Guard
    # (ADR-265). project-facts.md (oben) ist legitimer Per-Repo-Inhalt und
    # bleibt von diesem Guard unberührt. Unter --dry-run: keinerlei
    # Schreib-/mkdir-/Symlink-Operation (der ganze Block wird übersprungen).
    if not dry_run and _distribution_allowed(repo_path):
        # Copy workflows to every repo
        wf_dest = repo_path / ".windsurf" / "workflows"
        wf_dest.mkdir(parents=True, exist_ok=True)
        if WORKFLOWS_SRC.is_dir():
            for wf in ["run-local.md", "run-staging.md", "run-prod.md"]:
                src = WORKFLOWS_SRC / wf
                dst = wf_dest / wf
                # Tracked-Guard (ADR-265) auch auf dem Kopie-Pfad: eine getrackte
                # reguläre run-*.md NICHT überschreiben (sonst git-Dirt) — genau
                # dieser Pfad überschrieb im Incident 2026-07-05 billing-hub.
                if src.exists() and not dst.is_symlink() \
                        and not _is_tracked(repo_path, f".windsurf/workflows/{wf}"):
                    shutil.copy2(src, dst)

        # Symlink global rules to every repo.
        # Der frühere Einzel-Guard `repo != "platform" and not _origin_is_platform(...)`
        # (Retro d2522c M3, 0c2f607) ist hier entbehrlich: der SSoT-Skip oben
        # (`_is_platform_ssot`) greift bereits vor JEDEM Schreibzugriff und deckt
        # platform selbst wie auch Pins/Worktrees ab.
        rules_dest = facts_file.parent  # .windsurf/rules — bereits angelegt
        if RULES_SRC.is_dir():
            for rule in GLOBAL_RULES:
                src = RULES_SRC / rule
                link = rules_dest / rule
                if not src.exists():
                    continue
                if link.is_symlink():
                    link.unlink()
                    link.symlink_to(src)
                    continue
                if link.exists():
                    # Tracked-Guard (ADR-265): getrackte Datei nie durch
                    # Symlink ersetzen — diese Datei überspringen.
                    rel = str(link.relative_to(repo_path))
                    if _is_tracked(repo_path, rel):
                        continue
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
    if not port:
        port = detect_port(repo_path)
    if not port:
        port = "8000"
    if not db:
        db = detect_db(repo_path)
    if not db:
        db = repo.replace("-", "_")
    if not health:
        health = detect_health(repo_path)
    if not prod_url:
        prod_url = detect_prod_url(repo_path)
    # Plausibilitäts-Guard vor dem Schreiben (F-9): egal ob aus Registry oder
    # Auto-Detect — ein prod_url ohne "." oder mit <=4 Zeichen ist kein Domain-
    # Kandidat (z.B. ein TLD-Fragment wie "pet" aus dem alten Regex-Bug), sondern
    # ein Fallback-Fall.
    if not prod_url or "." not in prod_url or len(prod_url) <= 4:
        prod_url = f"{repo}.iil.pet"
    if not staging_url:
        staging_url = f"staging.{prod_url}"
    if not pypi:
        pypi = detect_pypi_name(repo_path)
    if not rtype:
        rtype = "unknown"

    prefix = detect_container_prefix(repo_path) or repo.replace("-", "_")
    has_compose = bool(compose_files(repo_path))

    # Fallback-Kette: local → dev → generisch (viele Repos haben nur dev/prod,
    # kein docker-compose.local.yml — vorher wurde fälschlich docker-compose.yml
    # emittiert, das nicht existiert). Siehe platform:ADR-219.
    if (repo_path / "docker-compose.local.yml").exists():
        compose_local = "docker-compose.local.yml"
    elif (repo_path / "docker-compose.dev.yml").exists():
        compose_local = "docker-compose.dev.yml"
    else:
        compose_local = "docker-compose.yml"
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

    # F-5: owner() liefert None für einen Namen, der weder in canonical.yaml
    # steht noch eine Prefix-Regel trifft (Typo/komplett unregistriert) — dann
    # NICHT still "None" in die generierte Doku schreiben, sondern den
    # konfigurierten Server-Default als sichtbaren Fallback nehmen.
    gh_owner = reg.owner(repo) or (reg.load_canonical().get("meta", {}).get("server") or {}).get(
        "github_org", "achimdehnert"
    )

    lines += [
        "",
        "## Meta",
        "",
        f"- **Type**: `{rtype}`",
        f"- **GitHub**: `https://github.com/{gh_owner}/{repo}`",
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

    if dry_run:
        return f"DRY-RUN (würde schreiben): {repo} (type={rtype}, port={port}, prod={prod_url})"
    facts_file.write_text("\n".join(lines) + "\n")
    return f"✅ {repo} (type={rtype}, port={port}, prod={prod_url})"


# ── Main ─────────────────────────────────────────────────────────────────────

USAGE = """gen_project_facts.py — Master Repo Identifier / project-facts-Generator

Usage:
  python3 gen_project_facts.py [repo] [--force] [--dry-run]

  (kein Arg)   alle Repos aus der Registry + unregistrierte auf Disk
  repo         nur dieses eine Repo
  --force      bestehende project-facts.md überschreiben
  --dry-run    NUR anzeigen, was generiert/verteilt würde — KEIN Schreiben,
               kein mkdir, keine Symlinks (safe gegen versehentliche Fleet-Writes)
  -h, --help   diese Hilfe

Achtung: OHNE --dry-run schreibt ein Lauf real in ALLE Repos unter $GITHUB_DIR.
"""


def main():
    args = sys.argv[1:]
    # --help/-h VOR jeder Registry-/Schreiboperation abfangen: früher fiel ein
    # `--help` mangels Handler auf einen echten Fleet-Vollauf durch (Incident
    # 2026-07-05, ADR-265 #931-Abnahme).
    if "-h" in args or "--help" in args:
        print(USAGE)
        return
    force = "--force" in args
    dry_run = "--dry-run" in args
    target = next((a for a in args if not a.startswith("-")), "")

    registry = load_registry()
    reg_repos = registry.get("repos", {})
    server_cfg = registry.get("server", {})

    print("=== gen_project_facts.py — Master Repo Identifier ===")
    print(f"Registry: {REGISTRY_FILE}")
    print(f"Force:    {force}")
    print(f"Dry-Run:  {dry_run}" + ("  (KEIN Schreiben)" if dry_run else ""))
    print(f"Server:   {server_cfg.get('github_base', GITHUB)}")
    print()

    results = []

    if target:
        entry = reg_repos.get(target, {})
        results.append(gen_facts(target, entry, force=force, dry_run=dry_run))
    else:
        # 1. All repos from registry (with overrides)
        for repo, entry in reg_repos.items():
            results.append(gen_facts(repo, entry or {}, force=force, dry_run=dry_run))

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
                results.append(gen_facts(repo, {}, force=force, dry_run=dry_run))

    print("\n".join(results))
    print(f"\n=== Done ({sum(1 for r in results if r.startswith('✅'))} generated, "
          f"{sum(1 for r in results if 'SKIP' in r)} skipped) ===")
    print("Run with --force to regenerate all.")


if __name__ == "__main__":
    main()

# NOTE: GLOBAL_RULES is defined at module level above — update it there
