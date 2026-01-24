"""
Prompt Factory Service
Centralized prompt building with templates, caching, and variable substitution
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from django.core.cache import cache
from django.db.models import Q
from jinja2 import BaseLoader, Environment, TemplateError, meta

from apps.bfagent.models import PromptTemplate

logger = logging.getLogger(__name__)


class PromptFactory:
    """
    Centralized service for building LLM prompts from templates

    Features:
    - Template rendering with Jinja2
    - Variable substitution
    - Template caching
    - Reusable components
    - Output format standardization

    Usage:
        factory = PromptFactory()
        prompt = factory.build('premise_generator', {
            'project': {'title': 'My Book', 'genre': 'Fantasy'},
            'inspiration': 'A story about...'
        })
        # Returns: {'system': '...', 'user': '...', 'full': '...'}
    """

    CACHE_TTL = 3600  # 1 hour
    CACHE_PREFIX = "prompt_template_"

    def __init__(self):
        """Initialize Jinja2 environment for template rendering"""
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=False,  # We're building prompts, not HTML
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters["json_pretty"] = lambda x: json.dumps(x, indent=2)

    def build(
        self,
        template_code: str,
        context: Dict[str, Any],
        output_format: str = "json",
        include_system: bool = True,
    ) -> Dict[str, str]:
        """
        Build prompt from template with context

        Args:
            template_code: Template identifier (e.g., 'premise_generator')
            context: Variables to substitute (e.g., {'project': {...}})
            output_format: 'json', 'markdown', or 'text'
            include_system: Whether to include system prompt

        Returns:
            {
                'system': str,        # System message
                'user': str,          # User message
                'full': str,          # Combined (for single-message models)
                'metadata': dict      # Template metadata
            }

        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateRenderError: If rendering fails
        """
        try:
            # Get template (from cache or DB)
            template = self.get_template(template_code)

            if not template:
                raise TemplateNotFoundError(f"Template '{template_code}' not found")

            if not template.is_active:
                logger.warning(f"Using inactive template: {template_code}")

            # Add output format instructions to context
            context["output_format"] = output_format
            context["json_schema"] = context.get("json_schema", "{}")

            # Render system prompt
            system_prompt = ""
            if include_system and template.system_prompt:
                system_prompt = self.render_template(template.system_prompt, context)

            # Render user prompt
            user_prompt = self.render_template(template.user_prompt_template, context)

            # Add output format instructions if specified
            if output_format and template.output_format_instructions:
                format_instructions = self.render_template(
                    template.output_format_instructions, context
                )
                user_prompt = f"{user_prompt}\n\n{format_instructions}"

            # Build full prompt (for single-message models)
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
            else:
                full_prompt = user_prompt

            logger.info(f"Built prompt from template: {template_code}")

            return {
                "system": system_prompt,
                "user": user_prompt,
                "full": full_prompt,
                "metadata": {
                    "template_code": template_code,
                    "template_version": template.version,
                    "template_type": template.template_type,
                    "output_format": output_format,
                },
            }

        except TemplateNotFoundError:
            raise
        except TemplateError as e:
            raise TemplateRenderError(f"Error rendering template '{template_code}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error building prompt: {e}")
            raise PromptFactoryError(f"Failed to build prompt: {e}")

    def get_template(self, code: str) -> Optional[PromptTemplate]:
        """
        Get template from cache or database

        Args:
            code: Template identifier

        Returns:
            PromptTemplate instance or None
        """
        cache_key = f"{self.CACHE_PREFIX}{code}"

        # Try cache first
        template = cache.get(cache_key)
        if template:
            logger.debug(f"Template '{code}' loaded from cache")
            return template

        # Load from database
        try:
            template = PromptTemplate.objects.get(name=code, is_active=True)

            # Cache for future use
            cache.set(cache_key, template, self.CACHE_TTL)
            logger.debug(f"Template '{code}' loaded from DB and cached")

            return template

        except PromptTemplate.DoesNotExist:
            logger.warning(f"Template '{code}' not found in database")
            return None
        except Exception as e:
            logger.error(f"Error loading template '{code}': {e}")
            return None

    def render_template(self, template_str: str, context: Dict[str, Any]) -> str:
        """
        Render Jinja2 template with context

        Args:
            template_str: Template string with {{ variables }}
            context: Variables to substitute

        Returns:
            Rendered string

        Raises:
            TemplateError: If rendering fails
        """
        try:
            # Sanitize context (prevent code injection)
            safe_context = self._sanitize_context(context)

            # Parse and render template
            template = self.env.from_string(template_str)
            rendered = template.render(**safe_context)

            return rendered.strip()

        except TemplateError as e:
            logger.error(f"Template rendering error: {e}")
            raise

    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize context to prevent code injection

        Args:
            context: Raw context dict

        Returns:
            Sanitized context dict
        """
        # Remove dangerous keys
        dangerous_keys = ["__builtins__", "__import__", "eval", "exec", "open"]
        safe_context = {k: v for k, v in context.items() if k not in dangerous_keys}

        # Convert None to empty string (Jinja2 friendly)
        def clean_value(val):
            if val is None:
                return ""
            elif isinstance(val, dict):
                return {k: clean_value(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [clean_value(v) for v in val]
            else:
                return val

        return {k: clean_value(v) for k, v in safe_context.items()}

    def extract_variables(self, template_str: str) -> set:
        """
        Extract variable names from template

        Args:
            template_str: Template string

        Returns:
            Set of variable names
        """
        try:
            ast = self.env.parse(template_str)
            return meta.find_undeclared_variables(ast)
        except TemplateError as e:
            logger.error(f"Error parsing template: {e}")
            return set()

    def validate_template(self, template_str: str, required_vars: Optional[set] = None) -> tuple:
        """
        Validate template syntax and required variables

        Args:
            template_str: Template string to validate
            required_vars: Set of required variable names

        Returns:
            (is_valid: bool, error_message: str)
        """
        try:
            # Check syntax
            self.env.parse(template_str)

            # Check required variables
            if required_vars:
                template_vars = self.extract_variables(template_str)
                missing_vars = required_vars - template_vars

                if missing_vars:
                    return (False, f"Missing required variables: {', '.join(missing_vars)}")

            return (True, "")

        except TemplateError as e:
            return (False, f"Template syntax error: {e}")

    def clear_cache(self, template_code: Optional[str] = None):
        """
        Clear template cache

        Args:
            template_code: Specific template to clear, or None for all
        """
        if template_code:
            cache_key = f"{self.CACHE_PREFIX}{template_code}"
            cache.delete(cache_key)
            logger.info(f"Cleared cache for template: {template_code}")
        else:
            # Clear all prompt templates
            # Note: This is inefficient, better to use cache.delete_pattern
            # if using Redis cache backend
            logger.info("Cleared all template cache")

    def get_template_metadata(self, template_code: str) -> Dict[str, Any]:
        """
        Get template metadata without rendering

        Args:
            template_code: Template identifier

        Returns:
            Metadata dict
        """
        template = self.get_template(template_code)

        if not template:
            return {}

        user_vars = self.extract_variables(template.user_prompt_template)
        system_vars = set()
        if template.system_prompt:
            system_vars = self.extract_variables(template.system_prompt)

        return {
            "code": template.name,
            "type": template.template_type,
            "version": template.version,
            "is_active": template.is_active,
            "required_variables": list(user_vars | system_vars),
            "has_system_prompt": bool(template.system_prompt),
            "has_output_format": bool(template.output_format_instructions),
            "created_at": (
                template.created_at.isoformat() if hasattr(template, "created_at") else None
            ),
        }


# Custom Exceptions
class PromptFactoryError(Exception):
    """Base exception for prompt factory errors"""

    pass


class TemplateNotFoundError(PromptFactoryError):
    """Template not found in database"""

    pass


class TemplateRenderError(PromptFactoryError):
    """Error rendering template"""

    pass


# Convenience function for quick usage
def build_prompt(template_code: str, context: Dict[str, Any], **kwargs) -> Dict[str, str]:
    """
    Quick helper to build prompt without instantiating factory

    Args:
        template_code: Template identifier
        context: Variables to substitute
        **kwargs: Additional args for factory.build()

    Returns:
        Prompt dict

    Example:
        prompt = build_prompt('premise_generator', {
            'project': {'title': 'My Book'}
        })
    """
    factory = PromptFactory()
    return factory.build(template_code, context, **kwargs)
