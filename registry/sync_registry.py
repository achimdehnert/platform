#!/usr/bin/env python3
"""
registry/sync_registry.py — Sync repos.yaml to all consumers.

Consumers:
  1. tools/repo_checker.py  — REPO_CONFIG dict
  2. dev-hub populate_catalog.py — PLATFORM_DATA list
  3. Stdout JSON (for CI/MCP use)

Usage:
    python registry/sync_registry.py                    # validate + print summary
    python registry/sync_registry.py --check            # exit 1 if out of sync
    python registry/sync_registry.py --json             # print JSON registry
    python registry/sync_registry.py --list             # print all repo names
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REGISTRY_PATH = Path(__file__).parent / "repos.yaml"


def load_registry() -> dict:
    """Load and return registry/repos.yaml."""
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))


def all_systems(registry: dict) -> list[dict]:
    """Flatten all systems across all domains."""
    result = []
    for domain in registry.get("domains", []):
        for system in domain.get("systems", []):
            result.append({**system, "domain": domain["name"]})
    return result


def to_repo_config(registry: dict) -> dict:
    """Generate REPO_CONFIG dict for repo_checker.py."""
    config = {}
    for sys in all_systems(registry):
        repo = sys.get("repo")
        if not repo or sys.get("type") not in ("django", "python"):
            continue
        config[repo] = {
            "type": sys.get("type", "django"),
            "deployed": sys.get("deployed", False),
            "dockerfile": sys.get("dockerfile", "Dockerfile"),
            "compose": sys.get("compose", "docker-compose.prod.yml"),
        }
    return config


def to_platform_data(registry: dict) -> list:
    """Generate PLATFORM_DATA list for populate_catalog.py."""
    domains_out = []
    for domain in registry.get("domains", []):
        systems_out = []
        for sys in domain.get("systems", []):
            comp_type = "service"
            if sys.get("type") == "library":
                comp_type = "library"
            elif sys.get("type") == "mcp_server":
                comp_type = "mcp_server"
            systems_out.append({
                "name": sys["name"],
                "desc": sys.get("description", ""),
                "components": [
                    {
                        "name": f"{sys['name']}-web",
                        "type": comp_type,
                        "lc": sys.get("lifecycle", "experimental"),
                    }
                ],
            })
        domains_out.append({
            "domain": domain["name"],
            "systems": systems_out,
        })
    return domains_out


def check_repo_checker_sync(registry: dict) -> list[str]:
    """Check if repo_checker.py REPO_CONFIG matches registry."""
    checker_path = Path(__file__).parent.parent / "tools" / "repo_checker.py"
    if not checker_path.exists():
        return ["tools/repo_checker.py not found"]

    content = checker_path.read_text(encoding="utf-8")
    expected = to_repo_config(registry)
    missing = []
    for repo in expected:
        if f'"{repo}"' not in content:
            missing.append(f"repo_checker.py missing: {repo}")
    return missing


def check_populate_catalog_sync(registry: dict) -> list[str]:
    """Check if populate_catalog.py PLATFORM_DATA matches registry."""
    catalog_path = (
        Path(__file__).parent.parent.parent
        / "dev-hub"
        / "apps"
        / "catalog"
        / "management"
        / "commands"
        / "populate_catalog.py"
    )
    if not catalog_path.exists():
        return []  # not in this repo, skip

    content = catalog_path.read_text(encoding="utf-8")
    missing = []
    for sys in all_systems(registry):
        name = sys["name"]
        if f'"{name}"' not in content:
            missing.append(f"populate_catalog.py missing system: {name}")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Platform Registry Sync Tool")
    parser.add_argument("--check", action="store_true", help="Exit 1 if out of sync")
    parser.add_argument("--json", action="store_true", help="Print JSON registry")
    parser.add_argument("--list", action="store_true", help="Print all repo names")
    parser.add_argument("--repo-config", action="store_true", help="Print REPO_CONFIG")
    args = parser.parse_args()

    registry = load_registry()
    systems = all_systems(registry)

    if args.json:
        print(json.dumps(registry, indent=2, default=str))
        return 0

    if args.list:
        for sys in systems:
            repo = sys.get("repo", sys["name"])
            deployed = "deployed" if sys.get("deployed") else "not deployed"
            print(f"{repo:25} [{sys.get('lifecycle', '?'):12}] {deployed}")
        return 0

    if args.repo_config:
        config = to_repo_config(registry)
        print(json.dumps(config, indent=2))
        return 0

    # Default: validate sync
    issues = []
    issues.extend(check_repo_checker_sync(registry))
    issues.extend(check_populate_catalog_sync(registry))

    total = len(systems)
    print(f"Registry: {total} systems across {len(registry.get('domains', []))} domains")
    print()
    for domain in registry.get("domains", []):
        print(f"  {domain['name']}")
        for sys in domain.get("systems", []):
            icon = "\u2705" if sys.get("deployed") else "\u26aa"
            print(f"    {icon} {sys['name']:25} [{sys.get('lifecycle', '?')}]")
    print()

    if issues:
        print(f"SYNC ISSUES ({len(issues)}):")
        for issue in issues:
            print(f"  \u26a0\ufe0f  {issue}")
        if args.check:
            return 1
    else:
        print("\u2705 All consumers in sync with registry.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
