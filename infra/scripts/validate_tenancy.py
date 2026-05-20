#!/usr/bin/env python3
"""Tenancy-Mode Registry Lint (ADR-212 Offene Punkte #1, Issue #247).

Prüft registry/repos.yaml auf:
  1. Pflicht-Feld `tenancy_mode` bei allen Systemen
  2. Gültiger Enum-Wert (subdomain | path | header | jwt_claim | none)
  3. Systeme mit `tenancy_mode: subdomain` MÜSSEN `demo_fixture` deklarieren
     (Klausel-1-Pflicht aus ADR-212)

Nutzung:
    python infra/scripts/validate_tenancy.py
    python infra/scripts/validate_tenancy.py --warn-only  # kein Exit 1

Exit-Codes:
    0 = vollständig und gültig
    1 = fehlende oder ungültige Felder
    2 = Datei nicht gefunden
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPOS_YAML = (
    Path(__file__).resolve().parent.parent.parent
    / "registry"
    / "repos.yaml"
)

VALID_TENANCY_MODES = frozenset(
    {"subdomain", "path", "header", "jwt_claim", "none"}
)


def load_repos(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: {path} nicht gefunden", file=sys.stderr)
        sys.exit(2)
    with open(path) as f:
        return yaml.safe_load(f)


def iter_systems(data: dict):
    """Yield (domain_name, system_dict) for every system in repos.yaml."""
    for domain in data.get("domains", []):
        domain_name = domain.get("name", "?")
        for system in domain.get("systems", []):
            yield domain_name, system


def validate(data: dict) -> list[str]:
    """Return list of error strings. Empty list = clean."""
    errors: list[str] = []

    for domain_name, system in iter_systems(data):
        slug = system.get("name", "<unnamed>")
        label = f"{domain_name}/{slug}"

        tenancy_mode = system.get("tenancy_mode")

        # Rule 1: tenancy_mode must be present
        if tenancy_mode is None:
            errors.append(
                f"[MISSING] {label}: 'tenancy_mode' fehlt"
                " — muss einen der Werte"
                f" {sorted(VALID_TENANCY_MODES)} haben"
            )
            continue  # further checks meaningless without the field

        # Rule 2: tenancy_mode must be a valid enum value
        if tenancy_mode not in VALID_TENANCY_MODES:
            errors.append(
                f"[INVALID] {label}: tenancy_mode='{tenancy_mode}'"
                f" ist kein gültiger Wert."
                f" Erlaubt: {sorted(VALID_TENANCY_MODES)}"
            )

        # Rule 3: subdomain systems must declare demo_fixture
        if tenancy_mode == "subdomain":
            demo_fixture = system.get("demo_fixture")
            if demo_fixture is None:
                errors.append(
                    f"[MISSING] {label}: tenancy_mode=subdomain"
                    " erfordert Pflicht-Feld 'demo_fixture: true|false'"
                    " (ADR-212 Klausel 1 — iil-demo-fixture Anbindung)"
                )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate tenancy_mode in registry/repos.yaml"
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Print errors but exit 0 (non-blocking CI mode)",
    )
    args = parser.parse_args()

    data = load_repos(REPOS_YAML)

    # Count systems
    system_count = sum(
        len(d.get("systems", []))
        for d in data.get("domains", [])
    )

    print("=" * 60)
    print("Tenancy-Mode Registry Lint (ADR-212 Issue #247)")
    print("=" * 60)
    print(f"\nSysteme geprüft: {system_count}")

    errors = validate(data)

    if errors:
        print(f"\n⚠  {len(errors)} Fehler gefunden:\n")
        for e in errors:
            print(f"  {e}")
        print()
        if args.warn_only:
            print("--warn-only aktiv: kein Exit 1")
        else:
            print("Lint FAILED — bitte registry/repos.yaml korrigieren.")
            print("=" * 60)
            sys.exit(1)
    else:
        print("\n✅ Alle Systeme haben gültiges 'tenancy_mode'.")
        # Summarize tenancy distribution
        counts: dict[str, int] = {}
        subdomain_systems: list[str] = []
        for _, system in iter_systems(data):
            mode = system.get("tenancy_mode", "MISSING")
            counts[mode] = counts.get(mode, 0) + 1
            if mode == "subdomain":
                subdomain_systems.append(system.get("name", "?"))

        print("\nVerteilung:")
        for mode, count in sorted(counts.items()):
            print(f"  {mode}: {count}")

        if subdomain_systems:
            print(f"\nKlausel-1-Systeme (subdomain): {subdomain_systems}")
            configured = [
                s for _, s in iter_systems(data)
                if s.get("tenancy_mode") == "subdomain"
                and s.get("demo_fixture") is True
            ]
            if len(configured) < len(subdomain_systems):
                pending = len(subdomain_systems) - len(configured)
                print(
                    f"  ⚠  {pending} System(e) mit"
                    " demo_fixture: false"
                    " — Klausel-1-Pflicht noch offen (Issue #248)"
                )

    print("=" * 60)


if __name__ == "__main__":
    main()
