#!/usr/bin/env python3
"""Kandidaten fuer den Test-Scaffold-PR (scaffold-tests.yml) aus der kanonischen Registry.

Vorher las der Workflow die generierte flache Legacy-View (ADR-234) und nahm fuer
jedes Repo den Owner des platform-Repos an — `frist-hub` liegt aber unter
`meiki-lra`, und `pulls.list()` brach mit 404 ab: 20 von 20 Laeufen rot seit
2026-07-02 (#2645). Dieselbe Klasse wie in `tools/fleet_checkout.py` beschrieben.

Hier wird je Repo der Ist-Owner ueber `registry_api.owner()` aufgeloest und in
drei Gruppen geteilt, damit der Workflow Fremd-Org-Repos bewusst zaehlt statt
still uebergeht:

  eigene     [{owner, repo}]  — Owner in EIGENE_ORGS, wird bearbeitet
  fremd      [{owner, repo}]  — anderer Owner (meiki-lra, ttz-lif, …), gezaehlt, nicht angefasst
  unbekannt  [repo]           — kein Owner aufloesbar (Registry-Luecke)

Aufruf:  python3 tools/scaffold_kandidaten.py [--repo NAME] [--github-output PFAD]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry_api  # noqa: E402
from fleet_checkout import EIGENE_ORGS  # noqa: E402

#: Nur App-Repos bekommen ein Django-Test-Scaffold.
SCAFFOLD_TYPES = frozenset({"django", "agent", "bot"})
#: Eingefrorene/archivierte Repos bekommen keine Auto-PRs (KONZ-Queue-Regel).
RUHENDE_LIFECYCLES = frozenset({"frozen", "archived"})


def kandidaten(canon: dict) -> list[str]:
    """Repo-Namen mit Scaffold-Typ, nicht platform, nicht ruhend."""
    aus = []
    for name, e in canon.get("repos", {}).items():
        if name == "platform" or not isinstance(e, dict):
            continue
        if (e.get("flat") or {}).get("type") not in SCAFFOLD_TYPES:
            continue
        if registry_api._lifecycle(e) in RUHENDE_LIFECYCLES:
            continue
        aus.append(name)
    return sorted(aus)


def plane(canon: dict, einzel: str | None = None) -> dict[str, list]:
    """Kandidaten nach Owner einteilen — ohne Netz/Dateisystem."""
    namen = kandidaten(canon)
    if einzel:
        namen = [einzel] if einzel in namen else []
    eigene: list[dict] = []
    fremd: list[dict] = []
    unbekannt: list[str] = []
    for repo in namen:
        besitzer = registry_api.owner(repo, canon)
        if not besitzer:
            unbekannt.append(repo)
        elif besitzer in EIGENE_ORGS:
            eigene.append({"owner": besitzer, "repo": repo})
        else:
            fremd.append({"owner": besitzer, "repo": repo})
    return {"eigene": eigene, "fremd": fremd, "unbekannt": unbekannt}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default="", help="einzelnes Repo (workflow_dispatch)")
    ap.add_argument(
        "--github-output",
        default=os.environ.get("GITHUB_OUTPUT"),
        help="Datei fuer `repos=`/`count=`/`foreign=`/`unknown=` (Default: $GITHUB_OUTPUT)",
    )
    args = ap.parse_args(argv)

    plan = plane(registry_api.load_canonical(), args.repo.strip() or None)
    print(
        f"Kandidaten: {len(plan['eigene'])} eigene, {len(plan['fremd'])} fremd, "
        f"{len(plan['unbekannt'])} ohne Owner"
    )
    for e in plan["fremd"]:
        print(f"  fremd:     {e['owner']}/{e['repo']} — nicht angefasst")
    for r in plan["unbekannt"]:
        print(f"  unbekannt: {r} — in registry/canonical.yaml ergaenzen")

    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as f:
            f.write(f"repos={json.dumps(plan['eigene'])}\n")
            f.write(f"count={len(plan['eigene'])}\n")
            f.write(f"foreign={len(plan['fremd'])}\n")
            f.write(f"unknown={len(plan['unbekannt'])}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
