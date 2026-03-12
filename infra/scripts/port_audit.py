#!/usr/bin/env python3
"""Port Audit — vergleicht ports.yaml mit dem realen Server-Zustand.

Nutzung:
    # Remote-Audit (Standard):
    python infra/scripts/port_audit.py

    # Mit explizitem Server:
    python infra/scripts/port_audit.py --server root@88.198.191.108

    # Nur ports.yaml auf Duplikate prüfen (offline):
    python infra/scripts/port_audit.py --offline

Exit-Codes:
    0 = keine Konflikte
    1 = Konflikte gefunden
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


PORTS_YAML = Path(__file__).resolve().parent.parent / "ports.yaml"
DEFAULT_SERVER = "root@88.198.191.108"


def load_ports_yaml(path: Path) -> dict:
    """Lade ports.yaml und gib das services-dict zurück."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("services", {})


def check_yaml_duplicates(services: dict) -> list[str]:
    """Prüfe ports.yaml auf doppelt vergebene Ports."""
    port_owners: dict[int, list[str]] = {}
    for name, cfg in services.items():
        if cfg is None:
            continue
        for env in ("staging", "prod"):
            port = cfg.get(env)
            if port and isinstance(port, int):
                key = port
                owner = f"{name}/{env}"
                port_owners.setdefault(key, []).append(owner)

    errors = []
    for port, owners in sorted(port_owners.items()):
        if len(owners) > 1:
            errors.append(
                f"  DUPLIKAT Port {port}: {', '.join(owners)}"
            )
    return errors


def get_server_ports(server: str) -> dict[int, str]:
    """Hole alle Docker-Container-Port-Mappings vom Server."""
    cmd = [
        "ssh", server,
        "docker ps --format '{{.Names}}\\t{{.Ports}}'"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"FEHLER: SSH fehlgeschlagen: {result.stderr.strip()}")
        sys.exit(2)

    port_map: dict[int, str] = {}
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t", 1)
        if len(parts) < 2:
            continue
        container_name, ports_str = parts
        if not ports_str.strip():
            continue
        # Parse: "127.0.0.1:8090->8000/tcp, ..."
        for mapping in ports_str.split(","):
            mapping = mapping.strip()
            if "->" not in mapping:
                continue
            host_part = mapping.split("->")[0]
            # Extract host port (last part after :)
            if ":" in host_part:
                host_port_str = host_part.rsplit(":", 1)[1]
            else:
                host_port_str = host_part
            try:
                host_port = int(host_port_str)
                port_map[host_port] = container_name
            except ValueError:
                continue
    return port_map


def _normalize_name(name: str) -> str:
    """Normalisiere Service-/Container-Name für Vergleich.

    Entfernt Docker-Suffixe, Trennzeichen, und optionales '-hub'.
    """
    n = name.lower().replace("-", "_")
    # Docker-Suffixe entfernen (längste zuerst)
    for suffix in (
        "_staging_web_rls", "_staging_web", "_staging_caddy",
        "_web", "_caddy",
    ):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
            break
    # 'staging_' Präfix entfernen (bei staging-Containern)
    if n.startswith("staging_"):
        n = n[len("staging_"):]
    # '_staging' Suffix entfernen (bei risk_hub_staging etc.)
    if n.endswith("_staging"):
        n = n[: -len("_staging")]
    # Trennzeichen entfernen
    n = n.replace("_", "")
    return n


def _names_match(yaml_name: str, container_name: str) -> bool:
    """Prüfe ob ein ports.yaml-Name zu einem Container-Namen passt.

    Vergleicht normalisierte Namen. Erlaubt auch Match ohne '-hub'-Suffix,
    z.B. 'illustration-hub' matched 'illustration_web'.
    """
    a = _normalize_name(yaml_name)
    b = _normalize_name(container_name)
    if a == b:
        return True
    # Erlaube Match wenn einer '-hub' hat und der andere nicht
    a_no_hub = a.removesuffix("hub")
    b_no_hub = b.removesuffix("hub")
    return a_no_hub == b_no_hub and (a_no_hub != a or b_no_hub != b)


def audit(services: dict, server_ports: dict[int, str]) -> list[str]:
    """Vergleiche ports.yaml mit Server-Zustand."""
    errors = []

    # 1. ports.yaml-Ports die auf dem Server von anderem Service belegt sind
    for name, cfg in services.items():
        if cfg is None:
            continue
        for env in ("staging", "prod"):
            port = cfg.get(env)
            if not port or not isinstance(port, int):
                continue
            if port in server_ports:
                container = server_ports[port]
                if not _names_match(name, container):
                    errors.append(
                        f"  KONFLIKT Port {port}: "
                        f"ports.yaml={name}/{env}, "
                        f"Server={container}"
                    )

    # 2. Server-Ports die nicht in ports.yaml stehen
    yaml_ports: set[int] = set()
    for cfg in services.values():
        if cfg is None:
            continue
        for env in ("staging", "prod"):
            port = cfg.get(env)
            if port and isinstance(port, int):
                yaml_ports.add(port)

    for port, container in sorted(server_ports.items()):
        if port not in yaml_ports and 8000 <= port <= 8199:
            errors.append(
                f"  NICHT REGISTRIERT Port {port}: "
                f"Server={container}, fehlt in ports.yaml"
            )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Port Audit")
    parser.add_argument(
        "--server", default=DEFAULT_SERVER,
        help=f"SSH target (default: {DEFAULT_SERVER})",
    )
    parser.add_argument(
        "--offline", action="store_true",
        help="Nur ports.yaml auf Duplikate prüfen",
    )
    args = parser.parse_args()

    print(f"📋 Lade {PORTS_YAML}")
    services = load_ports_yaml(PORTS_YAML)
    print(f"   {len(services)} Services geladen\n")

    # Check 1: YAML-Duplikate
    print("Check 1: Duplikate in ports.yaml")
    dupes = check_yaml_duplicates(services)
    if dupes:
        print("\n".join(dupes))
    else:
        print("  OK — keine Duplikate\n")

    if args.offline:
        sys.exit(1 if dupes else 0)

    # Check 2: Server-Vergleich
    print(f"Check 2: Server-Abgleich ({args.server})")
    server_ports = get_server_ports(args.server)
    print(f"  {len(server_ports)} Port-Mappings auf Server gefunden\n")

    print("Check 3: Konflikte & fehlende Einträge")
    conflicts = audit(services, server_ports)
    if conflicts:
        print("\n".join(conflicts))
    else:
        print("  OK — keine Konflikte\n")

    all_errors = dupes + conflicts
    if all_errors:
        print(f"\n{'='*50}")
        print(f"ERGEBNIS: {len(all_errors)} Problem(e) gefunden")
        sys.exit(1)
    else:
        print(f"\n{'='*50}")
        print("ERGEBNIS: Alles OK")
        sys.exit(0)


if __name__ == "__main__":
    main()
