#!/usr/bin/env python3
"""Graph-Kurzlinks an die internetMessageId binden — das Graph-Gegenstueck zu anker.py.

Warum es das gibt: Die Kurz-ID-Registry (`~/.claude/mail-links.json`) hielt je
Eintrag nur die Graph-`id` der Nachricht. Die ist NICHT stabil: Outlook vergibt
beim Verschieben in einen anderen Ordner eine neue. Gemessen am 2026-09-01
(platform#2563): 5 von 12 `/r/<nr>`-Links antworteten 502 „Graph antwortet
404", weil die Mail seit der Registrierung abgelegt worden war.

Stabil ist die `internetMessageId` — der RFC-Message-ID-Header, derselbe Anker,
den `anker.py` fuer IMAP nutzt. Mit ihr laesst sich die Nachricht nach jedem
Ordnerwechsel per `$filter=internetMessageId eq '…'` wiederfinden.

Drei Wege, in dieser Reihenfolge:

1. **Die Graph-id gilt noch** → nur die internetMessageId nachtragen, falls
   sie fehlt (Bestandsdaten von vor diesem Modul).
2. **404, internetMessageId bekannt** → per Filter wiederfinden, Graph-id
   nachziehen. Das tut der Mail-Dienst auch beim Rendern selbst.
3. **404, keine internetMessageId** → per `$search` ueber die Betreffs des
   Vorgangs suchen: erst der thread_key, dann jeder Betreff, den der Verlauf
   in Anfuehrungszeichen nennt (so verlangt es mailcheck.md, wenn keine Nummer
   vorliegt). Der erste Betreff mit Treffern zaehlt; darunter ist die AELTESTE
   Nachricht der Anker, so wie `/a/<nr>` den Anfang des Strangs meint. Ohne
   Treffer bleibt der Eintrag tot und wird gemeldet — nicht geraten.

Die HTTP-Funktion wird hereingereicht, damit die Tests ohne Netz auskommen.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_mail  # noqa: E402

FELDER = "id,subject,receivedDateTime,internetMessageId"
GUELTIG = "gueltig"
NACHGEZOGEN = "nachgezogen"
NEU_GESUCHT = "neu-gesucht"
TOT = "tot"
UNPRUEFBAR = "unpruefbar"

_PRAEFIX = re.compile(r"^\s*(?:(?:aw|re|wg|fwd?|antw)\s*:\s*)+", re.I)


@dataclass
class Befund:
    kurz: str
    zustand: str
    hinweis: str = ""


def _http_standard(method: str, url: str, **kw):
    return graph_mail._http(method, url, **kw)


def hole(tok: str, graph_id: str, http=None) -> tuple[int, dict]:
    """(Status, Nachricht) — die Nachricht nur mit den Ankerfeldern."""
    http = http or _http_standard
    r = http(
        "GET",
        f"{graph_mail.GRAPH}/me/messages/{quote(graph_id, safe='')}?$select={FELDER}",
        headers=graph_mail._auth(tok),
    )
    try:
        daten = r.json() if r.status_code == 200 else {}
    except ValueError:
        daten = {}
    return r.status_code, daten


def finde_per_internet_id(tok: str, internet_id: str, http=None) -> dict | None:
    """Die Nachricht mit dieser internetMessageId — egal in welchem Ordner."""
    http = http or _http_standard
    wert = internet_id.replace("'", "''")
    r = http(
        "GET",
        f"{graph_mail.GRAPH}/me/messages?$filter=internetMessageId eq "
        f"{quote(chr(39) + wert + chr(39), safe='')}&$select={FELDER}",
        headers=graph_mail._auth(tok),
    )
    if r.status_code != 200:
        return None
    treffer = r.json().get("value", [])
    return treffer[0] if treffer else None


def normalisiere(betreff: str) -> str:
    return " ".join(_PRAEFIX.sub("", betreff or "").lower().split())


def finde_per_betreff(tok: str, betreff: str, http=None) -> list[dict]:
    """Alle Nachrichten, deren Betreff den Vorgangs-Betreff enthaelt — aelteste zuerst."""
    http = http or _http_standard
    suche = quote(f'"subject:{betreff}"', safe="")
    r = http(
        "GET",
        f"{graph_mail.GRAPH}/me/messages?$search={suche}&$select={FELDER}&$top=50",
        headers=graph_mail._auth(tok),
    )
    if r.status_code != 200:
        return []
    ziel = normalisiere(betreff)
    passend = [
        m
        for m in r.json().get("value", [])
        if ziel and ziel in normalisiere(m.get("subject"))
    ]
    return sorted(passend, key=lambda m: m.get("receivedDateTime") or "")


def heile_eintrag(
    kurz: str, eintrag: dict, tok: str, betreffe: list[str] | None = None, http=None
) -> Befund:
    """Einen Registry-Eintrag pruefen und — wo moeglich — an Ort und Stelle nachziehen."""
    status, nachricht = hole(tok, eintrag.get("graph_id", ""), http)
    if status == 200:
        if not eintrag.get("internet_message_id") and nachricht.get(
            "internetMessageId"
        ):
            eintrag["internet_message_id"] = nachricht["internetMessageId"]
            return Befund(kurz, GUELTIG, "internetMessageId nachgetragen")
        return Befund(kurz, GUELTIG)
    if status != 404:
        return Befund(kurz, UNPRUEFBAR, f"Graph antwortet {status}")

    if eintrag.get("internet_message_id"):
        neu = finde_per_internet_id(tok, eintrag["internet_message_id"], http)
        if neu:
            eintrag["graph_id"] = neu["id"]
            return Befund(kurz, NACHGEZOGEN, "ueber internetMessageId wiedergefunden")
        return Befund(kurz, TOT, "internetMessageId in keinem Ordner mehr")

    betreffe = [b for b in (betreffe or []) if b]
    if not betreffe:
        return Befund(kurz, TOT, "keine internetMessageId und kein Betreff zum Suchen")
    treffer: list[dict] = []
    for betreff in betreffe:
        treffer = finde_per_betreff(tok, betreff, http)
        if treffer:
            break
    if not treffer:
        return Befund(
            kurz,
            TOT,
            f"kein Treffer fuer {len(betreffe)} Betreff(e), z.B. '{betreffe[0][:40]}'",
        )
    aelteste = treffer[0]
    eintrag["graph_id"] = aelteste["id"]
    if aelteste.get("internetMessageId"):
        eintrag["internet_message_id"] = aelteste["internetMessageId"]
    return Befund(
        kurz,
        NEU_GESUCHT,
        f"{len(treffer)} Treffer, aelteste vom {aelteste.get('receivedDateTime', '')[:10]}",
    )


def heile(
    registry: dict[str, dict], betreffe: dict[str, list[str]], tok: str, http=None
) -> list[Befund]:
    """Alle Eintraege; `betreffe` ist Kurz-ID → Betreff-Kandidaten (aus dem Ledger)."""
    return [
        heile_eintrag(kurz, eintrag, tok, betreffe.get(kurz, []), http)
        for kurz, eintrag in sorted(registry.items())
    ]


#: Betreff in einfachen oder typografischen Anfuehrungszeichen — die Form, die
#: mailcheck.md fuer Eintraege ohne Nummer vorschreibt.
_ZITAT = re.compile(r"['‚‘\"„»]([^'’‘\"«»\n]{8,120})['’‘\"«»]")


def betreffe_aus_ledger(ledger: dict) -> dict[str, list[str]]:
    """Kurz-ID (= Board-Nummer) → [thread_key, zitierte Betreffs aus dem Verlauf …]."""
    ergebnis: dict[str, list[str]] = {}
    for v in ledger.get("vorgaenge", []):
        if v.get("nr") is None:
            continue
        kandidaten: list[str] = []
        for text in [
            str(v.get("thread_key") or ""),
            *_ZITAT.findall(str(v.get("notiz") or "")),
        ]:
            text = text.strip()
            if text and text not in kandidaten:
                kandidaten.append(text)
        if kandidaten:
            ergebnis[str(v["nr"])] = kandidaten
    return ergebnis


def bericht(befunde: list[Befund]) -> str:
    zaehler: dict[str, int] = {}
    for b in befunde:
        zaehler[b.zustand] = zaehler.get(b.zustand, 0) + 1
    kopf = f"{len(befunde)} Kurzlinks: " + ", ".join(
        f"{n} {z}" for z, n in sorted(zaehler.items())
    )
    zeilen = [kopf] + [
        f"  {b.kurz:<8} {b.zustand:<12} {b.hinweis}"
        for b in befunde
        if b.zustand != GUELTIG or b.hinweis
    ]
    return "\n".join(zeilen)
