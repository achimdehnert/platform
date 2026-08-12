#!/usr/bin/env python3
"""Gate: ein NEUES Werkzeug-Modul kommt mit einem Test — oder wird gemeldet.

Retro-Muster `untested-tool-module-green-gate` (platform#1650, Owner-Go
2026-08-12): `tools-tests.yml` prueft den BESTAND zuverlaessig (make test,
blockierend), aber nichts prueft NEUZUGAENGE — ein neues tools/*.py ohne jede
Testdatei laesst CI gruen. Der Workflow sagt es selbst (Ehrlichkeits-Hinweis:
~24 scripts/*.py ungetestet, "Gate laeuft gruen, ohne sie zu pruefen").

Bewusst NUR im PR HINZUGEFUEGTE Dateien (--diff-filter=A): die Altfaelle sind
Bestandsschutz — ein Gate, das am ersten Tag 24 fremde Befunde wirft, wird
umgangen statt befolgt (repo-health-Disziplin: 0-FP-Baseline zuerst).

Ein Modul gilt als getestet, wenn EINE der beiden Spuren existiert:
  1. eine Testdatei test_<stem>.py irgendwo unter tools/ oder tests/, ODER
  2. sein Stem kommt woertlich in einer Testdatei vor (deckt Suites ab, die
     mehrere Module in einer Datei testen, z.B. test_block_unformatted_push_suite).

Exit: 0 = sauber · 1 = Befund (advisory — der CI-Step bleibt gruen, druckt aber
die Warnung) · 2 = Werkzeugfehler (der CI-Step wird ROT: ein Melder, der beim
Ausfall schweigt, ist schlimmer als keiner).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Maschinenlesbarer Kopf (KONZ-038 D8) — von tools/gate_drill_check.py gegen
# docs/governance/gate-registry.json abgeglichen.
GATE_HEADER = {
    "slug": "untested-tool-module-green-gate",
    "mode": "advisory",  # blocking erst nach 0-FP-Kalibrierfenster (Registry-frozen_note)
    "owner": "achim",
    "last_drill_pass": "2026-08-12",
    "evidence": "tools/tests/test_check_new_module_tests.py",
}

REPO_ROOT = Path(__file__).resolve().parent.parent

# Nur diese Wurzeln werden auf ungetestete Neuzugaenge geprueft.
MODUL_WURZELN = ("tools/", "scripts/")
# Verzeichnisse, in denen nach Test-Spuren gesucht wird.
TEST_WURZELN = ("tools", "tests", "scripts")


def ist_pruefpflichtig(pfad: str) -> bool:
    """Neuzugang, der einen Test braucht: .py unter tools/ oder scripts/,
    aber keine Testdatei, kein __init__, kein conftest, kein tests/-Ordner."""
    if not pfad.endswith(".py"):
        return False
    if not pfad.startswith(MODUL_WURZELN):
        return False
    p = Path(pfad)
    if "tests" in p.parts:
        return False
    name = p.name
    return not (name.startswith("test_") or name in ("__init__.py", "conftest.py"))


def hat_test_spur(stem: str, repo_root: Path) -> bool:
    """Spur 1: test_<stem>.py existiert; Spur 2: Stem steht in einer Testdatei."""
    for wurzel in TEST_WURZELN:
        basis = repo_root / wurzel
        if not basis.is_dir():
            continue
        if any(basis.rglob(f"test_{stem}.py")):
            return True
    for wurzel in TEST_WURZELN:
        basis = repo_root / wurzel
        if not basis.is_dir():
            continue
        for testdatei in basis.rglob("test_*.py"):
            try:
                if stem in testdatei.read_text(encoding="utf-8"):
                    return True
            except OSError:
                continue
    return False


def hinzugefuegte_dateien(bereich: str, repo_root: Path) -> list[str] | None:
    """--diff-filter=A ueber den Bereich; None = git-Fehler (nicht bewertbar)."""
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "diff",
                "--name-only",
                "--diff-filter=A",
                bereich,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return [z.strip() for z in out.stdout.splitlines() if z.strip()]


def befunde_fuer(dateien: list[str], repo_root: Path) -> list[str]:
    """Kernlogik, git-frei und damit drillbar: neue Module ohne Test-Spur."""
    befunde = []
    for pfad in dateien:
        if not ist_pruefpflichtig(pfad):
            continue
        stem = Path(pfad).stem
        if not hat_test_spur(stem, repo_root):
            befunde.append(pfad)
    return befunde


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Neue tools/scripts-Module ohne Test melden (advisory)"
    )
    ap.add_argument(
        "--range",
        required=True,
        help="git-Diff-Bereich, z.B. origin/main...HEAD",
    )
    ap.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repo-Wurzel (Default: Repo dieses Skripts)",
    )
    args = ap.parse_args()
    root = Path(args.repo_root)

    dateien = hinzugefuegte_dateien(args.range, root)
    if dateien is None:
        print(
            "⚠ git-Diff nicht bestimmbar — NICHT bewertbar (nie als sauber werten).",
            file=sys.stderr,
        )
        return 2

    befunde = befunde_fuer(dateien, root)
    if not befunde:
        print(
            "✅ Neuzugaenge: jedes neue Modul hat eine Test-Spur (oder es gab keine)."
        )
        return 0

    print(
        "⚠ Neue Module OHNE Test-Spur (Retro-Muster untested-tool-module-green-gate):"
    )
    for b in befunde:
        print(
            f"   - {b} (weder test_{Path(b).stem}.py noch Erwaehnung in einer Testdatei)"
        )
    print(
        "   → Testdatei nachliefern ODER im PR kurz begruenden, warum nicht"
        " (Fehlalarm-Feedback fliesst in die Kalibrierung, das Gate ist advisory)."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
