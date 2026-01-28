"""
SecureTemplateEngine - Sandboxed Jinja2 Template Rendering
===========================================================

Provides a hardened template engine with multi-layer security:
1. ImmutableSandboxedEnvironment (Jinja2 native)
2. Pattern-based pre-validation (forbidden patterns)
3. Context key blacklist (dangerous attributes)
4. Recursive depth limit (prevent infinite loops)
5. JSON Schema validation for context
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from jinja2 import StrictUndefined
from jinja2.sandbox import ImmutableSandboxedEnvironment

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of template validation."""
    
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __bool__(self) -> bool:
        return self.valid


@dataclass
class RenderedPrompt:
    """Result of template rendering."""
    
    system_prompt: str
    user_prompt: str
    full_prompt: str
    output_format: str = ""
    variables_used: Set[str] = field(default_factory=set)
    validation: ValidationResult = field(default_factory=lambda: ValidationResult(valid=True))
    
    @property
    def total_length(self) -> int:
        """Total character length of rendered prompt."""
        return len(self.full_prompt)


class TemplateSecurityError(Exception):
    """Raised when template contains security violations."""
    
    def __init__(self, message: str, violations: Optional[List[str]] = None):
        super().__init__(message)
        self.violations = violations or []


class ContextValidationError(Exception):
    """Raised when context fails JSON Schema validation."""
    
    def __init__(self, message: str, schema_errors: Optional[List[str]] = None):
        super().__init__(message)
        self.schema_errors = schema_errors or []


class SecureTemplateEngine:
    """
    Hardened Template Engine with Security Features.
    
    Features:
    - Sandboxed Jinja2 Environment
    - Pattern-based security validation
    - Context sanitization
    - JSON Schema validation
    - Component inclusion support
    
    Usage:
        engine = SecureTemplateEngine()
        result = engine.render_string("Hello {{ name }}!", {"name": "World"})
    """
    
    # Allowed Jinja2 globals (whitelist)
    ALLOWED_GLOBALS = frozenset({
        "range", "len", "str", "int", "float", "bool",
        "list", "dict", "set", "tuple",
        "min", "max", "sum", "sorted", "enumerate", "zip",
        "true", "false", "none",
        "abs", "round",
    })
    
    # Forbidden patterns in templates (regex, message)
    FORBIDDEN_PATTERNS = [
        (r"\{\%\s*import", "Import statements not allowed"),
        (r"\{\%\s*from", "From imports not allowed"),
        (r"__\w+__", "Dunder attributes not allowed"),
        (r"\.mro\s*\(", "MRO access not allowed"),
        (r"\.base\s*\(", "Base class access not allowed"),
        (r"\.__class__", "Class attribute access not allowed"),
        (r"\.__bases__", "Bases attribute access not allowed"),
        (r"\.__subclasses__", "Subclasses access not allowed"),
        (r"\bconfig\s*\[", "Config access not allowed"),
        (r"\bself\.", "Self access not allowed"),
        (r"\brequest\.", "Request access not allowed"),
        (r"\bos\.", "OS module access not allowed"),
        (r"\bsys\.", "Sys module access not allowed"),
        (r"\beval\s*\(", "Eval not allowed"),
        (r"\bexec\s*\(", "Exec not allowed"),
        (r"\bopen\s*\(", "Open not allowed"),
        (r"\bcompile\s*\(", "Compile not allowed"),
        (r"\bgetattr\s*\(", "Getattr not allowed"),
        (r"\bsetattr\s*\(", "Setattr not allowed"),
        (r"\bdelattr\s*\(", "Delattr not allowed"),
        (r"\bglobals\s*\(", "Globals not allowed"),
        (r"\blocals\s*\(", "Locals not allowed"),
        (r"\bvars\s*\(", "Vars not allowed"),
        (r"\bdir\s*\(", "Dir not allowed"),
    ]
    
    # Blocked context keys (dangerous attributes)
    BLOCKED_CONTEXT_KEYS = frozenset({
        "__builtins__", "__import__", "eval", "exec", "compile",
        "open", "file", "input", "raw_input", "reload",
        "globals", "locals", "vars", "dir", "getattr", "setattr",
        "delattr", "hasattr", "__class__", "__bases__", "__subclasses__",
        "__mro__", "__dict__", "__doc__", "__module__", "__name__",
        "__qualname__", "__annotations__", "__wrapped__",
        "breakpoint", "exit", "quit",
    })
    
    # Maximum recursion depth for context sanitization
    MAX_CONTEXT_DEPTH = 10
    
    def __init__(
        self,
        component_store: Optional[Any] = None,
        enable_schema_validation: bool = True,
    ):
        """
        Initialize SecureTemplateEngine.
        
        Args:
            component_store: Optional store for reusable components
            enable_schema_validation: Enable JSON Schema validation for context
        """
        self.component_store = component_store
        self.enable_schema_validation = enable_schema_validation
        
        # Create sandboxed environment
        self.env = ImmutableSandboxedEnvironment(
            autoescape=False,  # Prompts are not HTML
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )
        
        # Restrict globals to whitelist
        safe_globals = {
            k: v for k, v in self.env.globals.items()
            if k in self.ALLOWED_GLOBALS
        }
        self.env.globals = safe_globals
        
        # Register safe custom filters
        self._register_filters()
    
    def _register_filters(self) -> None:
        """Register safe custom filters."""
        import json
        
        def json_pretty(value: Any) -> str:
            """Pretty-print JSON."""
            try:
                return json.dumps(value, indent=2, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                return str(value)
        
        def truncate_words(text: str, num_words: int) -> str:
            """Truncate text to N words."""
            words = str(text).split()
            if len(words) <= num_words:
                return text
            return " ".join(words[:num_words]) + "..."
        
        def default_if_none(value: Any, default: Any) -> Any:
            """Return default if value is None."""
            return default if value is None else value
        
        def strip_html(text: str) -> str:
            """Remove HTML tags from text."""
            return re.sub(r"<[^>]+>", "", str(text))
        
        def escape_quotes(text: str) -> str:
            """Escape quotes for JSON embedding."""
            return str(text).replace('"', '\\"').replace("'", "\\'")
        
        self.env.filters["json_pretty"] = json_pretty
        self.env.filters["truncate_words"] = truncate_words
        self.env.filters["default_if_none"] = default_if_none
        self.env.filters["strip_html"] = strip_html
        self.env.filters["escape_quotes"] = escape_quotes
    
    def validate_template(self, template_str: str) -> ValidationResult:
        """
        Validate template for security and syntax.
        
        Args:
            template_str: Template string to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        if not template_str:
            return ValidationResult(valid=True, errors=[], warnings=[])
        
        # Pattern-based security check
        for pattern, message in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, template_str, re.IGNORECASE):
                errors.append(f"Security violation: {message}")
        
        # Syntax check
        try:
            self.env.parse(template_str)
        except Exception as e:
            errors.append(f"Syntax error: {e}")
        
        # Check for potentially dangerous constructs (warnings)
        if "loop.index" in template_str and "loop.last" not in template_str:
            warnings.append("Loop without termination check detected")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def validate_context(
        self,
        context: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate context against JSON Schema.
        
        Args:
            context: Context dictionary to validate
            schema: Optional JSON Schema for validation
            
        Returns:
            ValidationResult with errors
        """
        errors: List[str] = []
        
        if not schema or not self.enable_schema_validation:
            return ValidationResult(valid=True)
        
        try:
            from jsonschema import ValidationError, validate
            
            validate(instance=context, schema=schema)
        except ValidationError as e:
            errors.append(f"Context validation failed: {e.message}")
        except ImportError:
            logger.warning("jsonschema not installed, skipping validation")
        except Exception as e:
            errors.append(f"Schema validation error: {e}")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
    
    def render_string(
        self,
        template_str: str,
        context: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render a single template string.
        
        Args:
            template_str: Template string to render
            context: Variables for rendering
            schema: Optional JSON Schema for context validation
            
        Returns:
            Rendered string
            
        Raises:
            TemplateSecurityError: If template contains security violations
            ContextValidationError: If context fails schema validation
        """
        # Validate template
        validation = self.validate_template(template_str)
        if not validation.valid:
            raise TemplateSecurityError(
                "Template contains security violations",
                violations=validation.errors,
            )
        
        # Validate context if schema provided
        if schema:
            ctx_validation = self.validate_context(context, schema)
            if not ctx_validation.valid:
                raise ContextValidationError(
                    "Context validation failed",
                    schema_errors=ctx_validation.errors,
                )
        
        # Sanitize context
        safe_context = self._sanitize_context(context)
        
        return self._render_safe(template_str, safe_context)
    
    def render(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
        output_format: str = "",
        default_values: Optional[Dict[str, Any]] = None,
        schema: Optional[Dict[str, Any]] = None,
    ) -> RenderedPrompt:
        """
        Render system and user prompts with context.
        
        Args:
            system_prompt: System prompt template
            user_prompt: User prompt template
            context: Variables for rendering
            output_format: Optional output format instructions
            default_values: Default values for missing context keys
            schema: Optional JSON Schema for context validation
            
        Returns:
            RenderedPrompt with all rendered parts
            
        Raises:
            TemplateSecurityError: If template contains security violations
            ContextValidationError: If context fails schema validation
        """
        # Validate all templates
        all_violations: List[str] = []
        for name, tmpl in [
            ("system", system_prompt),
            ("user", user_prompt),
            ("output", output_format),
        ]:
            validation = self.validate_template(tmpl)
            if not validation.valid:
                all_violations.extend([f"{name}: {e}" for e in validation.errors])
        
        if all_violations:
            raise TemplateSecurityError(
                "Template contains security violations",
                violations=all_violations,
            )
        
        # Validate context against schema
        if schema:
            ctx_validation = self.validate_context(context, schema)
            if not ctx_validation.valid:
                raise ContextValidationError(
                    "Context validation failed",
                    schema_errors=ctx_validation.errors,
                )
        
        # Sanitize context
        safe_context = self._sanitize_context(context)
        
        # Add component include function if available
        if self.component_store:
            safe_context["include_component"] = self._include_component
        
        # Merge default values
        full_context = {**(default_values or {})}
        full_context.update(safe_context)
        
        # Render each part
        rendered_system = self._render_safe(system_prompt, full_context)
        rendered_user = self._render_safe(user_prompt, full_context)
        rendered_output = self._render_safe(output_format, full_context)
        
        # Combine into full prompt
        parts = []
        if rendered_system:
            parts.append(rendered_system)
        if rendered_user:
            parts.append(rendered_user)
        if rendered_output:
            parts.append(rendered_output)
        
        full_prompt = "\n\n".join(parts)
        
        # Build user prompt with output format
        user_with_format = rendered_user
        if rendered_output:
            user_with_format = f"{rendered_user}\n\n{rendered_output}"
        
        return RenderedPrompt(
            system_prompt=rendered_system,
            user_prompt=user_with_format,
            full_prompt=full_prompt,
            output_format=rendered_output,
            variables_used=self._extract_variables(user_prompt),
            validation=ValidationResult(valid=True),
        )
    
    def _sanitize_context(
        self,
        context: Any,
        depth: int = 0,
    ) -> Any:
        """
        Deep sanitization of context.
        
        Removes dangerous keys and converts objects to safe representations.
        """
        if depth > self.MAX_CONTEXT_DEPTH:
            return str(context)
        
        if isinstance(context, dict):
            return {
                k: self._sanitize_context(v, depth + 1)
                for k, v in context.items()
                if k not in self.BLOCKED_CONTEXT_KEYS
                and not str(k).startswith("_")
            }
        elif isinstance(context, (list, tuple)):
            return [self._sanitize_context(v, depth + 1) for v in context]
        elif isinstance(context, (str, int, float, bool, type(None))):
            return context
        else:
            # Objects: Convert to safe string representation
            try:
                if hasattr(context, "__dict__"):
                    return self._sanitize_context(
                        {k: v for k, v in context.__dict__.items() if not k.startswith("_")},
                        depth + 1,
                    )
                return str(context)
            except Exception:
                return str(context)
    
    def _render_safe(
        self,
        template_str: str,
        context: Dict[str, Any],
    ) -> str:
        """Render with error handling."""
        if not template_str:
            return ""
        
        try:
            template = self.env.from_string(template_str)
            return template.render(**context).strip()
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            raise
    
    def _include_component(self, code: str) -> str:
        """Load and return component content."""
        if not self.component_store:
            return f"[Component '{code}' not available]"
        
        try:
            component = self.component_store.get(code)
            if component:
                return component.content
            return f"[Component '{code}' not found]"
        except Exception as e:
            logger.error(f"Error loading component '{code}': {e}")
            return f"[Error loading component '{code}']"
    
    def _extract_variables(self, template_str: str) -> Set[str]:
        """Extract variable names from template."""
        if not template_str:
            return set()
        
        try:
            from jinja2 import meta
            
            ast = self.env.parse(template_str)
            return meta.find_undeclared_variables(ast)
        except Exception:
            return set()
