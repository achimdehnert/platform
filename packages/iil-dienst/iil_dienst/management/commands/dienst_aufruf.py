"""``manage.py dienst_aufruf <name> [--argumente JSON]`` — einen Dienst ueber seinen Vertrag aufrufen.

Ausgabe immer JSON auf stdout: ``{"dienst": <vertrag>, "ergebnis": ...}`` oder
``{"fehler": ..., "art": "vertrag"|"laufzeit"}``. Exit 0 = Ergebnis, 2 = Vertrag
verletzt (unbekannter Dienst, falsche Argumente), 3 = der Dienst selbst warf.
Der Gateway-Aufruf und der App-Aufruf treffen dieselbe Funktion.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from iil_dienst import REGISTRY, DienstFehler, aufruf


class Command(BaseCommand):
    help = "Einen registrierten Dienst aufrufen; Ergebnis als JSON (iil-dienst)"

    def add_arguments(self, parser):
        parser.add_argument("name")
        parser.add_argument("--argumente", default="{}", help="Argumente als JSON-Objekt")

    def handle(self, *args, **options):
        try:
            argumente = json.loads(options["argumente"])
        except json.JSONDecodeError as e:
            raise CommandError(f"--argumente ist kein JSON: {e}") from e
        if not isinstance(argumente, dict):
            raise CommandError("--argumente muss ein JSON-Objekt sein")
        name = options["name"]
        try:
            ergebnis = aufruf(name, **argumente)
        except DienstFehler as e:
            self.stdout.write(json.dumps({"fehler": str(e), "art": "vertrag"}, ensure_ascii=False))
            raise SystemExit(2) from e
        except Exception as e:  # noqa: BLE001 — der Dienst selbst hat geworfen; Art und Text durchreichen
            self.stdout.write(json.dumps({"fehler": f"{type(e).__name__}: {e}", "art": "laufzeit"}, ensure_ascii=False))
            raise SystemExit(3) from e
        self.stdout.write(json.dumps({"dienst": REGISTRY[name].vertrag(), "ergebnis": ergebnis}, ensure_ascii=False, default=str))
