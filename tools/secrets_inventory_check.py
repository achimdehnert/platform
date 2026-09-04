#!/usr/bin/env python3
"""Prueft ``infra/secrets-inventory.yaml`` gegen das Schema — und zaehlt.

KONZ-dev-hub-005 REC-1 / MT-2. Das Inventar ist SSoT fuer "was liegt wo und
womit beweist man es". Bis zum 2026-09-04 stand dort Freitext ohne Org und ohne
Beleg; ein Werkzeug konnte daraus nicht ableiten, welches Repo gemeint ist.

Das Werkzeug macht zwei Dinge:

1. **Schema** — Verstoss ist Exit 1. Die alte String-Form von ``consumers[]``
   bleibt gueltig (sonst waere die Migration ein Big-Bang), zaehlt aber als
   *unvollstaendig*.
2. **Zaehlen** — die vier Zahlen des Kill-Gates: Eintraege gesamt, mit
   Konsumenten, davon vollqualifiziert, mit ``proof``. AD-3: eine Zahl ist die
   einzige Verteidigung gegen "Konsument weglassen ist billiger als proof
   pflegen".

Werte werden nie gelesen und nie ausgegeben — das Inventar enthaelt keine.

Aufruf::

    python3 tools/secrets_inventory_check.py            # Bericht + Exit-Code
    python3 tools/secrets_inventory_check.py --kurz     # eine Zeile
    python3 tools/secrets_inventory_check.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
INVENTAR = ROOT / "infra" / "secrets-inventory.yaml"
SCHEMA = ROOT / "infra" / "schemas" / "secrets-inventory.schema.json"

#: Diese drei Sektionen haben eine eigene Gestalt (Dateilisten, Serverpfade,
#: SOPS-Konfiguration) und sind bewusst NICHT Eintraege im Sinne des Schemas.
#: Sie kommen mit Stufe 2 (host_env_file-Treiber) dazu.
KEINE_EINTRAEGE = {"server_side", "local", "sops"}


def _iso(wert: Any) -> Any:
    """YAML liest ``2026-09-02`` als ``datetime.date``, JSON Schema kennt nur
    Strings. Ohne diese Normalisierung meldet der Check fuenf Verstoesse an
    voellig korrekten Datumszeilen — ein Lint, der Richtiges rot faerbt, wird
    abgeschaltet statt befolgt."""
    if isinstance(wert, (date, datetime)):
        return wert.isoformat()
    if isinstance(wert, dict):
        return {k: _iso(v) for k, v in wert.items()}
    if isinstance(wert, list):
        return [_iso(v) for v in wert]
    return wert


def lade(pfad: Path = INVENTAR) -> dict[str, Any]:
    return _iso(yaml.safe_load(pfad.read_text(encoding="utf-8")) or {})


def eintraege(inv: dict[str, Any]) -> list[tuple[str, str, dict]]:
    """(sektion, secret, eintrag) fuer alles, was ein Secret-Eintrag ist."""
    raus = []
    for sektion, gruppe in inv.items():
        if sektion in KEINE_EINTRAEGE or not isinstance(gruppe, dict):
            continue
        for name, eintrag in gruppe.items():
            if isinstance(eintrag, dict):
                raus.append((sektion, name, eintrag))
    return raus


def zaehle(inv: dict[str, Any]) -> dict[str, int]:
    gesamt = mit_konsumenten = vollqualifiziert = mit_proof = konsumenten = 0
    konsumenten_ohne_proof = 0
    for _sektion, _name, eintrag in eintraege(inv):
        gesamt += 1
        cons = eintrag.get("consumers") or []
        if not cons:
            continue
        mit_konsumenten += 1
        konsumenten += len(cons)
        if all(isinstance(c, dict) for c in cons):
            vollqualifiziert += 1
        if any(isinstance(c, dict) and c.get("proof") for c in cons):
            mit_proof += 1
        konsumenten_ohne_proof += sum(
            1 for c in cons if not (isinstance(c, dict) and c.get("proof"))
        )
    return {
        "eintraege": gesamt,
        "mit_konsumenten": mit_konsumenten,
        "vollqualifiziert": vollqualifiziert,
        "unvollstaendig": mit_konsumenten - vollqualifiziert,
        "mit_proof": mit_proof,
        "konsumenten": konsumenten,
        "konsumenten_ohne_proof": konsumenten_ohne_proof,
    }


def schema_verstoesse(inv: dict[str, Any], schema_pfad: Path = SCHEMA) -> list[str]:
    """Leere Liste = sauber. Fehlt ``jsonschema``, ist das ein Verstoss —
    ein uebersprungener Check ist kein gruener Check (#2280)."""
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - Umgebungsfrage, nicht Logik
        return ["jsonschema nicht installiert — Schema-Pruefung nicht moeglich"]

    schema = json.loads(schema_pfad.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    raus = []
    for fehler in sorted(validator.iter_errors(inv), key=lambda e: list(e.path)):
        pfad = ".".join(str(p) for p in fehler.path) or "<wurzel>"
        raus.append(f"{pfad}: {fehler.message}")
    return raus


def kurzzeile(z: dict[str, int], verstoesse: list[str]) -> str:
    if verstoesse:
        return (
            f"{len(verstoesse)} Schema-Verstoss/-Verstoesse im Inventar — "
            f"{verstoesse[0][:120]}"
        )
    return (
        f"OK: {z['eintraege']} Eintraege, {z['mit_konsumenten']} mit Konsumenten, "
        f"davon {z['vollqualifiziert']} vollqualifiziert, {z['mit_proof']} mit Beleg "
        f"({z['konsumenten_ohne_proof']} Konsumenten ohne Beleg)"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kurz", action="store_true", help="eine Zeile (Runner-Phase)")
    p.add_argument("--json", action="store_true", dest="als_json")
    p.add_argument("--inventar", type=Path, default=INVENTAR)
    p.add_argument("--schema", type=Path, default=SCHEMA)
    a = p.parse_args(argv)

    inv = lade(a.inventar)
    z = zaehle(inv)
    verstoesse = schema_verstoesse(inv, a.schema)

    if a.als_json:
        print(json.dumps({"zahlen": z, "verstoesse": verstoesse}, ensure_ascii=False, indent=2))
    elif a.kurz:
        print(kurzzeile(z, verstoesse))
    else:
        print(f"Inventar : {a.inventar}")
        print(f"Schema   : {a.schema}")
        print()
        for schluessel, wert in z.items():
            print(f"  {schluessel:<24} {wert}")
        print()
        if verstoesse:
            print(f"{len(verstoesse)} Schema-Verstoss/-Verstoesse:")
            for v in verstoesse:
                print(f"  ✗ {v}")
        else:
            print("✓ Schema erfuellt")
    return 1 if verstoesse else 0


if __name__ == "__main__":
    sys.exit(main())
