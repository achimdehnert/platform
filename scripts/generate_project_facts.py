#!/usr/bin/env python3
"""Generate project-facts.md for a Django repo.

Reads DJANGO_SETTINGS_MODULE from .env.prod (or REPOS table fallback),
calls django.setup() in a subprocess, and writes
.windsurf/rules/project-facts.md into the target repo.

Usage:
    # Single repo (run from anywhere):
    python platform/scripts/generate_project_facts.py /path/to/repo

    # All platform repos at once:
    python platform/scripts/generate_project_facts.py --all

    # Explicit settings module override:
    python platform/scripts/generate_project_facts.py /path/to/repo --settings config.settings.base
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path


REPOS: dict[str, dict] = {
    "travel-beat": {
        "settings": "config.settings.base",
        "container": "travel_beat_web",
        "port": 8089,
        "dockerfile": "docker/Dockerfile",
        "has_htmx": True,
        "has_multi_tenancy": False,
    },
    "bfagent": {
        "settings": "config.settings",
        "container": "bfagent_web",
        "port": 8080,
        "dockerfile": "docker/app/Dockerfile",
        "has_htmx": False,
        "has_multi_tenancy": False,
    },
    "weltenhub": {
        "settings": "config.settings.base",
        "container": "weltenhub_web",
        "port": 8091,
        "dockerfile": "docker/Dockerfile",
        "has_htmx": True,
        "has_multi_tenancy": True,
    },
    "risk-hub": {
        "settings": "config.settings",
        "container": "risk_hub_web",
        "port": 8090,
        "dockerfile": "docker/Dockerfile",
        "has_htmx": True,
        "has_multi_tenancy": True,
    },
    "trading-hub": {
        "settings": "trading_hub.django.settings",
        "container": "trading_hub_web",
        "port": 8092,
        "dockerfile": "docker/Dockerfile",
        "has_htmx": False,
        "has_multi_tenancy": False,
    },
    "pptx-hub": {
        "settings": "config.settings.base",
        "container": "pptx_hub_web",
        "port": 8093,
        "dockerfile": "docker/Dockerfile",
        "has_htmx": False,
        "has_multi_tenancy": False,
    },
    "cad-hub": {
        "settings": "config.settings.base",
        "container": "cad_hub_web",
        "port": 8094,
        "dockerfile": "docker/Dockerfile",
        "has_htmx": False,
        "has_multi_tenancy": False,
    },
}

_DJANGO_INTROSPECT_SCRIPT = """
import django
django.setup()
from django.conf import settings
import json

facts = {
    "ROOT_URLCONF": getattr(settings, "ROOT_URLCONF", ""),
    "WSGI_APPLICATION": getattr(settings, "WSGI_APPLICATION", ""),
    "AUTH_USER_MODEL": getattr(settings, "AUTH_USER_MODEL", "auth.User"),
    "DEFAULT_AUTO_FIELD": str(getattr(settings, "DEFAULT_AUTO_FIELD", "")),
    "INSTALLED_APPS": list(getattr(settings, "INSTALLED_APPS", [])),
    "MIDDLEWARE": list(getattr(settings, "MIDDLEWARE", [])),
}
print(json.dumps(facts))
"""


def _detect_settings_module(repo_path: Path, override: str | None = None) -> str:
    """Return settings module: override > .env.prod > REPOS table > fallback."""
    if override:
        return override
    env_prod = repo_path / ".env.prod"
    if env_prod.exists():
        for line in env_prod.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DJANGO_SETTINGS_MODULE="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    repo_name = repo_path.name
    return REPOS.get(repo_name, {}).get("settings", "config.settings")


def _build_pythonpath(repo_path: Path) -> str:
    """Detect src/ prefix (risk-hub pattern) and build PYTHONPATH."""
    src = repo_path / "src"
    base = str(src) if src.exists() else str(repo_path)
    existing = os.environ.get("PYTHONPATH", "")
    return base + (":" + existing if existing else "")


def _run_django_introspect(repo_path: Path, settings_module: str) -> dict:
    """Run django.setup() in subprocess and return settings dict."""
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = settings_module
    env["PYTHONPATH"] = _build_pythonpath(repo_path)

    result = subprocess.run(
        [sys.executable, "-c", _DJANGO_INTROSPECT_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(repo_path),
    )
    if result.returncode != 0:
        print(
            f"  WARNING: django.setup() failed for {settings_module}:\n"
            f"  {result.stderr[:400].strip()}",
            file=sys.stderr,
        )
        return {}
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        print("  WARNING: could not parse django introspect output", file=sys.stderr)
        return {}


def _detect_htmx(facts: dict) -> tuple[bool, str]:
    """Return (has_htmx, detection_method)."""
    apps = facts.get("INSTALLED_APPS", [])
    middleware = facts.get("MIDDLEWARE", [])
    if "django_htmx" in apps or any("HtmxMiddleware" in m for m in middleware):
        return True, "request.htmx"
    if any("htmx" in a.lower() for a in apps):
        return True, "request.headers.get('HX-Request') == 'true'"
    return False, "N/A"


def _detect_apps_prefix(facts: dict) -> str:
    """Detect app prefix like 'apps.' from INSTALLED_APPS."""
    skip = {"django", "rest_framework", "allauth", "crispy", "django_htmx", "config"}
    apps = [
        a for a in facts.get("INSTALLED_APPS", [])
        if "." in a and not any(a.startswith(s) for s in skip)
    ]
    prefixes = [a.split(".")[0] for a in apps]
    if not prefixes:
        return ""
    most_common = max(set(prefixes), key=prefixes.count)
    return f"{most_common}." if most_common not in skip else ""


def _detect_settings_layout(settings_module: str) -> str:
    """Classify settings layout from module path."""
    parts = settings_module.split(".")
    if len(parts) >= 3:
        return "split (base/development/production/test)"
    if parts[-1] in ("settings",) and len(parts) == 2:
        return "single-file"
    if len(parts) == 1:
        return "flat"
    return "custom"


def _generate_facts_md(repo_path: Path, settings_override: str | None = None) -> str:
    """Return full project-facts.md content for a repo."""
    repo_name = repo_path.name
    settings_module = _detect_settings_module(repo_path, settings_override)
    settings_layout = _detect_settings_layout(settings_module)

    print(f"  Settings: {settings_module}")
    facts = _run_django_introspect(repo_path, settings_module)

    if not facts:
        return (
            f"# {repo_name} — Project Facts\n\n"
            f"> AUTO-GENERATED — django.setup() failed, fill manually.\n"
            f"> Settings attempted: `{settings_module}`\n"
        )

    has_htmx, htmx_method = _detect_htmx(facts)
    apps_prefix = _detect_apps_prefix(facts)
    repo_meta = REPOS.get(repo_name, {})
    apps = facts.get("INSTALLED_APPS", [])
    has_tenancy = (
        any("tenant" in a.lower() for a in apps)
        or repo_meta.get("has_multi_tenancy", False)
    )

    today = datetime.date.today().isoformat()
    lines: list[str] = [
        f"# {repo_name} — Project Facts",
        "",
        "> AUTO-GENERATED by platform/scripts/generate_project_facts.py — DO NOT EDIT MANUALLY",
        f"> Generated: {today}  |  Settings: `{settings_module}`",
        "",
        "## Settings & Paths",
        f"- **Settings module**: `{settings_module}` ({settings_layout})",
        f"- **ROOT_URLCONF**: `{facts.get('ROOT_URLCONF', 'UNKNOWN')}`",
        f"- **WSGI_APPLICATION**: `{facts.get('WSGI_APPLICATION', 'UNKNOWN')}`",
    ]
    if apps_prefix:
        lines.append(
            f"- **Apps prefix**: `{apps_prefix}`"
            f" (e.g. `{apps_prefix}core`, `{apps_prefix}accounts`)"
        )

    lines += ["", "## Authentication"]
    lines.append(f"- **AUTH_USER_MODEL**: `{facts.get('AUTH_USER_MODEL', 'auth.User')}`")
    if "allauth" in str(apps):
        lines.append("- Framework: django-allauth")
    elif "rest_framework_simplejwt" in str(apps):
        lines.append("- Framework: JWT (simplejwt)")

    lines += ["", "## HTMX"]
    if has_htmx:
        if "request.htmx" in htmx_method:
            lines.append(f"- **Detection**: `{htmx_method}` (django_htmx installed)")
            lines.append(
                "- NEVER use `request.headers.get('HX-Request')`"
                " → use `request.htmx` only"
            )
        else:
            lines.append(
                f"- **Detection**: `{htmx_method}`"
                " (raw headers — django_htmx NOT installed)"
            )
            lines.append(
                "- NEVER use `request.htmx`"
                " → AttributeError (django_htmx not installed)"
            )
        lines.append("- **Im Zweifel**: project-facts.md ist massgeblich")
    else:
        lines.append("- **HTMX**: NOT USED in this repo")
        lines.append("- NEVER add HTMX attributes unless explicitly instructed")
        lines.append("- NEVER use `request.htmx` → AttributeError")

    lines += ["", "## Multi-Tenancy"]
    if has_tenancy:
        lines.append("- **Multi-tenancy**: YES")
        lines.append(
            "- Every user-data model MUST have"
            " `tenant_id = UUIDField(db_index=True)`"
        )
        lines.append("- ALWAYS use `org.tenant_id` (NOT `org.id`) for filtering")
        lines.append(
            "- Middleware sets `request.tenant_id` from subdomain resolution"
        )
    else:
        lines.append("- **Multi-tenancy**: NO")

    lines += ["", "## Docker & Deployment"]
    dockerfile = repo_meta.get("dockerfile", "docker/Dockerfile")
    container = repo_meta.get("container", f"{repo_name.replace('-', '_')}_web")
    port = repo_meta.get("port", "808x")
    lines += [
        f"- **Dockerfile**: `{dockerfile}`",
        "- **Compose**: `docker-compose.prod.yml`",
        f"- **Container**: `{container}` (port {port})",
        f"- **Registry**: `ghcr.io/achimdehnert/{repo_name}/{repo_name}-web:latest`",
        "- **Health**: `/livez/` (liveness) + `/healthz/` (readiness)",
        "- **env_file**: `.env.prod` (NEVER `${VAR}` interpolation in compose)",
    ]

    lines += ["", "## Database"]
    auto_field = facts.get("DEFAULT_AUTO_FIELD", "")
    lines.append(
        f"- **DEFAULT_AUTO_FIELD**: `{auto_field or 'BigAutoField (default)'}`"
        " → integer PKs"
    )
    lines.append("- NEVER use `UUIDField(primary_key=True)`")
    lines.append("- FK: `on_delete=PROTECT` unless explicitly justified")
    lines.append("- No `JSONField()` for structured data — use lookup tables")

    return "\n".join(lines) + "\n"


def process_repo(repo_path: Path, settings_override: str | None = None) -> bool:
    """Generate project-facts.md for a single repo. Returns True on success."""
    if not repo_path.exists():
        print(f"ERROR: {repo_path} does not exist", file=sys.stderr)
        return False

    print(f"\n=== {repo_path.name} ===")
    content = _generate_facts_md(repo_path, settings_override)

    out_dir = repo_path / ".windsurf" / "rules"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "project-facts.md"
    out_file.write_text(content, encoding="utf-8")
    print(f"  Written: {out_file}")

    if "UNKNOWN" in content:
        print("  WARNING: Some fields show UNKNOWN — verify django.setup() succeeded")
        return False
    if "django.setup() failed" in content:
        print("  WARNING: django.setup() failed — fill project-facts.md manually")
        return False

    print("  OK")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate .windsurf/rules/project-facts.md"
            " for Django repos (ADR-094 Layer 0)"
        )
    )
    parser.add_argument(
        "repos",
        nargs="*",
        help="Repo paths to process. Omit to use --all.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all known platform repos relative to this script's grandparent dir.",
    )
    parser.add_argument(
        "--settings",
        default=None,
        help="Override DJANGO_SETTINGS_MODULE (only with single repo).",
    )
    args = parser.parse_args()

    if args.all:
        base = Path(__file__).resolve().parent.parent.parent
        repo_paths = [base / name for name in REPOS]
    elif args.repos:
        repo_paths = [Path(p).resolve() for p in args.repos]
    else:
        repo_paths = [Path.cwd()]

    if args.settings and len(repo_paths) > 1:
        print(
            "ERROR: --settings can only be used with a single repo path",
            file=sys.stderr,
        )
        sys.exit(1)

    results = []
    for repo_path in repo_paths:
        ok = process_repo(repo_path, args.settings)
        results.append((repo_path.name, ok))

    print("\n=== Summary ===")
    ok_count = sum(1 for _, ok in results if ok)
    for name, ok in results:
        status = "OK" if ok else "WARN"
        print(f"  [{status}] {name}")
    print(f"\n{ok_count}/{len(results)} repos processed successfully.")
    if ok_count < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
