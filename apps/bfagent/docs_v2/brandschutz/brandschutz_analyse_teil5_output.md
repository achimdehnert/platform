# Brandschutz-Experte: Teil 5 - Output-Generierung & Integration

## 13. Recommendation Engine

```python
# generators/recommendation_engine.py
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..models.analysis_result import Finding, AnalysisResult, RiskLevel, AnalysisStatus

class Priority(Enum):
    IMMEDIATE = 1  # Sofort umsetzen
    SHORT_TERM = 2  # Kurzfristig (< 3 Monate)
    MEDIUM_TERM = 3  # Mittelfristig (3-12 Monate)
    LONG_TERM = 4  # Langfristig (> 12 Monate)

@dataclass
class Recommendation:
    """Strukturierte Handlungsempfehlung"""
    id: str
    title: str
    description: str
    priority: Priority
    category: str
    related_findings: List[str] = field(default_factory=list)
    norm_references: List[str] = field(default_factory=list)
    estimated_cost: str = ""  # "gering", "mittel", "hoch"
    implementation_steps: List[str] = field(default_factory=list)

class RecommendationEngine:
    """Generiert Handlungsempfehlungen aus Analyseergebnissen"""
    
    # Mapping von Finding-Kategorien zu Empfehlungsvorlagen
    RECOMMENDATION_TEMPLATES = {
        'rettungsweg': {
            'length_exceeded': {
                'title': "Rettungsweglänge reduzieren",
                'steps': [
                    "Bauliche Prüfung der Fluchtwegsituation",
                    "Identifikation von Alternativ-Ausgängen",
                    "Ggf. Einbau zusätzlicher Notausgänge",
                    "Anpassung der Fluchtweg-Beschilderung",
                    "Aktualisierung des Fluchtplans"
                ],
                'cost': "hoch"
            },
            'width_insufficient': {
                'title': "Rettungswegbreite anpassen",
                'steps': [
                    "Prüfung der aktuellen Durchgangsbreiten",
                    "Entfernung von Hindernissen/Einbauten",
                    "Ggf. bauliche Erweiterung",
                    "Markierung der erforderlichen Fluchtwebreite"
                ],
                'cost': "mittel"
            },
            'missing_second': {
                'title': "Zweiten Rettungsweg schaffen",
                'steps': [
                    "Analyse der Gebäudestruktur",
                    "Prüfung von Rettungsgeräten der Feuerwehr als 2. RW",
                    "Planung eines baulichen 2. Rettungsweges",
                    "Abstimmung mit Bauaufsicht",
                    "Umsetzung und Dokumentation"
                ],
                'cost': "hoch"
            }
        },
        'brandabschnitt': {
            'size_exceeded': {
                'title': "Brandabschnitt unterteilen",
                'steps': [
                    "Analyse der Nutzungsbereiche",
                    "Planung zusätzlicher Brandwände",
                    "Auswahl geeigneter Feuerschutzabschlüsse",
                    "Bauliche Umsetzung",
                    "Abnahme durch Sachverständigen"
                ],
                'cost': "hoch"
            },
            'fire_resistance_insufficient': {
                'title': "Feuerwiderstand erhöhen",
                'steps': [
                    "Prüfung der vorhandenen Bauteile",
                    "Auswahl von Ertüchtigungsmaßnahmen",
                    "Brandschutzbeschichtung oder Verkleidung",
                    "Nachweisführung und Dokumentation"
                ],
                'cost': "mittel"
            }
        },
        'technik': {
            'bma_missing': {
                'title': "Brandmeldeanlage installieren",
                'steps': [
                    "Erforderlichkeitsprüfung",
                    "Konzepterstellung nach DIN 14675",
                    "Ausschreibung und Vergabe",
                    "Installation und Inbetriebnahme",
                    "Aufschaltung zur Feuerwehr",
                    "Abnahme und Wartungsvertrag"
                ],
                'cost': "hoch"
            },
            'extinguishers_insufficient': {
                'title': "Feuerlöscherausstattung ergänzen",
                'steps': [
                    "Berechnung nach ASR A2.2",
                    "Auswahl geeigneter Löschmittel",
                    "Beschaffung und Montage",
                    "Kennzeichnung gemäß ASR A1.3",
                    "Einweisung der Mitarbeiter"
                ],
                'cost': "gering"
            }
        },
        'organisation': {
            'fire_regulation_missing': {
                'title': "Brandschutzordnung erstellen",
                'steps': [
                    "Erfassung der Gebäudedaten",
                    "Erstellung Teil A (Aushang)",
                    "Erstellung Teil B (Mitarbeiter)",
                    "Ggf. Erstellung Teil C (Beauftragte)",
                    "Aushang und Verteilung",
                    "Schulung der Mitarbeiter"
                ],
                'cost': "gering"
            }
        },
        'vollständigkeit': {
            'section_missing': {
                'title': "Brandschutzkonzept vervollständigen",
                'steps': [
                    "Identifikation fehlender Inhalte",
                    "Erhebung der erforderlichen Daten",
                    "Ergänzung des Konzepts",
                    "Prüfung durch Brandschutzsachverständigen"
                ],
                'cost': "gering"
            }
        }
    }
    
    def __init__(self):
        self.recommendations: List[Recommendation] = []
    
    def generate_recommendations(
        self, 
        analysis_result: AnalysisResult
    ) -> List[Recommendation]:
        """Generiert Empfehlungen aus dem Analyseergebnis"""
        
        self.recommendations = []
        
        # Gruppiere Findings nach Kategorie
        findings_by_category = {}
        for finding in analysis_result.findings:
            findings_by_category.setdefault(finding.category, []).append(finding)
        
        # Generiere Empfehlungen pro Kategorie
        for category, findings in findings_by_category.items():
            self._process_category(category, findings)
        
        # Sortiere nach Priorität
        self.recommendations.sort(key=lambda r: r.priority.value)
        
        # Füge übergreifende Empfehlungen hinzu
        self._add_general_recommendations(analysis_result)
        
        return self.recommendations
    
    def _process_category(self, category: str, findings: List[Finding]):
        """Verarbeitet Findings einer Kategorie"""
        
        # Kritische Findings priorisieren
        critical = [f for f in findings if f.severity == RiskLevel.CRITICAL]
        high = [f for f in findings if f.severity == RiskLevel.HIGH]
        
        # Empfehlungen für kritische Findings
        for finding in critical:
            rec = self._create_recommendation(finding, Priority.IMMEDIATE)
            if rec:
                self.recommendations.append(rec)
        
        # Empfehlungen für hohe Findings
        for finding in high:
            rec = self._create_recommendation(finding, Priority.SHORT_TERM)
            if rec:
                self.recommendations.append(rec)
        
        # Restliche Findings gruppieren
        other = [f for f in findings if f.severity not in [RiskLevel.CRITICAL, RiskLevel.HIGH]]
        if other:
            rec = self._create_grouped_recommendation(category, other)
            if rec:
                self.recommendations.append(rec)
    
    def _create_recommendation(
        self, 
        finding: Finding, 
        priority: Priority
    ) -> Optional[Recommendation]:
        """Erstellt eine Empfehlung für ein Finding"""
        
        # Template suchen
        template_key = self._get_template_key(finding)
        templates = self.RECOMMENDATION_TEMPLATES.get(finding.category, {})
        template = templates.get(template_key)
        
        if template:
            return Recommendation(
                id=f"REC-{len(self.recommendations)+1:03d}",
                title=template['title'],
                description=finding.recommendation or finding.description,
                priority=priority,
                category=finding.category,
                related_findings=[finding.id],
                norm_references=[finding.norm_reference] if finding.norm_reference else [],
                estimated_cost=template.get('cost', 'mittel'),
                implementation_steps=template.get('steps', [])
            )
        else:
            # Generische Empfehlung
            return Recommendation(
                id=f"REC-{len(self.recommendations)+1:03d}",
                title=f"Mangel beheben: {finding.title}",
                description=finding.recommendation or "Siehe Befund für Details.",
                priority=priority,
                category=finding.category,
                related_findings=[finding.id],
                norm_references=[finding.norm_reference] if finding.norm_reference else [],
                estimated_cost="mittel",
                implementation_steps=["Prüfung der Situation", "Maßnahmenplanung", "Umsetzung", "Dokumentation"]
            )
    
    def _get_template_key(self, finding: Finding) -> str:
        """Ermittelt Template-Key anhand des Findings"""
        title_lower = finding.title.lower()
        
        if 'länge' in title_lower or 'length' in title_lower:
            return 'length_exceeded'
        if 'breite' in title_lower or 'width' in title_lower:
            return 'width_insufficient'
        if 'zweiter' in title_lower or 'zwei' in title_lower:
            return 'missing_second'
        if 'größe' in title_lower or 'size' in title_lower:
            return 'size_exceeded'
        if 'feuerwiderstand' in title_lower:
            return 'fire_resistance_insufficient'
        if 'brandmeldeanlage' in title_lower or 'bma' in title_lower:
            return 'bma_missing'
        if 'feuerlöscher' in title_lower:
            return 'extinguishers_insufficient'
        if 'brandschutzordnung' in title_lower:
            return 'fire_regulation_missing'
        if 'fehlt' in title_lower or 'unvollständig' in title_lower:
            return 'section_missing'
        
        return 'generic'
    
    def _create_grouped_recommendation(
        self, 
        category: str, 
        findings: List[Finding]
    ) -> Optional[Recommendation]:
        """Erstellt eine gruppierte Empfehlung für mehrere Findings"""
        
        if not findings:
            return None
        
        category_names = {
            'rettungsweg': 'Rettungswege',
            'brandabschnitt': 'Brandabschnitte',
            'technik': 'Technischer Brandschutz',
            'organisation': 'Organisation',
            'beschilderung': 'Beschilderung',
            'plan': 'Pläne',
            'vollständigkeit': 'Dokumentation'
        }
        
        return Recommendation(
            id=f"REC-{len(self.recommendations)+1:03d}",
            title=f"{category_names.get(category, category)}: Hinweise bearbeiten",
            description=f"{len(findings)} Hinweise im Bereich {category_names.get(category, category)} gefunden.",
            priority=Priority.MEDIUM_TERM,
            category=category,
            related_findings=[f.id for f in findings],
            estimated_cost="gering",
            implementation_steps=[
                "Alle Hinweise sichten",
                "Relevanz bewerten",
                "Maßnahmen planen",
                "Sukzessive Umsetzung"
            ]
        )
    
    def _add_general_recommendations(self, result: AnalysisResult):
        """Fügt allgemeine Empfehlungen hinzu"""
        
        # Bei niedrigem Vollständigkeits-Score
        if result.completeness_score < 70:
            self.recommendations.append(Recommendation(
                id=f"REC-{len(self.recommendations)+1:03d}",
                title="Brandschutzkonzept überarbeiten",
                description=f"Das Konzept erreicht nur {result.completeness_score:.0f}% Vollständigkeit.",
                priority=Priority.SHORT_TERM,
                category="allgemein",
                estimated_cost="mittel",
                implementation_steps=[
                    "Vollständigkeitsprüfung nach Checkliste",
                    "Fehlende Abschnitte identifizieren",
                    "Datenerhebung vor Ort",
                    "Konzept ergänzen",
                    "Erneute Prüfung"
                ]
            ))
```

---

## 14. Report Generator

```python
# generators/report_generator.py
from typing import List, Dict
from pathlib import Path
from datetime import datetime
import json

from ..models.analysis_result import AnalysisResult, Finding, RiskLevel, AnalysisStatus
from .recommendation_engine import Recommendation, Priority

class ReportGenerator:
    """Generiert Prüfberichte in verschiedenen Formaten"""
    
    def __init__(self, analysis_result: AnalysisResult, recommendations: List[Recommendation]):
        self.result = analysis_result
        self.recommendations = recommendations
        self.generated_at = datetime.now()
    
    def generate_markdown(self) -> str:
        """Generiert Markdown-Bericht"""
        
        lines = []
        
        # Header
        lines.append("# Brandschutz-Prüfbericht")
        lines.append("")
        lines.append(f"**Erstellt am:** {self.generated_at.strftime('%d.%m.%Y %H:%M')}")
        lines.append("")
        
        # Zusammenfassung
        lines.append("## Zusammenfassung")
        lines.append("")
        lines.append(f"- **Vollständigkeit:** {self.result.completeness_score:.0f}%")
        lines.append(f"- **Risikobewertung:** {self.result.risk_score:.0f}/100")
        lines.append(f"- **Kritische Mängel:** {len(self.result.critical_findings)}")
        lines.append(f"- **Hohe Risiken:** {len(self.result.high_risk_findings)}")
        lines.append(f"- **Gesamtbefunde:** {len(self.result.findings)}")
        lines.append("")
        
        if self.result.summary:
            lines.append(self.result.summary)
            lines.append("")
        
        # Kritische Mängel
        if self.result.critical_findings:
            lines.append("## Kritische Mängel (Sofortmaßnahmen erforderlich)")
            lines.append("")
            for finding in self.result.critical_findings:
                lines.append(self._format_finding_md(finding))
            lines.append("")
        
        # Weitere Befunde nach Kategorie
        lines.append("## Befunde nach Kategorie")
        lines.append("")
        
        categories = {}
        for finding in self.result.findings:
            if finding.severity != RiskLevel.CRITICAL:
                categories.setdefault(finding.category, []).append(finding)
        
        for category, findings in sorted(categories.items()):
            lines.append(f"### {category.title()}")
            lines.append("")
            for finding in findings:
                lines.append(self._format_finding_md(finding))
            lines.append("")
        
        # Handlungsempfehlungen
        lines.append("## Handlungsempfehlungen")
        lines.append("")
        
        for rec in self.recommendations:
            lines.append(self._format_recommendation_md(rec))
        
        return "\n".join(lines)
    
    def _format_finding_md(self, finding: Finding) -> str:
        """Formatiert ein Finding als Markdown"""
        
        severity_icons = {
            RiskLevel.CRITICAL: "🔴",
            RiskLevel.HIGH: "🟠",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.LOW: "🟢"
        }
        
        lines = []
        lines.append(f"#### {severity_icons.get(finding.severity, '⚪')} {finding.title}")
        lines.append(f"**Status:** {finding.status.value} | **Schwere:** {finding.severity.value}")
        lines.append("")
        lines.append(finding.description)
        
        if finding.norm_reference:
            lines.append(f"**Norm:** {finding.norm_reference}")
        if finding.location:
            lines.append(f"**Fundstelle:** {finding.location}")
        if finding.recommendation:
            lines.append(f"**Empfehlung:** {finding.recommendation}")
        
        lines.append("")
        return "\n".join(lines)
    
    def _format_recommendation_md(self, rec: Recommendation) -> str:
        """Formatiert eine Empfehlung als Markdown"""
        
        priority_labels = {
            Priority.IMMEDIATE: "🔴 SOFORT",
            Priority.SHORT_TERM: "🟠 Kurzfristig",
            Priority.MEDIUM_TERM: "🟡 Mittelfristig",
            Priority.LONG_TERM: "🟢 Langfristig"
        }
        
        lines = []
        lines.append(f"### {priority_labels.get(rec.priority, '')} {rec.title}")
        lines.append("")
        lines.append(rec.description)
        lines.append("")
        lines.append(f"**Geschätzte Kosten:** {rec.estimated_cost}")
        
        if rec.implementation_steps:
            lines.append("**Umsetzungsschritte:**")
            for i, step in enumerate(rec.implementation_steps, 1):
                lines.append(f"{i}. {step}")
        
        lines.append("")
        return "\n".join(lines)
    
    def generate_json(self) -> str:
        """Generiert JSON-Export"""
        
        data = {
            'generated_at': self.generated_at.isoformat(),
            'summary': {
                'completeness_score': self.result.completeness_score,
                'risk_score': self.result.risk_score,
                'total_findings': len(self.result.findings),
                'critical_findings': len(self.result.critical_findings),
            },
            'findings': [
                {
                    'id': f.id,
                    'category': f.category,
                    'title': f.title,
                    'description': f.description,
                    'severity': f.severity.value,
                    'status': f.status.value,
                    'norm_reference': f.norm_reference,
                    'recommendation': f.recommendation
                }
                for f in self.result.findings
            ],
            'recommendations': [
                {
                    'id': r.id,
                    'title': r.title,
                    'priority': r.priority.name,
                    'category': r.category,
                    'steps': r.implementation_steps,
                    'estimated_cost': r.estimated_cost
                }
                for r in self.recommendations
            ]
        }
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def save(self, output_path: Path, format: str = 'md'):
        """Speichert Bericht"""
        
        if format == 'md':
            content = self.generate_markdown()
            output_path.write_text(content, encoding='utf-8')
        elif format == 'json':
            content = self.generate_json()
            output_path.write_text(content, encoding='utf-8')
        else:
            raise ValueError(f"Unbekanntes Format: {format}")
```

---

## 15. CLI Interface

```python
# cli.py
import argparse
import sys
from pathlib import Path
from typing import Optional

from .parsers.pdf_parser import PDFParser
from .parsers.docx_parser import DOCXParser
from .parsers.cad_parser import CADParser
from .analyzers.concept_analyzer import ConceptAnalyzer
from .analyzers.plan_analyzer import PlanAnalyzer
from .generators.recommendation_engine import RecommendationEngine
from .generators.report_generator import ReportGenerator
from .models.analysis_result import AnalysisResult

def main():
    parser = argparse.ArgumentParser(
        description='Brandschutz-Experte: Analyse und Optimierung von Brandschutzkonzepten'
    )
    
    parser.add_argument(
        'input',
        type=Path,
        help='Eingabedatei (PDF, DOCX, DXF, DWG)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=None,
        help='Ausgabedatei für den Bericht'
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=['md', 'json'],
        default='md',
        help='Ausgabeformat (default: md)'
    )
    
    parser.add_argument(
        '--type',
        choices=['concept', 'plan', 'auto'],
        default='auto',
        help='Dokumenttyp (default: auto-detect)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Ausführliche Ausgabe'
    )
    
    args = parser.parse_args()
    
    # Eingabedatei prüfen
    if not args.input.exists():
        print(f"Fehler: Datei nicht gefunden: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Parser auswählen
        suffix = args.input.suffix.lower()
        
        if suffix == '.pdf':
            parser_instance = PDFParser(args.input)
            doc_type = 'concept'
        elif suffix == '.docx':
            parser_instance = DOCXParser(args.input)
            doc_type = 'concept'
        elif suffix in ['.dxf', '.dwg']:
            parser_instance = CADParser(args.input)
            doc_type = 'plan'
        else:
            print(f"Fehler: Nicht unterstütztes Format: {suffix}", file=sys.stderr)
            sys.exit(1)
        
        # Override doc_type wenn angegeben
        if args.type != 'auto':
            doc_type = args.type
        
        if args.verbose:
            print(f"Verarbeite: {args.input}")
            print(f"Dokumenttyp: {doc_type}")
        
        # Parsen
        parse_result = parser_instance.parse()
        
        if not parse_result.success:
            print(f"Fehler beim Parsen: {parse_result.errors}", file=sys.stderr)
            sys.exit(1)
        
        # Analyzer auswählen
        if doc_type == 'concept':
            analyzer = ConceptAnalyzer()
        else:
            analyzer = PlanAnalyzer()
        
        # Analyse durchführen
        findings = analyzer.analyze(parse_result.__dict__)
        
        if args.verbose:
            print(f"Gefundene Befunde: {len(findings)}")
        
        # Ergebnis erstellen
        analysis_result = AnalysisResult(
            concept=getattr(analyzer, 'concept', None),
            findings=findings,
            completeness_score=calculate_completeness(findings),
            risk_score=calculate_risk(findings)
        )
        
        # Empfehlungen generieren
        rec_engine = RecommendationEngine()
        recommendations = rec_engine.generate_recommendations(analysis_result)
        
        if args.verbose:
            print(f"Empfehlungen: {len(recommendations)}")
        
        # Bericht generieren
        report_gen = ReportGenerator(analysis_result, recommendations)
        
        if args.output:
            report_gen.save(args.output, args.format)
            print(f"Bericht gespeichert: {args.output}")
        else:
            # Ausgabe auf stdout
            if args.format == 'md':
                print(report_gen.generate_markdown())
            else:
                print(report_gen.generate_json())
        
    except Exception as e:
        print(f"Fehler: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def calculate_completeness(findings) -> float:
    """Berechnet Vollständigkeits-Score"""
    from .models.analysis_result import AnalysisStatus
    
    missing = len([f for f in findings if f.status == AnalysisStatus.MISSING])
    incomplete = len([f for f in findings if f.status == AnalysisStatus.INCOMPLETE])
    
    # Basis: 100%, Abzüge für Mängel
    score = 100 - (missing * 10) - (incomplete * 5)
    return max(0, min(100, score))

def calculate_risk(findings) -> float:
    """Berechnet Risiko-Score"""
    from .models.analysis_result import RiskLevel
    
    weights = {
        RiskLevel.CRITICAL: 25,
        RiskLevel.HIGH: 15,
        RiskLevel.MEDIUM: 5,
        RiskLevel.LOW: 1
    }
    
    score = sum(weights.get(f.severity, 0) for f in findings)
    return min(100, score)

if __name__ == '__main__':
    main()
```

---

## 16. Setup und Installation

### 16.1 requirements.txt

```
# Core
pymupdf>=1.23.0          # PDF parsing
python-docx>=1.1.0       # DOCX parsing
ezdxf>=1.3.0             # DXF/DWG parsing

# Utilities
pyyaml>=6.0              # Configuration
```

### 16.2 setup.py

```python
from setuptools import setup, find_packages

setup(
    name='brandschutz-experte',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'pymupdf>=1.23.0',
        'python-docx>=1.1.0',
        'ezdxf>=1.3.0',
        'pyyaml>=6.0',
    ],
    entry_points={
        'console_scripts': [
            'brandschutz=brandschutz_experte.cli:main',
        ],
    },
    python_requires='>=3.9',
)
```

---

## 17. Implementierungsreihenfolge (Zusammenfassung)

| Phase | Schritt | Dateien | Aufwand |
|-------|---------|---------|---------|
| **1** | 1.1 Projektstruktur | `__init__.py`, `models/` | 30 min |
| | 1.2 Datenmodelle | `models/document_types.py`, `models/analysis_result.py` | 1h |
| | 1.3 Base Parser | `parsers/base_parser.py` | 30 min |
| **2** | 2.1 PDF Parser | `parsers/pdf_parser.py` | 2h |
| | 2.2 DOCX Parser | `parsers/docx_parser.py` | 1h |
| | 2.3 CAD Parser | `parsers/cad_parser.py` | 3h |
| **3** | 3.1 Normendatenbank | `knowledge/norms.py` | 2h |
| | 3.2 Checklisten | `knowledge/checklists.py` | 2h |
| **4** | 4.1 Base Analyzer | `analyzers/base_analyzer.py` | 1h |
| | 4.2 Concept Analyzer | `analyzers/concept_analyzer.py` | 3h |
| | 4.3 Plan Analyzer | `analyzers/plan_analyzer.py` | 3h |
| **5** | 5.1 Recommendation Engine | `generators/recommendation_engine.py` | 2h |
| | 5.2 Report Generator | `generators/report_generator.py` | 2h |
| | 5.3 CLI | `cli.py` | 1h |

**Geschätzter Gesamtaufwand:** ~24h

---

## 18. Nächste Schritte

Das Konzept ist vollständig. Mögliche Erweiterungen:

1. **Word-Report-Export** (docx-js)
2. **Visualisierung** (CAD-Overlay mit Mängeln)
3. **LLM-Integration** (intelligente Textanalyse)
4. **Web-Interface** (FastAPI + React)

**Soll ich mit der Implementierung von Phase 1 beginnen?**
