#!/usr/bin/env python3
"""setup_repo.py — Neues Repo aus Golden-Path-Templates initialisieren.

Kopiert Dockerfile, docker-compose.prod.yml, ci.yml, .env.example
aus docs/templates/ in das Ziel-Repo und ersetzt Platzhalter.

Verwendung:
    python3 scripts/setup_repo.py <repo_name> --port=8015
    python3 scripts/setup_repo.py <repo_name> --port=8015 --dry-run
    python3 scripts/setup_repo.py <repo_name> --port=8015 --settings=config.settings.base

Danach:
    python3 scripts/gen_test_scaffold.py <repo_name>   # Test-Infrastruktur
    python3 scripts/gen_django_app.py <repo_name> <app_name>  # Erste App
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

PLATFORM_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PLATFORM_ROOT / "docs" / "templates"


TEMPLATE_FILES = [
    ("Dockerfile",               "Dockerfile"),
    ("docker-compose.prod.yml",  "docker-compose.prod.yml"),
    ("ci.yml",                   ".github/workflows/ci.yml"),
    (".env.example",             ".env.example"),
    ("cliff.toml",               "cliff.toml"),
    (".importlinter",            ".importlinter"),
    ("renovate.json",            "renovate.json"),  # aus platform root
    (".dockerignore",            ".dockerignore"),
]


def _replace_placeholders(content: str, repo_name: str, port: str,
                           settings_module: str) -> str:
    return (
        content
        .replace("REPO_NAME", repo_name)
        .replace("PORT", port)
        .replace("config.settings.test", settings_module)
    )


def setup_repo(
    repo_dir: Path,
    port: str,
    settings_module: str,
    dry_run: bool = False,
) -> dict[str, str]:
    repo_name = repo_dir.name
    results: dict[str, str] = {}

    for template_name, target_rel in TEMPLATE_FILES:
        # renovate.json liegt im platform-Root, nicht in docs/templates
        if template_name == "renovate.json":
            src = PLATFORM_ROOT / "renovate.json"
            # Für andere Repos: nur das 3-Zeiler-Preset, nicht den vollen Config
            template_content = (
                '{\n'
                '  "$schema": "https://docs.renovatebot.com/renovate-schema.json",\n'
                '  "extends": ["github>achimdehnert/platform//renovate.json"]\n'
                '}\n'
            )
        else:
            src = TEMPLATES_DIR / template_name
            if not src.exists():
                results[target_rel] = "SKIP (Template nicht gefunden)"
                continue
            template_content = src.read_text(encoding="utf-8")

        content = _replace_placeholders(template_content, repo_name, port, settings_module)
        target = repo_dir / target_rel

        if target.exists():
            results[target_rel] = "SKIP (exists)"
            continue

        if dry_run:
            results[target_rel] = "DRY-RUN"
            print(f"\n--- {target_rel} ---")
            print(content[:200] + ("..." if len(content) > 200 else ""))
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        results[target_rel] = "CREATED"

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Neues Repo aus Golden-Path-Templates initialisieren"
    )
    parser.add_argument("repo", help="Repo-Name oder absoluter Pfad")
    parser.add_argument("--port", required=True,
                        help="Prod-Port (z.B. 8015) — muss einmalig in repo-registry.yaml vergeben sein")
    parser.add_argument("--settings", default="config.settings.test",
                        help="DJANGO_SETTINGS_MODULE (default: config.settings.test)")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen")
    args = parser.parse_args()

    repo_dir = Path(args.repo)
    if not repo_dir.is_absolute():
        github_dir = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))
        repo_dir = github_dir / args.repo

    if not repo_dir.exists():
        print(f"❌ Repo nicht gefunden: {repo_dir}")
        return 1

    print(f"\n🚀  Setup: {repo_dir.name} | Port: {args.port} | "
          f"Settings: {args.settings} | {'DRY-RUN' if args.dry_run else 'ERSTELLEN'}\n")

    results = setup_repo(repo_dir, args.port, args.settings, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    for path, status in results.items():
        icon = "✅" if "CREAT" in status or "DRY" in status else "⏭️ "
        print(f"  {icon}  {path:<40} {status}")
    print(f"{'='*60}")

    if not args.dry_run:
        repo_name = repo_dir.name
        print(f"\n📋  Nächste Schritte für '{repo_name}':")
        print(f"  1. Port {args.port} in scripts/repo-registry.yaml eintragen")
        print(f"  2. Nginx-Konfig auf Server: /etc/nginx/sites-available/{repo_name}.conf")
        print(f"  3. python3 scripts/gen_test_scaffold.py {repo_name}")
        print(f"  4. python3 scripts/gen_django_app.py {repo_name} <app_name>")
        print(f"  5. .env.example → .env.prod kopieren + echte Werte setzen")
        print(f"  6. git add -A && git commit -m 'chore: initial setup via setup_repo.py'")
        print(f"  7. git push → CI baut + deployt automatisch")

    return 0


if __name__ == "__main__":
    sys.exit(main())
