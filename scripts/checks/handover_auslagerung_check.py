#!/usr/bin/env python3
"""handover_auslagerung_check.py — Auslagern darf keine offenen Punkte verschlucken.

## Anlass (platform#2974, 2026-09-08)

`AGENT_HANDOVER.md` traegt einen Byte-Deckel; wird er eng, wandert der aelteste
Stand-Block ins Archiv. Die Konvention der Datei sagt dazu ausdruecklich: „Offenes
vorher als Kurzzeile nach `## Offene Faeden` retten."

Am 2026-09-08 geschah das bei einer Auslagerung nicht. **Sechs offene Punkte** —
darunter eine Frist zum 30.11. — standen nur im ausgelagerten Text und waren danach
im Handover nirgends mehr auffindbar. Niemand hat es gemerkt, weil **nichts es prueft**:
Byte-Deckel, Append-only und Frische sahen alle gruen.

## Was geprueft wird

Vergleich der Datei gegen die Basis (Default `origin/main`):

    verschwunden = {Referenzen vorher} - {Referenzen nachher}

Von den verschwundenen Referenzen zaehlt nur, was **offen** ist. Eine geschlossene
Nummer darf mit dem Block gehen — genau dafuer gibt es das Archiv.

Bewusst der ganze Text, nicht nur die offenen Abschnitte: die verlorenen Punkte
standen mitten in einem Stand-Block. Geparst wird mit `handover_refs.alle_refs`,
also demselben Parser wie ueberall — ein zweiter waere die Doppelung, vor der dessen
Modulkopf warnt (und die dort schon einmal vier falsche Owner erzeugt hat).

## Warum eine Referenz und kein Textvergleich

Ein Textvergleich wuerde bei jeder Umformulierung anschlagen. Die Frage ist nicht
„steht derselbe Satz noch da", sondern „ist der Vorgang noch auffindbar" — und
auffindbar ist er ueber seine Nummer.

## Test-Naht

`--zustand-datei` ersetzt die GitHub-Abfrage durch eine JSON-Abbildung
`{"owner/repo#N": "OPEN"}`. Der Golden-Test im Workflow benutzt sie, damit er ohne
Netz deterministisch fehlschlaegt; der echte Lauf im selben Job geht ueber `gh` und
deckt den Pfad ab, den die Naht umgeht.

Exit-Codes
----------
0 = nichts Offenes verloren · 1 = mindestens eine offene Referenz verschwunden
2 = Zustand nicht ermittelbar (blind ist nicht gruen)

Usage
-----
    python3 scripts/checks/handover_auslagerung_check.py
    python3 scripts/checks/handover_auslagerung_check.py --basis origin/main --datei AGENT_HANDOVER.md
    python3 scripts/checks/handover_auslagerung_check.py --zustand-datei /tmp/zustand.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from handover_refs import alle_refs  # noqa: E402

DEFAULT_OWNER = "achimdehnert"
DEFAULT_REPO = "platform"


def schluessel(ref) -> str:
    return f"{ref.owner}/{ref.repo}#{ref.number}"


def verschwundene(alt_text: str, neu_text: str) -> list[str]:
    """Referenzen, die vorher im Text standen und jetzt nirgends mehr."""
    vorher = {schluessel(r) for r in alle_refs(alt_text, DEFAULT_OWNER, DEFAULT_REPO)}
    nachher = {schluessel(r) for r in alle_refs(neu_text, DEFAULT_OWNER, DEFAULT_REPO)}
    return sorted(vorher - nachher)


def zustand_via_gh(schluessel_liste: list[str]) -> tuple[dict[str, str], list[str]]:
    """Zustand je Referenz. Zweiter Wert: was nicht ermittelbar war."""
    zustand: dict[str, str] = {}
    blind: list[str] = []
    for s in schluessel_liste:
        repo, _, nummer = s.partition("#")
        p = subprocess.run(
            [
                "gh",
                "issue",
                "view",
                nummer,
                "--repo",
                repo,
                "--json",
                "state",
                "-q",
                ".state",
            ],
            capture_output=True,
            text=True,
        )
        wert = p.stdout.strip()
        if p.returncode != 0 or not wert:
            # Eine PR-Nummer ist kein Issue — `gh pr view` entscheidet, ob es sie gibt.
            q = subprocess.run(
                [
                    "gh",
                    "pr",
                    "view",
                    nummer,
                    "--repo",
                    repo,
                    "--json",
                    "state",
                    "-q",
                    ".state",
                ],
                capture_output=True,
                text=True,
            )
            wert = q.stdout.strip()
            if q.returncode != 0 or not wert:
                blind.append(s)
                continue
        zustand[s] = wert
    return zustand, blind


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--datei", default="AGENT_HANDOVER.md")
    p.add_argument("--basis", default="origin/main")
    p.add_argument(
        "--zustand-datei",
        default=None,
        help="JSON {'owner/repo#N': 'OPEN'} statt GitHub-Abfrage (Test-Naht)",
    )
    a = p.parse_args(argv)

    neu = pathlib.Path(a.datei).read_text(encoding="utf-8")
    zeige = subprocess.run(
        ["git", "show", f"{a.basis}:{a.datei}"], capture_output=True, text=True
    )
    if zeige.returncode != 0:
        print(
            f"⛔ {a.basis}:{a.datei} nicht lesbar — blind ist nicht gruen",
            file=sys.stderr,
        )
        return 2
    weg = verschwundene(zeige.stdout, neu)
    if not weg:
        print(f"✅ {a.datei}: keine Referenz aus dem Blick geraten")
        return 0

    if a.zustand_datei:
        zustand = json.loads(pathlib.Path(a.zustand_datei).read_text(encoding="utf-8"))
        blind = [s for s in weg if s not in zustand]
    else:
        zustand, blind = zustand_via_gh(weg)

    offen = [s for s in weg if zustand.get(s) == "OPEN"]
    if blind:
        print(f"⛔ Zustand nicht ermittelbar: {', '.join(blind)}", file=sys.stderr)
        return 2
    if not offen:
        print(
            f"✅ {a.datei}: {len(weg)} Referenz(en) entfernt, alle geschlossen — "
            "das ist der gewollte Fall"
        )
        return 0

    print(f"⛔ Auslagerung verschluckt {len(offen)} OFFENE(N) Vorgang/Vorgaenge:")
    for s in offen:
        print(f"  {s}")
    print()
    print(
        "Die Konvention der Datei verlangt: Offenes vor dem Auslagern als Kurzzeile "
        "nach '## Offene Faeden' retten. Eine Zeile je Nummer, mit Link — dann ist "
        "der Vorgang weiter auffindbar und dieser Check gruen."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
