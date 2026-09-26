#!/usr/bin/env python3
"""Beleg-Pruefung und Fragetext fuer das Technologiescreening (KONZ-063 Stufe 1).

Die platform-Seite der Entscheidung D4: **billig sammelt, teuer waehlt aus** —
und dazwischen steht diese Datei als mechanisches Sieb, das ohne Modell
auskommt.

Gemessen am 2026-09-22 ueber ein Fenster der Morgen-Zeitung (Protokoll in
platform#3383): das guenstige Modell allein nimmt naiv Hardware-Buendel und
Desktop-Apps als „Technologie" (rund fuenf Fehltreffer von 17); streng
eingegrenzt verliert es die drei wertvollsten Kandidaten und **erfindet eine
Begruendung** (Astra als „klinische Anwendung" — stammt aus einer anderen
Schlagzeile). Eine zweite billige Meinung strich 0 von 8 und kostete 1.193
Tokens.

Was half, war kein besseres Modell, sondern ein Zwang: jeder Kandidat muss die
Schlagzeile **woertlich zitieren**, und ein Zeichenkettenvergleich prueft das.
Danach: 8 von 8 Zitaten auffindbar, 0 erfunden, und die Einordnung in
`kompetenz`/`portfolio` erholte sich von 8:0 auf 4:4. Dieselbe Beleg-Pflicht,
die ADR-299 Paragraf 4.2 dem Tageslauf auferlegt — hier auf das Urteil
angewandt.

**Die Pruefung ist einseitig und hat eine Mindestlaenge.** Die zuerst benutzte
Fassung verglich in beide Richtungen (`Zitat in Zeile ODER Zeile in Zitat`) und
liess damit jedes Kurzwort durch: „AI" und „Astra" sind Teilzeichenkette
irgendeiner Schlagzeile. In der Positivkontrolle fiel sie bei 2 von 8 Proben um
(`tools/tests/test_screening_beleg.py`), die verschaerfte Fassung bei 0.

**Was diese Datei NICHT tut: auswaehlen.** Die Reihenfolge der Kandidaten kommt
herein und geht unveraendert hinaus; `--max` schneidet nur ab. Das Auswaehlen
ist der teure Schritt aus D4 und passiert in der Briefing-Lane, die werktags
ohnehin laeuft — wer hier eine Rangfolge einbaute, haette den teuren Schritt
still durch den guenstigen ersetzt.

Echter Lauf am 2026-09-23 ueber das Fenster 09-15…09-21: das T1a-Modell lieferte
8 Kandidaten, alle Belege hielten, die erste Frage lautete „14,7 MB-Modell —
koennten wir anbieten" mit der Schlagzeile als Beleg.

    screening_beleg.py --kandidaten k.json --korpus korpus.tsv
    screening_beleg.py --kandidaten k.json --korpus korpus.tsv --json
    screening_beleg.py --kandidaten k.json --korpus korpus.tsv --max 1

Exit 0 = mindestens ein Kandidat haelt · 1 = keiner haelt (dann bleibt die
Morgen-Meldung zu diesem Thema stumm, REC-22) · 2 = Eingabe unbrauchbar.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

#: Kuerzestes Zitat, das noch als Beleg zaehlt (normalisierte Zeichen). Unter
#: dieser Grenze ist ein „Zitat" nur noch ein Wort und trifft zufaellig.
MINDEST_BELEG = 25

#: Hoechstens so viele Fragen je Meldung. Das Aufmerksamkeitsbudget teilt sich
#: die Technologie-Frage mit den Befund-Fragen aus `chat_agent/vorschlaege.py`
#: (dort `MAX_FRAGEN = 3`); sie rangiert hinter ihnen, deshalb hier 1.
MAX_FRAGEN = 1

#: Erlaubte Toepfe. „offen" ist zugelassen, weil eine falsche Einordnung den
#: Owner einen Satz kostet, eine erzwungene Einordnung dagegen eine Erfindung.
TOEPFE = ("kompetenz", "portfolio", "offen")

#: Was der Daumen tut — woertlich, weil dieselbe Geste sonst „zur Kenntnis" und
#: „bau das" nicht unterscheidet (KONZ-063 REC-7).
DAUMEN_SATZ = "Daumen hoch = ich lege ein Issue an, mehr nicht."


def _lade_backtest() -> Any:
    """`screening_backtest` aus demselben Verzeichnis laden.

    Der Korpus-Leser lebt dort und bleibt dort: zwei Leser fuer dasselbe
    TSV-Format waeren zwei Wahrheiten ueber das Format.
    """
    pfad = Path(__file__).resolve().parent / "screening_backtest.py"
    spec = importlib.util.spec_from_file_location("screening_backtest", pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("screening_backtest", modul)
    spec.loader.exec_module(modul)
    return modul


def norm(text: str) -> str:
    """Vergleichsform: Unicode vereinheitlicht, nur Wortzeichen, ein Leerzeichen.

    Die Titel tragen Unicode-Striche und typografische Anfuehrungszeichen, die
    das Modell beim Zitieren nicht zuverlaessig reproduziert. Ohne diese
    Normalisierung scheitert ein korrektes Zitat an einem Bindestrich.
    """
    gefaltet = unicodedata.normalize("NFKC", text).lower()
    return " ".join(re.sub(r"[^a-z0-9äöüß ]+", " ", gefaltet).split())


def beleg_gilt(beleg: str, stoff: list[str], mindest: int = MINDEST_BELEG) -> bool:
    """Steht dieses Zitat so im Eingabestoff?

    Einseitig: das Zitat muss in einer Zeile vorkommen — nicht umgekehrt.
    """
    n = norm(beleg)
    if len(n) < mindest:
        return False
    return any(n in zeile for zeile in stoff)


def stoff_aus_korpus(pfad: str) -> list[str]:
    zeilen = _lade_backtest().korpus_lesen(pfad)
    return [norm(titel) for _, _, titel in zeilen]


def pruefe(
    kandidaten: list[dict], stoff: list[str], mindest: int = MINDEST_BELEG
) -> tuple[list[dict], list[dict]]:
    """Trennt Kandidaten mit auffindbarem Zitat von den uebrigen.

    Verworfen wird mit Grund — nichts verschwindet stillschweigend, wie schon
    bei der Themen-Bewertung der Zeitung (ADR-299 Paragraf 4.2).
    """
    behalten: list[dict] = []
    verworfen: list[dict] = []
    gesehen: set[str] = set()

    for k in kandidaten:
        name = (k.get("name") or "").strip()
        beleg = (k.get("beleg") or "").strip()
        if not name:
            verworfen.append({**k, "grund": "ohne Namen"})
            continue
        if norm(name) in gesehen:
            verworfen.append({**k, "grund": "Dublette"})
            continue
        if not beleg:
            verworfen.append({**k, "grund": "kein Beleg angegeben"})
            continue
        if not beleg_gilt(beleg, stoff, mindest):
            verworfen.append({**k, "grund": "Beleg nicht im Stoff auffindbar"})
            continue
        gesehen.add(norm(name))
        topf = k.get("topf") if k.get("topf") in TOEPFE else "offen"
        behalten.append({**k, "topf": topf})

    return behalten, verworfen


def frage_text(behalten: list[dict], max_fragen: int = MAX_FRAGEN) -> str:
    """Der Text fuer die Morgen-Meldung — leer, wenn nichts haelt.

    Eine Woche ohne Substanz schweigt (KONZ-063 REC-22): lieber keine Meldung
    als die drei besten Ankuendigungen. Der aufrufende Lauf haengt einen leeren
    Text nicht an.
    """
    if not behalten:
        return ""

    zeilen = ["Aus der Morgen-Zeitung ist mir etwas aufgefallen:"]
    for nr, k in enumerate(behalten[:max_fragen], start=1):
        topf = {
            "kompetenz": "koennte unsere Agenten besser machen",
            "portfolio": "koennten wir anbieten",
            "offen": "Einordnung unklar",
        }[k["topf"]]
        zeilen.append(
            "%d. %s — %s. %s" % (nr, k["name"], topf, (k.get("warum") or "").strip())
        )
        zeilen.append("   Beleg: %s" % k["beleg"].strip())
    zeilen.append(DAUMEN_SATZ)
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--kandidaten", required=True, help='JSON: {"kandidaten": [...]}')
    p.add_argument("--korpus", required=True, help="TSV wie in screening_backtest.py")
    p.add_argument("--max", type=int, default=MAX_FRAGEN)
    p.add_argument("--mindest-beleg", type=int, default=MINDEST_BELEG)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    try:
        roh = json.loads(Path(a.kandidaten).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print("Kandidaten nicht lesbar: %s" % exc, file=sys.stderr)
        return 2

    kandidaten = roh.get("kandidaten") if isinstance(roh, dict) else roh
    if not isinstance(kandidaten, list):
        print("Kandidaten-Datei enthaelt keine Liste.", file=sys.stderr)
        return 2

    stoff = stoff_aus_korpus(a.korpus)
    if not stoff:
        print("Korpus ist leer — ohne Stoff ist kein Beleg pruefbar.", file=sys.stderr)
        return 2

    behalten, verworfen = pruefe(kandidaten, stoff, a.mindest_beleg)

    if a.json:
        print(
            json.dumps(
                {
                    "behalten": behalten,
                    "verworfen": verworfen,
                    "frage": frage_text(behalten, a.max),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for k in verworfen:
            print(
                "verworfen: %s — %s" % (k.get("name") or "(ohne Namen)", k["grund"]),
                file=sys.stderr,
            )
        text = frage_text(behalten, a.max)
        if text:
            print(text)

    return 0 if behalten else 1


if __name__ == "__main__":
    raise SystemExit(main())
