#!/usr/bin/env python3
"""gate_drill_check.py — Fenster-Prüflauf der Gate-Drills (KONZ-038 D8).

Liest docs/governance/gate-registry.json und führt jeden Drill ECHT aus
(pytest je Drill-Datei). Ein Gate mit rotem oder fehlendem Drill wird
K4-konform als NICHT GEBAUT gemeldet — der wiederkehrende Lauf beantwortet
M-8 dauerhaft: ein toter Hook wird binnen eines Fensters entdeckt, nicht 2028.

Verdrahtet im regel-ritual-Workflow (2.+16.); Ausgabe landet im Kommentar auf
dem Tracking-Issue. Exit 0 immer (Report-Tool, kein Gate-Enforcer — das Urteil
steht im Text). stdlib-only.

Aufruf: python3 tools/gate_drill_check.py [--registry <pfad>]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(REPO_ROOT, "docs", "governance", "gate-registry.json")


def run_drill(drill_path: str) -> tuple[bool, str]:
    """True = Drill grün. Fehlende Datei = rot (K4: nicht belegbar = nicht gebaut)."""
    full = os.path.join(REPO_ROOT, drill_path)
    if not os.path.isfile(full):
        return False, "Drill-Datei fehlt"
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", full, "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=REPO_ROOT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Drill-Lauf fehlgeschlagen: {exc}"
    tail = (out.stdout.strip().splitlines() or ["(keine Ausgabe)"])[-1]
    return out.returncode == 0, tail


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate-Drills echt ausführen (KONZ-038 D8)")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    args = ap.parse_args()

    try:
        registry = json.load(open(args.registry, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"⚠ Gate-Registry nicht lesbar ({exc}) — Prüflauf NICHT bewertbar.")
        return 0

    gates = registry.get("gates", [])
    print(f"## Gate-Drill-Prüflauf ({len(gates)} registrierte Gates)")
    dead = 0
    for g in gates:
        ok, detail = run_drill(g.get("drill", ""))
        if ok:
            print(f"  ✓ {g['slug']} ({g.get('mode', '?')}) — {detail}")
        else:
            dead += 1
            print(
                f"  ✗ {g['slug']} ({g.get('mode', '?')}) — K4: NICHT GEBAUT — {detail}"
            )
    if dead:
        print(
            f"\n→ {dead} Gate(s) K4-zurückgestuft: Drill reparieren oder Gate aus der "
            "Registry nehmen — beides per PR, nicht stillschweigend."
        )
    else:
        print("\n→ alle registrierten Gates Drill-frisch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
