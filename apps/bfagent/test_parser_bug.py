"""
Test: Warum extrahiert _get_all_properties() keine Properties?
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from pathlib import Path

import ifcopenshell

IFC_PATH = Path(
    r"C:\Users\achim\github\mcp-hub\cad_mcp\drawings\20230426_IFC Bendl Offingen SF22-050.ifc"
)

print("Opening IFC with ifcopenshell...")
ifc_file = ifcopenshell.open(str(IFC_PATH))

windows = ifc_file.by_type("IfcWindow")
window = windows[0]

print(f"\nFenster: {window.Name}")
print(f"IsDefinedBy Relations: {len(list(window.IsDefinedBy))}")

# MANUELL Properties extrahieren (wie Parser es machen sollte)
properties = {}

for rel in window.IsDefinedBy:
    print(f"\nRelation Type: {rel.is_a()}")

    if rel.is_a("IfcRelDefinesByProperties"):
        pset = rel.RelatingPropertyDefinition
        print(f"  PropertyDefinition Type: {pset.is_a()}")

        if pset.is_a("IfcPropertySet"):
            pset_name = pset.Name or "Unknown"
            pset_props = {}

            for prop in pset.HasProperties:
                prop_name = prop.Name or "Unknown"

                if prop.is_a("IfcPropertySingleValue"):
                    if hasattr(prop, "NominalValue") and prop.NominalValue:
                        pset_props[prop_name] = str(prop.NominalValue.wrappedValue)
                    else:
                        pset_props[prop_name] = None

            if pset_props:
                properties[pset_name] = pset_props
                print(f"  ✅ PropertySet '{pset_name}': {len(pset_props)} Properties")

print(f"\n{'='*80}")
print(f"RESULTAT:")
print(f"  Extrahierte PropertySets: {len(properties)}")
print(f"  PropertySet Namen: {list(properties.keys())}")

if properties:
    print(f"\n✅ SUCCESS! Properties wurden extrahiert!")

    # Ersten PropertySet anzeigen
    first_pset = list(properties.keys())[0]
    print(f"\n  Beispiel: {first_pset}")
    for key, value in list(properties[first_pset].items())[:3]:
        print(f"    {key}: {value}")
else:
    print(f"\n❌ FAIL! Keine Properties extrahiert!")
