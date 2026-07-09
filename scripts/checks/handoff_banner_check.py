#!/usr/bin/env python3
"""handoff_banner_check.py — CI-Gate `handover-stale-vor-merge` (Retro f5e1d F-S3/F-P3).

Problem: statische Handoff-/Übergabe-Dokumente frieren beim Commit ein, während
das lebende Tracking-Issue weiterläuft — Folge-Sessions lesen dann einen falschen
Stand (Retro 2026-07-04 f5e1d: Handoff sagte „alle Gates OFFEN", Issue #913 hatte
G2/G4/G7 längst abgehakt; Slug ×2 → Gate-Pflicht laut tools/retro_kpis.py, #913).

Gate: jede geänderte/neue HANDOFF-*.md muss in den ersten HEAD_LINES Zeilen ein
Live-Status-Banner tragen, das auf die lebende Statusquelle verweist:

    Live-Status: ... #<nummer>    oder    Live-Status: ... <issue-url>

Aufruf:  handoff_banner_check.py <datei> [<datei> ...]
Exit 0 = alle Dateien tragen das Banner · Exit 1 = mindestens eine ohne
Exit 2 = Usage-Fehler (keine Argumente). Nur stdlib, kein Netz.
Verdrahtet in .github/workflows/handoff-banner-gate.yml;
Tests: tools/tests/test_handoff_banner_check.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HEAD_LINES = 30
BANNER_RE = re.compile(r"Live-Status:.*(?:#\d+|https?://\S+)")

FAIL_HINT = (
    "statische Handoffs führen keinen Gate-Stand — Live-Status-Banner Pflicht, "
    "siehe Retro f5e1d F-P3.\n"
    "  Fix: in den ersten %d Zeilen eine Zeile ergänzen wie\n"
    "  > **Live-Status: <owner>/<repo>#<issue>** — der Stand in diesem Dokument "
    "ist eingefroren; lebende Quelle ist das Issue." % HEAD_LINES
)


def has_banner(path: Path) -> bool:
    """True, wenn die ersten HEAD_LINES Zeilen ein Live-Status-Banner enthalten."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if i >= HEAD_LINES:
                return False
            if BANNER_RE.search(line):
                return True
    return False


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: handoff_banner_check.py <HANDOFF-*.md> [...]", file=sys.stderr)
        return 2
    failed: list[str] = []
    for name in argv:
        path = Path(name)
        if not path.is_file():
            # Gelöschte/umbenannte Dateien sind kein Gate-Fall (Caller filtert
            # per --diff-filter=ACMR; hier defensiv doppelt abgesichert).
            print(f"SKIP  {name} (existiert nicht — vermutlich gelöscht)")
            continue
        if has_banner(path):
            print(f"PASS  {name} (Live-Status-Banner in den ersten {HEAD_LINES} Zeilen)")
        else:
            print(f"FAIL  {name} — kein Live-Status-Banner in den ersten {HEAD_LINES} Zeilen")
            failed.append(name)
    if failed:
        print(f"\n⛔ Gate handover-stale-vor-merge: {len(failed)} Datei(en) ohne Banner —")
        print(FAIL_HINT)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
