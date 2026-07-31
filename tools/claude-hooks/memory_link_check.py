#!/usr/bin/env python3
"""Prueft die Verweis-Integritaet der Claude-Code-Memory-Verzeichnisse.

Hintergrund (2026-07-31): in `projects/-home-devuser-github-platform/memory`
waren 32 von 323 `[[..]]`-Verweisen tot. Groesste Einzelursache mit 11 Faellen:
das Frontmatter-Feld `name:` und der Dateiname duerfen auseinanderlaufen — die
Datei heisst `feedback_reporting_table_format.md`, verlinkt wurde
`[[feedback-reporting-table-format]]`. Ein Verweis auf den Frontmatter-Namen
zeigt dann ins Leere, obwohl das Ziel existiert.

Geprueft wird pro Memory-Verzeichnis:
  slug-mismatch   `name:` im Frontmatter passt nicht zum Dateinamen
  dead-wikilink   `[[ziel]]` hat keine Zieldatei
  dead-indexlink  `(datei.md)` in MEMORY.md hat keine Zieldatei
  missing-name    Frontmatter ohne `name:`-Feld

Exit-Code 1 bedeutet FUNDE, nicht "Werkzeug kaputt" — dieselbe Konvention wie
die Monitor-Workflows des Repos. Werkzeugfehler enden mit Exit-Code 2.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
INDEXLINK = re.compile(r"\]\(([^)]+\.md)\)")
NAME_FIELD = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)

# Code ist kein Verweis. Memories dokumentieren Makro- und Glob-Syntax, die
# zufaellig wie ein Wiki-Verweis aussieht — `[[clause:…]]`, `[[angebot-cover]]`,
# `[[*_extract*]]` aus dem design-hub-Renderer, `[[reisekosten:…]]` aus einer
# Angebotsvorlage. Wer den Codebereich mitliest, meldet Dokumentation als
# kaputten Link; am 2026-07-31 waren das 12 der 45 verbleibenden Befunde.
CODE_FENCE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def _ohne_code(text: str) -> str:
    """Leert Code-Bereiche, behaelt aber Laenge und Zeilenumbrueche.

    Bewusst leeren statt loeschen: so bleiben Zeilennummern und Offsets gueltig,
    falls der Bericht spaeter Zeilen nennen soll.
    """

    def leeren(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))

    return INLINE_CODE.sub(leeren, CODE_FENCE.sub(leeren, text))

# In MEMORY.md/Body duerfen Verweise auf Nicht-Memories stehen (Policies, ADRs).
# Die werden nicht als tot gemeldet, sondern verlangen Klartext statt [[..]] —
# deshalb hier nur die bekannten Ausnahmen, damit der Check keine Fehlalarme wirft.
NICHT_MEMORY = {"evidence-discipline", "session-routing", "llm-routing", "adr-threshold"}


@dataclass(frozen=True)
class Fund:
    art: str
    datei: str
    detail: str

    def zeile(self) -> str:
        return f"{self.art:<15} {self.datei:<58} {self.detail}"


def _slugs(mem: Path) -> set[str]:
    return {p.stem for p in mem.glob("*.md")}


def _frontmatter(text: str) -> str:
    """Gibt den Frontmatter-Block zurueck, sonst einen leeren String."""
    if not text.startswith("---"):
        return ""
    ende = text.find("\n---", 3)
    return text[3:ende] if ende != -1 else ""


def pruefe_verzeichnis(
    mem: Path, erlaubt: frozenset[str] | set[str] = frozenset()
) -> list[Fund]:
    """Prueft ein Memory-Verzeichnis.

    `erlaubt` sind vorausschauende Verweisziele aus der Baseline: sie werden als
    `forward-ref` gemeldet statt als `dead-wikilink` und lassen den Lauf gruen.
    Ein vorausschauender Verweis ist laut Memory-Spezifikation zulaessig — er
    markiert, was noch zu schreiben waere. Von einem Tippfehler ist er maschinell
    nicht zu unterscheiden, deshalb die ausdrueckliche Liste statt einer Heuristik.
    """
    funde: list[Fund] = []
    slugs = _slugs(mem)

    for pfad in sorted(mem.glob("*.md")):
        text = pfad.read_text(encoding="utf-8", errors="replace")
        # Verweise werden aus dem code-freien Text gelesen, das Frontmatter aus
        # dem Original — dort gibt es keine Code-Bereiche zu schonen.
        prosa = _ohne_code(text)
        name = pfad.name

        if name != "MEMORY.md":
            fm = _frontmatter(text)
            treffer = NAME_FIELD.search(fm)
            if not treffer:
                funde.append(Fund("missing-name", name, "kein name:-Feld im Frontmatter"))
            elif treffer.group(1) != pfad.stem:
                funde.append(
                    Fund("slug-mismatch", name, f"name: {treffer.group(1)!r} != Dateiname")
                )

        for ziel in WIKILINK.findall(prosa):
            if ziel in slugs or ziel in NICHT_MEMORY:
                continue
            art = "forward-ref" if ziel in erlaubt else "dead-wikilink"
            funde.append(Fund(art, name, f"[[{ziel}]]"))

        if name == "MEMORY.md":
            for ziel in INDEXLINK.findall(prosa):
                if ziel.startswith(("http://", "https://")):
                    continue
                if not (mem / ziel).exists():
                    funde.append(Fund("dead-indexlink", name, ziel))

    return funde


BASELINE = Path(__file__).with_name("memory_forward_refs.tsv")


def lade_baseline(pfad: Path) -> dict[str, set[str]]:
    """projekt -> erlaubte Verweisziele. Fehlende Datei = leere Baseline."""
    erlaubt: dict[str, set[str]] = {}
    if not pfad.is_file():
        return erlaubt
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        teile = zeile.split("\t")
        if len(teile) < 2:
            continue
        erlaubt.setdefault(teile[0].strip(), set()).add(teile[1].strip())
    return erlaubt


def pruefe_baseline(mem: Path, erlaubt: set[str], gesehen: set[str]) -> list[Fund]:
    """Meldet Baseline-Eintraege, die ihren Zweck verloren haben.

    Ohne diese Rueckrichtung wird jede Ausnahmeliste zur stillen Dauerschuld:
    Eintraege bleiben stehen, nachdem das Memory geschrieben oder der Verweis
    entfernt wurde, und decken irgendwann einen echten Tippfehler mit ab.
    """
    funde: list[Fund] = []
    for ziel in sorted(erlaubt):
        if (mem / f"{ziel}.md").exists():
            funde.append(
                Fund(
                    "stale-baseline",
                    "memory_forward_refs.tsv",
                    f"{ziel} existiert inzwischen — Eintrag entfernen",
                )
            )
        elif ziel not in gesehen:
            funde.append(
                Fund(
                    "stale-baseline",
                    "memory_forward_refs.tsv",
                    f"{ziel} wird nicht mehr verwiesen — Eintrag entfernen",
                )
            )
    return funde


def finde_verzeichnisse(wurzel: Path) -> list[Path]:
    if (wurzel / "MEMORY.md").exists() or wurzel.name == "memory":
        return [wurzel]
    return sorted(p for p in wurzel.glob("*/memory") if p.is_dir())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--root",
        default=str(Path.home() / ".claude" / "projects"),
        help="Wurzel mit <projekt>/memory-Verzeichnissen ODER ein Memory-Verzeichnis selbst",
    )
    ap.add_argument("--json", action="store_true", help="Funde als JSON ausgeben")
    ap.add_argument(
        "--baseline",
        default=str(BASELINE),
        help="TSV mit erlaubten vorausschauenden Verweisen (projekt\\tziel\\tgrund)",
    )
    args = ap.parse_args(argv)
    baseline = lade_baseline(Path(args.baseline).expanduser())

    wurzel = Path(args.root).expanduser()
    if not wurzel.is_dir():
        print(f"FEHLER: kein Verzeichnis: {wurzel}", file=sys.stderr)
        return 2

    verzeichnisse = finde_verzeichnisse(wurzel)
    if not verzeichnisse:
        print(f"FEHLER: keine Memory-Verzeichnisse unter {wurzel}", file=sys.stderr)
        return 2

    alle: list[tuple[Path, list[Fund]]] = []
    for mem in verzeichnisse:
        erlaubt = baseline.get(mem.parent.name, set())
        funde = pruefe_verzeichnis(mem, erlaubt)
        gesehen = {f.detail[2:-2] for f in funde if f.art == "forward-ref"}
        funde += pruefe_baseline(mem, erlaubt, gesehen)
        alle.append((mem, funde))

    gesamt = sum(len(f) for _, f in alle)
    hart = sum(1 for _, fs in alle for f in fs if f.art != "forward-ref")
    dateien = sum(len(list(m.glob("*.md"))) for m, _ in alle)

    if args.json:
        print(
            json.dumps(
                {
                    "verzeichnisse": len(verzeichnisse),
                    "dateien": dateien,
                    "funde": gesamt,
                    "harte_funde": hart,
                    "details": [
                        {"verzeichnis": str(m), "funde": [asdict(f) for f in fs]}
                        for m, fs in alle
                        if fs
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if hart else 0

    for mem, funde in alle:
        if not funde:
            continue
        print(f"\n{mem}")
        for f in funde:
            print("  " + f.zeile())

    weich = gesamt - hart
    print(
        f"\n{len(verzeichnisse)} Verzeichnisse, {dateien} Dateien, {hart} harte Funde"
        + (f", {weich} vorausschauend (Baseline)" if weich else "")
        + ("" if hart else " — sauber")
    )
    return 1 if hart else 0


if __name__ == "__main__":
    sys.exit(main())
