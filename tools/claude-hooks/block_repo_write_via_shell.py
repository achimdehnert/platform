#!/usr/bin/env python3
"""PreToolUse(Bash) — blockt, wenn ein Shell-Befehl in ein Git-Arbeitsverzeichnis schreibt.

GATE_HEADER (KONZ-038 D8):
  "slug": "inline-heredoc-quoting-rework"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-10-16"
  "evidence": "tools/claude-hooks/tests/test_block_repo_write_via_shell.py"

Hintergrund: der Slug steht mit fünf Vorkommen über Retros in der Registry, davon
drei am 2026-09-21 und vier am 2026-09-23 — einmal beim Retro-Report selbst. Die
Hausregel („Repo-Dateien nur per Edit/Write-Tool, nie per Bash-Heredoc") ist seit
2026-09-21 als `declined` geführt, weil der Owner sie weich halten wollte. Sie hat
in der Form nicht gehalten.

**Der Auslöser ist bewusst nicht `<<HEREDOC`.** Ein Hook auf Heredocs hätte an einem
einzigen Arbeitstag jeden `git commit -F - <<'MSG'` blockiert — legitim, häufig,
und nach zwei Stunden wäre der Hook abgeschaltet. Ein Heredoc, der an die Standard-
eingabe eines Kommandos geht, schreibt keine Datei und ist harmlos.

Gefährlich ist das **Schreibziel**: eine Umleitung (`>`, `>>`, `tee`) oder ein
In-Place-Editor (`sed -i`, `perl -i`), deren Pfad in einem Git-Arbeitsverzeichnis
liegt. Dort kippt ein Anführungszeichen im Text oder ein verschobener Anker den
Patch still — F821, halbe Ersetzung, kein Fehlerausgang. Das Edit-Werkzeug kann
das nicht: es scheitert laut, wenn der Anker nicht eindeutig ist.

FAIL-OPEN (bewusste Grenzen, hier benannt statt im Gate behauptet):
  * Variable oder Kommando-Substitution im Pfad (`> "$S/x.json"`, `> $(mktemp)`)
    — der Pfad ist zur Prüfzeit unbekannt, der Hook schweigt.
  * Kein `cwd` im Hook-Payload und relativer Pfad — nicht auflösbar, schweigt.
  * Umleitungen in Dateideskriptoren (`2>&1`, `>&2`) und `/dev/*`.
  * Der Scratchpad und alles außerhalb der Repo-Wurzeln. Ausnahme seit
    2026-10-16: ein Git-Arbeitsverzeichnis IM Scratchpad (ein Vorfahr trägt
    `.git`) zählt als Repo — Retro c5851a Befund 1, Owner-Wort „G1-go“.
  * Bei `sed -i` gilt das LETZTE Token des Abschnitts als Ziel. Das trifft die
    reale Form (`sed -i 's/a/b/' datei`); `sed -i -e ... datei1 datei2` erkennt
    nur die zweite Datei.

  * Ein `cd` mit Variable oder `cd -` macht das Verzeichnis unbekannt; relative
    Pfade danach schweigen.

BLOCKING seit 2026-10-14 (Retro 161b19 Befund 1, Owner-Wort „R1 go"): ein Schreibziel
im Repo endet mit Exit 2. Die frühere „0 Treffer"-Messung, auf der die Streichung
vom 2026-10-08 stand, kam aus einer fehlenden Verdrahtung — der Hook lag in
`~/.claude/hooks/`, aber kein Eintrag in `settings.json` rief ihn auf. Das Replay
über 21 Tage echter Bash-Befehle ersetzt das Kalibrierfenster (Zahlen im
Registry-Eintrag). Der Inline-Text-Fall („…" mit ASCII-Schluss) bleibt advisory:
dort fand dasselbe Replay Fehlalarme (Text in einfachen Anführungszeichen,
`\\"`-Escape). Zurück auf advisory = Modus-Datei mit `advisory`, s. `_modus()`.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "inline-heredoc-quoting-rework"

#: Wurzeln, unter denen ein Pfad als Repo-Arbeitsverzeichnis gilt.
_REPO_WURZELN = (
    Path.home() / "github",
    Path.home() / ".repo-session" / "worktrees",
)

#: Git-Interna und Abhängigkeiten sind nie ein Ziel dieser Regel.
_AUSGENOMMEN = re.compile(r"/\.git/|/node_modules/")

#: Der Scratchpad liegt je nach Sitzung woanders; erkannt wird er am Namen.
#: Wegwerf-Skripte dort sind ausdrücklich erlaubt (Owner-Entscheid 2026-09-21) —
#: aber nicht ein Git-Worktree, der dort liegt (Owner-Wort „G1-go“ 2026-10-16).
#: Realfall Retro c5851a Befund 1: `git worktree add <scratchpad>/wt-181`, danach
#: `cd <scratchpad>/wt-181 && python3 - <<'EOF'` mit `p.write_text(s)` auf eine
#: Repo-Datei — Konfliktauflösung per Regex, ungeblockt.
_SCRATCHPAD = "scratchpad"


def _git_worktree_im_scratchpad(p: Path) -> bool:
    """True, wenn zwischen `p` und dem Scratchpad ein Verzeichnis `.git` trägt.

    Ein Worktree hat `.git` als Datei, ein Klon als Verzeichnis — `exists()` deckt
    beides. Die Suche endet am Scratchpad selbst: der ist nie das Repo.
    """
    for d in (p, *p.parents):
        if d.name == _SCRATCHPAD:
            return False
        try:
            if (d / ".git").exists():
                return True
        except OSError:
            return False
    return False

#: Heredoc-Körper: reiner Text, darf Umleitungszeichen enthalten, ohne dass
#: daraus ein Schreibziel wird (`cat <<'X'` mit `> foo` im Fließtext).
#: Der Rest der Startzeile (`<<'MSG' && git push`) ist Befehl und bleibt stehen;
#: der Körper darf leer sein und endet an der Zeile, die nur den Begrenzer trägt.
_HEREDOC = re.compile(
    r"<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1([^\n]*)\n(?:.*?\n)??\t*\2(?=[ \t]*(?:\n|$))",
    re.S,
)
#: Anführungszeichen-Spannen: ein `>` in einem PR-Text ist keine Umleitung.
_GEQUOTET = re.compile(r"'[^']*'|\"[^\"]*\"", re.S)

#: `> pfad` / `>> pfad` — nicht `>&`, nicht `2>&1`.
#: Nur Leerzeichen/Tab bis zum Ziel: ein `\s*` lief über den Zeilenumbruch und las
#: das erste Wort der NÄCHSTEN Zeile als Ziel (Replay 2026-10-14: `gh`, `echo`).
_UMLEITUNG = re.compile(r"(?<![0-9&>-])>>?[ \t]*(?![&|=])([^\s;&|<>]+)")
#: `tee [-a] pfad`
_TEE = re.compile(r"\btee\b(?:[ \t]+-\w+)*[ \t]+([^\s;&|<>]+)")
#: `sed -i` / `perl -i` — Ziel ist das letzte Token des Abschnitts.
_INPLACE = re.compile(r"\b(?:sed|perl|ruby)\s+(?:-\w*i\w*|--in-place)\b")

#: Ein Skript, das seine Quelle per Heredoc oder `-c` bekommt. Hier schreibt
#: nicht die Shell, sondern der Interpreter — es gibt kein Umleitungszeichen zu
#: finden. Gemessen am eigenen Fall: dieser Hook wurde am 2026-09-23 gebaut und
#: schon beim Eintragen seines eigenen Registry-Eintrags umgangen, weil
#: `python3 - <<'PY'` mit `p.write_text(...)` keine Umleitung enthaelt.
#: `git commit -F - <<'MSG'` bleibt frei: git ist kein Interpreter.
_SKRIPT_HEREDOC = re.compile(
    r"\b(?:python3?|perl|ruby|node)\b[^\n|;&]*(?:<<-?\s*['\"]?[A-Za-z_]|-c\s)"
)
#: Schreibende Aufrufe innerhalb eines solchen Skripts.
_SKRIPT_SCHREIBT = re.compile(
    r"\.write_text\(|\.write\(|open\([^)]*['\"][wa]|json\.dump\(|yaml\.(?:safe_)?dump\("
)
#: Ein Pfad im Skripttext, der auf eine Repo-Datei zeigt.
_PFAD_IM_TEXT = re.compile(r"['\"]([A-Za-z0-9_./-]+/[A-Za-z0-9_.-]+\.[a-z]{1,5})['\"]")
#: Das Literal direkt im schreibenden Aufruf — fängt auch Dateien auf oberster
#: Ebene (`open('CHANGELOG.md', 'a')`), die `_PFAD_IM_TEXT` ohne `/` nicht sieht.
_SCHREIB_LITERAL = re.compile(
    r"open\(\s*['\"]([^'\"\n]+)['\"]\s*,\s*['\"][wa]"
    r"|Path\(\s*['\"]([^'\"\n]+)['\"]\s*\)\.write_(?:text|bytes)\("
)

#: Ausweitung 2026-09-24 (Retro 02b7f5, platform#3545 §5a): dieselbe Fehlerklasse ohne
#: Schreibziel. Ein Inline-Text an `gh … --body "…"` oder `git commit -m "…"` mit einem
#: deutschen „…", das mit einem ASCII-`"` statt `“` endet: das ASCII-Zeichen beendet den
#: Shell-String. Zweimal an einem Tag — ein Issue-Kommentar kam abgeschnitten an, ein
#: Commit scheiterte. Ein korrekt geschlossenes „…“ bleibt still.
_INLINE_TEXT = re.compile(r"(?:^|\s)(?:--body|--title|--message|-m|-b)\s+\"")
_ASCII_SCHLUSS = re.compile(r"„[^“\"\n]*\"")


def inline_quote_bricht(kommando: str) -> bool:
    """Inline-Text mit „…" (ASCII-Schluss) — Heredoc-Körper zählen nicht."""
    ohne_heredoc = _ohne_heredoc(kommando)
    return bool(
        _INLINE_TEXT.search(ohne_heredoc) and _ASCII_SCHLUSS.search(ohne_heredoc)
    )


def _modus() -> str:
    """blocking (Default) | advisory. Bis 2026-10-14 umgekehrt — damals waren die
    Fehlalarm-Grenzen ungemessen. Die Datei mit `advisory` ist der Rückweg ohne
    Code-Änderung, falls im Betrieb doch ein Fehlalarm auftaucht."""
    verzeichnis = Path(
        os.environ.get(
            "REPO_WRITE_HOOK_STATE_DIR", str(Path.home() / ".claude/hooks/state")
        )
    )
    try:
        wert = (
            (verzeichnis / "repo_write_hook_mode").read_text(encoding="utf-8").strip()
        )
    except OSError:
        return "blocking"
    return "advisory" if wert == "advisory" else "blocking"


#: Platzhalter für ausgeblendeten Text — kommt in keinem echten Pfad vor.
_AUSGEBLENDET = "\x00"


def _ohne_heredoc(kommando: str) -> str:
    return _HEREDOC.sub(lambda m: " " + m.group(3), kommando)


def _ohne_text(kommando: str) -> str:
    """Heredoc-Körper und gequotete Spannen entfernen — dort steht Text, kein Befehl.

    Gequotete Spannen werden LÄNGENTREU durch `_AUSGEBLENDET` ersetzt: eine Position
    in diesem Text ist dieselbe wie in `_ohne_heredoc`, aus dem `_cwd_bei` das
    `cd`-Ziel samt Anführungszeichen liest. Und ein gequotetes Ziel
    (`> "$S/x.md"`) bleibt ein Wort, das `_im_repo` als unbekannt verwirft — statt
    dass die Umleitung das nächste Wort als Ziel greift.
    """
    return _GEQUOTET.sub(
        lambda m: _AUSGEBLENDET * len(m.group()), _ohne_heredoc(kommando)
    )


#: `cd` am Anfang eines Teilbefehls (gesucht im bereinigten Text, damit ein „cd" in
#: einem PR-Text nicht zählt) und sein Argument (gelesen im Text MIT Quotes).
_CD = re.compile(r"(?:^|&&|\|\||[;\n(|&])\s*cd\b")
_CD_ZIEL = re.compile(r"[ \t]+('[^']*'|\"[^\"]*\"|[^\s;&|)]+)")
#: Erster Interpreter-Aufruf: ab hier gilt das Verzeichnis für Pfade im Skripttext.
_INTERPRETER = re.compile(r"\b(?:python3?|perl|ruby|node)\b")


def _cwd_bei(kommando: str, cwd: str, bis: int) -> str:
    """Wirksames Verzeichnis an Position `bis`: Ziel des letzten `cd` davor, sonst cwd.

    Realfall Retro 161b19 Befund 1: `cd <worktree> && python3 - <<'EOF'` mit
    relativem Pfad im Skript — gegen das Payload-`cwd` aufgelöst zeigte die Meldung
    auf den falschen Klon, und aus einem cwd außerhalb der Repo-Wurzeln (Scratchpad)
    wäre derselbe Befehl gar nicht gefallen. "" = nicht bestimmbar (fail-open).
    """
    sauber = _ohne_text(kommando)
    roh = _ohne_heredoc(kommando)
    aktuell = cwd
    for treffer in _CD.finditer(sauber):
        if treffer.end() > bis:
            break
        arg = _CD_ZIEL.match(roh, treffer.end())
        ziel = arg.group(1).strip("'\"") if arg else ""
        if not ziel or ziel == "--":
            aktuell = str(Path.home())
        elif ziel == "-" or "$" in ziel or "`" in ziel:
            aktuell = ""
        else:
            ziel = os.path.expanduser(ziel)
            if os.path.isabs(ziel):
                aktuell = ziel
            else:
                aktuell = os.path.join(aktuell, ziel) if aktuell else ""
    return aktuell


def _abschnitt(kommando: str, start: int) -> str:
    rest = kommando[start:]
    ende = re.search(r"&&|\|\||;|\n|\|", rest)
    return rest[: ende.start()] if ende else rest


def _ziele(kommando: str) -> list[tuple[str, int]]:
    """Alle Pfade, in die dieser Befehl schreiben würde, je mit ihrer Position."""
    sauber = _ohne_text(kommando)
    ziele = [(m.group(1), m.start()) for m in _UMLEITUNG.finditer(sauber)]
    ziele += [(m.group(1), m.start()) for m in _TEE.finditer(sauber)]
    for treffer in _INPLACE.finditer(sauber):
        teile = _abschnitt(sauber, treffer.start()).split()
        # Ein gequotetes `"$R"` ist hier schon ausgeblendet; dann bliebe die
        # Option selbst als letztes Token stehen und würde als Pfad gelesen.
        if len(teile) > 2 and not teile[-1].startswith("-"):
            ziele.append((teile[-1], treffer.start()))
    # Skript-Heredoc: der Interpreter schreibt, nicht die Shell. Hier wird der
    # ROHE Befehl gelesen (nicht `sauber`) — der Pfad steht ja gerade im
    # Skripttext, den `_ohne_text` entfernt haette.
    if _SKRIPT_HEREDOC.search(kommando) and _SKRIPT_SCHREIBT.search(kommando):
        aufruf = _INTERPRETER.search(sauber)
        stelle = aufruf.start() if aufruf else len(sauber)
        ziele += [(p, stelle) for p in _pfade_im_skript(kommando)]
    return ziele


def _pfade_im_skript(kommando: str) -> list[str]:
    """Pfad-Literale im Skripttext — ohne angehängte Segmente.

    `Path.home() / ".claude/x.md"` nennt einen relativen String, der aber an eine
    unbekannte Basis gehängt wird. Gegen das cwd aufgelöst landete er im Repo —
    der erste Fehlalarm des Replays vom 2026-10-14.
    """
    pfade = []
    for treffer in _PFAD_IM_TEXT.finditer(kommando):
        davor = kommando[: treffer.start()].rstrip()
        if davor.endswith("/"):
            continue
        pfade.append(treffer.group(1))
    pfade += [a or b for a, b in _SCHREIB_LITERAL.findall(kommando)]
    return pfade


#: Zeichen, die ein zur Prüfzeit bekannter Dateipfad nicht trägt: Variable,
#: Substitution, ausgeblendeter Text, Glob, Regex-Rest aus einem ungleich
#: gequoteten Befehl (Replay 2026-10-14: `]{0,60}(invoice`, `6}s`, `[^`).
_KEIN_PFAD = re.compile("[$`\"'\\\\*?{}\\[\\]()<>^" + _AUSGEBLENDET + "]")


def _im_repo(pfad: str, cwd: str) -> Path | None:
    """Aufgelöster Pfad, wenn er in einem Repo-Arbeitsverzeichnis liegt — sonst None."""
    if _KEIN_PFAD.search(pfad) or pfad.startswith("/dev/"):
        return None  # zur Pruefzeit unbekannt: fail-open
    p = Path(pfad).expanduser()
    if not p.is_absolute():
        if not cwd:
            return None
        p = Path(cwd) / p
    try:
        p = Path(os.path.normpath(str(p)))
    except (OSError, ValueError):
        return None
    if _AUSGENOMMEN.search(str(p) + "/"):
        return None
    if f"/{_SCRATCHPAD}/" in str(p) + "/":
        return p if _git_worktree_im_scratchpad(p) else None
    for wurzel in _REPO_WURZELN:
        try:
            p.relative_to(wurzel)
        except ValueError:
            continue
        return p
    return None


def entscheide(kommando: str, cwd: str) -> str | None:
    """Grund für die Meldung oder None (durchlassen)."""
    for ziel, stelle in _ziele(kommando):
        p = _im_repo(ziel, _cwd_bei(kommando, cwd, stelle))
        if p is None:
            continue
        return (
            f"Repo-Dateien nur per Edit/Write: dieser Shell-Befehl schreibt nach `{p}`, "
            "und das liegt in einem Git-Arbeitsverzeichnis. Ein "
            "Anführungszeichen im Text oder ein verschobener Anker kippt einen "
            "Shell-Patch still, während Edit laut scheitert. Heredocs an die "
            "Standardeingabe (`git commit -F -`) und Wegwerf-Skripte im Scratchpad "
            "sind nicht gemeint — ein Git-Worktree im Scratchpad schon."
        )
    if inline_quote_bricht(kommando):
        return (
            'Inline-Text mit „…" an `--body`/`--title`/`-m`: das ASCII-Schlusszeichen '
            "beendet den Shell-String, der Text kommt abgeschnitten an oder der Befehl "
            "scheitert. Text in eine Datei schreiben (Write-Werkzeug) und per "
            "`--body-file` bzw. `git commit -F` übergeben."
        )
    return None


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not kommando:
        return 0
    grund = entscheide(kommando, str(daten.get("cwd") or ""))
    if grund is None:
        return 0
    inline = grund.startswith("Inline")
    modus = "advisory" if inline else _modus()
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "Inline-Text mit ASCII-Schluss" if inline else "Shell-Schreibziel im Repo",
            beleg=kommando[:200],
            session=daten.get("session_id", ""),
            modus=modus,
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass
    if modus == "blocking":
        print(
            f"⛔ {grund} (Hook-Rückmeldung, keine Ablehnung durch den Nutzer — "
            "derselbe Schritt per Edit/Write geht durch.)",
            file=sys.stderr,
        )
        return 2
    print(f"⚠️  {grund}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
