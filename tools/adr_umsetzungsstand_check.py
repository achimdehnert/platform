#!/usr/bin/env python3
"""adr_umsetzungsstand_check.py — zwei Pruefungen auf `implementation_status`.

## Warum es das gibt

Ein ADR mit `status: accepted` liest sich als geltendes Recht. Ob es auch
GEBAUT ist, steht in `implementation_status` — einem Frontmatter-Feld, das
beim Lesen des Fliesstexts niemand sieht. Wer die Datei oeffnet, sieht oben
"accepted" und darunter eine Anleitung, und befolgt sie.

Realfall 2026-09-07 (platform#2931): ADR-228 stand auf `accepted` und
`implementation_status: none`. Ich bin der Anleitung gefolgt, habe eine Datei
in der dort vorgeschriebenen Form angelegt — und bin am **Pflicht-Gate**
gescheitert, weil die Form nie umgesetzt worden war. Die Regel war nicht nur
unwirksam, sie war aktiv irrefuehrend. Behoben wurde das durch einen von Hand
geschriebenen Hinweis direkt unter der Ueberschrift.

Dieses Werkzeug sucht die anderen Faelle derselben Art.

## Was geprueft wird

Ein ADR faellt auf, wenn ALLE drei zutreffen:

1. `status: accepted` — es liest sich als geltend
2. `implementation_status` NICHT in (implemented, complete, verified,
   rolled_back) — es ist nicht fertig gebaut
3. der Fliesstext traegt keinen sichtbaren Hinweis darauf

Punkt 3 ist der eigentliche Befund. Nicht "ungebaut" ist das Problem — das ist
ein normaler Zwischenzustand und steht sauber im Frontmatter. Das Problem ist
"ungebaut UND liest sich wie geltend".

## Modus

SUGGEST ist Vorgabe (Exit 0 auch bei Funden). Neue Regeln starten im Repo
advisory, bis der Bestand bereinigt und die Fehlalarm-Klasse bekannt ist
(repo-health-rule-discipline). `--gate` macht daraus Exit 1.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DIR_DEFAULT = REPO_ROOT / "docs" / "adr"

FRONT_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
STATUS_RE = re.compile(r"^status:\s*(\S+)", re.MULTILINE)
IMPL_RE = re.compile(r"^implementation_status:\s*(\S+)", re.MULTILINE)

# Das Schema gibt `implementation_status` den Default "none" — ein fehlendes
# Feld heisst also "nicht gebaut", nicht "unbekannt".
IMPL_DEFAULT = "none"
FERTIG = {"implemented", "complete", "verified", "rolled_back"}

# Der Werte-Vorrat aus dem Schema von iil-adrfw (adr_frontmatter.schema.json).
# Hier gespiegelt, weil `iil-adrfw validate` ihn NICHT durchsetzt: gemessen am
# 2026-09-08 traegt eine Datei mit `implementation_status: voellig-erfundener-wert`
# das Urteil "2/2 valid" davon. Ein Feld, das jeden Wert annimmt, macht jede
# Auswertung darauf still falsch — auch die, mit der dieser Befund entstand.
ENUM = {
    "none",
    "planned",
    "in_progress",
    "partial",
    "implemented",
    "complete",
    "verified",
    "rolled_back",
}

# Ein Hinweis muss SICHTBAR sein — im Fliesstext, nicht im Frontmatter. Die
# Muster sind bewusst wenige und stehen hier im Klartext, damit man sie im
# Befund nachvollziehen kann. Sie decken die Formen ab, die im Repo vorkommen:
# Admonition-Bloecke, Blockzitate und ausgeschriebene Saetze.
HINWEIS_MUSTER = [
    re.compile(r"nicht\s+in\s+kraft", re.IGNORECASE),
    re.compile(r"noch\s+nicht\s+(umgesetzt|gebaut|implementiert)", re.IGNORECASE),
    re.compile(r"\bimplementation_status\b", re.IGNORECASE),
    re.compile(r"not\s+yet\s+implemented", re.IGNORECASE),
    re.compile(r"\bteilweise\s+umgesetzt\b", re.IGNORECASE),
]

# Nur der Kopf des Fliesstexts zaehlt: ein Hinweis, den man erst nach 300
# Zeilen findet, hat den Leser laengst verfehlt.
KOPF_ZEILEN = 40


def hat_hinweis(body: str, kopf_zeilen: int = KOPF_ZEILEN) -> bool:
    """Traegt der Kopf des Fliesstexts einen sichtbaren Umsetzungs-Hinweis?"""
    kopf = "\n".join(body.splitlines()[:kopf_zeilen])
    return any(p.search(kopf) for p in HINWEIS_MUSTER)


def pruefe_datei(pfad: Path) -> list[dict]:
    """Alle Befunde zu einer Datei — leere Liste, wenn sie unauffaellig ist."""
    m = FRONT_RE.match(pfad.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return []
    front, body = m.group(1), m.group(2)
    status = (STATUS_RE.search(front) or [None, "?"])[1]
    impl_m = IMPL_RE.search(front)
    impl = impl_m.group(1) if impl_m else IMPL_DEFAULT

    befunde = []
    # Pruefung 1 — Wert ausserhalb des Schema-Vorrats.
    if impl_m and impl not in ENUM:
        befunde.append(
            {"art": "wert", "datei": pfad.name, "implementation_status": impl}
        )
    # Pruefung 2 — liest sich als geltend, ist es aber nicht, und sagt es nicht.
    # Bewusst nur bei ausdruecklichem `none`: `partial` heisst, dass etwas
    # existiert, und ein fehlendes Feld heisst "nicht erklaert", nicht
    # "nicht gebaut". Beide waeren hier Rauschen — gemessen 92 statt 8 Funde.
    if status == "accepted" and impl_m and impl == "none" and not hat_hinweis(body):
        befunde.append(
            {"art": "hinweis", "datei": pfad.name, "implementation_status": impl}
        )
    return befunde


def sammle(adr_dir: Path) -> list[dict]:
    befunde = []
    for f in sorted(adr_dir.glob("ADR-[0-9]*.md")):
        befunde.extend(pruefe_datei(f))
    return befunde


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adr-dir", default=str(ADR_DIR_DEFAULT))
    ap.add_argument(
        "--gate",
        action="store_true",
        help="Exit 1 bei Funden (Vorgabe: SUGGEST, Exit 0)",
    )
    a = ap.parse_args(argv)

    adr_dir = Path(a.adr_dir)
    if not adr_dir.is_dir():
        print(f"ADR-Verzeichnis nicht lesbar: {adr_dir}", file=sys.stderr)
        return 2

    befunde = sammle(adr_dir)
    if not befunde:
        print("✓ implementation_status: alle Werte gueltig, kein stiller Widerspruch.")
        return 0

    marke = "🚫" if a.gate else "💡"
    wert = [b for b in befunde if b["art"] == "wert"]
    hinweis = [b for b in befunde if b["art"] == "hinweis"]

    if wert:
        print(
            f"{marke} {len(wert)} ADR(s) mit einem Wert ausserhalb des Schema-Vorrats:"
        )
        for b in wert:
            print(f"  - {b['datei']}  [{b['implementation_status']}]")
        print(f"  erlaubt: {', '.join(sorted(ENUM))}")
        print()
    if hinweis:
        print(
            f"{marke} {len(hinweis)} ADR(s) stehen auf accepted + none und sagen "
            "im Text nicht, dass nichts davon gebaut ist:"
        )
        for b in hinweis:
            print(f"  - {b['datei']}")
        print(
            "  Fix: kurzer Hinweis direkt unter die H1, was bis zur Umsetzung gilt "
            "— Vorlage: docs/adr/ADR-228-*.md (platform#2931)."
        )
    return 1 if a.gate else 0


if __name__ == "__main__":
    sys.exit(main())
