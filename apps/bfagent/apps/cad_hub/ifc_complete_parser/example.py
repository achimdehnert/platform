#!/usr/bin/env python3
"""
Beispiel: IFC Complete Parser

Zeigt wie man alle Informationen aus einer IFC-Datei extrahiert.
"""

from pathlib import Path

from ifc_complete_parser import IfcCompleteParser, ParsedProject


def main():
    # === 1. IFC Datei parsen ===
    ifc_path = Path("model.ifc")  # Pfad zur IFC-Datei anpassen

    parser = IfcCompleteParser(ifc_path)
    project: ParsedProject = parser.parse()

    # === 2. Projekt-Informationen ===
    print("=" * 60)
    print(f"PROJEKT: {project.name}")
    print(f"Schema: {project.schema_version.value}")
    print(f"Authoring: {project.authoring_app}")
    print(f"Datei: {project.file_path}")
    print("=" * 60)

    # === 3. Räumliche Struktur ===
    print(f"\n📍 Sites: {len(project.sites)}")
    for site in project.sites:
        print(f"   - {site.name}")
        if site.latitude and site.longitude:
            print(f"     Koordinaten: {site.latitude:.6f}, {site.longitude:.6f}")

    print(f"\n🏢 Gebäude: {len(project.buildings)}")
    for building in project.buildings:
        print(f"   - {building.name}")

    print(f"\n🏗️ Geschosse: {len(project.storeys)}")
    for storey in project.storeys:
        print(f"   - {storey.name} (Elevation: {storey.elevation}m)")

    # === 4. Räume mit Details ===
    print(f"\n🚪 Räume: {len(project.spaces)}")
    print("-" * 60)

    for space in project.spaces:
        print(f"\n📦 {space.space_number or space.name} - {space.long_name or ''}")

        # Geometrie
        if space.net_floor_area:
            print(f"   Fläche: {float(space.net_floor_area):.2f} m²")
        if space.net_volume:
            print(f"   Volumen: {float(space.net_volume):.2f} m³")
        if space.net_height:
            print(f"   Höhe: {float(space.net_height):.2f} m")

        # Brandschutz
        if space.fire_rating or space.fire_compartment:
            print(f"   🔥 Brandschutz:")
            if space.fire_rating:
                print(f"      - Feuerwiderstand: {space.fire_rating}")
            if space.fire_compartment:
                print(f"      - Brandabschnitt: {space.fire_compartment}")
            if space.sprinkler_protected:
                print(f"      - Sprinkler: Ja")

        # Ex-Zone
        if space.ex_zone:
            print(f"   ⚡ Ex-Zone: {space.ex_zone}")

        # Akustik
        if space.acoustic_rating:
            print(f"   🔊 Akustik: {space.acoustic_rating}")

        # Thermik
        if space.design_temperature_heating or space.design_temperature_cooling:
            print(f"   🌡️ Thermik:")
            if space.design_temperature_heating:
                print(f"      - Heizung: {float(space.design_temperature_heating):.1f}°C")
            if space.design_temperature_cooling:
                print(f"      - Kühlung: {float(space.design_temperature_cooling):.1f}°C")

        # Oberflächen
        if space.finish_floor or space.finish_wall or space.finish_ceiling:
            print(f"   🎨 Oberflächen:")
            if space.finish_floor:
                print(f"      - Boden: {space.finish_floor}")
            if space.finish_wall:
                print(f"      - Wand: {space.finish_wall}")
            if space.finish_ceiling:
                print(f"      - Decke: {space.finish_ceiling}")

        # Alle Properties anzeigen
        if space.properties:
            print(f"   📋 Properties ({len(space.properties)}):")
            for prop in space.properties[:5]:  # Max 5 anzeigen
                print(f"      - {prop.pset_name}.{prop.name} = {prop.value}")
            if len(space.properties) > 5:
                print(f"      ... und {len(space.properties) - 5} weitere")

    # === 5. Element-Statistiken ===
    print("\n" + "=" * 60)
    print("ELEMENT-STATISTIKEN")
    print("=" * 60)

    for ifc_class, count in sorted(project.element_counts.items(), key=lambda x: -x[1]):
        print(f"   {ifc_class}: {count}")

    # === 6. Wände mit Brandschutz ===
    print("\n" + "-" * 60)
    print("WÄNDE MIT BRANDSCHUTZ")
    print("-" * 60)

    walls_with_fire = [
        e
        for e in project.elements
        if e.ifc_class in ("IfcWall", "IfcWallStandardCase") and e.fire_rating
    ]

    for wall in walls_with_fire[:10]:
        print(f"   {wall.name or wall.global_id[:8]}")
        print(f"      - Brandschutz: {wall.fire_rating}")
        print(f"      - Außen: {wall.is_external}")
        print(f"      - Tragend: {wall.is_load_bearing}")
        if wall.thermal_transmittance:
            print(f"      - U-Wert: {float(wall.thermal_transmittance):.3f} W/(m²·K)")

    # === 7. Materialien ===
    print("\n" + "-" * 60)
    print(f"VERWENDETE MATERIALIEN ({len(project.all_materials)})")
    print("-" * 60)

    for mat in sorted(project.all_materials):
        print(f"   - {mat}")

    # === 8. Export ===
    output_path = Path("ifc_export.json")
    project.save_json(output_path)
    print(f"\n✅ JSON exportiert nach: {output_path}")

    # Statistik
    print(f"\n📊 Zusammenfassung:")
    print(f"   - {len(project.spaces)} Räume")
    print(f"   - {len(project.elements)} Bauelemente")
    print(f"   - {len(project.element_types)} Element-Typen")
    print(f"   - {len(project.all_materials)} Materialien")


def extract_fire_protection_report(project: ParsedProject) -> str:
    """Erstellt einen Brandschutz-Bericht."""
    lines = ["# Brandschutz-Bericht", ""]

    # Räume nach Brandabschnitt gruppieren
    compartments = {}
    for space in project.spaces:
        compartment = space.fire_compartment or "Nicht zugeordnet"
        if compartment not in compartments:
            compartments[compartment] = []
        compartments[compartment].append(space)

    for compartment, spaces in compartments.items():
        lines.append(f"## Brandabschnitt: {compartment}")
        lines.append("")

        total_area = sum(float(s.net_floor_area or 0) for s in spaces)
        lines.append(f"**Gesamtfläche:** {total_area:.2f} m²")
        lines.append("")

        lines.append("| Raum | Fläche | Feuerwiderstand | Sprinkler |")
        lines.append("|------|--------|-----------------|-----------|")

        for space in spaces:
            area = f"{float(space.net_floor_area):.2f} m²" if space.net_floor_area else "-"
            fire = space.fire_rating or "-"
            sprinkler = "✅" if space.sprinkler_protected else "❌"
            lines.append(f"| {space.name or space.space_number} | {area} | {fire} | {sprinkler} |")

        lines.append("")

    return "\n".join(lines)


def extract_thermal_requirements(project: ParsedProject) -> dict:
    """Extrahiert thermische Anforderungen für TGA-Planung."""
    requirements = {
        "spaces_with_heating": [],
        "spaces_with_cooling": [],
        "total_heating_load_w": 0,
        "total_cooling_load_w": 0,
    }

    for space in project.spaces:
        if space.design_heating_load:
            requirements["spaces_with_heating"].append(
                {
                    "name": space.name,
                    "area_m2": float(space.net_floor_area) if space.net_floor_area else 0,
                    "heating_load_w": float(space.design_heating_load),
                    "design_temp_c": (
                        float(space.design_temperature_heating)
                        if space.design_temperature_heating
                        else None
                    ),
                }
            )
            requirements["total_heating_load_w"] += float(space.design_heating_load)

        if space.design_cooling_load:
            requirements["spaces_with_cooling"].append(
                {
                    "name": space.name,
                    "area_m2": float(space.net_floor_area) if space.net_floor_area else 0,
                    "cooling_load_w": float(space.design_cooling_load),
                    "design_temp_c": (
                        float(space.design_temperature_cooling)
                        if space.design_temperature_cooling
                        else None
                    ),
                }
            )
            requirements["total_cooling_load_w"] += float(space.design_cooling_load)

    return requirements


if __name__ == "__main__":
    main()
