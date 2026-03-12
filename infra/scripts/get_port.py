#!/usr/bin/env python3
"""
Gibt den Port für einen Service zurück.
ADR-106 FIX-C — für Deploy-Scripts und CI.

Usage:
    python infra/scripts/get_port.py <service> <staging|prod>

Beispiel:
    python infra/scripts/get_port.py risk-hub staging
    → 8190
"""

import sys
import yaml
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: get_port.py <service> <staging|prod>", file=sys.stderr)
        sys.exit(1)

    service = sys.argv[1]
    env = sys.argv[2]

    if env not in ("staging", "prod"):
        print(
            f"Ungültige Umgebung: {env} (muss staging oder prod sein)",
            file=sys.stderr,
        )
        sys.exit(1)

    ports_file = Path(__file__).parent.parent / "ports.yaml"
    with open(ports_file) as f:
        data = yaml.safe_load(f)

    services = data.get("services", {})
    if service not in services:
        print(f"Unbekannter Service: {service}", file=sys.stderr)
        known = ', '.join(services.keys())
        print(f"Bekannte Services: {known}", file=sys.stderr)
        sys.exit(1)

    port = services[service].get(env)
    if port is None:
        print(f"Kein {env}-Port für {service}", file=sys.stderr)
        sys.exit(1)

    print(port)


if __name__ == "__main__":
    main()
