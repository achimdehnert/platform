import pytest

from cad_services.models import SourceFormat
from cad_services.parsers import DXFParser


def test_dxf_parser_parses_minimal(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")

    doc = ezdxf.new()
    msp = doc.modelspace()
    line = msp.add_line((0, 0), (1, 1))
    line.dxf.layer = "WAND_A"

    path = tmp_path / "a.dxf"
    doc.saveas(path)

    parser = DXFParser()
    result = parser.parse(path)

    assert result.source_format == SourceFormat.DXF
    assert result.file_hash
    assert result.statistics.file_size_bytes > 0
    assert result.statistics.parse_duration_ms >= 0

    assert len(result.elements) == 1
    assert result.statistics.total_elements == 1
    assert result.statistics.elements_by_category["wall"] == 1
