#!/usr/bin/env python3
"""gpu_leerlauf.py — haelt ein Dienst Grafikspeicher, ohne gerufen zu werden?

Anlass (platform#3352, Owner-Frage 2026-09-21 „ich sehe keine notwendigkeit ->
nicht freigegeben nach verwendung?"): Auf der gx10 hielt vLLM **37,5 GB** und
hatte seit dem Hochfahren sechs Tage zuvor **keine einzige Anfrage** gesehen —
84 Journal-Zeilen insgesamt, die letzte „Application startup complete". Im Repo
gab es keinen lebenden Aufrufer; die einzige nicht-archivierte Fundstelle war
das Skript, das den Dienst *anhaelt*. Aufgefallen ist das nicht beim Betrieb,
sondern weil der Owner nachfragte, als ein weiterer Dienst dazukam.

Ein Serving-Endpunkt haelt absichtlich Speicher, damit die erste Anfrage schnell
ist. Das ist Bereitschaft. Sechs Tage ohne eine Anfrage sind keine Bereitschaft
mehr, sondern eine vergessene Sitzung. Dieser Melder trennt die beiden Faelle.

**Was er NICHT tut:** abschalten. Ein Dienst kann aus gutem Grund warten (neu
aufgesetzt, saisonal, Ausweichpfad). Der Melder nennt die Zahlen und ueberlaesst
das Urteil dem Menschen — genau wie `befund_journal` es fuer andere Melder haelt.

Aufruf:
  python3 tools/gpu_leerlauf.py            # Bericht
  python3 tools/gpu_leerlauf.py --kurz     # eine Zeile fuer den Sitzungsstart
  python3 tools/gpu_leerlauf.py --json
  ... --mindest-gb 4 --mindest-tage 3      # Schwellen verschieben

Exit 0 = nichts zu melden · 1 = mindestens ein Leerlauf-Dienst · 2 = kein Knoten
messbar (Werkzeugfehler, **keine** Entwarnung).
stdlib-only ausser `ssh` und der Hosts-Registry.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "infra" / "hosts.yaml"
FERN = Path(__file__).with_name("gpu_leerlauf_remote.sh")

#: Unterhalb dieser Belegung lohnt die Meldung nicht — ein Dienst mit 300 MB
#: kostet niemanden etwas, und ein Melder, der Kleinkram meldet, wird ueberlesen.
MINDEST_GB = 4.0

#: Erst ab dieser Stille gilt Bereitschaft als Leerlauf. Drei Tage lassen ein
#: Wochenende durchgehen, ohne dass der Melder Montag frueh Unsinn erzaehlt.
MINDEST_TAGE = 3

#: Knoten mit Grafikkarte, und wie ein Befehl dort ankommt. Bewusst eine
#: Aufzaehlung und kein Rateschema: `server_type` sagt nichts Verlaessliches
#: ueber eine GPU, und ein falsch geratener Knoten laesst den Melder in einen
#: Verbindungsfehler laufen statt zu messen.
#:
#: Der Wert ist die Huelle um den eigentlichen Befehl. Die gpu-box antwortet mit
#: Windows-OpenSSH; dort scheitert ein `cat > ~/datei` mit „Das System kann den
#: angegebenen Pfad nicht finden" — Linux liegt eine Ebene tiefer in der WSL.
GPU_KNOTEN: dict[str, str] = {
    "gx10": "{befehl}",
    "gpu-box": 'wsl -d Ubuntu -u root -e bash -c "{befehl}"',
}


def ssh_ziel(knoten: str) -> tuple[str, str] | None:
    """(Sprung, Ziel) aus hosts.yaml. None, wenn der Knoten dort fehlt.

    Gelesen wird mit einem Zeilenscanner statt mit einem YAML-Parser: die Datei
    traegt mehrere Bloecke gleichen Namens in verschiedenen Sektionen, und ein
    Parser wuerde still den falschen nehmen.
    """
    if not REGISTRY.is_file():
        return None
    zeilen = REGISTRY.read_text(encoding="utf-8").splitlines()
    for i, z in enumerate(zeilen):
        if re.match(rf"^\s{{2}}{re.escape(knoten)}:\s*$", z):
            ssh = via = ""
            for folge in zeilen[i + 1 : i + 20]:
                if re.match(r"^\s{2}\S", folge):  # naechster Knoten
                    break
                if m := re.match(r"\s+ssh:\s*(\S+)", folge):
                    ssh = m.group(1)
                elif m := re.match(r"\s+ssh_via:\s*(\S+)", folge):
                    via = m.group(1)
            if ssh:
                return (via or "hetzner-prod", ssh)
    return None


def messe_knoten(knoten: str) -> tuple[list[dict], str | None]:
    """(Prozesse, Fehler). Fehler != None heisst: NICHT gemessen, nicht sauber."""
    ziel = ssh_ziel(knoten)
    if ziel is None:
        return [], f"{knoten}: kein ssh-Eintrag in hosts.yaml"
    if not FERN.is_file():
        return [], f"{knoten}: {FERN.name} fehlt"
    _via, ssh = ziel
    huelle = GPU_KNOTEN.get(knoten, "{befehl}")
    skript = FERN.read_text(encoding="utf-8")
    basis = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "hetzner-prod"]
    try:
        ab = subprocess.run(
            [
                *basis,
                f"ssh -o BatchMode=yes {ssh} "
                f"'{huelle.format(befehl='cat > /tmp/gpu_leerlauf_remote.sh')}'",
            ],
            input=skript,
            capture_output=True,
            text=True,
            timeout=90,
        )
        if ab.returncode != 0:
            return [], f"{knoten}: Skript nicht uebertragbar ({ab.stderr.strip()[:60]})"
        lauf = subprocess.run(
            [
                *basis,
                f"ssh -o BatchMode=yes {ssh} "
                f"'{huelle.format(befehl='bash /tmp/gpu_leerlauf_remote.sh')}'",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return [], f"{knoten}: nicht erreichbar ({type(e).__name__})"
    if lauf.returncode != 0:
        return [], f"{knoten}: Fernlauf fehlgeschlagen ({lauf.stderr.strip()[:60]})"

    procs: list[dict] = []
    for zeile in lauf.stdout.splitlines():
        zeile = zeile.strip()
        if not zeile.startswith("{"):
            continue
        try:
            d = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        d["knoten"] = knoten
        procs.append(d)
    return procs, None


def stille_tage(letzte: str, heute: date) -> int | None:
    """Tage seit der letzten Anfrage. None, wenn nie eine gesehen wurde."""
    if not letzte:
        return None
    try:
        d = datetime.fromisoformat(letzte.replace("Z", "+00:00")).date()
    except ValueError:
        return None
    return (heute - d).days


def beurteile(
    procs: list[dict], mindest_gb: float, mindest_tage: int, heute: date
) -> list[dict]:
    """Welche Dienste halten viel und werden nicht gerufen?"""
    befunde = []
    for p in procs:
        gb = float(p.get("mib", 0)) / 1024.0
        if gb < mindest_gb:
            continue
        tage = stille_tage(str(p.get("letzte_anfrage", "")), heute)
        # `None` heisst: keine einzige Anfrage im Journal. Das ist der
        # schwerere Fall, nicht der unklare — ein Dienst, der nie gerufen
        # wurde, haelt seinen Speicher ohne jeden Beleg eines Zwecks.
        if tage is None or tage >= mindest_tage:
            befunde.append({**p, "gb": round(gb, 1), "stille_tage": tage})
    return befunde


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mindest-gb", type=float, default=MINDEST_GB)
    p.add_argument("--mindest-tage", type=int, default=MINDEST_TAGE)
    p.add_argument("--kurz", action="store_true")
    p.add_argument("--json", action="store_true", dest="als_json")
    a = p.parse_args(argv)

    alle: list[dict] = []
    fehler: list[str] = []
    for knoten in GPU_KNOTEN:
        procs, f = messe_knoten(knoten)
        alle.extend(procs)
        if f:
            fehler.append(f)

    heute = date.today()
    befunde = beurteile(alle, a.mindest_gb, a.mindest_tage, heute)
    gemessen = len(GPU_KNOTEN) - len(fehler)

    if a.als_json:
        print(json.dumps({"befunde": befunde, "fehler": fehler, "gemessen": gemessen}))
    elif a.kurz:
        if gemessen == 0:
            print(f"gpu-leerlauf: NICHT messbar — {'; '.join(fehler)}")
        elif befunde:
            teile = [
                f"{b['unit'].removesuffix('.service')}@{b['knoten']} {b['gb']} GB "
                f"({'nie gerufen' if b['stille_tage'] is None else str(b['stille_tage']) + ' d still'})"
                for b in befunde
            ]
            print(
                f"gpu-leerlauf: {len(befunde)} Dienst(e) im Leerlauf — "
                + " · ".join(teile)
            )
        else:
            print(
                f"gpu-leerlauf: kein Leerlauf ({gemessen}/{len(GPU_KNOTEN)} Knoten gemessen)"
            )
    else:
        print("GPU-Leerlauf (platform#3352)")
        print(f"  Schwellen: ab {a.mindest_gb} GB und ab {a.mindest_tage} Tagen Stille")
        print(f"  Knoten gemessen: {gemessen} von {len(GPU_KNOTEN)}")
        for f in fehler:
            print(f"  ◌ NICHT gemessen — {f}")
        if not befunde:
            print("  kein Dienst im Leerlauf")
        for b in befunde:
            still = (
                "nie gerufen"
                if b["stille_tage"] is None
                else f"{b['stille_tage']} Tage still"
            )
            print(f"  ⚠ {b['unit']} auf {b['knoten']}: {b['gb']} GB, {still}")
            print(f"      {b['cmd'][:80]}")
        if fehler:
            print(
                "  Hinweis: ein nicht gemessener Knoten ist eine Luecke, keine Entwarnung."
            )

    if gemessen == 0:
        return 2
    return 1 if befunde else 0


if __name__ == "__main__":
    raise SystemExit(main())
