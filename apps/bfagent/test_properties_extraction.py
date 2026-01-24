"""
Test-Script: Properties-Extraktion aus Bendl IFC

Testet ob der Parser Properties extrahiert.
"""

import os
import sys

import django

# Django Setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from pathlib import Path

from apps.cad_hub.services.ifc_parser import IFCParserService

# Bendl IFC Pfad
IFC_PATH = Path(
    r"C:\Users\achim\github\mcp-hub\cad_mcp\drawings\20230426_IFC Bendl Offingen SF22-050.ifc"
)

if not IFC_PATH.exists():
    print(f"❌ IFC Datei nicht gefunden: {IFC_PATH}")
    sys.exit(1)

print(f"📋 Teste Properties-Extraktion...")
print(f"IFC: {IFC_PATH}")
print("-" * 80)

# Parser initialisieren
parser = IFCParserService()

# IFC parsen
result = parser.parse_file(IFC_PATH)

print(f"\n✅ Parse erfolgreich!")
print(f"Schema: {result.schema}")
print(f"Application: {result.application}")
print(f"Fenster gefunden: {len(result.windows)}")

# Erstes Fenster analysieren
if result.windows:
    window = result.windows[0]
    print(f"\n📐 Erstes Fenster:")
    print(f"  Name: {window.name}")
    print(f"  GUID: {window.ifc_guid}")
    print(f"  Breite: {window.width}m")
    print(f"  Höhe: {window.height}m")
    print(f"  Material: {window.material}")
    print(f"\n🔧 PROPERTIES:")

    if window.properties:
        print(f"  Anzahl PropertySets: {len(window.properties)}")
        for pset_name, props in window.properties.items():
            print(f"\n  [{pset_name}]")
            for key, value in list(props.items())[:5]:  # Erste 5 Properties
                print(f"    {key}: {value}")
            if len(props) > 5:
                print(f"    ... und {len(props) - 5} weitere")
    else:
        print("  ❌ KEINE PROPERTIES GEFUNDEN!")
        print(f"  properties = {window.properties}")

    print(f"\n📊 Properties Type: {type(window.properties)}")
    print(f"📊 Properties Length: {len(window.properties) if window.properties else 0}")

else:
    print("\n❌ Keine Fenster gefunden!")

print("\n" + "=" * 80)
print("DONE")
