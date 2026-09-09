#!/usr/bin/env python3
"""ci_deckung.py — laeuft eine lokal vorhandene Pruefung auch im CI, oder nie?

## Warum es das gibt

Der Befund-Slug `ci-gate-narrower-than-local-test` ist dreimal aufgetreten und trug
bis hierhin kein Gate:

- **robo-lab, 2026-08-28**: `sim/test_stream_gate.py` steht als Makefile-Ziel
  `stream-gate`, der CI-Job installiert nur `mujoco numpy` und ruft es nie auf
  (`docs/retros/session-retro-2026-08-28-robo-lab-54195f.md` Zeile 40).
- **robo-lab, 2026-09-07**: der vendor-abhaengige Exo-Pfad laeuft nie in CI —
  `make exo-konformitaet-myoassist` wird von keinem Workflow aufgerufen
  (`docs/retros/session-retro-2026-09-07-robo-lab-6972fc.md` Zeile 47). Zweites
  Vorkommen desselben Slugs im selben Repo ⇒ GATE-PFLICHT (`retro_kpis.py`).
- **chat-hub, 2026-09-06** (iilgmbh/chat-hub#79): `ruff format --check` fehlte
  in der CI, `ruff check` lief. Bei der Nachmessung fuer dieses Gate zeigte sich:
  `ruff format --check` war **nie** ein Makefile-Ziel in chat-hub, sondern nur ein
  Schritt in einer manuellen Vorab-Push-Pruefung (platform#2860) — dieses Werkzeug
  vergleicht Makefile↔CI, nicht Doku↔CI, und haette den Fall darum nie im
  Makefile-Scope gefunden. Der Drill bildet trotzdem die FORM des Falls nach (ein
  Rezept-Kommando, das lokal existiert und im CI fehlt) als Fixture nach — siehe
  `tools/tests/test_ci_deckung.py`, Docstring dort nennt die Einschraenkung explizit.

## Was gemessen wird

1. `Makefile` je Repo parsen: Ziele, deren Rezept ein Pruefwerkzeug ausfuehrt
   (`CHECK_TOOL_PREFIXES` unten) ODER ein Skript `test_*.py` / `*_test.py` direkt
   startet (der robo-lab-Fall — kein `pytest`-Aufruf, ein roher Skriptstart).
2. Kommandos NORMALISIEREN: Make-Variablen (`$(TEST_PY)`, `$(PYTHON)`) und reine
   Ausgabeflags (`-q`, `-v`, `--no-header`) fallen weg, ebenso ein Flag, dessen WERT
   eine Make-Variable ist (`--seed $(SEED)` → weg, der Wert ist nicht literal
   vergleichbar). Ein fuehrender Interpreter (`python`/`python3`) vor einem `.py`-
   Skript faellt weg wie `$(PYTHON)`. **Pfade sind bedeutungstragend und bleiben
   stehen** — `$(TEST_PY) -m pytest tests/ -q` → `pytest tests/`, nicht `pytest`.
3. `.github/workflows/*.yml` parsen: jeden `run:`-Block (inline und Blockskalar)
   in Einzelzeilen zerlegen, `make <ziel>`-Aufrufe gesondert erfassen.
4. Gedeckt ist ein Makefile-Kommando, wenn ein Workflow entweder sein Ziel per
   `make <ziel>` aufruft ODER dasselbe normalisierte Kommando inline ausfuehrt.
   Ungedeckt = Befund: "lokal vorhanden, im CI nie ausgefuehrt".

## Erweiterung ueber die acht Werkzeugnamen hinaus (Realfall 2, Pflicht)

Die acht Namen oben reichen fuer Realfall 1 nicht aus (`sim/test_stream_gate.py`
ist ein roher Skriptstart, kein `pytest`-Aufruf — Punkt 1 hat die Ausnahme dafuer)
und fuer Realfall 2 (`exo-konformitaet-myoassist`, robo-lab 2026-09-07) erst recht
nicht: das Rezept ruft `exo/konformitaet.py --adapter myoassist ...` — weder ein
bekanntes Werkzeug noch ein `test_*.py`-Dateiname. Was den Fall trotzdem sicher
markiert, ist der ZIELNAME selbst: `exo-konformitaet-myoassist` enthaelt das
Segment `konformitaet`. Ein zweites, generalisierbares Kriterium (`ZIEL_SCHLUESSELWOERTER`
unten) erkennt darum zusaetzlich Ziele, deren NAME (durch `-`/`_` getrennt) ein
Pruef-Schluesselwort traegt (`test`, `check`, `lint`, `verify`, `konformitaet`,
`selbsttest`, `gegenprobe`, `gate` — Wortgrenze, nicht Teilstring: `latest` matcht
nicht). Das ist bewusst WEITER als die acht Werkzeugnamen und bewusst NICHT auf
robo-lab zugeschnitten (kein `konformitaet`-Sonderfall im Code, nur ein Wort in
einer Menge) — mit der Konsequenz, dass es fleet-weit mehr NAMEN als
Pruef-Kommando einstuft, darunter legitime Ausnahmen wie ein `chat-verify`-Ziel,
das echten Serverzugriff braucht. Genau dafuer existiert der Verzicht
(`governance/ci-deckung-verzicht.yaml`) — ein Treffer aus diesem zweiten
Kriterium ist ein Befund, der entweder gedeckt, verzichtet oder tatsaechlich eine
Luecke ist, nicht automatisch falsch. Shell-Fuellwoerter innerhalb eines so
markierten Ziels (`echo`, `set`, `test -f`, `. datei`, `exit`, …) werden dabei
verworfen — nur eine Zeile, die wirklich ein Skript/Werkzeug aufruft, zaehlt.

## Falsifikation (Pflicht, kein Kuer)

Wo die Entscheidung nicht sicher ist, wird NICHT PRUEFBAR gemeldet statt eines
stillen Treffers oder einer stillen Luecke:

- Makefile vorhanden, aber keine Tab-Rezeptzeile gefunden (Leerzeichen-Rezepte,
  generiertes Makefile) → das ganze Repo ist NICHT PRUEFBAR.
- Ein Workflow referenziert einen wiederverwendbaren Workflow
  (`uses: .../.github/workflows/...`) oder eine lokale Composite-Action
  (`uses: ./...`) → deren Inhalt ist von hier aus nicht einsehbar; jedes sonst
  ungedeckte Kommando dieses Repos wird NICHT PRUEFBAR statt Befund.
- Ein `run:`-Kommando enthaelt eine Matrix-Expression (`${{ matrix.* }}`) an einer
  Stelle, die das Werkzeug/Ziel bestimmt → dieses eine Kommando ist NICHT PRUEFBAR.

## Bewusster Verzicht

`governance/ci-deckung-verzicht.yaml` (Default-Pfad, relativ zu diesem Repo, NICHT
zum gescannten `--repo`) haelt legitime Ausnahmen fest — GPU, echte Hardware,
Prod-Zugriff. Schema: eine Liste von Eintraegen `repo`, `ziel`, `grund`. `grund`
ist Pflicht; ein Eintrag ohne ihn ist ungueltig und wird als Fehler gemeldet, nicht
stillschweigend als Verzicht gewertet. Bewusst OHNE PyYAML geparst (stdlib-only,
siehe unten) — das Schema ist flach genug fuer einen Handparser.

## Aufruf

    python3 tools/ci_deckung.py --repo ~/github/robo-lab   # voller Report
    python3 tools/ci_deckung.py --repo ~/github/robo-lab --kurz
    python3 tools/ci_deckung.py --repo ~/github/robo-lab --json

Exit-Code 0 immer — Report-Werkzeug, kein Enforcer (Hausform wie `gate_deckung.py`,
`gate_namensdeckung.py`). stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass

# Maschinenlesbarer Kopf (KONZ-038 D8)
GATE_HEADER = {
    "slug": "ci-gate-narrower-than-local-test",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-09-09",
    "evidence": "tools/tests/test_ci_deckung.py",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_VERZICHT = os.path.join(REPO_ROOT, "governance", "ci-deckung-verzicht.yaml")

# Rezept-Praefixe, die ein Ziel als "Pruef-Kommando" markieren. Zusaetzlich zaehlt
# jedes Kommando, dessen erstes Token ein Skript `test_*.py` / `*_test.py` direkt
# startet (robo-lab: `$(PYTHON) sim/test_stream_gate.py`, kein `pytest`-Aufruf).
CHECK_TOOL_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("pytest",),
    ("ruff",),
    ("shellcheck",),
    ("mypy",),
    ("bandit",),
    ("manage.py", "check"),
    ("manage.py", "test"),
    ("npm", "test"),
)
TEST_SCRIPT_RE = re.compile(r"(?:^|/)(test_[\w\-]+|[\w\-]+_test)\.py$")

# Zweites, generalisierbares Kriterium (siehe Docstring "Erweiterung"): ein
# Zielname mit einem dieser Segmente gilt als Pruef-Kandidat, auch wenn sein
# Rezept keinem bekannten Werkzeug entspricht. Wortgrenze durch `-`/`_`, kein
# Teilstring-Match — sonst matcht "latest" auf "test".
ZIEL_SCHLUESSELWOERTER = {
    "test",
    "tests",
    "check",
    "checks",
    "lint",
    "verify",
    "konformitaet",
    "konformität",
    "selbsttest",
    "gegenprobe",
    "gate",
}

# Reine Ausgabeflags — normalisiert weg, tragen keine Bedeutung fuer den Vergleich.
OUTPUT_FLAGS = {"-q", "--quiet", "-v", "--verbose", "-vv", "--no-header"}
INTERPRETER_NAMES = {"python", "python3", "py"}

# Shell-Fuellwoerter/Builtins: fuehren sie ein Kommando an, ist es kein
# Werkzeugaufruf, sondern Ablaufsteuerung (Realfall chat-hub `chat-verify`:
# `test -f ... || { ... }`, `set -a`, `. ./deploy/.env`).
SHELL_NOOP_ODER_BUILTIN = {
    "echo",
    "true",
    ":",
    "exit",
    "cd",
    "set",
    ".",
    "source",
    "test",
    "export",
    "umask",
    "trap",
    "wait",
    "{",
    "}",
}

ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
MAKEVAR_RE = re.compile(r"^\$[\(\{][\w.\-]+[\)\}]$")
TARGET_RE = re.compile(r"^([^\s:#][^:#]*):(?!=)")
RUN_KEY_RE = re.compile(r"^(\s*)(?:-\s+)?run:\s*(.*)$")
MAKE_CALL_RE = re.compile(r"^make\s+([A-Za-z0-9_.\-]+)")
REUSABLE_WF_RE = re.compile(r"^\s*uses:\s*(\S*\.github/workflows/\S+)", re.MULTILINE)
LOCAL_ACTION_RE = re.compile(r"^\s*uses:\s*(\./\S+)", re.MULTILINE)
MATRIX_EXPR_RE = re.compile(r"\$\{\{\s*matrix\.")


@dataclass
class Kommando:
    ziel: str
    roh: str
    normalisiert: str


def _lies(pfad: str) -> str:
    try:
        with open(pfad, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _split_subcommands(zeile: str) -> list[str]:
    """Grobe Trennung an `&&`/`;` — genuegt fuer die bekannten Rezepte/Workflows."""
    teile = re.split(r"&&|;", zeile)
    return [t.strip() for t in teile if t.strip()]


def _normalize_one(kommando: str) -> str:
    """Ein einzelnes Kommando normalisieren (siehe Modul-Docstring Punkt 2).

    Gibt "" zurueck, wenn das Kommando nach dem Saeubern nur noch Ablaufsteuerung
    ist (Shell-Builtin/Fuellwort fuehrt an) — das ist kein Werkzeugaufruf.
    """
    kommando = kommando.strip()
    while kommando[:1] in ("@", "-", "+"):
        kommando = kommando[1:].lstrip()
    tokens = kommando.split()
    # Fuehrende Inline-Env-Zuweisungen (`VAR=wert ... echt.py`) sind kein Werkzeug.
    while tokens and ENV_ASSIGN_RE.match(tokens[0]):
        tokens.pop(0)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if MAKEVAR_RE.match(tok):
            # Vorheriges Flag faellt mit weg, wenn SEIN Wert eine Variable war —
            # `--seed $(SEED)` ist kein literal vergleichbares Argument.
            if out and out[-1].startswith("-"):
                out.pop()
            i += 1
            continue
        if tok == "-m" and i + 1 < len(tokens):
            i += 1
            continue
        if tok in OUTPUT_FLAGS:
            i += 1
            continue
        if (
            i == 0
            and tok.rsplit("/", 1)[-1] in INTERPRETER_NAMES
            and i + 1 < len(tokens)
            and (tokens[i + 1].endswith(".py") or tokens[i + 1] == "-m")
        ):
            # `python3 -m pytest ...` UND `python3 x.py` faellt der Interpreter weg —
            # sonst ueberlebt "python3" das spaetere Wegfallen von "-m" und haengt
            # als sinnloses erstes Token vor dem eigentlichen Werkzeug (`python3
            # pytest tests/` statt `pytest tests/`, Realfall gpufw).
            i += 1
            continue
        out.append(tok)
        i += 1
    if not out or out[0] in SHELL_NOOP_ODER_BUILTIN:
        return ""
    return " ".join(out)


def normalize_command(zeile: str) -> list[str]:
    return [_normalize_one(c) for c in _split_subcommands(zeile)]


def is_pruef_kommando(normalisiert: str) -> bool:
    if not normalisiert:
        return False
    tokens = normalisiert.split()
    for praefix in CHECK_TOOL_PREFIXES:
        if tuple(tokens[: len(praefix)]) == praefix:
            return True
    if TEST_SCRIPT_RE.search(tokens[0]):
        return True
    return False


def _ziel_ist_pruef_kandidat(ziel: str) -> bool:
    """Zielname traegt ein Pruef-Schluesselwort als eigenes `-`/`_`-Segment."""
    segmente = re.split(r"[-_]", ziel.lower())
    return any(s in ZIEL_SCHLUESSELWOERTER for s in segmente)


def parse_makefile(text: str) -> list[Kommando]:
    """Ziele + ihre Pruef-Kommandos. Nur Rezeptzeilen mit echtem TAB zaehlen.

    Rezeptzeilen, die mit `\\` enden, werden mit der naechsten Tab-Zeile zu EINEM
    logischen Kommando verbunden (Make-Zeilenfortsetzung) — sonst zerreisst ein
    mehrzeiliges Rezept (robo-lab `exo-konformitaet-myoassist`) in Fragmente.
    """
    ergebnisse: list[Kommando] = []
    aktuelle_ziele: list[str] | None = None
    rohzeilen = text.splitlines()
    i, n = 0, len(rohzeilen)
    while i < n:
        raw = rohzeilen[i]
        if raw.startswith("\t"):
            logisch = raw[1:]
            while (
                logisch.rstrip().endswith("\\")
                and i + 1 < n
                and rohzeilen[i + 1].startswith("\t")
            ):
                logisch = logisch.rstrip()[:-1] + " " + rohzeilen[i + 1][1:]
                i += 1
            if aktuelle_ziele is not None:
                kandidat = any(_ziel_ist_pruef_kandidat(z) for z in aktuelle_ziele)
                for sub in _split_subcommands(logisch):
                    norm = _normalize_one(sub)
                    if norm and (is_pruef_kommando(norm) or kandidat):
                        for ziel in aktuelle_ziele:
                            ergebnisse.append(Kommando(ziel=ziel, roh=sub, normalisiert=norm))
            i += 1
            continue
        if not raw or raw[0].isspace() or raw.lstrip().startswith("#"):
            aktuelle_ziele = None
            i += 1
            continue
        m = TARGET_RE.match(raw)
        aktuelle_ziele = m.group(1).split() if m else None
        i += 1
    return ergebnisse


def _run_bloecke(text: str) -> list[str]:
    """Jede Zeile innerhalb eines `run:`-Schritts, inline wie Blockskalar."""
    zeilen = text.splitlines()
    ergebnis: list[str] = []
    i, n = 0, len(zeilen)
    while i < n:
        m = RUN_KEY_RE.match(zeilen[i])
        if not m:
            i += 1
            continue
        einzug, rest = m.group(1), m.group(2).strip()
        if rest in ("", "|", ">", "|-", ">-", "|+", ">+"):
            basis = len(einzug)
            j = i + 1
            while j < n:
                zeile = zeilen[j]
                if zeile.strip() == "":
                    j += 1
                    continue
                cur = len(zeile) - len(zeile.lstrip(" "))
                if cur <= basis:
                    break
                ergebnis.append(zeile.strip())
                j += 1
            i = j
        else:
            ergebnis.append(rest.strip("\"'"))
            i += 1
    return ergebnis


def parse_workflows(pfade: list[str]) -> tuple[set[str], set[str], list[str]]:
    """(normalisierte Inline-Kommandos, per `make <ziel>` aufgerufene Ziele, unresolved)."""
    normierte: set[str] = set()
    make_ziele: set[str] = set()
    unresolved: list[str] = []
    for pfad in pfade:
        text = _lies(pfad)
        if not text:
            continue
        basisname = os.path.basename(pfad)
        for treffer in REUSABLE_WF_RE.findall(text):
            unresolved.append(
                f"{basisname}: wiederverwendbarer Workflow referenziert, "
                f"Inhalt nicht aufgeloest: {treffer}"
            )
        for treffer in LOCAL_ACTION_RE.findall(text):
            unresolved.append(
                f"{basisname}: lokale Composite-Action referenziert, "
                f"Inhalt nicht aufgeloest: {treffer}"
            )
        for zeile in _run_bloecke(text):
            for sub in _split_subcommands(zeile):
                if MATRIX_EXPR_RE.search(sub):
                    unresolved.append(
                        f"{basisname}: Matrix-Expression im Kommando, "
                        f"nicht aufloesbar: {sub[:80]}"
                    )
                    continue
                m = MAKE_CALL_RE.match(sub)
                if m:
                    make_ziele.add(m.group(1))
                    continue
                norm = _normalize_one(sub)
                if norm:
                    normierte.add(norm)
    return normierte, make_ziele, unresolved


def lade_verzicht(pfad: str) -> tuple[dict[tuple[str, str], str], list[str]]:
    """`governance/ci-deckung-verzicht.yaml` OHNE PyYAML lesen (stdlib-only Pflicht).

    Schema, streng: eine Liste von Eintraegen `repo`, `ziel`, `grund`. `grund` ist
    PFLICHT — ein Eintrag ohne ihn ist ungueltig und landet in der Fehlerliste,
    nicht in den akzeptierten Eintraegen.
    """
    eintraege: dict[tuple[str, str], str] = {}
    fehler: list[str] = []
    if not os.path.exists(pfad):
        return eintraege, fehler
    aktuelles: dict[str, str] = {}

    def _uebernehmen() -> None:
        if not aktuelles:
            return
        repo, ziel, grund = (
            aktuelles.get("repo"),
            aktuelles.get("ziel"),
            aktuelles.get("grund"),
        )
        if not repo or not ziel:
            fehler.append(f"Eintrag ohne repo/ziel: {aktuelles}")
        elif not grund:
            fehler.append(f"{repo}/{ziel}: Verzicht OHNE Grund — ungueltig")
        else:
            eintraege[(repo, ziel)] = grund

    with open(pfad, encoding="utf-8") as f:
        for roh in f:
            stripped = roh.rstrip("\n").strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                _uebernehmen()
                aktuelles = {}
                stripped = stripped[2:].strip()
            m = re.match(r"^(\w+):\s*(.*)$", stripped)
            if m:
                aktuelles[m.group(1)] = m.group(2).strip().strip("\"'")
        _uebernehmen()
    return eintraege, fehler


def scan_repo(repo_pfad: str, verzicht: dict[tuple[str, str], str] | None = None) -> dict:
    verzicht = verzicht or {}
    repo_pfad = os.path.abspath(os.path.expanduser(repo_pfad))
    repo_name = os.path.basename(repo_pfad.rstrip("/"))

    kommandos: list[Kommando] = []
    nicht_pruefbar: list[dict] = []
    makefile_pfad = os.path.join(repo_pfad, "Makefile")
    hat_makefile = os.path.exists(makefile_pfad)
    if hat_makefile:
        text = _lies(makefile_pfad)
        if text.strip() and not re.search(r"(?m)^\t", text):
            nicht_pruefbar.append(
                {
                    "ziel": None,
                    "kommando": None,
                    "grund": (
                        "Makefile vorhanden, aber keine Tab-Rezeptzeile gefunden — "
                        "evtl. Leerzeichen-Rezepte oder generiert, nicht geparst"
                    ),
                }
            )
        else:
            kommandos = parse_makefile(text)

    wf_dir = os.path.join(repo_pfad, ".github", "workflows")
    wf_pfade = []
    if os.path.isdir(wf_dir):
        wf_pfade = [
            os.path.join(wf_dir, n)
            for n in sorted(os.listdir(wf_dir))
            if n.endswith((".yml", ".yaml"))
        ]
    ci_kommandos, ci_make_ziele, unresolved = parse_workflows(wf_pfade)

    gedeckt: list[dict] = []
    befunde: list[dict] = []
    verzichtet: list[dict] = []
    for k in kommandos:
        if k.ziel in ci_make_ziele or k.normalisiert in ci_kommandos:
            gedeckt.append({"ziel": k.ziel, "kommando": k.normalisiert})
            continue
        grund_verzicht = verzicht.get((repo_name, k.ziel))
        if grund_verzicht:
            verzichtet.append(
                {"ziel": k.ziel, "kommando": k.normalisiert, "grund": grund_verzicht}
            )
            continue
        if unresolved:
            nicht_pruefbar.append(
                {
                    "ziel": k.ziel,
                    "kommando": k.normalisiert,
                    "grund": "Deckung unsicher — " + "; ".join(unresolved),
                }
            )
        else:
            befunde.append(
                {
                    "ziel": k.ziel,
                    "kommando": k.normalisiert,
                    "grund": "lokal vorhanden, im CI nie ausgefuehrt",
                }
            )

    return {
        "repo": repo_name,
        "repo_pfad": repo_pfad,
        "hat_makefile": hat_makefile,
        "hat_workflows": bool(wf_pfade),
        "geprueft": len(kommandos),
        "gedeckt": gedeckt,
        "befunde": befunde,
        "nicht_pruefbar": nicht_pruefbar,
        "verzicht": verzichtet,
        "unresolved": unresolved,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=REPO_ROOT, help="Pfad zum zu messenden Repo")
    parser.add_argument("--verzicht", default=DEFAULT_VERZICHT)
    parser.add_argument("--kurz", action="store_true")
    parser.add_argument("--json", action="store_true", dest="als_json")
    args = parser.parse_args()

    verzicht, verzicht_fehler = lade_verzicht(args.verzicht)
    ergebnis = scan_repo(args.repo, verzicht)
    ergebnis["verzicht_fehler"] = verzicht_fehler

    if args.als_json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2, default=lambda o: asdict(o)))
        return 0

    befunde = ergebnis["befunde"]
    nicht_pruefbar = ergebnis["nicht_pruefbar"]

    if args.kurz:
        teile = []
        if befunde:
            spitze = befunde[0]
            weitere = f" (+{len(befunde) - 1} weitere)" if len(befunde) > 1 else ""
            teile.append(
                f"{len(befunde)} Kommando(s) lokal vorhanden, im CI nie ausgefuehrt — "
                f"{spitze['ziel']}: {spitze['kommando']}{weitere}"
            )
        if nicht_pruefbar:
            teile.append(f"{len(nicht_pruefbar)} NICHT PRUEFBAR")
        if verzicht_fehler:
            teile.append(f"{len(verzicht_fehler)} Verzicht-Eintrag(e) ungueltig")
        if not teile:
            print(f"keine offene Deckungsluecke ({ergebnis['repo']}, {ergebnis['geprueft']} Kommando(s) geprueft)")
        else:
            print(" · ".join(teile))
        return 0

    print(f"# CI-Deckung — {ergebnis['repo']}\n")
    print(f"Pfad                 : {ergebnis['repo_pfad']}")
    print(f"Makefile vorhanden   : {ergebnis['hat_makefile']}")
    print(f"Workflows vorhanden  : {ergebnis['hat_workflows']}")
    print(f"Pruef-Kommandos      : {ergebnis['geprueft']}")
    print(f"  gedeckt            : {len(ergebnis['gedeckt'])}")
    print(f"  Befund (ungedeckt) : {len(befunde)}")
    print(f"  NICHT PRUEFBAR     : {len(nicht_pruefbar)}")
    print(f"  Verzicht           : {len(ergebnis['verzicht'])}")
    print()

    if befunde:
        print("🚨 lokal vorhanden, im CI nie ausgefuehrt:\n")
        for b in befunde:
            print(f"  · {b['ziel']:<32} {b['kommando']}")
        print()
    else:
        print("→ Kein ungedecktes Pruef-Kommando.\n")

    if nicht_pruefbar:
        print("⚠️  NICHT PRUEFBAR (Falsifikation nicht moeglich):\n")
        for n in nicht_pruefbar:
            ziel = n["ziel"] or "(Repo-weit)"
            print(f"  · {ziel}: {n['grund']}")
        print()

    if ergebnis["verzicht"]:
        print("✓ Bewusster Verzicht (governance/ci-deckung-verzicht.yaml):\n")
        for v in ergebnis["verzicht"]:
            print(f"  · {v['ziel']}: {v['grund']}")
        print()

    if verzicht_fehler:
        print("🚨 Ungueltige Verzicht-Eintraege (ohne Grund — nicht wirksam):\n")
        for f in verzicht_fehler:
            print(f"  · {f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
