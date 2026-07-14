#!/usr/bin/env python3
"""Validate Repo Registry.

Cross-Check GitHub vs canonical.yaml vs ports.yaml.

Stellt sicher, dass ALLE GitHub-Repos in der Registry erfasst sind
und ports.yaml konsistent ist.

Nutzung:
    # Offline (nur Registry vs ports.yaml):
    python infra/scripts/validate_repos.py

    # Mit GitHub-Check (braucht GITHUB_TOKEN oder gh CLI):
    python infra/scripts/validate_repos.py --github

Exit-Codes:
    0 = alles konsistent
    1 = Inkonsistenzen gefunden
    2 = Datei nicht gefunden

Referenz: ADR-157, ADR-106, ADR-275 (Registry-SSoT = canonical.yaml)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

# ADR-275: registry/canonical.yaml ist die Registry-SSoT. Zugriff über den
# Accessor tools/registry_api.py (ADR-234 §11.1: neuer Code liest die Registry
# über den Accessor, nicht die generierten Views bzw. die retirete
# github_repos.yaml direkt).
sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent.parent / "tools"),
)
import registry_api  # noqa: E402

PORTS_YAML = (
    Path(__file__).resolve().parent.parent / "ports.yaml"
)


def load_ports() -> dict:
    """Load ports.yaml services."""
    if not PORTS_YAML.exists():
        print(
            f"ERROR: {PORTS_YAML} nicht gefunden",
            file=sys.stderr,
        )
        sys.exit(2)
    with open(PORTS_YAML) as f:
        data = yaml.safe_load(f)
    return data.get("services", {})


def get_all_registry_repos() -> dict[str, dict]:
    """Flatten canonical.yaml repos into the shape the checks need.

    ADR-275: Quelle ist registry/canonical.yaml (SSoT) statt der retireten
    github_repos.yaml. Die frühere Sektions-Semantik wird auf lifecycle + type
    abgebildet:
      - Sektion 'archive'      -> ``_archived`` (lifecycle == 'archived')
      - Sektion 'django_apps'  -> ``_type == 'django'``
    ``port_prod`` stammt aus ``flat.port``; einen separaten Staging-Port hält
    canonical bewusst nicht (ports.yaml ist dafür die SSoT) -> es gibt kein
    ``port_staging`` mehr (der frühere port_staging-Cross-Check entfällt).
    """
    canon = registry_api.load_canonical()
    repos: dict[str, dict] = {}
    for name, entry in (canon.get("repos") or {}).items():
        entry = entry or {}
        rich = entry.get("rich") or {}
        flat = entry.get("flat") or {}
        lifecycle = registry_api._lifecycle(entry)
        repos[name] = {
            "github": entry.get("github") or rich.get("github"),
            "description": (
                entry.get("description") or rich.get("description")
            ),
            "deployed": rich.get("deployed", False),
            "port_prod": flat.get("port"),
            "_type": rich.get("type") or flat.get("type"),
            "_lifecycle": lifecycle,
            "_archived": lifecycle == "archived",
        }
    return repos


def get_github_repos() -> set[str]:
    """Get all repo names from GitHub via gh CLI."""
    try:
        result = subprocess.run(
            [
                "gh", "repo", "list",
                "achimdehnert",
                "--limit", "200",
                "--json", "name",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(
                f"  WARN: gh CLI failed: {result.stderr}",
                file=sys.stderr,
            )
            return set()
        data = json.loads(result.stdout)
        return {r["name"] for r in data}
    except FileNotFoundError:
        print(
            "  WARN: gh CLI nicht installiert",
            file=sys.stderr,
        )
        return set()
    except subprocess.TimeoutExpired:
        print(
            "  WARN: gh CLI Timeout",
            file=sys.stderr,
        )
        return set()


def check_ports_consistency(
    registry_repos: dict[str, dict],
    ports: dict,
) -> list[str]:
    """Check ports.yaml vs registry consistency."""
    issues = []

    for svc_name, svc_cfg in ports.items():
        if svc_cfg is None:
            continue
        repo_ref = svc_cfg.get("repo")
        if repo_ref and "/" in repo_ref:
            repo_name = repo_ref.split("/")[1]
        else:
            repo_name = svc_name

        if svc_name not in registry_repos:
            alt = repo_name if repo_name != svc_name else None
            if alt and alt in registry_repos:
                continue
            issues.append(
                f"ports.yaml '{svc_name}'"
                " nicht in Registry"
            )
            continue

        reg = registry_repos[svc_name]
        if reg.get("_archived"):
            issues.append(
                f"'{svc_name}' in ports.yaml"
                " aber als archiviert markiert"
            )

        prod_port = svc_cfg.get("prod")
        reg_prod = reg.get("port_prod")
        if (
            prod_port
            and reg_prod
            and prod_port != reg_prod
        ):
            issues.append(
                f"'{svc_name}' port_prod:"
                f" ports.yaml={prod_port}"
                f" registry={reg_prod}"
            )

    return issues


def check_github_coverage(
    registry_repos: dict[str, dict],
    github_repos: set[str],
) -> list[str]:
    """Check all GitHub repos are in registry."""
    issues = []
    for repo_name in sorted(github_repos):
        if repo_name not in registry_repos:
            issues.append(
                f"GitHub repo '{repo_name}'"
                " nicht in Registry"
            )
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Repo Registry",
    )
    parser.add_argument(
        "--github",
        action="store_true",
        help="GitHub-Repos via gh CLI prüfen",
    )
    args = parser.parse_args()

    registry_repos = get_all_registry_repos()
    ports = load_ports()

    print("=" * 60)
    print("Repo Registry Validation")
    print("=" * 60)

    # Stats (nach type, da canonical keine Sektionen kennt)
    types: dict[str, int] = {}
    for name, cfg in registry_repos.items():
        t = cfg.get("_type") or "unknown"
        types[t] = types.get(t, 0) + 1
    print(
        f"\nRegistry: {len(registry_repos)} Repos"
        " (Quelle: canonical.yaml)"
    )
    for t, count in sorted(types.items()):
        print(f"  type={t}: {count}")
    print(f"ports.yaml: {len(ports)} Services")

    all_issues: list[str] = []

    # Check 1: ports.yaml vs registry
    print("\n--- Check 1: ports.yaml vs Registry ---")
    issues = check_ports_consistency(
        registry_repos, ports,
    )
    all_issues.extend(issues)
    if issues:
        for i in issues:
            print(f"  ⚠ {i}")
    else:
        print("  ✅ Konsistent")

    # Check 2: GitHub coverage
    if args.github:
        print("\n--- Check 2: GitHub vs Registry ---")
        github_repos = get_github_repos()
        if github_repos:
            print(f"  GitHub: {len(github_repos)} Repos")
            issues = check_github_coverage(
                registry_repos, github_repos,
            )
            all_issues.extend(issues)
            if issues:
                for i in issues:
                    print(f"  ⚠ {i}")
            else:
                print("  ✅ Alle GitHub-Repos erfasst")
        else:
            print("  SKIP: GitHub nicht erreichbar")

    # Check 3: Registry internal
    print("\n--- Check 3: Registry-Integrität ---")
    deployed = [
        n for n, c in registry_repos.items()
        if c.get("deployed")
        and c.get("_type") == "django"
    ]
    no_port = [
        n for n in deployed
        if not registry_repos[n].get("port_prod")
    ]
    if no_port:
        for n in no_port:
            msg = f"'{n}' deployed=true aber kein port_prod"
            all_issues.append(msg)
            print(f"  ⚠ {msg}")
    else:
        print("  ✅ Alle deployed Repos haben Ports")

    # Summary
    print("\n" + "=" * 60)
    if all_issues:
        print(
            f"⚠ {len(all_issues)}"
            " Inkonsistenz(en) gefunden"
        )
        sys.exit(1)
    else:
        print("✅ Registry vollständig und konsistent")
    print("=" * 60)


if __name__ == "__main__":
    main()
