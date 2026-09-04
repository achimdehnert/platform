"""Vertragstest fuer den Registry-Erreichbarkeits-Melder (platform#2685).

Die interessanten Faelle sind die, in denen der Melder GRUEN aussieht, ohne es zu sein:
ein stummer Rekorder und ein leeres Protokoll. Beide muessen einen Befund erzeugen —
sonst ist er genau der blinde Melder, gegen den er gebaut wurde.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from registry_erreichbarkeit_melder import Hostbild, _bewerte  # noqa: E402


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _frisch(name: str, zeilen: int = 500, fenster: list[str] | None = None) -> Hostbild:
    return Hostbild(name=name, zeilen=zeilen, juengste=_jetzt() - timedelta(minutes=2),
                    fenster=fenster or [])


def test_should_pass_wenn_beide_hosts_frisch_und_ohne_fenster():
    status, text = _bewerte([_frisch("prod"), _frisch("prod-b")])
    assert status == "PASS"
    assert "kein Ausfallfenster" in text


def test_should_warn_wenn_ein_host_ein_fenster_zeigt():
    status, text = _bewerte([
        _frisch("prod", fenster=["2026-09-02T13:20:00Z ziel=1/5 kontrolle=5/5"]),
        _frisch("prod-b"),
    ])
    assert status == "WARN"
    assert "prod" in text and "Ausfallfenster" in text


def test_should_warn_wenn_der_rekorder_stumm_ist():
    """Ein toter Timer ist der gefaehrlichste Zustand: er meldet nie ein Fenster."""
    alt = Hostbild(name="prod", zeilen=500, juengste=_jetzt() - timedelta(hours=6))
    status, text = _bewerte([alt, _frisch("prod-b")])
    assert status == "WARN"
    assert "stumm" in text


def test_should_warn_wenn_ein_host_noch_nie_gemessen_hat():
    nie = Hostbild(name="prod-b", zeilen=0, juengste=None)
    status, text = _bewerte([_frisch("prod"), nie])
    assert status == "WARN"
    assert "prod-b" in text


def test_should_skip_wenn_kein_host_erreichbar_ist():
    """Nicht messbar ist kein Gruen — die Null waere sonst der eigene Filter."""
    status, text = _bewerte([
        Hostbild(name="prod", fehler="ssh gescheitert: TimeoutExpired"),
        Hostbild(name="prod-b", fehler="kein Protokoll (Rekorder nicht installiert?)"),
    ])
    assert status == "SKIP"
    assert "keine Entwarnung" in text


def test_should_pass_aber_nicht_messbare_hosts_benennen():
    status, text = _bewerte([_frisch("prod"), Hostbild(name="prod-b", fehler="ssh gescheitert")])
    assert status == "PASS"
    assert "nicht messbar: prod-b" in text


@pytest.mark.parametrize("befund_zeile,erwartet", [
    ("2026-09-02T13:20:00Z host=p ziel=1/5 kontrolle=5/5 ip=1.2.3.4 befund=registry", True),
    ("2026-09-02T13:20:00Z host=p ziel=5/5 kontrolle=5/5 ip=1.2.3.4 befund=ok", False),
    ("2026-09-02T13:20:00Z host=p ziel=1/5 kontrolle=1/5 ip=1.2.3.4 befund=leitung", False),
])
def test_should_nur_registry_befunde_als_fenster_zaehlen(befund_zeile, erwartet):
    """`leitung` ist ausdruecklich kein Registry-Fenster — sonst meldet eine schlechte
    Hausleitung einen Registry-Ausfall, und der Kontrollarm waere umsonst gebaut."""
    from registry_erreichbarkeit_melder import ZEILE

    m = ZEILE.match(befund_zeile)
    assert m is not None
    assert (m["befund"] == "registry") is erwartet
