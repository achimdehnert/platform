#!/usr/bin/env python3
"""Rausch-Kandidaten aus 30 Tagen Index vorschlagen (V7, platform#3015 K4).

**Warum es das gibt.** Ein Blick auf zwei Tage Index zeigte 40 von 50 Treffern
als Werbung/Newsletter — aber die vom Owner bestätigten Rauschregeln im Ledger
(`rausch_regeln`) kannten die Absender nicht, weil noch nie jemand nachgesehen
hat, welche Adressen regelmäßig auftauchen, ohne je einen Vorgang auszulösen.
Dieses Werkzeug schlägt neue Absender-Regeln zur **Einmal-Bestätigung** vor —
es verschiebt, löscht und schreibt NICHTS. Der Ledger bleibt read-only.

**Kandidat** ist eine Absenderadresse mit mindestens drei Treffern im
30-Tage-Fenster, die
  (a) in keiner bestehenden Rauschregel steht (Adresse ODER Domain),
  (b) in keinem offenen Vorgang vorkommt (Vergleich gegen `gegenueber`,
      `thread_key`, `notiz` — Domain-Treffer zählen dabei nur, wenn die
      Domain nicht zu den drei eigenen Konten gehört; sonst würde jede
      Signatur im Vorgangstext jeden Absender aus derselben Firma decken),
  (c) nur in Posteingangs-Ordnern liegt (Gesendet/Entwürfe zählen nicht —
      eine dort einsortierte Nachricht sagt nichts über eingehendes Rauschen).

**Vorgeschlagene Regelform.** `rausch_regeln` selbst ist im Ledger heute kein
einheitliches Objekt-Schema (Freitext-Kampagnen neben reinen Adresslisten wie
`nach_ordner_zur_loeschung`) — dieses Werkzeug führt darum ein knappes,
dokumentiertes Feldset ein (`absender`, `typ`, `ziel`, `treffer_30_tage`,
`vorschlag_stichtag`, `quelle`), das der Owner nach Prüfung 1:1 in
`rausch_regeln` übernehmen kann, statt Freitext von Hand nachzubauen.

Zielordner ist ausnahmslos "Zur Loeschung" (seit 2026-08-07 der einzige
Zielordner für Rauschregeln, siehe `_hinweis` in `rausch_regeln`).

Aufruf::

    python3 tools/mail_agent/rausch_kandidaten.py
    python3 tools/mail_agent/rausch_kandidaten.py --stichtag 2026-09-13 --json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
HIER = Path(__file__).resolve().parent

#: 30-Tage-Fenster (Owner-Beobachtung: 40/50 Treffer in zwei Tagen waren Rauschen).
FENSTER_TAGE = 30

#: Ab wie vielen Treffern im Fenster ein Absender ein Kandidat ist.
SCHWELLE_TREFFER = 3

#: Der seit 2026-08-07 einzige Zielordner für Rauschregeln (`rausch_regeln._hinweis`).
ZIELORDNER = "Zur Loeschung"

#: Domains der drei eigenen Konten (bereits unredigiert im Repo: mail_wache.py
#: IIL_KONTO_HINWEIS "iil.gmbh", suche.py-Docstring "--von offner@hnu.de",
#: referenzpostfach.py-Fixture "search@dehnert.team" für das dritte/AD-Konto).
#: Ohne diese Ausnahme würde jede Signatur in einem Vorgangstext jeden
#: Absender derselben Firma faelschlich als "schon im Vorgang" decken.
EIGENE_DOMAENEN = ("iil.gmbh", "hnu.de", "dehnert.team")

#: Ordnernamen, die als Posteingang zaehlen (IIL/Graph, HNU/Mittwald-IMAP).
POSTEINGANG_PRAEFIXE = ("inbox", "posteingang")

#: Ordner-Teilstrings, die eine Nachricht von der Zaehlung ausschliessen —
#: Gesendet/Entwuerfe sagen nichts ueber eingehendes Rauschen aus.
AUSGESCHLOSSENE_ORDNER_TEILE = ("esendet", "ntwürfe", "ntwuerfe", "draft")


@dataclass
class Kandidat:
    absender: str
    treffer: int
    beispiel_betreffs: list[str] = field(default_factory=list)


def treffer_laden(seit: str, bis: str | None = None, limit: int = 3000) -> list[dict]:
    """Mail-Index fuer das Fenster abfragen — injizierbar, damit Tests eine
    Fake-Liste uebergeben koennen, statt SSH+Django zu brauchen."""
    argv = [
        sys.executable,
        str(HIER / "suche.py"),
        "--seit",
        seit,
        "--limit",
        str(limit),
        "--json",
    ]
    if bis:
        argv += ["--bis", bis]
    lauf = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    if lauf.returncode != 0:
        raise RuntimeError(f"Mail-Index nicht erreichbar: {lauf.stderr[:200]}")
    daten = json.loads(lauf.stdout)
    return daten.get("treffer", [])


def ledger_laden(pfad: Path | None = None) -> dict:
    """Den Ledger LESEN — dieses Werkzeug schreibt ihn nie."""
    p = pfad or LEDGER
    return json.loads(p.read_text(encoding="utf-8"))


def _domain_von(adresse: str) -> str:
    return adresse.rsplit("@", 1)[-1]


def ist_posteingang_treffer(treffer: dict) -> bool:
    """Nur Treffer aus Posteingangs-Ordnern zaehlen (nicht Gesendet/Entwuerfe)."""
    ordner = treffer.get("ordner") or []
    if any(any(teil in o.lower() for teil in AUSGESCHLOSSENE_ORDNER_TEILE) for o in ordner):
        return False
    return any(
        o.strip().lower() == praefix or o.strip().lower().startswith(praefix + "/")
        for o in ordner
        for praefix in POSTEINGANG_PRAEFIXE
    )


def _rausch_regeln_corpus(rausch_regeln: dict) -> str:
    """Der ganze `rausch_regeln`-Baum als ein durchsuchbarer Text.

    `rausch_regeln` ist heute kein einheitliches Schema (Freitext-Kampagnen
    neben reinen Adresslisten) — ein Substring-Vergleich ueber den gesamten
    JSON-Text findet Adresse/Domain unabhaengig davon, in welcher der
    verschiedenen Formen sie gerade steht.
    """
    return json.dumps(rausch_regeln, ensure_ascii=False).lower()


def _vorgang_corpus(vorgang: dict) -> str:
    teile = [str(vorgang.get(feld) or "") for feld in ("gegenueber", "thread_key", "notiz")]
    return " ".join(teile).lower()


def _bereits_erfasst(
    adresse: str,
    domain: str,
    rausch_corpus: str,
    vorgaenge: list[dict],
) -> bool:
    if adresse in rausch_corpus or domain in rausch_corpus:
        return True
    for v in vorgaenge:
        corpus = _vorgang_corpus(v)
        if adresse in corpus:
            return True
        if domain not in EIGENE_DOMAENEN and domain in corpus:
            return True
    return False


def kandidaten_ermitteln(
    treffer: list[dict],
    rausch_regeln: dict,
    vorgaenge: list[dict],
    schwelle: int = SCHWELLE_TREFFER,
) -> list[Kandidat]:
    """Reine Logik, ohne I/O — testbar mit synthetischen Fixtures."""
    gruppen: dict[str, list[dict]] = {}
    for t in treffer:
        if not ist_posteingang_treffer(t):
            continue
        adresse = (t.get("von") or "").strip().lower()
        if "@" not in adresse:
            continue
        gruppen.setdefault(adresse, []).append(t)

    rausch_corpus = _rausch_regeln_corpus(rausch_regeln)

    kandidaten: list[Kandidat] = []
    for adresse, treffer_liste in sorted(gruppen.items()):
        if len(treffer_liste) < schwelle:
            continue
        domain = _domain_von(adresse)
        if _bereits_erfasst(adresse, domain, rausch_corpus, vorgaenge):
            continue
        geordnet = sorted(treffer_liste, key=lambda t: t.get("datum") or "", reverse=True)
        betreffs = [t.get("betreff") or "" for t in geordnet[:2]]
        kandidaten.append(
            Kandidat(absender=adresse, treffer=len(treffer_liste), beispiel_betreffs=betreffs)
        )
    kandidaten.sort(key=lambda k: k.treffer, reverse=True)
    return kandidaten


def regel_vorschlag(kandidat: Kandidat, stichtag: str) -> dict:
    """Die fertige Regel in der Form, die `rausch_regeln` nach Bestätigung erwartet."""
    return {
        "absender": kandidat.absender,
        "typ": "adresse",
        "ziel": ZIELORDNER,
        "treffer_30_tage": kandidat.treffer,
        "vorschlag_stichtag": stichtag,
        "quelle": "rausch_kandidaten.py (V7) — Owner-Bestaetigung ausstehend",
    }


def _tabelle(kandidaten: list[Kandidat]) -> str:
    if not kandidaten:
        return "Keine Rausch-Kandidaten im Fenster."
    zeilen = ["Absender | Treffer | Beispiel-Betreffs (2) | Vorschlag", "---|---|---|---"]
    for k in kandidaten:
        beispiele = " / ".join(b[:60] for b in k.beispiel_betreffs) or "(kein Betreff)"
        zeilen.append(f"{k.absender} | {k.treffer} | {beispiele} | {ZIELORDNER}")
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--stichtag",
        default=date.today().isoformat(),
        help="Fenster-Ende YYYY-MM-DD, fuer reproduzierbare Laeufe (Default: heute)",
    )
    p.add_argument("--limit", type=int, default=3000)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    stichtag = date.fromisoformat(args.stichtag)
    seit = (stichtag - timedelta(days=FENSTER_TAGE)).isoformat()

    treffer = treffer_laden(seit, bis=args.stichtag, limit=args.limit)
    ledger = ledger_laden()
    rausch_regeln = ledger.get("rausch_regeln", {})
    vorgaenge = ledger.get("vorgaenge", [])

    kandidaten = kandidaten_ermitteln(treffer, rausch_regeln, vorgaenge)

    if args.json:
        ausgabe = {
            "stichtag": args.stichtag,
            "seit": seit,
            "kandidaten": [
                {
                    "absender": k.absender,
                    "treffer": k.treffer,
                    "beispiel_betreffs": k.beispiel_betreffs,
                    "regel": regel_vorschlag(k, args.stichtag),
                }
                for k in kandidaten
            ],
        }
        print(json.dumps(ausgabe, ensure_ascii=False, indent=2))
        return 0

    print(f"Rausch-Kandidaten {seit} .. {args.stichtag} (Fenster {FENSTER_TAGE} Tage)\n")
    print(_tabelle(kandidaten))
    if kandidaten:
        print("\nVorschlaege als Regel-Zeile (rausch_regeln-Form):\n")
        for k in kandidaten:
            print(json.dumps(regel_vorschlag(k, args.stichtag), ensure_ascii=False))
        print(
            "\nBestätigen: Zeile in rausch_regeln übernehmen (Owner-Wort) — "
            "dieses Werkzeug schreibt den Ledger nicht selbst."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
