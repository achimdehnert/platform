#!/usr/bin/env python3
"""Die zwei Gegenchecks des ux-review-Laufs — KONZ-platform-051 K7 und K8.

Beide waren im Konzept als Skill-Parameter beschrieben (`-kd`, `-marker`,
Zeile 138/139) und **nie gebaut**. Am 2026-09-01 gemessen: `Kontrollmarker`,
`weg-fehlt` und `spec-luecke` kamen in `.windsurf/workflows/ux-review.md` je
0-mal vor, in beiden verteilten Kopien ebenfalls 0 — waehrend die
Positivkontrolle (`--kette`, `--no-issues`, `--vor`) je 6 Treffer fand. K7 und
K8 massen also Funktionen, die es nicht gab.

Bewusst OHNE `GATE_HEADER`: dies ist ein Messwerkzeug, kein Gate. Ein Kopf, der
ein Gate behauptet, das der Code nicht durchsetzt, ist schlimmer als keiner — er
laesst die Registry gedeckt aussehen, wo nichts geprueft wird.

Warum ein Werkzeug und nicht eine Anweisung im Skill: beide Checks sind
Mengenvergleiche. Ein Mengenvergleich, den ein Agent im Kopf macht, ist beim
naechsten Lauf ein anderer. Der Lauf erzeugt ein kleines JSON, dieses Werkzeug
faellt das Urteil — reproduzierbar und ohne Browser testbar.

## Unterbefehl `kd` (K7)

Vergleicht die Screens einer Klickdummy-Spec mit den Stationen, die der
Klick-Durchlauf wirklich erreicht hat.

  weg-fehlt    (fehler)       Screen ist als `routing_mode: live` spezifiziert,
                              wurde aber nie erreicht — ein Weg, den die App
                              schuldet und nicht hat.
  spec-luecke  (optimierung)  Station wurde erreicht, steht in keiner Spec —
                              der Klickdummy hinkt der App hinterher (R5).

**Grenze, ausdruecklich:** „nie erreicht" heisst „in DIESER Kette nicht
erreicht". Ein Screen, der zu einer anderen Kette gehoert, erscheint hier als
`weg-fehlt`, obwohl er einen Weg hat. Deshalb `--kette-deckt`, mit dem der Lauf
angibt, welche `flow_anchor` seine Kette ueberhaupt abdeckt; alles ausserhalb
wird nicht beurteilt statt falsch beurteilt.

## Unterbefehl `marker` (K8)

Prueft die inhaltliche Durchgaengigkeit (E11): ein Eigenname aus Station 1 muss
in jeder Folgestation wieder auftauchen.

  marker-riss      (fehler)   Marker in Station 1 vorhanden, spaeter weg.
  kontrollmarker   (Abbruch)  Der Kontrollmarker MUSS ueberall 0 ergeben. Tut
                              er es nicht, misst der Suchlauf nicht das, was er
                              zu messen vorgibt — dann ist das Ergebnis der
                              anderen Marker wertlos, nicht nur dieser Fund.

Ohne den Kontrollmarker waere ein Suchlauf, der **nie** etwas findet, von einem
Suchlauf, der **nichts zu finden hat**, nicht zu unterscheiden.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

# Ein Marker, den kein Text der Welt zufaellig enthaelt, und der trotzdem wie ein
# Eigenname aussieht (R6: `ZZZ-TEST` wuerde die Erzeugung verzerren).
KONTROLLMARKER = "Quirinus Vandelaar"


_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def _grundform(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def varianten(text: str) -> set[str]:
    """Zwei Schreibweisen desselben Titels, die beide im Bestand vorkommen:
    'Entwürfe' steht so im Browser, 'Entwuerfe' in unserer eigenen Prosa
    (die Repos schreiben Umlaute durchgaengig aus). Wer nur Diakritika
    abstreift, bekommt 'entwurfe' und trifft keins von beiden."""
    t = (text or "").lower()
    ausgeschrieben = _grundform(t.translate(_UMLAUTE))
    ohne_diakritika = _grundform(
        "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    )
    return {v for v in (ausgeschrieben, ohne_diakritika) if v}


def normalisieren(text: str) -> str:
    """Eine der Varianten — fuer Ausgaben und Mengen, wo eine Form reicht."""
    v = varianten(text)
    return sorted(v)[0] if v else ""


# ── K7: KD-Gegencheck ──────────────────────────────────────────────────────


def lade_spec(pfad: Path) -> list[dict]:
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    screens = daten.get("screens")
    if not isinstance(screens, list):
        raise ValueError(f"{pfad}: kein 'screens'-Block (Liste) gefunden")
    return screens


def kd_gegencheck(
    screens: list[dict], stationen: list[dict], kette_deckt: list[str] | None
) -> dict:
    """Gibt Befunde und die Zaehlwerte zurueck, gegen die K7 geprueft wird."""
    besucht_ids = {s.get("id") for s in stationen if s.get("id")}
    besucht_titel: set[str] = set()
    for s in stationen:
        besucht_titel |= varianten(s.get("titel", ""))
    besucht_titel.discard("")

    weg_fehlt, spec_luecke, nicht_beurteilt = [], [], []
    spec_ids, spec_titel = set(), set()

    for sc in screens:
        sid = sc.get("id")
        titel = sc.get("title", "")
        spec_ids.add(sid)
        spec_titel |= varianten(titel)

        if kette_deckt and sc.get("flow_anchor") not in kette_deckt:
            nicht_beurteilt.append(
                {"id": sid, "titel": titel, "grund": f"flow_anchor {sc.get('flow_anchor')!r} ausserhalb der Kette"}
            )
            continue
        if sc.get("routing_mode") != "live":
            nicht_beurteilt.append(
                {"id": sid, "titel": titel, "grund": f"routing_mode {sc.get('routing_mode')!r}, kein Live-Weg geschuldet"}
            )
            continue
        if sid in besucht_ids or (varianten(titel) & besucht_titel):
            continue
        weg_fehlt.append({"klasse": "weg-fehlt", "schwere": "fehler", "id": sid, "titel": titel})

    for st in stationen:
        if st.get("id") in spec_ids:
            continue
        if varianten(st.get("titel", "")) & spec_titel:
            continue
        spec_luecke.append(
            {"klasse": "spec-luecke", "schwere": "optimierung", "id": st.get("id"), "titel": st.get("titel")}
        )

    return {
        "screens_gesamt": len(screens),
        "stationen_besucht": len(stationen),
        "beurteilt": len(screens) - len(nicht_beurteilt),
        "weg_fehlt": weg_fehlt,
        "spec_luecke": spec_luecke,
        "nicht_beurteilt": nicht_beurteilt,
    }


# ── K8: Marker-Durchgaengigkeit ────────────────────────────────────────────


def marker_check(stationen: list[dict], marker: list[str]) -> dict:
    """stationen: [{'titel': …, 'text': …}, …] in Reihenfolge des Durchlaufs."""
    if not stationen:
        raise ValueError("keine Stationen — ohne Text kann nichts gesucht werden")

    def enthalten(text: str, m: str) -> bool:
        tv = varianten(text)
        return any(any(mv in t for t in tv) for mv in varianten(m))

    kontroll_treffer = [
        {"station": s.get("titel"), "marker": KONTROLLMARKER}
        for s in stationen
        if enthalten(s.get("text", ""), KONTROLLMARKER)
    ]

    risse, verlauf = [], {}
    for m in marker:
        gefunden = [enthalten(s.get("text", ""), m) for s in stationen]
        verlauf[m] = gefunden
        if not gefunden[0]:
            risse.append(
                {
                    "klasse": "marker-nie-gesetzt",
                    "schwere": "fehler",
                    "marker": m,
                    "station": stationen[0].get("titel"),
                    "hinweis": "Marker fehlt schon in Station 1 — er wurde nie eingegeben oder nicht gespeichert",
                }
            )
            continue
        for s, ok in zip(stationen[1:], gefunden[1:]):
            if not ok:
                risse.append(
                    {"klasse": "marker-riss", "schwere": "fehler", "marker": m, "station": s.get("titel")}
                )
                break

    return {
        "stationen": len(stationen),
        "marker": marker,
        "verlauf": verlauf,
        "risse": risse,
        "kontrollmarker": KONTROLLMARKER,
        "kontroll_treffer": kontroll_treffer,
        "messung_gueltig": not kontroll_treffer,
    }


# ── CLI ────────────────────────────────────────────────────────────────────


def _lade_json(pfad: str) -> list[dict]:
    daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    if not isinstance(daten, list):
        raise ValueError(f"{pfad}: erwartet wird eine Liste von Stationen")
    return daten


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="befehl", required=True)

    k = sub.add_parser("kd", help="K7: Klickdummy-Spec gegen besuchte Stationen")
    k.add_argument("--spec", required=True, help="Pfad zu klickdummy/<name>/spec.yaml")
    k.add_argument("--stationen", required=True, help="JSON: [{'id':…,'titel':…}, …]")
    k.add_argument("--kette-deckt", default="", help="Kommaliste der flow_anchor, die die Kette abdeckt")

    m = sub.add_parser("marker", help="K8: Durchgaengigkeit der Marker + Kontrollmarker")
    m.add_argument("--stationen", required=True, help="JSON: [{'titel':…,'text':…}, …] in Laufreihenfolge")
    m.add_argument("--marker", required=True, help="Kommaliste der Eigennamen aus Station 1")

    a = p.parse_args()

    try:
        if a.befehl == "kd":
            deckt = [x.strip() for x in a.kette_deckt.split(",") if x.strip()] or None
            e = kd_gegencheck(lade_spec(Path(a.spec)), _lade_json(a.stationen), deckt)
            print(f"KD-Gegencheck: {e['screens_gesamt']} Screens, {e['beurteilt']} beurteilt, "
                  f"{e['stationen_besucht']} Stationen besucht")
            for b in e["weg_fehlt"]:
                print(f"  ❌ weg-fehlt (fehler)      {b['id']}: {b['titel']}")
            for b in e["spec_luecke"]:
                print(f"  ⚠ spec-luecke (optimierung) {b['id']}: {b['titel']}")
            for b in e["nicht_beurteilt"]:
                print(f"  · nicht beurteilt          {b['id']}: {b['grund']}")
            if e["beurteilt"] == 0:
                print("\nFEHLER: kein einziger Screen wurde beurteilt — der Filter frisst die Spec.", file=sys.stderr)
                return 2
            print(f"\nErgebnis: {len(e['weg_fehlt'])} weg-fehlt, {len(e['spec_luecke'])} spec-luecke")
            return 1 if e["weg_fehlt"] else 0

        e = marker_check(_lade_json(a.stationen), [x.strip() for x in a.marker.split(",") if x.strip()])
        print(f"Marker-Durchgaengigkeit ueber {e['stationen']} Stationen")
        for mk, verlauf in e["verlauf"].items():
            print(f"  {mk}: {''.join('x' if v else '.' for v in verlauf)}")
        if not e["messung_gueltig"]:
            print(f"\nFEHLER: der Kontrollmarker {e['kontrollmarker']!r} wurde gefunden — "
                  f"in {len(e['kontroll_treffer'])} Station(en). Der Suchlauf misst nicht, was er zu "
                  f"messen vorgibt; die Ergebnisse der anderen Marker sind damit wertlos.", file=sys.stderr)
            return 2
        print(f"  Kontrollmarker {e['kontrollmarker']!r}: 0 Treffer ✅ (die Messung ist gueltig)")
        for r in e["risse"]:
            print(f"  ❌ {r['klasse']} (fehler)  {r['marker']} reisst bei: {r['station']}")
        print(f"\nErgebnis: {len(e['risse'])} Riss(e)")
        return 1 if e["risse"] else 0

    except (ValueError, FileNotFoundError, yaml.YAMLError) as fehler:
        print(f"FEHLER: {fehler}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
