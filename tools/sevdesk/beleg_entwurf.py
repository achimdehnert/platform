#!/usr/bin/env python3
"""Eingangsrechnung als sevdesk-Beleg-ENTWURF anlegen — nie buchen (platform#1827, K3).

Warum es das gibt: Der Juli-Importer (30 Hetzner/Mittwald-Entwürfe, 2026-07-28) lebte
im Session-Scratchpad und ist weg; seine teuer bezahlten Lehren stehen im Memory. Dieses
Werkzeug macht sie dauerhaft:

- ``status: 50`` (Entwurf) ist fest verdrahtet — Verbuchen bleibt ausnahmslos beim Owner
  (⛔-Gate, ``feedback_sevdesk_booking_only_after_owner_approval``).
- ``sumNet``/``sumTax``/``sumGross`` werden explizit gesetzt; ``net: False`` wird von der
  API IGNORIERT (Brutto würde als Netto gelesen und nochmals versteuert). Die
  Plausibilitätsprobe netto+steuer==brutto bricht bei Abweichung >1 Cent ab.
- ``creditDebit: 'C'`` für Lieferanten (der 'D'-Fehler machte 30 Eingangsrechnungen
  zu Einnahmen). Buchungskonto gehört in ``accountDatev`` — ``accountingType`` speichert
  die API klaglos, die Oberfläche zeigt dann „kein Konto".
- Konto NUR bei eindeutigem ``GET /AccountDatev``-Treffer auf die NUMMER; ohne
  ``--konto`` bleibt das Feld leer (kein Raten — 🌀 6310-statt-6837-Realfall).
- ``taxRule`` nested (Update 2.0); ``taxType`` würde stillschweigend verworfen.
- Dedup über ``description`` (= Rechnungsnummer/-kennung) gegen den Bestand: existiert
  ein Beleg mit identischer description, wird NICHT erneut angelegt (K5 Idempotenz).

    python3 tools/sevdesk/beleg_entwurf.py --pdf r.pdf --lieferant "Groq LLC" \
        --datum 2026-08-06 --brutto 12.34 --steuer 0.00 --beschreibung GROQ-2026-08 \
        --taxrule 12 [--konto 6837]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

API = "https://my.sevdesk.de/api/v1"
TOKEN_DATEI = Path.home() / ".secrets" / "sevdesk_api_token"

#: GET /TaxRule, verifiziert 2026-07-28: 9 = Vorsteuerabziehbare Aufwendungen ·
#: 12 = Reverse Charge §13b Abs. 2 Drittland · 14 = Reverse Charge §13b Abs. 1 EU.
TAXRULES_BEKANNT = {"1", "9", "12", "14"}


def token_lesen(pfad: Path = TOKEN_DATEI) -> str:
    """Datei ist KEY=WERT — die ganze Zeile als Header gibt 401 bei gültigem Token."""
    roh = pfad.read_text(encoding="utf-8").strip()
    return roh.split("=", 1)[1] if "=" in roh else roh


def _client():
    import httpx

    return httpx.Client(
        base_url=API, headers={"Authorization": token_lesen()}, timeout=30
    )


def konto_aufloesen(client, nummer: str) -> dict | None:
    """AccountDatev-Objekt zur KONTONUMMER — eindeutig oder gar nicht (nie raten)."""
    r = client.get("/AccountDatev", params={"limit": 1000})
    r.raise_for_status()
    treffer = [o for o in r.json()["objects"] if str(o.get("number")) == str(nummer)]
    if len(treffer) != 1:
        print(f"⚠ Konto {nummer}: {len(treffer)} AccountDatev-Treffer — Feld bleibt leer.")
        return None
    return {"id": treffer[0]["id"], "objectName": "AccountDatev"}


def duplikat(client, beschreibung: str) -> str | None:
    """Bestehenden Beleg mit identischer description finden (Bestand, neueste 500)."""
    r = client.get(
        "/Voucher",
        params={"limit": 500, "offset": 0, "order[create]": "desc", "embed": ""},
    )
    r.raise_for_status()
    for v in r.json()["objects"]:
        if (v.get("description") or "").strip() == beschreibung:
            return v["id"]
    return None


def _dd_mm_yyyy(iso: str) -> str:
    """2026-08-06 -> 06.08.2026 (Format laut OpenAPI-Beispiel 01.01.2022)."""
    j, m, t_ = iso.split("-")
    return f"{t_}.{m}.{j}"


def anlegen(args) -> int:
    brutto = round(float(args.brutto), 2)
    steuer = round(float(args.steuer), 2)
    netto = round(brutto - steuer, 2)
    if abs((netto + steuer) - brutto) > 0.01:
        print("ABBRUCH: netto+steuer != brutto — Plausibilitätsprobe verletzt.")
        return 2
    if args.taxrule not in TAXRULES_BEKANNT:
        print(f"ABBRUCH: taxRule {args.taxrule} nicht in {sorted(TAXRULES_BEKANNT)}.")
        return 2

    client = _client()
    vorhanden = duplikat(client, args.beschreibung)
    if vorhanden:
        print(f"DUPLIKAT: description '{args.beschreibung}' existiert als Beleg {vorhanden} — nichts angelegt.")
        return 0

    pdf = Path(args.pdf)
    up = client.post(
        "/Voucher/Factory/uploadTempFile",
        files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")},
    )
    up.raise_for_status()
    intern = up.json()["objects"]["filename"]

    konto = konto_aufloesen(client, args.konto) if args.konto else None
    steuersatz = round(steuer / netto * 100, 0) if netto and steuer else 0.0
    daten = {
        "voucher[objectName]": "Voucher",
        "voucher[mapAll]": "true",
        "voucher[voucherDate]": args.datum,
        "voucher[supplierName]": args.lieferant,
        "voucher[description]": args.beschreibung,
        "voucher[status]": "50",
        "voucher[creditDebit]": "C",
        "voucher[voucherType]": "VOU",
        "voucher[currency]": args.waehrung,
        # Fremdwaehrung (OpenAPI-Spec): propertyForeignCurrencyDeadline laesst sevdesk
        # den offiziellen Kurs zum Stichtag setzen — kein Kurs-Raten. Alternativ
        # propertyExchangeRate (NICHT propExchangeRate — der 500-Fehler des Probelaufs
        # 2026-08-07 kam vom falschen Feldnamen). Deadline gewinnt laut Spec.
        **({"voucher[propertyForeignCurrencyDeadline]": _dd_mm_yyyy(args.datum)}
           if args.waehrung != "EUR" and not args.kurs else {}),
        **({"voucher[propertyExchangeRate]": args.kurs} if args.kurs else {}),
        "voucher[taxRule][id]": args.taxrule,
        "voucher[taxRule][objectName]": "TaxRule",
        "voucherPosSave[0][objectName]": "VoucherPos",
        "voucherPosSave[0][mapAll]": "true",
        "voucherPosSave[0][taxRate]": f"{steuersatz:g}",
        "voucherPosSave[0][net]": "false",
        "voucherPosSave[0][sumNet]": f"{netto:.2f}",
        "voucherPosSave[0][sumTax]": f"{steuer:.2f}",
        "voucherPosSave[0][sumGross]": f"{brutto:.2f}",
        "voucherPosSave[0][comment]": args.lieferant,
        "filename": intern,
    }
    if konto:
        daten["voucherPosSave[0][accountDatev][id]"] = str(konto["id"])
        daten["voucherPosSave[0][accountDatev][objectName]"] = "AccountDatev"

    r = client.post("/Voucher/Factory/saveVoucher", data=daten)
    r.raise_for_status()
    beleg = r.json()["objects"]["voucher"]
    print(
        json.dumps(
            {
                "beleg_id": beleg["id"],
                "status": beleg["status"],
                "beschreibung": args.beschreibung,
                "brutto": f"{brutto:.2f}",
                "konto": args.konto or "LEER (nicht zugeordnet — Owner)",
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--pdf", required=True)
    p.add_argument("--lieferant", required=True)
    p.add_argument("--datum", required=True, help="YYYY-MM-DD (Rechnungsdatum)")
    p.add_argument("--brutto", required=True)
    p.add_argument("--steuer", required=True, help="enthaltene USt in EUR (0.00 bei Reverse Charge)")
    p.add_argument("--beschreibung", required=True, help="Rechnungsnummer/eindeutige Kennung (Dedup-Schlüssel)")
    p.add_argument("--taxrule", default="9", help="9 DE-Vorsteuer · 12 Drittland RC · 14 EU RC")
    p.add_argument("--konto", default="", help="Kontonummer NUR wenn Owner-zugeordnet; sonst leer lassen")
    p.add_argument("--waehrung", default="EUR", help="Rechnungswährung, z.B. USD (Beträge dann in dieser Währung)")
    p.add_argument("--kurs", default="", help="optional: fester Kurs (propertyExchangeRate); ohne Angabe setzt sevdesk den Stichtagskurs selbst")
    return anlegen(p.parse_args())


if __name__ == "__main__":
    sys.exit(main())
