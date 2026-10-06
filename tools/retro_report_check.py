#!/usr/bin/env python3
"""retro_report_check.py — prueft einen Retro-Report gegen die harten Regeln des Skills.

## Anlass (2026-09-16)

`/session-retro` fuehrt fuenf **Eiserne Regeln** ("nicht verhandelbar"). Regel 5
verlangt woertlich: *"Jeder Report endet auf getan · angenommen · nicht
verifizierbar · offen geblieben"* — die Abdeckungsauskunft, die "nichts
gefunden" von "nicht hingesehen" unterscheidbar macht.

Gemessen an diesem Tag ueber die 16 Reports seit dem 2026-09-02: **5 ohne
diesen Vierklang**, darunter die zwei juengsten (2026-09-14 apo-hub 40c069 und
platform b7822e). Die Abschluss-Checkliste des Skills hat dafuer keine Zeile —
ihr Punkt 11 verlangt "§8 gefuellt", und §8 ist in allen 16 vorhanden. Die
Regel war also da, ihre Pruefung nicht.

Dasselbe Muster wie bei `skill_phasen_deckung.py`: eine als PFLICHT markierte
Anweisung ohne Zeile in der Abschluss-Checkliste wird beim Lesen ueberflogen.

## Was geprueft wird

| Regel | Quelle im Skill | Pruefung |
|---|---|---|
| Vierklang | Eiserne Regel 5 | alle vier Woerter im Report (Gross/Klein egal) |
| §8 vorhanden | Checkliste 11 | Ueberschrift `## 8` |
| eingefrorene Spalten | Anti-Pattern "Nummernlose Befund-Zeile" | Kopfzeile der Befund-Tabelle woertlich |
| Pflicht-Frontmatter | Phase 4 / 5b / 7 | `findings_total`, `refuted_rate`, `pre_refuted`, `over_ask_klassen`, `over_act_klassen`, `gate_candidates` |
| Streichbahn | Phase 7 | `streichkandidaten:` — leer nur mit `streich_begruendung:` |

**Baseline statt Rueckwirkung** (Lehre `advisory-scanner-reactivation-needs-baseline`):
der Sammel-Lauf prueft nur Reports ab `GILT_AB`. Die fuenf aelteren Luecken sind
oben als gemessene Ausgangslage festgehalten und werden nicht nachtraeglich rot
gemacht — ein Pruefer, der beim ersten Lauf 5 Altlasten meldet, wird abgeschaltet
statt befolgt.

Aufruf:
  python3 tools/retro_report_check.py <datei.md>     # ein Report
  python3 tools/retro_report_check.py --alle [--kurz] # alle ab GILT_AB
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

GILT_AB = "2026-09-16"

SPALTEN = "| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |"
VIERKLANG = ("getan", "angenommen", "nicht verifizierbar", "offen geblieben")
PFLICHT_FELDER = (
    "findings_total",
    "refuted_rate",
    "pre_refuted",
    "over_ask_klassen",
    "over_act_klassen",
    "gate_candidates",
)

_DATUM_IM_NAMEN = re.compile(r"session-retro-(\d{4}-\d{2}-\d{2})-")


def datum_aus_name(pfad: pathlib.Path) -> str | None:
    m = _DATUM_IM_NAMEN.match(pfad.name)
    return m.group(1) if m else None


def pruefe(text: str) -> list[str]:
    """Liste der Regelverstoesse. Leer = sauber."""
    befunde: list[str] = []
    klein = text.lower()

    fehlend = [w for w in VIERKLANG if w not in klein]
    if fehlend:
        befunde.append(
            "Eiserne Regel 5: Abdeckungsauskunft unvollstaendig — fehlt: "
            + ", ".join(fehlend)
        )

    if not re.search(r"^##\s*8[.\s]", text, re.M):
        befunde.append("Abschnitt `## 8` (Nicht verifiziert / Restluecken) fehlt")

    if SPALTEN not in text:
        befunde.append(
            "Befund-Tabelle ohne die eingefrorenen Spalten — `findings_total` "
            "und der Laengsschnitt haengen an dieser Kopfzeile"
        )

    kopf = text[:4000]
    fehlende_felder = [
        f for f in PFLICHT_FELDER if not re.search(rf"^{f}:", kopf, re.M)
    ]
    if fehlende_felder:
        befunde.append(
            "Frontmatter unvollstaendig — fehlt: " + ", ".join(fehlende_felder)
        )

    m = re.search(r"^streichkandidaten:\s*\[(.*?)\]", kopf, re.M | re.S)
    if m is None:
        befunde.append("Phase 7: `streichkandidaten:` fehlt im Frontmatter")
    elif not m.group(1).strip() and not re.search(r"^streich_begruendung:", kopf, re.M):
        befunde.append(
            "Phase 7: leere `streichkandidaten:` ohne `streich_begruendung:` — "
            "'keiner' braucht den Grund-Satz, nicht nur das Wort"
        )

    return befunde


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("datei", nargs="?", help="ein Report; ohne Angabe: --alle noetig")
    p.add_argument("--alle", action="store_true", help=f"alle Reports ab {GILT_AB}")
    p.add_argument("--kurz", action="store_true", help="eine Zeile statt Bericht")
    a = p.parse_args(argv)

    wurzel = pathlib.Path(__file__).resolve().parent.parent
    if a.alle:
        dateien = [
            f
            for f in sorted((wurzel / "docs" / "retros").glob("session-retro-*.md"))
            if (datum_aus_name(f) or "") >= GILT_AB
        ]
    elif a.datei:
        dateien = [pathlib.Path(a.datei)]
    else:
        p.error("entweder <datei> oder --alle")

    treffer: list[tuple[pathlib.Path, list[str]]] = []
    for f in dateien:
        if not f.exists():
            print(f"⛔ nicht lesbar: {f}", file=sys.stderr)
            return 2
        befunde = pruefe(f.read_text(encoding="utf-8"))
        if befunde:
            treffer.append((f, befunde))

    offen = sum(len(b) for _, b in treffer)
    if a.kurz:
        wort = "Report" if len(dateien) == 1 else "Reports"
        if offen:
            print(
                f"retro-report: {offen} Verstoss/Verstoesse in {len(treffer)}/{len(dateien)} {wort}"
            )
        else:
            print(f"retro-report: {len(dateien)} {wort} regelkonform (ab {GILT_AB})")
        return 1 if offen else 0

    if not treffer:
        print(f"✅ {len(dateien)} Report(s) regelkonform (Pruefbereich ab {GILT_AB})")
        return 0

    print(f"⛔ {offen} Verstoss/Verstoesse:")
    for f, befunde in treffer:
        print(f"\n  {f.name}")
        for b in befunde:
            print(f"    - {b}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
