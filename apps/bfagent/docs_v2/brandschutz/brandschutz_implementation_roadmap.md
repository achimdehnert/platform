# Implementierungs-Roadmap: Brandschutz-System Integration

## 🎯 Übersicht

Integration des Brandschutz-/Explosionsschutzgutachten-Systems in die bestehende Unified Platform unter Nutzung der vorhandenen Template Agent Architektur.

## 📊 Aktuelle System-Analyse

### Vorhandene Komponenten (können wiederverwendet werden)

1. **Template Agent**
   - ✅ Dokumentextraktion (PDF, Word, Excel)
   - ✅ Pattern-Matching für Feldtypen
   - ✅ Datenbank-Integration
   - ✅ Test-Infrastruktur

2. **Plugin-System**
   - ✅ Explosionsschutz Plugin (bereits vorhanden!)
   - ✅ Plugin Registry
   - ✅ Modulare Architektur

3. **Datenbank-Layer**
   - ✅ Repository Pattern
   - ✅ SQLite Backend
   - ✅ Unified Data Repository

## 🚀 Implementierungsplan

### Phase 1: Template Mining für Brandschutz-Dokumente (Woche 1-2)

#### Schritt 1.1: Erweitere Template Agent für Brandschutz-Patterns
```python
# gui/components/template_agent_brandschutz.py
class BrandschutzTemplateAgent(TemplateAgent):
    def __init__(self):
        super().__init__()
        self.add_brandschutz_patterns()
    
    def add_brandschutz_patterns(self):
        self.field_patterns.update({
            "brandschutz_zone": [
                r"(?:ex-zone|schutzbereich|explosionsgefährdet)\s*:?\s*",
                r"(?:zone\s+\d+|bereich\s+\d+)\s*:?\s*"
            ],
            "schutzmaßnahme": [
                r"(?:maßnahme|schutzmaßnahme|vorkehrung)\s*:?\s*",
                r"(?:primär|sekundär|tertiär|TOP|STOP)\s*:?\s*"
            ],
            "gefährdung": [
                r"(?:gefährdung|risiko|gefahr)\s*:?\s*",
                r"(?:brand|explosion|entzündung)\s*:?\s*"
            ]
        })
```

#### Tests für Phase 1.1
```python
# tests/test_brandschutz_template_agent.py
import unittest
from gui.components.template_agent_brandschutz import BrandschutzTemplateAgent

class TestBrandschutzTemplateAgent(unittest.TestCase):
    def setUp(self):
        self.agent = BrandschutzTemplateAgent()
    
    def test_ex_zone_pattern_recognition(self):
        test_text = "Ex-Zone: Zone 1 - Explosionsgefährdeter Bereich"
        fields = self.agent._analyze_document(test_text)
        self.assertIn("ex_zone", [f.name for f in fields])
    
    def test_schutzmaßnahme_extraction(self):
        test_text = "Primäre Schutzmaßnahme: Inertisierung"
        fields = self.agent._analyze_document(test_text)
        self.assertIn("schutzmaßnahme", [f.name for f in fields])
```

#### Schritt 1.2: Template-Bibliothek für Brandschutz
```python
# gui/data/brandschutz_templates/base_templates.py
BRANDSCHUTZ_BASE_TEMPLATE = {
    "name": "brandschutz_gutachten_basis",
    "category": "Brandschutz",
    "sections": [
        {
            "name": "rechtliche_grundlagen",
            "fields": [
                {"name": "betrsichv_version", "type": "text_input"},
                {"name": "gefstoffv_version", "type": "text_input"},
                {"name": "anwendbare_trgs", "type": "array_group"}
            ]
        },
        {
            "name": "anlagenbeschreibung",
            "fields": [
                {"name": "anlagentyp", "type": "selectbox"},
                {"name": "standort", "type": "text_input"},
                {"name": "verfahrensbeschreibung", "type": "text_area"}
            ]
        }
    ]
}
```

### Phase 2: Requirements Engineering Integration (Woche 3-4)

#### Schritt 2.1: Strukturierter Fragebogen
```python
# gui/components/requirements_agent.py
class RequirementsAgent:
    def __init__(self):
        self.db_agent = create_database_agent()
        self.questionnaire_templates = self.load_questionnaires()
    
    def create_brandschutz_questionnaire(self, project_type: str):
        """Erstellt dynamischen Fragebogen basierend auf Projekttyp"""
        base_questions = [
            {
                "id": "q1",
                "text": "Welche Art von Anlage soll begutachtet werden?",
                "type": "selectbox",
                "options": ["Produktionsanlage", "Lager", "Labor", "Sonstiges"]
            },
            {
                "id": "q2",
                "text": "Werden brennbare Flüssigkeiten verwendet?",
                "type": "checkbox",
                "follow_up": "q2_details"
            }
        ]
        return self.customize_for_project_type(base_questions, project_type)
```

#### Tests für Phase 2.1
```python
# tests/test_requirements_agent.py
class TestRequirementsAgent(unittest.TestCase):
    def test_questionnaire_generation(self):
        agent = RequirementsAgent()
        questionnaire = agent.create_brandschutz_questionnaire("explosionsschutz")
        self.assertGreater(len(questionnaire), 0)
        self.assertIn("type", questionnaire[0])
    
    def test_follow_up_questions(self):
        agent = RequirementsAgent()
        responses = {"q2": True}
        follow_ups = agent.get_follow_up_questions(responses)
        self.assertIn("q2_details", [q["id"] for q in follow_ups])
```

#### Schritt 2.2: Integration mit Streamlit UI
```python
# gui/pages/brandschutz_requirements.py
import streamlit as st
from gui.components.requirements_agent import RequirementsAgent

def render_requirements_page():
    st.title("📋 Anforderungserhebung Brandschutz")
    
    agent = RequirementsAgent()
    
    # Schritt 1: Projekttyp
    project_type = st.selectbox(
        "Projekttyp",
        ["Brandschutzgutachten", "Explosionsschutzgutachten", "Kombiniert"]
    )
    
    # Dynamischer Fragebogen
    questionnaire = agent.create_brandschutz_questionnaire(project_type)
    responses = {}
    
    for question in questionnaire:
        if question["type"] == "selectbox":
            responses[question["id"]] = st.selectbox(
                question["text"],
                question["options"]
            )
        elif question["type"] == "checkbox":
            responses[question["id"]] = st.checkbox(question["text"])
    
    if st.button("Anforderungen speichern"):
        agent.save_requirements(st.session_state.project_id, responses)
        st.success("Anforderungen gespeichert!")
```

### Phase 3: Document Analysis für Brandschutz (Woche 5-6)

#### Schritt 3.1: Spezialisierter Document Analyzer
```python
# gui/components/brandschutz_document_analyzer.py
class BrandschutzDocumentAnalyzer:
    def __init__(self):
        self.required_documents = self.load_document_requirements()
        self.compliance_mapper = ComplianceMapper()
    
    def analyze_for_compliance(self, documents: List[Document]) -> ComplianceResult:
        """Prüft Dokumente auf Vollständigkeit und Compliance"""
        result = ComplianceResult()
        
        # Pflichtdokumente prüfen
        for req_doc in self.required_documents["mandatory"]:
            found = self.find_matching_document(req_doc, documents)
            if not found:
                result.add_missing(req_doc, "KRITISCH")
        
        # Mapping zu Vorschriften
        for doc in documents:
            mappings = self.compliance_mapper.map_document(doc)
            result.add_mappings(doc, mappings)
        
        return result
    
    def extract_safety_data(self, document: Document) -> SafetyData:
        """Extrahiert sicherheitsrelevante Daten"""
        if document.type == "sicherheitsdatenblatt":
            return self.extract_sds_data(document)
        elif document.type == "verfahrensbeschreibung":
            return self.extract_process_data(document)
```

#### Tests für Phase 3.1
```python
# tests/test_brandschutz_document_analyzer.py
class TestBrandschutzDocumentAnalyzer(unittest.TestCase):
    def test_mandatory_document_check(self):
        analyzer = BrandschutzDocumentAnalyzer()
        documents = []  # Keine Dokumente
        result = analyzer.analyze_for_compliance(documents)
        self.assertTrue(result.has_critical_missing())
    
    def test_sds_data_extraction(self):
        analyzer = BrandschutzDocumentAnalyzer()
        mock_sds = create_mock_sds_document()
        safety_data = analyzer.extract_safety_data(mock_sds)
        self.assertIsNotNone(safety_data.flash_point)
        self.assertIn("H226", safety_data.hazard_codes)
```

### Phase 4: Technical Analysis Engine (Woche 7-8)

#### Schritt 4.1: TOP/STOP Analyse-Modul
```python
# gui/components/technical_analysis_engine.py
class TechnicalAnalysisEngine:
    def __init__(self):
        self.protection_hierarchy = ["T", "O", "P"]  # Technisch vor Personell
        
    def perform_top_analysis(self, hazards: List[Hazard], 
                           existing_measures: List[Measure]) -> ProtectionConcept:
        """Führt TOP-Analyse durch"""
        concept = ProtectionConcept()
        
        for hazard in hazards:
            # Technische Maßnahmen priorisieren
            tech_measures = self.identify_technical_measures(hazard)
            if tech_measures:
                concept.add_primary_measure(hazard, tech_measures[0])
            else:
                # Fallback zu organisatorischen Maßnahmen
                org_measures = self.identify_organizational_measures(hazard)
                concept.add_secondary_measure(hazard, org_measures[0])
        
        return concept
    
    def calculate_ex_zones(self, substances: List[Substance], 
                          ventilation: VentilationData) -> List[ExZone]:
        """Berechnet Ex-Zonen basierend auf TRGS 720"""
        zones = []
        
        for substance in substances:
            if substance.is_flammable():
                zone_type = self.determine_zone_type(
                    substance.vapor_pressure,
                    ventilation.air_changes_per_hour
                )
                zone = ExZone(
                    type=zone_type,
                    extent=self.calculate_zone_extent(substance, ventilation)
                )
                zones.append(zone)
        
        return zones
```

#### Tests für Phase 4.1
```python
# tests/test_technical_analysis_engine.py
class TestTechnicalAnalysisEngine(unittest.TestCase):
    def test_top_hierarchy(self):
        engine = TechnicalAnalysisEngine()
        hazard = Hazard(type="explosion", severity="high")
        concept = engine.perform_top_analysis([hazard], [])
        
        # Technische Maßnahme sollte Priorität haben
        primary = concept.get_primary_measures(hazard)
        self.assertEqual(primary[0].category, "technical")
    
    def test_ex_zone_calculation(self):
        engine = TechnicalAnalysisEngine()
        ethanol = Substance(name="Ethanol", flash_point=13, vapor_pressure=5.8)
        ventilation = VentilationData(air_changes_per_hour=6)
        
        zones = engine.calculate_ex_zones([ethanol], ventilation)
        self.assertEqual(len(zones), 1)
        self.assertIn(zones[0].type, ["Zone 0", "Zone 1", "Zone 2"])
```

### Phase 5: Report Generation & Quality Assurance (Woche 9-10)

#### Schritt 5.1: Gutachten-Generator
```python
# gui/components/report_generator.py
class BrandschutzReportGenerator:
    def __init__(self):
        self.template_engine = TemplateEngine()
        self.compliance_checker = ComplianceChecker()
        
    def generate_report(self, project_data: ProjectData) -> Report:
        """Generiert vollständiges Gutachten"""
        report = Report()
        
        # Strukturierte Abschnitte
        report.add_section(self.create_legal_basis_section(project_data))
        report.add_section(self.create_facility_description(project_data))
        report.add_section(self.create_hazard_analysis(project_data))
        report.add_section(self.create_protection_concept(project_data))
        report.add_section(self.create_measures_catalog(project_data))
        
        # Anhänge
        report.add_appendix(self.create_zone_plans(project_data))
        report.add_appendix(self.compile_evidence_documents(project_data))
        
        return report
    
    def validate_report_compliance(self, report: Report) -> ValidationResult:
        """Validiert Gutachten auf Vollständigkeit und Compliance"""
        return self.compliance_checker.validate(report)
```

#### Schritt 5.2: Quality Assurance Framework
```python
# gui/components/quality_assurance.py
class QualityAssuranceFramework:
    def __init__(self):
        self.checklist = self.load_qa_checklist()
        self.peer_review_system = PeerReviewSystem()
        
    def perform_quality_check(self, report: Report) -> QAResult:
        """Führt umfassende Qualitätsprüfung durch"""
        qa_result = QAResult()
        
        # Automatische Checks
        qa_result.completeness = self.check_completeness(report)
        qa_result.consistency = self.check_consistency(report)
        qa_result.compliance = self.check_regulatory_compliance(report)
        
        # Peer Review initiieren
        if qa_result.requires_peer_review():
            review_request = self.peer_review_system.create_request(report)
            qa_result.peer_review_id = review_request.id
        
        return qa_result
```

### Phase 6: Integration & Deployment (Woche 11-12)

#### Schritt 6.1: Plugin Integration
```python
# gui/plugins/brandschutz_explosionsschutz/plugin.py
class BrandschutzExplosionsschutzPlugin:
    def __init__(self):
        self.name = "Brandschutz & Explosionsschutz"
        self.version = "1.0.0"
        self.components = {
            "template_agent": BrandschutzTemplateAgent(),
            "requirements_agent": RequirementsAgent(),
            "document_analyzer": BrandschutzDocumentAnalyzer(),
            "analysis_engine": TechnicalAnalysisEngine(),
            "report_generator": BrandschutzReportGenerator(),
            "qa_framework": QualityAssuranceFramework()
        }
    
    def register(self, app):
        """Registriert Plugin in der Hauptanwendung"""
        app.register_plugin(self)
        app.add_navigation_item("Brandschutz-Gutachten", self.render_main_page)
```

## 🧪 Test-Strategie

### Unit Tests (Kontinuierlich)
```bash
# Einzelne Komponenten testen
pytest tests/test_brandschutz_template_agent.py -v
pytest tests/test_requirements_agent.py -v
pytest tests/test_technical_analysis_engine.py -v
```

### Integration Tests (Nach jeder Phase)
```bash
# Komponenten-Integration testen
pytest tests/integration/test_template_to_requirements.py -v
pytest tests/integration/test_analysis_to_report.py -v
```

### End-to-End Tests (Vor Release)
```bash
# Kompletter Workflow
pytest tests/e2e/test_complete_gutachten_workflow.py -v
```

### Performance Tests
```python
# tests/performance/test_report_generation_speed.py
def test_report_generation_performance():
    start_time = time.time()
    generator = BrandschutzReportGenerator()
    report = generator.generate_report(create_test_project_data())
    end_time = time.time()
    
    assert end_time - start_time < 5.0  # Max 5 Sekunden
```

## 📊 Metriken & Monitoring

### Erfolgs-Metriken
- **Code Coverage:** Minimum 80% pro Phase
- **Test Pass Rate:** 100% vor Phase-Abschluss
- **Performance:** Report-Generierung < 5 Sekunden
- **Compliance Score:** 100% für kritische Checks

### Monitoring Dashboard
```python
# gui/pages/brandschutz_dashboard.py
def render_dashboard():
    st.title("📊 Brandschutz-System Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Gutachten erstellt", "42", "+5 diese Woche")
    
    with col2:
        st.metric("Compliance Score", "98.5%", "+0.5%")
    
    with col3:
        st.metric("Ø Bearbeitungszeit", "3.2h", "-0.3h")
```

## 🔄 Continuous Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/brandschutz_tests.yml
name: Brandschutz System Tests

on:
  push:
    paths:
      - 'gui/components/brandschutz_*'
      - 'tests/test_brandschutz_*'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/test_brandschutz_* -v --cov
```

## 🚦 Go-Live Checkliste

### Vor jeder Phase
- [ ] Design Review abgeschlossen
- [ ] Test-Fälle definiert
- [ ] Dependencies dokumentiert

### Nach jeder Phase
- [ ] Alle Tests grün
- [ ] Code Review durchgeführt
- [ ] Dokumentation aktualisiert
- [ ] Integration getestet

### Vor Produktion
- [ ] Compliance-Validierung bestanden
- [ ] Performance-Tests erfolgreich
- [ ] Benutzer-Akzeptanz getestet
- [ ] Rollback-Plan erstellt

## 📝 Dokumentation

### Entwickler-Dokumentation
- API-Dokumentation für jede Komponente
- Architektur-Diagramme aktualisiert
- Test-Dokumentation

### Benutzer-Dokumentation
- Schritt-für-Schritt Anleitungen
- Video-Tutorials
- FAQ-Sektion

---

**Start:** KW 40/2025  
**Geplanter Go-Live:** KW 51/2025  
**Iterations-Zyklus:** 2 Wochen pro Phase