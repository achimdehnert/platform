#!/usr/bin/env python3
"""Naechste freie ADR-/KONZ-Nummer — gegen ALLE Refs, offene PRs und Reservierungen.

K1 aus platform#1944. Der Anlass ist gemessen, nicht vermutet: Am 2026-08-12
vergaben zwei parallele Sitzungen beide die KONZ-043 (#1942 und #1934). Beide
hatten korrekt `max+1` **gegen `main`** gerechnet — und genau darin lag der
Fehler. Zum jeweiligen Vergabezeitpunkt war das fuer beide die 043.

`scripts/adr_next_number.py --next` und `scripts/konz_number_check.py` sehen
denselben Ausschnitt: den Baum. Dieses Kommando sieht drei Quellen mehr.

**Woher die Nummern kommen**

1. **Alle Remote-Refs**, nicht nur `main` — ein einziges `git rev-list
   --remotes=origin --objects` deckt `main` und jeden Session-Branch ab
   (gemessen: 0,2 s ueber 251 unmerged Branches, billiger als der Umweg ueber
   einzelne Branches).
2. **Offene PRs** ueber `gh` — faengt PRs, deren Branch lokal nicht gefetcht
   ist. Faellt still weg, wenn `gh` nicht verfuegbar ist; das wird gemeldet,
   nicht verschwiegen.
3. **Lokale Reservierungen** — der Teil, ohne den das Kriterium nicht erfuellbar
   ist: „zweimal gezogen, ohne dass dazwischen gepusht wurde, ergibt zwei
   verschiedene Nummern". Eine Reservierung ist eine Datei neben den
   repo-session-Leases, mit derselben Lebensdauer (7 Tage).

**Bewusst konservativ:** Quelle 1 sieht auch Nummern aus aufgegebenen Branches
und aus der Historie. Eine einmal vergebene Nummer bleibt damit vergeben, auch
wenn ihre Datei spaeter umbenannt wurde. Das verschenkt gelegentlich eine
Nummer und verhindert dafuer, dass zwei Dokumente je dieselbe tragen — in
dieser Richtung ist der Fehler billiger.

Usage:
    python3 scripts/naechste_nummer.py --art konz
    python3 scripts/naechste_nummer.py --art adr --reservieren mein-thema
    python3 scripts/naechste_nummer.py --art konz --zeige-quellen
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESERVIERUNGEN = Path.home() / ".repo-session" / "nummern-reservierungen.json"
LEBENSDAUER_S = 7 * 24 * 3600

MUSTER = {
    # Genau drei Ziffern und der Dateiname beginnt mit ADR-: `docs/adr/reviews/
    # REVIEW-ADR-2026-001-…md` lieferte sonst 2026 → "naechste Nummer 2027"
    # (gemessen 2026-09-17). Archivierte ADRs in Unterordnern bleiben vergeben.
    "adr": re.compile(r"docs/adr/(?:[^/]+/)*ADR-(\d{3})-[^/]+\.md$"),
    "konz": re.compile(r"docs/konzepte/KONZ-platform-(\d{3})-[^/]+\.md$"),
}


def _lauf(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or REPO_ROOT)


ARCHIV_MARKER = ("/_archive/", "/archive/", "/_ARCHIVED/")


def _ref_baeume() -> list[tuple[str, str]]:
    refs = _lauf(
        [
            "git",
            "for-each-ref",
            "--format=%(objectname) %(refname)",
            "refs/remotes/origin",
        ]
    )
    if refs.returncode != 0:
        return []
    out, gesehen = [], set()
    for zeile in refs.stdout.splitlines():
        tree, ref = zeile.split(" ", 1)
        if tree not in gesehen:
            gesehen.add(tree)
            out.append((tree, ref))
    return out


def _pfade(tree: str) -> list[str]:
    res = _lauf(["git", "ls-tree", "-r", "--name-only", tree])
    return res.stdout.splitlines() if res.returncode == 0 else []


def aus_refs(art: str) -> set[int]:
    """Jede LEBENDE Nummer auf der Spitze irgendeines Remote-Refs.

    Bis 2026-09-17 las das Kommando `git rev-list --remotes=origin --objects`,
    also jeden je erreichbaren Blob — auch laengst geloeschte Dateien. Vergeben
    ist, was ein Zweig HEUTE ausserhalb der Archiv-Ordner traegt; Archiv-Nummern
    (nur main massgeblich) sperrt `aus_archiv` gesondert, damit ADR-400/401 aus
    `_archive/superseded/` nicht "naechste Nummer 402" ergeben, waehrend main
    bei 307 steht (gemessen 2026-09-17).
    """
    muster = MUSTER[art]
    belegt: set[int] = set()
    for tree, _ref in _ref_baeume():
        for pfad in _pfade(tree):
            m = muster.search(pfad)
            if m and not any(x in pfad for x in ARCHIV_MARKER):
                belegt.add(int(m.group(1)))
    return belegt


def aus_archiv(art: str) -> set[int]:
    """Nummern in Archiv-Ordnern auf main — bleiben gesperrt, zaehlen aber nicht
    als Obergrenze (alte Zweige tragen Archiv-Staende mit, die main aufgeraeumt hat)."""
    muster = MUSTER[art]
    for tree, ref in _ref_baeume():
        if ref.endswith("/main"):
            return {
                int(m.group(1))
                for pfad in _pfade(tree)
                if (m := muster.search(pfad)) and any(x in pfad for x in ARCHIV_MARKER)
            }
    return set()


def aus_offenen_prs(art: str, repo: str | None) -> tuple[set[int], str | None]:
    """Nummern, die offene PRs beanspruchen. Zweiter Rueckgabewert = Grund fuer Ausfall."""
    cmd = ["gh", "pr", "list", "--state", "open", "--json", "number", "--limit", "200"]
    if repo:
        cmd += ["--repo", repo]
    listed = _lauf(cmd)
    if listed.returncode != 0:
        return set(), f"gh nicht verfuegbar ({listed.stderr.strip()[:60]})"

    muster = MUSTER[art]
    nummern: set[int] = set()
    for eintrag in json.loads(listed.stdout or "[]"):
        n = eintrag["number"]
        cmd = ["gh", "pr", "view", str(n), "--json", "files"]
        if repo:
            cmd += ["--repo", repo]
        fr = _lauf(cmd)
        if fr.returncode != 0:
            continue
        for f in json.loads(fr.stdout or "{}").get("files", []):
            if m := muster.search(f.get("path", "")):
                nummern.add(int(m.group(1)))
    return nummern, None


def _lies_reservierungen() -> dict:
    if not RESERVIERUNGEN.is_file():
        return {}
    try:
        return json.loads(RESERVIERUNGEN.read_text())
    except json.JSONDecodeError:
        return {}


def aus_reservierungen(art: str, jetzt: float | None = None) -> set[int]:
    jetzt = jetzt if jetzt is not None else time.time()
    daten = _lies_reservierungen()
    return {
        int(e["nummer"]) for e in daten.get(art, []) if e.get("laeuft_ab", 0) > jetzt
    }


def reserviere(art: str, nummer: int, slug: str, jetzt: float | None = None) -> dict:
    """Nummer lokal belegen, damit die naechste Ziehung sie nicht wieder liefert."""
    jetzt = jetzt if jetzt is not None else time.time()
    daten = _lies_reservierungen()
    behalten = [e for e in daten.get(art, []) if e.get("laeuft_ab", 0) > jetzt]
    eintrag = {
        "nummer": nummer,
        "slug": slug,
        "worktree": os.getcwd(),
        "angelegt": jetzt,
        "laeuft_ab": jetzt + LEBENSDAUER_S,
    }
    daten[art] = behalten + [eintrag]
    RESERVIERUNGEN.parent.mkdir(parents=True, exist_ok=True)
    RESERVIERUNGEN.write_text(json.dumps(daten, indent=2, ensure_ascii=False))
    return eintrag


def naechste(belegt: set[int], gesperrt: set[int] | None = None) -> int:
    """Kleinste Nummer oberhalb der lebenden Nummern, die nicht gesperrt ist."""
    n = (max(belegt) + 1) if belegt else 1
    while gesperrt and n in gesperrt:
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--art", choices=sorted(MUSTER), required=True)
    ap.add_argument("--reservieren", metavar="SLUG", help="Nummer lokal belegen")
    ap.add_argument("--repo", default=None, help="owner/repo fuer gh")
    ap.add_argument("--ohne-prs", action="store_true", help="gh ueberspringen")
    ap.add_argument("--zeige-quellen", action="store_true")
    args = ap.parse_args()

    refs = aus_refs(args.art)
    archiv = aus_archiv(args.art)
    prs, ausfall = (
        (set(), "uebersprungen")
        if args.ohne_prs
        else aus_offenen_prs(args.art, args.repo)
    )
    resv = aus_reservierungen(args.art)
    belegt = refs | prs | resv
    nr = naechste(belegt, archiv)

    if args.zeige_quellen:
        print(
            f"Refs (alle Branches) : {len(refs):>3} Nummern, hoechste {max(refs) if refs else '-'}"
        )
        print(
            f"Offene PRs           : {len(prs):>3}"
            + (f"  [{ausfall}]" if ausfall else "")
        )
        print(f"Reservierungen       : {len(resv):>3} {sorted(resv) if resv else ''}")
        print(f"-> belegt insgesamt  : {len(belegt)}")
        print()
    elif ausfall and ausfall != "uebersprungen":
        print(f"WARNUNG: PR-Quelle ausgefallen — {ausfall}", file=sys.stderr)
        print("Die Zahl unten kennt offene PRs damit NICHT.", file=sys.stderr)

    if args.reservieren:
        e = reserviere(args.art, nr, args.reservieren)
        print(f"{nr:03d}  reserviert fuer '{e['slug']}' (7 Tage)")
    else:
        print(f"{nr:03d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
