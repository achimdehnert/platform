#!/usr/bin/env python3
"""Räumt das verschachtelte ``~/.secrets/.secrets/`` auf — dry-run als Standard.

Hintergrund
-----------
``infra/lib/secrets.py`` ist der erklärte Resolver und löst gegen
``Path.home() / ".secrets"`` auf — die **obere** Ebene. Ein Verzeichnis darunter
ist in Resolver wie Inventar nirgends vorgesehen. Trotzdem liegt dort:

* **6 Unikate**, die es oben nicht gibt — darunter ``fritz-nas``, das
  ``tax-hub/scripts/sync-scans-to-paperless.py`` **oben** sucht und deshalb
  aktuell nicht findet.
* **5 veraltete Kopien** rotierter Secrets. In allen fünf Fällen ist die obere
  Datei die neuere; wer unten liest, bekommt abgelaufene Zugangsdaten.
* **3 abgelöste Loader** (``load_secrets.py``, ``env_loader.py``,
  ``deploy_env_loader.sh``) — laut Inventar seit 2026-04-03 ersetzt.

Das Skript entscheidet **nicht selbst**, was neuer ist: es vergleicht Inhalte
per SHA-256 und behandelt jede Abweichung als Konflikt, den es meldet statt
aufzulösen. Nur eindeutige Fälle werden vorgeschlagen.

Werte werden nie ausgegeben — ausschließlich Namen und Fingerabdrücke.

Aufruf
------
    python3 tools/secrets-flatten.py            # zeigt den Plan, ändert nichts
    python3 tools/secrets-flatten.py --apply    # führt ihn aus
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

SECRETS = Path.home() / ".secrets"
NESTED = SECRETS / ".secrets"

#: Laut infra/secrets-inventory.yaml seit 2026-04-03 durch infra/lib/secrets.py
#: ersetzt. Werden verworfen, nicht nach oben gezogen.
ABGELOEST = {"load_secrets.py", "env_loader.py", "deploy_env_loader.sh"}


def fingerprint(path: Path) -> str | None:
    try:
        return (
            f"{path.stat().st_size}·{hashlib.sha256(path.read_bytes()).hexdigest()[:8]}"
        )
    except PermissionError:
        return None


def plan() -> tuple[list, list, list, list]:
    """(hochziehen, verwerfen_kopie, verwerfen_abgeloest, konflikte)"""
    hoch, kopie, abgeloest, konflikt = [], [], [], []

    for p in sorted(NESTED.iterdir()):
        if not p.is_file():
            continue
        oben = SECRETS / p.name

        if p.name in ABGELOEST:
            abgeloest.append(p.name)
        elif not oben.exists():
            hoch.append(p.name)
        else:
            fu, fo = fingerprint(p), fingerprint(oben)
            if fu is None or fo is None:
                konflikt.append((p.name, "nicht lesbar", fo or "?", fu or "?"))
            elif fu == fo:
                kopie.append(p.name)
            else:
                # Bewusst NICHT nach mtime entscheiden: eine Kopie kann neuer
                # sein und trotzdem den aelteren Wert tragen.
                konflikt.append((p.name, "Inhalte verschieden", fo, fu))
    return hoch, kopie, abgeloest, konflikt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Plan wirklich ausführen")
    args = parser.parse_args()

    if not NESTED.is_dir():
        print(f"{NESTED} existiert nicht — nichts zu tun.")
        return 0

    hoch, kopie, abgeloest, konflikt = plan()

    print(f"\n{NESTED}\n")
    print(f"  hochziehen (oben nicht vorhanden) : {len(hoch)}")
    for n in hoch:
        print(f"      + {n}")
    print(f"  verwerfen (inhaltsgleiche Kopie)  : {len(kopie)}")
    for n in kopie:
        print(f"      - {n}")
    print(f"  verwerfen (abgeloester Loader)    : {len(abgeloest)}")
    for n in abgeloest:
        print(f"      - {n}")
    print(f"  KONFLIKT (Hand anlegen)           : {len(konflikt)}")
    for n, grund, fo, fu in konflikt:
        print(f"      ! {n:<30} {grund}")
        print(f"        oben {fo}   unten {fu}")

    if konflikt:
        print(
            "\n  Konflikte werden NICHT angefasst. Die obere Datei ist in allen bisher"
        )
        print(
            "  geprueften Faellen die neuere — pruefen, dann die untere von Hand loeschen."
        )

    if not args.apply:
        print("\nDRY RUN — nichts geaendert. Ausfuehren mit --apply\n")
        return 0

    for n in hoch:
        shutil.move(str(NESTED / n), str(SECRETS / n))
        print(f"  hochgezogen: {n}")
    for n in kopie + abgeloest:
        (NESTED / n).unlink()
        print(f"  entfernt:    {n}")

    rest = [p.name for p in NESTED.iterdir()]
    if rest:
        print(
            f"\n{NESTED} bleibt bestehen — {len(rest)} Eintrag/Eintraege offen: {', '.join(sorted(rest))}"
        )
    else:
        NESTED.rmdir()
        print(f"\n{NESTED} entfernt — leer.")
    print(
        "\nDanach pruefen: tax-hub/scripts/sync-scans-to-paperless.py findet ~/.secrets/fritz-nas\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
