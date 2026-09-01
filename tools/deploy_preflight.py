#!/usr/bin/env python3
"""deploy_preflight.py — haelt einen Deploy an, bevor er auf den falschen Knoten geht.

Der Anlass steht in KONZ-platform-054: coach-hub war seit dem 2026-08-23 als
``betriebsstatus: stillgelegt`` deklariert und mit ``prod_host: prod-b`` gefuehrt —
und wurde am 2026-08-29 trotzdem auf ``prod`` deployt, wo der Stack 25 Stunden in
einer Fehlerschleife lief, ohne dass ein Melder darauf zeigte. Kein Deploy-Pfad
liest diese beiden Felder heute. Genau das tut dieses Werkzeug, vor dem Deploy.

Es meldet vier Zustaende, weil "geprueft und in Ordnung" und "gar nicht
pruefbar" nicht dasselbe sind (siehe ``EXIT_*``):

    0  konform      — Dienst ist aktiv und das Ziel ist der deklarierte Knoten
    1  Verstoss     — stillgelegt/blockiert, oder Ziel != deklarierter Knoten
    2  Datenfehler  — ports.yaml/hosts.yaml nicht lesbar oder nicht parsebar
    3  Scope-Luecke — Dienst nicht deklariert, Knoten ohne IP, Ziel unbekannt

Exit 3 ist bewusst KEIN Erfolg. Ein Melder, der ungemessenes Gebiet als gruen
verbucht, belohnt kleine Nenner — die Aufrufer-Seite entscheidet, ob sie eine
Scope-Luecke blockieren oder sichtbar durchlassen will, aber sie erfaehrt davon.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml

EXIT_OK = 0
EXIT_VERSTOSS = 1
EXIT_DATENFEHLER = 2
EXIT_SCOPE = 3

#: Nur dieser Wert laesst einen Deploy durch. Alles andere — ``stillgelegt``,
#: ``blockiert`` und jeder kuenftige Wert — haelt ihn an. Das ist Absicht: ein
#: neuer Lebenszyklus-Zustand darf nicht versehentlich deploybar sein.
STATUS_DEPLOYBAR = "aktiv"

#: Felder, unter denen ein Knoten in hosts.yaml wiedererkennbar ist. Der Aufrufer
#: kennt sein Ziel als IP, als DNS-Name oder als ssh-Alias — alle drei muessen
#: auf denselben Knoten fuehren, sonst meldet das Werkzeug einen Verstoss, wo
#: nur eine andere Schreibweise vorliegt.
KNOTEN_KENNUNGEN = ("ip", "hostname", "cloud_name", "ssh_alias")


def _lade(quelle: str) -> Any:
    """Liest YAML aus Datei oder URL. Fehler werden nicht geschluckt."""
    if quelle.startswith(("http://", "https://")):
        with urllib.request.urlopen(quelle, timeout=20) as antwort:  # noqa: S310
            roh = antwort.read().decode("utf-8")
    else:
        roh = Path(quelle).read_text(encoding="utf-8")
    return yaml.safe_load(roh)


def knoten_kennungen(eintrag: dict) -> set[str]:
    """Alle Namen und Adressen, unter denen ein Knoten gemeint sein kann."""
    kennungen: set[str] = set()
    for feld in KNOTEN_KENNUNGEN:
        wert = eintrag.get(feld)
        if wert:
            kennungen.add(str(wert).strip().lower())
    ssh = eintrag.get("ssh")
    if ssh:
        # "root@88.198.191.108" meint denselben Knoten wie "88.198.191.108"
        kennungen.add(str(ssh).split("@")[-1].strip().lower())
    return kennungen


def pruefe(
    app: str,
    environment: str,
    deploy_host: str | None,
    ports: dict,
    hosts: dict,
) -> tuple[int, list[str]]:
    """Kern der Pruefung. Gibt (Exit-Code, Meldungen) zurueck."""
    meldungen: list[str] = []
    dienste = (ports or {}).get("services") or {}
    knoten = (hosts or {}).get("hosts") or {}

    dienst = dienste.get(app)
    if dienst is None:
        return EXIT_SCOPE, [
            f"Scope-Luecke: '{app}' steht nicht in ports.yaml — der Deploy ist "
            f"ungeprueft, nicht in Ordnung. Deklariert sind {len(dienste)} Dienste."
        ]

    status = str(dienst.get("betriebsstatus", STATUS_DEPLOYBAR)).strip().lower()
    if status != STATUS_DEPLOYBAR:
        grund = str(dienst.get("betriebsstatus_grund", "")).strip()
        meldungen.append(
            f"Verstoss: '{app}' ist als '{status}' deklariert und darf nicht "
            f"deployt werden." + (f" Grund laut ports.yaml: {grund}" if grund else "")
        )
        return EXIT_VERSTOSS, meldungen

    if environment != "production":
        meldungen.append(
            f"OK: '{app}' ist aktiv. Knotenpruefung entfaellt fuer environment="
            f"'{environment}' — prod_host beschreibt nur den Produktionsknoten."
        )
        return EXIT_OK, meldungen

    if not deploy_host:
        return EXIT_SCOPE, [
            f"Scope-Luecke: '{app}' ist aktiv, aber ohne Zielangabe laesst sich "
            f"der Knoten nicht pruefen (--deploy-host fehlt oder ist leer)."
        ]

    soll_name = str(dienst.get("prod_host", "prod")).strip()
    soll = knoten.get(soll_name)
    if soll is None:
        return EXIT_SCOPE, [
            f"Scope-Luecke: '{app}' nennt prod_host '{soll_name}', den hosts.yaml "
            f"nicht kennt. Bekannt sind: {', '.join(sorted(knoten))}."
        ]

    soll_kennungen = knoten_kennungen(soll)
    if not soll_kennungen:
        return EXIT_SCOPE, [
            f"Scope-Luecke: Knoten '{soll_name}' hat in hosts.yaml weder ip noch "
            f"hostname, ssh oder ssh_alias — das Ziel ist nicht vergleichbar."
        ]

    # Das Ziel kommt je nach Aufrufer als "89.167.43.30", "root@89.167.43.30"
    # oder als ssh-Alias — dieselbe Normalisierung wie fuer die Knotenseite.
    ziel = deploy_host.strip().lower().split("@")[-1]
    if ziel in soll_kennungen:
        meldungen.append(
            f"OK: '{app}' ist aktiv und geht auf '{soll_name}' ({deploy_host})."
        )
        return EXIT_OK, meldungen

    for name, eintrag in knoten.items():
        if name == soll_name or not isinstance(eintrag, dict):
            continue
        if ziel in knoten_kennungen(eintrag):
            meldungen.append(
                f"Verstoss: '{app}' ist fuer Knoten '{soll_name}' deklariert, das "
                f"Deploy-Ziel '{deploy_host}' ist aber '{name}'."
            )
            return EXIT_VERSTOSS, meldungen

    return EXIT_SCOPE, [
        f"Scope-Luecke: Deploy-Ziel '{deploy_host}' laesst sich keinem Knoten aus "
        f"hosts.yaml zuordnen — weder '{soll_name}' noch einem anderen."
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--app", required=True, help="App-Name wie in ports.yaml (z.B. coach-hub)"
    )
    p.add_argument("--environment", default="production", help="staging|production")
    p.add_argument(
        "--deploy-host",
        default="",
        help="Ziel des Deploys: IP, Hostname oder ssh-Alias",
    )
    p.add_argument(
        "--ports", default="infra/ports.yaml", help="Pfad oder URL zu ports.yaml"
    )
    p.add_argument(
        "--hosts", default="infra/hosts.yaml", help="Pfad oder URL zu hosts.yaml"
    )
    p.add_argument(
        "--json", action="store_true", help="Ergebnis maschinenlesbar ausgeben"
    )
    a = p.parse_args(argv)

    try:
        ports = _lade(a.ports)
        hosts = _lade(a.hosts)
    except Exception as fehler:  # noqa: BLE001 — jede Ursache blockiert gleich
        text = f"Datenfehler: ports.yaml/hosts.yaml nicht lesbar ({fehler})."
        print(
            json.dumps({"code": EXIT_DATENFEHLER, "meldungen": [text]})
            if a.json
            else text
        )
        return EXIT_DATENFEHLER

    code, meldungen = pruefe(a.app, a.environment, a.deploy_host, ports, hosts)
    if a.json:
        print(
            json.dumps(
                {"code": code, "app": a.app, "meldungen": meldungen}, ensure_ascii=False
            )
        )
    else:
        for zeile in meldungen:
            print(zeile)
    return code


if __name__ == "__main__":
    sys.exit(main())
