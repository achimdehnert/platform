"""
Core Validators
===============

Unified validation utilities for consistent data validation.

Consolidates validators from:
- Scattered validation logic across handlers
- Email/URL validators
- File type validators
"""

import re
from pathlib import Path
from typing import Any, List, Optional, Union

from pydantic import ValidationError as PydanticValidationError
from pydantic import field_validator

from .base import ValidationResult

# =============================================================================
# Email Validation
# =============================================================================

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email(email: str) -> ValidationResult:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        ValidationResult with validation status

    Example:
        >>> result = validate_email("user@example.com")
        >>> assert result.is_valid
    """
    result = ValidationResult(is_valid=True)

    if not email:
        result.add_error("Email cannot be empty")
        return result

    if not EMAIL_REGEX.match(email):
        result.add_error(f"Invalid email format: {email}")

    if len(email) > 254:  # RFC 5321
        result.add_error("Email address too long (max 254 characters)")

    return result


# =============================================================================
# URL Validation
# =============================================================================

URL_REGEX = re.compile(
    r"^https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


def validate_url(url: str, require_https: bool = False) -> ValidationResult:
    """
    Validate URL format.

    Args:
        url: URL to validate
        require_https: If True, only HTTPS URLs are valid

    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult(is_valid=True)

    if not url:
        result.add_error("URL cannot be empty")
        return result

    if not URL_REGEX.match(url):
        result.add_error(f"Invalid URL format: {url}")
        return result

    if require_https and not url.startswith("https://"):
        result.add_error("HTTPS is required")

    return result


# =============================================================================
# File Validation
# =============================================================================

ALLOWED_EXTENSIONS = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"},
    "document": {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"},
    "presentation": {".pptx", ".ppt", ".odp"},
    "spreadsheet": {".xlsx", ".xls", ".csv", ".ods"},
    "archive": {".zip", ".tar", ".gz", ".rar", ".7z"},
    "video": {".mp4", ".avi", ".mov", ".wmv", ".flv"},
    "audio": {".mp3", ".wav", ".ogg", ".flac", ".aac"},
}


def validate_file_extension(
    filename: str,
    allowed_types: Optional[List[str]] = None,
    allowed_extensions: Optional[List[str]] = None,
) -> ValidationResult:
    """
    Validate file extension.

    Args:
        filename: Name of file to validate
        allowed_types: List of allowed file type categories ('image', 'document', etc.)
        allowed_extensions: List of specific allowed extensions (e.g., ['.pdf', '.docx'])

    Returns:
        ValidationResult with validation status

    Example:
        >>> result = validate_file_extension("doc.pdf", allowed_types=['document'])
        >>> assert result.is_valid
    """
    result = ValidationResult(is_valid=True)

    if not filename:
        result.add_error("Filename cannot be empty")
        return result

    ext = Path(filename).suffix.lower()

    if not ext:
        result.add_error("File has no extension")
        return result

    # Check specific extensions if provided
    if allowed_extensions:
        if ext not in [
            e.lower() if e.startswith(".") else f".{e.lower()}" for e in allowed_extensions
        ]:
            result.add_error(
                f"File extension {ext} not allowed. " f"Allowed: {', '.join(allowed_extensions)}"
            )

    # Check type categories if provided
    if allowed_types:
        valid = False
        for file_type in allowed_types:
            if file_type in ALLOWED_EXTENSIONS and ext in ALLOWED_EXTENSIONS[file_type]:
                valid = True
                break

        if not valid:
            result.add_error(
                f"File type {ext} not allowed for categories: {', '.join(allowed_types)}"
            )

    return result


def validate_file_size(
    file_size: int, max_size_mb: Optional[float] = None, min_size_kb: Optional[float] = None
) -> ValidationResult:
    """
    Validate file size.

    Args:
        file_size: Size in bytes
        max_size_mb: Maximum size in megabytes
        min_size_kb: Minimum size in kilobytes

    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult(is_valid=True)

    if file_size < 0:
        result.add_error("File size cannot be negative")
        return result

    if max_size_mb and file_size > (max_size_mb * 1024 * 1024):
        result.add_error(f"File too large (max: {max_size_mb} MB)")

    if min_size_kb and file_size < (min_size_kb * 1024):
        result.add_error(f"File too small (min: {min_size_kb} KB)")

    return result


# =============================================================================
# String Validation
# =============================================================================


def validate_slug(slug: str) -> ValidationResult:
    """
    Validate URL slug format.

    Slugs should be lowercase, alphanumeric with hyphens only.

    Args:
        slug: Slug to validate

    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult(is_valid=True)

    if not slug:
        result.add_error("Slug cannot be empty")
        return result

    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug):
        result.add_error(
            "Slug must be lowercase alphanumeric with hyphens " "(e.g., 'my-project-name')"
        )

    if len(slug) > 100:
        result.add_error("Slug too long (max 100 characters)")

    if slug.startswith("-") or slug.endswith("-"):
        result.add_error("Slug cannot start or end with hyphen")

    return result


def validate_json_string(json_str: str) -> ValidationResult:
    """
    Validate JSON string format.

    Args:
        json_str: JSON string to validate

    Returns:
        ValidationResult with validation status
    """
    import json

    result = ValidationResult(is_valid=True)

    if not json_str or not json_str.strip():
        result.add_error("JSON string cannot be empty")
        return result

    try:
        json.loads(json_str)
    except json.JSONDecodeError as e:
        result.add_error(f"Invalid JSON: {e}")

    return result


# =============================================================================
# Numeric Validation
# =============================================================================


def validate_range(
    value: Union[int, float],
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    field_name: str = "value",
) -> ValidationResult:
    """
    Validate numeric range.

    Args:
        value: Number to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Name of field for error messages

    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult(is_valid=True)

    if min_value is not None and value < min_value:
        result.add_error(f"{field_name} must be at least {min_value}")

    if max_value is not None and value > max_value:
        result.add_error(f"{field_name} must be at most {max_value}")

    return result


# =============================================================================
# List Validation
# =============================================================================


def validate_list_length(
    items: List[Any],
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    field_name: str = "list",
) -> ValidationResult:
    """
    Validate list length.

    Args:
        items: List to validate
        min_length: Minimum number of items
        max_length: Maximum number of items
        field_name: Name of field for error messages

    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult(is_valid=True)

    if min_length is not None and len(items) < min_length:
        result.add_error(f"{field_name} must have at least {min_length} items")

    if max_length is not None and len(items) > max_length:
        result.add_error(f"{field_name} must have at most {max_length} items")

    return result


def validate_unique_items(items: List[Any], field_name: str = "list") -> ValidationResult:
    """
    Validate list has unique items.

    Args:
        items: List to check for uniqueness
        field_name: Name of field for error messages

    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult(is_valid=True)

    if len(items) != len(set(items)):
        duplicates = [item for item in items if items.count(item) > 1]
        result.add_error(f"{field_name} contains duplicate items: {set(duplicates)}")

    return result


# =============================================================================
# Combined Validators
# =============================================================================


def validate_all(*validation_results: ValidationResult) -> ValidationResult:
    """
    Combine multiple validation results.

    Args:
        *validation_results: ValidationResult objects to combine

    Returns:
        Combined ValidationResult
    """
    combined = ValidationResult(is_valid=True)

    for result in validation_results:
        if not result.is_valid:
            combined.is_valid = False
        combined.errors.extend(result.errors)
        combined.warnings.extend(result.warnings)
        for field, errors in result.field_errors.items():
            if field not in combined.field_errors:
                combined.field_errors[field] = []
            combined.field_errors[field].extend(errors)

    return combined


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Email
    "validate_email",
    # URL
    "validate_url",
    # File
    "validate_file_extension",
    "validate_file_size",
    # String
    "validate_slug",
    "validate_json_string",
    # Numeric
    "validate_range",
    # List
    "validate_list_length",
    "validate_unique_items",
    # Combined
    "validate_all",
    # Constants
    "ALLOWED_EXTENSIONS",
]
