import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import ifcopenshell

from apps.cad_hub.models import IFCModel

# Get latest uploaded model
model = IFCModel.objects.latest("uploaded_at")
print(f"IFC File: {model.ifc_file.path}")
print(f"Status: {model.status}")
print(f"Schema: {model.ifc_schema}")
print()

# Open with ifcopenshell
ifc = ifcopenshell.open(model.ifc_file.path)
print(f"✅ IFC File opened successfully")
print(f"Schema: {ifc.schema}")
print()

# Count all element types
print("=" * 60)
print("ELEMENT TYPES IN IFC FILE:")
print("=" * 60)

element_types = {}
for element in ifc:
    element_type = element.is_a()
    element_types[element_type] = element_types.get(element_type, 0) + 1

# Sort by count descending
for elem_type, count in sorted(element_types.items(), key=lambda x: x[1], reverse=True):
    print(f"{elem_type:40s} : {count:5d}")

print()
print("=" * 60)
print("RELEVANT FOR PARSING:")
print("=" * 60)

# Check specific types we need
relevant_types = [
    "IfcBuildingStorey",
    "IfcSpace",
    "IfcWindow",
    "IfcDoor",
    "IfcWall",
    "IfcWallStandardCase",
    "IfcSlab",
    "IfcSlabStandardCase",
    "IfcRoom",  # Alternative to IfcSpace
    "IfcZone",  # Another alternative
]

for elem_type in relevant_types:
    count = len(ifc.by_type(elem_type))
    status = "✅" if count > 0 else "❌"
    print(f"{status} {elem_type:40s} : {count:5d}")

print()
print("=" * 60)
print("SAMPLE IfcSpace (first 3):")
print("=" * 60)

spaces = ifc.by_type("IfcSpace")
for i, space in enumerate(spaces[:3]):
    print(f"\nSpace {i+1}:")
    print(f"  GlobalId: {space.GlobalId}")
    print(f"  Name: {space.Name}")
    print(f"  LongName: {space.LongName if hasattr(space, 'LongName') else 'N/A'}")
    print(f"  ObjectType: {space.ObjectType if hasattr(space, 'ObjectType') else 'N/A'}")
