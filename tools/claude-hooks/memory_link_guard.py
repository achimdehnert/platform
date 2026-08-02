#!/usr/bin/env python3
"""Stop-Hook: meldet kaputte Memory-Verweise in dem Zug, der sie erzeugt hat.

Warum Stop und nicht SessionStart
---------------------------------
Memory-Schaden entsteht beim **Schreiben**, nicht beim Starten. Realfall
2026-07-31: eine parallel laufende Sitzung schrieb um 15:10 ein Memory mit einem
Verweis auf einen Namen, der um 10:43 zusammengelegt worden war. Ein
SessionStart-Hook hätte in jener Sitzung kurz vor 15:00 gefeuert — also *bevor*
der schlechte Verweis existierte — und danach geschwiegen. Gefunden wurde es
zwei Stunden später nur durch einen Lauf von Hand.

Vorbedingung statt Dauerlauf
----------------------------
833 Dateien nach jeder Antwort zu scannen wäre Verschwendung. Der Hook prüft
zuerst per ``git status``, ob dieser Zug überhaupt unter ``projects/*/memory/``
geschrieben hat — möglich, seit das Verzeichnis versioniert ist. Ist dort nichts
offen, endet er nach einem git-Aufruf. Bewusst ``git status`` und nicht mtime:
mtime ändert sich auch ohne Inhaltsänderung (siehe Memory ``mtime_not_dirty``).

Vertrag: Stop-Event-JSON auf stdin, **immer Exit 0** — ein Melder darf nie
blockieren. Funde gehen als ``hookSpecificOutput.additionalContext`` nach stdout.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJEKTE = Path.home() / ".claude" / "projects"
CLAUDE_REPO = Path.home() / ".claude"
PRUEFER = Path(__file__).with_name("memory_link_check.py")


def geaenderte_memory_dirs() -> list[Path]:
    """Memory-Verzeichnisse mit offenen Änderungen — leer heißt: nichts zu tun."""
    try:
        roh = subprocess.run(
            ["git", "-C", str(CLAUDE_REPO), "status", "--porcelain", "--", "projects/"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if roh.returncode != 0:
        return []

    dirs: set[Path] = set()
    for zeile in roh.stdout.splitlines():
        # Format: "XY <pfad>"; bei Umbenennung "XY alt -> neu"
        pfad = zeile[3:].split(" -> ")[-1].strip().strip('"')
        teile = Path(pfad).parts
        if "memory" not in teile:
            continue
        idx = teile.index("memory")
        dirs.add(CLAUDE_REPO.joinpath(*teile[: idx + 1]))
    return sorted(d for d in dirs if d.is_dir())


def pruefe(dirs: list[Path]) -> list[str]:
    """Harte Funde je Verzeichnis, als fertige Meldezeilen."""
    meldungen: list[str] = []
    for d in dirs:
        try:
            lauf = subprocess.run(
                [sys.executable, str(PRUEFER), "--root", str(d), "--json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if lauf.returncode == 2:  # Werkzeugfehler, kein Befund
            continue
        try:
            bericht = json.loads(lauf.stdout)
        except json.JSONDecodeError:
            continue
        for det in bericht.get("details", []):
            for f in det.get("funde", []):
                if f.get("art") == "forward-ref":
                    continue
                meldungen.append(f"  {f['art']:<15} {f['datei']:<52} {f['detail']}")
    return meldungen


def main() -> int:
    # Der Client verlangt hookSpecificOutput.hookEventName ("Stop"|"SubagentStop");
    # ohne das Feld verwirft er die Ausgabe und zeigt den rohen Schema-Dump.
    event = "Stop"
    try:
        daten = json.load(sys.stdin)
        if isinstance(daten, dict) and daten.get("hook_event_name") == "SubagentStop":
            event = "SubagentStop"
    except (json.JSONDecodeError, ValueError):
        pass

    if not PRUEFER.is_file():
        return 0

    dirs = geaenderte_memory_dirs()
    if not dirs:
        return 0

    meldungen = pruefe(dirs)
    if not meldungen:
        return 0

    text = (
        "⚠️ memory-link-guard: dieser Zug hat Memory-Dateien geschrieben und "
        f"dabei {len(meldungen)} harte(n) Verweis-Fund erzeugt:\n"
        + "\n".join(meldungen)
        + "\n\nEin toter Verweis entsteht meist, weil ein Ziel unter seinem "
        "Frontmatter-Namen statt seinem Dateinamen genannt wurde, oder weil das "
        "Ziel zusammengelegt/umbenannt wurde. Vorausschauende Verweise gehören "
        "in tools/claude-hooks/memory_forward_refs.tsv, nicht in die Prosa. "
        "Jetzt im selben Zug korrigieren."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": text,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
