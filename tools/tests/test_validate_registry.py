"""Registry-Validierung: Decommission-Eintraege und Waiver-Overrides.

Der Validator ist fail-closed gebaut — ein Override ohne `expires_at` oder mit
abgelaufenem Datum soll blockieren, nicht durchrutschen. Genau das war ungetestet.
Ein Waiver, der still weiterlebt, ist die teurere Fehlrichtung: er haelt eine
Ausnahme offen, von der niemand mehr weiss.

Die Datumsfaelle sind relativ zu heute gerechnet, nicht auf ein festes Datum
gepinnt — ein Test, der am Stichtag kippt, ist selbst ein Fund.
"""

import datetime as dt
import importlib.util
import pathlib

_SRC = pathlib.Path(__file__).resolve().parents[1] / "validate_registry.py"
_spec = importlib.util.spec_from_file_location("validate_registry", _SRC)
vr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vr)

HEUTE = dt.date.today()
MORGEN = (HEUTE + dt.timedelta(days=1)).isoformat()
GESTERN = (HEUTE - dt.timedelta(days=1)).isoformat()


def override(**over):
    basis = {
        "repo": "beispiel-hub",
        "path": "config/settings.py",
        "reason": "Migration laeuft",
        "owner": "achim",
        "expires_at": MORGEN,
    }
    basis.update(over)
    return basis


def decomm(**over):
    basis = {"name": "alt-hub", "date": "2026-01-01", "dead_hostnames": ["alt.example"]}
    basis.update(over)
    return basis


# --- decommissioned ---------------------------------------------------------


def test_should_accept_a_complete_decommission_entry():
    fehler = []
    vr.validate_decommissioned([decomm()], fehler)

    assert fehler == []


def test_should_reject_an_entry_without_any_dead_marker():
    # ohne hostname/ip hat der Eintrag keine Gate-Wirkung — der teuerste Fall,
    # weil die Registry dann Sicherheit vortaeuscht
    fehler = []
    vr.validate_decommissioned([decomm(dead_hostnames=[], dead_ips=[])], fehler)

    assert len(fehler) == 1
    assert "ohne Gate-Wirkung" in fehler[0]


def test_should_accept_an_entry_carrying_only_dead_ips():
    fehler = []
    vr.validate_decommissioned([decomm(dead_hostnames=[], dead_ips=["10.0.0.1"])], fehler)

    assert fehler == []


def test_should_reject_a_duplicate_name():
    fehler = []
    vr.validate_decommissioned([decomm(), decomm()], fehler)

    assert any("doppelter name" in f for f in fehler)


def test_should_reject_missing_name_and_missing_date():
    fehler = []
    vr.validate_decommissioned([decomm(name=None, date=None)], fehler)

    assert any("'name' fehlt" in f for f in fehler)
    assert any("'date' fehlt" in f for f in fehler)


def test_should_reject_an_entry_that_is_not_a_mapping():
    fehler = []
    vr.validate_decommissioned(["nur ein string"], fehler)

    assert fehler == ["decommissioned[0]: kein Mapping"]


# --- overrides --------------------------------------------------------------


def test_should_accept_an_override_that_expires_in_the_future():
    fehler = []
    vr.validate_overrides([override()], fehler)

    assert fehler == []


def test_should_reject_an_expired_override():
    fehler = []
    vr.validate_overrides([override(expires_at=GESTERN)], fehler)

    assert len(fehler) == 1
    assert "abgelaufen" in fehler[0]


def test_should_reject_an_override_expiring_today_as_still_valid():
    # heute ist noch nicht abgelaufen — Grenze explizit festhalten,
    # damit ein spaeterer Umbau sie nicht unbemerkt verschiebt
    fehler = []
    vr.validate_overrides([override(expires_at=HEUTE.isoformat())], fehler)

    assert fehler == []


def test_should_reject_an_override_without_expiry():
    fehler = []
    vr.validate_overrides([override(expires_at=None)], fehler)

    assert len(fehler) == 1
    assert "expires_at" in fehler[0]


def test_should_name_every_missing_required_field_at_once():
    fehler = []
    vr.validate_overrides([{"repo": "x"}], fehler)

    assert len(fehler) == 1
    for feld in ("path", "reason", "owner", "expires_at"):
        assert feld in fehler[0]


def test_should_reject_a_non_iso_expiry_date():
    fehler = []
    vr.validate_overrides([override(expires_at="31.12.2026")], fehler)

    assert len(fehler) == 1
    assert "kein ISO-Datum" in fehler[0]
