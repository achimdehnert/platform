"""
Input sanitizers for prompt templates.

This module provides functions to clean and sanitize user input
before it's used in prompt templates.
"""

import html
import re


def sanitize_for_prompt(
    text: str,
    max_length: int | None = None,
    strip_html: bool = True,
    normalize_whitespace: bool = True,
    remove_control_chars: bool = True,
) -> str:
    """
    Sanitize text for safe use in prompts.

    Args:
        text: Input text to sanitize
        max_length: Maximum length (truncates if exceeded)
        strip_html: Whether to escape HTML entities
        normalize_whitespace: Whether to normalize whitespace
        remove_control_chars: Whether to remove control characters

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    result = text

    # Remove control characters (except newline and tab)
    if remove_control_chars:
        result = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", result)

    # Escape HTML entities to prevent any HTML injection
    if strip_html:
        result = html.escape(result, quote=False)

    # Normalize whitespace
    if normalize_whitespace:
        # Replace multiple spaces/tabs with single space
        result = re.sub(r"[ \t]+", " ", result)
        # Replace multiple newlines with double newline (paragraph break)
        result = re.sub(r"\n{3,}", "\n\n", result)
        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in result.split("\n")]
        result = "\n".join(lines)

    # Strip overall
    result = result.strip()

    # Truncate if needed
    if max_length and len(result) > max_length:
        result = truncate_safely(result, max_length)

    return result


def truncate_safely(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text safely without breaking words or sentences.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    # Account for suffix length
    target_length = max_length - len(suffix)
    if target_length <= 0:
        return suffix[:max_length]

    # Try to break at sentence boundary
    truncated = text[:target_length]

    # Look for sentence end in last 20% of text
    search_start = int(target_length * 0.8)
    sentence_end = -1

    for end_char in [".", "!", "?", "\n"]:
        pos = truncated.rfind(end_char, search_start)
        if pos > sentence_end:
            sentence_end = pos

    if sentence_end > search_start:
        return truncated[: sentence_end + 1]

    # Fall back to word boundary
    word_end = truncated.rfind(" ", search_start)
    if word_end > search_start:
        return truncated[:word_end] + suffix

    # Last resort: hard truncate
    return truncated + suffix


def escape_template_syntax(text: str) -> str:
    """
    Escape Jinja2 template syntax in user input.

    This prevents user input from being interpreted as template code.

    Args:
        text: Text to escape

    Returns:
        Text with template syntax escaped
    """
    # Escape Jinja2 delimiters
    text = text.replace("{{", "{ {")
    text = text.replace("}}", "} }")
    text = text.replace("{%", "{ %")
    text = text.replace("%}", "% }")
    text = text.replace("{#", "{ #")
    text = text.replace("#}", "# }")

    return text


def remove_markdown_injection(text: str) -> str:
    """
    Remove potentially dangerous Markdown that could affect rendering.

    Args:
        text: Text to clean

    Returns:
        Text with dangerous Markdown removed
    """
    # Remove image tags (could be used for tracking)
    text = re.sub(r"!\[.*?\]\(.*?\)", "[image removed]", text)

    # Remove links (could be phishing)
    text = re.sub(r"\[([^\]]*)\]\(.*?\)", r"\1", text)

    # Remove HTML-style tags
    text = re.sub(r"<[^>]+>", "", text)

    return text


def normalize_for_comparison(text: str) -> str:
    """
    Normalize text for comparison purposes.

    Useful for checking if two inputs are semantically similar
    despite formatting differences.

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    # Lowercase
    text = text.lower()

    # Remove all punctuation
    text = re.sub(r"[^\w\s]", "", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # Strip
    text = text.strip()

    return text
