#!/usr/bin/env python3
"""PreToolUse(Bash|Write|Edit|MultiEdit|NotebookEdit|mcp__.*|WebFetch) — Vertrauliches bleibt in der Ablage.

GATE_HEADER (KONZ-038 D8):
  "slug": "vertrauliches-verlaesst-ablage"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-10-16"
  "evidence": "tools/claude-hooks/tests/test_block_vertrauliches_verlassen.py"

Anlass 2026-10-16: Ein Kunde stuft jede Mail mit einem Vermerk am Zeilenanfang
ein („<Kunde> Intern"). Der Owner will interne Inhalte im Dialog zulassen,
sobald die Vertraulichkeit vertraglich geklaert ist. Bis dahin und danach gilt:
markierte Inhalte duerfen in eine abgeschlossene Ablage (Tresor), aber nicht in
Repos, ins Gedaechtnis, zu fremden Sprachmodellen oder nach GitHub.

Kundenname, Vermerk und Pfade stehen NICHT hier, sondern in einer Regeldatei
ausserhalb jedes Repos (`~/.claude/vertraulich_regeln.json`, Muster:
`vertraulich_regeln.beispiel.json`). Dieses Repo ist oeffentlich; schon der
Vermerk wuerde die Kundenbeziehung nennen.

Was der Hook sperrt:
  1. Write/Edit/MultiEdit/NotebookEdit, deren neuer Inhalt einen Vermerk traegt,
     in ein geschuetztes Ziel (Repos, `~/.claude`). Der Tresor selbst ist frei.
  2. Bash, das den Tresor nennt UND einen Ausgang (gh, git commit/push, URL
     ausser localhost, Anbieter-Namen) oder ein geschuetztes Ziel beruehrt —
     auch, wenn der Ausgang erst im Inhalt eines gestarteten Python-Skripts steht.
  3. Bash mit Ausgang oder Schreibzugriff auf ein geschuetztes Ziel, wenn der
     Befehl selbst oder eine darin genannte Datei einen Vermerk traegt
     (`--body-file`, `-F`, `curl -d @datei`, `cp mail.txt ~/github/...`).
  4. MCP-Werkzeuge und WebFetch, deren Eingabe einen Vermerk oder den
     Tresorpfad enthaelt (Lehre aus platform#3862 Fund 1: Kommentare ueber den
     GitHub-Werkzeugserver liefen an Shell-Haken vorbei).

FAIL-Verhalten: Regeldatei fehlt ⇒ Haken aus (Maschine nicht eingerichtet).
Regeldatei kaputt oder Pruefung wirft ⇒ fail-closed fuer jedes erfasste
Werkzeug, und der Fehler wird gezaehlt (`gate_hits`, Marker `fehler`) —
Lehre aus platform#3862 Fund 5: ein Haken, der still versagt, sieht aus wie
einer, der nichts findet. Das Protokoll nennt nie Inhalt, nur Werkzeug und Ziel.

GRENZEN (bewusst): Inhalte ohne Vermerk (abgeschriebene Zahlen, Zusammen-
fassungen) erkennt kein Muster. Das Lesen des Tresors durch die Sitzung selbst
sperrt der Hook nicht — ob das zulaessig ist, ist eine Vertragsfrage, keine
technische. Skripte ausser `python <datei>.py`, Shell-Variablen statt Pfaden,
Owner-Befehle mit `!` (laufen nicht durch PreToolUse).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

SLUG = "vertrauliches-verlaesst-ablage"
REGELN_ENV = "VERTRAULICH_REGELN"
REGELN_STANDARD = "~/.claude/vertraulich_regeln.json"

_DATEI_WERKZEUGE = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
_EINGABE_WERKZEUGE = ("mcp__", "WebFetch", "WebSearch")
_SKRIPT = re.compile(
    r"\bpython[0-9.]*\s+((?:-[A-Za-z]\S*\s+)*)([^\s;&|<>()\"']+\.py)\b"
)
#: Umleitungen, die nichts schreiben — vor der Schreib-Pruefung entfernt.
_HARMLOSE_UMLEITUNG = re.compile(r"&?\d*>>?\s*/dev/null\b|\d*>&\d+")
_SCHREIBT = re.compile(
    r">|\btee\b|\bcp\b|\bmv\b|\brsync\b|\binstall\b|\bsed\s+-[a-zA-Z]*i|\bgit\b"
)
MAX_DATEI = 1024 * 1024


class Regeln:
    def __init__(self, roh: dict) -> None:
        self.vermerk = [re.compile(m) for m in roh["vermerk_muster"]]
        self.ausgang = [re.compile(m, re.IGNORECASE) for m in roh["ausgang_muster"]]
        self.tresore = [_norm(p) for p in roh["tresore"]]
        self.ziele = [_norm(p) for p in roh["geschuetzte_ziele"]]
        if not self.vermerk or not self.tresore:
            raise ValueError("vermerk_muster und tresore duerfen nicht leer sein")


def regeln_pfad() -> Path:
    return Path(os.path.expanduser(os.environ.get(REGELN_ENV) or REGELN_STANDARD))


def lade_regeln(pfad: Path) -> Regeln:
    return Regeln(json.loads(pfad.read_text(encoding="utf-8")))


def _norm(pfad: str, cwd: str = "/") -> str:
    return os.path.normpath(os.path.join(cwd, os.path.expanduser(pfad)))


def _unter(pfad: str, wurzeln: list[str]) -> bool:
    return any(pfad == w or pfad.startswith(w + os.sep) for w in wurzeln)


def _schreibweisen(wurzel: str) -> list[str]:
    """Absolut, `~/…`, `$HOME/…`, `${HOME}/…` — so steht ein Pfad in Befehlen."""
    formen = [wurzel]
    heim = os.path.expanduser("~")
    if wurzel.startswith(heim + os.sep):
        rest = wurzel[len(heim) + 1 :]
        formen += [f"~/{rest}", f"$HOME/{rest}", f"${{HOME}}/{rest}"]
    return formen


def _nennt(text: str, wurzeln: list[str]) -> bool:
    return any(f in text for w in wurzeln for f in _schreibweisen(w))


def hat_vermerk(text: str, regeln: Regeln) -> bool:
    return any(m.search(text) for m in regeln.vermerk)


def _ausgang(text: str, regeln: Regeln) -> bool:
    return any(m.search(text) for m in regeln.ausgang)


def _inhalt_neu(werkzeug: str, eingabe: dict) -> str:
    if werkzeug == "Write":
        return str(eingabe.get("content") or "")
    if werkzeug == "Edit":
        return str(eingabe.get("new_string") or "")
    if werkzeug == "MultiEdit":
        return "\n".join(str(e.get("new_string") or "") for e in eingabe.get("edits") or [])
    return str(eingabe.get("new_source") or "")


def _lies(pfad: str) -> str:
    try:
        p = Path(pfad)
        if p.is_file() and p.stat().st_size <= MAX_DATEI:
            return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        pass
    return ""


def _dateien_im_befehl(befehl: str, cwd: str) -> list[str]:
    try:
        token = shlex.split(befehl, comments=False)
    except ValueError:
        token = befehl.split()
    pfade = []
    for t in token:
        for kandidat in (t, t.split("=", 1)[-1], t.lstrip("@<")):
            if kandidat and ("/" in kandidat or "." in kandidat):
                p = _norm(kandidat, cwd)
                if os.path.isfile(p):
                    pfade.append(p)
                    break
    return pfade


def _skript_inhalte(befehl: str, cwd: str) -> list[str]:
    return [_lies(_norm(m.group(2), cwd)) for m in _SKRIPT.finditer(befehl)]


def _pruefe_bash(eingabe: dict, cwd: str, regeln: Regeln) -> str | None:
    befehl = str(eingabe.get("command") or "")
    ausgang = _ausgang(befehl, regeln)
    schreibt = bool(_SCHREIBT.search(_HARMLOSE_UMLEITUNG.sub("", befehl)))
    ziel = _nennt(befehl, regeln.ziele) or (_unter(cwd, regeln.ziele) and schreibt)

    if _nennt(befehl, regeln.tresore):
        if ausgang:
            return "Befehl liest den Tresor und hat einen Ausgang (GitHub, Git, URL oder fremdes Modell)."
        if ziel and schreibt:
            return "Befehl bewegt Tresor-Inhalt in ein geschuetztes Ziel (Repo oder ~/.claude)."
        if any(_ausgang(s, regeln) for s in _skript_inhalte(befehl, cwd)):
            return "Befehl gibt Tresor-Inhalt an ein Skript mit Ausgang (fremdes Modell, URL, GitHub)."
        return None

    if not (ausgang or (ziel and schreibt)):
        return None
    if hat_vermerk(befehl, regeln):
        return "Befehlstext traegt einen Vertraulichkeits-Vermerk und hat einen Ausgang oder ein geschuetztes Ziel."
    for pfad in _dateien_im_befehl(befehl, cwd):
        if _unter(pfad, regeln.tresore) or hat_vermerk(_lies(pfad), regeln):
            return f"Datei `{pfad}` traegt einen Vertraulichkeits-Vermerk; der Befehl hat einen Ausgang oder ein geschuetztes Ziel."
    return None


def entscheide(daten: dict, regeln: Regeln) -> str | None:
    werkzeug = str(daten.get("tool_name") or "")
    eingabe = daten.get("tool_input") or {}
    cwd = str(daten.get("cwd") or os.getcwd())

    if werkzeug in _DATEI_WERKZEUGE:
        pfad = _norm(str(eingabe.get("file_path") or eingabe.get("notebook_path") or ""), cwd)
        if _unter(pfad, regeln.tresore) or not _unter(pfad, regeln.ziele):
            return None
        if hat_vermerk(_inhalt_neu(werkzeug, eingabe), regeln):
            return f"Inhalt mit Vertraulichkeits-Vermerk soll nach `{pfad}` (geschuetztes Ziel)."
        return None

    if werkzeug == "Bash":
        return _pruefe_bash(eingabe, cwd, regeln)

    if werkzeug.startswith(_EINGABE_WERKZEUGE):
        text = json.dumps(eingabe, ensure_ascii=False)
        # json.dumps maskiert Zeilenumbrueche — fuer die Zeilenanfangs-Muster zurueckholen.
        text = text.replace("\\n", "\n")
        if hat_vermerk(text, regeln) or _nennt(text, regeln.tresore):
            return f"Eingabe an `{werkzeug}` traegt einen Vertraulichkeits-Vermerk oder nennt den Tresor."
    return None


def erfasst(daten: dict) -> bool:
    werkzeug = str(daten.get("tool_name") or "")
    return (
        werkzeug in _DATEI_WERKZEUGE
        or werkzeug == "Bash"
        or werkzeug.startswith(_EINGABE_WERKZEUGE)
    )


def _notiere(marker: str, daten: dict) -> None:
    """Nur Werkzeug und Ziel, nie Inhalt — das Protokoll ist kein Tresor."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import gate_hits

        eingabe = daten.get("tool_input") or {}
        gate_hits.notiere(
            SLUG,
            marker,
            beleg=f"{daten.get('tool_name') or ''} {eingabe.get('file_path') or ''}".strip()[:200],
            session=str(daten.get("session_id") or ""),
            modus="blocking",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stoeren
        pass


def _deny(grund: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"⛔ Vertrauliches ({SLUG}): {grund} "
                    "Vertrauliches bleibt im Tresor; Freigabe nur durch den Owner.",
                }
            },
            ensure_ascii=False,
        )
    )


def pruefe_text_cli(regeln_datei: Path) -> int:
    """`--pruefe-text`: stdin auf Vermerke pruefen. Exit 1 = Fund, 2 = Regeln kaputt."""
    try:
        regeln = lade_regeln(regeln_datei)
    except (OSError, ValueError, KeyError, re.error):
        return 2
    return 1 if hat_vermerk(sys.stdin.read(), regeln) else 0


def main() -> int:
    pfad = regeln_pfad()
    if "--pruefe-text" in sys.argv[1:]:
        return pruefe_text_cli(pfad)
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        _notiere("fehler", {})
        return 0
    if not erfasst(daten) or not pfad.exists():
        return 0
    try:
        grund = entscheide(daten, lade_regeln(pfad))
        marker = "treffer"
    except Exception as exc:  # noqa: BLE001 — Sicherheits-Haken: fail-closed
        grund = f"Hook-Fehler ({type(exc).__name__}) — fail-closed. Regeldatei `{pfad}` pruefen."
        marker = "fehler"
    if grund:
        _notiere(marker, daten)
        _deny(grund)
    return 0


if __name__ == "__main__":
    sys.exit(main())
