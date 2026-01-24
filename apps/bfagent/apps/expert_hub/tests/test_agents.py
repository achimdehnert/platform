"""
Tests für Expert Hub Agents - Explosionsschutz Tools

Fokus auf sicherheitsrelevante Berechnungen!
"""

import pytest
from apps.expert_hub.agents.tools import (
    get_substance_properties,
    calculate_zone_extent,
    check_equipment_suitability,
    analyze_ventilation_effectiveness,
)


class TestSubstanceDatabase:
    """Tests für Stoffdatenbank."""
    
    def test_known_substance_aceton(self):
        """Aceton sollte korrekte Daten liefern."""
        result = get_substance_properties("Aceton")
        
        assert result["success"] is True
        assert result["substance"]["name"] == "Aceton"
        assert result["substance"]["lower_explosion_limit"] == 2.5
        assert result["substance"]["upper_explosion_limit"] == 13.0
        assert result["substance"]["temperature_class"] == "T1"
        assert result["substance"]["explosion_group"] == "IIA"
    
    def test_substance_alias(self):
        """Englische Aliase sollten funktionieren."""
        result = get_substance_properties("acetone")
        assert result["success"] is True
        assert result["substance"]["name"] == "Aceton"
    
    def test_unknown_substance(self):
        """Unbekannte Stoffe sollten Fehlermeldung liefern."""
        result = get_substance_properties("Kryptonit")
        assert result["success"] is False
        assert "error" in result
    
    def test_hydrogen_iic(self):
        """Wasserstoff muss IIC sein (höchste Gefährlichkeit)."""
        result = get_substance_properties("Wasserstoff")
        
        assert result["success"] is True
        assert result["substance"]["explosion_group"] == "IIC"
        assert result["substance"]["lower_explosion_limit"] == 4.0


class TestZoneCalculation:
    """Tests für Zonenberechnung nach TRGS 721."""
    
    def test_good_ventilation_zone_2(self):
        """Gute Lüftung sollte Zone 2 ergeben."""
        result = calculate_zone_extent(
            release_rate_kg_s=0.001,
            ventilation_rate_m3_s=1.0,
            lel_percent=2.5
        )
        
        assert result["success"] is True
        assert result["zone_type"] == "Zone 2"
        assert result["dilution_factor"] > 100
    
    def test_poor_ventilation_zone_0(self):
        """Schlechte Lüftung sollte Zone 0 ergeben."""
        result = calculate_zone_extent(
            release_rate_kg_s=0.1,
            ventilation_rate_m3_s=0.01,
            lel_percent=2.5
        )
        
        assert result["success"] is True
        assert result["zone_type"] == "Zone 0"
    
    def test_no_ventilation(self):
        """Keine Lüftung = Zone 0."""
        result = calculate_zone_extent(
            release_rate_kg_s=0.001,
            ventilation_rate_m3_s=0,
            lel_percent=2.5
        )
        
        assert result["zone_type"] == "Zone 0"
        assert "unbegrenzt" in str(result["zone_radius_m"])
    
    def test_with_substance_name(self):
        """LEL sollte automatisch aus Stoffdaten geholt werden."""
        result = calculate_zone_extent(
            release_rate_kg_s=0.001,
            ventilation_rate_m3_s=0.5,
            substance_name="Aceton"
        )
        
        assert result["success"] is True
        assert result["input_parameters"]["lel_percent"] == 2.5  # Aceton LEL
    
    def test_calculation_basis_documented(self):
        """Berechnungsgrundlage muss dokumentiert sein."""
        result = calculate_zone_extent(
            release_rate_kg_s=0.001,
            ventilation_rate_m3_s=0.5
        )
        
        assert "TRGS 721" in result["calculation_basis"]


class TestEquipmentCheck:
    """Tests für Equipment-Eignungsprüfung."""
    
    def test_category_2g_in_zone_1(self):
        """Kategorie 2G ist für Zone 1 geeignet."""
        result = check_equipment_suitability(
            ex_marking="II 2G Ex d IIB T4",
            zone="Zone 1"
        )
        
        assert result["success"] is True
        assert result["is_suitable"] is True
        assert result["detected"]["category"] == "2G"
    
    def test_category_3g_not_in_zone_1(self):
        """Kategorie 3G ist für Zone 1 NICHT geeignet."""
        result = check_equipment_suitability(
            ex_marking="II 3G Ex nA IIA T3",
            zone="Zone 1"
        )
        
        assert result["success"] is True
        assert result["is_suitable"] is False
        assert len(result["issues"]) > 0
    
    def test_category_1g_everywhere(self):
        """Kategorie 1G ist überall geeignet (Gas)."""
        for zone in ["Zone 0", "Zone 1", "Zone 2"]:
            result = check_equipment_suitability(
                ex_marking="II 1G Ex ia IIC T6",
                zone=zone
            )
            assert result["is_suitable"] is True, f"1G sollte für {zone} geeignet sein"
    
    def test_dust_zones(self):
        """Staub-Zonen (D) prüfen."""
        result = check_equipment_suitability(
            ex_marking="II 2D Ex tb IIIC T80",
            zone="Zone 21"
        )
        
        assert result["success"] is True
        assert result["detected"]["category"] == "2D"
    
    def test_invalid_zone(self):
        """Ungültige Zone sollte Fehler liefern."""
        result = check_equipment_suitability(
            ex_marking="II 2G Ex d IIB T4",
            zone="Zone 99"
        )
        
        assert result["success"] is False
        assert "valid_zones" in result


class TestVentilationAnalysis:
    """Tests für Lüftungsanalyse."""
    
    def test_high_air_changes(self):
        """12+ Luftwechsel = hohe Effektivität."""
        result = analyze_ventilation_effectiveness(
            room_volume_m3=100,
            air_flow_m3_h=1500,  # 15 LW/h
            ventilation_type="technisch"
        )
        
        assert result["effectiveness"] == "hoch"
        assert result["can_reduce_zone"] is True
    
    def test_low_air_changes(self):
        """<6 Luftwechsel = geringe Effektivität."""
        result = analyze_ventilation_effectiveness(
            room_volume_m3=100,
            air_flow_m3_h=300,  # 3 LW/h
            ventilation_type="technisch"
        )
        
        assert result["effectiveness"] == "gering"
        assert result["can_reduce_zone"] is False
    
    def test_natural_ventilation(self):
        """Natürliche Lüftung = keine Zonenreduzierung."""
        result = analyze_ventilation_effectiveness(
            room_volume_m3=100,
            air_flow_m3_h=1500,
            ventilation_type="natürlich"
        )
        
        assert result["can_reduce_zone"] is False
        assert "Keine Anrechnung" in result["recommendation"]


# Pytest marker für Django-Tests
pytestmark = pytest.mark.django_db(transaction=True)
