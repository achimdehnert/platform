"""
Direct ifcopenshell Debug: Properties extrahieren
"""

from pathlib import Path

import ifcopenshell

IFC_PATH = Path(
    r"C:\Users\achim\github\mcp-hub\cad_mcp\drawings\20230426_IFC Bendl Offingen SF22-050.ifc"
)

print("Opening IFC...")
ifc = ifcopenshell.open(str(IFC_PATH))

print(f"Schema: {ifc.schema}")

windows = ifc.by_type("IfcWindow")
print(f"\nGefundene Fenster: {len(windows)}")

if windows:
    window = windows[0]
    print(f"\n=== Erstes Fenster ===")
    print(f"Name: {window.Name}")
    print(f"GlobalId: {window.GlobalId}")

    # IsDefinedBy Relations prüfen
    print(f"\nIsDefinedBy Attribut vorhanden: {hasattr(window, 'IsDefinedBy')}")

    if hasattr(window, "IsDefinedBy"):
        rels = list(window.IsDefinedBy)
        print(f"Anzahl IsDefinedBy Relations: {len(rels)}")

        for i, rel in enumerate(rels):
            print(f"\n--- Relation {i+1} ---")
            print(f"  Type: {rel.is_a()}")

            if rel.is_a("IfcRelDefinesByProperties"):
                pset = rel.RelatingPropertyDefinition
                print(f"  PropertyDefinition Type: {pset.is_a()}")
                print(f"  PropertyDefinition Name: {getattr(pset, 'Name', 'N/A')}")

                if pset.is_a("IfcPropertySet"):
                    print(f"  PropertySet: {pset.Name}")
                    props = list(pset.HasProperties)
                    print(f"  Anzahl Properties: {len(props)}")

                    for j, prop in enumerate(props[:5]):  # Erste 5
                        print(
                            f"    Property {j+1}: {prop.Name} = {getattr(prop, 'NominalValue', 'N/A')}"
                        )

                    if len(props) > 5:
                        print(f"    ... und {len(props) - 5} weitere")
    else:
        print("FEHLER: IsDefinedBy Attribut fehlt!")
        print(f"Verfügbare Attribute: {dir(window)}")

print("\n" + "=" * 80)
