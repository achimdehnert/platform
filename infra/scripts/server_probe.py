#!/usr/bin/env python3
"""
server_probe.py — TCP-basierte Server-Erreichbarkeitsprüfung.

Ersetzt `ping` als Diagnose-Tool, da Hetzner-Server ICMP blockieren.
Prüft TCP-Ports (SSH, HTTP, HTTPS, App-Ports) und SSH-Login.

Nutzung:
    python server_probe.py                    # Prod-Server prüfen
    python server_probe.py --host 88.99.38.75 # Staging prüfen
    python server_probe.py --json             # JSON-Output für CI
    python server_probe.py --with-apps        # Auch App-Ports prüfen

Referenz: Lesson Learned 2026-04-03 — "Ping ist kein valider Diagnose-Weg"
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

PORTS_YAML = Path(__file__).resolve().parent.parent / "ports.yaml"

# Standard-Ports die IMMER geprüft werden
INFRA_PORTS = {
    22: "SSH",
    80: "HTTP",
    443: "HTTPS",
}

# Bekannte Server
SERVERS = {
    "prod": "88.198.191.108",
    "staging": "88.99.38.75",
}

# Bekannte ICMP-Blocking-Server (NICHT ping verwenden)
ICMP_BLOCKED = {"88.198.191.108"}


@dataclass
class ProbeResult:
    host: str
    port: int
    service: str
    status: str  # "open", "filtered", "refused", "error"
    latency_ms: float | None = None
    error: str = ""


@dataclass
class ServerReport:
    host: str
    reachable: bool = False
    ssh_login: bool = False
    ssh_user: str = ""
    uptime: str = ""
    results: list[ProbeResult] = field(default_factory=list)
    icmp_blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "reachable": self.reachable,
            "ssh_login": self.ssh_login,
            "ssh_user": self.ssh_user,
            "uptime": self.uptime,
            "icmp_blocked": self.icmp_blocked,
            "ports": [
                {
                    "port": r.port,
                    "service": r.service,
                    "status": r.status,
                    "latency_ms": r.latency_ms,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


def tcp_probe(host: str, port: int, timeout: float = 3.0) -> ProbeResult:
    """Prüfe ob ein TCP-Port erreichbar ist."""
    service = INFRA_PORTS.get(port, f"port-{port}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        t0 = time.monotonic()
        s.connect((host, port))
        latency = (time.monotonic() - t0) * 1000
        return ProbeResult(host, port, service, "open", latency)
    except socket.timeout:
        return ProbeResult(host, port, service, "filtered")
    except ConnectionRefusedError:
        return ProbeResult(
            host, port, service, "refused",
            error="Port closed but host responds",
        )
    except OSError as e:
        return ProbeResult(host, port, service, "error", error=str(e))
    finally:
        s.close()


def ssh_check(host: str, user: str = "root",
              timeout: int = 10) -> tuple[bool, str]:
    """Prüfe ob SSH-Login funktioniert und hole Uptime."""
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", f"ConnectTimeout={timeout}",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=accept-new",
                f"{user}@{host}",
                "uptime",
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()[:200]
    except subprocess.TimeoutExpired:
        return False, "SSH timeout"
    except FileNotFoundError:
        return False, "SSH client not found"


def load_app_ports(host: str) -> dict[int, str]:
    """Lade App-Ports aus ports.yaml für den gegebenen Host."""
    if not PORTS_YAML.exists():
        return {}
    try:
        import yaml

        data = yaml.safe_load(PORTS_YAML.read_text())
    except ImportError:
        return {}

    ports: dict[int, str] = {}
    is_prod = host == SERVERS.get("prod")
    is_staging = host == SERVERS.get("staging")

    for name, cfg in data.get("services", {}).items():
        if not cfg:
            continue
        port = None
        if is_prod:
            port = cfg.get("prod")
        elif is_staging:
            port = cfg.get("staging")
        if port:
            ports[int(port)] = name
    return ports


def probe_server(
    host: str,
    user: str = "root",
    with_apps: bool = False,
    timeout: float = 3.0,
) -> ServerReport:
    """Vollständige Server-Diagnose via TCP-Probes."""
    report = ServerReport(host=host)
    report.icmp_blocked = host in ICMP_BLOCKED

    # 1. Infra-Ports prüfen (SSH, HTTP, HTTPS)
    for port, service in sorted(INFRA_PORTS.items()):
        result = tcp_probe(host, port, timeout)
        result.service = service
        report.results.append(result)

    # Server erreichbar wenn mindestens SSH ODER HTTP offen
    open_ports = {r.port for r in report.results if r.status == "open"}
    report.reachable = bool(open_ports & {22, 80, 443})

    # 2. SSH-Login prüfen (nur wenn Port 22 offen)
    if 22 in open_ports:
        ok, info = ssh_check(host, user)
        report.ssh_login = ok
        report.ssh_user = user
        report.uptime = info if ok else ""

    # 3. App-Ports prüfen (optional)
    if with_apps:
        app_ports = load_app_ports(host)
        for port, name in sorted(app_ports.items()):
            if port in INFRA_PORTS:
                continue
            result = tcp_probe(host, port, timeout)
            result.service = name
            report.results.append(result)

    return report


def print_report(report: ServerReport) -> None:
    """Human-readable Report ausgeben."""
    print(f"\n{'=' * 60}")
    print(f"  Server Probe: {report.host}")
    print(f"{'=' * 60}")

    if report.icmp_blocked:
        print("  ⚠️  ICMP blocked — ping funktioniert NICHT (normal)")

    print()
    for r in report.results:
        if r.status == "open":
            icon = "✅"
            detail = f"{r.latency_ms:.0f}ms" if r.latency_ms else ""
        elif r.status == "refused":
            icon = "🟡"
            detail = "refused (Host antwortet, Port zu)"
        elif r.status == "filtered":
            icon = "🔴"
            detail = "filtered (Firewall)"
        else:
            icon = "❌"
            detail = r.error
        print(f"  {icon} {r.port:>5} {r.service:<25} {detail}")

    print()
    if report.ssh_login:
        print(f"  🔑 SSH-Login OK ({report.ssh_user}@{report.host})")
        print(f"  ⏱  Uptime: {report.uptime}")
    elif report.reachable:
        print("  🔑 SSH-Login FEHLGESCHLAGEN (Port offen, Auth-Problem?)")
    else:
        print("  ❌ Server NICHT ERREICHBAR (kein offener Port)")

    # Zusammenfassung
    open_count = sum(1 for r in report.results if r.status == "open")
    total = len(report.results)
    print(f"\n  Ergebnis: {open_count}/{total} Ports offen", end="")
    if report.reachable:
        print(" — Server erreichbar ✅")
    else:
        print(" — Server NICHT erreichbar ❌")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TCP-basierte Server-Erreichbarkeitsprüfung",
    )
    parser.add_argument(
        "--host",
        default=SERVERS["prod"],
        help=f"Server-IP (default: {SERVERS['prod']})",
    )
    parser.add_argument(
        "--user", default="root",
        help="SSH-User (default: root)",
    )
    parser.add_argument(
        "--with-apps", action="store_true",
        help="Auch App-Ports aus ports.yaml prüfen",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Alle bekannten Server prüfen",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_out",
        help="JSON-Output",
    )
    parser.add_argument(
        "--timeout", type=float, default=3.0,
        help="TCP-Timeout in Sekunden (default: 3)",
    )
    args = parser.parse_args()

    hosts = (
        list(SERVERS.values()) if args.all
        else [SERVERS.get(args.host, args.host)]
    )

    reports = []
    for host in hosts:
        report = probe_server(
            host, args.user, args.with_apps, args.timeout,
        )
        reports.append(report)

    if args.json_out:
        out = (
            reports[0].to_dict() if len(reports) == 1
            else [r.to_dict() for r in reports]
        )
        print(json.dumps(out, indent=2))
    else:
        for report in reports:
            print_report(report)

    # Exit-Code: 0 wenn alle Server erreichbar
    return 0 if all(r.reachable for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
