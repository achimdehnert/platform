"""Tests fuer iil-dienst — Vertrag, Aufruf, Export, Kommandos."""

import json
from io import StringIO

import pytest
from django.core.management import call_command

import iil_dienst
from iil_dienst import DienstFehler, aufruf, dienst, katalog


def test_should_find_demo_service_via_autodiscovery():
    assert "demo-summe" in iil_dienst.REGISTRY
    assert katalog()[0]["parameter"] == [
        {"name": "a", "pflicht": True, "standard": None},
        {"name": "b", "pflicht": False, "standard": 1},
    ]


def test_should_call_same_function_as_app_would():
    from tests.demo.dienste import summe

    assert aufruf("demo-summe", a=2) == summe(a=2) == {"summe": 3}


def test_should_reject_unknown_service_and_bad_arguments():
    with pytest.raises(DienstFehler, match="unbekannter Dienst"):
        aufruf("gibt-es-nicht")
    with pytest.raises(DienstFehler, match="unbekannte Argumente"):
        aufruf("demo-summe", a=1, c=2)
    with pytest.raises(DienstFehler, match="Pflichtargumente fehlen"):
        aufruf("demo-summe")


def test_should_refuse_protected_data_without_gate():
    with pytest.raises(DienstFehler, match="braucht ein Gate"):
        dienst("x", datenklasse="personenbezogen", gate="keins")(lambda: None)
    with pytest.raises(DienstFehler, match="nicht in"):
        dienst("y", datenklasse="geheim", gate="keins")(lambda: None)


def test_should_refuse_positional_only_and_double_registration():
    def f(a, /):
        return a

    with pytest.raises(DienstFehler, match="Schluesselwort"):
        dienst("z", datenklasse="intern", gate="keins")(f)
    with pytest.raises(DienstFehler, match="doppelt registriert"):
        dienst("demo-summe", datenklasse="intern", gate="keins")(lambda: None)


def test_should_export_and_call_via_management_commands():
    out = StringIO()
    call_command("dienste_export", stdout=out)
    export = json.loads(out.getvalue())
    assert [d["name"] for d in export["dienste"]] == ["demo-summe"]

    out = StringIO()
    call_command("dienst_aufruf", "demo-summe", "--argumente", '{"a": 5}', stdout=out)
    antwort = json.loads(out.getvalue())
    assert antwort["ergebnis"] == {"summe": 6}
    assert antwort["dienst"]["gate"] == "keins"


def test_should_exit_2_on_contract_violation_and_3_on_runtime_error():
    out = StringIO()
    with pytest.raises(SystemExit) as e:
        call_command("dienst_aufruf", "demo-summe", "--argumente", '{"a": "x"}', stdout=out)
    assert e.value.code == 3 and json.loads(out.getvalue())["art"] == "laufzeit"

    out = StringIO()
    with pytest.raises(SystemExit) as e:
        call_command("dienst_aufruf", "nix", stdout=out)
    assert e.value.code == 2 and json.loads(out.getvalue())["art"] == "vertrag"
