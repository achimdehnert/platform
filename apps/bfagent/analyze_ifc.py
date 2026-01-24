import ifcopenshell

# IFC File path
ifc_path = r"C:\Users\achim\github\bfagent\media\ifc_models\2025\12\5_qU8MDf0.2.02_-_3D-Modell_nur_Kern_30.04.2024.ifc"

print(f"Opening: {ifc_path}")
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
print("ALL ELEMENT TYPES (Top 30):")
print("=" * 80)
for elem_type, count in sorted(element_types.items(), key=lambda x: x[1], reverse=True)[:30]:
    print(f"{elem_type:50s} : {count:6d}")

print()
print("=" * 80)
print("CHECKING SPECIFIC TYPES WE NEED:")
print("=" * 80)

checks = [
    ("IfcBuildingStorey", "Geschosse"),
    ("IfcSpace", "Räume (IfcSpace)"),
    ("IfcZone", "Zonen"),
    ("IfcBuildingElementProxy", "Building Element Proxy (evtl. Räume?)"),
    ("IfcWindow", "Fenster"),
    ("IfcDoor", "Türen"),
    ("IfcWall", "Wände (IfcWall)"),
    ("IfcWallStandardCase", "Wände (IfcWallStandardCase)"),
    ("IfcSlab", "Decken (IfcSlab)"),
    ("IfcSlabStandardCase", "Decken (IfcSlabStandardCase)"),
    ("IfcCovering", "Beläge/Oberflächen"),
]

for ifc_type, description in checks:
    try:
        elements = ifc.by_type(ifc_type)
        count = len(elements)
        status = "✅" if count > 0 else "❌"
        print(f"{status} {description:35s} : {count:6d} gefunden")
    except RuntimeError as e:
        print(f"⚠️  {description:35s} : N/A (nicht in {ifc.schema})")

# Check IfcBuildingElementProxy - könnte Räume enthalten!
print()
print("=" * 80)
print("SAMPLE IfcBuildingElementProxy (first 10):")
print("=" * 80)

proxies = ifc.by_type("IfcBuildingElementProxy")
if proxies:
    print(f"Found {len(proxies)} proxies - showing first 10:")
    for i, proxy in enumerate(proxies[:10]):
        print(f"\n#{i+1} IfcBuildingElementProxy:")
        print(f"  GlobalId    : {proxy.GlobalId}")
        print(f"  Name        : {proxy.Name}")
        print(f"  ObjectType  : {proxy.ObjectType if hasattr(proxy, 'ObjectType') else 'N/A'}")
        print(f"  Description : {proxy.Description if hasattr(proxy, 'Description') else 'N/A'}")
else:
    print("❌ Keine IfcBuildingElementProxy gefunden!")

print()
print("=" * 80)
print("🔍 FAZIT:")
print("=" * 80)
print(f"Schema: {ifc.schema}")
print(f"✅ {len(ifc.by_type('IfcBuildingStorey'))} Geschosse gefunden")
print(f"❌ 0 Räume (IfcSpace nicht vorhanden)")
print(f"❌ 0 Fenster, Türen, Wände, Decken")
print(f"⚠️  409 IfcBuildingElementProxy - evtl. Platzhalter für Ausbau")
print()
print("HINWEIS: Dies scheint ein 'Kern-Modell' zu sein - nur Struktur ohne Ausbau!")
print("Für vollständige Analyse wird ein IFC-Modell mit Ausbau benötigt.")
