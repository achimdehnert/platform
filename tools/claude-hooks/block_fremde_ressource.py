#!/usr/bin/env python3
"""PreToolUse(Bash|Write|Edit|MultiEdit|NotebookEdit) — ein externes Schreibziel, eine Sitzung.

GATE_HEADER (KONZ-038 D8):
  "slug": "fremde-sitzung-schreibt-externe-ressource"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-10-14"
  "evidence": "tools/claude-hooks/tests/test_block_fremde_ressource.py"

Realfall 2026-10-14: Zwei Sitzungen im selben Repo bearbeiteten denselben
Buchhaltungs-Mandanten und dasselbe Board. Die eine bereitete eine Rueckzahlung
als Ueberweisungsdatei vor, die andere legte dieselbe Zahlung im
Buchhaltungssystem an. Das Owner-Wort „erledigt" landete in der falschen
Sitzung und wurde dort als die andere Zahlung verbucht, eine Doppelzahlung war
nur noch eine Lesart entfernt. Die Trennung paralleler Sitzungen war mehrfach
beauftragt (platform#1944, #3549), gebaut war sie nur fuer Git-Worktrees.

Was der Hook tut:
  1. Er erkennt anhand von `ressourcen_schreibziele.json`, ob der Aufruf eine
     dort gelistete Ressource beruehrt: Befehlsmuster, Inhalt eines gestarteten
     Python-Skripts, Dateipfad bei Write/Edit.
  2. Je Ressource beansprucht er die Lease (`ressourcen_lease.py`): frei oder
     verwaist ⇒ diese Sitzung wird Inhaber, der Aufruf laeuft. Gehoert sie einer
     anderen LEBENDEN Sitzung ⇒ deny mit Inhaber und Ausweg.
  3. Er sperrt die Umgehung: `--erzwingen` und direkte Schreibzugriffe auf das
     Lease-Verzeichnis sind Owner-Recht (Owner-Befehle mit `!` laufen nicht
     durch PreToolUse-Hooks — Hypothese bis zur ersten Owner-Probe, s. PR).

FAIL-Verhalten: Erkennung kaputt (Regeldatei fehlt/ungueltig, kein JSON) ⇒
fail-open mit Warnung auf stderr. Ressource erkannt, Lease-Pruefung wirft ⇒
fail-closed. Sitzung unbekannt (keine `session_id`) ⇒ fail-closed.

GRENZEN (bewusst, fail-open): Skripte, die nicht per `python <datei>.py`
starten (`bash x.sh`, `make`, Importketten ueber Hilfsmodule ohne Marker),
Board-Schreiben ueber Werkzeuge, deren Befehl den Board-Pfad nicht nennt,
Ressourcen ausserhalb der Regeldatei (Postfach, Ablage: platform#3549).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ressourcen_lease as rl  # noqa: E402

SLUG = "fremde-sitzung-schreibt-externe-ressource"
REGELN = Path(__file__).with_name("ressourcen_schreibziele.json")

_DATEI_WERKZEUGE = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
#: `python[3[.x]] [-flags] datei.py` — auch `.venv/bin/python`.
_SKRIPT = re.compile(
    r"\bpython[0-9.]*\s+((?:-[A-Za-z]\S*\s+)*)([^\s;&|<>()\"']+\.py)\b"
)
_CD = re.compile(r"(?:^|&&|;|\|\||\n)\s*cd\s+([^\s;&|]+)")
_LEASE_PFAD = re.compile(r"\.claude/leases/ressourcen")
_LEASE_SCHREIBEN = re.compile(
    r"\b(?:rm|mv|cp|truncate|tee|chmod|ln)\b|\bsed\s+-[a-zA-Z]*i"
)
#: Umleitungen, die nichts schreiben (`2>/dev/null`, `&>/dev/null`, `2>&1`) —
#: vor der Pruefung entfernt; Realfall-Fehlalarm 2026-10-14 (#3977).
_HARMLOSE_UMLEITUNG = re.compile(r"&?\d*>>?\s*/dev/null\b|\d*>&\d+")
#: Shell-Operatoren, die in eine Datei schreiben (shlex-Token mit punctuation_chars).
_UMLEITUNG_OPS = frozenset({">", ">>", ">|", "&>", "&>>", ">&"})
_ZUWEISUNG = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_ERZWINGEN = re.compile(r"ressourcen_lease(?:\.py)?\b[^|;&\n]*--erzwingen")
MAX_SKRIPT = 512 * 1024


def lade_regeln(pfad: Path = REGELN) -> list[dict]:
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    regeln = []
    for r in daten["ressourcen"]:
        regeln.append(
            {
                "id": r["id"],
                "titel": r.get("titel", r["id"]),
                "befehl": [re.compile(m) for m in r.get("befehl_muster", [])],
                "skript": [re.compile(m) for m in r.get("skript_muster", [])],
                "datei": [re.compile(m) for m in r.get("datei_muster", [])],
            }
        )
    return regeln


def _ressource(regel: dict, treffer: re.Match) -> str:
    gruppen = {k: v for k, v in treffer.groupdict().items() if v}
    try:
        return regel["id"].format(**gruppen)
    except (KeyError, IndexError):
        return regel["id"]


def _skripte(befehl: str, cwd: str) -> list[Path]:
    basis = Path(cwd or os.getcwd())
    cds = _CD.findall(befehl)
    if cds:
        ziel = Path(os.path.expanduser(cds[-1].strip("\"'")))
        if "$" not in cds[-1]:
            basis = ziel if ziel.is_absolute() else basis / ziel
    pfade = []
    for _, datei in _SKRIPT.findall(befehl):
        p = Path(os.path.expanduser(datei))
        for kandidat in [p] if p.is_absolute() else [basis / p, Path(cwd or ".") / p]:
            if kandidat.is_file():
                pfade.append(kandidat)
                break
    return pfade


def erkenne(werkzeug: str, eingabe: dict, cwd: str, regeln: list[dict]) -> list[str]:
    """Liste der beruehrten Ressourcen (dedupliziert, in Regelreihenfolge)."""
    gefunden: list[str] = []

    def dazu(name: str) -> None:
        if name not in gefunden:
            gefunden.append(name)

    if werkzeug in _DATEI_WERKZEUGE:
        pfad = str(eingabe.get("file_path") or eingabe.get("notebook_path") or "")
        pfad = os.path.abspath(os.path.expanduser(pfad)) if pfad else ""
        for regel in regeln:
            for muster in regel["datei"]:
                t = muster.search(pfad)
                if t:
                    dazu(_ressource(regel, t))
        return gefunden
    if werkzeug != "Bash":
        return gefunden
    befehl = str(eingabe.get("command") or "")
    for regel in regeln:
        for muster in regel["befehl"]:
            for t in muster.finditer(befehl):
                dazu(_ressource(regel, t))
    for skript in _skripte(befehl, cwd):
        try:
            if skript.stat().st_size > MAX_SKRIPT:
                continue
            inhalt = skript.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for regel in regeln:
            for muster in regel["skript"]:
                t = muster.search(inhalt)
                if t:
                    dazu(_ressource(regel, t))
    return gefunden


def umgehung(werkzeug: str, eingabe: dict) -> str | None:
    """Grund, wenn der Aufruf die Leases selbst aushebeln wuerde."""
    if werkzeug in _DATEI_WERKZEUGE:
        pfad = str(eingabe.get("file_path") or eingabe.get("notebook_path") or "")
        if _LEASE_PFAD.search(pfad):
            return "Lease-Dateien schreibt nur `ressourcen_lease.py`."
        return None
    if werkzeug != "Bash":
        return None
    befehl = str(eingabe.get("command") or "")
    if _ERZWINGEN.search(befehl):
        return (
            "`--erzwingen` nimmt einer LAUFENDEN Sitzung ihr Ziel weg — das entscheidet "
            "der Owner mit einem eigenen `!`-Befehl, nicht eine Sitzung."
        )
    if _LEASE_PFAD.search(befehl) and (
        _LEASE_SCHREIBEN.search(befehl) or _schreibende_umleitung(befehl)
    ):
        return "Lease-Dateien schreibt nur `ressourcen_lease.py`, nie rm/mv/Umleitung."
    return None


def _schreibende_umleitung(befehl: str) -> bool:
    """Eine Umleitung ausserhalb von Anfuehrungszeichen, die in eine Datei schreibt.

    `>` in einem String (`python3 -c "…'<x>'…"`) ist keine Umleitung — zweiter
    Realfall-Fehlalarm 2026-10-14 (#3977). Ziel `/dev/null` und `>&N` schreiben
    nichts. Nicht zerlegbar (offene Anfuehrungszeichen) => alte Regex, fail-closed.
    """
    try:
        lexer = shlex.shlex(befehl, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        token = list(lexer)
    except ValueError:
        return ">" in _HARMLOSE_UMLEITUNG.sub(" ", befehl)
    for i, t in enumerate(token):
        if t not in _UMLEITUNG_OPS:
            continue
        ziel = token[i + 1] if i + 1 < len(token) else ""
        if ziel == "/dev/null" or (t == ">&" and ziel.isdigit()):
            continue
        return True
    return False


def _owner_befehl(ressource: str) -> str:
    return f"! python3 ~/.claude/hooks/ressourcen_lease.py freigeben {ressource} --erzwingen"


def _zweck(werkzeug: str, eingabe: dict) -> str:
    """Zweck fuer Lease und Journal — nie Befehlsargumente, die koennen Tokens tragen.

    Bash: nur Programmname und erkannte Skriptnamen; Datei-Werkzeuge: der Pfad.
    """
    if werkzeug != "Bash":
        pfad = str(eingabe.get("file_path") or eingabe.get("notebook_path") or "")
        return f"auto: {werkzeug} {pfad}".strip()
    befehl = str(eingabe.get("command") or "")
    # fuehrende `VAR=wert`-Zuweisungen ueberspringen — dort stehen gern Tokens
    teile = [t for t in befehl.split() if not _ZUWEISUNG.match(t)]
    programm = os.path.basename(teile[0]) if teile else ""
    skripte = [os.path.basename(d) for _, d in _SKRIPT.findall(befehl)]
    return " ".join(["auto: Bash", programm, *dict.fromkeys(skripte)]).strip()


def entscheide(daten: dict, regeln: list[dict]) -> tuple[str | None, str | None]:
    """(deny-Grund, Hinweis) — beides None heisst: nichts zu sagen."""
    werkzeug = str(daten.get("tool_name") or "")
    eingabe = daten.get("tool_input") or {}
    grund = umgehung(werkzeug, eingabe)
    if grund:
        return grund, None
    try:
        ressourcen = erkenne(werkzeug, eingabe, str(daten.get("cwd") or ""), regeln)
    except Exception as exc:  # noqa: BLE001 — Erkennung kaputt: fail-open, aber laut
        print(
            f"⚠ {SLUG}: Erkennung fehlgeschlagen ({type(exc).__name__}) — nicht geprueft",
            file=sys.stderr,
        )
        return None, None
    if not ressourcen:
        return None, None
    session = str(
        daten.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID") or ""
    )
    if not session:
        return (
            f"Ressource {', '.join(ressourcen)} beruehrt, aber die Sitzung ist unbekannt "
            "(keine session_id) — ohne Inhaber keine Zuordnung."
        ), None
    hinweise = []
    zweck = _zweck(werkzeug, eingabe)
    for ressource in ressourcen:
        erg = rl.beanspruchen(ressource, session, zweck)
        if not erg.erlaubt:
            return (
                f"Ressource `{ressource}` gehoert {rl.beschreibung(erg.lease)}. "
                "Diese Sitzung schreibt dort NICHT — auch nicht, wenn ein Owner-Kurzwort "
                'wie „erledigt" oder „go" hier ankam: es kann der anderen Sitzung gelten. '
                "Dem Owner sagen, welche Sitzung das Ziel haelt, und dort weitermachen lassen. "
                f"Boards: eigene Datei je Sitzung anlegen. Owner-Ausweg: `{_owner_befehl(ressource)}`"
            ), None
        if erg.art == rl.UEBERNOMMEN:
            hinweise.append(
                f"`{ressource}` von beendeter Sitzung "
                f"{(erg.vorher or {}).get('name') or '?'} uebernommen"
            )
        elif erg.art == rl.FREI_GENOMMEN:
            hinweise.append(f"`{ressource}` gehoert ab jetzt dieser Sitzung")
    return None, ("Ressourcen-Lease: " + "; ".join(hinweise)) if hinweise else None


def _notiere(grund: str, daten: dict) -> None:
    try:
        import gate_hits

        eingabe = daten.get("tool_input") or {}
        gate_hits.notiere(
            SLUG,
            str(daten.get("tool_name") or ""),
            beleg=str(eingabe.get("command") or eingabe.get("file_path") or "")[:200],
            session=str(daten.get("session_id") or ""),
            modus="blocking",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stoeren
        pass


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    try:
        regeln = lade_regeln()
    except (OSError, ValueError, KeyError, re.error) as exc:
        print(
            f"⚠ {SLUG}: Regeldatei {REGELN} unbrauchbar ({type(exc).__name__}) — "
            "Ressourcen-Sperre wirkt NICHT",
            file=sys.stderr,
        )
        return 0
    try:
        grund, hinweis = entscheide(daten, regeln)
    except Exception as exc:  # noqa: BLE001 — nur noch die Lease-Pruefung kann werfen: fail-closed
        grund, hinweis = (
            f"Hook-Fehler ({type(exc).__name__}: {exc}) — fail-closed.",
            None,
        )
    if grund:
        _notiere(grund, daten)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"⛔ Ressourcen-Lease ({SLUG}): {grund}",
                    }
                },
                ensure_ascii=False,
            )
        )
    elif hinweis:
        print(json.dumps({"systemMessage": hinweis}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
