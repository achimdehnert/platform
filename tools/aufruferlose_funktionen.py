#!/usr/bin/env python3
"""Findet Funktionen, deren einzige Aufrufer Tests sind.

Ausweitung des Gates ``built-but-never-called`` (Retro 61c35d §5a, 2026-09-08).

Das Gate wurde am 2026-08-29 fuer eine eng gefasste Familie gebaut: ein
String-Schluessel, den ein Adapter in ``RawAusschreibung.raw_data`` schreibt und
den niemand liest. Sein eigener Registry-Eintrag benennt seither die Restluecke —
„der zweite Teil der Klasse bleibt ungegated".

Der Rueckfall am 2026-09-08 war genau dieser zweite Teil in neuer Gestalt:
``tools/melder_ergebnis.py`` bekam ein Paar ``schreibe()``/``lies()``. Vier
Produzenten riefen ``schreibe()``, ``lies()`` rief niemand ausser zwei Tests.
Eine Lesefunktion ohne Leser ist gebauter, gruener, gedrillter und wirkungsloser
Code — dieselbe Klasse wie ein Schluessel ohne Leser.

**Warum Verwendungen und nicht Importe gezaehlt werden:** ein Import belegt nur,
dass ein Modul bekannt ist. Der Realfall stand in der Testdatei genauso importiert
wie in einer Produktivdatei — was fehlte, war die Verwendung.

**Warum Verwendung und nicht nur Aufruf:** eine Funktion, die als WERT weiter-
gereicht wird — ``("Drill", pruefe_drill)`` in einer Pruefliste, ``set_defaults(
func=cmd_age)`` an einem Unterbefehl — ist verdrahtet, ohne je namentlich gerufen
zu werden. Die erste Fassung meldete vier solcher Faelle; sie waren richtig
gebaut, die Probe war falsch.

**Bewusste Verengungen**, damit die Probe eine Schranke sein kann und kein
Rauschmelder:

* nur oeffentliche Funktionen auf Modulebene (kein ``_``-Praefix, kein ``main``),
* keine dekorierten Funktionen — ``@app.command``, ``@task``, ``@property`` und
  Verwandte werden vom Rahmenwerk gerufen, nicht vom Quelltext,
* Aufrufe werden ueber den Syntaxbaum gezaehlt, punktiert (``modul.f()``) wie
  unpunktiert (``f()``). Ein Regex-Zaehler ohne Punkt uebersieht genau den
  Realfall.
* Aufrufe werden dem MODUL zugeordnet, nicht nur dem Namen. Ohne das faengt die
  Probe ihren eigenen Anlass nicht: ``lies`` heisst in ``gate_hits.py`` und in
  ``rotation/log.py`` dasselbe, beide werden produktiv gerufen — und entlasteten
  in der ersten Fassung ``melder_ergebnis.lies`` gleich mit.
* Ein Aufruf, dessen Modul sich nicht aufloesen laesst (tiefe Kette, dynamisch),
  entlastet vorsichtshalber jeden gleichnamigen Kandidaten. Die Probe soll lieber
  einen Befund verlieren als einen erfinden.

Ausnahmen stehen in ``tools/aufruferlose_funktionen_ausnahmen.tsv`` und brauchen
jeweils einen Grund mit Anker — „bewusst so" ohne Anker ist keine Ausnahme.

Exit 0 = keine ungedeckten Befunde, Exit 1 = Befunde.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
AUSNAHMEN = WURZEL / "aufruferlose_funktionen_ausnahmen.tsv"

#: Dekoratoren machen eine Funktion vom Rahmenwerk aufrufbar — der Quelltext
#: nennt sie dann nirgends, und das ist richtig so.
_RAHMEN_DEKORATOR_TEILE = (
    "command",
    "route",
    "task",
    "fixture",
    "property",
    "setter",
    "hookimpl",
    "register",
    "handler",
    "cli",
    "app",
    "click",
    "typer",
    "celery",
    "cached",
    "lru_cache",
    "overload",
    "singledispatch",
)


def ist_testdatei(pfad: Path) -> bool:
    return "tests" in pfad.parts or pfad.name.startswith("test_")


def _dekorator_namen(node: ast.AST) -> list[str]:
    namen: list[str] = []
    for d in getattr(node, "decorator_list", []):
        ziel = d.func if isinstance(d, ast.Call) else d
        while isinstance(ziel, ast.Attribute):
            namen.append(ziel.attr)
            ziel = ziel.value
        if isinstance(ziel, ast.Name):
            namen.append(ziel.id)
    return namen


def vom_rahmen_gerufen(node: ast.AST) -> bool:
    namen = [n.lower() for n in _dekorator_namen(node)]
    return any(teil in n for n in namen for teil in _RAHMEN_DEKORATOR_TEILE)


def _modul_alias(baum: ast.AST) -> dict[str, str]:
    """alias -> Modul-Basisname, aus den Importen dieser Datei."""
    karte: dict[str, str] = {}
    for k in ast.walk(baum):
        if isinstance(k, ast.Import):
            for a in k.names:
                basis = a.name.rsplit(".", 1)[-1]
                karte[a.asname or basis] = basis
        elif isinstance(k, ast.ImportFrom):
            for a in k.names:
                # `from x import f` bindet f an das Modul x
                karte.setdefault(
                    a.asname or a.name, (k.module or "").rsplit(".", 1)[-1]
                )
    return karte


def verwendete_namen(baum: ast.AST, eigenes_modul: str) -> set[tuple[str | None, str]]:
    """Alle Verwendungen dieser Datei als (Modul, Name).

    Erfasst wird jede lesende Nennung — der Aufruf ``f()`` genauso wie die
    Weitergabe als Wert (``func=f``, ``("Drill", f)``). ``Modul is None`` heisst
    „nicht aufloesbar" und entlastet spaeter jeden gleichnamigen Kandidaten,
    bewusst vorsichtig.
    """
    alias = _modul_alias(baum)
    importiert = {
        a.asname or a.name
        for k in ast.walk(baum)
        if isinstance(k, ast.ImportFrom)
        for a in k.names
    }
    ziele: set[tuple[str | None, str]] = set()
    for k in ast.walk(baum):
        if isinstance(k, ast.Name):
            if not isinstance(k.ctx, ast.Load):
                continue
            modul = alias.get(k.id) if k.id in importiert else eigenes_modul
            ziele.add((modul or None, k.id))
        elif isinstance(k, ast.Attribute):
            if not isinstance(k.ctx, ast.Load):
                continue
            traeger = k.value
            if isinstance(traeger, ast.Name):
                ziele.add((alias.get(traeger.id, traeger.id), k.attr))
            elif isinstance(traeger, ast.Attribute):
                # `paket.modul.f` — das letzte Glied vor dem Namen ist das Modul
                ziele.add((traeger.attr, k.attr))
            else:
                ziele.add((None, k.attr))
    return ziele


def lade_ausnahmen() -> dict[str, str]:
    if not AUSNAHMEN.exists():
        return {}
    raus: dict[str, str] = {}
    for zeile in AUSNAHMEN.read_text(encoding="utf-8").splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        teile = zeile.split("\t")
        if len(teile) >= 2 and teile[1].strip():
            raus[teile[0].strip()] = teile[1].strip()
    return raus


def scanne(wurzel: Path) -> list[tuple[str, str]]:
    """Liefert (schluessel, hinweis) je Funktion ohne Produktivaufrufer."""
    dateien = sorted(wurzel.rglob("*.py"))
    baeume: dict[Path, ast.AST] = {}
    for p in dateien:
        try:
            baeume[p] = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, ValueError):
            continue

    prod_ziele: set[tuple[str | None, str]] = set()
    test_ziele: set[tuple[str | None, str]] = set()
    for p, baum in baeume.items():
        ziel = test_ziele if ist_testdatei(p) else prod_ziele
        ziel.update(verwendete_namen(baum, p.stem))

    prod_unaufloesbar = {n for m, n in prod_ziele if m is None}

    befunde: list[tuple[str, str]] = []
    for p, baum in baeume.items():
        if ist_testdatei(p):
            continue
        modul = p.stem
        for node in baum.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = node.name
            if name.startswith("_") or name == "main":
                continue
            if vom_rahmen_gerufen(node):
                continue
            if (modul, name) in prod_ziele or name in prod_unaufloesbar:
                continue
            gerufen_im_test = (modul, name) in test_ziele or any(
                m is None and n == name for m, n in test_ziele
            )
            if not gerufen_im_test:
                continue
            rel = p.relative_to(wurzel.parent) if wurzel.parent in p.parents else p
            befunde.append(
                (
                    f"{rel}::{name}",
                    f"{rel}:{node.lineno} — {name}() wird nirgends im Produktivpfad "
                    "verwendet, nur Tests nennen es",
                )
            )
    return befunde


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--wurzel", default=str(WURZEL), help="Verzeichnis (Vorgabe: tools/)"
    )
    args = ap.parse_args(argv)

    ausnahmen = lade_ausnahmen()
    befunde = scanne(Path(args.wurzel).resolve())
    offen = [(s, h) for s, h in befunde if s not in ausnahmen]
    gedeckt = [(s, h) for s, h in befunde if s in ausnahmen]

    print(
        f"## Aufruferlose Funktionen — {len(befunde)} gefunden, {len(offen)} ungedeckt"
    )
    for s, h in gedeckt:
        print(f"  · {s} — Ausnahme: {ausnahmen[s]}")
    for s, h in offen:
        print(f"  ✗ {h}")
    if not offen:
        print("\n→ keine ungedeckte Funktion ohne Produktivverwendung.")
        return 0
    print(
        "\n→ Entweder verdrahten (echte Verwendung im Produktivpfad) oder mit Grund "
        f'und Anker in {AUSNAHMEN.name} eintragen. „Kommt spaeter" ohne Anker zaehlt nicht.'
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
