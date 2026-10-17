#!/usr/bin/env python3
"""Claude Code Stop hook — Owner-Kürzel mit „go“ ohne Gegenzeile im Artefakt.

Charta Art. 10: Jede Freigabe bekommt im selben Zug ein durables Artefakt. In der
Sitzung 835f30 blieben „MA go“ und „FR go“ ohne Zeile in Issue, PR oder Memory
(Retro 835f30 Befund 18); derselbe Slug stand schon in Retro 767d40-incr
(platform#4062).

WAS DER SCANNER MISST
---------------------
Nur die **letzte getippte Owner-Nachricht** zählt — sie ist der Zug, an dessen
Ende der Hook läuft. Jedes `<KÜRZEL> go` darin (`MA go`, `Z10 go`, `GR2 go`)
braucht danach einen Schreibzugriff, der das Kürzel nennt:

* `gh`/`lotse-gh` `issue|pr create|comment|edit|review` oder `gh api` auf
  Issues/PRs — der Befehl selbst oder eine Datei, die per Name im Befehl steht
  (`--body-file`, `-F`) und vorher geschrieben wurde,
* ein GitHub-MCP-Schreibwerkzeug,
* Write/Edit in die Memory, ein Handover-Fragment oder eine Retro, oder ein
  Shell-Schreibzugriff (`>>`, `>`, `tee`) dorthin.

WAS ER BEWUSST NICHT MISST
--------------------------
* Ältere Owner-Nachrichten. Ihr Zug ist vorbei; wer sie jeden Turn neu meldet,
  erzeugt Rauschen, und ein Gate, das nervt, wird abgeschaltet statt befolgt.
* Ob die Zeile inhaltlich passt. Der Scanner prüft Nennung, nicht Wahrheit.

Modus `advisory` (Meldephase, platform#4061). Abschalten: `KUERZEL_GATE=aus`.
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
    "slug": "kuerzel-ohne-artefakt-bezug",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-10-17",
    "evidence": "tools/claude-hooks/tests/test_kuerzel_ohne_gegenzeile_scanner.py",
}

#: Ein Freigabe-Kürzel: Großbuchstabe, bis zu drei weitere Großbuchstaben/Ziffern.
KUERZEL_GO = re.compile(r"(?<![\w])([A-Z][A-Z0-9]{0,3})\s+go\b")

#: Eingeschleuste Blöcke in Nutzer-Nachrichten sind keine Owner-Worte.
_EINGESCHLEUST = re.compile(
    r"<(system-reminder|pasted_content)\b[^>]*>.*?</\1[^>]*>", re.S
)

#: Bash-Befehle, die in Issue oder PR schreiben.
GH_SCHREIBEN = re.compile(
    r"\b(?:gh|lotse-gh(?:\s+\S+)?)\s+(?:issue|pr)\s+(?:create|comment|edit|review)\b"
    r"|\bgh\s+api\b[^\n]*\b(?:comments|issues|pulls)\b"
)

#: GitHub-MCP-Werkzeuge mit Schreibwirkung.
MCP_SCHREIBEN = re.compile(
    r"^mcp__github__(?:create_issue|add_issue_comment|update_issue"
    r"|create_pull_request(?:_review)?|create_or_update_file|push_files)$"
)

#: Dateien, die selbst ein durables Artefakt sind.
ARTEFAKT_PFAD = re.compile(
    r"/\.claude/projects/[^/]+/memory/|(?:^|/)docs/handover\.d/|(?:^|/)docs/retros/"
)

#: Shell-Schreibweg in eine solche Datei (Realfall 835f30: `printf … >> memory/…`).
SHELL_SCHREIBEN = re.compile(r">>?|\btee\b")


def _text(inhalt) -> str:
    if isinstance(inhalt, str):
        return inhalt
    if isinstance(inhalt, list):
        return " ".join(
            b.get("text", "")
            for b in inhalt
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _ist_owner_nachricht(e: dict, mit_herkunft: bool) -> bool:
    if e.get("type") != "user" or e.get("isMeta") or e.get("isCompactSummary"):
        return False
    if mit_herkunft and (e.get("origin") or {}).get("kind") != "human":
        return False
    inhalt = (e.get("message") or {}).get("content")
    if isinstance(inhalt, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in inhalt
    ):
        return False
    return True


def _tool_uses(e: dict):
    if e.get("type") != "assistant":
        return
    inhalt = (e.get("message") or {}).get("content")
    if not isinstance(inhalt, list):
        return
    for c in inhalt:
        if isinstance(c, dict) and c.get("type") == "tool_use":
            yield str(c.get("name", "")), c.get("input") or {}


def offene_kuerzel(eintraege: list[dict]) -> list[str]:
    """Kürzel der letzten Owner-Nachricht, die danach kein Artefakt nennt."""
    mit_herkunft = any(
        "origin" in e for e in eintraege if isinstance(e, dict) and e.get("type") == "user"
    )
    letzte = None
    for i, e in enumerate(eintraege):
        if isinstance(e, dict) and _ist_owner_nachricht(e, mit_herkunft):
            letzte = i
    if letzte is None:
        return []
    owner_text = _EINGESCHLEUST.sub(
        " ", _text((eintraege[letzte].get("message") or {}).get("content"))
    )
    kuerzel = list(dict.fromkeys(KUERZEL_GO.findall(owner_text)))
    if not kuerzel:
        return []

    geschrieben: dict[str, str] = {}
    belege: list[str] = []
    for e in eintraege[letzte + 1 :]:
        for name, eingabe in _tool_uses(e):
            if name in ("Write", "Edit"):
                pfad = str(eingabe.get("file_path", ""))
                text = str(eingabe.get("content") or eingabe.get("new_string") or "")
                geschrieben[pfad] = geschrieben.get(pfad, "") + "\n" + text
                if ARTEFAKT_PFAD.search(pfad):
                    belege.append(text)
            elif MCP_SCHREIBEN.match(name):
                belege.append(json.dumps(eingabe, ensure_ascii=False))
            elif name == "Bash":
                befehl = str(eingabe.get("command", ""))
                if ARTEFAKT_PFAD.search(befehl) and SHELL_SCHREIBEN.search(befehl):
                    belege.append(befehl)
                    continue
                if not GH_SCHREIBEN.search(befehl):
                    continue
                anhang = [
                    t
                    for p, t in geschrieben.items()
                    if len(Path(p).name) >= 5 and Path(p).name in befehl
                ]
                belege.append("\n".join([befehl, *anhang]))

    def genannt(k: str) -> bool:
        muster = re.compile(rf"(?<![\w]){re.escape(k)}(?![\w])")
        return any(muster.search(b) for b in belege)

    return [k for k in kuerzel if not genannt(k)]


def _lade(pfad: Path) -> list[dict] | None:
    try:
        zeilen = pfad.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    eintraege = []
    for zeile in zeilen:
        try:
            obj = json.loads(zeile)
        except ValueError:
            continue
        if isinstance(obj, dict):
            eintraege.append(obj)
    return eintraege


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(event, dict) or event.get("stop_hook_active"):
        return 0
    if os.environ.get("KUERZEL_GATE", "").lower() == "aus":
        return 0
    pfad = event.get("transcript_path") or ""
    if not pfad:
        return 0
    eintraege = _lade(Path(pfad))
    if not eintraege:
        return 0

    offen = offene_kuerzel(eintraege)
    if not offen:
        return 0

    grund = ", ".join(f"{k} go" for k in offen)
    gate_hits.notiere(
        GATE_HEADER["slug"],
        grund,
        turn=grund,
        session=str(event.get("session_id") or ""),
        modus="advisory",
    )
    print(
        f"🧾 kuerzel-ohne-artefakt-bezug: {grund} hat in diesem Zug keine Gegenzeile "
        "in Issue, PR, Memory oder Handover.\n"
        "Charta Art. 10: jede Freigabe bekommt im selben Zug ein durables Artefakt — "
        "das Kürzel wörtlich, mit Datum und Kanal.\n"
        "(Gate kuerzel-ohne-artefakt-bezug, advisory, platform#4062.)",
        file=sys.stderr,
    )
    return 0


def main_sicher() -> int:
    """`main()` unter dem Hook-Vertrag: Exit 0 immer."""
    try:
        return main()
    except Exception as exc:  # noqa: BLE001 — Hook-Vertrag: nie blockieren
        print(
            f"kuerzel_ohne_gegenzeile_scanner: {type(exc).__name__}: {exc}"[:400],
            file=sys.stderr,
        )
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
