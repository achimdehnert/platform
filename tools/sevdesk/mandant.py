#!/usr/bin/env python3
"""Mandanten-Umschaltung fuer die sevdesk-Werkzeuge — K8 aus platform#3102.

Warum es das gibt: Der Owner betreibt zwei sevdesk-Mandanten — die IIL GmbH
(Standard) und die Dehnert EDV-Beratung, die der IIL meist selbst Rechnungen
stellt. Jedes sevdesk-Werkzeug soll `--mandant iil|edv` verstehen, ohne den
Zugang je Werkzeug neu zu verdrahten. Diese Datei ist die einzige Stelle, die
weiss, welche Secret-Datei zu welchem Mandanten gehoert — ein Zeiger, nie der
Wert (siehe ``~/.secrets/``, read-only, Inhalte nie auf stdout).

    from mandant import client, mandant_argument

    p = argparse.ArgumentParser()
    mandant_argument(p)
    args = p.parse_args()
    c = client(args.mandant)   # httpx.Client, Authorization-Header gesetzt

`SEVDESK_MANDANT` als Umgebungsvariable ist gleichwertig zu `--mandant` (Default
fuer `--mandant`, per CLI-Flag weiter uebersteuerbar).

Fehlt die Secret-Datei eines Mandanten, bricht ``token_lesen``/``client`` mit
einer Meldung ab, die den ERWARTETEN Pfad nennt (nie den Inhalt) — Exit 3,
kein Traceback (``sys.exit`` statt eine Exception durchreichen lassen).

Bestehende Werkzeuge (``bankpositionen.py``, ``zahlungsabgleich.py``,
``beleg_entwurf.py``) lesen ihren Zugang noch fest verdrahtet auf den
IIL-Pfad — das Umstellen auf dieses Modul ist ein Folgeschritt (#3102 K8),
hier bewusst NICHT mitgemacht (``beleg_entwurf.py`` wird von PR #3104 in
derselben Auftragsrunde bearbeitet).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

API = "https://my.sevdesk.de/api/v1"

#: Standard-Mandant, wenn weder ``--mandant`` noch ``SEVDESK_MANDANT`` gesetzt sind.
STANDARD_MANDANT = "iil"

#: Secret-Datei je Mandant. "iil" ist exakt der Pfad aus
#: ``beleg_entwurf.token_lesen()``/``bankpositionen.token_lesen()``
#: (``TOKEN_DATEI = Path.home() / ".secrets" / "sevdesk_api_token"``).
#: "edv" folgt demselben KEY=WERT-Dateimuster unter einem eigenen Namen
#: (Owner-Vorgabe 2026-09-12: ``sevdesk_dehnert_edv_api_token``).
SECRET_DATEIEN: dict[str, Path] = {
    "iil": Path.home() / ".secrets" / "sevdesk_api_token",
    "edv": Path.home() / ".secrets" / "sevdesk_dehnert_edv_api_token",
}


def mandant_argument(parser: argparse.ArgumentParser) -> None:
    """Fuegt ``--mandant`` hinzu; Default aus ``SEVDESK_MANDANT`` oder iil."""
    parser.add_argument(
        "--mandant",
        choices=sorted(SECRET_DATEIEN),
        default=os.environ.get("SEVDESK_MANDANT", STANDARD_MANDANT),
        help=(
            f"sevdesk-Mandant (Standard: {STANDARD_MANDANT}; "
            "auch per Umgebungsvariable SEVDESK_MANDANT)"
        ),
    )


def secret_datei(mandant: str) -> Path:
    """Erwarteter Pfad der Secret-Datei — auch fuer eine Fehlermeldung nuetzlich,
    ohne dass die Datei existieren oder gelesen werden muss."""
    if mandant not in SECRET_DATEIEN:
        # Explizit print() + sys.exit(3) statt sys.exit(<str>): Letzteres gibt
        # die Meldung nur aus, wenn SystemExit bis zum Interpreter durchreicht
        # (in Tests/aufrufendem Code abgefangen, bliebe sie sonst stumm).
        print(
            f"ABBRUCH: unbekannter Mandant '{mandant}' — bekannt: "
            f"{', '.join(sorted(SECRET_DATEIEN))}"
        )
        sys.exit(3)
    return SECRET_DATEIEN[mandant]


def token_lesen(mandant: str = STANDARD_MANDANT) -> str:
    """Token-Datei ist KEY=WERT, nicht der rohe Wert (sonst 401 bei gueltigem Token).

    Fehlt die Datei, bricht dies mit Exit 3 ab — Meldung nennt den erwarteten
    Pfad, nie einen Wert. ``sys.exit`` statt eine Exception hochzureichen haelt
    den Abbruch traceback-frei.
    """
    pfad = secret_datei(mandant)
    if not pfad.exists():
        print(
            f"ABBRUCH: Zugang fuer Mandant '{mandant}' fehlt — erwartete Datei: {pfad}"
        )
        sys.exit(3)
    roh = pfad.read_text(encoding="utf-8").strip()
    return roh.split("=", 1)[1].strip() if "=" in roh else roh


def client(mandant: str = STANDARD_MANDANT):
    """httpx.Client fuer den gewaehlten Mandanten. Lazy-Import wie in den
    uebrigen sevdesk-Werkzeugen — Umgebungen ohne httpx bleiben testbar."""
    import httpx  # noqa: PLC0415

    return httpx.Client(
        base_url=API, headers={"Authorization": token_lesen(mandant)}, timeout=30
    )


if __name__ == "__main__":
    # Diagnose-Kommando: prueft nur, ob die Secret-Datei je Mandant vorhanden
    # ist — liest/zeigt nie den Inhalt.
    for name, pfad in sorted(SECRET_DATEIEN.items()):
        status = "vorhanden" if pfad.exists() else "FEHLT"
        print(f"{name}: {pfad} — {status}")
