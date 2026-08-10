#!/usr/bin/env python3
"""Abgleich Registry ↔ Live-Zustand (KONZ-platform-015 Nachtrag 2026-07-10, Hauptmaßnahme).

Vergleicht die deklarierte Topologie (registry/canonical.yaml + infra/ports.yaml)
mit dem realen Zustand des Prod-Hosts (laufende Container, publizierte Ports,
nginx-vhosts, DNS-Auflösung) und zählt Abweichungen — die Drift-Kennzahl,
die im KONZ-015-Kill-Gate steht.

Checks:
  C0 host_unreachable     Nebenhost nicht erreichbar — C1/C2 dort ungeprüft
  C1 port_mismatch        deklarierter Prod-Port ≠ real publizierter Port des Containers
  C2 container_missing    deklarierter Container läuft nicht (nur bei rich.deployed=true)
  C3 dns_unresolved       deklarierte prod_url löst im DNS nicht auf
  C4 port_unregistered    real publizierter Host-Port ohne ports.yaml-Eintrag
  C5 duplicate_port       derselbe Prod-Port mehrfach in ports.yaml deklariert

MEHRERE PROD-HOSTS (2026-08-10, #1876):
Seit dem 2026-07-22 gibt es einen zweiten Prod-Host (`prod-b`), und `ports.yaml`
führt je Dienst ein `prod_host`-Feld. Dieses Werkzeug las es nicht: es inspizierte
NUR den Host, auf dem es lief, und meldete jeden dorthin ausgelagerten Dienst als
"Container läuft nicht". Am 2026-08-10 waren das vier Falschmeldungen (apo-hub,
research-hub, trading-hub, weltenhub) — alle vier liefen einwandfrei, nur eben auf
`prod-b`, unter exakt dem deklarierten Namen.

C1/C2 werden deshalb gegen den ZUSTÄNDIGEN Host geprüft (`prod_host`, Default
`prod`), aufgelöst über `infra/hosts.yaml`. Der Host, auf dem das Werkzeug läuft,
wird lokal gelesen, alle anderen per SSH.

Ist ein Nebenhost nicht erreichbar, werden seine Dienste NICHT als fehlend
gemeldet — das wäre derselbe Fehler in neuer Verkleidung. Stattdessen fällt ein
eigener Befund `C0:<host>`, und C1/C2 werden für diesen Host übersprungen. Die
blinde Stelle bleibt so sichtbar und ist wie jede andere Drift triagierbar
(beheben oder mit owner+expires_at stunden), statt sich als Grün zu tarnen.

Baseline: infra/reconcile-baseline.yaml — bekannte, triagierte Abweichungen mit
PFLICHT-Feldern owner + expires_at (E2-Waiver-Muster aus KONZ-015 / ADR-264 D1:
ohne Ablaufdatum → Fehler; abgelaufen → Fehler). Baseline-Treffer werden
unterdrückt, aber separat gezählt.

Exit-Codes (⚠️ run-conclusion ≠ Tool-Health, siehe CC-Memory):
  0 = keine neue Drift (Baseline-Treffer erlaubt)
  1 = NEUE Drift gefunden — das ist ein FUND-Signal, kein Tool-Fehler
  2 = Tool-/Konfigurationsfehler (Baseline ungültig, Host unerreichbar, ...)

Aufruf:
  python3 tools/reconcile_registry_live.py                  # host-aware (lokal + SSH je prod_host)
  python3 tools/reconcile_registry_live.py --ssh root@HOST  # ALT: alles gegen EINEN Host
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
HOSTS_PATH = REPO_ROOT / "infra" / "hosts.yaml"

#: Dienste ohne `prod_host` in ports.yaml liegen auf dem historischen Einzelhost.
DEFAULT_PROD_HOST = "prod"

# Host-Ports, die bewusst außerhalb der Service-Registry leben (Infra-Stacks
# mit eigener Verwaltung). Bewusst kurz — alles andere gehört in ports.yaml
# oder in die Baseline (mit Ablaufdatum), nicht hierher.
INFRA_PORT_RANGES = [
    (3000, 3199),  # Infrastructure UIs (Grafana, Outline, Uptime-Kuma)
    (4000, 4099),  # Finance-Infra
    (5432, 5499),  # PostgreSQL
    (6379, 6399),  # Redis
    (9000, 9099),  # Auth + Object Storage (Authentik, MinIO)
    (
        19000,
        19999,
    ),  # Staging-Range (ADR-210 R4) — Staging-Host separat, hier nur Durchreiche
]


def sh(cmd: list[str], ssh: str | None = None) -> str:
    if ssh:
        cmd = [
            "ssh",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "BatchMode=yes",
            ssh,
            shlex.join(cmd),
        ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd}: rc={r.returncode} {r.stderr[:200]}")
    return r.stdout


def load_declared() -> tuple[dict, dict]:
    canonical = yaml.safe_load((REPO_ROOT / "registry" / "canonical.yaml").read_text())
    ports = yaml.safe_load((REPO_ROOT / "infra" / "ports.yaml").read_text())
    return canonical.get("repos", {}), ports.get("services", {})


def _knapper_grund(e: Exception) -> str:
    """Nur die Fehlerursache, ohne das komplette argv aus `sh()`.

    `sh()` haengt das ganze Kommando vor die Meldung; in einer Drift-Zeile ist
    das Rauschen, das die eigentliche Ursache ans Zeilenende draengt.
    """
    text = str(e)
    _, sep, rest = text.partition("rc=")
    return (rest.split(" ", 1)[-1] if sep else text).strip()[:120]


def load_hosts() -> dict[str, dict]:
    """`infra/hosts.yaml` → {hostname: {ssh, hostname, cloud_name, ...}}."""
    return (yaml.safe_load(HOSTS_PATH.read_text()) or {}).get("hosts", {})


def lokaler_host(hosts: dict[str, dict]) -> str | None:
    """Welcher Eintrag aus hosts.yaml ist die Maschine, auf der wir laufen?

    Verglichen wird der `hostname` der Maschine gegen die Felder `hostname` und
    `cloud_name`. Beide sind in hosts.yaml gepflegt und beide kommen real vor:
    `prod` meldet `ubuntu-8gb-nbg1-1` (= `hostname`), `prod-b` meldet
    `iilgmbh-prod-b` (= `cloud_name`, `hostname` ist dort nicht gesetzt).

    Kein Treffer (z.B. Lauf von einer Dev-Maschine) ist kein Fehler — dann wird
    JEDER Host per SSH gelesen.
    """
    try:
        eigen = sh(["hostname"]).strip()
    except (RuntimeError, subprocess.SubprocessError, OSError):
        return None
    for name, cfg in hosts.items():
        if eigen in {cfg.get("hostname"), cfg.get("cloud_name")}:
            return name
    return None


def load_baseline() -> list[dict]:
    if not BASELINE_PATH.exists():
        return []
    data = yaml.safe_load(BASELINE_PATH.read_text()) or {}
    entries = data.get("known_drift", [])
    today = dt.date.today()
    for e in entries:
        for field in ("id", "reason", "owner", "expires_at"):
            if not e.get(field):
                sys.exit(
                    f"BASELINE-FEHLER: Eintrag ohne Pflichtfeld '{field}': {e} "
                    "(E2-Waiver-Muster: owner + expires_at sind Pflicht)"
                )
        expires = dt.date.fromisoformat(str(e["expires_at"]))
        if expires < today:
            sys.exit(
                f"BASELINE-FEHLER: Eintrag '{e['id']}' ist am {expires} abgelaufen "
                "— fail-closed: verlängern (bewusst, mit Grund) oder Drift beheben."
            )
    return entries


def live_containers(ssh: str | None) -> dict[str, list[int]]:
    """container_name -> [publizierte Host-Ports]"""
    out = sh(["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"], ssh)
    result: dict[str, list[int]] = {}
    for line in out.strip().splitlines():
        name, _, ports = line.partition("\t")
        host_ports = [
            int(m) for m in re.findall(r"(?:127\.0\.0\.1|0\.0\.0\.0):(\d+)->", ports)
        ]
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
    ap.add_argument(
        "--ssh", default=None, help="root@HOST für Remote-Lauf (default: lokal)"
    )
    ap.add_argument(
        "--skip-dns",
        action="store_true",
        help="C3 überspringen (z.B. Host ohne Resolver)",
    )
    args = ap.parse_args()

    canonical, ports_decl = load_declared()
    baseline = load_baseline()
    baseline_ids = {e["id"] for e in baseline}

    drift: list[tuple[str, str]] = []  # (drift_id, beschreibung)

    # ── Live-Zustand je zuständigem Host einsammeln ────────────────────────
    # `--ssh` bleibt der alte Einzelhost-Modus: alles gegen genau diesen Host.
    # Ohne `--ssh` wird pro `prod_host` gelesen — lokal für die eigene Maschine,
    # sonst per SSH aus hosts.yaml.
    hosts_cfg = load_hosts()
    hier = lokaler_host(hosts_cfg)

    if args.ssh:
        benoetigt = {None}
        ziel = {None: args.ssh}
    else:
        # Der Haupthost wird IMMER gelesen, auch wenn ihn kein Dienst nennt:
        # C4 (unregistrierte Ports) braucht ihn unabhaengig von der Deklaration,
        # und ein nicht erreichbarer Haupthost muss ein Tool-Fehler bleiben.
        # Ohne dieses `|` fiel bei leerer ports.yaml gar kein Host mehr an und
        # das Werkzeug meldete fröhlich "keine Drift" — gefangen vom
        # Bestandstest `test_should_exit_2_on_unreadable_live_state`.
        benoetigt = {DEFAULT_PROD_HOST} | {
            cfg.get("prod_host") or DEFAULT_PROD_HOST for cfg in ports_decl.values()
        }
        ziel = {}
        for h in benoetigt:
            if h == hier:
                ziel[h] = None  # lokal, kein SSH
            elif h in hosts_cfg and hosts_cfg[h].get("ssh"):
                ziel[h] = hosts_cfg[h]["ssh"]
            else:
                ziel[h] = False  # kein Zugang deklariert

    je_host: dict[str | None, dict[str, list[int]]] = {}
    unerreichbar: dict[str, str] = {}
    for h in benoetigt:
        if ziel.get(h) is False:
            unerreichbar[h] = f"kein ssh-Feld für '{h}' in infra/hosts.yaml"
            continue
        try:
            je_host[h] = live_containers(ziel[h])
        except (RuntimeError, subprocess.SubprocessError, OSError) as e:
            # Der Haupthost (bzw. das explizite --ssh-Ziel) ist die
            # Betriebsgrundlage — faellt der aus, misst das Werkzeug im Kern
            # nichts und meldet ehrlich einen Tool-Fehler statt einer Kennzahl
            # (exit 2, unveraendert). Bewusst an DEFAULT_PROD_HOST festgemacht
            # und NICHT an `hier`: sonst haenge das Exit-Verhalten davon ab, auf
            # welcher Maschine der Lauf zufaellig startet.
            if h == DEFAULT_PROD_HOST or args.ssh:
                print(
                    f"TOOL-FEHLER: Live-Zustand nicht lesbar: {e}",
                    file=sys.stderr,
                )
                return 2
            unerreichbar[h] = _knapper_grund(e)

    for h, grund in sorted(unerreichbar.items()):
        betroffen = sum(
            1
            for cfg in ports_decl.values()
            if (cfg.get("prod_host") or DEFAULT_PROD_HOST) == h
        )
        drift.append(
            (
                f"C0:{h}",
                f"Host '{h}' nicht erreichbar ({grund}) — C1/C2 für "
                f"{betroffen} Dienst(e) ungeprüft, NICHT als fehlend gewertet",
            )
        )

    def containers_of(host: str | None) -> dict[str, list[int]] | None:
        """Container des zuständigen Hosts, oder None wenn ungeprüft."""
        return je_host.get(None if args.ssh else host)

    def ort(host: str | None) -> str:
        """Was in der Meldung stehen soll: der TATSÄCHLICH inspizierte Host.

        Im `--ssh`-Einzelhostmodus ist das immer das SSH-Ziel — dort den
        deklarierten `prod_host` zu nennen wäre eine Falschaussage ("läuft
        nicht auf 'prod'", während gegen prod-b gemessen wurde).
        """
        return args.ssh if args.ssh else str(host)

    # C5: doppelte Port-Deklaration — prod UND staging getrennt (das bekannte
    # 8099-Duplikat risk-hub/tax-hub lag auf staging, nicht prod)
    for env in ("prod", "staging"):
        seen: dict[int, str] = {}
        for svc, cfg in ports_decl.items():
            p = cfg.get(env)
            if not isinstance(p, int):
                continue
            if p in seen:
                drift.append(
                    (
                        f"C5:{env}:{p}",
                        f"{env}-Port {p} doppelt deklariert: {seen[p]} + {svc}",
                    )
                )
            seen[p] = svc

    # C1 + C2 je deklariertem Service — gegen den ZUSTÄNDIGEN Host
    for svc, cfg in ports_decl.items():
        cname, p = cfg.get("container_name"), cfg.get("prod")
        if not cname or not isinstance(p, int):
            continue
        host = cfg.get("prod_host") or DEFAULT_PROD_HOST
        containers = containers_of(host)
        if containers is None:
            continue  # Host ungeprüft — bereits als C0 gemeldet
        rich = canonical.get(svc, {}).get("rich", {})
        deployed = rich.get("deployed") is True
        if cname in containers:
            live_ports = containers[cname]
            if live_ports and p not in live_ports:
                drift.append(
                    (
                        f"C1:{svc}",
                        f"{svc}: deklariert {p}, Container {cname} publiziert "
                        f"{live_ports} (auf {ort(host)})",
                    )
                )
        elif deployed:
            drift.append(
                (
                    f"C2:{svc}",
                    f"{svc}: rich.deployed=true, aber Container {cname} "
                    f"läuft nicht auf '{ort(host)}'",
                )
            )

    # C3: DNS je deklarierter prod_url (flat), nur für deployte Services
    if not args.skip_dns:
        for repo, entry in canonical.items():
            url = entry.get("flat", {}).get("prod_url")
            deployed = entry.get("rich", {}).get("deployed") is True
            if url and deployed and not live_dns(url, args.ssh):
                drift.append(
                    (f"C3:{repo}", f"{repo}: prod_url {url} löst nicht auf (NXDOMAIN)")
                )

    # C4: live publizierter Port ohne Deklaration
    declared_ports = (
        {cfg.get("prod") for cfg in ports_decl.values()}
        | {cfg.get("staging") for cfg in ports_decl.values()}
        | {cfg.get("dev") for cfg in ports_decl.values()}
    )
    # Über ALLE gelesenen Hosts. Die Drift-ID bleibt bewusst `C4:<port>` ohne
    # Host-Anteil: die fünf Baseline-Einträge sind darauf ausgestellt, und ein
    # Host-Suffix hätte sie stillschweigend entwertet (der Waiver griffe nicht
    # mehr, der Lauf meldete "neue" Drift, die keine ist). Derselbe Port auf
    # zwei Hosts — `mon_cadvisor` ist genau so ein Fall — wird deshalb einmal
    # gemeldet; die Fundorte stehen in der Beschreibung.
    gefunden: dict[int, list[str]] = {}
    for h, containers in sorted(je_host.items(), key=lambda kv: str(kv[0])):
        for cname, live_ports in containers.items():
            for p in live_ports:
                if p not in declared_ports and not in_infra_range(p):
                    gefunden.setdefault(p, []).append(f"{cname} auf {ort(h)}")
    for p, orte in sorted(gefunden.items()):
        drift.append(
            (
                f"C4:{p}",
                f"Port {p} ({', '.join(orte)}) publiziert, aber in ports.yaml unbekannt",
            )
        )

    new = [(i, d) for i, d in drift if i not in baseline_ids]
    suppressed = [(i, d) for i, d in drift if i in baseline_ids]

    print(
        f"Drift-Kennzahl: {len(drift)} gesamt = {len(new)} NEU + {len(suppressed)} baselined"
    )
    for i, d in suppressed:
        print(f"  [baseline] {i}  {d}")
    for i, d in new:
        print(f"  [NEU]      {i}  {d}")
    if new:
        print(
            "\n→ Exit 1 = FUND-Signal (neue Drift), kein Tool-Fehler. "
            "Triage: beheben ODER mit owner+expires_at in infra/reconcile-baseline.yaml."
        )
        return 1
    print("→ Keine neue Drift gegenüber Baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
