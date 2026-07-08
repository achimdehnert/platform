"""Tests für scripts/adr_next_number.py (Issue #997, T-13).

`scan_adr_dir` / `get_conflicts` / `get_next_free` liefen bisher 0 Tests, obwohl
adr-guard.yml sie auf jedem ADR-PR aufruft (und der ADR-265-Kollisions-Vorfall
vom 2026-07-05 genau die Konflikt-Erkennung betraf). Rein lokal (tmp_path),
keine echten `gh`-/Netz-Calls nötig — das Modul ruft keine an.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "adr_next_number.py"
_spec = importlib.util.spec_from_file_location("adr_next_number", _SCRIPT)
ann = importlib.util.module_from_spec(_spec)
sys.modules["adr_next_number"] = ann
_spec.loader.exec_module(ann)


def _touch(d: Path, name: str) -> Path:
    f = d / name
    f.write_text(f"# {name}\n", encoding="utf-8")
    return f


# --- scan_adr_dir ------------------------------------------------------------

def test_should_return_empty_mapping_for_empty_adr_dir(tmp_path):
    assert ann.scan_adr_dir(tmp_path) == {}


def test_should_scan_adr_files_into_number_mapping(tmp_path):
    _touch(tmp_path, "ADR-001-first-decision.md")
    _touch(tmp_path, "ADR-002-second-decision.md")

    mapping = ann.scan_adr_dir(tmp_path)

    assert set(mapping.keys()) == {1, 2}
    assert mapping[1][0].name == "ADR-001-first-decision.md"
    assert mapping[2][0].name == "ADR-002-second-decision.md"


def test_should_ignore_non_adr_files_when_scanning(tmp_path):
    _touch(tmp_path, "ADR-001-first-decision.md")
    _touch(tmp_path, "README.md")
    _touch(tmp_path, "not-an-adr.txt")

    mapping = ann.scan_adr_dir(tmp_path)

    assert set(mapping.keys()) == {1}


# --- get_conflicts -------------------------------------------------------------

def test_should_report_no_conflicts_on_happy_path(tmp_path):
    _touch(tmp_path, "ADR-001-first-decision.md")
    _touch(tmp_path, "ADR-002-second-decision.md")

    mapping = ann.scan_adr_dir(tmp_path)

    assert ann.get_conflicts(mapping) == {}


def test_should_detect_conflict_when_two_files_claim_same_number(tmp_path):
    """Repro ADR-265-Kollision (2026-07-05): zwei Dateien beanspruchen dieselbe Nummer."""
    _touch(tmp_path, "ADR-100-first-slug.md")
    _touch(tmp_path, "ADR-100-second-slug.md")
    _touch(tmp_path, "ADR-101-unrelated.md")

    mapping = ann.scan_adr_dir(tmp_path)
    conflicts = ann.get_conflicts(mapping)

    assert set(conflicts.keys()) == {100}
    assert len(conflicts[100]) == 2
    names = {f.name for f in conflicts[100]}
    assert names == {"ADR-100-first-slug.md", "ADR-100-second-slug.md"}


def test_should_return_no_conflicts_for_empty_dir(tmp_path):
    mapping = ann.scan_adr_dir(tmp_path)
    assert ann.get_conflicts(mapping) == {}


# --- get_next_free --------------------------------------------------------------

def test_should_return_one_as_next_free_when_no_adrs_exist():
    assert ann.get_next_free({}) == 1


def test_should_return_max_plus_one_as_next_free():
    mapping = {1: [Path("ADR-001-a.md")], 2: [Path("ADR-002-b.md")], 5: [Path("ADR-005-c.md")]}
    assert ann.get_next_free(mapping) == 6


def test_should_ignore_gaps_when_computing_next_free():
    """Range-/Gap-Konzept ist ADR-059/ADR-107 zufolge abgeschafft: global max+1 zählt,
    Lücken (hier: 2 fehlt) werden NICHT aufgefüllt."""
    mapping = {1: [Path("ADR-001-a.md")], 3: [Path("ADR-003-c.md")]}
    assert ann.get_next_free(mapping) == 4


def test_should_return_max_plus_one_even_when_max_number_itself_is_a_conflict():
    """Edge-Case: die höchste vergebene Nummer ist selbst eine Kollision (2 Dateien) —
    get_next_free zählt trotzdem korrekt einen weiter (max+1 liegt außerhalb aller
    belegten Keys, Kollisionen ändern daran nichts)."""
    mapping = {
        5: [Path("ADR-005-a.md")],
        6: [Path("ADR-006-a.md"), Path("ADR-006-b.md")],
    }
    assert ann.get_next_free(mapping) == 7
