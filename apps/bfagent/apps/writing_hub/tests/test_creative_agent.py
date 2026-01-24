"""
Tests für Creative Agent Service
================================

Pytest-basierte Tests mit dem Agent Test Framework.
"""

import pytest
import json
from unittest.mock import MagicMock, patch

from apps.writing_hub.services.schemas import (
    IdeaSchema, 
    IdeasListSchema, 
    PremiseSchema,
    LLMResponseParser,
    get_idea_json_schema
)
from apps.writing_hub.services.creative_agent_service import (
    CreativeAgentService,
    IdeaSketch,
    BrainstormResult,
    CharacterSketch,
    WorldSketch
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_llm():
    """Erstellt einen Mock-LLM für Tests."""
    mock = MagicMock()
    mock.is_active = True
    mock.name = "Test-LLM"
    mock.provider = "openai"
    mock.llm_name = "gpt-4o-mini"
    mock.api_key = "test-key"
    mock.api_endpoint = ""
    mock.max_tokens = 4096
    mock.temperature = 0.7
    return mock


@pytest.fixture
def service(mock_llm):
    """Erstellt einen Creative Agent Service mit Mock-LLM."""
    return CreativeAgentService(llm=mock_llm)


@pytest.fixture
def sample_idea():
    """Eine Beispiel-Idee für Tests."""
    return IdeaSketch(
        title_sketch="Der Letzte Wächter",
        hook="Ein alter Krieger muss sein Dorf vor einer uralten Bedrohung schützen",
        genre="Fantasy",
        setting_sketch="Mittelalterliche Welt",
        protagonist_sketch="Ein müder Veteran",
        conflict_sketch="Dunkle Mächte erwachen"
    )


# ============================================================
# Schema Validation Tests
# ============================================================

class TestIdeaSchema:
    """Tests für IdeaSchema Validierung."""
    
    def test_valid_idea(self):
        """Testet Validierung einer gültigen Idee."""
        data = {
            "title_sketch": "Test Titel",
            "hook": "Ein spannender Hook für die Geschichte",
            "genre": "Fantasy"
        }
        idea = IdeaSchema.model_validate(data)
        assert idea.title_sketch == "Test Titel"
        assert idea.hook == "Ein spannender Hook für die Geschichte"
        assert idea.genre == "Fantasy"
    
    def test_alternative_keys(self):
        """Testet Mapping von alternativen Feldnamen."""
        data = {
            "title": "Alternativer Titel",  # statt title_sketch
            "logline": "Ein spannender Hook",  # statt hook
            "setting": "Eine interessante Welt"  # statt setting_sketch
        }
        idea = IdeaSchema.model_validate(data)
        assert idea.title_sketch == "Alternativer Titel"
        assert idea.hook == "Ein spannender Hook"
        assert idea.setting_sketch == "Eine interessante Welt"
    
    def test_missing_required_fields(self):
        """Testet Fehler bei fehlenden Pflichtfeldern."""
        data = {"genre": "Fantasy"}  # title_sketch und hook fehlen
        with pytest.raises(Exception):
            IdeaSchema.model_validate(data)
    
    def test_hook_too_short(self):
        """Testet Validierung der minimalen Hook-Länge."""
        data = {
            "title_sketch": "Test",
            "hook": "Kurz"  # Weniger als 10 Zeichen
        }
        with pytest.raises(Exception):
            IdeaSchema.model_validate(data)
    
    def test_with_characters(self):
        """Testet Idee mit Charakteren."""
        data = {
            "title_sketch": "Test",
            "hook": "Ein spannender Hook für die Geschichte",
            "characters": [
                {"name": "Hero", "role": "Protagonist", "description": "Der Held"},
                {"name": "Villain", "role": "Antagonist", "description": "Der Böse"}
            ]
        }
        idea = IdeaSchema.model_validate(data)
        assert len(idea.characters) == 2
        assert idea.characters[0].name == "Hero"
        assert idea.characters[1].role == "Antagonist"
    
    def test_with_world(self):
        """Testet Idee mit Weltenbau."""
        data = {
            "title_sketch": "Test",
            "hook": "Ein spannender Hook für die Geschichte",
            "world": {
                "name": "Fantasia",
                "description": "Eine magische Welt",
                "key_features": ["Drachen", "Magie"],
                "atmosphere": "Mystisch"
            }
        }
        idea = IdeaSchema.model_validate(data)
        assert idea.world is not None
        assert idea.world.name == "Fantasia"
        assert "Drachen" in idea.world.key_features


# ============================================================
# LLM Response Parser Tests
# ============================================================

class TestLLMResponseParser:
    """Tests für den LLM Response Parser."""
    
    def test_extract_json_from_code_block(self):
        """Testet JSON-Extraktion aus Code-Block."""
        content = '''```json
{"title_sketch": "Test", "hook": "Ein spannender Hook"}
```'''
        result = LLMResponseParser.extract_json(content)
        assert result is not None
        assert result["title_sketch"] == "Test"
    
    def test_extract_json_from_plain_text(self):
        """Testet JSON-Extraktion aus reinem Text."""
        content = '{"title_sketch": "Test", "hook": "Ein spannender Hook"}'
        result = LLMResponseParser.extract_json(content)
        assert result is not None
        assert result["title_sketch"] == "Test"
    
    def test_extract_json_with_surrounding_text(self):
        """Testet JSON-Extraktion mit umgebendem Text."""
        content = '''Hier ist meine Idee:
{"title_sketch": "Test", "hook": "Ein spannender Hook für die Geschichte"}
Das ist der Rest.'''
        result = LLMResponseParser.extract_json(content)
        assert result is not None
        assert result["title_sketch"] == "Test"
    
    def test_extract_json_array(self):
        """Testet Extraktion eines JSON-Arrays."""
        content = '''```json
[
    {"title_sketch": "Idee 1", "hook": "Hook eins ist hier"},
    {"title_sketch": "Idee 2", "hook": "Hook zwei ist hier"}
]
```'''
        result = LLMResponseParser.extract_json(content)
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2
    
    def test_extract_json_removes_think_tags(self):
        """Testet Entfernung von <think> Tags."""
        content = '''<think>
Hier denke ich nach...
</think>
{"title_sketch": "Test", "hook": "Ein spannender Hook für die Geschichte"}'''
        result = LLMResponseParser.extract_json(content)
        assert result is not None
        assert result["title_sketch"] == "Test"
    
    def test_extract_json_invalid(self):
        """Testet Fehlerbehandlung bei ungültigem JSON."""
        content = "Das ist kein JSON, sondern nur Text."
        result = LLMResponseParser.extract_json(content)
        assert result is None
    
    def test_parse_idea_success(self):
        """Testet erfolgreiche Idee-Parsing."""
        content = '''```json
{
    "title_sketch": "Der Letzte Wächter",
    "hook": "Ein alter Krieger muss sein Dorf vor einer uralten Bedrohung schützen"
}
```'''
        idea, error = LLMResponseParser.parse_idea(content)
        assert error is None
        assert idea is not None
        assert idea.title_sketch == "Der Letzte Wächter"
    
    def test_parse_idea_from_list(self):
        """Testet Idee-Parsing aus einer Liste (nimmt erste)."""
        content = '''{"ideas": [
    {"title_sketch": "Erste Idee", "hook": "Hook für die erste Idee"},
    {"title_sketch": "Zweite Idee", "hook": "Hook für die zweite Idee"}
]}'''
        idea, error = LLMResponseParser.parse_idea(content)
        assert error is None
        assert idea is not None
        assert idea.title_sketch == "Erste Idee"
    
    def test_parse_ideas_list_success(self):
        """Testet erfolgreiche Listen-Parsing."""
        content = '''[
    {"title_sketch": "Idee 1", "hook": "Hook für Idee eins hier"},
    {"title_sketch": "Idee 2", "hook": "Hook für Idee zwei hier"},
    {"title_sketch": "Idee 3", "hook": "Hook für Idee drei hier"}
]'''
        ideas, error = LLMResponseParser.parse_ideas_list(content)
        assert error is None
        assert len(ideas) == 3
        assert ideas[0].title_sketch == "Idee 1"
    
    def test_parse_ideas_list_partial_valid(self):
        """Testet Listen-Parsing mit teilweise ungültigen Einträgen."""
        content = '''[
    {"title_sketch": "Gültige Idee", "hook": "Ein gültiger Hook hier"},
    {"invalid": "data"},
    {"title_sketch": "Noch eine gültige Idee", "hook": "Noch ein gültiger Hook"}
]'''
        ideas, error = LLMResponseParser.parse_ideas_list(content)
        # Sollte mindestens die gültigen Ideen parsen
        assert len(ideas) >= 1


# ============================================================
# Creative Agent Service Tests
# ============================================================

class TestCreativeAgentService:
    """Tests für den Creative Agent Service."""
    
    def test_init_with_llm(self, mock_llm):
        """Testet Service-Initialisierung mit LLM."""
        service = CreativeAgentService(llm=mock_llm)
        assert service.llm == mock_llm
    
    def test_init_without_llm(self):
        """Testet Service-Initialisierung ohne LLM."""
        service = CreativeAgentService()
        assert service.llm is None
    
    @patch('apps.bfagent.services.llm_client.generate_text')
    def test_refine_idea_success(self, mock_generate, service, sample_idea):
        """Testet erfolgreiche Ideen-Verfeinerung."""
        mock_generate.return_value = {
            'success': True,
            'text': '''```json
{
    "title_sketch": "Der Letzte Wächter: Dämmerung des Lichts",
    "hook": "Ein alter Krieger kämpft gegen seine eigene Vergangenheit und eine uralte Bedrohung",
    "genre": "Dark Fantasy",
    "setting_sketch": "Eine zerfallende mittelalterliche Welt",
    "protagonist_sketch": "Ein vom Krieg gezeichneter Veteran mit dunklem Geheimnis",
    "conflict_sketch": "Innere Dämonen und äußere Feinde drohen alles zu vernichten"
}
```''',
            'error': None,
            'usage': {'tokens_in': 100, 'tokens_out': 200}
        }
        
        result = service.refine_idea(sample_idea, "Mache es dunkler und dramatischer")
        
        assert result.success
        assert len(result.ideas) > 0
        assert "Dämmerung" in result.ideas[0].title_sketch or "Wächter" in result.ideas[0].title_sketch
    
    @patch('apps.bfagent.services.llm_client.generate_text')
    def test_refine_idea_llm_error(self, mock_generate, service, sample_idea):
        """Testet Fehlerbehandlung bei LLM-Fehler."""
        mock_generate.return_value = {
            'success': False,
            'text': None,
            'error': 'API Rate Limit erreicht',
            'usage': None
        }
        
        result = service.refine_idea(sample_idea, "Test")
        
        assert not result.success
        assert result.error != ""
    
    @patch('apps.bfagent.services.llm_client.generate_text')
    def test_refine_idea_invalid_json(self, mock_generate, service, sample_idea):
        """Testet Fehlerbehandlung bei ungültigem JSON."""
        mock_generate.return_value = {
            'success': True,
            'text': 'Das ist keine JSON-Antwort',
            'error': None,
            'usage': {'tokens_in': 50, 'tokens_out': 20}
        }
        
        result = service.refine_idea(sample_idea, "Test")
        
        # Sollte entweder fehlschlagen oder leere Ideen zurückgeben
        assert not result.success or len(result.ideas) == 0
    
    @patch('apps.bfagent.services.llm_client.generate_text')
    def test_generate_ideas_success(self, mock_generate, service):
        """Testet erfolgreiche Ideen-Generierung."""
        mock_generate.return_value = {
            'success': True,
            'text': '''```json
[
    {"title_sketch": "Idee 1", "hook": "Ein spannender Hook für die erste Idee", "genre": "Fantasy"},
    {"title_sketch": "Idee 2", "hook": "Ein spannender Hook für die zweite Idee", "genre": "Thriller"},
    {"title_sketch": "Idee 3", "hook": "Ein spannender Hook für die dritte Idee", "genre": "Romance"}
]
```''',
            'error': None,
            'usage': {'tokens_in': 100, 'tokens_out': 300}
        }
        
        result = service.generate_ideas("Ich möchte eine Geschichte über Abenteuer")
        
        assert result.success
        assert len(result.ideas) >= 1


# ============================================================
# Integration Tests
# ============================================================

@pytest.mark.integration
class TestCreativeAgentIntegration:
    """Integration Tests - benötigen echte DB und evtl. LLM."""
    
    @pytest.mark.django_db
    def test_service_with_db_llm(self):
        """Testet Service mit LLM aus der Datenbank."""
        from apps.bfagent.models import Llms
        
        llm = Llms.objects.filter(is_active=True).first()
        if llm is None:
            pytest.skip("Kein aktives LLM in der Datenbank")
        
        service = CreativeAgentService(llm=llm)
        assert service.llm is not None


# ============================================================
# JSON Schema Tests
# ============================================================

class TestJSONSchema:
    """Tests für JSON Schema Generation."""
    
    def test_idea_json_schema(self):
        """Testet JSON Schema für Idee."""
        schema = get_idea_json_schema()
        
        assert "properties" in schema
        assert "title_sketch" in schema["properties"]
        assert "hook" in schema["properties"]
    
    def test_schema_can_validate(self):
        """Testet dass Schema zur Validierung verwendet werden kann."""
        schema = get_idea_json_schema()
        
        # Schema sollte required fields definieren
        assert "required" in schema or "title_sketch" in schema.get("properties", {})


# ============================================================
# Run all tests with: pytest apps/writing_hub/tests/test_creative_agent.py -v
# ============================================================
