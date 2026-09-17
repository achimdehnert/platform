#!/usr/bin/env python3
"""Kostenabgleich: Bankabgaenge gegen offene Belege, Kontovorschlag — K7 aus platform#3102.

Warum es das gibt: Jeder Abgang auf dem Geschaeftskonto braucht frueher oder
spaeter einen Beleg und ein Buchungskonto. Von Hand ist das muehsam, sobald
Dutzende wiederkehrender Kosten (Miete, Lizenzen, Abos) dazukommen. Dieses
Werkzeug macht sichtbar, was sich automatisch sicher zuordnen laesst, was
einen Owner-Blick braucht und wo schlicht ein Beleg fehlt — read-only per
Standardlauf, Buchen ausschliesslich mit ``--buchen --ja`` und ausschliesslich
fuer **sichere** Zuordnungen.

    python3 tools/sevdesk/kostenabgleich.py                  # 120 Tage, Markdown
    python3 tools/sevdesk/kostenabgleich.py --tage 60        # engeres Fenster
    python3 tools/sevdesk/kostenabgleich.py --mandant edv    # zweiter Mandant (K8)
    python3 tools/sevdesk/kostenabgleich.py --json           # maschinenlesbar
    python3 tools/sevdesk/kostenabgleich.py --buchen         # Vorschau, bucht NICHTS
    python3 tools/sevdesk/kostenabgleich.py --buchen --ja    # bucht die sicheren Faelle

Drei Zuordnungsstufen je Bankabgang (Betrag < 0, Status 100 = unverbucht):

- **Beleg vorhanden (buchbar)**: genau EIN offener Beleg (Status 50/100,
  ``creditDebit`` = C) trifft den Betrag auf 1 Cent genau, teilt ein Wort
  (>= 4 Zeichen, ohne Fuellwoerter gmbh/mbh/ag/kg) mit dem Lieferantennamen
  und liegt maximal 14 Tage vom Abgang entfernt.
- **Unklar**: der Betrag trifft, aber kein Name passt eindeutig, oder mehrere
  Belege kommen infrage — Owner-Blick noetig.
- **Beleg fehlt**: kein offener Beleg trifft den Betrag ueberhaupt.
- **Intern** (vierte Stufe, 2026-09-17): kein Lieferantenbeleg noetig — die
  Regel in ``sevdesk-konten.json`` traegt ``"beleg": "ohne_dokument"`` (Lohn,
  Sozialversicherung, Kontofuehrung, Privatentnahme). Das Werkzeug legt den
  Beleg selbst an (Status 100, Konto/Steuerregel aus der Regel, Steuerregel
  vorher gegen ``ReceiptGuidance/forAccountNumber`` geprueft) und bucht ihn
  mit Zahldatum = Umsatzdatum. **Gebucht wird nur mit Mandat**: die Regel
  traegt ``"autonom": true`` — das ist das stehende Owner-Wort je
  Regelklasse; ohne Mandat steht die Position sichtbar unter „intern", wird
  aber nie geschrieben. ``nur_betraege`` gilt weiter: ein Betrag ausserhalb
  der Liste bleibt „Beleg fehlt" (Sammelueberweisung mit Fremdposten).
  Sonderklasse ``"klasse": "kontoabschluss_paar"``: Gebuehr-Zeile und
  USt-Zeile der Bank werden zu EINEM Beleg (netto = Gebuehr, USt = Bankzeile
  1:1, nie 19 % gerechnet — Owner-Wort 2026-09-17) mit zwei Teilbuchungen
  Typ N; Zuordnung ueber „per DD.MM.YYYY" im Zweck, bei Bank-Tippfehler ueber
  die Bemessungsgrundlage. Eine Gebuehr ohne USt-Zeile wartet.

**Betragstoleranz** (2026-09-17): Ein Beleg trifft auch bei 2 Cent Rundung
(Hetzner 133,99 ↔ 134,00) und bei Fremdwaehrungsbelegen bis 8 % Kursdifferenz
(GitHub 181,10 USD: 156,83 EUR Beleg ↔ 164,71 EUR Bank). Gebucht wird dann
per ``bookAmount`` Typ O mit dem **Bank**betrag — FULL_PAYMENT antwortet bei
jeder Abweichung 422 (Lehre 2026-09-13); paidAmount wird der Belegbetrag, der
Beleg 1000, der Umsatz 400.

**Wiederkehrend**: Abgaenge mit gleichem normalisiertem Zahler und Betrag
(Toleranz 0,50 EUR) in mindestens zwei aufeinanderfolgenden Kalendermonaten
werden in allen drei Listen als "wiederkehrend (nx)" markiert. Fehlt bei einer
solchen Serie ausgerechnet in diesem Monat der Beleg, obwohl ein frueherer
Monat der Serie einen hatte, wird das zusaetzlich vermerkt ("Beleg fuer diesen
Monat fehlt").

**Kontovorschlag** je Position: zuerst eine Regel aus
``~/.claude/sevdesk-konten.json`` (wiederverwendet aus ``bankpositionen.py``),
sonst bis zu zwei Treffer aus ``GET /ReceiptGuidance/forExpense``, deren
Kontoname/-beschreibung mit dem Zahlernamen (nicht dem Verwendungszweck —
der hat zu viele Fuellwoerter, K7-Fix platform#3102) mindestens zwei
gemeinsame Woerter oder ein einzelnes Wort ab 7 Zeichen ausserhalb der
Stoppliste teilt; kein Treffer -> "—".

K8 (zweiter Mandant): ``--mandant iil|edv`` (Standard iil) waehlt den
sevdesk-Zugang ueber ``mandant.py``; gleichwertig per Umgebungsvariable
``SEVDESK_MANDANT``.

Fallen (siehe auch ``tools/sevdesk/README.md``):

- ``--buchen`` ohne ``--ja`` zeigt nur, was gebucht wuerde; ``bookAmount``
  wird in KEINEM Fall aufgerufen.
- ``--buchen --ja`` bucht die Stufe "Beleg vorhanden" und "intern" **mit
  Mandat** (``"autonom": true``) — sonst nichts.
- Wiederholung bucht nie doppelt: eine bereits verbuchte/verknuepfte
  Bank-Transaktion (Status != 100) taucht bei einem erneuten Lauf nicht mehr
  unter den offenen Abgaengen auf — derselbe Mechanismus wie in
  ``zahlungsabgleich.py``.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bankpositionen import KONTEN_DATEI, konten_laden, kurz, paypal_haendler  # noqa: E402
from bankpositionen import regel_treffer  # noqa: E402
from bankpositionen import zuordnen as regel_zuordnen  # noqa: E402
from mandant import client, mandant_argument  # noqa: E402

#: CheckAccountTransaction-Status: 100 = unverbucht/offen (siehe bankpositionen.py).
STATUS_TX_OFFEN = "100"

#: Voucher-Status (Model_Voucher, OpenAPI): 50 Entwurf, 100 offen/unbezahlt,
#: 1000 bezahlt. Nur 50/100 kommen als "noch zu buchender Beleg" infrage.
VOUCHER_STATUS_OFFEN = {"50", "100"}

CREDIT = "C"  # Lieferantenbeleg (Ausgabe), s. beleg_entwurf.py

LOG_VERZEICHNIS = Path.home() / ".claude"
STANDARD_ZIEL = Path.home() / ".claude" / "boards" / "sevdesk-kostenabgleich.md"

#: Fuellwoerter, die beim Namensvergleich (Zahler <-> Lieferant) ignoriert
#: werden — sonst haelt "GmbH" jede Firma fuer denselben Zahler.
FUELLWOERTER = {"gmbh", "mbh", "ag", "kg"}
RE_WORT = re.compile(r"[A-Za-zÄÖÜäöüß]+")

#: Zusaetzliche Stoppwoerter fuer den ReceiptGuidance-Abgleich (guidance_treffer,
#: K7-Fix platform#3102) — Rechtsformen/Fuellwoerter, die in praktisch jedem
#: Firmennamen auftauchen und deshalb allein keinen Kontovorschlag rechtfertigen.
#: Woerter mit <= 3 Zeichen sind ueber ``worte()`` ohnehin schon ausgeschlossen.
GUIDANCE_STOPPWOERTER = FUELLWOERTER | {
    "service",
    "services",
    "inc",
    "ltd",
    "llc",
    "limited",
    "online",
    "payment",
    "payments",
    "europe",
    "deutschland",
    "germany",
    "sarl",
    "cie",
    "holdings",
    "holding",
}

#: Ab dieser Laenge rechtfertigt ein EINZELNES gemeinsames Wort (ausserhalb
#: der Stoppliste) allein schon einen Guidance-Vorschlag.
GUIDANCE_MIN_EINZELWORT = 7

#: Datum-Toleranz fuer eine sichere Zuordnung.
TAGE_TOLERANZ = 14
#: Betrags-Toleranz fuer die Wiederkehrend-Erkennung (Miete/Abo schwankt
#: gelegentlich um Cent-Betraege, z. B. Rundung oder Index-Anpassung).
BETRAG_TOLERANZ_WIEDERKEHREND = 0.50

#: Cent-Rundung zwischen Beleg (aus dem PDF gelesen) und Bankabgang — Hetzner
#: 133,99 ↔ 134,00 und 124,22 ↔ 124,23 (Echtprobe 2026-09-17). Bis hier gilt der
#: Beleg als Treffer; gebucht wird dann per Typ O mit dem Bankbetrag.
BETRAG_TOLERANZ_CENT = 0.02
#: Fremdwaehrungsbelege (USD): sevdesk rechnet mit dem Stichtagskurs, PayPal mit
#: seinem eigenen — GitHub 181,10 USD = 156,83 EUR Beleg gegen 164,71 EUR Bank (5 %).
#: FULL_PAYMENT gibt bei jeder Abweichung 422, durch geht nur Typ O mit dem
#: Bankbetrag (Lehre 2026-09-13). Anteilige Toleranz, nur bei currency != EUR.
BETRAG_TOLERANZ_FREMDWAEHRUNG = 0.08

#: Vierte Zuordnungsstufe: kein Lieferantenbeleg noetig (Lohn, Sozialversicherung,
#: Kontofuehrung, Privatentnahme) — die Regel in sevdesk-konten.json traegt
#: ``"beleg": "ohne_dokument"`` und das Werkzeug legt den Beleg selbst an.
STATUS_INTERN = "intern"
BELEG_OHNE_DOKUMENT = "ohne_dokument"
#: Sonderklasse: die Bank bucht Kontogebuehr und 19 % USt darauf als ZWEI Zeilen
#: (Gebuehr am Monatsende, USt sechs Wochen spaeter). Ein Beleg fuer beide —
#: netto = Gebuehr, USt = Bankzeile 1:1 —, zwei Teilbuchungen Typ N. Vorbild:
#: Owner-Beleg 100430331 (11/2024). Owner-Wort 2026-09-17: die Gebuehr traegt
#: keine USt, die zweite Zeile ist ausschliesslich USt — nie 19 % draufrechnen.
KLASSE_KONTOABSCHLUSS = "kontoabschluss_paar"
RE_PER_DATUM = re.compile(r"per (\d\d\.\d\d\.\d{4})", re.IGNORECASE)


def worte(text: str) -> set[str]:
    return {
        w.lower()
        for w in RE_WORT.findall(text or "")
        if len(w) >= 4 and w.lower() not in FUELLWOERTER
    }


def hole(client_, pfad: str, **params) -> list[dict]:
    """Blaettert vollstaendig durch (sevdesk liefert maximal 200 je Anfrage)."""
    ergebnis: list[dict] = []
    offset = 0
    while True:
        r = client_.get(pfad, params=dict(params, limit=200, offset=offset))
        r.raise_for_status()
        seite = r.json().get("objects") or []
        ergebnis += seite
        if len(seite) < 200:
            return ergebnis
        offset += 200


def voucher_offener_betrag(v: dict) -> float:
    brutto = float(v.get("sumGross") or 0)
    bezahlt = float(v.get("paidAmount") or 0)
    return round(brutto - bezahlt, 2)


def _datum(roh: str) -> dt.date | None:
    roh = (roh or "")[:10]
    if not roh:
        return None
    try:
        return dt.date.fromisoformat(roh)
    except ValueError:
        return None


def zahler_anzeige(name: str, zweck: str) -> str:
    """PayPal nennt den echten Haendler im Zweck — wie in bankpositionen.py."""
    if "paypal" in f"{name} {zweck}".lower():
        haendler = paypal_haendler(zweck)
        if haendler:
            return haendler
    return name


def monat_schluessel(datum: dt.date) -> str:
    return f"{datum.year:04d}-{datum.month:02d}"


def _monat_diff(a: str, b: str) -> int:
    ya, ma = (int(x) for x in a.split("-"))
    yb, mb = (int(x) for x in b.split("-"))
    return (yb * 12 + mb) - (ya * 12 + ma)


def guidance_treffer(
    guidance: list[dict], zahler: str, max_n: int = 2
) -> list[tuple[str, str, str]]:
    """(kontonummer, kontoname, treffer_wort) je Vorschlag, bis zu max_n.

    Geht ausschliesslich vom Zahlernamen aus — NICHT vom Verwendungszweck,
    der bei Bankueberweisungen zu viele Fuellwoerter enthaelt und sonst
    Fehltreffer erzeugt (K7-Fix platform#3102: "Beispiel Hosting GmbH" wurde
    ueber ein Fuellwort im Zweck faelschlich "Freiwillige soziale
    Aufwendungen" zugeordnet). Ein Treffer zaehlt nur, wenn mindestens zwei
    gemeinsame Woerter uebrig bleiben oder ein einzelnes Wort ab
    ``GUIDANCE_MIN_EINZELWORT`` Zeichen ausserhalb der Stoppliste steht.
    """
    ziel = worte(zahler) - GUIDANCE_STOPPWOERTER
    treffer: list[tuple[str, str, str]] = []
    for g in guidance:
        gwort = (
            worte(f"{g.get('accountName', '')} {g.get('description', '')}")
            - GUIDANCE_STOPPWOERTER
        )
        schnitt = ziel & gwort
        einzelwort_ok = (
            len(schnitt) == 1 and len(next(iter(schnitt))) >= GUIDANCE_MIN_EINZELWORT
        )
        if schnitt and (len(schnitt) >= 2 or einzelwort_ok):
            treffer.append(
                (
                    str(g.get("accountNumber", "")),
                    g.get("accountName", ""),
                    sorted(schnitt)[0],
                )
            )
        if len(treffer) >= max_n:
            break
    return treffer


def kontovorschlag(
    regeln: list[dict], guidance: list[dict], zahler: str, zweck: str, betrag: float
) -> tuple[str, str]:
    """(vorschlag_text, grund) — zuerst Regel aus sevdesk-konten.json, sonst
    ReceiptGuidance (nur Zahlername, siehe guidance_treffer), sonst "—"."""
    konto, bez, _anm = regel_zuordnen(f"{zahler} {zweck}", betrag, regeln)
    if konto:
        text = f"{konto} — {bez}" if bez else konto
        return text, "Regel aus sevdesk-konten.json"
    treffer = guidance_treffer(guidance, zahler)
    if treffer:
        text = "; ".join(f"{nr} {name}" for nr, name, _wort in treffer)
        return text, "sevdesk-Kontenhilfe (ReceiptGuidance/forExpense)"
    return "—", ""


def name_trifft(zahler_text: str, lieferant: str) -> bool:
    return bool(worte(zahler_text) & worte(lieferant))


def zuordnen_position(
    zahler_text: str, betrag: float, datum: dt.date | None, kandidaten: list[dict]
) -> dict:
    """Ordnet EINEN Bankabgang offenen Belegen zu.

    Rueckgabe: {"status": "sicher"|"unklar"|"fehlend", "beleg": dict|None,
    "kandidaten": [...], "grund": str}
    """
    if not kandidaten:
        return {
            "status": "fehlend",
            "beleg": None,
            "kandidaten": [],
            "grund": "kein Beleg mit passendem Betrag",
        }
    sichere = [
        v
        for v in kandidaten
        if name_trifft(zahler_text, v.get("supplierName") or "")
        and datum is not None
        and _datum(v.get("voucherDate")) is not None
        and abs((datum - _datum(v.get("voucherDate"))).days) <= TAGE_TOLERANZ
    ]
    if len(sichere) == 1:
        return {
            "status": "sicher",
            "beleg": sichere[0],
            "kandidaten": sichere,
            "grund": "Betrag, Lieferant und Datum passen",
        }
    if len(sichere) > 1:
        return {
            "status": "unklar",
            "beleg": None,
            "kandidaten": sichere,
            "grund": f"{len(sichere)} Kandidaten passen zu Betrag, Lieferant und Datum",
        }
    return {
        "status": "unklar",
        "beleg": None,
        "kandidaten": kandidaten,
        "grund": "Betrag passt, Lieferant/Datum nicht eindeutig",
    }


def cluster_wiederkehrend(
    positionen: list[dict], toleranz: float = BETRAG_TOLERANZ_WIEDERKEHREND
) -> None:
    """Setzt 'wiederkehrend' (Anzahl oder None) und 'beleg_frueher_vorhanden'
    je Position — in-place, gruppiert nach normalisiertem Zahler und
    Betrags-Clustern (Toleranz), markiert Serien in >=2 aufeinanderfolgenden
    Monaten."""
    gruppen: dict[frozenset, list[dict]] = collections.defaultdict(list)
    for p in positionen:
        gruppen[p["zahler_key"]].append(p)

    for mitglieder in gruppen.values():
        mitglieder = sorted(mitglieder, key=lambda p: p["datum"])
        cluster: list[list[dict]] = []
        for p in mitglieder:
            ziel = None
            for c in cluster:
                if abs(c[-1]["betrag"] - p["betrag"]) <= toleranz:
                    ziel = c
                    break
            if ziel is None:
                cluster.append([p])
            else:
                ziel.append(p)

        for c in cluster:
            monate = sorted({p["monat"] for p in c if p["monat"]})
            aufeinanderfolgend = any(
                _monat_diff(monate[i], monate[i + 1]) == 1
                for i in range(len(monate) - 1)
            )
            if not (aufeinanderfolgend and len(c) >= 2):
                continue
            for p in c:
                p["wiederkehrend"] = len(c)
            for p in c:
                if p["status"] != "fehlend":
                    continue
                if any(q["status"] == "sicher" and q["datum"] < p["datum"] for q in c):
                    p["beleg_frueher_vorhanden"] = True


def _dd_mm_yyyy(datum: dt.date) -> str:
    return datum.strftime("%d.%m.%Y")


def _iso_zu_dd_mm_yyyy(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"


def beleg_kandidaten(belege: list[dict], betrag: float) -> list[dict]:
    """Offene Belege, deren offener Betrag den Abgang trifft: auf 2 Cent genau,
    bei Fremdwaehrungsbelegen anteilig (Kursdifferenz sevdesk ↔ PayPal)."""
    treffer = []
    for v in belege:
        diff = abs(voucher_offener_betrag(v) - betrag)
        fremd = (v.get("currency") or "EUR") != "EUR"
        if diff <= BETRAG_TOLERANZ_CENT or (
            fremd and diff <= betrag * BETRAG_TOLERANZ_FREMDWAEHRUNG
        ):
            treffer.append(v)
    return treffer


def kontoabschluss_paare(abgaenge: list[dict], regeln: list[dict]) -> dict:
    """Gebuehr-Zeile ↔ USt-Zeile derselben Kontoabrechnung.

    Rueckgabe {gebuehr_tx_id: {"partner": ust_tx, "netto", "steuer"}} plus
    ``{"_ust_ids": {...}}`` der verbrauchten USt-Zeilen. Zuordnung ueber das
    „per DD.MM.YYYY" im Zweck; fehlt das Datum auf einer Seite (die Bank schrieb
    real „per 30.02.2026"), ueber die im USt-Zweck genannte Bemessungsgrundlage.
    Ein Paar gilt nur, wenn 19 % der Gebuehr die USt-Zeile auf 1 Cent treffen.
    """
    regel = next(
        (r for r in regeln if r.get("klasse") == KLASSE_KONTOABSCHLUSS), None
    )
    if regel is None or not regel.get("ust_muster"):
        return {"_ust_ids": set()}
    ust_re = re.compile(regel["ust_muster"], re.IGNORECASE)
    gebuehr_re = re.compile(regel["muster"], re.IGNORECASE)

    gebuehren: list[dict] = []
    usts: list[tuple[dict, float, str]] = []  # (tx, basis, per)
    for t in abgaenge:
        zweck = t.get("paymtPurpose") or ""
        m = ust_re.search(zweck)
        if m:
            try:
                basis = float(m.group(1).replace(".", "").replace(",", "."))
            except (IndexError, ValueError):
                continue
            per = RE_PER_DATUM.search(zweck)
            usts.append((t, basis, per.group(1) if per else ""))
        elif gebuehr_re.search(zweck):
            gebuehren.append(t)

    paare: dict = {"_ust_ids": set()}
    for g in gebuehren:
        netto = abs(float(g.get("amount") or 0))
        per = RE_PER_DATUM.search(g.get("paymtPurpose") or "")
        per = per.group(1) if per else ""
        kand = [u for u in usts if u[0]["id"] not in paare["_ust_ids"] and per and u[2] == per]
        if not kand:
            kand = [
                u
                for u in usts
                if u[0]["id"] not in paare["_ust_ids"] and abs(u[1] - netto) <= 0.01
            ]
        if len(kand) != 1:
            continue
        u, basis, _per = kand[0]
        steuer = abs(float(u.get("amount") or 0))
        if abs(basis - netto) > 0.01 or abs(round(netto * 0.19, 2) - steuer) > 0.01:
            continue
        paare[g["id"]] = {"partner": u, "netto": netto, "steuer": steuer}
        paare["_ust_ids"].add(u["id"])
    return paare


def konto_guidance(client_, konto: str) -> tuple[str | None, set[str]]:
    """(AccountDatev-ID, erlaubte Steuerregeln) aus GET /ReceiptGuidance/forAccountNumber.

    Die ID kommt bewusst von hier und nicht aus ``GET /AccountDatev``: die Liste
    liefert nur 100 aktive Konten — 2100 Privatentnahmen (deactivated=1) fehlt
    dort, ist per Beleg aber buchbar (Echtprobe 2026-09-17, Abbruch „Konto 2100
    nicht im Kontenrahmen"). Bei einem Treffer antwortet sevdesk mit einem Dict
    statt einer Liste (#3109). Konto ohne Guidance (7600) → (None, set()).
    """
    r = client_.get("/ReceiptGuidance/forAccountNumber", params={"accountNumber": konto})
    r.raise_for_status()
    objekte = r.json().get("objects") or []
    if isinstance(objekte, dict):
        objekte = [objekte]
    for o in objekte:
        if str(o.get("accountNumber")) == str(konto):
            regeln = {str(x.get("id")) for x in o.get("allowedTaxRules") or []}
            konto_id = o.get("accountDatevId")
            return (str(konto_id) if konto_id else None), regeln
    return None, set()


def intern_buchen(client_, position: dict) -> dict:
    """Beleg ohne Dokument nach Regel anlegen (Status 100) und auf den Abgang
    buchen — FULL_PAYMENT negativ; beim Kontoabschluss-Paar zwei Teilbuchungen
    Typ N (Gebuehr + USt-Zeile). Zahldatum = Umsatzdatum (#3270). Nach der
    Buchung wird der Beleg gelesen: alles andere als Status 1000 ist ein Fehler.
    """
    regel = position["regel"]
    konto = str(regel["konto"])
    taxrule = str(regel.get("taxrule") or "9")
    konto_id, erlaubt = konto_guidance(client_, konto)
    if konto_id is None:
        raise RuntimeError(f"Konto {konto}: keine ReceiptGuidance — per Beleg nicht buchbar")
    if taxrule not in erlaubt:
        raise RuntimeError(
            f"Konto {konto}: Steuerregel {taxrule} laut ReceiptGuidance nicht erlaubt"
        )
    partner = position.get("partner")
    if partner:
        netto, steuer = position["netto"], position["steuer"]
        satz = 19
    else:
        satz = int(regel.get("steuersatz") or 0)
        brutto = position["betrag"]
        netto = round(brutto / (1 + satz / 100), 2)
        steuer = round(brutto - netto, 2)
    brutto = round(netto + steuer, 2)
    monat = f"{position['datum'][5:7]}/{position['datum'][:4]}"
    beschreibung = f"{regel.get('beschreibung') or regel.get('bezeichnung') or konto} {monat}"
    zahler = position["zahler"] if position["zahler"] != "—" else ""
    # saveVoucher ohne supplierName antwortet 422 (Echtprobe 2026-09-17).
    lieferant = regel.get("lieferant") or zahler or regel.get("bezeichnung") or konto
    daten = {
        "voucher[objectName]": "Voucher",
        "voucher[mapAll]": "true",
        "voucher[voucherDate]": _iso_zu_dd_mm_yyyy(position["datum"]),
        "voucher[supplierName]": lieferant,
        "voucher[description]": beschreibung,
        "voucher[comment]": kurz(position.get("zweck", ""), 120),
        "voucher[status]": "100",
        "voucher[creditDebit]": CREDIT,
        "voucher[voucherType]": "VOU",
        "voucher[currency]": "EUR",
        "voucher[taxRule][id]": taxrule,
        "voucher[taxRule][objectName]": "TaxRule",
        "voucherPosSave[0][objectName]": "VoucherPos",
        "voucherPosSave[0][mapAll]": "true",
        "voucherPosSave[0][accountDatev][id]": konto_id,
        "voucherPosSave[0][accountDatev][objectName]": "AccountDatev",
        "voucherPosSave[0][taxRate]": str(satz),
        "voucherPosSave[0][net]": "false",
        "voucherPosSave[0][sumNet]": f"{netto:.2f}",
        "voucherPosSave[0][sumTax]": f"{steuer:.2f}",
        "voucherPosSave[0][sumGross]": f"{brutto:.2f}",
        "voucherPosSave[0][comment]": beschreibung,
    }
    r = client_.post("/Voucher/Factory/saveVoucher", data=daten)
    r.raise_for_status()
    beleg_id = str(r.json()["objects"]["voucher"]["id"])

    checkaccount = position.get("checkAccount") or {}
    buchungen = [(position["id"], position["datum"], netto if partner else brutto)]
    if partner:
        buchungen.append((partner["id"], (partner.get("valueDate") or "")[:10], steuer))
    for umsatz_id, datum, betrag in buchungen:
        payload = {
            "amount": -abs(betrag),
            "date": _iso_zu_dd_mm_yyyy(datum),
            "type": "N" if partner else "FULL_PAYMENT",
            "checkAccount": {"id": checkaccount.get("id"), "objectName": "CheckAccount"},
            "checkAccountTransaction": {
                "id": umsatz_id,
                "objectName": "CheckAccountTransaction",
            },
        }
        b = client_.put(f"/Voucher/{beleg_id}/bookAmount", json=payload)
        b.raise_for_status()

    pruef = client_.get(f"/Voucher/{beleg_id}")
    pruef.raise_for_status()
    objekte = pruef.json().get("objects") or []
    danach = objekte[0] if objekte else {}
    if str(danach.get("status")) != "1000":
        raise RuntimeError(
            f"Beleg {beleg_id} nach Buchung Status {danach.get('status')}, nicht 1000"
        )
    return {"beleg_id": beleg_id, "typ": "N" if partner else "FULL_PAYMENT", "warnung": None}


def entwurf_buchen(client_, beleg: dict) -> dict:
    """Entwurf (Status 50) → gebucht (Status 100) — Pflichtschritt vor bookAmount.

    sevdesk lehnt ``bookAmount`` auf einem Entwurf mit 422 ab und den
    Statuswechsel per ``PUT /Voucher/{id}`` mit „Use saveVoucher instead"
    (Echtprobe 2026-09-13, Mandant edv). Also ``saveVoucher`` mit id, Status
    100 und den vorhandenen Positionen (ids), danach Kontrolle per GET.
    """
    if str(beleg.get("status")) != "50":
        return beleg
    pos = client_.get(
        "/VoucherPos",
        params={
            "voucher[id]": beleg["id"],
            "voucher[objectName]": "Voucher",
            "limit": 50,
        },
    )
    pos.raise_for_status()
    daten = {
        "voucher[id]": str(beleg["id"]),
        "voucher[objectName]": "Voucher",
        "voucher[mapAll]": "true",
        "voucher[status]": "100",
    }
    for i, p in enumerate(pos.json().get("objects") or []):
        daten[f"voucherPosSave[{i}][id]"] = str(p["id"])
        daten[f"voucherPosSave[{i}][objectName]"] = "VoucherPos"
        daten[f"voucherPosSave[{i}][mapAll]"] = "true"
    r = client_.post("/Voucher/Factory/saveVoucher", data=daten)
    r.raise_for_status()
    pruef = client_.get(f"/Voucher/{beleg['id']}")
    pruef.raise_for_status()
    objekte = pruef.json().get("objects") or []
    danach = objekte[0] if isinstance(objekte, list) and objekte else objekte
    if str(danach.get("status")) != "100":
        raise RuntimeError(
            f"Beleg {beleg['id']}: Status nach saveVoucher ist {danach.get('status')}, nicht 100"
        )
    return danach


def buchen(client_, position: dict, heute: dt.date) -> dict:
    """Bucht EINEN sicheren Abgang voll auf seinen Beleg (immer FULL_PAYMENT —
    Teilbetraege ohne Owner-Wort sind ausgeschlossen). Ein Entwurf wird vorher
    gebucht (Status 100), siehe ``entwurf_buchen``."""
    beleg = entwurf_buchen(client_, position["beleg"])
    checkaccount = position.get("checkAccount") or {}
    # Weicht der Bankbetrag vom Belegbetrag ab (Fremdwaehrungskurs, Cent-Rundung),
    # nimmt sevdesk nur Typ O ("anderer Grund") mit dem BANKbetrag; paidAmount
    # wird trotzdem der Belegbetrag, der Beleg 1000, der Umsatz 400.
    differenz = abs(position.get("kursdifferenz") or 0) >= 0.01
    payload = {
        # Ausgabenbeleg (creditDebit C): sevdesk erwartet die Zahlung NEGATIV.
        # Mit positivem Betrag entstand am 2026-09-13 bei 25 Belegen paidAmount
        # -x, Status 750 und "offen 2x" — alle per resetToOpen + Neubuchung
        # repariert. Der Vorzeichen-Fehler war durch Fakes nicht sichtbar.
        "amount": -abs(position["betrag"] if differenz else voucher_offener_betrag(beleg)),
        "date": _dd_mm_yyyy(heute),
        "type": "O" if differenz else "FULL_PAYMENT",
        "checkAccount": {"id": checkaccount.get("id"), "objectName": "CheckAccount"},
        "checkAccountTransaction": {
            "id": position["id"],
            "objectName": "CheckAccountTransaction",
        },
    }
    r = client_.put(f"/Voucher/{beleg['id']}/bookAmount", json=payload)
    r.raise_for_status()
    antwort = r.json()

    pruef = client_.get(f"/Voucher/{beleg['id']}")
    pruef.raise_for_status()
    objekte = pruef.json().get("objects") or []
    danach = objekte[0] if objekte else {}
    warnung = None
    if danach and abs(voucher_offener_betrag(danach)) > 0.01:
        warnung = (
            f"Beleg {beleg.get('id')} nach Buchung noch nicht ausgeglichen "
            f"(offen: {voucher_offener_betrag(danach):.2f} EUR) — pruefen."
        )
    return {
        "antwort": antwort,
        "danach_offen": voucher_offener_betrag(danach) if danach else None,
        "typ": payload["type"],
        "warnung": warnung,
    }


def buchen_lauf(
    client_, sichere: list[dict], heute: dt.date, wirklich: bool
) -> list[dict]:
    log: list[dict] = []
    ziel = LOG_VERZEICHNIS / f"sevdesk-kostenabgleich-{heute.isoformat()}.json"
    for p in sichere:
        intern = p["status"] == STATUS_INTERN
        posten = {
            "umsatz_id": p["id"],
            "partner_umsatz_id": (p.get("partner") or {}).get("id"),
            "beleg_id": p["beleg"]["id"] if p.get("beleg") else None,
            "betrag": p["betrag"],
            "art": "intern" if intern else "beleg",
            "datum": heute.isoformat(),
            "ausgefuehrt": False,
        }
        if wirklich:
            if intern:
                ergebnis = intern_buchen(client_, p)
                posten["beleg_id"] = ergebnis["beleg_id"]
            else:
                ergebnis = buchen(client_, p, heute)
            posten["ausgefuehrt"] = True
            posten["typ"] = ergebnis["typ"]
            posten["warnung"] = ergebnis["warnung"]
            # Log je Buchung, nicht erst am Ende: bricht der Lauf bei Position n
            # ab, sind die n-1 geschriebenen Buchungen trotzdem nachvollziehbar
            # (Echtprobe 2026-09-17: Abbruch bei Position 3, Log leer).
            _log_anhaengen(ziel, posten)
        log.append(posten)
    return log


def _log_anhaengen(ziel: Path, posten: dict) -> None:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    bestehend = []
    if ziel.exists():
        bestehend = json.loads(ziel.read_text(encoding="utf-8"))
    ziel.write_text(
        json.dumps(bestehend + [posten], ensure_ascii=False, indent=1), encoding="utf-8"
    )


def positionen_ermitteln(
    client_, heute: dt.date, tage: int, regeln: list[dict]
) -> list[dict]:
    """Alle offenen Bankabgaenge des Fensters als fertige Positionen.

    Laedt Umsaetze, offene Lieferantenbelege und die Kontenhilfe, ordnet jeden
    Abgang zu (``zuordnen_position``), haengt den Kontovorschlag an und
    markiert wiederkehrende Serien (``cluster_wiederkehrend``). Eigene
    Funktion, damit andere Werkzeuge dieselbe Liste bekommen, ohne ``main()``
    und dessen Ausgabe zu durchlaufen (K9, platform#3102) — API-Fehler reicht
    sie unveraendert nach oben, der Aufrufer entscheidet ueber den Exit-Code.
    """
    seit = (heute - dt.timedelta(days=tage)).isoformat()
    alle_tx = hole(client_, "/CheckAccountTransaction", startDate=seit)
    alle_belege = hole(client_, "/Voucher", creditDebit=CREDIT)
    guidance_r = client_.get("/ReceiptGuidance/forExpense")
    guidance_r.raise_for_status()
    guidance = guidance_r.json().get("objects") or []

    belege = [v for v in alle_belege if str(v.get("status")) in VOUCHER_STATUS_OFFEN]

    abgaenge = sorted(
        (
            t
            for t in alle_tx
            if str(t.get("status")) == STATUS_TX_OFFEN
            and float(t.get("amount") or 0) < 0
        ),
        key=lambda t: t.get("valueDate") or "",
    )

    paare = kontoabschluss_paare(abgaenge, regeln)
    ust_ids = paare.pop("_ust_ids")

    positionen: list[dict] = []
    nr = 0
    for t in abgaenge:
        if t.get("id") in ust_ids:
            continue  # steckt als Partner in der Gebuehr-Position
        nr += 1
        betrag = abs(float(t.get("amount") or 0))
        zweck = t.get("paymtPurpose") or ""
        name = t.get("payeePayerName") or ""
        anzeige = zahler_anzeige(name, zweck)
        datum = _datum(t.get("valueDate"))
        kandidaten = beleg_kandidaten(belege, betrag)
        ergebnis = zuordnen_position(anzeige, betrag, datum, kandidaten)
        kursdifferenz = 0.0
        if ergebnis["status"] == "sicher" and ergebnis.get("beleg"):
            # 1:1 — ein Beleg deckt genau einen Abgang. Ohne diese Zeile traf
            # ein Eigenbeleg zwei gleich hohe Abgaenge desselben Monats und
            # waere mit --buchen --ja zweimal gebucht worden (Echtprobe
            # 2026-09-13, Mandant edv).
            benutzt = ergebnis["beleg"].get("id")
            belege = [v for v in belege if v.get("id") != benutzt]
            kursdifferenz = round(betrag - voucher_offener_betrag(ergebnis["beleg"]), 2)
            if abs(kursdifferenz) >= 0.01:
                ergebnis["grund"] += f" — Differenz {kursdifferenz:+.2f} EUR (Typ O)"
        regel = regel_treffer(f"{anzeige} {zweck}", regeln)
        paar = paare.get(t.get("id"))
        buchbar = False
        if ergebnis["status"] == "fehlend" and regel and regel.get("beleg") == BELEG_OHNE_DOKUMENT:
            _k, _b, anmerkung = regel_zuordnen(f"{anzeige} {zweck}", betrag, regeln)
            if anmerkung.startswith(("NUR TEILWEISE", "BETRAG UNBEKANNT")):
                ergebnis["grund"] = f"Regel {regel['konto']}: {anmerkung}"
            elif regel.get("klasse") == KLASSE_KONTOABSCHLUSS and not paar:
                ergebnis = {
                    "status": STATUS_INTERN,
                    "beleg": None,
                    "kandidaten": [],
                    "grund": f"Regel {regel['konto']}: wartet auf die USt-Zeile der Bank",
                }
            else:
                buchbar = bool(regel.get("autonom"))
                ergebnis = {
                    "status": STATUS_INTERN,
                    "beleg": None,
                    "kandidaten": [],
                    "grund": f"Beleg ohne Dokument nach Regel {regel['konto']}"
                    + (" (Paar Gebuehr + USt)" if paar else "")
                    + ("" if buchbar else " — Mandat fehlt (\"autonom\": true)"),
                }
        vorschlag, vorschlag_grund = kontovorschlag(
            regeln, guidance, anzeige, zweck, betrag
        )
        positionen.append(
            {
                "nr": nr,
                "id": t.get("id"),
                "datum": (t.get("valueDate") or "")[:10],
                "betrag": betrag,
                "zahler": anzeige or "—",
                "zweck": zweck,
                "status": ergebnis["status"],
                "grund": ergebnis["grund"],
                "kandidaten": ergebnis["kandidaten"],
                "beleg": ergebnis["beleg"],
                "checkAccount": t.get("checkAccount"),
                "kursdifferenz": kursdifferenz,
                "regel": regel if ergebnis["status"] == STATUS_INTERN else None,
                "buchbar": buchbar,
                "partner": paar["partner"] if (paar and ergebnis["status"] == STATUS_INTERN) else None,
                "netto": paar["netto"] if paar else None,
                "steuer": paar["steuer"] if paar else None,
                "konto_vorschlag": vorschlag,
                "konto_grund": vorschlag_grund,
                "zahler_key": frozenset(worte(anzeige)),
                "monat": monat_schluessel(datum) if datum else "",
                "wiederkehrend": None,
                "beleg_frueher_vorhanden": False,
            }
        )

    cluster_wiederkehrend(positionen)
    return positionen


def _wiederkehrend_text(p: dict) -> str:
    if not p.get("wiederkehrend"):
        return ""
    return f"wiederkehrend ({p['wiederkehrend']}x)"


def render_markdown(
    positionen: list[dict], gebucht: list[dict], kennzahlen: dict, args
) -> str:
    zeilen: list[str] = []
    zeilen.append(
        f"# Kostenabgleich — Fenster {args.tage} Tage (Mandant {args.mandant})\n"
    )
    zeilen.append(
        f"\n{kennzahlen['abgaenge_geprueft']} Abgaenge geprueft — "
        f"**{kennzahlen['sicher']} Beleg vorhanden** · **{kennzahlen['unklar']} unklar** · "
        f"**{kennzahlen['beleg_fehlt']} Beleg fehlt** "
        f"({kennzahlen['summe_beleg_fehlt']:,.2f} EUR) · "
        f"**{kennzahlen['intern']} intern** ({kennzahlen['intern_ohne_mandat']} ohne Mandat) · "
        f"{kennzahlen['wiederkehrend']} wiederkehrend\n"
    )

    def _tabelle(titel: str, teilmenge: list[dict]) -> None:
        zeilen.append(f"\n## {titel} ({len(teilmenge)})\n")
        if not teilmenge:
            zeilen.append("\n(keine)\n")
            return
        zeilen.append(
            "\n| Datum | Zahler | Betrag EUR | Beleg/Kandidaten | Konto-Vorschlag | Grund | wiederkehrend |"
        )
        zeilen.append("|---|---|---:|---|---|---|---|")
        for p in teilmenge:
            if p["status"] == "sicher" and p["beleg"]:
                beleg_text = f"Beleg {p['beleg'].get('id')}"
            elif p["status"] == STATUS_INTERN:
                beleg_text = "wird angelegt" if p["buchbar"] else "Regel ohne Mandat"
                if p.get("partner"):
                    beleg_text += f" (+ USt-Zeile `{p['partner'].get('id')}`)"
            elif p["kandidaten"]:
                beleg_text = f"{len(p['kandidaten'])} Kandidat(en)"
            else:
                beleg_text = "—"
            hinweis = p["grund"]
            if p.get("beleg_frueher_vorhanden"):
                hinweis = f"{hinweis} — Beleg fuer diesen Monat fehlt"
            zeilen.append(
                f"| {p['datum']} | {kurz(p['zahler'], 30)} | {p['betrag']:,.2f} | "
                f"{beleg_text} | {kurz(p['konto_vorschlag'], 40)} | {kurz(hinweis, 80)} | "
                f"{_wiederkehrend_text(p)} |"
            )

    _tabelle(
        "Beleg vorhanden (buchbar)", [p for p in positionen if p["status"] == "sicher"]
    )
    _tabelle("Unklar", [p for p in positionen if p["status"] == "unklar"])
    _tabelle(
        "Intern — Beleg ohne Dokument nach Regel",
        [p for p in positionen if p["status"] == STATUS_INTERN],
    )
    _tabelle("Beleg fehlt", [p for p in positionen if p["status"] == "fehlend"])

    if args.buchen:
        zeilen.append(
            f"\n## Buchung ({'ausgefuehrt' if args.ja else 'Vorschau — NICHTS gebucht'})\n"
        )
        if gebucht:
            zeilen.append("\n| Umsatz-ID | Beleg-ID | Betrag EUR | Art | Typ | Datum |")
            zeilen.append("|---|---|---:|---|---|---|")
            for g in gebucht:
                zeilen.append(
                    f"| `{g['umsatz_id']}` | {g['beleg_id'] or '(neu)'} | {g['betrag']:,.2f} | "
                    f"{g['art']} | {g.get('typ') or '—'} | {g['datum']} |"
                )
        else:
            zeilen.append("\n(keine sicheren Zuordnungen zu buchen)\n")

    return "\n".join(zeilen) + "\n"


def als_json(positionen: list[dict], gebucht: list[dict], kennzahlen: dict) -> dict:
    def pos_json(p: dict) -> dict:
        return {
            "datum": p["datum"],
            "zahler": p["zahler"],
            # Ohne geparsten Zahlernamen ("—") ist der Verwendungszweck die
            # einzige Spur auf den Lieferanten — nachgelagerte Werkzeuge
            # (belegbeschaffung.py, K9) brauchen ihn deshalb im JSON.
            "zweck": kurz(p.get("zweck", ""), 80),
            "betrag": p["betrag"],
            "status": p["status"],
            "grund": p["grund"],
            "beleg_id": p["beleg"]["id"] if p.get("beleg") else None,
            "kandidaten": len(p["kandidaten"]),
            "kursdifferenz": p.get("kursdifferenz") or 0.0,
            "buchbar": p.get("buchbar", False),
            "partner_umsatz_id": (p.get("partner") or {}).get("id"),
            "konto_vorschlag": p["konto_vorschlag"],
            "konto_grund": p["konto_grund"],
            "wiederkehrend": p["wiederkehrend"],
            "beleg_frueher_vorhanden": p["beleg_frueher_vorhanden"],
        }

    return {
        "kennzahlen": kennzahlen,
        "beleg_vorhanden": [pos_json(p) for p in positionen if p["status"] == "sicher"],
        "unklar": [pos_json(p) for p in positionen if p["status"] == "unklar"],
        "intern": [pos_json(p) for p in positionen if p["status"] == STATUS_INTERN],
        "beleg_fehlt": [pos_json(p) for p in positionen if p["status"] == "fehlend"],
        "gebucht": gebucht,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mandant_argument(p)
    p.add_argument(
        "--tage",
        type=int,
        default=120,
        help="Fenster fuer Bankabgaenge in Tagen (Standard 120)",
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
        "--nicht-buchen",
        dest="nicht_buchen",
        default="",
        help="Regex (case-insensitive) gegen Zahler/Zweck: passende Abgaenge werden "
        "gezeigt, aber nie gebucht (z. B. ein Anbieter mit privater Zweitserie)",
    )
    p.add_argument(
        "--heute",
        default=None,
        help="Stichtag YYYY-MM-DD (Reproduzierbarkeit); Standard: Systemdatum",
    )
    p.add_argument("--konten", type=Path, default=KONTEN_DATEI)
    p.add_argument("--ziel", type=Path, default=STANDARD_ZIEL)
    args = p.parse_args()

    heute = dt.date.fromisoformat(args.heute) if args.heute else dt.date.today()
    regeln = konten_laden(args.konten)

    c = client(args.mandant)
    try:
        positionen = positionen_ermitteln(c, heute, args.tage, regeln)
    except Exception as exc:  # httpx.HTTPError, ConnectError, etc.
        print(f"ABBRUCH: API-Fehler — {exc}")
        return 3

    sicher = [p for p in positionen if p["status"] == "sicher"]
    unklar = [p for p in positionen if p["status"] == "unklar"]
    fehlend = [p for p in positionen if p["status"] == "fehlend"]
    intern = [p for p in positionen if p["status"] == STATUS_INTERN]
    wiederkehrend_n = sum(1 for p in positionen if p["wiederkehrend"])
    summe_fehlend = round(sum(p["betrag"] for p in fehlend), 2)

    gebucht: list[dict] = []
    if args.buchen:
        try:
            # Intern nur mit Mandat: die Regel traegt "autonom": true — das ist
            # das stehende Owner-Wort je Regelklasse (Baustein 5, 2026-09-17).
            zu_buchen = sicher + [q for q in intern if q["buchbar"]]
            if args.nicht_buchen:
                muster = re.compile(args.nicht_buchen, re.IGNORECASE)
                zu_buchen = [
                    q
                    for q in sicher
                    if not muster.search(
                        (q.get("zahler") or "") + " " + (q.get("zweck") or "")
                    )
                ]
            gebucht = buchen_lauf(c, zu_buchen, heute, wirklich=args.ja)
        except Exception as exc:
            print(f"ABBRUCH: API-Fehler beim Buchen — {exc}")
            return 3

    kennzahlen = {
        "abgaenge_geprueft": len(positionen),
        "sicher": len(sicher),
        "unklar": len(unklar),
        "beleg_fehlt": len(fehlend),
        "intern": len(intern),
        "intern_ohne_mandat": sum(1 for q in intern if not q["buchbar"]),
        "wiederkehrend": wiederkehrend_n,
        "summe_beleg_fehlt": summe_fehlend,
    }

    if args.json:
        print(
            json.dumps(
                als_json(positionen, gebucht, kennzahlen), ensure_ascii=False, indent=1
            )
        )
    else:
        text = render_markdown(positionen, gebucht, kennzahlen, args)
        print(text)
        args.ziel.parent.mkdir(parents=True, exist_ok=True)
        args.ziel.write_text(text, encoding="utf-8")
        print(f"geschrieben: {args.ziel}")

    if positionen and not (unklar or fehlend or [q for q in intern if not q["buchbar"]]):
        return 0
    if not positionen:
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
