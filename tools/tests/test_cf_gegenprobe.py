"""Tests der Gegenprobe-Beurteilung aus tools/cf_access/gegenprobe.sh (platform#2700).

Die Entscheidung lag bis 2026-09-02 als `if [ "$code" = "200" ]` mitten in
`veroeffentlichen.sh` — zwischen `systemctl --user enable` und einem echten
HTTPS-Abruf, also nicht testbar. Genau dort steckte der Fehler: **jedes** andere
Ergebnis galt als Erfolg, auch ein 502 durch einen kaputten Ursprung.

Geprüft wird deshalb die ausgelagerte Funktion, mit echten Rückgabewerten aus
bash — keine Nachbildung der Logik in Python (die würde nur sich selbst testen).

Seit #3507 entscheidet ueber den schlafenden Ursprung die Deklaration
`auf_zuruf` des Geraets (zweites Argument), nicht mehr ein von Hand gesetzter
Schalter. Die Deklarationen kommen aus einer Fixture-Datei, nie aus der echten
governance/deklarationen.json.
"""

from __future__ import annotations

import datetime as dt
import os
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import befund_journal as bj  # noqa: E402

SKRIPT = pathlib.Path(__file__).resolve().parents[1] / "cf_access" / "gegenprobe.sh"

ERWARTET = 0
ACCESS_GREIFT_NICHT = 1
URSPRUNG_STUMM = 2
UNERWARTET = 3


@pytest.fixture
def dekl(tmp_path: pathlib.Path) -> pathlib.Path:
    """Leere Fixture-Datei; Tests legen darin Deklarationen an."""
    return tmp_path / "deklarationen.json"


def _heute() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def urteil(code: str, dekl: pathlib.Path, geraet: str = "") -> int:
    """Ruft die echte bash-Funktion und gibt ihren Rückgabewert zurück."""
    umgebung = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "BEFUND_DEKLARATIONEN_DATEI": str(dekl),
    }
    fertig = subprocess.run(
        ["bash", "-c", f'. "{SKRIPT}"; beurteile_gegenprobe "{code}" "{geraet}"'],
        capture_output=True,
        env=umgebung,
    )
    return fertig.returncode


def _auf_zuruf(dekl: pathlib.Path, geraet: str, bis: dt.date) -> None:
    bj.setze_deklaration(geraet, "auf_zuruf", "Test", bis.isoformat(), pfad=dekl)


@pytest.mark.parametrize("code", ["301", "302"])
def test_should_accept_the_access_redirect(code, dekl):
    """Gemessen 2026-09-02: vier Access-Namen antworten unangemeldet mit 302."""
    assert urteil(code, dekl) == ERWARTET


def test_should_reject_a_plain_200(dekl):
    """Ein 200 mit laufendem Tunnel heisst: Access greift nicht."""
    assert urteil("200", dekl) == ACCESS_GREIFT_NICHT


@pytest.mark.parametrize("code", ["502", "503", "504"])
def test_should_separate_a_dead_origin_from_the_access_redirect(code, dekl):
    """Der Kern des Befunds — vorher war das von der Abweisung nicht zu trennen."""
    assert urteil(code, dekl) == URSPRUNG_STUMM


@pytest.mark.parametrize("code", ["502", "503", "504"])
def test_should_allow_a_dead_origin_when_the_device_is_declared_auf_zuruf(code, dekl):
    """Geraet mit gueltiger Deklaration `auf_zuruf` liefert regulaer 502."""
    _auf_zuruf(dekl, "gpu-box", _heute() + dt.timedelta(days=30))
    assert urteil(code, dekl, "gpu-box") == ERWARTET


def test_should_flag_dead_origin_again_when_declaration_expired_yesterday(dekl):
    """Positivkontrolle #3507: Ablauf einen Tag zurueck -> 502 ist wieder ein Fehler."""
    _auf_zuruf(dekl, "gpu-box", _heute() - dt.timedelta(days=1))
    assert urteil("502", dekl, "gpu-box") == URSPRUNG_STUMM


def test_should_not_let_another_device_declaration_excuse_this_origin(dekl):
    """Die Deklaration gilt ihrem Geraet, nicht jedem Ursprung."""
    _auf_zuruf(dekl, "gpu-box", _heute() + dt.timedelta(days=30))
    assert urteil("502", dekl, "dev-desktop") == URSPRUNG_STUMM


def test_should_ignore_the_retired_hand_switch(dekl):
    """Der alte Schalter URSPRUNG_DARF_SCHLAFEN=1 wirkt nicht mehr (#3507)."""
    fertig = subprocess.run(
        ["bash", "-c", f'. "{SKRIPT}"; beurteile_gegenprobe 502'],
        capture_output=True,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "BEFUND_DEKLARATIONEN_DATEI": str(dekl),
            "URSPRUNG_DARF_SCHLAFEN": "1",
        },
    )
    assert fertig.returncode == URSPRUNG_STUMM


def test_should_not_let_the_sleep_declaration_hide_a_missing_access_wall(dekl):
    """Die Ausnahme gilt dem Ursprung, nicht der Wand: 200 bleibt ein Abbruch."""
    _auf_zuruf(dekl, "gpu-box", _heute() + dt.timedelta(days=30))
    assert urteil("200", dekl, "gpu-box") == ACCESS_GREIFT_NICHT


@pytest.mark.parametrize("code", ["000", "404", "403", "500", ""])
def test_should_flag_anything_else_as_unexpected(code, dekl):
    """Auch 000 (keine Antwort) und 403 sind kein Erfolg — vorher waren sie es."""
    assert urteil(code, dekl) == UNERWARTET
