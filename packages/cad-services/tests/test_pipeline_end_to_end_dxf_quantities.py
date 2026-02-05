import pytest

from cad_services import FootprintAreaQuantityRule, QuantityEngine
from cad_services.models import SourceFormat
from cad_services.parsers import DXFParser
from cad_services.pipeline import run_pipeline


def test_pipeline_dxf_to_quantities(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")

    doc = ezdxf.new()
    msp = doc.modelspace()

    poly = msp.add_lwpolyline([(0, 0), (1, 0), (1, 1), (0, 1)], close=True)
    poly.dxf.layer = "SPACE"

    path = tmp_path / "square.dxf"
    doc.saveas(path)

    engine = QuantityEngine(rules=[FootprintAreaQuantityRule(confidence=0.6)])

    result = run_pipeline(parser=DXFParser(), file_path=path, quantity_engine=engine)

    assert result.source_format == SourceFormat.DXF
    assert len(result.elements) == 1

    element = result.elements[0]
    assert element.geometry is not None
    assert element.geometry.footprint_area == pytest.approx(1.0)

    assert len(element.quantities) == 1
    assert element.quantities[0].unit == "m²"
