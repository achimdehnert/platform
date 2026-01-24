# -*- coding: utf-8 -*-
"""
CodeQualityAgent - Erweiterte Code-Qualitätsanalyse.

Baut auf DjangoAgent auf und bietet zusätzliche Checks:
- Complexity Analysis (Zyklomatische Komplexität)
- Dead Code Detection
- Dependency Analysis
- Code Smell Detection
- Documentation Coverage

Kompatibel mit dem Orchestrator (BaseAgent).
"""
import re
import ast
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .orchestrator import BaseAgent, AgentState
from .django_agent import DjangoAgent, ValidationResult, ValidationError

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ComplexityResult:
    """Ergebnis einer Komplexitätsanalyse."""
    function_name: str
    complexity: int
    line: int
    rating: str  # A, B, C, D, F
    suggestion: Optional[str] = None


@dataclass
class QualityReport:
    """Vollständiger Qualitätsbericht."""
    file_path: str
    validation: ValidationResult
    complexity_score: float
    complexity_details: List[ComplexityResult] = field(default_factory=list)
    dead_code: List[Dict] = field(default_factory=list)
    code_smells: List[Dict] = field(default_factory=list)
    doc_coverage: float = 0.0
    overall_grade: str = "?"
    
    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "valid": self.validation.valid,
            "error_count": self.validation.error_count,
            "warning_count": self.validation.warning_count,
            "complexity_score": self.complexity_score,
            "doc_coverage": self.doc_coverage,
            "overall_grade": self.overall_grade,
            "complexity_details": [
                {"name": c.function_name, "complexity": c.complexity, "rating": c.rating}
                for c in self.complexity_details
            ],
            "dead_code_count": len(self.dead_code),
            "code_smell_count": len(self.code_smells),
        }


# =============================================================================
# COMPLEXITY THRESHOLDS
# =============================================================================

COMPLEXITY_THRESHOLDS = {
    "A": (1, 5),    # Simple, low risk
    "B": (6, 10),   # More complex, low risk
    "C": (11, 20),  # Complex, moderate risk
    "D": (21, 30),  # Very complex, high risk
    "F": (31, 999), # Untestable, very high risk
}


# =============================================================================
# CODE SMELL PATTERNS
# =============================================================================

CODE_SMELL_PATTERNS = {
    "god_class": {
        "check": lambda code: len(re.findall(r'def\s+\w+\s*\(', code)) > 20,
        "message": "God Class - zu viele Methoden (>20), aufteilen",
        "severity": "warning",
    },
    "long_method": {
        "check": lambda lines: any(len(lines[i:j]) > 50 
                                   for i in range(len(lines)) 
                                   for j in range(i, min(i+100, len(lines)))
                                   if lines[i].strip().startswith('def ')),
        "message": "Lange Methode - über 50 Zeilen, refactoren",
        "severity": "info",
    },
    "magic_numbers": {
        "pattern": r'(?<![a-zA-Z_])(?<!\.)\b(?!0\b|1\b|2\b|-1\b)[0-9]{2,}\b(?!\s*[:\]])',
        "message": "Magic Number - verwende benannte Konstante",
        "severity": "info",
    },
    "deep_nesting": {
        "pattern": r'^(\s{16,})(if|for|while|try)',
        "message": "Tiefe Verschachtelung (>4 Ebenen) - vereinfachen",
        "severity": "warning",
    },
    "empty_except": {
        "pattern": r'except\s*:\s*\n\s*pass',
        "message": "Leerer Exception-Handler - Fehler loggen oder behandeln",
        "severity": "warning",
    },
    "mutable_default": {
        "pattern": r'def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|\set\(\))',
        "message": "Mutable Default Argument - verwende None stattdessen",
        "severity": "error",
    },
    "hardcoded_path": {
        "pattern": r'["\'][A-Z]:\\|["\']\/home\/|["\']\/Users\/',
        "message": "Hardcoded Path - verwende Path oder Umgebungsvariable",
        "severity": "warning",
    },
    "commented_code": {
        "pattern": r'#\s*(def |class |import |from |if |for |while |return )',
        "message": "Auskommentierter Code - entfernen",
        "severity": "info",
    },
}


# =============================================================================
# CODE QUALITY AGENT
# =============================================================================

class CodeQualityAgent(BaseAgent):
    """
    Erweiterte Code-Qualitätsanalyse als orchestrierbarer Agent.
    
    Kombiniert DjangoAgent-Validierung mit:
    - Zyklomatischer Komplexität
    - Code Smell Detection
    - Dead Code Detection
    - Documentation Coverage
    
    Usage (standalone):
        agent = CodeQualityAgent()
        report = agent.analyze("code here", "file.py")
        
    Usage (in Pipeline):
        pipeline = Pipeline([
            CodeQualityAgent(),
            AutoFixAgent(),
        ])
        result = await pipeline.run(AgentState(data={"code": "...", "path": "..."}))
    """
    
    name = "CodeQualityAgent"
    
    def __init__(self, strict: bool = False):
        """
        Args:
            strict: Wenn True, werden auch Info-Level Issues als Warnings behandelt
        """
        self.strict = strict
        self.django_agent = DjangoAgent()
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Führt Qualitätsanalyse auf Code im State aus.
        
        Erwartet im State:
            - code: Der zu analysierende Code
            - path: Dateipfad (für Kontext)
            
        Setzt im State:
            - quality_report: Vollständiger QualityReport
            - quality_grade: Gesamtnote (A-F)
            - quality_issues: Liste der gefundenen Issues
        """
        code = state.get("code", "")
        file_path = state.get("path", "unknown.py")
        
        if not code:
            return state.with_error("No code provided for analysis")
        
        report = self.analyze(code, file_path)
        
        return state.with_data(
            quality_report=report.to_dict(),
            quality_grade=report.overall_grade,
            quality_issues=len(report.code_smells) + len(report.dead_code),
        )
    
    def analyze(self, code: str, file_path: str = "unknown.py") -> QualityReport:
        """
        Vollständige Qualitätsanalyse.
        
        Args:
            code: Python-Code
            file_path: Dateipfad
            
        Returns:
            QualityReport mit allen Analyseergebnissen
        """
        # 1. Django Validation
        validation = self.django_agent.validate_python_file(code, file_path)
        
        # 2. Complexity Analysis
        complexity_details = self._analyze_complexity(code)
        complexity_score = self._calculate_complexity_score(complexity_details)
        
        # 3. Code Smell Detection
        code_smells = self._detect_code_smells(code)
        
        # 4. Dead Code Detection
        dead_code = self._detect_dead_code(code)
        
        # 5. Documentation Coverage
        doc_coverage = self._calculate_doc_coverage(code)
        
        # 6. Overall Grade
        overall_grade = self._calculate_overall_grade(
            validation, complexity_score, code_smells, dead_code, doc_coverage
        )
        
        return QualityReport(
            file_path=file_path,
            validation=validation,
            complexity_score=complexity_score,
            complexity_details=complexity_details,
            dead_code=dead_code,
            code_smells=code_smells,
            doc_coverage=doc_coverage,
            overall_grade=overall_grade,
        )
    
    def quick_check(self, code: str) -> Tuple[str, List[str]]:
        """
        Schnelle Qualitätsprüfung.
        
        Returns:
            Tuple (grade, issues)
        """
        report = self.analyze(code)
        issues = []
        
        for smell in report.code_smells:
            issues.append(f"[{smell['type']}] {smell['message']}")
        
        for dead in report.dead_code:
            issues.append(f"[dead_code] {dead['name']} at line {dead['line']}")
        
        return report.overall_grade, issues
    
    def _analyze_complexity(self, code: str) -> List[ComplexityResult]:
        """Analysiert zyklomatische Komplexität pro Funktion."""
        results = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return results
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_cyclomatic_complexity(node)
                rating = self._get_complexity_rating(complexity)
                
                suggestion = None
                if rating in ("D", "F"):
                    suggestion = "Funktion aufteilen oder vereinfachen"
                elif rating == "C":
                    suggestion = "Überprüfen ob Vereinfachung möglich"
                
                results.append(ComplexityResult(
                    function_name=node.name,
                    complexity=complexity,
                    line=node.lineno,
                    rating=rating,
                    suggestion=suggestion,
                ))
        
        return results
    
    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """
        Berechnet zyklomatische Komplexität für einen AST-Knoten.
        
        CC = E - N + 2P
        Vereinfacht: 1 + Anzahl der Verzweigungen
        """
        complexity = 1  # Basis
        
        for child in ast.walk(node):
            # Verzweigungen
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.With, ast.AsyncWith)):
                complexity += 1
            # Boolean Operatoren
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            # Comprehensions
            elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                complexity += sum(1 for _ in child.generators)
            # Ternary
            elif isinstance(child, ast.IfExp):
                complexity += 1
        
        return complexity
    
    def _get_complexity_rating(self, complexity: int) -> str:
        """Gibt Rating basierend auf Komplexität."""
        for rating, (low, high) in COMPLEXITY_THRESHOLDS.items():
            if low <= complexity <= high:
                return rating
        return "F"
    
    def _calculate_complexity_score(self, details: List[ComplexityResult]) -> float:
        """Berechnet Durchschnitts-Komplexitätsscore."""
        if not details:
            return 0.0
        return sum(d.complexity for d in details) / len(details)
    
    def _detect_code_smells(self, code: str) -> List[Dict]:
        """Erkennt Code Smells."""
        smells = []
        lines = code.split('\n')
        
        for smell_name, config in CODE_SMELL_PATTERNS.items():
            if "pattern" in config:
                for i, line in enumerate(lines, 1):
                    if re.search(config["pattern"], line):
                        smells.append({
                            "type": smell_name,
                            "message": config["message"],
                            "severity": config["severity"],
                            "line": i,
                        })
                        break  # One per type
            elif "check" in config:
                try:
                    if config["check"](code if "lines" not in str(config["check"]) else lines):
                        smells.append({
                            "type": smell_name,
                            "message": config["message"],
                            "severity": config["severity"],
                            "line": None,
                        })
                except Exception:
                    pass
        
        return smells
    
    def _detect_dead_code(self, code: str) -> List[Dict]:
        """Erkennt potenziell toten Code."""
        dead = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return dead
        
        # Sammle alle definierten Namen
        defined_functions = set()
        defined_classes = set()
        used_names = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private/dunder methods
                if not node.name.startswith('_'):
                    defined_functions.add((node.name, node.lineno))
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith('_'):
                    defined_classes.add((node.name, node.lineno))
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                used_names.add(node.attr)
        
        # Finde unbenutzte (vereinfachte Heuristik)
        for name, line in defined_functions:
            if name not in used_names and name != 'main':
                dead.append({
                    "type": "function",
                    "name": name,
                    "line": line,
                    "reason": "Wird nirgends aufgerufen",
                })
        
        return dead
    
    def _calculate_doc_coverage(self, code: str) -> float:
        """Berechnet Docstring-Abdeckung."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return 0.0
        
        total = 0
        documented = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                total += 1
                if ast.get_docstring(node):
                    documented += 1
        
        return (documented / total * 100) if total > 0 else 100.0
    
    def _calculate_overall_grade(
        self,
        validation: ValidationResult,
        complexity: float,
        smells: List[Dict],
        dead_code: List[Dict],
        doc_coverage: float,
    ) -> str:
        """Berechnet Gesamtnote."""
        score = 100
        
        # Validation Errors
        score -= validation.error_count * 10
        score -= validation.warning_count * 2
        
        # Complexity
        if complexity > 20:
            score -= 20
        elif complexity > 10:
            score -= 10
        elif complexity > 5:
            score -= 5
        
        # Code Smells
        for smell in smells:
            if smell["severity"] == "error":
                score -= 10
            elif smell["severity"] == "warning":
                score -= 5
            else:
                score -= 2
        
        # Dead Code
        score -= len(dead_code) * 3
        
        # Doc Coverage
        if doc_coverage < 50:
            score -= 10
        elif doc_coverage < 80:
            score -= 5
        
        # Grade
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_code_quality(code: str, file_path: str = "unknown.py") -> QualityReport:
    """
    Convenience-Funktion für Code-Qualitätsanalyse.
    
    Usage:
        from apps.bfagent.agents import analyze_code_quality
        
        report = analyze_code_quality(code, "views.py")
        print(f"Grade: {report.overall_grade}")
    """
    agent = CodeQualityAgent()
    return agent.analyze(code, file_path)


def quick_quality_check(code: str) -> Tuple[str, List[str]]:
    """
    Schnelle Qualitätsprüfung.
    
    Returns:
        Tuple (grade, list of issues)
    """
    agent = CodeQualityAgent()
    return agent.quick_check(code)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "CodeQualityAgent",
    "QualityReport",
    "ComplexityResult",
    "analyze_code_quality",
    "quick_quality_check",
]
