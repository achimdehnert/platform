"""
LLM Prompts for Handler Generation
Engineered prompts for reliable handler code generation
"""

from apps.bfagent.services.handlers.config_models import HandlerRequirements


class PromptBuilder:
    """Builds optimized prompts for handler generation"""

    # System prompts
    REQUIREMENTS_SYSTEM_PROMPT = """You are an expert software architect analyzing requirements for workflow handlers.

Your task is to extract structured requirements from natural language descriptions.

Focus on:
1. Clear handler identification (snake_case ID)
2. Accurate categorization (input/processing/output)
3. Complete configuration parameters
4. Necessary dependencies
5. Error scenarios

Be precise and thorough."""

    CODE_GENERATION_SYSTEM_PROMPT = """You are an expert Python developer specializing in clean, production-ready code.

Your task is to generate complete, working handlers with:
1. Full type hints (typing module)
2. Comprehensive docstrings (Google style)
3. Pydantic config models with validation
4. Complete test suites (pytest)
5. Error handling and edge cases
6. Clear, documented code

Follow Python best practices:
- PEP 8 style
- Single responsibility
- DRY principle
- Explicit is better than implicit

Generate production-ready code that works on first try."""

    def build_requirements_prompt(self, description: str) -> str:
        """
        Build prompt for requirements analysis

        Args:
            description: User's natural language description

        Returns:
            Formatted prompt for LLM
        """
        return f"""Analyze this handler request and extract structured requirements:

USER REQUEST:
{description}

EXTRACT:
1. **handler_id**: Snake_case identifier (e.g., 'pdf_text_extractor')
2. **display_name**: Human-readable name (e.g., 'PDF Text Extractor')
3. **description**: Clear, concise description of what it does
4. **category**: One of: 'input', 'processing', 'output'
   - input: Collects/loads data
   - processing: Transforms/processes data
   - output: Saves/exports data
5. **dependencies**: Python packages needed (e.g., ['pdfplumber', 'pytesseract'])
6. **config_parameters**: Configuration options with:
   - type (string, integer, boolean, array, etc.)
   - default value
   - description
   - validation rules (min, max, pattern, etc.)
7. **input_requirements**: What the handler needs from context
8. **output_format**: What the handler returns
9. **error_scenarios**: Possible errors and how to handle them

Think step by step:
- What does this handler DO?
- What CATEGORY fits best?
- What CONFIG does it need?
- What can go WRONG?

Provide complete, accurate requirements."""

    def build_generation_prompt(self, requirements: HandlerRequirements) -> str:
        """
        Build prompt for code generation

        Args:
            requirements: Structured requirements

        Returns:
            Formatted prompt for code generation
        """
        deps = ", ".join(requirements.dependencies) if requirements.dependencies else "None"

        return f"""Generate a complete, production-ready handler implementation.

REQUIREMENTS:
```json
{requirements.model_dump_json(indent=2)}
```

GENERATE THE FOLLOWING:

1. **handler_code**: Complete handler class
   - Inherits from Base{requirements.category.title()}Handler
   - Full type hints (Dict, Any, Optional, etc.)
   - Google-style docstrings
   - execute() method with context and config parameters
   - Helper methods as needed
   - Comprehensive error handling
   - Example:
   ```python
   from typing import Dict, Any
   from apps.core.handlers import Base{requirements.category.title()}Handler

   class {self._to_class_name(requirements.handler_id)}(Base{requirements.category.title()}Handler):
       \"\"\"
       {requirements.description}
       \"\"\"

       display_name = "{requirements.display_name}"
       description = "{requirements.description}"
       version = "1.0.0"

       def execute(self, context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
           \"\"\"Execute handler logic\"\"\"
           # Implementation here
           pass
   ```

2. **config_model_code**: Pydantic config model
   - Class name: {self._to_class_name(requirements.handler_id)}Config
   - Inherits from BaseHandlerConfig
   - All config parameters as fields with Field()
   - Validation rules
   - Example config
   - Example:
   ```python
   from pydantic import BaseModel, Field
   from apps.bfagent.services.handlers.config_models import BaseHandlerConfig

   class {self._to_class_name(requirements.handler_id)}Config(BaseHandlerConfig):
       \"\"\"Configuration for {requirements.display_name}\"\"\"

       param_name: str = Field(
           ...,
           description="Parameter description",
           min_length=1
       )
   ```

3. **test_code**: Complete pytest test suite
   - Test class: Test{self._to_class_name(requirements.handler_id)}
   - Fixtures
   - Happy path tests
   - Error case tests
   - Edge case tests
   - Mock dependencies
   - Example:
   ```python
   import pytest
   from apps.bfagent.services.handlers.{requirements.category}.{requirements.handler_id} import {self._to_class_name(requirements.handler_id)}

   class Test{self._to_class_name(requirements.handler_id)}:
       @pytest.fixture
       def handler(self):
           return {self._to_class_name(requirements.handler_id)}()

       def test_execute_success(self, handler):
           context = {{'key': 'value'}}
           config = {{}}
           result = handler.execute(context, config)
           assert 'result' in result
   ```

4. **documentation**: Markdown documentation
   - Purpose
   - Features
   - Configuration parameters table
   - Input/Output formats
   - Usage example
   - Error handling

5. **example_usage**: Python code example showing usage

DEPENDENCIES: {deps}

IMPORTANT:
- Code must be syntactically correct Python
- Include ALL necessary imports
- Handle ALL error scenarios from requirements
- Follow PEP 8
- Add type hints everywhere
- Write clear docstrings
- Make tests comprehensive

Generate complete, working code that runs on first try."""

    def build_regeneration_prompt(self, requirements: HandlerRequirements, feedback: str) -> str:
        """
        Build prompt for regeneration with feedback

        Args:
            requirements: Original requirements
            feedback: User feedback on what to improve

        Returns:
            Formatted prompt for regeneration
        """
        return f"""Regenerate handler implementation based on feedback.

ORIGINAL REQUIREMENTS:
```json
{requirements.model_dump_json(indent=2)}
```

USER FEEDBACK:
{feedback}

INSTRUCTIONS:
1. Address all points in the feedback
2. Keep what was good from original
3. Improve based on specific feedback
4. Maintain code quality and completeness

Generate improved version with same structure:
- handler_code
- config_model_code
- test_code
- documentation
- example_usage

Make it better while keeping it production-ready."""

    def _to_class_name(self, handler_id: str) -> str:
        """Convert handler_id to ClassName"""
        parts = handler_id.split("_")
        return "".join(word.capitalize() for word in parts) + "Handler"


# Example prompts for common scenarios

EXAMPLE_PDF_EXTRACTOR_PROMPT = """
I need a handler that extracts text from PDF files.

Requirements:
- Accept file path or file object
- Support multi-page PDFs
- Preserve text structure (paragraphs)
- Optional OCR for scanned PDFs
- Return plain text with metadata

Configuration:
- ocr_enabled: boolean (default: false)
- preserve_formatting: boolean (default: true)
- pages: list of page numbers or "all" (default: "all")

Error Handling:
- Invalid file format → Clear error message
- Missing file → FileNotFoundError
- Corrupted PDF → Try OCR or fail gracefully
"""

EXAMPLE_EXCEL_READER_PROMPT = """
Create a handler to read Excel files and convert to JSON.

Features:
- Support .xlsx and .xls files
- Handle multiple sheets
- Convert data types appropriately
- Handle missing values

Configuration:
- sheet_names: list or "all" (default: "all")
- skip_rows: integer (default: 0)
- header_row: integer (default: 0)
- fill_missing: string (default: "")

Output:
- JSON structure with sheet names as keys
- Array of row objects
- Preserve data types
"""

EXAMPLE_EMAIL_SENDER_PROMPT = """
Build a handler that sends emails via SMTP.

Capabilities:
- Send plain text or HTML emails
- Support attachments
- CC and BCC
- Email templates

Configuration:
- smtp_host: string (required)
- smtp_port: integer (default: 587)
- use_tls: boolean (default: true)
- from_email: string (required)
- to_emails: list of strings (required)
- subject: string (required)
- body: string (required)
- html: boolean (default: false)
- attachments: list of file paths (optional)

Error Handling:
- Connection errors → Retry with backoff
- Authentication errors → Clear message
- Invalid email addresses → Validation error
"""
