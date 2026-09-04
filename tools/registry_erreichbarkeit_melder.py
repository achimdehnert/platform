#!/usr/bin/env python3
"""registry_erreichbarkeit_melder.py — liest, was der Rekorder auf den Hosts misst.

## Warum es das gibt

Am 2026-09-02 scheiterten vier Prod-Deploys daran, dass `prod` ghcr.io nur in 4 von 10
Versuchen erreichte — bei 10 von 10 gegen github.com und verlustfreiem ICMP zum selben
Rechner. Zwei Stunden spaeter war der Zustand von selbst vorbei. Die Ursache ist damit
nachtraeglich nicht bestimmbar (platform#2685).

`infra/host-maintenance/registry-probe.sh` misst diese Strecke seither dauerhaft. Dieses
Werkzeug ist sein **Leser**: ein Melder, den niemand liest, ist keiner — dieselbe
Fehlerklasse, die in dieser Flotte bereits als `melder-ohne-leser` gefuehrt wird.

## Was gemeldet wird

1. **Ein Ausfallfenster** (`befund=registry`): die Registry war schlecht erreichbar,
   WAEHREND der Kontrollarm sauber war. Das ist der Fund.
2. **Ein stummer Rekorder**: liegt die juengste Messung zu lange zurueck, ist der Timer
   tot — und ein toter Rekorder meldet nie ein Fenster. Er waere sonst genau der blinde
   Melder, gegen den er gebaut wurde, deshalb ist sein Schweigen selbst ein Befund.
3. **Nicht messbar**: kein Protokoll, kein ssh. Ausdruecklich KEIN Gruen.

## Wozu die Zahl gebraucht wird

ADR-301 (Registry-Spiegel) traegt ein Kill-Gate: zurueckziehen, wenn bis zum 2026-12-02
kein zweites Fenster auftritt. Ohne diese Messung ist diese Bedingung nicht pruefbar —
das Kill-Gate waere eine Absichtserklaerung. Der Bericht hier ist sein Messgeraet.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG_PFAD = "/var/log/registry-probe/probe.log"
# Hosts, die den Deploy-Entrypoint ausfuehren — dort und nur dort laeuft der Rekorder.
# Die Liste kommt aus hosts.yaml, nicht aus fest getippten Namen: genau eine solche
# Namensliste hat den Drift-Melder drei von vier Hosts uebersehen lassen (platform#2711).
HOSTS_YAML = Path(__file__).resolve().parent.parent / "infra" / "hosts.yaml"
ROLLEN_HOSTS = ("prod", "prod-b")
STUMM_AB_MINUTEN = 30  # Timer laeuft alle 5 min; 30 min sind sechs verpasste Laeufe.
FENSTER_TAGE = 30

ZEILE = re.compile(
    r"^(?P<zeit>\S+) host=(?P<host>\S+) ziel=(?P<zok>\d+)/(?P<zn>\d+) "
    r"kontrolle=(?P<kok>\d+)/(?P<kn>\d+) ip=(?P<ip>\S+) befund=(?P<befund>\w+)"
)


@dataclass
class Hostbild:
    name: str
    zeilen: int = 0
    juengste: datetime | None = None
    fenster: list[str] = field(default_factory=list)
    fehler: str | None = None


def _ssh_ziele() -> dict[str, str]:
    import yaml

    d = yaml.safe_load(HOSTS_YAML.read_text())
    hosts = d.get("hosts") or {}
    return {n: hosts[n]["ssh"] for n in ROLLEN_HOSTS if hosts.get(n, {}).get("ssh")}


def _lies(name: str, ssh: str, tage: int) -> Hostbild:
    bild = Hostbild(name=name)
    seit = datetime.now(timezone.utc) - timedelta(days=tage)
    try:
        roh = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", ssh,
             f"tail -20000 {LOG_PFAD} 2>/dev/null"],
            capture_output=True, text=True, timeout=60,
        ).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        bild.fehler = f"ssh gescheitert: {type(exc).__name__}"
        return bild

    if not roh.strip():
        bild.fehler = "kein Protokoll (Rekorder nicht installiert?)"
        return bild

    for zeile in roh.splitlines():
        m = ZEILE.match(zeile)
        if not m:
            continue
        try:
            zeit = datetime.strptime(m["zeit"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        bild.zeilen += 1
        if bild.juengste is None or zeit > bild.juengste:
            bild.juengste = zeit
        if zeit >= seit and m["befund"] == "registry":
            bild.fenster.append(
                f"{m['zeit']} ziel={m['zok']}/{m['zn']} kontrolle={m['kok']}/{m['kn']}"
            )
    return bild


def _bewerte(bilder: list[Hostbild]) -> tuple[str, str]:
    nicht_messbar = [b.name for b in bilder if b.fehler]
    stumm, mit_fenster = [], []
    jetzt = datetime.now(timezone.utc)
    for b in bilder:
        if b.fehler:
            continue
        if b.juengste is None or (jetzt - b.juengste) > timedelta(minutes=STUMM_AB_MINUTEN):
            alter = "nie" if b.juengste is None else f"{int((jetzt - b.juengste).total_seconds() // 60)} min"
            stumm.append(f"{b.name} (juengste Messung: {alter})")
        if b.fenster:
            mit_fenster.append(f"{b.name} ({len(b.fenster)} Messpunkt(e))")

    if mit_fenster:
        return "WARN", (
            f"Ausfallfenster gegen die Registry: {', '.join(mit_fenster)} "
            f"— Registry schlecht erreichbar bei sauberem Kontrollarm (platform#2685)"
        )
    if stumm:
        return "WARN", f"Rekorder stumm: {', '.join(stumm)} — ein toter Rekorder meldet nie ein Fenster"
    if nicht_messbar and len(nicht_messbar) == len(bilder):
        return "SKIP", f"nicht messbar: {', '.join(nicht_messbar)} — kein Beleg, aber auch keine Entwarnung"
    rest = f" · nicht messbar: {', '.join(nicht_messbar)}" if nicht_messbar else ""
    gemessen = sum(b.zeilen for b in bilder)
    return "PASS", f"kein Ausfallfenster in {FENSTER_TAGE} Tagen ({gemessen} Messpunkte){rest}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--tage", type=int, default=FENSTER_TAGE, help=f"Rueckschau (Vorgabe {FENSTER_TAGE})")
    p.add_argument("--quiet", action="store_true", help="nur die Ergebniszeile")
    args = p.parse_args()

    try:
        ziele = _ssh_ziele()
    except Exception as exc:  # noqa: BLE001 — hosts.yaml kaputt ist selbst der Befund
        print(f"RESULT: SKIP — hosts.yaml nicht lesbar: {exc}")
        return 0

    bilder = [_lies(n, ssh, args.tage) for n, ssh in ziele.items()]

    if not args.quiet:
        print(f"Rekorder-Protokoll {LOG_PFAD}, Rueckschau {args.tage} Tage\n")
        for b in bilder:
            if b.fehler:
                print(f"  {b.name:8} –  {b.fehler}")
                continue
            juengste = b.juengste.strftime("%Y-%m-%dT%H:%M:%SZ") if b.juengste else "–"
            print(f"  {b.name:8} {b.zeilen:6} Messpunkte, juengste {juengste}")
            for f in b.fenster[:10]:
                print(f"             ⚠ {f}")
            if len(b.fenster) > 10:
                print(f"             … {len(b.fenster) - 10} weitere")
        print()

    status, text = _bewerte(bilder)
    print(f"RESULT: {status} — {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
