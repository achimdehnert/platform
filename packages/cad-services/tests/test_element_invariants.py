import pytest

from cad_services.models import CADElement, ElementCategory, SourceFormat


def test_element_external_id_not_empty():
    with pytest.raises(Exception):
        CADElement(
            source_format=SourceFormat.IFC,
            external_id=" ",
            category=ElementCategory.UNKNOWN,
            element_type="IfcWall",
        )
