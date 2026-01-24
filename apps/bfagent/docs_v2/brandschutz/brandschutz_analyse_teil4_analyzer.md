# Brandschutz-Experte: Teil 4 - Analyzer-Module

## 9. Base Analyzer

### 9.1 Abstrakte Basisklasse

```python
# analyzers/base_analyzer.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..models.analysis_result import Finding, RiskLevel, AnalysisStatus
from ..knowledge.checklists import CheckItem, CheckResult, CheckItemStatus
from ..knowledge.norms import NormDatabase, NormRequirement

class BaseAnalyzer(ABC):
    """Abstrakte Basisklasse für alle Analyzer"""
    
    def __init__(self):
        self.norm_db = NormDatabase()
        self.findings: List[Finding] = []
        self.check_results: List[CheckResult] = []
    
    @abstractmethod
    def analyze(self, data: Dict[str, Any]) -> List[Finding]:
        """Führt die Analyse durch"""
        pass
    
    def add_finding(
        self,
        category: str,
        title: str,
        description: str,
        severity: RiskLevel,
        status: AnalysisStatus,
        norm_reference: str = "",
        location: str = "",
        recommendation: str = ""
    ) -> Finding:
        """Fügt einen Befund hinzu"""
        finding = Finding(
            id=f"F-{len(self.findings)+1:03d}",
            category=category,
            title=title,
            description=description,
            severity=severity,
            status=status,
            norm_reference=norm_reference,
            location=location,
            recommendation=recommendation
        )
        self.findings.append(finding)
        return finding
    
    def check_item(
        self,
        item: CheckItem,
        status: CheckItemStatus,
        finding: str = "",
        recommendation: str = "",
        evidence: str = ""
    ) -> CheckResult:
        """Prüft einen Checklistenpunkt"""
        result = CheckResult(
            item=item,
            status=status,
            finding=finding,
            recommendation=recommendation,
            evidence=evidence
        )
        self.check_results.append(result)
        
        # Bei Fehlschlag auch Finding erstellen
        if status == CheckItemStatus.FAIL:
            self.add_finding(
                category=item.category,
                title=item.question,
                description=finding or item.description,
                severity=self._severity_to_risk(item.severity),
                status=AnalysisStatus.ERROR,
                norm_reference=", ".join(item.norm_references),
                recommendation=recommendation
            )
        elif status == CheckItemStatus.WARNING:
            self.add_finding(
                category=item.category,
                title=item.question,
                description=finding or item.description,
                severity=RiskLevel.MEDIUM,
                status=AnalysisStatus.WARNING,
                norm_reference=", ".join(item.norm_references),
                recommendation=recommendation
            )
        
        return result
    
    def _severity_to_risk(self, severity: str) -> RiskLevel:
        """Konvertiert Severity zu RiskLevel"""
        mapping = {
            'low': RiskLevel.LOW,
            'medium': RiskLevel.MEDIUM,
            'high': RiskLevel.HIGH,
            'critical': RiskLevel.CRITICAL
        }
        return mapping.get(severity, RiskLevel.MEDIUM)
```

---

## 10. Konzept-Analyzer (Textbasiert)

```python
# analyzers/concept_analyzer.py
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .base_analyzer import BaseAnalyzer
from ..models.document_types import (
    FireProtectionConcept, BuildingInfo, BuildingClass,
    FireSection, EscapeRoute, FireProtectionSystem
)
from ..models.analysis_result import Finding, RiskLevel, AnalysisStatus
from ..knowledge.checklists import FireProtectionChecklist, CheckItemStatus

class ConceptAnalyzer(BaseAnalyzer):
    """Analysiert textbasierte Brandschutzkonzepte"""
    
    # Regex-Pattern für Informationsextraktion
    PATTERNS = {
        # Gebäudeklasse
        'building_class': [
            r'gebäudeklasse\s*[:\-]?\s*(\d|[IViv]+)',
            r'GK\s*[:\-]?\s*(\d)',
            r'klasse\s*(\d)\s*gebäude',
        ],
        # Höhe
        'height': [
            r'höhe\s*[:\-]?\s*(\d+[,.]?\d*)\s*m',
            r'gebäudehöhe\s*[:\-]?\s*(\d+[,.]?\d*)',
            r'(\d+[,.]?\d*)\s*m\s*hoch',
        ],
        # Geschosse
        'floors': [
            r'(\d+)\s*(ober)?geschoss',
            r'(\d+)\s*etage',
            r'erdgeschoss\s*\+\s*(\d+)\s*(ober)?geschoss',
        ],
        # Fläche
        'area': [
            r'bgf\s*[:\-]?\s*(\d+[.,]?\d*)\s*m²',
            r'bruttogeschossfläche\s*[:\-]?\s*(\d+[.,]?\d*)',
            r'(\d+[.,]?\d*)\s*m²\s*(bgf|bruttogeschossfläche)',
        ],
        # Rettungsweglänge
        'escape_length': [
            r'rettungsweglänge\s*[:\-]?\s*(\d+[,.]?\d*)\s*m',
            r'lauflänge\s*[:\-]?\s*(\d+[,.]?\d*)\s*m',
            r'(\d+[,.]?\d*)\s*m\s*(lauflänge|rettungsweg)',
        ],
        # Brandabschnitt
        'fire_section': [
            r'brandabschnitt\s*[:\-]?\s*(\d+)',
            r'ba\s*[:\-]?\s*(\d+)',
        ],
        # Feuerwiderstandsklasse
        'fire_resistance': [
            r'(f\s*\d+|rei\s*\d+)',
            r'feuerwiderstand[sklasse]*\s*[:\-]?\s*(f\s*\d+)',
        ],
    }
    
    # Schlüsselwörter für Vollständigkeitsprüfung
    REQUIRED_SECTIONS = {
        'gebaeude': ['gebäude', 'bauliche anlage', 'objekt', 'bauvorhaben'],
        'brandabschnitte': ['brandabschnitt', 'brandbekämpfungsabschnitt', 'abschottung'],
        'fluchtwege': ['fluchtweg', 'rettungsweg', 'notausgang', 'evakuierung'],
        'technik': ['brandmeldeanlage', 'bma', 'feuerlöscher', 'sprinkler', 'rwa'],
        'organisation': ['brandschutzordnung', 'organisation', 'unterweisung'],
    }
    
    def __init__(self):
        super().__init__()
        self.checklist = FireProtectionChecklist()
    
    def analyze(self, parse_result: Dict[str, Any]) -> List[Finding]:
        """Analysiert ein gepartes Brandschutzkonzept"""
        
        raw_text = parse_result.get('raw_text', '')
        sections = parse_result.get('content', {}).get('sections', {})
        
        # 1. Extraktion der Gebäudeinformationen
        concept = self._extract_concept_data(raw_text, sections)
        
        # 2. Vollständigkeitsprüfung
        self._check_completeness(raw_text, sections)
        
        # 3. Normkonformitätsprüfung
        self._check_norm_compliance(concept)
        
        # 4. Checklisten-Prüfung
        self._run_checklist(concept, raw_text)
        
        return self.findings
    
    def _extract_concept_data(
        self, 
        raw_text: str, 
        sections: Dict[str, str]
    ) -> FireProtectionConcept:
        """Extrahiert strukturierte Daten aus dem Text"""
        concept = FireProtectionConcept()
        concept.raw_text = raw_text
        concept.extracted_sections = sections
        
        text_lower = raw_text.lower()
        
        # Gebäudeklasse extrahieren
        for pattern in self.PATTERNS['building_class']:
            match = re.search(pattern, text_lower)
            if match:
                gk_str = match.group(1)
                concept.building.building_class = self._parse_building_class(gk_str)
                break
        
        # Höhe extrahieren
        for pattern in self.PATTERNS['height']:
            match = re.search(pattern, text_lower)
            if match:
                concept.building.height = float(match.group(1).replace(',', '.'))
                break
        
        # Geschosse extrahieren
        for pattern in self.PATTERNS['floors']:
            match = re.search(pattern, text_lower)
            if match:
                concept.building.floors_above = int(match.group(1))
                break
        
        # Fläche extrahieren
        for pattern in self.PATTERNS['area']:
            match = re.search(pattern, text_lower)
            if match:
                concept.building.gross_area = float(
                    match.group(1).replace('.', '').replace(',', '.')
                )
                break
        
        # Brandabschnitte identifizieren
        concept.fire_sections = self._extract_fire_sections(raw_text)
        
        # Rettungswege identifizieren
        concept.escape_routes = self._extract_escape_routes(raw_text)
        
        # Technische Anlagen identifizieren
        concept.systems = self._extract_systems(raw_text)
        
        return concept
    
    def _parse_building_class(self, gk_str: str) -> Optional[BuildingClass]:
        """Parst Gebäudeklasse aus String"""
        gk_str = gk_str.strip().upper()
        mapping = {
            '1': BuildingClass.GK1, 'I': BuildingClass.GK1,
            '2': BuildingClass.GK2, 'II': BuildingClass.GK2,
            '3': BuildingClass.GK3, 'III': BuildingClass.GK3,
            '4': BuildingClass.GK4, 'IV': BuildingClass.GK4,
            '5': BuildingClass.GK5, 'V': BuildingClass.GK5,
        }
        return mapping.get(gk_str)
    
    def _extract_fire_sections(self, text: str) -> List[FireSection]:
        """Extrahiert Brandabschnitte aus dem Text"""
        sections = []
        
        # Suche nach Brandabschnitts-Beschreibungen
        ba_pattern = r'brandabschnitt\s*(\d+|[a-z])[:\s]+([^\n]+)'
        for match in re.finditer(ba_pattern, text.lower()):
            sections.append(FireSection(
                id=f"BA-{match.group(1)}",
                name=f"Brandabschnitt {match.group(1)}",
                description=match.group(2).strip()
            ))
        
        # Feuerwiderstandsklassen zuordnen
        fw_pattern = r'(f|rei)\s*(\d+)'
        fw_matches = re.findall(fw_pattern, text.lower())
        if fw_matches and sections:
            # Ordne häufigste Klasse zu
            classes = [f"{m[0].upper()}{m[1]}" for m in fw_matches]
            most_common = max(set(classes), key=classes.count)
            for section in sections:
                if not section.fire_resistance_class:
                    section.fire_resistance_class = most_common
        
        return sections
    
    def _extract_escape_routes(self, text: str) -> List[EscapeRoute]:
        """Extrahiert Rettungswege aus dem Text"""
        routes = []
        
        # Erster Rettungsweg
        if re.search(r'erst(er|en)\s*rettungsweg', text.lower()):
            route = EscapeRoute(id="RW-1", type="erster_rw")
            
            # Länge suchen
            length_match = re.search(
                r'erst\w*\s*rettungsweg[^.]*?(\d+[,.]?\d*)\s*m',
                text.lower()
            )
            if length_match:
                route.length = float(length_match.group(1).replace(',', '.'))
            
            routes.append(route)
        
        # Zweiter Rettungsweg
        if re.search(r'zweit(er|en)\s*rettungsweg', text.lower()):
            route = EscapeRoute(id="RW-2", type="zweiter_rw")
            routes.append(route)
        
        # Notausgänge zählen
        notausgang_count = len(re.findall(r'notausgang', text.lower()))
        for i in range(notausgang_count):
            routes.append(EscapeRoute(
                id=f"NA-{i+1}",
                type="notausgang"
            ))
        
        return routes
    
    def _extract_systems(self, text: str) -> List[FireProtectionSystem]:
        """Extrahiert technische Anlagen"""
        systems = []
        text_lower = text.lower()
        
        # BMA
        if re.search(r'brandmeldeanlage|bma', text_lower):
            coverage = 'vollflächig' if 'vollflächig' in text_lower else 'teilweise'
            systems.append(FireProtectionSystem(
                type="BMA",
                coverage=coverage,
                norm_reference="VdS 2095"
            ))
        
        # RWA
        if re.search(r'rauchabzug|rwa|rauch.*wärme.*abzug', text_lower):
            systems.append(FireProtectionSystem(
                type="RWA",
                coverage="teilweise",
                norm_reference="DIN 18232"
            ))
        
        # Sprinkler
        if re.search(r'sprinkler|löschanlage', text_lower):
            systems.append(FireProtectionSystem(
                type="Sprinkleranlage",
                coverage="vollflächig" if 'vollflächig' in text_lower else 'teilweise',
                norm_reference="VdS CEA 4001"
            ))
        
        # Feuerlöscher
        if re.search(r'feuerlöscher|handfeuerlöscher', text_lower):
            systems.append(FireProtectionSystem(
                type="Feuerlöscher",
                coverage="punktuell",
                norm_reference="ASR A2.2"
            ))
        
        return systems
    
    def _check_completeness(self, raw_text: str, sections: Dict[str, str]):
        """Prüft Vollständigkeit des Konzepts"""
        text_lower = raw_text.lower()
        
        for section_name, keywords in self.REQUIRED_SECTIONS.items():
            found = any(kw in text_lower for kw in keywords)
            
            if not found:
                self.add_finding(
                    category="vollständigkeit",
                    title=f"Abschnitt '{section_name}' fehlt oder unvollständig",
                    description=f"Im Brandschutzkonzept wurden keine Informationen zu '{section_name}' gefunden.",
                    severity=RiskLevel.HIGH,
                    status=AnalysisStatus.MISSING,
                    recommendation=f"Ergänzen Sie Informationen zu: {', '.join(keywords)}"
                )
    
    def _check_norm_compliance(self, concept: FireProtectionConcept):
        """Prüft Einhaltung der Normanforderungen"""
        
        # Prüfe Rettungsweglängen
        for route in concept.escape_routes:
            if route.length and route.length > 35:
                self.add_finding(
                    category="rettungsweg",
                    title="Rettungsweglänge überschritten",
                    description=f"Der Rettungsweg {route.id} hat eine Länge von {route.length}m. Das Maximum beträgt 35m.",
                    severity=RiskLevel.CRITICAL,
                    status=AnalysisStatus.ERROR,
                    norm_reference="MBO §33, ASR A2.3",
                    recommendation="Zusätzliche Ausgänge vorsehen oder Rettungsweglänge durch bauliche Maßnahmen reduzieren."
                )
        
        # Prüfe Gebäudeklasse vs. Feuerwiderstand
        if concept.building.building_class:
            required_fw = self._get_required_fire_resistance(concept.building.building_class)
            for section in concept.fire_sections:
                if section.fire_resistance_class:
                    actual_minutes = self._parse_fire_resistance(section.fire_resistance_class)
                    if actual_minutes < required_fw:
                        self.add_finding(
                            category="brandabschnitt",
                            title="Feuerwiderstand nicht ausreichend",
                            description=f"{section.name}: {section.fire_resistance_class} erfüllt nicht die Anforderung von F{required_fw}",
                            severity=RiskLevel.CRITICAL,
                            status=AnalysisStatus.ERROR,
                            norm_reference="MBO §28, DIN 4102",
                            recommendation=f"Feuerwiderstandsklasse auf mindestens F{required_fw} erhöhen."
                        )
    
    def _get_required_fire_resistance(self, building_class: BuildingClass) -> int:
        """Gibt erforderliche Feuerwiderstandsdauer zurück"""
        requirements = {
            BuildingClass.GK1: 0,
            BuildingClass.GK2: 30,
            BuildingClass.GK3: 30,
            BuildingClass.GK4: 60,
            BuildingClass.GK5: 90,
        }
        return requirements.get(building_class, 30)
    
    def _parse_fire_resistance(self, fw_class: str) -> int:
        """Parst Feuerwiderstandsklasse zu Minuten"""
        match = re.search(r'(\d+)', fw_class)
        return int(match.group(1)) if match else 0
    
    def _run_checklist(self, concept: FireProtectionConcept, raw_text: str):
        """Führt automatische Checklistenprüfung durch"""
        
        for item in self.checklist.get_auto_checkable():
            method_name = item.check_method
            if hasattr(self, f"_check_{method_name}"):
                check_func = getattr(self, f"_check_{method_name}")
                check_func(item, concept, raw_text)
    
    # Automatische Prüfmethoden
    def _check_check_building_info(self, item, concept, raw_text):
        """Prüft vollständige Gebäudeinformationen"""
        missing = []
        if not concept.building.building_class:
            missing.append("Gebäudeklasse")
        if not concept.building.height:
            missing.append("Gebäudehöhe")
        if not concept.building.gross_area:
            missing.append("Bruttogeschossfläche")
        
        if missing:
            self.check_item(
                item,
                CheckItemStatus.WARNING,
                f"Fehlende Angaben: {', '.join(missing)}",
                "Vervollständigen Sie die Gebäudeinformationen."
            )
        else:
            self.check_item(item, CheckItemStatus.OK)
    
    def _check_check_escape_routes_count(self, item, concept, raw_text):
        """Prüft Anzahl der Rettungswege"""
        rw_count = len([r for r in concept.escape_routes if r.type in ['erster_rw', 'zweiter_rw']])
        
        if rw_count < 2:
            self.check_item(
                item,
                CheckItemStatus.FAIL,
                f"Nur {rw_count} Rettungsweg(e) dokumentiert.",
                "Stellen Sie sicher, dass mindestens zwei unabhängige Rettungswege vorhanden und dokumentiert sind."
            )
        else:
            self.check_item(item, CheckItemStatus.OK)
    
    def _check_check_fire_sections_documented(self, item, concept, raw_text):
        """Prüft ob Brandabschnitte dokumentiert sind"""
        if not concept.fire_sections:
            self.check_item(
                item,
                CheckItemStatus.FAIL,
                "Keine Brandabschnitte im Konzept dokumentiert.",
                "Dokumentieren Sie alle Brandabschnitte mit Größe und Feuerwiderstandsklasse."
            )
        else:
            self.check_item(
                item,
                CheckItemStatus.OK,
                f"{len(concept.fire_sections)} Brandabschnitt(e) dokumentiert."
            )
```

---

## 11. Plan-Analyzer (CAD-basiert)

```python
# analyzers/plan_analyzer.py
from typing import Dict, List, Any, Tuple
import math

from .base_analyzer import BaseAnalyzer
from ..models.analysis_result import Finding, RiskLevel, AnalysisStatus
from ..knowledge.checklists import FireProtectionChecklist, CheckItemStatus

class PlanAnalyzer(BaseAnalyzer):
    """Analysiert CAD-Pläne auf Brandschutz-Kriterien"""
    
    # Mindestanforderungen
    MIN_ESCAPE_WIDTH_MM = 900  # 0,90m
    MAX_ESCAPE_LENGTH_MM = 35000  # 35m
    MIN_DOOR_WIDTH_MM = 800  # 0,80m
    MIN_STAIR_WIDTH_MM = 1000  # 1,00m
    
    def __init__(self):
        super().__init__()
        self.checklist = FireProtectionChecklist()
    
    def analyze(self, parse_result: Dict[str, Any]) -> List[Finding]:
        """Analysiert einen CAD-Plan"""
        
        content = parse_result.get('content', {})
        
        fire_elements = content.get('fire_elements', [])
        rooms = content.get('rooms', [])
        escape_routes = content.get('escape_routes', [])
        layers = content.get('layers', {})
        blocks = content.get('blocks', {})
        bbox = content.get('bounding_box', {})
        
        # 1. Brandschutz-Elemente prüfen
        self._analyze_fire_elements(fire_elements)
        
        # 2. Räume prüfen
        self._analyze_rooms(rooms)
        
        # 3. Fluchtwege prüfen
        self._analyze_escape_routes(escape_routes)
        
        # 4. Vollständigkeit der Layer prüfen
        self._check_layer_completeness(layers)
        
        # 5. Brandschutz-Symbole prüfen
        self._check_safety_symbols(blocks, fire_elements)
        
        return self.findings
    
    def _analyze_fire_elements(self, elements: List[Dict]):
        """Analysiert Brandschutz-relevante Elemente"""
        
        # Kategorisieren
        by_category = {}
        for elem in elements:
            cat = elem.get('category', 'sonstige')
            by_category.setdefault(cat, []).append(elem)
        
        # Brandschutztüren prüfen
        doors = by_category.get('brandschutztueren', [])
        if not doors:
            self.add_finding(
                category="plan",
                title="Keine Brandschutztüren erkannt",
                description="Im Plan wurden keine Brandschutztüren (T30/T60/T90/RS-Türen) identifiziert.",
                severity=RiskLevel.MEDIUM,
                status=AnalysisStatus.WARNING,
                recommendation="Prüfen Sie, ob Brandschutztüren auf einem separaten Layer dargestellt sind oder ergänzen Sie diese."
            )
        
        # Feuerlöscher-Verteilung prüfen
        extinguishers = by_category.get('loescher', [])
        if extinguishers:
            self._check_extinguisher_coverage(extinguishers)
        
        # Melder prüfen
        detectors = by_category.get('melder', [])
        if detectors:
            self._check_detector_coverage(detectors)
    
    def _analyze_rooms(self, rooms: List[Dict]):
        """Analysiert Räume"""
        
        if not rooms:
            self.add_finding(
                category="plan",
                title="Keine Räume erkannt",
                description="Es konnten keine Räume automatisch erkannt werden.",
                severity=RiskLevel.LOW,
                status=AnalysisStatus.WARNING,
                recommendation="Räume sollten als geschlossene Polylinien auf einem Raum-Layer dargestellt werden."
            )
            return
        
        # Große Räume ohne Unterteilung prüfen
        large_rooms = [r for r in rooms if r.get('area_sqm', 0) > 400]
        for room in large_rooms:
            self.add_finding(
                category="brandabschnitt",
                title="Großer Raum ohne erkennbare Unterteilung",
                description=f"Raum mit {room['area_sqm']:.0f}m² könnte Brandabschnittsbildung erfordern.",
                severity=RiskLevel.MEDIUM,
                status=AnalysisStatus.WARNING,
                location=f"Schwerpunkt: ({room['centroid'][0]:.0f}, {room['centroid'][1]:.0f})",
                recommendation="Prüfen Sie, ob eine Brandabschnittsbildung erforderlich ist (>400m² oder >1.600m²)."
            )
    
    def _analyze_escape_routes(self, routes: List[Dict]):
        """Analysiert erkannte Fluchtwege"""
        
        if not routes:
            self.add_finding(
                category="rettungsweg",
                title="Keine Fluchtwege im Plan erkannt",
                description="Es konnten keine Fluchtwege automatisch identifiziert werden.",
                severity=RiskLevel.HIGH,
                status=AnalysisStatus.WARNING,
                recommendation="Fluchtwege sollten auf einem separaten Layer (z.B. 'FLUCHTWEG') dargestellt werden."
            )
            return
        
        # Fluchtweglängen prüfen
        for route in routes:
            length_m = route.get('length_m', 0)
            if length_m > 35:
                self.add_finding(
                    category="rettungsweg",
                    title="Fluchtweglänge überschritten",
                    description=f"Erkannter Fluchtweg hat {length_m:.1f}m Länge (max. 35m).",
                    severity=RiskLevel.CRITICAL,
                    status=AnalysisStatus.ERROR,
                    norm_reference="MBO §33, ASR A2.3",
                    recommendation="Zusätzliche Ausgänge vorsehen oder Fluchtweglänge reduzieren."
                )
    
    def _check_layer_completeness(self, layers: Dict[str, Dict]):
        """Prüft ob alle brandschutzrelevanten Layer vorhanden sind"""
        
        required_categories = {
            'fluchtwege': "Fluchtweg-Darstellung",
            'brandabschnitt': "Brandabschnittsbildung",
            'beschilderung': "Sicherheitsbeschilderung"
        }
        
        found_categories = set()
        for layer_name, layer_info in layers.items():
            cat = layer_info.get('category')
            if cat in required_categories:
                found_categories.add(cat)
        
        for cat, desc in required_categories.items():
            if cat not in found_categories:
                self.add_finding(
                    category="plan",
                    title=f"Kein Layer für {desc} gefunden",
                    description=f"Es wurde kein Layer für '{cat}' im Plan identifiziert.",
                    severity=RiskLevel.LOW,
                    status=AnalysisStatus.INCOMPLETE,
                    recommendation=f"Erstellen Sie einen Layer für {desc} mit entsprechenden Inhalten."
                )
    
    def _check_safety_symbols(self, blocks: Dict, fire_elements: List[Dict]):
        """Prüft Brandschutz-Symbole"""
        
        # Zähle relevante Block-Kategorien
        block_categories = {}
        for block_name, block_info in blocks.items():
            cat = block_info.get('category')
            if cat != 'sonstige':
                block_categories.setdefault(cat, []).append(block_name)
        
        # Empfohlene Symbole
        recommended = {
            'feuerloescher': "Feuerlöscher-Symbole",
            'notausgang': "Notausgang-Symbole",
            'sammelplatz': "Sammelplatz-Symbol",
        }
        
        for cat, desc in recommended.items():
            if cat not in block_categories:
                # Prüfe auch in fire_elements
                in_elements = any(e.get('category') == cat for e in fire_elements)
                if not in_elements:
                    self.add_finding(
                        category="beschilderung",
                        title=f"Keine {desc} erkannt",
                        description=f"Im Plan wurden keine {desc} identifiziert.",
                        severity=RiskLevel.LOW,
                        status=AnalysisStatus.INCOMPLETE,
                        recommendation=f"Ergänzen Sie {desc} gemäß ASR A1.3."
                    )
    
    def _check_extinguisher_coverage(self, extinguishers: List[Dict]):
        """Prüft Feuerlöscher-Abdeckung"""
        
        if len(extinguishers) < 2:
            self.add_finding(
                category="technik",
                title="Wenige Feuerlöscher erkannt",
                description=f"Nur {len(extinguishers)} Feuerlöscher im Plan erkannt.",
                severity=RiskLevel.MEDIUM,
                status=AnalysisStatus.WARNING,
                norm_reference="ASR A2.2",
                recommendation="Prüfen Sie die Feuerlöscher-Anzahl gemäß ASR A2.2 (max. 20m Laufweg)."
            )
    
    def _check_detector_coverage(self, detectors: List[Dict]):
        """Prüft Melder-Abdeckung"""
        
        # Einfache Prüfung: Mindestanzahl
        if len(detectors) < 3:
            self.add_finding(
                category="technik",
                title="Wenige Brandmelder erkannt",
                description=f"Nur {len(detectors)} Melder im Plan erkannt.",
                severity=RiskLevel.LOW,
                status=AnalysisStatus.WARNING,
                recommendation="Prüfen Sie die Melder-Verteilung gemäß VdS 2095 / DIN 14675."
            )
```

---

## 12. Nächste Schritte

Die Analyzer sind nun spezifiziert. Im letzten Teil folgen:
- **Teil 5:** Recommendation Engine und Report Generator
- **Teil 6:** CLI und Integration

Soll ich mit Teil 5 (Output-Generierung) fortfahren?
