#!/usr/bin/env python3
"""Zahlungsabgleich: offene Bankeingaenge gegen offene Rechnungen, Mahnkandidaten.

K4 aus platform#3102 (Vorschlag 228 der sevdesk-API-Analyse). Read-only per
Standardlauf — Schreiben (``bookAmount``) passiert ausschliesslich mit
``--buchen --ja`` und ausschliesslich fuer **sichere** Zuordnungen.

    python3 tools/sevdesk/zahlungsabgleich.py                 # drei Listen + Mahnkandidaten
    python3 tools/sevdesk/zahlungsabgleich.py --tage 60        # engeres Fenster
    python3 tools/sevdesk/zahlungsabgleich.py --json           # maschinenlesbar
    python3 tools/sevdesk/zahlungsabgleich.py --buchen          # Vorschau, bucht NICHTS
    python3 tools/sevdesk/zahlungsabgleich.py --buchen --ja    # bucht die sicheren Faelle

Drei Zuordnungsstufen je Bankeingang (Betrag > 0, Status 100 = unzugeordnet):

- **sicher**: eine oder mehrere Rechnungsnummern (Muster ``YYYYMMDD-NNN``) stehen
  im Verwendungszweck, und die Summe der genannten offenen Rechnungen trifft den
  Betrag auf 1 Cent genau. Sammelueberweisungen mit mehreren Nummern zaehlen dazu.
- **unsicher**: entweder passt der Betrag zu genau EINER offenen Rechnung, deren
  Zahler-/Kontaktname ein gemeinsames Wort (>= 4 Zeichen) mit dem Zahlungsempfaenger
  im Umsatz teilt — ohne Nummer im Zweck; oder eine Nummer steht im Zweck, aber die
  Summe weicht ab (Skonto, Teilzahlung, Rundung > 1 Cent).
- **ohne Zuordnung**: der Rest (Fremdeingang, unbekannter Zahler, keine passende
  Rechnung).

**Mahnkandidaten**: offene Rechnungen (Status 200), deren Faelligkeit
(``invoiceDate`` + ``timeToPay`` Tage) am Stichtag ueberschritten ist und die in
keiner der beiden Trefferlisten oben vorkommen. Absteigend nach Tagen ueberfaellig.
Es wird **nichts gemahnt** — nur angezeigt (Mahnungen sind ein eigener Auftrag).

Fallen (siehe auch ``tools/sevdesk/README.md``):

- Eine Rechnungsnummer im Zweck ist kein Beweis — erst die Summenprobe (±0,01 EUR)
  macht sie sicher. Genannt, aber falscher Betrag -> unsicher, nie sicher.
- Sammelueberweisungen nennen mehrere Nummern in einem Zweck; alle muessen bekannt
  sein UND in Summe passen, sonst faellt der ganze Eingang auf unsicher zurueck.
- Skonto/Teilzahlung sehen wie ein Tippfehler in der Nummer aus, sind aber
  gewollte Abweichungen — deshalb unsicher statt sicher, nie automatisch gebucht.
- ``--buchen`` ohne ``--ja`` zeigt nur, was gebucht wuerde; es ruft ``bookAmount``
  in KEINEM Fall auf.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from beleg_entwurf import _client  # noqa: E402

#: CheckAccountTransaction-Status (OpenAPI Model_CheckAccountTransaction):
#: 100 = angelegt/unzugeordnet, 200 = verknuepft, 300 = privat, 400 = verbucht.
#: Am Bestand (Echtprobe 2026-09-12) taucht zusaetzlich 350 auf — in der
#: OpenAPI-Spezifikation nicht dokumentiert, hier ohne Bedeutung: nur 100 zaehlt
#: als offen, alles andere faellt schon durch den Ungleichheits-Filter raus.
STATUS_TX_OFFEN = "100"

#: Invoice-Status: 50 Entwurf, 100 angelegt, 200 gesendet/offen, 750 ?, 1000 bezahlt.
STATUS_RECHNUNG_OFFEN = "200"

LOG_VERZEICHNIS = Path.home() / ".claude"

#: Rechnungsnummer-Muster laut Rechnungslauf: YYYYMMDD-NNN. Mehrere Treffer in
#: einem Verwendungszweck sind eine Sammelueberweisung, kein Fehler.
RE_RECHNUNGSNUMMER = re.compile(r"\b(\d{8}-\d{3})\b")

RE_WORT = re.compile(r"[A-Za-zÄÖÜäöüß]+")


def hole(client, pfad: str, **params) -> list[dict]:
    """Blaettert vollstaendig durch (sevdesk liefert maximal 200 je Anfrage)."""
    ergebnis: list[dict] = []
    offset = 0
    while True:
        r = client.get(pfad, params=dict(params, limit=200, offset=offset))
        r.raise_for_status()
        seite = r.json().get("objects") or []
        ergebnis += seite
        if len(seite) < 200:
            return ergebnis
        offset += 200


def rechnungsnummern_im_zweck(zweck: str) -> list[str]:
    return RE_RECHNUNGSNUMMER.findall(zweck or "")


def kontaktname(rechnung: dict) -> str:
    contact = rechnung.get("contact") or {}
    name = (contact.get("name") or "").strip()
    if name:
        return name
    vorname = (contact.get("surename") or "").strip()
    nachname = (contact.get("familyname") or "").strip()
    return f"{vorname} {nachname}".strip()


def worte(text: str, mindestlaenge: int = 4) -> set[str]:
    return {w.lower() for w in RE_WORT.findall(text or "") if len(w) >= mindestlaenge}


def offener_betrag(rechnung: dict) -> float:
    brutto = float(rechnung.get("sumGross") or 0)
    bezahlt = float(rechnung.get("paidAmount") or 0)
    return round(brutto - bezahlt, 2)


def faelligkeitsdatum(rechnung: dict) -> dt.date | None:
    roh = (rechnung.get("invoiceDate") or "")[:10]
    if not roh:
        return None
    try:
        datum = dt.date.fromisoformat(roh)
    except ValueError:
        return None
    frist = int(rechnung.get("timeToPay") or 0)
    return datum + dt.timedelta(days=frist)


def zuordnen(eingang: dict, rechnungen: list[dict]) -> dict:
    """Ordnet EINEN Bankeingang einer/mehreren offenen Rechnungen zu.

    Rueckgabe: {"stufe": "sicher"|"unsicher"|"ohne", "rechnungen": [...], "grund": str}
    """
    betrag = round(abs(float(eingang.get("amount") or 0)), 2)
    zweck = eingang.get("paymtPurpose") or ""
    name = eingang.get("payeePayerName") or ""
    nummern = rechnungsnummern_im_zweck(zweck)

    if nummern:
        nach_nummer = {r.get("invoiceNumber"): r for r in rechnungen}
        treffer = [nach_nummer[n] for n in nummern if n in nach_nummer]
        if treffer:
            summe = round(sum(offener_betrag(r) for r in treffer), 2)
            vollstaendig = len(treffer) == len(nummern)
            if vollstaendig and abs(summe - betrag) <= 0.01:
                return {
                    "stufe": "sicher",
                    "rechnungen": treffer,
                    "grund": (
                        f"Rechnungsnummer(n) {', '.join(nummern)} im Zweck, "
                        f"Summe {summe:.2f} EUR = Betrag"
                    ),
                }
            grund = (
                f"Nummer(n) {', '.join(nummern)} im Zweck, "
                f"aber Summe {summe:.2f} EUR != Betrag {betrag:.2f} EUR "
                "(Skonto/Teilzahlung/unbekannte Nummer?)"
            )
            return {"stufe": "unsicher", "rechnungen": treffer, "grund": grund}

    # (b) unsicher: Betrag passt zu GENAU EINER offenen Rechnung des Zahlers,
    # ohne (verwertbare) Nummer im Zweck.
    zahler_worte = worte(name)
    kandidaten = [
        r
        for r in rechnungen
        if abs(offener_betrag(r) - betrag) <= 0.01
        and zahler_worte & worte(kontaktname(r))
    ]
    if len(kandidaten) == 1:
        return {
            "stufe": "unsicher",
            "rechnungen": kandidaten,
            "grund": "Betrag passt zu genau einer offenen Rechnung des Zahlers, keine Nummer im Zweck",
        }

    return {
        "stufe": "ohne",
        "rechnungen": [],
        "grund": "kein Treffer (Fremdeingang oder unbekannter Zahler)",
    }


def mahnkandidaten_ermitteln(
    rechnungen: list[dict], zugeordnete_ids: set, heute: dt.date
) -> list[dict]:
    kandidaten = []
    for r in rechnungen:
        if r.get("id") in zugeordnete_ids:
            continue
        faellig = faelligkeitsdatum(r)
        if faellig is None or faellig >= heute:
            continue
        tage = (heute - faellig).days
        kandidaten.append(
            {
                "rechnung": r,
                "faellig": faellig,
                "tage_ueberfaellig": tage,
                "betrag": offener_betrag(r),
            }
        )
    return sorted(kandidaten, key=lambda k: k["tage_ueberfaellig"], reverse=True)


def _dd_mm_yyyy(datum: dt.date) -> str:
    return datum.strftime("%d.%m.%Y")


def buchen(client, eingang: dict, rechnung: dict, heute: dt.date) -> dict:
    """Bucht EINE Rechnung voll auf den Bankeingang (immer FULL_PAYMENT — Teilbetraege
    ohne Owner-Wort sind ausgeschlossen, die sichere Stufe ist per Konstruktion voll).
    """
    checkaccount = eingang.get("checkAccount") or {}
    payload = {
        "amount": offener_betrag(rechnung),
        "date": _dd_mm_yyyy(heute),
        "type": "FULL_PAYMENT",
        "checkAccount": {"id": checkaccount.get("id"), "objectName": "CheckAccount"},
        "checkAccountTransaction": {
            "id": eingang.get("id"),
            "objectName": "CheckAccountTransaction",
        },
    }
    r = client.put(f"/Invoice/{rechnung['id']}/bookAmount", json=payload)
    r.raise_for_status()
    antwort = r.json()

    # Ergebnis pruefen: Rechnung danach abrufen, paidAmount/Status vergleichen.
    pruef = client.get(f"/Invoice/{rechnung['id']}")
    pruef.raise_for_status()
    objekte = pruef.json().get("objects") or []
    danach = objekte[0] if objekte else {}
    warnung = None
    if danach and abs(offener_betrag(danach)) > 0.01:
        warnung = (
            f"Rechnung {rechnung.get('invoiceNumber')} nach Buchung noch nicht "
            f"ausgeglichen (offen: {offener_betrag(danach):.2f} EUR) — pruefen."
        )
    return {
        "antwort": antwort,
        "danach_offen": offener_betrag(danach) if danach else None,
        "warnung": warnung,
    }


def buchen_lauf(
    client, ergebnisse: list[dict], heute: dt.date, wirklich: bool
) -> list[dict]:
    log: list[dict] = []
    for eintrag in ergebnisse:
        if eintrag["stufe"] != "sicher":
            continue
        eingang = eintrag["eingang"]
        for rechnung in eintrag["rechnungen"]:
            posten = {
                "umsatz_id": eingang.get("id"),
                "rechnung": rechnung.get("invoiceNumber"),
                "rechnung_id": rechnung.get("id"),
                "betrag": offener_betrag(rechnung),
                "datum": heute.isoformat(),
                "ausgefuehrt": False,
            }
            if wirklich:
                ergebnis = buchen(client, eingang, rechnung, heute)
                posten["ausgefuehrt"] = True
                posten["warnung"] = ergebnis["warnung"]
            log.append(posten)
    if wirklich and log:
        ziel = LOG_VERZEICHNIS / f"sevdesk-zahlungsabgleich-{heute.isoformat()}.json"
        ziel.parent.mkdir(parents=True, exist_ok=True)
        bestehend = []
        if ziel.exists():
            bestehend = json.loads(ziel.read_text(encoding="utf-8"))
        ziel.write_text(
            json.dumps(bestehend + log, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return log


def _kurz(text: str, laenge: int) -> str:
    text = " ".join((text or "").split())
    return (text[: laenge - 1] + "…") if len(text) > laenge else text


def render_markdown(
    ergebnisse: list[dict], mahnkandidaten: list[dict], gebucht: list[dict], args
) -> str:
    zeilen: list[str] = []
    zeilen.append(f"# Zahlungsabgleich — Fenster {args.tage} Tage\n")

    def _tabelle(titel: str, teilmenge: list[dict]) -> None:
        zeilen.append(f"\n## {titel} ({len(teilmenge)})\n")
        if not teilmenge:
            zeilen.append("\n(keine)\n")
            return
        zeilen.append("\n| Datum | Zahler | Betrag € | Rechnung(en) | Grund |")
        zeilen.append("|---|---|---:|---|---|")
        for e in teilmenge:
            eingang = e["eingang"]
            nummern = (
                ", ".join(r.get("invoiceNumber", "") for r in e["rechnungen"]) or "—"
            )
            zeilen.append(
                f"| {(eingang.get('valueDate') or '')[:10]} | "
                f"{_kurz(eingang.get('payeePayerName') or '', 34)} | "
                f"{float(eingang.get('amount') or 0):,.2f} | {nummern} | {_kurz(e['grund'], 60)} |"
            )

    _tabelle("Sicher zugeordnet", [e for e in ergebnisse if e["stufe"] == "sicher"])
    _tabelle(
        "Unsicher — Owner-Blick noetig",
        [e for e in ergebnisse if e["stufe"] == "unsicher"],
    )
    _tabelle("Ohne Zuordnung", [e for e in ergebnisse if e["stufe"] == "ohne"])

    zeilen.append(f"\n## Mahnkandidaten ({len(mahnkandidaten)})\n")
    zeilen.append(
        "\nUeberfaellige offene Rechnungen ohne passenden Zahlungseingang. "
        "Es wird nichts versendet — reine Anzeige.\n"
    )
    if mahnkandidaten:
        zeilen.append(
            "\n| Rechnung | Kunde | Betrag € | faellig seit | Tage ueberfaellig |"
        )
        zeilen.append("|---|---|---:|---|---:|")
        for m in mahnkandidaten:
            r = m["rechnung"]
            zeilen.append(
                f"| {r.get('invoiceNumber', '')} | {_kurz(kontaktname(r), 30)} | "
                f"{m['betrag']:,.2f} | {m['faellig'].isoformat()} | {m['tage_ueberfaellig']} |"
            )
    else:
        zeilen.append("\n(keine)\n")

    if args.buchen:
        zeilen.append(
            f"\n## Buchung ({'ausgefuehrt' if args.ja else 'Vorschau — NICHTS gebucht'})\n"
        )
        if gebucht:
            zeilen.append("\n| Umsatz-ID | Rechnung | Betrag € | Datum |")
            zeilen.append("|---|---|---:|---|")
            for g in gebucht:
                zeilen.append(
                    f"| `{g['umsatz_id']}` | {g['rechnung']} | {g['betrag']:,.2f} | {g['datum']} |"
                )
        else:
            zeilen.append("\n(keine sicheren Zuordnungen zu buchen)\n")

    return "\n".join(zeilen) + "\n"


def als_json(
    ergebnisse: list[dict], mahnkandidaten: list[dict], gebucht: list[dict]
) -> dict:
    def eingang_json(e: dict) -> dict:
        eingang = e["eingang"]
        return {
            "umsatz_id": eingang.get("id"),
            "datum": (eingang.get("valueDate") or "")[:10],
            "zahler": eingang.get("payeePayerName"),
            "betrag": float(eingang.get("amount") or 0),
            "zweck": eingang.get("paymtPurpose"),
            "rechnungen": [r.get("invoiceNumber") for r in e["rechnungen"]],
            "grund": e["grund"],
        }

    return {
        "sicher": [eingang_json(e) for e in ergebnisse if e["stufe"] == "sicher"],
        "unsicher": [eingang_json(e) for e in ergebnisse if e["stufe"] == "unsicher"],
        "ohne": [eingang_json(e) for e in ergebnisse if e["stufe"] == "ohne"],
        "mahnkandidaten": [
            {
                "rechnung": m["rechnung"].get("invoiceNumber"),
                "kunde": kontaktname(m["rechnung"]),
                "betrag": m["betrag"],
                "faellig_seit": m["faellig"].isoformat(),
                "tage_ueberfaellig": m["tage_ueberfaellig"],
            }
            for m in mahnkandidaten
        ],
        "gebucht": gebucht,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--tage",
        type=int,
        default=120,
        help="Fenster fuer Bankeingaenge in Tagen (Standard 120)",
    )
    p.add_argument(
        "--json", action="store_true", help="Ausgabe als JSON statt Markdown"
    )
    p.add_argument(
        "--buchen",
        action="store_true",
        help="sichere Zuordnungen buchen (bookAmount) — ohne --ja nur Vorschau, bucht NICHTS",
    )
    p.add_argument(
        "--ja",
        action="store_true",
        help="Buchung wirklich ausfuehren (nur mit --buchen)",
    )
    p.add_argument(
        "--heute",
        default=None,
        help="Stichtag YYYY-MM-DD fuer Faelligkeits-/Tage-Berechnung (Reproduzierbarkeit); Standard: Systemdatum",
    )
    args = p.parse_args()

    heute = dt.date.fromisoformat(args.heute) if args.heute else dt.date.today()

    try:
        client = _client()
        seit = (heute - dt.timedelta(days=args.tage)).isoformat()
        # `onlyCredit=true` klingt nach "nur positive Betraege", filtert in der
        # sevdesk-API aber NICHT auf das Vorzeichen (Echtprobe 2026-09-12: mit
        # onlyCredit kamen ausschliesslich negative Betraege zurueck). Deshalb
        # ungefiltert holen und das Vorzeichen unten selbst pruefen — wie
        # bankpositionen.py es fuer denselben Endpunkt bereits macht.
        alle_tx = hole(client, "/CheckAccountTransaction", startDate=seit)
        rechnungen = hole(
            client, "/Invoice", status=STATUS_RECHNUNG_OFFEN, embed="contact"
        )
    except Exception as exc:  # httpx.HTTPError, ConnectError, etc.
        print(f"ABBRUCH: API-Fehler — {exc}")
        return 3

    eingaenge = sorted(
        (
            t
            for t in alle_tx
            if str(t.get("status")) == STATUS_TX_OFFEN
            and float(t.get("amount") or 0) > 0
        ),
        key=lambda t: t.get("valueDate") or "",
    )

    ergebnisse = []
    zugeordnete_rechnungs_ids: set = set()
    for e in eingaenge:
        treffer = zuordnen(e, rechnungen)
        zugeordnete_rechnungs_ids |= {r.get("id") for r in treffer["rechnungen"]}
        ergebnisse.append({"eingang": e, **treffer})

    mahnkandidaten = mahnkandidaten_ermitteln(
        rechnungen, zugeordnete_rechnungs_ids, heute
    )

    gebucht: list[dict] = []
    if args.buchen:
        try:
            gebucht = buchen_lauf(client, ergebnisse, heute, wirklich=args.ja)
        except Exception as exc:
            print(f"ABBRUCH: API-Fehler beim Buchen — {exc}")
            return 3

    if args.json:
        print(
            json.dumps(
                als_json(ergebnisse, mahnkandidaten, gebucht),
                ensure_ascii=False,
                indent=1,
            )
        )
    else:
        print(render_markdown(ergebnisse, mahnkandidaten, gebucht, args))

    unsicher = [e for e in ergebnisse if e["stufe"] == "unsicher"]
    return 2 if unsicher else 0


if __name__ == "__main__":
    sys.exit(main())
