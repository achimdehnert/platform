#!/usr/bin/env python3
"""Claude Code Stop hook — Scope-Checkpoint-Gate (Rev 2, Ausloeser aus Tool-Evidenz).

Hausregel: sobald eine Aufgabe ein DRITTES Repo beruehrt ODER Prod/Publish
erreicht, einmal innehalten, den gewachsenen Scope spiegeln und die Antwort
durabel festhalten.

WARUM REV 2 (Messung 2026-08-18/19, #1640)
------------------------------------------
Rev 1 las den Antworttext und feuerte, wenn er einen Checkpoint AUSSPRACH,
ohne ein durables Artefakt zu hinterlassen. Der Retro-Slug zaehlt aber die
andere Haelfte: Checkpoint GAR NICHT ausgesprochen (x10). Beide Mengen sind
disjunkt — schweigt man, sah Rev 1 nichts, und Schweigen ist der Fehler.
Replay ueber 374 echte Turns: SOLL 1, IST 0; der Fehler selbst passierte x10.

Gegen Nicht-Gesagtes ist ein Wortlaut-Scanner strukturell blind. Rev 2 dreht
die Richtung um: die BEDINGUNG kommt aus Tool-Evidenz (welche Repos wurden
beschrieben, lief ein Prod-/Publish-Schritt) — die ist sichtbar, egal ob
jemand den Mund aufmacht. Der Wortlaut wird erst danach geprueft, und zwar
als ERFUELLUNG, nicht als Ausloeser.

ZWEI FEHLERFORMEN, GETRENNT GEMELDET
------------------------------------
A ``kein-checkpoint``   Bedingung erfuellt, in der ganzen Sitzung kein
                        Checkpoint ausgesprochen. Das ist der x10-Fehler,
                        fuer den Rev 1 blind war.
B ``nicht-festgehalten`` Checkpoint ausgesprochen, aber kein durables
                        Artefakt in der Sitzung. Das ist Rev 1, behalten.

MESSGROESSE FUER "DRITTES REPO"
-------------------------------
Rev 3 (2026-08-23) zaehlt zusaetzlich die Repos, die ein schreibendes Kommando
laut seiner eigenen AUSGABE angefasst hat. Anlass ist der Rueckfall aus Retro
``8d6869-incr`` #8: ein Flottenlauf entfernte 69 Arbeitskopien und blieb unter
der Schwelle, weil im Aufruf ein einziger Pfad stand. Reichweite ist eine
Eigenschaft der Wirkung, nicht der Argumente.

NICHT die Zahl der genannten Repos: ``artefakt_budget`` hat am 2026-08-17
gemessen, dass die in echten Sitzungen 50 bzw. 26 ergibt, weil sie jede
Erwaehnung mitzaehlt. Gezaehlt werden Repos mit einem SCHREIBZUGRIFF —
Write/Edit auf einen Pfad im Repo oder ein schreibendes git/gh-Kommando im
Repo-Verzeichnis. Das ist "beruehrt" im Sinn der Hausregel und liegt
zwischen der Erwaehnungs-Zahl (zu laut) und ``repos_mit_artefakt`` (zu eng,
verlangt einen angelegten PR/Issue).

Beide Meldungen sind pro Sitzung und Fehlerform EINMALIG (Entprellung ueber
eine Merkdatei) — die Pflicht entsteht einmal, wenn Repo drei dazukommt,
nicht in jedem Folge-Turn.

GATE-HEADER (KONZ-038 D8, maschinenlesbar):
mode=advisory BEWUSST: Rev 2 ist ein Umbau, kein Nachziehen — die
Fehlalarm-Baseline von Rev 1 gilt fuer den neuen Ausloeser NICHT. Neues
Kalibrierfenster ab Merge; blocking erst nach einem Fenster MIT echten
Treffern und 0 Fehlalarmen, per eigenem PR.

Contract: Stop-Event auf stdin, IMMER Exit 0, advisory via
hookSpecificOutput.additionalContext.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_hits  # noqa: E402  (haengt am sys.path oben)
from artefakt_budget import _PROD  # noqa: E402  (dieselbe Prod-Definition)

GATE_HEADER = {
    "slug": "scope-checkpoint-not-durably-recorded",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-19",
    "evidence": "tools/claude-hooks/tests/test_scope_checkpoint_scanner.py",
}

# Ab wie vielen beschriebenen Repos die Pflicht entsteht (Hausregel: das dritte).
REPO_SCHWELLE = 3

# Der Checkpoint-Moment, wie er real formuliert wird. In Rev 2 ist das die
# ERFUELLUNG, nicht der Ausloeser — deshalb darf er grosszuegig bleiben: ein
# zu enges Muster wuerde einen echten Checkpoint uebersehen und faelschlich
# Fehlerform A melden.
CHECKPOINT_PATTERNS = re.compile(
    r"Scope-Checkpoint"
    r"|\bScope\s+(?:ist\s+|war\s+)?(?:deutlich\s+|stark\s+)?(?:gewachsen|eskaliert|erweitert)\b"
    r"|\bRepos?\b[^.\n]{0,60}\bvon\s+deiner\s+urspr(?:ü|ue)nglichen\s+(?:Frage|Anfrage|Aufgabe)\b"
    r"|\bweiter\s+als\s+(?:die|der)\s+urspr(?:ü|ue)ngliche[nr]?\s+(?:Frage|Auftrag|Scope)\b"
    r"|\bist\s+das\s+noch\s+gewollt\b"
    r"|\bber(?:ü|ue)hren?\s+(?:wir\s+)?(?:jetzt\s+)?(?:ein\s+)?dritte[sn]?\s+Repo\b"
    r"|\berreichen?\s+(?:jetzt\s+)?(?:Prod|Produktion|einen\s+Prod-Schritt)\b",
    re.I,
)

# Schreibende Kommandos. Bewusst eng: ein `git status` beruehrt kein Repo im
# Sinn der Hausregel, ein `git commit` schon.
_SCHREIBEND = re.compile(
    r"\bgit\s+(?:commit|push|merge|cherry-pick|revert)\b"
    r"|\bgh\s+(?:pr|issue)\s+(?:create|edit|merge|close|comment)\b"
)

#: Die HAUSEIGENE Wirkungs-Konvention, nicht eine Verb-Liste aus dem Sprachgebrauch.
#: Werkzeuge dieses Repos laufen per Vorgabe trocken und brauchen fuer die Wirkung
#: ein ausdrueckliches Flag (`--apply`, `--allow-live`, `--sync`, `reap`). Genau
#: diese Kommandos fehlten in `_SCHREIBEND` — der Arbeitsbaum-Reaper entfernte 69
#: Arbeitskopien und galt fuer das Gate als lesend (Retro 8d6869-incr #8).
#:
#: Der Unterschied zu einer Muster-Aufzaehlung: das hier ist eine **Konvention des
#: eigenen Repos**, abzaehlbar und dokumentiert — kein Versuch, natuerliche Sprache
#: zu erraten. Sie zaehlt ausserdem nur zusammen mit dem zweiten Signal: die
#: Ausgabe muss von sich aus mehrere Repos nennen.
_WIRKUNGS_FLAGGE = re.compile(
    r"--apply\b|--allow-live\b|--sync\b|\breap\b|\bworktree\s+remove\b", re.I
)

#: Rev 4, Ausweitung 2026-08-25 (Retro fdd368 §5a, Owner-Entscheid „ausweiten"):
#: dritter Ausloeser — eine LAUFENDE Ressource beendet, die diese Sitzung nicht
#: gestartet hat.
#:
#: Anlass: am 2026-08-25 wurde ein seit dem Vortag laufender Entwicklungsserver
#: per `kill <pid>` beendet, waehrend zwoelf Sitzungen parallel liefen. Die
#: Zugehoerigkeit wurde erst DANACH ueber `/proc/<pid>/cwd` plausibilisiert. Beide
#: bestehenden Ausloeser griffen nicht: es war kein drittes beschriebenes Repo und
#: kein Prod-Schritt. Der Ausgang war harmlos — aber der Checkpoint fragt nach dem
#: gewachsenen SCOPE, nicht nach dem entstandenen Schaden. Genau diese
#: Harmlosigkeits-Ausnahme hoehlt ihn aus, und genau so kam der Slug wieder.
#:
#: Bewusst eng: nur das Beenden fremder Prozesse und Dienste. `docker compose
#: up/down` auf den eigenen Stack ist Alltag und faellt absichtlich nicht darunter.
_FREMDE_RESSOURCE = re.compile(
    r"\bkill\s+(?:-\w+\s+)?\d{2,}\b|\bpkill\b|\bkillall\b"
    r"|\bsystemctl\s+(?:stop|restart|disable|mask)\b"
    r"|\bdocker\s+(?:kill|stop)\s+\S",
    re.I,
)

# Durables Artefakt (unveraendert aus Rev 1, nur sitzungsweit ausgewertet).
_DURABLE_CMD = re.compile(r"gh\s+(?:pr|issue)\s+(?:comment|create|edit)", re.I)
_DURABLE_FILE = re.compile(r"docs/|AGENT_HANDOVER|KONZ-|ledger|\.claude/boards/", re.I)
_DURABLE_TOOL_PREFIXES = (
    "mcp__github__create_issue",
    "mcp__github__add_issue_comment",
    "mcp__github__update_issue",
    "mcp__github__create_pull_request_review",
)

_SCHREIB_TOOLS = ("Write", "Edit", "NotebookEdit")


#: Woraus ein Repo-Name bestehen darf. Der erste Buchstabe muss alphanumerisch
#: sein — das haelt versteckte Verzeichnisse (``.repo-session``) heraus, ohne
#: dafuer eine eigene Bedingung zu brauchen.
_REPO_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

#: Die beiden Orte, an denen Repos liegen: der geteilte Haupt-Tree
#: (``~/github/<repo>``) und die Worktrees aus ``repo-session.sh``
#: (``.repo-session/worktrees/<repo>/<branch-slug>``).
_REPO_MARKER = ("/worktrees/", "/github/")


def _repo_aus_pfad(pfad: str) -> str:
    """Repo-Name aus einem echten Datei- oder Arbeitsverzeichnis-Pfad.

    Bis 2026-08-21 stand hier ``rest.split("/", 1)[0]`` — alles bis zum naechsten
    Schraegstrich. Auf einem Pfad ist das richtig; die zweite Aufrufstelle
    uebergibt aber einen ganzen **Bash-Kommandostring**, und dort steht hinter
    dem Repo-Namen kein Schraegstrich, sondern Shell-Syntax. Aus
    ``cd ~/github/platform && cat > /tmp/x`` wurde so der "Repo-Name"
    ``'platform && cat > '``. ``repos_beschrieben`` ist ein Set von Strings:
    drei Schreibweisen desselben Repos sind darin drei Eintraege, und die
    Schwelle war erreicht.

    Die Wirkung war schlimmer als eine Fehlmeldung. Das Gate soll bei echtem
    Scope-Wachstum innehalten lassen; wenn es in Ein-Repo-Sitzungen anschlaegt,
    sobald jemand ``cd <repo> && …`` schreibt — also fast immer —, gewoehnt es
    genau das Weghoeren an, gegen das es gebaut ist. Ein spaeterer Rueckfall
    liefe dann als "Gate wirkt nicht", obwohl die Ursache Messrauschen ist.
    """
    for marker in _REPO_MARKER:
        if marker in pfad:
            treffer = _REPO_NAME.match(pfad.split(marker, 1)[1])
            if treffer:
                return treffer.group(0)
    return ""


def _repos_aus_kommando(cmd: str) -> set[str]:
    """ALLE Repos, die ein Kommando anfasst — nicht nur das erste.

    ``_repo_aus_pfad`` bricht beim ersten Treffer ab; das ist fuer einen Pfad
    richtig und fuer ein Kommando falsch. Ein ``cp ~/github/a/x ~/github/b/y``
    beruehrt zwei Repos, und ausgerechnet dieses Gate zaehlt Repos. Ein
    Untertreiben ist hier die gefaehrlichere Richtung: es verschweigt genau den
    Cross-Repo-Sprung, den der Checkpoint sichtbar machen soll.
    """
    gefunden: set[str] = set()
    for marker in _REPO_MARKER:
        for teil in cmd.split(marker)[1:]:
            treffer = _REPO_NAME.match(teil)
            if treffer:
                gefunden.add(treffer.group(0))
    return gefunden


#: Obergrenze fuer die Ausgabe, die auf Repo-Namen abgesucht wird. Ein Lauf ueber
#: die ganze Flotte nennt seine Repos in den ersten Zeilen; alles darueber ist
#: Kosten ohne Erkenntnis.
_AUSGABE_MAX = 20000


def _repos_aus_ausgabe(text: str) -> set[str]:
    """Repos, die ein Kommando laut seiner eigenen AUSGABE angefasst hat.

    Rev 3, und der Grund dafuer steht in Retro `8d6869-incr` Befund #8: der
    Arbeitsbaum-Reaper lief mit `--karenz-stunden 0` und entfernte **69** Baeume
    ueber die ganze Flotte statt der zwei besprochenen. Der Scope wuchs also um
    ein Vielfaches — und erreichte die Drei-Repo-Schwelle nie, weil im Kommando
    genau **ein** Pfad stand. Wer nur die Argumente liest, sieht ein Repo.

    Die Reichweite steht nicht im Aufruf, sie steht im Ergebnis: der Reaper
    schreibt jede entfernte Arbeitskopie mit ihrem Pfad. Deshalb misst Rev 3 an
    der Wirkung statt an der Deklaration — dieselbe Wendung wie bei
    `deploy_wirkung` (platform#2148).

    Nur fuer Ergebnisse SCHREIBENDER Kommandos aufrufen: ein `grep -rn ~/github/`
    nennt dieselben Pfade, ohne irgendetwas anzufassen.
    """
    return _repos_aus_kommando(text[:_AUSGABE_MAX])


def _text_aus_ergebnis(block: dict) -> str:
    """Ergebnistext eines ``tool_result``-Blocks — Liste oder String."""
    inhalt = block.get("content")
    if isinstance(inhalt, str):
        return inhalt
    if isinstance(inhalt, list):
        return " ".join(str(t.get("text") or "") for t in inhalt if isinstance(t, dict))
    return ""


def sammle_evidenz(transcript_path: Path) -> dict:
    """Sitzungsweite Tool-Evidenz. Reiner Lesevorgang, keine Seiteneffekte."""
    ergebnis = {
        "repos_beschrieben": set(),
        "prod": False,
        "checkpoint_text": "",
        "durables_artefakt": False,
        "fremde_ressource": "",
    }
    # Reihenfolge zaehlt: ein durables Artefakt BELEGT den Checkpoint nur,
    # wenn es nach ihm entstand. Ohne diese Kopplung genuegte irgendein
    # frueherer `docs/`-Edit derselben Sitzung — Fehlerform B waere dann
    # praktisch nie ausloesbar (gefunden vom eigenen Drill, 2026-08-19).
    schritt = 0
    #: ``tool_use_id`` der schreibenden Kommandos — nur deren Ausgabe zaehlt.
    schreib_ids: set[str] = set()
    checkpoint_bei = None
    durable_bei: list[int] = []
    try:
        fh = transcript_path.open(encoding="utf-8", errors="replace")
    except OSError:
        return ergebnis

    with fh:
        for raw in fh:
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            cwd = str(obj.get("cwd") or "")
            msg = obj.get("message", obj)
            content = msg.get("content", []) if isinstance(msg, dict) else []
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                schritt += 1
                typ = c.get("type")

                if typ == "text" and obj.get("type") == "assistant":
                    text = str(c.get("text") or "")
                    if not ergebnis["checkpoint_text"]:
                        m = CHECKPOINT_PATTERNS.search(text)
                        if m:
                            ergebnis["checkpoint_text"] = m.group(0)
                            checkpoint_bei = schritt
                    continue

                if typ == "tool_result":
                    if str(c.get("tool_use_id") or "") in schreib_ids:
                        ergebnis["repos_beschrieben"].update(
                            _repos_aus_ausgabe(_text_aus_ergebnis(c))
                        )
                    continue

                if typ != "tool_use":
                    continue
                name = str(c.get("name") or "")
                inp = c.get("input") or {}
                if not isinstance(inp, dict):
                    inp = {}

                if name.startswith(_DURABLE_TOOL_PREFIXES):
                    durable_bei.append(schritt)

                if name in _SCHREIB_TOOLS:
                    pfad = str(inp.get("file_path") or "")
                    repo = _repo_aus_pfad(pfad)
                    if repo:
                        ergebnis["repos_beschrieben"].add(repo)
                    if _DURABLE_FILE.search(pfad):
                        durable_bei.append(schritt)
                    continue

                cmd = str(inp.get("command") or "")
                if not cmd:
                    continue
                if _PROD.search(cmd):
                    ergebnis["prod"] = True
                # Rev 4: fremde laufende Ressource beendet — eigener Ausloeser,
                # unabhaengig von Repo-Zahl und Prod. Der erste Treffer traegt
                # den Beleg; spaetere ueberschreiben ihn nicht.
                if not ergebnis["fremde_ressource"] and (
                    m := _FREMDE_RESSOURCE.search(cmd)
                ):
                    ergebnis["fremde_ressource"] = m.group(0).strip()
                if _DURABLE_CMD.search(cmd):
                    durable_bei.append(schritt)
                # Die Ausgabe eines wirkenden Kommandos traegt seine Reichweite.
                # Getrennt vom `_SCHREIBEND`-Zweig, weil ein Flottenlauf KEIN
                # git/gh-Kommando ist und sonst nie hierher kaeme.
                if _WIRKUNGS_FLAGGE.search(cmd) and (tid := str(c.get("id") or "")):
                    schreib_ids.add(tid)
                if _SCHREIBEND.search(cmd):
                    repos = _repos_aus_kommando(cmd)
                    if not repos and (aus_cwd := _repo_aus_pfad(cwd)):
                        repos = {aus_cwd}
                    ergebnis["repos_beschrieben"].update(repos)
                    # Die Ausgabe dieses Kommandos darf gleich mitzaehlen — sie
                    # traegt die tatsaechliche Reichweite (s. _repos_aus_ausgabe).
                    if tid := str(c.get("id") or ""):
                        schreib_ids.add(tid)

    if checkpoint_bei is not None:
        ergebnis["durables_artefakt"] = any(i >= checkpoint_bei for i in durable_bei)
    return ergebnis


def _merker(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"scope_checkpoint_{session_id or 'na'}.txt"


def _schon_gemeldet(session_id: str, form: str) -> bool:
    p = _merker(session_id)
    try:
        return form in p.read_text(encoding="utf-8").split()
    except OSError:
        return False


def _merken(session_id: str, form: str) -> None:
    p = _merker(session_id)
    try:
        alt = p.read_text(encoding="utf-8") if p.exists() else ""
        p.write_text(f"{alt}\n{form}".strip(), encoding="utf-8")
    except OSError:
        pass


def _melde(msg: str) -> None:
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": msg}}
        )
    )


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0
    if event.get("stop_hook_active"):
        return 0
    transcript_path = event.get("transcript_path") or ""
    if not transcript_path:
        return 0

    ev = sammle_evidenz(Path(transcript_path))
    repos = sorted(ev["repos_beschrieben"])
    ausloeser = []
    if len(repos) >= REPO_SCHWELLE:
        ausloeser.append(f"{len(repos)} beschriebene Repos ({', '.join(repos)})")
    if ev["prod"]:
        ausloeser.append("Prod-/Publish-Schritt")
    if ev["fremde_ressource"]:
        ausloeser.append(f"fremde Ressource beendet ({ev['fremde_ressource']})")
    if not ausloeser:
        return 0  # keine Pflicht entstanden

    session = event.get("session_id", "")
    grund = " + ".join(ausloeser)

    if not ev["checkpoint_text"]:
        form = "kein-checkpoint"
        if _schon_gemeldet(session, form):
            return 0
        _merken(session, form)
        gate_hits.notiere(
            GATE_HEADER["slug"], grund, turn=grund, session=session, modus="advisory"
        )
        _melde(
            f"🧭 scope-checkpoint: {grund} — aber in dieser Sitzung wurde kein "
            "Scope-Checkpoint ausgesprochen. Hausregel: beim dritten beruehrten "
            "Repo oder beim Prod-Schritt einmal innehalten und dem Owner den "
            "gewachsenen Scope spiegeln, bevor weitergemacht wird. (Gate "
            "scope-checkpoint-not-durably-recorded Rev 2, Fehlerform A, advisory.)"
        )
        return 0

    if not ev["durables_artefakt"]:
        form = "nicht-festgehalten"
        if _schon_gemeldet(session, form):
            return 0
        _merken(session, form)
        gate_hits.notiere(
            GATE_HEADER["slug"],
            ev["checkpoint_text"],
            turn=grund,
            session=session,
            modus="advisory",
        )
        _melde(
            f"🧭 scope-checkpoint: {grund}, Checkpoint ausgesprochen (Marker: "
            f"'{ev['checkpoint_text']}') — aber kein durables Artefakt in der "
            "Sitzung. Checkpoint-Frage UND Owner-Antwort gehoeren als "
            "PR-/Issue-Kommentar oder Doku-Zeile festgehalten, sonst kann keine "
            "spaetere Sitzung pruefen, was freigegeben wurde. (Gate "
            "scope-checkpoint-not-durably-recorded Rev 2, Fehlerform B, advisory.)"
        )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
