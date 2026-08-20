#!/usr/bin/env python3
"""gate_deckung.py — die vierte Achse: wurde fuer einen Befund je etwas GEBAUT?

## Warum es das gibt

Der Loop hat drei Messpunkte und eine Luecke — dieselbe Konstruktion wie bei
`gate_wirkung.py`, nur eine Ebene davor:

- `docs/governance/gate-registry.json` sagt, ein Gate ist **gebaut**.
- `tools/gate_drill_check.py` sagt, es **feuert**.
- `tools/gate_wirkung.py` sagt, ob es **wirkt** (Rueckfaelle nach dem Bau).
- **Keiner** sagt, fuer wie viele Befunde ueberhaupt je etwas gebaut wurde.

`retro_kpis.py` eskaliert jeden Slug mit Zaehler >= 2 zur "GATE-PFLICHT". Diese
Pflicht wird gezaehlt, aber ihre **Einloesung** nirgends. Gemessen am 2026-08-20
ueber alle Retros: von 100 Befund-Slugs tragen **16** ein Gate oder einen
dokumentierten Verzicht — **84 tragen nichts**. Darunter `planned-phase-no-issue`
mit **acht** Vorkommen: achtmal eskaliert, nie gebaut, nie bewusst abgelehnt.

Der Unterschied zu `gate_wirkung.py` in einem Satz: dort geht es um Gates, die
**versagen**; hier um Befunde, fuer die nie eines **entstand**. Das erste ist ein
lautes Problem, das zweite ein stilles — und deshalb das groessere.

## Was "Deckung" heisst und was nicht

Gedeckt ist ein Slug, wenn er in der Registry steht — als **Gate** ODER in der
**declined**-Liste. Ein bewusst abgelehntes Gate ist eine getroffene Entscheidung
und damit gedeckt; genau dafuer existiert die Liste. Ungedeckt heisst: niemand hat
je entschieden, weder dafuer noch dagegen.

**Einmalige Befunde sind kein Versaeumnis.** Ein Slug mit Zaehler 1 gehoert nicht
automatisch gegated — die Schwelle des Hauses ist 2 (`retro_kpis.py`). Dieses
Werkzeug meldet deshalb nur, was **mehrfach** auftrat und trotzdem nichts hat; die
Einmaligen erscheinen als Kontext, nicht als Befund.

## Aufruf

    python3 tools/gate_deckung.py            # voller Report
    python3 tools/gate_deckung.py --kurz     # eine Zeile fuer den Session-Start
    python3 tools/gate_deckung.py --json     # maschinenlesbar
    python3 tools/gate_deckung.py --dir <p>  # Retro-Verzeichnis(se) ueberschreiben

Exit-Code 0 immer — Report-Werkzeug, kein Enforcer (Hausform wie `retro_kpis.py`,
`gate_drill_check.py`, `gate_wirkung.py`). stdlib-only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections import Counter

# Maschinenlesbarer Kopf (KONZ-038 D8)
GATE_HEADER = {
    "slug": "gate-pflicht-nie-eingeloest",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-20",
    "evidence": "tools/tests/test_gate_deckung.py",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(REPO_ROOT, "docs", "governance", "gate-registry.json")

# Ab so vielen Vorkommen gilt ein ungedeckter Slug als Befund. Deckungsgleich mit
# der GATE-PFLICHT-Schwelle in retro_kpis.py — zwei Werkzeuge duerfen sich hier
# nicht widersprechen, sonst eskaliert das eine, was das andere durchwinkt.
PFLICHT_SCHWELLE = 2


def _lade_gate_wirkung():
    """Retro-Leser aus `gate_wirkung.py` wiederverwenden statt ihn zu kopieren.

    Der Parser dort hat zwei Fehler hinter sich (Bau-Tag-Zaehlung, Kommentar-Abbruch,
    Retro beefc148) und ist seither getestet. Eine zweite Kopie waere die dritte
    Gelegenheit fuer denselben Fehler — und beim naechsten Frontmatter-Format
    wuerde nur eine der beiden nachgezogen.
    """
    pfad = os.path.join(REPO_ROOT, "tools", "gate_wirkung.py")
    spec = importlib.util.spec_from_file_location("gate_wirkung", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def gedeckte_slugs(registry: dict) -> set[str]:
    """Gates (inkl. ihrer `covers`-Liste) UND declined — jede getroffene Entscheidung.

    **`covers` ist Pflicht, nicht Kuer.** Ein Gate deckt oft mehr als seinen eigenen
    Slug: `aufschub-anker` deckt `planned-phase-no-issue` mit. Wer nur `slug` liest,
    meldet solche Slugs faelschlich als ungedeckt — der erste Lauf dieses Werkzeugs
    kam so auf 19 offene Pflichten, waehrend `retro_kpis.py` (das `covers` liest) 3
    meldete. Zwei Werkzeuge, die dieselbe Registry unterschiedlich lesen, sind
    schlimmer als eines: sie machen jede Zahl verhandelbar.
    """
    gedeckt: set[str] = set()
    for g in registry.get("gates", []):
        if g.get("slug"):
            gedeckt.add(g["slug"])
        gedeckt.update(c for c in g.get("covers", []) if isinstance(c, str))
    for eintrag in registry.get("declined", []):
        gedeckt.add(eintrag if isinstance(eintrag, str) else eintrag.get("slug"))
    return {s for s in gedeckt if s}


def bewerte(retros, gedeckt: set[str]) -> dict:
    zaehler = Counter()
    for _datum, slugs, _name in retros:
        zaehler.update(slugs)

    offen = [
        {"slug": s, "vorkommen": n, "letztes": max(d for d, sl, _ in retros if s in sl)}
        for s, n in zaehler.items()
        if s not in gedeckt and n >= PFLICHT_SCHWELLE
    ]
    offen.sort(key=lambda e: (-e["vorkommen"], e["slug"]))
    einmalig = sorted(
        s for s, n in zaehler.items() if s not in gedeckt and n < PFLICHT_SCHWELLE
    )

    return {
        "slugs_gesamt": len(zaehler),
        "gedeckt": sorted(s for s in zaehler if s in gedeckt),
        "offene_pflichten": offen,
        "einmalig_ungedeckt": einmalig,
        "retros": len(retros),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--dir", action="append", dest="dirs")
    parser.add_argument("--kurz", action="store_true")
    parser.add_argument("--json", action="store_true", dest="als_json")
    args = parser.parse_args()

    try:
        registry = json.load(open(args.registry, encoding="utf-8"))
    except (OSError, ValueError) as fehler:
        # Fail-open wie die Geschwister-Werkzeuge: ein Melder, der den
        # Sitzungsstart aufhaelt, wird abgeschaltet und meldet danach gar nichts.
        if not args.kurz:
            print(f"Registry nicht lesbar ({fehler}) — kein Urteil.", file=sys.stderr)
        return 0

    gw = _lade_gate_wirkung()
    retros = gw.lies_retros(args.dirs or gw.standard_verzeichnisse())
    ergebnis = bewerte(retros, gedeckte_slugs(registry))
    offen = ergebnis["offene_pflichten"]

    if args.als_json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
        return 0

    if args.kurz:
        if offen:
            spitze = offen[0]
            weitere = f" (+{len(offen) - 1} weitere)" if len(offen) > 1 else ""
            print(
                f"{len(offen)} Befund(e) mehrfach aufgetreten, aber nie gegated — "
                f"{spitze['slug']}: {spitze['vorkommen']}x, zuletzt {spitze['letztes']}{weitere}"
            )
            for e in offen[1:5]:
                print(f"  · {e['slug']} — {e['vorkommen']}x, zuletzt {e['letztes']}")
            if len(offen) > 5:
                print(
                    f"  · … {len(offen) - 5} weitere, Vollbild: tools/gate_deckung.py"
                )
        return 0

    gesamt = ergebnis["slugs_gesamt"]
    gedeckt_n = len(ergebnis["gedeckt"])
    quote = (100 * gedeckt_n // gesamt) if gesamt else 0
    print(f"# Gate-Deckung ueber {ergebnis['retros']} Retro-Reports\n")
    print(f"Befund-Slugs insgesamt : {gesamt}")
    print(f"  mit Gate oder Verzicht: {gedeckt_n}  ({quote} %)")
    print(f"  ohne jede Entscheidung: {gesamt - gedeckt_n}")
    print()

    if offen:
        print(
            f"🚨 {len(offen)} Slug(s) >= {PFLICHT_SCHWELLE}x aufgetreten und trotzdem ungedeckt:\n"
        )
        kopf = f"{'slug':<48}{'x':>4}  letztes Vorkommen"
        print(kopf)
        print("-" * len(kopf))
        for e in offen:
            print(f"{e['slug']:<48}{e['vorkommen']:>4}  {e['letztes']}")
        print(
            "\n→ Jeder dieser Slugs wurde von `retro_kpis.py` als GATE-PFLICHT gemeldet.\n"
            "  Die Pflicht wird dort gezaehlt, ihre Einloesung nirgends — das ist diese Liste.\n"
            "  Zulaessige Abschluesse je Zeile: Gate bauen, ODER in die `declined`-Liste der\n"
            "  Registry eintragen (mit Grund). Liegenlassen ist der dritte Weg und der\n"
            "  einzige, der nicht zaehlt."
        )
    else:
        print("→ Kein mehrfacher Befund ohne Entscheidung.")

    einmalig = ergebnis["einmalig_ungedeckt"]
    if einmalig:
        print(
            f"\n  ({len(einmalig)} weitere Slugs sind ungedeckt, aber bisher nur EINMAL "
            f"aufgetreten — unterhalb der Schwelle {PFLICHT_SCHWELLE} und damit kein Befund.)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
