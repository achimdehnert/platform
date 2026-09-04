#!/usr/bin/env python3
"""Prüft AGENTS.md eines PyPI-Pakets gegen das Schema pkg-agents-v1 (#2075 K2).

Pflichtstruktur (docs/templates/pkg-AGENTS.md):
  - H1-Titel in Zeile 1
  - Schema-Marker "Schema: pkg-agents-v1"
  - H2-Sektionen: Zweck, Setup & Test, Public API, Architektur-Constraints, Release
  - "Setup & Test" enthält einen bash-Fence mit genau einem nicht-leeren Kommando

Aufruf:
    python3 tools/check_agents_md.py PATH [PATH ...]
    python3 tools/check_agents_md.py --advisory PATH   # rc immer 0, nur Report

Neue Checks starten advisory (ADR-266-Amendment 2026-08-19 / #2075 K3-Regel);
blocking erst nach Präzisions-Nachweis über die Flotte.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCHEMA_MARKER = "Schema: pkg-agents-v1"
REQUIRED_H2 = [
    "Zweck",
    "Setup & Test",
    "Public API",
    "Architektur-Constraints",
    "Release",
]


def check_text(text: str) -> list[str]:
    """Alle Schema-Verstöße eines AGENTS.md-Inhalts (leer = konform)."""
    problems: list[str] = []
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        problems.append("Zeile 1 ist kein H1-Titel ('# ...')")
    if SCHEMA_MARKER not in text:
        problems.append(f"Schema-Marker fehlt: '{SCHEMA_MARKER}'")
    headings = {
        m.group(1).strip() for m in re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE)
    }

    # H2 darf Zusätze in Klammern tragen: "Setup & Test (Einstiegskommando)"
    def has(h: str) -> bool:
        return any(x == h or x.startswith(h + " (") for x in headings)

    for h in REQUIRED_H2:
        if not has(h):
            problems.append(f"Pflicht-Sektion fehlt: '## {h}'")
    problems.extend(_check_entry_command(text))
    return problems


def _check_entry_command(text: str) -> list[str]:
    """Der Setup-&-Test-Abschnitt braucht einen bash-Fence mit 1 Kommando."""
    m = re.search(r"^##\s+Setup & Test.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return []  # fehlende Sektion wird oben schon gemeldet
    fences = re.findall(r"```bash\n(.*?)```", m.group(1), re.S)
    if not fences:
        return ["'Setup & Test' hat keinen ```bash-Fence mit Einstiegskommando"]
    cmds = [
        ln for ln in fences[0].splitlines() if ln.strip() and not ln.startswith("#")
    ]
    if len(cmds) != 1:
        return [
            f"Einstiegskommando muss GENAU 1 Zeile sein (gefunden: {len(cmds)}) — "
            "Mehrschritt-Setup gehört hinter ein make-Target"
        ]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--advisory", action="store_true", help="rc 0 auch bei Verstößen")
    args = ap.parse_args()

    rc = 0
    for path in args.paths:
        if not path.is_file():
            print(f"{path}: FEHLT")
            rc = 1
            continue
        problems = check_text(path.read_text(encoding="utf-8"))
        if problems:
            rc = 1
            for p in problems:
                print(f"{path}: {p}")
        else:
            print(f"{path}: ok (pkg-agents-v1)")
    return 0 if args.advisory else rc


if __name__ == "__main__":
    sys.exit(main())
