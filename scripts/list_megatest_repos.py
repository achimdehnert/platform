#!/usr/bin/env python3
"""list_megatest_repos.py — Gibt alle Repos aus, die gescannt werden sollen.

Schnittmenge von repo-registry.yaml und tests/megatest/budgets.toml.
Ausgabe: space-separated Liste für Shell-Nutzung.

Usage:
    python3 scripts/list_megatest_repos.py
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import yaml

_SKIP = {"platform"}
_ROOT = Path(__file__).parent.parent


def main() -> None:
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

    print(" ".join(repos))


if __name__ == "__main__":
    main()
