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
from datetime import datetime, timezone
from statistics import median

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


def _liegezeit(zaehler, retros, gedeckt: set[str], heute: str) -> dict | None:
    """Wie lange liegt ein unentschiedener Befund schon da?

    Bis hierhin misst dieses Werkzeug nur den BESTAND: wie viele Slugs ohne
    Entscheidung. Ein Bestand allein sagt nicht, ob der Loop schneller entscheidet
    als er findet — er kann bei 77 stehen, weil gestern 77 neue dazukamen, oder
    weil dieselben 77 seit Monaten liegen. Das sind zwei verschiedene Lagen mit
    derselben Zahl.

    Gemessen wird ab dem ERSTEN Vorkommen, nicht ab dem letzten: ein Slug, der
    seit Mai wiederkehrt, liegt seit Mai, auch wenn er gestern zuletzt auftrat.

    Median statt Mittelwert, weil ein einzelner sehr alter Slug den Mittelwert
    traegt und dann eine Verbesserung vortaeuscht, sobald er endlich entschieden
    wird.

    **Die Zahl ist eine Untergrenze, keine Messung.** Sie kann nur so weit
    zurueckreichen wie der Retro-Korpus. Ein Slug, der schon vor dem aeltesten
    Report auftrat, bekommt das Korpus-Anfangsdatum und erscheint dadurch
    juenger, als er ist. Gemessen am 2026-08-25: der aelteste unentschiedene
    Slug lag bei 56 Tagen — bei einem Korpus von exakt 56 Tagen. Ein Wert am
    Rand ist also abgeschnitten, nicht bestaetigt. Deshalb traegt die
    Berichtszeile das Korpus-Anfangsdatum mit; ohne es liest sich die Zahl
    genauer, als sie ist.
    """
    tage = []
    stichtag = datetime.strptime(heute, "%Y-%m-%d").date()
    for slug in zaehler:
        if slug in gedeckt:
            continue
        erstes = min(r[0] for r in retros if slug in r[1])
        try:
            alter = (stichtag - datetime.strptime(erstes, "%Y-%m-%d").date()).days
        except ValueError:
            continue  # unparsbares Retro-Datum: nicht raten, weglassen
        tage.append((alter, slug))
    if not tage:
        return None
    tage.sort()
    aeltester = tage[-1]
    return {
        "slugs": len(tage),
        "median_tage": int(median(a for a, _ in tage)),
        "aeltester_tage": aeltester[0],
        "aeltester_slug": aeltester[1],
        "korpus_ab": min(r[0] for r in retros),
    }


def bewerte(retros, gedeckt: set[str], heute: str | None = None) -> dict:
    # `lies_retros` liefert seit 2026-08-20 ein VIERTES Feld (`gates_caught`).
    # Hier zaehlt weiter jedes Vorkommen — dieses Werkzeug fragt "gibt es ueberhaupt
    # eine Entscheidung zu dem Slug?", nicht "hat ein Gate ihn gefangen". Der Zugriff
    # ueber den Index nimmt drei- wie vierstellige Tupel.
    zaehler = Counter()
    for retro in retros:
        zaehler.update(retro[1])

    offen = [
        {
            "slug": s,
            "vorkommen": n,
            "letztes": max(r[0] for r in retros if s in r[1]),
        }
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
        "liegezeit": _liegezeit(
            zaehler,
            retros,
            gedeckt,
            heute or datetime.now(timezone.utc).date().isoformat(),
        ),
    }


def liegezeit_zeile(lz: dict, kurz: bool = False) -> str:
    if kurz:
        # Die Runner-Summary ist eine Tabelle; eine lange Notiz sprengt die
        # Zeile. Das `>=` bleibt auch hier stehen — es ist der Unterschied
        # zwischen einer Messung und einer Untergrenze, nicht Zierrat.
        return (
            f"Liegezeit Median >={lz['median_tage']} d, "
            f"aeltester >={lz['aeltester_tage']} d ({lz['slugs']} offen)"
        )
    return (
        f"Liegezeit unentschieden: Median >= {lz['median_tage']} d, "
        f"aeltester >= {lz['aeltester_tage']} d ({lz['aeltester_slug']}), "
        f"{lz['slugs']} Slugs — Untergrenze, Korpus ab {lz['korpus_ab']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--dir", action="append", dest="dirs")
    parser.add_argument("--kurz", action="store_true")
    parser.add_argument("--json", action="store_true", dest="als_json")
    parser.add_argument(
        "--liegezeit",
        action="store_true",
        help="nur die eine Zeile: wie lange unentschiedene Befunde liegen",
    )
    args = parser.parse_args()

    try:
        registry = json.load(open(args.registry, encoding="utf-8"))
    except (OSError, ValueError) as fehler:
        # Fail-open wie die Geschwister-Werkzeuge: ein Melder, der den
        # Sitzungsstart aufhaelt, wird abgeschaltet und meldet danach gar nichts.
        # `--kurz` schrieb diese Zeile bisher gar nicht, und im Nicht-kurz-Fall
        # ging sie nach stderr. Der Sitzungsstart ruft `--kurz 2>/dev/null` auf:
        # beide Unterdrueckungen zugleich. Leere Ausgabe liest der Runner als
        # PASS und behauptet dann "keine offene Gate-Pflicht" — ein Satz ueber Gates, die nie
        # gelesen wurden. Fail-open bleibt (Exit 0, der Start laeuft weiter),
        # aber die Zeile geht nach STDOUT, damit daraus ein WARN wird statt
        # eines stillen Gruens (platform#2278).
        print(
            "Registry nicht lesbar — dieser Lauf misst nichts, kein Urteil ueber Gates"
        )
        if not args.kurz:
            print(f"  Grund: {fehler}", file=sys.stderr)
        return 0

    gw = _lade_gate_wirkung()
    retros = gw.lies_retros(args.dirs or gw.standard_verzeichnisse())
    ergebnis = bewerte(retros, gedeckte_slugs(registry))
    offen = ergebnis["offene_pflichten"]

    if args.als_json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
        return 0

    if args.liegezeit:
        # Eigener Aufruf statt Anhaengsel an `--kurz`: der Runner entscheidet PASS
        # und WARN allein an der LAENGE der `--kurz`-Ausgabe. Wuerde die Liegezeit
        # dort mitlaufen, waere 0.7.9 dauerhaft gelb, und ein Melder, der jede
        # Sitzung warnt, wird nicht gelesen. Dieselbe Zweitabfrage nutzt der
        # Runner schon fuer die Zahlen von `gate_namensdeckung` (Phase 0.7.15).
        if lz := ergebnis["liegezeit"]:
            print(liegezeit_zeile(lz, args.kurz))
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
    if ergebnis["liegezeit"]:
        print(f"  {liegezeit_zeile(ergebnis['liegezeit'])}")
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
