#!/usr/bin/env python3
"""Cloudflare-Access-Anwendung + Owner-Richtlinie für einen Hostnamen anlegen.

Idempotent: existiert die Anwendung schon, wird sie wiederverwendet; existiert die
Richtlinie schon, bleibt sie unangetastet.

Umgebung:
  HOST         Pflicht, z.B. mail.iil.pet
  NAME         Anzeigename (Default: "<HOST> — Access")
  ERLAUBT      Komma-Liste der E-Mails (Default siehe unten)
  GESUNDHEIT   Komma-Liste offener Pfade (Default: livez,healthz,readyz; "" schaltet ab)
  TOKEN_ID     Service-Token fuer Maschinen-Zugriff (Default: playwright-verify; "" schaltet ab)

🌀 Identitäts-Falle: Das Zero-Trust-Konto hat genau EINEN Identitäts-Anbieter —
GitHub, keine Einmal-PIN. Cloudflare reicht die E-Mail des GitHub-Kontos weiter,
und das ist `admin@wir-digital.de`. Eine Richtlinie ohne diese Adresse sperrt den
Owner aus. Details: docs/runbooks/loopback-dienst-hinter-cloudflare-access.md

🌀 Deploy-Falle: Eine Access-Wand vor einem deployten Dienst bricht dessen
Deploy, wenn der Gesundheitspfad mitgesperrt wird. `scripts/deploy.sh` akzeptiert
**ausschliesslich HTTP 200**; Access antwortet unangemeldet mit 302 — der Deploy
laeuft ins Retry-Budget und endet mit Exit 4. Bei apo-hub (2026-07-18) wurde
daraufhin die externe Pruefung dauerhaft per `skip_external_verify` stillgelegt,
also die Luecke dokumentiert statt geschlossen
(docs/conventions/access-gated-hosts-pruefen.md).

Deshalb legt dieses Skript neben der Wand **immer** die offenen Gesundheitspfade
an — als eigene, pfadgenaue Anwendungen mit `decision: bypass`. Genau so ist
illustration.iil.pet konfiguriert (Vorbild, gemessen 2026-08-11: `/` → 302,
`/livez/` → 200). Wer das nicht will, setzt `GESUNDHEIT=""` und weiss, was er tut.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cf import api, umgebung, zone_und_konto  # noqa: E402

STANDARD_ERLAUBT = "admin@wir-digital.de,achim.dehnert@iil.gmbh"

#: Service-Token `playwright-verify` — dasselbe, das iil.pet als Richtlinie
#: `playwright-verify-svc` traegt und das `tools/cf-access-fetch.sh` benutzt.
#: Ohne diese Richtlinie ist die neue Anwendung fuer JEDE Maschine blind: kein
#: Playwright-Lauf, kein CI-Check, keine Inhaltspruefung — nur 302.
#: Genau daraus entstand bei apo-hub die dauerhaft stillgelegte Pruefung
#: (docs/conventions/access-gated-hosts-pruefen.md). Ueber TOKEN_ID="" abwaehlbar.
STANDARD_TOKEN_ID = "2ad795e6-dbe9-4654-a657-3118dee21736"

#: Pfade, die offen bleiben muessen, damit Deploy-Gate und Uptime-Melder
#: weiterhin ein 200 sehen. Ohne fuehrenden Slash — Cloudflare erwartet
#: "<host>/<pfad>" als Domain der pfadgenauen Anwendung.
#:
#: Alle drei Haus-Varianten sind drin, weil die Apps sich unterscheiden:
#: `livez`/`healthz` kurzschliesst die HealthBypassMiddleware (ADR-167),
#: `readyz` traegt bei manchen Apps den Versions-Marker fuer die
#: Deploy-Verifikation. Ein Bypass auf einen Pfad, den es in einer App nicht
#: gibt, ist wirkungslos (er oeffnet ein 404) — das ist billiger als ein
#: vergessener Pfad, der einen Deploy zum Stehen bringt.
STANDARD_GESUNDHEIT = "livez,healthz,readyz"


def _gesundheitspfad_oeffnen(konto: str, host: str, pfad: str) -> None:
    """Legt eine pfadgenaue Anwendung mit bypass-Richtlinie an. Idempotent."""
    domain = f"{host}/{pfad}"
    apps = api("GET", f"/accounts/{konto}/access/apps?per_page=100")["result"] or []
    treffer = [a for a in apps if a.get("domain") == domain]

    if treffer:
        aid = treffer[0]["id"]
        print(f"Gesundheitspfad {domain} existiert bereits: {aid}")
    else:
        aid = api(
            "POST",
            f"/accounts/{konto}/access/apps",
            {
                "name": f"{domain} — Gesundheitspfad (offen)",
                "domain": domain,
                "type": "self_hosted",
                "session_duration": "24h",
                "app_launcher_visible": False,
                "http_only_cookie_attribute": True,
            },
        )["result"]["id"]
        print(f"Gesundheitspfad {domain} angelegt: {aid}")

    vorhanden = (
        api("GET", f"/accounts/{konto}/access/apps/{aid}/policies")["result"] or []
    )
    if any(p.get("decision") == "bypass" for p in vorhanden):
        print(f"  bypass-Richtlinie existiert bereits fuer {domain}.")
        return

    api(
        "POST",
        f"/accounts/{konto}/access/apps/{aid}/policies",
        {
            "name": "Deploy-Health offen",
            "decision": "bypass",
            "include": [{"everyone": {}}],
        },
    )
    print(f"  bypass-Richtlinie gesetzt fuer {domain}.")


def main() -> None:
    (host,) = umgebung("HOST")
    name = os.environ.get("NAME") or f"{host} — Access"
    erlaubt = [
        e.strip()
        for e in (os.environ.get("ERLAUBT") or STANDARD_ERLAUBT).split(",")
        if e.strip()
    ]
    gesundheit = [
        p.strip().lstrip("/")
        for p in os.environ.get("GESUNDHEIT", STANDARD_GESUNDHEIT).split(",")
        if p.strip()
    ]
    _, konto = zone_und_konto(host)

    # Zuerst die offenen Pfade, DANN die Wand. Andersherum gaebe es ein Fenster,
    # in dem der Gesundheitspfad bereits gesperrt ist — genau waehrenddessen
    # laufende Deploys oder Uptime-Pruefungen wuerden fehlschlagen.
    for pfad in gesundheit:
        _gesundheitspfad_oeffnen(konto, host, pfad)

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

    token_id = os.environ.get("TOKEN_ID", STANDARD_TOKEN_ID).strip()
    if not token_id:
        print("Kein Service-Token gesetzt — die Anwendung bleibt fuer Maschinen blind.")
    elif any(p.get("name") == "playwright-verify-svc" for p in vorhanden):
        print("Richtlinie 'playwright-verify-svc' existiert bereits.")
    else:
        api(
            "POST",
            f"/accounts/{konto}/access/apps/{aid}/policies",
            {
                "name": "playwright-verify-svc",
                "decision": "non_identity",
                "include": [{"service_token": {"token_id": token_id}}],
            },
        )
        print("Richtlinie 'playwright-verify-svc' gesetzt (Maschinen-Zugriff).")

    print(f"APP_ID={aid}")


if __name__ == "__main__":
    main()
