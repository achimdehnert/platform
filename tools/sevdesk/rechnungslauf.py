#!/usr/bin/env python3
"""Monats-/Quartalsrechnungslauf für sevdesk-Dauerkunden — ENTWURF, kein Versand ohne Gate (#3102, K1/K2/K3/K5).

Schwesterwerkzeug zu ``rechnung_entwurf.py`` (Einzelrechnung). Dieses hier
erkennt wiederkehrende Kunden aus dem Bestand und legt ihnen je Monat/Quartal
einen neuen Rechnungs-ENTWURF an, indem es die letzte Rechnung als Vorlage
kopiert (Positionen, Texte, Zahlungsziel, Adresse) und nur den
Leistungszeitraum (``deliveryDate``/``deliveryDateUntil``) austauscht.

- ``--kunden-ermitteln`` liest die Rechnungen der letzten 18 Monate, erkennt
  je Kontakt den Rhythmus aus der Länge des Leistungszeitraums (27–31 Tage =
  Monat, 89–93 Tage = Quartal; mindestens 2 Rechnungen desselben Rhythmus,
  sonst „unregelmäßig" — wird gemeldet, nicht übernommen) und schreibt
  ``~/.claude/sevdesk-dauerkunden.json`` (0600, NIE im Repo). Ein erneuter
  Lauf meldet Abweichungen (Kunde neu/entfallen) gegenüber der bestehenden
  Datei.
- ``--monat YYYY-MM`` / ``--quartal YYYY-Qn`` (ohne Wert: Vormonat/Vorquartal;
  ganz ohne Modus-Flag: Vormonat) legt je Dauerkunde des passenden Rhythmus
  einen Entwurf an — Duplikatprüfung über ``deliveryDate`` verhindert eine
  zweite Rechnung für denselben Zeitraum. ``--dry-run`` zeigt nur die
  Prüfliste; zwei ``--dry-run``-Läufe liefern identische Ausgabe.
- ``--senden [--ja]`` verschickt NUR bestehende Entwürfe (Status 100) des
  angegebenen Zeitraums per ``sendViaEmail``; ohne ``--ja`` nur Anzeige. Ein
  Versandlog je Zeitraum (``~/.claude/sevdesk-versand-<von>.json``) macht
  Wiederholungen idempotent — Rechnungen mit Mail-ID im Log oder ohne Status
  100 werden übersprungen. sevdesk drosselt (HTTP 429): 15 s Pause zwischen
  Sendungen, bei 429 ``Retry-After`` oder 30/60/90/120 s, max. 6 Versuche.
- Jeder Lauf hängt eine Kennzahlen-Zeile an
  ``~/.claude/sevdesk-rechnungslauf-journal.jsonl`` (K2) —
  ``tools/mail_agent/messjournal.py --anwendung sevdesk`` liest davon nur die
  jüngste Zeile.

**Kein Kundenname, keine Adresse, kein Betrag echter Kunden in diesem Modul,
seinen Tests oder seiner Doku** — platform ist öffentlich. Die reale
Kundendatei lebt lokal unter ``~/.claude/sevdesk-dauerkunden.json``.

    python3 tools/sevdesk/rechnungslauf.py --kunden-ermitteln
    python3 tools/sevdesk/rechnungslauf.py --monat 2026-08 --dry-run
    python3 tools/sevdesk/rechnungslauf.py --monat 2026-09
    python3 tools/sevdesk/rechnungslauf.py --senden --monat 2026-09
    python3 tools/sevdesk/rechnungslauf.py --senden --monat 2026-09 --ja
"""

from __future__ import annotations

import argparse
import calendar
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from beleg_entwurf import _client  # noqa: E402  geteilter Helfer, keine Kopie
from rechnung_entwurf import _seiten, naechste_nummer  # noqa: E402

TOOL_VERSION = "rechnungslauf.py/1"

KUNDEN_DATEI = Path.home() / ".claude" / "sevdesk-dauerkunden.json"
JOURNAL_DATEI = Path.home() / ".claude" / "sevdesk-rechnungslauf-journal.jsonl"

RHYTHMUS_MONAT = "monat"
RHYTHMUS_QUARTAL = "quartal"

#: Toleranz um 30 bzw. 91 Tage (kalendarische Monats-/Quartalslängen).
_MONAT_TAGE = range(27, 32)
_QUARTAL_TAGE = range(89, 94)

STEUERSATZ_STANDARD = 19
ZAHLUNGSZIEL_STANDARD = 14

VERSAND_PAUSE_SEKUNDEN = 15
#: Backoff-Folge bei HTTP 429 ohne ``Retry-After``-Header.
VERSAND_BACKOFF = (30, 60, 90, 120)
VERSAND_MAX_VERSUCHE = 6

#: Wortlaut aus dem Auftrag #3102 — nicht selbst formulieren, Owner-Text.
VERSAND_TEXT_VORLAGE = (
    "<p>Sehr geehrte Damen und Herren,</p><p>anbei erhalten Sie unsere Rechnung "
    "{nr} über {betrag} für den Leistungszeitraum {von} bis {bis}. Bitte "
    "überweisen Sie den Betrag bis zum {faellig} unter Angabe der "
    "Rechnungsnummer.</p><p>Bei Fragen zur Rechnung erreichen Sie mich "
    "jederzeit unter der Mobilnummer in der Signatur.</p><p>Mit freundlichen "
    "Grüßen</p>{signatur}"
)


# --- Rhythmuserkennung (reine Logik, ohne API) -----------------------------


def _tage_zeitraum(von: str, bis: str) -> int:
    """Inklusive Tagesanzahl zwischen zwei YYYY-MM-DD-Daten."""
    return (date.fromisoformat(bis) - date.fromisoformat(von)).days + 1


def _rhythmus_klassifizieren(tage: int) -> str | None:
    if tage in _MONAT_TAGE:
        return RHYTHMUS_MONAT
    if tage in _QUARTAL_TAGE:
        return RHYTHMUS_QUARTAL
    return None


def dauerkunden_erkennen(
    rechnungen: list[dict],
) -> tuple[dict[str, dict], list[dict]]:
    """Gruppiert rohe Rechnungsdaten je Kontakt und erkennt einen Rhythmus.

    ``rechnungen``: Liste von ``{id, contact_id, contact_name, von, bis}``.
    Ein Rhythmus gilt als erkannt, wenn er unter den klassifizierbaren
    Zeiträumen eines Kontakts mindestens zweimal (und häufiger als jeder
    andere Rhythmus) auftritt — sonst zählt der Kontakt als „unregelmäßig"
    und wird NICHT übernommen.

    Rückgabe: (``{kontakt_id: {name, rhythmus, letzte_rechnung_id,
    letzter_zeitraum}}``, Liste unregelmäßiger Kontakte).
    """
    je_kontakt: dict[str, list[dict]] = {}
    for r in rechnungen:
        if not r.get("von") or not r.get("bis"):
            continue
        je_kontakt.setdefault(r["contact_id"], []).append(r)

    kunden: dict[str, dict] = {}
    unregelmaessig: list[dict] = []
    for kontakt_id, liste in je_kontakt.items():
        liste = sorted(liste, key=lambda r: r["von"])
        zaehlung: dict[str, int] = {}
        for r in liste:
            klasse = _rhythmus_klassifizieren(_tage_zeitraum(r["von"], r["bis"]))
            if klasse:
                zaehlung[klasse] = zaehlung.get(klasse, 0) + 1

        dominant = max(zaehlung, key=lambda k: zaehlung[k]) if zaehlung else None
        if dominant and zaehlung[dominant] >= 2:
            letzte = liste[-1]
            kunden[kontakt_id] = {
                "name": letzte.get("contact_name") or "",
                "rhythmus": dominant,
                "letzte_rechnung_id": letzte["id"],
                "letzter_zeitraum": [letzte["von"], letzte["bis"]],
            }
        else:
            unregelmaessig.append(
                {"kontakt_id": kontakt_id, "name": liste[-1].get("contact_name") or ""}
            )
    return kunden, unregelmaessig


# --- Kunden ermitteln (API) -------------------------------------------------


def _rechnungen_fuer_erkennung(client, monate: int = 18) -> list[dict]:
    grenze = (date.today() - timedelta(days=monate * 31)).isoformat()
    ergebnis: list[dict] = []
    for rechnung in _seiten(client, "/Invoice"):
        von = (rechnung.get("deliveryDate") or "")[:10]
        bis = (rechnung.get("deliveryDateUntil") or "")[:10]
        if not von or not bis or von < grenze:
            continue
        kontakt = rechnung.get("contact") or {}
        if not kontakt.get("id"):
            continue
        ergebnis.append(
            {
                "id": rechnung["id"],
                "contact_id": str(kontakt["id"]),
                "contact_name": None,
                "von": von,
                "bis": bis,
            }
        )
    return ergebnis


def _kontaktname(client, kontakt_id: str) -> str:
    r = client.get(f"/Contact/{kontakt_id}")
    r.raise_for_status()
    objekte = r.json()["objects"]
    objekt = objekte[0] if isinstance(objekte, list) else objekte
    return objekt.get("name") or ""


def _kunden_lesen(pfad: Path) -> dict:
    if not pfad.exists():
        return {}
    try:
        geladen = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return geladen if isinstance(geladen, dict) else {}


def _kunden_schreiben(pfad: Path, kunden: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(
        json.dumps(kunden, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pfad.chmod(0o600)


def kunden_ermitteln(
    client, kunden_datei: Path = KUNDEN_DATEI, monate: int = 18
) -> dict:
    """Voller Ablauf: Bestand lesen, Rhythmus erkennen, Datei schreiben, Diff melden."""
    roh = _rechnungen_fuer_erkennung(client, monate)
    kunden, unregelmaessig = dauerkunden_erkennen(roh)
    for kontakt_id, eintrag in kunden.items():
        if not eintrag["name"]:
            eintrag["name"] = _kontaktname(client, kontakt_id)

    alt = _kunden_lesen(kunden_datei)
    neu_ids = sorted(set(kunden) - set(alt))
    entfernt_ids = sorted(set(alt) - set(kunden))

    _kunden_schreiben(kunden_datei, kunden)

    je_rhythmus: dict[str, int] = {}
    for eintrag in kunden.values():
        je_rhythmus[eintrag["rhythmus"]] = je_rhythmus.get(eintrag["rhythmus"], 0) + 1

    return {
        "kunden_gesamt": len(kunden),
        "je_rhythmus": je_rhythmus,
        "unregelmaessig": len(unregelmaessig),
        "neu": neu_ids,
        "entfallen": entfernt_ids,
    }


# --- Zeitraeume --------------------------------------------------------------


def zeitraum_monat(yyyy_mm: str) -> tuple[str, str]:
    jahr, monat = (int(t) for t in yyyy_mm.split("-"))
    letzter_tag = calendar.monthrange(jahr, monat)[1]
    return f"{jahr:04d}-{monat:02d}-01", f"{jahr:04d}-{monat:02d}-{letzter_tag:02d}"


def vormonat(heute: date | None = None) -> str:
    heute = heute or date.today()
    erster = heute.replace(day=1)
    letzter_vormonat = erster - timedelta(days=1)
    return f"{letzter_vormonat.year:04d}-{letzter_vormonat.month:02d}"


def zeitraum_quartal(yyyy_qn: str) -> tuple[str, str]:
    jahr_s, q_s = yyyy_qn.upper().split("-Q")
    jahr, q = int(jahr_s), int(q_s)
    start_monat = (q - 1) * 3 + 1
    end_monat = start_monat + 2
    letzter_tag = calendar.monthrange(jahr, end_monat)[1]
    return (
        f"{jahr:04d}-{start_monat:02d}-01",
        f"{jahr:04d}-{end_monat:02d}-{letzter_tag:02d}",
    )


def vorquartal(heute: date | None = None) -> str:
    heute = heute or date.today()
    q = (heute.month - 1) // 3 + 1
    jahr = heute.year
    q -= 1
    if q == 0:
        q = 4
        jahr -= 1
    return f"{jahr:04d}-Q{q}"


# --- Formatierung ------------------------------------------------------------


def betrag_format(wert: float) -> str:
    """1234.5 -> "1.234,50 EUR" (deutsches Format, Tausenderpunkt)."""
    text = f"{wert:,.2f}"
    text = text.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{text} EUR"


def faelligkeit(rechnungsdatum: str, zahlungsziel: int) -> str:
    return (
        date.fromisoformat(rechnungsdatum) + timedelta(days=zahlungsziel)
    ).isoformat()


# --- Vorlage kopieren (API) --------------------------------------------------


def _positionen_lesen(client, invoice_id: str) -> list[dict]:
    r = client.get(
        "/InvoicePos",
        params={
            "invoice[id]": invoice_id,
            "invoice[objectName]": "Invoice",
            "limit": 100,
        },
    )
    r.raise_for_status()
    positionen = []
    for pos in r.json()["objects"]:
        positionen.append(
            {
                "name": pos.get("name") or "",
                "text": pos.get("text") or None,
                "quantity": float(pos.get("quantity") or 0),
                "price": float(pos.get("price") or 0),
                "taxRate": float(pos.get("taxRate") or STEUERSATZ_STANDARD),
                "unity_id": str((pos.get("unity") or {}).get("id") or "1"),
            }
        )
    return positionen


def _vorlage_lesen(client, invoice_id: str) -> dict:
    r = client.get(f"/Invoice/{invoice_id}")
    r.raise_for_status()
    objekte = r.json()["objects"]
    rechnung = objekte[0] if isinstance(objekte, list) else objekte
    return {
        "address": rechnung.get("address") or "",
        "addressName": rechnung.get("addressName") or "",
        "headText": rechnung.get("headText") or "",
        "footText": rechnung.get("footText") or "",
        "timeToPay": int(rechnung.get("timeToPay") or ZAHLUNGSZIEL_STANDARD),
        "paymentMethod": rechnung.get("paymentMethod") or {},
        "contactPerson": rechnung.get("contactPerson") or {},
    }


def _entwurf_fuer_zeitraum_vorhanden(client, kontakt_id: str, von: str) -> str | None:
    """Existiert für den Kontakt bereits EINE Rechnung (beliebiger Status) mit
    identischem ``deliveryDate``? Rückgabe: Rechnungsnummer (oder ID, falls
    keine Nummer vergeben) — sonst ``None``."""
    for rechnung in _seiten(
        client,
        "/Invoice",
        **{"contact[id]": kontakt_id, "contact[objectName]": "Contact"},
    ):
        if (rechnung.get("deliveryDate") or "")[:10] == von:
            return rechnung.get("invoiceNumber") or rechnung["id"]
    return None


def _entwurf_anlegen(
    client,
    kontakt_id: str,
    kunde_eintrag: dict,
    vorlage: dict,
    positionen: list[dict],
    von: str,
    bis: str,
    nummer: str,
) -> str:
    heute = date.today().isoformat()
    daten: dict = {
        "invoice[objectName]": "Invoice",
        "invoice[mapAll]": "true",
        "invoice[invoiceNumber]": nummer,
        "invoice[invoiceDate]": heute,
        "invoice[deliveryDate]": von,
        "invoice[deliveryDateUntil]": bis,
        "invoice[status]": "100",
        "invoice[invoiceType]": "RE",
        "invoice[currency]": "EUR",
        "invoice[contact][id]": str(kontakt_id),
        "invoice[contact][objectName]": "Contact",
        "invoice[timeToPay]": str(vorlage["timeToPay"]),
        "invoice[header]": f"Rechnung Nr. {nummer}",
        "invoice[headText]": vorlage["headText"],
        "invoice[footText]": vorlage["footText"],
        "invoice[showNet]": "1",
        "invoice[smallSettlement]": "0",
        "invoice[taxType]": "default",
        "invoice[sendType]": "VPDF",
        "invoice[address]": vorlage["address"],
        "invoice[addressName]": vorlage["addressName"]
        or kunde_eintrag.get("name")
        or "",
    }
    if vorlage.get("paymentMethod", {}).get("id"):
        daten["invoice[paymentMethod][id]"] = str(vorlage["paymentMethod"]["id"])
        daten["invoice[paymentMethod][objectName]"] = "PaymentMethod"
    if vorlage.get("contactPerson", {}).get("id"):
        daten["invoice[contactPerson][id]"] = str(vorlage["contactPerson"]["id"])
        daten["invoice[contactPerson][objectName]"] = "SevUser"
    for i, pos in enumerate(positionen):
        daten[f"invoicePosSave[{i}][objectName]"] = "InvoicePos"
        daten[f"invoicePosSave[{i}][mapAll]"] = "true"
        daten[f"invoicePosSave[{i}][quantity]"] = f"{pos['quantity']:g}"
        daten[f"invoicePosSave[{i}][price]"] = f"{pos['price']:.2f}"
        daten[f"invoicePosSave[{i}][taxRate]"] = f"{pos['taxRate']:g}"
        daten[f"invoicePosSave[{i}][unity][id]"] = pos["unity_id"]
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
    return rechnung["id"]


def rechnungslauf(
    client, kunden: dict, rhythmus: str, von: str, bis: str, dry_run: bool
) -> list[dict]:
    """Prüfliste (bzw. echte Entwürfe, wenn ``dry_run=False``) für alle
    Dauerkunden des angegebenen Rhythmus im Zeitraum ``von``..``bis``."""
    posten: list[dict] = []
    for kontakt_id, eintrag in sorted(kunden.items()):
        if eintrag.get("rhythmus") != rhythmus:
            continue

        vorhandene_nummer = _entwurf_fuer_zeitraum_vorhanden(client, kontakt_id, von)
        if vorhandene_nummer:
            posten.append(
                {
                    "kunde": eintrag.get("name") or kontakt_id,
                    "rhythmus": rhythmus,
                    "zeitraum": f"{von}..{bis}",
                    "positionen": None,
                    "netto": None,
                    "brutto": None,
                    "entwurfsnummer": vorhandene_nummer,
                    "status": "vorhanden",
                }
            )
            continue

        vorlage_id = eintrag.get("letzte_rechnung_id")
        vorlage = _vorlage_lesen(client, vorlage_id)
        positionen = _positionen_lesen(client, vorlage_id)
        netto = round(sum(p["quantity"] * p["price"] for p in positionen), 2)
        steuer = round(
            sum(p["quantity"] * p["price"] * p["taxRate"] / 100 for p in positionen), 2
        )
        brutto = round(netto + steuer, 2)

        if dry_run:
            posten.append(
                {
                    "kunde": eintrag.get("name") or kontakt_id,
                    "rhythmus": rhythmus,
                    "zeitraum": f"{von}..{bis}",
                    "positionen": len(positionen),
                    "netto": netto,
                    "brutto": brutto,
                    "entwurfsnummer": None,
                    "status": "wuerde_angelegt",
                }
            )
            continue

        nummer = naechste_nummer(client, date.today().isoformat())
        rechnung_id = _entwurf_anlegen(
            client, kontakt_id, eintrag, vorlage, positionen, von, bis, nummer
        )
        posten.append(
            {
                "kunde": eintrag.get("name") or kontakt_id,
                "rhythmus": rhythmus,
                "zeitraum": f"{von}..{bis}",
                "positionen": len(positionen),
                "netto": netto,
                "brutto": brutto,
                "entwurfsnummer": nummer,
                "status": "angelegt",
                "rechnung_id": rechnung_id,
            }
        )
    return posten


def markdown_tabelle(posten: list[dict]) -> str:
    zeilen = [
        "| Kunde | Rhythmus | Zeitraum | Positionen | Netto | Brutto | Entwurfsnummer |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in posten:
        netto = betrag_format(p["netto"]) if p["netto"] is not None else "—"
        brutto = betrag_format(p["brutto"]) if p["brutto"] is not None else "—"
        positionen = str(p["positionen"]) if p["positionen"] is not None else "—"
        nummer = p["entwurfsnummer"] or "—"
        zeilen.append(
            f"| {p['kunde']} | {p['rhythmus']} | {p['zeitraum']} | {positionen} | "
            f"{netto} | {brutto} | {nummer} |"
        )
    return "\n".join(zeilen)


# --- Versand -----------------------------------------------------------------


def _entwuerfe_fuer_versand(
    client, kunden: dict, rhythmus: str, von: str
) -> list[dict]:
    ergebnis = []
    for kontakt_id, eintrag in sorted(kunden.items()):
        if eintrag.get("rhythmus") != rhythmus:
            continue
        for rechnung in _seiten(
            client,
            "/Invoice",
            **{
                "contact[id]": kontakt_id,
                "contact[objectName]": "Contact",
                "status": "100",
            },
        ):
            if (rechnung.get("deliveryDate") or "")[:10] != von:
                continue
            ergebnis.append(
                {
                    "kontakt_id": kontakt_id,
                    "kunde": eintrag.get("name") or kontakt_id,
                    "rechnung_id": rechnung["id"],
                    "nummer": rechnung.get("invoiceNumber") or rechnung["id"],
                    "brutto": round(float(rechnung.get("sumGross") or 0), 2),
                    "invoiceDate": (rechnung.get("invoiceDate") or "")[:10]
                    or date.today().isoformat(),
                    "timeToPay": int(
                        rechnung.get("timeToPay") or ZAHLUNGSZIEL_STANDARD
                    ),
                }
            )
    return ergebnis


def _email_empfaenger(client, kontakt_id: str) -> str | None:
    r = client.get(
        "/CommunicationWay",
        params={"contact[id]": kontakt_id, "contact[objectName]": "Contact"},
    )
    r.raise_for_status()
    for weg in r.json()["objects"]:
        if weg.get("type") == "EMAIL":
            return weg.get("value")
    return None


def _signatur_holen(client) -> str:
    r = client.get(
        "/TextTemplate", params={"objectType": "RE", "textType": "SIGNATURE"}
    )
    r.raise_for_status()
    objekte = r.json()["objects"]
    for vorlage in objekte:
        if str(vorlage.get("main")) in ("1", "True", "true"):
            return vorlage.get("text") or ""
    return objekte[0].get("text", "") if objekte else ""


def versandtext(
    nummer: str, betrag: str, von: str, bis: str, faellig: str, signatur: str
) -> str:
    return VERSAND_TEXT_VORLAGE.format(
        nr=nummer, betrag=betrag, von=von, bis=bis, faellig=faellig, signatur=signatur
    )


def _versandlog_pfad(von: str) -> Path:
    """Eine Log-Datei je Zeitraum-Start (nicht je Tag) — Wiederholungen an
    anderen Tagen bleiben gegen DENSELBEN Zeitraum idempotent."""
    return Path.home() / ".claude" / f"sevdesk-versand-{von}.json"


def _versandlog_lesen(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    try:
        geladen = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return geladen if isinstance(geladen, list) else []


def _versandlog_schreiben(pfad: Path, eintraege: list[dict]) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(
        json.dumps(eintraege, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _mit_429_wiederholung(aufruf, schlaf=time.sleep):
    """``aufruf()`` (kein Argument) fuehrt die POST-Anfrage aus. Bei HTTP 429
    wird bis zu ``VERSAND_MAX_VERSUCHE``-mal wiederholt — ``Retry-After`` hat
    Vorrang vor der festen Backoff-Folge. Rueckgabe: (letzte Antwort,
    Anzahl Wiederholungen)."""
    wiederholungen = 0
    antwort = aufruf()
    while antwort.status_code == 429 and wiederholungen < VERSAND_MAX_VERSUCHE:
        retry_after = antwort.headers.get("Retry-After")
        try:
            wartezeit = (
                float(retry_after)
                if retry_after
                else VERSAND_BACKOFF[min(wiederholungen, len(VERSAND_BACKOFF) - 1)]
            )
        except ValueError:
            wartezeit = VERSAND_BACKOFF[min(wiederholungen, len(VERSAND_BACKOFF) - 1)]
        schlaf(wartezeit)
        wiederholungen += 1
        antwort = aufruf()
    return antwort, wiederholungen


def versenden(
    client, kunden: dict, rhythmus: str, von: str, bis: str, ja: bool, schlaf=time.sleep
) -> dict:
    kandidaten = _entwuerfe_fuer_versand(client, kunden, rhythmus, von)
    log_pfad = _versandlog_pfad(von)
    log = _versandlog_lesen(log_pfad)
    bereits_gesendet = {e["rechnung_id"] for e in log if e.get("mail_id")}

    ergebnisse: list[dict] = []
    gesendet = 0
    uebersprungen = 0
    wiederholungen_gesamt = 0
    #: erst beim ersten tatsaechlichen Versand geholt (nicht vorab) — sonst
    #: kostet jeder Lauf einen TextTemplate-Aufruf, auch wenn am Ende gar
    #: nichts zu senden ist (Duplikate, falscher Status, keine E-Mail).
    signatur: str | None = None
    erste = True

    for kandidat in kandidaten:
        if kandidat["rechnung_id"] in bereits_gesendet:
            uebersprungen += 1
            ergebnisse.append(
                {**kandidat, "aktion": "uebersprungen (bereits gesendet)"}
            )
            continue

        r = client.get(f"/Invoice/{kandidat['rechnung_id']}")
        r.raise_for_status()
        objekte = r.json()["objects"]
        aktuell = objekte[0] if isinstance(objekte, list) else objekte
        if str(aktuell.get("status")) != "100":
            uebersprungen += 1
            ergebnisse.append(
                {
                    **kandidat,
                    "aktion": f"uebersprungen (status={aktuell.get('status')})",
                }
            )
            continue

        if not ja:
            ergebnisse.append({**kandidat, "aktion": "wuerde_gesendet"})
            continue

        empfaenger = _email_empfaenger(client, kandidat["kontakt_id"])
        if not empfaenger:
            uebersprungen += 1
            ergebnisse.append({**kandidat, "aktion": "uebersprungen (keine E-Mail)"})
            continue

        if not erste:
            schlaf(VERSAND_PAUSE_SEKUNDEN)
        erste = False

        if signatur is None:
            signatur = _signatur_holen(client)

        faellig = faelligkeit(kandidat["invoiceDate"], kandidat["timeToPay"])
        text = versandtext(
            kandidat["nummer"],
            betrag_format(kandidat["brutto"]),
            von,
            bis,
            faellig,
            signatur,
        )
        betreff = f"Rechnung {kandidat['nummer']} der IIL GmbH"

        def _aufruf(
            rid=kandidat["rechnung_id"], empf=empfaenger, txt=text, betr=betreff
        ):
            return client.post(
                f"/Invoice/{rid}/sendViaEmail",
                data={"toEmail": empf, "subject": betr, "text": txt, "copy": "true"},
            )

        antwort, wiederholt = _mit_429_wiederholung(_aufruf, schlaf=schlaf)
        wiederholungen_gesamt += wiederholt

        eintrag = {
            "rechnung_id": kandidat["rechnung_id"],
            "nummer": kandidat["nummer"],
            "empfaenger": empfaenger,
            "brutto": kandidat["brutto"],
            "http": antwort.status_code,
        }
        if antwort.status_code < 300:
            try:
                mail_id = (antwort.json() or {}).get("objects", {}).get("id")
            except (ValueError, AttributeError):
                mail_id = None
            eintrag["mail_id"] = mail_id
            gesendet += 1
            ergebnisse.append({**kandidat, "aktion": "gesendet"})
        else:
            eintrag["mail_id"] = None
            uebersprungen += 1
            ergebnisse.append(
                {**kandidat, "aktion": f"fehler (http={antwort.status_code})"}
            )
        log.append(eintrag)
        _versandlog_schreiben(log_pfad, log)

    return {
        "kandidaten": ergebnisse,
        "gesendet": gesendet,
        "uebersprungen": uebersprungen,
        "wiederholungen_429": wiederholungen_gesamt,
    }


# --- Journal (K2) --------------------------------------------------------


def journal_schreiben(
    pfad: Path,
    modus: str,
    rhythmus: str | None,
    kennzahlen: dict,
    dauer_sekunden: float,
) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    zeile = {
        "zeit": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "modus": modus,
        "rhythmus": rhythmus,
        "entwuerfe_angelegt": kennzahlen.get("entwuerfe_angelegt", 0),
        "uebersprungen": kennzahlen.get("uebersprungen", 0),
        "gesendet": kennzahlen.get("gesendet", 0),
        "wiederholungen_429": kennzahlen.get("wiederholungen_429", 0),
        "dauer_sekunden": round(dauer_sekunden, 1),
    }
    with pfad.open("a", encoding="utf-8") as datei:
        datei.write(json.dumps(zeile, ensure_ascii=False, sort_keys=True) + "\n")


# --- CLI -----------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modus = p.add_mutually_exclusive_group()
    modus.add_argument(
        "--monat", nargs="?", const="VORMONAT", help="YYYY-MM; ohne Wert: Vormonat"
    )
    modus.add_argument(
        "--quartal",
        nargs="?",
        const="VORQUARTAL",
        help="YYYY-Qn; ohne Wert: Vorquartal",
    )
    p.add_argument("--kunden-ermitteln", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--senden", action="store_true")
    p.add_argument("--ja", action="store_true")
    p.add_argument("--kunden-datei", default=str(KUNDEN_DATEI))
    p.add_argument("--journal", default=str(JOURNAL_DATEI))
    args = p.parse_args()

    kunden_datei = Path(args.kunden_datei).expanduser()
    journal_pfad = Path(args.journal).expanduser()

    client = _client()

    if args.kunden_ermitteln:
        bericht = kunden_ermitteln(client, kunden_datei)
        print(json.dumps(bericht, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.quartal is not None:
        quartal_wert = vorquartal() if args.quartal == "VORQUARTAL" else args.quartal
        von, bis = zeitraum_quartal(quartal_wert)
        rhythmus = RHYTHMUS_QUARTAL
    else:
        monat_wert = vormonat() if args.monat in (None, "VORMONAT") else args.monat
        von, bis = zeitraum_monat(monat_wert)
        rhythmus = RHYTHMUS_MONAT

    kunden = _kunden_lesen(kunden_datei)
    start = time.monotonic()

    if args.senden:
        ergebnis = versenden(client, kunden, rhythmus, von, bis, args.ja)
        dauer = time.monotonic() - start
        journal_schreiben(
            journal_pfad,
            "senden" if args.ja else "senden-vorschau",
            rhythmus,
            ergebnis,
            dauer,
        )
        if args.json:
            print(json.dumps(ergebnis, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            for k in ergebnis["kandidaten"]:
                print(
                    f"{k['kunde']} | {k['nummer']} | {betrag_format(k['brutto'])} | {k['aktion']}"
                )
            print(
                f"\ngesendet={ergebnis['gesendet']} uebersprungen={ergebnis['uebersprungen']} "
                f"wiederholungen_429={ergebnis['wiederholungen_429']}"
            )
        return 0

    posten = rechnungslauf(client, kunden, rhythmus, von, bis, args.dry_run)
    dauer = time.monotonic() - start
    kennzahlen = {
        "entwuerfe_angelegt": sum(1 for p in posten if p["status"] == "angelegt"),
        "uebersprungen": sum(1 for p in posten if p["status"] == "vorhanden"),
        "gesendet": 0,
        "wiederholungen_429": 0,
    }
    journal_schreiben(
        journal_pfad, "dry-run" if args.dry_run else "lauf", rhythmus, kennzahlen, dauer
    )

    if args.json:
        print(json.dumps(posten, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(markdown_tabelle(posten))
    return 0


if __name__ == "__main__":
    sys.exit(main())
