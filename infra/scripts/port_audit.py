#!/usr/bin/env python3
"""Port Audit — vergleicht ports.yaml mit Servern.

Nutzung:
    # Prod-Server-Audit (Standard):
    python infra/scripts/port_audit.py

    # Staging-Server-Audit:
    python infra/scripts/port_audit.py --staging

    # Beide Server:
    python infra/scripts/port_audit.py --all-servers

    # Nur ports.yaml auf Duplikate prüfen (offline):
    python infra/scripts/port_audit.py --offline

    # Nächsten freien Port ermitteln:
    python infra/scripts/port_audit.py --next-free

Exit-Codes:
    0 = keine Konflikte
    1 = Konflikte gefunden

Referenz: ADR-106, ADR-157
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


PORTS_YAML = (
    Path(__file__).resolve().parent.parent / "ports.yaml"
)


def load_ports_yaml(path: Path) -> tuple[dict, dict]:
    """Lade ports.yaml, gib (services, servers) zurück."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return (
        data.get("services", {}),
        data.get("servers", {}),
    )


def check_yaml_duplicates(services: dict) -> list[str]:
    """Prüfe ports.yaml auf doppelt vergebene Ports.

    Prod-Ports und Staging-Ports werden GETRENNT geprüft,
    da sie auf verschiedenen Servern laufen (ADR-157).
    """
    prod_owners: dict[int, list[str]] = {}
    staging_owners: dict[int, list[str]] = {}
    for name, cfg in services.items():
        if cfg is None:
            continue
        prod_port = cfg.get("prod")
        if prod_port and isinstance(prod_port, int):
            prod_owners.setdefault(
                prod_port, [],
            ).append(name)
        staging_port = cfg.get("staging")
        if staging_port and isinstance(staging_port, int):
            staging_owners.setdefault(
                staging_port, [],
            ).append(name)

    errors = []
    for port, owners in sorted(prod_owners.items()):
        if len(owners) > 1:
            errors.append(
                f"  DUPLIKAT prod:{port}:"
                f" {', '.join(owners)}"
            )
    for port, owners in sorted(staging_owners.items()):
        if len(owners) > 1:
            errors.append(
                f"  DUPLIKAT staging:{port}:"
                f" {', '.join(owners)}"
            )
    return errors


def find_next_free_port(services: dict) -> int:
    """Berechne den nächsten freien Port."""
    used: set[int] = set()
    for cfg in services.values():
        if cfg is None:
            continue
        for env in ("prod", "staging"):
            port = cfg.get(env)
            if port and isinstance(port, int):
                used.add(port)
    if not used:
        return 8001
    candidate = max(used) + 1
    while candidate in used:
        candidate += 1
    return candidate


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


def audit_server(
    services: dict,
    server_ssh: str,
    env: str,
) -> list[str]:
    """Audit eines Servers gegen ports.yaml."""
    print(f"  Verbinde zu {server_ssh}...")
    server_ports = get_server_ports(server_ssh)
    print(
        f"  {len(server_ports)} Port-Mappings"
        " gefunden\n",
    )
    return audit(services, server_ports)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Port Audit (ADR-106, ADR-157)",
    )
    parser.add_argument(
        "--server",
        help="SSH target (überschreibt ports.yaml)",
    )
    parser.add_argument(
        "--staging", action="store_true",
        help="Staging-Server prüfen",
    )
    parser.add_argument(
        "--all-servers", action="store_true",
        help="Beide Server prüfen",
    )
    parser.add_argument(
        "--offline", action="store_true",
        help="Nur ports.yaml auf Duplikate prüfen",
    )
    parser.add_argument(
        "--next-free", action="store_true",
        help="Nächsten freien Port ausgeben",
    )
    args = parser.parse_args()

    services, servers = load_ports_yaml(PORTS_YAML)
    print(f"Lade {PORTS_YAML.name}")
    print(f"  {len(services)} Services geladen")

    # --next-free: nur Port ausgeben und exit
    if args.next_free:
        nfp = find_next_free_port(services)
        print(f"\nNächster freier Port: {nfp}")
        sys.exit(0)

    # Check 1: YAML-Duplikate
    print("\nCheck 1: Duplikate in ports.yaml")
    dupes = check_yaml_duplicates(services)
    if dupes:
        print("\n".join(dupes))
    else:
        print("  OK — keine Duplikate\n")

    if args.offline:
        sys.exit(1 if dupes else 0)

    # Determine which servers to audit
    targets: list[tuple[str, str]] = []
    if args.server:
        targets.append((args.server, "custom"))
    elif args.all_servers:
        for env, cfg in servers.items():
            if cfg and cfg.get("ssh"):
                targets.append((cfg["ssh"], env))
    elif args.staging:
        stg = servers.get("staging", {})
        ssh = stg.get("ssh") if stg else None
        if ssh:
            targets.append((ssh, "staging"))
        else:
            print("ERROR: Kein staging-Server")
            sys.exit(2)
    else:
        prod = servers.get("prod", {})
        ssh = prod.get("ssh") if prod else None
        if ssh:
            targets.append((ssh, "prod"))
        else:
            targets.append(
                ("root@88.198.191.108", "prod"),
            )

    all_errors = list(dupes)
    for ssh_target, env in targets:
        print(
            f"Check: Server-Abgleich"
            f" [{env}] ({ssh_target})"
        )
        conflicts = audit_server(
            services, ssh_target, env,
        )
        if conflicts:
            print("\n".join(conflicts))
        else:
            print("  OK — keine Konflikte\n")
        all_errors.extend(conflicts)

    if all_errors:
        print(f"\n{'='*50}")
        print(
            f"ERGEBNIS:"
            f" {len(all_errors)} Problem(e)"
        )
        sys.exit(1)
    else:
        print(f"\n{'='*50}")
        print("ERGEBNIS: Alles OK")
        sys.exit(0)


if __name__ == "__main__":
    main()
