#!/usr/bin/env python3
"""Gate-Registry aus Einzeldateien laden (#1944 K7).

Bis 2026-09-16 war die Registry EINE Datei `docs/governance/gate-registry.json`,
von jeder Sitzung mitgeschrieben, die ein Gate baut oder revidiert — mit 20
Kollisionspaaren in 14 Tagen die meistgeteilte Datei des Repos
(`session_collision_meter.py`). Jetzt liegt jeder Eintrag in einer eigenen Datei:

    docs/governance/gates/_meta.json            Doku-Schluessel (_doc, _faengt_doc, ...)
    docs/governance/gates/<abschnitt>/<slug>.json   ein Eintrag je Datei

mit `<abschnitt>` aus `gates`, `declined`, `widerrufen`, `kandidaten`. Zwei
Sitzungen kollidieren nur noch, wenn sie denselben Eintrag aendern.

`laden()` setzt daraus dasselbe Dict zusammen, das die alte Datei lieferte;
Leser aendern nur ihren Ladeaufruf. Eine einzelne JSON-Datei (Test-Fixture,
Altstand auf einem Git-Ref) wird unveraendert gelesen.

Aufruf:  gate_registry.py [--ref REF] [PFAD]   → zusammengesetztes JSON auf stdout
         gate_registry.py --aufteilen DATEI [--ziel VERZ]   → Altdatei in Einzeldateien
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATES_REL = os.path.join("docs", "governance", "gates")
LEGACY_REL = os.path.join("docs", "governance", "gate-registry.json")
DEFAULT_PFAD = os.path.join(REPO_ROOT, GATES_REL)
ABSCHNITTE = ("gates", "declined", "widerrufen", "kandidaten")
META = "_meta.json"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _zusammensetzen(meta: dict, eintraege: dict[str, list[dict]]) -> dict:
    daten = dict(meta)
    for abschnitt in ABSCHNITTE:
        daten[abschnitt] = sorted(
            eintraege.get(abschnitt, []), key=lambda e: e.get("slug", "")
        )
    return daten


def _aus_verzeichnis(pfad: str) -> dict:
    meta_pfad = os.path.join(pfad, META)
    meta = {}
    if os.path.isfile(meta_pfad):
        with open(meta_pfad, encoding="utf-8") as fh:
            meta = json.load(fh)
    eintraege: dict[str, list[dict]] = {}
    for abschnitt in ABSCHNITTE:
        ordner = os.path.join(pfad, abschnitt)
        if not os.path.isdir(ordner):
            continue
        for name in sorted(os.listdir(ordner)):
            if name.endswith(".json"):
                with open(os.path.join(ordner, name), encoding="utf-8") as fh:
                    eintraege.setdefault(abschnitt, []).append(json.load(fh))
    return _zusammensetzen(meta, eintraege)


def _git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=repo, timeout=60
    )


def _aus_ref(ref: str, repo: str) -> dict:
    """Registry auf einem Git-Ref — Einzeldateien, sonst die Altdatei.

    Der Rueckfall auf die Altdatei traegt den Uebergang: eine Basis vor der
    Aufteilung kennt nur `gate-registry.json`.
    """
    gates_git = GATES_REL.replace(os.sep, "/")
    liste = _git(repo, "ls-tree", "-r", "--name-only", ref, "--", gates_git)
    if liste.returncode != 0:
        raise RuntimeError(
            f"`git ls-tree {ref}` fehlgeschlagen: {liste.stderr.strip()}"
        )
    dateien = [z for z in liste.stdout.splitlines() if z.endswith(".json")]
    if not dateien:
        alt = _git(repo, "show", f"{ref}:{LEGACY_REL.replace(os.sep, '/')}")
        if alt.returncode != 0:
            raise RuntimeError(f"keine Registry auf {ref}: {alt.stderr.strip()}")
        return json.loads(alt.stdout)
    meta: dict = {}
    eintraege: dict[str, list[dict]] = {}
    for datei in dateien:
        inhalt = _git(repo, "show", f"{ref}:{datei}")
        if inhalt.returncode != 0:
            raise RuntimeError(
                f"`git show {ref}:{datei}` fehlgeschlagen: {inhalt.stderr.strip()}"
            )
        teile = datei[len(gates_git) + 1 :].split("/")
        if teile == [META]:
            meta = json.loads(inhalt.stdout)
        elif len(teile) == 2 and teile[0] in ABSCHNITTE:
            eintraege.setdefault(teile[0], []).append(json.loads(inhalt.stdout))
    return _zusammensetzen(meta, eintraege)


def laden(
    pfad: Optional[str] = None, ref: Optional[str] = None, repo: str = REPO_ROOT
) -> dict:
    """Registry als Dict im Format der frueheren `gate-registry.json`.

    ``pfad``: Verzeichnis (Einzeldateien) oder eine einzelne JSON-Datei.
    Zeigt er auf die fruehere Sammeldatei, die es nicht mehr gibt, wird das
    Verzeichnis daneben gelesen — alte Aufrufe mit `--registry` laufen weiter.
    ``ref``: statt des Arbeitsbaums einen Git-Ref lesen.

    Wirft OSError/ValueError/RuntimeError, wenn nichts lesbar ist; ein Leser,
    der daraus „keine Gates" macht, waere ein blinder Melder.
    """
    if ref is not None:
        return _aus_ref(ref, repo)
    pfad = pfad or DEFAULT_PFAD
    if os.path.isfile(pfad):
        with open(pfad, encoding="utf-8") as fh:
            return json.load(fh)
    if not os.path.isdir(pfad) and os.path.basename(pfad) == os.path.basename(
        LEGACY_REL
    ):
        pfad = os.path.join(os.path.dirname(pfad), "gates")
    if not os.path.isdir(pfad):
        raise FileNotFoundError(f"keine Gate-Registry unter {pfad}")
    return _aus_verzeichnis(pfad)


def eintrag_pfad(abschnitt: str, slug: str, wurzel: str = DEFAULT_PFAD) -> str:
    if abschnitt not in ABSCHNITTE:
        raise ValueError(f"unbekannter Abschnitt: {abschnitt}")
    if not SLUG_RE.match(slug):
        raise ValueError(f"Slug nicht dateitauglich: {slug!r}")
    return os.path.join(wurzel, abschnitt, f"{slug}.json")


def _schreiben(pfad: str, daten: dict) -> None:
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(daten, indent=2, ensure_ascii=False) + "\n")


def aufteilen(daten: dict, ziel: str) -> int:
    """Sammel-Dict in Einzeldateien schreiben; liefert die Zahl der Eintraege."""
    meta = {k: v for k, v in daten.items() if k not in ABSCHNITTE}
    _schreiben(os.path.join(ziel, META), meta)
    n = 0
    for abschnitt in ABSCHNITTE:
        gesehen = set()
        for eintrag in daten.get(abschnitt, []):
            slug = eintrag.get("slug", "")
            if slug in gesehen:
                raise ValueError(f"Slug doppelt in {abschnitt}: {slug}")
            gesehen.add(slug)
            _schreiben(eintrag_pfad(abschnitt, slug, ziel), eintrag)
            n += 1
    return n


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pfad", nargs="?", default=None)
    ap.add_argument("--ref")
    ap.add_argument("--aufteilen", metavar="DATEI")
    ap.add_argument("--ziel", default=DEFAULT_PFAD)
    args = ap.parse_args(argv)
    if args.aufteilen:
        with open(args.aufteilen, encoding="utf-8") as fh:
            n = aufteilen(json.load(fh), args.ziel)
        print(f"{n} Eintraege nach {args.ziel}")
        return 0
    json.dump(laden(args.pfad, args.ref), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
