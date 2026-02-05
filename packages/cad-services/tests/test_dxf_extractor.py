import pytest

from cad_services.extractors import DXFExtractor
from cad_services.models import ElementCategory


def test_dxf_extractor_maps_layer_to_category():
    ezdxf = pytest.importorskip("ezdxf")

    doc = ezdxf.new()
    msp = doc.modelspace()
    line = msp.add_line((0, 0), (1, 1))
    line.dxf.layer = "WAND_X"

    extractor = DXFExtractor()
    elements = extractor.extract(msp)

    assert len(elements) == 1
    assert elements[0].category == ElementCategory.WALL
