#!/usr/bin/env python3
"""Abgleich Registry ↔ Live-Zustand (KONZ-platform-015 Nachtrag 2026-07-10, Hauptmaßnahme).

Vergleicht die deklarierte Topologie (registry/canonical.yaml + infra/ports.yaml)
mit dem realen Zustand des Prod-Hosts (laufende Container, publizierte Ports,
nginx-vhosts, DNS-Auflösung) und zählt Abweichungen — die Drift-Kennzahl,
die im KONZ-015-Kill-Gate steht.

Checks:
  C1 port_mismatch        deklarierter Prod-Port ≠ real publizierter Port des Containers
  C2 container_missing    deklarierter Container läuft nicht (nur bei rich.deployed=true)
  C3 dns_unresolved       deklarierte prod_url löst im DNS nicht auf
  C4 port_unregistered    real publizierter Host-Port ohne ports.yaml-Eintrag
  C5 duplicate_port       derselbe Prod-Port mehrfach in ports.yaml deklariert

Baseline: infra/reconcile-baseline.yaml — bekannte, triagierte Abweichungen mit
PFLICHT-Feldern owner + expires_at (E2-Waiver-Muster aus KONZ-015 / ADR-264 D1:
ohne Ablaufdatum → Fehler; abgelaufen → Fehler). Baseline-Treffer werden
unterdrückt, aber separat gezählt.

Exit-Codes (⚠️ run-conclusion ≠ Tool-Health, siehe CC-Memory):
  0 = keine neue Drift (Baseline-Treffer erlaubt)
  1 = NEUE Drift gefunden — das ist ein FUND-Signal, kein Tool-Fehler
  2 = Tool-/Konfigurationsfehler (Baseline ungültig, Host unerreichbar, ...)

Aufruf:
  python3 tools/reconcile_registry_live.py                  # lokal auf dem Prod-Host (Runner)
  python3 tools/reconcile_registry_live.py --ssh root@HOST  # remote von dev aus
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "infra" / "reconcile-baseline.yaml"

# Host-Ports, die bewusst außerhalb der Service-Registry leben (Infra-Stacks
# mit eigener Verwaltung). Bewusst kurz — alles andere gehört in ports.yaml
# oder in die Baseline (mit Ablaufdatum), nicht hierher.
INFRA_PORT_RANGES = [
    (3000, 3199),   # Infrastructure UIs (Grafana, Outline, Uptime-Kuma)
    (4000, 4099),   # Finance-Infra
    (5432, 5499),   # PostgreSQL
    (6379, 6399),   # Redis
    (9000, 9099),   # Auth + Object Storage (Authentik, MinIO)
    (19000, 19999), # Staging-Range (ADR-210 R4) — Staging-Host separat, hier nur Durchreiche
]


def sh(cmd: list[str], ssh: str | None = None) -> str:
    if ssh:
        cmd = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", ssh,
               shlex.join(cmd)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd}: rc={r.returncode} {r.stderr[:200]}")
    return r.stdout


def load_declared() -> tuple[dict, dict]:
    canonical = yaml.safe_load((REPO_ROOT / "registry" / "canonical.yaml").read_text())
    ports = yaml.safe_load((REPO_ROOT / "infra" / "ports.yaml").read_text())
    return canonical.get("repos", {}), ports.get("services", {})


def load_baseline() -> list[dict]:
    if not BASELINE_PATH.exists():
        return []
    data = yaml.safe_load(BASELINE_PATH.read_text()) or {}
    entries = data.get("known_drift", [])
    today = dt.date.today()
    for e in entries:
        for field in ("id", "reason", "owner", "expires_at"):
            if not e.get(field):
                sys.exit(f"BASELINE-FEHLER: Eintrag ohne Pflichtfeld '{field}': {e} "
                         "(E2-Waiver-Muster: owner + expires_at sind Pflicht)")
        expires = dt.date.fromisoformat(str(e["expires_at"]))
        if expires < today:
            sys.exit(f"BASELINE-FEHLER: Eintrag '{e['id']}' ist am {expires} abgelaufen "
                     "— fail-closed: verlängern (bewusst, mit Grund) oder Drift beheben.")
    return entries


def live_containers(ssh: str | None) -> dict[str, list[int]]:
    """container_name -> [publizierte Host-Ports]"""
    out = sh(["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"], ssh)
    result: dict[str, list[int]] = {}
    for line in out.strip().splitlines():
        name, _, ports = line.partition("\t")
        host_ports = [int(m) for m in re.findall(r"(?:127\.0\.0\.1|0\.0\.0\.0):(\d+)->", ports)]
        result[name] = sorted(set(host_ports))
    return result


def live_dns(domain: str, ssh: str | None) -> bool:
    try:
        sh(["getent", "hosts", domain], ssh)
        return True
    except RuntimeError:
        return False


def in_infra_range(port: int) -> bool:
    return any(lo <= port <= hi for lo, hi in INFRA_PORT_RANGES)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ssh", default=None, help="root@HOST für Remote-Lauf (default: lokal)")
    ap.add_argument("--skip-dns", action="store_true", help="C3 überspringen (z.B. Host ohne Resolver)")
    args = ap.parse_args()

    canonical, ports_decl = load_declared()
    baseline = load_baseline()
    baseline_ids = {e["id"] for e in baseline}

    try:
        containers = live_containers(args.ssh)
    except RuntimeError as e:
        print(f"TOOL-FEHLER: Live-Zustand nicht lesbar: {e}", file=sys.stderr)
        return 2

    drift: list[tuple[str, str]] = []   # (drift_id, beschreibung)

    # C5: doppelte Port-Deklaration — prod UND staging getrennt (das bekannte
    # 8099-Duplikat risk-hub/tax-hub lag auf staging, nicht prod)
    for env in ("prod", "staging"):
        seen: dict[int, str] = {}
        for svc, cfg in ports_decl.items():
            p = cfg.get(env)
            if not isinstance(p, int):
                continue
            if p in seen:
                drift.append((f"C5:{env}:{p}", f"{env}-Port {p} doppelt deklariert: {seen[p]} + {svc}"))
            seen[p] = svc

    # C1 + C2 je deklariertem Service
    for svc, cfg in ports_decl.items():
        cname, p = cfg.get("container_name"), cfg.get("prod")
        if not cname or not isinstance(p, int):
            continue
        rich = canonical.get(svc, {}).get("rich", {})
        deployed = rich.get("deployed") is True
        if cname in containers:
            live_ports = containers[cname]
            if live_ports and p not in live_ports:
                drift.append((f"C1:{svc}", f"{svc}: deklariert {p}, Container {cname} publiziert {live_ports}"))
        elif deployed:
            drift.append((f"C2:{svc}", f"{svc}: rich.deployed=true, aber Container {cname} läuft nicht"))

    # C3: DNS je deklarierter prod_url (flat), nur für deployte Services
    if not args.skip_dns:
        for repo, entry in canonical.items():
            url = entry.get("flat", {}).get("prod_url")
            deployed = entry.get("rich", {}).get("deployed") is True
            if url and deployed and not live_dns(url, args.ssh):
                drift.append((f"C3:{repo}", f"{repo}: prod_url {url} löst nicht auf (NXDOMAIN)"))

    # C4: live publizierter Port ohne Deklaration
    declared_ports = {cfg.get("prod") for cfg in ports_decl.values()} \
                   | {cfg.get("staging") for cfg in ports_decl.values()} \
                   | {cfg.get("dev") for cfg in ports_decl.values()}
    for cname, live_ports in containers.items():
        for p in live_ports:
            if p not in declared_ports and not in_infra_range(p):
                drift.append((f"C4:{p}", f"Port {p} ({cname}) publiziert, aber in ports.yaml unbekannt"))

    new = [(i, d) for i, d in drift if i not in baseline_ids]
    suppressed = [(i, d) for i, d in drift if i in baseline_ids]

    print(f"Drift-Kennzahl: {len(drift)} gesamt = {len(new)} NEU + {len(suppressed)} baselined")
    for i, d in suppressed:
        print(f"  [baseline] {i}  {d}")
    for i, d in new:
        print(f"  [NEU]      {i}  {d}")
    if new:
        print("\n→ Exit 1 = FUND-Signal (neue Drift), kein Tool-Fehler. "
              "Triage: beheben ODER mit owner+expires_at in infra/reconcile-baseline.yaml.")
        return 1
    print("→ Keine neue Drift gegenüber Baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
