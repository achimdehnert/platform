#!/usr/bin/env python3
"""Gemeinsame Cloudflare-API-Hilfen für die Veröffentlichungs-Skripte.

Bewusst stdlib-only (wie tools/mail_agent): kein Fremd-Paket, damit die Skripte
auf jedem Host laufen, auf dem auch der Dienst läuft.

Token: ``~/.secrets/cloudflare_write_token``. Das kleinere ``cloudflare_api_token``
reicht **nicht** — DNS antwortet dort 403. Werte werden nie ausgegeben.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.cloudflare.com/client/v4"
TOKEN_DATEI = Path.home() / ".secrets" / "cloudflare_write_token"


def token() -> str:
    if not TOKEN_DATEI.exists():
        sys.exit(f"FEHLER: {TOKEN_DATEI} fehlt — ohne Write-Token geht DNS nicht.")
    wert = TOKEN_DATEI.read_text().split()
    if not wert:
        sys.exit(f"FEHLER: {TOKEN_DATEI} ist leer.")
    return wert[0]


def api(method: str, pfad: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{API}{pfad}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            "Authorization": f"Bearer {token()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        roh = (e.read() or b"").decode("utf-8", "replace")
        try:
            fehler = json.dumps(json.loads(roh).get("errors"))
        except ValueError:
            fehler = roh[:300]
        # Ein Berechtigungsfehler sieht an manchen Endpunkten wie eine leere Liste
        # aus (access/identity_providers). Darum laut abbrechen statt still weiter.
        sys.exit(f"FEHLER: HTTP {e.code} bei {method} {pfad} — {fehler}")


def umgebung(*namen: str) -> list[str]:
    """Pflicht-Umgebungsvariablen holen; fehlt eine, sofort abbrechen."""
    werte = []
    for name in namen:
        wert = os.environ.get(name, "").strip()
        if not wert:
            sys.exit(f"FEHLER: Umgebungsvariable {name} fehlt.")
        werte.append(wert)
    return werte


def zone_name(host: str) -> str:
    """Hostname → Zonenname (letzter Zwei-Teile-Suffix).

    'mail.iil.pet' → 'iil.pet'; 'iil.pet' bleibt 'iil.pet'. Mehrteilige
    Endungen wie '.co.uk' deckt das nicht ab — bei denen die Zone übergeben,
    statt sie zu raten.
    """
    return ".".join(host.strip(".").split(".")[-2:])


def zone_und_konto(host: str) -> tuple[str, str]:
    """Hostname → (zone_id, account_id)."""
    name = zone_name(host)
    treffer = api("GET", f"/zones?name={name}")["result"] or []
    if not treffer:
        sys.exit(f"FEHLER: Zone '{name}' nicht gefunden (Token-Reichweite?).")
    zone = treffer[0]
    return zone["id"], zone["account"]["id"]


#: Erlaubte Form eines Tunnel-Ursprungs: `host:port`, Port 1–65535.
#: Host ist ein Name oder eine IPv4; IPv6 gehoert in eckige Klammern.
_ORIGIN = re.compile(
    r"^(?:\[[0-9A-Fa-f:]+\]|[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?):(\d{1,5})$"
)


def pruefe_origin(origin: str) -> str:
    """Ursprung eines Tunnels validieren — oder laut abbrechen.

    **Warum das laut sein muss (Retro-Befund 2026-09-02):** `tunnel_anlegen.py`
    schrieb einen gesetzten `ORIGIN` ungeprueft als `service: http://{origin}` in
    die Config und meldete danach bedingungslos Erfolg. Ein Wert mit Schema
    (`http://10.99.0.2:11434`) erzeugt `http://http://…` — eine Config, die
    `cloudflared` annimmt und die still nichts ausliefert.

    Der nachgelagerte Schritt faengt das **nicht**: `veroeffentlichen.sh` wertet
    jedes `nicht 200` als Erfolg, weil es die Access-Abweisung (302) sucht. Ein
    502 durch einen kaputten Ursprung ist davon nicht zu unterscheiden. Deshalb
    ist diese Pruefung die einzige Stelle in der Kette, an der der Fehler
    ueberhaupt auffallen kann.

    Geprueft wird die **Form**, nicht die Erreichbarkeit — letztere gehoert auf
    das Gateway, auf dem der Tunnel laeuft (siehe Runbook, Abschnitt
    Gegenstellen-Variante).
    """
    wert = (origin or "").strip()
    if not wert:
        sys.exit("FEHLER: ORIGIN ist leer — erwartet wird `host:port`.")
    if "://" in wert:
        sys.exit(
            f"FEHLER: ORIGIN '{wert}' enthaelt ein Schema. Erwartet wird nur "
            "`host:port` — das `http://` setzt das Werkzeug selbst."
        )
    if "/" in wert:
        sys.exit(f"FEHLER: ORIGIN '{wert}' enthaelt einen Pfad. Erwartet: `host:port`.")
    treffer = _ORIGIN.match(wert)
    if not treffer:
        sys.exit(
            f"FEHLER: ORIGIN '{wert}' ist keine gueltige `host:port`-Angabe "
            "(IPv6 gehoert in eckige Klammern)."
        )
    port = int(treffer.group(1))
    if not 1 <= port <= 65535:
        sys.exit(f"FEHLER: ORIGIN '{wert}' hat den Port {port} — erlaubt ist 1–65535.")
    return wert
