#!/usr/bin/env python3
"""Einen einzelnen Pfad hinter Cloudflare Access legen — Vorbild-Richtlinie spiegeln.

Schwesterwerkzeug zu `cf_access_idp_pin.py`. Der Anlass ist ein wiederkehrender
Fall: Ein Host laeuft ueber Cloudflare, aber **ohne** Access, und eine einzelne
empfindliche Route (typisch `/admin`) soll geschuetzt werden, ohne den ganzen
Host zu gaten.

Warum ein Werkzeug und kein Klick im Dashboard: Der Zuschnitt hat drei Stellen,
an denen ein Handgriff still danebengreift.

1. **`allowed_idps` leer heisst ALLE Anbieter**, nicht keiner. Wer die Liste im
   Dashboard uebergeht, oeffnet die neue Anwendung auch fuer Anmeldedienste, die
   fuer ganz andere Anwendungen gedacht sind (bei uns ein Einmal-PIN fuer zwei
   externe Personen). Dieses Werkzeug setzt den Anbieter **explizit**.
2. **Eine zu kurze Adressliste sperrt aus.** Access sitzt VOR der Anmeldung der
   Anwendung; fehlt die Adresse, die der Anmeldeweg tatsaechlich liefert, ist die
   Route zu — auch fuer den Eigentuemer. Deshalb wird die Liste nicht getippt,
   sondern von einer **Vorbild-Anwendung** uebernommen, die nachweislich benutzt
   wird.
3. **Kennungen gehoeren nicht in dieses Repo.** `platform` ist oeffentlich; IdP-
   und Anwendungs-Kennungen werden zur Laufzeit aufgeloest, nie hartkodiert
   (gleiche Linie wie `cf_access_idp_pin.py`).

Ohne `--anwenden` wird nichts geschrieben.

    ./cf_access_pfad_schuetzen.py --ziel host.example/admin --vorbild host2.example
    ./cf_access_pfad_schuetzen.py --ziel host.example/admin --vorbild host2.example --anwenden

Liest `~/.secrets/cloudflare_account_id` und `~/.secrets/cloudflare_write_token`.
Rueckbau: die angelegte Anwendung loeschen — der Vorzustand ist „kein Access".
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

GEHEIM = pathlib.Path.home() / ".secrets"
BASIS = "https://api.cloudflare.com/client/v4/accounts"


def _lies_geheim(name: str) -> str:
    pfad = GEHEIM / name
    if not pfad.is_file():
        sys.exit(f"fehlt: ~/.secrets/{name}")
    return pfad.read_text().strip()


def api(acc: str, tok: str, pfad: str, methode: str = "GET", nutzlast=None) -> dict:
    daten = json.dumps(nutzlast).encode() if nutzlast is not None else None
    req = urllib.request.Request(
        f"{BASIS}/{acc}/{pfad}",
        data=daten,
        method=methode,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def tarne(adresse: str) -> str:
    """Adresse fuer die Ausgabe kuerzen — Protokolle sind kein Adressbuch."""
    name, _, dom = adresse.partition("@")
    return f"{name[:2]}…@{dom}" if dom else adresse


def anbieter_id(acc: str, tok: str, art: str) -> str:
    idps = api(acc, tok, "access/identity_providers").get("result", [])
    treffer = [i for i in idps if i.get("type") == art]
    if len(treffer) != 1:
        sys.exit(
            f"erwartet genau einen Anbieter vom Typ '{art}', gefunden: {len(treffer)}"
        )
    return treffer[0]["id"]


def vorbild_regeln(acc: str, tok: str, apps: list, vorbild: str) -> list:
    quelle = [a for a in apps if a.get("domain") == vorbild]
    if not quelle:
        sys.exit(f"Vorbild-Anwendung '{vorbild}' nicht gefunden")
    pol = api(acc, tok, f"access/apps/{quelle[0]['id']}/policies").get("result", [])
    erlauben = [p for p in pol if p.get("decision") == "allow"]
    if not erlauben:
        sys.exit(f"Vorbild '{vorbild}' hat keine allow-Richtlinie")
    regeln = [r for r in erlauben[0].get("include", []) if "email" in r]
    if not regeln:
        sys.exit(f"Vorbild '{vorbild}' hat keine E-Mail-Regeln — Zuschnitt unklar")
    return regeln


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ziel", required=True, help="host/pfad, z.B. host.example/admin")
    ap.add_argument(
        "--vorbild",
        required=True,
        help="Domain, deren allow-Richtlinie gespiegelt wird",
    )
    ap.add_argument("--anbieter", default="github", help="IdP-Typ (Default github)")
    ap.add_argument("--dauer", default="24h", help="session_duration (Default 24h)")
    ap.add_argument("--anwenden", action="store_true", help="wirklich schreiben")
    args = ap.parse_args()

    acc, tok = (
        _lies_geheim("cloudflare_account_id"),
        _lies_geheim("cloudflare_write_token"),
    )
    apps = api(acc, tok, "access/apps?per_page=50").get("result", [])

    host = args.ziel.split("/")[0]
    kollision = [a for a in apps if str(a.get("domain", "")) == args.ziel]
    if kollision:
        print(f"Es gibt bereits eine Anwendung fuer '{args.ziel}' — nichts zu tun:")
        for a in kollision:
            print(f"  {a.get('name')} | uid {a.get('id')}")
        return 0

    breiter = [a for a in apps if str(a.get("domain", "")) == host]
    if breiter:
        print(
            f"Hinweis: '{host}' ist bereits als Ganzes geschuetzt — ein Pfad-Eintrag "
            f"waere doppelt gemoppelt:"
        )
        for a in breiter:
            print(f"  {a.get('name')} | uid {a.get('id')}")
        return 0

    include = vorbild_regeln(acc, tok, apps, args.vorbild)
    anwendung = {
        "name": f"{args.ziel} — Access",
        "domain": args.ziel,
        "type": "self_hosted",
        "session_duration": args.dauer,
        "allowed_idps": [anbieter_id(acc, tok, args.anbieter)],
        "app_launcher_visible": False,
        "http_only_cookie_attribute": True,
    }

    zeig = dict(anwendung, allowed_idps=[f"<{args.anbieter}>"])
    print("=== Anwendung ===")
    print(json.dumps(zeig, indent=2, ensure_ascii=False))
    print(
        f"\n=== Richtlinie (von '{args.vorbild}' gespiegelt, {len(include)} Adressen) ==="
    )
    for r in include:
        print(f"  {tarne(r['email']['email'])}")

    if not args.anwenden:
        print("\nTROCKENLAUF — nichts geschrieben. Mit --anwenden ausfuehren.")
        return 0

    erg = api(acc, tok, "access/apps", "POST", anwendung)
    if not erg.get("success"):
        sys.exit(f"Anlegen fehlgeschlagen: {erg.get('errors')}")
    uid = erg["result"]["id"]
    print(f"\nAnwendung angelegt: uid={uid}")

    pol = api(
        acc,
        tok,
        f"access/apps/{uid}/policies",
        "POST",
        {"name": "Owner", "decision": "allow", "include": include, "precedence": 1},
    )
    if not pol.get("success"):
        print(f"WARNUNG: Richtlinie fehlgeschlagen: {pol.get('errors')}")
        print(f"Die Anwendung ist damit ZU. Rueckbau: DELETE access/apps/{uid}")
        return 1
    print("Richtlinie angelegt.")
    print(f"\nGegenprobe: curl -sI https://{args.ziel}/ | grep -i location")
    print(f"Rueckbau:   DELETE access/apps/{uid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
