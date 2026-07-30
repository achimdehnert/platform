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
