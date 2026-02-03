from cad_services.extractors import IFCExtractor
from cad_services.models import ElementCategory


def test_ifc_extractor_minimal_maps_types():
    class FakeIfc:
        def by_type(self, t: str):
            if t == "IfcWall":
                o = type("Obj", (), {})()
                o.GlobalId = "W1"
                o.Name = "Wall"
                return [o]
            return []

    extractor = IFCExtractor()
    elements = extractor.extract(FakeIfc())

    assert len(elements) == 1
    assert elements[0].category == ElementCategory.WALL
