"""
Integration Tests for Handler Generator Agent
Tests complete workflow from description to deployment
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from apps.bfagent.agents.handler_generator.agent import HandlerGeneratorAgent
from apps.bfagent.services.handlers.config_models import (
    HandlerRequirements,
    GeneratedHandler
)


class TestHandlerGeneratorAgent:
    """Test Handler Generator Agent end-to-end"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return HandlerGeneratorAgent(llm_provider="anthropic")
    
    @pytest.fixture
    def mock_llm_response_requirements(self):
        """Mock LLM response for requirements analysis"""
        return HandlerRequirements(
            handler_id="pdf_text_extractor",
            display_name="PDF Text Extractor",
            description="Extracts text from PDF files",
            category="input",
            dependencies=["pdfplumber"],
            config_parameters={
                "ocr_enabled": {
                    "type": "boolean",
                    "default": False
                },
                "pages": {
                    "type": "string",
                    "default": "all"
                }
            },
            input_requirements=["file_path"],
            output_format={"text": "string", "page_count": "integer"},
            error_scenarios={"missing_file": "raise FileNotFoundError"}
        )
    
    @pytest.fixture
    def mock_llm_response_generated(self):
        """Mock LLM response for code generation"""
        return GeneratedHandler(
            handler_code="""
from typing import Dict, Any
from apps.bfagent.services.handlers.base import BaseInputHandler

class PDFTextExtractorHandler(BaseInputHandler):
    display_name = "PDF Text Extractor"
    description = "Extracts text from PDF files"
    version = "1.0.0"
    
    def execute(self, context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        return {"text": "Sample text", "page_count": 1}
""",
            config_model_code="""
from pydantic import Field
from apps.bfagent.services.handlers.config_models import BaseHandlerConfig

class PDFTextExtractorConfig(BaseHandlerConfig):
    ocr_enabled: bool = Field(default=False)
    pages: str = Field(default="all")
""",
            test_code="""
import pytest
from apps.bfagent.services.handlers.input.pdf_text_extractor import PDFTextExtractorHandler

class TestPDFTextExtractorHandler:
    @pytest.fixture
    def handler(self):
        return PDFTextExtractorHandler()
    
    def test_execute(self, handler):
        context = {'file_path': 'test.pdf'}
        config = {}
        result = handler.execute(context, config)
        assert 'text' in result
        assert 'page_count' in result
""",
            documentation="# PDF Text Extractor\n\nExtracts text from PDF files.",
            example_usage="handler = PDFTextExtractorHandler()\nresult = handler.execute({}, {})"
        )
    
    def test_requirements_analysis_structure(self, agent, mock_llm_response_requirements):
        """Test requirements analysis returns correct structure"""
        with patch.object(agent.llm, 'generate_with_fallback', return_value=mock_llm_response_requirements):
            result = agent._analyze_requirements("Extract text from PDFs")
            
            assert isinstance(result, HandlerRequirements)
            assert result.handler_id == "pdf_text_extractor"
            assert result.category == "input"
            assert len(result.dependencies) > 0
    
    def test_code_generation_structure(self, agent, mock_llm_response_requirements, mock_llm_response_generated):
        """Test code generation returns correct structure"""
        with patch.object(agent.llm, 'generate_with_fallback', return_value=mock_llm_response_generated):
            result = agent._generate_code(mock_llm_response_requirements)
            
            assert isinstance(result, GeneratedHandler)
            assert len(result.handler_code) > 0
            assert len(result.config_model_code) > 0
            assert len(result.test_code) > 0
            assert len(result.documentation) > 0
    
    def test_validation_success(self, agent, mock_llm_response_generated):
        """Test validation passes for valid code"""
        validation = agent._quick_validate(mock_llm_response_generated)
        
        assert validation.is_valid
        assert validation.syntax_valid
        assert len(validation.syntax_errors) == 0
    
    def test_validation_fails_on_syntax_error(self, agent):
        """Test validation fails on syntax errors"""
        bad_code = GeneratedHandler(
            handler_code="class BadHandler:\n    def (invalid syntax",
            config_model_code="class Config:\n    pass",
            test_code="def test():\n    pass",
            documentation="docs",
            example_usage="example"
        )
        
        validation = agent._quick_validate(bad_code)
        
        assert not validation.is_valid
        assert not validation.syntax_valid
        assert len(validation.syntax_errors) > 0
    
    def test_generate_handler_workflow(
        self,
        agent,
        mock_llm_response_requirements,
        mock_llm_response_generated
    ):
        """Test complete handler generation workflow"""
        with patch.object(agent.llm, 'generate_with_fallback') as mock_llm:
            # Mock LLM calls
            mock_llm.side_effect = [
                mock_llm_response_requirements,
                mock_llm_response_generated
            ]
            
            result = agent.generate_handler(
                description="Extract text from PDFs",
                auto_deploy=False
            )
            
            assert result['requirements'].handler_id == "pdf_text_extractor"
            assert result['generated'].handler_code is not None
            assert result['validation'].is_valid
            assert not result['deployed']
            assert result['handler'] is None
    
    @pytest.mark.integration
    def test_deploy_handler_transaction_rollback(self, agent, mock_llm_response_requirements):
        """Test deployment rolls back on error"""
        bad_code = GeneratedHandler(
            handler_code="INVALID PYTHON CODE",
            config_model_code="class Config: pass",
            test_code="def test(): pass",
            documentation="docs",
            example_usage="example"
        )
        
        with pytest.raises(Exception):
            agent.deploy_handler(
                requirements=mock_llm_response_requirements,
                generated=bad_code
            )
        
        # Verify no handler was created in DB
        from apps.bfagent.models_handlers import Handler
        assert not Handler.objects.filter(handler_id="pdf_text_extractor").exists()
    
    def test_regenerate_with_feedback(
        self,
        agent,
        mock_llm_response_requirements,
        mock_llm_response_generated
    ):
        """Test handler regeneration with feedback"""
        with patch.object(agent.llm, 'generate_with_fallback', return_value=mock_llm_response_generated):
            result = agent.regenerate_handler(
                requirements=mock_llm_response_requirements,
                feedback="Add caching support"
            )
            
            assert isinstance(result, GeneratedHandler)
            assert result.handler_code is not None


class TestPromptBuilder:
    """Test prompt building"""
    
    def test_requirements_prompt_contains_description(self):
        """Test requirements prompt includes user description"""
        from apps.bfagent.agents.handler_generator.prompts import PromptBuilder
        
        builder = PromptBuilder()
        prompt = builder.build_requirements_prompt("Extract PDF text")
        
        assert "Extract PDF text" in prompt
        assert "handler_id" in prompt
        assert "category" in prompt
    
    def test_generation_prompt_contains_requirements(self):
        """Test generation prompt includes all requirements"""
        from apps.bfagent.agents.handler_generator.prompts import PromptBuilder
        
        requirements = HandlerRequirements(
            handler_id="test_handler",
            display_name="Test Handler",
            description="Test description",
            category="input",
            dependencies=[],
            config_parameters={},
            input_requirements=[],
            output_format={},
            error_scenarios={}
        )
        
        builder = PromptBuilder()
        prompt = builder.build_generation_prompt(requirements)
        
        assert "test_handler" in prompt
        assert "Test Handler" in prompt
        assert "handler_code" in prompt
        assert "test_code" in prompt


class TestDeploymentManager:
    """Test deployment manager"""
    
    def test_atomic_deployment_context_manager(self):
        """Test atomic deployment context manager"""
        from apps.bfagent.agents.handler_generator.deployment import HandlerDeploymentManager
        
        manager = HandlerDeploymentManager()
        
        try:
            with manager.atomic_deployment() as ctx:
                assert 'temp_files' in ctx
                raise Exception("Test rollback")
        except Exception:
            pass  # Expected
    
    def test_class_name_generation(self):
        """Test handler class name generation"""
        from apps.bfagent.agents.handler_generator.deployment import HandlerDeploymentManager
        
        manager = HandlerDeploymentManager()
        
        assert manager._get_class_name("pdf_extractor") == "PdfExtractorHandler"
        assert manager._get_class_name("simple_handler") == "SimpleHandlerHandler"
    
    def test_config_class_name_generation(self):
        """Test config class name generation"""
        from apps.bfagent.agents.handler_generator.deployment import HandlerDeploymentManager
        
        manager = HandlerDeploymentManager()
        
        assert manager._get_config_class_name("pdf_extractor") == "PdfExtractorConfig"


class TestStructuredLLMClient:
    """Test structured LLM client"""
    
    @pytest.mark.skipif(
        True,
        reason="Requires API keys - run manually with real credentials"
    )
    def test_anthropic_structured_generation(self):
        """Test Anthropic structured generation (manual test)"""
        from apps.bfagent.agents.handler_generator.llm_client import StructuredLLMClient
        from pydantic import BaseModel, Field
        
        class TestModel(BaseModel):
            name: str = Field(..., description="Name field")
            age: int = Field(..., description="Age field")
        
        client = StructuredLLMClient(provider="anthropic")
        result = client.generate_structured(
            prompt="Extract: John is 30 years old",
            response_model=TestModel
        )
        
        assert isinstance(result, TestModel)
        assert result.name == "John"
        assert result.age == 30


# ============================================================================
# INTEGRATION TESTS (require full setup)
# ============================================================================

@pytest.mark.integration
@pytest.mark.django_db
class TestHandlerGeneratorIntegration:
    """Full integration tests with database"""
    
    def test_full_workflow_mock_llm(self):
        """Test complete workflow with mocked LLM"""
        agent = HandlerGeneratorAgent()
        
        mock_requirements = HandlerRequirements(
            handler_id="simple_test",
            display_name="Simple Test",
            description="Simple test handler",
            category="input",
            dependencies=[],
            config_parameters={},
            input_requirements=[],
            output_format={},
            error_scenarios={}
        )
        
        mock_generated = GeneratedHandler(
            handler_code="""
from typing import Dict, Any
from apps.bfagent.services.handlers.base import BaseInputHandler

class SimpleTestHandler(BaseInputHandler):
    display_name = "Simple Test"
    version = "1.0.0"
    
    def execute(self, context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        return {"result": "test"}
""",
            config_model_code="""
from apps.bfagent.services.handlers.config_models import BaseHandlerConfig

class SimpleTestConfig(BaseHandlerConfig):
    pass
""",
            test_code="""
import pytest

def test_simple():
    assert True
""",
            documentation="# Simple Test",
            example_usage="handler = SimpleTestHandler()"
        )
        
        with patch.object(agent.llm, 'generate_with_fallback') as mock_llm:
            mock_llm.side_effect = [mock_requirements, mock_generated]
            
            result = agent.generate_handler(
                description="Simple test handler",
                auto_deploy=False
            )
            
            assert result['success'] or 'requirements' in result
            assert result['validation'].syntax_valid


# Run with: pytest tests/test_handler_generator.py -v
# Integration tests: pytest tests/test_handler_generator.py -v -m integration
