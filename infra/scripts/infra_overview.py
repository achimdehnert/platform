#!/usr/bin/env python3
"""infra_overview.py — read-only Single-Pane Infra-Übersicht (platform, ADR-157/164).

Aggregiert die SSoT `infra/ports.yaml` zu EINER Ansicht:
  - Server-Inventar (dev/staging/prod)
  - App × Umgebung Port-Matrix (die kein bestehendes Tool druckt)
  - Compose-Drift (Port in ports.yaml ≠ Compose-File) + Staging≠Prod-Skew

Default = OFFLINE/deterministisch (kein SSH, CI-tauglich). `--live` hängt die
read-only TCP-Reachability je Server an, indem es an `server_probe.py --all`
delegiert (kein eigener Netz-Code). **Reines Reporting — schreibt nichts.**

Exit: 0 = keine Compose-Drift, 1 = Compose-Drift gefunden (deploy-blocker).
"""
import argparse, os, subprocess, sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML fehlt — pip install pyyaml")

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PORTS = os.path.normpath(os.path.join(HERE, "..", "ports.yaml"))
ENVS = ["dev", "staging", "prod"]  # 'dev' = Dev-Desktop / lokal


def main():
    ap = argparse.ArgumentParser(description="Read-only Single-Pane Infra-Übersicht (platform)")
    ap.add_argument("--ports", default=DEFAULT_PORTS, help="Pfad zu ports.yaml")
    ap.add_argument("--live", action="store_true",
                    help="read-only TCP-Probe je Server (delegiert an server_probe.py --all)")
    args = ap.parse_args()

    with open(args.ports, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    servers = data.get("servers", {}) or {}
    services = data.get("services", {}) or {}

    print(f"=== Infra-Overview (read-only) — Quelle: {os.path.basename(args.ports)}, "
          f"{len(services)} Apps ===\n")

    # --- Server-Inventar ---
    print("SERVER")
    for env in ENVS:
        s = servers.get(env)
        if s:
            print(f"  {env:<8} {str(s.get('ip','')):<16} {s.get('name','')}")
        else:
            print(f"  {env:<8} {'—':<16} (kein Server definiert)")
    print()

    # --- App × Umgebung Matrix + Drift-Klassifikation ---
    compose_drift = {}
    skew = {}
    for name, svc in services.items():
        if svc.get("compose_drift"):
            compose_drift[name] = svc["compose_drift"]
        sp, st = svc.get("prod"), svc.get("staging")
        if isinstance(sp, int) and isinstance(st, int) and sp != st:
            skew[name] = (st, sp)

    print(f"{'APP':<28} {'dev':>5} {'staging':>8} {'prod':>6}   drift")
    for name in sorted(services):
        svc = services[name]
        tags = []
        if name in compose_drift:
            tags.append("compose")
        if name in skew:
            tags.append("skew")
        flag = "+".join(tags) if tags else "ok"
        print(f"  {name:<26} {str(svc.get('dev','—')):>5} {str(svc.get('staging','—')):>8} "
              f"{str(svc.get('prod','—')):>6}   {flag}")
    print()

    # --- Drift-Detail ---
    print(f"COMPOSE-DRIFT ({len(compose_drift)}/{len(services)} betroffen — deploy-blocker)")
    for n in sorted(compose_drift):
        print(f"  ! {n}: {compose_drift[n]}")
    if not compose_drift:
        print("  ok — keine")
    if skew:
        print(f"\nSTAGING≠PROD-SKEW ({len(skew)} — ADR-164 will staging=prod; ggf. bewusste Ausnahme)")
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

    drift_total = len(compose_drift)
    print(f"\n=== DRIFT (compose): {drift_total} (0 = sauber) ===")
    return 1 if drift_total else 0


if __name__ == "__main__":
    sys.exit(main())
