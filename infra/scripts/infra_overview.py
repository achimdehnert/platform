#!/usr/bin/env python3
"""infra_overview.py — read-only Single-Pane Infra-Übersicht (platform, ADR-157/164).

Aggregiert die SSoT `infra/ports.yaml` zu EINER Ansicht:
  - Server-Inventar (dev/staging/prod)
  - App × Umgebung Port-Matrix (die kein bestehendes Tool druckt)
  - Compose-Drift (Port in ports.yaml ≠ Compose-File) + Staging≠Prod-Skew

Compose-Drift wird GEMESSEN (#1685): für jeden Service mit `repo:` werden die
lokal geklonten Compose-Dateien (`~/github/<repo>/docker-compose.yml` → dev,
`docker-compose.prod.yml` → prod) geparst und der Host-Port des Web-Service
gegen ports.yaml verglichen. Statische `compose_drift:`-Anmerkungen aus
ports.yaml werden nur noch als "unverifizierte Annotation" mitgeführt; Services
ohne lokalen Klon zählen als "nicht messbar", NICHT als sauber.

Default = OFFLINE/deterministisch (kein SSH, CI-tauglich). `--live` hängt die
read-only TCP-Reachability je Server an, indem es an `server_probe.py --all`
delegiert (kein eigener Netz-Code). **Reines Reporting — schreibt nichts.**

Exit: 0 = keine GEMESSENE Compose-Drift, 1 = gemessene Drift (deploy-blocker).
Annotationen und nicht messbare Services beeinflussen den Exit-Code nicht.
"""

import argparse
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML fehlt — pip install pyyaml")

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PORTS = os.path.normpath(os.path.join(HERE, "..", "ports.yaml"))
ENVS = ["dev", "staging", "prod"]  # 'dev' = Dev-Desktop / lokal
GITHUB_ROOT = os.path.expanduser("~/github")  # lokale Klone (Mess-Basis)
# Compose-Datei → ports.yaml-Feld, gegen das gemessen wird
COMPOSE_FILES = [("docker-compose.yml", "dev"), ("docker-compose.prod.yml", "prod")]
# ${VAR:-8042} → Default-Wert ist der effektive Host-Port ohne gesetzte Env.
# MUSS vor dem ":"-Split ersetzt werden — der Default steckt selbst hinter ":".
_ENV_DEFAULT = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*:-([^}]+)\}")


def _host_port(entry):
    """Host-Port aus EINEM ports-Eintrag einer Compose-Datei, sonst None.

    Versteht "8093:8000", "127.0.0.1:8088:8000", "127.0.0.1:${PORT:-8042}:8000"
    (mit/ohne Anführungszeichen — YAML-geparst) sowie Long-Syntax {published:…}.
    Container-only-Einträge ("8000") und Unparsebares → None.
    """
    if isinstance(entry, dict):  # Long-Syntax
        entry = entry.get("published")
        return int(entry) if str(entry or "").isdigit() else None
    entry = _ENV_DEFAULT.sub(r"\1", str(entry))  # ${PORT:-8042} → 8042
    parts = entry.split("/")[0].split(":")  # "/tcp"-Suffix abtrennen
    if len(parts) == 2:  # HOST:CONTAINER
        host = parts[0]
    elif len(parts) == 3:  # IP:HOST:CONTAINER
        host = parts[1]
    else:  # kein Host-Mapping oder exotisch (IPv6, Range)
        return None
    return int(host) if host.isdigit() else None


def extract_web_host_ports(compose_path):
    """(web_service_name, [host_ports]) des Web-Service einer Compose-Datei.

    Web-Service-Heuristik (in dieser Reihenfolge): Name enthält "web",
    exakt "app" (risk-hub-Dev-Muster), Name enthält "caddy" (travel-beat:
    Caddy IST der Web-Einstieg). Reverse-Proxies wie nginx/traefik werden
    bewusst NICHT geraten (odoo: traefik 80/443 wäre ein False Positive).
    Kein Kandidat mit parsebarem Host-Port → (None, []).
    """
    with open(compose_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    services = data.get("services") or {}
    for match in (lambda n: "web" in n, lambda n: n == "app", lambda n: "caddy" in n):
        cands = [
            (n, s)
            for n, s in services.items()
            if match(n.lower()) and (s or {}).get("ports")
        ]
        if cands:
            break
    else:
        return None, []
    name = "+".join(n for n, _ in cands)
    ports = [
        p for _, s in cands for e in s["ports"] if (p := _host_port(e)) is not None
    ]
    return (name, ports) if ports else (None, [])


def measure_compose_drift(services, github_root=GITHUB_ROOT):
    """Misst Compose-Drift gegen lokale Klone. → dict name → Ergebnis.

    Ergebnis: {"status": "drift"|"ok"|"unmeasurable", "drifts": […],
               "ok": […], "reason": str (nur unmeasurable)}.
    Nur Services mit `repo:`-Feld werden gemessen; kein Klon/keine parsebare
    Compose-Datei → "unmeasurable" (NICHT sauber).
    """
    results = {}
    for name, svc in services.items():
        repo = svc.get("repo")
        if not repo:
            continue
        repo_dir = os.path.join(github_root, repo.split("/")[-1])
        if not os.path.isdir(repo_dir):
            results[name] = {
                "status": "unmeasurable",
                "drifts": [],
                "ok": [],
                "reason": "kein lokaler Klon",
            }
            continue
        drifts, oks, skips = [], [], []
        for fname, env in COMPOSE_FILES:
            path = os.path.join(repo_dir, fname)
            expected = svc.get(env)
            if not os.path.isfile(path) or not isinstance(expected, int):
                continue
            try:
                web, ports = extract_web_host_ports(path)
            except Exception as e:  # kaputtes YAML = nicht messbar, nicht sauber
                skips.append(f"{fname}: Parse-Fehler ({e})")
                continue
            if not ports:
                skips.append(f"{fname}: kein Web-Service mit parsebarem Host-Port")
            elif expected in ports:
                oks.append(f"{fname}={expected}")
            else:
                drifts.append(f"{fname} [{web}] Host-Ports {ports} ≠ {env} {expected}")
        if drifts:
            results[name] = {"status": "drift", "drifts": drifts, "ok": oks}
        elif oks:
            results[name] = {"status": "ok", "drifts": [], "ok": oks}
        else:
            results[name] = {
                "status": "unmeasurable",
                "drifts": [],
                "ok": [],
                "reason": "; ".join(skips) or "keine Compose-Datei im Klon",
            }
    return results


def main():
    ap = argparse.ArgumentParser(
        description="Read-only Single-Pane Infra-Übersicht (platform)"
    )
    ap.add_argument("--ports", default=DEFAULT_PORTS, help="Pfad zu ports.yaml")
    ap.add_argument(
        "--live",
        action="store_true",
        help="read-only TCP-Probe je Server (delegiert an server_probe.py --all)",
    )
    args = ap.parse_args()

    with open(args.ports, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    servers = data.get("servers", {}) or {}
    services = data.get("services", {}) or {}

    print(
        f"=== Infra-Overview (read-only) — Quelle: {os.path.basename(args.ports)}, "
        f"{len(services)} Apps ===\n"
    )

    # --- Server-Inventar ---
    print("SERVER")
    for env in ENVS:
        s = servers.get(env)
        if s:
            print(f"  {env:<8} {str(s.get('ip', '')):<16} {s.get('name', '')}")
        else:
            print(f"  {env:<8} {'—':<16} (kein Server definiert)")
    print()

    # --- App × Umgebung Matrix + Drift-Klassifikation ---
    annotations = {}  # statische compose_drift:-Anmerkungen (unverifiziert)
    skew = {}
    for name, svc in services.items():
        if svc.get("compose_drift"):
            annotations[name] = svc["compose_drift"]
        sp, st = svc.get("prod"), svc.get("staging")
        if isinstance(sp, int) and isinstance(st, int) and sp != st:
            skew[name] = (st, sp)

    measured = measure_compose_drift(services)  # ECHTE Messung gegen lokale Klone
    drifted = {n for n, r in measured.items() if r["status"] == "drift"}
    clean = {n for n, r in measured.items() if r["status"] == "ok"}
    unmeasurable = {
        n: r["reason"] for n, r in measured.items() if r["status"] == "unmeasurable"
    }

    print(f"{'APP':<28} {'dev':>5} {'staging':>8} {'prod':>6}   drift")
    for name in sorted(services):
        svc = services[name]
        tags = []
        if name in drifted:
            tags.append("compose")
        elif name in annotations:
            tags.append("annot")
        if name in skew:
            tags.append("skew")
        flag = "+".join(tags) if tags else "ok"
        print(
            f"  {name:<26} {str(svc.get('dev', '—')):>5} {str(svc.get('staging', '—')):>8} "
            f"{str(svc.get('prod', '—')):>6}   {flag}"
        )
    print()

    # --- Drift-Detail (gemessen, #1685) ---
    print(
        f"COMPOSE-DRIFT — GEMESSEN gegen lokale Klone in {GITHUB_ROOT} "
        f"({len(drifted)} Drift, {len(clean)} sauber, {len(unmeasurable)} nicht messbar)"
    )
    for n in sorted(drifted):
        for d in measured[n]["drifts"]:
            print(f"  ! {n}: {d}")
    if not drifted:
        print("  ok — keine gemessene Drift")
    if unmeasurable:
        print(f"\n  NICHT MESSBAR ({len(unmeasurable)} — zählt NICHT als sauber)")
        for n in sorted(unmeasurable):
            print(f"  - {n}: {unmeasurable[n]}")
    if annotations:
        print(
            f"\n  UNVERIFIZIERTE ANNOTATIONEN aus ports.yaml ({len(annotations)} — "
            "compose_drift:-Freitext, keine Messung)"
        )
        for n in sorted(annotations):
            stale = (
                "  [Messung sauber — Annotation vermutlich veraltet]"
                if n in clean
                else ""
            )
            print(f"  ? {n}: {annotations[n]}{stale}")
    if skew:
        print(
            f"\nSTAGING≠PROD-SKEW ({len(skew)} — ADR-164 will staging=prod; ggf. bewusste Ausnahme)"
        )
        for n in sorted(skew):
            st, sp = skew[n]
            print(f"  ~ {n}: staging={st} prod={sp}")
    print()

    # --- Live (optional, read-only Passthrough) ---
    if args.live:
        print("LIVE-REACHABILITY (server_probe.py --all, read-only TCP)\n")
        probe = os.path.join(HERE, "server_probe.py")
        rc = subprocess.run([sys.executable, probe, "--all"]).returncode
        print(f"\n  (server_probe exit={rc})")
    else:
        print("LIVE: übersprungen — '--live' für TCP-Probe + Uptime je Server")

    drift_total = len(drifted)
    print(
        f"\n=== DRIFT (compose, gemessen): {drift_total} (0 = sauber; "
        f"{len(unmeasurable)} nicht messbar, {len(annotations)} Annotationen) ==="
    )
    return 1 if drift_total else 0


if __name__ == "__main__":
    sys.exit(main())
