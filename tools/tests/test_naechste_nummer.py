"""Tests für scripts/naechste_nummer.py (K1 aus platform#1944).

Das Akzeptanzkriterium lautet: „zweimal hintereinander aus zwei Worktrees
gezogen → zwei verschiedene Nummern, ohne dass dazwischen gepusht wurde."
Genau das prüft `test_should_hand_out_a_different_number_on_the_second_draw` —
alles andere hier stützt es ab.

Kein Netz, kein `gh`, kein `git`: die drei Quellen sind einzeln ersetzbar.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "naechste_nummer.py"
_spec = importlib.util.spec_from_file_location("naechste_nummer", _SCRIPT)
nn = importlib.util.module_from_spec(_spec)
sys.modules["naechste_nummer"] = nn
_spec.loader.exec_module(nn)


@pytest.fixture
def reservierungsdatei(tmp_path, monkeypatch):
    ziel = tmp_path / "nummern-reservierungen.json"
    monkeypatch.setattr(nn, "RESERVIERUNGEN", ziel)
    return ziel


# --- Mustererkennung --------------------------------------------------------


def test_should_recognise_a_konz_path():
    m = nn.MUSTER["konz"].search("docs/konzepte/KONZ-platform-043-formatsatz.md")
    assert m and m.group(1) == "043"


def test_should_recognise_an_adr_path():
    m = nn.MUSTER["adr"].search("docs/adr/ADR-294-llm-gateway.md")
    assert m and m.group(1) == "294"


def test_should_recognise_an_archived_adr_path():
    """Archiv-ADRs liegen tiefer — ihre Nummer bleibt trotzdem vergeben."""
    m = nn.MUSTER["adr"].search("docs/adr/_ARCHIVED/ADR-101-alt.md")
    assert m and m.group(1) == "101"


def test_should_ignore_an_index_file():
    assert nn.MUSTER["konz"].search("docs/konzepte/README.md") is None


# --- naechste ---------------------------------------------------------------


def test_should_return_one_when_nothing_is_taken():
    assert nn.naechste(set()) == 1


def test_should_return_max_plus_one():
    assert nn.naechste({1, 2, 43}) == 44


def test_should_not_reuse_a_gap():
    """Eine Luecke ist meist eine zurueckgezogene Nummer — nicht neu vergeben."""
    assert nn.naechste({1, 2, 5}) == 6


# --- Reservierungen ---------------------------------------------------------


def test_should_persist_a_reservation(reservierungsdatei):
    nn.reserviere("konz", 45, "mein-thema", jetzt=1000.0)
    daten = json.loads(reservierungsdatei.read_text())
    assert daten["konz"][0]["nummer"] == 45
    assert daten["konz"][0]["slug"] == "mein-thema"


def test_should_read_back_a_fresh_reservation(reservierungsdatei):
    nn.reserviere("konz", 45, "x", jetzt=1000.0)
    assert nn.aus_reservierungen("konz", jetzt=1000.0) == {45}


def test_should_ignore_an_expired_reservation(reservierungsdatei):
    nn.reserviere("konz", 45, "x", jetzt=1000.0)
    spaeter = 1000.0 + nn.LEBENSDAUER_S + 1
    assert nn.aus_reservierungen("konz", jetzt=spaeter) == set()


def test_should_keep_reservations_of_the_two_kinds_apart(reservierungsdatei):
    nn.reserviere("konz", 45, "x", jetzt=1000.0)
    assert nn.aus_reservierungen("adr", jetzt=1000.0) == set()


def test_should_drop_expired_entries_when_writing(reservierungsdatei):
    nn.reserviere("konz", 45, "alt", jetzt=1000.0)
    spaeter = 1000.0 + nn.LEBENSDAUER_S + 1
    nn.reserviere("konz", 46, "neu", jetzt=spaeter)
    daten = json.loads(reservierungsdatei.read_text())
    assert [e["nummer"] for e in daten["konz"]] == [46]


def test_should_survive_a_corrupt_reservation_file(reservierungsdatei):
    """Eine kaputte Datei darf die Vergabe nicht anhalten."""
    reservierungsdatei.write_text("{kein json")
    assert nn.aus_reservierungen("konz", jetzt=1000.0) == set()


# --- Das eigentliche Kriterium ---------------------------------------------


def test_should_hand_out_a_different_number_on_the_second_draw(reservierungsdatei):
    """K1: zwei Ziehungen ohne Push dazwischen ergeben zwei Nummern.

    Die Refs bleiben unveraendert — genau der Fall vom 2026-08-12, in dem beide
    Sitzungen `max+1` gegen denselben Stand rechneten.
    """
    refs = {41, 42, 43}

    erste = nn.naechste(refs | nn.aus_reservierungen("konz", jetzt=1000.0))
    nn.reserviere("konz", erste, "sitzung-a", jetzt=1000.0)

    zweite = nn.naechste(refs | nn.aus_reservierungen("konz", jetzt=1001.0))

    assert erste == 44
    assert zweite == 45
    assert erste != zweite


def test_should_repeat_the_collision_without_the_reservation(reservierungsdatei):
    """Gegenprobe: ohne Reservierung liefert die zweite Ziehung dieselbe Nummer.

    Ohne diesen Test belegt der vorige nur, dass zwei Aufrufe zwei Zahlen
    liefern — nicht, dass die Reservierung der Grund dafuer ist.
    """
    refs = {41, 42, 43}
    erste = nn.naechste(refs)
    zweite = nn.naechste(refs)
    assert erste == zweite == 44
