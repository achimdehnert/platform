import ifcopenshell

# IFC File with windows
ifc_path = (
    r"C:\Users\achim\github\mcp-hub\cad_mcp\drawings\20230426_IFC Bendl Offingen SF22-050.ifc"
)

print(f"Analyzing: {ifc_path}")
print("=" * 80)

ifc = ifcopenshell.open(ifc_path)
print(f"✅ IFC File opened")
print(f"Schema: {ifc.schema}")
print()

# Count element types
element_types = {}
for element in ifc:
    element_type = element.is_a()
    element_types[element_type] = element_types.get(element_type, 0) + 1

print("=" * 80)
print("TOP 20 ELEMENT TYPES:")
print("=" * 80)
for elem_type, count in sorted(element_types.items(), key=lambda x: x[1], reverse=True)[:20]:
    print(f"{elem_type:50s} : {count:6d}")

print()
print("=" * 80)
print("RELEVANT FOR CAD HUB:")
print("=" * 80)

checks = [
    ("IfcBuildingStorey", "Geschosse"),
    ("IfcSpace", "Räume (IfcSpace)"),
    ("IfcZone", "Zonen"),
    ("IfcWindow", "Fenster"),
    ("IfcDoor", "Türen"),
    ("IfcWall", "Wände (IfcWall)"),
    ("IfcWallStandardCase", "Wände (IfcWallStandardCase)"),
    ("IfcSlab", "Decken (IfcSlab)"),
    ("IfcBeam", "Träger"),
    ("IfcColumn", "Stützen"),
]

results = {}
for ifc_type, description in checks:
    try:
        elements = ifc.by_type(ifc_type)
        count = len(elements)
        status = "✅" if count > 0 else "❌"
        print(f"{status} {description:40s} : {count:6d}")
        results[ifc_type] = count
    except RuntimeError:
        print(f"⚠️  {description:40s} : N/A (nicht in {ifc.schema})")
        results[ifc_type] = 0

# Sample Windows
print()
print("=" * 80)
print("SAMPLE WINDOWS (first 10):")
print("=" * 80)

windows = ifc.by_type("IfcWindow")
if windows:
    print(f"Total: {len(windows)} Fenster gefunden\n")
    for i, window in enumerate(windows[:10]):
        print(f"\n#{i+1} IfcWindow:")
        print(f"  GlobalId    : {window.GlobalId}")
        print(f"  Name        : {window.Name}")
        print(f"  ObjectType  : {window.ObjectType if hasattr(window, 'ObjectType') else 'N/A'}")
        print(f"  Tag         : {window.Tag if hasattr(window, 'Tag') else 'N/A'}")

        # Try to get dimensions
        if hasattr(window, "IsDefinedBy"):
            for rel in window.IsDefinedBy[:2]:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    if hasattr(pset, "Name"):
                        print(f"    PropertySet: {pset.Name}")
                        if hasattr(pset, "HasProperties"):
                            for prop in list(pset.HasProperties)[:3]:
                                if hasattr(prop, "Name") and hasattr(prop, "NominalValue"):
                                    print(
                                        f"      - {prop.Name}: {prop.NominalValue.wrappedValue if hasattr(prop.NominalValue, 'wrappedValue') else prop.NominalValue}"
                                    )
else:
    print("❌ Keine Fenster gefunden!")

# Summary
print()
print("=" * 80)
print("🎯 ZUSAMMENFASSUNG:")
print("=" * 80)
print(f"Schema: {ifc.schema}")
print(f"✅ {results.get('IfcBuildingStorey', 0)} Geschosse")
print(f"✅ {results.get('IfcSpace', 0)} Räume")
print(f"✅ {results.get('IfcWindow', 0)} Fenster")
print(f"✅ {results.get('IfcDoor', 0)} Türen")
print(f"✅ {results.get('IfcWall', 0) + results.get('IfcWallStandardCase', 0)} Wände")
print(f"✅ {results.get('IfcSlab', 0)} Decken")
print()
print("👉 Dieses Modell sollte ALLE Daten für CAD Hub liefern!")
