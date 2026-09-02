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

Vertrag: Stop-Event-JSON auf stdin lesen, IMMER Exit 0 (auch blockierend wird
nie über den Exit-Code entschieden, s. u.). Bei einem Fund JSON auf stdout —
``{"decision": "block", "reason": …}`` im blocking-Modus, sonst
``hookSpecificOutput.additionalContext``, der dokumentierte Hinweiskanal für
Exit-0-Stop-Hooks.

**blocking seit 2026-09-02** (Owner-Entscheid E4, platform#2606). Die Messung der
Advisory-Gates fand 23 protokollierte Treffer dieses Slugs, und als einziger der
vier Stop-Hook-Melder ließen sich seine Treffer auf konkrete Folge-Issues
zurückführen (#2577, #2576); zugleich weist ``gate_wirkung.py`` ihn als 4×
rückfällig seit dem Bau aus. Ein Melder, dessen Befund belegbar echt ist und
trotzdem viermal wiederkehrt, ist genau der Fall, für den die Registry
``advisory → blocking`` als Antwort vorsieht — nicht das N+1-te Memo.
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
    "mode": "blocking",  # Laufzeit-Opt-out: State-Datei, s. _mode()
    "owner": "achim",
    "last_drill_pass": "2026-09-02",
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


# Marker, an denen eine VERWEIGERTE Ausfuehrung im Tool-Ergebnis erkennbar ist.
# Ein Befehl, den der Assistent versucht hat und der ihm verwehrt wurde, ist nicht
# "ungetestet" — er ist unausfuehrbar. Ein Waechter, dem man nicht folgen KANN,
# wird gelernt zu ignorieren; deshalb deckt eine belegte Ablehnung den Kern ab.
# Anlass: Sitzung 2026-09-01 (meiki-hub 33616e), Retro-Befund #8 — der Melder
# feuerte dreimal auf denselben Befehl, dessen Ausfuehrung der Permission-
# Classifier gesperrt hatte.
ABLEHNUNG_MARKER = (
    "Permission for this action was denied",
    "Blocked by classifier",
    '"permissionDecision":"deny"',
    "permissionDecision': 'deny'",
)


def _ist_ablehnung(inhalt) -> bool:
    """True, wenn ein tool_result-Inhalt eine verweigerte Ausfuehrung beschreibt."""
    if isinstance(inhalt, str):
        text = inhalt
    elif isinstance(inhalt, list):
        text = " ".join(b.get("text", "") for b in inhalt if isinstance(b, dict))
    else:
        return False
    return any(m in text for m in ABLEHNUNG_MARKER)


def _last_turn(transcript_path: str):
    """(assistant_text, bash_commands, abgelehnte_kerne) seit der letzten echten User-Nachricht."""
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
    versuche = {}  # tool_use_id -> Befehl (auch wenn er scheiterte)
    abgelehnte_kerne = set()
    for rec in turn:
        typ = rec.get("type")
        content = (rec.get("message") or {}).get("content")

        if typ == "user":
            # Tool-Ergebnisse liegen in den user-Records. Bis 2026-09-01 wurden
            # sie hier verworfen — der Waechter sah den Versuch, nie seinen Ausgang.
            if isinstance(content, list):
                for block in content:
                    if (
                        not isinstance(block, dict)
                        or block.get("type") != "tool_result"
                    ):
                        continue
                    befehl = versuche.get(block.get("tool_use_id"))
                    if befehl and _ist_ablehnung(block.get("content")):
                        for zeile in befehl.splitlines():
                            kern = _command_core(zeile)
                            if kern:
                                abgelehnte_kerne.add(kern)
            continue

        if typ != "assistant":
            continue
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
                    versuche[block.get("id")] = cmd
    return "\n".join(assistant_text), bash_commands, abgelehnte_kerne


def find_untested(
    assistant_text: str,
    bash_commands: list[str],
    abgelehnte_kerne: set[str] | None = None,
):
    """(ungetestet, mit_platzhalter) — je eine Liste von Befehlszeilen.

    `abgelehnte_kerne` deckt Befehle ab, deren Ausfuehrung im selben Turn
    versucht und VERWEIGERT wurde. Der Abgleich laeuft ueber `_command_core`,
    also ueber die ersten zwei Token: `docker exec` deckt jedes `docker exec`,
    aber KEIN `ssh host 'docker exec …'` — dort ist der Kern `ssh host`. Diese
    Grenze ist gewollt eng; sie hat am 2026-09-01 einen echten Quoting-Fehler
    gefangen, den ein breiterer Abgleich durchgelassen haette.
    """
    ran = "\n".join(bash_commands)
    ran_cores = {
        _command_core(line) for cmd in bash_commands for line in cmd.splitlines()
    }
    ran_cores |= abgelehnte_kerne or set()
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

#: Name der Opt-out-Datei im STATE_DIR. Steht dort das Wort `advisory`, meldet der
#: Scanner nur noch. Sonst blockiert er.
MODUS_DATEI = "untested_scanner_mode"


def _mode() -> str:
    """blocking (Default) | advisory — Opt-out ueber eine State-Datei.

    Bewusst KEIN stiller Advisory-Default bei fehlender Datei: sonst faellt das
    Gate auf einer frischen Maschine lautlos in genau den Zustand zurueck, dessen
    Wirkungslosigkeit hier gemessen wurde (4 Rueckfaelle seit Bau, 23 Treffer ohne
    Verhaltensaenderung). Uebernommen von evidence_claim_scanner._mode(), damit es
    nur EINEN Weg gibt, einen Stop-Hook scharf oder stumpf zu schalten.
    """
    try:
        if (STATE_DIR / MODUS_DATEI).read_text(
            encoding="utf-8"
        ).strip().lower() == "advisory":
            return "advisory"
    except OSError:
        pass
    return "blocking"


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

    # Ein erzwungener Korrektur-Zug pro Turn (Registry `_wording_convention`,
    # EXT2-M28-5). Ohne diesen Guard feuert der Scanner in der vom Block
    # ausgeloesten Fortsetzung erneut — das Analysefenster reicht bis zur letzten
    # ECHTEN Nutzernachricht und enthaelt den Befehl weiterhin. Realfall am
    # Claim-Gate: 9 Blocks hintereinander, bis die Block-Sperre den Turn beendete.
    if event.get("stop_hook_active"):
        return 0

    transcript_path = event.get("transcript_path") or ""
    if not transcript_path:
        return 0

    assistant_text, bash_commands, abgelehnte_kerne = _last_turn(transcript_path)
    untested, placeholders = find_untested(
        assistant_text, bash_commands, abgelehnte_kerne
    )

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
            modus=_mode(),
        )

    reminder = build_reminder(untested, placeholders)
    if not reminder:
        return 0

    if _mode() == "blocking":
        # `decision: block` statt Exit 2 — bewusst: Exit 2 wird teils als
        # Nutzer-Ablehnung gelesen und wuerde den Turn stallen statt ihn zu
        # korrigieren (Registry `_wording_convention`, EXT2-M28-5). Der
        # stop_hook_active-Guard oben begrenzt auf EINEN erzwungenen Zug.
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": (
                        "Automatischer Uebergabe-Check (Gate "
                        "untested-command-handed-to-user — dies ist KEINE "
                        "Nutzer-Ablehnung, sondern Maschinen-Feedback): "
                        + reminder
                        + " Lass den Befehl JETZT selbst laufen (bei "
                        "Handover-Skripten mit `< /dev/null`) oder nimm ihn aus "
                        "der Antwort, dann den Turn normal beenden; dieser Check "
                        "feuert pro Turn nur einmal."
                    ),
                }
            )
        )
        return 0

    # advisory (Opt-out): dokumentierte additionalContext-Form fuer Exit-0-Stop-Hooks.
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
