#!/usr/bin/env python3
"""PreToolUse(Bash) gate — blockt rohes `pytest`, wo das Repo ein `make test` hat.

GATE_HEADER (KONZ-038 D8):
  "slug": "rohes-pytest-statt-make-test"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-10-08"
  "evidence": "tools/claude-hooks/tests/test_block_rohes_pytest.py"

Hintergrund: Retro `increment-retro-767d40-incr` (platform#3859) Befund #18. In
einer Sitzung liefen 49 rohe pytest-Aufrufe in Repo-Worktrees, obwohl die
Hausregel lautet „Tests: `make test`, nie rohes `pytest`". Das Makefile-Ziel
trägt, was ein roher Aufruf nicht kennt: Testpfade, Einstellungsmodul, Flags der
CI (`--no-migrations`), Umgebung. Ein roher Lauf kann grün sein, wo die CI rot
ist (und umgekehrt).

Der Hook sperrt, wenn BEIDES gilt:
  1. ein Teilbefehl startet pytest (`pytest`, `python[3] -m pytest`,
     `.venv/bin/pytest`, `uv run pytest`, auch nach `cd X &&` oder `;`),
  2. das wirksame Verzeichnis (Ziel des letzten `cd` davor, sonst `cwd` der
     Hook-Eingabe) liegt in einem Git-Repo, dessen Makefile im Wurzelverzeichnis
     ein Ziel `test:` hat.

Die Begründung nennt den Ersatz: `make test ARGS="…"`, wenn das Makefile `ARGS`
verwendet, sonst `make test`.

FAIL-OPEN (bewusste Grenze): kein JSON, kein pytest-Teilbefehl, `cd` mit
Variable/Substitution im Pfad (wirksames Verzeichnis unbekannt), Anführungs-
zeichen nicht geschlossen (Parse-Fehler), Heredoc im Befehl, `pytest --version`/
`--help`, pytest in `docker exec`/`docker compose exec|run` (der Teilbefehl
beginnt nicht mit pytest), Repos ohne Ziel `test:`. Nicht erfasst und deshalb
hier benannt: `bash -c "pytest …"`, `sh -c`, `xargs pytest`, Aufruf über ein
Skript, das pytest selbst startet.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "rohes-pytest-statt-make-test"

#: Ziel `test:` am Zeilenanfang (nicht `test:=` und nicht `.PHONY: test`).
_ZIEL_TEST = re.compile(r"^test[ \t]*:(?!=)", re.MULTILINE)
#: Das Makefile reicht Argumente über `ARGS` durch.
_ARGS = re.compile(r"\$[({]ARGS[)}]")
_ENV_ZUWEISUNG = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_PYTHON = re.compile(r"python(?:3(?:\.\d+)?)?$")
#: Aufrufe, die nichts testen.
_HILFE = frozenset({"--version", "-h", "--help"})
_TRENNER = ("&&", "||", ";", "\n", "|", "&")


def _teilbefehle(kommando: str) -> list[str] | None:
    """Zerlegt an Shell-Trennern ausserhalb von Anführungszeichen.

    None = nicht auswertbar (offenes Anführungszeichen) → fail-open.
    """
    teile: list[str] = []
    aktuell: list[str] = []
    quote = ""
    i = 0
    while i < len(kommando):
        c = kommando[i]
        if quote:
            aktuell.append(c)
            if c == "\\" and quote == '"' and i + 1 < len(kommando):
                aktuell.append(kommando[i + 1])
                i += 1
            elif c == quote:
                quote = ""
        elif c in "'\"":
            quote = c
            aktuell.append(c)
        elif c == "\\" and i + 1 < len(kommando):
            aktuell.append(c)
            aktuell.append(kommando[i + 1])
            i += 1
        else:
            trenner = next((t for t in _TRENNER if kommando.startswith(t, i)), None)
            if trenner:
                teile.append("".join(aktuell))
                aktuell = []
                i += len(trenner)
                continue
            aktuell.append(c)
        i += 1
    if quote:
        return None
    teile.append("".join(aktuell))
    return [t.strip().lstrip("(").strip() for t in teile if t.strip()]


def _basisname(wort: str) -> str:
    return wort.rsplit("/", 1)[-1]


def _startet_pytest(woerter: list[str]) -> bool:
    """Beginnt der Teilbefehl mit einem pytest-Aufruf (ohne reine Hilfe-Aufrufe)?"""
    i = 0
    while i < len(woerter):
        w = woerter[i]
        if _ENV_ZUWEISUNG.match(w) or w in ("time", "command", "exec"):
            i += 1
        elif w == "uv" and woerter[i + 1 : i + 2] == ["run"]:
            i += 2
            while i < len(woerter) and woerter[i].startswith("-"):
                i += 1
        else:
            break
    rest = woerter[i:]
    if not rest:
        return False
    erstes = _basisname(rest[0])
    if erstes in ("pytest", "py.test"):
        argumente = rest[1:]
    elif _PYTHON.match(erstes) and rest[1:3] == ["-m", "pytest"]:
        argumente = rest[3:]
    else:
        return False
    return not (set(argumente) & _HILFE)


def _neues_verzeichnis(woerter: list[str], aktuell: str | None) -> str | None:
    """Wirksames Verzeichnis nach einem `cd`; None = nicht bestimmbar."""
    ziel = [w for w in woerter[1:] if w != "--"]
    if not ziel:
        return str(Path.home())
    pfad = ziel[0]
    if pfad == "-" or "$" in pfad or "`" in pfad:
        return None
    pfad = os.path.expanduser(pfad)
    if os.path.isabs(pfad):
        return pfad
    return os.path.join(aktuell, pfad) if aktuell else None


def _repo_wurzel(verzeichnis: str) -> Path | None:
    """Nächstes Elternverzeichnis mit `.git` (Ordner oder Datei = Worktree)."""
    p = Path(verzeichnis)
    for kandidat in (p, *p.parents):
        if (kandidat / ".git").exists():
            return kandidat
    return None


def _makefile_test(wurzel: Path) -> tuple[bool, bool]:
    """(hat Ziel `test:`, reicht `ARGS` durch)."""
    try:
        text = (wurzel / "Makefile").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False, False
    return bool(_ZIEL_TEST.search(text)), bool(_ARGS.search(text))


def entscheide(kommando: str, cwd: str | None = None) -> str | None:
    """Grund für ein deny oder None (durchlassen)."""
    if "<<" in kommando:
        return None
    teile = _teilbefehle(kommando)
    if teile is None:
        return None
    verzeichnis = cwd or None
    for teil in teile:
        try:
            woerter = shlex.split(teil)
        except ValueError:
            return None
        if not woerter:
            continue
        if woerter[0] == "cd":
            verzeichnis = _neues_verzeichnis(woerter, verzeichnis)
            continue
        if not _startet_pytest(woerter) or verzeichnis is None:
            continue
        wurzel = _repo_wurzel(verzeichnis)
        if wurzel is None:
            continue
        hat_test, hat_args = _makefile_test(wurzel)
        if not hat_test:
            continue
        ersatz = 'make test ARGS="…"' if hat_args else "make test"
        return (
            f"Rohes pytest in `{wurzel.name}`, das ein `make test` hat. Das Ziel "
            "trägt Testpfade, Einstellungen und CI-Flags, die ein roher Aufruf "
            "nicht kennt — grün roh heißt nicht grün in der CI (Retro platform#3859 "
            f"Befund #18: 49 rohe Läufe in einer Sitzung). Stattdessen `{ersatz}`."
        )
    return None


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(daten, dict):
        return 0
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if "pytest" not in kommando and "py.test" not in kommando:
        return 0
    grund = entscheide(kommando, daten.get("cwd") or None)
    if grund is None:
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "rohes pytest statt make test",
            beleg=kommando[:200],
            session=daten.get("session_id", ""),
            modus="blocking",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass
    print(f"⛔ {grund}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
