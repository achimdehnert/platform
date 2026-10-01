#!/usr/bin/env python3
"""Claude Code PreToolUse(Bash) hook — `gh`-Poll-Schleife ohne Frist (dev-hub#404 Baustein C2).

Realfall (2026-09-28): ein Scratchpad-Skript beobachtete Deploys nach einer
Merge-Welle mit `while true; do … gh pr view …; gh run list …; sleep 60; done`
und endete nur, wenn ALLE Deploys fertig waren. Ein Deploy, der nie fertig
wird, haelt die Schleife ewig am Leben. Die gh-Mitschrift seit 2026-09-28
14:08Z zaehlt 306 Aufrufe aus genau diesem Skript — Rang 4 aller Aufrufer, an
einem Tag, an dem das GitHub-Kontingent erschoepft war.

Muster: eine `while`/`until`-Schleife ruft `gh` auf und traegt keine Frist —
weder ein vorangestelltes `timeout <n>`, noch `$SECONDS`, noch einen
`date +%s`-Vergleich, noch eine als Frist benannte Grenze (`deadline`,
`frist`, `max_versuche`, `MAX_…`). Eine Abbruchbedingung "wenn fertig" ist
KEINE Frist: sie greift genau dann nicht, wenn etwas haengt — und das ist der
Fall, fuer den die Frist da ist.

Gemeldet wird nur ein Aufruf, der im HINTERGRUND laeuft (`run_in_background`,
`nohup`, abschliessendes `&`): im Vordergrund begrenzt der Tool-Timeout (max.
10 min) jede Schleife, das ist eine Frist. Kalibrierung ueber die Bash-Aufrufe
aller Sitzungen der letzten 7 Tage (2026-09-29): 71 fristlose gh-Schleifen,
davon 58 im Hintergrund — die Meldung trifft also ein alltaegliches Muster,
keinen Einzelfall.

Gelesen wird der Befehl selbst und, wenn er ein Skript startet
(`bash x.sh`, `sh x.sh`, `./x.sh`), dieses Skript: der Realfall steckte in
einer Datei, der Befehl selbst war nur `bash …/deploy-watch.sh`.

Vertrag wie `cd_fehlschlag_ketten_scanner.py`: PreToolUse-Event-JSON auf
stdin, IMMER Exit 0, Modus **advisory** — Klartext-Hinweis auf stdout, kein
Block. stdlib-only.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_hits  # noqa: E402  (haengt am sys.path oben)

GATE_HEADER = {
    "slug": "gh-poll-schleife-ohne-frist",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-09-29",
    "evidence": "tools/claude-hooks/tests/test_gh_poll_ohne_frist_scanner.py",
}

#: Groesste Skriptdatei, die gelesen wird — ein Poll-Skript ist klein, alles
#: darueber ist etwas anderes und der Hook darf den Aufruf nicht verzoegern.
SKRIPT_MAX_BYTES = 64 * 1024

#: `while read …` iteriert ueber eine endliche Eingabe und pollt nicht — ohne
#: diese Ausnahme waren in der Kalibrierung die meisten Treffer Pipelines wie
#: `gh repo list … | while read r; do gh issue view …; done`.
_SCHLEIFE = re.compile(
    r"(?:^|[;&|\n({]\s*|\bdo\s+|\bthen\s+|\s-c\s+['\"]\s*)(?:while|until)\b(?!\s+(?:IFS=\S*\s+)?read\b)"
)
_GH = re.compile(r"(?<![\w/.-])gh\s+(?:pr|api|run|issue|repo|release|workflow)\b")
_FRIST = re.compile(
    r"(?:^|[\s;&|(])timeout\s+-?\w*\s*\d"
    r"|\$\{?SECONDS\b"
    r"|\bdate\s+\+%s\b"
    r"|\b(?:deadline|frist|max_?versuche|max_?tries)\b"
    r"|\$\{?MAX_\w+",
    re.I,
)
_SHELLS = {"bash", "sh", "zsh", "dash"}
_HINTERGRUND = re.compile(r"\bnohup\b|(?<![&>|])&\s*$|(?<![&>|])&\s*(?:\n|;)")


def gestartete_skripte(command: str) -> list[Path]:
    """Skriptdateien, die der Befehl direkt startet (`bash x.sh`, `./x.sh`)."""
    try:
        worte = shlex.split(command, comments=True)
    except ValueError:
        return []
    pfade: list[Path] = []
    for i, w in enumerate(worte):
        kandidat = None
        if Path(w).name in _SHELLS and i + 1 < len(worte) and not worte[i + 1].startswith("-"):
            kandidat = worte[i + 1]
        elif w.endswith(".sh") and (i == 0 or worte[i - 1] in {";", "&&", "||", "timeout"}):
            kandidat = w
        if kandidat:
            p = Path(kandidat).expanduser()
            if p.is_file():
                pfade.append(p)
    return pfade


def _lies(p: Path) -> str:
    try:
        if p.stat().st_size > SKRIPT_MAX_BYTES:
            return ""
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def ohne_frist(text: str) -> bool:
    """`True`, wenn `text` eine gh-Poll-Schleife ohne jede Frist enthaelt."""
    return bool(_SCHLEIFE.search(text) and _GH.search(text) and not _FRIST.search(text))


def befund(command: str) -> str | None:
    """Wo die fristlose Schleife steht: `befehl` oder der Skriptname."""
    if _FRIST.search(command):
        # Ein `timeout 1800 bash x.sh` begrenzt auch das Skript.
        return None
    if ohne_frist(command):
        return "befehl"
    for p in gestartete_skripte(command):
        if ohne_frist(_lies(p)):
            return p.name
    return None


def im_hintergrund(tool_input: dict) -> bool:
    """Laeuft der Aufruf ohne Tool-Timeout weiter?"""
    if tool_input.get("run_in_background") is True:
        return True
    return bool(_HINTERGRUND.search(str(tool_input.get("command") or "")))


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(event, dict):
        return 0
    tool_name = event.get("tool_name")
    if tool_name and tool_name != "Bash":
        return 0
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    if not im_hintergrund(tool_input):
        return 0
    ort = befund(command)
    if not ort:
        return 0

    gate_hits.notiere(
        GATE_HEADER["slug"],
        ort,
        turn=command[:400],
        session=str(event.get("session_id") or ""),
        modus="advisory",
    )
    wo = "im Befehl" if ort == "befehl" else f"im gestarteten Skript `{ort}`"
    print(
        f"⚠ gh-poll-schleife-ohne-frist: {wo} ruft eine `while`/`until`-Schleife "
        "`gh` auf, ohne Frist (kein `timeout <n>`, kein `$SECONDS`-/`date +%s`-"
        "Vergleich). \"Bis fertig\" ist keine Frist — haengt ein Lauf, pollt die "
        "Schleife ewig und frisst GitHub-Kontingent (Realfall 2026-09-28: 306 "
        "Aufrufe aus einem Deploy-Waechter, dev-hub#404). Sichere Form: "
        "`timeout 1800 bash x.sh` oder `ende=$((SECONDS+1800)); while [ $SECONDS "
        "-lt $ende ]; do …`. (Gate gh-poll-schleife-ohne-frist, advisory, "
        "blockiert diesen Aufruf nicht.)"
    )
    return 0


def main_sicher() -> int:
    """`main()` unter dem Hook-Vertrag: Exit 0 immer."""
    try:
        return main()
    except Exception as exc:  # noqa: BLE001 — Hook-Vertrag: nie blockieren
        print(f"gh_poll_ohne_frist_scanner: {type(exc).__name__}: {exc}"[:400], file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
