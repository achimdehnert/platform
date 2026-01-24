# Brandschutz-Experte: Teil 3 - Normendatenbank & Prüfchecklisten

## 6. Normendatenbank

### 6.1 Struktur der Wissensbasis

```python
# knowledge/norms.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class NormCategory(Enum):
    """Kategorien von Brandschutz-Normen"""
    BAURECHT = "Baurecht"
    ARBEITSSCHUTZ = "Arbeitsschutz"
    TECHNISCH = "Technische Normen"
    VERSICHERUNG = "Versicherungsrecht"

@dataclass
class NormRequirement:
    """Einzelne Anforderung aus einer Norm"""
    id: str
    norm_id: str
    paragraph: str
    title: str
    description: str
    requirement_type: str  # 'muss', 'soll', 'kann'
    applies_to: List[str]  # Gebäudeklassen, Nutzungsarten
    keywords: List[str] = field(default_factory=list)
    measurable: bool = False
    threshold_value: Optional[float] = None
    threshold_unit: str = ""

@dataclass
class Norm:
    """Repräsentation einer Brandschutz-Norm"""
    id: str
    name: str
    full_name: str
    category: NormCategory
    version: str
    valid_from: str
    requirements: List[NormRequirement] = field(default_factory=list)
    
class NormDatabase:
    """Datenbank aller Brandschutz-relevanten Normen"""
    
    def __init__(self):
        self.norms: Dict[str, Norm] = {}
        self._load_norms()
    
    def _load_norms(self):
        """Lädt alle Normen in die Datenbank"""
        self._load_mbo()
        self._load_asr_a23()
        self._load_din_14096()
        self._load_din_4102()
        self._load_vds()
    
    def _load_mbo(self):
        """Musterbauordnung / Landesbauordnungen"""
        mbo = Norm(
            id="MBO",
            name="MBO",
            full_name="Musterbauordnung",
            category=NormCategory.BAURECHT,
            version="2023",
            valid_from="2023-01-01"
        )
        
        # §14 Brandschutz
        mbo.requirements.extend([
            NormRequirement(
                id="MBO-14-1",
                norm_id="MBO",
                paragraph="§14 Abs. 1",
                title="Brandschutz Grundsatz",
                description="Bauliche Anlagen sind so anzuordnen, zu errichten, zu ändern und instand zu halten, dass der Entstehung eines Brandes und der Ausbreitung von Feuer und Rauch vorgebeugt wird.",
                requirement_type="muss",
                applies_to=["alle"],
                keywords=["brandschutz", "grundsatz", "vorbeugung"]
            ),
            NormRequirement(
                id="MBO-33-1",
                norm_id="MBO",
                paragraph="§33 Abs. 1",
                title="Erster Rettungsweg",
                description="Für Nutzungseinheiten mit mindestens einem Aufenthaltsraum müssen in jedem Geschoss mindestens zwei voneinander unabhängige Rettungswege ins Freie vorhanden sein.",
                requirement_type="muss",
                applies_to=["alle"],
                keywords=["rettungsweg", "fluchtweg", "notausgang"],
                measurable=False
            ),
            NormRequirement(
                id="MBO-33-2",
                norm_id="MBO",
                paragraph="§33 Abs. 2",
                title="Rettungsweglänge",
                description="Von jeder Stelle eines Aufenthaltsraumes muss der Ausgang ins Freie oder in einen notwendigen Treppenraum in höchstens 35 m Lauflänge erreichbar sein.",
                requirement_type="muss",
                applies_to=["alle"],
                keywords=["rettungsweg", "lauflänge", "entfernung"],
                measurable=True,
                threshold_value=35.0,
                threshold_unit="m"
            ),
            NormRequirement(
                id="MBO-34-1",
                norm_id="MBO",
                paragraph="§34 Abs. 1",
                title="Notwendige Treppen",
                description="Jedes nicht zu ebener Erde liegende Geschoss und der benutzbare Dachraum eines Gebäudes müssen über mindestens eine Treppe zugänglich sein (notwendige Treppe).",
                requirement_type="muss",
                applies_to=["alle"],
                keywords=["treppe", "notwendig", "geschoss"]
            ),
            NormRequirement(
                id="MBO-35-3",
                norm_id="MBO",
                paragraph="§35 Abs. 3",
                title="Treppenraumbreite",
                description="Die nutzbare Breite der Treppen muss mindestens 1,00 m betragen.",
                requirement_type="muss",
                applies_to=["GK3", "GK4", "GK5"],
                keywords=["treppe", "breite", "nutzbar"],
                measurable=True,
                threshold_value=1.0,
                threshold_unit="m"
            ),
            NormRequirement(
                id="MBO-37-1",
                norm_id="MBO",
                paragraph="§37 Abs. 1",
                title="Notwendige Flure",
                description="Flure, über die Rettungswege aus Aufenthaltsräumen oder aus Nutzungseinheiten mit Aufenthaltsräumen zu Ausgängen in notwendige Treppenräume oder ins Freie führen (notwendige Flure), müssen so angeordnet und ausgebildet sein, dass die Nutzung im Brandfall ausreichend lang möglich ist.",
                requirement_type="muss",
                applies_to=["alle"],
                keywords=["flur", "rettungsweg", "brandfall"]
            ),
        ])
        
        self.norms["MBO"] = mbo
    
    def _load_asr_a23(self):
        """ASR A2.3 - Fluchtwege und Notausgänge"""
        asr = Norm(
            id="ASR_A2.3",
            name="ASR A2.3",
            full_name="Technische Regeln für Arbeitsstätten - Fluchtwege und Notausgänge",
            category=NormCategory.ARBEITSSCHUTZ,
            version="2022",
            valid_from="2022-03-01"
        )
        
        asr.requirements.extend([
            NormRequirement(
                id="ASR-A23-4.1",
                norm_id="ASR_A2.3",
                paragraph="4.1",
                title="Allgemeine Anforderungen Fluchtwege",
                description="Fluchtwege müssen ständig freigehalten werden, damit sie jederzeit ungehindert benutzt werden können.",
                requirement_type="muss",
                applies_to=["arbeitsstätte"],
                keywords=["fluchtweg", "frei", "begehbar"]
            ),
            NormRequirement(
                id="ASR-A23-4.3",
                norm_id="ASR_A2.3",
                paragraph="4.3",
                title="Fluchtweglänge",
                description="Die Fluchtweglänge darf bei Gefährdung durch erhöhte Brandgefahr max. 25 m, bei normaler Brandgefährdung max. 35 m und bei geringer Brandgefährdung max. 50 m betragen.",
                requirement_type="muss",
                applies_to=["arbeitsstätte"],
                keywords=["fluchtweg", "länge", "brandgefahr"],
                measurable=True,
                threshold_value=35.0,  # Standardfall
                threshold_unit="m"
            ),
            NormRequirement(
                id="ASR-A23-5.1",
                norm_id="ASR_A2.3",
                paragraph="5.1",
                title="Mindestbreite Fluchtwege",
                description="Die lichte Mindestbreite für Fluchtwege beträgt bei bis zu 5 Personen 0,875 m, bei bis zu 20 Personen 1,00 m, bei bis zu 200 Personen 1,20 m, bei bis zu 300 Personen 1,80 m.",
                requirement_type="muss",
                applies_to=["arbeitsstätte"],
                keywords=["fluchtweg", "breite", "personen"],
                measurable=True,
                threshold_value=1.0,
                threshold_unit="m"
            ),
            NormRequirement(
                id="ASR-A23-5.2",
                norm_id="ASR_A2.3",
                paragraph="5.2",
                title="Lichte Höhe Fluchtwege",
                description="Die lichte Höhe von Fluchtwegen muss mindestens 2,10 m betragen.",
                requirement_type="muss",
                applies_to=["arbeitsstätte"],
                keywords=["fluchtweg", "höhe", "licht"],
                measurable=True,
                threshold_value=2.1,
                threshold_unit="m"
            ),
            NormRequirement(
                id="ASR-A23-6.1",
                norm_id="ASR_A2.3",
                paragraph="6.1",
                title="Sicherheitsbeleuchtung",
                description="In Arbeitsstätten ist eine Sicherheitsbeleuchtung für Fluchtwege erforderlich, wenn bei Ausfall der allgemeinen Beleuchtung das gefahrlose Verlassen der Arbeitsstätte nicht gewährleistet ist.",
                requirement_type="soll",
                applies_to=["arbeitsstätte"],
                keywords=["beleuchtung", "sicherheit", "fluchtweg"]
            ),
            NormRequirement(
                id="ASR-A23-7.1",
                norm_id="ASR_A2.3",
                paragraph="7.1",
                title="Kennzeichnung Fluchtwege",
                description="Fluchtwege und Notausgänge sind zu kennzeichnen. Die Kennzeichnung muss der ASR A1.3 entsprechen.",
                requirement_type="muss",
                applies_to=["arbeitsstätte"],
                keywords=["kennzeichnung", "beschilderung", "fluchtweg"]
            ),
        ])
        
        self.norms["ASR_A2.3"] = asr
    
    def _load_din_14096(self):
        """DIN 14096 - Brandschutzordnung"""
        din = Norm(
            id="DIN_14096",
            name="DIN 14096",
            full_name="Brandschutzordnung - Regeln für das Erstellen und Aushängen",
            category=NormCategory.TECHNISCH,
            version="2014-05",
            valid_from="2014-05-01"
        )
        
        din.requirements.extend([
            NormRequirement(
                id="DIN14096-A",
                norm_id="DIN_14096",
                paragraph="Teil A",
                title="Brandschutzordnung Teil A",
                description="Aushang mit Verhaltensregeln bei Brand - richtet sich an alle Personen im Gebäude.",
                requirement_type="muss",
                applies_to=["alle"],
                keywords=["brandschutzordnung", "aushang", "verhalten"]
            ),
            NormRequirement(
                id="DIN14096-B",
                norm_id="DIN_14096",
                paragraph="Teil B",
                title="Brandschutzordnung Teil B",
                description="Richtet sich an Personen ohne besondere Brandschutzaufgaben (Mitarbeiter).",
                requirement_type="soll",
                applies_to=["arbeitsstätte"],
                keywords=["brandschutzordnung", "mitarbeiter", "schulung"]
            ),
            NormRequirement(
                id="DIN14096-C",
                norm_id="DIN_14096",
                paragraph="Teil C",
                title="Brandschutzordnung Teil C",
                description="Richtet sich an Personen mit besonderen Brandschutzaufgaben (Brandschutzbeauftragte, Brandschutzhelfer).",
                requirement_type="soll",
                applies_to=["sonderbau", "arbeitsstätte"],
                keywords=["brandschutzordnung", "brandschutzbeauftragter", "organisation"]
            ),
        ])
        
        self.norms["DIN_14096"] = din
    
    def _load_din_4102(self):
        """DIN 4102 - Brandverhalten von Baustoffen"""
        din = Norm(
            id="DIN_4102",
            name="DIN 4102",
            full_name="Brandverhalten von Baustoffen und Bauteilen",
            category=NormCategory.TECHNISCH,
            version="2016",
            valid_from="2016-01-01"
        )
        
        din.requirements.extend([
            NormRequirement(
                id="DIN4102-F30",
                norm_id="DIN_4102",
                paragraph="Teil 2",
                title="Feuerwiderstandsklasse F30",
                description="Bauteile mit Feuerwiderstandsdauer von mindestens 30 Minuten.",
                requirement_type="muss",
                applies_to=["GK1", "GK2"],
                keywords=["feuerwiderstand", "f30", "tragende bauteile"],
                measurable=True,
                threshold_value=30.0,
                threshold_unit="min"
            ),
            NormRequirement(
                id="DIN4102-F90",
                norm_id="DIN_4102",
                paragraph="Teil 2",
                title="Feuerwiderstandsklasse F90",
                description="Bauteile mit Feuerwiderstandsdauer von mindestens 90 Minuten.",
                requirement_type="muss",
                applies_to=["GK4", "GK5"],
                keywords=["feuerwiderstand", "f90", "tragende bauteile"],
                measurable=True,
                threshold_value=90.0,
                threshold_unit="min"
            ),
        ])
        
        self.norms["DIN_4102"] = din
    
    def _load_vds(self):
        """VdS-Richtlinien"""
        vds = Norm(
            id="VdS",
            name="VdS",
            full_name="VdS Schadenverhütung - Brandschutzrichtlinien",
            category=NormCategory.VERSICHERUNG,
            version="aktuell",
            valid_from="2020-01-01"
        )
        
        vds.requirements.extend([
            NormRequirement(
                id="VdS-2001",
                norm_id="VdS",
                paragraph="VdS 2001",
                title="Feuerlöscheinrichtungen",
                description="Vorgaben für Art, Anzahl und Verteilung von Feuerlöschern.",
                requirement_type="soll",
                applies_to=["gewerblich"],
                keywords=["feuerlöscher", "löscheinrichtung", "anzahl"]
            ),
            NormRequirement(
                id="VdS-2095",
                norm_id="VdS",
                paragraph="VdS 2095",
                title="Brandmeldeanlagen",
                description="Richtlinien für Planung und Einbau von Brandmeldeanlagen.",
                requirement_type="soll",
                applies_to=["sonderbau", "gewerblich"],
                keywords=["bma", "brandmeldeanlage", "melder"]
            ),
        ])
        
        self.norms["VdS"] = vds
    
    def get_requirements_for_building(
        self, 
        building_class: str, 
        usage_types: List[str]
    ) -> List[NormRequirement]:
        """Gibt alle anwendbaren Anforderungen für ein Gebäude zurück"""
        requirements = []
        
        for norm in self.norms.values():
            for req in norm.requirements:
                # Prüfe Anwendbarkeit
                applies = (
                    'alle' in req.applies_to or
                    building_class in req.applies_to or
                    any(usage in req.applies_to for usage in usage_types)
                )
                if applies:
                    requirements.append(req)
        
        return requirements
    
    def search_by_keyword(self, keyword: str) -> List[NormRequirement]:
        """Sucht Anforderungen nach Stichwort"""
        keyword = keyword.lower()
        results = []
        
        for norm in self.norms.values():
            for req in norm.requirements:
                if (keyword in req.title.lower() or 
                    keyword in req.description.lower() or
                    keyword in req.keywords):
                    results.append(req)
        
        return results
```

---

## 7. Prüfchecklisten

### 7.1 Struktur

```python
# knowledge/checklists.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class CheckItemStatus(Enum):
    UNCHECKED = "nicht geprüft"
    OK = "erfüllt"
    WARNING = "Hinweis"
    FAIL = "nicht erfüllt"
    NA = "nicht anwendbar"

@dataclass
class CheckItem:
    """Einzelner Prüfpunkt"""
    id: str
    category: str
    question: str
    description: str
    norm_references: List[str] = field(default_factory=list)
    auto_checkable: bool = False  # Kann automatisch geprüft werden
    check_method: str = ""  # Name der Prüfmethode
    severity: str = "medium"  # low, medium, high, critical

@dataclass
class CheckResult:
    """Ergebnis eines Prüfpunkts"""
    item: CheckItem
    status: CheckItemStatus
    finding: str = ""
    recommendation: str = ""
    evidence: str = ""  # Fundstelle/Nachweis

class FireProtectionChecklist:
    """Prüfcheckliste für Brandschutzkonzepte"""
    
    def __init__(self):
        self.items: List[CheckItem] = []
        self._load_checklist()
    
    def _load_checklist(self):
        """Lädt alle Prüfpunkte"""
        
        # ===== KATEGORIE: ALLGEMEINE ANGABEN =====
        self.items.extend([
            CheckItem(
                id="ALL-001",
                category="allgemein",
                question="Sind vollständige Angaben zum Gebäude vorhanden?",
                description="Adresse, Eigentümer, Nutzung, Gebäudeklasse",
                norm_references=["MBO §2"],
                auto_checkable=True,
                check_method="check_building_info"
            ),
            CheckItem(
                id="ALL-002",
                category="allgemein",
                question="Ist die Gebäudeklasse korrekt ermittelt?",
                description="Prüfung anhand Höhe, Fläche und Nutzungseinheiten",
                norm_references=["MBO §2"],
                auto_checkable=True,
                check_method="check_building_class"
            ),
            CheckItem(
                id="ALL-003",
                category="allgemein",
                question="Liegt ein Sonderbau vor?",
                description="Prüfung auf Sonderbautatbestände (Hochhaus, Versammlungsstätte, etc.)",
                norm_references=["MBO §2 Abs. 4"],
                auto_checkable=False
            ),
        ])
        
        # ===== KATEGORIE: BRANDABSCHNITTE =====
        self.items.extend([
            CheckItem(
                id="BA-001",
                category="brandabschnitt",
                question="Sind die Brandabschnitte dokumentiert?",
                description="Darstellung und Beschreibung aller Brandabschnitte",
                norm_references=["MBO §28"],
                auto_checkable=True,
                check_method="check_fire_sections_documented",
                severity="high"
            ),
            CheckItem(
                id="BA-002",
                category="brandabschnitt",
                question="Entspricht die Brandabschnittsgröße den Vorgaben?",
                description="Max. 40m Länge bzw. 1.600m² ohne BMA",
                norm_references=["MBO §28"],
                auto_checkable=True,
                check_method="check_fire_section_size",
                severity="critical"
            ),
            CheckItem(
                id="BA-003",
                category="brandabschnitt",
                question="Sind die Brandwände korrekt klassifiziert?",
                description="Feuerwiderstandsdauer gemäß Gebäudeklasse",
                norm_references=["MBO §28", "DIN 4102"],
                auto_checkable=True,
                check_method="check_firewall_classification",
                severity="critical"
            ),
            CheckItem(
                id="BA-004",
                category="brandabschnitt",
                question="Sind Öffnungen in Brandwänden geschützt?",
                description="Feuerschutzabschlüsse, selbstschließend",
                norm_references=["MBO §28", "MBO §30"],
                auto_checkable=False,
                severity="critical"
            ),
        ])
        
        # ===== KATEGORIE: RETTUNGSWEGE =====
        self.items.extend([
            CheckItem(
                id="RW-001",
                category="rettungsweg",
                question="Sind zwei unabhängige Rettungswege vorhanden?",
                description="Erster und zweiter Rettungsweg für jede Nutzungseinheit",
                norm_references=["MBO §33"],
                auto_checkable=True,
                check_method="check_escape_routes_count",
                severity="critical"
            ),
            CheckItem(
                id="RW-002",
                category="rettungsweg",
                question="Werden die Rettungsweglängen eingehalten?",
                description="Max. 35m Lauflänge (Standard), 25m bei erhöhter Brandgefahr",
                norm_references=["MBO §33", "ASR A2.3"],
                auto_checkable=True,
                check_method="check_escape_route_length",
                severity="critical"
            ),
            CheckItem(
                id="RW-003",
                category="rettungsweg",
                question="Sind die Rettungswegbreiten ausreichend?",
                description="Mind. 0,90m, in Abhängigkeit von Personenzahl",
                norm_references=["MBO §35", "ASR A2.3"],
                auto_checkable=True,
                check_method="check_escape_route_width",
                severity="high"
            ),
            CheckItem(
                id="RW-004",
                category="rettungsweg",
                question="Sind notwendige Treppen vorhanden?",
                description="Für jedes nicht zu ebener Erde liegende Geschoss",
                norm_references=["MBO §34"],
                auto_checkable=True,
                check_method="check_stairs_present",
                severity="critical"
            ),
            CheckItem(
                id="RW-005",
                category="rettungsweg",
                question="Sind Treppenräume rauchfrei ausgebildet?",
                description="Notwendige Treppenräume in GK4/5",
                norm_references=["MBO §35"],
                auto_checkable=False,
                severity="critical"
            ),
        ])
        
        # ===== KATEGORIE: TECHNISCHER BRANDSCHUTZ =====
        self.items.extend([
            CheckItem(
                id="TEC-001",
                category="technik",
                question="Ist eine Brandmeldeanlage erforderlich und vorhanden?",
                description="BMA nach VdS oder DIN",
                norm_references=["VdS 2095", "DIN 14675"],
                auto_checkable=True,
                check_method="check_fire_alarm_system",
                severity="high"
            ),
            CheckItem(
                id="TEC-002",
                category="technik",
                question="Sind ausreichend Feuerlöscher vorhanden?",
                description="Art, Anzahl und Verteilung gemäß ASR A2.2",
                norm_references=["ASR A2.2", "VdS 2001"],
                auto_checkable=True,
                check_method="check_fire_extinguishers",
                severity="medium"
            ),
            CheckItem(
                id="TEC-003",
                category="technik",
                question="Ist eine Sicherheitsbeleuchtung installiert?",
                description="Notbeleuchtung für Rettungswege",
                norm_references=["ASR A2.3", "DIN EN 1838"],
                auto_checkable=False,
                severity="high"
            ),
            CheckItem(
                id="TEC-004",
                category="technik",
                question="Sind Rauch-/Wärmeabzugsanlagen vorhanden?",
                description="RWA gemäß Anforderungen",
                norm_references=["MBO §35", "DIN 18232"],
                auto_checkable=True,
                check_method="check_smoke_ventilation",
                severity="medium"
            ),
        ])
        
        # ===== KATEGORIE: ORGANISATION =====
        self.items.extend([
            CheckItem(
                id="ORG-001",
                category="organisation",
                question="Liegt eine Brandschutzordnung vor?",
                description="Teil A (Aushang) verpflichtend, Teil B und C nach Bedarf",
                norm_references=["DIN 14096", "ASR A2.3"],
                auto_checkable=True,
                check_method="check_fire_protection_regulation",
                severity="medium"
            ),
            CheckItem(
                id="ORG-002",
                category="organisation",
                question="Ist ein Brandschutzbeauftragter benannt?",
                description="Bei Sonderbauten und größeren Arbeitsstätten",
                norm_references=["VdS 3111", "DGUV I 205-003"],
                auto_checkable=False,
                severity="medium"
            ),
            CheckItem(
                id="ORG-003",
                category="organisation",
                question="Werden regelmäßige Brandschutzunterweisungen durchgeführt?",
                description="Mind. jährlich für alle Beschäftigten",
                norm_references=["ASR A2.2", "DGUV V1"],
                auto_checkable=False,
                severity="medium"
            ),
            CheckItem(
                id="ORG-004",
                category="organisation",
                question="Ist ein Feuerwehrplan vorhanden?",
                description="Bei Sonderbauten und auf Anforderung",
                norm_references=["DIN 14095"],
                auto_checkable=True,
                check_method="check_fire_brigade_plan",
                severity="low"
            ),
        ])
    
    def get_by_category(self, category: str) -> List[CheckItem]:
        """Gibt alle Prüfpunkte einer Kategorie zurück"""
        return [item for item in self.items if item.category == category]
    
    def get_auto_checkable(self) -> List[CheckItem]:
        """Gibt alle automatisch prüfbaren Items zurück"""
        return [item for item in self.items if item.auto_checkable]
    
    def get_critical(self) -> List[CheckItem]:
        """Gibt alle kritischen Prüfpunkte zurück"""
        return [item for item in self.items if item.severity == "critical"]
```

---

## 8. Nächste Schritte

Die Wissensbasis ist definiert. Im nächsten Teil folgen:
- **Teil 4:** Analyzer-Module (Konzept-Analyzer, Plan-Analyzer)
- **Teil 5:** Recommendation Engine und Report Generator

Soll ich mit Teil 4 (Analyzer-Module) fortfahren?
