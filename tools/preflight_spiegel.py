#!/usr/bin/env python3
"""Minimalauszug der Preflight-Eingaben fuer den Spiegel in iilgmbh/shared-ci (platform#3596).

Die Deploy-Bausteine in shared-ci laden vor jedem Deploy ``deploy_preflight.py``,
``ports.yaml`` und ``hosts.yaml``. Solange platform oeffentlich ist, kommen sie per
Raw-Abruf von hier; nach dem Flip auf privat (KONZ-platform-039, #3234) geht das nicht
mehr. Der Spiegel legt sie deshalb im Kanon ab. Er spiegelt nicht die vollen Dateien,
sondern nur die Felder, die ``pruefe`` liest: Notizen, Haertungs-Historie, Ports,
Domains und SSH-Benutzer bleiben in platform.

Aufruf::

    python3 tools/preflight_spiegel.py --ziel <verzeichnis>

Ergebnis: ``<ziel>/deploy_preflight.py``, ``<ziel>/ports.yaml``, ``<ziel>/hosts.yaml``.
Die Aequivalenz zum vollen Stand sichert ``tools/tests/test_preflight_spiegel.py``.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deploy_preflight import KNOTEN_KENNUNGEN  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
PORTS = REPO / "infra" / "ports.yaml"
HOSTS = REPO / "infra" / "hosts.yaml"
PREFLIGHT = REPO / "tools" / "deploy_preflight.py"

#: Dienst-Felder, die ``pruefe`` liest. Alles andere bleibt in platform.
DIENST_FELDER = ("betriebsstatus", "betriebsstatus_grund", "prod_host")

KOPF = (
    "# GENERIERT von achimdehnert/platform tools/preflight_spiegel.py — nicht editieren.\n"
    "# Minimalauszug fuer den Deploy-Preflight (platform#3596); Quelle: platform {quelle}.\n"
)


def dienst_auszug(ports: dict) -> dict:
    dienste = (ports or {}).get("services") or {}
    return {
        "services": {
            name: {f: eintrag[f] for f in DIENST_FELDER if f in eintrag}
            for name, eintrag in sorted(dienste.items())
        }
    }


def knoten_auszug(hosts: dict) -> dict:
    knoten = (hosts or {}).get("hosts") or {}
    auszug: dict = {}
    for name, eintrag in sorted(knoten.items()):
        eintrag = eintrag or {}
        kurz = {f: eintrag[f] for f in KNOTEN_KENNUNGEN if eintrag.get(f)}
        if eintrag.get("ssh"):
            # nur das Ziel, nicht der Benutzer — deploy_preflight liest ohnehin nur den Teil nach "@"
            kurz["ssh"] = str(eintrag["ssh"]).split("@")[-1].strip()
        auszug[name] = kurz
    return {"hosts": auszug}


def _schreibe(pfad: Path, daten: dict, quelle: str) -> None:
    pfad.write_text(
        KOPF.format(quelle=quelle)
        + yaml.safe_dump(daten, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def erzeuge(ziel: Path, ports: Path = PORTS, hosts: Path = HOSTS) -> list[Path]:
    ziel.mkdir(parents=True, exist_ok=True)
    p_daten = yaml.safe_load(ports.read_text(encoding="utf-8"))
    h_daten = yaml.safe_load(hosts.read_text(encoding="utf-8"))
    _schreibe(ziel / "ports.yaml", dienst_auszug(p_daten), "infra/ports.yaml")
    _schreibe(ziel / "hosts.yaml", knoten_auszug(h_daten), "infra/hosts.yaml")
    shutil.copyfile(PREFLIGHT, ziel / "deploy_preflight.py")
    return [ziel / n for n in ("deploy_preflight.py", "ports.yaml", "hosts.yaml")]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ziel", required=True, type=Path)
    args = ap.parse_args(argv)
    for pfad in erzeuge(args.ziel):
        print(pfad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
