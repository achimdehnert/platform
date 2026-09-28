#!/usr/bin/env python3
"""gh-Abrufe je Aufrufer und je Befehl zaehlen (dev-hub#404).

Liest das Protokoll des Mitschreibers ``tools/gh_abrufe/gh`` und zeigt, wer in
den letzten N Stunden wie oft ``gh`` aufgerufen hat. Ein ``gh``-Aufruf ist nicht
immer genau ein API-Abruf (``gh pr list`` blaettert, ``gh pr view`` ist GraphQL),
die Zahl ist also eine Rangfolge der Verbraucher, keine Kontingent-Abrechnung.

    python3 tools/gh_abrufe/auswertung.py --stunden 24
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
from collections import Counter
from pathlib import Path

STANDARD_LOG = Path(
    os.environ.get("GH_ABRUF_LOG", Path.home() / ".local/state/gh-abrufe/abrufe.tsv")
)
SPALTEN = ("zeit", "aufrufer", "cwd", "befehl", "ziel", "repo")


def lese(log: Path, seit: dt.datetime) -> list[dict[str, str]]:
    """Zeilen ab ``seit``; kaputte Zeilen werden uebersprungen, nicht geraten."""
    zeilen = []
    if not log.is_file():
        return zeilen
    for roh in log.read_text(encoding="utf-8", errors="replace").splitlines():
        teile = roh.split("\t")
        if len(teile) != len(SPALTEN):
            continue
        z = dict(zip(SPALTEN, teile))
        try:
            zeit = dt.datetime.fromisoformat(z["zeit"].replace("Z", "+00:00"))
        except ValueError:
            continue
        if zeit >= seit:
            zeilen.append(z)
    return zeilen


def rangliste(zeilen: list[dict[str, str]], schluessel: str, n: int) -> list[tuple[str, int]]:
    return Counter(z[schluessel].strip() or "?" for z in zeilen).most_common(n)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--stunden", type=float, default=24)
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--log", type=Path, default=STANDARD_LOG)
    a = p.parse_args(argv)

    seit = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=a.stunden)
    zeilen = lese(a.log, seit)
    print(f"{len(zeilen)} gh-Aufrufe in {a.stunden:g} h ({a.log})")
    for titel, schluessel in (("Aufrufer", "aufrufer"), ("Befehl", "befehl"), ("Repo", "repo")):
        print(f"\n{titel}:")
        for wert, anzahl in rangliste(zeilen, schluessel, a.top):
            print(f"  {anzahl:6d}  {wert}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
