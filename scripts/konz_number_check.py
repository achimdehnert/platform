#!/usr/bin/env python3
"""KONZ-Nummern-Guard — Eindeutigkeit + concept_id/Dateiname-Konsistenz.

Analog zu scripts/adr_next_number.py (ADR-Guard). Prüft die KONZ-Dokumente in
docs/konzepte/:

  1. **Eindeutigkeit:** keine zwei Dateien teilen dieselbe KONZ-platform-Nummer.
     (Genau diese Kollision blieb bis 2026-07-24 unentdeckt — 4x doppelt vergeben,
     aufgeräumt in #1410 — weil es keinen Gate gab.)
  2. **Konsistenz:** das `concept_id`-Frontmatter stimmt mit der Dateinamen-Nummer
     überein (KONZ-platform-NNN).

Usage:
    python3 scripts/konz_number_check.py            # Report + nächste freie Nummer
    python3 scripts/konz_number_check.py --check     # exit 1 bei Konflikten (CI)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

KONZ_DIR = Path(__file__).resolve().parent.parent / "docs" / "konzepte"
FILENAME_RE = re.compile(r"KONZ-platform-(\d{3})")
CONCEPT_ID_RE = re.compile(r"^concept_id:\s*KONZ-platform-(\d{3})\b", re.MULTILINE)


def scan(konz_dir: Path = KONZ_DIR) -> tuple[dict[int, list[Path]], list[tuple[Path, str, str]]]:
    """Return (number -> files) and a list of (file, filename_num, concept_id_num)
    for files whose concept_id does not match the filename number."""
    by_number: dict[int, list[Path]] = {}
    mismatches: list[tuple[Path, str, str]] = []
    for f in sorted(konz_dir.glob("KONZ-platform-*.md")):
        m = FILENAME_RE.search(f.name)
        if not m:
            continue
        fname_num = m.group(1)
        by_number.setdefault(int(fname_num), []).append(f)

        cid = CONCEPT_ID_RE.search(f.read_text(encoding="utf-8"))
        cid_num = cid.group(1) if cid else "(fehlt)"
        if cid_num != fname_num:
            mismatches.append((f, fname_num, cid_num))
    return by_number, mismatches


def conflicts(by_number: dict[int, list[Path]]) -> dict[int, list[Path]]:
    return {n: fs for n, fs in by_number.items() if len(fs) > 1}


def next_free(by_number: dict[int, list[Path]]) -> int:
    return (max(by_number) + 1) if by_number else 1


def main() -> int:
    check = "--check" in sys.argv[1:]
    by_number, mismatches = scan()
    dupes = conflicts(by_number)

    lines: list[str] = []
    if dupes:
        lines.append(f"🚫 KOLLISIONEN ({len(dupes)} doppelte Nummern):")
        for n in sorted(dupes):
            lines.append(f"  KONZ-platform-{n:03d}:")
            for f in dupes[n]:
                lines.append(f"    - {f.name}")
    else:
        lines.append("✅ Keine doppelten KONZ-Nummern.")

    if mismatches:
        lines.append(f"🚫 concept_id/Dateiname-ABWEICHUNG ({len(mismatches)}):")
        for f, fnum, cnum in mismatches:
            lines.append(f"    - {f.name}: Dateiname={fnum} concept_id={cnum}")
    else:
        lines.append("✅ concept_id stimmt überall mit dem Dateinamen überein.")

    lines.append(f"→ nächste freie Nummer: KONZ-platform-{next_free(by_number):03d}")
    print("\n".join(lines))

    if check and (dupes or mismatches):
        print("\nExit 1: KONZ-Guard fehlgeschlagen (siehe oben).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
