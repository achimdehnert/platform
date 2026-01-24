# gui/components/template_agent_brandschutz_extension.py
"""
Erweiterung des Template Agents für Brandschutz- und Explosionsschutz-Dokumente
Version: 0.1.0
"""

from typing import Dict, List, Tuple
import re
from gui.components.template_agent import TemplateAgent, FieldType, FieldSuggestion, ConfidenceLevel

class BrandschutzTemplateAgent(TemplateAgent):
    """Erweiterte Template Agent Klasse für Brandschutz-spezifische Dokumente"""
    
    def __init__(self):
        super().__init__()
        self._add_brandschutz_patterns()
        self._add_explosionsschutz_patterns()
        self._add_compliance_patterns()
    
    def _add_brandschutz_patterns(self):
        """Fügt Brandschutz-spezifische Pattern hinzu"""
        
        # Erweitere bestehende Patterns
        self.field_patterns["text_input"].extend([
            # Anlagen-Identifikation
            r"(?:anlagen?(?:bezeichnung|name|typ|art))\s*:?\s*",
            r"(?:betreiber|eigentümer|verantwortlich)\s*:?\s*",
            r"(?:standort|gebäude|halle|bereich)\s*:?\s*",
            
            # Stoffbezeichnungen
            r"(?:stoff|substanz|chemikalie|produkt)(?:bezeichnung|name)\s*:?\s*",
            r"(?:cas[\-\s]?nummer|cas[\-\s]?nr\.?)\s*:?\s*",
            r"(?:eg[\-\s]?nummer|einecs)\s*:?\s*",
            
            # Referenzen
            r"(?:aktenzeichen|projektnummer|auftragsnummer)\s*:?\s*",
            r"(?:gutachten[\-\s]?nr\.?|bericht[\-\s]?nr\.?)\s*:?\s*",
        ])
        
        self.field_patterns["text_area"].extend([
            # Beschreibungen
            r"(?:verfahrensbeschreibung|prozessbeschreibung)\s*:?\s*",
            r"(?:gefährdungsbeurteilung|risikoanalyse)\s*:?\s*",
            r"(?:schutzkonzept|sicherheitskonzept)\s*:?\s*",
            
            # Maßnahmen
            r"(?:schutzmaßnahmen?|sicherheitsmaßnahmen?)\s*:?\s*",
            r"(?:technische\s+maßnahmen?|bauliche\s+maßnahmen?)\s*:?\s*",
            r"(?:organisatorische\s+maßnahmen?)\s*:?\s*",
            r"(?:persönliche\s+schutz(?:maßnahmen?|ausrüstung))\s*:?\s*",
        ])
        
        self.field_patterns["selectbox"].extend([
            # Klassifizierungen
            r"(?:gefahr|gefahren)(?:klasse|kategorie)\s*:?\s*",
            r"(?:brandklasse|feuerwiderstandsklasse)\s*:?\s*",
            r"(?:lagerklasse|wassergefährdungsklasse|wgk)\s*:?\s*",
            
            # Schutzgrade
            r"(?:schutzart|schutzgrad|ip[\-\s]?schutz)\s*:?\s*",
            r"(?:temperaturklasse|t[\-\s]?klasse)\s*:?\s*",
        ])
        
        self.field_patterns["number_input"].extend([
            # Physikalische Eigenschaften
            r"(?:flammpunkt|flash[\-\s]?point)\s*:?\s*",
            r"(?:zündtemperatur|zündpunkt)\s*:?\s*",
            r"(?:explosionsgrenze|eg|ueg|oeg)\s*:?\s*",
            r"(?:dampfdruck|vapor[\-\s]?pressure)\s*:?\s*",
            
            # Mengen
            r"(?:lagermenge|vorratsmenge|bestandsmenge)\s*:?\s*",
            r"(?:jahresverbrauch|monatsverbrauch)\s*:?\s*",
            r"(?:füllmenge|nennvolumen|fassungsvermögen)\s*:?\s*",
        ])
        
        self.field_patterns["checkbox"].extend([
            # Ja/Nein Eigenschaften
            r"(?:brennbar|entzündlich|explosiv)\s*:?\s*",
            r"(?:giftig|ätzend|reizend)\s*:?\s*",
            r"(?:vorhanden|erforderlich|notwendig)\s*:?\s*",
            r"(?:geprüft|zertifiziert|zugelassen)\s*:?\s*",
        ])
        
        self.field_patterns["date_input"].extend([
            # Termine und Fristen
            r"(?:prüfdatum|prüftermin|letzte\s+prüfung)\s*:?\s*",
            r"(?:gültig(?:keit)?(?:\s+bis)?|ablaufdatum)\s*:?\s*",
            r"(?:nächste\s+prüfung|wiederholung(?:sprüfung)?)\s*:?\s*",
            r"(?:erstellungsdatum|ausgabedatum|stand)\s*:?\s*",
        ])
    
    def _add_explosionsschutz_patterns(self):
        """Fügt Explosionsschutz-spezifische Pattern hinzu"""
        
        # Neue Pattern-Kategorie für Ex-Zonen
        if "ex_zone" not in self.field_patterns:
            self.field_patterns["ex_zone"] = []
        
        self.field_patterns["ex_zone"].extend([
            r"(?:ex[\-\s]?zone|atex[\-\s]?zone)\s*:?\s*",
            r"(?:zone\s+[0-2]|zone\s+2[0-2])\s*",
            r"(?:explosionsgefährdete[r]?\s+bereich)\s*:?\s*",
            r"(?:bereich\s+der\s+zone)\s*:?\s*",
        ])
        
        # Neue Pattern-Kategorie für Zündschutzarten
        if "zuendschutzart" not in self.field_patterns:
            self.field_patterns["zuendschutzart"] = []
        
        self.field_patterns["zuendschutzart"].extend([
            r"(?:zündschutzart|schutzart|ex[\-\s]?schutz)\s*:?\s*",
            r"(?:ex\s*[deimnopqrs])\s+",
            r"(?:eigensicher|druckfest|erhöhte\s+sicherheit)\s*:?\s*",
        ])
        
        # Neue Pattern-Kategorie für Gerätegruppen
        if "geraetegruppe" not in self.field_patterns:
            self.field_patterns["geraetegruppe"] = []
        
        self.field_patterns["geraetegruppe"].extend([
            r"(?:gerätegruppe|equipment\s+group)\s*:?\s*",
            r"(?:gruppe\s+i{1,2}[abc]?)\s+",
            r"(?:gasgruppe|staubgruppe)\s*:?\s*",
        ])
    
    def _add_compliance_patterns(self):
        """Fügt Pattern für rechtliche/normative Referenzen hinzu"""
        
        # Neue Pattern-Kategorie für Vorschriften
        if "regulation_reference" not in self.field_patterns:
            self.field_patterns["regulation_reference"] = []
        
        self.field_patterns["regulation_reference"].extend([
            r"(?:betrsichv|betriebssicherheitsverordnung)\s*",
            r"(?:gefstoffv|gefahrstoffverordnung)\s*",
            r"(?:trgs|technische\s+regel\s+gefahrstoffe)\s*\d+\s*",
            r"(?:trbs|technische\s+regel\s+betriebssicherheit)\s*\d+\s*",
            r"(?:din\s*en?\s*\d+|iso\s*\d+|vde\s*\d+)\s*",
            r"(?:atex|richtlinie\s*\d+/\d+/e[gu])\s*",
        ])
        
        # Neue Pattern-Kategorie für Schutzkonzepte
        if "schutzkonzept_typ" not in self.field_patterns:
            self.field_patterns["schutzkonzept_typ"] = []
        
        self.field_patterns["schutzkonzept_typ"].extend([
            r"(?:primärer?\s+explosionsschutz)\s*:?\s*",
            r"(?:sekundärer?\s+explosionsschutz)\s*:?\s*",
            r"(?:tertiärer?\s+explosionsschutz|konstruktiver?\s+explosionsschutz)\s*:?\s*",
            r"(?:top[\-\s]?prinzip|stop[\-\s]?prinzip)\s*:?\s*",
        ])
    
    def _analyze_document(self, text: str) -> List[FieldSuggestion]:
        """Überschriebene Methode mit erweiterten Brandschutz-Features"""
        
        # Basis-Analyse durchführen
        fields = super()._analyze_document(text)
        
        # Brandschutz-spezifische Analyse hinzufügen
        brandschutz_fields = self._analyze_brandschutz_specific(text)
        fields.extend(brandschutz_fields)
        
        # Duplikate entfernen und sortieren
        unique_fields = self._remove_duplicates_smart(fields)
        
        # Priorisierung für Brandschutz-Felder
        prioritized_fields = self._prioritize_brandschutz_fields(unique_fields)
        
        return prioritized_fields[:15]  # Maximal 15 Felder für Übersichtlichkeit
    
    def _analyze_brandschutz_specific(self, text: str) -> List[FieldSuggestion]:
        """Spezielle Analyse für Brandschutz-Dokumente"""
        additional_fields = []
        
        # Ex-Zonen Erkennung
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in self.field_patterns.get("ex_zone", [])):
            additional_fields.append(FieldSuggestion(
                name="ex_zone_classification",
                label="Ex-Zonen Klassifizierung",
                field_type=FieldType.SELECTBOX,
                confidence=ConfidenceLevel.HIGH,
                description="Klassifizierung der explosionsgefährdeten Bereiche",
                options=["Zone 0", "Zone 1", "Zone 2", "Zone 20", "Zone 21", "Zone 22", "Keine"],
                is_array=True  # Mehrere Zonen möglich
            ))
        
        # Stoffdaten-Array für mehrere gefährliche Stoffe
        if re.search(r"(?:stoff|chemikalie|produkt)", text, re.IGNORECASE):
            additional_fields.append(FieldSuggestion(
                name="hazardous_substances",
                label="Gefährliche Stoffe",
                field_type=FieldType.ARRAY_GROUP,
                confidence=ConfidenceLevel.HIGH,
                description="Liste der verwendeten gefährlichen Stoffe",
                options=None,
                is_array=True
            ))
        
        # Schutzmaßnahmen-Checkliste
        if re.search(r"(?:schutzmaßnahme|sicherheitsmaßnahme)", text, re.IGNORECASE):
            additional_fields.append(FieldSuggestion(
                name="protection_measures",
                label="Implementierte Schutzmaßnahmen",
                field_type=FieldType.ARRAY_GROUP,
                confidence=ConfidenceLevel.HIGH,
                description="Liste der technischen, organisatorischen und persönlichen Schutzmaßnahmen",
                options=None,
                is_array=True
            ))
        
        # Prüfintervalle
        if re.search(r"(?:prüf|kontroll)(?:frist|intervall|turnus)", text, re.IGNORECASE):
            additional_fields.append(FieldSuggestion(
                name="inspection_interval",
                label="Prüfintervall",
                field_type=FieldType.SELECTBOX,
                confidence=ConfidenceLevel.MEDIUM,
                description="Wiederkehrende Prüffristen",
                options=["Täglich", "Wöchentlich", "Monatlich", "Vierteljährlich", 
                        "Halbjährlich", "Jährlich", "Alle 2 Jahre", "Alle 3 Jahre"],
                is_array=False
            ))
        
        return additional_fields
    
    def _remove_duplicates_smart(self, fields: List[FieldSuggestion]) -> List[FieldSuggestion]:
        """Intelligente Duplikaterkennung mit Brandschutz-Kontext"""
        unique_fields = []
        seen_concepts = set()
        
        # Ähnliche Konzepte gruppieren
        concept_groups = {
            "anlage": ["anlage", "betrieb", "standort", "gebäude"],
            "stoff": ["stoff", "substanz", "chemikalie", "produkt"],
            "gefahr": ["gefahr", "risiko", "gefährdung"],
            "schutz": ["schutz", "sicherheit", "maßnahme"],
        }
        
        for field in fields:
            # Konzept aus Feldnamen extrahieren
            field_concept = None
            for concept, keywords in concept_groups.items():
                if any(keyword in field.name.lower() for keyword in keywords):
                    field_concept = concept
                    break
            
            # Wenn kein ähnliches Konzept vorhanden, hinzufügen
            if field_concept is None or field_concept not in seen_concepts:
                unique_fields.append(field)
                if field_concept:
                    seen_concepts.add(field_concept)
        
        return unique_fields
    
    def _prioritize_brandschutz_fields(self, fields: List[FieldSuggestion]) -> List[FieldSuggestion]:
        """Priorisiert Felder nach Brandschutz-Relevanz"""
        
        # Prioritäts-Mapping
        priority_keywords = {
            1: ["ex_zone", "gefährdung", "schutzkonzept", "maßnahme"],
            2: ["stoff", "flammpunkt", "explosionsgrenze", "menge"],
            3: ["anlage", "betreiber", "standort", "verfahren"],
            4: ["prüfung", "datum", "frist", "intervall"],
            5: ["sonstige", "bemerkung", "kommentar"]
        }
        
        def get_priority(field: FieldSuggestion) -> int:
            for priority, keywords in priority_keywords.items():
                if any(keyword in field.name.lower() for keyword in keywords):
                    return priority
            return 6  # Niedrigste Priorität für nicht erkannte Felder
        
        # Sortieren nach Priorität und Konfidenz
        return sorted(fields, key=lambda f: (get_priority(f), -f.confidence.value))


# Beispiel-Verwendung und Test
if __name__ == "__main__":
    # Test mit Beispieltext
    test_text = """
    BRANDSCHUTZGUTACHTEN
    
    Anlagenbezeichnung: Lackieranlage Halle 3
    Betreiber: Mustermann GmbH
    Standort: Industriestraße 42, 12345 Musterstadt
    
    Gefährdungsbeurteilung:
    In der Anlage werden lösemittelhaltige Lacke mit einem Flammpunkt von 23°C verwendet.
    Die maximale Lagermenge beträgt 500 Liter.
    
    Ex-Zone: Zone 1 im Bereich der Spritzstände
    Zone 2 im Lagerbereich
    
    Schutzmaßnahmen:
    - Technische Lüftung mit 10-fachem Luftwechsel
    - Ex-geschützte Beleuchtung der Schutzart Ex e
    - Erdung aller leitfähigen Teile
    
    Prüffrist: Jährliche Überprüfung erforderlich
    Letzte Prüfung: 15.03.2025
    """
    
    agent = BrandschutzTemplateAgent()
    
    # Mock für database_agent, falls nicht verfügbar
    class MockDatabaseAgent:
        def get_field_options(self, field_type):
            return []
    
    agent.db_agent = MockDatabaseAgent()
    
    # Analyse durchführen
    suggested_fields = agent._analyze_document(test_text)
    
    # Ergebnisse ausgeben
    print("Erkannte Felder für Brandschutz-Template:")
    print("-" * 50)
    for field in suggested_fields:
        print(f"\nFeld: {field.label}")
        print(f"  Name: {field.name}")
        print(f"  Typ: {field.field_type.value}")
        print(f"  Konfidenz: {field.confidence.name}")
        print(f"  Array: {field.is_array}")
        if field.options:
            print(f"  Optionen: {', '.join(field.options[:3])}...")
