"""
Template rendering using Jinja2.

Provides safe rendering of prompt templates with variable substitution.
"""

from typing import Any

from ..schemas import PromptTemplateSpec, PromptVariable
from ..exceptions import RenderError, VariableMissingError, VariableTypeError
from ..security import sanitize_for_prompt, check_injection, escape_template_syntax
from ..exceptions import InjectionDetectedError

# Try to import Jinja2
try:
    from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


class TemplateRenderer:
    """
    Renders prompt templates with Jinja2.

    Handles variable validation, sanitization, and injection checking.
    """

    def __init__(
        self,
        autoescape: bool = False,
        undefined_strict: bool = True,
    ):
        """
        Initialize the renderer.

        Args:
            autoescape: Whether to auto-escape HTML (usually False for prompts)
            undefined_strict: Whether to raise on undefined variables
        """
        if not JINJA2_AVAILABLE:
            raise ImportError(
                "Jinja2 is required for template rendering. "
                "Install with: pip install jinja2"
            )

        from jinja2 import StrictUndefined, Undefined

        self._env = Environment(
            loader=BaseLoader(),
            autoescape=autoescape,
            undefined=StrictUndefined if undefined_strict else Undefined,
        )

    def render(
        self,
        template: PromptTemplateSpec,
        variables: dict[str, Any],
        sanitize: bool = True,
        check_injections: bool = True,
    ) -> tuple[str, str]:
        """
        Render a template with variables.

        Args:
            template: Template to render
            variables: Variables to substitute
            sanitize: Whether to sanitize variable values
            check_injections: Whether to check for prompt injection

        Returns:
            Tuple of (rendered_system_prompt, rendered_user_prompt)

        Raises:
            VariableMissingError: If required variable is missing
            VariableTypeError: If variable has wrong type
            InjectionDetectedError: If injection is detected
            RenderError: If rendering fails
        """
        # Prepare variables with defaults and validation
        prepared_vars = self._prepare_variables(
            template=template,
            variables=variables,
            sanitize=sanitize and template.sanitize_user_input,
            check_injections=check_injections and template.check_injection,
            max_length=template.max_variable_length,
        )

        # Render system prompt
        try:
            system_template = self._env.from_string(template.system_prompt)
            rendered_system = system_template.render(**prepared_vars)
        except UndefinedError as e:
            raise RenderError(template.template_key, f"Undefined variable in system prompt: {e}")
        except TemplateSyntaxError as e:
            raise RenderError(template.template_key, f"Syntax error in system prompt: {e}")
        except Exception as e:
            raise RenderError(template.template_key, f"System prompt render failed: {e}")

        # Render user prompt
        try:
            user_template = self._env.from_string(template.user_prompt)
            rendered_user = user_template.render(**prepared_vars)
        except UndefinedError as e:
            raise RenderError(template.template_key, f"Undefined variable in user prompt: {e}")
        except TemplateSyntaxError as e:
            raise RenderError(template.template_key, f"Syntax error in user prompt: {e}")
        except Exception as e:
            raise RenderError(template.template_key, f"User prompt render failed: {e}")

        return rendered_system, rendered_user

    def _prepare_variables(
        self,
        template: PromptTemplateSpec,
        variables: dict[str, Any],
        sanitize: bool,
        check_injections: bool,
        max_length: int,
    ) -> dict[str, Any]:
        """
        Prepare variables for rendering.

        - Applies defaults for missing optional variables
        - Validates required variables are present
        - Validates variable types
        - Sanitizes string values
        - Checks for injection attempts
        """
        prepared: dict[str, Any] = {}

        # Get defaults
        defaults = template.get_variable_defaults()

        # Process each defined variable
        for var_def in template.variables:
            name = var_def.name

            # Get value (from input or default)
            if name in variables:
                value = variables[name]
            elif name in defaults:
                value = defaults[name]
            elif var_def.required:
                raise VariableMissingError(name, template.template_key)
            else:
                continue  # Optional with no default, skip

            # Validate type
            is_valid, error = var_def.validate_value(value)
            if not is_valid:
                raise VariableTypeError(
                    name,
                    var_def.var_type.value,
                    type(value).__name__,
                )

            # Process string values
            if isinstance(value, str):
                # Check injection if enabled for this variable
                if check_injections and var_def.check_injection:
                    result = check_injection(value)
                    if result.detected:
                        raise InjectionDetectedError(
                            variable_name=name,
                            pattern_matched=result.pattern_name or "unknown",
                            input_preview=value[:100],
                        )

                # Sanitize if enabled for this variable
                if sanitize and var_def.sanitize:
                    value = sanitize_for_prompt(
                        value,
                        max_length=min(var_def.max_length or max_length, max_length),
                    )

                # Escape template syntax to prevent injection via Jinja2
                value = escape_template_syntax(value)

            prepared[name] = value

        # Add any extra variables not in template definition
        # (useful for custom filters/functions)
        for name, value in variables.items():
            if name not in prepared:
                if isinstance(value, str):
                    value = escape_template_syntax(value)
                prepared[name] = value

        return prepared


# Module-level renderer instance
_default_renderer: TemplateRenderer | None = None


def get_renderer() -> TemplateRenderer:
    """Get or create the default renderer."""
    global _default_renderer
    if _default_renderer is None:
        _default_renderer = TemplateRenderer()
    return _default_renderer


def render_template(
    template: PromptTemplateSpec,
    variables: dict[str, Any],
    sanitize: bool = True,
    check_injections: bool = True,
) -> tuple[str, str]:
    """
    Render a template using the default renderer.

    Convenience function for simple use cases.

    Args:
        template: Template to render
        variables: Variables to substitute
        sanitize: Whether to sanitize values
        check_injections: Whether to check for injections

    Returns:
        Tuple of (rendered_system_prompt, rendered_user_prompt)
    """
    renderer = get_renderer()
    return renderer.render(
        template=template,
        variables=variables,
        sanitize=sanitize,
        check_injections=check_injections,
    )
