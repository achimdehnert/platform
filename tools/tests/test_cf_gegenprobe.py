"""Tests der Gegenprobe-Beurteilung aus tools/cf_access/gegenprobe.sh (platform#2700).

Die Entscheidung lag bis 2026-09-02 als `if [ "$code" = "200" ]` mitten in
`veroeffentlichen.sh` — zwischen `systemctl --user enable` und einem echten
HTTPS-Abruf, also nicht testbar. Genau dort steckte der Fehler: **jedes** andere
Ergebnis galt als Erfolg, auch ein 502 durch einen kaputten Ursprung.

Geprüft wird deshalb die ausgelagerte Funktion, mit echten Rückgabewerten aus
bash — keine Nachbildung der Logik in Python (die würde nur sich selbst testen).
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

SKRIPT = pathlib.Path(__file__).resolve().parents[1] / "cf_access" / "gegenprobe.sh"

ERWARTET = 0
ACCESS_GREIFT_NICHT = 1
URSPRUNG_STUMM = 2
UNERWARTET = 3


def urteil(code: str, *, schlafen: bool = False) -> int:
    """Ruft die echte bash-Funktion und gibt ihren Rückgabewert zurück."""
    umgebung = {"PATH": "/usr/bin:/bin"}
    if schlafen:
        umgebung["URSPRUNG_DARF_SCHLAFEN"] = "1"
    fertig = subprocess.run(
        ["bash", "-c", f'. "{SKRIPT}"; beurteile_gegenprobe "{code}"'],
        capture_output=True,
        env=umgebung,
    )
    return fertig.returncode


@pytest.mark.parametrize("code", ["301", "302"])
def test_should_accept_the_access_redirect(code):
    """Gemessen 2026-09-02: vier Access-Namen antworten unangemeldet mit 302."""
    assert urteil(code) == ERWARTET


def test_should_reject_a_plain_200():
    """Ein 200 mit laufendem Tunnel heisst: Access greift nicht."""
    assert urteil("200") == ACCESS_GREIFT_NICHT


@pytest.mark.parametrize("code", ["502", "503", "504"])
def test_should_separate_a_dead_origin_from_the_access_redirect(code):
    """Der Kern des Befunds — vorher war das von der Abweisung nicht zu trennen."""
    assert urteil(code) == URSPRUNG_STUMM


@pytest.mark.parametrize("code", ["502", "503", "504"])
def test_should_allow_a_dead_origin_when_the_device_sleeps(code):
    """Geräte mit `betrieb: auf_zuruf` liefern regulär 502 — bewusst erlaubt."""
    assert urteil(code, schlafen=True) == ERWARTET


def test_should_not_let_the_sleep_switch_hide_a_missing_access_wall():
    """Die Ausnahme gilt dem Ursprung, nicht der Wand: 200 bleibt ein Abbruch."""
    assert urteil("200", schlafen=True) == ACCESS_GREIFT_NICHT


@pytest.mark.parametrize("code", ["000", "404", "403", "500", ""])
def test_should_flag_anything_else_as_unexpected(code):
    """Auch 000 (keine Antwort) und 403 sind kein Erfolg — vorher waren sie es."""
    assert urteil(code) == UNERWARTET
