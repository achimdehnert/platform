from cad_services.calculators import FootprintAreaQuantityRule, QuantityEngine
from cad_services.models import (
    CADElement,
    CADGeometry,
    ElementCategory,
    QuantityMethod,
    QuantityType,
    SourceFormat,
)


def test_quantity_engine_applies_rules():
    element = CADElement(
        source_format=SourceFormat.DXF,
        external_id="1",
        category=ElementCategory.SPACE,
        element_type="LWPOLYLINE",
        geometry=CADGeometry(footprint_area=12.5),
    )

    engine = QuantityEngine(rules=[FootprintAreaQuantityRule(confidence=0.6)])
    engine.apply([element])

    assert len(element.quantities) == 1

    q = element.quantities[0]
    assert q.quantity_type == QuantityType.AREA
    assert q.unit == "m²"
    assert q.method == QuantityMethod.COMPUTED_2D
    assert q.confidence == 0.6
    assert q.inputs == {"footprint_area": 12.5}
    assert q.formula == "footprint_area"
