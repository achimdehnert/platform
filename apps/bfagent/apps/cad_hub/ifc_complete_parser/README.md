# 📋 IFC Complete Parser - Vollständige Dokumentation

## Übersicht

Der **IFC Complete Parser** extrahiert **ALLE** Informationen aus IFC-Dateien, einschließlich:

- ✅ Alle PropertySets (Pset_*)
- ✅ Alle BaseQuantities (Qto_*)
- ✅ Materialien mit Schichtaufbau
- ✅ Klassifikationen (Omniclass, Uniclass, etc.)
- ✅ Räumliche Struktur (Site, Building, Storeys, Spaces)
- ✅ Alle Bauelemente mit Properties
- ✅ Beziehungen und Abhängigkeiten

---

## Installation

```bash
pip install ifcopenshell
```

---

## Schnellstart

```python
from ifc_complete_parser import IfcCompleteParser

# Parsen
parser = IfcCompleteParser("model.ifc")
project = parser.parse()

# Räume mit Brandschutz
for space in project.spaces:
    print(f"{space.name}: {space.fire_rating}")
    
# Export als JSON
project.save_json("output.json")
```

---

## 🏠 Extrahierte Raum-Informationen (IfcSpace)

### Geometrie (BaseQuantities)

| Property | Typ | Einheit | Quelle |
|----------|-----|---------|--------|
| `net_floor_area` | Decimal | m² | Qto_SpaceBaseQuantities.NetFloorArea |
| `gross_floor_area` | Decimal | m² | Qto_SpaceBaseQuantities.GrossFloorArea |
| `net_wall_area` | Decimal | m² | Qto_SpaceBaseQuantities.NetWallArea |
| `net_ceiling_area` | Decimal | m² | Qto_SpaceBaseQuantities.NetCeilingArea |
| `net_volume` | Decimal | m³ | Qto_SpaceBaseQuantities.NetVolume |
| `gross_volume` | Decimal | m³ | Qto_SpaceBaseQuantities.GrossVolume |
| `net_perimeter` | Decimal | m | Qto_SpaceBaseQuantities.NetPerimeter |
| `net_height` | Decimal | m | Qto_SpaceBaseQuantities.FinishCeilingHeight |

### Brandschutz (Pset_SpaceFireSafetyRequirements)

| Property | Typ | Beschreibung |
|----------|-----|--------------|
| `fire_compartment` | str | Brandabschnitt-Bezeichnung |
| `fire_rating` | str | Feuerwiderstandsklasse (F30, F60, F90, REI 90...) |
| `sprinkler_protected` | bool | Sprinkleranlage vorhanden |
| `ex_zone` | str | Explosionsschutz-Zone (0, 1, 2, 20, 21, 22) |

### Thermik (Pset_SpaceThermalRequirements)

| Property | Typ | Einheit | Beschreibung |
|----------|-----|---------|--------------|
| `design_heating_load` | Decimal | W | Heizlast |
| `design_cooling_load` | Decimal | W | Kühllast |
| `design_temperature_heating` | Decimal | °C | Auslegungstemperatur Heizung |
| `design_temperature_cooling` | Decimal | °C | Auslegungstemperatur Kühlung |
| `humidity_min` | Decimal | % | Min. rel. Luftfeuchte |
| `humidity_max` | Decimal | % | Max. rel. Luftfeuchte |

### Akustik

| Property | Typ | Einheit | Beschreibung |
|----------|-----|---------|--------------|
| `acoustic_rating` | str | - | Schallschutzklasse |
| `reverberation_time` | Decimal | s | Nachhallzeit |

### Nutzung (Pset_SpaceOccupancyRequirements)

| Property | Typ | Beschreibung |
|----------|-----|--------------|
| `occupancy_type` | str | Nutzungsart (nach DIN 277) |
| `occupancy_number` | int | Max. Personenzahl |

### Oberflächen / Finishes

| Property | Typ | Beschreibung |
|----------|-----|--------------|
| `finish_floor` | str | Bodenbelag |
| `finish_wall` | str | Wandoberfläche |
| `finish_ceiling` | str | Deckenoberfläche |
| `finish_floor_rating` | str | Rutschfestigkeit etc. |

### Beleuchtung & Elektro

| Property | Typ | Einheit | Beschreibung |
|----------|-----|---------|--------------|
| `illuminance` | Decimal | lux | Beleuchtungsstärke |
| `electrical_load` | Decimal | kW | Elektrische Last |

---

## 🧱 Extrahierte Element-Informationen

### Gemeinsame Properties (Pset_*Common)

| Property | Typ | Beschreibung |
|----------|-----|--------------|
| `is_external` | bool | Außenbauteil |
| `is_load_bearing` | bool | Tragend |
| `fire_rating` | str | Feuerwiderstandsklasse |
| `surface_spread_of_flame` | str | Flammenausbreitung |
| `combustible` | bool | Brennbar |
| `acoustic_rating` | str | Schallschutzklasse |
| `thermal_transmittance` | Decimal | U-Wert W/(m²·K) |

### Geometrie (BaseQuantities)

| Property | Typ | Einheit | Qto-Source |
|----------|-----|---------|------------|
| `length_m` | Decimal | m | Length, NetLength |
| `width_m` | Decimal | m | Width, NetWidth |
| `height_m` | Decimal | m | Height, OverallHeight |
| `thickness_m` | Decimal | m | Thickness |
| `area_m2` | Decimal | m² | Area, NetArea |
| `gross_area_m2` | Decimal | m² | GrossSideArea, GrossArea |
| `net_area_m2` | Decimal | m² | NetSideArea, NetArea |
| `opening_area_m2` | Decimal | m² | OpeningArea |
| `volume_m3` | Decimal | m³ | NetVolume, GrossVolume |

### Türen/Fenster spezifisch

| Property | Typ | Beschreibung |
|----------|-----|--------------|
| `operation_type` | str | SINGLE_SWING_LEFT, SLIDING, etc. |
| `panel_operation` | str | Flügelart |
| `glass_layers` | int | Anzahl Glasschichten |

---

## 📦 Unterstützte IFC-Klassen

### Bauelemente

```
IfcWall, IfcWallStandardCase, IfcCurtainWall
IfcDoor, IfcWindow
IfcSlab, IfcRoof
IfcColumn, IfcBeam
IfcStair, IfcStairFlight
IfcRamp, IfcRampFlight
IfcRailing, IfcCovering
IfcPlate, IfcMember
IfcFooting, IfcPile
IfcOpeningElement
IfcFurniture, IfcFurnishingElement
```

### TGA-Elemente

```
IfcDistributionElement
IfcFlowSegment, IfcPipeSegment, IfcDuctSegment
IfcFlowFitting, IfcPipeFitting, IfcDuctFitting
IfcFlowTerminal, IfcAirTerminal
IfcSanitaryTerminal, IfcLightFixture
IfcEnergyConversionDevice
IfcFlowController, IfcFlowMovingDevice
```

### Element-Typen

```
IfcWallType, IfcDoorType, IfcWindowType
IfcSlabType, IfcColumnType, IfcBeamType
IfcCoveringType, IfcStairType, IfcRampType
IfcRailingType, IfcRoofType
IfcFurnitureType
IfcPipeSegmentType, IfcDuctSegmentType
IfcAirTerminalType, IfcSanitaryTerminalType
```

---

## 🔧 Standard PropertySets nach buildingSMART

### Räume

| PropertySet | Beschreibung |
|-------------|--------------|
| `Pset_SpaceCommon` | Allgemeine Raumeigenschaften |
| `Pset_SpaceFireSafetyRequirements` | Brandschutzanforderungen |
| `Pset_SpaceThermalRequirements` | Thermische Anforderungen |
| `Pset_SpaceOccupancyRequirements` | Belegungsanforderungen |
| `Pset_SpaceLightingRequirements` | Beleuchtungsanforderungen |
| `Qto_SpaceBaseQuantities` | Raum-Mengen |

### Wände

| PropertySet | Beschreibung |
|-------------|--------------|
| `Pset_WallCommon` | IsExternal, LoadBearing, FireRating, ThermalTransmittance |
| `Qto_WallBaseQuantities` | Length, Height, Width, GrossSideArea, NetSideArea, Volume |

### Türen

| PropertySet | Beschreibung |
|-------------|--------------|
| `Pset_DoorCommon` | FireRating, AcousticRating, IsExternal, ThermalTransmittance |
| `Pset_DoorWindowGlazingType` | GlassLayers, GlassThickness |
| `Qto_DoorBaseQuantities` | Width, Height, Area |

### Fenster

| PropertySet | Beschreibung |
|-------------|--------------|
| `Pset_WindowCommon` | FireRating, AcousticRating, ThermalTransmittance |
| `Pset_WindowGlazingProperties` | GlassLayers, SolarTransmittance |
| `Qto_WindowBaseQuantities` | Width, Height, Area |

### Decken/Böden

| PropertySet | Beschreibung |
|-------------|--------------|
| `Pset_SlabCommon` | FireRating, LoadBearing, AcousticRating |
| `Qto_SlabBaseQuantities` | Width, Length, Depth, GrossArea, NetArea, Volume |

---

## 📊 JSON Export Struktur

```json
{
  "project": {
    "name": "Projektname",
    "schema_version": "IFC4",
    "description": "..."
  },
  "file_info": {
    "path": "/path/to/model.ifc",
    "hash": "md5...",
    "size_bytes": 12345678
  },
  "authoring": {
    "application": "Revit 2024",
    "author": "Max Mustermann",
    "organization": "Firma GmbH"
  },
  "spatial_structure": {
    "sites": [...],
    "buildings": [...],
    "storeys": [...],
    "spaces": [
      {
        "global_id": "2O2Fr$...",
        "name": "Büro 101",
        "geometry": {
          "net_floor_area_m2": 25.5,
          "net_volume_m3": 63.75,
          "net_height_m": 2.5
        },
        "fire_protection": {
          "fire_rating": "F30",
          "fire_compartment": "BA-01",
          "sprinkler_protected": true
        },
        "thermal": {
          "design_heating_load_w": 1500,
          "design_temperature_heating_c": 20
        },
        "properties": [...],
        "quantities": [...]
      }
    ]
  },
  "elements": [...],
  "element_types": [...],
  "statistics": {
    "total_elements": 5432,
    "total_spaces": 87,
    "element_counts": {
      "IfcWall": 234,
      "IfcDoor": 156,
      ...
    }
  }
}
```

---

## 🔌 Django Integration

```python
# views.py
from ifc_complete_parser import IfcCompleteParser

def parse_ifc_upload(request):
    ifc_file = request.FILES['ifc_file']
    
    # Temporär speichern
    with tempfile.NamedTemporaryFile(suffix='.ifc', delete=False) as tmp:
        for chunk in ifc_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    
    try:
        parser = IfcCompleteParser(tmp_path)
        project = parser.parse()
        
        # In Datenbank speichern
        for space in project.spaces:
            Room.objects.create(
                name=space.name,
                number=space.space_number,
                area=space.net_floor_area,
                fire_rating=space.fire_rating,
                # ...
            )
        
        return JsonResponse(project.to_dict())
    finally:
        os.unlink(tmp_path)
```

---

## 📈 Performance

| Modellgröße | Elemente | Parse-Zeit |
|-------------|----------|------------|
| Klein | < 1.000 | < 1s |
| Mittel | 1.000 - 10.000 | 2-5s |
| Groß | 10.000 - 50.000 | 10-30s |
| Sehr groß | > 50.000 | 30-120s |

---

## 🚀 Erweiterungen

### Custom PropertySets hinzufügen

```python
# Nach dem Parsen zusätzliche Properties extrahieren
for space in project.spaces:
    for prop in space.properties:
        if prop.pset_name == "Pset_MeineFirma_Brandschutz":
            if prop.name == "ExZone":
                space.ex_zone = prop.value
```

### Geometrie aus Shape berechnen

```python
import ifcopenshell.geom

settings = ifcopenshell.geom.settings()
settings.set(settings.USE_WORLD_COORDS, True)

for wall in ifc.by_type("IfcWall"):
    shape = ifcopenshell.geom.create_shape(settings, wall)
    # shape.geometry enthält Vertices, Faces, etc.
```

---

## 📚 Referenzen

- [IFC Specification](https://technical.buildingsmart.org/standards/ifc/)
- [IfcOpenShell Docs](https://docs.ifcopenshell.org/)
- [buildingSMART Property Sets](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/annex/annex-b/alphabeticalorder_psets.htm)
