"""Tests fuer tools/pypi_coldstart_stufe2.py — die Sicherheitsgrenze (#3575 K3).

Der Probe-PR ist der Beweis fuer den Loop; hier haengt, was Modell-Output von
Befehl trennt: die ast-Grammatik ist fail-closed, der Pfad ist fest.
"""

from __future__ import annotations

import importlib.util
import pathlib

_SPEC = importlib.util.spec_from_file_location(
    "pypi_coldstart_stufe2",
    pathlib.Path(__file__).resolve().parents[1] / "pypi_coldstart_stufe2.py",
)
m = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(m)

MODS = {"aifw"}


def test_should_accept_trivial_probe():
    src = '"""Probe."""\nimport aifw\n\n\ndef test_should_expose_module():\n    assert hasattr(aifw, "__name__")\n    assert isinstance(aifw.__name__, str)\n'
    assert m.validate_probe(src, MODS) == []


def test_should_reject_foreign_import_and_from_import():
    assert m.validate_probe("import os\n\ndef test_x():\n    assert os\n", MODS)
    assert m.validate_probe("from aifw import x\n\ndef test_x():\n    assert x\n", MODS)


def test_should_reject_calls_into_package_and_io():
    assert m.validate_probe(
        "import aifw\n\ndef test_x():\n    assert aifw.run()\n", MODS
    )
    assert m.validate_probe(
        "import aifw\n\ndef test_x():\n    assert open('x')\n", MODS
    )


def test_should_reject_non_assert_statements_and_top_level_code():
    assert m.validate_probe(
        "import aifw\n\ndef test_x():\n    y = 1\n    assert y\n", MODS
    )
    assert m.validate_probe(
        "import aifw\nprint(1)\n\ndef test_x():\n    assert aifw\n", MODS
    )


def test_should_reject_fixtures_decorators_and_too_many_tests():
    assert m.validate_probe(
        "import aifw\n\ndef test_x(tmp_path):\n    assert aifw\n", MODS
    )
    src = "import aifw\n" + "".join(
        f"\ndef test_{i}():\n    assert aifw\n" for i in range(3)
    )
    assert any("zu viele" in p for p in m.validate_probe(src, MODS))


def test_should_require_at_least_one_test_and_valid_syntax():
    assert any("keine test_" in p for p in m.validate_probe("import aifw\n", MODS))
    assert any("SyntaxError" in p for p in m.validate_probe("def (:\n", MODS))


def test_should_parse_answer_only_with_string_path_and_content():
    assert m.parse_answer({"path": "a", "content": "b"}) == ("a", "b")
    assert m.parse_answer({"path": 1, "content": "b"}) == (None, None)
    assert m.parse_answer(None) == (None, None)
