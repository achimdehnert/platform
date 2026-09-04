"""Drill fuer tools/deploy_concurrency_sweep.py (platform#2229).

Der Sweep fasst 13 fremde Repos an. Jede Zeile, die er NICHT umbaut, muss einen
benannten Grund haben — „passt nicht" als Sammelantwort wuerde sichere,
unbetroffene und uebersehene Repos in einen Topf werfen.
"""

import importlib.util
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "deploy_concurrency_sweep", TOOLS / "deploy_concurrency_sweep.py"
)
sweep = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = sweep
_spec.loader.exec_module(sweep)

KOPF = """name: "Deploy"

concurrency:
  group: deploy-tax-hub-${{ github.ref_name }}
  cancel-in-progress: true

on:
  workflow_dispatch:
    inputs:
      target_environment:
        default: "staging"
"""


def test_should_gruppe_um_die_umgebung_erweitern():
    neu, befund = sweep.umbau(KOPF)
    assert befund == ""
    assert (
        "deploy-tax-hub-${{ github.ref_name }}-${{ inputs.target_environment || 'staging' }}"
        in neu
    )
    assert (
        "cancel-in-progress: ${{ (inputs.target_environment || 'staging') != 'production' }}"
        in neu
    )


def test_should_den_rest_der_datei_unberuehrt_lassen():
    neu, _ = sweep.umbau(KOPF)
    assert neu.startswith('name: "Deploy"')
    assert neu.rstrip().endswith('default: "staging"')


def test_should_idempotent_sein():
    """Zweiter Lauf darf nicht erneut umbauen — sonst schachtelt sich der Ausdruck."""
    neu, _ = sweep.umbau(KOPF)
    nochmal, befund = sweep.umbau(neu)
    assert nochmal == neu
    assert befund == "bereits je Umgebung getrennt"


def test_should_ohne_target_environment_nicht_anfassen():
    """Ohne die Eingabe waere der Ausdruck immer `staging` — Zierrat statt Wirkung."""
    ohne = KOPF.replace('      target_environment:\n        default: "staging"\n', "")
    neu, befund = sweep.umbau(ohne)
    assert neu == ohne
    assert "wirkungslos" in befund


def test_should_cancel_false_als_eigene_loesung_erkennen():
    """trading-hubs Form: Kommentarzeilen zwischen group und cancel-in-progress."""
    anders = """concurrency:
  group: deploy-trading-hub-${{ github.ref_name }}
  # cancel-in-progress: false (issue #170) — verifiziert gegen shared-ci
  cancel-in-progress: false

on:
  workflow_dispatch:
    inputs:
      target_environment:
"""
    neu, befund = sweep.umbau(anders)
    assert neu == anders
    assert "anders geloest" in befund


def test_should_fehlende_gruppe_benennen():
    neu, befund = sweep.umbau("name: x\non:\n  push:\n")
    assert befund == "keine Concurrency-Gruppe — nicht betroffen"


def test_should_unbekannte_form_zur_handpruefung_melden():
    """Der gefaehrlichste Fall: sieht betroffen aus, passt aber nicht ins Muster."""
    seltsam = """concurrency:
  group: deploy-x-${{ github.ref_name }}-${{ github.event_name }}
  cancel-in-progress: true

on:
  workflow_dispatch:
    inputs:
      target_environment:
"""
    _, befund = sweep.umbau(seltsam)
    assert "von Hand ansehen" in befund


def test_should_einrueckung_uebernehmen():
    vier = KOPF.replace("  group:", "    group:").replace(
        "  cancel-in-progress:", "    cancel-in-progress:"
    )
    neu, befund = sweep.umbau(vier)
    assert befund == ""
    assert "\n    group: deploy-tax-hub-" in neu
