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

**Wiederkehrend**: Abgaenge mit gleichem normalisiertem Zahler und Betrag
(Toleranz 0,50 EUR) in mindestens zwei aufeinanderfolgenden Kalendermonaten
werden in allen drei Listen als "wiederkehrend (nx)" markiert. Fehlt bei einer
solchen Serie ausgerechnet in diesem Monat der Beleg, obwohl ein frueherer
Monat der Serie einen hatte, wird das zusaetzlich vermerkt ("Beleg fuer diesen
Monat fehlt").

**Kontovorschlag** je Position: zuerst eine Regel aus
``~/.claude/sevdesk-konten.json`` (wiederverwendet aus ``bankpositionen.py``),
sonst bis zu zwei Treffer aus ``GET /ReceiptGuidance/forExpense``, deren
Kontoname/-beschreibung ein Wort des Zahlers/Zwecks enthaelt; kein Treffer
-> "—".

K8 (zweiter Mandant): ``--mandant iil|edv`` (Standard iil) waehlt den
sevdesk-Zugang ueber ``mandant.py``; gleichwertig per Umgebungsvariable
``SEVDESK_MANDANT``.

Fallen (siehe auch ``tools/sevdesk/README.md``):

- ``--buchen`` ohne ``--ja`` zeigt nur, was gebucht wuerde; ``bookAmount``
  wird in KEINEM Fall aufgerufen.
- ``--buchen --ja`` bucht **ausschliesslich** die Stufe "Beleg vorhanden".
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

#: Datum-Toleranz fuer eine sichere Zuordnung.
TAGE_TOLERANZ = 14
#: Betrags-Toleranz fuer die Wiederkehrend-Erkennung (Miete/Abo schwankt
#: gelegentlich um Cent-Betraege, z. B. Rundung oder Index-Anpassung).
BETRAG_TOLERANZ_WIEDERKEHREND = 0.50


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
    guidance: list[dict], zahler: str, zweck: str, max_n: int = 2
) -> list[tuple[str, str, str]]:
    """(kontonummer, kontoname, treffer_wort) je Vorschlag, bis zu max_n."""
    ziel = worte(f"{zahler} {zweck}")
    treffer: list[tuple[str, str, str]] = []
    for g in guidance:
        gwort = worte(f"{g.get('accountName', '')} {g.get('description', '')}")
        schnitt = ziel & gwort
        if schnitt:
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
    ReceiptGuidance, sonst "—"."""
    konto, bez, _anm = regel_zuordnen(f"{zahler} {zweck}", betrag, regeln)
    if konto:
        text = f"{konto} — {bez}" if bez else konto
        return text, "Regel aus sevdesk-konten.json"
    treffer = guidance_treffer(guidance, zahler, zweck)
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


def buchen(client_, position: dict, heute: dt.date) -> dict:
    """Bucht EINEN sicheren Abgang voll auf seinen Beleg (immer FULL_PAYMENT —
    Teilbetraege ohne Owner-Wort sind ausgeschlossen)."""
    beleg = position["beleg"]
    checkaccount = position.get("checkAccount") or {}
    payload = {
        "amount": voucher_offener_betrag(beleg),
        "date": _dd_mm_yyyy(heute),
        "type": "FULL_PAYMENT",
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
        "warnung": warnung,
    }


def buchen_lauf(
    client_, sichere: list[dict], heute: dt.date, wirklich: bool
) -> list[dict]:
    log: list[dict] = []
    for p in sichere:
        posten = {
            "umsatz_id": p["id"],
            "beleg_id": p["beleg"]["id"] if p.get("beleg") else None,
            "betrag": p["betrag"],
            "datum": heute.isoformat(),
            "ausgefuehrt": False,
        }
        if wirklich:
            ergebnis = buchen(client_, p, heute)
            posten["ausgefuehrt"] = True
            posten["warnung"] = ergebnis["warnung"]
        log.append(posten)
    if wirklich and log:
        ziel = LOG_VERZEICHNIS / f"sevdesk-kostenabgleich-{heute.isoformat()}.json"
        ziel.parent.mkdir(parents=True, exist_ok=True)
        bestehend = []
        if ziel.exists():
            bestehend = json.loads(ziel.read_text(encoding="utf-8"))
        ziel.write_text(
            json.dumps(bestehend + log, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return log


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
    _tabelle("Beleg fehlt", [p for p in positionen if p["status"] == "fehlend"])

    if args.buchen:
        zeilen.append(
            f"\n## Buchung ({'ausgefuehrt' if args.ja else 'Vorschau — NICHTS gebucht'})\n"
        )
        if gebucht:
            zeilen.append("\n| Umsatz-ID | Beleg-ID | Betrag EUR | Datum |")
            zeilen.append("|---|---|---:|---|")
            for g in gebucht:
                zeilen.append(
                    f"| `{g['umsatz_id']}` | {g['beleg_id']} | {g['betrag']:,.2f} | {g['datum']} |"
                )
        else:
            zeilen.append("\n(keine sicheren Zuordnungen zu buchen)\n")

    return "\n".join(zeilen) + "\n"


def als_json(positionen: list[dict], gebucht: list[dict], kennzahlen: dict) -> dict:
    def pos_json(p: dict) -> dict:
        return {
            "datum": p["datum"],
            "zahler": p["zahler"],
            "betrag": p["betrag"],
            "status": p["status"],
            "grund": p["grund"],
            "beleg_id": p["beleg"]["id"] if p.get("beleg") else None,
            "kandidaten": len(p["kandidaten"]),
            "konto_vorschlag": p["konto_vorschlag"],
            "konto_grund": p["konto_grund"],
            "wiederkehrend": p["wiederkehrend"],
            "beleg_frueher_vorhanden": p["beleg_frueher_vorhanden"],
        }

    return {
        "kennzahlen": kennzahlen,
        "beleg_vorhanden": [pos_json(p) for p in positionen if p["status"] == "sicher"],
        "unklar": [pos_json(p) for p in positionen if p["status"] == "unklar"],
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
        seit = (heute - dt.timedelta(days=args.tage)).isoformat()
        alle_tx = hole(c, "/CheckAccountTransaction", startDate=seit)
        alle_belege = hole(c, "/Voucher", creditDebit=CREDIT)
        guidance_r = c.get("/ReceiptGuidance/forExpense")
        guidance_r.raise_for_status()
        guidance = guidance_r.json().get("objects") or []
    except Exception as exc:  # httpx.HTTPError, ConnectError, etc.
        print(f"ABBRUCH: API-Fehler — {exc}")
        return 3

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

    positionen: list[dict] = []
    for nr, t in enumerate(abgaenge, 1):
        betrag = abs(float(t.get("amount") or 0))
        zweck = t.get("paymtPurpose") or ""
        name = t.get("payeePayerName") or ""
        anzeige = zahler_anzeige(name, zweck)
        datum = _datum(t.get("valueDate"))
        kandidaten = [
            v for v in belege if abs(voucher_offener_betrag(v) - betrag) <= 0.01
        ]
        ergebnis = zuordnen_position(anzeige, betrag, datum, kandidaten)
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
                "konto_vorschlag": vorschlag,
                "konto_grund": vorschlag_grund,
                "zahler_key": frozenset(worte(anzeige)),
                "monat": monat_schluessel(datum) if datum else "",
                "wiederkehrend": None,
                "beleg_frueher_vorhanden": False,
            }
        )

    cluster_wiederkehrend(positionen)

    sicher = [p for p in positionen if p["status"] == "sicher"]
    unklar = [p for p in positionen if p["status"] == "unklar"]
    fehlend = [p for p in positionen if p["status"] == "fehlend"]
    wiederkehrend_n = sum(1 for p in positionen if p["wiederkehrend"])
    summe_fehlend = round(sum(p["betrag"] for p in fehlend), 2)

    gebucht: list[dict] = []
    if args.buchen:
        try:
            gebucht = buchen_lauf(c, sicher, heute, wirklich=args.ja)
        except Exception as exc:
            print(f"ABBRUCH: API-Fehler beim Buchen — {exc}")
            return 3

    kennzahlen = {
        "abgaenge_geprueft": len(positionen),
        "sicher": len(sicher),
        "unklar": len(unklar),
        "beleg_fehlt": len(fehlend),
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

    if positionen and not (unklar or fehlend):
        return 0
    if not positionen:
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
