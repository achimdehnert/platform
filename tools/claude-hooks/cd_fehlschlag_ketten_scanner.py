#!/usr/bin/env python3
"""Claude Code PreToolUse(Bash) hook — `cd`-Fehlschlag-Kette laeuft weiter (Retro b7822e B12).

Realfall (2026-09-14): ein Worktree war nach dem Merge geraeumt; die naechste
Bash-Kette begann trotzdem mit `cd $W; git switch -c …`. `cd` scheiterte
lautlos (kein `set -e`, kein `|| exit`), und `git switch -c …` lief im
platform-Haupt-Tree weiter — ein Guard fing dort den HEAD-Wechsel ab, aber das
war Glueck, kein Entwurf. Drei Memory-Vorkommen (2026-09-04 ×2, 2026-09-14),
bisher KEIN Gate (`gate_wirkung.py`/`retro_kpis.py`, Retro-Frontmatter
`recurring_findings`).

Muster: eine Kette wechselt per `cd <pfad-oder-$VAR>` in ein Worktree-/
Variablen-Ziel und haengt weitere Befehle mit `;` oder Zeilenumbruch an, ohne
Abbruch bei fehlgeschlagenem `cd` — weder `|| exit`/`|| return`, noch
`&&`-Verkettung, noch ein vorangestelltes `set -e`. Nur ZIEL-eingeschraenkt
gemeldet (`$VAR`, `~/.repo-session/…`, `/home/*/.repo-session/…`): ein
literaler Repo-Pfad wie `cd ~/github/platform && …` ist Alltag und Elternteil
eines stabilen Verzeichnisses, das nicht "unter den Fuessen" verschwindet —
genau das unterscheidet einen Worktree (per Definition raeumbar) von einem
Haupt-Tree.

Warum PreToolUse und nicht Stop: der Schaden entsteht, WAEHREND der Befehl
laeuft (falsches Arbeitsverzeichnis fuer jeden Folgebefehl in der Kette) — ein
Stop-Hook saehe ihn erst danach, wenn Commit/Edit schon im falschen Baum
gelandet sind.

Vertrag: PreToolUse-Event-JSON auf stdin (`{"tool_input": {"command": …}, …}`
— derselbe minimale Zuschnitt wie bei `tools/hooks/foreign_clone_check.sh`),
IMMER Exit 0. Modus **advisory**: kein Block, keine Rueckfrage — nur ein
Klartext-Hinweis auf stdout, exakt der Weg, auf dem der bereits erzwungene
PreToolUse-Hook dieses Repos (`stale-local-clone-as-ground-truth`, Zweig
`foreign_clone_check.sh`) seinen Fund meldet. Bewusst KEIN
`hookSpecificOutput`/JSON: PreToolUse kennt `additionalContext` nicht (nur
`permissionDecision` mit `allow` (stumm) / `ask` (haelt den Turn an) /
`deny` (blockt) — keine der drei Formen ist "Hinweis ohne Anhalten"); der
Klartext-Pfad ist der einzige in diesem Repo bereits belegte Weg, bei dem ein
PreToolUse-Hook etwas zeigt, OHNE den Fluss zu unterbrechen.

Slug: `cd-fehlschlag-kette-laeuft-weiter` (platform#3175-Retro b7822e, M3).
stdlib-only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_hits  # noqa: E402  (haengt am sys.path oben)

GATE_HEADER = {
    "slug": "cd-fehlschlag-kette-laeuft-weiter",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-09-14",
    "evidence": "tools/claude-hooks/tests/test_cd_fehlschlag_ketten_scanner.py",
}

#: Nur diese Ziele zaehlen als "gefaehrlich raeumbar": eine Variable (traegt
#: ueblicherweise einen Worktree-Pfad) oder ein woertlicher Worktree-Pfad.
#: ~/github/<repo> (Haupt-Tree) gehoert absichtlich nicht zur Muster-Liste — das ist der
#: stabile Ort, in den eine gescheiterte Kette im Realfall zurueckfaellt, aber
#: fuer sich genommen kein raeumbares Ziel.
_WORKTREE_ZIEL = re.compile(
    r"^\$\{?\w+\}?$"
    r"|^~/\.repo-session/"
    r"|^/home/[^/\s]+/\.repo-session/"
)

_CD_STMT = re.compile(r"^\s*cd\s+(\S+)(?P<rest>.*)$", re.S)
_EXIT_GUARD = re.compile(r"\|\|\s*(?:exit|return)\b")
_SET_E = re.compile(r"(?m)^\s*set\s+-\w*e\w*\b")


def _ziel_ohne_quotes(roh: str) -> str:
    if len(roh) >= 2 and roh[0] in "\"'" and roh[-1] == roh[0]:
        return roh[1:-1]
    return roh


def _top_level_split(text: str) -> list[str]:
    """Text in Segmente an `;`/Zeilenumbruch AUSSERHALB von Quotes teilen.

    Bewusst kein voller Shell-Parser (wie die uebrigen Scanner dieses
    Verzeichnisses auch keinen bauen) — nur so weit, dass ein zitiertes `;`
    oder ein Zeilenumbruch innerhalb einer Quote NICHT als Trenner zaehlt.
    """
    segmente: list[str] = []
    puffer: list[str] = []
    quote: str | None = None
    for ch in text:
        if quote:
            puffer.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            puffer.append(ch)
            continue
        if ch in (";", "\n"):
            segmente.append("".join(puffer))
            puffer = []
            continue
        puffer.append(ch)
    segmente.append("".join(puffer))
    return segmente


def finde_unsichere_cd_ketten(command: str) -> list[str]:
    """Liste der unsicheren `cd`-Segmente (Klartext, fuer die Meldung).

    Ein Segment gilt als unsicher, wenn ALLE drei zutreffen:
      1. es ist (nach Whitespace) ein `cd <ziel>`-Statement,
      2. `<ziel>` ist eine Variable oder ein woertlicher Worktree-Pfad,
      3. weder im Segment selbst (`|| exit`/`|| return`, `&&`-Verkettung) noch
         in einem VORHERIGEN Segment (`set -e`) steckt ein Abbruch-Mechanismus,
      4. es folgt mindestens ein weiteres, nicht-leeres Segment in der Kette
         (ein `cd` ohne jeden Folgebefehl kann nichts "weiterlaufen lassen").
    """
    segmente = _top_level_split(command)
    treffer: list[str] = []
    for i, seg in enumerate(segmente):
        m = _CD_STMT.match(seg)
        if not m:
            continue
        ziel = _ziel_ohne_quotes(m.group(1))
        if not _WORKTREE_ZIEL.match(ziel):
            continue
        rest = (m.group("rest") or "").strip()
        if _EXIT_GUARD.search(rest):
            continue
        if rest.startswith("&&") or rest.startswith("||"):
            continue
        folge = [s for s in segmente[i + 1 :] if s.strip()]
        if not folge:
            continue
        vorher = ";".join(segmente[:i])
        if _SET_E.search(vorher):
            continue
        treffer.append(seg.strip())
    return treffer


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

    treffer = finde_unsichere_cd_ketten(command)
    if not treffer:
        return 0

    session = str(event.get("session_id") or "")
    gate_hits.notiere(
        GATE_HEADER["slug"],
        treffer[0],
        turn=command[:400],
        session=session,
        modus="advisory",
    )

    print(
        "⚠ cd-fehlschlag-kette-laeuft-weiter: `"
        + "`; `".join(treffer[:2])
        + "` — cd in einen Worktree-/Variablen-Pfad ohne Abbruch bei "
        "Fehlschlag (kein `|| exit`/`|| return`, keine `&&`-Verkettung, kein "
        "vorheriges `set -e`). Schlaegt `cd` fehl (z. B. geraeumter Worktree), "
        "laufen die folgenden Befehle im FALSCHEN Verzeichnis weiter — Realfall "
        'Retro b7822e B12. Sichere Form: `cd "$W" || exit 1; …`. '
        "(Gate cd-fehlschlag-kette-laeuft-weiter, advisory, blockiert diesen "
        "Aufruf nicht.)"
    )
    return 0


def main_sicher() -> int:
    """`main()` unter dem Hook-Vertrag: Exit 0 immer.

    Siehe `evidence_claim_scanner.main_sicher` fuer die Begruendung; bewusst
    dupliziert statt geteilt, damit der Auffangbogen keinen Import braucht.
    """
    try:
        return main()
    except Exception as exc:  # noqa: BLE001 — Hook-Vertrag: nie blockieren
        print(
            f"cd_fehlschlag_ketten_scanner: {type(exc).__name__}: {exc}"[:400],
            file=sys.stderr,
        )
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
