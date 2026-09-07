#!/usr/bin/env python3
"""Ausgangsrechnung als sevdesk-ENTWURF anlegen — nie senden, nie festschreiben (platform#2895).

Schwesterwerkzeug zu ``beleg_entwurf.py`` (Eingangsrechnungen als Voucher-Entwurf).
Dieses hier legt Ausgangsrechnungen (Invoice) an — gleiche Grundregeln, andere
Richtung:

- ``status: 100`` (Entwurf) ist fest verdrahtet. Kein ``sendBy``, kein Status > 100,
  kein ``Invoice/<id>/sendViaEmail`` — Verbuchen/Versand bleibt beim Owner
  (⛔-Gate, ``feedback_sevdesk_booking_only_after_owner_approval``).
- ``sumNet``/``sumTax``/``sumGross`` werden nach dem Anlegen zurückgelesen und gegen
  die selbst berechnete Erwartung geprüft (Beleg-Lehre: nie nur netto liefern und
  hoffen — ``net``-artige Flags werden von der API ignoriert, explizit rechnen).
- Kontakte sind ``Contact`` mit ``category`` id 3 ("Kunde", verifiziert 2026-09-07);
  Adresse als ``ContactAddress`` (``category`` id 43 "Arbeit"), Land als
  ``StaticCountry`` id 1 ("Deutschland"), E-Mail als ``CommunicationWay``
  (``type EMAIL``, ``key`` id 2 "Arbeit" — alle vier Werte am 2026-09-07 live gegen
  die API geprüft, nicht geraten). Ein Zusatz (z. B. "z. Hd. ...") kommt in
  ``Contact.name2`` — Beleg dafür ist ein realer Bestandskontakt mit ``name2``
  in Form eines "c/o ..."-Zusatzes; ``ContactAddress`` selbst führt in diesem
  sevdesk-Konto kein entsprechendes Feld (51 Bestandsadressen geprüft, keine
  mit ``name2``).
- ``contactPerson`` (SevUser 1115780), ``paymentMethod`` (SEPA Überweisung, id
  21919), ``timeToPay`` 14, ``taxType default`` sind aus der Vorgabe übernommen und
  am 2026-09-07 gegen die neueste Bestandsrechnung (20260828-287) verifiziert.
  ``headText``/``footText`` werden zur Laufzeit von der neuesten Rechnung
  übernommen, nicht hartkodiert — sevdesk ändert den Textbaustein gelegentlich.
- Nummernkreis ``JJJJMMTT-NNN``: die laufende Nummer NNN ist ein einziger,
  fortlaufender Zähler über ALLE Rechnungen (auch Stornorechnungen SR teilen sich
  ihn, siehe 20260702-285/-286) — kein Reset zum Jahreswechsel, kein Reset pro
  Tag. ``naechste_nummer`` paginiert daher den kompletten Bestand — und filtert
  strikt auf das Muster ``JJJJMMTT-NNN`` (8 Ziffern, Bindestrich, Ziffern): der
  Bestand enthält mindestens eine Alt-Rechnung im Format ``RE-1000`` aus einem
  anderen, älteren Nummernkreis. Ein naiver Split auf den letzten Bindestrich
  läse deren "1000" als aktuell höchste laufende Nummer und würde die nächste
  Rechnung fälschlich auf ``…-1001`` statt ``…-288`` setzen — am 2026-09-07 live
  im eigenen Dry-Run aufgefallen, deshalb der Regex-Filter statt Freitext-Split.
- Dedup: ein ENTWURF (status 100) mit gleichem Kontakt, Datum und Netto-Summe
  verhindert eine zweite Rechnung (K5 Idempotenz, wie beim Beleg-Werkzeug).
- ``invoiceDate`` wird als ``YYYY-MM-DD`` gesendet — dieselbe Konvention, mit der
  ``beleg_entwurf.py`` das strukturgleiche ``voucher[voucherDate]`` produktiv an
  ``Voucher/Factory/saveVoucher`` schickt (unkonvertiert). Für ``Invoice/Factory/
  saveInvoice`` ist das eine Analogie, keine unabhängig bestätigte Tatsache — die
  Plausibilitätsprüfung nach dem Anlegen ist die Gegenprobe.

    python3 tools/sevdesk/rechnung_entwurf.py --kunde "Musterkommune" \
        --strasse "Rathausplatz 1" --plz 12345 --ort Musterstadt \
        --email rathaus@musterkommune.de --datum 2026-09-07 \
        --position "Vortrag|Klausurtagung|1|650.00" --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from beleg_entwurf import _client  # noqa: E402  geteilter Helfer, keine Kopie

#: Verifiziert 2026-09-07 gegen die produktive sevdesk-API (siehe Modul-Docstring).
KONTAKTPERSON_SEVUSER_ID = "1115780"
ZAHLUNGSMETHODE_SEPA_ID = "21919"
KATEGORIE_KUNDE_ID = "3"
KATEGORIE_ADRESSE_ARBEIT_ID = "43"
DEUTSCHLAND_ID = "1"
EMAIL_KEY_ARBEIT_ID = "2"
STEUERSATZ = 19

#: JJJJMMTT-NNN — exakt 8 Ziffern Datum, Bindestrich, Ziffern laufende Nummer.
#: Nicht mit einem Freitext-Split auf den letzten Bindestrich verwechseln: der
#: Bestand enthält auch Alt-Rechnungen wie "RE-1000" aus einem anderen Schema.
_NUMMERNKREIS = re.compile(r"^\d{8}-(\d+)$")


def _seiten(client, pfad: str, **params) -> list[dict]:
    """Generisches Paging über eine sevdesk-Liste (Limit/Offset) — keine Seite auslassen."""
    ergebnis: list[dict] = []
    limit = 500
    offset = 0
    while True:
        r = client.get(pfad, params={**params, "limit": limit, "offset": offset})
        r.raise_for_status()
        seite = r.json()["objects"]
        ergebnis.extend(seite)
        if len(seite) < limit:
            return ergebnis
        offset += limit


def naechste_nummer(client, datum: str) -> str:
    """Höchste NNN über ALLE Invoice-Objekte + 1, Präfix aus ``datum`` (YYYY-MM-DD)."""
    hoechste = 0
    for rechnung in _seiten(client, "/Invoice"):
        nummer = rechnung.get("invoiceNumber") or ""
        treffer = _NUMMERNKREIS.match(nummer)
        if not treffer:
            continue
        hoechste = max(hoechste, int(treffer.group(1)))
    return f"{datum.replace('-', '')}-{hoechste + 1:03d}"


def entwurf_duplikat(client, kontakt_id: str, datum: str, netto: float) -> str | None:
    """Existiert schon ein ENTWURF (status 100) mit gleichem Kontakt/Datum/Netto?"""
    for rechnung in _seiten(
        client,
        "/Invoice",
        **{
            "contact[id]": kontakt_id,
            # objectName ist Pflicht: ohne ihn quittiert sevdesk den Objekt-Filter
            # mit 400 Bad Request (Realfund 2026-09-07, siehe kontakt_finden_oder_anlegen).
            "contact[objectName]": "Contact",
            "status": "100",
        },
    ):
        rechnungsdatum = (rechnung.get("invoiceDate") or "")[:10]
        try:
            sum_netto = round(float(rechnung.get("sumNet") or 0), 2)
        except (TypeError, ValueError):
            continue
        if rechnungsdatum == datum and abs(sum_netto - netto) < 0.01:
            return rechnung["id"]
    return None


def neueste_texte(client) -> tuple[str, str]:
    """headText/footText von der neuesten Rechnung übernehmen — nicht hartkodieren."""
    r = client.get(
        "/Invoice", params={"limit": 1, "offset": 0, "order[create]": "desc"}
    )
    r.raise_for_status()
    objekte = r.json()["objects"]
    if not objekte:
        return "", ""
    neueste = objekte[0]
    return neueste.get("headText") or "", neueste.get("footText") or ""


def kontakt_finden_oder_anlegen(
    client, name: str, strasse: str, plz: str, ort: str, email: str, zusatz: str = ""
) -> tuple[str, bool]:
    """Exakte Namenssuche zuerst; sonst Kunde + Adresse + E-Mail anlegen.

    Rückgabe: (kontakt_id, war_neu).
    """
    r = client.get("/Contact", params={"name": name})
    r.raise_for_status()
    treffer = [o for o in r.json()["objects"] if o.get("name") == name]
    if treffer:
        return treffer[0]["id"], False

    kontakt_payload: dict = {
        "name": name,
        "status": 1000,
        "category": {"id": KATEGORIE_KUNDE_ID, "objectName": "Category"},
    }
    if zusatz:
        kontakt_payload["name2"] = zusatz
    r = client.post("/Contact", json=kontakt_payload)
    r.raise_for_status()
    neu = r.json()["objects"]
    kontakt_id = (neu[0] if isinstance(neu, list) else neu)["id"]

    r = client.post(
        "/ContactAddress",
        json={
            "contact": {"id": kontakt_id, "objectName": "Contact"},
            "category": {"id": KATEGORIE_ADRESSE_ARBEIT_ID, "objectName": "Category"},
            "street": strasse,
            "zip": plz,
            "city": ort,
            "country": {"id": DEUTSCHLAND_ID, "objectName": "StaticCountry"},
        },
    )
    r.raise_for_status()

    r = client.post(
        "/CommunicationWay",
        json={
            "contact": {"id": kontakt_id, "objectName": "Contact"},
            "type": "EMAIL",
            "value": email,
            "key": {"id": EMAIL_KEY_ARBEIT_ID, "objectName": "CommunicationWayKey"},
            "main": 1,
        },
    )
    r.raise_for_status()

    return kontakt_id, True


def adressblock(kunde: str, strasse: str, plz: str, ort: str, zusatz: str = "") -> str:
    """Mehrzeiliger Adressblock — Reihenfolge wie im realen Bestand (Name, Zusatz, Straße, PLZ Ort)."""
    zeilen = [kunde]
    if zusatz:
        zeilen.append(zusatz)
    zeilen.append(strasse)
    zeilen.append(f"{plz} {ort}")
    return "\n".join(zeilen)


def pruefe_plausibilitaet(
    erwartet_netto: float,
    erwartet_steuer: float,
    erwartet_brutto: float,
    sum_net,
    sum_tax,
    sum_gross,
) -> None:
    """netto+steuer==brutto laut sevdesk-Rückmeldung — bricht bei Abweichung >1 Cent ab."""
    ist_netto = round(float(sum_net or 0), 2)
    ist_steuer = round(float(sum_tax or 0), 2)
    ist_brutto = round(float(sum_gross or 0), 2)
    if (
        abs(ist_netto - erwartet_netto) > 0.01
        or abs(ist_steuer - erwartet_steuer) > 0.01
        or abs(ist_brutto - erwartet_brutto) > 0.01
    ):
        raise ValueError(
            "Plausibilitätsprobe verletzt: erwartet "
            f"netto={erwartet_netto:.2f} steuer={erwartet_steuer:.2f} brutto={erwartet_brutto:.2f}, "
            f"sevdesk lieferte netto={ist_netto:.2f} steuer={ist_steuer:.2f} brutto={ist_brutto:.2f}"
        )


def rechnung_entwurf(
    client,
    kontakt_id: str,
    kontakt_name: str,
    adresse: str,
    datum: str,
    positionen: list[dict],
    zahlungsziel: int = 14,
) -> dict:
    """POST Invoice/Factory/saveInvoice als ENTWURF (status 100) + Rückles-Plausibilität.

    ``positionen``: Liste von ``{"name", "text", "menge", "preis"}`` (preis = netto/Einheit).
    Rückgabe bei Duplikat: ``{"duplikat": True, "vorhanden_id": ...}`` — es wird NICHTS angelegt.
    """
    netto = round(sum(p["menge"] * p["preis"] for p in positionen), 2)

    vorhanden = entwurf_duplikat(client, kontakt_id, datum, netto)
    if vorhanden:
        return {"duplikat": True, "vorhanden_id": vorhanden}

    nummer = naechste_nummer(client, datum)
    head_text, foot_text = neueste_texte(client)

    daten: dict = {
        "invoice[objectName]": "Invoice",
        "invoice[mapAll]": "true",
        "invoice[invoiceNumber]": nummer,
        "invoice[invoiceDate]": datum,
        "invoice[status]": "100",
        "invoice[invoiceType]": "RE",
        "invoice[currency]": "EUR",
        "invoice[contact][id]": str(kontakt_id),
        "invoice[contact][objectName]": "Contact",
        "invoice[contactPerson][id]": KONTAKTPERSON_SEVUSER_ID,
        "invoice[contactPerson][objectName]": "SevUser",
        "invoice[paymentMethod][id]": ZAHLUNGSMETHODE_SEPA_ID,
        "invoice[paymentMethod][objectName]": "PaymentMethod",
        "invoice[timeToPay]": str(zahlungsziel),
        "invoice[header]": f"Rechnung Nr. {nummer}",
        "invoice[headText]": head_text,
        "invoice[footText]": foot_text,
        "invoice[showNet]": "1",
        "invoice[smallSettlement]": "0",
        "invoice[taxRate]": str(STEUERSATZ),
        "invoice[taxType]": "default",
        "invoice[sendType]": "VPDF",
        "invoice[address]": adresse,
        "invoice[addressName]": kontakt_name,
    }
    for i, pos in enumerate(positionen):
        daten[f"invoicePosSave[{i}][objectName]"] = "InvoicePos"
        daten[f"invoicePosSave[{i}][mapAll]"] = "true"
        daten[f"invoicePosSave[{i}][quantity]"] = f"{pos['menge']:g}"
        daten[f"invoicePosSave[{i}][price]"] = f"{pos['preis']:.2f}"
        daten[f"invoicePosSave[{i}][taxRate]"] = str(STEUERSATZ)
        daten[f"invoicePosSave[{i}][unity][id]"] = "1"
        daten[f"invoicePosSave[{i}][unity][objectName]"] = "Unity"
        daten[f"invoicePosSave[{i}][name]"] = pos["name"]
        if pos.get("text"):
            daten[f"invoicePosSave[{i}][text]"] = pos["text"]

    r = client.post("/Invoice/Factory/saveInvoice", data=daten)
    r.raise_for_status()
    ergebnis = r.json()["objects"]
    rechnung = (
        ergebnis["invoice"]
        if isinstance(ergebnis, dict) and "invoice" in ergebnis
        else ergebnis
    )
    rechnung_id = rechnung["id"]

    r2 = client.get(f"/Invoice/{rechnung_id}")
    r2.raise_for_status()
    frisch = r2.json()["objects"]
    frisch = frisch[0] if isinstance(frisch, list) else frisch

    steuer = round(netto * STEUERSATZ / 100, 2)
    brutto = round(netto + steuer, 2)
    pruefe_plausibilitaet(
        netto,
        steuer,
        brutto,
        frisch.get("sumNet"),
        frisch.get("sumTax"),
        frisch.get("sumGross"),
    )

    return {
        "duplikat": False,
        "id": rechnung_id,
        "nummer": nummer,
        "netto": netto,
        "steuer": steuer,
        "brutto": brutto,
    }


def parse_position(roh: str) -> dict:
    """``NAME|TEXT|MENGE|NETTOPREIS`` — Komma oder Punkt als Dezimaltrenner erlaubt."""
    teile = roh.split("|")
    if len(teile) != 4:
        raise ValueError(
            f"--position braucht 4 Felder NAME|TEXT|MENGE|NETTOPREIS: {roh!r}"
        )
    name, text, menge, preis = teile
    return {
        "name": name,
        "text": text or None,
        "menge": float(menge.replace(",", ".")),
        "preis": float(preis.replace(",", ".")),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--kunde", required=True)
    p.add_argument("--strasse", required=True)
    p.add_argument("--plz", required=True)
    p.add_argument("--ort", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--zusatz", default="")
    p.add_argument("--datum", default=date.today().isoformat(), help="YYYY-MM-DD")
    p.add_argument("--zahlungsziel", type=int, default=14)
    p.add_argument(
        "--position",
        action="append",
        required=True,
        help='mehrfach: "NAME|TEXT|MENGE|NETTOPREIS"',
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    try:
        positionen = [parse_position(s) for s in args.position]
    except ValueError as exc:
        print(f"ABBRUCH: {exc}")
        return 2

    netto = round(sum(pos["menge"] * pos["preis"] for pos in positionen), 2)
    adresse = adressblock(args.kunde, args.strasse, args.plz, args.ort, args.zusatz)

    client = _client()

    treffer = client.get("/Contact", params={"name": args.kunde})
    treffer.raise_for_status()
    gefunden = [o for o in treffer.json()["objects"] if o.get("name") == args.kunde]
    nummer_vorschau = naechste_nummer(client, args.datum)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "nummer": nummer_vorschau,
                    "kontakt": "gefunden" if gefunden else "wird neu angelegt",
                    "kontakt_id": gefunden[0]["id"] if gefunden else None,
                    "netto": f"{netto:.2f}",
                    "steuer": f"{round(netto * STEUERSATZ / 100, 2):.2f}",
                    "brutto": f"{round(netto * (100 + STEUERSATZ) / 100, 2):.2f}",
                    "positionen": positionen,
                    "adresse": adresse,
                    "zahlungsziel": args.zahlungsziel,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    kontakt_id, war_neu = kontakt_finden_oder_anlegen(
        client, args.kunde, args.strasse, args.plz, args.ort, args.email, args.zusatz
    )

    ergebnis = rechnung_entwurf(
        client,
        kontakt_id,
        args.kunde,
        adresse,
        args.datum,
        positionen,
        args.zahlungsziel,
    )
    if ergebnis["duplikat"]:
        print(
            "DUPLIKAT: Entwurf mit gleichem Kontakt/Datum/Netto existiert bereits als "
            f"Rechnung {ergebnis['vorhanden_id']} — nichts angelegt."
        )
        return 0

    print(
        json.dumps(
            {
                "rechnung_id": ergebnis["id"],
                "nummer": ergebnis["nummer"],
                "netto": f"{ergebnis['netto']:.2f}",
                "steuer": f"{ergebnis['steuer']:.2f}",
                "brutto": f"{ergebnis['brutto']:.2f}",
                "kontakt": "neu angelegt" if war_neu else "gefunden",
                "kontakt_id": kontakt_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
