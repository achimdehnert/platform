#!/usr/bin/env python3
"""Cloudflare Access: Anmeldedienste festnageln und Einmal-PIN einrichten.

Ausgangslage: alle 16 Access-Anwendungen haben `allowed_idps` leer. Laut Cloudflare
heisst leer "alle im Konto konfigurierten Anbieter". Ein neu aktivierter Anbieter
gaelte damit voraussichtlich sofort ueberall — auch fuer praes.iil.ai (LRA) und
schulungspass.de. Deshalb: erst festnageln, dann PIN anlegen, dann gezielt EINE
Anwendung oeffnen.

  ./cf_access_idp_pin.py --trocken            zeigt alle drei Schritte, aendert nichts
  ./cf_access_idp_pin.py --schritt 1          nagelt alle Anwendungen auf GitHub fest
  ./cf_access_idp_pin.py --schritt 2          legt den Einmal-PIN-Anbieter an
  ./cf_access_idp_pin.py --schritt 3          oeffnet NUR docs.iil.pet fuer PIN + md@/sd@
  ./cf_access_idp_pin.py --schritt 1 --token cloudflare_api_token   anderes Token

Schritt 1 schreibt zuerst NUR eine einzige Anwendung (docs.iil.pet, gesichert) als
Berechtigungsprobe. Scheitert sie, bricht das Skript ab und druckt den HTTP-Fehler
im Wortlaut — die anderen 15 bleiben unberuehrt. Schritt 2 verweigert den Dienst,
solange noch eine Anwendung offen ist. Jeder Schritt sichert vorher nach
~/cf_access_sicherung/ und prueft hinterher nach.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime

ZIEL_DOMAIN = "docs.iil.pet"
NEUE_MAILS = ["md@dehnert.team", "sd@dehnert.team"]
SICHERUNG = os.path.expanduser("~/cf_access_sicherung")
GEHEIM = os.path.expanduser("~/.secrets")


def geheimnis(name):
    with open(os.path.join(GEHEIM, name)) as f:
        return f.read().strip()


TOKEN_NAME = "cloudflare_write_token"
if "--token" in sys.argv:
    TOKEN_NAME = sys.argv[sys.argv.index("--token") + 1]

KONTO = geheimnis("cloudflare_account_id")
BASIS = "https://api.cloudflare.com/client/v4/accounts/%s/access/" % KONTO
KOPF = {
    "Authorization": "Bearer " + geheimnis(TOKEN_NAME),
    "Content-Type": "application/json",
}


def api(pfad, methode="GET", daten=None):
    """(ok, ergebnis_oder_fehlertext) — wirft nie, damit der Fehler lesbar bleibt."""
    anfrage = urllib.request.Request(
        BASIS + pfad,
        method=methode,
        headers=KOPF,
        data=json.dumps(daten).encode() if daten is not None else None,
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=30) as antwort:
            return True, json.load(antwort)
    except urllib.error.HTTPError as fehler:
        roh = fehler.read().decode("utf-8", "replace")
        try:
            koerper = json.loads(roh)
            teile = [
                "%s %s" % (e.get("code"), e.get("message"))
                for e in koerper.get("errors", [])
            ]
            meldung = " | ".join(teile) or roh[:300]
        except ValueError:
            meldung = roh[:300]
        return False, "HTTP %s — %s" % (fehler.code, meldung)
    except Exception as fehler:  # Netz, DNS, Timeout
        return False, "%s: %s" % (type(fehler).__name__, str(fehler)[:150])


def sichere(name, inhalt):
    os.makedirs(SICHERUNG, exist_ok=True)
    stempel = datetime.now().strftime("%Y%m%d-%H%M%S")
    ziel = os.path.join(SICHERUNG, "%s-%s.json" % (name, stempel))
    with open(ziel, "w") as f:
        json.dump(inhalt, f, indent=1, ensure_ascii=False)
    return ziel


def lies(pfad, was):
    ok, d = api(pfad)
    if not ok:
        print("   ABBRUCH beim Lesen (%s): %s" % (was, d))
        sys.exit(1)
    return d["result"]


def github_id(idps):
    treffer = [i for i in idps if i.get("type") == "github"]
    if not treffer:
        print("   ABBRUCH: kein GitHub-Anmeldedienst im Konto gefunden")
        sys.exit(1)
    return treffer[0]["id"]


def pin_id(idps):
    treffer = [i for i in idps if i.get("type") == "onetimepin"]
    return treffer[0]["id"] if treffer else None


def ziel_app(apps):
    treffer = [a for a in apps if ZIEL_DOMAIN in str(a.get("domain", ""))]
    if not treffer:
        print("   ABBRUCH: Anwendung %s nicht gefunden" % ZIEL_DOMAIN)
        sys.exit(1)
    return treffer[0]


# Felder, die Cloudflare selbst verwaltet — duerfen im PUT nicht mitgeschickt werden.
NUR_LESEN = {"id", "uid", "aud", "created_at", "updated_at"}


def setze_idps(app, idps_liste, beschriftung):
    """PUT mit vollstaendigem Rumpf + Nachlesen. Gibt (ok, meldung) zurueck.

    PATCH beantwortet dieser Endpunkt mit HTTP 405 (Code 10405) — er kennt nur PUT,
    und PUT ersetzt. Deshalb wird der gelesene Stand vollstaendig zurueckgeschickt und
    nur `allowed_idps` ausgetauscht. Die Richtlinien werden als Referenz uebergeben
    (id + Reihenfolge), nicht als Inhalt — sonst wuerden sie mitersetzt.
    """
    rumpf = {k: v for k, v in app.items() if k not in NUR_LESEN}
    rumpf["allowed_idps"] = idps_liste
    if isinstance(app.get("policies"), list):
        rumpf["policies"] = [
            {"id": p["id"], "precedence": i + 1}
            for i, p in enumerate(app["policies"])
            if isinstance(p, dict) and p.get("id")
        ]
    ok, d = api("apps/%s" % app["id"], "PUT", rumpf)
    if not ok:
        return False, d
    if sorted(d["result"].get("allowed_idps") or []) != sorted(idps_liste):
        return False, "PUT war 200, aber allowed_idps wurde nicht uebernommen"
    return True, beschriftung


# ---------------------------------------------------------------- Schritt 1


def schritt1(trocken):
    print("== Schritt 1: alle Anwendungen auf GitHub festnageln")
    apps = lies("apps", "Anwendungen")
    idps = lies("identity_providers", "Anmeldedienste")
    gh = github_id(idps)
    offen = [a for a in apps if not a.get("allowed_idps")]
    print("   Anwendungen: %d   davon ohne Festlegung: %d" % (len(apps), len(offen)))
    if not offen:
        print("   nichts zu tun")
        return True

    if trocken:
        for a in offen:
            print("   WUERDE festnageln: %s" % str(a.get("name"))[:50])
        print("   (Probe zuerst auf %s, danach der Rest)" % ZIEL_DOMAIN)
        return True

    print("   Sicherung: %s" % sichere("apps-vor-schritt1", apps))
    probe = (
        ziel_app(offen)
        if any(ZIEL_DOMAIN in str(a.get("domain", "")) for a in offen)
        else offen[0]
    )
    print("   Berechtigungsprobe an einer einzigen Anwendung: %s" % probe.get("name"))
    ok, meldung = setze_idps(probe, [gh], "ok")
    if not ok:
        print("   PROBE FEHLGESCHLAGEN — nichts geaendert (0 von %d)." % len(offen))
        print("   %s" % meldung)
        print("   Token: ~/.secrets/%s" % TOKEN_NAME)
        print("   Braucht die Berechtigung 'Access: Apps and Policies — Edit'")
        print("   auf Kontoebene. Anderes Token: --token cloudflare_api_token")
        return False
    print("   Probe ok — Berechtigung vorhanden, weiter mit dem Rest")

    erledigt = 1
    for a in offen:
        if a["id"] == probe["id"]:
            continue
        ok, meldung = setze_idps(a, [gh], "ok")
        if ok:
            erledigt += 1
            print("   OK      %s" % str(a.get("name"))[:50])
        else:
            print("   FEHLER  %-50s %s" % (str(a.get("name"))[:50], meldung))
    print("   festgenagelt: %d von %d" % (erledigt, len(offen)))
    return erledigt == len(offen)


# ---------------------------------------------------------------- Schritt 2


def schritt2(trocken):
    print("== Schritt 2: Einmal-PIN als Anmeldedienst anlegen")
    apps = lies("apps", "Anwendungen")
    idps = lies("identity_providers", "Anmeldedienste")
    offen = [a for a in apps if not a.get("allowed_idps")]
    if offen and not trocken:
        print("   ABBRUCH: %d Anwendungen sind noch nicht festgenagelt." % len(offen))
        print("   Der PIN wuerde dort voraussichtlich sofort gelten. Erst Schritt 1.")
        for a in offen[:6]:
            print("     offen: %s" % str(a.get("name"))[:50])
        return False
    if offen and trocken:
        print(
            "   HINWEIS: im Trockenlauf sind noch %d offen — scharf bricht das ab"
            % len(offen)
        )
    if pin_id(idps):
        print("   Einmal-PIN existiert bereits — nichts zu tun")
        return True
    if trocken:
        print("   WUERDE anlegen: Anmeldedienst 'Einmal-PIN' (Typ onetimepin)")
        return True

    print("   Sicherung: %s" % sichere("idps-vor-schritt2", idps))
    ok, d = api(
        "identity_providers",
        "POST",
        {"name": "Einmal-PIN", "type": "onetimepin", "config": {}},
    )
    if not ok:
        print("   FEHLER: %s" % d)
        return False
    print("   angelegt, Kennung %s…" % d["result"]["id"][:8])
    return True


# ---------------------------------------------------------------- Schritt 3


def schritt3(trocken):
    print("== Schritt 3: nur %s fuer PIN oeffnen, Adressen ergaenzen" % ZIEL_DOMAIN)
    apps = lies("apps", "Anwendungen")
    idps = lies("identity_providers", "Anmeldedienste")
    gh = github_id(idps)
    pin = pin_id(idps)
    if not pin and not trocken:
        print("   ABBRUCH: kein Einmal-PIN vorhanden — erst Schritt 2")
        return False
    app = ziel_app(apps)
    richtlinien = lies("apps/%s/policies" % app["id"], "Richtlinien")

    erlaubt = set()
    for p in richtlinien:
        for eintrag in p.get("include", []):
            if "email" in eintrag:
                erlaubt.add(eintrag["email"].get("email"))
    fehlend = [m for m in NEUE_MAILS if m not in erlaubt]

    print("   Anwendung  : %s" % app.get("name"))
    print("   Richtlinien: %d" % len(richtlinien))
    print(
        "   erlaubt    : %s" % (", ".join(sorted(erlaubt)) or "(keine Einzeladresse)")
    )
    print("   ergaenzen  : %s" % (", ".join(fehlend) or "nichts"))

    if trocken:
        print(
            "   WUERDE setzen: Anmeldedienste = GitHub + Einmal-PIN%s"
            % ("" if pin else "  (PIN existiert noch nicht)")
        )
        if fehlend and richtlinien:
            print(
                "   WUERDE ergaenzen in Richtlinie '%s': %s"
                % (richtlinien[0].get("name"), ", ".join(fehlend))
            )
        return True

    print(
        "   Sicherung: %s"
        % sichere("docs-app-und-richtlinien", {"app": app, "policies": richtlinien})
    )
    ok, meldung = setze_idps(app, [gh, pin], "ok")
    if not ok:
        print("   FEHLER beim Setzen der Anmeldedienste: %s" % meldung)
        return False
    print("   Anmeldedienste gesetzt: GitHub + Einmal-PIN")

    if not fehlend:
        return True
    if not richtlinien:
        print("   FEHLER: keine Richtlinie vorhanden, Adressen nicht ergaenzbar")
        return False
    p = richtlinien[0]
    neu = list(p.get("include", [])) + [{"email": {"email": m}} for m in fehlend]
    ok, d = api(
        "apps/%s/policies/%s" % (app["id"], p["id"]),
        "PUT",
        {
            "name": p.get("name"),
            "decision": p.get("decision"),
            "include": neu,
            "exclude": p.get("exclude", []),
            "require": p.get("require", []),
        },
    )
    if not ok:
        print("   FEHLER beim Ergaenzen der Adressen: %s" % d)
        print("   (Anmeldedienste sind gesetzt — Ruecknahme siehe Sicherung)")
        return False
    print("   Adressen ergaenzt: %s" % ", ".join(fehlend))
    return True


# ---------------------------------------------------------------- Ablauf


def main():
    trocken = "--trocken" in sys.argv
    if "--schritt" in sys.argv:
        schritte = [int(sys.argv[sys.argv.index("--schritt") + 1])]
    elif trocken:
        schritte = [1, 2, 3]
    else:
        print(__doc__)
        return 2

    print("Token: ~/.secrets/%s   Konto: %s…" % (TOKEN_NAME, KONTO[:8]))
    if trocken:
        print(">>> TROCKENLAUF — es wird nichts geaendert")
    print()

    for nummer in schritte:
        fertig = {1: schritt1, 2: schritt2, 3: schritt3}[nummer](trocken)
        print()
        if not fertig and not trocken:
            print(
                "Schritt %d nicht vollstaendig — Abbruch, kein Folgeschritt." % nummer
            )
            return 1

    print(">>> Trockenlauf Ende" if trocken else ">>> fertig")
    return 0


if __name__ == "__main__":
    sys.exit(main())
