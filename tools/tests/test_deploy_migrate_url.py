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


# --- Verhalten statt Text (Retro beefc148, Befund #4) ------------------------
# Die Pruefungen oben vergleichen Zeichenketten. Sie waeren blind gegenueber einer
# textlich aehnlichen, in der Shell aber kaputten Zeile — z.B. doppelte statt
# einfacher Anfuehrungszeichen um das `-c`-Argument. Der folgende Test fuehrt das
# Fragment REAL aus und prueft die Aufloesung am Ergebnis.

import subprocess  # noqa: E402


def _fragment() -> str:
    """Das `-c`-Argument aus deploy.sh, mit `printenv` statt `manage.py` als Sonde.

    **`printenv` und nicht `printf %s "$DATABASE_URL"`** — und das ist keine
    Geschmacksfrage: bei `VAR=wert kommando` expandiert die Shell `"$VAR"` im
    Argument, BEVOR die Zuweisung wirkt. Eine `printf`-Sonde zeigt deshalb den
    ALTEN Wert und laesst den Mechanismus kaputt aussehen, obwohl er traegt.
    `printenv` liest seine EIGENE Umgebung — genau wie `manage.py` es tut
    (`os.environ`). Der erste Anlauf dieses Tests fiel darauf herein; genau dafuer
    fuehrt man das Fragment aus, statt es zu greppen.
    """
    return 'DATABASE_URL="${DATABASE_URL_MIGRATE:-$DATABASE_URL}" printenv DATABASE_URL'


def _lauf(umgebung: dict[str, str]) -> str:
    ergebnis = subprocess.run(
        ["sh", "-c", _fragment()],
        capture_output=True,
        text=True,
        env=umgebung,
        check=True,
    )
    return ergebnis.stdout.rstrip("\n")


def test_should_prefer_migrate_url_when_both_are_set():
    assert (
        _lauf({"DATABASE_URL": "laufzeit", "DATABASE_URL_MIGRATE": "privilegiert"})
        == "privilegiert"
    )


def test_should_fall_back_to_database_url_when_migrate_is_unset():
    """Repos ohne die Variable muessen sich unveraendert verhalten."""
    assert _lauf({"DATABASE_URL": "laufzeit"}) == "laufzeit"


def test_should_fall_back_when_migrate_is_set_but_empty():
    """`:-` statt `-`: auch eine LEERE Variable faellt zurueck.

    Mit `-` statt `:-` liefe der Deploy mit leerer DATABASE_URL — der Fehler
    waere ein Verbindungsfehler weit weg von seiner Ursache.
    """
    assert _lauf({"DATABASE_URL": "laufzeit", "DATABASE_URL_MIGRATE": ""}) == "laufzeit"


def test_should_not_leak_the_assignment_into_the_surrounding_shell():
    """Die Zuweisung gilt nur fuer den einen Prozess, nicht fuer den Stack danach."""
    ergebnis = subprocess.run(
        ["sh", "-c", _fragment() + '; printf ":%s" "$DATABASE_URL"'],
        capture_output=True,
        text=True,
        env={"DATABASE_URL": "laufzeit", "DATABASE_URL_MIGRATE": "privilegiert"},
        check=True,
    )
    assert ergebnis.stdout == "privilegiert\n:laufzeit"
