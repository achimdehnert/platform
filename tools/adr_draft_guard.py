#!/usr/bin/env python3
"""tools/adr_draft_guard.py — Gate: ein ADR-Entwurf darf `main` nie erreichen (ADR-228).

ADR-228 erlaubt Entwuerfe (`docs/adr/ADR-DRAFT-*.md`, `id: ADR-000`) ausdruecklich
waehrend der Arbeit an einem PR — das ist der vorgesehene Zustand. Verboten ist nur,
dass ein Entwurf im Zielbaum landet, der nach `main` geht: dort muss die Nummer
laengst vergeben sein (`python3 tools/adr_allocate.py --apply`, ADR-228).

Dieses Skript prueft immer denselben Zustand — den aktuell ausgecheckten Baum —,
liefert aber je nach Aufrufkontext unterschiedliche Konsequenzen:

  * ohne `--gate`  : SUGGEST/Report, Exit 0 auch bei Funden
  * mit `--gate`   : Exit 1 bei Funden

**Wo `--gate` gesetzt wird, entscheidet ueber Praevention oder Obduktion.**
Erste Fassung gatete nur beim `push` auf `main` — da IST der Entwurf aber schon
gelandet, und CI meldet nur noch, dass es passiert ist. Ohne Merge-Queue
(`main-required-checks` kennt nur `required_status_checks` + `pull_request`)
ist der PR-Lauf der einzige Hebel VOR dem Merge. Deshalb gatet der PR-Lauf
gegen `main` ebenfalls.

Ein roter Check waehrend der Arbeit am Entwurf ist dabei kein Defekt, sondern
das Signal "noch nicht mergebar". Er wird gruen, sobald der Autor die Nummer
vergibt — und genau das ist ADR-228: die Nummer faellt zuletzt.

Die Unterscheidung "PR-Zweig ok, main verboten" gehoert nicht in dieses
Skript, sondern in den aufrufenden Workflow-Schritt (Ereignistyp + Ziel-Branch,
siehe .github/workflows/adr-validate.yml) — das Skript selbst kennt nur den
Dateibestand, nicht den Kontext, in dem er geprueft wird.

Findet zwei Verstoss-Arten:
  * eine Datei `ADR-DRAFT-*.md`
  * ein ADR mit `id: ADR-000` im Frontmatter (auch unter numeriertem Dateinamen —
    ein liegen gebliebener Platzhalter waere sonst unsichtbar)

Usage:
    python3 tools/adr_draft_guard.py [--adr-dir docs/adr] [--gate]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DIR_DEFAULT = REPO_ROOT / "docs" / "adr"
FIX_COMMAND = "python3 tools/adr_allocate.py --apply"

ID_LINE_RE = re.compile(r"(?m)^id:\s*(\S+)\s*$")


def find_findings(adr_dir: Path) -> list[str]:
    """Liefert eine Liste menschenlesbarer Fund-Meldungen (leer = sauber)."""
    findings: list[str] = []

    for f in sorted(adr_dir.glob("ADR-DRAFT-*.md")):
        findings.append(f"Entwurfsdatei ohne vergebene Nummer: {f.name}")

    for f in sorted(adr_dir.glob("ADR-*.md")):
        if f.name.startswith("ADR-DRAFT-"):
            continue  # oben bereits erfasst
        text = f.read_text(encoding="utf-8", errors="replace")
        m = ID_LINE_RE.search(text)
        if m and m.group(1) == "ADR-000":
            findings.append(
                f"Platzhalter-ID 'id: ADR-000' liegen geblieben in: {f.name}"
            )

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adr-dir", default=str(ADR_DIR_DEFAULT), help="Pfad zu docs/adr")
    ap.add_argument(
        "--gate",
        action="store_true",
        help="Exit 1 bei Funden (fuer den main-Lauf). Ohne Flag: SUGGEST, immer Exit 0.",
    )
    args = ap.parse_args()

    adr_dir = Path(args.adr_dir)
    if not adr_dir.is_dir():
        print(f"FEHLER: ADR-Verzeichnis nicht gefunden: {adr_dir}", file=sys.stderr)
        return 1

    findings = find_findings(adr_dir)

    if not findings:
        print("✓ Kein ADR-Entwurf, keine liegen gebliebene Platzhalter-ID im Zielbaum.")
        return 0

    print(f"🚫 {len(findings)} Fund(e) — ADR-Entwurf/Platzhalter im Zielbaum:")
    for msg in findings:
        print(f"  - {msg}")
    print(f"Fix: {FIX_COMMAND}")

    if args.gate:
        return 1

    print("SUGGEST-Modus (kein --gate) — auf einem PR-Zweig ist ein Entwurf normal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
