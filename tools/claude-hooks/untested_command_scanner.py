#!/usr/bin/env python3
"""Claude Code Stop hook — Handover-Befehle ohne eigenen Testlauf melden.

Warum es das gibt (Session 2026-07-26, platform): der Assistent hat dem User
dreimal hintereinander einen Befehl zum Ausführen gegeben, den er selbst nie
ausgeführt hatte — und alle drei scheiterten beim User:

1. ``GH_TOKEN=<dieser PAT> gh api …`` — bash las ``<`` als Umleitung.
2. ``GH_TOKEN=PAT gh api …`` — der Token-*Name* statt seines Werts, 401.
3. ``fix-devhub-token.sh`` mit ``read -rsp`` — im ``!``-Modus gibt es kein
   Terminal, ``read`` bekam sofort EOF.

Die Regel „gib nur getestete Befehle" stand danach als Memory fest. Dieser Hook
macht sie prüfbar, statt sie ein viertes Mal zu formulieren: er sieht in der
Antwort nach ausführbar aussehenden Codeblöcken und prüft, ob im SELBEN Turn ein
Bash-Tool-Aufruf mit demselben Befehlskern lief.

Zwei Fundklassen, absichtlich eng gehalten:

* **ungetestet** — Befehlsblock ohne passenden Bash-Aufruf im Turn.
* **Platzhalter** — ``<…>``/``DEIN_…`` im Befehl; der ist per Konstruktion nicht
  ausführbar und war Fehlschlag 1 und 2.

Vertrag: Stop-Event-JSON auf stdin lesen, IMMER Exit 0 (ein Scanner darf Claude
nie blockieren). Bei einem Fund JSON auf stdout mit ``hookSpecificOutput.
additionalContext`` — der dokumentierte Hinweiskanal für Exit-0-Stop-Hooks.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_hits  # noqa: E402  (haengt am sys.path oben)

# Maschinenlesbarer Kopf (KONZ-038 D8). Nachgetragen 2026-08-16 (Retro 9d861a):
# dieser Scanner lief seit Wochen aktiv, war aber in KEINER Registry gefuehrt —
# damit unsichtbar fuer `gate_drill_check.py` und fuer die Gate-Buchhaltung in
# `retro_kpis.py`. Ein aktiver, unregistrierter Waechter ist kein halbes Gate,
# sondern ein blinder Fleck in genau der Uebersicht, die Gates zaehlen soll.
GATE_HEADER = {
    "slug": "untested-command-handed-to-user",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-16",
    "evidence": "tools/claude-hooks/tests/test_untested_command_scanner.py",
}

# Fenced Code-Block: ```[sprache]\n<inhalt>```
FENCE_RE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)

# Ein Block gilt als "auszuführender Befehl", wenn seine erste sinnvolle Zeile
# mit einem dieser Kommandos beginnt. Bewusst eine Positivliste: Ausgabe-
# Beispiele, Logs, JSON und Diffs sollen NICHT feuern.
COMMAND_STARTERS = {
    "bash",
    "sh",
    "ssh",
    "scp",
    "gh",
    "git",
    "curl",
    "wget",
    "make",
    "docker",
    "python3",
    "python",
    "pytest",
    "npm",
    "pnpm",
    "yarn",
    "systemctl",
    "journalctl",
    "psql",
    "kubectl",
    "rsync",
}

# Platzhalter, die ein Befehl nie enthalten darf, wenn er kopierbar sein soll.
PLACEHOLDER_RE = re.compile(r"<[^>\s][^>]{0,40}>|DEIN_[A-Z_]+|<pfad|\bXXX\b")

# Zeilen, die im Block stehen dürfen, ohne ihn zu einem Befehl zu machen.
#
# `!` steht bewusst in dieser Klasse, und es ist der wichtigste Eintrag darin:
# in Claude Code bedeutet `! <befehl>`, dass der OWNER ihn selbst ausfuehrt — das
# ist die Uebergabe-Konvention und damit die praeziseste Form dessen, wonach
# dieser Scanner sucht. Bis 2026-08-23 machte genau dieses Zeichen ihn blind:
# `bash install-certbot-token.sh` feuerte, `! bash install-certbot-token.sh`
# nicht. Realfall ausschreibungs-hub 2026-08-23: ein nie ausgefuehrtes Skript
# ging so an den Owner und schrieb seine eigenen Zeilen in eine
# Prod-Credential-Datei. Gate war gebaut, Drill gruen, Familie ungesehen
# (platform#2230, Antwort "ausweiten" aus derselben Retro).
PROMPT_PREFIX_RE = re.compile(r"^\s*(?:[\$#>!]|\w+@[\w.-]+:[^$#]*[$#])\s*")


def _iter_command_lines(block: str):
    """Liefert die Befehlszeilen eines Blocks (ohne Kommentare/Leerzeilen)."""
    for raw in block.splitlines():
        line = PROMPT_PREFIX_RE.sub("", raw).strip()
        if not line or line.startswith("#"):
            continue
        yield line


def _looks_like_command(line: str) -> bool:
    """Beginnt die Zeile mit einem bekannten Kommando oder einem Skriptaufruf?"""
    try:
        tokens = shlex.split(line, comments=True)
    except ValueError:
        tokens = line.split()
    if not tokens:
        return False
    head = tokens[0]
    # Env-Prefix überspringen: FOO=bar cmd …
    idx = 0
    while idx < len(tokens) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[idx]):
        idx += 1
    if idx >= len(tokens):
        return False
    head = tokens[idx]
    base = head.rsplit("/", 1)[-1]
    return base in COMMAND_STARTERS or base.endswith(".sh")


def _contains_starter(line: str) -> bool:
    """Steht irgendwo in der Zeile ein bekanntes Kommando?

    Nötig, weil ein Platzhalter die Zeile unparsbar macht:
    ``GH_TOKEN=<dieser PAT> gh api …`` zerfällt in ``GH_TOKEN=<dieser`` und
    ``PAT>``, sodass die reine Anfangsprüfung das ``gh`` nicht mehr sieht —
    genau der Befehl, der am 2026-07-26 beim User scheiterte.
    """
    for tok in re.split(r"\s+", line):
        base = tok.rsplit("/", 1)[-1]
        if base in COMMAND_STARTERS or base.endswith(".sh"):
            return True
    return False


def _command_core(line: str) -> str:
    """Normalisierter Kern einer Befehlszeile für den Abgleich mit Bash-Calls.

    Env-Prefixe und Pfade fallen weg, damit ``bash ~/shared/x.sh`` und
    ``bash /home/u/shared/x.sh`` als derselbe Befehl gelten.
    """
    try:
        tokens = shlex.split(line, comments=True)
    except ValueError:
        tokens = line.split()
    tokens = [t for t in tokens if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", t)]
    if not tokens:
        return ""
    core = []
    for tok in tokens[:2]:
        core.append(tok.rsplit("/", 1)[-1])
    return " ".join(core)


def _last_turn(transcript_path: str):
    """(assistant_text, bash_commands) seit der letzten echten User-Nachricht."""
    try:
        lines = (
            Path(transcript_path)
            .read_text(encoding="utf-8", errors="replace")
            .splitlines()
        )
    except OSError:
        return "", []

    turn = []
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        turn.append(rec)
        if rec.get("type") == "user":
            content = (rec.get("message") or {}).get("content")
            is_tool_result = isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in content
            )
            if not is_tool_result:
                break
    turn.reverse()

    assistant_text, bash_commands = [], []
    for rec in turn:
        if rec.get("type") != "assistant":
            continue
        content = (rec.get("message") or {}).get("content")
        if isinstance(content, str):
            assistant_text.append(content)
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                assistant_text.append(block.get("text", ""))
            elif block.get("type") == "tool_use" and block.get("name") == "Bash":
                cmd = (block.get("input") or {}).get("command", "")
                if isinstance(cmd, str):
                    bash_commands.append(cmd)
    return "\n".join(assistant_text), bash_commands


def find_untested(assistant_text: str, bash_commands: list[str]):
    """(ungetestet, mit_platzhalter) — je eine Liste von Befehlszeilen."""
    ran = "\n".join(bash_commands)
    ran_cores = {
        _command_core(line) for cmd in bash_commands for line in cmd.splitlines()
    }
    ran_cores.discard("")

    untested, placeholders = [], []
    for block in FENCE_RE.findall(assistant_text or ""):
        for line in _iter_command_lines(block):
            has_placeholder = bool(PLACEHOLDER_RE.search(line))
            if has_placeholder:
                # Ein Platzhalter zerlegt die Zeile; die Anfangsprüfung greift
                # dann nicht mehr, deshalb hier die tolerante Variante.
                if _contains_starter(line):
                    placeholders.append(line)
                continue
            if not _looks_like_command(line):
                continue
            core = _command_core(line)
            if core and core not in ran_cores and line not in ran:
                untested.append(line)
    return untested, placeholders


def build_reminder(untested: list[str], placeholders: list[str]) -> str:
    parts = []
    if placeholders:
        parts.append(
            "Platzhalter im Befehl (nicht kopierbar, scheitert beim User): "
            + "; ".join(placeholders[:3])
        )
    if untested:
        parts.append(
            "Befehl an den User weitergegeben, ohne ihn in diesem Turn selbst "
            "auszuführen: " + "; ".join(untested[:3])
        )
    if not parts:
        return ""
    return (
        "[untested-command-scanner] "
        + " | ".join(parts)
        + " — Regel: auszuführende Befehle vorher selbst laufen lassen "
        "(bei Handover-Skripten mit `< /dev/null`, weil der !-Modus kein "
        "Terminal hat), Platzhalter durch Datei-Argumente ersetzen."
    )


STATE_DIR = Path.home() / ".claude" / "hooks" / "state"


def _state_path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "unknown"
    return STATE_DIR / f"untested_{safe}.json"


def _bereits_gemeldet(session_id: str) -> set[str]:
    try:
        roh = json.loads(_state_path(session_id).read_text())
        return set(roh.get("gemeldet") or [])
    except (OSError, json.JSONDecodeError, ValueError, AttributeError):
        return set()


def _merken(session_id: str, kerne: set[str]) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        alt = _bereits_gemeldet(session_id)
        _state_path(session_id).write_text(
            json.dumps({"gemeldet": sorted(alt | kerne)[-500:]})
        )
    except OSError:
        # Ein nicht schreibbarer Zustand darf den Hook nicht scheitern lassen —
        # er verliert dann nur seine Entprellung.
        pass


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0

    transcript_path = event.get("transcript_path") or ""
    if not transcript_path:
        return 0

    assistant_text, bash_commands = _last_turn(transcript_path)
    untested, placeholders = find_untested(assistant_text, bash_commands)

    # Entprellung (2026-07-31). `_last_turn` endet bei der letzten ECHTEN
    # Nutzernachricht — Hintergrund-Benachrichtigungen und Hook-Injektionen
    # zaehlen nicht als solche. Arbeitet der Agent laenger ohne Zwischenruf,
    # waechst das Fenster unbegrenzt und schleppt jeden frueher genannten
    # Befehl mit: real gemessen 166 Records mit 27 Vorkommen DESSELBEN
    # Befehls, siebenmal hintereinander gemeldet. Ein Waechter, der ab dem
    # ersten Treffer dauerhaft anschlaegt, meldet nichts mehr — dieselbe
    # Klasse wie die blinden Cron-Melder aus platform#1508.
    session_id = event.get("session_id") or ""
    if session_id:
        # Fingerabdruck ist die NORMALISIERTE ZEILE, nicht `_command_core`.
        # Der Kern ist absichtlich grob (er soll gegen tatsaechlich gelaufene
        # Befehle matchen) und reduziert `ssh host 'systemctl …'` und
        # `ssh host 'docker …'` auf denselben Wert — als Entprellungs-
        # schluessel wuerde er den zweiten Befund verschlucken. Genau das
        # fiel im Test auf.
        schon = _bereits_gemeldet(session_id)

        def _abdruck(zeile: str) -> str:
            return " ".join(zeile.split())

        # Beide Befundarten entprellen, nicht nur `untested`.
        #
        # Bis 2026-08-16 filterte diese Stelle ausschliesslich `untested`, und
        # `_merken` speicherte auch nur die. Folge: ein Platzhalter-Befund wurde bei
        # JEDEM weiteren Stop erneut gemeldet, bis der Mensch etwas schrieb — auch
        # dann noch, wenn er laengst behoben war. Real gemessen in der Sitzung, in
        # der dieser Fix entstand: DERSELBE Ausschnitt dreimal, zweimal davon nach
        # der Korrektur. Das ist exakt die Klasse, vor der der Kommentar oben warnt
        # („ein Waechter, der ab dem ersten Treffer dauerhaft anschlaegt, meldet
        # nichts mehr" — platform#1508); die Entprellung war dagegen gebaut und
        # liess einen ihrer beiden Zweige aus.
        #
        # Der Fingerabdruck ist die normalisierte Zeile: ein NEUER Platzhalter in
        # einer spaeteren Antwort traegt einen anderen Abdruck und meldet weiterhin.
        # Entprellt wird die Wiederholung, nicht der Befund.
        untested = [b for b in untested if _abdruck(b) not in schon]
        placeholders = [p for p in placeholders if _abdruck(p) not in schon]
        if not untested and not placeholders:
            return 0
        _merken(session_id, {_abdruck(x) for x in (*untested, *placeholders)})

    # Treffer mitschreiben (Retro 9d861a, Befund #1). Bis 2026-08-16 meldete dieser
    # Scanner ausschliesslich in den Sitzungs-Kontext; von fuenf aktiven Scannern
    # protokollierten nur drei, und die FP-/Recall-Auswertung in platform#1640 stand
    # unbemerkt auf einer unvollstaendigen Datenbasis. Bewusst NACH der Entprellung:
    # protokolliert wird, was auch gemeldet wird — sonst zaehlt das Protokoll
    # Wiederholungen, die der Mensch nie zu sehen bekam.
    if untested or placeholders:
        gate_hits.notiere(
            GATE_HEADER["slug"],
            f"untested={len(untested)} placeholders={len(placeholders)}",
            session=session_id,
            modus=GATE_HEADER["mode"],
        )

    reminder = build_reminder(untested, placeholders)
    if reminder:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "Stop",
                        "additionalContext": reminder,
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
