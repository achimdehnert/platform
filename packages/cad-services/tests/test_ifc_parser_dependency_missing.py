from pathlib import Path

import pytest

from cad_services.exceptions import CADParseError
from cad_services.parsers import IFCParser


def test_ifc_parser_dependency_missing(tmp_path: Path):
    p = tmp_path / "a.ifc"
    p.write_text("IFC", encoding="utf-8")

    parser = IFCParser()

    try:
        parser.parse(p)
    except CADParseError as e:
        assert e.code == "IFC_DEPENDENCY_MISSING"
    else:
        pytest.skip("ifcopenshell installed in this environment")
