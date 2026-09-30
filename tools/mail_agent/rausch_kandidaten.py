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
      eine dort einsortierte Nachricht sagt nichts über eingehendes Rauschen),
  (d) in keiner Schutzklasse aus ``loeschschutz`` liegt — eigene Adresse,
      Beleg-Betreff/-Anhang in IRGENDEINEM Treffer, Gesendet-Historie
      (platform#3176 K1),
  (e) vom Modell als ``newsletter`` oder ``werbung`` eingeordnet wird und die
      deterministische Plausibilitätsprüfung besteht (K2, siehe unten).

**Warum (d) und (e).** Am 2026-09-13 bestätigte Kandidaten enthielten
Einzelpersonen, Partner, die eigene Adresse und Rechnungsabsender — „häufig
und in keinem Vorgang" trennt Mensch und Maschine nicht. Owner-Wort
2026-09-14: „wenn es komplex wird -> kein grep, regex sondern LLM".

**Modell-Einordnung (K2).** Alle Rest-Kandidaten gehen in EINEM Aufruf an das
Groq-Modell (Muster ``verankerung_pruefer``): Adresse plus bis zu fünf
Betreffe, Klasse ``newsletter | werbung | transaktion | person | partner``.
Danach prüft `plausibel` deterministisch: eine Adresse im Personenmuster
(``vorname.nachname@``) oder unter einer Freemail-Domain bleibt kein
Kandidat, gleich was das Modell sagt. Fehlt der Schlüssel oder scheitert der
Aufruf, wird NICHTS vorgeschlagen (fail-closed) — die Ausgabe sagt, warum.

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
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
HIER = Path(__file__).resolve().parent

sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent))
import loeschschutz  # noqa: E402  (platform#3176 K1)
from verankerung_pruefer import (  # noqa: E402
    GROQ_DEFAULT_MODELL,
    GROQ_ENDPOINT,
    GROQ_KENNUNG,
    _groq_schluessel,
)

#: 30-Tage-Fenster (Owner-Beobachtung: 40/50 Treffer in zwei Tagen waren Rauschen).
FENSTER_TAGE = 30

#: Ab wie vielen Treffern im Fenster ein Absender ein Kandidat ist.
SCHWELLE_TREFFER = 3

#: Der seit 2026-08-07 einzige Zielordner für Rauschregeln (`rausch_regeln._hinweis`).
ZIELORDNER = loeschschutz.ZIELORDNER_LOESCHUNG

#: K2: Klassen der Modell-Einordnung; nur ``RAUSCH_KLASSEN`` bleiben Kandidat.
KLASSEN = ("newsletter", "werbung", "transaktion", "person", "partner")
RAUSCH_KLASSEN = ("newsletter", "werbung")

#: Betreffe je Absender, die das Modell sieht (Stichprobe, neueste zuerst).
STICHPROBE_BETREFFS = 5
LLM_TIMEOUT_SEKUNDEN = 120
LLM_MAX_ANTWORT_TOKEN = 4000

#: K2-Plausibilität: Freemail-Domains schicken Menschen, keine Newsletter.
FREEMAIL_DOMAENEN = (
    "gmail.com", "googlemail.com", "gmx.de", "gmx.net", "gmx.at", "web.de",
    "t-online.de", "yahoo.com", "yahoo.de", "outlook.com", "outlook.de",
    "hotmail.com", "hotmail.de", "live.com", "icloud.com", "me.com",
    "posteo.de", "mailbox.org", "freenet.de", "aol.com", "proton.me",
    "protonmail.com",
)  # fmt: skip

#: K2-Plausibilität: ``vorname.nachname`` (auch mit Bindestrich/Unterstrich).
PERSONEN_MUSTER = re.compile(r"^[a-zäöüß]{2,}[._-][a-zäöüß]{2,}$")

#: Rollen-Wörter im lokalen Teil, die das Personenmuster aufheben
#: ("news.letter@", "no-reply@" sehen formal wie Vor.Nachname aus).
ROLLEN_WOERTER = (
    "news", "letter", "info", "reply", "noreply", "marketing", "mailer",
    "team", "service", "support", "hello", "kontakt", "contact", "notification",
    "update", "promo", "angebot", "shop", "mail", "online",
)  # fmt: skip

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
    #: Alle Betreffe/Anhangnamen des Fensters — für den Beleg-Schutz (K1).
    betreffs: list[str] = field(default_factory=list)
    anhaenge: list[str] = field(default_factory=list)
    #: K2-Klasse nach Modell + Plausibilität ("" = noch nicht eingeordnet).
    klasse: str = ""


@dataclass
class Ausschluss:
    """Ein Absender, der KEIN Kandidat wird, mit Grund (für die Owner-Anzeige)."""

    absender: str
    treffer: int
    grund: str


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
    if any(
        any(teil in o.lower() for teil in AUSGESCHLOSSENE_ORDNER_TEILE) for o in ordner
    ):
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
    teile = [
        str(vorgang.get(feld) or "") for feld in ("gegenueber", "thread_key", "notiz")
    ]
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
        geordnet = sorted(
            treffer_liste, key=lambda t: t.get("datum") or "", reverse=True
        )
        alle_betreffs = [t.get("betreff") or "" for t in geordnet]
        kandidaten.append(
            Kandidat(
                absender=adresse,
                treffer=len(treffer_liste),
                beispiel_betreffs=alle_betreffs[:2],
                betreffs=alle_betreffs,
                anhaenge=[n for t in geordnet for n in _anhang_namen(t)],
            )
        )
    kandidaten.sort(key=lambda k: k.treffer, reverse=True)
    return kandidaten


def _anhang_namen(treffer: dict) -> list[str]:
    """Anhangnamen eines Index-Treffers — Strings oder Objekte mit Namensfeld.

    Die Index-Projektion liefert die Namen unter ``anhang_namen`` (dev-hub
    ``mail_suche``, #3627); ``anhaenge`` ist dort nur ein Bool („hat Anhänge").
    Ein Index ohne das Feld (vor dem Deploy) ergibt keine Namen — dann stützt
    sich der Beleg-Schutz allein auf den Betreff.
    """
    roh = treffer.get("anhang_namen", treffer.get("anhaenge"))
    if not isinstance(roh, list):
        return []
    namen = []
    for a in roh:
        if isinstance(a, dict):
            a = a.get("name") or a.get("dateiname") or a.get("filename") or ""
        namen.append(str(a))
    return namen


def schutz_filtern(
    kandidaten: list[Kandidat], *, eigene: set[str], gesendet: set[str]
) -> tuple[list[Kandidat], list[Ausschluss]]:
    """K1: Schutzklassen aus ``loeschschutz`` — über ALLE Treffer des Fensters.

    Ein einziger Beleg-Betreff reicht: derselbe Absender schickt dann auch
    Rechnungen, und eine Absender-Regel träfe sie mit.
    """
    frei: list[Kandidat] = []
    raus: list[Ausschluss] = []
    for k in kandidaten:
        befund = None
        for betreff in k.betreffs or [""]:
            befund = loeschschutz.pruefe(
                k.absender,
                betreff,
                eigene=eigene,
                gesendet=gesendet,
                anhaenge=k.anhaenge,
            )
            if befund:
                break
        if befund:
            raus.append(Ausschluss(k.absender, k.treffer, f"schutz:{befund.klasse}"))
        else:
            frei.append(k)
    return frei, raus


def plausibel(adresse: str, klasse: str) -> str:
    """K2-Nachprüfung: das Modell darf eine Person nicht zum Newsletter machen.

    Gibt die endgültige Klasse zurück — ``person``, wenn Adressmuster oder
    Freemail-Domain dem Modell widersprechen, sonst die Modell-Klasse.
    """
    if klasse not in RAUSCH_KLASSEN:
        return klasse
    lokal, _, domain = adresse.partition("@")
    if domain in FREEMAIL_DOMAENEN:
        return "person"
    if PERSONEN_MUSTER.match(lokal) and not any(w in lokal for w in ROLLEN_WOERTER):
        return "person"
    return klasse


def _prompt(kandidaten: list[Kandidat]) -> str:
    zeilen = [
        {"nr": i, "absender": k.absender, "betreffe": k.betreffs[:STICHPROBE_BETREFFS]}
        for i, k in enumerate(kandidaten)
    ]
    return (
        "Ordne jeden Absender eines geschäftlichen Postfachs genau einer Klasse zu:\n"
        "- newsletter: regelmäßiger Info-/Nachrichtenversand an viele Empfänger\n"
        "- werbung: Angebote, Rabatte, Verkaufs- oder Veranstaltungswerbung\n"
        "- transaktion: Rechnung, Konto, Bestellung, Sicherheit, Systemmeldung "
        "zu einem eigenen Vertrag oder Konto\n"
        "- person: ein einzelner Mensch schreibt\n"
        "- partner: Kunde, Lieferant, Behörde, Hochschule oder Projektpartner "
        "mit persönlichem Bezug\n"
        "Im Zweifel NICHT newsletter/werbung wählen. Antworte nur als JSON: "
        '{"klassen": {"<nr>": "<klasse>", ...}}\n\n'
        + json.dumps(zeilen, ensure_ascii=False)
    )


def groq_einordnen(kandidaten: list[Kandidat]) -> dict:
    """Der eingebaute Groq-Aufruf — Muster ``todo_board/straenge.py``.

    Wirft bei fehlendem ``GROQ_API_KEY``, Netzfehler oder kaputtem JSON; der
    Aufrufer (`llm_einordnen`) behandelt das als fail-closed.
    """
    schluessel = _groq_schluessel()
    rumpf = json.dumps(
        {
            "model": GROQ_DEFAULT_MODELL,
            "messages": [{"role": "user", "content": _prompt(kandidaten)}],
            "temperature": 0,
            "max_tokens": LLM_MAX_ANTWORT_TOKEN,
            "reasoning_effort": "low",
            "response_format": {"type": "json_object"},
        }
    ).encode()
    req = urllib.request.Request(
        GROQ_ENDPOINT,
        data=rumpf,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {schluessel}",
            "User-Agent": GROQ_KENNUNG,
        },
    )
    with urllib.request.urlopen(req, timeout=LLM_TIMEOUT_SEKUNDEN) as antwort:
        umschlag = json.load(antwort)
    return json.loads(umschlag["choices"][0]["message"]["content"])


def llm_einordnen(
    kandidaten: list[Kandidat],
    klassifikator: Callable[[list[Kandidat]], dict] | None = None,
) -> tuple[list[Kandidat], list[Ausschluss]]:
    """K2: nur ``newsletter``/``werbung`` nach Plausibilität bleiben Kandidat.

    Fehlende oder unbekannte Klasse zählt als ``unklar`` — kein Kandidat.
    Scheitert der Aufruf ganz, fallen ALLE heraus (fail-closed).
    """
    if not kandidaten:
        return [], []
    try:
        antwort = (klassifikator or groq_einordnen)(kandidaten)
        klassen = antwort.get("klassen") or {}
    except Exception as e:  # noqa: BLE001 — jeder Modell-Fehler ist fail-closed
        grund = f"einordnung_fehlgeschlagen:{type(e).__name__}"
        return [], [Ausschluss(k.absender, k.treffer, grund) for k in kandidaten]
    behalten: list[Kandidat] = []
    raus: list[Ausschluss] = []
    for i, k in enumerate(kandidaten):
        roh = str(klassen.get(str(i), "")).strip().lower()
        klasse = plausibel(k.absender, roh if roh in KLASSEN else "unklar")
        k.klasse = klasse
        if klasse in RAUSCH_KLASSEN:
            behalten.append(k)
        else:
            raus.append(Ausschluss(k.absender, k.treffer, f"klasse:{klasse}"))
    return behalten, raus


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
    zeilen = [
        "Absender | Treffer | Beispiel-Betreffs (2) | Vorschlag",
        "---|---|---|---",
    ]
    for k in kandidaten:
        beispiele = " / ".join(b[:60] for b in k.beispiel_betreffs) or "(kein Betreff)"
        zeilen.append(f"{k.absender} | {k.treffer} | {beispiele} | {ZIELORDNER}")
    return "\n".join(zeilen)


def bestand_einordnen(
    eintraege: list[str],
    *,
    eigene: set[str],
    abfrage: Callable[[list[dict]], list[dict]],
    klassifikator: Callable[[list[Kandidat]], dict] | None = None,
) -> list[dict]:
    """K4: je Regel-Eintrag Klasse und Treffer im Löschordner — Owner-Vorlage.

    Ein Eintrag ist Adresse, Domain oder Freitext. Die Mails im Löschordner
    liefern Betreffe für Beleg-Schutz und Modell; die Gesendet-Historie gilt
    für volle Adressen. Nichts wird geschrieben oder verschoben.
    """
    eintraege = [e.strip().lower() for e in eintraege if e and e.strip()]
    anfragen = [{"von": e, "ordner": ZIELORDNER, "limit": 200} for e in eintraege]
    ergebnisse = {e.get("index", i): e for i, e in enumerate(abfrage(anfragen))}
    gesendet = loeschschutz.gesendet_an(eintraege, abfrage)
    kandidaten = []
    for i, e in enumerate(eintraege):
        treffer = (ergebnisse.get(i) or {}).get("treffer") or []
        kandidaten.append(
            Kandidat(
                absender=e,
                treffer=len(treffer),
                betreffs=[t.get("betreff") or "" for t in treffer],
                anhaenge=[n for t in treffer for n in _anhang_namen(t)],
            )
        )
    frei, raus_schutz = schutz_filtern(kandidaten, eigene=eigene, gesendet=gesendet)
    rausch, raus_klasse = llm_einordnen(frei, klassifikator)
    zeilen = [
        _bestand_zeile(k.absender, k.treffer, f"klasse:{k.klasse}", bleibt=True)
        for k in rausch
    ] + [
        _bestand_zeile(a.absender, a.treffer, a.grund, bleibt=False)
        for a in raus_schutz + raus_klasse
    ]
    return sorted(zeilen, key=lambda z: (z["bleibt"], -z["im_loeschordner"]))


def _bestand_zeile(eintrag: str, treffer: int, einordnung: str, *, bleibt: bool):
    return {
        "eintrag": eintrag,
        "im_loeschordner": treffer,
        "einordnung": einordnung,
        "bleibt": bleibt,
    }


def _bestand_ausgeben(rausch_regeln: dict, *, als_json: bool) -> int:
    eintraege = rausch_regeln.get("nach_ordner_zur_loeschung") or []
    zeilen = bestand_einordnen(
        eintraege,
        eigene=loeschschutz.eigene_adressen(),
        abfrage=loeschschutz.index_batch,
    )
    if als_json:
        print(json.dumps(zeilen, ensure_ascii=False, indent=2))
        return 0
    fraglich = [z for z in zeilen if not z["bleibt"]]
    print(
        f"Bestand nach_ordner_zur_loeschung: {len(zeilen)} Einträge, "
        f"{len(fraglich)} fraglich (Owner-Vorlage, platform#3176 K4)\n"
    )
    print("Eintrag | im Löschordner | Einordnung | Vorschlag")
    print("---|---|---|---")
    for z in zeilen:
        vorschlag = "bleibt" if z["bleibt"] else "raus + zurückverschieben?"
        print(
            f"{z['eintrag']} | {z['im_loeschordner']} | {z['einordnung']} | {vorschlag}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--stichtag",
        default=date.today().isoformat(),
        help="Fenster-Ende YYYY-MM-DD, fuer reproduzierbare Laeufe (Default: heute)",
    )
    p.add_argument("--limit", type=int, default=3000)
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--bestand",
        action="store_true",
        help="K4: heutige Einträge von nach_ordner_zur_loeschung einordnen "
        "(Owner-Vorlage, schreibt nichts)",
    )
    args = p.parse_args(argv)

    ledger = ledger_laden()
    rausch_regeln = ledger.get("rausch_regeln", {})

    if args.bestand:
        return _bestand_ausgeben(rausch_regeln, als_json=args.json)

    stichtag = date.fromisoformat(args.stichtag)
    seit = (stichtag - timedelta(days=FENSTER_TAGE)).isoformat()

    treffer = treffer_laden(seit, bis=args.stichtag, limit=args.limit)
    vorgaenge = ledger.get("vorgaenge", [])

    roh = kandidaten_ermitteln(treffer, rausch_regeln, vorgaenge)
    gesendet = loeschschutz.gesendet_an(k.absender for k in roh)
    geschuetzt, raus_schutz = schutz_filtern(
        roh, eigene=loeschschutz.eigene_adressen(), gesendet=gesendet
    )
    kandidaten, raus_klasse = llm_einordnen(geschuetzt)
    ausgeschlossen = raus_schutz + raus_klasse

    if args.json:
        ausgabe = {
            "stichtag": args.stichtag,
            "seit": seit,
            "kandidaten": [
                {
                    "absender": k.absender,
                    "treffer": k.treffer,
                    "klasse": k.klasse,
                    "beispiel_betreffs": k.beispiel_betreffs,
                    "regel": regel_vorschlag(k, args.stichtag),
                }
                for k in kandidaten
            ],
            "ausgeschlossen": [a.__dict__ for a in ausgeschlossen],
        }
        print(json.dumps(ausgabe, ensure_ascii=False, indent=2))
        return 0

    print(
        f"Rausch-Kandidaten {seit} .. {args.stichtag} (Fenster {FENSTER_TAGE} Tage)\n"
    )
    print(_tabelle(kandidaten))
    if ausgeschlossen:
        print(f"\nNicht vorgeschlagen (platform#3176): {len(ausgeschlossen)}")
        for a in ausgeschlossen:
            print(f"  · {a.absender} ({a.treffer}) — {a.grund}")
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
