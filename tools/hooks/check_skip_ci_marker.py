#!/usr/bin/env python3
"""commit-msg-Hook: literales `[skip ci]` nur mit ausdrücklichem Opt-in.

Warum das nötig ist (Retro-Befund 2026-07-31, zwei Vorfälle an einem Tag):
GitHub liest den Marker aus der Commit-Message, unabhängig davon, ob er als
Steuerbefehl gemeint ist oder ob der Text nur ÜBER ihn schreibt. Ein Commit, der
den Marker zitiert, startet keinen `pull_request`-Lauf — die Required Checks
melden nie, und der PR bleibt blockiert, **ohne rot zu werden**. Es gibt kein
Fehlsignal, nur Stillstand.

Gemessen: platform#1503 blieb so 37 h 56 min hängen (Kopf-Commit `dae483be`:
1 Check-Run; Folgecommit ohne den Wortlaut: 7 Check-Runs). platform#1559 12 min.

Absichtliche Nutzung bleibt möglich — sie braucht nur eine zweite Zeile:

    docs: nur README

    Skip-CI: absichtlich

Der Trailer macht aus einem Versehen eine Entscheidung. Genau das ist der Zweck:
nicht den Marker verbieten, sondern den unbeabsichtigten Marker.

stdlib-only, keine Abhängigkeiten.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

#: Die Marker, auf die GitHub Actions und gängige CI-Dienste reagieren.
MARKER = re.compile(
    r"\[(?:skip[ -]ci|ci[ -]skip|no[ -]ci|skip[ -]actions)\]", re.IGNORECASE
)

#: Opt-in-Trailer: eine eigene Zeile, damit sie bewusst gesetzt werden muss.
OPT_IN = re.compile(r"^Skip-CI:\s*absichtlich\s*$", re.IGNORECASE | re.MULTILINE)


def pruefe(nachricht: str) -> str | None:
    """Fehlermeldung, wenn ein Marker ohne Opt-in in der Nachricht steht."""
    # Kommentarzeilen zählen nicht — git entfernt sie, GitHub sieht sie nie.
    ohne_kommentar = "\n".join(
        z for z in nachricht.split("\n") if not z.lstrip().startswith("#")
    )
    treffer = MARKER.findall(ohne_kommentar)
    if not treffer:
        return None
    if OPT_IN.search(ohne_kommentar):
        return None
    return (
        f"Die Commit-Message enthält {treffer[0]} — GitHub überspringt daraufhin alle\n"
        "Läufe. Required Checks melden dann NIE, und der PR bleibt blockiert, ohne\n"
        "rot zu werden (Realfall 2026-07-31: 37 h 56 min an platform#1503).\n"
        "\n"
        "Wolltest du über den Marker SCHREIBEN? Dann umschreibe ihn, z.B.\n"
        '  "der Marker, der CI-Läufe überspringt"\n'
        "Im Dateitext ist er harmlos — nur die Commit-Message wird ausgewertet.\n"
        "\n"
        "Wolltest du ihn wirklich SETZEN? Dann ergänze eine eigene Zeile:\n"
        "  Skip-CI: absichtlich"
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Aufruf: check_skip_ci_marker.py <pfad-zur-commit-message>", file=sys.stderr
        )
        return 2
    fehler = pruefe(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if fehler:
        print(f"\n⛔ {fehler}\n", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
