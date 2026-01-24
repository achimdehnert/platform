"""
BF Agent MCP Server - Code Generators
======================================

Template- und AI-gestützte Code-Generierung.

Design:
- Strategy Pattern: Verschiedene Generator-Strategien
- Template + AI Hybrid: Basis-Template + AI-Enhancement
- Extensible: Neue Generator einfach hinzufügbar

Generator-Hierarchie:
- BaseGenerator (Abstract)
- TemplateGenerator (Jinja2-basiert)
- AIEnhancedGenerator (Template + AI)
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from string import Template
from typing import Any, Dict, List, Optional

from ..core import (
    HandlerType,
    AIProvider,
    GeneratedCode,
    DomainScaffold,
    CodeGenerationError,
    AIServiceError,
)


# =============================================================================
# TEMPLATES
# =============================================================================

HANDLER_TEMPLATE = '''"""
${handler_name}
${"=" * len(handler_name)}

${description}

Domain: ${domain}
Handler Type: ${handler_type}
Generated: ${timestamp}
Version: 2.0
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict

from apps.core.handlers.base import BaseHandler, HandlerResult
from apps.core.handlers.registry import register_handler
${ai_imports}

logger = logging.getLogger(__name__)


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class ${schema_prefix}Input(BaseModel):
    """
    Input schema for ${handler_name}.
    
    Attributes:
${input_fields_docs}
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
        validate_assignment=True
    )
    
${input_fields}


class ${schema_prefix}Output(BaseModel):
    """
    Output schema for ${handler_name}.
    
    Attributes:
${output_fields_docs}
    """
    model_config = ConfigDict(extra='forbid')
    
${output_fields}


# =============================================================================
# HANDLER IMPLEMENTATION
# =============================================================================

@register_handler(
    name="${handler_name}",
    domain="${domain}",
    handler_type="${handler_type}",
    description="${description_short}"
)
class ${handler_name}(BaseHandler):
    """
    ${description}
    
    Three-Phase Pattern:
        1. validate() - Input validation with Pydantic
        2. process() - Core business logic
        3. save_result() - Persist to database
    
    Attributes:
        input_schema: ${schema_prefix}Input
        output_schema: ${schema_prefix}Output
    """
    
    input_schema = ${schema_prefix}Input
    output_schema = ${schema_prefix}Output
    
    def __init__(self):
        """Initialize handler with dependencies."""
        super().__init__()
        self.logger = logger
${ai_init}
    
    async def validate(self, context: Dict[str, Any]) -> ${schema_prefix}Input:
        """
        Phase 1: Validate input data.
        
        Validates raw input context against Pydantic schema.
        
        Args:
            context: Raw input data from workflow
            
        Returns:
            Validated input model
            
        Raises:
            ValidationError: If input data is invalid
        """
        self.logger.debug(f"Validating input for {self.__class__.__name__}")
        return self.input_schema(**context)
    
    async def process(
        self, 
        validated_input: ${schema_prefix}Input
    ) -> ${schema_prefix}Output:
        """
        Phase 2: Execute core business logic.
        
        This is where the main processing happens.
        
        Args:
            validated_input: Validated input from Phase 1
            
        Returns:
            Processing result as output schema
            
        Raises:
            ProcessingError: If processing fails
        """
        self.logger.info(f"Processing {self.__class__.__name__}")
        
        try:
            # TODO: Implement your business logic here
            # Example:
            # result = await self._do_processing(validated_input)
            
            result = {
${output_defaults}
            }
            
            return self.output_schema(**result)
            
        except Exception as e:
            self.logger.error(f"Processing error in {self.__class__.__name__}: {e}")
            raise
    
    async def save_result(
        self, 
        result: ${schema_prefix}Output,
        context: Dict[str, Any]
    ) -> HandlerResult:
        """
        Phase 3: Persist result to database.
        
        Saves the processing result and returns execution status.
        
        Args:
            result: Processing result from Phase 2
            context: Original context for reference
            
        Returns:
            HandlerResult with success status and data
        """
        self.logger.debug(f"Saving result for {self.__class__.__name__}")
        
        # TODO: Implement persistence if needed
        # Example:
        # await self._save_to_database(result, context)
        
        return HandlerResult(
            success=True,
            data=result.model_dump(),
            message=f"{self.__class__.__name__} completed successfully"
        )
    
    async def execute(self, context: Dict[str, Any]) -> HandlerResult:
        """
        Main execution method following three-phase pattern.
        
        Orchestrates the complete handler lifecycle:
        validate → process → save_result
        
        Args:
            context: Input context from workflow
            
        Returns:
            HandlerResult with execution outcome
        """
        try:
            # Phase 1: Validate
            validated = await self.validate(context)
            
            # Phase 2: Process
            result = await self.process(validated)
            
            # Phase 3: Save
            return await self.save_result(result, context)
            
        except Exception as e:
            self.logger.exception(f"Handler execution failed: {e}")
            return HandlerResult(
                success=False,
                error=str(e),
                message=f"{self.__class__.__name__} failed"
            )
'''


TEST_TEMPLATE = '''"""
Tests for ${handler_name}
${"=" * (len(handler_name) + 10)}

Comprehensive test suite following pytest best practices.

Generated: ${timestamp}
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from apps.${domain}.handlers.${module_name} import (
    ${handler_name},
    ${schema_prefix}Input,
    ${schema_prefix}Output,
)
from apps.core.handlers.base import HandlerResult


class Test${handler_name}:
    """Test suite for ${handler_name}."""
    
    # =========================================================================
    # FIXTURES
    # =========================================================================
    
    @pytest.fixture
    def handler(self):
        """Create handler instance for testing."""
        return ${handler_name}()
    
    @pytest.fixture
    def valid_input(self) -> dict:
        """Create valid input data for testing."""
        return {
${test_input_data}
        }
    
    @pytest.fixture
    def invalid_input(self) -> dict:
        """Create invalid input data for testing."""
        return {}  # Empty dict should fail validation
    
    # =========================================================================
    # VALIDATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_validate_success(self, handler, valid_input):
        """Test successful input validation."""
        result = await handler.validate(valid_input)
        
        assert isinstance(result, ${schema_prefix}Input)
${validation_assertions}
    
    @pytest.mark.asyncio
    async def test_validate_invalid_input_raises_error(self, handler, invalid_input):
        """Test validation with invalid input raises ValidationError."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            await handler.validate(invalid_input)
    
    @pytest.mark.asyncio
    async def test_validate_extra_fields_rejected(self, handler, valid_input):
        """Test that extra fields are rejected (extra='forbid')."""
        from pydantic import ValidationError
        
        valid_input["unexpected_field"] = "should fail"
        
        with pytest.raises(ValidationError):
            await handler.validate(valid_input)
    
    # =========================================================================
    # PROCESSING TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_process_success(self, handler, valid_input):
        """Test successful processing."""
        validated = await handler.validate(valid_input)
        result = await handler.process(validated)
        
        assert isinstance(result, ${schema_prefix}Output)
    
    @pytest.mark.asyncio
    async def test_process_returns_expected_fields(self, handler, valid_input):
        """Test that process returns all expected output fields."""
        validated = await handler.validate(valid_input)
        result = await handler.process(validated)
        
        # Check all output fields are present
        result_dict = result.model_dump()
${output_field_assertions}
    
    # =========================================================================
    # SAVE RESULT TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_save_result_success(self, handler, valid_input):
        """Test successful result saving."""
        validated = await handler.validate(valid_input)
        processed = await handler.process(validated)
        result = await handler.save_result(processed, valid_input)
        
        assert isinstance(result, HandlerResult)
        assert result.success is True
        assert result.data is not None
    
    # =========================================================================
    # FULL EXECUTION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_execute_full_workflow_success(self, handler, valid_input):
        """Test complete handler execution (all three phases)."""
        result = await handler.execute(valid_input)
        
        assert isinstance(result, HandlerResult)
        assert result.success is True
        assert result.data is not None
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_execute_handles_validation_errors(self, handler, invalid_input):
        """Test that execute handles validation errors gracefully."""
        result = await handler.execute(invalid_input)
        
        assert isinstance(result, HandlerResult)
        assert result.success is False
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_execute_handles_processing_errors(self, handler, valid_input):
        """Test that execute handles processing errors gracefully."""
        with patch.object(handler, 'process', side_effect=Exception("Test error")):
            result = await handler.execute(valid_input)
        
        assert result.success is False
        assert "Test error" in result.error
    
    # =========================================================================
    # EDGE CASES
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_handler_is_idempotent(self, handler, valid_input):
        """Test that handler can be called multiple times with same input."""
        result1 = await handler.execute(valid_input)
        result2 = await handler.execute(valid_input)
        
        assert result1.success == result2.success
    
    @pytest.mark.asyncio
    async def test_handler_logging(self, handler, valid_input, caplog):
        """Test that handler logs appropriately."""
        import logging
        
        with caplog.at_level(logging.DEBUG):
            await handler.execute(valid_input)
        
        assert any("${handler_name}" in record.message for record in caplog.records)
'''


DOMAIN_MODELS_TEMPLATE = '''"""
${display_name} - Domain Models
${"=" * (len(display_name) + 16)}

${description}

Generated: ${timestamp}
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel, AuditModel, SoftDeleteModel


class ${model_name}Project(AuditModel, SoftDeleteModel):
    """
    Main project model for ${display_name} domain.
    
    Represents a single workflow instance with all associated data.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        IN_PROGRESS = 'in_progress', _('In Progress')
        REVIEW = 'review', _('In Review')
        COMPLETED = 'completed', _('Completed')
        ARCHIVED = 'archived', _('Archived')
    
    # Core Fields
    name = models.CharField(
        max_length=200,
        verbose_name=_('Project Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_('Status'),
        db_index=True
    )
    
    # Workflow Tracking
    current_phase = models.CharField(
        max_length=50,
        default='${first_phase}',
        verbose_name=_('Current Phase')
    )
    
    # Metadata (flexible JSON storage)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metadata')
    )
    
    class Meta:
        verbose_name = _('${display_name} Project')
        verbose_name_plural = _('${display_name} Projects')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['current_phase']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @classmethod
    def get_phases(cls) -> list:
        """Return list of workflow phases."""
        return ${phases_list}
    
    def advance_phase(self) -> bool:
        """
        Move to next workflow phase.
        
        Returns:
            True if advanced, False if already at last phase
        """
        phases = self.get_phases()
        try:
            current_idx = [p.lower() for p in phases].index(self.current_phase.lower())
            if current_idx < len(phases) - 1:
                self.current_phase = phases[current_idx + 1].lower()
                self.save(update_fields=['current_phase', 'updated_at'])
                return True
        except ValueError:
            pass
        return False


class ${model_name}Result(TimeStampedModel):
    """
    Stores processing results for ${display_name} workflows.
    
    One result per handler execution within a project.
    """
    
    project = models.ForeignKey(
        ${model_name}Project,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name=_('Project')
    )
    handler_name = models.CharField(
        max_length=100,
        verbose_name=_('Handler'),
        db_index=True
    )
    phase = models.CharField(
        max_length=50,
        verbose_name=_('Phase')
    )
    
    # Result Data
    result_data = models.JSONField(
        default=dict,
        verbose_name=_('Result Data')
    )
    
    # Status
    success = models.BooleanField(
        default=True,
        verbose_name=_('Success'),
        db_index=True
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    
    # Performance
    execution_time_ms = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Execution Time (ms)')
    )
    
    class Meta:
        verbose_name = _('${display_name} Result')
        verbose_name_plural = _('${display_name} Results')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'handler_name']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.handler_name} ({self.phase})"
'''


DOMAIN_ADMIN_TEMPLATE = '''"""
${display_name} - Django Admin Configuration
${"=" * (len(display_name) + 32)}

Generated: ${timestamp}
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import ${model_name}Project, ${model_name}Result


@admin.register(${model_name}Project)
class ${model_name}ProjectAdmin(admin.ModelAdmin):
    """Admin configuration for ${display_name} projects."""
    
    list_display = [
        'name',
        'status_badge',
        'current_phase',
        'created_at',
        'updated_at',
    ]
    list_filter = ['status', 'current_phase', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'status')
        }),
        ('Workflow', {
            'fields': ('current_phase', 'metadata')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'draft': '#6B7280',
            'in_progress': '#3B82F6',
            'review': '#F59E0B',
            'completed': '#10B981',
            'archived': '#9CA3AF',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 500;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Set created_by/updated_by on save."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(${model_name}Result)
class ${model_name}ResultAdmin(admin.ModelAdmin):
    """Admin configuration for ${display_name} results."""
    
    list_display = [
        'project',
        'handler_name',
        'phase',
        'success_badge',
        'execution_time_display',
        'created_at',
    ]
    list_filter = ['success', 'phase', 'handler_name', 'created_at']
    search_fields = ['project__name', 'handler_name', 'error_message']
    readonly_fields = ['created_at']
    raw_id_fields = ['project']
    
    def success_badge(self, obj):
        """Display success status as badge."""
        if obj.success:
            return format_html(
                '<span style="color: #10B981; font-weight: bold;">✓ Success</span>'
            )
        return format_html(
            '<span style="color: #EF4444; font-weight: bold;">✗ Failed</span>'
        )
    success_badge.short_description = 'Status'
    
    def execution_time_display(self, obj):
        """Display execution time formatted."""
        if obj.execution_time_ms > 1000:
            return f"{obj.execution_time_ms / 1000:.2f}s"
        return f"{obj.execution_time_ms}ms"
    execution_time_display.short_description = 'Duration'
'''


# =============================================================================
# BASE GENERATOR
# =============================================================================

class BaseGenerator(ABC):
    """Abstract base class for code generators."""
    
    @abstractmethod
    async def generate_handler(
        self,
        name: str,
        domain: str,
        handler_type: HandlerType,
        description: str,
        input_fields: List[str],
        output_fields: List[str],
        ai_provider: Optional[AIProvider] = None,
    ) -> GeneratedCode:
        """Generate handler code."""
        ...
    
    @abstractmethod
    async def generate_domain(
        self,
        domain_id: str,
        display_name: str,
        description: str,
        phases: List[str],
    ) -> DomainScaffold:
        """Generate domain scaffold."""
        ...


# =============================================================================
# TEMPLATE GENERATOR
# =============================================================================

class TemplateGenerator(BaseGenerator):
    """
    Template-based code generator.
    
    Uses string templates for consistent, high-quality code generation.
    """
    
    def _generate_field_definitions(
        self, 
        fields: List[str], 
        is_output: bool = False
    ) -> tuple[str, str]:
        """
        Generate Pydantic field definitions and docs.
        
        Returns:
            Tuple of (field_definitions, field_docs)
        """
        if not fields:
            return "    pass  # Add fields here", "        (none defined)"
        
        definitions = []
        docs = []
        
        for field in fields:
            field_name = field.strip().lower().replace(' ', '_').replace('-', '_')
            field_title = field.replace('_', ' ').title()
            
            if is_output:
                # Output fields have defaults
                definitions.append(
                    f'    {field_name}: str = Field(default="", description="{field_title}")'
                )
            else:
                # Input fields are required
                definitions.append(
                    f'    {field_name}: str = Field(..., description="{field_title}")'
                )
            
            docs.append(f'        {field_name}: {field_title}')
        
        return '\n'.join(definitions), '\n'.join(docs)
    
    def _generate_output_defaults(self, fields: List[str]) -> str:
        """Generate default output values for template."""
        if not fields:
            return '                # Add output fields here'
        
        defaults = []
        for field in fields:
            field_name = field.strip().lower().replace(' ', '_').replace('-', '_')
            defaults.append(f'                "{field_name}": "",  # TODO: Set actual value')
        
        return '\n'.join(defaults)
    
    def _generate_test_input_data(self, fields: List[str]) -> str:
        """Generate test input data."""
        if not fields:
            return '            # Add test data here'
        
        data = []
        for field in fields:
            field_name = field.strip().lower().replace(' ', '_').replace('-', '_')
            data.append(f'            "{field_name}": "test_{field_name}_value",')
        
        return '\n'.join(data)
    
    def _generate_validation_assertions(self, fields: List[str]) -> str:
        """Generate validation assertions for tests."""
        if not fields:
            return '        # Add assertions here'
        
        assertions = []
        for field in fields:
            field_name = field.strip().lower().replace(' ', '_').replace('-', '_')
            assertions.append(f'        assert result.{field_name} == valid_input["{field_name}"]')
        
        return '\n'.join(assertions)
    
    def _generate_output_field_assertions(self, fields: List[str]) -> str:
        """Generate output field assertions for tests."""
        if not fields:
            return '        # Add assertions here'
        
        assertions = []
        for field in fields:
            field_name = field.strip().lower().replace(' ', '_').replace('-', '_')
            assertions.append(f'        assert "{field_name}" in result_dict')
        
        return '\n'.join(assertions)
    
    async def generate_handler(
        self,
        name: str,
        domain: str,
        handler_type: HandlerType,
        description: str,
        input_fields: List[str],
        output_fields: List[str],
        ai_provider: Optional[AIProvider] = None,
        include_tests: bool = True,
        include_docstrings: bool = True,
    ) -> GeneratedCode:
        """
        Generate handler code from template.
        
        Args:
            name: Handler name
            domain: Target domain
            handler_type: Handler type
            description: Handler description
            input_fields: Input field names
            output_fields: Output field names
            ai_provider: AI provider (for ai_powered handlers)
            include_tests: Generate test file
            include_docstrings: Include detailed docstrings
            
        Returns:
            GeneratedCode with handler, test, and schema code
        """
        # Ensure handler name follows convention
        if not name.endswith('Handler'):
            name = f"{name}Handler"
        if name[0].islower():
            name = name[0].upper() + name[1:]
        
        # Generate schema prefix (handler name without "Handler" suffix)
        schema_prefix = name.replace('Handler', '')
        
        # Generate field definitions
        input_defs, input_docs = self._generate_field_definitions(input_fields, is_output=False)
        output_defs, output_docs = self._generate_field_definitions(output_fields, is_output=True)
        
        # AI-specific imports and init
        ai_imports = ""
        ai_init = ""
        if handler_type == HandlerType.AI_POWERED and ai_provider:
            ai_imports = "from apps.core.services.ai_service import AIService"
            ai_init = "        self.ai_service = AIService()"
        
        # Module name for imports
        module_name = name.lower().replace('handler', '')
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate handler code
        # Using simple string replacement instead of Template for complex cases
        handler_code = HANDLER_TEMPLATE
        handler_code = handler_code.replace('${handler_name}', name)
        handler_code = handler_code.replace('${"=" * len(handler_name)}', '=' * len(name))
        handler_code = handler_code.replace('${description}', description)
        handler_code = handler_code.replace('${description_short}', description[:100])
        handler_code = handler_code.replace('${domain}', domain)
        handler_code = handler_code.replace('${handler_type}', handler_type.value)
        handler_code = handler_code.replace('${timestamp}', timestamp)
        handler_code = handler_code.replace('${schema_prefix}', schema_prefix)
        handler_code = handler_code.replace('${input_fields}', input_defs)
        handler_code = handler_code.replace('${input_fields_docs}', input_docs)
        handler_code = handler_code.replace('${output_fields}', output_defs)
        handler_code = handler_code.replace('${output_fields_docs}', output_docs)
        handler_code = handler_code.replace('${output_defaults}', self._generate_output_defaults(output_fields))
        handler_code = handler_code.replace('${ai_imports}', ai_imports)
        handler_code = handler_code.replace('${ai_init}', ai_init)
        
        # Generate test code
        test_code = ""
        if include_tests:
            test_code = TEST_TEMPLATE
            test_code = test_code.replace('${handler_name}', name)
            test_code = test_code.replace('${"=" * (len(handler_name) + 10)}', '=' * (len(name) + 10))
            test_code = test_code.replace('${timestamp}', timestamp)
            test_code = test_code.replace('${domain}', domain)
            test_code = test_code.replace('${module_name}', module_name)
            test_code = test_code.replace('${schema_prefix}', schema_prefix)
            test_code = test_code.replace('${test_input_data}', self._generate_test_input_data(input_fields))
            test_code = test_code.replace('${validation_assertions}', self._generate_validation_assertions(input_fields))
            test_code = test_code.replace('${output_field_assertions}', self._generate_output_field_assertions(output_fields))
        
        return GeneratedCode(
            handler_code=handler_code,
            test_code=test_code,
            schema_code="",  # Schemas are included in handler code
            handler_filename=f"{module_name}.py",
            test_filename=f"test_{module_name}.py",
            schema_filename="",
            metadata={
                "handler_name": name,
                "domain": domain,
                "handler_type": handler_type.value,
                "generated_at": timestamp,
                "generator": "TemplateGenerator",
            }
        )
    
    async def generate_domain(
        self,
        domain_id: str,
        display_name: str,
        description: str,
        phases: List[str],
        include_admin: bool = True,
        include_tests: bool = True,
    ) -> DomainScaffold:
        """
        Generate domain scaffold.
        
        Args:
            domain_id: Domain identifier (slug)
            display_name: Human-readable name
            description: Domain description
            phases: Workflow phases
            include_admin: Generate admin.py
            include_tests: Generate test structure
            
        Returns:
            DomainScaffold with all generated files
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Model name (PascalCase from domain_id)
        model_name = ''.join(word.title() for word in domain_id.split('_'))
        
        # Normalize phases
        phases = [p.strip().title() for p in phases if p.strip()]
        first_phase = phases[0].lower() if phases else 'start'
        
        files: Dict[str, str] = {}
        
        # Generate models.py
        models_code = DOMAIN_MODELS_TEMPLATE
        models_code = models_code.replace('${display_name}', display_name)
        models_code = models_code.replace('${"=" * (len(display_name) + 16)}', '=' * (len(display_name) + 16))
        models_code = models_code.replace('${description}', description)
        models_code = models_code.replace('${timestamp}', timestamp)
        models_code = models_code.replace('${model_name}', model_name)
        models_code = models_code.replace('${first_phase}', first_phase)
        models_code = models_code.replace('${phases_list}', str(phases))
        files['models.py'] = models_code
        
        # Generate admin.py
        if include_admin:
            admin_code = DOMAIN_ADMIN_TEMPLATE
            admin_code = admin_code.replace('${display_name}', display_name)
            admin_code = admin_code.replace('${"=" * (len(display_name) + 32)}', '=' * (len(display_name) + 32))
            admin_code = admin_code.replace('${timestamp}', timestamp)
            admin_code = admin_code.replace('${model_name}', model_name)
            files['admin.py'] = admin_code
        
        # Generate __init__.py
        files['__init__.py'] = f'''"""
{display_name} Domain
{'=' * (len(display_name) + 7)}

{description}
"""

default_app_config = 'apps.{domain_id}.apps.{model_name}Config'
'''
        
        # Generate apps.py
        files['apps.py'] = f'''"""
{display_name} - App Configuration
"""

from django.apps import AppConfig


class {model_name}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.{domain_id}'
    verbose_name = '{display_name}'
    
    def ready(self):
        # Import handlers for auto-registration
        from . import handlers  # noqa
'''
        
        # Generate handlers/__init__.py
        files['handlers/__init__.py'] = f'''"""
{display_name} - Handler Registry
{'=' * (len(display_name) + 19)}

All handlers for the {display_name} domain.
Import handlers here for auto-registration.
"""

# Import handlers here
# from .my_handler import MyHandler

__all__ = []
'''
        
        # Generate directory structure
        directory_structure = f"""
apps/{domain_id}/
├── __init__.py
├── apps.py
├── models.py
├── admin.py
├── urls.py (create manually)
├── views.py (create manually)
├── handlers/
│   ├── __init__.py
│   └── (handler files)
├── templates/{domain_id}/
│   └── (template files)
└── tests/
    ├── __init__.py
    └── (test files)
"""
        
        return DomainScaffold(
            files=files,
            directory_structure=directory_structure,
            metadata={
                "domain_id": domain_id,
                "display_name": display_name,
                "phases": phases,
                "generated_at": timestamp,
                "generator": "TemplateGenerator",
            }
        )


# =============================================================================
# AI-ENHANCED GENERATOR
# =============================================================================

class AIEnhancedGenerator(TemplateGenerator):
    """
    AI-enhanced code generator.
    
    Uses templates as base and enhances with AI for:
    - Better docstrings
    - Implementation suggestions
    - Edge case handling
    """
    
    def __init__(self, ai_client=None):
        """
        Initialize with optional AI client.
        
        Args:
            ai_client: AI client for code enhancement (OpenAI, Anthropic, etc.)
        """
        super().__init__()
        self.ai_client = ai_client
    
    async def _enhance_with_ai(
        self,
        code: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Enhance generated code with AI.
        
        Args:
            code: Base generated code
            context: Generation context
            
        Returns:
            Enhanced code
        """
        if not self.ai_client:
            return code
        
        try:
            prompt = f"""You are a Python expert. Review and enhance this BF Agent handler code.

Focus on:
1. Adding helpful inline comments
2. Improving docstrings with examples
3. Adding edge case handling
4. Suggesting potential optimizations

Keep the structure intact. Only enhance, don't restructure.

Handler Name: {context.get('name', 'Unknown')}
Domain: {context.get('domain', 'Unknown')}
Description: {context.get('description', '')}

Code:
```python
{code}
```

Return only the enhanced Python code, no explanations."""

            enhanced = await self.ai_client.generate(prompt)
            
            # Basic validation that we got Python code back
            if 'class ' in enhanced and 'def ' in enhanced:
                return enhanced
            
            return code
            
        except Exception as e:
            # Fall back to template code on AI error
            return code
    
    async def generate_handler(
        self,
        name: str,
        domain: str,
        handler_type: HandlerType,
        description: str,
        input_fields: List[str],
        output_fields: List[str],
        ai_provider: Optional[AIProvider] = None,
        include_tests: bool = True,
        include_docstrings: bool = True,
        use_ai_enhancement: bool = True,
    ) -> GeneratedCode:
        """
        Generate handler code with optional AI enhancement.
        """
        # Generate base code using template
        result = await super().generate_handler(
            name=name,
            domain=domain,
            handler_type=handler_type,
            description=description,
            input_fields=input_fields,
            output_fields=output_fields,
            ai_provider=ai_provider,
            include_tests=include_tests,
            include_docstrings=include_docstrings,
        )
        
        # Enhance with AI if requested and available
        if use_ai_enhancement and self.ai_client:
            context = {
                "name": name,
                "domain": domain,
                "description": description,
            }
            
            enhanced_handler = await self._enhance_with_ai(result.handler_code, context)
            
            return GeneratedCode(
                handler_code=enhanced_handler,
                test_code=result.test_code,
                schema_code=result.schema_code,
                handler_filename=result.handler_filename,
                test_filename=result.test_filename,
                schema_filename=result.schema_filename,
                metadata={
                    **result.metadata,
                    "ai_enhanced": True,
                    "generator": "AIEnhancedGenerator",
                }
            )
        
        return result


# =============================================================================
# GENERATOR FACTORY
# =============================================================================

class GeneratorFactory:
    """Factory for code generators."""
    
    @staticmethod
    def get_generator(
        use_ai: bool = False,
        ai_client=None
    ) -> BaseGenerator:
        """
        Get appropriate generator.
        
        Args:
            use_ai: Use AI enhancement
            ai_client: AI client instance
            
        Returns:
            Generator instance
        """
        if use_ai and ai_client:
            return AIEnhancedGenerator(ai_client=ai_client)
        return TemplateGenerator()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "BaseGenerator",
    "TemplateGenerator",
    "AIEnhancedGenerator",
    "GeneratorFactory",
]
