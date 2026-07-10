#!/usr/bin/env python3
"""Runner für scripts/checks/staging_*.sh nach Wire-or-delete-Config (KONZ-015 REC-1).

Liest infra/staging-checks.yaml: enabled-Checks laufen; disabled-Checks brauchen
reason + owner + decide_by — abgelaufenes decide_by schlägt HART fehl (fail-closed,
E2-Waiver-Muster wie infra/reconcile-baseline.yaml). Fehlschläge aktivierter Checks
werden gegen known_failures gestundet (owner + expires_at Pflicht).

Exit-Codes (⚠️ run-conclusion ≠ Tool-Health):
  0 = alle aktivierten Checks grün/SKIP (Baseline-Treffer erlaubt)
  1 = NEUER Fehlschlag eines aktivierten Checks — FUND-Signal
  2 = Config-Fehler (Pflichtfeld fehlt, decide_by/expires_at abgelaufen, Skript fehlt)

  --include-disabled: manueller Voll-Lauf aller 8 (z.B. von dev mit SSH-Keys).
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / "infra" / "staging-checks.yaml"
CHECKS_DIR = REPO_ROOT / "scripts" / "checks"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--include-disabled", action="store_true",
                    help="auch enabled:false-Checks ausführen (manueller Voll-Lauf)")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text())
    checks: dict = cfg.get("checks", {})
    baseline: list = cfg.get("known_failures") or []
    today = dt.date.today()

    for e in baseline:
        for f in ("id", "reason", "owner", "expires_at"):
            if not e.get(f):
                print(f"CONFIG-FEHLER: known_failures-Eintrag ohne '{f}': {e}", file=sys.stderr)
                return 2
        if dt.date.fromisoformat(str(e["expires_at"])) < today:
            print(f"CONFIG-FEHLER: Stundung '{e['id']}' abgelaufen ({e['expires_at']}) — "
                  "fail-closed: beheben oder bewusst verlängern.", file=sys.stderr)
            return 2
    baseline_ids = {e["id"] for e in baseline}

    on_disk = {p.name for p in CHECKS_DIR.glob("staging_*.sh")}
    configured = set(checks)
    if on_disk != configured:
        print(f"CONFIG-FEHLER: Skripte auf Platte ≠ Config — nur auf Platte: "
              f"{sorted(on_disk - configured)}, nur in Config: {sorted(configured - on_disk)}. "
              "Jedes Skript braucht einen expliziten Zustand (kein dritter Zustand).",
              file=sys.stderr)
        return 2

    new_failures: list[str] = []
    for name in sorted(checks):
        c = checks[name] or {}
        if not c.get("enabled"):
            for f in ("reason", "owner", "decide_by"):
                if not c.get(f):
                    print(f"CONFIG-FEHLER: '{name}' disabled ohne '{f}' — "
                          "disabled braucht Grund + Owner + Datum.", file=sys.stderr)
                    return 2
            if dt.date.fromisoformat(str(c["decide_by"])) < today:
                print(f"CONFIG-FEHLER: decide_by für '{name}' abgelaufen "
                      f"({c['decide_by']}) — fail-closed: einbauen, löschen oder "
                      "bewusst verlängern.", file=sys.stderr)
                return 2
            if not args.include_disabled:
                print(f"[disabled]  {name}  (bis {c['decide_by']}: {c['reason'][:80]}…)")
                continue

        r = subprocess.run(["bash", str(CHECKS_DIR / name)],
                           capture_output=True, text=True, timeout=120)
        tail = (r.stdout + r.stderr).strip().splitlines()
        summary = tail[-1][:120] if tail else "(kein Output)"
        if r.returncode == 0:
            print(f"[ok]        {name}  {summary}")
        elif name in baseline_ids:
            print(f"[baseline]  {name}  rc={r.returncode}  {summary}")
        else:
            print(f"[NEU ROT]   {name}  rc={r.returncode}  {summary}")
            new_failures.append(name)

    if new_failures:
        print(f"\n→ Exit 1 = FUND-Signal ({len(new_failures)} neuer Fehlschlag), kein Tool-Fehler. "
              "Triage: beheben ODER in infra/staging-checks.yaml known_failures stunden.")
        return 1
    print("\n→ Alle aktivierten Checks grün bzw. gestundet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
