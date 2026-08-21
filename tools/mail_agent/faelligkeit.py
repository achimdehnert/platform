#!/usr/bin/env python3
"""Wann kommt die Antwort? Erwartungsdatum je wartendem Vorgang — aus echten Mailzeiten.

Warum es das gibt (platform#2176 Kriterium 5): Ein Vorgang im Bucket `warten` sagt
heute nur, DASS gewartet wird. Ob das normal ist oder ob die Gegenseite seit drei
Wochen schweigt, muss ein Mensch aus dem Verlauf zusammenrechnen — und tut es
darum nicht.

**Die Datenquelle ist der Mail-Index, nicht der Ledger-Text.** Der erste Entwurf
las die Wartezeiten aus den Notizen der Vorgänge und kam auf einen Median von
einem Tag. Das Gegenlesen der erkannten Paare zeigte, was da gemessen wurde:
überwiegend eigene Ledger-Einträge („Antwort-Entwurf angelegt", „gelesen") mit
dem Datum ihrer *Bearbeitung*. Gemessen wurde also, wie schnell wir Notizen
schreiben — nicht, wie schnell jemand antwortet. Der Index trägt echte
Zeitstempel und die Richtung (Posteingang/Gesendete), und darauf steht dieses
Werkzeug.

**Zwei Zahlen statt einer.** „Erwartet" ist der Median (die Hälfte antwortet
schneller), „überfällig" das 90-Prozent-Quantil. Ein Vorgang, der einen Tag über
dem Median liegt, ist nicht säumig — er ist die andere Hälfte. Wer beides
gleichsetzt, baut sich einen Alarm, der immer leuchtet.

Read-only gegenüber Ledger, Index und Postfach.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
#: Der gekappte Teil des Verlaufs. Ohne ihn fehlen die aelteren GESENDET-Eintraege
#: — gemessen: vier von zehn wartenden Vorgaengen hatten "kein datierter Versand",
#: weil genau diese Zeile ins Archiv gewandert war.
ARCHIV = Path.home() / ".claude" / "mail-vorgaenge-archiv.json"
#: Ergebnis fuer die Anzeige. Das Board darf den Index nicht selbst befragen — ein
#: SSH-Aufruf je Seitenaufruf waere eine Ansicht, die man nicht mehr aufmacht.
AUSGABE = Path.home() / ".claude" / "mail-faelligkeit.json"
HIER = Path(__file__).resolve().parent

#: Ab wann eine eigene Statistik trägt. Darunter ist der Flottenwert ehrlicher als
#: ein Median aus zwei Datenpunkten.
MIN_PAARE = 3

#: Antwortabstände jenseits davon sind kein Antwortverhalten mehr, sondern ein
#: neuer Vorgang im selben Strang.
MAX_TAGE = 90

_MAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


@dataclass(frozen=True)
class Paar:
    """Ein gemessener Antwortabstand: wir haben gesendet, sie haben geantwortet."""

    tage: int
    domain: str
    adresse: str


def _ausgehend(nachricht: dict) -> bool:
    return any("esendet" in ordner for ordner in nachricht.get("ordner", []))


def index_lesen(seit: str, limit: int, cache: Path | None) -> list[dict]:
    """Den Mail-Index abfragen (SSH, Sekunden) oder aus dem Cache lesen."""
    if cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8")).get("treffer", [])
    roh = subprocess.run(
        [
            sys.executable,
            str(HIER / "suche.py"),
            "--seit",
            seit,
            "--limit",
            str(limit),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if roh.returncode != 0:
        raise RuntimeError(f"Mail-Index nicht erreichbar: {roh.stderr[:200]}")
    daten = json.loads(roh.stdout)
    if cache:
        cache.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    return daten.get("treffer", [])


def paare(nachrichten: list[dict]) -> list[Paar]:
    """Je Strang: eigener Versand → nächster Eingang danach."""
    straenge: dict[str, list[dict]] = defaultdict(list)
    for m in nachrichten:
        straenge[m.get("strang") or m.get("id")].append(m)

    out: list[Paar] = []
    for gruppe in straenge.values():
        gruppe = sorted(gruppe, key=lambda x: x.get("datum", ""))
        offen: str | None = None
        for m in gruppe:
            if _ausgehend(m):
                offen = m.get("datum")
                continue
            if not offen:
                continue
            try:
                tage = (
                    date.fromisoformat(m["datum"]) - date.fromisoformat(offen)
                ).days
            except (KeyError, ValueError):
                offen = None
                continue
            if 0 <= tage <= MAX_TAGE:
                adresse = (m.get("von") or "").lower()
                out.append(Paar(tage, adresse.split("@")[-1], adresse))
            offen = None
    return out


def quantil(werte: list[int], p: float) -> int:
    if not werte:
        return 0
    geordnet = sorted(werte)
    return geordnet[min(len(geordnet) - 1, int(len(geordnet) * p))]


def profil(paare_: list[Paar], adresse: str = "", domain: str = "") -> tuple[int, int, str]:
    """→ (erwartet_tage, ueberfaellig_tage, Quelle) für ein Gegenüber."""
    if adresse:
        eigene = [p.tage for p in paare_ if p.adresse == adresse.lower()]
        if len(eigene) >= MIN_PAARE:
            return quantil(eigene, 0.5), quantil(eigene, 0.9), f"Adresse ({len(eigene)})"
    if domain:
        je_domain = [p.tage for p in paare_ if p.domain == domain.lower()]
        if len(je_domain) >= MIN_PAARE:
            return (
                quantil(je_domain, 0.5),
                quantil(je_domain, 0.9),
                f"Domain ({len(je_domain)})",
            )
    alle = [p.tage for p in paare_]
    return quantil(alle, 0.5), quantil(alle, 0.9), f"Flotte ({len(alle)})"


def _archiv_eintraege(nr, archiv: dict) -> list[str]:
    return [str(e) for e in archiv.get(str(nr), [])]


def letzter_versand(v: dict, archiv: dict | None = None) -> date | None:
    """Datum des letzten eigenen Versands aus dem Vorgangs-Verlauf.

    Der Ledger taugt für DIESE Frage, weil ein GESENDET-Eintrag den Versand mit
    seinem eigenen Datum protokolliert — anders als bei den Eingängen, wo das
    Eintragsdatum die Bearbeitung meint.
    """
    letzte: date | None = None
    eintraege = _archiv_eintraege(v.get("nr"), archiv or {}) + str(
        v.get("notiz") or ""
    ).split(" | ")
    for eintrag in eintraege:
        if "GESENDET" not in eintrag:
            continue
        treffer = re.search(r"(20\d\d-\d\d-\d\d)", eintrag)
        if not treffer:
            continue
        try:
            tag = datetime.strptime(treffer.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if letzte is None or tag > letzte:
            letzte = tag
    return letzte


def gegenueber_adresse(v: dict) -> str:
    treffer = _MAIL.search(json.dumps(v, ensure_ascii=False))
    return treffer.group(0).lower() if treffer else ""


def backtest(paare_: list[Paar]) -> dict:
    """Leave-one-out gegen den Median der übrigen — und Deckung der 90-%-Regel."""
    werte = [p.tage for p in paare_]
    if len(werte) < 5:
        return {"paare": len(werte), "genug": False}
    fehler = []
    for i, ist in enumerate(werte):
        rest = werte[:i] + werte[i + 1 :]
        fehler.append(abs(ist - statistics.median(rest)))
    grenze = quantil(werte, 0.9)
    return {
        "paare": len(werte),
        "genug": True,
        "median_tage": statistics.median(werte),
        "median_fehler_tage": round(statistics.median(fehler), 1),
        "ueberfaellig_grenze_tage": grenze,
        "deckung_prozent": round(100 * sum(1 for w in werte if w <= grenze) / len(werte)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--seit", default="2026-06-01", help="Fenster für den Index")
    ap.add_argument("--limit", type=int, default=900)
    ap.add_argument("--index-cache", default=None, help="Index-Antwort zwischenspeichern")
    ap.add_argument("--backtest", action="store_true", help="nur den eigenen Fehler messen")
    ap.add_argument("--heute", default=None)
    ap.add_argument(
        "--schreibe",
        nargs="?",
        const=str(AUSGABE),
        default=None,
        help="Ergebnis als JSON ablegen (Default-Pfad ~/.claude/mail-faelligkeit.json)",
    )
    args = ap.parse_args()

    cache = Path(args.index_cache) if args.index_cache else None
    try:
        nachrichten = index_lesen(args.seit, args.limit, cache)
    except (RuntimeError, json.JSONDecodeError) as fehler:
        print(f"Keine Vorhersage: {fehler}")
        return 1

    gemessen = paare(nachrichten)
    if args.backtest:
        e = backtest(gemessen)
        if not e.get("genug"):
            print(f"Zu wenig Historie ({e['paare']} Paare) — keine Aussage.")
            return 0
        print(
            f"Backtest ueber {e['paare']} echte Antwortabstaende (leave-one-out):\n"
            f"  Median-Antwortzeit    {e['median_tage']:.0f} Tage\n"
            f"  Median-Fehler         {e['median_fehler_tage']} Tage\n"
            f"  Ueberfaellig ab       {e['ueberfaellig_grenze_tage']} Tagen (90-%-Quantil)\n"
            f"  Deckung dieser Regel  {e['deckung_prozent']} % der Faelle"
        )
        return 0

    heute = (
        datetime.strptime(args.heute, "%Y-%m-%d").date() if args.heute else date.today()
    )
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    try:
        archiv = json.loads(ARCHIV.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        archiv = {}
    ergebnis: dict[str, dict] = {}
    print(f"Datenbasis: {len(gemessen)} echte Antwortabstaende seit {args.seit}\n")
    for v in sorted(ledger.get("vorgaenge", []), key=lambda x: x.get("nr", 0)):
        if v.get("bucket") != "warten":
            continue
        versand = letzter_versand(v, archiv)
        kurz = (v.get("kurz") or "")[:36]
        if versand is None:
            print(f"  {v.get('nr'):>4}  {kurz:<36} —            kein datierter Versand")
            continue
        adresse = gegenueber_adresse(v)
        erwartet_tage, grenze_tage, quelle = profil(
            gemessen, adresse, adresse.split("@")[-1] if adresse else ""
        )
        erwartet = versand + timedelta(days=erwartet_tage)
        faellig = versand + timedelta(days=grenze_tage)
        marke = "UEBERFAELLIG" if heute > faellig else "erwartet"
        print(
            f"  {v.get('nr'):>4}  {kurz:<36} {marke:<12} {erwartet}"
            f"  (spaetestens {faellig}, {quelle})"
        )
        ergebnis[str(v.get("nr"))] = {
            "erwartet": erwartet.isoformat(),
            "spaetestens": faellig.isoformat(),
            "quelle": quelle,
            "ueberfaellig": heute > faellig,
            "stand": heute.isoformat(),
        }

    if args.schreibe:
        Path(args.schreibe).write_text(
            json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nGeschrieben: {Path(args.schreibe).name} ({len(ergebnis)} Vorgaenge)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
