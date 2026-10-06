#!/usr/bin/env python3
"""Rueckrechnung fuer das Technologiescreening (KONZ-platform-063, Stufe 0).

Bevor in news-hub eine Zeile Produktionscode entsteht, beantwortet dieses
Kommando die einzige Frage, die ueber den Bau entscheidet: **was haette eine
Aufsteiger-Regel in den letzten Wochen tatsaechlich geliefert?**

Es schreibt nichts, ruft kein Modell und braucht keinen Datenbankzugang. Es
liest einen Auszug aus der news-hub-Datenbank als TSV — drei Spalten, durch Tab
getrennt:

    T<TAB>2026-09-21<TAB>Two New OCR Models Land on Hugging Face
    Q<TAB>2026-09-21<TAB>Self-Evolving Search Index for RAG Agents

`T` ist ein Thema-Titel, `Q` der Titel einer externen Quelle; die zweite Spalte
ist `Lauf.bis`. Den Auszug erzeugt auf dem Prod-Host:

    docker exec news_hub_web python manage.py shell -c "
    from apps.digest.models import Thema, Quelle
    for t in Thema.objects.select_related('lauf').order_by('lauf__bis','id'):
        print('T\\t%s\\t%s' % (t.lauf.bis, t.titel))
    for q in Quelle.objects.filter(art='extern').select_related('thema__lauf').order_by('id'):
        print('Q\\t%s\\t%s' % (q.thema.lauf.bis, q.titel))
    "

Zwei Regeln werden gerechnet:

* **Variante A (Aufsteiger):** ein Name, der im Fenster an mindestens
  `--mindest-tage` verschiedenen Tagen vorkommt und in den `--basis-tage` davor
  an keinem.
* **Variante B (Erst-Nennung):** ein Name, dessen allererstes Vorkommen im
  ganzen Korpus in dieses Fenster faellt.

Gezaehlt wird je **Tag**, nie je Lauf. Am 2026-09-22 lagen 31 Laeufe an 14
Kalendertagen vor (Nachlaeufe desselben Tages) — eine Schwelle „zwei Nennungen"
waere sonst von zwei Laeufen desselben Tages allein erfuellt worden.

Gemessenes Ergebnis beim ersten Lauf (2026-09-22, Korpus 464 Zeilen ueber 10
Tage mit Inhalt, 307 Namenskandidaten):

* Variante A, Fenster 09-15…09-21: **2 Treffer** — `GPT-6 Astra` (brauchbar)
  und `Sequence Radar Issue Last` (Newsletter-Fliesstext, Fehltreffer).
* Variante B: 196 Erst-Nennungen, davon 2 an mindestens zwei Tagen.

Das reisst die Schwelle aus KONZ-063 §13 (mindestens drei brauchbare Namen je
Woche, hoechstens ein Fehltreffer) deutlich. Genau dafuer gibt es diese Stufe:
die naheliegende Regel ist widerlegt, bevor sie gebaut wurde.

    screening_backtest.py korpus.tsv                  # letztes 7-Tage-Fenster
    screening_backtest.py korpus.tsv --alle-fenster   # jede Woche einzeln
    screening_backtest.py korpus.tsv --json           # maschinenlesbar
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date, timedelta

#: Woerter, die gross geschrieben mitten im Titel stehen, aber keine
#: Technologie bezeichnen. Handgepflegt und mit Grund — dieselbe Entscheidung
#: wie bei den Stopwortlisten der Themenbildung in news-hub: die Liste muss
#: lesbar bleiben, weil sie mitbestimmt, was als Kandidat durchkommt.
KEIN_NAME = frozenset(
    """
    Der Die Das Ein Eine Wie Was Warum Wer Wo Und Oder Aber Mit Ohne Fuer Für
    Von Vom Zum Zur Bei Im In Am An Auf Aus Nach Ueber Über Neue Neuer Neues Neu
    The A An How Why What When Where This That These Those And Or But With
    Without For From To On At By New Two Three First Best Top More Most Your
    You Our We Are Here Try Arrives Land Lands Build Building Learn Survives
    Towards Center Week Hours Seven Game Campus Stack Video Valuation Synthetic
    Modelle Modell Models Model Tools Tool Data Daten Agents Agent Search Index
    Long Self Time Live Open Source Prompt Prompts Interface Policy Small Gute
    Frontier General Test Tests Update Real Decision Encoder Workflow
    KI AI GenAI LLM LLMs Coding Research Desktop Work Arena Collection Fall
    Bundles Superpowers Custom Connectors Audit Logs
    Vergleich Entwicklung Verlangsamung Ergebnisse Beispiel Alternative Platz
    Kosten Kleines Kleiner Sensible Lokal Viral Wettbewerbsvorteil
    """.split()
)

#: Ein Wort im Titel: Buchstabe am Anfang, danach Wortzeichen, Binde- und
#: Punktzeichen (`GPT-6`, `v0`, `Mistral's`). Unicode-Bindestriche kommen in den
#: Titeln vor, weil das Modell sie setzt.
#: Der Bereich U+2010 bis U+2015 (Bindestrich bis Geviertstrich) steht hier als
#: Codepunkte statt als Zeichen — die sechs Striche sind im Editor nicht
#: voneinander zu unterscheiden, und `Grok Imagine Image 2.0` traegt einen davon.
STRICHE = "%c-%c" % (0x2010, 0x2015)
WORT = re.compile(r"[A-Za-zÄÖÜäöüß][\w" + STRICHE + r".\-']*")

MINDEST_LAENGE = 3


def namen(titel: str) -> list[str]:
    """Namenskandidaten eines Titels — zusammenhaengende Grossschreibung.

    Das erste Wort zaehlt nie: jeder Titel beginnt gross, und ein Satzanfang
    sagt nichts ueber einen Eigennamen. Ein Wort mit Ziffer (`GPT-6`, `Z1T`)
    zaehlt auch klein geschrieben, weil Produktnamen so aussehen.
    """
    text = unicodedata.normalize("NFKC", titel)
    kette: list[str] = []
    gefunden: list[str] = []
    for i, wort in enumerate(WORT.findall(text)):
        kern = wort.strip(".,;:!?'")
        passt = (
            i > 0
            and len(kern) > MINDEST_LAENGE - 1
            and kern not in KEIN_NAME
            and (kern[:1].isupper() or any(z.isdigit() for z in kern))
        )
        if passt:
            kette.append(kern)
        elif kette:
            gefunden.append(" ".join(kette))
            kette = []
    if kette:
        gefunden.append(" ".join(kette))
    return gefunden


def korpus_lesen(pfad: str) -> list[tuple[str, date, str]]:
    zeilen = []
    quelle = sys.stdin if pfad == "-" else open(pfad, encoding="utf-8")
    with quelle as datei:
        for roh in datei:
            teile = roh.rstrip("\n").split("\t")
            if len(teile) < 3 or teile[0] not in ("T", "Q"):
                continue
            try:
                tag = date.fromisoformat(teile[1])
            except ValueError:
                continue
            if teile[2].strip():
                zeilen.append((teile[0], tag, teile[2]))
    return zeilen


def nennungen(zeilen) -> dict[str, set[date]]:
    """Name -> Menge der TAGE, an denen er vorkam (nie: Zahl der Laeufe)."""
    tage: dict[str, set[date]] = defaultdict(set)
    for _, tag, titel in zeilen:
        for name in namen(titel):
            tage[name].add(tag)
    return tage


def fenster_auswerten(
    tage: dict[str, set[date]], ende: date, breite: int, basis: int, mindest: int
) -> dict:
    start = ende - timedelta(days=breite - 1)
    basis_start = start - timedelta(days=basis)
    erst = {name: min(ts) for name, ts in tage.items()}

    aufsteiger, erstnennungen = [], []
    for name, ts in tage.items():
        im_fenster = [t for t in ts if start <= t <= ende]
        davor = [t for t in ts if basis_start <= t < start]
        if len(im_fenster) >= mindest and not davor:
            aufsteiger.append({"name": name, "tage": len(im_fenster)})
        if start <= erst[name] <= ende:
            erstnennungen.append({"name": name, "tage": len(ts)})

    aufsteiger.sort(key=lambda e: (-e["tage"], e["name"]))
    erstnennungen.sort(key=lambda e: (-e["tage"], e["name"]))
    return {
        "von": start.isoformat(),
        "bis": ende.isoformat(),
        "variante_a": aufsteiger,
        "variante_b": erstnennungen,
    }


def als_text(bericht: dict) -> str:
    zeilen = [
        "Korpus: %d Zeilen, %d Tage mit Inhalt (%s .. %s), %d Namenskandidaten"
        % (
            bericht["zeilen"],
            bericht["tage"],
            bericht["erster_tag"],
            bericht["letzter_tag"],
            bericht["kandidaten"],
        )
    ]
    for f in bericht["fenster"]:
        zeilen.append("")
        zeilen.append("Fenster %s .. %s" % (f["von"], f["bis"]))
        zeilen.append("  Variante A (Aufsteiger): %d" % len(f["variante_a"]))
        for e in f["variante_a"]:
            zeilen.append("    %dx %s" % (e["tage"], e["name"]))
        mehrfach = [e for e in f["variante_b"] if e["tage"] > 1]
        zeilen.append(
            "  Variante B (Erst-Nennung): %d, davon %d an mehreren Tagen"
            % (len(f["variante_b"]), len(mehrfach))
        )
        for e in mehrfach[:10]:
            zeilen.append("    %dx %s" % (e["tage"], e["name"]))
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("korpus", help="TSV-Auszug (art<TAB>tag<TAB>titel), '-' fuer stdin")
    p.add_argument("--fenster", type=int, default=7, help="Fensterbreite in Tagen")
    p.add_argument("--basis-tage", type=int, default=21, help="Vorlauf ohne Nennung")
    p.add_argument("--mindest-tage", type=int, default=2, help="Tage im Fenster")
    p.add_argument("--alle-fenster", action="store_true", help="jede Woche einzeln")
    p.add_argument("--json", action="store_true", help="maschinenlesbar")
    a = p.parse_args(argv)

    zeilen = korpus_lesen(a.korpus)
    if not zeilen:
        print("Korpus ist leer — kein Urteil moeglich.", file=sys.stderr)
        return 2

    tage_gesamt = sorted({t for _, t, _ in zeilen})
    tage = nennungen(zeilen)

    enden = [tage_gesamt[-1]]
    if a.alle_fenster:
        enden = sorted({t for t in tage_gesamt})[a.fenster - 1 :: a.fenster] or enden

    bericht = {
        "zeilen": len(zeilen),
        "tage": len(tage_gesamt),
        "erster_tag": tage_gesamt[0].isoformat(),
        "letzter_tag": tage_gesamt[-1].isoformat(),
        "kandidaten": len(tage),
        "fenster": [
            fenster_auswerten(tage, e, a.fenster, a.basis_tage, a.mindest_tage)
            for e in enden
        ],
    }

    print(
        json.dumps(bericht, ensure_ascii=False, indent=2)
        if a.json
        else als_text(bericht)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
