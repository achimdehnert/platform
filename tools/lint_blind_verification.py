#!/usr/bin/env python3
"""Findet Pruefschritte, die nichts belegen — und Pipelines, die unter pipefail brechen.

Beide Fehler haben dieselbe Gestalt: `<befehl> | grep -q <muster>`.

GATE_HEADER (KONZ-038 D8):
  "slug": "verification-proves-absence-not-success"
  "mode": "advisory"
  "owner": "achim"
  "last_drill_pass": "2026-09-02"
  "evidence": "tools/tests/test_lint_blind_verification.py"

1. Als PRUEFUNG belegt das nur die An-/Abwesenheit eines Musters im AUSGABETEXT,
   nicht den Erfolg des Befehls. Ein vollstaendig gescheiterter Befehl, dessen
   Fehlermeldung das Muster nicht enthaelt, gilt als gruen.
   Realfall 2026-08-21 (chat-hub): `git fetch --dry-run | grep -qi 'moved|redirect'`
   stellte die Remotes auf ein Repo, das es nicht gab, und meldete Erfolg.

2. Unter `set -o pipefail` steigt `grep -q` beim ersten Treffer aus, der linke
   Befehl bekommt SIGPIPE, und die Pipeline gilt als FEHLGESCHLAGEN — je nach
   Puffergroesse mal so, mal so. Realfall am selben Tag: `tar -tzf ... | grep -qx`
   verwarf ein vollstaendiges Archiv als "Datei fehlt".

Sicher ist dieselbe Pruefung mit Here-String, weil dort keine Pipeline steht:
    LISTE="$(tar -tzf "$ARCHIVE")"
    grep -qxF "$datei" <<<"$LISTE"

Aufruf:  python3 tools/lint_blind_verification.py [pfad ...] [--strict]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MUSTER = re.compile(r"\|\s*(?:command\s+)?grep\b[^|;&\n]*?\s-[a-zA-Z]*q")
SHEBANG = re.compile(rb"^#!.*\b(bash|sh|zsh)\b")


def ist_shell(p: Path) -> bool:
    if p.suffix in {".sh", ".bash"}:
        return True
    if p.suffix:
        return False
    try:
        return bool(SHEBANG.match(p.open("rb").read(80)))
    except OSError:
        return False


def pruefe(p: Path) -> list[tuple[int, str]]:
    treffer = []
    for nr, zeile in enumerate(
        p.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        nackt = zeile.split("#", 1)[0]
        if MUSTER.search(nackt):
            treffer.append((nr, zeile.strip()))
    return treffer


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    ziele = [a for a in argv if not a.startswith("--")] or ["."]
    dateien: list[Path] = []
    for z in ziele:
        p = Path(z)
        dateien.extend(
            q
            for q in (p.rglob("*") if p.is_dir() else [p])
            if q.is_file() and ".git/" not in str(q) and ist_shell(q)
        )

    gesamt = 0
    for f in sorted(set(dateien)):
        for nr, zeile in pruefe(f):
            gesamt += 1
            print(f"{f}:{nr}: blinde Pruefung / SIGPIPE-Falle — {zeile}")

    if gesamt:
        print(f"\n{gesamt} Fund(e). Ausgabe in eine Variable ziehen und dort greppen:")
        print('  LISTE="$(<befehl>)" ; grep -qxF "<muster>" <<<"$LISTE"')
        print(
            "Als Pruefung stattdessen den Exit-Code messen: `<befehl> >/dev/null 2>&1 || abbruch`"
        )
    else:
        print(f"keine Funde in {len(set(dateien))} Shell-Datei(en).")
    return 1 if (gesamt and strict) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
