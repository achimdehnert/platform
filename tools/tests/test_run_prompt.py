"""run_prompt: Komplexitaets-Einschaetzung.

`_estimate_complexity` entscheidet, ob eine Aufgabe direkt umgesetzt oder ueber
den vollen agentic-coding-Pfad geschickt wird. Die Regel ist eine
Schluesselwort-Heuristik mit fester Vorrangfolge — und genau die Vorrangfolge
ist das, was beim Umbau versehentlich kippt. Die Faelle unten halten sie fest,
inklusive der Grenze bei der Dateizahl.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "run_prompt.py"
_spec = importlib.util.spec_from_file_location("run_prompt", _SRC)
rp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = rp
_spec.loader.exec_module(rp)


def stufe(instruction: str, dateien: list[str] | None = None) -> str:
    return rp._estimate_complexity(instruction, dateien or [])


@pytest.mark.parametrize(
    "wort", ["refactor", "migrate", "architecture", "service", "celery", "async", "api"]
)
def test_should_rate_a_complex_keyword_as_complex(wort):
    assert stufe(f"Bitte {wort} umsetzen").startswith("COMPLEX")


@pytest.mark.parametrize(
    "wort", ["fix", "bug", "typo", "rename", "text", "farbe", "color"]
)
def test_should_rate_a_simple_keyword_as_simple(wort):
    assert stufe(f"Nur ein {wort}").startswith("SIMPLE")


def test_should_default_to_moderate_without_any_keyword():
    assert stufe("Formular um ein Feld ergaenzen").startswith("MODERATE")


def test_should_let_complex_win_over_simple():
    """Beide Klassen im selben Satz: die teurere Einschaetzung gewinnt."""
    assert stufe("fix im service layer").startswith("COMPLEX")


def test_should_match_keywords_case_insensitively():
    assert stufe("REFACTOR der Abrechnung").startswith("COMPLEX")


def test_should_rate_more_than_four_files_as_complex():
    assert stufe("Kleinigkeit", [f"a{i}.py" for i in range(5)]).startswith("COMPLEX")


def test_should_not_trigger_the_file_threshold_at_exactly_four():
    """Die Grenze ist >4, nicht >=4 — hier festgehalten, damit sie nicht wandert."""
    assert stufe("Kleinigkeit", [f"a{i}.py" for i in range(4)]).startswith("MODERATE")


def test_should_let_the_file_count_override_a_simple_keyword():
    assert stufe("nur ein typo", [f"a{i}.py" for i in range(6)]).startswith("COMPLEX")


def test_should_name_the_recommended_path_in_the_complex_verdict():
    assert "/agentic-coding" in stufe("refactor")


def test_should_match_a_keyword_inside_a_longer_word():
    """Die Heuristik prueft Teilstrings, nicht Wortgrenzen — sichtbar statt still."""
    assert stufe("Prefix-Renaming vorbereiten").startswith("SIMPLE")


def test_should_handle_an_empty_instruction():
    assert stufe("").startswith("MODERATE")
