#!/usr/bin/env python3
"""erreichbarkeit_melder.py — fragt die Prod-Ziele, statt ihre Deklaration zu vergleichen.

## Warum es das gibt

Der Loop prueft Erreichbarkeit heute nur mittelbar: `infra/ports.yaml` sagt, welcher
Dienst auf welchem Host unter welcher Domain laufen **soll**, die Tunnel-Route sagt,
wohin sie zeigt, und `0.7 deploy-scan` sagt, wie der letzte Lauf ausging. Alle drei
sind **Zusagen**. Stimmen sie miteinander ueberein, sieht die Lage konsistent aus —
auch dann, wenn hinter der Route seit Tagen nichts mehr antwortet.

Realfall wedding-hub: sechs bis sieben Tage tot, waehrend Registry und Tunnel-Route
uebereinstimmten. Wer nur Deklarationen vergleicht, sieht einen gesunden Zustand.
Eine einzige Anfrage an das Ziel haette es am ersten Tag gemeldet.

Der Kalibrierlauf am 2026-08-23 ueber alle 26 deklarierten Prod-Domains fand vier
Abweichungen in **zwei** Klassen, und das ist der eigentliche Punkt:

- **502** (`bahn-hub`, `recruiting-hub`) — Route steht, Backend tot.
- **NXDOMAIN** (`coach-hub`, `frist-hub`) — die deklarierte Domain loest gar nicht auf.

Die zweite Klasse haette ein reiner Health-Check nie gefunden: dort ist nicht der
Dienst kaputt, sondern die **Deklaration** falsch.

## Warum es ein Lebenszyklus-Feld braucht

Zwei der vier Abweichungen sind gewollt: `frist-hub` ist auf einen Hosting-ADR
blockiert, `recruiting-hub` bewusst stillgelegt. Ohne eine Moeglichkeit, das zu
sagen, meldete dieses Werkzeug ab Tag 1 zwei Dauer-Fehlalarme — also genau die
Krankheit, gegen die es gebaut wird (ein Melder, den man zu ueberblaettern lernt).

Deshalb kennt `infra/ports.yaml` jetzt `betriebsstatus` mit drei Werten:

    betriebsstatus: aktiv         # Vorgabe, muss nicht geschrieben werden
    betriebsstatus: stillgelegt   # absichtlich aus
    betriebsstatus: blockiert     # soll laufen, wartet auf eine Entscheidung

Alles ausser `aktiv` braucht ein `betriebsstatus_grund`. Fehlt der Grund, ist **das**
der Befund — eine Ausnahme ohne Begruendung ist eine stumme Ausnahme, und die ist
genauso wenig wert wie gar keine Pruefung.

## Was KEIN Befund ist

- **401/403** — hinter Cloudflare Access antwortet der Perimeter, nicht die App.
  Dass ueberhaupt jemand antwortet, ist der Beweis, um den es hier geht.
- **3xx** — eine Weiterleitung ist eine Antwort.
- Alles mit `betriebsstatus != aktiv` und hinterlegtem Grund.

## Aufruf

    python3 tools/erreichbarkeit_melder.py            # voller Report
    python3 tools/erreichbarkeit_melder.py --kurz     # eine Zeile fuer den Session-Start
    python3 tools/erreichbarkeit_melder.py --json     # maschinenlesbar
    python3 tools/erreichbarkeit_melder.py --offline  # nur Deklarations-Pruefung, ohne Netz

Exit-Code 0 immer — Report-Werkzeug, kein Enforcer (Hausform wie `gate_deckung.py`).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

import yaml

# Maschinenlesbarer Kopf (KONZ-038 D8)
GATE_HEADER = {
    "slug": "erreichbarkeit-nur-aus-deklaration-erschlossen",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-23",
    "evidence": "tools/tests/test_erreichbarkeit_melder.py",
}
from pathlib import Path  # noqa: E402

# Vokabular kommt aus tools/betriebsstatus.py — drei Kopien einer Liste
# sind drei Gelegenheiten, dass sie auseinanderlaufen (#2586 K5).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from betriebsstatus import STATUS_ERLAUBT  # noqa: E402

TIMEOUT_S = 12
PARALLEL = 10
UA = "iil-erreichbarkeit-melder/1.0 (+platform/tools)"

# Klassen. `befund` sagt, ob die Klasse eine Meldung wert ist.
KLASSEN = {
    "erreichbar": (False, "antwortet"),
    "auth": (False, "Perimeter antwortet (401/403)"),
    "route-ohne-backend": (True, "Route steht, Backend antwortet nicht (5xx)"),
    "ziel-loest-nicht-auf": (True, "deklarierte Domain hat keinen DNS-Eintrag"),
    "keine-antwort": (True, "keine Antwort (Timeout/abgelehnt/TLS)"),
    "unklar": (True, "unerwarteter Statuscode"),
    "nicht-geprueft": (False, "offline-Lauf"),
}


def _ports_yaml_pfad() -> str:
    hier = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(hier, "infra", "ports.yaml")


def lade_dienste(pfad: str) -> list[dict]:
    """Dienste mit deklarierter Prod-Domain, inklusive Lebenszyklus-Angabe."""
    daten = yaml.safe_load(open(pfad, encoding="utf-8")) or {}
    raus = []
    for name, v in (daten.get("services") or {}).items():
        if not isinstance(v, dict) or not v.get("domain_prod"):
            continue
        raus.append(
            {
                "name": name,
                "domain": str(v["domain_prod"]),
                "host": str(v.get("prod_host", "prod")),
                "betriebsstatus": str(v.get("betriebsstatus", "aktiv")),
                "grund": v.get("betriebsstatus_grund"),
            }
        )
    return sorted(raus, key=lambda d: d["name"])


def _dns_fehler(exc: BaseException) -> bool:
    """Trennt 'Name loest nicht auf' von 'Ziel antwortet nicht'.

    Die Unterscheidung traegt den halben Wert dieses Werkzeugs, deshalb steht sie
    hier und nicht inline: NXDOMAIN heisst, die Deklaration ist falsch; ein
    Verbindungsfehler heisst, der Dienst ist weg. Das sind verschiedene Aufgaben
    fuer verschiedene Leute.
    """
    text = f"{exc}"
    return "Name or service not known" in text or "nodename nor servname" in text


def probiere(dienst: dict, oeffner=None) -> str:
    """Fragt genau einmal an und gibt die Klasse zurueck."""
    oeffner = oeffner or _oeffne
    url = f"https://{dienst['domain']}/"
    try:
        code = oeffner(url)
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:  # noqa: BLE001 — jede Netzstoerung ist hier ein Ergebnis
        return "ziel-loest-nicht-auf" if _dns_fehler(e) else "keine-antwort"
    if code in (401, 403):
        return "auth"
    if 200 <= code < 400:
        return "erreichbar"
    if 500 <= code < 600:
        return "route-ohne-backend"
    return "unklar"


def _oeffne(url: str) -> int:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
    with urllib.request.urlopen(
        req, timeout=TIMEOUT_S, context=ssl.create_default_context()
    ) as r:
        return r.status


def bewerte(dienste: list[dict], klassen: dict[str, str]) -> dict:
    """Klasse + Lebenszyklus ergeben das Urteil. Reine Funktion, ohne Netz."""
    befunde, geparkt, stumme_ausnahme, ok = [], [], [], []
    for d in dienste:
        klasse = klassen.get(d["name"], "nicht-geprueft")
        zeile = dict(d, klasse=klasse)
        if d["betriebsstatus"] not in STATUS_ERLAUBT:
            zeile["warum"] = f"unbekannter betriebsstatus {d['betriebsstatus']!r}"
            stumme_ausnahme.append(zeile)
            continue
        if d["betriebsstatus"] != "aktiv":
            if not d["grund"]:
                zeile["warum"] = "betriebsstatus ohne betriebsstatus_grund"
                stumme_ausnahme.append(zeile)
            else:
                geparkt.append(zeile)
            continue
        if KLASSEN.get(klasse, (True, ""))[0]:
            befunde.append(zeile)
        else:
            ok.append(zeile)
    return {
        "geprueft": len(dienste),
        "befunde": befunde,
        "geparkt": geparkt,
        "stumme_ausnahme": stumme_ausnahme,
        "ok": ok,
    }


def messe(dienste: list[dict], offline: bool = False, oeffner=None) -> dict[str, str]:
    if offline:
        return {d["name"]: "nicht-geprueft" for d in dienste}
    aktive = [d for d in dienste if d["betriebsstatus"] == "aktiv"]
    with cf.ThreadPoolExecutor(max_workers=PARALLEL) as ex:
        ergebnisse = list(ex.map(lambda d: probiere(d, oeffner), aktive))
    return {d["name"]: k for d, k in zip(aktive, ergebnisse)}


def _kurzzeile(e: dict) -> str:
    # Ein Offline-Lauf hat NICHTS gemessen. Ihn wie "alles gruen" zu melden waere
    # dieselbe Falle, die dieses Werkzeug schliessen soll: eine Null aus dem eigenen
    # Filter als Abwesenheit von Befunden lesen.
    ungeprueft = [z for z in e["ok"] if z["klasse"] == "nicht-geprueft"]
    if ungeprueft and not e["befunde"]:
        return f"{len(ungeprueft)} Prod-Ziel(e) NICHT geprueft (offline) — keine Aussage zur Erreichbarkeit"
    if e["stumme_ausnahme"]:
        n = len(e["stumme_ausnahme"])
        return f"{n} Ausnahme(n) ohne Grund — betriebsstatus gesetzt, betriebsstatus_grund fehlt"
    if not e["befunde"]:
        return f"{e['geprueft']} Prod-Ziele geprueft, alle antworten ({len(e['geparkt'])} bewusst geparkt)"
    teile = [f"{b['name']} ({b['klasse']})" for b in e["befunde"]]
    return (
        f"{len(e['befunde'])} von {e['geprueft']} Prod-Zielen antworten nicht — "
        + ", ".join(teile)
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--kurz", action="store_true", help="eine Zeile fuer den Session-Start"
    )
    p.add_argument("--json", action="store_true", dest="als_json")
    p.add_argument(
        "--offline", action="store_true", help="ohne Netz, nur Deklarations-Pruefung"
    )
    p.add_argument(
        "--ports", default=None, help="Pfad zu ports.yaml (Vorgabe: infra/ports.yaml)"
    )
    a = p.parse_args()

    dienste = lade_dienste(a.ports or _ports_yaml_pfad())
    ergebnis = bewerte(dienste, messe(dienste, offline=a.offline))

    if a.als_json:
        json.dump(ergebnis, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    if a.kurz:
        print(_kurzzeile(ergebnis))
        return 0

    print(
        f"# Erreichbarkeit der deklarierten Prod-Ziele ({ergebnis['geprueft']} Dienste)\n"
    )
    for titel, schluessel, hinweis in (
        ("🚨 Befunde", "befunde", "antwortet nicht, obwohl als aktiv deklariert"),
        (
            "⚠️  Ausnahme ohne Grund",
            "stumme_ausnahme",
            "betriebsstatus gesetzt, Begruendung fehlt",
        ),
        ("⏸  Bewusst geparkt", "geparkt", "kein Befund — Grund hinterlegt"),
        ("✅ Antwortet", "ok", ""),
    ):
        zeilen = ergebnis[schluessel]
        if not zeilen:
            continue
        print(f"{titel} ({len(zeilen)}){' — ' + hinweis if hinweis else ''}")
        for z in zeilen:
            anhang = (
                z.get("warum")
                or z.get("grund")
                or KLASSEN.get(z["klasse"], ("", ""))[1]
            )
            print(f"  {z['name']:<20} {z['domain']:<34} host={z['host']:<7} {anhang}")
        print()

    if ergebnis["befunde"]:
        print(
            "→ Jeder Befund ist eine Anfrage an das echte Ziel, keine Ableitung aus einer\n"
            "  Zusage. Zulaessige Abschluesse: Dienst reparieren, Deklaration korrigieren,\n"
            "  ODER betriebsstatus + betriebsstatus_grund setzen. Liegenlassen zaehlt nicht."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
