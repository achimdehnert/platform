#!/usr/bin/env python3
"""PreToolUse(Bash) — warnt, wenn eine Shell-Umleitung in ein Git-Arbeitsverzeichnis schreibt.

GATE_HEADER (KONZ-038 D8):
  "slug": "inline-heredoc-quoting-rework"
  "mode": "advisory"
  "owner": "achim"
  "last_drill_pass": "2026-09-23"
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
  * Der Scratchpad und alles außerhalb der Repo-Wurzeln.
  * Bei `sed -i` gilt das LETZTE Token des Abschnitts als Ziel. Das trifft die
    reale Form (`sed -i 's/a/b/' datei`); `sed -i -e ... datei1 datei2` erkennt
    nur die zweite Datei.

ADVISORY: der Hook blockt nicht, er schreibt eine Zeile nach stderr und lässt den
Befehl laufen. Grund: die Fehlalarm-Grenzen oben sind Hypothesen, bis `gate_hits`
sie gemessen hat. Umstellen auf blocking = `MODUS`-Datei anlegen, s. `_modus()`.
Die Frist dafür ist gesetzt und getrackt: 2026-10-21, danach blocking oder
gestrichen — platform#3451 (`expires` im Registry-Eintrag).
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

#: Der Scratchpad liegt je nach Sitzung woanders; erkannt wird er am Namen.
#: Wegwerf-Skripte dort sind ausdrücklich erlaubt (Owner-Entscheid 2026-09-21).
_AUSGENOMMEN = re.compile(r"/scratchpad/|/\.git/|/node_modules/")

#: Heredoc-Körper: reiner Text, darf Umleitungszeichen enthalten, ohne dass
#: daraus ein Schreibziel wird (`cat <<'X'` mit `> foo` im Fließtext).
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1\s*\n.*?\n\2\b", re.S)
#: Anführungszeichen-Spannen: ein `>` in einem PR-Text ist keine Umleitung.
_GEQUOTET = re.compile(r"'[^']*'|\"[^\"]*\"", re.S)

#: `> pfad` / `>> pfad` — nicht `>&`, nicht `2>&1`.
_UMLEITUNG = re.compile(r"(?<![0-9&>])>>?\s*(?![&|])([^\s;&|<>]+)")
#: `tee [-a] pfad`
_TEE = re.compile(r"\btee\b(?:\s+-\w+)*\s+([^\s;&|<>]+)")
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


def _modus() -> str:
    """advisory (Default) | blocking. Anders herum als beim Evidenz-Scanner:
    dieses Gate startet bewusst advisory, weil seine Fehlalarm-Grenzen ungemessen
    sind. Eine fehlende Datei heisst hier advisory, nicht blocking."""
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
        return "advisory"
    return "blocking" if wert == "blocking" else "advisory"


def _ohne_text(kommando: str) -> str:
    """Heredoc-Körper und gequotete Spannen entfernen — dort steht Text, kein Befehl."""
    ohne = _HEREDOC.sub(" ", kommando)
    return _GEQUOTET.sub(" ", ohne)


def _abschnitt(kommando: str, start: int) -> str:
    rest = kommando[start:]
    ende = re.search(r"&&|\|\||;|\n|\|", rest)
    return rest[: ende.start()] if ende else rest


def _ziele(kommando: str) -> list[str]:
    """Alle Pfade, in die dieser Befehl schreiben würde."""
    sauber = _ohne_text(kommando)
    ziele = [m.group(1) for m in _UMLEITUNG.finditer(sauber)]
    ziele += [m.group(1) for m in _TEE.finditer(sauber)]
    for treffer in _INPLACE.finditer(sauber):
        teile = _abschnitt(sauber, treffer.start()).split()
        if len(teile) > 1:
            ziele.append(teile[-1])
    # Skript-Heredoc: der Interpreter schreibt, nicht die Shell. Hier wird der
    # ROHE Befehl gelesen (nicht `sauber`) — der Pfad steht ja gerade im
    # Skripttext, den `_ohne_text` entfernt haette.
    if _SKRIPT_HEREDOC.search(kommando) and _SKRIPT_SCHREIBT.search(kommando):
        ziele += _PFAD_IM_TEXT.findall(kommando)
    return ziele


def _im_repo(pfad: str, cwd: str) -> Path | None:
    """Aufgelöster Pfad, wenn er in einem Repo-Arbeitsverzeichnis liegt — sonst None."""
    if "$" in pfad or "`" in pfad or pfad.startswith("/dev/"):
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
    for wurzel in _REPO_WURZELN:
        try:
            p.relative_to(wurzel)
        except ValueError:
            continue
        return p
    return None


def entscheide(kommando: str, cwd: str) -> str | None:
    """Grund für die Meldung oder None (durchlassen)."""
    for ziel in _ziele(kommando):
        p = _im_repo(ziel, cwd)
        if p is None:
            continue
        return (
            f"Shell-Umleitung schreibt nach `{p}` — das liegt in einem "
            "Git-Arbeitsverzeichnis. Dafür ist das Edit/Write-Werkzeug da: ein "
            "Anführungszeichen im Text oder ein verschobener Anker kippt einen "
            "Shell-Patch still, während Edit laut scheitert. Heredocs an die "
            "Standardeingabe (`git commit -F -`) und Wegwerf-Skripte im Scratchpad "
            "sind nicht gemeint."
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
    modus = _modus()
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "Shell-Schreibziel im Repo",
            beleg=kommando[:200],
            session=daten.get("session_id", ""),
            modus=modus,
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass
    if modus == "blocking":
        print(f"⛔ {grund}", file=sys.stderr)
        return 2
    print(f"⚠️  {grund}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
