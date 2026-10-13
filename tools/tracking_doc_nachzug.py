#!/usr/bin/env python3
"""tracking_doc_nachzug.py — ADR/KONZ erwähnt, aber nicht nachgezogen.

Gate `tracking-doc-stale-after-new-occurrence` (×18 über Retros, Mandat Retro
e50644 M6). Die häufigste Familie in platform: ein Commit beruft sich auf ein
ADR oder Konzept, ändert es aber nicht, und das Dokument führt weiter offene
Posten. Belegte Realfälle:

- e50644: #3931 nennt „Fund aus KONZ-071", KONZ-071 §13 führt das Kill-Gate
  weiter als „offen".
- eb9de7: #3721 liefert die Profil-Negativtests für ADR-308, das ADR nennt sie
  weiter „noch offen".

Geprüft wird je Commit im Bereich (älteste zuerst): jede ADR-/KONZ-Nummer in
der Commit-Nachricht. Ändert derselbe oder ein späterer Commit im Bereich die
Datei, ist sie nachgezogen. Sonst wird sie am Kopf-Stand auf offene Posten
gelesen (Tabellenzelle `offen`/`noch offen`/`steht aus`/`ausstehend`,
Checkbox `- [ ]`, Fließtext „noch offen"). Nur mit offenen Posten ist es ein
Befund — ein erwähntes Dokument ohne offenen Posten hat nichts nachzuziehen.

Grenzen, bewusst: Issue-Bodies (zweite Familie) prüft `session_abgleich.py`
unter eigenen Slugs. Ein Vorkommen in einem anderen Repo, das keinen platform-
Commit erzeugt, sieht dieses Werkzeug nicht.

Aufruf:
    tracking_doc_nachzug.py --seit 2026-10-13          # origin/main seit dem Tag
    tracking_doc_nachzug.py --basis A --kopf B         # Bereich A..B
    tracking_doc_nachzug.py --commit <sha>             # ein Commit (Positivkontrolle)

Ausgabe: je Befund eine Zeile, dann `KURZ:` und `RESULT: BEFUND <n>` oder
`RESULT: OK`; Ref nicht lesbar ⇒ `RESULT: HINWEIS`, nie OK.
Exit 0 (advisory); mit `--strict` Exit 1 bei Befund.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field

DOC_ID_RE = re.compile(r"\b(ADR|KONZ)-(?:platform-)?(\d{3})\b")
DOC_VERZEICHNIS = {
    "ADR": "docs/adr/ADR-{n}-",
    "KONZ": "docs/konzepte/KONZ-platform-{n}-",
}
# Optionales Status-Symbol davor: Phasenstand-Tabellen schreiben „⬜ Ausstehend".
OFFEN_ZELLE_RE = re.compile(
    r"\|\s*(?:[^\w\s|]+\s*)?(?:offen|noch offen|steht aus|ausstehend)\s*\|",
    re.IGNORECASE,
)
OFFEN_CHECKBOX_RE = re.compile(r"^\s*[-*] \[ \]")
OFFEN_PROSA_RE = re.compile(r"\bnoch offen\b", re.IGNORECASE)
MAX_ZEILEN_JE_DOC = 3


@dataclass
class Befund:
    doc_id: str
    pfad: str
    commit: str
    betreff: str
    offene_zeilen: list[tuple[int, str]] = field(default_factory=list)


def _git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, timeout=60
    )


def doc_ids(text: str) -> set[str]:
    """`KONZ-071` und `KONZ-platform-071` sind dasselbe Dokument."""
    return {f"{art}-{nummer}" for art, nummer in DOC_ID_RE.findall(text)}


def offene_zeilen(inhalt: str) -> list[tuple[int, str]]:
    treffer = []
    for nr, zeile in enumerate(inhalt.splitlines(), start=1):
        if (
            OFFEN_ZELLE_RE.search(zeile)
            or OFFEN_CHECKBOX_RE.match(zeile)
            or OFFEN_PROSA_RE.search(zeile)
        ):
            treffer.append((nr, zeile.strip()))
    return treffer


def doc_pfade(repo: str, ref: str) -> dict[str, str]:
    """Doc-ID → Pfad am Ref, nur ADRs und platform-Konzepte."""
    out = _git(repo, "ls-tree", "-r", "--name-only", ref, "docs/adr", "docs/konzepte")
    pfade: dict[str, str] = {}
    for pfad in out.stdout.splitlines():
        for art, praefix in DOC_VERZEICHNIS.items():
            m = re.match(praefix.replace("{n}", r"(\d{3})"), pfad)
            if m and pfad.endswith(".md"):
                pfade.setdefault(f"{art}-{m.group(1)}", pfad)
    return pfade


def commits_im_bereich(
    repo: str, bereich: list[str]
) -> list[tuple[str, str, set[str]]]:
    """(sha, Nachricht, geänderte Dateien) je Commit, älteste zuerst."""
    log = _git(
        repo, "log", "--reverse", "--no-merges", "--format=%H%x00%B%x1e", *bereich
    )
    if log.returncode != 0:
        raise RuntimeError(log.stderr.strip() or "git log fehlgeschlagen")
    commits = []
    for block in log.stdout.split("\x1e"):
        block = block.strip("\n")
        if not block:
            continue
        sha, _, nachricht = block.partition("\x00")
        dateien = _git(repo, "show", "--name-only", "--format=", sha).stdout
        commits.append((sha, nachricht, set(dateien.split())))
    return commits


def pruefen(repo: str, bereich: list[str], kopf: str) -> list[Befund]:
    pfade = doc_pfade(repo, kopf)
    offen_seit: dict[str, tuple[str, str]] = {}
    for sha, nachricht, dateien in commits_im_bereich(repo, bereich):
        for doc_id, pfad in pfade.items():
            if pfad in dateien:
                offen_seit.pop(doc_id, None)
        for doc_id in doc_ids(nachricht):
            pfad = pfade.get(doc_id)
            if pfad and pfad not in dateien:
                offen_seit[doc_id] = (
                    sha,
                    nachricht.splitlines()[0] if nachricht else "",
                )
    befunde = []
    for doc_id, (sha, betreff) in sorted(offen_seit.items()):
        inhalt = _git(repo, "show", f"{kopf}:{pfade[doc_id]}").stdout
        zeilen = offene_zeilen(inhalt)
        if zeilen:
            befunde.append(Befund(doc_id, pfade[doc_id], sha, betreff, zeilen))
    return befunde


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--ref", default="origin/main", help="Kopf im --seit-Modus")
    ap.add_argument("--seit", help="Commits auf --ref seit diesem Datum (YYYY-MM-DD)")
    ap.add_argument("--basis")
    ap.add_argument("--kopf", default="HEAD")
    ap.add_argument("--commit")
    ap.add_argument("--strict", action="store_true", help="Exit 1 bei Befund")
    args = ap.parse_args(argv)

    if args.commit:
        bereich, kopf = [f"{args.commit}^..{args.commit}"], args.commit
    elif args.basis:
        bereich, kopf = [f"{args.basis}..{args.kopf}"], args.kopf
    elif args.seit:
        bereich, kopf = [f"--since={args.seit} 00:00", args.ref], args.ref
    else:
        ap.error("--seit, --basis oder --commit angeben")

    stand = _git(args.repo, "rev-parse", "--short", kopf)
    if stand.returncode != 0:
        print(f"RESULT: HINWEIS (Ref {kopf} nicht lesbar — keine Entwarnung)")
        return 0
    try:
        befunde = pruefen(args.repo, bereich, kopf)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"RESULT: HINWEIS ({exc} — keine Entwarnung)")
        return 0

    for b in befunde:
        print(
            f"BEFUND {b.doc_id} ({b.pfad}): erwähnt in {b.commit[:8]} "
            f"„{b.betreff}“, seither nicht geändert; {len(b.offene_zeilen)} offene Posten"
        )
        for nr, zeile in b.offene_zeilen[:MAX_ZEILEN_JE_DOC]:
            print(f"  L{nr}: {zeile[:160]}")
    if befunde:
        kurz = ", ".join(f"{b.doc_id} (via {b.commit[:8]})" for b in befunde)
        print(f"KURZ: {kurz}")
        print(f"RESULT: BEFUND {len(befunde)} (Stand {kopf} {stand.stdout.strip()})")
        return 1 if args.strict else 0
    print(f"RESULT: OK (Stand {kopf} {stand.stdout.strip()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
