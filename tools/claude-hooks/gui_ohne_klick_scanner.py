#!/usr/bin/env python3
"""Claude Code Stop hook — GUI geaendert, aber nie angesehen.

Hausregel (Owner-Weisung 2026-08-26): geht es um **GUI oder Templates**, wird
`/ux-review` verwendet — und ein GUI-Fix ist erst fertig, wenn der Knopf im
Browser gedrueckt wurde.

WARUM EIN HOOK UND KEIN MEMORY
------------------------------
Ein Memory wird gelesen, wenn jemand danach sucht. Der Fehler passiert aber
gerade dann, wenn niemand sucht. Am 2026-08-25/26 lief ein kompletter
GUI-Durchlauf durch writing-hub, ohne dass `/ux-review` je aufgerufen wurde —
obwohl der Skill existiert, obwohl er genau diese Kette abdeckt und obwohl er
die Fehler der Vorsitzung bereits als Realfaelle nennt. Drei davon passierten
trotzdem erneut.

WAS DER SCANNER MISST
---------------------
Bedingung aus **Tool-Evidenz**, nicht aus dem Antworttext (dieselbe Lehre wie
scope_checkpoint_scanner Rev 2: gegen Nicht-Gesagtes ist ein Wortlaut-Scanner
strukturell blind):

  A  In dieser Sitzung wurde eine GUI-Datei geschrieben —
     `templates/**.html`, `views*.py`, `*.jinja2`, `static/**.js`.
  B  In derselben Sitzung lief **kein** Browser-Werkzeug
     (`mcp__playwright__browser_*`) und **kein** `/ux-review`.

A und B zusammen = der Befund. Ein einzelner Klick genuegt als Erfuellung; der
Scanner verlangt nicht den ganzen Skill, sondern den Nachweis, dass jemand
hingesehen hat.

WAS ER BEWUSST NICHT MISST
--------------------------
* **Reine Test-Aenderungen.** Wer `tests/ux/test_*.py` schreibt, hat den Klick
  bereits automatisiert — das ist der gewuenschte Zustand, kein Verstoss.
* **Reine Doku.** `docs/`, `*.md`, `AGENT_HANDOVER` sind keine GUI.
* **Loeschungen ohne Ersatz.** Wer ein Template entfernt, kann es nicht anklicken.

Modus `advisory`. Ein blockierendes Gate auf dieser Klasse wuerde jede
Template-Zeile am Sitzungsende anhalten, auch die Kommentar-Korrektur — und
ein Gate, das nervt, wird abgeschaltet statt befolgt.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import gate_hits  # type: ignore
except Exception:  # pragma: no cover - Hook darf nie am Import scheitern

    class _Still:
        @staticmethod
        def notiere(*_a, **_k):
            return None

    gate_hits = _Still()  # type: ignore

GATE_HEADER = {
    "slug": "gui-geaendert-ohne-klick",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-26",
    "evidence": "tools/claude-hooks/tests/test_gui_ohne_klick_scanner.py",
}

#: Dateien, deren Aenderung sich am Bildschirm auswirkt.
GUI_PFAD = re.compile(
    r"(?:^|/)templates/.*\.html$"
    r"|(?:^|/)views(?:_html)?\.py$"
    r"|\.jinja2$"
    r"|(?:^|/)static/.*\.(?:js|css)$",
    re.I,
)

#: Ausnahmen — hier ist der Klick schon automatisiert oder sinnlos.
KEINE_GUI = re.compile(r"(?:^|/)tests?/|(?:^|/)docs/|\.md$|conftest\.py$", re.I)

#: Werkzeuge, die belegen, dass jemand wirklich hingesehen hat.
BLICK_TOOL = re.compile(r"^mcp__playwright__browser_", re.I)

#: Der Skill selbst — als Kommando im Text oder als Skill-Aufruf.
UX_REVIEW = re.compile(r"/ux-review\b|\bux[-_]review\b", re.I)

SCHREIB_TOOLS = ("Write", "Edit", "NotebookEdit")


def _pfade_und_tools(transcript_path: Path):
    """(geaenderte GUI-Pfade, wurde geblickt?) — reiner Lesevorgang."""
    gui: list[str] = []
    geblickt = False
    try:
        fh = transcript_path.open(encoding="utf-8", errors="replace")
    except OSError:
        return gui, True  # nicht lesbar -> nicht melden (fail-open)

    with fh:
        for zeile in fh:
            try:
                obj = json.loads(zeile)
            except (json.JSONDecodeError, ValueError):
                continue
            inhalt = (obj.get("message") or {}).get("content")
            if not isinstance(inhalt, list):
                continue
            for c in inhalt:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "text" and UX_REVIEW.search(str(c.get("text", ""))):
                    geblickt = True
                if c.get("type") != "tool_use":
                    continue
                name = str(c.get("name", ""))
                if BLICK_TOOL.match(name):
                    geblickt = True
                    continue
                if name == "Skill" and UX_REVIEW.search(json.dumps(c.get("input", {}))):
                    geblickt = True
                    continue
                if name not in SCHREIB_TOOLS:
                    continue
                pfad = str((c.get("input") or {}).get("file_path", ""))
                if pfad and GUI_PFAD.search(pfad) and not KEINE_GUI.search(pfad):
                    gui.append(pfad)
    return gui, geblickt


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0
    if event.get("stop_hook_active"):
        return 0
    if os.environ.get("GUI_KLICK_GATE", "").lower() == "aus":
        return 0

    pfad = event.get("transcript_path") or ""
    if not pfad:
        return 0

    gui, geblickt = _pfade_und_tools(Path(pfad))
    if not gui or geblickt:
        return 0

    kurz = sorted({p.split("/")[-1] for p in gui})[:4]
    grund = ", ".join(kurz) + (" …" if len(set(gui)) > 4 else "")
    gate_hits.notiere(
        GATE_HEADER["slug"], grund, turn=grund, session=event.get("session_id", ""), modus="advisory"
    )
    print(
        "🖱️  gui-geaendert-ohne-klick: In dieser Sitzung wurden GUI-Dateien geschrieben "
        f"({grund}), aber kein Browser-Werkzeug lief und `/ux-review` wurde nicht "
        "aufgerufen.\n"
        "Hausregel (Owner 2026-08-26): geht es um GUI oder Templates, wird `/ux-review` "
        "verwendet — und ein GUI-Fix ist erst fertig, wenn der Knopf gedrückt wurde.\n"
        "Warum das zählt: am 2026-08-26 waren 180 Tests grün, während drei Prompt-Vorlagen "
        "beim Rendern brachen — jeder Test hatte die Render-Schicht gemockt. Gefunden hat "
        "es der erste echte Klick.\n"
        "Ein einzelner `browser_navigate` + `browser_snapshot` genügt als Nachweis. "
        "Bewusst nicht angesehen? Dann als Restlücke benennen, nicht stillschweigend.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
