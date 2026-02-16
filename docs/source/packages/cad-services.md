# cad-services

Shared Python package for CAD file processing (IFC, DXF) with domain services
for fire safety analysis, escape route calculation, and 3D model conversion.

**Package**: `platform/packages/cad-services`
**Version**: 0.1.0
**Python**: ≥ 3.11

## Installation

```bash
pip install -e ".[ifc,dxf,viewer]"
```

### Optional Dependencies

| Extra      | Packages                        | Purpose                          |
|------------|---------------------------------|----------------------------------|
| `ifc`      | `ifcopenshell`                  | IFC file parsing                 |
| `dxf`      | `ezdxf`                        | DXF file parsing                 |
| `viewer`   | `networkx`                     | Escape route graph algorithms    |
| `postgres` | `psycopg[binary]`              | PostgreSQL writer                |

## Architecture

```text
cad_services/
├── models.py              # CADElement, CADParseResult, enums
├── parsers/
│   ├── ifc_parser.py      # IFC → CADElement[]
│   └── dxf_parser.py      # DXF → CADElement[]
├── services/
│   ├── ifc_service.py           # IFC domain extraction (floors, rooms, walls, ...)
│   ├── dxf_service.py           # DXF domain extraction (layers, rooms, blocks)
│   ├── fire_safety_service.py   # DIN 4102 / EN 13501 compliance
│   ├── escape_route_service.py  # Graph-based escape route calculation
│   ├── floorplan_svg_service.py # 2D SVG floor plan rendering
│   ├── xgf_converter_service.py # IFC/glTF → XGF (xeokit v3+)
│   └── xkt_converter_service.py # IFC → XKT (legacy xeokit)
├── writer/
│   ├── base.py            # WriteResult dataclass
│   └── postgres.py        # PostgreSQL bulk writer
└── handlers.py            # Orchestration pipeline
```

## Services

### IFCService

Extracts building elements from IFC files using `ifcopenshell`:

- **Floors** (`IfcBuildingStorey`) — elevation, height
- **Rooms** (`IfcSpace`) — area, perimeter, usage type
- **Walls** (`IfcWall`) — length, height, thickness, load-bearing, external
- **Doors** (`IfcDoor`) — width, height, fire rating
- **Windows** (`IfcWindow`) — width, height
- **Slabs** (`IfcSlab`) — area, thickness

### DXFService

Extracts entities from DXF files using `ezdxf`:

- **Layers** — name, color, line type
- **Rooms** — closed polylines with area/perimeter calculation
- **Blocks** — block references with attributes
- **Text labels** — assigned to nearest room by proximity

### FireSafetyService

Analyzes fire safety compliance (DIN 4102 / EN 13501):

- Extracts fire ratings from IFC property sets
- Normalizes rating formats (F30, REI60, T30, etc.)
- Checks element compliance against required ratings
- Configurable for building type and sprinkler systems

### EscapeRouteService

Calculates escape routes using `networkx` graph algorithms:

- Builds room connectivity graph from rooms, doors, exits
- Shortest-path calculation to nearest exit
- Compliance check: max distance, min door/corridor width
- Configurable per building type (standard, high-rise, assembly)

### FloorplanSVGService

Generates 2D SVG floor plans with configurable rendering:

- Room polygons with area labels
- Door/window markers
- Fire-rated wall highlighting
- Color-coded usage categories
- Legend generation

### XGF/XKT Converter Services

Convert IFC models for web-based 3D viewing:

- **XGFConverterService** — IFC/glTF → XGF via `xeoconvert` CLI (xeokit v3+)
- **XKTConverterService** — IFC → XKT via `xeokit-convert` CLI (legacy)
- Strategy recommendations based on file size

## Recent Fixes (2026-02-16)

- **C-1**: `fire_safety_service.py` — lazy import for optional `ifcopenshell` dep
  (was crashing all imports when not installed)
- **C-2**: `xkt_converter_service.py` — fixed `xkt_path=` → `output_path=` in
  `ConversionResult` constructor (would TypeError at runtime)
- **M-1**: `test_escape_route_service.py` — skip guard for optional `networkx` dep

## Tests

```bash
# Run all tests (67 passed, 9 skipped without optional deps)
pytest tests/ -v
```
