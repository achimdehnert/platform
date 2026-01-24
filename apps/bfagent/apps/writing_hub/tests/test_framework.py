"""
Agent Test Framework
====================

Umfangreiches Test-Framework für alle BF Agent Services.

Features:
- Mock LLM für deterministische Tests
- Fixture-basierte Testdaten
- Validierung von Input/Output Schemas
- Performance-Messung
- Snapshot-Tests für LLM-Prompts
"""

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type
from unittest.mock import MagicMock, patch
import logging

logger = logging.getLogger(__name__)


@dataclass
class MockLLMResponse:
    """Konfigurierbare Mock-Antwort für LLM-Tests."""
    content: str
    success: bool = True
    error: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=lambda: {"tokens_in": 100, "tokens_out": 200})
    latency_ms: int = 100


@dataclass
class TestCase:
    """Ein einzelner Testfall."""
    name: str
    description: str
    input_data: Dict[str, Any]
    expected_output_type: Type
    mock_response: MockLLMResponse
    validation_fn: Optional[Callable[[Any], bool]] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """Ergebnis eines Testlaufs."""
    test_name: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class AgentTestFramework:
    """
    Framework für das Testen von Agent Services.
    
    Verwendung:
        framework = AgentTestFramework()
        
        # Test mit Mock-LLM
        result = framework.run_test(
            service_class=CreativeAgentService,
            method_name="refine_idea",
            test_case=TestCase(...)
        )
        
        # Batch-Tests
        results = framework.run_all_tests(test_cases)
    """
    
    def __init__(self, fixtures_dir: Optional[Path] = None):
        self.fixtures_dir = fixtures_dir or Path(__file__).parent / "fixtures"
        self.results: List[TestResult] = []
        self.snapshots_dir = Path(__file__).parent / "snapshots"
        self.snapshots_dir.mkdir(exist_ok=True)
    
    def create_mock_llm(self, response: MockLLMResponse) -> MagicMock:
        """Erstellt einen Mock-LLM für Tests."""
        mock = MagicMock()
        mock.is_active = True
        mock.name = "Test-LLM"
        mock.provider = "mock"
        mock.llm_name = "mock-model"
        mock.api_key = "test-key"
        mock.api_endpoint = ""
        mock.max_tokens = 4096
        mock.temperature = 0.7
        return mock
    
    def run_test(
        self,
        service_class: Type,
        method_name: str,
        test_case: TestCase,
        mock_llm_call: bool = True
    ) -> TestResult:
        """
        Führt einen einzelnen Test durch.
        
        Args:
            service_class: Die zu testende Service-Klasse
            method_name: Name der zu testenden Methode
            test_case: Der Testfall
            mock_llm_call: Wenn True, wird der LLM-Call gemockt
        
        Returns:
            TestResult mit Ergebnis
        """
        start_time = time.time()
        
        try:
            mock_llm = self.create_mock_llm(test_case.mock_response)
            service = service_class(llm=mock_llm)
            
            if mock_llm_call:
                # Mock die _call_llm Methode
                with patch.object(service, '_call_llm') as mock_call:
                    mock_call.return_value = {
                        'success': test_case.mock_response.success,
                        'content': test_case.mock_response.content,
                        'error': test_case.mock_response.error,
                        'usage': test_case.mock_response.usage
                    }
                    
                    method = getattr(service, method_name)
                    result = method(**test_case.input_data)
            else:
                method = getattr(service, method_name)
                result = method(**test_case.input_data)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Validiere Output
            passed = True
            error = None
            details = {}
            
            # Type Check
            if not isinstance(result, test_case.expected_output_type):
                passed = False
                error = f"Falscher Output-Typ: erwartet {test_case.expected_output_type}, bekommen {type(result)}"
            
            # Custom Validation
            elif test_case.validation_fn:
                try:
                    if not test_case.validation_fn(result):
                        passed = False
                        error = "Custom Validation fehlgeschlagen"
                except Exception as e:
                    passed = False
                    error = f"Validation Exception: {str(e)}"
            
            # Details sammeln
            if hasattr(result, '__dict__'):
                details['result'] = {k: str(v)[:100] for k, v in vars(result).items()}
            
            return TestResult(
                test_name=test_case.name,
                passed=passed,
                duration_ms=duration_ms,
                error=error,
                details=details
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_case.name,
                passed=False,
                duration_ms=duration_ms,
                error=f"Exception: {str(e)}",
                details={"exception_type": type(e).__name__}
            )
    
    def run_all_tests(
        self,
        service_class: Type,
        method_name: str,
        test_cases: List[TestCase],
        stop_on_failure: bool = False
    ) -> List[TestResult]:
        """
        Führt alle Tests durch.
        
        Args:
            service_class: Die zu testende Service-Klasse
            method_name: Name der zu testenden Methode
            test_cases: Liste von Testfällen
            stop_on_failure: Bei True, stoppt beim ersten Fehler
        
        Returns:
            Liste von TestResults
        """
        self.results = []
        
        for test_case in test_cases:
            result = self.run_test(service_class, method_name, test_case)
            self.results.append(result)
            
            if stop_on_failure and not result.passed:
                break
        
        return self.results
    
    def save_snapshot(self, name: str, content: str) -> str:
        """Speichert einen Snapshot (z.B. LLM-Prompt) für Vergleiche."""
        hash_val = hashlib.md5(content.encode()).hexdigest()[:8]
        filename = f"{name}_{hash_val}.txt"
        filepath = self.snapshots_dir / filename
        filepath.write_text(content, encoding='utf-8')
        return str(filepath)
    
    def compare_snapshot(self, name: str, content: str) -> tuple[bool, Optional[str]]:
        """Vergleicht Content mit gespeichertem Snapshot."""
        hash_val = hashlib.md5(content.encode()).hexdigest()[:8]
        filename = f"{name}_{hash_val}.txt"
        filepath = self.snapshots_dir / filename
        
        if not filepath.exists():
            return False, f"Snapshot nicht gefunden: {filename}"
        
        saved = filepath.read_text(encoding='utf-8')
        if saved == content:
            return True, None
        else:
            return False, f"Snapshot unterscheidet sich"
    
    def generate_report(self) -> str:
        """Generiert einen Test-Report."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        total_time = sum(r.duration_ms for r in self.results)
        
        lines = [
            "=" * 60,
            "AGENT TEST REPORT",
            "=" * 60,
            f"Gesamt: {total} Tests",
            f"✅ Bestanden: {passed}",
            f"❌ Fehlgeschlagen: {failed}",
            f"⏱️ Gesamtzeit: {total_time:.2f}ms",
            "",
            "-" * 60,
            "DETAILS:",
            "-" * 60,
        ]
        
        for result in self.results:
            status = "✅" if result.passed else "❌"
            lines.append(f"{status} {result.test_name} ({result.duration_ms:.2f}ms)")
            if result.error:
                lines.append(f"   Error: {result.error}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# ============================================================
# Vordefinierte Test-Fixtures für Creative Agent
# ============================================================

CREATIVE_AGENT_FIXTURES = {
    "valid_idea_response": MockLLMResponse(
        content='''```json
{
    "title_sketch": "Der Letzte Wächter",
    "hook": "Ein alter Krieger muss sein Dorf vor einer uralten Bedrohung schützen",
    "genre": "Fantasy",
    "setting_sketch": "Mittelalterliche Welt mit Magie",
    "protagonist_sketch": "Ein müder Veteran, der eigentlich in Rente ist",
    "conflict_sketch": "Dunkle Mächte erwachen und bedrohen alles"
}
```''',
        success=True
    ),
    
    "valid_ideas_list_response": MockLLMResponse(
        content='''```json
[
    {
        "title_sketch": "Idee 1",
        "hook": "Eine spannende Geschichte über Abenteuer und Mut",
        "genre": "Fantasy"
    },
    {
        "title_sketch": "Idee 2", 
        "hook": "Ein Thriller über Verrat und Rache in der Großstadt",
        "genre": "Thriller"
    },
    {
        "title_sketch": "Idee 3",
        "hook": "Romantische Komödie über zwei Menschen die sich im Urlaub treffen",
        "genre": "Romance"
    }
]
```''',
        success=True
    ),
    
    "invalid_json_response": MockLLMResponse(
        content="Das ist keine JSON-Antwort, sondern nur Text.",
        success=True
    ),
    
    "error_response": MockLLMResponse(
        content="",
        success=False,
        error="API Rate Limit erreicht"
    ),
    
    "malformed_json_response": MockLLMResponse(
        content='```json\n{"title_sketch": "Test", "hook": "Kurz"\n```',  # Missing closing brace
        success=True
    ),
    
    "nested_json_response": MockLLMResponse(
        content='''Hier ist meine Idee:

```json
{
    "title_sketch": "Das Geheimnis der alten Bibliothek",
    "hook": "Eine junge Archäologin entdeckt in einer vergessenen Bibliothek ein Buch, das die Zukunft vorhersagt",
    "genre": "Mystery/Fantasy",
    "setting_sketch": "Eine verstaubte Universitätsbibliothek mit geheimen Gewölben",
    "protagonist_sketch": "Dr. Elena Voss, 32, brillante aber unterschätzte Historikerin",
    "conflict_sketch": "Eine geheime Gesellschaft will das Buch um jeden Preis",
    "characters": [
        {"name": "Elena Voss", "role": "Protagonist", "description": "Brillante Historikerin"},
        {"name": "Marcus Black", "role": "Antagonist", "description": "Anführer der Gesellschaft"}
    ],
    "world": {
        "name": "Moderne Welt mit versteckter Magie",
        "description": "Unsere Welt, aber mit verborgenen magischen Elementen",
        "key_features": ["Versteckte Bibliotheken", "Geheime Gesellschaften"],
        "atmosphere": "Mysteriös und spannend"
    }
}
```

Ich hoffe diese Idee gefällt dir!''',
        success=True
    ),
    
    "thinking_model_response": MockLLMResponse(
        content='''<think>
Der User möchte eine verbesserte Buchidee. Ich sollte den Titel origineller machen
und den Hook spannender gestalten.
</think>

```json
{
    "title_sketch": "Verbesserte Idee",
    "hook": "Eine dramatisch verbesserte Version der ursprünglichen Idee mit mehr Spannung",
    "genre": "Thriller"
}
```''',
        success=True
    ),
}


def get_creative_agent_test_cases() -> List[TestCase]:
    """Gibt vordefinierte Testfälle für den Creative Agent zurück."""
    from ..services.creative_agent_service import BrainstormResult, IdeaSketch
    
    return [
        TestCase(
            name="refine_idea_valid",
            description="Testet Verfeinerung mit gültiger LLM-Antwort",
            input_data={
                "idea": IdeaSketch(
                    title_sketch="Test",
                    hook="Ein kurzer Hook",
                    genre="Fantasy"
                ),
                "feedback": "Mache es spannender"
            },
            expected_output_type=BrainstormResult,
            mock_response=CREATIVE_AGENT_FIXTURES["valid_idea_response"],
            validation_fn=lambda r: r.success and len(r.ideas) > 0,
            tags=["refine", "happy_path"]
        ),
        
        TestCase(
            name="refine_idea_nested_json",
            description="Testet Verfeinerung mit verschachteltem JSON",
            input_data={
                "idea": IdeaSketch(
                    title_sketch="Test",
                    hook="Ein kurzer Hook"
                ),
                "feedback": "Mehr Details"
            },
            expected_output_type=BrainstormResult,
            mock_response=CREATIVE_AGENT_FIXTURES["nested_json_response"],
            validation_fn=lambda r: r.success and r.ideas[0].characters is not None,
            tags=["refine", "complex_json"]
        ),
        
        TestCase(
            name="refine_idea_thinking_model",
            description="Testet Verfeinerung mit <think> Tags",
            input_data={
                "idea": IdeaSketch(
                    title_sketch="Test",
                    hook="Ein kurzer Hook"
                ),
                "feedback": "Verbessere"
            },
            expected_output_type=BrainstormResult,
            mock_response=CREATIVE_AGENT_FIXTURES["thinking_model_response"],
            validation_fn=lambda r: r.success and "<think>" not in r.ideas[0].title_sketch,
            tags=["refine", "reasoning_model"]
        ),
        
        TestCase(
            name="refine_idea_error",
            description="Testet Fehlerbehandlung bei LLM-Fehler",
            input_data={
                "idea": IdeaSketch(
                    title_sketch="Test",
                    hook="Ein kurzer Hook"
                ),
                "feedback": "Test"
            },
            expected_output_type=BrainstormResult,
            mock_response=CREATIVE_AGENT_FIXTURES["error_response"],
            validation_fn=lambda r: not r.success and r.error != "",
            tags=["refine", "error_handling"]
        ),
        
        TestCase(
            name="refine_idea_invalid_json",
            description="Testet Fehlerbehandlung bei ungültigem JSON",
            input_data={
                "idea": IdeaSketch(
                    title_sketch="Test",
                    hook="Ein kurzer Hook"
                ),
                "feedback": "Test"
            },
            expected_output_type=BrainstormResult,
            mock_response=CREATIVE_AGENT_FIXTURES["invalid_json_response"],
            validation_fn=lambda r: not r.success or len(r.ideas) == 0,
            tags=["refine", "json_parsing"]
        ),
    ]
