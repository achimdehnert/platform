"""Tests fuer tools/registry-consistency-check.py (PR-Check „Registry-Konsistenz prüfen").

Positivkontrolle in beide Richtungen (#2623): eine Registry mit bekanntem Fehler
liefert genau dieses Finding, eine saubere Registry liefert keins. Kein Netz.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Dateiname mit Bindestrich → kein regulaerer import moeglich.
_MODUL = Path(__file__).resolve().parents[1] / "registry-consistency-check.py"
_spec = importlib.util.spec_from_file_location("registry_consistency_check", _MODUL)
rcc = importlib.util.module_from_spec(_spec)
sys.modules["registry_consistency_check"] = rcc
_spec.loader.exec_module(rcc)


def _rich(*systeme: dict) -> dict[str, dict]:
    return {"domains": [{"name": "d", "systems": list(systeme)}]}


def test_should_report_nothing_for_a_consistent_registry_pair():
    flat = {"a-hub": {"type": "django"}, "b-lib": {"type": "library"}}
    rich = {"a-hub": {"type": "django"}, "b-lib": {"type": "library"}}
    assert rcc.vergleichen(flat, rich) == ([], [], [])


def test_should_report_a_repo_missing_on_either_side():
    flat = {"a-hub": {}, "nur-flach": {}}
    rich = {"a-hub": {}, "nur-reich": {}}
    only_flat, only_rich, mismatch = rcc.vergleichen(flat, rich)
    assert (only_flat, only_rich, mismatch) == (["nur-flach"], ["nur-reich"], [])


def test_should_report_a_type_divergence_on_the_intersection():
    flat = {"a-hub": {"type": "infra"}}
    rich = {"a-hub": {"type": "library"}}
    assert rcc.vergleichen(flat, rich)[2] == [("a-hub", "infra", "library")]


def test_should_not_count_a_missing_type_as_divergence():
    """Fehlt das Feld auf einer Seite, ist das kein Widerspruch, sondern keine Aussage."""
    flat = {"a-hub": {"type": "infra"}}
    rich = {"a-hub": {}}
    assert rcc.vergleichen(flat, rich)[2] == []


def test_should_load_both_registry_shapes_from_files(tmp_path: Path):
    flat_datei = tmp_path / "repo-registry.yaml"
    flat_datei.write_text("repos:\n  a-hub:\n    type: django\n  kaputt: nicht-dict\n")
    rich_datei = tmp_path / "repos.yaml"
    rich_datei.write_text(
        "domains:\n  - name: d\n    systems:\n"
        "      - name: A Hub\n        repo: a-hub\n        type: django\n"
        "      - name: ohne-repo-feld\n"
    )
    flat = rcc.load_flat(flat_datei)
    rich = rcc.load_rich(rich_datei)
    assert flat == {"a-hub": {"type": "django"}}  # Nicht-Dict-Eintrag verworfen
    assert set(rich) == {"a-hub", "ohne-repo-feld"}  # name ist Fallback fuer repo
    assert rcc.vergleichen(flat, rich) == ([], ["ohne-repo-feld"], [])
