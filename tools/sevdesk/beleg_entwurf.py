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

## Erweiterungen K6 (platform#3102) — Vorschlag statt Raten, Validierung, Messung

Alle vier Punkte sind Zusatzoptionen; ein Aufruf ohne sie verhält sich exakt wie oben.

- ``--konto-vorschlag``: schlägt bis zu drei Konten vor (Regeln aus
  ``~/.claude/sevdesk-konten.json`` zuerst, dann ``GET /ReceiptGuidance/forExpense``
  über Wortüberschneidung mit der Beschreibung — lokal gecacht 30 Tage unter
  ``~/.claude/sevdesk-receipt-guidance.json``). **Der Vorschlag setzt nie selbst ein
  Konto** — ohne ``--konto`` bleibt das Feld wie bisher leer, der Vorschlag steht nur
  in Ausgabe und Journal. Owner bestätigt über ``--konto``.
- Ist ``--konto`` gesetzt, prüft ``GET /ReceiptGuidance/forAccountNumber``, ob das Konto
  existiert und die gewählte ``--taxrule`` dort erlaubt ist; sonst Abbruch außer
  ``--trotzdem``.
- Dedup-Softcheck: zusätzlich zur harten description-Prüfung ein Warnhinweis bei
  gleichem Bruttobetrag + gleichem Datum (+ gleichem Lieferanten, falls angegeben)
  unter den letzten 500 Belegen — Dauerrechnungen mit gleichem Betrag sind legitim,
  darum nur Warnung; ``--strikt`` macht daraus einen Abbruch.
- ``--dry-run``: alle Prüfungen/Vorschläge laufen, es wird nichts hochgeladen oder
  angelegt (kein POST). ``--auswertung [N]``: legt nichts an, liest stattdessen
  ``~/.claude/sevdesk-belege-journal.jsonl`` und gibt die Trefferquote
  Vorschlag-1 / Vorschlag-in-Top-3 über die letzten N Läufe aus (K6-Messpunkt).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

API = "https://my.sevdesk.de/api/v1"
TOKEN_DATEI = Path.home() / ".secrets" / "sevdesk_api_token"

#: Personenbezogene Kontenzuordnung des Owners — NIE ins Repo, Vorlage daneben.
KONTEN_DATEI = Path.home() / ".claude" / "sevdesk-konten.json"
#: Lokaler Cache für GET /ReceiptGuidance/forExpense (ein API-Call pro Tag reicht).
GUIDANCE_CACHE = Path.home() / ".claude" / "sevdesk-receipt-guidance.json"
GUIDANCE_MAX_ALTER_TAGE = 30
#: Messjournal (K6) — Beschreibung nur gehasht, nie im Klartext.
JOURNAL_DATEI = Path.home() / ".claude" / "sevdesk-belege-journal.jsonl"
#: Wörter kürzer als das zählen nicht als Treffer gegen eine Kontobezeichnung.
WORT_MIN_LAENGE = 4

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
        print(
            f"⚠ Konto {nummer}: {len(treffer)} AccountDatev-Treffer — Feld bleibt leer."
        )
        return None
    return {"id": treffer[0]["id"], "objectName": "AccountDatev"}


def konto_validieren(client, konto: str, taxrule: str) -> tuple[bool, str]:
    """Prüft Konto + taxRule gegen GET /ReceiptGuidance/forAccountNumber.

    Kein Ersatz für ``konto_aufloesen`` (das bleibt die Quelle für die
    AccountDatev-ID) — dies ist die zusätzliche fachliche Prüfung: existiert das
    Konto laut Guidance, und passt die gewählte Steuerregel dazu.
    """
    r = client.get("/ReceiptGuidance/forAccountNumber", params={"accountNumber": konto})
    if r.status_code == 422:
        return False, f"Konto {konto}: sevdesk kennt dieses Konto nicht (422)."
    r.raise_for_status()
    objekte = r.json().get("objects") or []
    if not objekte:
        return False, f"Konto {konto}: keine ReceiptGuidance-Daten gefunden."
    erlaubt = {
        str(regel["id"]) for o in objekte for regel in (o.get("allowedTaxRules") or [])
    }
    if str(taxrule) not in erlaubt:
        return False, (
            f"Konto {konto}: taxRule {taxrule} laut ReceiptGuidance nicht erlaubt "
            f"(erlaubt: {sorted(erlaubt)})."
        )
    return True, ""


def beleg_bestand(client) -> list[dict]:
    """Letzte 500 Belege — Grundlage für Dedup (description) und Softcheck."""
    r = client.get(
        "/Voucher",
        params={"limit": 500, "offset": 0, "order[create]": "desc", "embed": ""},
    )
    r.raise_for_status()
    return r.json()["objects"]


def duplikat(belege: list[dict], beschreibung: str) -> str | None:
    """Bestehenden Beleg mit identischer description finden (harter Dedup, K5)."""
    for v in belege:
        if (v.get("description") or "").strip() == beschreibung:
            return v["id"]
    return None


def dedup_softcheck(
    belege: list[dict], brutto: float, datum: str, lieferant: str | None
) -> str | None:
    """Warnt bei gleichem Bruttobetrag + Datum (+ Lieferant) unter anderer description.

    Dauerrechnungen mit identischem Betrag sind legitim — deshalb nur ein Warnhinweis,
    kein automatischer Abbruch (den erzwingt ausschließlich ``--strikt``).
    """
    for v in belege:
        try:
            gross = round(float(v.get("sumGross") or 0), 2)
        except (TypeError, ValueError):
            continue
        if gross != brutto:
            continue
        if (v.get("voucherDate") or "")[:10] != datum:
            continue
        if lieferant:
            bestand_lieferant = (v.get("supplierName") or "").strip().lower()
            if bestand_lieferant != lieferant.strip().lower():
                continue
        return v["id"]
    return None


def regeln_laden(pfad: Path) -> list[dict]:
    """Owner-Kontenzuordnung (Lieferant/Beschreibung → Konto) — Vorlage im Repo,
    echte Datei personenbezogen unter ``~/.claude`` (nie ins Repo)."""
    if not pfad.exists():
        return []
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return daten.get("regeln") or []


def guidance_laden(
    client,
    cache_pfad: Path,
    max_alter_tage: int = GUIDANCE_MAX_ALTER_TAGE,
    heute: date | None = None,
) -> list[dict]:
    """GET /ReceiptGuidance/forExpense, lokal gecacht (Alter > max_alter_tage → neu)."""
    heute = heute or date.today()
    if cache_pfad.exists():
        try:
            cache = json.loads(cache_pfad.read_text(encoding="utf-8"))
            alter = (heute - date.fromisoformat(cache["datum"])).days
            if alter <= max_alter_tage:
                return cache["objects"]
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    r = client.get("/ReceiptGuidance/forExpense")
    r.raise_for_status()
    objekte = r.json().get("objects") or []
    cache_pfad.parent.mkdir(parents=True, exist_ok=True)
    cache_pfad.write_text(
        json.dumps(
            {"datum": heute.isoformat(), "objects": objekte}, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    return objekte


#: Rechtsformen etc. — stehen in praktisch jedem Lieferantennamen und wären sonst ein
#: Treffer gegen JEDE Kontobezeichnung, die zufällig dasselbe Wort enthält (Echtprobe
#: 2026-09-12: "gmbh" aus "Synthetik-Test GmbH" traf "... GmbH-Gesellschafter").
STOPWOERTER = {"gmbh", "mbh", "haftungsbeschraenkt"}


def _woerter(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[a-zäöüß]+", text.lower())
        if len(w) >= WORT_MIN_LAENGE and w not in STOPWOERTER
    }


def vorschlaege(
    lieferant: str, beschreibung: str, regeln: list[dict], guidance: list[dict]
) -> list[dict]:
    """Bis zu drei Kontovorschläge: Regel-Treffer zuerst, dann Guidance über Wortmatch.

    Setzt NIE selbst ein Konto — reine Entscheidungshilfe für den Owner.
    """
    haystack = f"{lieferant} {beschreibung}".lower()
    ergebnis: list[dict] = []
    gesehene_konten: set[str] = set()

    for regel in regeln:
        muster = regel.get("muster", "")
        if not muster or not re.search(muster, haystack):
            continue
        konto = str(regel.get("konto", "")).strip()
        if not konto or konto in gesehene_konten:
            continue
        begruendung = f"Regel '{muster}' trifft"
        if regel.get("anmerkung"):
            begruendung += f" ({regel['anmerkung']})"
        ergebnis.append(
            {
                "konto": konto,
                "bezeichnung": regel.get("bezeichnung", ""),
                "quelle": "Regel",
                "begruendung": begruendung,
            }
        )
        gesehene_konten.add(konto)
        if len(ergebnis) >= 3:
            return ergebnis

    woerter = _woerter(f"{lieferant} {beschreibung}")
    if woerter:
        kandidaten = []
        for obj in guidance:
            name = str(obj.get("accountName", ""))
            beschr = str(obj.get("description", ""))
            treffer = woerter & _woerter(f"{name} {beschr}")
            if not treffer:
                continue
            konto = str(obj.get("accountNumber", "")).strip()
            if not konto or konto in gesehene_konten:
                continue
            kandidaten.append((len(treffer), konto, name, sorted(treffer)))
        kandidaten.sort(key=lambda t: (-t[0], t[1]))
        for _, konto, name, treffer_woerter in kandidaten:
            if len(ergebnis) >= 3:
                break
            ergebnis.append(
                {
                    "konto": konto,
                    "bezeichnung": name,
                    "quelle": "Guidance",
                    "begruendung": f"Kontobezeichnung enthält {', '.join(treffer_woerter)}",
                }
            )
            gesehene_konten.add(konto)

    return ergebnis


def _journal_zeile(
    args,
    *,
    konto_gesetzt: bool,
    vorschlaege_liste: list[dict],
    dedup_treffer: str | None,
    dauer_s: float,
) -> dict:
    vorschlag_konten = [v["konto"] for v in vorschlaege_liste]
    return {
        "zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "beschreibung_hash": hashlib.sha256(
            args.beschreibung.encode("utf-8")
        ).hexdigest()[:16],
        "konto_gesetzt": konto_gesetzt,
        "vorschlaege": vorschlag_konten,
        "vorschlag_treffer_1": bool(args.konto)
        and bool(vorschlag_konten)
        and args.konto == vorschlag_konten[0],
        "vorschlag_top3": bool(args.konto) and args.konto in vorschlag_konten,
        "taxrule": args.taxrule,
        "dedup_treffer": dedup_treffer,
        "dauer_s": round(dauer_s, 3),
    }


def journal_schreiben(zeile: dict, pfad: Path) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as f:
        f.write(json.dumps(zeile, ensure_ascii=False) + "\n")


def auswertung_text(pfad: Path, n: int | None) -> str:
    """K6-Messpunkt: Trefferquote Vorschlag-1 / Vorschlag-in-Top-3 über die letzten N."""
    if not pfad.exists():
        return "Kein Journal vorhanden — noch kein Lauf protokolliert."
    zeilen = [
        json.loads(z)
        for z in pfad.read_text(encoding="utf-8").splitlines()
        if z.strip()
    ]
    if n is not None:
        zeilen = zeilen[-n:]
    vergleichbar = [
        z for z in zeilen if z.get("konto_gesetzt") and z.get("vorschlaege")
    ]
    basis = len(vergleichbar)
    if basis == 0:
        return (
            f"Keine vergleichbaren Läufe (Konto gesetzt UND Vorschlag vorhanden) "
            f"unter {len(zeilen)} Journal-Zeilen."
        )
    treffer_1 = sum(1 for z in vergleichbar if z.get("vorschlag_treffer_1"))
    treffer_top3 = sum(1 for z in vergleichbar if z.get("vorschlag_top3"))
    return (
        f"Basis: {basis} vergleichbare Läufe von {len(zeilen)} Journal-Zeilen.\n"
        f"Vorschlag-1-Trefferquote: {treffer_1}/{basis} ({treffer_1 / basis:.0%})\n"
        f"Vorschlag-in-Top-3-Trefferquote: {treffer_top3}/{basis} "
        f"({treffer_top3 / basis:.0%})"
    )


def _dd_mm_yyyy(iso: str) -> str:
    """2026-08-06 -> 06.08.2026 (Format laut OpenAPI-Beispiel 01.01.2022)."""
    j, m, t_ = iso.split("-")
    return f"{t_}.{m}.{j}"


def anlegen(args) -> int:
    start = time.monotonic()
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
    belege = beleg_bestand(client)

    vorhanden = duplikat(belege, args.beschreibung)
    if vorhanden:
        print(
            f"DUPLIKAT: description '{args.beschreibung}' existiert als Beleg "
            f"{vorhanden} — nichts angelegt."
        )
        journal_schreiben(
            _journal_zeile(
                args,
                konto_gesetzt=False,
                vorschlaege_liste=[],
                dedup_treffer=vorhanden,
                dauer_s=time.monotonic() - start,
            ),
            JOURNAL_DATEI,
        )
        return 0

    weich_treffer = dedup_softcheck(belege, brutto, args.datum, args.lieferant or None)
    if weich_treffer:
        meldung = (
            f"Beleg {weich_treffer}: gleicher Bruttobetrag {brutto:.2f} EUR am "
            f"gleichen Datum {args.datum}"
            + (" mit gleichem Lieferanten" if args.lieferant else "")
            + " — Dauerrechnungen mit gleichem Betrag sind legitim, darum nur Warnung."
        )
        if args.strikt:
            print(f"ABBRUCH (--strikt): {meldung}")
            journal_schreiben(
                _journal_zeile(
                    args,
                    konto_gesetzt=False,
                    vorschlaege_liste=[],
                    dedup_treffer=weich_treffer,
                    dauer_s=time.monotonic() - start,
                ),
                JOURNAL_DATEI,
            )
            return 2
        print(f"WARNUNG: {meldung}")

    vorschlaege_liste: list[dict] = []
    if args.konto_vorschlag:
        guidance = guidance_laden(client, GUIDANCE_CACHE)
        regeln = regeln_laden(KONTEN_DATEI)
        vorschlaege_liste = vorschlaege(
            args.lieferant, args.beschreibung, regeln, guidance
        )
        if vorschlaege_liste:
            print("Kontovorschläge (Bestätigung nötig — nie automatisch gesetzt):")
            for i, v in enumerate(vorschlaege_liste, 1):
                print(
                    f"  {i}. Konto {v['konto']} ({v['bezeichnung']}) — "
                    f"{v['begruendung']} [{v['quelle']}]"
                )
        else:
            print("Kontovorschlag: keine Treffer (Regel/Guidance) — Konto bleibt leer.")

    konto = None
    if args.konto:
        ok, fehler = konto_validieren(client, args.konto, args.taxrule)
        if not ok:
            if args.trotzdem:
                print(f"WARNUNG (--trotzdem): {fehler}")
            else:
                print(f"ABBRUCH: {fehler}")
                journal_schreiben(
                    _journal_zeile(
                        args,
                        konto_gesetzt=False,
                        vorschlaege_liste=vorschlaege_liste,
                        dedup_treffer=weich_treffer,
                        dauer_s=time.monotonic() - start,
                    ),
                    JOURNAL_DATEI,
                )
                return 2
        konto = konto_aufloesen(client, args.konto)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "beschreibung": args.beschreibung,
                    "brutto": f"{brutto:.2f}",
                    "taxrule": args.taxrule,
                    "konto": args.konto or "LEER (nicht zugeordnet — Owner)",
                    "vorschlaege": vorschlaege_liste,
                },
                ensure_ascii=False,
            )
        )
        journal_schreiben(
            _journal_zeile(
                args,
                konto_gesetzt=bool(konto),
                vorschlaege_liste=vorschlaege_liste,
                dedup_treffer=weich_treffer,
                dauer_s=time.monotonic() - start,
            ),
            JOURNAL_DATEI,
        )
        return 0

    pdf = Path(args.pdf)
    up = client.post(
        "/Voucher/Factory/uploadTempFile",
        files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")},
    )
    up.raise_for_status()
    intern = up.json()["objects"]["filename"]

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
        **(
            {"voucher[propertyForeignCurrencyDeadline]": _dd_mm_yyyy(args.datum)}
            if args.waehrung != "EUR" and not args.kurs
            else {}
        ),
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
    journal_schreiben(
        _journal_zeile(
            args,
            konto_gesetzt=bool(konto),
            vorschlaege_liste=vorschlaege_liste,
            dedup_treffer=weich_treffer,
            dauer_s=time.monotonic() - start,
        ),
        JOURNAL_DATEI,
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--pdf")
    p.add_argument("--lieferant")
    p.add_argument("--datum", help="YYYY-MM-DD (Rechnungsdatum)")
    p.add_argument("--brutto")
    p.add_argument(
        "--steuer",
        help="enthaltene USt in EUR (0.00 bei Reverse Charge)",
    )
    p.add_argument(
        "--beschreibung",
        help="Rechnungsnummer/eindeutige Kennung (Dedup-Schlüssel)",
    )
    p.add_argument(
        "--taxrule", default="9", help="9 DE-Vorsteuer · 12 Drittland RC · 14 EU RC"
    )
    p.add_argument(
        "--konto",
        default="",
        help="Kontonummer NUR wenn Owner-zugeordnet; sonst leer lassen",
    )
    p.add_argument(
        "--waehrung",
        default="EUR",
        help="Rechnungswährung, z.B. USD (Beträge dann in dieser Währung)",
    )
    p.add_argument(
        "--kurs",
        default="",
        help="optional: fester Kurs (propertyExchangeRate); ohne Angabe setzt sevdesk den Stichtagskurs selbst",
    )
    p.add_argument(
        "--konto-vorschlag",
        action="store_true",
        dest="konto_vorschlag",
        help="bis zu 3 Kontovorschläge ausgeben (Regeln + ReceiptGuidance) — setzt nie selbst ein Konto",
    )
    p.add_argument(
        "--trotzdem",
        action="store_true",
        help="Validierung von --konto (ReceiptGuidance) ignorieren und trotzdem anlegen",
    )
    p.add_argument(
        "--strikt",
        action="store_true",
        help="Dedup-Softcheck (Betrag+Datum+Lieferant) bricht ab statt nur zu warnen",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="alle Prüfungen/Vorschläge laufen, es wird nichts hochgeladen oder angelegt",
    )
    p.add_argument(
        "--auswertung",
        nargs="?",
        const="alle",
        default=None,
        metavar="N",
        help="legt nichts an — gibt die Vorschlag-Trefferquote der letzten N Journal-Läufe aus (ohne N: alle)",
    )
    args = p.parse_args()

    if args.auswertung is not None:
        n = None if args.auswertung == "alle" else int(args.auswertung)
        print(auswertung_text(JOURNAL_DATEI, n))
        return 0

    pflicht = {
        "--pdf": args.pdf,
        "--lieferant": args.lieferant,
        "--datum": args.datum,
        "--brutto": args.brutto,
        "--steuer": args.steuer,
        "--beschreibung": args.beschreibung,
    }
    fehlend = [name for name, wert in pflicht.items() if not wert]
    if fehlend:
        p.error(f"the following arguments are required: {', '.join(fehlend)}")

    return anlegen(args)


if __name__ == "__main__":
    sys.exit(main())
