#!/usr/bin/env python3
"""list_megatest_repos.py — Gibt alle Repos aus, die gescannt werden sollen.

Schnittmenge von repo-registry.yaml und tests/megatest/budgets.toml.
Ausgabe: space-separated Liste für Shell-Nutzung.

Usage:
    python3 scripts/list_megatest_repos.py                # nur Repo-Namen
    python3 scripts/list_megatest_repos.py --with-owner   # "owner/repo" je Zeile

``--with-owner`` (platform#1682): ``megatest.yml`` hat den Owner bis 2026-08-05
als ``achimdehnert/$repo`` hartkodiert, obwohl die Registry ihn längst auflöst
(``registry_api.owner`` — per-Repo ``github:``-Feld, ``meta.repo_owner``-Override,
``owner_prefix_rules``). Für transferierte Repos verdeckte GitHubs Redirect den
Fehler; Repos, die direkt in einer Fremd-Org entstanden sind, blieben still
ungescannt. Der Resolver war gebaut — nur nicht aufgerufen.

Ein Repo, dessen Owner sich NICHT auflösen lässt, wird laut übersprungen
(stderr-WARN + Ausschluss) statt still auf den Default-Owner zu fallen — sonst
wäre das Ergebnis wieder ein geratener Pfad.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

import yaml

_SKIP = {"platform"}
_ROOT = Path(__file__).parent.parent

sys.path.insert(0, str(_ROOT / "tools"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--with-owner",
        action="store_true",
        help="'owner/repo' je Zeile ausgeben (Owner aus der Registry aufgelöst)",
    )
    args = ap.parse_args()

    reg_path = _ROOT / "scripts" / "repo-registry.yaml"
    bud_path = _ROOT / "tests" / "megatest" / "budgets.toml"

    reg = yaml.safe_load(reg_path.read_text())
    bud = tomllib.loads(bud_path.read_text())

    registry_repos = set(reg.get("repos", {}).keys())
    budget_repos = set(bud.get("budgets", {}).keys())

    repos = sorted((registry_repos & budget_repos) - _SKIP)

    missing_budget = sorted(registry_repos - budget_repos - _SKIP)
    if missing_budget:
        print(
            f"WARN: {len(missing_budget)} Repos in Registry ohne Budget: "
            f"{missing_budget}",
            file=sys.stderr,
        )

    if not args.with_owner:
        print(" ".join(repos))
        return

    import registry_api

    canon = registry_api.load_canonical()
    zeilen = []
    ohne_owner = []
    for name in repos:
        besitzer = registry_api.owner(name, canon)
        if not besitzer:
            ohne_owner.append(name)
            continue
        zeilen.append(f"{besitzer}/{name}")
    if ohne_owner:
        print(
            f"WARN: {len(ohne_owner)} Repo(s) ohne auflösbaren Owner — "
            f"NICHT gescannt (kein Default-Raten): {ohne_owner}",
            file=sys.stderr,
        )
    print("\n".join(zeilen))


if __name__ == "__main__":
    main()
