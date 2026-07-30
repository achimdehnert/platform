#!/usr/bin/env python3
"""Cloudflare-Access-Anwendung + Owner-Richtlinie für einen Hostnamen anlegen.

Idempotent: existiert die Anwendung schon, wird sie wiederverwendet; existiert die
Richtlinie schon, bleibt sie unangetastet.

Umgebung:
  HOST      Pflicht, z.B. mail.iil.pet
  NAME      Anzeigename (Default: "<HOST> — Access")
  ERLAUBT   Komma-Liste der E-Mails (Default siehe unten)

🌀 Identitäts-Falle: Das Zero-Trust-Konto hat genau EINEN Identitäts-Anbieter —
GitHub, keine Einmal-PIN. Cloudflare reicht die E-Mail des GitHub-Kontos weiter,
und das ist `admin@wir-digital.de`. Eine Richtlinie ohne diese Adresse sperrt den
Owner aus. Details: docs/runbooks/loopback-dienst-hinter-cloudflare-access.md
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cf import api, umgebung, zone_und_konto  # noqa: E402

STANDARD_ERLAUBT = "admin@wir-digital.de,achim.dehnert@iil.gmbh"


def main() -> None:
    (host,) = umgebung("HOST")
    name = os.environ.get("NAME") or f"{host} — Access"
    erlaubt = [
        e.strip()
        for e in (os.environ.get("ERLAUBT") or STANDARD_ERLAUBT).split(",")
        if e.strip()
    ]
    _, konto = zone_und_konto(host)

    apps = api("GET", f"/accounts/{konto}/access/apps?per_page=100")["result"] or []
    treffer = [a for a in apps if a.get("domain") == host]
    if treffer:
        aid = treffer[0]["id"]
        print(f"Access-Anwendung für {host} existiert bereits: {aid}")
    else:
        aid = api(
            "POST",
            f"/accounts/{konto}/access/apps",
            {
                "name": name,
                "domain": host,
                "type": "self_hosted",
                "session_duration": "24h",
                "app_launcher_visible": False,
                "http_only_cookie_attribute": True,
            },
        )["result"]["id"]
        print(f"Access-Anwendung angelegt: {aid}")

    vorhanden = (
        api("GET", f"/accounts/{konto}/access/apps/{aid}/policies")["result"] or []
    )
    if any(p.get("name") == "Owner" for p in vorhanden):
        print("Richtlinie 'Owner' existiert bereits.")
    else:
        api(
            "POST",
            f"/accounts/{konto}/access/apps/{aid}/policies",
            {
                "name": "Owner",
                "decision": "allow",
                "include": [{"email": {"email": e}} for e in erlaubt],
            },
        )
        print(f"Richtlinie 'Owner' gesetzt: {', '.join(erlaubt)}")
    print(f"APP_ID={aid}")


if __name__ == "__main__":
    main()
