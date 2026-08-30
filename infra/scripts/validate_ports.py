#!/usr/bin/env python3
"""
Validiert infra/ports.yaml auf Duplikate und Schema-Konformität.
ADR-106 FIX-C — wird in CI ausgeführt bei jedem PR der ports.yaml ändert.

Usage:
    python infra/scripts/validate_ports.py
"""

import sys
import yaml
from pathlib import Path
from collections import defaultdict


def load_ports(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def validate(data: dict) -> list[str]:
    errors = []
    port_usage: dict[int, list[str]] = defaultdict(list)

    services = data.get("services", {})

    for name, config in services.items():
        if not isinstance(config, dict):
            errors.append(f"{name}: Kein dict")
            continue

        required = ("staging", "domain_staging", "domain_prod", "repo")
        for field in required:
            if field not in config:
                errors.append(f"{name}: Pflichtfeld '{field}' fehlt")

        staging_port = config.get("staging")
        if staging_port is not None:
            if not isinstance(staging_port, int):
                errors.append(
                    f"{name}: staging-Port muss int sein, ist: {type(staging_port)}"
                )
            elif not (1024 <= staging_port <= 9999):
                errors.append(
                    f"{name}: staging-Port {staging_port} außerhalb Range 1024–9999"
                )
            else:
                port_usage[staging_port].append(f"{name}/staging")

        prod_port = config.get("prod")
        if prod_port is not None:
            if not isinstance(prod_port, int):
                errors.append(f"{name}: prod-Port muss int sein")
            else:
                port_usage[prod_port].append(f"{name}/prod")

    for port, users in port_usage.items():
        if len(users) > 1:
            errors.append(f"Port-Kollision {port}: {', '.join(users)}")

    return errors


def validate_servers(data: dict, hosts: dict) -> list[str]:
    """`servers:` ist eine Projektion von hosts.yaml — hier wird sie nachgerechnet.

    KONZ-054 §12 S1 (2026-08-30): der Block deckte 3 von 8 Knoten, und `staging`
    meinte hier eine andere Maschine als in hosts.yaml. Eine Projektion ohne
    Rueckpruefung ist eine zweite Wahrheit; mit ihr ist sie ein Cache.
    """
    errors: list[str] = []
    knoten = (hosts or {}).get("hosts", {}) or {}
    for env, s in (data.get("servers", {}) or {}).items():
        if not isinstance(s, dict):
            errors.append(f"servers.{env}: kein dict")
            continue
        host = s.get("host")
        if not host:
            errors.append(
                f"servers.{env}: 'host' fehlt — muss auf einen Knoten in hosts.yaml zeigen"
            )
            continue
        k = knoten.get(host)
        if not isinstance(k, dict):
            errors.append(
                f"servers.{env}: host '{host}' steht nicht in hosts.yaml ({', '.join(sorted(knoten))})"
            )
            continue
        if str(s.get("ip", "")) != str(k.get("ip", "")):
            errors.append(
                f"servers.{env}: ip {s.get('ip')} != hosts.yaml {host}.ip {k.get('ip')}"
            )
        if s.get("ssh") and k.get("ssh") and str(s["ssh"]) != str(k["ssh"]):
            errors.append(
                f"servers.{env}: ssh {s['ssh']} != hosts.yaml {host}.ssh {k['ssh']}"
            )
    return errors


def main():
    ports_file = Path(__file__).parent.parent / "ports.yaml"
    data = load_ports(ports_file)
    errors = validate(data)

    if errors:
        print("❌ Validierungs-Fehler in ports.yaml:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    services = data.get("services", {})
    count = len(services)
    print(f"✅ ports.yaml valide — {count} Services, keine Port-Kollisionen")
    print()
    print(f"{'Service':<20} {'Staging':>8} {'Prod':>8}  Staging-URL")
    print("-" * 70)
    for name, cfg in services.items():
        staging = cfg.get("staging") or "-"
        prod = cfg.get("prod") or "-"
        domain = cfg.get("domain_staging") or "-"
        print(f"{name:<20} {str(staging):>8} {str(prod):>8}  {domain}")
    sys.exit(0)


if __name__ == "__main__":
    main()
