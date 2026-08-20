"""Drill: der Deploy-Pfad muss `DATABASE_URL_MIGRATE` beachten.

Warum es diesen Test gibt: `scripts/deploy.sh` ueberschreibt bewusst den ENTRYPOINT
der App-Images (sonst kaeme `manage.py migrate` nur als Argument beim Entrypoint an).
Genau dadurch war die Logik IM Entrypoint wirkungslos — travel-beat hatte
`DATABASE_URL_MIGRATE` nach einem Crash-Loop korrekt eingebaut, und auf dem
Deploy-Pfad lief die Migration trotzdem als restricted Rolle. Der Fehler
("no schema has been selected to create in") stand woertlich als Vorhersage im
Entrypoint-Kommentar und trat vier Wochen spaeter genau so ein.

Der Test prueft deshalb nicht die Absicht, sondern die **Aufrufzeile**: die Ableitung
muss in derselben Zeile stehen wie das `migrate`, sonst wirkt sie nicht.

Run: `python3 -m pytest tools/tests/test_deploy_migrate_url.py -q`
"""

from __future__ import annotations

import re
from pathlib import Path

_DEPLOY = Path(__file__).resolve().parents[2] / "scripts" / "deploy.sh"
_ABLEITUNG = 'DATABASE_URL="${DATABASE_URL_MIGRATE:-$DATABASE_URL}"'


def _migrate_zeilen() -> list[str]:
    """Alle Zeilen, die `manage.py migrate` im Container starten."""
    return [
        zeile
        for zeile in _DEPLOY.read_text(encoding="utf-8").splitlines()
        if "manage.py migrate" in zeile and "#" not in zeile.split("manage.py")[0]
    ]


def test_should_find_the_migrate_invocations():
    """Schutz gegen einen stillen Fehlschlag dieses Tests selbst.

    Wird `deploy.sh` umgebaut und die Aufrufe verschwinden, wuerden die Pruefungen
    unten ueber eine leere Liste laufen und gruen melden — die Attrappen-Falle.
    """
    zeilen = _migrate_zeilen()
    assert len(zeilen) >= 2, f"erwartet: migrate + migrate --check, gefunden: {zeilen}"


def test_should_derive_migrate_url_in_every_migrate_invocation():
    for zeile in _migrate_zeilen():
        assert _ABLEITUNG in zeile, (
            "Migrations-Aufruf ohne DATABASE_URL_MIGRATE-Ableitung — der Entrypoint "
            f"wird hier ueberschrieben und greift NICHT: {zeile.strip()}"
        )


def test_should_keep_fallback_so_repos_without_the_variable_are_unchanged():
    """`:-` statt `-`: leere Variable faellt ebenfalls auf DATABASE_URL zurueck."""
    assert ":-$DATABASE_URL}" in _DEPLOY.read_text(encoding="utf-8")


def test_should_use_single_quotes_so_the_variable_expands_inside_the_container():
    """Doppelte Anfuehrungszeichen wuerden die Variable auf dem HOST aufloesen —
    dort ist sie leer, und die Ableitung waere still wirkungslos."""
    for zeile in _migrate_zeilen():
        treffer = re.search(r"-c\s+(['\"])", zeile)
        assert treffer, f"kein -c-Argument gefunden: {zeile.strip()}"
        assert treffer.group(1) == "'", (
            "Das -c-Argument muss einfach gequotet sein, sonst expandiert "
            f"${{DATABASE_URL_MIGRATE}} auf dem Host: {zeile.strip()}"
        )
