#!/usr/bin/env python
"""Quick test for Expert Hub Agent tools."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from apps.expert_hub.agents.tools import (
    get_substance_properties,
    calculate_zone_extent,
    check_equipment_suitability,
    analyze_ventilation_effectiveness,
)

def main():
    print("=== Expert Hub Agent Tools Test ===\n")
    
    # Test 1: Stoffdaten
    print("1. Stoffdaten-Test (Aceton)")
    result = get_substance_properties("Aceton")
    assert result["success"], "Aceton sollte gefunden werden"
    assert result["substance"]["lower_explosion_limit"] == 2.5
    print(f"   ✓ UEG: {result['substance']['lower_explosion_limit']}%")
    print(f"   ✓ OEG: {result['substance']['upper_explosion_limit']}%")
    print(f"   ✓ T-Klasse: {result['substance']['temperature_class']}")
    
    # Test 2: Zonenberechnung
    print("\n2. Zonenberechnung-Test")
    result = calculate_zone_extent(
        release_rate_kg_s=0.001,
        ventilation_rate_m3_s=1.0,
        lel_percent=2.5
    )
    assert result["success"], "Berechnung sollte erfolgreich sein"
    print(f"   ✓ Zone: {result['zone_type']}")
    print(f"   ✓ Radius: {result['zone_radius_m']}m")
    print(f"   ✓ Verdünnung: {result['dilution_factor']}")
    
    # Test 3: Equipment-Prüfung
    print("\n3. Equipment-Prüfung-Test")
    result = check_equipment_suitability(
        ex_marking="II 2G Ex d IIB T4",
        zone="Zone 1"
    )
    assert result["success"], "Prüfung sollte erfolgreich sein"
    assert result["is_suitable"], "2G sollte für Zone 1 geeignet sein"
    print(f"   ✓ Geeignet: {result['is_suitable']}")
    print(f"   ✓ Kategorie: {result['detected']['category']}")
    
    # Test 4: Lüftungsanalyse
    print("\n4. Lüftungsanalyse-Test")
    result = analyze_ventilation_effectiveness(
        room_volume_m3=100,
        air_flow_m3_h=1500,
        ventilation_type="technisch"
    )
    assert result["success"], "Analyse sollte erfolgreich sein"
    print(f"   ✓ Luftwechsel: {result['air_changes_per_hour']}/h")
    print(f"   ✓ Effektivität: {result['effectiveness']}")
    
    print("\n" + "="*40)
    print("✅ ALLE TESTS BESTANDEN!")
    print("="*40)

if __name__ == "__main__":
    main()
