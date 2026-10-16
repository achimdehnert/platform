#!/usr/bin/env python3
"""PreToolUse(Bash|mcp__github__.*) gate — blockt Issue-/PR-Texte mit Aufschub ohne Anker beim Schreiben.

GATE_HEADER (KONZ-038 D8):
  "slug": "aufschub-anker"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-10-16"
  "evidence": "tools/claude-hooks/tests/test_block_aufschub_ohne_anker.py"

Hintergrund: platform#3859 M7 (Retro 767d40-incr Befund #2, Owner-Wort „M7
bauen“). Ein Kommentar in meiki-lra/meiki-hub#582 fuehrte unter „Bewusst
ausgelassen“ sechs Posten, fuenf ohne Issue. Das Gate aufschub-anker sah das
aus zwei Gruenden nicht:

  * Es sitzt als Workflow nur in platform und prueft dort PR-Texte. Kommentare
    und PRs in Ziel-Repos erreicht es nicht; der Close-Hook greift erst beim
    Schliessen eines Issues.
  * Es zaehlte je Abschnitt: ein Anker im ersten Posten deckte alle. Das ist in
    `deferral_anchor_check.finde_ankerlose_stellen` jetzt je Posten.

Dieser Hook sitzt deshalb am Moment des Schreibens, in jedem Repo:
`gh issue create|comment|edit` und `gh pr create|comment|edit` mit `--body`/`-b`
oder `--body-file`/`-F`. Er prueft den Text mit derselben Funktion wie das Werkzeug.

Ausweitung 2026-10-16 (platform#3862 Punkte 2, 4, 5; Owner-Wort „29 go“):

  * MCP: `mcp__github__*` mit `body` (Issue, Kommentar, PR, Review samt
    Zeilenkommentaren) laeuft durch denselben Pruefkern.
  * Text ausserhalb des Befehls: `-F -` liest den Heredoc im Befehl, eine
    Datei vor `| gh …` (`cat datei |`) oder hinter `< datei`; `--body "$(cat datei)"`,
    `$(< datei)` und `` `cat datei` `` lesen die Datei.
  * Fehlerfaelle zaehlen: Parse-Fehler, Ausnahme und fehlendes Werkzeug stehen
    als Marker `fehler` in gate_hits, ein nicht auffindbarer Text als
    `ungeprueft`. Der Hook bleibt fail-open — ein kaputter Hook sieht damit
    nicht mehr aus wie „kein Treffer“.

Grenzen bleiben, offen in platform#3862: eine PR-Nummer gilt als Anker (Punkt 1),
jede Raute mit Ziffer gilt als Anker (Punkt 3).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from block_issue_close_without_anchor import lade_werkzeug  # noqa: E402

SLUG = "aufschub-anker"
MAX_DATEI = 1_000_000

_SCHREIBEN = re.compile(r"\bgh\s+(issue|pr)\s+(create|comment|edit)\b")
_TRENNER = {"&&", "||", ";", "|", "&"}
_BODY = ("-b", "--body")
_BODY_DATEI = ("-F", "--body-file")
_MCP_GITHUB = "mcp__github__"
_ERSETZUNG = re.compile(r"\$\(\s*(?:cat\s+|<\s*)([^)\s]+)\s*\)|`\s*cat\s+([^`\s]+)\s*`")
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*(?:\n|$)", re.S)
_PIPE_QUELLE = re.compile(r"\bcat\s+([^\s|;&<>]+)[^|;&]*\|\s*gh\b")
_UMLEITUNG = re.compile(r"(?<!<)<\s*([^\s<|;&]+)")


def _lies(wert: str, cwd: str | None) -> str | None:
    pfad = Path(os.path.expanduser(wert.strip("'\"")))
    if not pfad.is_absolute() and cwd:
        pfad = Path(cwd) / pfad
    try:
        if pfad.stat().st_size > MAX_DATEI:
            return None
        return pfad.read_text()
    except (OSError, UnicodeDecodeError):
        return None


def _ersetze(wert: str, cwd: str | None) -> str:
    """`$(cat datei)`, `$(< datei)`, `` `cat datei` `` durch den Dateiinhalt ersetzen."""

    def inhalt(m: re.Match) -> str:
        text = _lies(m.group(1) or m.group(2), cwd)
        return m.group(0) if text is None else text

    return _ERSETZUNG.sub(inhalt, wert)


def _stdin(kommando: str, start: int, cwd: str | None) -> str | None:
    """Text, den `-F -` von stdin liest: Heredoc, `cat datei |` oder `< datei`."""
    for m in _HEREDOC.finditer(kommando, start):
        return m.group(3)
    for m in _PIPE_QUELLE.finditer(kommando[:start]):
        text = _lies(m.group(1), cwd)
        if text is not None:
            return text
    rest = kommando[start:]
    for trenner in ("&&", "||", ";"):
        rest = rest.split(trenner, 1)[0]
    for m in _UMLEITUNG.finditer(rest):
        text = _lies(m.group(1), cwd)
        if text is not None:
            return text
    return None


def erhebe(kommando: str, cwd: str | None) -> tuple[list[tuple[str, str]], list[str]]:
    """(Herkunft, Text) je `gh issue|pr create|comment|edit`, dazu die nicht lesbaren Herkuenfte."""
    gefunden: list[tuple[str, str]] = []
    ungeprueft: list[str] = []
    for treffer in _SCHREIBEN.finditer(kommando):
        try:
            woerter = shlex.split(kommando[treffer.end() :])
        except ValueError:
            ungeprueft.append(f"gh {treffer.group(1)} {treffer.group(2)} (nicht zerlegbar)")
            continue
        herkunft = f"gh {treffer.group(1)} {treffer.group(2)}"
        i = 0
        while i < len(woerter):
            wort = woerter[i]
            if wort in _TRENNER:
                break
            wert = woerter[i + 1] if i + 1 < len(woerter) else ""
            if wort.startswith("--body=") or wort.startswith("--body-file="):
                wort, wert = wort.split("=", 1)
                i -= 1
            if wort in _BODY:
                gefunden.append((herkunft, _ersetze(wert, cwd)))
                i += 2
                continue
            if wort in _BODY_DATEI:
                if wert == "-":
                    text = _stdin(kommando, treffer.end(), cwd)
                    quelle = f"{herkunft} -F -"
                else:
                    text = _lies(wert, cwd) if wert else None
                    quelle = f"{herkunft} -F {wert}"
                if text is None:
                    ungeprueft.append(quelle)
                else:
                    gefunden.append((quelle, text))
                i += 2
                continue
            i += 1
    return gefunden, ungeprueft


def texte(kommando: str, cwd: str | None) -> list[tuple[str, str]]:
    """(Herkunft, Text) je `gh issue|pr create|comment|edit` mit lesbarem Body."""
    return erhebe(kommando, cwd)[0]


def mcp_texte(werkzeug: str, eingabe: dict) -> list[tuple[str, str]]:
    """`body` eines GitHub-MCP-Schreibwerkzeugs, bei Reviews auch die Zeilenkommentare."""
    if not werkzeug.startswith(_MCP_GITHUB):
        return []
    name = werkzeug[len(_MCP_GITHUB) :]
    gefunden = []
    if isinstance(eingabe.get("body"), str):
        gefunden.append((name, eingabe["body"]))
    for k in eingabe.get("comments") or []:
        if isinstance(k, dict) and isinstance(k.get("body"), str):
            gefunden.append((f"{name} Zeilenkommentar", k["body"]))
    return gefunden


def befund(daten: dict, werkzeug=None) -> tuple[str | None, list[str]]:
    """(Ablehnungsgrund oder None, nicht pruefbare Herkuenfte).

    `werkzeug` ist fuer Tests injizierbar. Fehlt das Werkzeug, obwohl Text da ist,
    wirft der Aufruf RuntimeError — main zaehlt das als `fehler`.
    """
    name = str(daten.get("tool_name") or "Bash")
    eingabe = daten.get("tool_input") or {}
    if name.startswith(_MCP_GITHUB):
        stoff, ungeprueft = mcp_texte(name, eingabe), []
    else:
        kommando = eingabe.get("command") or ""
        if not _SCHREIBEN.search(kommando):
            return None, []
        stoff, ungeprueft = erhebe(kommando, daten.get("cwd"))
    if not stoff:
        return None, ungeprueft
    werkzeug = werkzeug or lade_werkzeug()
    if werkzeug is None:
        raise RuntimeError("deferral_anchor_check nicht ladbar")
    stellen = [
        f"{herkunft}, Zeile {nr}: {zeile}"
        for herkunft, text in stoff
        for nr, zeile in werkzeug.finde_ankerlose_stellen(text)
    ]
    if not stellen:
        return None, ungeprueft
    liste = "\n".join(f"  - {s[:160]}" for s in stellen[:6])
    return (
        f"Aufschub-Anker (platform#3859 M7): {len(stellen)} Stelle(n) kuendigen "
        f"Folgearbeit ohne Issue an:\n{liste}\n"
        "Je Posten ein Issue anlegen und im Posten verlinken, oder ein Sammel-Issue "
        "vor dem ersten Posten nennen. Ein Anker deckt nur den Posten, in dem er steht."
    ), ungeprueft


def entscheide(daten: dict, werkzeug=None) -> str | None:
    """Ablehnungsgrund oder None. Ohne Werkzeug fail-open."""
    try:
        return befund(daten, werkzeug)[0]
    except RuntimeError:
        return None


def _notiere(marker: str, daten: dict, beleg: str = "") -> None:
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            marker,
            beleg=beleg[:200],
            session=str(daten.get("session_id") or ""),
            modus="blocking",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        _notiere("fehler", {}, "kein JSON auf stdin")
        return 0
    try:
        grund, ungeprueft = befund(daten)
    except Exception as exc:  # noqa: BLE001 — fail-open, aber gezaehlt
        _notiere("fehler", daten, f"{type(exc).__name__}: {exc}")
        return 0
    for quelle in ungeprueft:
        _notiere("ungeprueft", daten, quelle)
    if grund is None:
        return 0
    eingabe = daten.get("tool_input") or {}
    _notiere("gh issue/pr Text", daten, str(eingabe.get("command") or daten.get("tool_name") or ""))
    antwort = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": grund,
        }
    }
    print(json.dumps(antwort, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 — Hook darf nie die Sitzung blockieren
        _notiere("fehler", {}, "Ausnahme ausserhalb von main")
        sys.exit(0)
