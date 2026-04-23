"""
Security module for the Prompt Template System.

Provides validators for injection detection and sanitizers for input cleaning.
"""

from .validators import (
    normalize_text,
    check_injection,
    is_safe,
    INJECTION_PATTERNS,
)

from .sanitizers import (
    sanitize_for_prompt,
    truncate_safely,
    escape_template_syntax,
    remove_markdown_injection,
)

__all__ = [
    "normalize_text",
    "check_injection",
    "is_safe",
    "INJECTION_PATTERNS",
    "sanitize_for_prompt",
    "truncate_safely",
    "escape_template_syntax",
    "remove_markdown_injection",
]
